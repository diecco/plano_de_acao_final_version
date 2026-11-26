import hmac
import logging
import os
import base64
from datetime import date, datetime, time, timezone
from decimal import Decimal
from functools import wraps

from flask import jsonify, request

from app.utils.db import get_db_connection


LOGGER = logging.getLogger(__name__)
VERSAO_API_BI = "v1"
TAMANHO_PAGINA_PADRAO = 500
TAMANHO_PAGINA_MAXIMO = 2000


def _resposta(payload, status=200):
    resposta = jsonify(payload)
    resposta.status_code = status
    resposta.headers["Cache-Control"] = "no-store"
    resposta.headers["X-Content-Type-Options"] = "nosniff"
    return resposta


def _extrair_chave():
    chave = (request.headers.get("X-API-Key") or "").strip()
    if chave:
        return chave
    autorizacao = (request.headers.get("Authorization") or "").strip()
    if autorizacao.lower().startswith("basic "):
        try:
            credencial = base64.b64decode(autorizacao[6:].strip()).decode("utf-8")
            usuario, separador, senha = credencial.partition(":")
        except (ValueError, UnicodeDecodeError):
            return ""
        usuario_configurado = (os.getenv("POWER_BI_API_USER") or "powerbi").strip()
        if separador and hmac.compare_digest(usuario, usuario_configurado):
            return senha
        return ""
    if autorizacao.lower().startswith("bearer "):
        return autorizacao[7:].strip()
    return ""


def api_bi_required(funcao):
    @wraps(funcao)
    def decorada(*args, **kwargs):
        chave_configurada = (os.getenv("POWER_BI_API_KEY") or "").strip()
        if not chave_configurada:
            LOGGER.error("POWER_BI_API_KEY não configurada; acesso à API BI bloqueado")
            return _resposta(
                {"erro": "api_indisponivel", "mensagem": "Credencial da API BI não configurada."},
                503,
            )
        chave_recebida = _extrair_chave()
        if not chave_recebida or not hmac.compare_digest(chave_recebida, chave_configurada):
            LOGGER.warning(
                "Acesso negado à API BI endpoint=%s ip=%s",
                request.path,
                request.headers.get("X-Forwarded-For", request.remote_addr),
            )
            return _resposta(
                {"erro": "nao_autorizado", "mensagem": "Credencial inválida."},
                401,
            )
        try:
            return funcao(*args, **kwargs)
        except ValueError as erro:
            return _resposta(
                {"erro": "parametro_invalido", "mensagem": str(erro)}, 400
            )
        except Exception:
            LOGGER.exception("Falha na API BI endpoint=%s", request.path)
            return _resposta(
                {"erro": "erro_interno", "mensagem": "Não foi possível consultar os dados."},
                500,
            )

    return decorada


def _paginacao():
    try:
        pagina = max(int(request.args.get("pagina", 1)), 1)
        tamanho = int(request.args.get("tamanho_pagina", TAMANHO_PAGINA_PADRAO))
    except (TypeError, ValueError):
        raise ValueError("Parâmetros de paginação inválidos.")
    tamanho = min(max(tamanho, 1), TAMANHO_PAGINA_MAXIMO)
    return pagina, tamanho, (pagina - 1) * tamanho


def _data_iso(nome):
    valor = (request.args.get(nome) or "").strip()
    if not valor:
        return None
    try:
        return date.fromisoformat(valor).isoformat()
    except ValueError as exc:
        raise ValueError(f"{nome} deve usar o formato AAAA-MM-DD.") from exc


def _data_hora_iso(nome):
    valor = (request.args.get(nome) or "").strip()
    if not valor:
        return None
    try:
        convertido = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        if convertido.tzinfo:
            convertido = convertido.astimezone(timezone.utc).replace(tzinfo=None)
        return convertido
    except ValueError as exc:
        raise ValueError(f"{nome} deve usar o formato ISO 8601.") from exc


def _filtros_comuns(campo_data, campo_cc, campo_atualizacao=None):
    filtros, parametros = [], []
    inicio = _data_iso("data_inicio")
    fim = _data_iso("data_fim")
    if inicio and fim and inicio > fim:
        raise ValueError("data_inicio não pode ser posterior a data_fim.")
    if inicio:
        filtros.append(f"{campo_data} >= %s")
        parametros.append(inicio)
    if fim:
        filtros.append(f"{campo_data} <= %s")
        parametros.append(fim)
    centros = [
        item.strip() for item in (request.args.get("centro_custos") or "").split(",")
        if item.strip()
    ]
    if centros:
        if len(centros) > 50:
            raise ValueError("Informe no máximo 50 centros de custos.")
        filtros.append(f"{campo_cc} IN ({','.join(['%s'] * len(centros))})")
        parametros.extend(centros)
    atualizado_apos = _data_hora_iso("atualizado_apos")
    if atualizado_apos and campo_atualizacao:
        filtros.append(f"{campo_atualizacao} >= %s")
        parametros.append(atualizado_apos)
    return filtros, parametros


