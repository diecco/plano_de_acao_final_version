import os

from flask import current_app, flash, redirect, render_template, request, session, url_for

from app.decorators import login_required, module_required
from app.upload_security import UploadService, UploadValidationError, validar_conteudo_upload
from app.utils.db import get_db_connection


def register_apr_routes(blueprint):
    @blueprint.route('/listar_apr', methods=['GET'])
    @login_required
    @module_required('acesso_ssma')
    def listar_apr():

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        usuario_id = session.get('usuario_id')
        perfil = session.get('perfil')
        centro_custos_id = session.get('centro_custos_id')

        if request.args.get('limpar'):
            conn.close()
            return redirect(url_for('main.listar_apr'))

        emitente_id = request.args.get('emitente_id', '').strip()
        aprovador_id = request.args.get('aprovador_id', '').strip()
        data_inicio = request.args.get('data_inicio', '').strip()
        data_fim = request.args.get('data_fim', '').strip()

        sort = request.args.get('sort', 'data_apr').strip()
        order = request.args.get('order', 'desc').strip().lower()

        page = request.args.get('page', 1, type=int)
        per_page = 20

        if page < 1:
            page = 1

        offset = (page - 1) * per_page

        colunas_validas = {
            'data_apr': 'apr.data_apr',
            'area_setor': 'apr.area_setor',
            'atividade': 'apr.atividade',
            'emitente_nome': 'emitente.nome',
            'aprovador_nome': 'aprovador.nome'
        }

        sort_sql = colunas_validas.get(sort, 'apr.data_apr')
        order_sql = 'ASC' if order == 'asc' else 'DESC'

        filtros_sql = ["apr.ativo = 1"]
        params = []

        # Controle de escopo por perfil
        if perfil == 'basico':
            filtros_sql.append("apr.criado_por = %s")
            params.append(usuario_id)

        elif perfil == 'intermediario':
            filtros_sql.append("emitente.centro_custos_id = %s")
            params.append(centro_custos_id)

        # avançado e administrador veem tudo

        if emitente_id:
            filtros_sql.append("apr.emitente_id = %s")
            params.append(emitente_id)

        if aprovador_id:
            filtros_sql.append("apr.aprovador_id = %s")
            params.append(aprovador_id)

        if data_inicio:
            filtros_sql.append("apr.data_apr >= %s")
            params.append(data_inicio)

        if data_fim:
            filtros_sql.append("apr.data_apr <= %s")
            params.append(data_fim)

        where_clause = "WHERE " + " AND ".join(filtros_sql)

        base_from = f"""
            FROM aprs apr
            JOIN usuarios emitente
                ON emitente.id = apr.emitente_id
            JOIN usuarios aprovador
                ON aprovador.id = apr.aprovador_id
            {where_clause}
        """

        cursor.execute(f"""
            SELECT COUNT(*) AS total
            {base_from}
        """, params)
        total_registros = cursor.fetchone()['total']

        total_paginas = (total_registros + per_page - 1) // per_page

        if total_paginas > 0 and page > total_paginas:
            page = total_paginas
            offset = (page - 1) * per_page

        cursor.execute(f"""
            SELECT
                apr.id,
                apr.data_apr,
                apr.area_setor,
                apr.atividade,
                apr.emitente_id,
                apr.aprovador_id,
                apr.arquivo_pdf,
                apr.criado_por,
                apr.criado_em,

                emitente.nome AS emitente_nome,
                aprovador.nome AS aprovador_nome

            {base_from}
            ORDER BY {sort_sql} {order_sql}, apr.id DESC
            LIMIT %s OFFSET %s
        """, params + [per_page, offset])
        aprs = cursor.fetchall()

        if perfil in ['administrador', 'avancado']:
            cursor.execute("""
                SELECT id, nome, matricula
                FROM usuarios
                WHERE ativo = 1
                ORDER BY nome
            """)
        else:
            cursor.execute("""
                SELECT id, nome, matricula
                FROM usuarios
                WHERE ativo = 1
                  AND centro_custos_id = %s
                ORDER BY nome
            """, (centro_custos_id,))

        usuarios = cursor.fetchall()

        conn.close()

        filtros = {
            'emitente_id': emitente_id,
            'aprovador_id': aprovador_id,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'sort': sort,
            'order': order
        }

        return render_template(
            'listar_apr.html',
            aprs=aprs,
            usuarios=usuarios,
            filtros=filtros,
            page=page,
            per_page=per_page,
            total_registros=total_registros,
            total_paginas=total_paginas
        )

    @blueprint.route('/cadastrar_apr', methods=['POST'])
    @login_required
    @module_required('acesso_ssma')
    def cadastrar_apr():
        data_apr = request.form.get('data_apr', '').strip()
        area_setor = request.form.get('area_setor', '').strip()
        atividade = request.form.get('atividade', '').strip()
        emitente_id = request.form.get('emitente_id', '').strip()
        aprovador_id = request.form.get('aprovador_id', '').strip()
        arquivo = request.files.get('arquivo_pdf')

        usuario_id = session.get('usuario_id')
        perfil = session.get('perfil')
        centro_custos_id = session.get('centro_custos_id')

        if not data_apr or not area_setor or not atividade or not emitente_id or not aprovador_id:
            flash('Preencha todos os campos obrigatórios.', 'warning')
            return redirect(url_for('main.listar_apr'))

        if not arquivo or arquivo.filename == '':
            flash('Anexe o arquivo PDF da APR.', 'warning')
            return redirect(url_for('main.listar_apr'))

        extensao = arquivo.filename.rsplit('.', 1)[-1].lower() if '.' in arquivo.filename else ''

        if extensao != 'pdf':
            flash('Somente arquivos PDF são permitidos.', 'danger')
            return redirect(url_for('main.listar_apr'))

        try:
            validar_conteudo_upload(arquivo, {"pdf"})
        except UploadValidationError as exc:
            flash(str(exc), 'danger')
            return redirect(url_for('main.listar_apr'))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if perfil in ['administrador', 'avancado']:
            cursor.execute("""
                SELECT id
                FROM usuarios
                WHERE id IN (%s, %s)
                  AND ativo = 1
            """, (emitente_id, aprovador_id))
        else:
            cursor.execute("""
                SELECT id
                FROM usuarios
                WHERE id IN (%s, %s)
                  AND ativo = 1
                  AND centro_custos_id = %s
            """, (emitente_id, aprovador_id, centro_custos_id))

        usuarios_validos = cursor.fetchall()

        if len(usuarios_validos) != 2:
            conn.close()
            flash('Emitente ou aprovador inválido para seu escopo.', 'danger')
            return redirect(url_for('main.listar_apr'))

        nome_arquivo = UploadService.salvar(
            arquivo,
            {"pdf"},
            prefixo="apr",
            diretorio=os.path.join('static', 'aprs'),
        )

        cursor.execute("""
            INSERT INTO aprs (
                data_apr,
                area_setor,
                atividade,
                emitente_id,
                aprovador_id,
                arquivo_pdf,
                criado_por
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            data_apr,
            area_setor,
            atividade,
            emitente_id,
            aprovador_id,
            nome_arquivo,
            usuario_id
        ))

        conn.commit()
        conn.close()

        flash('APR cadastrada com sucesso.', 'success')
        return redirect(url_for('main.listar_apr'))

    @blueprint.route('/editar_apr/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_ssma')
    def editar_apr(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        apr = pode_acessar_ssma(cursor, 'apr', id)

        if not apr:
            conn.close()
            flash('APR não encontrada ou você não possui permissão para editá-la.', 'warning')
            return redirect(url_for('main.listar_apr'))

        usuario_id = session.get('usuario_id')
        perfil = session.get('perfil')
        centro_custos_id = session.get('centro_custos_id')

        if apr['criado_por'] != usuario_id and perfil != 'administrador':
            conn.close()
            flash('Você não tem permissão para editar esta APR.', 'danger')
            return redirect(url_for('main.listar_apr'))

        data_apr = request.form.get('data_apr', '').strip()
        area_setor = request.form.get('area_setor', '').strip()
        atividade = request.form.get('atividade', '').strip()
        emitente_id = request.form.get('emitente_id', '').strip()
        aprovador_id = request.form.get('aprovador_id', '').strip()
        arquivo = request.files.get('arquivo_pdf')

        if not data_apr or not area_setor or not atividade or not emitente_id or not aprovador_id:
            conn.close()
            flash('Preencha todos os campos obrigatórios.', 'warning')
            return redirect(url_for('main.listar_apr'))

        if perfil in ['administrador', 'avancado']:
            cursor.execute("""
                SELECT id
                FROM usuarios
                WHERE id IN (%s, %s)
                  AND ativo = 1
            """, (emitente_id, aprovador_id))
        else:
            cursor.execute("""
                SELECT id
                FROM usuarios
                WHERE id IN (%s, %s)
                  AND ativo = 1
                  AND centro_custos_id = %s
            """, (emitente_id, aprovador_id, centro_custos_id))

        usuarios_validos = cursor.fetchall()

        if len(usuarios_validos) != 2:
            conn.close()
            flash('Emitente ou aprovador inválido para seu escopo.', 'danger')
            return redirect(url_for('main.listar_apr'))

        nome_arquivo = apr['arquivo_pdf']
        nome_arquivo_anterior = None

        if arquivo and arquivo.filename:
            try:
                validar_conteudo_upload(arquivo, {"pdf"})
            except UploadValidationError as exc:
                conn.close()
                flash(str(exc), 'danger')
                return redirect(url_for('main.listar_apr'))

            extensao = arquivo.filename.rsplit('.', 1)[-1].lower() if '.' in arquivo.filename else ''

            if extensao != 'pdf':
                conn.close()
                flash('Somente arquivos PDF são permitidos.', 'danger')
                return redirect(url_for('main.listar_apr'))

            novo_nome_arquivo = UploadService.salvar(
                arquivo,
                {"pdf"},
                prefixo=f"apr_{id}",
                diretorio=os.path.join('static', 'aprs'),
            )

            nome_arquivo_anterior = nome_arquivo
            nome_arquivo = novo_nome_arquivo

        cursor.execute("""
            UPDATE aprs
            SET data_apr = %s,
                area_setor = %s,
                atividade = %s,
                emitente_id = %s,
                aprovador_id = %s,
                arquivo_pdf = %s,
                atualizado_em = NOW()
            WHERE id = %s
              AND ativo = 1
        """, (
            data_apr,
            area_setor,
            atividade,
            emitente_id,
            aprovador_id,
            nome_arquivo,
            id
        ))

        conn.commit()
        conn.close()

        if nome_arquivo_anterior:
            try:
                UploadService.excluir(
                    nome_arquivo_anterior,
                    diretorio=os.path.join('static', 'aprs'),
                )
            except OSError:
                current_app.logger.exception("Falha ao excluir o PDF anterior da APR %s", id)

        flash('APR atualizada com sucesso.', 'success')
        return redirect(url_for('main.listar_apr'))

    @blueprint.route('/excluir_apr/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_ssma')
    def excluir_apr(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        apr = pode_acessar_ssma(cursor, 'apr', id)

        if not apr:
            conn.close()
            flash('APR não encontrada ou você não possui permissão para excluí-la.', 'warning')
            return redirect(url_for('main.listar_apr'))

        if apr['criado_por'] != session.get('usuario_id') and session.get('perfil') != 'administrador':
            conn.close()
            flash('Você não tem permissão para excluir esta APR.', 'danger')
            return redirect(url_for('main.listar_apr'))

        cursor.execute("""
            UPDATE aprs
            SET ativo = 0,
                atualizado_em = NOW()
            WHERE id = %s
        """, (id,))

        conn.commit()
        conn.close()

        flash('APR excluída com sucesso.', 'success')
        return redirect(url_for('main.listar_apr'))

