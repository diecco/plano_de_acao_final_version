from flask import flash, redirect, render_template, request

from app.decorators import admin_required, login_required
from app.utils.db import get_db_connection


def register_origens_routes(blueprint):
    @blueprint.route('/origens', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def origens():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == 'POST':
            descricao = (request.form.get('descricao') or '').strip()
            centro_custos_id = request.form.get('centro_custos_id')

            if not descricao:
                flash('Informe a descrição da origem.', 'danger')
                conn.close()
                return redirect('/origens')
            if not centro_custos_id:
                flash('Selecione o centro de custo da origem.', 'danger')
                conn.close()
                return redirect('/origens')

            try:
                cursor.execute("""
                    SELECT id FROM centros_custos
                    WHERE id = %s AND ativo = 1
                """, (centro_custos_id,))
                centro = cursor.fetchone()
                if not centro:
                    flash('Centro de custo inválido ou inativo.', 'danger')
                    conn.close()
                    return redirect('/origens')

                cursor.execute("""
                    INSERT INTO origens (descricao, nome, centro_custos_id, ativo)
                    VALUES (%s, %s, %s, 1)
                """, (descricao, descricao, centro_custos_id))
                conn.commit()
                flash('Origem cadastrada com sucesso!', 'success')
            except Exception as exc:
                msg = str(exc)
                if '1062' in msg or 'Duplicate entry' in msg:
                    flash('Já existe uma origem com esse nome/descrição.', 'warning')
                else:
                    flash(f'Erro ao salvar origem: {exc}', 'danger')
                conn.rollback()

        cursor.execute("""
            SELECT o.id, o.descricao, o.nome, o.ativo, o.centro_custos_id,
                   cc.codigo AS codigo_cc, cc.descricao AS descricao_cc
            FROM origens o
            LEFT JOIN centros_custos cc ON o.centro_custos_id = cc.id
            ORDER BY o.id DESC
        """)
        registros = cursor.fetchall()
        cursor.execute("""
            SELECT id, codigo, descricao FROM centros_custos
            WHERE ativo = 1 ORDER BY codigo, descricao
        """)
        centros_custos = cursor.fetchall()
        conn.close()
        return render_template(
            'origens.html',
            origens=registros,
            centros_custos=centros_custos,
        )

    @blueprint.route('/editar_origem/<int:id>', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def editar_origem(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == 'POST':
            nova_descricao = (request.form.get('descricao') or '').strip()
            centro_custos_id = request.form.get('centro_custos_id')
            if not nova_descricao:
                flash('Informe a descrição.', 'danger')
                conn.close()
                return redirect(f'/editar_origem/{id}')
            if not centro_custos_id:
                flash('Selecione o centro de custo da origem.', 'danger')
                conn.close()
                return redirect(f'/editar_origem/{id}')

            try:
                cursor.execute("""
                    SELECT id FROM centros_custos
                    WHERE id = %s AND ativo = 1
                """, (centro_custos_id,))
                centro = cursor.fetchone()
                if not centro:
                    flash('Centro de custo inválido ou inativo.', 'danger')
                    conn.close()
                    return redirect(f'/editar_origem/{id}')

                cursor.execute("""
                    UPDATE origens
                    SET descricao = %s, nome = %s, centro_custos_id = %s
                    WHERE id = %s
                """, (nova_descricao, nova_descricao, centro_custos_id, id))
                conn.commit()
                flash('Origem atualizada com sucesso!', 'success')
                conn.close()
                return redirect('/origens')
            except Exception as exc:
                msg = str(exc)
                if '1062' in msg or 'Duplicate entry' in msg:
                    flash('Já existe outra origem com esse nome/descrição.', 'warning')
                else:
                    flash(f'Erro ao atualizar origem: {exc}', 'danger')
                conn.rollback()
                conn.close()
                return redirect(f'/editar_origem/{id}')

        cursor.execute("SELECT * FROM origens WHERE id = %s", (id,))
        origem = cursor.fetchone()
        if not origem:
            conn.close()
            flash('Origem não encontrada.')
            return redirect('/origens')

        cursor.execute("""
            SELECT id, codigo, descricao FROM centros_custos
            WHERE ativo = 1 ORDER BY codigo, descricao
        """)
        centros_custos = cursor.fetchall()
        conn.close()
        return render_template(
            'editar_origens.html',
            origem=origem,
            centros_custos=centros_custos,
        )

    @blueprint.route('/desabilitar_origem/<int:id>', methods=['POST'])
    @login_required
    @admin_required
    def desabilitar_origem(id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE origens SET ativo = FALSE WHERE id = %s", (id,))
        conn.commit()
        conn.close()
        flash('Origem desabilitada com sucesso!', 'success')
        return redirect('/origens')

    @blueprint.route('/habilitar_origem/<int:id>', methods=['POST'])
    @login_required
    @admin_required
    def habilitar_origem(id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE origens SET ativo = TRUE WHERE id = %s", (id,))
        conn.commit()
        conn.close()
        flash('Origem habilitada com sucesso!', 'success')
        return redirect('/origens')

