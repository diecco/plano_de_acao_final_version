import os
from datetime import date
from math import ceil

from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.decorators import login_required, module_required
from app.services.groq_desvios import AnaliseIAError, analisar_desvio
from app.upload_security import UploadService, UploadValidationError
from app.utils.db import get_db_connection


POR_PAGINA = 30
EXTENSOES = {"pdf", "png", "jpg", "jpeg"}
ORDENACOES = {
    "id": "d.id",
    "data": "d.data_ocorrencia",
    "relator": "relator.nome",
    "setor": "s.nome",
    "categoria": "cat.nome",
    "descricao": "d.descricao",
    "potencial": "d.potencial",
    "status": "d.status",
}


def _admin():
    return session.get("perfil") == "administrador"


def _escopo(alias="d"):
    if _admin():
        return "1 = 1", []
    centro_id = session.get("centro_custos_id")
    if not centro_id:
        return "1 = 0", []
    return f"{alias}.centro_custos_id = %s", [centro_id]


def _pode_direcionar():
    return _admin() or bool(session.get("pode_direcionar_desvios"))


def _historico(cursor, desvio_id, evento, descricao):
    cursor.execute(
        """
        INSERT INTO desvios_historico (desvio_id, usuario_id, evento, descricao)
        VALUES (%s, %s, %s, %s)
        """,
        (desvio_id, session.get("usuario_id"), evento, descricao),
    )


def _buscar(cursor, desvio_id, for_update=False):
    filtro, params = _escopo("d")
    query = f"""
        SELECT d.*, relator.nome AS relator_nome,
               relator.matricula AS relator_matricula,
               registrador.nome AS registrador_nome,
               s.nome AS setor_nome, cat.nome AS categoria_nome,
               cc.codigo AS centro_codigo, cc.descricao AS centro_descricao,
               responsavel.nome AS responsavel_acao_nome,
               a.descricao AS acao_descricao, a.prazo AS acao_prazo,
               a.status AS acao_status
        FROM desvios d
        JOIN usuarios relator ON relator.id = d.relator_id
        JOIN usuarios registrador ON registrador.id = d.registrado_por
        JOIN setores s ON s.id = d.setor_id
        JOIN desvios_categorias cat ON cat.id = d.categoria_id
        JOIN centros_custos cc ON cc.id = d.centro_custos_id
        LEFT JOIN acoes a ON a.id = d.acao_id
        LEFT JOIN usuarios responsavel ON responsavel.id = a.responsavel_id
        WHERE d.id = %s AND d.excluido_em IS NULL AND {filtro}
    """
    if for_update:
        query += " FOR UPDATE"
    cursor.execute(query, [desvio_id, *params])
    return cursor.fetchone()


def _diretorio(desvio_id):
    return os.path.join("app", "static", "desvios", str(desvio_id))


VALORES_MATRIZ = {"baixa": 1, "media": 2, "alta": 3}


def _calcular_probabilidade(exposicao, controles, ocorrencia):
    valores = (exposicao, controles, ocorrencia)
    if any(valor not in VALORES_MATRIZ for valor in valores):
        raise ValueError("Preencha os três critérios de probabilidade.")
    media = sum(VALORES_MATRIZ[valor] for valor in valores) / 3
    if media <= 1.5:
        return "baixa"
    if media <= 2.3:
        return "media"
    return "alta"


def _calcular_risco(severidade, probabilidade):
    matriz = {
        "A": {"baixa": "medio", "media": "alto", "alta": "alto"},
        "B": {"baixa": "baixo", "media": "medio", "alta": "alto"},
        "C": {"baixa": "baixo", "media": "medio", "alta": "medio"},
    }
    try:
        return matriz[severidade][probabilidade]
    except KeyError as exc:
        raise ValueError("Classificação de risco inválida.") from exc


