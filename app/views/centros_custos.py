from flask import flash, redirect, render_template, request

from app.decorators import admin_required, login_required
from app.utils.db import get_db_connection


def register_centros_custos_routes(blueprint):
    @blueprint.route('/centros_custos', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def centros_custos():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == 'POST':
            codigo = request.form['codigo']
            descricao = request.form['descricao']
            superintendencia_id = request.form['superintendencia_id']

            cursor.execute("""
                INSERT INTO centros_custos (codigo, descricao, superintendencia_id)
                VALUES (%s, %s, %s)
            """, (codigo, descricao, superintendencia_id))

            conn.commit()
            flash('Centro de Custo cadastrado com sucesso!')

        cursor.execute("""
            SELECT cc.*, s.nome AS nome_superintendencia
            FROM centros_custos cc
            LEFT JOIN superintendencias s ON cc.superintendencia_id = s.id
        """)
        centros = cursor.fetchall()

        cursor.execute("SELECT * FROM superintendencias WHERE ativo = TRUE")
        superintendencias = cursor.fetchall()

        conn.close()
        return render_template(
            'centros_custos.html',
            centros=centros,
            superintendencias=superintendencias,
        )

    @blueprint.route('/editar_centro/<int:id>', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def editar_centro(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == 'POST':
            novo_codigo = request.form['codigo']
            nova_descricao = request.form['descricao']
            nova_superintendencia_id = request.form['superintendencia_id']
            cursor.execute("""
                UPDATE centros_custos
                SET codigo = %s, descricao = %s, superintendencia_id = %s
                WHERE id = %s
            """, (novo_codigo, nova_descricao, nova_superintendencia_id, id))
            conn.commit()
            conn.close()
            flash('Centro de Custo atualizado com sucesso!')
            return redirect('/centros_custos')

        cursor.execute("SELECT * FROM centros_custos WHERE id = %s", (id,))
        centro = cursor.fetchone()
        cursor.execute("SELECT * FROM superintendencias WHERE ativo = TRUE")
        superintendencias = cursor.fetchall()
        conn.close()

        return render_template(
            'editar_centro.html',
            centro=centro,
            superintendencias=superintendencias,
        )

    @blueprint.route('/habilitar_centrocusto/<int:id>', methods=['POST'])
    @login_required
    @admin_required
    def habilitar_centrocusto(id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE centros_custos SET ativo = TRUE WHERE id = %s", (id,))
        conn.commit()
        conn.close()
        flash('Centro de Custos habilitado com sucesso!', 'sucess')
        return redirect('/centros_custos')

    @blueprint.route('/desabilitar_centrocusto/<int:id>', methods=['POST'])
    @login_required
    @admin_required
    def desabilitar_centrocusto(id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE centros_custos SET ativo = FALSE WHERE id = %s", (id,))
        conn.commit()
        conn.close()
        flash('Centro de Custos desabilitado com sucesso!', 'success')
        return redirect('/centros_custos')

