import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from flask import jsonify, render_template, request, session

from app.decorators import admin_required, login_required
from app.services.monitoramento_aplicacao import atualizar_atividade
from app.utils.db import get_db_connection


FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")


def _horario_brasilia(valor):
    """Converte DATETIME armazenado em UTC para o horário oficial de Brasília."""
    if not isinstance(valor, datetime):
        return valor
    if valor.tzinfo is None:
        valor = valor.replace(tzinfo=timezone.utc)
    return valor.astimezone(FUSO_BRASILIA)


def _converter_datas(registros, *campos):
    for registro in registros:
        for campo in campos:
            registro[campo] = _horario_brasilia(registro.get(campo))
    return registros


def _periodo_selecionado():
    periodo = request.args.get("periodo", default=7, type=int)
    return periodo if periodo in {1, 7, 30, 90} else 7


def register_monitoramento_aplicacao_routes(blueprint):
    @blueprint.route("/admin/monitoramento")
    @login_required
    @admin_required
    def monitoramento_aplicacao():
        periodo = _periodo_selecionado()
        usuario_id = request.args.get("usuario_id", type=int)
        centro_custos_id = request.args.get("centro_custos_id", type=int)
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT 1 AS banco_online")
            banco_online = bool(cursor.fetchone())

            cursor.execute("""
                SELECT
                    SUM(logout_em IS NULL AND ultima_atividade >= UTC_TIMESTAMP() - INTERVAL 5 MINUTE)
                        AS usuarios_ativos,
                    SUM(
                        DATE(CONVERT_TZ(login_em, '+00:00', '-03:00')) =
                        DATE(CONVERT_TZ(UTC_TIMESTAMP(), '+00:00', '-03:00'))
                    ) AS acessos_hoje,
                    ROUND(
                        SUM(CASE WHEN login_em >= UTC_TIMESTAMP() - INTERVAL 24 HOUR THEN tempo_total_ms ELSE 0 END)
                        / NULLIF(SUM(CASE WHEN login_em >= UTC_TIMESTAMP() - INTERVAL 24 HOUR THEN total_requisicoes ELSE 0 END), 0)
                    ) AS tempo_medio_ms
                FROM aplicacao_sessoes
            """)
            indicadores = cursor.fetchone() or {}

            cursor.execute("""
                SELECT COUNT(*) AS erros_24h
                FROM aplicacao_erros
                WHERE ocorrido_em >= UTC_TIMESTAMP() - INTERVAL 24 HOUR
            """)
            indicadores.update(cursor.fetchone() or {})

            condicoes = ["s.login_em >= UTC_TIMESTAMP() - INTERVAL %s DAY"]
            parametros = [periodo]
            if usuario_id:
                condicoes.append("s.usuario_id = %s")
                parametros.append(usuario_id)
            if centro_custos_id:
                condicoes.append("u.centro_custos_id = %s")
                parametros.append(centro_custos_id)
            onde = " AND ".join(condicoes)

            cursor.execute(f"""
                SELECT s.*, u.nome AS usuario_nome, u.matricula,
                       u.perfil, cc.codigo AS centro_codigo,
                       TIMESTAMPDIFF(MINUTE, s.login_em,
                           COALESCE(s.logout_em, s.ultima_atividade)) AS duracao_minutos,
                       CASE
                           WHEN s.logout_em IS NOT NULL THEN 'Encerrada'
                           WHEN s.ultima_atividade >= UTC_TIMESTAMP() - INTERVAL 5 MINUTE THEN 'Ativa'
                           WHEN s.ultima_atividade >= UTC_TIMESTAMP() - INTERVAL 30 MINUTE THEN 'Inativa'
                           ELSE 'Expirada'
                       END AS status_sessao
                FROM aplicacao_sessoes s
                LEFT JOIN usuarios u ON u.id = s.usuario_id
                LEFT JOIN centros_custos cc ON cc.id = u.centro_custos_id
                WHERE {onde}
                ORDER BY s.ultima_atividade DESC
                LIMIT 250
            """, tuple(parametros))
            sessoes = _converter_datas(
                cursor.fetchall() or [],
                "login_em", "ultima_atividade", "logout_em",
            )

            cursor.execute("""
                SELECT e.*, u.nome AS usuario_nome
                FROM aplicacao_erros e
                LEFT JOIN usuarios u ON u.id = e.usuario_id
                WHERE e.ocorrido_em >= UTC_TIMESTAMP() - INTERVAL %s DAY
                ORDER BY e.ocorrido_em DESC
                LIMIT 100
            """, (periodo,))
            erros = _converter_datas(cursor.fetchall() or [], "ocorrido_em")

            cursor.execute("""
                SELECT identificador_mascarado, sucesso, motivo, ip_address, ocorrido_em
                FROM aplicacao_tentativas_login
                WHERE ocorrido_em >= UTC_TIMESTAMP() - INTERVAL %s DAY
                ORDER BY ocorrido_em DESC
                LIMIT 100
            """, (periodo,))
            tentativas_login = _converter_datas(
                cursor.fetchall() or [], "ocorrido_em"
            )

            cursor.execute("""
                SELECT id, nome, matricula FROM usuarios
                WHERE ativo = 1 AND tem_acesso_sistema = 1 ORDER BY nome
            """)
            usuarios = cursor.fetchall() or []
            cursor.execute("""
                SELECT id, codigo, descricao FROM centros_custos
                WHERE ativo = 1 ORDER BY codigo
            """)
            centros = cursor.fetchall() or []
        finally:
            cursor.close()
            conn.close()

        versao = (
            os.getenv("RENDER_GIT_COMMIT")
            or os.getenv("GIT_COMMIT")
            or "Ambiente local"
        )
        return render_template(
            "monitoramento_aplicacao.html",
            indicadores=indicadores,
            sessoes=sessoes,
            erros=erros,
            tentativas_login=tentativas_login,
            usuarios=usuarios,
            centros=centros,
            filtros={
                "periodo": periodo,
                "usuario_id": usuario_id,
                "centro_custos_id": centro_custos_id,
            },
            saude={
                "aplicacao_online": True,
                "banco_online": banco_online,
                "verificado_em": datetime.now(FUSO_BRASILIA),
                "versao": versao[:12] if versao != "Ambiente local" else versao,
            },
        )

    @blueprint.route("/monitoramento/ping", methods=["POST"])
    @login_required
    def monitoramento_ping():
        dados = request.get_json(silent=True) or {}
        rota = str(dados.get("rota") or "")[:255]
        atualizar_atividade(rota=rota, forcar=True)
        return jsonify({"ok": True})
