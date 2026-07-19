from flask import flash, redirect, render_template, request, url_for

from app.decorators import login_required, module_required
from app.utils.db import get_db_connection


def register_pcpm_checklist_routes(blueprint):
    @blueprint.route('/pcpm_checklist_modelos', methods=['GET'])
    @login_required
    @module_required('acesso_pcpm')
    def pcpm_checklist_modelos():


        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.args.get('limpar'):
            conn.close()
            return redirect(url_for('main.pcpm_checklist_modelos'))

        filtros = {
            'tipo_equipamento_id': request.args.get('tipo_equipamento_id') or '',
            'nome': (request.args.get('nome') or '').strip()
        }

        cursor.execute("""
            SELECT
                id,
                tag,
                nome
            FROM pcpm_tipos_equipamento
            WHERE ativo = 1
            ORDER BY tag, nome
        """)
        tipos_equipamento = cursor.fetchall()

        where = []
        params = []

        if filtros['tipo_equipamento_id']:
            where.append("m.tipo_equipamento_id = %s")
            params.append(filtros['tipo_equipamento_id'])

        if filtros['nome']:
            where.append("m.nome LIKE %s")
            params.append(f"%{filtros['nome']}%")

        where_sql = ""
        if where:
            where_sql = "WHERE " + " AND ".join(where)

        cursor.execute(f"""
            SELECT
                m.id,
                m.tipo_equipamento_id,
                m.nome,
                m.ativo,
                te.tag AS tipo_tag,
                te.nome AS tipo_nome
            FROM pcpm_checklist_modelos m
            JOIN pcpm_tipos_equipamento te
                ON te.id = m.tipo_equipamento_id
            {where_sql}
            ORDER BY te.nome ASC, m.nome ASC
        """, params)

        modelos = cursor.fetchall()

        conn.close()

        return render_template(
            'pcpm_checklist_modelos.html',
            modelos=modelos,
            tipos_equipamento=tipos_equipamento,
            filtros=filtros
        )


    # ==========================================================
    # CADASTRAR MODELO CHECKLIST
    # ==========================================================

    @blueprint.route('/cadastrar_pcpm_checklist_modelo', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def cadastrar_pcpm_checklist_modelo():


        tipo_equipamento_id = request.form.get('tipo_equipamento_id')
        nome = (request.form.get('nome') or '').strip()

        if not tipo_equipamento_id:
            flash('Selecione o tipo de equipamento.', 'warning')
            return redirect(url_for('main.pcpm_checklist_modelos'))

        if not nome:
            flash('Informe o nome do modelo.', 'warning')
            return redirect(url_for('main.pcpm_checklist_modelos'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:

            cursor.execute("""
                SELECT id
                FROM pcpm_tipos_equipamento
                WHERE id = %s
                  AND ativo = 1
            """, (tipo_equipamento_id,))

            tipo = cursor.fetchone()

            if not tipo:
                flash('Tipo de equipamento inválido.', 'warning')
                conn.close()
                return redirect(url_for('main.pcpm_checklist_modelos'))

            cursor.execute("""
                SELECT id
                FROM pcpm_checklist_modelos
                WHERE tipo_equipamento_id = %s
                  AND UPPER(nome) = UPPER(%s)
            """, (tipo_equipamento_id, nome))

            existente = cursor.fetchone()

            if existente:
                flash('Já existe um modelo com este nome para o tipo de equipamento selecionado.', 'warning')
                conn.close()
                return redirect(url_for('main.pcpm_checklist_modelos'))

            cursor.execute("""
                INSERT INTO pcpm_checklist_modelos (
                    tipo_equipamento_id,
                    nome,
                    ativo
                )
                VALUES (%s, %s, 1)
            """, (
                tipo_equipamento_id,
                nome
            ))

            conn.commit()

            flash('Modelo de checklist cadastrado com sucesso!', 'success')

        except Exception as e:

            conn.rollback()

            flash(f'Erro ao cadastrar modelo de checklist: {e}', 'danger')

        finally:

            conn.close()

        return redirect(url_for('main.pcpm_checklist_modelos'))


    # ==========================================================
    # EDITAR MODELO CHECKLIST
    # ==========================================================

    @blueprint.route('/editar_pcpm_checklist_modelo/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def editar_pcpm_checklist_modelo(id):


        tipo_equipamento_id = request.form.get('tipo_equipamento_id')
        nome = (request.form.get('nome') or '').strip()

        if not tipo_equipamento_id:
            flash('Selecione o tipo de equipamento.', 'warning')
            return redirect(url_for('main.pcpm_checklist_modelos'))

        if not nome:
            flash('Informe o nome do modelo.', 'warning')
            return redirect(url_for('main.pcpm_checklist_modelos'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:

            cursor.execute("""
                SELECT id
                FROM pcpm_tipos_equipamento
                WHERE id = %s
                  AND ativo = 1
            """, (tipo_equipamento_id,))

            tipo = cursor.fetchone()

            if not tipo:
                flash('Tipo de equipamento inválido.', 'warning')
                conn.close()
                return redirect(url_for('main.pcpm_checklist_modelos'))

            cursor.execute("""
                SELECT id
                FROM pcpm_checklist_modelos
                WHERE tipo_equipamento_id = %s
                  AND UPPER(nome) = UPPER(%s)
                  AND id <> %s
            """, (
                tipo_equipamento_id,
                nome,
                id
            ))

            existente = cursor.fetchone()

            if existente:
                flash('Já existe outro modelo com este nome para o tipo de equipamento selecionado.', 'warning')
                conn.close()
                return redirect(url_for('main.pcpm_checklist_modelos'))

            cursor.execute("""
                UPDATE pcpm_checklist_modelos
                SET tipo_equipamento_id = %s,
                    nome = %s
                WHERE id = %s
            """, (
                tipo_equipamento_id,
                nome,
                id
            ))

            conn.commit()

            flash('Modelo de checklist atualizado com sucesso!', 'success')

        except Exception as e:

            conn.rollback()

            flash(f'Erro ao atualizar modelo de checklist: {e}', 'danger')

        finally:

            conn.close()

        return redirect(url_for('main.pcpm_checklist_modelos'))


    # ==========================================================
    # INATIVAR MODELO CHECKLIST
    # ==========================================================

    @blueprint.route('/inativar_pcpm_checklist_modelo/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def inativar_pcpm_checklist_modelo(id):


        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE pcpm_checklist_modelos
            SET ativo = 0
            WHERE id = %s
        """, (id,))

        conn.commit()
        conn.close()

        flash('Modelo de checklist inativado com sucesso!', 'success')

        return redirect(url_for('main.pcpm_checklist_modelos'))


    # ==========================================================
    # ATIVAR MODELO CHECKLIST
    # ==========================================================

    @blueprint.route('/ativar_pcpm_checklist_modelo/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def ativar_pcpm_checklist_modelo(id):


        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE pcpm_checklist_modelos
            SET ativo = 1
            WHERE id = %s
        """, (id,))

        conn.commit()
        conn.close()

        flash('Modelo de checklist ativado com sucesso!', 'success')

        return redirect(url_for('main.pcpm_checklist_modelos'))

    # ==========================================================
    # PCP-M - ITENS DO CHECKLIST
    # ==========================================================

    @blueprint.route('/pcpm_checklist_itens/<int:modelo_id>', methods=['GET'])
    @login_required
    @module_required('acesso_pcpm')
    def pcpm_checklist_itens(modelo_id):


        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                m.id,
                m.nome,
                m.ativo,
                te.tag AS tipo_tag,
                te.nome AS tipo_nome
            FROM pcpm_checklist_modelos m
            JOIN pcpm_tipos_equipamento te
                ON te.id = m.tipo_equipamento_id
            WHERE m.id = %s
        """, (modelo_id,))

        modelo = cursor.fetchone()

        if not modelo:
            conn.close()
            flash('Modelo de checklist não encontrado.', 'warning')
            return redirect(url_for('main.pcpm_checklist_modelos'))

        cursor.execute("""
            SELECT
                id,
                modelo_id,
                ordem,
                item,
                criterio,
                exige_foto_nok,
                exige_observacao_nok,
                ativo
            FROM pcpm_checklist_itens
            WHERE modelo_id = %s
            ORDER BY ordem ASC
        """, (modelo_id,))

        itens = cursor.fetchall()

        conn.close()

        return render_template(
            'pcpm_checklist_itens.html',
            modelo=modelo,
            itens=itens
        )


    # ==========================================================
    # CADASTRAR ITEM CHECKLIST
    # ==========================================================

    @blueprint.route('/cadastrar_pcpm_checklist_item/<int:modelo_id>', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def cadastrar_pcpm_checklist_item(modelo_id):


        ordem = request.form.get('ordem')
        item = (request.form.get('item') or '').strip()
        criterio = (request.form.get('criterio') or '').strip()

        exige_foto_nok = request.form.get('exige_foto_nok', 1)
        exige_observacao_nok = request.form.get('exige_observacao_nok', 1)

        if not ordem:
            flash('Informe a ordem do item.', 'warning')
            return redirect(url_for('main.pcpm_checklist_itens', modelo_id=modelo_id))

        if not item:
            flash('Informe o item do checklist.', 'warning')
            return redirect(url_for('main.pcpm_checklist_itens', modelo_id=modelo_id))

        if not criterio:
            flash('Informe o critério/verificação.', 'warning')
            return redirect(url_for('main.pcpm_checklist_itens', modelo_id=modelo_id))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:

            cursor.execute("""
                SELECT id
                FROM pcpm_checklist_modelos
                WHERE id = %s
            """, (modelo_id,))

            modelo = cursor.fetchone()

            if not modelo:
                flash('Modelo de checklist inválido.', 'warning')
                conn.close()
                return redirect(url_for('main.pcpm_checklist_modelos'))

            cursor.execute("""
                SELECT id
                FROM pcpm_checklist_itens
                WHERE modelo_id = %s
                  AND ordem = %s
            """, (modelo_id, ordem))

            ordem_existente = cursor.fetchone()

            if ordem_existente:
                flash('Já existe um item cadastrado com esta ordem.', 'warning')
                conn.close()
                return redirect(url_for('main.pcpm_checklist_itens', modelo_id=modelo_id))

            cursor.execute("""
                INSERT INTO pcpm_checklist_itens (
                    modelo_id,
                    ordem,
                    item,
                    criterio,
                    exige_foto_nok,
                    exige_observacao_nok,
                    ativo
                )
                VALUES (%s, %s, %s, %s, %s, %s, 1)
            """, (
                modelo_id,
                ordem,
                item,
                criterio,
                exige_foto_nok,
                exige_observacao_nok
            ))

            conn.commit()

            flash('Item do checklist cadastrado com sucesso!', 'success')

        except Exception as e:

            conn.rollback()

            flash(f'Erro ao cadastrar item do checklist: {e}', 'danger')

        finally:

            conn.close()

        return redirect(url_for('main.pcpm_checklist_itens', modelo_id=modelo_id))


    # ==========================================================
    # EDITAR ITEM CHECKLIST
    # ==========================================================

    @blueprint.route('/editar_pcpm_checklist_item/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def editar_pcpm_checklist_item(id):


        ordem = request.form.get('ordem')
        item = (request.form.get('item') or '').strip()
        criterio = (request.form.get('criterio') or '').strip()

        exige_foto_nok = request.form.get('exige_foto_nok', 1)
        exige_observacao_nok = request.form.get('exige_observacao_nok', 1)

        if not ordem:
            flash('Informe a ordem do item.', 'warning')
            return redirect(url_for('main.pcpm_checklist_modelos'))

        if not item:
            flash('Informe o item do checklist.', 'warning')
            return redirect(url_for('main.pcpm_checklist_modelos'))

        if not criterio:
            flash('Informe o critério/verificação.', 'warning')
            return redirect(url_for('main.pcpm_checklist_modelos'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:

            cursor.execute("""
                SELECT
                    id,
                    modelo_id
                FROM pcpm_checklist_itens
                WHERE id = %s
            """, (id,))

            item_atual = cursor.fetchone()

            if not item_atual:
                flash('Item do checklist não encontrado.', 'warning')
                conn.close()
                return redirect(url_for('main.pcpm_checklist_modelos'))

            modelo_id = item_atual['modelo_id']

            cursor.execute("""
                SELECT id
                FROM pcpm_checklist_itens
                WHERE modelo_id = %s
                  AND ordem = %s
                  AND id <> %s
            """, (
                modelo_id,
                ordem,
                id
            ))

            ordem_existente = cursor.fetchone()

            if ordem_existente:
                flash('Já existe outro item cadastrado com esta ordem.', 'warning')
                conn.close()
                return redirect(url_for('main.pcpm_checklist_itens', modelo_id=modelo_id))

            cursor.execute("""
                UPDATE pcpm_checklist_itens
                SET ordem = %s,
                    item = %s,
                    criterio = %s,
                    exige_foto_nok = %s,
                    exige_observacao_nok = %s
                WHERE id = %s
            """, (
                ordem,
                item,
                criterio,
                exige_foto_nok,
                exige_observacao_nok,
                id
            ))

            conn.commit()

            flash('Item do checklist atualizado com sucesso!', 'success')

        except Exception as e:

            conn.rollback()

            flash(f'Erro ao atualizar item do checklist: {e}', 'danger')

        finally:

            conn.close()

        return redirect(url_for('main.pcpm_checklist_itens', modelo_id=modelo_id))


    # ==========================================================
    # INATIVAR ITEM CHECKLIST
    # ==========================================================

    @blueprint.route('/inativar_pcpm_checklist_item/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def inativar_pcpm_checklist_item(id):


        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT modelo_id
            FROM pcpm_checklist_itens
            WHERE id = %s
        """, (id,))

        item = cursor.fetchone()

        if not item:
            conn.close()
            flash('Item do checklist não encontrado.', 'warning')
            return redirect(url_for('main.pcpm_checklist_modelos'))

        modelo_id = item['modelo_id']

        cursor.execute("""
            UPDATE pcpm_checklist_itens
            SET ativo = 0
            WHERE id = %s
        """, (id,))

        conn.commit()
        conn.close()

        flash('Item do checklist inativado com sucesso!', 'success')

        return redirect(url_for('main.pcpm_checklist_itens', modelo_id=modelo_id))


    # ==========================================================
    # ATIVAR ITEM CHECKLIST
    # ==========================================================

    @blueprint.route('/ativar_pcpm_checklist_item/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def ativar_pcpm_checklist_item(id):


        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT modelo_id
            FROM pcpm_checklist_itens
            WHERE id = %s
        """, (id,))

        item = cursor.fetchone()

        if not item:
            conn.close()
            flash('Item do checklist não encontrado.', 'warning')
            return redirect(url_for('main.pcpm_checklist_modelos'))

        modelo_id = item['modelo_id']

        cursor.execute("""
            UPDATE pcpm_checklist_itens
            SET ativo = 1
            WHERE id = %s
        """, (id,))

        conn.commit()
        conn.close()

        flash('Item do checklist ativado com sucesso!', 'success')

        return redirect(url_for('main.pcpm_checklist_itens', modelo_id=modelo_id))

    # ==========================================================
    # PCP-M - MOVIMENTAÇÃO DE MÁQUINAS
    # ==========================================================

