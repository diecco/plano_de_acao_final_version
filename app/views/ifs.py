import json
from datetime import date, datetime

from flask import flash, redirect, render_template, request, session, url_for

from app.decorators import login_required, module_required
from app.utils.db import get_db_connection


def register_ifs_routes(blueprint):
    @blueprint.route(
        '/lancar_ifs',
        methods=['GET', 'POST']
    )
    @login_required
    @module_required('acesso_ssma')
    def lancar_ifs():

        conn = None
        cursor = None

        usuario_id = session.get('usuario_id')
        perfil = session.get('perfil')
        centro_custo_id = session.get('centro_custos_id')

        # =========================================================
        # FUNÇÕES AUXILIARES
        # =========================================================

        def obter_next_url():
            next_recebido = (
                request.form.get('next')
                if request.method == 'POST'
                else request.args.get('next')
            )

            if (
                next_recebido
                and next_recebido.startswith('/')
                and not next_recebido.startswith('//')
            ):
                return next_recebido

            return url_for('main.listar_ifs')

        def obter_agendamento_id():
            valor = (
                request.form.get('agendamento_id')
                if request.method == 'POST'
                else request.args.get('agendamento_id')
            )

            try:
                return int(valor) if valor else None
            except (TypeError, ValueError):
                return None

        next_url = obter_next_url()
        agendamento_id = obter_agendamento_id()

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            if not usuario_id:
                flash(
                    'Usuário logado não encontrado.',
                    'danger'
                )
                return redirect(
                    url_for('main.login')
                )

            if not centro_custo_id:
                flash(
                    'Não foi possível identificar o centro de custo do usuário logado.',
                    'danger'
                )
                return redirect(
                    url_for('main.dashboard')
                )

            # =====================================================
            # CARREGAR E VALIDAR AGENDAMENTO
            # =====================================================

            agendamento = None

            if agendamento_id:
                cursor.execute("""
                    SELECT
                        ag.id,
                        ag.pratica,
                        ag.lider_id,
                        ag.data_programada,
                        ag.status,
                        ag.registro_executado_id
                    FROM agendamentos_ssma ag
                    WHERE ag.id = %s
                      AND ag.lider_id = %s
                      AND ag.pratica = 'ifs'
                    LIMIT 1
                """, (
                    agendamento_id,
                    usuario_id
                ))

                agendamento = cursor.fetchone()

                if not agendamento:
                    flash(
                        'Agendamento de IFS não encontrado ou não pertence ao usuário logado.',
                        'warning'
                    )
                    return redirect(next_url)

                if agendamento.get('registro_executado_id'):
                    flash(
                        'Esta IFS agendada já foi executada.',
                        'warning'
                    )
                    return redirect(next_url)

                if agendamento.get('status') == 'cancelada':
                    flash(
                        'Não é possível executar um agendamento cancelado.',
                        'warning'
                    )
                    return redirect(next_url)

            # =====================================================
            # POST → SALVAR IFS
            # =====================================================

            if request.method == 'POST':

                profissional_sesmt_id = usuario_id

                participantes = (
                    request.form.get('participantes')
                    or ''
                ).strip()

                descricao_atividade_os = (
                    request.form.get('descricao_atividade_os')
                    or ''
                ).strip()

                local_inspecao = (
                    request.form.get('local_inspecao')
                    or ''
                ).strip()

                data_inspecao = request.form.get(
                    'data_inspecao'
                )

                hora_inspecao = request.form.get(
                    'hora_inspecao'
                )

                respostas_json = request.form.get(
                    'respostas_json'
                )

                desvios_json = request.form.get(
                    'desvios_json'
                )

                if not data_inspecao:
                    flash(
                        'Informe a data da inspeção.',
                        'warning'
                    )
                    return redirect(
                        url_for(
                            'main.lancar_ifs',
                            agendamento_id=agendamento_id or '',
                            next=next_url
                        )
                    )

                if not hora_inspecao:
                    flash(
                        'Informe a hora da inspeção.',
                        'warning'
                    )
                    return redirect(
                        url_for(
                            'main.lancar_ifs',
                            agendamento_id=agendamento_id or '',
                            next=next_url
                        )
                    )

                try:
                    respostas = (
                        json.loads(respostas_json)
                        if respostas_json
                        else []
                    )

                    desvios = (
                        json.loads(desvios_json)
                        if desvios_json
                        else []
                    )

                except json.JSONDecodeError:
                    flash(
                        'Os dados da IFS estão inválidos. Refaça o preenchimento.',
                        'danger'
                    )
                    return redirect(
                        url_for(
                            'main.lancar_ifs',
                            agendamento_id=agendamento_id or '',
                            next=next_url
                        )
                    )

                if not respostas:
                    flash(
                        'Avalie pelo menos um item da IFS.',
                        'warning'
                    )
                    return redirect(
                        url_for(
                            'main.lancar_ifs',
                            agendamento_id=agendamento_id or '',
                            next=next_url
                        )
                    )

                total_itens_avaliados = len(
                    respostas
                )

                total_nao_conformidades = sum(
                    1
                    for resposta in respostas
                    if resposta.get('resultado') == 'N'
                )

                # =================================================
                # BUSCAR OU CRIAR ORIGEM DA IFS
                # =================================================

                cursor.execute("""
                    SELECT id
                    FROM origens
                    WHERE nome = %s
                      AND centro_custos_id = %s
                      AND ativo = 1
                    LIMIT 1
                """, (
                    'IFS - Inspeção de Frente de Serviço',
                    centro_custo_id
                ))

                origem_ifs = cursor.fetchone()

                if not origem_ifs:
                    cursor.execute("""
                        INSERT INTO origens (
                            nome,
                            descricao,
                            ativo,
                            centro_custos_id
                        )
                        VALUES (%s, %s, 1, %s)
                    """, (
                        'IFS - Inspeção de Frente de Serviço',
                        'IFS - Inspeção de Frente de Serviço',
                        centro_custo_id
                    ))

                    origem_id_ifs = cursor.lastrowid

                else:
                    origem_id_ifs = origem_ifs['id']

                # =================================================
                # INSERIR INSPEÇÃO
                # =================================================

                cursor.execute("""
                    INSERT INTO ifs_inspecoes (
                        profissional_sesmt_id,
                        participantes,
                        descricao_atividade_os,
                        local_inspecao,
                        data_inspecao,
                        hora_inspecao,
                        total_itens_avaliados,
                        total_nao_conformidades,
                        criado_por
                    )
                    VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s
                    )
                """, (
                    profissional_sesmt_id,
                    participantes,
                    descricao_atividade_os,
                    local_inspecao,
                    data_inspecao,
                    hora_inspecao,
                    total_itens_avaliados,
                    total_nao_conformidades,
                    usuario_id
                ))

                inspecao_id = cursor.lastrowid

                # =================================================
                # SALVAR RESPOSTAS
                # =================================================

                for resposta in respostas:

                    item_id = resposta.get(
                        'item_id'
                    )

                    resultado = resposta.get(
                        'resultado'
                    )

                    if not item_id:
                        raise ValueError(
                            'Item inválido nas respostas da IFS.'
                        )

                    if resultado not in ['S', 'N']:
                        raise ValueError(
                            'Resultado inválido nas respostas da IFS.'
                        )

                    cursor.execute("""
                        INSERT INTO ifs_respostas (
                            inspecao_id,
                            item_id,
                            resultado
                        )
                        VALUES (%s, %s, %s)
                    """, (
                        inspecao_id,
                        item_id,
                        resultado
                    ))

                # =================================================
                # SALVAR DESVIOS E CRIAR AÇÕES
                # =================================================

                for desvio in desvios:

                    responsavel_id = desvio.get(
                        'responsavel_id'
                    )

                    if perfil in [
                        'administrador',
                        'avancado'
                    ]:
                        cursor.execute("""
                            SELECT id
                            FROM usuarios
                            WHERE id = %s
                              AND ativo = 1
                            LIMIT 1
                        """, (
                            responsavel_id,
                        ))

                    else:
                        cursor.execute("""
                            SELECT id
                            FROM usuarios
                            WHERE id = %s
                              AND ativo = 1
                              AND centro_custos_id = %s
                            LIMIT 1
                        """, (
                            responsavel_id,
                            centro_custo_id
                        ))

                    responsavel_valido = (
                        cursor.fetchone()
                    )

                    if not responsavel_valido:
                        raise ValueError(
                            'Responsável inválido para seu escopo.'
                        )

                    descricao_acao = (
                        f"IFS - Item {desvio.get('codigo')}: "
                        f"{desvio.get('descricao')}\n\n"
                        f"Desvio observado: "
                        f"{desvio.get('desvio_observado')}\n\n"
                        f"Ação proposta: "
                        f"{desvio.get('acao_proposta')}"
                    )

                    cursor.execute("""
                        INSERT INTO acoes (
                            origem_id,
                            descricao,
                            responsavel_id,
                            prazo,
                            status,
                            criado_por
                        )
                        VALUES (
                            %s,
                            %s,
                            %s,
                            %s,
                            'Não iniciada',
                            %s
                        )
                    """, (
                        origem_id_ifs,
                        descricao_acao,
                        responsavel_id,
                        desvio.get('prazo'),
                        usuario_id
                    ))

                    acao_id = cursor.lastrowid

                    cursor.execute("""
                        INSERT INTO ifs_desvios (
                            inspecao_id,
                            item_id,
                            desvio_observado,
                            acao_proposta,
                            responsavel_id,
                            prazo,
                            acao_id
                        )
                        VALUES (
                            %s, %s, %s, %s,
                            %s, %s, %s
                        )
                    """, (
                        inspecao_id,
                        desvio.get('item_id'),
                        desvio.get('desvio_observado'),
                        desvio.get('acao_proposta'),
                        responsavel_id,
                        desvio.get('prazo'),
                        acao_id
                    ))

                # =================================================
                # ATUALIZAR AGENDAMENTO
                # =================================================

                if agendamento:

                    data_programada = agendamento.get(
                        'data_programada'
                    )

                    data_realizada = datetime.strptime(
                        data_inspecao,
                        '%Y-%m-%d'
                    ).date()

                    if (
                        isinstance(
                            data_programada,
                            datetime
                        )
                    ):
                        data_programada = (
                            data_programada.date()
                        )

                    if (
                        data_programada
                        and data_realizada
                        > data_programada
                    ):
                        novo_status = (
                            'concluida_com_atraso'
                        )
                    else:
                        novo_status = 'concluida'

                    cursor.execute("""
                        UPDATE agendamentos_ssma
                        SET
                            registro_executado_id = %s,
                            status = %s,
                            houve_alteracao = 0,
                            justificativa_alteracao = NULL
                        WHERE id = %s
                          AND lider_id = %s
                          AND pratica = 'ifs'
                          AND registro_executado_id IS NULL
                          AND status <> 'cancelada'
                    """, (
                        inspecao_id,
                        novo_status,
                        agendamento_id,
                        usuario_id
                    ))

                    if cursor.rowcount != 1:
                        raise ValueError(
                            'Não foi possível atualizar o agendamento da IFS.'
                        )

                conn.commit()

                flash(
                    'IFS registrada com sucesso.',
                    'success'
                )

                return redirect(next_url)

            # =====================================================
            # GET → CARREGAR TELA
            # =====================================================

            cursor.execute("""
                SELECT
                    id,
                    nome
                FROM ifs_blocos
                WHERE ativo = 1
                ORDER BY ordem
            """)

            blocos = cursor.fetchall()

            cursor.execute("""
                SELECT
                    id,
                    bloco_id,
                    codigo,
                    descricao,
                    potencial
                FROM ifs_itens
                WHERE ativo = 1
                ORDER BY bloco_id, ordem
            """)

            itens = cursor.fetchall()

            if perfil in [
                'administrador',
                'avancado'
            ]:
                cursor.execute("""
                    SELECT
                        id,
                        nome,
                        matricula
                    FROM usuarios
                    WHERE ativo = 1
                    ORDER BY nome
                """)

            else:
                cursor.execute("""
                    SELECT
                        id,
                        nome,
                        matricula
                    FROM usuarios
                    WHERE ativo = 1
                      AND centro_custos_id = %s
                    ORDER BY nome
                """, (
                    centro_custo_id,
                ))

            usuarios = cursor.fetchall()

            cursor.execute("""
                SELECT
                    id,
                    nome,
                    matricula
                FROM usuarios
                WHERE id = %s
                LIMIT 1
            """, (
                usuario_id,
            ))

            profissional_logado = cursor.fetchone()

            itens_por_bloco = {
                bloco['id']: []
                for bloco in blocos
            }

            for item in itens:
                bloco_id = item['bloco_id']

                if bloco_id not in itens_por_bloco:
                    itens_por_bloco[bloco_id] = []

                itens_por_bloco[
                    bloco_id
                ].append(item)

            data_inicial = (
                agendamento['data_programada'].strftime(
                    '%Y-%m-%d'
                )
                if (
                    agendamento
                    and agendamento.get(
                        'data_programada'
                    )
                )
                else datetime.today().strftime(
                    '%Y-%m-%d'
                )
            )

            hora_inicial = datetime.now().strftime(
                '%H:%M'
            )

            return render_template(
                'lancar_ifs.html',
                blocos=blocos,
                itens_por_bloco=itens_por_bloco,
                usuarios=usuarios,
                profissional_logado=profissional_logado,
                agendamento_id=agendamento_id,
                agendamento=agendamento,
                next_url=next_url,
                data_inicial=data_inicial,
                hora_inicial=hora_inicial
            )

        except ValueError as e:
            if conn:
                conn.rollback()

            flash(
                str(e),
                'danger'
            )

            return redirect(
                url_for(
                    'main.lancar_ifs',
                    agendamento_id=agendamento_id or '',
                    next=next_url
                )
            )

        except Exception as e:
            if conn:
                conn.rollback()

            flash(
                f'Erro ao registrar a IFS: {e}',
                'danger'
            )

            return redirect(
                url_for(
                    'main.lancar_ifs',
                    agendamento_id=agendamento_id or '',
                    next=next_url
                )
            )

        finally:
            if cursor:
                try:
                    cursor.close()
                except Exception:
                    pass

            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

    @blueprint.route('/listar_ifs', methods=['GET'])
    @login_required
    @module_required('acesso_ssma')
    def listar_ifs():

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        usuario_id = session.get('usuario_id')
        perfil = session.get('perfil')
        centro_custo_id = session.get('centro_custos_id')

        # 🔹 limpar filtros
        if request.args.get('limpar'):
            conn.close()
            return redirect(url_for('main.listar_ifs'))

        # 🔹 filtros
        profissional_sesmt_id = request.args.get('profissional_sesmt_id', '').strip()
        local_inspecao = request.args.get('local_inspecao', '').strip()
        data_inicio = request.args.get('data_inicio', '').strip()
        data_fim = request.args.get('data_fim', '').strip()

        # 🔹 paginação
        page = request.args.get('page', 1, type=int)
        per_page = 20

        if page < 1:
            page = 1

        offset = (page - 1) * per_page

        # 🔹 filtros SQL
        filtros_sql = ["ifs.ativo = 1"]
        params = []

        # 🔒 CONTROLE DE ESCOPO
        if perfil == 'basico':
            filtros_sql.append("ifs.criado_por = %s")
            params.append(usuario_id)

        elif perfil == 'intermediario':
            filtros_sql.append("u.centro_custos_id = %s")
            params.append(centro_custo_id)

        # avançado e administrador veem tudo

        if profissional_sesmt_id:
            filtros_sql.append("ifs.profissional_sesmt_id = %s")
            params.append(profissional_sesmt_id)

        if local_inspecao:
            filtros_sql.append("ifs.local_inspecao LIKE %s")
            params.append(f"%{local_inspecao}%")

        if data_inicio:
            filtros_sql.append("ifs.data_inspecao >= %s")
            params.append(data_inicio)

        if data_fim:
            filtros_sql.append("ifs.data_inspecao <= %s")
            params.append(data_fim)

        where_clause = "WHERE " + " AND ".join(filtros_sql)

        # 🔹 base da query
        base_from = f"""
            FROM ifs_inspecoes ifs
            JOIN usuarios u
                ON u.id = ifs.profissional_sesmt_id
            {where_clause}
        """

        # 🔹 total de registros
        cursor.execute(f"""
            SELECT COUNT(*) AS total
            {base_from}
        """, params)

        total_registros = cursor.fetchone()['total']
        total_paginas = (total_registros + per_page - 1) // per_page

        if total_paginas > 0 and page > total_paginas:
            page = total_paginas
            offset = (page - 1) * per_page

        # 🔹 query principal
        cursor.execute(f"""
            SELECT
                ifs.id,
                ifs.data_inspecao,
                ifs.hora_inspecao,
                ifs.local_inspecao,
                ifs.descricao_atividade_os,
                ifs.total_itens_avaliados,
                ifs.total_nao_conformidades,
                ifs.criado_por,

                u.nome AS profissional_sesmt_nome

            {base_from}
            ORDER BY ifs.data_inspecao DESC, ifs.id DESC
            LIMIT %s OFFSET %s
        """, params + [per_page, offset])

        inspecoes = cursor.fetchall()

        # 🔹 usuários (para filtro)
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
            """, (centro_custo_id,))

        usuarios = cursor.fetchall()

        conn.close()

        # 🔹 filtros para manter estado na tela
        filtros = {
            'profissional_sesmt_id': profissional_sesmt_id,
            'local_inspecao': local_inspecao,
            'data_inicio': data_inicio,
            'data_fim': data_fim
        }

        return render_template(
            'listar_ifs.html',
            inspecoes=inspecoes,
            usuarios=usuarios,
            filtros=filtros,
            page=page,
            per_page=per_page,
            total_registros=total_registros,
            total_paginas=total_paginas
        )

    @blueprint.route('/excluir_ifs/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_ssma')
    def excluir_ifs(id):

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        inspecao = pode_acessar_ssma(cursor, 'ifs', id)

        if not inspecao:
            conn.close()
            flash('IFS não encontrada ou você não possui permissão para excluí-la.', 'warning')
            return redirect(url_for('main.listar_ifs'))

        # Regra adicional: somente administrador ou quem criou pode excluir
        if inspecao['criado_por'] != session.get('usuario_id') and session.get('perfil') != 'administrador':
            conn.close()
            flash('Você não tem permissão para excluir esta IFS.', 'danger')
            return redirect(url_for('main.listar_ifs'))

        cursor.execute("""
            UPDATE ifs_inspecoes
            SET ativo = 0,
                atualizado_em = NOW()
            WHERE id = %s
        """, (id,))

        conn.commit()
        conn.close()

        flash('IFS excluída com sucesso.', 'success')
        return redirect(url_for('main.listar_ifs'))

    @blueprint.route('/editar_ifs/<int:id>', methods=['GET', 'POST'])
    @login_required
    @module_required('acesso_ssma')
    def editar_ifs(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        usuario_id = session.get('usuario_id')
        perfil = session.get('perfil')
        centro_custo_id = session.get('centro_custos_id')

        inspecao = pode_acessar_ssma(cursor, 'ifs', id)

        if not inspecao:
            conn.close()
            flash('IFS não encontrada ou você não possui permissão para acessá-la.', 'warning')
            return redirect(url_for('main.listar_ifs'))

        if inspecao['criado_por'] != usuario_id and perfil != 'administrador':
            conn.close()
            flash('Você não tem permissão para editar esta IFS.', 'danger')
            return redirect(url_for('main.listar_ifs'))

        if request.method == 'POST':
            profissional_sesmt_id = usuario_id
            participantes = request.form.get('participantes')
            descricao_atividade_os = request.form.get('descricao_atividade_os')
            local_inspecao = request.form.get('local_inspecao')
            data_inspecao = request.form.get('data_inspecao')
            hora_inspecao = request.form.get('hora_inspecao')

            respostas_json = request.form.get('respostas_json')
            desvios_json = request.form.get('desvios_json')

            respostas = json.loads(respostas_json) if respostas_json else []
            desvios = json.loads(desvios_json) if desvios_json else []

            total_itens_avaliados = len(respostas)
            total_nao_conformidades = sum(1 for r in respostas if r.get('resultado') == 'N')

            cursor.execute("""
                UPDATE ifs_inspecoes
                SET profissional_sesmt_id = %s,
                    participantes = %s,
                    descricao_atividade_os = %s,
                    local_inspecao = %s,
                    data_inspecao = %s,
                    hora_inspecao = %s,
                    total_itens_avaliados = %s,
                    total_nao_conformidades = %s,
                    atualizado_em = NOW()
                WHERE id = %s
            """, (
                profissional_sesmt_id,
                participantes,
                descricao_atividade_os,
                local_inspecao,
                data_inspecao,
                hora_inspecao,
                total_itens_avaliados,
                total_nao_conformidades,
                id
            ))

            cursor.execute("DELETE FROM ifs_respostas WHERE inspecao_id = %s", (id,))

            for r in respostas:
                cursor.execute("""
                    INSERT INTO ifs_respostas (inspecao_id, item_id, resultado)
                    VALUES (%s, %s, %s)
                """, (id, r.get('item_id'), r.get('resultado')))

            cursor.execute("SELECT * FROM ifs_desvios WHERE inspecao_id = %s", (id,))
            desvios_existentes_lista = cursor.fetchall()

            desvios_existentes = {
                str(d['item_id']): d for d in desvios_existentes_lista
            }

            novos_item_ids = [str(d.get('item_id')) for d in desvios]

            if novos_item_ids:
                placeholders = ','.join(['%s'] * len(novos_item_ids))
                cursor.execute(f"""
                    DELETE FROM ifs_desvios
                    WHERE inspecao_id = %s
                      AND item_id NOT IN ({placeholders})
                """, [id] + novos_item_ids)
            else:
                cursor.execute("DELETE FROM ifs_desvios WHERE inspecao_id = %s", (id,))

            cursor.execute("""
                SELECT id
                FROM origens
                WHERE nome = 'IFS - Inspeção de Frente de Serviço'
                  AND centro_custos_id = %s
                  AND ativo = 1
                LIMIT 1
            """, (centro_custo_id,))
            origem_ifs = cursor.fetchone()

            if not origem_ifs:
                cursor.execute("""
                    INSERT INTO origens (nome, descricao, ativo, centro_custos_id)
                    VALUES (%s, %s, 1, %s)
                """, (
                    'IFS - Inspeção de Frente de Serviço',
                    'IFS - Inspeção de Frente de Serviço',
                    centro_custo_id
                ))
                origem_id_ifs = cursor.lastrowid
            else:
                origem_id_ifs = origem_ifs['id']

            for d in desvios:
                responsavel_id = d.get('responsavel_id')

                if perfil in ['administrador', 'avancado']:
                    cursor.execute("""
                        SELECT id
                        FROM usuarios
                        WHERE id = %s
                          AND ativo = 1
                    """, (responsavel_id,))
                else:
                    cursor.execute("""
                        SELECT id
                        FROM usuarios
                        WHERE id = %s
                          AND ativo = 1
                          AND centro_custos_id = %s
                    """, (responsavel_id, centro_custo_id))

                if not cursor.fetchone():
                    conn.rollback()
                    conn.close()
                    flash('Responsável inválido para seu escopo.', 'danger')
                    return redirect(url_for('main.editar_ifs', id=id))

                item_id = str(d.get('item_id'))

                descricao_acao = (
                    f"IFS - Item {d.get('codigo')}: {d.get('descricao')}\n\n"
                    f"Desvio observado: {d.get('desvio_observado')}\n\n"
                    f"Ação proposta: {d.get('acao_proposta')}"
                )

                desvio_existente = desvios_existentes.get(item_id)

                if desvio_existente:
                    acao_id = desvio_existente.get('acao_id')

                    cursor.execute("""
                        UPDATE ifs_desvios
                        SET desvio_observado = %s,
                            acao_proposta = %s,
                            responsavel_id = %s,
                            prazo = %s
                        WHERE id = %s
                    """, (
                        d.get('desvio_observado'),
                        d.get('acao_proposta'),
                        responsavel_id,
                        d.get('prazo'),
                        desvio_existente['id']
                    ))

                    if acao_id:
                        cursor.execute("""
                            UPDATE acoes
                            SET origem_id = %s,
                                descricao = %s,
                                responsavel_id = %s,
                                prazo = %s
                            WHERE id = %s
                        """, (
                            origem_id_ifs,
                            descricao_acao,
                            responsavel_id,
                            d.get('prazo'),
                            acao_id
                        ))

                else:
                    cursor.execute("""
                        INSERT INTO acoes (
                            origem_id,
                            descricao,
                            responsavel_id,
                            prazo,
                            status,
                            criado_por
                        )
                        VALUES (%s, %s, %s, %s, 'Não iniciada', %s)
                    """, (
                        origem_id_ifs,
                        descricao_acao,
                        responsavel_id,
                        d.get('prazo'),
                        usuario_id
                    ))

                    acao_id = cursor.lastrowid

                    cursor.execute("""
                        INSERT INTO ifs_desvios (
                            inspecao_id,
                            item_id,
                            desvio_observado,
                            acao_proposta,
                            responsavel_id,
                            prazo,
                            acao_id
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        id,
                        d.get('item_id'),
                        d.get('desvio_observado'),
                        d.get('acao_proposta'),
                        responsavel_id,
                        d.get('prazo'),
                        acao_id
                    ))

            conn.commit()
            conn.close()

            flash('IFS atualizada com sucesso.', 'success')
            return redirect(url_for('main.listar_ifs'))

        # =========================================================
        # GET → CARREGAR TELA
        # =========================================================

        cursor.execute("""
            SELECT id, nome
            FROM ifs_blocos
            WHERE ativo = 1
            ORDER BY ordem
        """)
        blocos = cursor.fetchall()

        cursor.execute("""
            SELECT id, bloco_id, codigo, descricao, potencial
            FROM ifs_itens
            WHERE ativo = 1
            ORDER BY bloco_id, ordem
        """)
        itens = cursor.fetchall()

        cursor.execute("""
            SELECT item_id, resultado
            FROM ifs_respostas
            WHERE inspecao_id = %s
        """, (id,))
        respostas_lista = cursor.fetchall()

        respostas_por_item = {
            str(r['item_id']): r['resultado'] for r in respostas_lista
        }

        cursor.execute("""
            SELECT
                d.id,
                d.inspecao_id,
                d.item_id,
                d.desvio_observado,
                d.acao_proposta,
                d.responsavel_id,
                DATE_FORMAT(d.prazo, '%Y-%m-%d') AS prazo,
                d.acao_id,
                i.codigo,
                i.descricao,
                i.potencial,
                i.bloco_id
            FROM ifs_desvios d
            JOIN ifs_itens i ON i.id = d.item_id
            WHERE d.inspecao_id = %s
        """, (id,))
        desvios_lista = cursor.fetchall()

        desvios_por_item = {
            str(d['item_id']): d for d in desvios_lista
        }

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
            """, (centro_custo_id,))

        usuarios = cursor.fetchall()

        conn.close()

        itens_por_bloco = {}

        for bloco in blocos:
            itens_por_bloco[bloco['id']] = []

        for item in itens:
            itens_por_bloco[item['bloco_id']].append(item)

        return render_template(
            'editar_ifs.html',
            inspecao=inspecao,
            blocos=blocos,
            itens_por_bloco=itens_por_bloco,
            respostas_por_item=respostas_por_item,
            desvios_por_item=desvios_por_item,
            usuarios=usuarios
        )

