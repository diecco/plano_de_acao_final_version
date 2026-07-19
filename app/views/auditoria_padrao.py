import json
import os
from datetime import date, datetime, timedelta

from flask import flash, redirect, render_template, request, session, url_for

from app.decorators import login_required, module_required
from app.utils.db import get_db_connection


def register_auditoria_padrao_routes(blueprint):
    @blueprint.route("/lancar_ap", methods=["GET", "POST"])
    @login_required
    @module_required("acesso_ssma")
    def lancar_ap():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        usuario_id = session.get("usuario_id")
        perfil = (session.get("perfil") or "").strip().lower()
        centro_custos_id = session.get("centro_custos_id")

        # =====================================================
        # FUNÇÕES AUXILIARES
        # =====================================================

        def fechar_conexao():
            try:
                cursor.close()
            except Exception:
                pass

            try:
                conn.close()
            except Exception:
                pass

        def validar_next_url(valor):
            valor = (valor or "").strip()

            if valor.startswith("/") and not valor.startswith("//"):
                return valor

            return url_for("main.listar_ap")

        def buscar_agendamento(agendamento_id):
            if not agendamento_id:
                return None

            cursor.execute("""
                SELECT
                    ag.id,
                    ag.pratica,
                    ag.lider_id,
                    ag.data_programada,
                    ag.colaborador_previsto_id,
                    ag.procedimento_id,
                    ag.status,
                    ag.registro_executado_id,
                    ag.houve_alteracao,
                    ag.justificativa_alteracao
                FROM agendamentos_ssma ag
                WHERE ag.id = %s
                  AND ag.lider_id = %s
                  AND ag.pratica = 'auditoria_padrao'
            """, (
                agendamento_id,
                usuario_id
            ))

            return cursor.fetchone()

        def montar_url_retorno_formulario(
            agendamento_id=None,
            auditado_id=None,
            procedimento_id=None,
            next_url=None
        ):
            parametros = {}

            if agendamento_id:
                parametros["agendamento_id"] = agendamento_id

            if auditado_id:
                parametros["auditado_id"] = auditado_id

            if procedimento_id:
                parametros["procedimento_id"] = procedimento_id

            if next_url:
                parametros["next"] = next_url

            return url_for(
                "main.lancar_ap",
                **parametros
            )

        # =====================================================
        # VALIDAR USUÁRIO
        # =====================================================

        if not usuario_id:
            fechar_conexao()

            flash(
                "Não foi possível identificar o usuário logado.",
                "danger"
            )

            return redirect(
                url_for("main.login")
            )

        # =====================================================
        # CONTEXTO DO AGENDAMENTO
        # =====================================================

        next_url = validar_next_url(
            request.values.get("next")
        )

        agendamento_id = request.values.get(
            "agendamento_id",
            type=int
        )

        agendamento = buscar_agendamento(
            agendamento_id
        )

        if agendamento_id and not agendamento:
            fechar_conexao()

            flash(
                "Agendamento não encontrado, fora do seu acesso "
                "ou incompatível com Auditoria de Padrão.",
                "warning"
            )

            return redirect(
                url_for("main.meu_calendario_ssma")
            )

        if agendamento:
            if agendamento.get("registro_executado_id"):
                fechar_conexao()

                flash(
                    "Esta Auditoria de Padrão já foi executada.",
                    "warning"
                )

                return redirect(next_url)

            if agendamento.get("status") == "cancelada":
                fechar_conexao()

                flash(
                    "Não é possível executar um agendamento cancelado.",
                    "warning"
                )

                return redirect(next_url)

        # =====================================================
        # POST
        # =====================================================

        if request.method == "POST":
            try:
                auditor_id = usuario_id

                auditado_id = request.form.get(
                    "auditado_id",
                    type=int
                )

                area_auditada = (
                    request.form.get("area_auditada")
                    or ""
                ).strip()

                data_auditoria = request.form.get(
                    "data_auditoria"
                )

                atividade_auditada = (
                    request.form.get("atividade_auditada")
                    or ""
                ).strip()

                procedimento_id = request.form.get(
                    "procedimento_id",
                    type=int
                )

                procedimento_revisao_id = request.form.get(
                    "procedimento_revisao_id",
                    type=int
                )

                pontos_observados = (
                    request.form.get("pontos_observados")
                    or ""
                ).strip() or None

                justificativa_alteracao = (
                    request.form.get(
                        "justificativa_alteracao"
                    )
                    or ""
                ).strip()

                criado_por = usuario_id

                auditado_previsto_id = (
                    agendamento.get(
                        "colaborador_previsto_id"
                    )
                    if agendamento
                    else None
                )

                procedimento_previsto_id = (
                    agendamento.get(
                        "procedimento_id"
                    )
                    if agendamento
                    else None
                )

                if not (
                    auditado_id
                    and area_auditada
                    and data_auditoria
                    and atividade_auditada
                    and procedimento_id
                    and procedimento_revisao_id
                ):
                    flash(
                        "Preencha todos os campos obrigatórios.",
                        "danger"
                    )

                    fechar_conexao()

                    return redirect(
                        montar_url_retorno_formulario(
                            agendamento_id=agendamento_id,
                            auditado_id=(
                                auditado_previsto_id
                                or auditado_id
                            ),
                            procedimento_id=(
                                procedimento_previsto_id
                                or procedimento_id
                            ),
                            next_url=next_url
                        )
                    )

                # =============================================
                # VALIDAR AUDITADO
                # =============================================

                if perfil in {
                    "administrador",
                    "avancado"
                }:
                    cursor.execute("""
                        SELECT
                            id,
                            nome,
                            matricula
                        FROM usuarios
                        WHERE id = %s
                          AND ativo = 1
                    """, (auditado_id,))

                else:
                    cursor.execute("""
                        SELECT
                            id,
                            nome,
                            matricula
                        FROM usuarios
                        WHERE id = %s
                          AND ativo = 1
                          AND centro_custos_id = %s
                    """, (
                        auditado_id,
                        centro_custos_id
                    ))

                usuario_valido = cursor.fetchone()

                if not usuario_valido:
                    flash(
                        "Usuário auditado inválido para seu escopo.",
                        "danger"
                    )

                    fechar_conexao()

                    return redirect(
                        montar_url_retorno_formulario(
                            agendamento_id=agendamento_id,
                            auditado_id=(
                                auditado_previsto_id
                                or auditado_id
                            ),
                            procedimento_id=(
                                procedimento_previsto_id
                                or procedimento_id
                            ),
                            next_url=next_url
                        )
                    )

                # =============================================
                # VALIDAR PROCEDIMENTO E REVISÃO
                # =============================================

                cursor.execute("""
                    SELECT
                        p.id AS procedimento_id,
                        pr.id AS revisao_id
                    FROM procedimentos p
                    JOIN procedimento_revisoes pr
                        ON pr.procedimento_id = p.id
                    WHERE p.id = %s
                      AND pr.id = %s
                      AND pr.vigente = 1
                """, (
                    procedimento_id,
                    procedimento_revisao_id
                ))

                procedimento_valido = cursor.fetchone()

                if not procedimento_valido:
                    flash(
                        "Procedimento ou revisão vigente inválidos.",
                        "warning"
                    )

                    fechar_conexao()

                    return redirect(
                        montar_url_retorno_formulario(
                            agendamento_id=agendamento_id,
                            auditado_id=(
                                auditado_previsto_id
                                or auditado_id
                            ),
                            procedimento_id=(
                                procedimento_previsto_id
                                or procedimento_id
                            ),
                            next_url=next_url
                        )
                    )

                # =============================================
                # COMPARAR COM O AGENDAMENTO
                # =============================================

                houve_alteracao = 0

                if agendamento:
                    if (
                        auditado_previsto_id
                        and int(auditado_id)
                        != int(auditado_previsto_id)
                    ):
                        houve_alteracao = 1

                    if (
                        procedimento_previsto_id
                        and int(procedimento_id)
                        != int(procedimento_previsto_id)
                    ):
                        houve_alteracao = 1

                    if (
                        houve_alteracao
                        and not justificativa_alteracao
                    ):
                        flash(
                            "Houve alteração em relação ao agendamento. "
                            "Informe a justificativa antes de salvar.",
                            "warning"
                        )

                        fechar_conexao()

                        return redirect(
                            montar_url_retorno_formulario(
                                agendamento_id=agendamento_id,
                                auditado_id=auditado_id,
                                procedimento_id=procedimento_id,
                                next_url=next_url
                            )
                        )

                # =============================================
                # BUSCAR/CRIAR ORIGEM AP
                # =============================================

                cursor.execute("""
                    SELECT id
                    FROM origens
                    WHERE descricao = %s
                      AND centro_custos_id = %s
                      AND ativo = 1
                    LIMIT 1
                """, (
                    "Auditoria de Padrão",
                    centro_custos_id
                ))

                origem = cursor.fetchone()

                if origem:
                    origem_ap_id = origem["id"]

                else:
                    cursor.execute("""
                        INSERT INTO origens (
                            nome,
                            descricao,
                            centro_custos_id,
                            ativo
                        )
                        VALUES (%s, %s, %s, 1)
                    """, (
                        "Auditoria de Padrão",
                        "Auditoria de Padrão",
                        centro_custos_id
                    ))

                    origem_ap_id = cursor.lastrowid

                # =============================================
                # INSERIR AUDITORIA
                # =============================================

                cursor.execute("""
                    INSERT INTO auditorias_padrao (
                        auditor_id,
                        auditado_id,
                        area_auditada,
                        data_auditoria,
                        atividade_auditada,
                        procedimento_id,
                        procedimento_revisao_id,
                        pontos_observados,
                        criado_por
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                """, (
                    auditor_id,
                    auditado_id,
                    area_auditada,
                    data_auditoria,
                    atividade_auditada,
                    procedimento_id,
                    procedimento_revisao_id,
                    pontos_observados,
                    criado_por
                ))

                auditoria_id = cursor.lastrowid

                # =============================================
                # SALVAR CHECKLIST
                # =============================================

                for i in range(1, 11):
                    item_texto = request.form.get(
                        f"item_texto_{i}"
                    )

                    resultado = request.form.get(
                        f"resultado_{i}"
                    )

                    if resultado not in {
                        "C",
                        "NC",
                        "NA"
                    }:
                        raise ValueError(
                            f"Resultado inválido no item {i}."
                        )

                    cursor.execute("""
                        INSERT INTO auditoria_padrao_respostas (
                            auditoria_id,
                            numero_item,
                            item_verificacao,
                            resultado
                        )
                        VALUES (%s, %s, %s, %s)
                    """, (
                        auditoria_id,
                        i,
                        item_texto,
                        resultado
                    ))

                # =============================================
                # DESVIOS
                # =============================================

                desvios_json = request.form.get(
                    "desvios_json"
                )

                if desvios_json:
                    desvios = json.loads(
                        desvios_json
                    )

                    for desvio in desvios:
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
                            origem_ap_id,
                            (
                                "Desvio AP - Item "
                                f"{desvio['numero_item']}: "
                                f"{desvio['acao_proposta']}"
                            ),
                            desvio["responsavel_id"],
                            desvio["prazo"],
                            criado_por
                        ))

                        acao_id = cursor.lastrowid

                        cursor.execute("""
                            INSERT INTO auditoria_padrao_desvios (
                                auditoria_id,
                                numero_item,
                                desvio_observado,
                                acao_proposta,
                                responsavel_id,
                                prazo,
                                acao_id
                            )
                            VALUES (
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                %s
                            )
                        """, (
                            auditoria_id,
                            desvio["numero_item"],
                            desvio["desvio_observado"],
                            desvio["acao_proposta"],
                            desvio["responsavel_id"],
                            desvio["prazo"],
                            acao_id
                        ))

                # =============================================
                # SOLICITAÇÃO DE REVISÃO
                # =============================================

                revisao_json = request.form.get(
                    "solicitacao_revisao_json"
                )

                if revisao_json:
                    revisao = json.loads(
                        revisao_json
                    )

                    cursor.execute("""
                        SELECT id
                        FROM usuarios
                        WHERE responsavel_revisao_padrao = 1
                          AND ativo = 1
                        LIMIT 1
                    """)

                    responsavel = cursor.fetchone()

                    if responsavel:
                        responsavel_id = (
                            responsavel["id"]
                        )

                        prazo_revisao = (
                            datetime.now().date()
                            + timedelta(days=30)
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
                            origem_ap_id,
                            (
                                "Revisão de procedimento: "
                                f"{revisao['sugestao_revisao']}"
                            ),
                            responsavel_id,
                            prazo_revisao,
                            criado_por
                        ))

                        acao_revisao_id = (
                            cursor.lastrowid
                        )

                        cursor.execute("""
                            UPDATE auditorias_padrao
                            SET necessita_revisao_padrao = 1,
                                oportunidade_revisao = %s,
                                justificativa_revisao = %s,
                                sugestao_revisao = %s,
                                acao_revisao_id = %s
                            WHERE id = %s
                        """, (
                            revisao["oportunidade_revisao"],
                            revisao["justificativa_revisao"],
                            revisao["sugestao_revisao"],
                            acao_revisao_id,
                            auditoria_id
                        ))

                # =============================================
                # VINCULAR AO AGENDAMENTO
                # =============================================

                if agendamento:
                    data_programada = agendamento.get(
                        "data_programada"
                    )

                    data_execucao = datetime.strptime(
                        data_auditoria,
                        "%Y-%m-%d"
                    ).date()

                    if (
                        data_programada
                        and hasattr(
                            data_programada,
                            "date"
                        )
                        and not isinstance(
                            data_programada,
                            date
                        )
                    ):
                        data_programada = (
                            data_programada.date()
                        )

                    if houve_alteracao:
                        status_agendamento = (
                            "concluida_com_alteracao"
                        )

                    elif (
                        data_programada
                        and data_execucao
                        > data_programada
                    ):
                        status_agendamento = (
                            "concluida_com_atraso"
                        )

                    else:
                        status_agendamento = "concluida"

                    cursor.execute("""
                        UPDATE agendamentos_ssma
                        SET registro_executado_id = %s,
                            status = %s,
                            houve_alteracao = %s,
                            justificativa_alteracao = %s,
                            atualizado_em = NOW()
                        WHERE id = %s
                          AND lider_id = %s
                          AND pratica = 'auditoria_padrao'
                          AND registro_executado_id IS NULL
                    """, (
                        auditoria_id,
                        status_agendamento,
                        houve_alteracao,
                        (
                            justificativa_alteracao
                            or None
                        ),
                        agendamento_id,
                        usuario_id
                    ))

                    if cursor.rowcount != 1:
                        raise ValueError(
                            "O agendamento não pôde ser "
                            "vinculado à execução."
                        )

                conn.commit()

                flash(
                    "Auditoria registrada com sucesso!",
                    "success"
                )

                return redirect(next_url)

            except Exception as e:
                conn.rollback()

                flash(
                    f"Erro ao salvar auditoria: {e}",
                    "danger"
                )

                return redirect(
                    montar_url_retorno_formulario(
                        agendamento_id=agendamento_id,
                        auditado_id=(
                            request.form.get(
                                "auditado_id"
                            )
                        ),
                        procedimento_id=(
                            request.form.get(
                                "procedimento_id"
                            )
                        ),
                        next_url=next_url
                    )
                )

            finally:
                fechar_conexao()

        # =====================================================
        # GET
        # =====================================================

        if perfil in {
            "administrador",
            "avancado"
        }:
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
                centro_custos_id,
            ))

        usuarios = cursor.fetchall()

        cursor.execute("""
            SELECT
                p.id AS procedimento_id,
                pr.id AS revisao_id,
                p.numero_documento,
                p.titulo,
                td.sigla,
                pr.numero_revisao
            FROM procedimentos p
            JOIN tipos_documento td
                ON td.id = p.tipo_documento_id
            JOIN procedimento_revisoes pr
                ON pr.procedimento_id = p.id
            WHERE pr.vigente = 1
            ORDER BY
                td.sigla,
                p.numero_documento
        """)

        procedimentos = cursor.fetchall()

        # =====================================================
        # DADOS INICIAIS - ACESSO DIRETO OU CALENDÁRIO
        # =====================================================

        auditado_previsto_id = request.args.get(
            "auditado_id",
            type=int
        )

        procedimento_previsto_id = request.args.get(
            "procedimento_id",
            type=int
        )

        data_inicial = datetime.today().strftime(
            "%Y-%m-%d"
        )

        if agendamento:
            if not auditado_previsto_id:
                auditado_previsto_id = (
                    agendamento.get(
                        "colaborador_previsto_id"
                    )
                )

            if not procedimento_previsto_id:
                procedimento_previsto_id = (
                    agendamento.get(
                        "procedimento_id"
                    )
                )

            data_programada = agendamento.get(
                "data_programada"
            )

            if (
                data_programada
                and hasattr(
                    data_programada,
                    "strftime"
                )
            ):
                data_inicial = (
                    data_programada.strftime(
                        "%Y-%m-%d"
                    )
                )

        auditado_previsto_nome = ""
        auditado_previsto_texto = ""

        if auditado_previsto_id:
            cursor.execute("""
                SELECT
                    id,
                    nome,
                    matricula
                FROM usuarios
                WHERE id = %s
                  AND ativo = 1
            """, (
                auditado_previsto_id,
            ))

            auditado_previsto = cursor.fetchone()

            if auditado_previsto:
                auditado_previsto_nome = (
                    auditado_previsto["nome"]
                )

                auditado_previsto_texto = (
                    f"{auditado_previsto.get('matricula') or 'Sem matrícula'}"
                    f" - {auditado_previsto['nome']}"
                )

        procedimento_revisao_prevista_id = None
        procedimento_previsto_texto = ""

        if procedimento_previsto_id:
            cursor.execute("""
                SELECT
                    p.id AS procedimento_id,
                    pr.id AS revisao_id,
                    p.numero_documento,
                    p.titulo,
                    td.sigla,
                    pr.numero_revisao
                FROM procedimentos p
                JOIN tipos_documento td
                    ON td.id = p.tipo_documento_id
                JOIN procedimento_revisoes pr
                    ON pr.procedimento_id = p.id
                WHERE p.id = %s
                  AND pr.vigente = 1
                LIMIT 1
            """, (
                procedimento_previsto_id,
            ))

            procedimento_previsto = (
                cursor.fetchone()
            )

            if procedimento_previsto:
                procedimento_revisao_prevista_id = (
                    procedimento_previsto["revisao_id"]
                )

                procedimento_previsto_texto = (
                    f"{procedimento_previsto['sigla']} - "
                    f"{procedimento_previsto['numero_documento']} - "
                    f"{procedimento_previsto['titulo']} | "
                    f"Rev. {procedimento_previsto['numero_revisao']}"
                )

        fechar_conexao()

        return render_template(
            "lancar_ap.html",
            usuarios=usuarios,
            procedimentos=procedimentos,
            agendamento_id=agendamento_id,
            agendamento=agendamento,
            next_url=next_url,
            data_inicial=data_inicial,
            auditado_previsto_id=(
                auditado_previsto_id
            ),
            auditado_previsto_nome=(
                auditado_previsto_nome
            ),
            auditado_previsto_texto=(
                auditado_previsto_texto
            ),
            procedimento_previsto_id=(
                procedimento_previsto_id
            ),
            procedimento_revisao_prevista_id=(
                procedimento_revisao_prevista_id
            ),
            procedimento_previsto_texto=(
                procedimento_previsto_texto
            )
        )

    @blueprint.route('/listar_ap', methods=['GET'])
    @login_required
    @module_required('acesso_ssma')
    def listar_ap():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        usuario_id = session.get('usuario_id')
        perfil = session.get('perfil')
        centro_custos_id = session.get('centro_custos_id')

        if request.args.get('limpar'):
            conn.close()
            return redirect(url_for('main.listar_ap'))

        auditor_id = request.args.get('auditor_id', '').strip()
        auditado_id = request.args.get('auditado_id', '').strip()
        procedimento_id = request.args.get('procedimento_id', '').strip()
        data_inicio = request.args.get('data_inicio', '').strip()
        data_fim = request.args.get('data_fim', '').strip()
        revisao_padrao = request.args.get('revisao_padrao', '').strip()

        sort = request.args.get('sort', 'data_auditoria').strip()
        order = request.args.get('order', 'desc').strip().lower()

        page = request.args.get('page', 1, type=int)
        per_page = 30

        if page < 1:
            page = 1

        offset = (page - 1) * per_page

        colunas_validas = {
            'id': 'ap.id',
            'data_auditoria': 'ap.data_auditoria',
            'auditor': 'auditor.nome',
            'auditado': 'auditado.nome',
            'area_auditada': 'ap.area_auditada',
            'procedimento': 'p.numero_documento',
            'revisao_padrao': 'ap.necessita_revisao_padrao'
        }

        coluna_sort = colunas_validas.get(sort, 'ap.data_auditoria')
        direcao = 'ASC' if order == 'asc' else 'DESC'

        filtros_sql = ["ap.ativo = 1"]
        params = []

        # CONTROLE DE ESCOPO POR PERFIL
        if perfil == 'basico':
            filtros_sql.append("ap.criado_por = %s")
            params.append(usuario_id)

        elif perfil == 'intermediario':
            filtros_sql.append("auditado.centro_custos_id = %s")
            params.append(centro_custos_id)

        # avançado e administrador veem tudo

        if auditor_id:
            filtros_sql.append("ap.auditor_id = %s")
            params.append(auditor_id)

        if auditado_id:
            filtros_sql.append("ap.auditado_id = %s")
            params.append(auditado_id)

        if procedimento_id:
            filtros_sql.append("ap.procedimento_id = %s")
            params.append(procedimento_id)

        if data_inicio:
            filtros_sql.append("ap.data_auditoria >= %s")
            params.append(data_inicio)

        if data_fim:
            filtros_sql.append("ap.data_auditoria <= %s")
            params.append(data_fim)

        if revisao_padrao == 'sim':
            filtros_sql.append("ap.necessita_revisao_padrao = 1")
        elif revisao_padrao == 'nao':
            filtros_sql.append("ap.necessita_revisao_padrao = 0")

        where_clause = "WHERE " + " AND ".join(filtros_sql)

        base_from = f"""
            FROM auditorias_padrao ap
            JOIN usuarios auditor
                ON auditor.id = ap.auditor_id
            JOIN usuarios auditado
                ON auditado.id = ap.auditado_id
            JOIN procedimentos p
                ON p.id = ap.procedimento_id
            JOIN tipos_documento td
                ON td.id = p.tipo_documento_id
            JOIN procedimento_revisoes pr
                ON pr.id = ap.procedimento_revisao_id
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
                ap.id,
                ap.auditor_id,
                ap.auditado_id,
                ap.data_auditoria,
                ap.area_auditada,
                ap.atividade_auditada,
                ap.pontos_observados,
                ap.necessita_revisao_padrao,
                ap.criado_por,

                auditor.nome AS auditor_nome,
                auditado.nome AS auditado_nome,

                td.sigla,
                p.numero_documento,
                p.titulo,
                pr.numero_revisao

            {base_from}
            ORDER BY {coluna_sort} {direcao}, ap.id DESC
            LIMIT %s OFFSET %s
        """, params + [per_page, offset])
        auditorias = cursor.fetchall()

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

        cursor.execute("""
            SELECT
                p.id,
                td.sigla,
                p.numero_documento,
                p.titulo
            FROM procedimentos p
            JOIN tipos_documento td
                ON td.id = p.tipo_documento_id
            WHERE p.ativo = 1
            ORDER BY td.sigla, p.numero_documento, p.titulo
        """)
        procedimentos = cursor.fetchall()

        conn.close()

        filtros = {
            'auditor_id': auditor_id,
            'auditado_id': auditado_id,
            'procedimento_id': procedimento_id,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'revisao_padrao': revisao_padrao,
            'sort': sort,
            'order': order
        }

        return render_template(
            'listar_ap.html',
            auditorias=auditorias,
            usuarios=usuarios,
            procedimentos=procedimentos,
            filtros=filtros,
            page=page,
            per_page=per_page,
            total_registros=total_registros,
            total_paginas=total_paginas
        )

    @blueprint.route('/excluir_ap/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_ssma')
    def excluir_ap(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            auditoria = pode_acessar_ssma(cursor, 'auditoria_padrao', id)

            if not auditoria:
                flash('Auditoria de Padrão não encontrada ou você não possui permissão para excluí-la.', 'warning')
                conn.close()
                return redirect(url_for('main.listar_ap'))

            perfil = session.get('perfil')
            usuario_id = session.get('usuario_id')

            # Regra adicional: somente administrador ou quem criou pode excluir
            if perfil != 'administrador' and auditoria['criado_por'] != usuario_id:
                flash('Você não tem permissão para excluir esta Auditoria de Padrão.', 'warning')
                conn.close()
                return redirect(url_for('main.listar_ap'))

            cursor.execute("""
                UPDATE auditorias_padrao
                SET ativo = 0
                WHERE id = %s
            """, (id,))

            conn.commit()
            flash('Auditoria de Padrão excluída com sucesso.', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Erro ao excluir Auditoria de Padrão: {e}', 'danger')

        finally:
            conn.close()

        return redirect(url_for('main.listar_ap'))

    @blueprint.route('/editar_ap/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_ssma')
    def editar_ap(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            auditoria = pode_acessar_ssma(cursor, 'auditoria_padrao', id)

            if not auditoria:
                flash('Auditoria de Padrão não encontrada ou você não possui permissão para editá-la.', 'warning')
                conn.close()
                return redirect(url_for('main.listar_ap'))

            perfil = session.get('perfil')
            usuario_id = session.get('usuario_id')
            centro_custos_id = session.get('centro_custos_id')

            # Regra adicional: somente administrador ou quem criou pode editar
            if perfil != 'administrador' and auditoria['criado_por'] != usuario_id:
                flash('Você não tem permissão para editar esta Auditoria de Padrão.', 'warning')
                conn.close()
                return redirect(url_for('main.listar_ap'))

            auditor_id = request.form.get('auditor_id')
            auditado_id = request.form.get('auditado_id')
            data_auditoria = request.form.get('data_auditoria')
            area_auditada = (request.form.get('area_auditada') or '').strip()
            atividade_auditada = (request.form.get('atividade_auditada') or '').strip()
            pontos_observados = (request.form.get('pontos_observados') or '').strip()

            if not auditor_id or not auditado_id or not data_auditoria or not area_auditada or not atividade_auditada:
                flash('Preencha todos os campos obrigatórios da Auditoria de Padrão.', 'danger')
                conn.close()
                return redirect(request.form.get('next') or url_for('main.listar_ap'))

            if perfil in ['administrador', 'avancado']:
                cursor.execute("""
                    SELECT id
                    FROM usuarios
                    WHERE id = %s
                      AND ativo = 1
                """, (auditado_id,))
            else:
                cursor.execute("""
                    SELECT id
                    FROM usuarios
                    WHERE id = %s
                      AND ativo = 1
                      AND centro_custos_id = %s
                """, (auditado_id, centro_custos_id))

            auditado_valido = cursor.fetchone()

            if not auditado_valido:
                flash('Usuário auditado inválido para seu escopo.', 'danger')
                conn.close()
                return redirect(request.form.get('next') or url_for('main.listar_ap'))

            if perfil == 'administrador':
                auditor_id_final = auditor_id
            else:
                auditor_id_final = auditoria['auditor_id']

            cursor.execute("""
                UPDATE auditorias_padrao
                SET auditor_id = %s,
                    auditado_id = %s,
                    data_auditoria = %s,
                    area_auditada = %s,
                    atividade_auditada = %s,
                    pontos_observados = %s
                WHERE id = %s
                  AND ativo = 1
            """, (
                auditor_id_final,
                auditado_id,
                data_auditoria,
                area_auditada,
                atividade_auditada,
                pontos_observados,
                id
            ))

            conn.commit()
            flash('Auditoria de Padrão atualizada com sucesso.', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Erro ao atualizar Auditoria de Padrão: {e}', 'danger')

        finally:
            conn.close()

        return redirect(request.form.get('next') or url_for('main.listar_ap'))