def _serializar(valor):
    if isinstance(valor, (datetime, date, time)):
        return valor.isoformat()
    if isinstance(valor, Decimal):
        return float(valor)
    return valor


def _linhas_serializadas(linhas):
    return [{chave: _serializar(valor) for chave, valor in linha.items()} for linha in linhas]


def _executar_paginado(base_from, campos, filtros, parametros, ordem):
    pagina, tamanho, offset = _paginacao()
    onde = f" WHERE {' AND '.join(filtros)}" if filtros else ""
    conexao = get_db_connection()
    cursor = conexao.cursor(dictionary=True)
    try:
        cursor.execute(f"SELECT COUNT(*) total {base_from}{onde}", tuple(parametros))
        total = int((cursor.fetchone() or {}).get("total") or 0)
        cursor.execute(
            f"SELECT {campos} {base_from}{onde} ORDER BY {ordem} LIMIT %s OFFSET %s",
            tuple(parametros + [tamanho, offset]),
        )
        dados = _linhas_serializadas(cursor.fetchall())
    finally:
        cursor.close()
        conexao.close()
    LOGGER.info("API BI endpoint=%s registros=%s pagina=%s", request.path, len(dados), pagina)
    return _resposta({
        "versao": VERSAO_API_BI,
        "pagina": pagina,
        "tamanho_pagina": tamanho,
        "total_registros": total,
        "total_paginas": (total + tamanho - 1) // tamanho if total else 0,
        "dados": dados,
    })


