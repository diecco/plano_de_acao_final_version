from flask import flash, jsonify, redirect, render_template, request, url_for

from app.decorators import api_module_required, login_required, module_required
from app.utils.db import get_db_connection


def register_pcpm_cadastros_routes(blueprint):
    @blueprint.route('/pcpm_pessoas', methods=['GET'])
    @login_required
    @module_required('acesso_pcpm')
    def pcpm_pessoas():


        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.args.get('limpar'):
            conn.close()
            return redirect(url_for('main.pcpm_pessoas'))

        filtros = {
            'matricula': (request.args.get('matricula') or '').strip(),
            'nome': (request.args.get('nome') or '').strip(),
            'empresa_id': request.args.get('empresa_id') or '',
            'setor_area': (request.args.get('setor_area') or '').strip()
        }

        cursor.execute("""
            SELECT
                id,
                nome
            FROM pcpm_empresas
            WHERE ativo = 1
            ORDER BY nome ASC
        """)
        empresas = cursor.fetchall()

        where = []
        params = []

        if filtros['matricula']:
            where.append("p.matricula LIKE %s")
            params.append(f"%{filtros['matricula']}%")

        if filtros['nome']:
            where.append("p.nome LIKE %s")
            params.append(f"%{filtros['nome']}%")

        if filtros['empresa_id']:
            where.append("p.empresa_id = %s")
            params.append(filtros['empresa_id'])

        if filtros['setor_area']:
            where.append("p.setor_area LIKE %s")
            params.append(f"%{filtros['setor_area']}%")

        where_sql = ""
        if where:
            where_sql = "WHERE " + " AND ".join(where)

        cursor.execute(f"""
            SELECT
                p.id,
                p.rfid,
                p.matricula,
                p.nome,
                p.empresa_id,
                emp.nome AS empresa_nome,
                p.setor_area,
                p.ativo
            FROM pcpm_pessoas p
            LEFT JOIN pcpm_empresas emp
                ON emp.id = p.empresa_id
            {where_sql}
            ORDER BY p.nome ASC
        """, params)

        pessoas = cursor.fetchall()

        conn.close()

        return render_template(
            'pcpm_pessoas.html',
            pessoas=pessoas,
            empresas=empresas,
            filtros=filtros
        )


    @blueprint.route('/cadastrar_pcpm_pessoa', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def cadastrar_pcpm_pessoa():


        rfid = (request.form.get('rfid') or '').strip()
        matricula = (request.form.get('matricula') or '').strip()
        nome = (request.form.get('nome') or '').strip()
        empresa_id = request.form.get('empresa_id') or None
        setor_area = (request.form.get('setor_area') or '').strip()

        if not rfid:
            flash('Informe o RFID do cliente/operador.', 'warning')
            return redirect(url_for('main.pcpm_pessoas'))

        if not matricula:
            flash('Informe a matrícula do cliente/operador.', 'warning')
            return redirect(url_for('main.pcpm_pessoas'))

        if not nome:
            flash('Informe o nome do cliente/operador.', 'warning')
            return redirect(url_for('main.pcpm_pessoas'))

        if not empresa_id:
            flash('Selecione a empresa do cliente/operador.', 'warning')
            return redirect(url_for('main.pcpm_pessoas'))

        if not setor_area:
            flash('Informe o setor/área do cliente/operador.', 'warning')
            return redirect(url_for('main.pcpm_pessoas'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT id
                FROM pcpm_empresas
                WHERE id = %s
                  AND ativo = 1
            """, (empresa_id,))
            empresa = cursor.fetchone()

            if not empresa:
                flash('Empresa inválida ou inativa.', 'warning')
                conn.close()
                return redirect(url_for('main.pcpm_pessoas'))

            cursor.execute("""
                SELECT id
                FROM pcpm_pessoas
                WHERE rfid = %s
                   OR matricula = %s
            """, (rfid, matricula))

            existente = cursor.fetchone()

            if existente:
                flash('Já existe um cliente/operador cadastrado com este RFID ou matrícula.', 'warning')
                conn.close()
                return redirect(url_for('main.pcpm_pessoas'))

            cursor.execute("""
                INSERT INTO pcpm_pessoas (
                    rfid,
                    matricula,
                    nome,
                    empresa_id,
                    setor_area,
                    ativo
                )
                VALUES (%s, %s, %s, %s, %s, 1)
            """, (
                rfid,
                matricula,
                nome,
                empresa_id,
                setor_area
            ))

            conn.commit()
            flash('Cliente/operador cadastrado com sucesso!', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Erro ao cadastrar cliente/operador: {e}', 'danger')

        finally:
            conn.close()

        return redirect(url_for('main.pcpm_pessoas'))


    @blueprint.route('/editar_pcpm_pessoa/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def editar_pcpm_pessoa(id):


        rfid = (request.form.get('rfid') or '').strip()
        matricula = (request.form.get('matricula') or '').strip()
        nome = (request.form.get('nome') or '').strip()
        empresa_id = request.form.get('empresa_id') or None
        setor_area = (request.form.get('setor_area') or '').strip()

        if not rfid:
            flash('Informe o RFID do cliente/operador.', 'warning')
            return redirect(url_for('main.pcpm_pessoas'))

        if not matricula:
            flash('Informe a matrícula do cliente/operador.', 'warning')
            return redirect(url_for('main.pcpm_pessoas'))

        if not nome:
            flash('Informe o nome do cliente/operador.', 'warning')
            return redirect(url_for('main.pcpm_pessoas'))

        if not empresa_id:
            flash('Selecione a empresa do cliente/operador.', 'warning')
            return redirect(url_for('main.pcpm_pessoas'))

        if not setor_area:
            flash('Informe o setor/área do cliente/operador.', 'warning')
            return redirect(url_for('main.pcpm_pessoas'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT id
                FROM pcpm_empresas
                WHERE id = %s
                  AND ativo = 1
            """, (empresa_id,))
            empresa = cursor.fetchone()

            if not empresa:
                flash('Empresa inválida ou inativa.', 'warning')
                conn.close()
                return redirect(url_for('main.pcpm_pessoas'))

            cursor.execute("""
                SELECT id
                FROM pcpm_pessoas
                WHERE (rfid = %s OR matricula = %s)
                  AND id <> %s
            """, (rfid, matricula, id))

            existente = cursor.fetchone()

            if existente:
                flash('Já existe outro cliente/operador cadastrado com este RFID ou matrícula.', 'warning')
                conn.close()
                return redirect(url_for('main.pcpm_pessoas'))

            cursor.execute("""
                UPDATE pcpm_pessoas
                SET rfid = %s,
                    matricula = %s,
                    nome = %s,
                    empresa_id = %s,
                    setor_area = %s
                WHERE id = %s
            """, (
                rfid,
                matricula,
                nome,
                empresa_id,
                setor_area,
                id
            ))

            conn.commit()
            flash('Cliente/operador atualizado com sucesso!', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Erro ao atualizar cliente/operador: {e}', 'danger')

        finally:
            conn.close()

        return redirect(url_for('main.pcpm_pessoas'))


    @blueprint.route('/inativar_pcpm_pessoa/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def inativar_pcpm_pessoa(id):


        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE pcpm_pessoas
            SET ativo = 0
            WHERE id = %s
        """, (id,))

        conn.commit()
        conn.close()

        flash('Cliente/operador inativado com sucesso!', 'success')
        return redirect(url_for('main.pcpm_pessoas'))


    @blueprint.route('/ativar_pcpm_pessoa/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def ativar_pcpm_pessoa(id):


        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE pcpm_pessoas
            SET ativo = 1
            WHERE id = %s
        """, (id,))

        conn.commit()
        conn.close()

        flash('Cliente/operador ativado com sucesso!', 'success')
        return redirect(url_for('main.pcpm_pessoas'))

    # ==========================================================
    # PCP-M - EMPRESAS
    # ==========================================================

    @blueprint.route('/pcpm_empresas', methods=['GET'])
    @login_required
    @module_required('acesso_pcpm')
    def pcpm_empresas():


        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        sort = request.args.get('sort', 'nome')
        order = request.args.get('order', 'asc')

        colunas_validas = {
            'id': 'id',
            'nome': 'nome'
        }

        if sort not in colunas_validas:
            sort = 'nome'

        if order not in ['asc', 'desc']:
            order = 'asc'

        cursor.execute(f"""
            SELECT
                id,
                nome,
                ativo
            FROM pcpm_empresas
            ORDER BY {colunas_validas[sort]} {order.upper()}
        """)

        empresas = cursor.fetchall()

        conn.close()

        return render_template(
            'pcpm_empresas.html',
            empresas=empresas
        )


    # ==========================================================
    # CADASTRAR EMPRESA
    # ==========================================================

    @blueprint.route('/cadastrar_pcpm_empresa', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def cadastrar_pcpm_empresa():


        nome = (request.form.get('nome') or '').strip()

        if not nome:
            flash('Informe o nome da empresa.', 'warning')
            return redirect(url_for('main.pcpm_empresas'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:

            cursor.execute("""
                SELECT id
                FROM pcpm_empresas
                WHERE UPPER(nome) = UPPER(%s)
            """, (nome,))

            existente = cursor.fetchone()

            if existente:
                flash('Já existe uma empresa cadastrada com este nome.', 'warning')
                conn.close()
                return redirect(url_for('main.pcpm_empresas'))

            cursor.execute("""
                INSERT INTO pcpm_empresas (
                    nome,
                    ativo
                )
                VALUES (%s, 1)
            """, (nome,))

            conn.commit()

            flash('Empresa cadastrada com sucesso!', 'success')

        except Exception as e:

            conn.rollback()

            flash(f'Erro ao cadastrar empresa: {e}', 'danger')

        finally:

            conn.close()

        return redirect(url_for('main.pcpm_empresas'))


    # ==========================================================
    # EDITAR EMPRESA
    # ==========================================================

    @blueprint.route('/editar_pcpm_empresa/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def editar_pcpm_empresa(id):


        nome = (request.form.get('nome') or '').strip()

        if not nome:
            flash('Informe o nome da empresa.', 'warning')
            return redirect(url_for('main.pcpm_empresas'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:

            cursor.execute("""
                SELECT id
                FROM pcpm_empresas
                WHERE UPPER(nome) = UPPER(%s)
                  AND id <> %s
            """, (nome, id))

            existente = cursor.fetchone()

            if existente:
                flash('Já existe outra empresa cadastrada com este nome.', 'warning')
                conn.close()
                return redirect(url_for('main.pcpm_empresas'))

            cursor.execute("""
                UPDATE pcpm_empresas
                SET nome = %s
                WHERE id = %s
            """, (
                nome,
                id
            ))

            conn.commit()

            flash('Empresa atualizada com sucesso!', 'success')

        except Exception as e:

            conn.rollback()

            flash(f'Erro ao atualizar empresa: {e}', 'danger')

        finally:

            conn.close()

        return redirect(url_for('main.pcpm_empresas'))


    # ==========================================================
    # INATIVAR EMPRESA
    # ==========================================================

    @blueprint.route('/inativar_pcpm_empresa/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def inativar_pcpm_empresa(id):


        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE pcpm_empresas
            SET ativo = 0
            WHERE id = %s
        """, (id,))

        conn.commit()
        conn.close()

        flash('Empresa inativada com sucesso!', 'success')

        return redirect(url_for('main.pcpm_empresas'))


    # ==========================================================
    # ATIVAR EMPRESA
    # ==========================================================

    @blueprint.route('/ativar_pcpm_empresa/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def ativar_pcpm_empresa(id):


        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE pcpm_empresas
            SET ativo = 1
            WHERE id = %s
        """, (id,))

        conn.commit()
        conn.close()

        flash('Empresa ativada com sucesso!', 'success')

        return redirect(url_for('main.pcpm_empresas'))

    # ==========================================================
    # API PCP-M - LISTAR EMPRESAS
    # ==========================================================

    @blueprint.route('/api/pcpm/empresas', methods=['GET'])
    @login_required
    @api_module_required('acesso_pcpm')
    def api_pcpm_empresas():


        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id,
                nome
            FROM pcpm_empresas
            WHERE ativo = 1
            ORDER BY nome
        """)

        empresas = cursor.fetchall()

        conn.close()

        return jsonify({
            'sucesso': True,
            'empresas': empresas
        })

