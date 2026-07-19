from flask import flash, redirect, render_template, request, url_for

from app.decorators import admin_required, login_required
from app.utils.db import get_db_connection


def register_setores_routes(blueprint):
    @blueprint.route('/setores', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def setores():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if request.method == 'POST':
            setor_id = request.form.get('id')
            nome = (request.form.get('nome') or '').strip()
            if not nome:
                flash('Informe o nome do setor.', 'danger')
                conn.close()
                return redirect(url_for('main.setores'))
            try:
                if setor_id:
                    cursor.execute(
                        'SELECT id FROM setores WHERE nome = %s AND id <> %s',
                        (nome, setor_id),
                    )
                    if cursor.fetchone():
                        flash('Já existe outro setor com esse nome.', 'warning')
                        conn.close()
                        return redirect(url_for('main.setores', editar_id=setor_id))
                    cursor.execute('UPDATE setores SET nome = %s WHERE id = %s', (nome, setor_id))
                    flash('Setor atualizado com sucesso!', 'success')
                else:
                    cursor.execute('SELECT id FROM setores WHERE nome = %s', (nome,))
                    if cursor.fetchone():
                        flash('Já existe um setor com esse nome.', 'warning')
                        conn.close()
                        return redirect(url_for('main.setores'))
                    cursor.execute('INSERT INTO setores (nome, ativo) VALUES (%s, 1)', (nome,))
                    flash('Setor cadastrado com sucesso!', 'success')
                conn.commit()
            except Exception as exc:
                conn.rollback()
                flash(f'Erro ao salvar setor: {exc}', 'danger')
            finally:
                conn.close()
            return redirect(url_for('main.setores'))

        editar_id = request.args.get('editar_id')
        setor_edicao = None
        if editar_id:
            cursor.execute('SELECT * FROM setores WHERE id = %s', (editar_id,))
            setor_edicao = cursor.fetchone()
        cursor.execute('SELECT * FROM setores ORDER BY nome ASC')
        registros = cursor.fetchall()
        conn.close()
        return render_template('setores.html', setores=registros, setor_edicao=setor_edicao)

    @blueprint.route('/desativar_setor/<int:id>', methods=['POST'])
    @login_required
    @admin_required
    def desativar_setor(id):
        return _alterar_status_setor(id, 0, 'desativado', 'desativar')

    @blueprint.route('/reativar_setor/<int:id>', methods=['POST'])
    @login_required
    @admin_required
    def reativar_setor(id):
        return _alterar_status_setor(id, 1, 'reativado', 'reativar')


def _alterar_status_setor(id, ativo, resultado, operacao):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute('UPDATE setores SET ativo = %s WHERE id = %s', (ativo, id))
        conn.commit()
        flash(f'Setor {resultado} com sucesso!', 'success')
    except Exception as exc:
        conn.rollback()
        flash(f'Erro ao {operacao} setor: {exc}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('main.setores'))
