import hashlib
import os
from datetime import date

from flask import (
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)

from app.decorators import login_required, module_required
from app.upload_security import UploadService, UploadValidationError
from app.utils.db import get_db_connection


STATUS_ACR = {
    "Rascunho",
    "Em Investigação",
    "Aguardando Informações",
    "Concluída",
    "Cancelada",
}

ORDENACOES_ACR = {
    "numero": "i.ano",
    "ocorrencia": "COALESCE(i.equipamento_processo, i.descricao_ocorrencia)",
    "classificacao": "c.nome",
    "gravidade": "g.ordem",
    "responsavel": "u.nome",
    "status": "i.status",
    "data": "i.data_ocorrencia",
}

ORDENACOES_ACOES_ACR = {
    "descricao": "a.descricao",
    "responsavel": "u.nome",
    "prazo": "a.prazo",
    "status": "a.status",
}

STATUS_ACAO_ACR = {
    "Não iniciada",
    "Em andamento",
    "Concluída",
    "Cancelada",
    "Vencida",
}

EXTENSOES_EVIDENCIA_ACAO = {
    "pdf",
    "png",
    "jpg",
    "jpeg",
    "doc",
    "docx",
    "xls",
    "xlsx",
}

ETAPAS_EVIDENCIA_ACR = {
    "identificacao": "Identificação",
    "investigacao": "Investigação",
    "causas": "Causas",
    "acoes": "Ações",
    "eficacia": "Eficácia",
}

TAMANHO_MAXIMO_EVIDENCIA_ACR = 10 * 1024 * 1024

RESULTADOS_EFICACIA_ACR = {
    "Eficaz",
    "Parcialmente eficaz",
    "Ineficaz",
}

CATEGORIAS_6M = {
    "metodo": "Método",
    "maquina": "Máquina",
    "mao_obra": "Mão de obra",
    "material": "Material",
    "medicao": "Medição",
    "meio_ambiente": "Meio ambiente",
}

CLASSIFICACOES_6M = {
    "potencial": "Potencial",
    "descartada": "Descartada",
    "contribuinte": "Contribuinte",
    "basica": "Básica",
    "fundamental": "Fundamental",
}


def _aplicar_escopo(query, params, alias="i"):
    perfil = session.get("perfil")
    usuario_id = session.get("usuario_id")

    if perfil == "basico":
        query += f"""
            AND (
                {alias}.criador_id = %s
                OR {alias}.responsavel_id = %s
                OR EXISTS (
                    SELECT 1
                    FROM acr_participantes ap
                    WHERE ap.investigacao_id = {alias}.id
                      AND ap.usuario_id = %s
                      AND ap.ativo = 1
                )
            )
        """
        params.extend([usuario_id, usuario_id, usuario_id])
    elif perfil == "intermediario":
        query += f" AND {alias}.centro_custos_id = %s"
        params.append(session.get("centro_custos_id"))

    return query, params


def _buscar_dominios(cursor):
    dominios = {}
    for chave, tabela in (
        ("origens", "acr_origens"),
        ("classificacoes", "acr_classificacoes"),
        ("gravidades", "acr_gravidades"),
        ("metodologias", "acr_metodologias"),
    ):
        filtro_implementada = (
            " AND implementada = 1"
            if tabela == "acr_metodologias"
            else ""
        )
        cursor.execute(
            f"""
            SELECT id, nome
            FROM {tabela}
            WHERE ativo = 1
            {filtro_implementada}
            ORDER BY ordem, nome
            """
        )
        dominios[chave] = cursor.fetchall()
    return dominios


def _buscar_centros_e_responsaveis(cursor):
    centro_sessao = session.get("centro_custos_id")

    cursor.execute(
        """
        SELECT id, codigo, descricao, superintendencia_id
        FROM centros_custos
        WHERE ativo = 1
          AND id = %s
        """,
        (centro_sessao,),
    )
    centros = cursor.fetchall()

    cursor.execute(
        """
        SELECT id, nome, matricula, centro_custos_id
        FROM usuarios
        WHERE ativo = 1
          AND tem_acesso_sistema = 1
          AND (acesso_acr = 1 OR perfil = 'administrador')
          AND centro_custos_id = %s
        ORDER BY nome
        """,
        (centro_sessao,),
    )

    responsaveis = cursor.fetchall()
    cursor.execute(
        """
        SELECT id, nome, matricula, centro_custos_id
        FROM usuarios
        WHERE ativo = 1
          AND centro_custos_id = %s
        ORDER BY nome
        """,
        (centro_sessao,),
    )
    return centros, responsaveis, cursor.fetchall()


def _validar_id_no_dominio(cursor, tabela, registro_id):
    cursor.execute(
        f"SELECT id FROM {tabela} WHERE id = %s AND ativo = 1",
        (registro_id,),
    )
    return cursor.fetchone() is not None


def _garantir_origem_acao_acr(cursor, investigacao):
    codigo_centro = (investigacao.get("centro_codigo") or "").strip()
    if not codigo_centro:
        raise ValueError(
            "O centro de custos da ACR não possui código para gerar a origem."
        )
    descricao = f"Análise de Causa Raiz - {codigo_centro}"
    cursor.execute(
        """
        INSERT INTO origens (nome, descricao, centro_custos_id, ativo)
        VALUES (%s, %s, %s, 1)
        ON DUPLICATE KEY UPDATE
            id = LAST_INSERT_ID(id),
            ativo = 1
        """,
        (
            descricao,
            descricao,
            investigacao["centro_custos_id"],
        ),
    )
    origem_id = cursor.lastrowid
    cursor.execute(
        """
        SELECT id, centro_custos_id
        FROM origens
        WHERE id = %s
        """,
        (origem_id,),
    )
    origem = cursor.fetchone()
    if (
        not origem
        or origem["centro_custos_id"] != investigacao["centro_custos_id"]
    ):
        raise ValueError(
            "A origem técnica da ACR está vinculada a outro centro de custos."
        )
    return origem_id


def _buscar_investigacao_acessivel(cursor, investigacao_id):
    query = """
        SELECT
            i.*,
            o.nome AS origem,
            c.nome AS classificacao,
            g.nome AS gravidade,
            m.nome AS metodologia,
            m.codigo AS metodologia_codigo,
            u.nome AS responsavel,
            uc.nome AS criador,
            cc.codigo AS centro_codigo,
            cc.descricao AS centro_descricao
        FROM acr_investigacoes i
        LEFT JOIN acr_origens o ON o.id = i.origem_id
        LEFT JOIN acr_classificacoes c ON c.id = i.classificacao_id
        LEFT JOIN acr_gravidades g ON g.id = i.gravidade_id
        LEFT JOIN acr_metodologias m ON m.id = i.metodologia_id
        LEFT JOIN usuarios u ON u.id = i.responsavel_id
        LEFT JOIN usuarios uc ON uc.id = i.criador_id
        LEFT JOIN centros_custos cc ON cc.id = i.centro_custos_id
        WHERE i.id = %s
          AND i.ativo = 1
    """
    params = [investigacao_id]
    query, params = _aplicar_escopo(query, params)
    cursor.execute(query, params)
    return cursor.fetchone()


def _diretorio_evidencias_acr():
    return os.path.join(
        current_app.config.get(
            "UPLOAD_FOLDER",
            os.path.join(current_app.root_path, "static", "evidencias"),
        ),
        "acr",
    )


def _tamanho_arquivo(arquivo):
    posicao = arquivo.stream.tell()
    arquivo.stream.seek(0, os.SEEK_END)
    tamanho = arquivo.stream.tell()
    arquivo.stream.seek(posicao)
    return tamanho


