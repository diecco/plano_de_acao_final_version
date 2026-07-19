import os
from datetime import datetime

from flask import current_app, flash, jsonify, redirect, render_template, request, session, url_for

from app.decorators import api_module_required, login_required, module_required
from app.upload_security import UploadService, UploadValidationError, validar_conteudo_upload
from app.utils.db import get_db_connection


ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def register_pcpm_movimentacoes_routes(blueprint):
    @blueprint.route('/pcpm_movimentacao', methods=['GET'])
    @login_required
    @module_required('acesso_pcpm')
    def pcpm_movimentacao():


        from datetime import datetime

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        equipamento_id = request.args.get('equipamento_id') or None

        cursor.execute("""
            SELECT
                e.id,
                e.codigo_frota,
                e.marca,
                e.modelo,
                e.status_localizacao,
                te.nome AS tipo_nome,
                te.tag AS tipo_tag
            FROM pcpm_equipamentos e
            JOIN pcpm_tipos_equipamento te
                ON te.id = e.tipo_equipamento_id
            WHERE e.ativo = 1
            ORDER BY e.codigo_frota
        """)
        equipamentos = cursor.fetchall()

        cursor.execute("""
            SELECT
                id,
                matricula,
                nome
            FROM usuarios
            WHERE ativo = 1
            ORDER BY nome
        """)
        funcionarios = cursor.fetchall()

        cursor.execute("""
            SELECT
                p.id,
                p.matricula,
                p.nome,
                p.rfid,
                emp.nome AS empresa_nome
            FROM pcpm_pessoas p
            LEFT JOIN pcpm_empresas emp
                ON emp.id = p.empresa_id
            WHERE p.ativo = 1
            ORDER BY p.nome
        """)
        pessoas = cursor.fetchall()

        equipamento_selecionado = None
        modelo_checklist = None
        itens_checklist = []
        tipo_movimentacao_permitido = None

        if equipamento_id:
            cursor.execute("""
                SELECT
                    e.id,
                    e.codigo_frota,
                    e.marca,
                    e.modelo,
                    e.tipo_equipamento_id,
                    e.status_localizacao,
                    te.nome AS tipo_nome,
                    te.tag AS tipo_tag
                FROM pcpm_equipamentos e
                JOIN pcpm_tipos_equipamento te
                    ON te.id = e.tipo_equipamento_id
                WHERE e.id = %s
                  AND e.ativo = 1
            """, (equipamento_id,))
            equipamento_selecionado = cursor.fetchone()

            if equipamento_selecionado:
                status = equipamento_selecionado.get('status_localizacao') or 'indefinido'

                if status == 'area':
                    tipo_movimentacao_permitido = 'retirada'
                elif status == 'tradimaq':
                    tipo_movimentacao_permitido = 'entrega'
                else:
                    tipo_movimentacao_permitido = None

                cursor.execute("""
                    SELECT
                        id,
                        nome
                    FROM pcpm_checklist_modelos
                    WHERE tipo_equipamento_id = %s
                      AND ativo = 1
                    ORDER BY id DESC
                    LIMIT 1
                """, (equipamento_selecionado['tipo_equipamento_id'],))
                modelo_checklist = cursor.fetchone()

                if modelo_checklist:
                    cursor.execute("""
                        SELECT
                            id,
                            ordem,
                            item,
                            criterio,
                            exige_foto_nok,
                            exige_observacao_nok
                        FROM pcpm_checklist_itens
                        WHERE modelo_id = %s
                          AND ativo = 1
                        ORDER BY ordem
                    """, (modelo_checklist['id'],))
                    itens_checklist = cursor.fetchall()

        conn.close()

        return render_template(
            'pcpm_movimentacao.html',
            equipamentos=equipamentos,
            funcionarios=funcionarios,
            pessoas=pessoas,
            equipamento_selecionado=equipamento_selecionado,
            modelo_checklist=modelo_checklist,
            itens_checklist=itens_checklist,
            tipo_movimentacao_permitido=tipo_movimentacao_permitido,
            data_atual=datetime.now().strftime('%d/%m/%Y')
        )


    @blueprint.route('/salvar_pcpm_movimentacao', methods=['POST'])
    @login_required
    @module_required('acesso_pcpm')
    def salvar_pcpm_movimentacao():


        import os
        from werkzeug.utils import secure_filename
        from datetime import datetime

        equipamento_id = request.form.get('equipamento_id')
        funcionario_id = request.form.get('funcionario_id')
        cliente_id = request.form.get('cliente_id')

        tipo_movimentacao = request.form.get('tipo_movimentacao')
        motivo_movimentacao = request.form.get('motivo_movimentacao')
        numero_os = (request.form.get('numero_os') or '').strip() or None
        horimetro = request.form.get('horimetro')
        descricao_anomalia = (request.form.get('descricao_anomalia') or '').strip()

        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')

        checklist_item_ids = request.form.getlist('checklist_item_ids[]')

        if not equipamento_id:
            flash('Selecione o equipamento.', 'warning')
            return redirect(url_for('main.pcpm_movimentacao'))

        if not funcionario_id:
            flash('Selecione o funcionário Tradimaq.', 'warning')
            return redirect(url_for('main.pcpm_movimentacao', equipamento_id=equipamento_id))

        if not cliente_id:
            flash('Selecione o cliente/operador.', 'warning')
            return redirect(url_for('main.pcpm_movimentacao', equipamento_id=equipamento_id))

        if not tipo_movimentacao:
            flash('Selecione o tipo de movimentação.', 'warning')
            return redirect(url_for('main.pcpm_movimentacao', equipamento_id=equipamento_id))

        if tipo_movimentacao not in ['retirada', 'entrega']:
            flash('Tipo de movimentação inválido.', 'warning')
            return redirect(url_for('main.pcpm_movimentacao', equipamento_id=equipamento_id))

        if not motivo_movimentacao:
            flash('Selecione o motivo da movimentação.', 'warning')
            return redirect(url_for('main.pcpm_movimentacao', equipamento_id=equipamento_id))

        if not horimetro:
            flash('Informe o horímetro.', 'warning')
            return redirect(url_for('main.pcpm_movimentacao', equipamento_id=equipamento_id))

        if not descricao_anomalia:
            flash('Informe o relato/condições encontradas.', 'warning')
            return redirect(url_for('main.pcpm_movimentacao', equipamento_id=equipamento_id))

        if not latitude or not longitude:
            flash('Não foi possível capturar a geolocalização.', 'danger')
            return redirect(url_for('main.pcpm_movimentacao', equipamento_id=equipamento_id))

        if not checklist_item_ids:
            flash('Não há itens de checklist cadastrados para este equipamento.', 'warning')
            return redirect(url_for('main.pcpm_movimentacao', equipamento_id=equipamento_id))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT
                    id,
                    status_localizacao
                FROM pcpm_equipamentos
                WHERE id = %s
                  AND ativo = 1
            """, (equipamento_id,))
            equipamento = cursor.fetchone()

            if not equipamento:
                flash('Equipamento inválido ou inativo.', 'warning')
                conn.close()
                return redirect(url_for('main.pcpm_movimentacao'))

            status_atual = equipamento.get('status_localizacao') or 'indefinido'

            if status_atual == 'area' and tipo_movimentacao != 'retirada':
                flash('Este equipamento está registrado como na área. A próxima movimentação deve ser retirada.', 'warning')
                conn.close()
                return redirect(url_for('main.pcpm_movimentacao', equipamento_id=equipamento_id))

            if status_atual == 'tradimaq' and tipo_movimentacao != 'entrega':
                flash('Este equipamento está registrado como em posse da Tradimaq. A próxima movimentação deve ser entrega.', 'warning')
                conn.close()
                return redirect(url_for('main.pcpm_movimentacao', equipamento_id=equipamento_id))

            cursor.execute("""
                SELECT
                    id,
                    uid_rfid
                FROM usuarios
                WHERE id = %s
                  AND ativo = 1
            """, (funcionario_id,))
            funcionario = cursor.fetchone()

            if not funcionario:
                flash('Funcionário Tradimaq inválido ou inativo.', 'warning')
                conn.close()
                return redirect(url_for('main.pcpm_movimentacao', equipamento_id=equipamento_id))

            cursor.execute("""
                SELECT
                    id,
                    rfid
                FROM pcpm_pessoas
                WHERE id = %s
                  AND ativo = 1
            """, (cliente_id,))
            cliente = cursor.fetchone()

            if not cliente:
                flash('Cliente/operador inválido ou inativo.', 'warning')
                conn.close()
                return redirect(url_for('main.pcpm_movimentacao', equipamento_id=equipamento_id))

            rfid_funcionario = funcionario.get('uid_rfid') or ''
            rfid_cliente = cliente.get('rfid') or ''

            cursor.execute("""
                INSERT INTO pcpm_movimentacoes (
                    equipamento_id,
                    cliente_id,
                    funcionario_id,
                    tipo_movimentacao,
                    motivo_movimentacao,
                    numero_os,
                    horimetro,
                    descricao_anomalia,
                    rfid_funcionario,
                    rfid_cliente,
                    latitude,
                    longitude,
                    criado_por,
                    ativo
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
            """, (
                equipamento_id,
                cliente_id,
                funcionario_id,
                tipo_movimentacao,
                motivo_movimentacao,
                numero_os,
                horimetro,
                descricao_anomalia,
                rfid_funcionario,
                rfid_cliente,
                latitude,
                longitude,
                session.get('usuario_id')
            ))

            movimentacao_id = cursor.lastrowid

            pasta_upload = os.path.join(
                current_app.root_path,
                'static',
                'pcpm_movimentacoes',
                str(movimentacao_id)
            )

            os.makedirs(pasta_upload, exist_ok=True)

            for item_id in checklist_item_ids:
                resultado = request.form.get(f'resultado_{item_id}')
                observacao = (request.form.get(f'observacao_{item_id}') or '').strip()

                if not resultado:
                    raise Exception('Todos os itens do checklist devem ser respondidos.')

                cursor.execute("""
                    SELECT
                        id,
                        ordem,
                        item,
                        criterio,
                        exige_foto_nok,
                        exige_observacao_nok
                    FROM pcpm_checklist_itens
                    WHERE id = %s
                """, (item_id,))
                item_checklist = cursor.fetchone()

                if not item_checklist:
                    raise Exception('Item de checklist inválido.')

                arquivo_foto = request.files.get(f'foto_{item_id}')

                if resultado == 'NOK':
                    if item_checklist['exige_observacao_nok'] and not observacao:
                        raise Exception(f"O item '{item_checklist['item']}' exige observação quando NOK.")

                    if item_checklist['exige_foto_nok'] and (not arquivo_foto or arquivo_foto.filename == ''):
                        raise Exception(f"O item '{item_checklist['item']}' exige foto quando NOK.")

                cursor.execute("""
                    INSERT INTO pcpm_movimentacao_checklist_respostas (
                        movimentacao_id,
                        checklist_item_id,
                        resultado,
                        observacao,
                        item_snapshot,
                        criterio_snapshot,
                        ordem_snapshot
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    movimentacao_id,
                    item_id,
                    resultado,
                    observacao,
                    item_checklist['item'],
                    item_checklist['criterio'],
                    item_checklist['ordem']
                ))

                resposta_id = cursor.lastrowid

                if arquivo_foto and arquivo_foto.filename:
                    nome_final = UploadService.salvar(
                        arquivo_foto,
                        ALLOWED_IMAGE_EXTENSIONS,
                        prefixo=f"checklist_{resposta_id}",
                        diretorio=pasta_upload,
                    )

                    caminho_relativo = f"pcpm_movimentacoes/{movimentacao_id}/{nome_final}"

                    cursor.execute("""
                        INSERT INTO pcpm_movimentacao_fotos (
                            movimentacao_id,
                            checklist_resposta_id,
                            tipo_foto,
                            caminho_arquivo
                        )
                        VALUES (%s, %s, 'checklist', %s)
                    """, (
                        movimentacao_id,
                        resposta_id,
                        caminho_relativo
                    ))

            novo_status = 'tradimaq' if tipo_movimentacao == 'retirada' else 'area'

            cursor.execute("""
                UPDATE pcpm_equipamentos
                SET status_localizacao = %s
                WHERE id = %s
            """, (
                novo_status,
                equipamento_id
            ))

            conn.commit()
            flash('Movimentação registrada com sucesso!', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Erro ao registrar movimentação: {e}', 'danger')

        finally:
            conn.close()

        return redirect(url_for('main.pcpm_movimentacao'))

    # ==========================================================
    # PCP-M - PAINEL DE MOVIMENTAÇÕES
    # ==========================================================

    @blueprint.route('/pcpm_painel_movimentacoes', methods=['GET'])
    @login_required
    @module_required('acesso_pcpm')
    def pcpm_painel_movimentacoes():


        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.args.get('limpar'):
            conn.close()
            return redirect(url_for('main.pcpm_painel_movimentacoes'))

        page = request.args.get('page', 1, type=int)
        per_page = 20
        offset = (page - 1) * per_page

        filtros = {
            'codigo_frota': (request.args.get('codigo_frota') or '').strip().upper(),
            'tipo_equipamento_id': request.args.get('tipo_equipamento_id') or '',
            'status_localizacao': request.args.get('status_localizacao') or '',
            'sort': request.args.get('sort', 'codigo_frota'),
            'order': request.args.get('order', 'asc')
        }

        sort = filtros['sort']
        order = filtros['order']

        colunas_validas = {
            'codigo_frota': 'e.codigo_frota',
            'tipo_nome': 'te.nome',
            'status_localizacao': 'e.status_localizacao',
            'ultima_movimentacao_data': 'mov.criado_em'
        }

        if sort not in colunas_validas:
            sort = 'codigo_frota'

        if order not in ['asc', 'desc']:
            order = 'asc'

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

        where = ["e.ativo = 1"]
        params = []

        if filtros['codigo_frota']:
            where.append("e.codigo_frota LIKE %s")
            params.append(f"%{filtros['codigo_frota']}%")

        if filtros['tipo_equipamento_id']:
            where.append("e.tipo_equipamento_id = %s")
            params.append(filtros['tipo_equipamento_id'])

        if filtros['status_localizacao']:
            where.append("e.status_localizacao = %s")
            params.append(filtros['status_localizacao'])

        where_sql = "WHERE " + " AND ".join(where)

        cursor.execute(f"""
            SELECT COUNT(*) AS total
            FROM pcpm_equipamentos e
            JOIN pcpm_tipos_equipamento te
                ON te.id = e.tipo_equipamento_id
            {where_sql}
        """, params)

        total_registros = cursor.fetchone()['total']
        total_paginas = (total_registros + per_page - 1) // per_page

        params_paginacao = params + [per_page, offset]

        cursor.execute(f"""
            SELECT
                e.id,
                e.codigo_frota,
                e.marca,
                e.modelo,
                e.status_localizacao,

                te.nome AS tipo_nome,
                te.tag AS tipo_tag,

                mov.id AS ultima_movimentacao_id,
                mov.tipo_movimentacao,
                mov.motivo_movimentacao,

                DATE_FORMAT(
                    mov.criado_em,
                    '%d/%m/%Y %H:%i'
                ) AS ultima_movimentacao_data,

                u.nome AS funcionario_nome,
                p.nome AS cliente_nome

            FROM pcpm_equipamentos e

            JOIN pcpm_tipos_equipamento te
                ON te.id = e.tipo_equipamento_id

            LEFT JOIN pcpm_movimentacoes mov
                ON mov.id = (
                    SELECT m2.id
                    FROM pcpm_movimentacoes m2
                    WHERE m2.equipamento_id = e.id
                      AND m2.ativo = 1
                    ORDER BY m2.id DESC
                    LIMIT 1
                )

            LEFT JOIN usuarios u
                ON u.id = mov.funcionario_id

            LEFT JOIN pcpm_pessoas p
                ON p.id = mov.cliente_id

            {where_sql}

            ORDER BY
                {colunas_validas[sort]} {order.upper()},
                e.codigo_frota ASC

            LIMIT %s OFFSET %s
        """, params_paginacao)

        equipamentos = cursor.fetchall()

        for equipamento in equipamentos:
            status = equipamento.get('status_localizacao') or 'indefinido'

            if status == 'area':
                equipamento['status_descricao'] = 'Na área'
                equipamento['proxima_acao'] = 'Retirada da área'
                equipamento['tipo_movimentacao_permitido'] = 'retirada'

            elif status == 'tradimaq':
                equipamento['status_descricao'] = 'Em posse da Tradimaq'
                equipamento['proxima_acao'] = 'Entrega na área'
                equipamento['tipo_movimentacao_permitido'] = 'entrega'

            else:
                equipamento['status_descricao'] = 'Sem histórico'
                equipamento['proxima_acao'] = 'Primeira movimentação'
                equipamento['tipo_movimentacao_permitido'] = None

        conn.close()

        return render_template(
            'pcpm_painel_movimentacoes.html',
            equipamentos=equipamentos,
            tipos_equipamento=tipos_equipamento,
            filtros=filtros,
            page=page,
            total_paginas=total_paginas,
            total_registros=total_registros
        )

    # ==========================================================
    # PCP-M - VISUALIZAR MOVIMENTAÇÃO
    # ==========================================================

    @blueprint.route('/visualizar_pcpm_movimentacao/<int:movimentacao_id>', methods=['GET'])
    @login_required
    @module_required('acesso_pcpm')
    def visualizar_pcpm_movimentacao(movimentacao_id):


        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                mov.id,
                mov.equipamento_id,
                mov.cliente_id,
                mov.funcionario_id,
                mov.tipo_movimentacao,
                mov.motivo_movimentacao,
                mov.numero_os,
                mov.horimetro,
                mov.descricao_anomalia,
                mov.rfid_funcionario,
                mov.rfid_cliente,
                mov.latitude,
                mov.longitude,
                DATE_FORMAT(mov.criado_em, '%d/%m/%Y %H:%i') AS criado_em_formatado,

                e.codigo_frota,
                e.marca,
                e.modelo,
                te.nome AS tipo_equipamento,
                te.tag AS tipo_tag,

                func.nome AS funcionario_nome,
                func.matricula AS funcionario_matricula,

                cli.nome AS cliente_nome,
                cli.matricula AS cliente_matricula,
                cli.setor_area AS cliente_setor_area,
                emp.nome AS cliente_empresa,

                criador.nome AS criado_por_nome

            FROM pcpm_movimentacoes mov

            JOIN pcpm_equipamentos e
                ON e.id = mov.equipamento_id

            JOIN pcpm_tipos_equipamento te
                ON te.id = e.tipo_equipamento_id

            LEFT JOIN usuarios func
                ON func.id = mov.funcionario_id

            LEFT JOIN pcpm_pessoas cli
                ON cli.id = mov.cliente_id

            LEFT JOIN pcpm_empresas emp
                ON emp.id = cli.empresa_id

            LEFT JOIN usuarios criador
                ON criador.id = mov.criado_por

            WHERE mov.id = %s
              AND mov.ativo = 1
        """, (movimentacao_id,))

        movimentacao = cursor.fetchone()

        if not movimentacao:
            conn.close()
            flash('Movimentação não encontrada.', 'warning')
            return redirect(url_for('main.pcpm_painel_movimentacoes'))

        cursor.execute("""
            SELECT
                r.id,
                r.checklist_item_id,
                r.resultado,
                r.observacao,
                r.foto_path,
                r.item_snapshot,
                r.criterio_snapshot,
                r.ordem_snapshot

            FROM pcpm_movimentacao_checklist_respostas r

            WHERE r.movimentacao_id = %s

            ORDER BY r.ordem_snapshot ASC
        """, (movimentacao_id,))

        respostas = cursor.fetchall()

        conn.close()

        return render_template(
            'visualizar_pcpm_movimentacao.html',
            movimentacao=movimentacao,
            respostas=respostas,
        )

    # ==========================================================
    # PCP-M - EDITAR MOVIMENTAÇÃO
    # ==========================================================

    @blueprint.route('/editar_pcpm_movimentacao/<int:movimentacao_id>', methods=['GET', 'POST'])
    @login_required
    @module_required('acesso_pcpm')
    def editar_pcpm_movimentacao(movimentacao_id):


        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # ======================================================
        # BUSCAR MOVIMENTAÇÃO
        # ======================================================

        cursor.execute("""
            SELECT
                mov.*,
                e.codigo_frota
            FROM pcpm_movimentacoes mov
            JOIN pcpm_equipamentos e
                ON e.id = mov.equipamento_id
            WHERE mov.id = %s
              AND mov.ativo = 1
        """, (movimentacao_id,))

        movimentacao = cursor.fetchone()

        if not movimentacao:
            conn.close()
            flash('Movimentação não encontrada.', 'warning')
            return redirect(url_for('main.pcpm_painel_movimentacoes'))

        # ======================================================
        # VALIDAR SE É A ÚLTIMA MOVIMENTAÇÃO
        # ======================================================

        cursor.execute("""
            SELECT id
            FROM pcpm_movimentacoes
            WHERE equipamento_id = %s
              AND ativo = 1
            ORDER BY id DESC
            LIMIT 1
        """, (movimentacao['equipamento_id'],))

        ultima_movimentacao = cursor.fetchone()

        if not ultima_movimentacao or ultima_movimentacao['id'] != movimentacao_id:
            conn.close()

            flash(
                'Somente a última movimentação do equipamento pode ser editada.',
                'warning'
            )

            return redirect(url_for('main.pcpm_painel_movimentacoes'))

        # ======================================================
        # POST
        # ======================================================

        if request.method == 'POST':

            numero_os = request.form.get('numero_os')
            horimetro = request.form.get('horimetro')
            descricao_anomalia = request.form.get('descricao_anomalia')

            try:

                cursor.execute("""
                    UPDATE pcpm_movimentacoes
                    SET
                        numero_os = %s,
                        horimetro = %s,
                        descricao_anomalia = %s
                    WHERE id = %s
                """, (
                    numero_os,
                    horimetro,
                    descricao_anomalia,
                    movimentacao_id
                ))

                conn.commit()

                flash('Movimentação atualizada com sucesso.', 'success')

                return redirect(
                    url_for(
                        'main.visualizar_pcpm_movimentacao',
                        movimentacao_id=movimentacao_id
                    )
                )

            except Exception as e:

                conn.rollback()

                flash(f'Erro ao atualizar movimentação: {e}', 'danger')

        conn.close()

        return render_template(
            'pcpm_editar_movimentacao.html',
            movimentacao=movimentacao
        )


    # ==========================================================
    # PCP-M - EXCLUIR MOVIMENTAÇÃO
    # ==========================================================

    @blueprint.route('/excluir_pcpm_movimentacao/<int:movimentacao_id>')
    @login_required
    @module_required('acesso_pcpm')
    def excluir_pcpm_movimentacao(movimentacao_id):


        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # ======================================================
        # BUSCAR MOVIMENTAÇÃO
        # ======================================================

        cursor.execute("""
            SELECT *
            FROM pcpm_movimentacoes
            WHERE id = %s
              AND ativo = 1
        """, (movimentacao_id,))

        movimentacao = cursor.fetchone()

        if not movimentacao:
            conn.close()

            flash('Movimentação não encontrada.', 'warning')

            return redirect(url_for('main.pcpm_painel_movimentacoes'))

        equipamento_id = movimentacao['equipamento_id']

        # ======================================================
        # VALIDAR ÚLTIMA MOVIMENTAÇÃO
        # ======================================================

        cursor.execute("""
            SELECT id
            FROM pcpm_movimentacoes
            WHERE equipamento_id = %s
              AND ativo = 1
            ORDER BY id DESC
            LIMIT 1
        """, (equipamento_id,))

        ultima_movimentacao = cursor.fetchone()

        if not ultima_movimentacao or ultima_movimentacao['id'] != movimentacao_id:

            conn.close()

            flash(
                'Somente a última movimentação do equipamento pode ser excluída.',
                'warning'
            )

            return redirect(url_for('main.pcpm_painel_movimentacoes'))

        try:

            # ==================================================
            # EXCLUSÃO LÓGICA
            # ==================================================

            cursor.execute("""
                UPDATE pcpm_movimentacoes
                SET ativo = 0
                WHERE id = %s
            """, (movimentacao_id,))

            # ==================================================
            # BUSCAR NOVA ÚLTIMA MOVIMENTAÇÃO
            # ==================================================

            cursor.execute("""
                SELECT *
                FROM pcpm_movimentacoes
                WHERE equipamento_id = %s
                  AND ativo = 1
                ORDER BY id DESC
                LIMIT 1
            """, (equipamento_id,))

            nova_ultima = cursor.fetchone()

            # ==================================================
            # RECALCULAR STATUS
            # ==================================================

            if nova_ultima:

                if nova_ultima['tipo_movimentacao'] == 'entrega':
                    novo_status = 'area'
                else:
                    novo_status = 'tradimaq'

            else:

                novo_status = 'indefinido'

            cursor.execute("""
                UPDATE pcpm_equipamentos
                SET status_localizacao = %s
                WHERE id = %s
            """, (
                novo_status,
                equipamento_id
            ))

            conn.commit()

            flash('Movimentação excluída com sucesso.', 'success')

        except Exception as e:

            conn.rollback()

            flash(f'Erro ao excluir movimentação: {e}', 'danger')

        conn.close()

        return redirect(url_for('main.pcpm_painel_movimentacoes'))

    # ==========================================================
    # PCP-M - LISTAR MOVIMENTAÇÕES
    # ==========================================================

    @blueprint.route('/listar_pcpm_movimentacoes', methods=['GET'])
    @login_required
    @module_required('acesso_pcpm')
    def listar_pcpm_movimentacoes():


        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.args.get('limpar'):
            conn.close()
            return redirect(url_for('main.listar_pcpm_movimentacoes'))

        page = request.args.get('page', 1, type=int)
        per_page = 20
        offset = (page - 1) * per_page

        filtros = {
            'codigo_frota': (request.args.get('codigo_frota') or '').strip().upper(),
            'tipo_movimentacao': request.args.get('tipo_movimentacao') or '',
            'data_inicio': request.args.get('data_inicio') or '',
            'data_fim': request.args.get('data_fim') or '',
            'sort': request.args.get('sort', 'criado_em'),
            'order': request.args.get('order', 'desc')
        }

        sort = filtros['sort']
        order = filtros['order']

        colunas_validas = {
            'criado_em': 'mov.criado_em',
            'codigo_frota': 'e.codigo_frota',
            'tipo_movimentacao': 'mov.tipo_movimentacao',
            'funcionario_nome': 'func.nome',
            'cliente_nome': 'cli.nome'
        }

        if sort not in colunas_validas:
            sort = 'criado_em'

        if order not in ['asc', 'desc']:
            order = 'desc'

        cursor.execute("""
            SELECT
                e.id,
                e.codigo_frota,
                e.marca,
                e.modelo,
                te.nome AS tipo_nome
            FROM pcpm_equipamentos e
            JOIN pcpm_tipos_equipamento te
                ON te.id = e.tipo_equipamento_id
            WHERE e.ativo = 1
            ORDER BY e.codigo_frota
        """)
        equipamentos = cursor.fetchall()

        where = ["mov.ativo = 1"]
        params = []

        if filtros['codigo_frota']:
            where.append("e.codigo_frota LIKE %s")
            params.append(f"%{filtros['codigo_frota']}%")

        if filtros['tipo_movimentacao']:
            where.append("mov.tipo_movimentacao = %s")
            params.append(filtros['tipo_movimentacao'])

        if filtros['data_inicio']:
            where.append("DATE(mov.criado_em) >= %s")
            params.append(filtros['data_inicio'])

        if filtros['data_fim']:
            where.append("DATE(mov.criado_em) <= %s")
            params.append(filtros['data_fim'])

        where_sql = "WHERE " + " AND ".join(where)

        cursor.execute(f"""
            SELECT COUNT(*) AS total
            FROM pcpm_movimentacoes mov

            JOIN pcpm_equipamentos e
                ON e.id = mov.equipamento_id

            LEFT JOIN usuarios func
                ON func.id = mov.funcionario_id

            LEFT JOIN pcpm_pessoas cli
                ON cli.id = mov.cliente_id

            {where_sql}
        """, params)

        total_registros = cursor.fetchone()['total']
        total_paginas = (total_registros + per_page - 1) // per_page

        params_paginacao = params + [per_page, offset]

        cursor.execute(f"""
            SELECT
                mov.id,
                mov.tipo_movimentacao,

                DATE_FORMAT(mov.criado_em, '%d/%m/%Y %H:%i') AS data_movimentacao,

                e.codigo_frota,
                te.nome AS tipo_equipamento,

                func.nome AS funcionario_nome,
                cli.nome AS cliente_nome

            FROM pcpm_movimentacoes mov

            JOIN pcpm_equipamentos e
                ON e.id = mov.equipamento_id

            JOIN pcpm_tipos_equipamento te
                ON te.id = e.tipo_equipamento_id

            LEFT JOIN usuarios func
                ON func.id = mov.funcionario_id

            LEFT JOIN pcpm_pessoas cli
                ON cli.id = mov.cliente_id

            {where_sql}

            ORDER BY {colunas_validas[sort]} {order.upper()}, mov.id DESC

            LIMIT %s OFFSET %s
        """, params_paginacao)

        movimentacoes = cursor.fetchall()

        conn.close()

        return render_template(
            'listar_pcpm_movimentacoes.html',
            movimentacoes=movimentacoes,
            equipamentos=equipamentos,
            filtros=filtros,
            page=page,
            total_paginas=total_paginas,
            total_registros=total_registros
        )


    # ===================================================================== #
    # ROTAS PARA O APLICATIVO                                               #
    # ===================================================================== #

    # ==========================================================
    # API PCP-M - TESTE
    # ==========================================================

    @blueprint.route('/api/pcpm/teste', methods=['GET'])
    @login_required
    @api_module_required('acesso_pcpm')
    def api_pcpm_teste():


        return jsonify({
            'sucesso': True,
            'mensagem': 'API PCP-M funcionando.',
            'usuario_id': session.get('usuario_id'),
            'nome': session.get('nome')
        })

    # ==========================================================
    # API PCP-M - LISTAR EQUIPAMENTOS
    # ==========================================================

    @blueprint.route('/api/pcpm/equipamentos', methods=['GET'])
    @login_required
    @api_module_required('acesso_pcpm')
    def api_pcpm_equipamentos():


        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                e.id,
                e.codigo_frota,
                e.marca,
                e.modelo,
                e.status_localizacao,
                te.tag AS tipo_tag,
                te.nome AS tipo_nome
            FROM pcpm_equipamentos e
            JOIN pcpm_tipos_equipamento te
                ON te.id = e.tipo_equipamento_id
            WHERE e.ativo = 1
            ORDER BY e.codigo_frota
        """)

        equipamentos = cursor.fetchall()

        conn.close()

        return jsonify({
            'sucesso': True,
            'total': len(equipamentos),
            'equipamentos': equipamentos
        })

    # ==========================================================
    # API PCP-M - CHECKLIST DO EQUIPAMENTO
    # ==========================================================

    @blueprint.route('/api/pcpm/checklist/<int:equipamento_id>', methods=['GET'])
    @login_required
    @api_module_required('acesso_pcpm')
    def api_pcpm_checklist(equipamento_id):


        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                e.id,
                e.codigo_frota,
                e.status_localizacao,
                e.marca,
                e.modelo,
                e.tipo_equipamento_id,
                te.tag AS tipo_tag,
                te.nome AS tipo_nome
            FROM pcpm_equipamentos e
            JOIN pcpm_tipos_equipamento te
                ON te.id = e.tipo_equipamento_id
            WHERE e.id = %s
              AND e.ativo = 1
        """, (equipamento_id,))

        equipamento = cursor.fetchone()

        if not equipamento:
            conn.close()
            return jsonify({
                'sucesso': False,
                'mensagem': 'Equipamento não encontrado.'
            }), 404

        status = equipamento.get('status_localizacao') or 'indefinido'

        if status == 'area':
            tipo_movimentacao_permitido = 'retirada'
        elif status == 'tradimaq':
            tipo_movimentacao_permitido = 'entrega'
        else:
            tipo_movimentacao_permitido = None

        cursor.execute("""
            SELECT
                id,
                nome
            FROM pcpm_checklist_modelos
            WHERE tipo_equipamento_id = %s
              AND ativo = 1
            ORDER BY id DESC
            LIMIT 1
        """, (equipamento['tipo_equipamento_id'],))

        modelo_checklist = cursor.fetchone()

        if not modelo_checklist:
            conn.close()
            return jsonify({
                'sucesso': False,
                'mensagem': 'Nenhum modelo de checklist ativo encontrado para este tipo de equipamento.',
                'equipamento': equipamento,
                'tipo_movimentacao_permitido': tipo_movimentacao_permitido,
                'checklist': []
            }), 404

        cursor.execute("""
            SELECT
                id,
                ordem,
                item,
                criterio,
                exige_foto_nok,
                exige_observacao_nok
            FROM pcpm_checklist_itens
            WHERE modelo_id = %s
              AND ativo = 1
            ORDER BY ordem
        """, (modelo_checklist['id'],))

        checklist = cursor.fetchall()

        conn.close()

        return jsonify({
            'sucesso': True,
            'equipamento': equipamento,
            'modelo_checklist': modelo_checklist,
            'tipo_movimentacao_permitido': tipo_movimentacao_permitido,
            'checklist': checklist
        })

    # ==========================================================
    # API PCP-M - SALVAR MOVIMENTAÇÃO
    # ==========================================================

    @blueprint.route('/api/pcpm/movimentacao', methods=['POST'])
    @login_required
    @api_module_required('acesso_pcpm')
    def api_pcpm_salvar_movimentacao():


        dados = request.get_json()

        print("JSON RECEBIDO /api/pcpm/movimentacao:")
        print(dados)

        if not dados:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Nenhum JSON recebido.'
            }), 400

        offline_id = dados.get('offline_id')
        equipamento_id = dados.get('equipamento_id')
        tipo_movimentacao = dados.get('tipo_movimentacao')
        cliente_id = dados.get('cliente_id')
        horimetro = dados.get('horimetro')
        numero_os = dados.get('numero_os')
        descricao_anomalia = dados.get('descricao_anomalia')
        latitude = dados.get('latitude')
        longitude = dados.get('longitude')
        itens = dados.get('itens', [])

        rfid_funcionario = (dados.get('rfid_funcionario') or '').strip()
        rfid_cliente = (dados.get('rfid_cliente') or '').strip()

        if not equipamento_id:
            return jsonify({'sucesso': False, 'mensagem': 'Equipamento não informado.'}), 400

        if not tipo_movimentacao:
            return jsonify({'sucesso': False, 'mensagem': 'Tipo de movimentação não informado.'}), 400

        if not cliente_id and not rfid_cliente:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Cliente não informado. Informe o cliente ou leia o RFID do cliente.'
            }), 400

        if not rfid_funcionario:
            return jsonify({'sucesso': False, 'mensagem': 'RFID do funcionário não informado.'}), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            if offline_id:
                cursor.execute("""
                    SELECT id
                    FROM pcpm_movimentacoes
                    WHERE offline_id = %s
                    LIMIT 1
                """, (offline_id,))
                movimentacao_existente = cursor.fetchone()

                if movimentacao_existente:
                    conn.close()
                    return jsonify({
                        'sucesso': True,
                        'mensagem': 'Movimentação offline já sincronizada anteriormente.',
                        'movimentacao_id': movimentacao_existente['id']
                    })

            cursor.execute("""
                SELECT id, status_localizacao
                FROM pcpm_equipamentos
                WHERE id = %s
                  AND ativo = 1
            """, (equipamento_id,))
            equipamento = cursor.fetchone()

            if not equipamento:
                conn.close()
                return jsonify({'sucesso': False, 'mensagem': 'Equipamento não encontrado.'}), 404

            status_atual = equipamento['status_localizacao']

            # Para movimentação feita online, mantém a trava de status.
            # Para movimentação offline, aceita sincronizar mesmo que o status atual já tenha mudado.
            if not offline_id:
                if status_atual == 'area' and tipo_movimentacao != 'retirada':
                    conn.close()
                    return jsonify({
                        'sucesso': False,
                        'mensagem': 'Equipamento está na área e só permite retirada.'
                    }), 400

                if status_atual == 'tradimaq' and tipo_movimentacao != 'entrega':
                    conn.close()
                    return jsonify({
                        'sucesso': False,
                        'mensagem': 'Equipamento está na Tradimaq e só permite entrega.'
                    }), 400

            cursor.execute("""
                SELECT id, nome, uid_rfid
                FROM usuarios
                WHERE uid_rfid = %s
                  AND ativo = 1
                  AND tem_acesso_sistema = 1
                LIMIT 1
            """, (rfid_funcionario,))
            funcionario = cursor.fetchone()

            if not funcionario:
                conn.close()
                return jsonify({
                    'sucesso': False,
                    'mensagem': 'Funcionário não localizado pelo RFID.'
                }), 400

            funcionario_id = funcionario['id']

            cliente_cadastrado = 0
            status_sync = 'pendente_cliente'

            if cliente_id:
                cursor.execute("""
                    SELECT id
                    FROM pcpm_pessoas
                    WHERE id = %s
                      AND ativo = 1
                    LIMIT 1
                """, (cliente_id,))
                cliente = cursor.fetchone()

                if not cliente:
                    conn.close()
                    return jsonify({
                        'sucesso': False,
                        'mensagem': 'Cliente informado não encontrado.'
                    }), 400

                cliente_cadastrado = 1
                status_sync = 'sincronizado'

            else:
                cursor.execute("""
                    SELECT id
                    FROM pcpm_pessoas
                    WHERE rfid = %s
                      AND ativo = 1
                    LIMIT 1
                """, (rfid_cliente,))
                cliente = cursor.fetchone()

                if cliente:
                    cliente_id = cliente['id']
                    cliente_cadastrado = 1
                    status_sync = 'sincronizado'

            cursor.execute("""
                INSERT INTO pcpm_movimentacoes (
                    offline_id,
                    equipamento_id,
                    cliente_id,
                    funcionario_id,
                    tipo_movimentacao,
                    horimetro,
                    numero_os,
                    descricao_anomalia,
                    rfid_funcionario,
                    rfid_cliente,
                    latitude,
                    longitude,
                    status_sync,
                    cliente_cadastrado,
                    criado_por,
                    ativo
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, 1
                )
            """, (
                offline_id,
                equipamento_id,
                cliente_id,
                funcionario_id,
                tipo_movimentacao,
                horimetro,
                numero_os,
                descricao_anomalia,
                rfid_funcionario,
                rfid_cliente,
                latitude,
                longitude,
                status_sync,
                cliente_cadastrado,
                session.get('usuario_id')
            ))

            movimentacao_id = cursor.lastrowid

            for item in itens:
                item_id = item.get('item_id')
                resultado = item.get('resultado')
                observacao = item.get('observacao') or ''
                foto_path = item.get('foto_path') or ''

                cursor.execute("""
                    SELECT id, ordem, item, criterio
                    FROM pcpm_checklist_itens
                    WHERE id = %s
                      AND ativo = 1
                """, (item_id,))
                item_checklist = cursor.fetchone()

                if not item_checklist:
                    raise Exception(f'Item de checklist inválido: {item_id}')

                cursor.execute("""
                    INSERT INTO pcpm_movimentacao_checklist_respostas (
                        movimentacao_id,
                        checklist_item_id,
                        resultado,
                        observacao,
                        foto_path,
                        item_snapshot,
                        criterio_snapshot,
                        ordem_snapshot
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    movimentacao_id,
                    item_id,
                    resultado,
                    observacao,
                    foto_path,
                    item_checklist['item'],
                    item_checklist['criterio'],
                    item_checklist['ordem']
                ))

            novo_status = 'tradimaq' if tipo_movimentacao == 'retirada' else 'area'

            cursor.execute("""
                UPDATE pcpm_equipamentos
                SET status_localizacao = %s
                WHERE id = %s
            """, (novo_status, equipamento_id))

            conn.commit()
            conn.close()

            return jsonify({
                'sucesso': True,
                'mensagem': 'Movimentação registrada com sucesso.',
                'movimentacao_id': movimentacao_id,
                'novo_status': novo_status,
                'status_sync': status_sync,
                'cliente_cadastrado': cliente_cadastrado,
                'cliente_id': cliente_id,
                'funcionario_id': funcionario_id
            })

        except Exception as e:
            conn.rollback()
            conn.close()

            print("ERRO AO SALVAR MOVIMENTAÇÃO:")
            print(str(e))

            return jsonify({
                'sucesso': False,
                'mensagem': str(e)
            }), 500

    @blueprint.route('/api/pcpm/upload_foto', methods=['POST'])
    @login_required
    @api_module_required('acesso_pcpm')
    def api_pcpm_upload_foto():

        movimentacao_id = request.form.get('movimentacao_id')
        checklist_item_id = request.form.get('checklist_item_id')
        foto = request.files.get('foto')

        if not movimentacao_id:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Movimentação não informada.'
            }), 400

        if not checklist_item_id:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Item do checklist não informado.'
            }), 400

        if not foto:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Foto não enviada.'
            }), 400

        try:
            pasta_destino = os.path.join(
                current_app.root_path,
                'static',
                'evidencias',
                'pcpm'
            )

            os.makedirs(pasta_destino, exist_ok=True)

            extensao = os.path.splitext(foto.filename)[1].lower()

            if extensao not in ['.jpg', '.jpeg', '.png']:
                return jsonify({
                    'sucesso': False,
                    'mensagem': 'Formato de imagem não permitido.'
                }), 400

            try:
                validar_conteudo_upload(foto, ALLOWED_IMAGE_EXTENSIONS)
            except UploadValidationError as exc:
                return jsonify({
                    'sucesso': False,
                    'mensagem': str(exc)
                }), 400

            nome_arquivo = UploadService.salvar(
                foto,
                ALLOWED_IMAGE_EXTENSIONS,
                prefixo=f"pcpm_mov_{movimentacao_id}_item_{checklist_item_id}",
                diretorio=pasta_destino,
            )

            caminho_relativo = f"evidencias/pcpm/{nome_arquivo}"

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                UPDATE pcpm_movimentacao_checklist_respostas
                SET foto_path = %s
                WHERE movimentacao_id = %s
                  AND checklist_item_id = %s
            """, (
                caminho_relativo,
                movimentacao_id,
                checklist_item_id
            ))

            conn.commit()
            conn.close()

            return jsonify({
                'sucesso': True,
                'mensagem': 'Foto enviada com sucesso.',
                'foto_path': caminho_relativo
            })

        except Exception as e:
            return jsonify({
                'sucesso': False,
                'mensagem': str(e)
            }), 500
        
    # ==========================================================
    # API PCP-M - CONSULTAR CLIENTE POR RFID
    # ==========================================================

    @blueprint.route('/api/pcpm/cliente/rfid/<rfid>', methods=['GET'])
    @login_required
    @api_module_required('acesso_pcpm')
    def api_pcpm_cliente_por_rfid(rfid):


        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                p.id,
                p.rfid,
                p.matricula,
                p.nome,
                p.empresa_id,
                emp.nome AS empresa_nome,
                p.setor_area
            FROM pcpm_pessoas p
            LEFT JOIN pcpm_empresas emp
                ON emp.id = p.empresa_id
            WHERE p.rfid = %s
              AND p.ativo = 1
            LIMIT 1
        """, (rfid,))

        pessoa = cursor.fetchone()

        conn.close()

        if not pessoa:
            return jsonify({
                'sucesso': True,
                'encontrado': False,
                'rfid': rfid,
                'mensagem': 'Cliente não cadastrado.'
            })

        return jsonify({
            'sucesso': True,
            'encontrado': True,
            'pessoa': pessoa
        })

    # ==========================================================
    # API PCP-M - CADASTRAR CLIENTE PELO APP
    # ==========================================================

    @blueprint.route('/api/pcpm/cliente/cadastrar', methods=['POST'])
    @login_required
    @api_module_required('acesso_pcpm')
    def api_pcpm_cadastrar_cliente_app():


        dados = request.get_json()

        if not dados:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Nenhum JSON recebido.'
            }), 400

        rfid = (dados.get('rfid') or '').strip()
        matricula = (dados.get('matricula') or '').strip()
        nome = (dados.get('nome') or '').strip()
        empresa_id = dados.get('empresa_id')
        setor_area = (dados.get('setor_area') or '').strip()

        if not rfid:
            return jsonify({
                'sucesso': False,
                'mensagem': 'RFID não informado.'
            }), 400

        if not matricula:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Matrícula/registro não informado.'
            }), 400

        if not nome:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Nome não informado.'
            }), 400

        if not setor_area:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Setor/área não informado.'
            }), 400

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:

            cursor.execute("""
                SELECT id
                FROM pcpm_pessoas
                WHERE rfid = %s
                  AND ativo = 1
                LIMIT 1
            """, (rfid,))

            pessoa_existente = cursor.fetchone()

            if pessoa_existente:
                conn.close()

                return jsonify({
                    'sucesso': False,
                    'mensagem': 'Já existe cliente cadastrado com este RFID.',
                    'pessoa_id': pessoa_existente['id']
                }), 409

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

            pessoa_id = cursor.lastrowid

            conn.commit()

            return jsonify({
                'sucesso': True,
                'mensagem': 'Cliente cadastrado com sucesso.',
                'pessoa_id': pessoa_id
            })

        except Exception as e:

            conn.rollback()

            return jsonify({
                'sucesso': False,
                'mensagem': str(e)
            }), 500

        finally:
            conn.close()

    # ==========================================================
    # API PCP-M - CONSULTAR FUNCIONÁRIO POR RFID

    @blueprint.route('/api/pcpm/funcionario/rfid/<rfid>', methods=['GET'])
    @login_required
    @api_module_required('acesso_pcpm')
    def api_pcpm_funcionario_por_rfid(rfid):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id,
                nome,
                matricula,
                uid_rfid
            FROM usuarios
            WHERE uid_rfid = %s
              AND ativo = 1
              AND tem_acesso_sistema = 1
            LIMIT 1
        """, (rfid,))

        funcionario = cursor.fetchone()
        conn.close()

        if not funcionario:
            return jsonify({
                'sucesso': True,
                'encontrado': False,
                'mensagem': 'Funcionário não localizado.'
            })

        return jsonify({
            'sucesso': True,
            'encontrado': True,
            'funcionario': funcionario
        })
