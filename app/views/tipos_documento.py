from flask import flash, redirect, render_template, request, url_for

from app.decorators import admin_required, login_required
from app.utils.db import get_db_connection


def register_tipos_documento_routes(blueprint):
    @blueprint.route('/tipos_documento', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def tipos_documento():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        if request.method == 'POST':
            tipo_id = request.form.get('id')
            sigla = request.form.get('sigla', '').strip().upper()
            descricao = request.form.get('descricao', '').strip()
            nivel = request.form.get('nivel')
            if not sigla or not descricao or not nivel:
                flash('Preencha todos os campos obrigatórios.', 'danger')
                conn.close()
                return redirect(url_for('main.tipos_documento'))
            try:
                if tipo_id:
                    cursor.execute(
                        'SELECT id FROM tipos_documento WHERE sigla = %s AND id <> %s',
                        (sigla, tipo_id),
                    )
                    if cursor.fetchone():
                        flash('Já existe outro tipo de documento com essa sigla.', 'warning')
                        conn.close()
                        return redirect(url_for('main.tipos_documento', editar_id=tipo_id))
                    cursor.execute("""
                        UPDATE tipos_documento
                        SET sigla = %s, descricao = %s, nivel = %s
                        WHERE id = %s
                    """, (sigla, descricao, nivel, tipo_id))
                    flash('Tipo de documento atualizado com sucesso!', 'success')
                else:
                    cursor.execute('SELECT id FROM tipos_documento WHERE sigla = %s', (sigla,))
                    if cursor.fetchone():
                        flash('Já existe um tipo de documento com essa sigla.', 'warning')
                        conn.close()
                        return redirect(url_for('main.tipos_documento'))
                    cursor.execute("""
                        INSERT INTO tipos_documento (sigla, descricao, nivel)
                        VALUES (%s, %s, %s)
                    """, (sigla, descricao, nivel))
                    flash('Tipo de documento cadastrado com sucesso!', 'success')
                conn.commit()
            except Exception as exc:
                conn.rollback()
                flash(f'Erro ao salvar tipo de documento: {exc}', 'danger')
            finally:
                conn.close()
            return redirect(url_for('main.tipos_documento'))

        editar_id = request.args.get('editar_id', '')
        filtro_sigla = request.args.get('filtro_sigla', '').strip()
        filtro_descricao = request.args.get('filtro_descricao', '').strip()
        sort = request.args.get('sort', 'nivel')
        order = request.args.get('order', 'asc')
        colunas = {'id': 'id', 'sigla': 'sigla', 'descricao': 'descricao', 'nivel': 'nivel'}
        coluna_sort = colunas.get(sort, 'nivel')
        direcao = 'ASC' if order == 'asc' else 'DESC'
        query = 'SELECT * FROM tipos_documento WHERE 1=1'
        params = []
        if filtro_sigla:
            query += ' AND sigla LIKE %s'
            params.append(f'%{filtro_sigla}%')
        if filtro_descricao:
            query += ' AND descricao LIKE %s'
            params.append(f'%{filtro_descricao}%')
        query += f' ORDER BY {coluna_sort} {direcao}, id ASC'
        cursor.execute(query, params)
        registros = cursor.fetchall()
        tipo_edicao = None
        if editar_id:
            cursor.execute('SELECT * FROM tipos_documento WHERE id = %s', (editar_id,))
            tipo_edicao = cursor.fetchone()
        filtros = {
            'filtro_sigla': filtro_sigla,
            'filtro_descricao': filtro_descricao,
            'sort': sort,
            'order': order,
        }
        conn.close()
        return render_template(
            'tipos_documento.html',
            tipos_documento=registros,
            tipo_edicao=tipo_edicao,
            filtros=filtros,
        )

    @blueprint.route('/desativar_tipo_documento/<int:id>', methods=['POST'])
    @login_required
    @admin_required
    def desativar_tipo_documento(id):
        return _alterar_status(id, 0, 'desativado', 'desativar')

    @blueprint.route('/reativar_tipo_documento/<int:id>', methods=['POST'])
    @login_required
    @admin_required
    def reativar_tipo_documento(id):
        return _alterar_status(id, 1, 'reativado', 'reativar')


def _alterar_status(id, ativo, resultado, operacao):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute('UPDATE tipos_documento SET ativo = %s WHERE id = %s', (ativo, id))
        conn.commit()
        flash(f'Tipo de documento {resultado} com sucesso!', 'success')
    except Exception as exc:
        conn.rollback()
        flash(f'Erro ao {operacao} tipo de documento: {exc}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('main.tipos_documento'))