def _hash_sha256_arquivo(caminho):
    resumo = hashlib.sha256()
    with open(caminho, "rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


def register_investigacao_causa_raiz_routes(blueprint):
    @blueprint.route("/acr")
    @login_required
    @module_required("acesso_acr")
    def investigacoes_acr():
        busca = (request.args.get("busca") or "").strip()
        status = (request.args.get("status") or "").strip()
        origem_id = request.args.get("origem_id", type=int)
        classificacao_id = request.args.get("classificacao_id", type=int)
        gravidade_id = request.args.get("gravidade_id", type=int)
        data_inicio = (request.args.get("data_inicio") or "").strip()
        data_fim = (request.args.get("data_fim") or "").strip()
        ordenacao = (request.args.get("ordenacao") or "numero").strip()
        direcao = (request.args.get("direcao") or "desc").strip().lower()

        if ordenacao not in ORDENACOES_ACR:
            ordenacao = "numero"
        if direcao not in ("asc", "desc"):
            direcao = "desc"

        for valor, rotulo in (
            (data_inicio, "inicial"),
            (data_fim, "final"),
        ):
            if valor:
                try:
                    date.fromisoformat(valor)
                except ValueError:
                    flash(f"Informe uma data {rotulo} válida.", "warning")
                    if rotulo == "inicial":
                        data_inicio = ""
                    else:
                        data_fim = ""
        if data_inicio and data_fim and data_inicio > data_fim:
            flash(
                "A data inicial não pode ser posterior à data final.",
                "warning",
            )
            data_inicio = ""
            data_fim = ""

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            dominios = _buscar_dominios(cursor)
            query = """
                SELECT
                    i.id,
                    i.numero,
                    i.data_ocorrencia,
                    i.equipamento_processo,
                    i.descricao_ocorrencia,
                    i.status,
                    i.criado_em,
                    o.nome AS origem,
                    c.nome AS classificacao,
                    g.nome AS gravidade,
                    m.nome AS metodologia,
                    u.nome AS responsavel,
                    cc.codigo AS centro_codigo,
                    cc.descricao AS centro_descricao
                FROM acr_investigacoes i
                LEFT JOIN acr_origens o ON o.id = i.origem_id
                LEFT JOIN acr_classificacoes c ON c.id = i.classificacao_id
                LEFT JOIN acr_gravidades g ON g.id = i.gravidade_id
                LEFT JOIN acr_metodologias m ON m.id = i.metodologia_id
                LEFT JOIN usuarios u ON u.id = i.responsavel_id
                LEFT JOIN centros_custos cc ON cc.id = i.centro_custos_id
                WHERE i.ativo = 1
            """
            params = []
            query, params = _aplicar_escopo(query, params)

            if busca:
                termo = f"%{busca}%"
                query += """
                    AND (
                        i.numero LIKE %s
                        OR i.equipamento_processo LIKE %s
                        OR i.descricao_ocorrencia LIKE %s
                        OR u.nome LIKE %s
                    )
                """
                params.extend([termo, termo, termo, termo])
            if status in STATUS_ACR:
                query += " AND i.status = %s"
                params.append(status)
            if origem_id:
                query += " AND i.origem_id = %s"
                params.append(origem_id)
            if classificacao_id:
                query += " AND i.classificacao_id = %s"
                params.append(classificacao_id)
            if gravidade_id:
                query += " AND i.gravidade_id = %s"
                params.append(gravidade_id)
            if data_inicio:
                query += " AND i.data_ocorrencia >= %s"
                params.append(data_inicio)
            if data_fim:
                query += " AND i.data_ocorrencia <= %s"
                params.append(data_fim)

            coluna_ordenacao = ORDENACOES_ACR[ordenacao]
            direcao_sql = direcao.upper()
            if ordenacao == "numero":
                query += (
                    f" ORDER BY {coluna_ordenacao} {direcao_sql}, "
                    f"i.sequencial {direcao_sql}"
                )
            else:
                query += (
                    f" ORDER BY {coluna_ordenacao} {direcao_sql}, "
                    "i.ano DESC, i.sequencial DESC"
                )
            cursor.execute(query, params)
            investigacoes = cursor.fetchall()

            indicadores = {
                "total": len(investigacoes),
                "em_andamento": sum(
                    item["status"] in (
                        "Em Investigação",
                        "Aguardando Informações",
                    )
                    for item in investigacoes
                ),
                "rascunhos": sum(
                    item["status"] == "Rascunho" for item in investigacoes
                ),
                "concluidas": sum(
                    item["status"] == "Concluída" for item in investigacoes
                ),
            }
            return render_template(
                "investigacoes_causa_raiz.html",
                investigacoes=investigacoes,
                indicadores=indicadores,
                dominios=dominios,
                status_acr=sorted(STATUS_ACR),
                filtros={
                    "busca": busca,
                    "status": status,
                    "origem_id": origem_id,
                    "classificacao_id": classificacao_id,
                    "gravidade_id": gravidade_id,
                    "data_inicio": data_inicio,
                    "data_fim": data_fim,
                },
                ordenacao=ordenacao,
                direcao=direcao,
            )
        finally:
            cursor.close()
            conn.close()

    @blueprint.route("/acr/<int:investigacao_id>")
    @login_required
    @module_required("acesso_acr")
    def detalhar_investigacao_acr(investigacao_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            investigacao = _buscar_investigacao_acessivel(
                cursor,
                investigacao_id,
            )
            if not investigacao:
                flash("Investigação não encontrada ou fora do seu escopo.", "danger")
                return redirect(url_for("main.investigacoes_acr"))

            cursor.execute(
                """
                SELECT ordem, pergunta, resposta, causa_raiz, atualizado_em
                FROM acr_5_porques
                WHERE investigacao_id = %s
                ORDER BY ordem
                """,
                (investigacao_id,),
            )
            respostas_banco = {
                item["ordem"]: item for item in cursor.fetchall()
            }
            porques = [
                {
                    "ordem": ordem,
                    "pergunta": (
                        respostas_banco.get(ordem, {}).get("pergunta") or ""
                    ),
                    "resposta": (
                        respostas_banco.get(ordem, {}).get("resposta") or ""
                    ),
                    "causa_raiz": bool(
                        respostas_banco.get(ordem, {}).get("causa_raiz")
                    ),
                }
                for ordem in range(1, 6)
            ]
            itens_6m = []
            if investigacao["metodologia_codigo"] == "ishikawa":
                cursor.execute(
                    """
                    SELECT id, categoria, descricao, causa_raiz, ordem,
                           classificacao, justificativa, validacao
                    FROM acr_6m_itens
                    WHERE investigacao_id = %s
                    ORDER BY categoria, ordem, id
                    """,
                    (investigacao_id,),
                )
                itens_6m = cursor.fetchall()
            itens_6m_por_categoria = {
                codigo: [] for codigo in CATEGORIAS_6M
            }
            for item in itens_6m:
                if item["categoria"] in itens_6m_por_categoria:
                    itens_6m_por_categoria[item["categoria"]].append(item)
            cursor.execute(
                """
                SELECT status, atualizado_em
                FROM acr_etapas
                WHERE investigacao_id = %s
                  AND codigo = %s
                """,
                (
                    investigacao_id,
                    (
                        "6m"
                        if investigacao["metodologia_codigo"] == "ishikawa"
                        else "5_porques"
                    ),
                ),
            )
            etapa = cursor.fetchone() or {
                "status": "Não iniciada",
                "atualizado_em": None,
            }
            cursor.execute(
                """
                SELECT id, descricao, identificada_em
                FROM acr_causas
                WHERE investigacao_id = %s AND confirmada = 1
                ORDER BY id
                """,
                (investigacao_id,),
            )
            causas_raiz = cursor.fetchall()
            causa_raiz = causas_raiz[0] if causas_raiz else None
            acao_sort = request.args.get("acao_sort", "prazo")
            if acao_sort not in ORDENACOES_ACOES_ACR:
                acao_sort = "prazo"
            acao_order = request.args.get("acao_order", "asc").lower()
            if acao_order not in ("asc", "desc"):
                acao_order = "asc"
            query_acoes = """
                SELECT
                    a.id, a.descricao, a.prazo, a.status,
                    a.responsavel_id, a.observacoes,
                    a.data_conclusao, a.arquivo_evidencia,
                    u.nome AS responsavel,
                    u.matricula AS responsavel_matricula
                FROM acr_acoes aa
                JOIN acoes a ON a.id = aa.acao_id
                LEFT JOIN usuarios u ON u.id = a.responsavel_id
                WHERE aa.investigacao_id = %s AND a.ativo = 1
            """
            params_acoes = [investigacao_id]
            query_acoes += (
                f" ORDER BY {ORDENACOES_ACOES_ACR[acao_sort]} "
                f"{acao_order.upper()}, a.id"
            )
            cursor.execute(query_acoes, tuple(params_acoes))
            acoes_vinculadas = cursor.fetchall()
            total_acoes = len(acoes_vinculadas)
            acoes_concluidas = bool(total_acoes) and all(
                acao["status"] == "Concluída"
                for acao in acoes_vinculadas
            )
            cursor.execute(
                """
                SELECT
                    ve.id, ve.ciclo, ve.data_prevista,
                    ve.data_realizada, ve.criterio, ve.resultado,
                    ve.justificativa, ve.responsavel_id,
                    u.nome AS responsavel
                FROM acr_verificacoes_eficacia ve
                LEFT JOIN usuarios u ON u.id = ve.responsavel_id
                WHERE ve.investigacao_id = %s
                ORDER BY ve.ciclo DESC
                """,
                (investigacao_id,),
            )
            verificacoes_eficacia = cursor.fetchall()
            verificacao_atual = (
                verificacoes_eficacia[0]
                if verificacoes_eficacia
                and verificacoes_eficacia[0]["resultado"] is None
                else None
            )
            cursor.execute(
                """
                SELECT status, atualizado_em, concluido_em
                FROM acr_etapas
                WHERE investigacao_id = %s AND codigo = 'eficacia'
                """,
                (investigacao_id,),
            )
            etapa_eficacia = cursor.fetchone() or {
                "status": "Não iniciada",
                "atualizado_em": None,
                "concluido_em": None,
            }
            cursor.execute(
                """
                SELECT
                    e.id, e.etapa, e.nome_original, e.extensao,
                    e.tamanho_bytes, e.descricao, e.criado_em,
                    e.enviado_por, u.nome AS enviado_por_nome
                FROM acr_evidencias e
                LEFT JOIN usuarios u ON u.id = e.enviado_por
                WHERE e.investigacao_id = %s
                  AND e.excluido_em IS NULL
                ORDER BY e.criado_em DESC, e.id DESC
                """,
                (investigacao_id,),
            )
            evidencias_por_etapa = {
                codigo: [] for codigo in ETAPAS_EVIDENCIA_ACR
            }
            for evidencia in cursor.fetchall():
                if evidencia["etapa"] in evidencias_por_etapa:
                    evidencias_por_etapa[evidencia["etapa"]].append(evidencia)
            cursor.execute(
                """
                SELECT
                    h.id, h.evento, h.etapa, h.entidade_tipo,
                    h.entidade_id, h.criado_em,
                    u.nome AS usuario,
                    COALESCE(
                        JSON_UNQUOTE(
                            JSON_EXTRACT(
                                h.valor_novo_json,
                                '$.justificativa'
                            )
                        ),
                        ''
                    ) AS justificativa
                FROM acr_historico h
                LEFT JOIN usuarios u ON u.id = h.usuario_id
                WHERE h.investigacao_id = %s
                ORDER BY h.criado_em DESC, h.id DESC
                """,
                (investigacao_id,),
            )
            historico_acr = cursor.fetchall()
            cursor.execute(
                """
                SELECT id, nome, matricula
                FROM usuarios
                WHERE ativo = 1 AND centro_custos_id = %s
                ORDER BY nome
                """,
                (investigacao["centro_custos_id"],),
            )
            responsaveis_acao = cursor.fetchall()
            cursor.execute(
                """
                SELECT u.id, u.nome, u.matricula
                FROM acr_participantes ap
                JOIN usuarios u ON u.id = ap.usuario_id
                WHERE ap.investigacao_id = %s
                  AND ap.ativo = 1
                  AND ap.usuario_id NOT IN (%s, %s)
                ORDER BY u.nome
                """,
                (
                    investigacao_id,
                    investigacao["criador_id"],
                    investigacao["responsavel_id"],
                ),
            )
            participantes_acr = cursor.fetchall()
            cursor.execute(
                """
                SELECT id, nome, matricula
                FROM usuarios
                WHERE ativo = 1
                  AND centro_custos_id = %s
                ORDER BY nome
                """,
                (investigacao["centro_custos_id"],),
            )
            participantes_disponiveis = cursor.fetchall()
            return render_template(
                "investigacao_causa_raiz_detalhe.html",
                investigacao=investigacao,
                porques=porques,
                categorias_6m=CATEGORIAS_6M,
                classificacoes_6m=CLASSIFICACOES_6M,
                itens_6m_por_categoria=itens_6m_por_categoria,
                etapa=etapa,
                causa_raiz=causa_raiz,
                causas_raiz=causas_raiz,
                acoes_vinculadas=acoes_vinculadas,
                acoes_concluidas=acoes_concluidas,
                verificacoes_eficacia=verificacoes_eficacia,
                verificacao_atual=verificacao_atual,
                verificacao_atual_pode_avaliar=(
                    bool(verificacao_atual)
                    and verificacao_atual["data_prevista"] <= date.today()
                ),
                etapa_eficacia=etapa_eficacia,
                etapas_evidencia=ETAPAS_EVIDENCIA_ACR,
                evidencias_por_etapa=evidencias_por_etapa,
                historico_acr=historico_acr,
                pode_gerenciar_eficacia=(
                    session.get("usuario_id") == investigacao["criador_id"]
                ),
                responsaveis_acao=responsaveis_acao,
                participantes_acr=participantes_acr,
                participantes_disponiveis=participantes_disponiveis,
                acao_sort=acao_sort,
                acao_order=acao_order,
                origem_acao_descricao=(
                    "Análise de Causa Raiz - "
                    f"{investigacao['centro_codigo']}"
                ),
                hoje=date.today().isoformat(),
                somente_leitura=investigacao["status"] in (
                    "Concluída",
                    "Cancelada",
                ),
            )
        finally:
            cursor.close()
            conn.close()

    @blueprint.route("/acr/<int:investigacao_id>/relatorio.pdf")
    @login_required
    @module_required("acesso_acr")
    def relatorio_pdf_acr(investigacao_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            investigacao = _buscar_investigacao_acessivel(
                cursor,
                investigacao_id,
            )
            if not investigacao:
                flash("Investigação não encontrada ou fora do seu escopo.", "danger")
                return redirect(url_for("main.investigacoes_acr"))

            cursor.execute(
                """
                SELECT u.nome
                FROM acr_participantes ap
                JOIN usuarios u ON u.id = ap.usuario_id
                WHERE ap.investigacao_id = %s AND ap.ativo = 1
                  AND ap.usuario_id NOT IN (%s, %s)
                ORDER BY u.nome
                """,
                (
                    investigacao_id,
                    investigacao["criador_id"],
                    investigacao["responsavel_id"],
                ),
            )
            participantes = [item["nome"] for item in cursor.fetchall()]

            cursor.execute(
                """
                SELECT ordem, pergunta, resposta, causa_raiz
                FROM acr_5_porques
                WHERE investigacao_id = %s
                ORDER BY ordem
                """,
                (investigacao_id,),
            )
            porques = cursor.fetchall()

            itens_6m = []
            if investigacao["metodologia_codigo"] == "ishikawa":
                cursor.execute(
                    """
                    SELECT categoria, descricao, causa_raiz, ordem,
                           classificacao, justificativa, validacao
                    FROM acr_6m_itens
                    WHERE investigacao_id = %s
                    ORDER BY categoria, ordem, id
                    """,
                    (investigacao_id,),
                )
                itens_6m = cursor.fetchall()

            cursor.execute(
                """
                SELECT descricao, identificada_em
                FROM acr_causas
                WHERE investigacao_id = %s AND confirmada = 1
                ORDER BY id
                """,
                (investigacao_id,),
            )
            causas_raiz = cursor.fetchall()
            causa_raiz = causas_raiz[0] if causas_raiz else None

            cursor.execute(
                """
                SELECT
                    a.descricao, a.prazo, a.status,
                    a.data_conclusao, a.observacoes,
                    u.nome AS responsavel
                FROM acr_acoes aa
                JOIN acoes a ON a.id = aa.acao_id
                LEFT JOIN usuarios u ON u.id = a.responsavel_id
                WHERE aa.investigacao_id = %s AND a.ativo = 1
                ORDER BY a.prazo, a.id
                """,
                (investigacao_id,),
            )
            acoes = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    ve.ciclo, ve.data_prevista, ve.data_realizada,
                    ve.criterio, ve.resultado, ve.justificativa,
                    u.nome AS responsavel
                FROM acr_verificacoes_eficacia ve
                LEFT JOIN usuarios u ON u.id = ve.responsavel_id
                WHERE ve.investigacao_id = %s
                ORDER BY ve.ciclo
                """,
                (investigacao_id,),
            )
            verificacoes = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    e.etapa, e.nome_original, e.descricao,
                    e.tamanho_bytes, e.criado_em,
                    u.nome AS enviado_por_nome
                FROM acr_evidencias e
                LEFT JOIN usuarios u ON u.id = e.enviado_por
                WHERE e.investigacao_id = %s
                  AND e.excluido_em IS NULL
                ORDER BY e.etapa, e.criado_em, e.id
                """,
                (investigacao_id,),
            )
            evidencias = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    h.evento, h.etapa, h.criado_em,
                    u.nome AS usuario,
                    COALESCE(
                        JSON_UNQUOTE(
                            JSON_EXTRACT(
                                h.valor_novo_json,
                                '$.justificativa'
                            )
                        ),
                        ''
                    ) AS justificativa
                FROM acr_historico h
                LEFT JOIN usuarios u ON u.id = h.usuario_id
                WHERE h.investigacao_id = %s
                ORDER BY h.criado_em, h.id
                """,
                (investigacao_id,),
            )
            historico = cursor.fetchall()

            from app.utils.acr_pdf import gerar_pdf_acr

            pdf = gerar_pdf_acr(
                {
                    "investigacao": investigacao,
                    "participantes": participantes,
                    "porques": porques,
                    "itens_6m": itens_6m,
                    "categorias_6m": CATEGORIAS_6M,
                    "classificacoes_6m": CLASSIFICACOES_6M,
                    "causa_raiz": causa_raiz,
                    "causas_raiz": causas_raiz,
                    "acoes": acoes,
                    "verificacoes": verificacoes,
                    "evidencias": evidencias,
                    "historico": historico,
                },
                logo_path=os.path.join(
                    current_app.static_folder,
                    "imagens",
                    "logo_trackplan.png",
                ),
            )
            nome_arquivo = (
                f"{investigacao['numero'].replace('/', '-')}.pdf"
            )
            return send_file(
                pdf,
                mimetype="application/pdf",
                as_attachment=True,
                download_name=nome_arquivo,
            )
        except ImportError:
            current_app.logger.exception(
                "Dependência de PDF indisponível ao gerar ACR %s",
                investigacao_id,
            )
            flash("O gerador de PDF não está disponível no servidor.", "danger")
            return redirect(
                url_for(
                    "main.detalhar_investigacao_acr",
                    investigacao_id=investigacao_id,
                )
            )
        except Exception:
            current_app.logger.exception(
                "Erro ao gerar relatório PDF da ACR %s",
                investigacao_id,
            )
            flash("Não foi possível gerar o relatório PDF.", "danger")
            return redirect(
                url_for(
                    "main.detalhar_investigacao_acr",
                    investigacao_id=investigacao_id,
                )
            )
        finally:
            cursor.close()
            conn.close()

    @blueprint.route(
        "/acr/<int:investigacao_id>/anexos",
        methods=["POST"],
    )
    @login_required
    @module_required("acesso_acr")
    def enviar_anexo_acr(investigacao_id):
        etapa_codigo = (request.form.get("etapa") or "").strip()
        descricao = (request.form.get("descricao") or "").strip()
        arquivo = request.files.get("arquivo")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        nome_armazenado = None
        diretorio = _diretorio_evidencias_acr()
        try:
            investigacao = _buscar_investigacao_acessivel(
                cursor,
                investigacao_id,
            )
            if not investigacao:
                flash("Investigação não encontrada ou fora do seu escopo.", "danger")
                return redirect(url_for("main.investigacoes_acr"))
            if investigacao["status"] in ("Concluída", "Cancelada"):
                raise ValueError(
                    "Reabra a ACR antes de incluir novos anexos."
                )
            if etapa_codigo not in ETAPAS_EVIDENCIA_ACR:
                raise ValueError("Selecione uma etapa válida para o anexo.")
            if len(descricao) > 500:
                raise ValueError("A descrição do anexo deve ter até 500 caracteres.")
            if not arquivo or not getattr(arquivo, "filename", ""):
                raise ValueError("Selecione um arquivo para anexar.")

            tamanho = _tamanho_arquivo(arquivo)
            if tamanho <= 0:
                raise ValueError("O arquivo selecionado está vazio.")
            if tamanho > TAMANHO_MAXIMO_EVIDENCIA_ACR:
                raise ValueError("O arquivo deve ter no máximo 10 MB.")

            nome_original = os.path.basename(
                arquivo.filename.replace("\\", "/")
            )[:255]
            mime_type = (arquivo.mimetype or "application/octet-stream")[:120]
            nome_armazenado = UploadService.salvar(
                arquivo,
                EXTENSOES_EVIDENCIA_ACAO,
                prefixo=f"acr_{investigacao_id}_{etapa_codigo}",
                diretorio=diretorio,
            )
            caminho = os.path.join(
                UploadService.resolver_diretorio(diretorio),
                nome_armazenado,
            )
            extensao = os.path.splitext(nome_armazenado)[1].lstrip(".")
            hash_sha256 = _hash_sha256_arquivo(caminho)

            cursor.execute(
                """
                INSERT INTO acr_evidencias (
                    investigacao_id, etapa, entidade_tipo,
                    nome_original, nome_armazenado, extensao,
                    mime_type, tamanho_bytes, hash_sha256,
                    descricao, enviado_por
                ) VALUES (%s, %s, 'etapa', %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    investigacao_id,
                    etapa_codigo,
                    nome_original,
                    nome_armazenado,
                    extensao,
                    mime_type,
                    tamanho,
                    hash_sha256,
                    descricao or None,
                    session.get("usuario_id"),
                ),
            )
            evidencia_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO acr_historico (
                    investigacao_id, usuario_id, evento, etapa,
                    entidade_tipo, entidade_id, valor_novo_json
                ) VALUES (
                    %s, %s, 'Anexo incluído', %s,
                    'evidencia', %s,
                    JSON_OBJECT('nome', %s, 'descricao', %s)
                )
                """,
                (
                    investigacao_id,
                    session.get("usuario_id"),
                    etapa_codigo,
                    evidencia_id,
                    nome_original,
                    descricao,
                ),
            )
            conn.commit()
            flash("Anexo incluído com sucesso.", "success")
        except (ValueError, UploadValidationError) as erro:
            conn.rollback()
            if nome_armazenado:
                UploadService.excluir(nome_armazenado, diretorio=diretorio)
            flash(str(erro), "warning")
        except Exception:
            conn.rollback()
            if nome_armazenado:
                UploadService.excluir(nome_armazenado, diretorio=diretorio)
            current_app.logger.exception(
                "Erro ao incluir anexo na ACR %s",
                investigacao_id,
            )
            flash("Não foi possível incluir o anexo.", "danger")
        finally:
            cursor.close()
            conn.close()
        return redirect(
            url_for(
                "main.detalhar_investigacao_acr",
                investigacao_id=investigacao_id,
                anexos_etapa=etapa_codigo,
            )
        )

    @blueprint.route(
        "/acr/<int:investigacao_id>/anexos/<int:evidencia_id>/download"
    )
    @login_required
    @module_required("acesso_acr")
    def baixar_anexo_acr(investigacao_id, evidencia_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            investigacao = _buscar_investigacao_acessivel(
                cursor,
                investigacao_id,
            )
            if not investigacao:
                flash("Investigação não encontrada ou fora do seu escopo.", "danger")
                return redirect(url_for("main.investigacoes_acr"))
            cursor.execute(
                """
                SELECT nome_original, nome_armazenado
                FROM acr_evidencias
                WHERE id = %s AND investigacao_id = %s
                  AND excluido_em IS NULL
                """,
                (evidencia_id, investigacao_id),
            )
            evidencia = cursor.fetchone()
            if not evidencia:
                flash("Anexo não encontrado.", "warning")
                return redirect(
                    url_for(
                        "main.detalhar_investigacao_acr",
                        investigacao_id=investigacao_id,
                    )
                )
            return send_from_directory(
                UploadService.resolver_diretorio(_diretorio_evidencias_acr()),
                evidencia["nome_armazenado"],
                as_attachment=True,
                download_name=evidencia["nome_original"],
            )
        finally:
            cursor.close()
            conn.close()

    @blueprint.route(
        "/acr/<int:investigacao_id>/anexos/<int:evidencia_id>/excluir",
        methods=["POST"],
    )
    @login_required
    @module_required("acesso_acr")
    def excluir_anexo_acr(investigacao_id, evidencia_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        nome_armazenado = None
        etapa_codigo = ""
        try:
            investigacao = _buscar_investigacao_acessivel(
                cursor,
                investigacao_id,
            )
            if not investigacao:
                flash("Investigação não encontrada ou fora do seu escopo.", "danger")
                return redirect(url_for("main.investigacoes_acr"))
            if investigacao["status"] in ("Concluída", "Cancelada"):
                raise ValueError("Reabra a ACR antes de excluir anexos.")
            cursor.execute(
                """
                SELECT id, etapa, nome_original, nome_armazenado
                FROM acr_evidencias
                WHERE id = %s AND investigacao_id = %s
                  AND excluido_em IS NULL
                FOR UPDATE
                """,
                (evidencia_id, investigacao_id),
            )
            evidencia = cursor.fetchone()
            if not evidencia:
                raise ValueError("Anexo não encontrado.")
            nome_armazenado = evidencia["nome_armazenado"]
            etapa_codigo = evidencia["etapa"]
            cursor.execute(
                """
                UPDATE acr_evidencias
                SET excluido_em = NOW(), excluido_por = %s
                WHERE id = %s
                """,
                (session.get("usuario_id"), evidencia_id),
            )
            cursor.execute(
                """
                INSERT INTO acr_historico (
                    investigacao_id, usuario_id, evento, etapa,
                    entidade_tipo, entidade_id, valor_novo_json
                ) VALUES (
                    %s, %s, 'Anexo excluído', %s,
                    'evidencia', %s, JSON_OBJECT('nome', %s)
                )
                """,
                (
                    investigacao_id,
                    session.get("usuario_id"),
                    evidencia["etapa"],
                    evidencia_id,
                    evidencia["nome_original"],
                ),
            )
            conn.commit()
            UploadService.excluir(
                nome_armazenado,
                diretorio=_diretorio_evidencias_acr(),
            )
            flash("Anexo excluído com sucesso.", "success")
        except ValueError as erro:
            conn.rollback()
            flash(str(erro), "warning")
        except Exception:
            conn.rollback()
            current_app.logger.exception(
                "Erro ao excluir anexo %s da ACR %s",
                evidencia_id,
                investigacao_id,
            )
            flash("Não foi possível excluir o anexo.", "danger")
        finally:
            cursor.close()
            conn.close()
        return redirect(
            url_for(
                "main.detalhar_investigacao_acr",
                investigacao_id=investigacao_id,
                anexos_etapa=etapa_codigo,
            )
        )

    @blueprint.route(
        "/acr/<int:investigacao_id>/5-porques",
        methods=["POST"],
    )
    @login_required
    @module_required("acesso_acr")
    def salvar_5_porques_acr(investigacao_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            investigacao = _buscar_investigacao_acessivel(
                cursor,
                investigacao_id,
            )
            if not investigacao:
                flash("Investigação não encontrada ou fora do seu escopo.", "danger")
                return redirect(url_for("main.investigacoes_acr"))
            if investigacao["status"] in ("Concluída", "Cancelada"):
                flash(
                    "Esta investigação não permite alterações no estado atual.",
                    "warning",
                )
                return redirect(
                    url_for(
                        "main.detalhar_investigacao_acr",
                        investigacao_id=investigacao_id,
                    )
                )
            if investigacao["metodologia_codigo"] != "5_porques":
                flash("A metodologia desta investigação não é 5 Porquês.", "danger")
                return redirect(
                    url_for(
                        "main.detalhar_investigacao_acr",
                        investigacao_id=investigacao_id,
                    )
                )

            perguntas = [
                (request.form.get(f"pergunta_{ordem}") or "").strip()
                for ordem in range(1, 6)
            ]
            respostas = [
                (request.form.get(f"resposta_{ordem}") or "").strip()
                for ordem in range(1, 6)
            ]
            acao_formulario = (request.form.get("acao") or "salvar").strip()
            causa_raiz_ordem = request.form.get("causa_raiz_ordem", type=int)

            if acao_formulario not in ("salvar", "concluir"):
                raise ValueError("Ação inválida para a etapa dos 5 Porquês.")
            if not any(perguntas) and not any(respostas):
                raise ValueError("Registre ao menos a primeira pergunta e resposta.")
            if any(len(pergunta) > 500 for pergunta in perguntas):
                raise ValueError(
                    "Cada pergunta deve possuir no máximo 500 caracteres."
                )
            if any(len(resposta) > 4000 for resposta in respostas):
                raise ValueError(
                    "Cada resposta deve possuir no máximo 4.000 caracteres."
                )
            encontrou_vazio = False
            for pergunta, resposta in zip(perguntas, respostas):
                if bool(pergunta) != bool(resposta):
                    raise ValueError(
                        "Cada nível preenchido precisa ter pergunta e resposta."
                    )
                if not pergunta:
                    encontrou_vazio = True
                elif encontrou_vazio:
                    raise ValueError(
                        "Preencha os Porquês em sequência, sem deixar lacunas."
                    )

            ultima_resposta = max(
                indice
                for indice, resposta in enumerate(respostas, start=1)
                if resposta
            )
            concluir_etapa = acao_formulario == "concluir"
            if concluir_etapa:
                if causa_raiz_ordem not in range(1, ultima_resposta + 1):
                    raise ValueError(
                        "Selecione qual resposta representa a causa raiz."
                    )

            for ordem, (pergunta, resposta) in enumerate(
                zip(perguntas, respostas),
                start=1,
            ):
                if not pergunta:
                    cursor.execute(
                        """
                        DELETE FROM acr_5_porques
                        WHERE investigacao_id = %s AND ordem = %s
                        """,
                        (investigacao_id, ordem),
                    )
                    continue
                cursor.execute(
                    """
                    INSERT INTO acr_5_porques (
                        investigacao_id, ordem, pergunta, resposta,
                        causa_raiz, respondido_por
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        pergunta = VALUES(pergunta),
                        resposta = VALUES(resposta),
                        causa_raiz = VALUES(causa_raiz),
                        respondido_por = VALUES(respondido_por)
                    """,
                    (
                        investigacao_id,
                        ordem,
                        pergunta,
                        resposta,
                        int(concluir_etapa and ordem == causa_raiz_ordem),
                        session.get("usuario_id"),
                    ),
                )

            status_etapa = "Concluída" if concluir_etapa else "Em andamento"
            cursor.execute(
                """
                INSERT INTO acr_etapas (
                    investigacao_id, codigo, status, iniciado_em,
                    concluido_em, atualizado_por
                )
                VALUES (
                    %s, '5_porques', %s, NOW(),
                    CASE WHEN %s = 'Concluída' THEN NOW() ELSE NULL END,
                    %s
                )
                ON DUPLICATE KEY UPDATE
                    status = VALUES(status),
                    iniciado_em = COALESCE(iniciado_em, NOW()),
                    concluido_em = CASE
                        WHEN VALUES(status) = 'Concluída' THEN NOW()
                        ELSE NULL
                    END,
                    atualizado_por = VALUES(atualizado_por)
                """,
                (
                    investigacao_id,
                    status_etapa,
                    status_etapa,
                    session.get("usuario_id"),
                ),
            )
            if investigacao["status"] == "Rascunho":
                cursor.execute(
                    """
                    UPDATE acr_investigacoes
                    SET status = 'Em Investigação'
                    WHERE id = %s
                    """,
                    (investigacao_id,),
                )

            if concluir_etapa:
                descricao_causa = respostas[causa_raiz_ordem - 1]
                cursor.execute(
                    """
                    SELECT id
                    FROM acr_causas
                    WHERE investigacao_id = %s
                      AND confirmada = 1
                    ORDER BY id
                    LIMIT 1
                    """,
                    (investigacao_id,),
                )
                causa_existente = cursor.fetchone()
                if causa_existente:
                    cursor.execute(
                        """
                        UPDATE acr_causas
                        SET descricao = %s,
                            metodologia_id = %s,
                            identificada_por = %s,
                            identificada_em = NOW()
                        WHERE id = %s
                        """,
                        (
                            descricao_causa,
                            investigacao["metodologia_id"],
                            session.get("usuario_id"),
                            causa_existente["id"],
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO acr_causas (
                            investigacao_id, metodologia_id, descricao,
                            confirmada, identificada_por
                        )
                        VALUES (%s, %s, %s, 1, %s)
                        """,
                        (
                            investigacao_id,
                            investigacao["metodologia_id"],
                            descricao_causa,
                            session.get("usuario_id"),
                        ),
                    )
            else:
                cursor.execute(
                    """
                    UPDATE acr_causas
                    SET confirmada = 0,
                        invalidada_em = NOW(),
                        motivo_invalidacao = %s
                    WHERE investigacao_id = %s
                      AND confirmada = 1
                    """,
                    (
                        "Etapa dos 5 Porquês reaberta para revisão.",
                        investigacao_id,
                    ),
                )

            cursor.execute(
                """
                INSERT INTO acr_historico (
                    investigacao_id, usuario_id, evento, etapa
                )
                VALUES (%s, %s, %s, '5_porques')
                """,
                (
                    investigacao_id,
                    session.get("usuario_id"),
                    (
                        "Etapa 5 Porquês concluída"
                        if concluir_etapa
                        else "Rascunho dos 5 Porquês salvo"
                    ),
                ),
            )
            conn.commit()
            flash(
                (
                    "Causa raiz confirmada com sucesso."
                    if concluir_etapa
                    else "Investigação salva como rascunho."
                ),
                "success",
            )
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "danger")
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

        return redirect(
            url_for(
                "main.detalhar_investigacao_acr",
                investigacao_id=investigacao_id,
            )
        )

    @blueprint.route(
        "/acr/<int:investigacao_id>/6m",
        methods=["POST"],
    )
    @login_required
    @module_required("acesso_acr")
    def salvar_6m_acr(investigacao_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            investigacao = _buscar_investigacao_acessivel(
                cursor,
                investigacao_id,
            )
            if not investigacao:
                flash("Investigação não encontrada ou fora do seu escopo.", "danger")
                return redirect(url_for("main.investigacoes_acr"))
            if investigacao["status"] in ("Concluída", "Cancelada"):
                raise ValueError(
                    "Esta investigação não permite alterações no estado atual."
                )
            if investigacao["metodologia_codigo"] != "ishikawa":
                raise ValueError("A metodologia desta investigação não é 6M.")
            cursor.execute(
                """
                SELECT COUNT(*) AS total
                FROM acr_acoes
                WHERE investigacao_id = %s
                """,
                (investigacao_id,),
            )
            if cursor.fetchone()["total"]:
                raise ValueError(
                    "O diagrama 6M não pode ser alterado após a criação do plano de ação."
                )

            acao_formulario = (request.form.get("acao") or "salvar").strip()
            if acao_formulario not in ("salvar", "concluir"):
                raise ValueError("Ação inválida para a etapa 6M.")
            concluir_etapa = acao_formulario == "concluir"

            itens_formulario = []
            for categoria in CATEGORIAS_6M:
                texto = request.form.get(f"itens_{categoria}") or ""
                linhas = [linha.strip() for linha in texto.splitlines() if linha.strip()]
                if len(linhas) > 20:
                    raise ValueError(
                        "Cada categoria do 6M aceita no máximo 20 hipóteses."
                    )
                if any(len(linha) > 1000 for linha in linhas):
                    raise ValueError(
                        "Cada hipótese do 6M deve possuir no máximo 1.000 caracteres."
                    )
                itens_formulario.extend(
                    (categoria, ordem, descricao)
                    for ordem, descricao in enumerate(linhas, start=1)
                )
            if not itens_formulario:
                raise ValueError("Registre ao menos uma hipótese no diagrama 6M.")

            cursor.execute(
                """
                SELECT id, categoria, descricao, classificacao,
                       justificativa, validacao
                FROM acr_6m_itens
                WHERE investigacao_id = %s
                """,
                (investigacao_id,),
            )
            analises_por_chave = {}
            for item in cursor.fetchall():
                classificacao = (
                    request.form.get(f"classificacao_6m_{item['id']}")
                    or item["classificacao"]
                    or "potencial"
                ).strip()
                justificativa = (
                    request.form.get(f"justificativa_6m_{item['id']}")
                    if f"justificativa_6m_{item['id']}" in request.form
                    else item["justificativa"]
                ) or ""
                validacao = (
                    request.form.get(f"validacao_6m_{item['id']}")
                    if f"validacao_6m_{item['id']}" in request.form
                    else item["validacao"]
                ) or ""
                justificativa = justificativa.strip()
                validacao = validacao.strip()
                if classificacao not in CLASSIFICACOES_6M:
                    raise ValueError("Classificação inválida em uma hipótese do 6M.")
                if len(justificativa) > 4000 or len(validacao) > 4000:
                    raise ValueError(
                        "Justificativa e validação aceitam até 4.000 caracteres."
                    )
                analises_por_chave[(item["categoria"], item["descricao"])] = {
                    "classificacao": classificacao,
                    "justificativa": justificativa,
                    "validacao": validacao,
                }

            analises_finais = []
            for categoria, ordem, descricao in itens_formulario:
                analise = analises_por_chave.get(
                    (categoria, descricao),
                    {
                        "classificacao": "potencial",
                        "justificativa": "",
                        "validacao": "",
                    },
                )
                analises_finais.append((categoria, ordem, descricao, analise))

            if concluir_etapa:
                if any(
                    analise["classificacao"] == "potencial"
                    for _, _, _, analise in analises_finais
                ):
                    raise ValueError(
                        "Classifique todas as hipóteses antes de concluir a análise."
                    )
                if any(
                    not analise["justificativa"] or not analise["validacao"]
                    for _, _, _, analise in analises_finais
                ):
                    raise ValueError(
                        "Informe a justificativa e a validação de todas as hipóteses."
                    )
                if not any(
                    analise["classificacao"] in ("basica", "fundamental")
                    for _, _, _, analise in analises_finais
                ):
                    raise ValueError(
                        "A análise deve possuir ao menos uma causa básica ou fundamental."
                    )

            cursor.execute(
                "DELETE FROM acr_6m_itens WHERE investigacao_id = %s",
                (investigacao_id,),
            )
            for categoria, ordem, descricao, analise in analises_finais:
                cursor.execute(
                    """
                    INSERT INTO acr_6m_itens (
                        investigacao_id, categoria, descricao,
                        causa_raiz, classificacao, justificativa,
                        validacao, ordem, registrado_por
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        investigacao_id,
                        categoria,
                        descricao,
                        int(
                            concluir_etapa
                            and analise["classificacao"] in ("basica", "fundamental")
                        ),
                        analise["classificacao"],
                        analise["justificativa"] or None,
                        analise["validacao"] or None,
                        ordem,
                        session.get("usuario_id"),
                    ),
                )

            cursor.execute(
                """
                UPDATE acr_causas
                SET confirmada = 0, invalidada_em = NOW(),
                    motivo_invalidacao = %s
                WHERE investigacao_id = %s AND confirmada = 1
                """,
                ("Diagrama 6M revisado.", investigacao_id),
            )
            if concluir_etapa:
                for categoria, _, descricao, analise in analises_finais:
                    if analise["classificacao"] not in (
                        "contribuinte",
                        "basica",
                        "fundamental",
                    ):
                        continue
                    cursor.execute(
                        """
                        INSERT INTO acr_causas (
                            investigacao_id, metodologia_id, descricao,
                            confirmada, identificada_por
                        ) VALUES (%s, %s, %s, 1, %s)
                        """,
                        (
                            investigacao_id,
                            investigacao["metodologia_id"],
                            (
                                f"{CLASSIFICACOES_6M[analise['classificacao']]}"
                                f" | {CATEGORIAS_6M[categoria]}: {descricao}"
                            ),
                            session.get("usuario_id"),
                        ),
                    )

            status_etapa = "Concluída" if concluir_etapa else "Em andamento"
            cursor.execute(
                """
                INSERT INTO acr_etapas (
                    investigacao_id, codigo, status, iniciado_em,
                    concluido_em, atualizado_por
                ) VALUES (
                    %s, '6m', %s, NOW(),
                    CASE WHEN %s = 'Concluída' THEN NOW() ELSE NULL END,
                    %s
                )
                ON DUPLICATE KEY UPDATE
                    status = VALUES(status),
                    iniciado_em = COALESCE(iniciado_em, NOW()),
                    concluido_em = CASE
                        WHEN VALUES(status) = 'Concluída' THEN NOW()
                        ELSE NULL
                    END,
                    atualizado_por = VALUES(atualizado_por)
                """,
                (
                    investigacao_id,
                    status_etapa,
                    status_etapa,
                    session.get("usuario_id"),
                ),
            )
            if investigacao["status"] == "Rascunho":
                cursor.execute(
                    """
                    UPDATE acr_investigacoes
                    SET status = 'Em Investigação'
                    WHERE id = %s
                    """,
                    (investigacao_id,),
                )
            cursor.execute(
                """
                INSERT INTO acr_historico (
                    investigacao_id, usuario_id, evento, etapa
                ) VALUES (%s, %s, %s, '6m')
                """,
                (
                    investigacao_id,
                    session.get("usuario_id"),
                    (
                        "Diagrama 6M concluído"
                        if concluir_etapa
                        else "Rascunho do diagrama 6M salvo"
                    ),
                ),
            )
            conn.commit()
            flash(
                "Análise 6M concluída com sucesso."
                if concluir_etapa
                else "Diagrama 6M salvo como rascunho.",
                "success",
            )
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "danger")
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
        return redirect(
            url_for(
                "main.detalhar_investigacao_acr",
                investigacao_id=investigacao_id,
            )
        )

    @blueprint.route(
        "/acr/<int:investigacao_id>/acoes",
        methods=["POST"],
    )
    @login_required
    @module_required("acesso_acr")
    def criar_acao_acr(investigacao_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            investigacao = _buscar_investigacao_acessivel(
                cursor,
                investigacao_id,
            )
            if not investigacao:
                flash("Investigação não encontrada ou fora do seu escopo.", "danger")
                return redirect(url_for("main.investigacoes_acr"))
            if investigacao["status"] in ("Concluída", "Cancelada"):
                raise ValueError(
                    "Esta investigação não permite novas ações no estado atual."
                )

            cursor.execute(
                """
                SELECT id, descricao
                FROM acr_causas
                WHERE investigacao_id = %s AND confirmada = 1
                ORDER BY id
                """,
                (investigacao_id,),
            )
            causas_raiz = cursor.fetchall()
            if not causas_raiz:
                raise ValueError(
                    "Confirme a causa raiz antes de cadastrar o plano de ação."
                )
            causa_raiz_id = request.form.get("causa_raiz_id", type=int)
            if len(causas_raiz) == 1:
                causa_raiz_id = causas_raiz[0]["id"]
            elif causa_raiz_id not in {
                causa["id"] for causa in causas_raiz
            }:
                raise ValueError(
                    "Selecione a causa raiz que será tratada pela ação."
                )

            responsavel_id = request.form.get("responsavel_id", type=int)
            descricao = (request.form.get("descricao") or "").strip()
            prazo_texto = (request.form.get("prazo") or "").strip()

            if not all((responsavel_id, descricao, prazo_texto)):
                raise ValueError("Preencha todos os campos da ação.")
            if len(descricao) > 4000:
                raise ValueError(
                    "A descrição da ação deve ter no máximo 4.000 caracteres."
                )
            try:
                prazo = date.fromisoformat(prazo_texto)
            except ValueError as exc:
                raise ValueError("Informe um prazo válido para a ação.") from exc
            if prazo < date.today():
                raise ValueError("O prazo da ação não pode estar no passado.")

            cursor.execute(
                """
                SELECT id
                FROM usuarios
                WHERE id = %s AND ativo = 1 AND centro_custos_id = %s
                """,
                (responsavel_id, investigacao["centro_custos_id"]),
            )
            if not cursor.fetchone():
                raise ValueError("Responsável fora do centro de custos da ACR.")

            origem_id = _garantir_origem_acao_acr(cursor, investigacao)

            cursor.execute(
                """
                INSERT INTO acoes (
                    origem_id, responsavel_id, centro_custos_id,
                    descricao, prazo, status, criado_por
                )
                VALUES (%s, %s, %s, %s, %s, 'Não iniciada', %s)
                """,
                (
                    origem_id,
                    responsavel_id,
                    investigacao["centro_custos_id"],
                    descricao,
                    prazo,
                    session.get("usuario_id"),
                ),
            )
            acao_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO acr_acoes (
                    investigacao_id, causa_raiz_id, acao_id, criado_por
                )
                VALUES (%s, %s, %s, %s)
                """,
                (
                    investigacao_id,
                    causa_raiz_id,
                    acao_id,
                    session.get("usuario_id"),
                ),
            )
            cursor.execute(
                """
                INSERT INTO acr_etapas (
                    investigacao_id, codigo, status, iniciado_em,
                    atualizado_por
                )
                VALUES (%s, 'acoes', 'Em andamento', NOW(), %s)
                ON DUPLICATE KEY UPDATE
                    status = 'Em andamento',
                    iniciado_em = COALESCE(iniciado_em, NOW()),
                    atualizado_por = VALUES(atualizado_por)
                """,
                (investigacao_id, session.get("usuario_id")),
            )
            cursor.execute(
                """
                INSERT INTO acr_historico (
                    investigacao_id, usuario_id, evento,
                    etapa, entidade_tipo, entidade_id
                )
                VALUES (%s, %s, 'Ação criada e vinculada',
                        'acoes', 'acao', %s)
                """,
                (investigacao_id, session.get("usuario_id"), acao_id),
            )
            conn.commit()
            flash("Ação criada e vinculada à ACR com sucesso.", "success")
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "danger")
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

        return redirect(
            url_for(
                "main.detalhar_investigacao_acr",
                investigacao_id=investigacao_id,
            )
        )

    @blueprint.route(
        "/acr/<int:investigacao_id>/acoes/<int:acao_id>/editar",
        methods=["POST"],
    )
    @login_required
    @module_required("acesso_acr")
    def editar_acao_acr(investigacao_id, acao_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        novo_arquivo = None
        arquivo_anterior = None
        try:
            investigacao = _buscar_investigacao_acessivel(
                cursor,
                investigacao_id,
            )
            if not investigacao:
                raise ValueError(
                    "Investigação não encontrada ou fora do seu escopo."
                )
            if investigacao["status"] in ("Concluída", "Cancelada"):
                raise ValueError(
                    "Esta investigação não permite editar ações no estado atual."
                )

            cursor.execute(
                """
                SELECT a.id, a.arquivo_evidencia
                FROM acr_acoes aa
                JOIN acoes a ON a.id = aa.acao_id
                WHERE aa.investigacao_id = %s
                  AND aa.acao_id = %s
                  AND a.ativo = 1
                """,
                (investigacao_id, acao_id),
            )
            acao_atual = cursor.fetchone()
            if not acao_atual:
                raise ValueError("Ação não encontrada nesta ACR.")
            arquivo_anterior = acao_atual.get("arquivo_evidencia")

            responsavel_id = request.form.get("responsavel_id", type=int)
            descricao = (request.form.get("descricao") or "").strip()
            prazo_texto = (request.form.get("prazo") or "").strip()
            status = (request.form.get("status") or "").strip()
            observacoes = (request.form.get("observacoes") or "").strip()
            data_conclusao_texto = (
                request.form.get("data_conclusao") or ""
            ).strip()
            if not all((responsavel_id, descricao, prazo_texto, status)):
                raise ValueError("Preencha todos os campos da ação.")
            if len(descricao) > 4000:
                raise ValueError(
                    "A descrição da ação deve ter no máximo 4.000 caracteres."
                )
            if status not in STATUS_ACAO_ACR:
                raise ValueError("Status inválido para a ação.")
            try:
                prazo = date.fromisoformat(prazo_texto)
            except ValueError as exc:
                raise ValueError("Informe um prazo válido para a ação.") from exc

            data_conclusao = None
            if data_conclusao_texto:
                try:
                    data_conclusao = date.fromisoformat(data_conclusao_texto)
                except ValueError as exc:
                    raise ValueError("Informe uma data de conclusão válida.") from exc
                if data_conclusao > date.today():
                    raise ValueError(
                        "A data de conclusão não pode ser superior à data de hoje."
                    )
                status = "Concluída"
            elif status == "Concluída":
                raise ValueError(
                    "Para concluir a ação, preencha a data de conclusão."
                )
            if status == "Cancelada" and not observacoes:
                raise ValueError(
                    "Ao cancelar a ação, o campo Observações é obrigatório."
                )
            if len(observacoes) > 4000:
                raise ValueError(
                    "As observações devem ter no máximo 4.000 caracteres."
                )

            cursor.execute(
                """
                SELECT id
                FROM usuarios
                WHERE id = %s AND ativo = 1 AND centro_custos_id = %s
                """,
                (responsavel_id, investigacao["centro_custos_id"]),
            )
            if not cursor.fetchone():
                raise ValueError("Responsável fora do centro de custos da ACR.")

            arquivo = request.files.get("arquivo_evidencia")
            arquivo_evidencia = arquivo_anterior
            if arquivo and arquivo.filename:
                try:
                    novo_arquivo = UploadService.salvar(
                        arquivo,
                        EXTENSOES_EVIDENCIA_ACAO,
                        prefixo=f"evidencia_acao_{acao_id}",
                        diretorio=os.path.join("static", "evidencias"),
                    )
                except UploadValidationError as exc:
                    raise ValueError(str(exc)) from exc
                arquivo_evidencia = novo_arquivo

            cursor.execute(
                """
                UPDATE acoes
                SET responsavel_id = %s,
                    descricao = %s,
                    prazo = %s,
                    status = %s,
                    observacoes = %s,
                    data_conclusao = %s,
                    arquivo_evidencia = %s
                WHERE id = %s
                """,
                (
                    responsavel_id,
                    descricao,
                    prazo,
                    status,
                    observacoes or None,
                    data_conclusao,
                    arquivo_evidencia,
                    acao_id,
                ),
            )
            cursor.execute(
                """
                INSERT INTO acr_historico (
                    investigacao_id, usuario_id, evento,
                    etapa, entidade_tipo, entidade_id
                )
                VALUES (%s, %s, 'Ação da ACR atualizada',
                        'acoes', 'acao', %s)
                """,
                (investigacao_id, session.get("usuario_id"), acao_id),
            )
            conn.commit()
            if novo_arquivo and arquivo_anterior:
                UploadService.excluir(
                    arquivo_anterior,
                    diretorio=os.path.join("static", "evidencias"),
                )
            flash("Ação atualizada com sucesso.", "success")
        except ValueError as exc:
            conn.rollback()
            if novo_arquivo:
                UploadService.excluir(
                    novo_arquivo,
                    diretorio=os.path.join("static", "evidencias"),
                )
            flash(str(exc), "danger")
        except Exception:
            conn.rollback()
            if novo_arquivo:
                UploadService.excluir(
                    novo_arquivo,
                    diretorio=os.path.join("static", "evidencias"),
                )
            raise
        finally:
            cursor.close()
            conn.close()

        return redirect(
            url_for(
                "main.detalhar_investigacao_acr",
                investigacao_id=investigacao_id,
            )
        )

    @blueprint.route(
        "/acr/<int:investigacao_id>/eficacia/agendar",
        methods=["POST"],
    )
    @login_required
    @module_required("acesso_acr")
    def agendar_eficacia_acr(investigacao_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            investigacao = _buscar_investigacao_acessivel(
                cursor,
                investigacao_id,
            )
            if not investigacao:
                raise ValueError(
                    "Investigação não encontrada ou fora do seu escopo."
                )
            if session.get("usuario_id") != investigacao["criador_id"]:
                raise ValueError(
                    "Somente o criador da ACR pode programar sua eficácia."
                )
            if investigacao["status"] in ("Concluída", "Cancelada"):
                raise ValueError(
                    "Esta investigação não permite uma nova verificação."
                )

            cursor.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(a.status <> 'Concluída') AS pendentes
                FROM acr_acoes aa
                JOIN acoes a ON a.id = aa.acao_id
                WHERE aa.investigacao_id = %s AND a.ativo = 1
                """,
                (investigacao_id,),
            )
            resumo = cursor.fetchone()
            if not resumo["total"]:
                raise ValueError(
                    "Cadastre e conclua pelo menos uma ação antes da eficácia."
                )
            if resumo["pendentes"]:
                raise ValueError(
                    "Todas as ações precisam estar concluídas antes da eficácia."
                )

            cursor.execute(
                """
                SELECT id
                FROM acr_verificacoes_eficacia
                WHERE investigacao_id = %s AND resultado IS NULL
                LIMIT 1
                """,
                (investigacao_id,),
            )
            if cursor.fetchone():
                raise ValueError("Já existe uma verificação de eficácia pendente.")

            data_texto = (request.form.get("data_prevista") or "").strip()
            criterio = (request.form.get("criterio") or "").strip()
            if not data_texto or not criterio:
                raise ValueError(
                    "Informe a data prevista e o critério de eficácia."
                )
            if len(criterio) > 4000:
                raise ValueError(
                    "O critério de eficácia deve ter no máximo 4.000 caracteres."
                )
            try:
                data_prevista = date.fromisoformat(data_texto)
            except ValueError as exc:
                raise ValueError(
                    "Informe uma data válida para a eficácia."
                ) from exc
            if data_prevista < date.today():
                raise ValueError(
                    "A verificação não pode ser programada para uma data passada."
                )

            cursor.execute(
                """
                SELECT COALESCE(MAX(ciclo), 0) + 1 AS proximo_ciclo
                FROM acr_verificacoes_eficacia
                WHERE investigacao_id = %s
                """,
                (investigacao_id,),
            )
            ciclo = cursor.fetchone()["proximo_ciclo"]
            cursor.execute(
                """
                INSERT INTO acr_verificacoes_eficacia (
                    investigacao_id, ciclo, data_prevista,
                    criterio, responsavel_id
                )
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    investigacao_id,
                    ciclo,
                    data_prevista,
                    criterio,
                    session.get("usuario_id"),
                ),
            )
            verificacao_id = cursor.lastrowid
            cursor.execute(
                """
                UPDATE acr_investigacoes
                SET data_prevista_eficacia = %s,
                    criterio_eficacia = %s
                WHERE id = %s
                """,
                (data_prevista, criterio, investigacao_id),
            )
            cursor.execute(
                """
                INSERT INTO acr_etapas (
                    investigacao_id, codigo, status,
                    iniciado_em, atualizado_por
                )
                VALUES (%s, 'acoes', 'Concluída', NOW(), %s)
                ON DUPLICATE KEY UPDATE
                    status = 'Concluída',
                    concluido_em = NOW(),
                    atualizado_por = VALUES(atualizado_por)
                """,
                (investigacao_id, session.get("usuario_id")),
            )
            cursor.execute(
                """
                INSERT INTO acr_etapas (
                    investigacao_id, codigo, status,
                    iniciado_em, atualizado_por
                )
                VALUES (%s, 'eficacia', 'Em andamento', NOW(), %s)
                ON DUPLICATE KEY UPDATE
                    status = 'Em andamento',
                    iniciado_em = COALESCE(iniciado_em, NOW()),
                    concluido_em = NULL,
                    atualizado_por = VALUES(atualizado_por)
                """,
                (investigacao_id, session.get("usuario_id")),
            )
            cursor.execute(
                """
                INSERT INTO acr_historico (
                    investigacao_id, usuario_id, evento,
                    etapa, entidade_tipo, entidade_id
                )
                VALUES (%s, %s, 'Verificação de eficácia programada',
                        'eficacia', 'verificacao_eficacia', %s)
                """,
                (
                    investigacao_id,
                    session.get("usuario_id"),
                    verificacao_id,
                ),
            )
            conn.commit()
            flash("Verificação de eficácia programada com sucesso.", "success")
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "danger")
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

        return redirect(
            url_for(
                "main.detalhar_investigacao_acr",
                investigacao_id=investigacao_id,
            )
            + "#eficacia"
        )

    @blueprint.route(
        "/acr/<int:investigacao_id>/eficacia/<int:verificacao_id>/avaliar",
        methods=["POST"],
    )
    @login_required
    @module_required("acesso_acr")
    def avaliar_eficacia_acr(investigacao_id, verificacao_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            investigacao = _buscar_investigacao_acessivel(
                cursor,
                investigacao_id,
            )
            if not investigacao:
                raise ValueError(
                    "Investigação não encontrada ou fora do seu escopo."
                )
            if session.get("usuario_id") != investigacao["criador_id"]:
                raise ValueError(
                    "Somente o criador da ACR pode verificar sua eficácia."
                )
            cursor.execute(
                """
                SELECT id, data_prevista, resultado
                FROM acr_verificacoes_eficacia
                WHERE id = %s AND investigacao_id = %s
                """,
                (verificacao_id, investigacao_id),
            )
            verificacao = cursor.fetchone()
            if not verificacao or verificacao["resultado"] is not None:
                raise ValueError("Verificação de eficácia inválida ou já avaliada.")
            if date.today() < verificacao["data_prevista"]:
                raise ValueError(
                    "A eficácia somente pode ser avaliada na data prevista ou depois."
                )

            resultado = (request.form.get("resultado") or "").strip()
            justificativa = (request.form.get("justificativa") or "").strip()
            if resultado not in RESULTADOS_EFICACIA_ACR:
                raise ValueError("Selecione um resultado válido para a eficácia.")
            if not justificativa:
                raise ValueError(
                    "Registre a justificativa e as evidências observadas."
                )
            if len(justificativa) > 4000:
                raise ValueError(
                    "A justificativa deve ter no máximo 4.000 caracteres."
                )

            cursor.execute(
                """
                UPDATE acr_verificacoes_eficacia
                SET data_realizada = CURDATE(),
                    resultado = %s,
                    justificativa = %s
                WHERE id = %s
                """,
                (resultado, justificativa, verificacao_id),
            )
            eficaz = resultado == "Eficaz"
            cursor.execute(
                """
                INSERT INTO acr_etapas (
                    investigacao_id, codigo, status,
                    iniciado_em, concluido_em, atualizado_por
                )
                VALUES (%s, 'eficacia', %s, NOW(), %s, %s)
                ON DUPLICATE KEY UPDATE
                    status = VALUES(status),
                    concluido_em = VALUES(concluido_em),
                    atualizado_por = VALUES(atualizado_por)
                """,
                (
                    investigacao_id,
                    "Concluída" if eficaz else "Com pendências",
                    date.today() if eficaz else None,
                    session.get("usuario_id"),
                ),
            )
            cursor.execute(
                """
                UPDATE acr_investigacoes
                SET status = %s,
                    concluido_em = %s
                WHERE id = %s
                """,
                (
                    "Concluída" if eficaz else "Em Investigação",
                    date.today() if eficaz else None,
                    investigacao_id,
                ),
            )
            cursor.execute(
                """
                INSERT INTO acr_historico (
                    investigacao_id, usuario_id, evento,
                    etapa, entidade_tipo, entidade_id
                )
                VALUES (%s, %s, %s, 'eficacia',
                        'verificacao_eficacia', %s)
                """,
                (
                    investigacao_id,
                    session.get("usuario_id"),
                    f"Eficácia avaliada: {resultado}",
                    verificacao_id,
                ),
            )
            conn.commit()
            if eficaz:
                flash("ACR concluída após verificação eficaz.", "success")
            else:
                flash(
                    "A ACR permanece aberta. Revise o plano de ação e "
                    "programe um novo ciclo de eficácia.",
                    "warning",
                )
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "danger")
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

        return redirect(
            url_for(
                "main.detalhar_investigacao_acr",
                investigacao_id=investigacao_id,
            )
            + "#eficacia"
        )

    @blueprint.route(
        "/acr/<int:investigacao_id>/cancelar",
        methods=["POST"],
    )
    @login_required
    @module_required("acesso_acr")
    def cancelar_investigacao_acr(investigacao_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            investigacao = _buscar_investigacao_acessivel(
                cursor,
                investigacao_id,
            )
            if not investigacao:
                raise ValueError(
                    "Investigação não encontrada ou fora do seu escopo."
                )
            if investigacao["status"] == "Cancelada":
                raise ValueError("Esta ACR já está cancelada.")
            if investigacao["status"] == "Concluída":
                raise ValueError(
                    "Reabra a ACR concluída antes de solicitar seu cancelamento."
                )
            justificativa = (
                request.form.get("justificativa_cancelamento") or ""
            ).strip()
            if not justificativa:
                raise ValueError("Informe a justificativa do cancelamento.")
            if len(justificativa) > 4000:
                raise ValueError(
                    "A justificativa deve ter no máximo 4.000 caracteres."
                )

            cursor.execute(
                """
                UPDATE acr_investigacoes
                SET status = 'Cancelada',
                    justificativa_cancelamento = %s,
                    cancelado_em = NOW(),
                    concluido_em = NULL
                WHERE id = %s
                """,
                (justificativa, investigacao_id),
            )
            cursor.execute(
                """
                INSERT INTO acr_historico (
                    investigacao_id, usuario_id, evento,
                    etapa, entidade_tipo, entidade_id,
                    valor_novo_json
                )
                VALUES (%s, %s, 'ACR cancelada', 'governanca',
                        'investigacao', %s,
                        JSON_OBJECT('justificativa', %s))
                """,
                (
                    investigacao_id,
                    session.get("usuario_id"),
                    investigacao_id,
                    justificativa,
                ),
            )
            conn.commit()
            flash("ACR cancelada com sucesso.", "success")
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "danger")
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

        return redirect(
            url_for(
                "main.detalhar_investigacao_acr",
                investigacao_id=investigacao_id,
            )
        )

    @blueprint.route(
        "/acr/<int:investigacao_id>/participantes",
        methods=["POST"],
    )
    @login_required
    @module_required("acesso_acr")
    def atualizar_participantes_acr(investigacao_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            investigacao = _buscar_investigacao_acessivel(
                cursor,
                investigacao_id,
            )
            if not investigacao:
                raise ValueError(
                    "Investigação não encontrada ou fora do seu escopo."
                )
            if investigacao["status"] in ("Concluída", "Cancelada"):
                raise ValueError(
                    "Reabra a ACR antes de alterar seus participantes."
                )

            selecionados = []
            for valor in request.form.getlist("participante_ids"):
                try:
                    selecionados.append(int(valor))
                except (TypeError, ValueError) as exc:
                    raise ValueError("A lista de participantes é inválida.") from exc
            selecionados = set(selecionados)
            selecionados.discard(investigacao["criador_id"])
            selecionados.discard(investigacao["responsavel_id"])

            cursor.execute(
                """
                SELECT id, nome
                FROM usuarios
                WHERE ativo = 1
                  AND centro_custos_id = %s
                """,
                (investigacao["centro_custos_id"],),
            )
            usuarios_validos = {
                item["id"]: item["nome"] for item in cursor.fetchall()
            }
            if any(item not in usuarios_validos for item in selecionados):
                raise ValueError(
                    "Um ou mais participantes estão fora do centro de custos da ACR."
                )

            cursor.execute(
                """
                SELECT ap.usuario_id, u.nome
                FROM acr_participantes ap
                JOIN usuarios u ON u.id = ap.usuario_id
                WHERE ap.investigacao_id = %s AND ap.ativo = 1
                FOR UPDATE
                """,
                (investigacao_id,),
            )
            atuais_registros = cursor.fetchall()
            atuais = {item["usuario_id"] for item in atuais_registros}
            nomes_atuais = {
                item["usuario_id"]: item["nome"] for item in atuais_registros
            }
            adicionados = selecionados - atuais
            removidos = atuais - selecionados

            cursor.execute(
                """
                UPDATE acr_participantes
                SET ativo = 0
                WHERE investigacao_id = %s AND ativo = 1
                """,
                (investigacao_id,),
            )
            for participante_id in selecionados:
                cursor.execute(
                    """
                    INSERT INTO acr_participantes (
                        investigacao_id, usuario_id, adicionado_por, ativo
                    ) VALUES (%s, %s, %s, 1)
                    ON DUPLICATE KEY UPDATE
                        ativo = 1,
                        adicionado_por = VALUES(adicionado_por)
                    """,
                    (
                        investigacao_id,
                        participante_id,
                        session.get("usuario_id"),
                    ),
                )

            if adicionados or removidos:
                detalhes = []
                if adicionados:
                    detalhes.append(
                        "Incluídos: "
                        + ", ".join(
                            usuarios_validos[item]
                            for item in sorted(
                                adicionados,
                                key=lambda chave: usuarios_validos[chave],
                            )
                        )
                    )
                if removidos:
                    detalhes.append(
                        "Removidos: "
                        + ", ".join(
                            nomes_atuais[item]
                            for item in sorted(
                                removidos,
                                key=lambda chave: nomes_atuais[chave],
                            )
                        )
                    )
                cursor.execute(
                    """
                    INSERT INTO acr_historico (
                        investigacao_id, usuario_id, evento, etapa,
                        entidade_tipo, entidade_id, valor_novo_json
                    ) VALUES (
                        %s, %s, 'Participantes atualizados', 'identificacao',
                        'investigacao', %s,
                        JSON_OBJECT('justificativa', %s)
                    )
                    """,
                    (
                        investigacao_id,
                        session.get("usuario_id"),
                        investigacao_id,
                        "; ".join(detalhes),
                    ),
                )
            conn.commit()
            flash("Participantes atualizados com sucesso.", "success")
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "danger")
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
        return redirect(
            url_for(
                "main.detalhar_investigacao_acr",
                investigacao_id=investigacao_id,
            )
        )

    @blueprint.route(
        "/acr/<int:investigacao_id>/reabrir",
        methods=["POST"],
    )
    @login_required
    @module_required("acesso_acr")
    def reabrir_investigacao_acr(investigacao_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            investigacao = _buscar_investigacao_acessivel(
                cursor,
                investigacao_id,
            )
            if not investigacao:
                raise ValueError(
                    "Investigação não encontrada ou fora do seu escopo."
                )
            if investigacao["status"] not in ("Concluída", "Cancelada"):
                raise ValueError(
                    "Somente uma ACR concluída ou cancelada pode ser reaberta."
                )
            justificativa = (
                request.form.get("justificativa_reabertura") or ""
            ).strip()
            if not justificativa:
                raise ValueError("Informe a justificativa da reabertura.")
            if len(justificativa) > 4000:
                raise ValueError(
                    "A justificativa deve ter no máximo 4.000 caracteres."
                )

            status_anterior = investigacao["status"]
            cursor.execute(
                """
                UPDATE acr_investigacoes
                SET status = 'Em Investigação',
                    cancelado_em = NULL,
                    concluido_em = NULL
                WHERE id = %s
                """,
                (investigacao_id,),
            )
            cursor.execute(
                """
                UPDATE acr_etapas
                SET status = 'Com pendências',
                    concluido_em = NULL,
                    atualizado_por = %s
                WHERE investigacao_id = %s
                  AND codigo = 'eficacia'
                  AND status = 'Concluída'
                """,
                (session.get("usuario_id"), investigacao_id),
            )
            cursor.execute(
                """
                INSERT INTO acr_historico (
                    investigacao_id, usuario_id, evento,
                    etapa, entidade_tipo, entidade_id,
                    valor_novo_json
                )
                VALUES (%s, %s, 'ACR reaberta', 'governanca',
                        'investigacao', %s,
                        JSON_OBJECT(
                            'justificativa', %s,
                            'status_anterior', %s
                        ))
                """,
                (
                    investigacao_id,
                    session.get("usuario_id"),
                    investigacao_id,
                    justificativa,
                    status_anterior,
                ),
            )
            conn.commit()
            flash("ACR reaberta com sucesso.", "success")
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "danger")
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

        return redirect(
            url_for(
                "main.detalhar_investigacao_acr",
                investigacao_id=investigacao_id,
            )
        )

    @blueprint.route("/acr/nova", methods=["GET", "POST"])
    @login_required
    @module_required("acesso_acr")
    def nova_investigacao_acr():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            dominios = _buscar_dominios(cursor)
            centros, responsaveis, participantes = (
                _buscar_centros_e_responsaveis(cursor)
            )
            participantes_selecionados = []
            if not centros:
                flash(
                    "Seu usuário precisa estar vinculado a um centro de custos "
                    "ativo para criar uma ACR.",
                    "danger",
                )
                return redirect(url_for("main.investigacoes_acr"))

            if request.method == "GET":
                return render_template(
                    "nova_investigacao_causa_raiz.html",
                    dominios=dominios,
                    centros=centros,
                    responsaveis=responsaveis,
                    participantes=participantes,
                    participantes_selecionados=participantes_selecionados,
                    hoje=date.today().isoformat(),
                )

            origem_id = request.form.get("origem_id", type=int)
            classificacao_id = request.form.get("classificacao_id", type=int)
            gravidade_id = request.form.get("gravidade_id", type=int)
            metodologia_id = request.form.get("metodologia_id", type=int)
            centro_custos_id = session.get("centro_custos_id")
            responsavel_id = request.form.get("responsavel_id", type=int)
            data_ocorrencia = (request.form.get("data_ocorrencia") or "").strip()
            equipamento = (
                request.form.get("equipamento_processo") or ""
            ).strip()
            descricao = (
                request.form.get("descricao_ocorrencia") or ""
            ).strip()
            origem_outros = (
                request.form.get("origem_outros") or ""
            ).strip() or None
            for valor in request.form.getlist("participante_ids"):
                try:
                    participantes_selecionados.append(int(valor))
                except (TypeError, ValueError) as exc:
                    raise ValueError("A lista de participantes é inválida.") from exc
            participantes_selecionados = list(
                dict.fromkeys(participantes_selecionados)
            )

            obrigatorios = (
                origem_id,
                classificacao_id,
                gravidade_id,
                metodologia_id,
                centro_custos_id,
                responsavel_id,
                data_ocorrencia,
                descricao,
            )
            if not all(obrigatorios):
                raise ValueError("Preencha todos os campos obrigatórios.")
            try:
                data_ocorrencia_convertida = date.fromisoformat(data_ocorrencia)
            except ValueError as exc:
                raise ValueError("Informe uma data de ocorrência válida.") from exc
            if data_ocorrencia_convertida > date.today():
                raise ValueError("A data da ocorrência não pode ser futura.")

            if not _validar_id_no_dominio(cursor, "acr_origens", origem_id):
                raise ValueError("Origem inválida.")
            if not _validar_id_no_dominio(
                cursor, "acr_classificacoes", classificacao_id
            ):
                raise ValueError("Classificação inválida.")
            if not _validar_id_no_dominio(
                cursor, "acr_gravidades", gravidade_id
            ):
                raise ValueError("Gravidade inválida.")

            cursor.execute(
                """
                SELECT id
                FROM acr_metodologias
                WHERE id = %s AND ativo = 1 AND implementada = 1
                """,
                (metodologia_id,),
            )
            if not cursor.fetchone():
                raise ValueError("A metodologia selecionada não está disponível.")

            centros_validos = {item["id"]: item for item in centros}
            responsaveis_validos = {item["id"]: item for item in responsaveis}
            participantes_validos = {
                item["id"]: item for item in participantes
            }
            if centro_custos_id not in centros_validos:
                raise ValueError("Centro de custos fora do seu escopo.")
            if responsavel_id not in responsaveis_validos:
                raise ValueError("Responsável fora do seu escopo.")
            if (
                responsaveis_validos[responsavel_id]["centro_custos_id"]
                != centro_custos_id
            ):
                raise ValueError(
                    "O responsável deve pertencer ao centro de custos da ACR."
                )
            if any(
                participante_id not in participantes_validos
                for participante_id in participantes_selecionados
            ):
                raise ValueError(
                    "Um ou mais participantes estão fora do centro de custos da ACR."
                )
            participantes_selecionados = [
                participante_id
                for participante_id in participantes_selecionados
                if participante_id
                not in {responsavel_id, session.get("usuario_id")}
            ]
            origem_outros_registro = next(
                (
                    item
                    for item in dominios["origens"]
                    if item["id"] == origem_id
                ),
                None,
            )
            if (
                origem_outros_registro
                and origem_outros_registro["nome"].strip().lower() == "outros"
                and not origem_outros
            ):
                raise ValueError("Detalhe a origem selecionada como Outros.")

            ano = date.today().year
            cursor.execute(
                """
                INSERT INTO acr_sequencias (ano, ultimo_numero)
                VALUES (%s, 0)
                ON DUPLICATE KEY UPDATE ano = VALUES(ano)
                """,
                (ano,),
            )
            cursor.execute(
                """
                SELECT ultimo_numero
                FROM acr_sequencias
                WHERE ano = %s
                FOR UPDATE
                """,
                (ano,),
            )
            sequencial = cursor.fetchone()["ultimo_numero"] + 1
            cursor.execute(
                """
                UPDATE acr_sequencias
                SET ultimo_numero = %s
                WHERE ano = %s
                """,
                (sequencial, ano),
            )
            numero = f"ACR-{sequencial:03d}/{ano}"
            centro = centros_validos[centro_custos_id]

            cursor.execute(
                """
                INSERT INTO acr_investigacoes (
                    ano, sequencial, numero, origem_id, origem_outros,
                    classificacao_id, gravidade_id, metodologia_id,
                    data_ocorrencia, data_investigacao,
                    equipamento_processo, descricao_ocorrencia,
                    responsavel_id, criador_id, centro_custos_id,
                    superintendencia_id, status
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, CURRENT_DATE,
                    %s, %s, %s, %s, %s,
                    %s, 'Rascunho'
                )
                """,
                (
                    ano,
                    sequencial,
                    numero,
                    origem_id,
                    origem_outros,
                    classificacao_id,
                    gravidade_id,
                    metodologia_id,
                    data_ocorrencia,
                    equipamento,
                    descricao,
                    responsavel_id,
                    session.get("usuario_id"),
                    centro_custos_id,
                    centro.get("superintendencia_id"),
                ),
            )
            investigacao_id = cursor.lastrowid
            for participante_id in participantes_selecionados:
                cursor.execute(
                    """
                    INSERT INTO acr_participantes (
                        investigacao_id, usuario_id, adicionado_por
                    )
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        ativo = 1,
                        adicionado_por = VALUES(adicionado_por)
                    """,
                    (
                        investigacao_id,
                        participante_id,
                        session.get("usuario_id"),
                    ),
                )
            cursor.execute(
                """
                INSERT INTO acr_historico (
                    investigacao_id, usuario_id, evento, etapa
                )
                VALUES (%s, %s, 'Investigação criada', 'Cadastro')
                """,
                (investigacao_id, session.get("usuario_id")),
            )
            conn.commit()
            flash(f"{numero} criada com sucesso.", "success")
            return redirect(url_for("main.investigacoes_acr"))
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "danger")
            return render_template(
                "nova_investigacao_causa_raiz.html",
                dominios=dominios,
                centros=centros,
                responsaveis=responsaveis,
                participantes=participantes,
                participantes_selecionados=participantes_selecionados,
                hoje=date.today().isoformat(),
            )
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
