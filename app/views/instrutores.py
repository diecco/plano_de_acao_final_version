from flask import flash, redirect, render_template, request, url_for

from app.decorators import admin_required, login_required
from app.utils.db import get_db_connection


def register_instrutores_routes(blueprint):
    @blueprint.route('/instrutores', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def instrutores():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if request.method == 'POST':
            nome, empresa, email, telefone, observacoes = _dados_formulario()
            if not nome:
                flash('Informe o nome do instrutor.', 'danger')
                conn.close()
                return redirect(url_for('main.instrutores'))
            try:
                cursor.execute("""
                    SELECT id FROM instrutores_externos
                    WHERE nome = %s AND IFNULL(email, '') = IFNULL(%s, '')
                """, (nome, email))
                if cursor.fetchone():
                    flash('Já existe um instrutor externo cadastrado com esse nome/e-mail.', 'warning')
                    conn.close()
                    return redirect(url_for('main.instrutores'))
                cursor.execute("""
                    INSERT INTO instrutores_externos
                        (nome, empresa, email, telefone, observacoes, ativo)
                    VALUES (%s, %s, %s, %s, %s, 1)
                """, (nome, empresa, email, telefone, observacoes))
                conn.commit()
                flash('Instrutor externo cadastrado com sucesso!', 'success')
            except Exception as exc:
                conn.rollback()
                flash(f'Erro ao cadastrar instrutor: {exc}', 'danger')
            finally:
                conn.close()
            return redirect(url_for('main.instrutores'))

        cursor.execute('SELECT * FROM instrutores_externos ORDER BY nome ASC')
        registros = cursor.fetchall()
        conn.close()
        return render_template('instrutores.html', instrutores=registros)

    @blueprint.route('/editar_instrutor/<int:id>', methods=['POST'])
    @login_required
    @admin_required
    def editar_instrutor(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        nome, empresa, email, telefone, observacoes = _dados_formulario()
        if not nome:
            flash('Informe o nome do instrutor.', 'danger')
            conn.close()
            return redirect(url_for('main.instrutores'))
        try:
            cursor.execute("""
                SELECT id FROM instrutores_externos
                WHERE nome = %s AND IFNULL(email, '') = IFNULL(%s, '') AND id <> %s
            """, (nome, email, id))
            if cursor.fetchone():
                flash('Já existe outro instrutor externo cadastrado com esse nome/e-mail.', 'warning')
                conn.close()
                return redirect(url_for('main.instrutores'))
            cursor.execute("""
                UPDATE instrutores_externos
                SET nome = %s, empresa = %s, email = %s,
                    telefone = %s, observacoes = %s
                WHERE id = %s
            """, (nome, empresa, email, telefone, observacoes, id))
            conn.commit()
            flash('Instrutor externo atualizado com sucesso!', 'success')
        except Exception as exc:
            conn.rollback()
            flash(f'Erro ao atualizar instrutor: {exc}', 'danger')
        finally:
            conn.close()
        return redirect(url_for('main.instrutores'))

    @blueprint.route('/alternar_instrutor/<int:id>', methods=['POST'])
    @login_required
    @admin_required
    def alternar_instrutor(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute('SELECT ativo FROM instrutores_externos WHERE id = %s', (id,))
            instrutor = cursor.fetchone()
            if not instrutor:
                conn.close()
                flash('Instrutor não encontrado.', 'warning')
                return redirect(url_for('main.instrutores'))
            novo_status = 0 if instrutor['ativo'] else 1
            cursor.execute(
                'UPDATE instrutores_externos SET ativo = %s WHERE id = %s',
                (novo_status, id),
            )
            conn.commit()
            if novo_status == 1:
                flash('Instrutor externo ativado com sucesso!', 'success')
            else:
                flash('Instrutor externo inativado com sucesso!', 'success')
        except Exception as exc:
            conn.rollback()
            flash(f'Erro ao alterar status do instrutor: {exc}', 'danger')
        finally:
            conn.close()
        return redirect(url_for('main.instrutores'))


def _dados_formulario():
    return (
        (request.form.get('nome') or '').strip(),
        (request.form.get('empresa') or '').strip() or None,
        (request.form.get('email') or '').strip() or None,
        (request.form.get('telefone') or '').strip() or None,
        (request.form.get('observacoes') or '').strip() or None,
    )

