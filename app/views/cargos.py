from flask import flash, redirect, render_template, request, url_for

from app.decorators import admin_required, login_required
from app.utils.db import get_db_connection


def register_cargos_routes(blueprint):
    @blueprint.route('/cargos', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def cargos():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if request.method == 'POST':
            cargo_id = request.form.get('id')
            nome = (request.form.get('nome') or '').strip()
            if not nome:
                flash('Informe o nome do cargo.', 'danger')
                conn.close()
                return redirect(url_for('main.cargos'))
            try:
                if cargo_id:
                    cursor.execute(
                        'SELECT id FROM cargos WHERE nome = %s AND id <> %s',
                        (nome, cargo_id),
                    )
                    if cursor.fetchone():
                        flash('Já existe outro cargo com esse nome.', 'warning')
                        conn.close()
                        return redirect(url_for('main.cargos', editar_id=cargo_id))
                    cursor.execute('UPDATE cargos SET nome = %s WHERE id = %s', (nome, cargo_id))
                    flash('Cargo atualizado com sucesso!', 'success')
                else:
                    cursor.execute('SELECT id FROM cargos WHERE nome = %s', (nome,))
                    if cursor.fetchone():
                        flash('Já existe um cargo com esse nome.', 'warning')
                        conn.close()
                        return redirect(url_for('main.cargos'))
                    cursor.execute('INSERT INTO cargos (nome, ativo) VALUES (%s, 1)', (nome,))
                    flash('Cargo cadastrado com sucesso!', 'success')
                conn.commit()
            except Exception as exc:
                conn.rollback()
                flash(f'Erro ao salvar cargo: {exc}', 'danger')
            finally:
                conn.close()
            return redirect(url_for('main.cargos'))

        editar_id = request.args.get('editar_id')
        cargo_edicao = None
        if editar_id:
            cursor.execute('SELECT * FROM cargos WHERE id = %s', (editar_id,))
            cargo_edicao = cursor.fetchone()
        cursor.execute('SELECT * FROM cargos ORDER BY nome ASC')
        registros = cursor.fetchall()
        conn.close()
        return render_template('cargos.html', cargos=registros, cargo_edicao=cargo_edicao)

    @blueprint.route('/desativar_cargo/<int:id>', methods=['POST'])
    @login_required
    @admin_required
    def desativar_cargo(id):
        return _alterar_status_cargo(id, 0, 'desativado', 'desativar')

    @blueprint.route('/reativar_cargo/<int:id>', methods=['POST'])
    @login_required
    @admin_required
    def reativar_cargo(id):
        return _alterar_status_cargo(id, 1, 'reativado', 'reativar')


def _alterar_status_cargo(id, ativo, resultado, operacao):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute('UPDATE cargos SET ativo = %s WHERE id = %s', (ativo, id))
        conn.commit()
        flash(f'Cargo {resultado} com sucesso!', 'success')
    except Exception as exc:
        conn.rollback()
        flash(f'Erro ao {operacao} cargo: {exc}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('main.cargos'))

