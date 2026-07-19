from flask import flash, redirect, render_template, request, url_for

from app.decorators import login_required, module_required
from app.utils.db import get_db_connection


def register_pcpm_equipamentos_routes(blueprint):
    @blueprint.route('/tipos_equipamento', methods=['GET'])
    @login_required
    @module_required('acesso_pcpm')
    def tipos_equipamento():

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        sort = request.args.get('sort', 'nome')
        order = request.args.get('order', 'asc')

        colunas_validas = {
            'id': 'id',
            'tag': 'tag',
            'nome': 'nome'
        }

        if sort not in colunas_validas:
            sort = 'nome'

        if order not in ['asc', 'desc']:
            order = 'asc'

        cursor.execute(f"""
            SELECT
                id,
                tag,
                nome,
                ativo
            FROM pcpm_tipos_equipamento
            ORDER BY {colunas_validas[sort]} {order.upper()}
        """)

        tipos_equipamento = cursor.fetchall()
        conn.close()

        return render_template(
            'tipos_equipamento.html',
            tipos_equipamento=tipos_equipamento
        )


    @blueprint.route('/cadastrar_tipo_equipamento', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def cadastrar_tipo_equipamento():


        tag = (request.form.get('tag') or '').strip().upper()
        nome = (request.form.get('nome') or '').strip()

        if not tag:
            flash('Informe a TAG do tipo de equipamento.', 'warning')
            return redirect(url_for('main.tipos_equipamento'))

        if not nome:
            flash('Informe o nome do tipo de equipamento.', 'warning')
            return redirect(url_for('main.tipos_equipamento'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT id
            FROM pcpm_tipos_equipamento
            WHERE UPPER(tag) = UPPER(%s)
               OR UPPER(nome) = UPPER(%s)
        """, (tag, nome))

        existente = cursor.fetchone()

        if existente:
            conn.close()
            flash('Já existe um tipo de equipamento com essa TAG ou nome.', 'warning')
            return redirect(url_for('main.tipos_equipamento'))

        cursor.execute("""
            INSERT INTO pcpm_tipos_equipamento (
                tag,
                nome,
                ativo
            )
            VALUES (%s, %s, 1)
        """, (tag, nome))

        conn.commit()
        conn.close()

        flash('Tipo de equipamento cadastrado com sucesso!', 'success')
        return redirect(url_for('main.tipos_equipamento'))


    @blueprint.route('/editar_tipo_equipamento/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def editar_tipo_equipamento(id):


        tag = (request.form.get('tag') or '').strip().upper()
        nome = (request.form.get('nome') or '').strip()

        if not tag:
            flash('Informe a TAG do tipo de equipamento.', 'warning')
            return redirect(url_for('main.tipos_equipamento'))

        if not nome:
            flash('Informe o nome do tipo de equipamento.', 'warning')
            return redirect(url_for('main.tipos_equipamento'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT id
            FROM pcpm_tipos_equipamento
            WHERE (UPPER(tag) = UPPER(%s)
                OR UPPER(nome) = UPPER(%s))
              AND id <> %s
        """, (tag, nome, id))

        existente = cursor.fetchone()

        if existente:
            conn.close()
            flash('Já existe outro tipo de equipamento com essa TAG ou nome.', 'warning')
            return redirect(url_for('main.tipos_equipamento'))

        cursor.execute("""
            UPDATE pcpm_tipos_equipamento
            SET tag = %s,
                nome = %s
            WHERE id = %s
        """, (tag, nome, id))

        conn.commit()
        conn.close()

        flash('Tipo de equipamento atualizado com sucesso!', 'success')
        return redirect(url_for('main.tipos_equipamento'))


    @blueprint.route('/inativar_tipo_equipamento/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def inativar_tipo_equipamento(id):


        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE pcpm_tipos_equipamento
            SET ativo = 0
            WHERE id = %s
        """, (id,))

        conn.commit()
        conn.close()

        flash('Tipo de equipamento inativado com sucesso!', 'success')
        return redirect(url_for('main.tipos_equipamento'))


    @blueprint.route('/ativar_tipo_equipamento/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def ativar_tipo_equipamento(id):


        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE pcpm_tipos_equipamento
            SET ativo = 1
            WHERE id = %s
        """, (id,))

        conn.commit()
        conn.close()

        flash('Tipo de equipamento ativado com sucesso!', 'success')
        return redirect(url_for('main.tipos_equipamento'))



    @blueprint.route('/equipamentos', methods=['GET'])
    @login_required
    @module_required('acesso_pcpm')
    def equipamentos():


        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.args.get('limpar'):
            conn.close()
            return redirect(url_for('main.equipamentos'))

        filtros = {
            'codigo_frota': (request.args.get('codigo_frota') or '').strip().upper(),
            'tipo_equipamento_id': request.args.get('tipo_equipamento_id') or '',
            'centro_custo_id': request.args.get('centro_custo_id') or ''
        }

        where = []
        params = []

        if filtros['codigo_frota']:
            where.append("e.codigo_frota LIKE %s")
            params.append(f"%{filtros['codigo_frota']}%")

        if filtros['tipo_equipamento_id']:
            where.append("e.tipo_equipamento_id = %s")
            params.append(filtros['tipo_equipamento_id'])

        if filtros['centro_custo_id']:
            where.append("e.centro_custo_id = %s")
            params.append(filtros['centro_custo_id'])

        where_sql = ""
        if where:
            where_sql = "WHERE " + " AND ".join(where)

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

        cursor.execute("""
            SELECT
                id,
                codigo,
                descricao
            FROM centros_custos
            WHERE ativo = 1
            ORDER BY codigo, descricao
        """)
        centros_custos = cursor.fetchall()

        cursor.execute(f"""
            SELECT
                e.id,
                e.tipo_equipamento_id,
                e.centro_custo_id,
                e.codigo_frota,
                e.marca,
                e.modelo,
                e.ativo,
                te.tag AS tipo_tag,
                te.nome AS tipo_nome,
                cc.codigo AS centro_custo_codigo,
                cc.descricao AS centro_custo_descricao
            FROM pcpm_equipamentos e
            JOIN pcpm_tipos_equipamento te
                ON te.id = e.tipo_equipamento_id
            JOIN centros_custos cc
                ON cc.id = e.centro_custo_id
            {where_sql}
            ORDER BY e.codigo_frota ASC
        """, params)

        equipamentos = cursor.fetchall()

        conn.close()

        return render_template(
            'equipamentos.html',
            equipamentos=equipamentos,
            tipos_equipamento=tipos_equipamento,
            centros_custos=centros_custos,
            filtros=filtros
        )


    @blueprint.route('/cadastrar_equipamento', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def cadastrar_equipamento():


        tipo_equipamento_id = request.form.get('tipo_equipamento_id')
        centro_custo_id = request.form.get('centro_custo_id')

        numero_frota = (request.form.get('codigo_frota') or '').strip()

        marca = (request.form.get('marca') or '').strip()
        modelo = (request.form.get('modelo') or '').strip()

        if not tipo_equipamento_id:
            flash('Selecione o tipo de equipamento.', 'warning')
            return redirect(url_for('main.equipamentos'))

        if not centro_custo_id:
            flash('Selecione o centro de custo.', 'warning')
            return redirect(url_for('main.equipamentos'))

        if not numero_frota:
            flash('Informe o número da frota.', 'warning')
            return redirect(url_for('main.equipamentos'))

        if not numero_frota.isdigit() or len(numero_frota) != 4:
            flash('Informe os 4 dígitos numéricos da frota.', 'warning')
            return redirect(url_for('main.equipamentos'))

        if not marca:
            flash('Informe a marca do equipamento.', 'warning')
            return redirect(url_for('main.equipamentos'))

        if not modelo:
            flash('Informe o modelo do equipamento.', 'warning')
            return redirect(url_for('main.equipamentos'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:

            cursor.execute("""
                SELECT
                    id,
                    tag
                FROM pcpm_tipos_equipamento
                WHERE id = %s
                  AND ativo = 1
            """, (tipo_equipamento_id,))

            tipo = cursor.fetchone()

            if not tipo:
                flash('Tipo de equipamento inválido.', 'warning')
                conn.close()
                return redirect(url_for('main.equipamentos'))

            codigo_frota = f"{tipo['tag']}-{numero_frota}"

            cursor.execute("""
                SELECT id
                FROM pcpm_equipamentos
                WHERE UPPER(codigo_frota) = UPPER(%s)
            """, (codigo_frota,))

            existente = cursor.fetchone()

            if existente:
                flash('Já existe um equipamento cadastrado com esta frota.', 'warning')
                conn.close()
                return redirect(url_for('main.equipamentos'))

            cursor.execute("""
                INSERT INTO pcpm_equipamentos (
                    tipo_equipamento_id,
                    centro_custo_id,
                    codigo_frota,
                    marca,
                    modelo,
                    ativo
                )
                VALUES (%s, %s, %s, %s, %s, 1)
            """, (
                tipo_equipamento_id,
                centro_custo_id,
                codigo_frota,
                marca,
                modelo
            ))

            conn.commit()

            flash('Equipamento cadastrado com sucesso!', 'success')

        except Exception as e:

            conn.rollback()

            flash(f'Erro ao cadastrar equipamento: {e}', 'danger')

        finally:

            conn.close()

        return redirect(url_for('main.equipamentos'))


    @blueprint.route('/editar_equipamento/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def editar_equipamento(id):


        tipo_equipamento_id = request.form.get('tipo_equipamento_id')
        centro_custo_id = request.form.get('centro_custo_id')

        numero_frota = (request.form.get('codigo_frota') or '').strip()

        marca = (request.form.get('marca') or '').strip()
        modelo = (request.form.get('modelo') or '').strip()

        if not tipo_equipamento_id:
            flash('Selecione o tipo de equipamento.', 'warning')
            return redirect(url_for('main.equipamentos'))

        if not centro_custo_id:
            flash('Selecione o centro de custo.', 'warning')
            return redirect(url_for('main.equipamentos'))

        if not numero_frota:
            flash('Informe o número da frota.', 'warning')
            return redirect(url_for('main.equipamentos'))

        if not numero_frota.isdigit() or len(numero_frota) != 4:
            flash('Informe os 4 dígitos numéricos da frota.', 'warning')
            return redirect(url_for('main.equipamentos'))

        if not marca:
            flash('Informe a marca do equipamento.', 'warning')
            return redirect(url_for('main.equipamentos'))

        if not modelo:
            flash('Informe o modelo do equipamento.', 'warning')
            return redirect(url_for('main.equipamentos'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:

            cursor.execute("""
                SELECT
                    id,
                    tag
                FROM pcpm_tipos_equipamento
                WHERE id = %s
                  AND ativo = 1
            """, (tipo_equipamento_id,))

            tipo = cursor.fetchone()

            if not tipo:
                flash('Tipo de equipamento inválido.', 'warning')
                conn.close()
                return redirect(url_for('main.equipamentos'))

            codigo_frota = f"{tipo['tag']}-{numero_frota}"

            cursor.execute("""
                SELECT id
                FROM pcpm_equipamentos
                WHERE UPPER(codigo_frota) = UPPER(%s)
                  AND id <> %s
            """, (codigo_frota, id))

            existente = cursor.fetchone()

            if existente:
                flash('Já existe outro equipamento cadastrado com esta frota.', 'warning')
                conn.close()
                return redirect(url_for('main.equipamentos'))

            cursor.execute("""
                UPDATE pcpm_equipamentos
                SET tipo_equipamento_id = %s,
                    centro_custo_id = %s,
                    codigo_frota = %s,
                    marca = %s,
                    modelo = %s
                WHERE id = %s
            """, (
                tipo_equipamento_id,
                centro_custo_id,
                codigo_frota,
                marca,
                modelo,
                id
            ))

            conn.commit()

            flash('Equipamento atualizado com sucesso!', 'success')

        except Exception as e:

            conn.rollback()

            flash(f'Erro ao atualizar equipamento: {e}', 'danger')

        finally:

            conn.close()

        return redirect(url_for('main.equipamentos'))


    @blueprint.route('/inativar_equipamento/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def inativar_equipamento(id):


        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE pcpm_equipamentos
            SET ativo = 0
            WHERE id = %s
        """, (id,))

        conn.commit()
        conn.close()

        flash('Equipamento inativado com sucesso!', 'success')

        return redirect(url_for('main.equipamentos'))


    @blueprint.route('/ativar_equipamento/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def ativar_equipamento(id):


        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE pcpm_equipamentos
            SET ativo = 1
            WHERE id = %s
        """, (id,))

        conn.commit()
        conn.close()

        flash('Equipamento ativado com sucesso!', 'success')

        return redirect(url_for('main.equipamentos'))

