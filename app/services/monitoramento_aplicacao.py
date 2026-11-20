import hashlib
import os
import secrets
import time
import uuid
from datetime import datetime

from flask import current_app, g, request, session

from app.utils.db import get_db_connection


INTERVALO_ATIVIDADE_SEGUNDOS = 45


def _ip_cliente():
    encaminhado = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return encaminhado or request.remote_addr or None


def _identificar_cliente(user_agent):
    texto = (user_agent or "").lower()
    dispositivo = "Celular" if any(item in texto for item in ("mobile", "android", "iphone")) else "Computador"
    if "edg/" in texto:
        navegador = "Microsoft Edge"
    elif "firefox/" in texto:
        navegador = "Firefox"
    elif "chrome/" in texto:
        navegador = "Chrome"
    elif "safari/" in texto:
        navegador = "Safari"
    else:
        navegador = "Outro"
    if "windows" in texto:
        sistema = "Windows"
    elif "android" in texto:
        sistema = "Android"
    elif "iphone" in texto or "ipad" in texto:
        sistema = "iOS"
    elif "mac os" in texto or "macintosh" in texto:
        sistema = "macOS"
    elif "linux" in texto:
        sistema = "Linux"
    else:
        sistema = "Outro"
    return dispositivo, navegador, sistema


def _executar_seguro(operacao):
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        operacao(cursor)
        conn.commit()
        return True
    except Exception as exc:
        if conn:
            conn.rollback()
        try:
            current_app.logger.debug("Monitoramento indisponível: %s", exc)
        except RuntimeError:
            pass
        return False
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


def iniciar_sessao_monitorada(usuario_id):
    token = secrets.token_hex(32)
    user_agent = request.headers.get("User-Agent", "")[:500]
    dispositivo, navegador, sistema = _identificar_cliente(user_agent)
    ip = _ip_cliente()

    def operacao(cursor):
        cursor.execute("""
            INSERT INTO aplicacao_sessoes (
                token_sessao, usuario_id, login_em, ultima_atividade,
                ip_address, user_agent, dispositivo, navegador, sistema_operacional,
                ultimo_endpoint, ultima_rota
            ) VALUES (%s, %s, NOW(), NOW(), %s, %s, %s, %s, %s, %s, %s)
        """, (
            token, usuario_id, ip, user_agent, dispositivo, navegador, sistema,
            request.endpoint, request.path,
        ))

    if _executar_seguro(operacao):
        session["monitor_token"] = token
        session["monitor_ultimo_ping"] = int(time.time())


def encerrar_sessao_monitorada(motivo="logout"):
    token = session.get("monitor_token")
    if not token:
        return

    def operacao(cursor):
        cursor.execute("""
            UPDATE aplicacao_sessoes
            SET logout_em = COALESCE(logout_em, NOW()), motivo_encerramento = %s
            WHERE token_sessao = %s
        """, (motivo, token))

    _executar_seguro(operacao)


def registrar_tentativa_login(email, sucesso, motivo):
    email_normalizado = (email or "").strip().lower()
    if "@" in email_normalizado:
        inicio, dominio = email_normalizado.split("@", 1)
        mascarado = f"{inicio[:2]}***@{dominio}"
    else:
        mascarado = "não informado"
    identificador_hash = hashlib.sha256(email_normalizado.encode("utf-8")).hexdigest()
    user_agent = request.headers.get("User-Agent", "")[:500]

    def operacao(cursor):
        cursor.execute("""
            INSERT INTO aplicacao_tentativas_login (
                identificador_hash, identificador_mascarado, sucesso, motivo,
                ip_address, user_agent, ocorrido_em
            ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (
            identificador_hash, mascarado, int(bool(sucesso)), motivo[:100],
            _ip_cliente(), user_agent,
        ))

    _executar_seguro(operacao)


def atualizar_atividade(
    rota=None, forcar=False, duracao_ms=0, status_http=None
):
    token = session.get("monitor_token")
    usuario_id = session.get("usuario_id")
    if not token or not usuario_id:
        return
    agora = int(time.time())
    ultimo_ping = int(session.get("monitor_ultimo_ping") or 0)
    if not forcar and agora - ultimo_ping < INTERVALO_ATIVIDADE_SEGUNDOS:
        return
    rota = (rota or request.path or "")[:255]

    def operacao(cursor):
        cursor.execute("""
            UPDATE aplicacao_sessoes
            SET ultima_atividade = NOW(), ultimo_endpoint = %s, ultima_rota = %s,
                total_requisicoes = total_requisicoes + 1,
                tempo_total_ms = tempo_total_ms + %s,
                ultimo_status_http = COALESCE(%s, ultimo_status_http)
            WHERE token_sessao = %s AND logout_em IS NULL
        """, (
            request.endpoint, rota, max(int(duracao_ms or 0), 0),
            status_http, token,
        ))

    if _executar_seguro(operacao):
        session["monitor_ultimo_ping"] = agora


def registrar_erro(exception):
    if exception is None:
        return
    codigo = uuid.uuid4().hex[:12]
    mensagem = str(exception).replace("\n", " ")[:500]

    def operacao(cursor):
        cursor.execute("""
            INSERT INTO aplicacao_erros (
                codigo_correlacao, token_sessao, usuario_id, endpoint, rota,
                metodo, tipo_erro, mensagem_resumida, ocorrido_em
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
        """, (
            codigo, session.get("monitor_token"), session.get("usuario_id"),
            request.endpoint, request.path[:255], request.method,
            type(exception).__name__[:120], mensagem,
        ))

    _executar_seguro(operacao)


def registrar_monitoramento_aplicacao(app):
    @app.before_request
    def _iniciar_medicao():
        g.monitor_inicio = time.perf_counter()
        if (
            session.get("usuario_id")
            and not session.get("monitor_token")
            and request.endpoint != "main.logout"
        ):
            iniciar_sessao_monitorada(session["usuario_id"])

    @app.after_request
    def _finalizar_medicao(response):
        if request.endpoint not in {"static", "main.monitoramento_ping"}:
            duracao_ms = 0
            if hasattr(g, "monitor_inicio"):
                duracao_ms = int(
                    (time.perf_counter() - g.monitor_inicio) * 1000
                )
            atualizar_atividade(
                duracao_ms=duracao_ms,
                status_http=response.status_code,
            )
        return response

    @app.teardown_request
    def _registrar_excecao(exception):
        registrar_erro(exception)

