from datetime import date

from flask import flash, redirect, render_template, request, session, url_for

from app.decorators import login_required, module_required
from app.utils.db import get_db_connection


STATUS_ACR = {
    "Rascunho",
    "Em Investigação",
    "Aguardando Informações",
    "Concluída",
    "Cancelada",
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
    perfil = session.get("perfil")
    centro_sessao = session.get("centro_custos_id")

    query_centros = """
        SELECT id, codigo, descricao, superintendencia_id
        FROM centros_custos
        WHERE ativo = 1
    """
    params_centros = []
    if perfil in ("basico", "intermediario"):
        query_centros += " AND id = %s"
        params_centros.append(centro_sessao)
    query_centros += " ORDER BY codigo"
    cursor.execute(query_centros, params_centros)
    centros = cursor.fetchall()

    query_usuarios = """
        SELECT id, nome, matricula, centro_custos_id
        FROM usuarios
        WHERE ativo = 1
          AND tem_acesso_sistema = 1
          AND (acesso_acr = 1 OR perfil = 'administrador')
    """
    params_usuarios = []
    if perfil in ("basico", "intermediario"):
        query_usuarios += " AND centro_custos_id = %s"
        params_usuarios.append(centro_sessao)
    query_usuarios += " ORDER BY nome"
    cursor.execute(query_usuarios, params_usuarios)

    return centros, cursor.fetchall()


def _validar_id_no_dominio(cursor, tabela, registro_id):
    cursor.execute(
        f"SELECT id FROM {tabela} WHERE id = %s AND ativo = 1",
        (registro_id,),
    )
    return cursor.fetchone() is not None


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

            query += " ORDER BY i.ano DESC, i.sequencial DESC"
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
            )
        finally:
            cursor.close()
            conn.close()

    @blueprint.route("/acr/nova", methods=["GET", "POST"])
    @login_required
    @module_required("acesso_acr")
    def nova_investigacao_acr():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            dominios = _buscar_dominios(cursor)
            centros, responsaveis = _buscar_centros_e_responsaveis(cursor)

            if request.method == "GET":
                return render_template(
                    "nova_investigacao_causa_raiz.html",
                    dominios=dominios,
                    centros=centros,
                    responsaveis=responsaveis,
                    hoje=date.today().isoformat(),
                )

            origem_id = request.form.get("origem_id", type=int)
            classificacao_id = request.form.get("classificacao_id", type=int)
            gravidade_id = request.form.get("gravidade_id", type=int)
            metodologia_id = request.form.get("metodologia_id", type=int)
            centro_custos_id = request.form.get("centro_custos_id", type=int)
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
            cursor.execute(
                """
                INSERT INTO acr_participantes (
                    investigacao_id, usuario_id, adicionado_por
                )
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE ativo = 1
                """,
                (
                    investigacao_id,
                    responsavel_id,
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
                hoje=date.today().isoformat(),
            )
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
