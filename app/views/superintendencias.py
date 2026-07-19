from flask import flash, redirect, render_template, request

from app.decorators import admin_required, login_required
from app.utils.db import get_db_connection


def register_superintendencias_routes(blueprint):
    @blueprint.route('/superintendencias', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def superintendencias():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == 'POST':
            nome = request.form['nome']
            cursor.execute("INSERT INTO superintendencias (nome) VALUES (%s)", (nome,))
            conn.commit()
            flash('Superintendência cadastrada com sucesso!')

        cursor.execute("SELECT * FROM superintendencias")
        registros = cursor.fetchall()
        conn.close()
        return render_template('superintendencias.html', superintendencias=registros)

    @blueprint.route('/editar_superintendencia/<int:id>', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def editar_superintendencia(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == 'POST':
            novo_nome = request.form['nome']
            cursor.execute(
                "UPDATE superintendencias SET nome = %s WHERE id = %s",
                (novo_nome, id),
            )
            conn.commit()
            flash('Superintendência atualizada com sucesso!')
            conn.close()
            return redirect('/superintendencias')

        cursor.execute("SELECT * FROM superintendencias WHERE id = %s", (id,))
        superintendencia = cursor.fetchone()
        conn.close()

        if not superintendencia:
            flash('Superintendência não encontrada.')
            return redirect('/superintendencias')

        return render_template(
            'editar_superintendencia.html',
            superintendencia=superintendencia,
        )

    @blueprint.route('/habilitar_superintendencia/<int:id>', methods=['POST'])
    @login_required
    @admin_required
    def habilitar_superintendencia(id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE superintendencias SET ativo = TRUE WHERE id = %s", (id,))
        conn.commit()
        conn.close()
        flash('Superintendência habilitada com sucesso!', 'sucess')
        return redirect('/superintendencias')

    @blueprint.route('/desabilitar_superintendencia/<int:id>', methods=['POST'])
    @login_required
    @admin_required
    def desabilitar_superintendencia(id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE superintendencias SET ativo = FALSE WHERE id = %s", (id,))
        conn.commit()
        conn.close()
        flash('Superintendencia desabilitada com sucesso!', 'success')
        return redirect('/superintendencias')

