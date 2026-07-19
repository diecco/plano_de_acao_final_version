from flask import flash, redirect, render_template, request, session, url_for

from app.decorators import login_required, module_required
from app.upload_security import UploadService
from app.utils.db import get_db_connection


ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS


def register_melhorias_routes(blueprint):
    def _save_image_if_present(field_name: str, prefix: str):
        file = request.files.get(field_name)
        if file and allowed_image_file(file.filename):
            return UploadService.salvar(file, ALLOWED_IMAGE_EXTENSIONS, prefixo=prefix)
        return None


    @blueprint.route("/listar_melhoria", methods=["GET"])
    @login_required
    @module_required('acesso_melhoria')
    def listar_melhorias():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        usuario_id = session.get("usuario_id")
        perfil = session.get("perfil")
        centro_custos_id = session.get("centro_custos_id")

        if request.args.get("limpar"):
            cursor.close()
            conn.close()
            return redirect(url_for("main.listar_melhorias"))

        executante_id = request.args.get("executante", "").strip()
        centro_custo_id = request.args.get("centro_custo", "").strip()
        criado_por_mim = request.args.get("criado_por_mim", "").strip()
        data_inicio = request.args.get("data_inicio", "").strip()
        data_fim = request.args.get("data_fim", "").strip()

        sort = request.args.get("sort", "data")
        order = request.args.get("order", "desc")

        page = request.args.get("page", 1, type=int)
        per_page = 30

        if page < 1:
            page = 1

        offset = (page - 1) * per_page

        colunas_validas = {
            "data": "m.data",
            "executante": "u.nome",
            "centro_custo": "cc.codigo"
        }

        coluna_sort = colunas_validas.get(sort, "m.data")
        direcao = "ASC" if order == "asc" else "DESC"

        filtros_sql = []
        valores = []

        # CONTROLE DE ESCOPO
        if perfil == "basico":
            filtros_sql.append("m.criado_por = %s")
            valores.append(usuario_id)

        elif perfil == "intermediario":
            filtros_sql.append("m.centro_custo_id = %s")
            valores.append(centro_custos_id)

        # avançado e administrador veem tudo

        if executante_id:
            filtros_sql.append("m.executante_id = %s")
            valores.append(int(executante_id))

        if centro_custo_id:
            filtros_sql.append("m.centro_custo_id = %s")
            valores.append(int(centro_custo_id))

        if criado_por_mim == "sim":
            filtros_sql.append("m.criado_por = %s")
            valores.append(usuario_id)
        elif criado_por_mim == "nao":
            filtros_sql.append("m.criado_por <> %s")
            valores.append(usuario_id)

        if data_inicio and data_fim:
            filtros_sql.append("m.data BETWEEN %s AND %s")
            valores.extend([data_inicio, data_fim])
        elif data_inicio:
            filtros_sql.append("m.data >= %s")
            valores.append(data_inicio)
        elif data_fim:
            filtros_sql.append("m.data <= %s")
            valores.append(data_fim)

        where_clause = ("WHERE " + " AND ".join(filtros_sql)) if filtros_sql else ""

        cursor.execute(f"""
            SELECT COUNT(*) AS total
            FROM melhorias m
            JOIN usuarios u ON m.executante_id = u.id
            JOIN centros_custos cc ON m.centro_custo_id = cc.id
            {where_clause}
        """, valores)
        total_registros = cursor.fetchone()["total"]

        total_paginas = (total_registros + per_page - 1) // per_page

        if total_paginas > 0 and page > total_paginas:
            page = total_paginas
            offset = (page - 1) * per_page

        cursor.execute(f"""
            SELECT 
                m.*,
                u.nome AS nome_executante,
                cc.codigo AS codigo_cc,
                cc.descricao AS descricao_cc
            FROM melhorias m
            JOIN usuarios u ON m.executante_id = u.id
            JOIN centros_custos cc ON m.centro_custo_id = cc.id
            {where_clause}
            ORDER BY {coluna_sort} {direcao}, m.id DESC
            LIMIT %s OFFSET %s
        """, valores + [per_page, offset])
        melhorias = cursor.fetchall()

        if perfil in ["administrador", "avancado"]:
            cursor.execute("""
                SELECT id, nome
                FROM usuarios
                WHERE ativo = 1
                ORDER BY nome
            """)
            usuarios = cursor.fetchall()

            cursor.execute("""
                SELECT id, codigo, descricao
                FROM centros_custos
                ORDER BY codigo
            """)
            centros_custos = cursor.fetchall()
        else:
            cursor.execute("""
                SELECT id, nome
                FROM usuarios
                WHERE ativo = 1
                  AND centro_custos_id = %s
                ORDER BY nome
            """, (centro_custos_id,))
            usuarios = cursor.fetchall()

            cursor.execute("""
                SELECT id, codigo, descricao
                FROM centros_custos
                WHERE id = %s
                ORDER BY codigo
            """, (centro_custos_id,))
            centros_custos = cursor.fetchall()

        filtros = {
            "executante": executante_id,
            "centro_custo": centro_custo_id,
            "criado_por_mim": criado_por_mim,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "sort": sort,
            "order": order
        }

        cursor.close()
        conn.close()

        return render_template(
            "listar_melhoria.html",
            melhorias=melhorias,
            usuarios=usuarios,
            centros_custos=centros_custos,
            filtros=filtros,
            page=page,
            per_page=per_page,
            total_registros=total_registros,
            total_paginas=total_paginas
        )


    @blueprint.route("/lancar_melhoria", methods=["GET", "POST"])
    @login_required
    @module_required('acesso_melhoria')
    def lancar_melhoria():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        usuario_logado_id = session.get("usuario_id")
        perfil = session.get("perfil")
        centro_custo_id_logado = session.get("centro_custos_id")

        if not usuario_logado_id or not centro_custo_id_logado:
            cursor.close()
            conn.close()
            flash("Usuário logado inválido.", "danger")
            return redirect(url_for("main.dashboard"))

        cursor.execute("""
            SELECT id, codigo, descricao
            FROM centros_custos
            WHERE id = %s
        """, (centro_custo_id_logado,))
        centro_custo_logado = cursor.fetchone()

        if not centro_custo_logado:
            cursor.close()
            conn.close()
            flash("Centro de custo do usuário logado não encontrado.", "danger")
            return redirect(url_for("main.dashboard"))

        if request.method == "POST":
            try:
                data = request.form.get("data")
                executante_id = request.form.get("executante")
                titulo = request.form.get("titulo")
                descricao_antes = request.form.get("descricao_antes")
                acao_realizada = request.form.get("acao_realizada")
                descricao_depois = request.form.get("descricao_depois")
                resultados_alcancados = request.form.get("resultados_alcancados")
                economia_estimada = request.form.get("economia_estimada") or None
                observacoes = request.form.get("observacoes")

                tipo_ganho = request.form.getlist("tipo_ganho")
                tipo_ganho_str = ",".join(tipo_ganho)

                if not all([
                    data,
                    executante_id,
                    titulo,
                    descricao_antes,
                    acao_realizada,
                    descricao_depois,
                    resultados_alcancados
                ]):
                    flash("Preencha todos os campos obrigatórios.", "danger")
                    return redirect(url_for("main.lancar_melhoria"))

                if perfil in ["administrador", "avancado"]:
                    cursor.execute("""
                        SELECT id
                        FROM usuarios
                        WHERE id = %s
                          AND ativo = 1
                    """, (executante_id,))
                else:
                    cursor.execute("""
                        SELECT id
                        FROM usuarios
                        WHERE id = %s
                          AND ativo = 1
                          AND centro_custos_id = %s
                    """, (executante_id, centro_custo_id_logado))

                if not cursor.fetchone():
                    flash("Executante inválido para seu escopo.", "danger")
                    return redirect(url_for("main.lancar_melhoria"))

                foto_antes = _save_image_if_present("foto_antes", "antes")
                foto_depois = _save_image_if_present("foto_depois", "depois")

                cursor.execute("""
                    INSERT INTO melhorias 
                    (data, executante_id, centro_custo_id, titulo, tipo_ganho,
                     descricao_antes, acao_realizada, descricao_depois, resultados_alcancados,
                     foto_antes, foto_depois, economia_estimada, observacoes, criado_por)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    data,
                    executante_id,
                    centro_custo_id_logado,
                    titulo,
                    tipo_ganho_str,
                    descricao_antes,
                    acao_realizada,
                    descricao_depois,
                    resultados_alcancados,
                    foto_antes,
                    foto_depois,
                    economia_estimada,
                    observacoes,
                    usuario_logado_id
                ))

                conn.commit()
                flash("Melhoria lançada com sucesso!", "success")
                return redirect(url_for("main.lancar_melhoria"))

            except Exception as e:
                conn.rollback()
                flash(f"Erro ao lançar melhoria: {e}", "danger")
                return redirect(url_for("main.lancar_melhoria"))

            finally:
                cursor.close()
                conn.close()

        if perfil in ["administrador", "avancado"]:
            cursor.execute("""
                SELECT id, nome
                FROM usuarios
                WHERE ativo = 1
                ORDER BY nome
            """)
        else:
            cursor.execute("""
                SELECT id, nome
                FROM usuarios
                WHERE ativo = 1
                  AND centro_custos_id = %s
                ORDER BY nome
            """, (centro_custo_id_logado,))

        usuarios = cursor.fetchall()

        centros_custos = [{
            "id": centro_custo_logado["id"],
            "codigo": centro_custo_logado["codigo"],
            "descricao": centro_custo_logado["descricao"]
        }]

        centro_custo_usuario = centros_custos[0]

        cursor.close()
        conn.close()

        return render_template(
            "lancar_melhoria.html",
            usuarios=usuarios,
            centros_custos=centros_custos,
            centro_custo_usuario=centro_custo_usuario,
            melhoria=None
        )


    @blueprint.route("/editar_melhoria/<int:id>", methods=["GET", "POST"])
    @login_required
    @module_required('acesso_melhoria')
    def editar_melhoria(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        usuario_id = session.get("usuario_id")
        perfil = session.get("perfil")
        centro_custo_id = session.get("centro_custos_id")

        cursor.execute("""
            SELECT * 
            FROM melhorias
            WHERE id = %s
        """, (id,))
        melhoria = cursor.fetchone()

        if not melhoria:
            conn.close()
            flash("Melhoria não encontrada.", "danger")
            return redirect(url_for("main.listar_melhorias"))

        # 🔒 PERMISSIONAMENTO CORRETO
        if perfil not in ["administrador", "avancado"]:
            if perfil == "intermediario":
                if melhoria.get("centro_custo_id") != centro_custo_id:
                    conn.close()
                    flash("Você não tem permissão para editar esta melhoria.", "danger")
                    return redirect(url_for("main.listar_melhorias"))

            elif perfil == "basico":
                if melhoria.get("criado_por") != usuario_id:
                    conn.close()
                    flash("Você não tem permissão para editar esta melhoria.", "danger")
                    return redirect(url_for("main.listar_melhorias"))

        # ======================================================
        # POST
        # ======================================================
        if request.method == "POST":
            try:
                data = request.form.get("data")
                executante_id = request.form.get("executante")
                titulo = request.form.get("titulo")
                descricao_antes = request.form.get("descricao_antes")
                acao_realizada = request.form.get("acao_realizada")
                descricao_depois = request.form.get("descricao_depois")
                resultados_alcancados = request.form.get("resultados_alcancados")
                economia_estimada = request.form.get("economia_estimada") or None
                observacoes = request.form.get("observacoes")

                tipo_ganho = request.form.getlist("tipo_ganho")
                tipo_ganho_str = ",".join(tipo_ganho)

                if not all([
                    data,
                    executante_id,
                    titulo,
                    descricao_antes,
                    acao_realizada,
                    descricao_depois,
                    resultados_alcancados
                ]):
                    flash("Preencha todos os campos obrigatórios.", "danger")
                    return redirect(url_for("main.editar_melhoria", id=id))

                # 🔒 valida executante
                if perfil in ["administrador", "avancado"]:
                    cursor.execute("""
                        SELECT id FROM usuarios
                        WHERE id = %s AND ativo = 1
                    """, (executante_id,))
                else:
                    cursor.execute("""
                        SELECT id FROM usuarios
                        WHERE id = %s
                          AND ativo = 1
                          AND centro_custos_id = %s
                    """, (executante_id, centro_custo_id))

                if not cursor.fetchone():
                    flash("Executante inválido para seu escopo.", "danger")
                    return redirect(url_for("main.editar_melhoria", id=id))

                foto_antes = _save_image_if_present("foto_antes", "antes")
                foto_depois = _save_image_if_present("foto_depois", "depois")

                cursor.execute("""
                    UPDATE melhorias 
                    SET data=%s,
                        executante_id=%s,
                        centro_custo_id=%s,
                        titulo=%s,
                        tipo_ganho=%s,
                        descricao_antes=%s,
                        acao_realizada=%s,
                        descricao_depois=%s,
                        resultados_alcancados=%s,
                        economia_estimada=%s,
                        observacoes=%s,
                        foto_antes = COALESCE(%s, foto_antes),
                        foto_depois = COALESCE(%s, foto_depois)
                    WHERE id=%s
                """, (
                    data,
                    executante_id,
                    centro_custo_id,
                    titulo,
                    tipo_ganho_str,
                    descricao_antes,
                    acao_realizada,
                    descricao_depois,
                    resultados_alcancados,
                    economia_estimada,
                    observacoes,
                    foto_antes,
                    foto_depois,
                    id
                ))

                conn.commit()
                flash("Melhoria atualizada com sucesso!", "success")
                return redirect(url_for("main.listar_melhorias"))

            except Exception as e:
                conn.rollback()
                flash(f"Erro ao atualizar melhoria: {e}", "danger")
                return redirect(url_for("main.editar_melhoria", id=id))

            finally:
                cursor.close()
                conn.close()

        # ======================================================
        # GET
        # ======================================================

        if melhoria.get("tipo_ganho"):
            if isinstance(melhoria["tipo_ganho"], str):
                melhoria["ganhos_list"] = [
                    g.strip()
                    for g in melhoria["tipo_ganho"].split(",")
                    if g.strip()
                ]
            elif isinstance(melhoria["tipo_ganho"], set):
                melhoria["ganhos_list"] = list(melhoria["tipo_ganho"])
            else:
                melhoria["ganhos_list"] = []
        else:
            melhoria["ganhos_list"] = []

        if melhoria.get("data") and hasattr(melhoria["data"], "strftime"):
            melhoria["data"] = melhoria["data"].strftime("%Y-%m-%d")

        if perfil in ["administrador", "avancado"]:
            cursor.execute("SELECT id, nome FROM usuarios WHERE ativo = 1 ORDER BY nome")
        else:
            cursor.execute("""
                SELECT id, nome FROM usuarios
                WHERE ativo = 1
                  AND centro_custos_id = %s
                ORDER BY nome
            """, (centro_custo_id,))

        usuarios = cursor.fetchall()

        centros_custos = [{
            "id": centro_custo_id,
            "codigo": session.get("codigo_cc"),
            "descricao": session.get("descricao_cc")
        }]

        conn.close()

        return render_template(
            "lancar_melhoria.html",
            usuarios=usuarios,
            centros_custos=centros_custos,
            centro_custo_usuario=centros_custos[0],
            melhoria=melhoria
        )


    @blueprint.route("/excluir_melhoria/<int:id>", methods=["GET", "POST"])
    @login_required
    @module_required('acesso_melhoria')
    def excluir_melhoria(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        usuario_id = session.get("usuario_id")
        perfil = session.get("perfil")
        centro_custos_id = session.get("centro_custos_id")

        try:
            cursor.execute("""
                SELECT id, criado_por, centro_custo_id
                FROM melhorias
                WHERE id = %s
            """, (id,))
            melhoria = cursor.fetchone()

            if not melhoria:
                flash("Melhoria não encontrada.", "warning")
                return redirect(url_for("main.listar_melhorias"))

            if perfil not in ["administrador", "avancado"]:
                if perfil == "intermediario" and melhoria.get("centro_custo_id") != centro_custos_id:
                    flash("Você não tem permissão para excluir esta melhoria.", "danger")
                    return redirect(url_for("main.listar_melhorias"))

                if perfil == "basico" and melhoria.get("criado_por") != usuario_id:
                    flash("Você não tem permissão para excluir esta melhoria.", "danger")
                    return redirect(url_for("main.listar_melhorias"))

            cursor.execute("""
                DELETE FROM melhorias
                WHERE id = %s
            """, (id,))

            conn.commit()
            flash("Melhoria excluída com sucesso!", "success")

        except Exception as e:
            conn.rollback()
            flash(f"Erro ao excluir melhoria: {e}", "danger")

        finally:
            cursor.close()
            conn.close()

        return redirect(url_for("main.listar_melhorias"))

