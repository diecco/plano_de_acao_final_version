from datetime import datetime

from flask import flash, redirect, render_template, request, session, url_for

from app.decorators import admin_required, login_required, module_required
from app.utils.db import get_db_connection


def register_recusa_tarefa_routes(blueprint):
    @blueprint.route("/causas_recusa", methods=["GET", "POST"])
    @login_required
    @admin_required
    def causas_recusa():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == "POST":
            descricao = request.form.get("descricao")

            if not descricao:
                flash("Informe a descrição da causa.", "danger")
                conn.close()
                return redirect(url_for("main.causas_recusa"))

            cursor.execute(
                "INSERT INTO causas_recusa (descricao, ativo) VALUES (%s, 1)",
                (descricao,)
            )
            conn.commit()
            flash("Causa de recusa cadastrada com sucesso!", "success")

        # Lista todas as causas já cadastradas
        cursor.execute("SELECT * FROM causas_recusa ORDER BY descricao")
        causas = cursor.fetchall()

        conn.close()
        return render_template("causas_recusa.html", causas=causas)


    @blueprint.route("/editar_causa/<int:id>", methods=["GET", "POST"])
    @login_required
    @admin_required
    def editar_causa(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == "POST":
            descricao = request.form.get("descricao")

            if not descricao:
                flash("Informe a descrição da causa.", "danger")
                conn.close()
                return redirect(url_for("main.editar_causa", id=id))

            cursor.execute(
                "UPDATE causas_recusa SET descricao=%s WHERE id=%s",
                (descricao, id)
            )
            conn.commit()
            flash("Causa de recusa atualizada com sucesso!", "success")
            conn.close()
            return redirect(url_for("main.causas_recusa"))

        cursor.execute("SELECT * FROM causas_recusa WHERE id=%s", (id,))
        causa = cursor.fetchone()
        conn.close()

        if not causa:
            flash("Causa não encontrada.", "danger")
            return redirect(url_for("main.causas_recusa"))

        return render_template("editar_causa.html", causa=causa)



    @blueprint.route("/desativar_causa/<int:id>", methods=["GET"])
    @login_required
    @admin_required
    def desativar_causa(id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE causas_recusa SET ativo=0 WHERE id=%s", (id,))
        conn.commit()
        conn.close()
        flash("Causa desativada com sucesso!", "success")
        return redirect(url_for("main.causas_recusa"))


    @blueprint.route("/ativar_causa/<int:id>", methods=["GET"])
    @login_required
    @admin_required
    def ativar_causa(id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE causas_recusa SET ativo=1 WHERE id=%s", (id,))
        conn.commit()
        conn.close()
        flash("Causa ativada com sucesso!", "success")
        return redirect(url_for("main.causas_recusa"))


    @blueprint.route("/lancar_recusa", methods=["GET", "POST"])
    @login_required
    @module_required('acesso_ssma')
    def lancar_recusa():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        usuario_logado_id = session.get("usuario_id")
        perfil = session.get("perfil")
        centro_custos_id = session.get("centro_custos_id")

        if not usuario_logado_id:
            flash("Usuário logado não encontrado.", "danger")
            conn.close()
            return redirect(url_for("main.login"))

        if request.method == "POST":
            data_recusa = request.form.get("data")
            hora_recusa = request.form.get("hora")
            id_usuario = request.form.get("usuario_id")
            local = request.form.get("local")
            classificacao = request.form.get("classificacao")
            descricao = request.form.get("descricao")
            potencial_severidade = request.form.get("potencial")
            id_causa = request.form.get("causa_id")

            criado_por = usuario_logado_id

            if not (
                data_recusa and
                hora_recusa and
                id_usuario and
                classificacao and
                descricao and
                potencial_severidade and
                id_causa
            ):
                flash("Preencha todos os campos obrigatórios.", "danger")
                conn.close()
                return redirect(url_for("main.lancar_recusa"))

            if perfil in ["administrador", "avancado"]:
                cursor.execute("""
                    SELECT id
                    FROM usuarios
                    WHERE id = %s
                      AND ativo = 1
                """, (id_usuario,))
            else:
                cursor.execute("""
                    SELECT id
                    FROM usuarios
                    WHERE id = %s
                      AND ativo = 1
                      AND centro_custos_id = %s
                """, (id_usuario, centro_custos_id))

            usuario_valido = cursor.fetchone()

            if not usuario_valido:
                flash("Usuário selecionado não pertence ao seu centro de custo.", "danger")
                conn.close()
                return redirect(url_for("main.lancar_recusa"))

            cursor.execute("""
                INSERT INTO recusa_tarefa
                    (
                        data_recusa,
                        hora_recusa,
                        id_usuario,
                        local,
                        classificacao,
                        descricao,
                        potencial_severidade,
                        id_causa,
                        criado_por
                    )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data_recusa,
                hora_recusa,
                id_usuario,
                local,
                classificacao,
                descricao,
                potencial_severidade,
                id_causa,
                criado_por
            ))

            conn.commit()

            flash("Recusa registrada com sucesso!", "success")

            conn.close()

            return redirect(url_for("main.lancar_recusa"))

        if perfil in ["administrador", "avancado"]:
            cursor.execute("""
                SELECT id, nome, matricula
                FROM usuarios
                WHERE ativo = 1
                ORDER BY nome
            """)
        else:
            cursor.execute("""
                SELECT id, nome, matricula
                FROM usuarios
                WHERE ativo = 1
                  AND centro_custos_id = %s
                ORDER BY nome
            """, (centro_custos_id,))

        usuarios = cursor.fetchall()

        cursor.execute("""
            SELECT id, descricao
            FROM causas_recusa
            WHERE ativo = 1
            ORDER BY descricao
        """)

        causas = cursor.fetchall()

        conn.close()

        return render_template(
            "lancar_recusa.html",
            hoje=datetime.today().strftime("%Y-%m-%d"),
            agora=datetime.now().strftime("%H:%M"),
            usuarios=usuarios,
            causas=causas
        )


    @blueprint.route("/editar_recusa/<int:id>", methods=["GET", "POST"])
    @login_required
    @module_required('acesso_ssma')
    def editar_recusa(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        perfil = session.get("perfil")
        centro_custos_id = session.get("centro_custos_id")

        recusa = pode_acessar_ssma(cursor, 'recusa', id)

        if not recusa:
            conn.close()
            flash(
                "Recusa não encontrada ou você não possui permissão para editá-la.",
                "warning"
            )
            return redirect(url_for("main.listar_recusa"))

        if request.method == "POST":
            data_recusa = request.form.get("data")
            hora_recusa = request.form.get("hora")
            id_usuario = request.form.get("usuario_id")
            local = request.form.get("local")
            classificacao = request.form.get("classificacao")
            descricao = request.form.get("descricao")
            potencial_severidade = request.form.get("potencial")
            id_causa = request.form.get("causa_id")

            if not (
                data_recusa and
                hora_recusa and
                id_usuario and
                classificacao and
                descricao and
                potencial_severidade and
                id_causa
            ):
                flash("Preencha todos os campos obrigatórios.", "danger")
                conn.close()
                return redirect(url_for("main.editar_recusa", id=id))

            if perfil in ["administrador", "avancado"]:
                cursor.execute("""
                    SELECT id
                    FROM usuarios
                    WHERE id = %s
                      AND ativo = 1
                """, (id_usuario,))
            else:
                cursor.execute("""
                    SELECT id
                    FROM usuarios
                    WHERE id = %s
                      AND ativo = 1
                      AND centro_custos_id = %s
                """, (id_usuario, centro_custos_id))

            usuario_valido = cursor.fetchone()

            if not usuario_valido:
                conn.close()
                flash(
                    "Usuário selecionado não pertence ao seu centro de custo.",
                    "danger"
                )
                return redirect(url_for("main.editar_recusa", id=id))

            cursor.execute("""
                UPDATE recusa_tarefa
                SET
                    data_recusa = %s,
                    hora_recusa = %s,
                    id_usuario = %s,
                    local = %s,
                    classificacao = %s,
                    descricao = %s,
                    potencial_severidade = %s,
                    id_causa = %s
                WHERE id = %s
            """, (
                data_recusa,
                hora_recusa,
                id_usuario,
                local,
                classificacao,
                descricao,
                potencial_severidade,
                id_causa,
                id
            ))

            conn.commit()

            conn.close()

            flash("Recusa atualizada com sucesso!", "success")

            return redirect(url_for("main.listar_recusa"))

        cursor.execute("""
            SELECT
                r.*,
                u.nome AS usuario_nome,
                c.descricao AS causa_nome
            FROM recusa_tarefa r
            JOIN usuarios u ON r.id_usuario = u.id
            JOIN causas_recusa c ON r.id_causa = c.id
            WHERE r.id = %s
        """, (id,))

        recusa = cursor.fetchone()

        if recusa:

            if recusa["data_recusa"]:
                if hasattr(recusa["data_recusa"], "strftime"):
                    recusa["data_recusa"] = recusa["data_recusa"].strftime("%Y-%m-%d")
                else:
                    try:
                        recusa["data_recusa"] = datetime.strptime(
                            str(recusa["data_recusa"]),
                            "%Y-%m-%d"
                        ).strftime("%Y-%m-%d")
                    except:
                        recusa["data_recusa"] = ""

            if recusa["hora_recusa"]:
                if hasattr(recusa["hora_recusa"], "strftime"):
                    recusa["hora_recusa"] = recusa["hora_recusa"].strftime("%H:%M")
                else:
                    try:
                        recusa["hora_recusa"] = datetime.strptime(
                            str(recusa["hora_recusa"]),
                            "%H:%M:%S"
                        ).strftime("%H:%M")
                    except:
                        recusa["hora_recusa"] = ""

        if perfil in ["administrador", "avancado"]:
            cursor.execute("""
                SELECT id, nome, matricula
                FROM usuarios
                WHERE ativo = 1
                ORDER BY nome
            """)
        else:
            cursor.execute("""
                SELECT id, nome, matricula
                FROM usuarios
                WHERE ativo = 1
                  AND centro_custos_id = %s
                ORDER BY nome
            """, (centro_custos_id,))

        usuarios = cursor.fetchall()

        cursor.execute("""
            SELECT id, descricao
            FROM causas_recusa
            WHERE ativo = 1
            ORDER BY descricao
        """)

        causas = cursor.fetchall()

        conn.close()

        return render_template(
            "editar_recusa.html",
            recusa=recusa,
            usuarios=usuarios,
            causas=causas
        )

    @blueprint.route("/excluir_recusa/<int:id>", methods=["POST"])
    @login_required
    @module_required('acesso_ssma')
    def excluir_recusa(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        recusa = pode_acessar_ssma(cursor, 'recusa', id)

        if not recusa:
            conn.close()
            flash("Recusa não encontrada ou você não possui permissão para excluí-la.", "warning")
            return redirect(url_for("main.listar_recusa"))

        cursor.execute("DELETE FROM recusa_tarefa WHERE id = %s", (id,))
        conn.commit()
        conn.close()

        flash("Recusa excluída com sucesso!", "success")
        return redirect(url_for("main.listar_recusa"))

    @blueprint.route("/listar_recusa", methods=["GET"])
    @login_required
    @module_required('acesso_ssma')
    def listar_recusa():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        usuario_logado_id = session.get("usuario_id") or session.get("user_id") or session.get("id")

        cursor.execute("""
            SELECT id, perfil, centro_custos_id
            FROM usuarios
            WHERE id = %s
        """, (usuario_logado_id,))
        usuario_logado = cursor.fetchone()

        if not usuario_logado:
            conn.close()
            flash("Usuário logado não encontrado.", "danger")
            return redirect(url_for("main.login"))

        if request.args.get("limpar"):
            conn.close()
            return redirect(url_for("main.listar_recusa"))

        usuario_id = request.args.get("usuario_id", "")
        classificacao = request.args.get("classificacao", "")
        potencial = request.args.get("potencial", "")
        causa_id = request.args.get("causa_id", "")
        local = request.args.get("local", "")
        criado_por_mim = request.args.get("criado_por_mim", "")
        data_inicio = request.args.get("data_inicio", "")
        data_fim = request.args.get("data_fim", "")

        sort = request.args.get("sort", "data")
        order = request.args.get("order", "desc")

        page = request.args.get("page", 1, type=int)
        per_page = 30

        if page < 1:
            page = 1

        offset = (page - 1) * per_page

        colunas_validas = {
            "id": "r.id",
            "data": "r.data_recusa",
            "usuario": "u.nome",
            "classificacao": "r.classificacao",
            "potencial": "r.potencial_severidade"
        }

        coluna_sort = colunas_validas.get(sort, "r.data_recusa")
        direcao = "ASC" if order == "asc" else "DESC"

        base_from = """
            FROM recusa_tarefa r
            JOIN usuarios u ON r.id_usuario = u.id
            JOIN causas_recusa c ON r.id_causa = c.id
            WHERE 1=1
        """

        params = []

        perfil = usuario_logado["perfil"]

        if perfil == "basico":
            base_from += " AND r.criado_por = %s"
            params.append(usuario_logado_id)

        elif perfil == "intermediario":
            base_from += " AND u.centro_custos_id = %s"
            params.append(usuario_logado["centro_custos_id"])

        # avançado e administrador veem tudo

        if usuario_id:
            base_from += " AND r.id_usuario = %s"
            params.append(usuario_id)

        if classificacao:
            base_from += " AND r.classificacao = %s"
            params.append(classificacao)

        if potencial:
            base_from += " AND r.potencial_severidade = %s"
            params.append(potencial)

        if causa_id:
            base_from += " AND r.id_causa = %s"
            params.append(causa_id)

        if local:
            base_from += " AND r.local LIKE %s"
            params.append(f"%{local}%")

        if criado_por_mim == "sim":
            base_from += " AND r.criado_por = %s"
            params.append(usuario_logado_id)
        elif criado_por_mim == "nao":
            base_from += " AND r.criado_por <> %s"
            params.append(usuario_logado_id)

        if data_inicio:
            base_from += " AND r.data_recusa >= %s"
            params.append(data_inicio)

        if data_fim:
            base_from += " AND r.data_recusa <= %s"
            params.append(data_fim)

        cursor.execute(f"""
            SELECT COUNT(*) AS total
            {base_from}
        """, params)
        total_registros = cursor.fetchone()["total"]

        total_paginas = (total_registros + per_page - 1) // per_page

        if total_paginas > 0 and page > total_paginas:
            page = total_paginas
            offset = (page - 1) * per_page

        cursor.execute(f"""
            SELECT
                r.*,
                u.nome AS usuario_nome,
                c.descricao AS causa_nome
            {base_from}
            ORDER BY {coluna_sort} {direcao}, r.hora_recusa DESC
            LIMIT %s OFFSET %s
        """, params + [per_page, offset])
        registros = cursor.fetchall()

        if usuario_logado["perfil"] == "administrador":
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
            """, (usuario_logado["centro_custos_id"],))

        usuarios = cursor.fetchall()

        cursor.execute("""
            SELECT id, descricao
            FROM causas_recusa
            WHERE ativo = 1
            ORDER BY descricao
        """)
        causas = cursor.fetchall()

        conn.close()

        filtros = {
            "usuario_id": usuario_id,
            "classificacao": classificacao,
            "potencial": potencial,
            "causa_id": causa_id,
            "local": local,
            "criado_por_mim": criado_por_mim,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "sort": sort,
            "order": order
        }

        return render_template(
            "listar_recusa.html",
            registros=registros,
            usuarios=usuarios,
            causas=causas,
            filtros=filtros,
            page=page,
            per_page=per_page,
            total_registros=total_registros,
            total_paginas=total_paginas
        )