def register_api_bi_routes(blueprint):
    @blueprint.route("/api/bi/v1")
    @api_bi_required
    def api_bi_indice():
        return _resposta({
            "nome": "TrackPlan BI API",
            "versao": VERSAO_API_BI,
            "somente_leitura": True,
            "recursos": [
                "/api/bi/v1/ocorrencias",
                "/api/bi/v1/observacoes-comportamentais",
                "/api/bi/v1/auditorias-padrao",
                "/api/bi/v1/ifs",
            ],
        })

    @blueprint.route("/api/bi/v1/ocorrencias")
    @api_bi_required
    def api_bi_ocorrencias():
        filtros, parametros = _filtros_comuns(
            "r.data_ocorrencia", "COALESCE(cc.codigo, r.centro_custos_codigo)",
            "r.atualizado_em",
        )
        return _executar_paginado(
            """FROM relatos_ocorrencias r
               LEFT JOIN centros_custos cc ON cc.id=r.centro_custos_id
               LEFT JOIN relatos_ocorrencias_classificacoes cl ON cl.relato_id=r.id""",
            """r.id, r.solicitacao, r.data_ocorrencia, r.hora_ocorrencia,
               r.tipo_relato, r.classificacao_ocorrencia, r.tipo_origem,
               r.descricao_ocorrencia, r.acao_tomada, r.area_ocorrencia,
               r.local_ocorrencia, r.turno, r.responsavel_registro,
               r.requisitante_nome, r.situacao_fluig,
               COALESCE(cc.codigo, r.centro_custos_codigo) centro_custos_codigo,
               cc.descricao centro_custos_descricao,
               cl.severidade potencial_severidade, cl.probabilidade,
               cl.nivel_risco, cl.classificado_em,
               r.importado_em, r.atualizado_em""",
            filtros, parametros, "r.data_ocorrencia DESC, r.id DESC",
        )

    @blueprint.route("/api/bi/v1/observacoes-comportamentais")
    @api_bi_required
    def api_bi_observacoes():
        filtros, parametros = _filtros_comuns(
            "r.data_observacao", "r.centro_custos_codigo", "r.atualizado_em"
        )
        return _executar_paginado(
            "FROM oc_fluig_registros r",
            """r.id, r.solicitacao, r.data_observacao, r.hora_observacao,
               r.observador_nome, r.observador_matricula,
               r.centro_custos_codigo, r.centro_custos_descricao,
               r.local_observado, r.setor_observado, r.area, r.atividade,
               r.pessoas_observadas, r.status, r.situacao_fluig,
               r.importado_em, r.atualizado_em""",
            filtros, parametros, "r.data_observacao DESC, r.id DESC",
        )

    @blueprint.route("/api/bi/v1/auditorias-padrao")
    @api_bi_required
    def api_bi_auditorias():
        filtros, parametros = _filtros_comuns(
            "ap.data_auditoria", "cc.codigo", "ap.atualizado_em"
        )
        base = """FROM auditorias_padrao ap
                  JOIN usuarios auditor ON auditor.id=ap.auditor_id
                  JOIN usuarios auditado ON auditado.id=ap.auditado_id
                  LEFT JOIN centros_custos cc ON cc.id=auditado.centro_custos_id
                  LEFT JOIN procedimentos p ON p.id=ap.procedimento_id
                  LEFT JOIN procedimento_revisoes pr ON pr.id=ap.procedimento_revisao_id
                  LEFT JOIN (
                      SELECT auditoria_id,
                             SUM(resultado='C') conformes,
                             SUM(resultado='NC') nao_conformes,
                             SUM(resultado='NA') nao_aplicaveis,
                             SUM(resultado IN ('C','NC')) aplicaveis
                      FROM auditoria_padrao_respostas GROUP BY auditoria_id
                  ) resumo ON resumo.auditoria_id=ap.id"""
        return _executar_paginado(
            base,
            """ap.id, ap.data_auditoria, ap.area_auditada,
               ap.atividade_auditada, ap.pontos_observados,
               ap.necessita_revisao_padrao, auditor.nome auditor_nome,
               auditado.nome auditado_nome, cc.codigo centro_custos_codigo,
               cc.descricao centro_custos_descricao,
               p.numero_documento, p.titulo procedimento_titulo,
               pr.numero_revisao, COALESCE(resumo.conformes,0) conformes,
               COALESCE(resumo.nao_conformes,0) nao_conformes,
               COALESCE(resumo.nao_aplicaveis,0) nao_aplicaveis,
               COALESCE(resumo.aplicaveis,0) itens_aplicaveis,
               ROUND(CASE WHEN COALESCE(resumo.aplicaveis,0)>0
                    THEN resumo.conformes/resumo.aplicaveis*100 ELSE 0 END,2) aderencia,
               ap.criado_em, ap.atualizado_em""",
            filtros + ["ap.ativo=1"], parametros,
            "ap.data_auditoria DESC, ap.id DESC",
        )

    @blueprint.route("/api/bi/v1/ifs")
    @api_bi_required
    def api_bi_ifs():
        filtros, parametros = _filtros_comuns(
            "base.data_inspecao", "base.centro_custos_codigo", "base.atualizado_em"
        )
        base_from = """FROM (
            SELECT i.id, 'IFS Tradimaq' origem_ifs, i.data_inspecao,
                   i.hora_inspecao, i.local_inspecao, i.descricao_atividade_os,
                   cc.codigo centro_custos_codigo, cc.descricao centro_custos_descricao,
                   u.nome responsavel_nome, i.total_itens_avaliados,
                   i.total_nao_conformidades,
                   ROUND(CASE WHEN COALESCE(rx.denominador,0)>0
                         THEN rx.conformes/rx.denominador*100 ELSE 0 END,2) nota,
                   CASE WHEN COALESCE(rx.denominador,0)=0 THEN '-'
                        WHEN rx.conformes/rx.denominador*100 >= 85 THEN 'Satisfatório'
                        ELSE 'Insatisfatório' END conceito,
                   NULL situacao, COALESCE(rx.potencial_a,0) potencial_a,
                   COALESCE(rx.potencial_b,0) potencial_b,
                   COALESCE(rx.potencial_c,0) potencial_c,
                   i.criado_em, i.atualizado_em
            FROM ifs_inspecoes i
            JOIN usuarios u ON u.id=i.profissional_sesmt_id
            LEFT JOIN centros_custos cc ON cc.id=u.centro_custos_id
            LEFT JOIN (
                SELECT r.inspecao_id,
                       SUM(r.resultado='S' AND it.potencial IN ('A','B','C')) conformes,
                       SUM(CASE WHEN r.resultado='S' AND it.potencial IN ('A','B','C') THEN 1
                                WHEN r.resultado='N' AND it.potencial='A' THEN 2
                                WHEN r.resultado='N' AND it.potencial='B' THEN 1
                                WHEN r.resultado='N' AND it.potencial='C' THEN 0.5 ELSE 0 END) denominador,
                       SUM(r.resultado='N' AND it.potencial='A') potencial_a,
                       SUM(r.resultado='N' AND it.potencial='B') potencial_b,
                       SUM(r.resultado='N' AND it.potencial='C') potencial_c
                FROM ifs_respostas r JOIN ifs_itens it ON it.id=r.item_id
                GROUP BY r.inspecao_id
            ) rx ON rx.inspecao_id=i.id
            WHERE i.ativo=1
            UNION ALL
            SELECT c.id, 'IFS do Cliente', c.data_inspecao, c.hora_inspecao,
                   c.local_inspecao, c.descricao_atividade_os,
                   cc.codigo, cc.descricao, u.nome, c.total_itens_avaliados,
                   c.total_nao_conformidades, c.percentual, c.conceito, c.status,
                   COALESCE(dx.potencial_a,0), COALESCE(dx.potencial_b,0),
                   COALESCE(dx.potencial_c,0), c.criado_em, c.atualizado_em
            FROM ifs_cliente_inspecoes c
            JOIN usuarios u ON u.id=c.criado_por
            LEFT JOIN centros_custos cc ON cc.id=c.centro_custos_id
            LEFT JOIN (
                SELECT inspecao_id, SUM(potencial='A') potencial_a,
                       SUM(potencial='B') potencial_b, SUM(potencial='C') potencial_c
                FROM ifs_cliente_desvios GROUP BY inspecao_id
            ) dx ON dx.inspecao_id=c.id
            WHERE c.ativo=1
        ) base"""
        return _executar_paginado(
            base_from,
            "base.*", filtros, parametros,
            "base.data_inspecao DESC, base.origem_ifs, base.id DESC",
        )