def register_desvios_routes(blueprint):
    @blueprint.route("/desvios/analisar-ia", methods=["POST"])
    @login_required
    @module_required("acesso_desvios")
    def analisar_desvio_ia():
        dados = request.get_json(silent=True) or {}
        if len((dados.get("descricao") or "").strip()) < 10:
            return jsonify({"erro": "Descreva o desvio com um pouco mais de detalhes."}), 400
        try:
            resultado = analisar_desvio(dados)
            if resultado.get("estado") == "concluida":
                resultado["descricao_original"] = (dados.get("descricao") or "")[:4000]
                resultado["token"] = URLSafeTimedSerializer(
                    current_app.secret_key, salt="analise-desvio-ia"
                ).dumps(resultado)
            return jsonify(resultado)
        except AnaliseIAError as exc:
            return jsonify({"erro": str(exc)}), 503

    @blueprint.route("/desvios")
    @login_required
    @module_required("acesso_desvios")
    def listar_desvios():
        pagina = max(request.args.get("page", 1, type=int), 1)
        data_inicio = (request.args.get("data_inicio") or "").strip()
        data_fim = (request.args.get("data_fim") or "").strip()
        potencial = (request.args.get("potencial") or "").strip().upper()
        status = (request.args.get("status") or "").strip()
        busca = (request.args.get("busca") or "").strip()
        relator_id = request.args.get("relator_id", type=int)
        sort = request.args.get("sort", "data")
        order = request.args.get("order", "desc").lower()
        sort = sort if sort in ORDENACOES else "data"
        order = order if order in {"asc", "desc"} else "desc"

        condicoes = ["d.excluido_em IS NULL"]
        params = []
        filtro_escopo, params_escopo = _escopo("d")
        condicoes.append(filtro_escopo)
        params.extend(params_escopo)
        if data_inicio:
            condicoes.append("d.data_ocorrencia >= %s")
            params.append(data_inicio)
        if data_fim:
            condicoes.append("d.data_ocorrencia <= %s")
            params.append(data_fim)
        if potencial in {"A", "B", "C"}:
            condicoes.append("d.potencial = %s")
            params.append(potencial)
        if status:
            condicoes.append("d.status = %s")
            params.append(status)
        if relator_id:
            condicoes.append("d.relator_id = %s")
            params.append(relator_id)
        if busca:
            condicoes.append("d.descricao LIKE %s")
            params.append(f"%{busca}%")
        where = " AND ".join(condicoes)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            base = f"""
                FROM desvios d
                JOIN usuarios relator ON relator.id = d.relator_id
                JOIN setores s ON s.id = d.setor_id
                JOIN desvios_categorias cat ON cat.id = d.categoria_id
                WHERE {where}
            """
            cursor.execute(f"SELECT COUNT(*) AS total {base}", params)
            total = cursor.fetchone()["total"]
            cursor.execute(
                f"""
                SELECT d.id, d.data_ocorrencia, d.hora_ocorrencia, d.tipo,
                       d.descricao, d.potencial, d.probabilidade,
                       d.nivel_risco, d.status, d.acao_id,
                       relator.nome AS relator_nome, s.nome AS setor_nome,
                       cat.nome AS categoria_nome
                {base}
                ORDER BY {ORDENACOES[sort]} {order}, d.id DESC
                LIMIT %s OFFSET %s
                """,
                [*params, POR_PAGINA, (pagina - 1) * POR_PAGINA],
            )
            registros = cursor.fetchall()
            if _admin():
                cursor.execute(
                    "SELECT id, nome, matricula FROM usuarios "
                    "WHERE ativo = 1 ORDER BY nome"
                )
            else:
                cursor.execute(
                    "SELECT id, nome, matricula FROM usuarios "
                    "WHERE ativo = 1 AND centro_custos_id = %s ORDER BY nome",
                    (session.get("centro_custos_id"),),
                )
            relatores = cursor.fetchall()
            relator_filtro = next(
                (item for item in relatores if item["id"] == relator_id), None
            )
        finally:
            cursor.close()
            conn.close()

        return render_template(
            "desvios.html",
            registros=registros,
            filtros={
                "data_inicio": data_inicio,
                "data_fim": data_fim,
                "potencial": potencial,
                "status": status,
                "busca": busca,
                "relator_id": relator_id or "",
                "sort": sort,
                "order": order,
            },
            page=pagina,
            total_paginas=max(ceil(total / POR_PAGINA), 1),
            total_registros=total,
            relatores=relatores,
            relator_filtro=relator_filtro,
        )

    @blueprint.route("/desvios/novo", methods=["GET", "POST"])
    @login_required
    @module_required("acesso_desvios")
    def novo_desvio():
        centro_id = session.get("centro_custos_id")
        if not centro_id:
            flash("Seu usuário não possui centro de custos configurado.", "danger")
            return redirect(url_for("main.listar_desvios"))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT id, nome, matricula FROM usuarios "
                "WHERE ativo = 1 AND centro_custos_id = %s ORDER BY nome",
                (centro_id,),
            )
            relatores = cursor.fetchall()
            cursor.execute("SELECT id, nome FROM setores WHERE ativo = 1 ORDER BY nome")
            setores = cursor.fetchall()
            cursor.execute(
                "SELECT id, nome FROM desvios_categorias "
                "WHERE ativo = 1 ORDER BY ordem, nome"
            )
            categorias = cursor.fetchall()

            if request.method == "POST":
                relator_id = request.form.get("relator_id", type=int)
                setor_id = request.form.get("setor_id", type=int)
                categoria_id = request.form.get("categoria_id", type=int)
                data_ocorrencia = (request.form.get("data_ocorrencia") or "").strip()
                hora_ocorrencia = (request.form.get("hora_ocorrencia") or "").strip()
                tipo = (request.form.get("tipo") or "").strip().lower()
                descricao = (request.form.get("descricao") or "").strip()
                severidade = (request.form.get("severidade") or "").strip().upper()
                exposicao = (request.form.get("matriz_exposicao") or "").strip()
                controles = (request.form.get("matriz_controles") or "").strip()
                ocorrencia = (request.form.get("matriz_ocorrencia") or "").strip()

                try:
                    date.fromisoformat(data_ocorrencia)
                    if tipo not in {"condicao", "comportamento"}:
                        raise ValueError("Selecione o tipo do desvio.")
                    if severidade not in {"A", "B", "C"}:
                        raise ValueError("Selecione a severidade da consequência.")
                    if not all((relator_id, setor_id, categoria_id, hora_ocorrencia, descricao)):
                        raise ValueError("Preencha todos os campos obrigatórios.")
                    cursor.execute(
                        "SELECT id FROM usuarios WHERE id = %s AND ativo = 1 "
                        "AND centro_custos_id = %s",
                        (relator_id, centro_id),
                    )
                    if not cursor.fetchone():
                        raise ValueError("Selecione um relator do seu centro de custos.")
                    cursor.execute("SELECT id FROM setores WHERE id = %s AND ativo = 1", (setor_id,))
                    if not cursor.fetchone():
                        raise ValueError("Selecione um setor válido.")
                    cursor.execute(
                        "SELECT id FROM desvios_categorias WHERE id = %s AND ativo = 1",
                        (categoria_id,),
                    )
                    if not cursor.fetchone():
                        raise ValueError("Selecione uma categoria válida.")

                    probabilidade = _calcular_probabilidade(exposicao, controles, ocorrencia)
                    nivel_risco = _calcular_risco(severidade, probabilidade)
                    analise_ia = None
                    token_ia = (request.form.get("ia_token") or "").strip()
                    if token_ia:
                        try:
                            analise_ia = URLSafeTimedSerializer(
                                current_app.secret_key, salt="analise-desvio-ia"
                            ).loads(token_ia, max_age=7200)
                        except (BadSignature, SignatureExpired) as exc:
                            raise ValueError("A sugestão da IA expirou ou é inválida. Analise novamente.") from exc
                    ia_utilizada = bool(analise_ia)
                    cursor.execute(
                        """
                        INSERT INTO desvios (
                            centro_custos_id, relator_id, registrado_por,
                            setor_id, categoria_id, data_ocorrencia,
                            hora_ocorrencia, tipo, descricao, matriz_critico,
                            matriz_grave, matriz_exposicao, matriz_controles,
                            matriz_ocorrencia, potencial, probabilidade, nivel_risco,
                            ia_utilizada, ia_modelo, ia_descricao_original,
                            ia_descricao_sugerida, ia_severidade_sugerida,
                            ia_probabilidade_sugerida, ia_justificativa, ia_confianca
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """,
                        (
                            centro_id, relator_id, session.get("usuario_id"),
                            setor_id, categoria_id, data_ocorrencia,
                            hora_ocorrencia, tipo, descricao,
                            int(severidade == "A"), int(severidade == "B"),
                            exposicao, controles, ocorrencia, severidade,
                            probabilidade, nivel_risco, int(ia_utilizada),
                            (analise_ia or {}).get("modelo"),
                            (analise_ia or {}).get("descricao_original"),
                            (analise_ia or {}).get("redacao_sugerida"),
                            (analise_ia or {}).get("severidade_sugerida"),
                            (analise_ia or {}).get("probabilidade_sugerida"),
                            (analise_ia or {}).get("justificativa"),
                            (analise_ia or {}).get("confianca"),
                        ),
                    )
                    desvio_id = cursor.lastrowid
                    for arquivo in request.files.getlist("anexos"):
                        if not arquivo or not arquivo.filename:
                            continue
                        nome_original = os.path.basename(
                            arquivo.filename.replace("\\", "/")
                        )[:255]
                        nome = UploadService.salvar(
                            arquivo,
                            EXTENSOES,
                            prefixo=f"desvio_{desvio_id}",
                            diretorio=_diretorio(desvio_id),
                        )
                        cursor.execute(
                            """
                            INSERT INTO desvios_anexos (
                                desvio_id, nome_original, nome_armazenado,
                                mime_type, criado_por
                            ) VALUES (%s,%s,%s,%s,%s)
                            """,
                            (
                                desvio_id, nome_original, nome,
                                (arquivo.mimetype or "application/octet-stream")[:120],
                                session.get("usuario_id"),
                            ),
                        )
                    _historico(
                        cursor,
                        desvio_id,
                        "cadastrado",
                        f"Desvio cadastrado com severidade {severidade}, "
                        f"probabilidade {probabilidade} e risco {nivel_risco}.",
                    )
                    conn.commit()
                    flash("Desvio cadastrado e enviado ao buffer.", "success")
                    return redirect(url_for("main.listar_desvios"))
                except (ValueError, UploadValidationError) as exc:
                    conn.rollback()
                    flash(str(exc), "warning")

            return render_template(
                "novo_desvio.html",
                relatores=relatores,
                setores=setores,
                categorias=categorias,
                registro=None,
            )
        finally:
            cursor.close()
            conn.close()

    @blueprint.route("/desvios/<int:desvio_id>/editar", methods=["GET", "POST"])
    @login_required
    @module_required("acesso_desvios")
    def editar_desvio(desvio_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            registro = _buscar(cursor, desvio_id)
            if not registro:
                flash("Desvio não encontrado ou fora do seu acesso.", "warning")
                return redirect(url_for("main.listar_desvios"))
            centro_id = registro["centro_custos_id"]
            cursor.execute(
                "SELECT id, nome, matricula FROM usuarios "
                "WHERE ativo = 1 AND centro_custos_id = %s ORDER BY nome",
                (centro_id,),
            )
            relatores = cursor.fetchall()
            cursor.execute("SELECT id, nome FROM setores WHERE ativo = 1 ORDER BY nome")
            setores = cursor.fetchall()
            cursor.execute(
                "SELECT id, nome FROM desvios_categorias "
                "WHERE ativo = 1 ORDER BY ordem, nome"
            )
            categorias = cursor.fetchall()

            if request.method == "POST":
                relator_id = request.form.get("relator_id", type=int)
                setor_id = request.form.get("setor_id", type=int)
                categoria_id = request.form.get("categoria_id", type=int)
                data_ocorrencia = (request.form.get("data_ocorrencia") or "").strip()
                hora_ocorrencia = (request.form.get("hora_ocorrencia") or "").strip()
                tipo = (request.form.get("tipo") or "").strip().lower()
                descricao = (request.form.get("descricao") or "").strip()
                severidade = (request.form.get("severidade") or "").strip().upper()
                exposicao = (request.form.get("matriz_exposicao") or "").strip()
                controles = (request.form.get("matriz_controles") or "").strip()
                ocorrencia = (request.form.get("matriz_ocorrencia") or "").strip()
                try:
                    date.fromisoformat(data_ocorrencia)
                    if tipo not in {"condicao", "comportamento"}:
                        raise ValueError("Selecione o tipo do desvio.")
                    if severidade not in {"A", "B", "C"}:
                        raise ValueError("Selecione a severidade da consequência.")
                    if not all((relator_id, setor_id, categoria_id, hora_ocorrencia, descricao)):
                        raise ValueError("Preencha todos os campos obrigatórios.")
                    cursor.execute(
                        "SELECT id FROM usuarios WHERE id = %s AND ativo = 1 "
                        "AND centro_custos_id = %s",
                        (relator_id, centro_id),
                    )
                    if not cursor.fetchone():
                        raise ValueError("Selecione um relator do centro de custos do desvio.")
                    cursor.execute("SELECT id FROM setores WHERE id = %s AND ativo = 1", (setor_id,))
                    if not cursor.fetchone():
                        raise ValueError("Selecione um setor válido.")
                    cursor.execute(
                        "SELECT id FROM desvios_categorias WHERE id = %s AND ativo = 1",
                        (categoria_id,),
                    )
                    if not cursor.fetchone():
                        raise ValueError("Selecione uma categoria válida.")
                    probabilidade = _calcular_probabilidade(exposicao, controles, ocorrencia)
                    nivel_risco = _calcular_risco(severidade, probabilidade)

                    analise_ia = None
                    token_ia = (request.form.get("ia_token") or "").strip()
                    if token_ia:
                        try:
                            analise_ia = URLSafeTimedSerializer(
                                current_app.secret_key, salt="analise-desvio-ia"
                            ).loads(token_ia, max_age=7200)
                        except (BadSignature, SignatureExpired) as exc:
                            raise ValueError(
                                "A sugestão da IA expirou ou é inválida. Analise novamente."
                            ) from exc

                    cursor.execute(
                        """
                        UPDATE desvios
                        SET relator_id = %s, setor_id = %s, categoria_id = %s,
                            data_ocorrencia = %s, hora_ocorrencia = %s,
                            tipo = %s, descricao = %s, matriz_critico = %s,
                            matriz_grave = %s, matriz_exposicao = %s,
                            matriz_controles = %s, matriz_ocorrencia = %s,
                            potencial = %s, probabilidade = %s, nivel_risco = %s,
                            ia_utilizada = IF(%s = 1, 1, ia_utilizada),
                            ia_modelo = COALESCE(%s, ia_modelo),
                            ia_descricao_original = COALESCE(%s, ia_descricao_original),
                            ia_descricao_sugerida = COALESCE(%s, ia_descricao_sugerida),
                            atualizado_em = NOW()
                        WHERE id = %s AND excluido_em IS NULL
                        """,
                        (
                            relator_id, setor_id, categoria_id, data_ocorrencia,
                            hora_ocorrencia, tipo, descricao, int(severidade == "A"),
                            int(severidade == "B"), exposicao, controles, ocorrencia,
                            severidade, probabilidade, nivel_risco, int(bool(analise_ia)),
                            (analise_ia or {}).get("modelo"),
                            (analise_ia or {}).get("descricao_original"),
                            (analise_ia or {}).get("redacao_sugerida"), desvio_id,
                        ),
                    )
                    for arquivo in request.files.getlist("anexos"):
                        if not arquivo or not arquivo.filename:
                            continue
                        nome_original = os.path.basename(
                            arquivo.filename.replace("\\", "/")
                        )[:255]
                        nome = UploadService.salvar(
                            arquivo,
                            EXTENSOES,
                            prefixo=f"desvio_{desvio_id}",
                            diretorio=_diretorio(desvio_id),
                        )
                        cursor.execute(
                            """
                            INSERT INTO desvios_anexos (
                                desvio_id, nome_original, nome_armazenado,
                                mime_type, criado_por
                            ) VALUES (%s,%s,%s,%s,%s)
                            """,
                            (
                                desvio_id, nome_original, nome,
                                (arquivo.mimetype or "application/octet-stream")[:120],
                                session.get("usuario_id"),
                            ),
                        )
                    _historico(
                        cursor,
                        desvio_id,
                        "editado",
                        f"Relato atualizado com severidade {severidade}, "
                        f"probabilidade {probabilidade} e risco {nivel_risco}.",
                    )
                    conn.commit()
                    flash("Desvio atualizado com sucesso.", "success")
                    return redirect(url_for("main.listar_desvios"))
                except (ValueError, UploadValidationError) as exc:
                    conn.rollback()
                    flash(str(exc), "warning")
                    registro = {**registro, **request.form.to_dict()}

            return render_template(
                "novo_desvio.html",
                relatores=relatores,
                setores=setores,
                categorias=categorias,
                registro=registro,
            )
        finally:
            cursor.close()
            conn.close()

    @blueprint.route("/desvios/<int:desvio_id>/excluir", methods=["POST"])
    @login_required
    @module_required("acesso_desvios")
    def excluir_desvio(desvio_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            registro = _buscar(cursor, desvio_id, for_update=True)
            if not registro:
                flash("Desvio não encontrado ou fora do seu acesso.", "warning")
                return redirect(url_for("main.listar_desvios"))
            _historico(
                cursor,
                desvio_id,
                "excluido",
                "Relato removido logicamente da listagem.",
            )
            cursor.execute(
                "UPDATE desvios SET excluido_em = NOW(), excluido_por = %s "
                "WHERE id = %s AND excluido_em IS NULL",
                (session.get("usuario_id"), desvio_id),
            )
            conn.commit()
            flash("Desvio excluído da listagem.", "success")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for("main.listar_desvios"))

    @blueprint.route("/desvios/buffer")
    @login_required
    @module_required("acesso_desvios")
    def buffer_desvios():
        if not _pode_direcionar():
            flash("Você não possui permissão para tratar o buffer de desvios.", "danger")
            return redirect(url_for("main.listar_desvios"))
        filtro, params = _escopo("d")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                f"""
                SELECT d.id, d.data_ocorrencia, d.hora_ocorrencia,
                       d.descricao, d.potencial, d.probabilidade,
                       d.nivel_risco, d.tipo,
                       r.nome AS relator_nome, s.nome AS setor_nome,
                       c.nome AS categoria_nome
                FROM desvios d
                JOIN usuarios r ON r.id = d.relator_id
                JOIN setores s ON s.id = d.setor_id
                JOIN desvios_categorias c ON c.id = d.categoria_id
                WHERE d.status = 'aguardando_direcionamento'
                  AND d.acao_id IS NULL AND d.excluido_em IS NULL
                  AND {filtro}
                ORDER BY FIELD(d.potencial, 'A', 'B', 'C'),
                         d.data_ocorrencia, d.id
                """,
                params,
            )
            registros = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
        return render_template("buffer_desvios.html", registros=registros)

    @blueprint.route("/desvios/<int:desvio_id>")
    @login_required
    @module_required("acesso_desvios")
    def detalhar_desvio(desvio_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            desvio = _buscar(cursor, desvio_id)
            if not desvio:
                flash("Desvio não encontrado ou fora do seu acesso.", "warning")
                return redirect(url_for("main.listar_desvios"))
            cursor.execute(
                "SELECT * FROM desvios_anexos WHERE desvio_id = %s AND ativo = 1 ORDER BY id",
                (desvio_id,),
            )
            anexos = cursor.fetchall()
            cursor.execute(
                """
                SELECT h.*, u.nome AS usuario_nome
                FROM desvios_historico h
                JOIN usuarios u ON u.id = h.usuario_id
                WHERE h.desvio_id = %s ORDER BY h.criado_em DESC, h.id DESC
                """,
                (desvio_id,),
            )
            historico = cursor.fetchall()
            responsaveis = []
            if _pode_direcionar() and not desvio.get("acao_id"):
                cursor.execute(
                    "SELECT id, nome, matricula FROM usuarios "
                    "WHERE ativo = 1 AND tem_acesso_sistema = 1 "
                    "AND acesso_plano_acao = 1 "
                    "AND centro_custos_id = %s ORDER BY nome",
                    (desvio["centro_custos_id"],),
                )
                responsaveis = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
        return render_template(
            "detalhe_desvio.html",
            desvio=desvio,
            anexos=anexos,
            historico=historico,
            responsaveis=responsaveis,
            pode_direcionar=_pode_direcionar(),
        )

    @blueprint.route("/desvios/<int:desvio_id>/direcionar", methods=["POST"])
    @login_required
    @module_required("acesso_desvios")
    def direcionar_desvio(desvio_id):
        if not _pode_direcionar():
            flash("Você não possui permissão para direcionar desvios.", "danger")
            return redirect(url_for("main.listar_desvios"))
        descricao = (request.form.get("acao") or "").strip()
        responsavel_id = request.form.get("responsavel_id", type=int)
        prazo_texto = (request.form.get("prazo") or "").strip()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            try:
                prazo = date.fromisoformat(prazo_texto)
                if prazo < date.today():
                    raise ValueError("O prazo não pode estar no passado.")
                if not descricao or not responsavel_id:
                    raise ValueError("Informe a ação e o responsável.")
                desvio = _buscar(cursor, desvio_id, for_update=True)
                if not desvio or desvio.get("acao_id"):
                    raise ValueError("Este desvio não está disponível no buffer.")
                cursor.execute(
                    "SELECT id FROM usuarios WHERE id = %s AND ativo = 1 "
                    "AND tem_acesso_sistema = 1 AND acesso_plano_acao = 1 "
                    "AND centro_custos_id = %s",
                    (responsavel_id, desvio["centro_custos_id"]),
                )
                if not cursor.fetchone():
                    raise ValueError("Selecione um responsável do centro de custos do desvio.")

                origem_nome = f"Relato de Desvio - {desvio['centro_codigo']}"
                cursor.execute(
                    """
                    INSERT INTO origens (nome, descricao, centro_custos_id, ativo)
                    VALUES (%s, %s, %s, 1)
                    ON DUPLICATE KEY UPDATE id = LAST_INSERT_ID(id), ativo = 1
                    """,
                    (origem_nome, origem_nome, desvio["centro_custos_id"]),
                )
                origem_id = cursor.lastrowid
                cursor.execute(
                    """
                    INSERT INTO acoes (
                        origem_id, responsavel_id, centro_custos_id,
                        descricao, prazo, status, criado_por
                    ) VALUES (%s,%s,%s,%s,%s,'Não iniciada',%s)
                    """,
                    (
                        origem_id, responsavel_id, desvio["centro_custos_id"],
                        f"[Desvio #{desvio_id}] {descricao}",
                        prazo, session.get("usuario_id"),
                    ),
                )
                acao_id = cursor.lastrowid
                cursor.execute(
                    """
                    UPDATE desvios
                    SET acao_id = %s, status = 'em_tratamento',
                        direcionado_por = %s, direcionado_em = NOW()
                    WHERE id = %s AND acao_id IS NULL
                      AND status = 'aguardando_direcionamento'
                    """,
                    (acao_id, session.get("usuario_id"), desvio_id),
                )
                if cursor.rowcount != 1:
                    raise ValueError("O desvio já foi direcionado por outro usuário.")
                _historico(
                    cursor,
                    desvio_id,
                    "direcionado",
                    f"Ação #{acao_id} criada e direcionada ao responsável selecionado.",
                )
                conn.commit()
                flash("Ação criada e desvio removido do buffer.", "success")
                return redirect(url_for("main.buffer_desvios"))
            except ValueError as exc:
                conn.rollback()
                flash(str(exc), "warning")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for("main.detalhar_desvio", desvio_id=desvio_id))

    @blueprint.route("/desvios/<int:desvio_id>/anexos/<int:anexo_id>")
    @login_required
    @module_required("acesso_desvios")
    def baixar_anexo_desvio(desvio_id, anexo_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            if not _buscar(cursor, desvio_id):
                flash("Anexo não encontrado ou fora do seu acesso.", "warning")
                return redirect(url_for("main.listar_desvios"))
            cursor.execute(
                "SELECT nome_original, nome_armazenado FROM desvios_anexos "
                "WHERE id = %s AND desvio_id = %s AND ativo = 1",
                (anexo_id, desvio_id),
            )
            anexo = cursor.fetchone()
            if not anexo:
                flash("Anexo não encontrado.", "warning")
                return redirect(url_for("main.detalhar_desvio", desvio_id=desvio_id))
            return send_from_directory(
                UploadService.resolver_diretorio(_diretorio(desvio_id)),
                anexo["nome_armazenado"],
                as_attachment=True,
                download_name=anexo["nome_original"],
            )
        finally:
            cursor.close()
            conn.close()
