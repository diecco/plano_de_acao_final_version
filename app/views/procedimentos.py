from flask import flash, redirect, render_template, request, session, url_for

from app.decorators import admin_required, login_required, module_required
from app.upload_security import UploadService
from app.utils.db import get_db_connection


def register_procedimentos_routes(blueprint):
    ALLOWED_PDF_EXTENSIONS = {"pdf"}


    def allowed_pdf_file(filename):
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_PDF_EXTENSIONS


    def _save_pdf_if_present(field_name: str):
        file = request.files.get(field_name)

        if not file or file.filename == "":
            return None

        if not allowed_pdf_file(file.filename):
            raise ValueError("Apenas arquivos PDF são permitidos.")

        return UploadService.salvar(file, ALLOWED_PDF_EXTENSIONS, prefixo="proc")


    @blueprint.route("/procedimentos", methods=["GET", "POST"])
    @login_required
    @module_required('acesso_procedimentos')
    def procedimentos():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        usuario_logado_id = session.get("usuario_id") or session.get("user_id") or session.get("id")

        if request.method == "POST":
            tipo_documento_id = request.form.get("tipo_documento_id")
            numero_documento = (request.form.get("numero_documento") or "").strip()
            titulo = (request.form.get("titulo") or "").strip()
            validade_dias = (request.form.get("validade_dias") or "").strip()
            niveis_aplicacao = request.form.getlist("niveis_aplicacao")

            numero_revisao = request.form.get("numero_revisao")
            data_revisao = request.form.get("data_revisao")
            elaborado_por = (request.form.get("elaborado_por") or "").strip() or None
            aprovado_por = (request.form.get("aprovado_por") or "").strip() or None
            observacoes = (request.form.get("observacoes") or "").strip() or None
            requer_treinamento = 1 if request.form.get("requer_treinamento") else 0

            niveis_validos = {"cargo", "funcao", "setor"}
            niveis_aplicacao = [n for n in niveis_aplicacao if n in niveis_validos]

            if not tipo_documento_id or not numero_documento or not titulo:
                flash("Preencha os campos obrigatórios do documento.", "danger")
                conn.close()
                return redirect(url_for("main.procedimentos"))

            if not niveis_aplicacao:
                flash("Selecione pelo menos um nível de aplicação do documento.", "warning")
                conn.close()
                return redirect(url_for("main.procedimentos"))

            try:
                import re

                if not re.match(r"^\d{3}$", numero_documento):
                    flash("O número do documento deve conter exatamente 3 dígitos.", "warning")
                    conn.close()
                    return redirect(url_for("main.procedimentos"))

                if validade_dias == "":
                    validade_dias_int = None
                else:
                    validade_dias_int = int(validade_dias)
                    if validade_dias_int < 0:
                        flash("A validade em dias não pode ser negativa.", "warning")
                        conn.close()
                        return redirect(url_for("main.procedimentos"))

                cursor.execute("""
                    SELECT id
                    FROM procedimentos
                    WHERE tipo_documento_id = %s
                      AND numero_documento = %s
                """, (tipo_documento_id, numero_documento))
                existente = cursor.fetchone()

                if existente:
                    flash("Já existe um documento com esse tipo e número.", "warning")
                    conn.close()
                    return redirect(url_for("main.procedimentos"))

                if numero_revisao in (None, "") or not data_revisao:
                    flash("Para cadastrar um novo procedimento, informe a revisão inicial e a data da revisão.", "danger")
                    conn.close()
                    return redirect(url_for("main.procedimentos"))

                try:
                    numero_revisao_int = int(numero_revisao)
                except ValueError:
                    flash("O número da revisão deve ser numérico.", "warning")
                    conn.close()
                    return redirect(url_for("main.procedimentos"))

                novo_pdf = _save_pdf_if_present("arquivo_pdf")

                cursor.execute("""
                    INSERT INTO procedimentos (
                        tipo_documento_id,
                        numero_documento,
                        titulo,
                        validade_dias,
                        ativo,
                        criado_por
                    )
                    VALUES (%s, %s, %s, %s, 1, %s)
                """, (
                    tipo_documento_id,
                    numero_documento,
                    titulo,
                    validade_dias_int,
                    usuario_logado_id
                ))
                novo_procedimento_id = cursor.lastrowid

                cursor.execute("""
                    INSERT INTO procedimento_revisoes (
                        procedimento_id,
                        numero_revisao,
                        data_revisao,
                        elaborado_por,
                        aprovado_por,
                        arquivo_pdf,
                        observacoes,
                        requer_treinamento,
                        vigente,
                        criado_por
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, %s)
                """, (
                    novo_procedimento_id,
                    numero_revisao_int,
                    data_revisao,
                    elaborado_por,
                    aprovado_por,
                    novo_pdf,
                    observacoes,
                    requer_treinamento,
                    usuario_logado_id
                ))

                for nivel in niveis_aplicacao:
                    cursor.execute("""
                        INSERT INTO procedimento_niveis_aplicacao (
                            procedimento_id,
                            nivel_aplicacao,
                            criado_por,
                            ativo
                        )
                        VALUES (%s, %s, %s, 1)
                    """, (
                        novo_procedimento_id,
                        nivel,
                        usuario_logado_id
                    ))

                conn.commit()
                flash("Procedimento cadastrado com sucesso!", "success")

            except ValueError:
                conn.rollback()
                flash("Informe um valor numérico válido para a validade em dias.", "danger")
            except Exception as e:
                conn.rollback()
                flash(f"Erro ao salvar procedimento: {e}", "danger")
            finally:
                conn.close()

            return redirect(url_for("main.listar_procedimentos"))

        cursor.execute("""
            SELECT id, sigla, descricao
            FROM tipos_documento
            WHERE ativo = 1
            ORDER BY nivel ASC, sigla ASC
        """)
        tipos_documento = cursor.fetchall()

        conn.close()

        return render_template(
            "procedimentos.html",
            tipos_documento=tipos_documento
        )


    @blueprint.route("/editar_procedimento/<int:id>", methods=["GET", "POST"])
    @login_required
    @module_required('acesso_procedimentos')
    def editar_procedimento(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        usuario_logado_id = session.get("usuario_id") or session.get("user_id") or session.get("id")

        cursor.execute("""
            SELECT *
            FROM procedimentos
            WHERE id = %s
        """, (id,))
        procedimento = cursor.fetchone()

        if not procedimento:
            conn.close()
            flash("Procedimento não encontrado.", "warning")
            return redirect(url_for("main.listar_procedimentos"))

        if request.method == "POST":
            tipo_documento_id = request.form.get("tipo_documento_id")
            numero_documento = (request.form.get("numero_documento") or "").strip()
            titulo = (request.form.get("titulo") or "").strip()
            validade_dias = (request.form.get("validade_dias") or "").strip()
            niveis_aplicacao = request.form.getlist("niveis_aplicacao")

            niveis_validos = {"cargo", "funcao", "setor"}
            niveis_aplicacao = [n for n in niveis_aplicacao if n in niveis_validos]

            if not tipo_documento_id or not numero_documento or not titulo:
                flash("Preencha todos os campos obrigatórios.", "danger")
                conn.close()
                return redirect(url_for("main.editar_procedimento", id=id))

            if not niveis_aplicacao:
                flash("Selecione pelo menos um nível de aplicação do documento.", "warning")
                conn.close()
                return redirect(url_for("main.editar_procedimento", id=id))

            try:
                import re

                if not re.match(r"^\d{3}$", numero_documento):
                    flash("O número do documento deve conter exatamente 3 dígitos.", "warning")
                    conn.close()
                    return redirect(url_for("main.editar_procedimento", id=id))

                if validade_dias == "":
                    validade_dias_int = None
                else:
                    validade_dias_int = int(validade_dias)
                    if validade_dias_int < 0:
                        flash("A validade em dias não pode ser negativa.", "warning")
                        conn.close()
                        return redirect(url_for("main.editar_procedimento", id=id))

                cursor.execute("""
                    SELECT id
                    FROM procedimentos
                    WHERE tipo_documento_id = %s
                      AND numero_documento = %s
                      AND id <> %s
                """, (tipo_documento_id, numero_documento, id))
                existente = cursor.fetchone()

                if existente:
                    flash("Já existe um documento com esse tipo e número.", "warning")
                    conn.close()
                    return redirect(url_for("main.editar_procedimento", id=id))

                cursor.execute("""
                    UPDATE procedimentos
                    SET tipo_documento_id = %s,
                        numero_documento = %s,
                        titulo = %s,
                        validade_dias = %s
                    WHERE id = %s
                """, (
                    tipo_documento_id,
                    numero_documento,
                    titulo,
                    validade_dias_int,
                    id
                ))

                cursor.execute("""
                    UPDATE procedimento_niveis_aplicacao
                    SET ativo = 0
                    WHERE procedimento_id = %s
                """, (id,))

                for nivel in niveis_aplicacao:
                    cursor.execute("""
                        SELECT id
                        FROM procedimento_niveis_aplicacao
                        WHERE procedimento_id = %s
                          AND nivel_aplicacao = %s
                        LIMIT 1
                    """, (id, nivel))
                    registro_existente = cursor.fetchone()

                    if registro_existente:
                        cursor.execute("""
                            UPDATE procedimento_niveis_aplicacao
                            SET ativo = 1
                            WHERE id = %s
                        """, (registro_existente["id"],))
                    else:
                        cursor.execute("""
                            INSERT INTO procedimento_niveis_aplicacao (
                                procedimento_id,
                                nivel_aplicacao,
                                criado_por,
                                ativo
                            )
                            VALUES (%s, %s, %s, 1)
                        """, (
                            id,
                            nivel,
                            usuario_logado_id
                        ))

                conn.commit()
                flash("Procedimento atualizado com sucesso!", "success")
                conn.close()
                return redirect(url_for("main.listar_procedimentos"))

            except ValueError:
                conn.rollback()
                conn.close()
                flash("Informe um valor numérico válido para a validade em dias.", "danger")
                return redirect(url_for("main.editar_procedimento", id=id))
            except Exception as e:
                conn.rollback()
                conn.close()
                flash(f"Erro ao atualizar procedimento: {e}", "danger")
                return redirect(url_for("main.editar_procedimento", id=id))

        cursor.execute("""
            SELECT id, sigla, descricao
            FROM tipos_documento
            WHERE ativo = 1
            ORDER BY nivel ASC, sigla ASC
        """)
        tipos_documento = cursor.fetchall()

        cursor.execute("""
            SELECT *
            FROM procedimento_revisoes
            WHERE procedimento_id = %s
              AND vigente = 1
            LIMIT 1
        """, (id,))
        revisao_vigente = cursor.fetchone()

        cursor.execute("""
            SELECT nivel_aplicacao
            FROM procedimento_niveis_aplicacao
            WHERE procedimento_id = %s
              AND ativo = 1
        """, (id,))
        niveis_aplicacao_salvos = [row["nivel_aplicacao"] for row in cursor.fetchall()]

        conn.close()

        return render_template(
            "editar_procedimento.html",
            procedimento=procedimento,
            tipos_documento=tipos_documento,
            revisao_vigente=revisao_vigente,
            niveis_aplicacao_salvos=niveis_aplicacao_salvos
        )


    @blueprint.route("/nova_revisao_procedimento/<int:id>", methods=["GET", "POST"])
    @login_required
    @module_required('acesso_procedimentos')
    def nova_revisao_procedimento(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        usuario_logado_id = session.get("usuario_id") or session.get("user_id") or session.get("id")

        cursor.execute("""
            SELECT
                p.id,
                p.tipo_documento_id,
                p.numero_documento,
                p.titulo,
                td.sigla,
                td.descricao AS descricao_tipo
            FROM procedimentos p
            JOIN tipos_documento td
                ON td.id = p.tipo_documento_id
            WHERE p.id = %s
        """, (id,))
        procedimento = cursor.fetchone()

        if not procedimento:
            conn.close()
            flash("Procedimento não encontrado.", "warning")
            return redirect(url_for("main.listar_procedimentos"))

        if request.method == "POST":
            numero_revisao = request.form.get("numero_revisao")
            data_revisao = request.form.get("data_revisao")
            elaborado_por = (request.form.get("elaborado_por") or "").strip() or None
            aprovado_por = (request.form.get("aprovado_por") or "").strip() or None
            observacoes = (request.form.get("observacoes") or "").strip() or None
            requer_treinamento = 1 if request.form.get("requer_treinamento") else 0

            try:
                if numero_revisao in (None, "") or not data_revisao:
                    flash("Informe o número da revisão e a data da revisão.", "danger")
                    conn.close()
                    return redirect(url_for("main.nova_revisao_procedimento", id=id))

                try:
                    numero_revisao_int = int(numero_revisao)
                except ValueError:
                    flash("O número da revisão deve ser numérico.", "warning")
                    conn.close()
                    return redirect(url_for("main.nova_revisao_procedimento", id=id))

                cursor.execute("""
                    SELECT id
                    FROM procedimento_revisoes
                    WHERE procedimento_id = %s
                      AND numero_revisao = %s
                """, (id, numero_revisao_int))
                revisao_existente = cursor.fetchone()

                if revisao_existente:
                    flash("Já existe uma revisão com esse número para este procedimento.", "warning")
                    conn.close()
                    return redirect(url_for("main.nova_revisao_procedimento", id=id))

                novo_pdf = _save_pdf_if_present("arquivo_pdf")

                cursor.execute("""
                    UPDATE procedimento_revisoes
                    SET vigente = 0
                    WHERE procedimento_id = %s
                      AND vigente = 1
                """, (id,))

                cursor.execute("""
                    INSERT INTO procedimento_revisoes (
                        procedimento_id,
                        numero_revisao,
                        data_revisao,
                        elaborado_por,
                        aprovado_por,
                        arquivo_pdf,
                        observacoes,
                        requer_treinamento,
                        vigente,
                        criado_por
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, %s)
                """, (
                    id,
                    numero_revisao_int,
                    data_revisao,
                    elaborado_por,
                    aprovado_por,
                    novo_pdf,
                    observacoes,
                    requer_treinamento,
                    usuario_logado_id
                ))

                conn.commit()
                flash("Nova revisão cadastrada com sucesso!", "success")
                conn.close()
                return redirect(url_for("main.listar_procedimentos"))

            except ValueError as e:
                conn.rollback()
                conn.close()
                flash(str(e), "danger")
                return redirect(url_for("main.nova_revisao_procedimento", id=id))
            except Exception as e:
                conn.rollback()
                conn.close()
                flash(f"Erro ao cadastrar nova revisão: {e}", "danger")
                return redirect(url_for("main.nova_revisao_procedimento", id=id))

        cursor.execute("""
            SELECT *
            FROM procedimento_revisoes
            WHERE procedimento_id = %s
              AND vigente = 1
            LIMIT 1
        """, (id,))
        revisao_vigente = cursor.fetchone()

        proxima_revisao = 0
        if revisao_vigente and revisao_vigente.get("numero_revisao") is not None:
            proxima_revisao = int(revisao_vigente["numero_revisao"]) + 1

        conn.close()

        return render_template(
            "nova_revisao_procedimento.html",
            procedimento=procedimento,
            revisao_vigente=revisao_vigente,
            proxima_revisao=proxima_revisao
        )


    @blueprint.route("/historico_revisoes_procedimento/<int:procedimento_id>", methods=["GET"])
    @login_required
    @module_required('acesso_procedimentos')
    def historico_revisoes_procedimento(procedimento_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                p.id,
                p.numero_documento,
                p.titulo,
                td.sigla
            FROM procedimentos p
            JOIN tipos_documento td
                ON td.id = p.tipo_documento_id
            WHERE p.id = %s
        """, (procedimento_id,))
        procedimento = cursor.fetchone()

        if not procedimento:
            conn.close()
            flash("Procedimento não encontrado.", "warning")
            return redirect(url_for("main.listar_procedimentos"))

        cursor.execute("""
            SELECT
                pr.*
            FROM procedimento_revisoes pr
            WHERE pr.procedimento_id = %s
            ORDER BY pr.numero_revisao DESC, pr.id DESC
        """, (procedimento_id,))
        revisoes = cursor.fetchall()

        conn.close()

        return render_template(
            "historico_revisoes_procedimento.html",
            procedimento=procedimento,
            revisoes=revisoes
        )


    @blueprint.route("/desativar_procedimento/<int:id>", methods=["POST"])
    @login_required
    @admin_required
    def desativar_procedimento(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                UPDATE procedimentos
                SET ativo = 0
                WHERE id = %s
            """, (id,))
            conn.commit()
            flash("Procedimento desativado com sucesso!", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Erro ao desativar procedimento: {e}", "danger")
        finally:
            conn.close()

        return redirect(url_for("main.listar_procedimentos"))


    @blueprint.route("/reativar_procedimento/<int:id>", methods=["POST"])
    @login_required
    @admin_required
    def reativar_procedimento(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                UPDATE procedimentos
                SET ativo = 1
                WHERE id = %s
            """, (id,))
            conn.commit()
            flash("Procedimento reativado com sucesso!", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Erro ao reativar procedimento: {e}", "danger")
        finally:
            conn.close()

        return redirect(url_for("main.listar_procedimentos"))

    @blueprint.route("/listar_procedimentos", methods=["GET"])
    @login_required
    @module_required('acesso_procedimentos')
    def listar_procedimentos():

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        tipo_documento_id = request.args.get("tipo_documento_id", "")
        status = request.args.get("status", "")

        sort = request.args.get("sort", "sigla")
        order = request.args.get("order", "asc")

        colunas_validas = {
            "sigla": "td.sigla",
            "numero_documento": "p.numero_documento",
            "titulo": "p.titulo",
            "numero_revisao": "pr.numero_revisao",
            "data_revisao": "pr.data_revisao"
        }

        coluna_sort = colunas_validas.get(sort, "td.sigla")
        direcao = "ASC" if order == "asc" else "DESC"

        query = """
            SELECT
                p.id,
                p.tipo_documento_id,
                p.numero_documento,
                p.titulo,
                p.ativo,
                td.sigla,
                pr.numero_revisao,
                pr.data_revisao,
                pr.arquivo_pdf,
                pr.requer_treinamento
            FROM procedimentos p
            JOIN tipos_documento td
                ON td.id = p.tipo_documento_id
            LEFT JOIN procedimento_revisoes pr
                ON pr.procedimento_id = p.id
               AND pr.vigente = 1
            WHERE 1=1
        """

        params = []

        if tipo_documento_id:
            query += " AND p.tipo_documento_id = %s"
            params.append(tipo_documento_id)

        if status == "ativo":
            query += " AND p.ativo = 1"
        elif status == "inativo":
            query += " AND p.ativo = 0"

        query += f" ORDER BY {coluna_sort} {direcao}, p.numero_documento ASC"

        cursor.execute(query, params)
        procedimentos = cursor.fetchall()

        cursor.execute("""
            SELECT id, sigla, descricao
            FROM tipos_documento
            WHERE ativo = 1
            ORDER BY nivel ASC, sigla ASC
        """)
        tipos_documento = cursor.fetchall()

        conn.close()

        filtros = {
            "tipo_documento_id": tipo_documento_id,
            "status": status,
            "sort": sort,
            "order": order
        }

        return render_template(
            "listar_procedimentos.html",
            procedimentos=procedimentos,
            tipos_documento=tipos_documento,
            filtros=filtros
        )
