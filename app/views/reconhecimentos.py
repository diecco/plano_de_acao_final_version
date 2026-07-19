from datetime import date

from flask import flash, redirect, render_template, request, session, url_for

from app.decorators import login_required, module_required
from app.utils.db import get_db_connection


def register_reconhecimentos_routes(blueprint):
    @blueprint.route("/lancar_reconhecimento", methods=["GET", "POST"])
    @login_required
    @module_required('acesso_gestao_pessoas')
    def lancar_reconhecimento():
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        usuario_logado_id = session.get("usuario_id")
        perfil = session.get("perfil")
        centro_custo_id_logado = session.get("centro_custos_id")

        if (
            not usuario_logado_id
            or (
                perfil not in ['administrador', 'avancado']
                and not centro_custo_id_logado
            )
        ):
            cur.close()
            conn.close()
            flash("Usuário logado inválido.", "danger")
            return redirect(url_for("main.dashboard"))

        if perfil in ["administrador", "avancado"]:
            cur.execute("""
                SELECT id, nome, matricula
                FROM usuarios
                WHERE ativo = 1
                ORDER BY nome
            """)
        else:
            cur.execute("""
                SELECT id, nome, matricula
                FROM usuarios
                WHERE ativo = 1
                  AND centro_custos_id = %s
                ORDER BY nome
            """, (centro_custo_id_logado,))

        usuarios = cur.fetchall()

        if request.method == "POST":
            apoiador_id = request.form.get("apoiador_id")
            id_reconhecido = request.form.get("id_reconhecido")
            data_reconhecimento = request.form.get("data_reconhecimento")
            reconhecimento = request.form.get("reconhecimento")
            criado_por = usuario_logado_id

            if not (apoiador_id and id_reconhecido and data_reconhecimento and reconhecimento and criado_por):
                flash("Preencha todos os campos obrigatórios.", "warning")
                cur.close()
                conn.close()
                return render_template(
                    "lancar_reconhecimento.html",
                    usuarios=usuarios,
                    current_date=date.today().isoformat()
                )

            if apoiador_id == id_reconhecido:
                flash("O apoiador e o reconhecido não podem ser a mesma pessoa.", "warning")
                cur.close()
                conn.close()
                return render_template(
                    "lancar_reconhecimento.html",
                    usuarios=usuarios,
                    current_date=date.today().isoformat()
                )

            if perfil in ["administrador", "avancado"]:
                cur.execute("""
                    SELECT id
                    FROM usuarios
                    WHERE id IN (%s, %s)
                      AND ativo = 1
                """, (apoiador_id, id_reconhecido))
            else:
                cur.execute("""
                    SELECT id
                    FROM usuarios
                    WHERE id IN (%s, %s)
                      AND ativo = 1
                      AND centro_custos_id = %s
                """, (apoiador_id, id_reconhecido, centro_custo_id_logado))

            usuarios_validos = cur.fetchall()

            if len(usuarios_validos) != 2:
                flash("Apoiador e reconhecido devem pertencer ao seu escopo de acesso.", "warning")
                cur.close()
                conn.close()
                return render_template(
                    "lancar_reconhecimento.html",
                    usuarios=usuarios,
                    current_date=date.today().isoformat()
                )

            cur.execute("""
                INSERT INTO reconhecimentos
                    (apoiador_id, id_reconhecido, data_reconhecimento, reconhecimento, criado_por)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                apoiador_id,
                id_reconhecido,
                data_reconhecimento,
                reconhecimento,
                criado_por
            ))

            conn.commit()

            flash("Reconhecimento cadastrado com sucesso!", "success")

            cur.close()
            conn.close()

            return redirect(url_for("main.lancar_reconhecimento"))

        cur.close()
        conn.close()

        return render_template(
            "lancar_reconhecimento.html",
            usuarios=usuarios,
            current_date=date.today().isoformat()
        )


    @blueprint.route("/listar_reconhecimento", methods=["GET"])
    @login_required
    @module_required('acesso_gestao_pessoas')
    def listar_reconhecimento():
        usuario_logado_id = session.get("usuario_id")
        perfil = session.get("perfil")
        centro_custo_id_logado = session.get("centro_custos_id")

        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        if not usuario_logado_id or not centro_custo_id_logado:
            cur.close()
            conn.close()
            flash("Usuário logado inválido.", "danger")
            return redirect(url_for("main.dashboard"))

        if request.args.get("limpar"):
            cur.close()
            conn.close()
            return redirect(url_for("main.listar_reconhecimento"))

        apoiador_id = request.args.get("apoiador_id", "")
        id_reconhecido = request.args.get("id_reconhecido", "")
        data_inicio = request.args.get("data_inicio", "")
        data_fim = request.args.get("data_fim", "")
        sort = request.args.get("sort", "data_reconhecimento")
        order = request.args.get("order", "desc")

        page = request.args.get("page", 1, type=int)
        per_page = 30

        if page < 1:
            page = 1

        offset = (page - 1) * per_page

        base_from = """
            FROM reconhecimentos r
            JOIN usuarios u1 ON r.apoiador_id = u1.id
            JOIN usuarios u2 ON r.id_reconhecido = u2.id
            WHERE 1 = 1
        """

        params = []

        if perfil == "basico":
            base_from += " AND r.criado_por = %s"
            params.append(usuario_logado_id)

        elif perfil == "intermediario":
            base_from += """
                AND u1.centro_custos_id = %s
                AND u2.centro_custos_id = %s
            """
            params.extend([centro_custo_id_logado, centro_custo_id_logado])

        # avançado e administrador veem tudo

        if apoiador_id:
            base_from += " AND r.apoiador_id = %s"
            params.append(apoiador_id)

        if id_reconhecido:
            base_from += " AND r.id_reconhecido = %s"
            params.append(id_reconhecido)

        if data_inicio:
            base_from += " AND r.data_reconhecimento >= %s"
            params.append(data_inicio)

        if data_fim:
            base_from += " AND r.data_reconhecimento <= %s"
            params.append(data_fim)

        allowed_sorts = {
            "id": "r.id",
            "apoiador": "u1.nome",
            "reconhecido": "u2.nome",
            "data_reconhecimento": "r.data_reconhecimento",
            "reconhecimento": "r.reconhecimento"
        }

        coluna_sort = allowed_sorts.get(sort, "r.data_reconhecimento")
        direcao = "ASC" if order == "asc" else "DESC"

        cur.execute(f"""
            SELECT COUNT(*) AS total
            {base_from}
        """, params)
        total_registros = cur.fetchone()["total"]

        total_paginas = (total_registros + per_page - 1) // per_page

        if total_paginas > 0 and page > total_paginas:
            page = total_paginas
            offset = (page - 1) * per_page

        cur.execute(f"""
            SELECT
                r.id,
                r.apoiador_id,
                r.id_reconhecido,
                r.data_reconhecimento,
                r.reconhecimento,
                r.criado_por,
                u1.nome AS nome_apoiador,
                u2.nome AS nome_reconhecido
            {base_from}
            ORDER BY {coluna_sort} {direcao}, r.id DESC
            LIMIT %s OFFSET %s
        """, params + [per_page, offset])
        reconhecimentos = cur.fetchall()

        if perfil in ["administrador", "avancado"]:
            cur.execute("""
                SELECT id, nome
                FROM usuarios
                WHERE ativo = 1
                ORDER BY nome ASC
            """)
        else:
            cur.execute("""
                SELECT id, nome
                FROM usuarios
                WHERE ativo = 1
                  AND centro_custos_id = %s
                ORDER BY nome ASC
            """, (centro_custo_id_logado,))

        usuarios = cur.fetchall()

        filtros = {
            "apoiador_id": apoiador_id,
            "id_reconhecido": id_reconhecido,
            "data_inicio": data_inicio,
            "data_fim": data_fim,
            "sort": sort,
            "order": order
        }

        cur.close()
        conn.close()

        return render_template(
            "listar_reconhecimento.html",
            reconhecimentos=reconhecimentos,
            usuarios=usuarios,
            filtros=filtros,
            page=page,
            per_page=per_page,
            total_registros=total_registros,
            total_paginas=total_paginas
        )

    @blueprint.route("/editar_reconhecimento/<int:id>", methods=["GET", "POST"])
    @login_required
    @module_required('acesso_gestao_pessoas')
    def editar_reconhecimento(id):
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        usuario_id = session.get("usuario_id")
        perfil = session.get("perfil")
        centro_custo_id = session.get("centro_custos_id")

        if (
            not usuario_id
            or (
                perfil not in ['administrador', 'avancado']
                and not centro_custo_id
            )
        ):
            cur.close()
            conn.close()
            flash("Usuário logado inválido.", "danger")
            return redirect(url_for("main.dashboard"))

        cur.execute("""
            SELECT *
            FROM reconhecimentos
            WHERE id = %s
        """, (id,))
        reconhecimento = cur.fetchone()

        if not reconhecimento:
            cur.close()
            conn.close()
            flash("Reconhecimento não encontrado.", "danger")
            return redirect(url_for("main.listar_reconhecimento"))

        if perfil not in ["administrador", "avancado"]:
            if perfil == "intermediario":
                cur.execute("""
                    SELECT 1
                    FROM usuarios u1
                    JOIN usuarios u2 ON u2.id = %s
                    WHERE u1.id = %s
                      AND u1.centro_custos_id = %s
                      AND u2.centro_custos_id = %s
                """, (
                    reconhecimento["id_reconhecido"],
                    reconhecimento["apoiador_id"],
                    centro_custo_id,
                    centro_custo_id
                ))

                if not cur.fetchone():
                    cur.close()
                    conn.close()
                    flash("Você não tem permissão para editar este reconhecimento.", "danger")
                    return redirect(url_for("main.listar_reconhecimento"))

            elif perfil == "basico":
                if reconhecimento.get("criado_por") != usuario_id:
                    cur.close()
                    conn.close()
                    flash("Você não tem permissão para editar este reconhecimento.", "danger")
                    return redirect(url_for("main.listar_reconhecimento"))

        if request.method == "POST":
            apoiador_id = request.form.get("apoiador_id")
            id_reconhecido = request.form.get("id_reconhecido")
            data_reconhecimento = request.form.get("data_reconhecimento")
            reconhecimento_texto = request.form.get("reconhecimento")

            if not (apoiador_id and id_reconhecido and data_reconhecimento and reconhecimento_texto):
                flash("Preencha todos os campos obrigatórios.", "warning")
                return redirect(url_for("main.editar_reconhecimento", id=id))

            if apoiador_id == id_reconhecido:
                flash("O apoiador e o reconhecido não podem ser a mesma pessoa.", "warning")
                return redirect(url_for("main.editar_reconhecimento", id=id))

            if perfil in ["administrador", "avancado"]:
                cur.execute("""
                    SELECT id
                    FROM usuarios
                    WHERE id IN (%s, %s)
                      AND ativo = 1
                """, (apoiador_id, id_reconhecido))
            else:
                cur.execute("""
                    SELECT id
                    FROM usuarios
                    WHERE id IN (%s, %s)
                      AND ativo = 1
                      AND centro_custos_id = %s
                """, (apoiador_id, id_reconhecido, centro_custo_id))

            usuarios_validos = cur.fetchall()

            if len(usuarios_validos) != 2:
                flash("Apoiador e reconhecido devem pertencer ao seu escopo.", "warning")
                return redirect(url_for("main.editar_reconhecimento", id=id))

            cur.execute("""
                UPDATE reconhecimentos
                SET apoiador_id = %s,
                    id_reconhecido = %s,
                    data_reconhecimento = %s,
                    reconhecimento = %s
                WHERE id = %s
            """, (
                apoiador_id,
                id_reconhecido,
                data_reconhecimento,
                reconhecimento_texto,
                id
            ))

            conn.commit()

            cur.close()
            conn.close()

            flash("Reconhecimento atualizado com sucesso!", "success")
            return redirect(url_for("main.listar_reconhecimento"))

        if perfil in ["administrador", "avancado"]:
            cur.execute("""
                SELECT id, nome, matricula
                FROM usuarios
                WHERE ativo = 1
                ORDER BY nome
            """)
        else:
            cur.execute("""
                SELECT id, nome, matricula
                FROM usuarios
                WHERE ativo = 1
                  AND centro_custos_id = %s
                ORDER BY nome
            """, (centro_custo_id,))

        usuarios = cur.fetchall()

        if reconhecimento.get("data_reconhecimento") and hasattr(reconhecimento["data_reconhecimento"], "strftime"):
            reconhecimento["data_reconhecimento"] = reconhecimento["data_reconhecimento"].strftime("%Y-%m-%d")

        cur.close()
        conn.close()

        return render_template(
            "editar_reconhecimento.html",
            reconhecimento=reconhecimento,
            usuarios=usuarios
        )

    @blueprint.route("/excluir_reconhecimento/<int:id>", methods=["POST"])
    @login_required
    @module_required('acesso_gestao_pessoas')
    def excluir_reconhecimento(id):
        conn = get_db_connection()
        cur = conn.cursor(dictionary=True)

        usuario_id = session.get("usuario_id")
        perfil = session.get("perfil")
        centro_custo_id = session.get("centro_custos_id")

        cur.execute("""
            SELECT
                r.id,
                r.criado_por,
                u1.centro_custos_id AS centro_custo_apoiador,
                u2.centro_custos_id AS centro_custo_reconhecido
            FROM reconhecimentos r
            JOIN usuarios u1 ON u1.id = r.apoiador_id
            JOIN usuarios u2 ON u2.id = r.id_reconhecido
            WHERE r.id = %s
        """, (id,))
        reconhecimento = cur.fetchone()

        if not reconhecimento:
            cur.close()
            conn.close()
            flash("Reconhecimento não encontrado.", "danger")
            return redirect(url_for("main.listar_reconhecimento"))

        if perfil not in ["administrador", "avancado"]:
            if perfil == "intermediario":
                if (
                    reconhecimento.get("centro_custo_apoiador") != centro_custo_id or
                    reconhecimento.get("centro_custo_reconhecido") != centro_custo_id
                ):
                    cur.close()
                    conn.close()
                    flash("Você não tem permissão para excluir este reconhecimento.", "danger")
                    return redirect(url_for("main.listar_reconhecimento"))

            elif perfil == "basico":
                if reconhecimento.get("criado_por") != usuario_id:
                    cur.close()
                    conn.close()
                    flash("Você não tem permissão para excluir este reconhecimento.", "danger")
                    return redirect(url_for("main.listar_reconhecimento"))

        cur.execute("DELETE FROM reconhecimentos WHERE id = %s", (id,))
        conn.commit()

        cur.close()
        conn.close()

        flash("Reconhecimento excluído com sucesso!", "success")
        return redirect(url_for("main.listar_reconhecimento"))

