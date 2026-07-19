from flask import flash, redirect, render_template, request, url_for

from app.decorators import admin_required, login_required
from app.utils.db import get_db_connection


def register_funcoes_routes(blueprint):
    @blueprint.route('/funcoes', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def funcoes():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if request.method == 'POST':
            funcao_id = request.form.get('id')
            nome = (request.form.get('nome') or '').strip()
            if not nome:
                flash('Informe o nome da função.', 'danger')
                conn.close()
                return redirect(url_for('main.funcoes'))
            try:
                if funcao_id:
                    cursor.execute(
                        'SELECT id FROM funcoes WHERE nome = %s AND id <> %s',
                        (nome, funcao_id),
                    )
                    if cursor.fetchone():
                        flash('Já existe outra função com esse nome.', 'warning')
                        conn.close()
                        return redirect(url_for('main.funcoes', editar_id=funcao_id))
                    cursor.execute('UPDATE funcoes SET nome = %s WHERE id = %s', (nome, funcao_id))
                    flash('Função atualizada com sucesso!', 'success')
                else:
                    cursor.execute('SELECT id FROM funcoes WHERE nome = %s', (nome,))
                    if cursor.fetchone():
                        flash('Já existe uma função com esse nome.', 'warning')
                        conn.close()
                        return redirect(url_for('main.funcoes'))
                    cursor.execute('INSERT INTO funcoes (nome, ativo) VALUES (%s, 1)', (nome,))
                    flash('Função cadastrada com sucesso!', 'success')
                conn.commit()
            except Exception as exc:
                conn.rollback()
                flash(f'Erro ao salvar função: {exc}', 'danger')
            finally:
                conn.close()
            return redirect(url_for('main.funcoes'))

        editar_id = request.args.get('editar_id')
        funcao_edicao = None
        if editar_id:
            cursor.execute('SELECT * FROM funcoes WHERE id = %s', (editar_id,))
            funcao_edicao = cursor.fetchone()
        cursor.execute('SELECT * FROM funcoes ORDER BY nome ASC')
        registros = cursor.fetchall()
        conn.close()
        return render_template('funcoes.html', funcoes=registros, funcao_edicao=funcao_edicao)

    @blueprint.route('/desativar_funcao/<int:id>', methods=['POST'])
    @login_required
    @admin_required
    def desativar_funcao(id):
        return _alterar_status_funcao(id, 0, 'desativada', 'desativar')

    @blueprint.route('/reativar_funcao/<int:id>', methods=['POST'])
    @login_required
    @admin_required
    def reativar_funcao(id):
        return _alterar_status_funcao(id, 1, 'reativada', 'reativar')


def _alterar_status_funcao(id, ativo, resultado, operacao):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute('UPDATE funcoes SET ativo = %s WHERE id = %s', (ativo, id))
        conn.commit()
        flash(f'Função {resultado} com sucesso!', 'success')
    except Exception as exc:
        conn.rollback()
        flash(f'Erro ao {operacao} função: {exc}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('main.funcoes'))

