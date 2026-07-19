import calendar
import os
from calendar import monthrange
from datetime import date, datetime

from flask import current_app, flash, redirect, render_template, request, session, url_for

from app.decorators import gerenciar_agendamentos_ssma_required, lider_ssma_required, login_required
from app.utils.db import get_db_connection


def register_agenda_ssma_routes(blueprint):
    @blueprint.route(
        "/agendamentos_ssma",
        methods=["GET"]
    )
    @blueprint.route(
        "/listar_agendamentos_ssma",
        methods=["GET"]
    )
    @login_required
    @gerenciar_agendamentos_ssma_required
    def listar_agendamentos_ssma():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        usuario_logado_id = session.get("usuario_id")

        def fechar_conexao():
            try:
                cursor.close()
            except Exception:
                pass

            try:
                conn.close()
            except Exception:
                pass

        if not usuario_logado_id:
            fechar_conexao()

            flash(
                "Não foi possível identificar o usuário logado.",
                "danger"
            )

            return redirect(
                url_for("main.login")
            )

        cursor.execute("""
            SELECT
                id,
                perfil,
                centro_custos_id
            FROM usuarios
            WHERE id = %s
              AND ativo = 1
        """, (usuario_logado_id,))

        usuario_escopo = cursor.fetchone()

        if not usuario_escopo:
            fechar_conexao()

            flash(
                "Não foi possível identificar o escopo do usuário.",
                "danger"
            )

            return redirect(
                url_for("main.dashboard")
            )

        perfil = (
            usuario_escopo.get("perfil")
            or ""
        ).strip().lower()

        centro_custos_id_logado = (
            usuario_escopo.get("centro_custos_id")
        )

        possui_escopo_global = perfil in {
            "administrador",
            "avancado"
        }

        if (
            not possui_escopo_global
            and not centro_custos_id_logado
        ):
            fechar_conexao()

            flash(
                "Usuário sem centro de custos vinculado. "
                "Contate o administrador.",
                "danger"
            )

            return redirect(
                url_for("main.dashboard")
            )

        if request.args.get("limpar"):
            fechar_conexao()

            return redirect(
                url_for("main.listar_agendamentos_ssma")
            )

        lider_id = (
            request.args.get("lider_id")
            or ""
        ).strip()

        mes = (
            request.args.get("mes")
            or ""
        ).strip()

        pratica = (
            request.args.get("pratica")
            or ""
        ).strip()

        sort = (
            request.args.get("sort")
            or "data"
        ).strip()

        order = (
            request.args.get("order")
            or "desc"
        ).strip().lower()

        praticas_validas = {
            "hora_seguranca",
            "auditoria_padrao",
            "ifs"
        }

        if pratica not in praticas_validas:
            pratica = ""

        colunas_ordenacao = {
            "id": "ag.id",
            "lider": "lider.nome",
            "data": "ag.data_programada",
            "pratica": "ag.pratica"
        }

        coluna_order_by = colunas_ordenacao.get(
            sort,
            "ag.data_programada"
        )

        if sort not in colunas_ordenacao:
            sort = "data"

        direcao_order_by = (
            "ASC"
            if order == "asc"
            else "DESC"
        )

        order = (
            "asc"
            if direcao_order_by == "ASC"
            else "desc"
        )

        primeiro_dia = None
        proximo_mes = None

        if mes:
            try:
                data_mes = datetime.strptime(
                    mes,
                    "%Y-%m"
                )

                primeiro_dia = datetime(
                    data_mes.year,
                    data_mes.month,
                    1
                ).strftime("%Y-%m-%d")

                if data_mes.month == 12:
                    proximo_mes = datetime(
                        data_mes.year + 1,
                        1,
                        1
                    ).strftime("%Y-%m-%d")
                else:
                    proximo_mes = datetime(
                        data_mes.year,
                        data_mes.month + 1,
                        1
                    ).strftime("%Y-%m-%d")

            except ValueError:
                mes = ""
                primeiro_dia = None
                proximo_mes = None

        page = request.args.get(
            "page",
            1,
            type=int
        )

        if page < 1:
            page = 1

        per_page = 30
        offset = (page - 1) * per_page

        from_where = """
            FROM agendamentos_ssma ag

            JOIN usuarios lider
                ON lider.id = ag.lider_id

            WHERE 1 = 1
        """

        params = []

        if not possui_escopo_global:
            from_where += """
                AND lider.centro_custos_id = %s
            """

            params.append(
                centro_custos_id_logado
            )

        if lider_id:
            from_where += """
                AND ag.lider_id = %s
            """

            params.append(
                lider_id
            )

        if primeiro_dia and proximo_mes:
            from_where += """
                AND ag.data_programada >= %s
                AND ag.data_programada < %s
            """

            params.extend([
                primeiro_dia,
                proximo_mes
            ])

        if pratica:
            from_where += """
                AND ag.pratica = %s
            """

            params.append(
                pratica
            )

        count_query = f"""
            SELECT
                COUNT(*) AS total
            {from_where}
        """

        cursor.execute(
            count_query,
            params
        )

        total_registros = (
            cursor.fetchone().get("total")
            or 0
        )

        total_paginas = (
            total_registros + per_page - 1
        ) // per_page

        if (
            total_paginas > 0
            and page > total_paginas
        ):
            page = total_paginas
            offset = (page - 1) * per_page

        query = f"""
            SELECT
                ag.id,
                ag.lider_id,
                ag.data_programada,
                ag.pratica,
                lider.nome AS nome_lider

            {from_where}

            ORDER BY
                {coluna_order_by} {direcao_order_by},
                ag.id DESC

            LIMIT %s
            OFFSET %s
        """

        cursor.execute(
            query,
            params + [
                per_page,
                offset
            ]
        )

        agendamentos = cursor.fetchall()

        if possui_escopo_global:
            cursor.execute("""
                SELECT
                    id,
                    nome,
                    matricula
                FROM usuarios
                WHERE ativo = 1
                  AND tem_acesso_sistema = 1
                  AND pode_ser_lider_ssma = 1
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
                  AND tem_acesso_sistema = 1
                  AND pode_ser_lider_ssma = 1
                  AND centro_custos_id = %s
                ORDER BY nome
            """, (
                centro_custos_id_logado,
            ))

        lideres = cursor.fetchall()

        fechar_conexao()

        filtros = {
            "lider_id": lider_id,
            "mes": mes,
            "pratica": pratica,
            "sort": sort,
            "order": order
        }

        return render_template(
            "agendamentos_ssma.html",
            agendamentos=agendamentos,
            lideres=lideres,
            filtros=filtros,
            page=page,
            per_page=per_page,
            total_registros=total_registros,
            total_paginas=total_paginas
        )

    @blueprint.route(
        "/novo_agendamento_ssma",
        methods=["GET", "POST"]
    )
    @login_required
    @gerenciar_agendamentos_ssma_required
    def novo_agendamento_ssma():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        usuario_logado_id = session.get("usuario_id")

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

        def redirecionar_cronograma(
            mes_selecionado="",
            lider_id=""
        ):
            if mes_selecionado and lider_id:
                return redirect(
                    url_for(
                        "main.novo_agendamento_ssma",
                        mes=mes_selecionado,
                        lider_id=lider_id
                    )
                )

            return redirect(
                url_for("main.novo_agendamento_ssma")
            )

        def buscar_usuario_escopo():
            cursor.execute("""
                SELECT
                    id,
                    perfil,
                    centro_custos_id
                FROM usuarios
                WHERE id = %s
                  AND ativo = 1
            """, (usuario_logado_id,))

            return cursor.fetchone()

        def buscar_lider(
            lider_id,
            possui_escopo_global,
            centro_custos_id
        ):
            if possui_escopo_global:
                cursor.execute("""
                    SELECT
                        id,
                        nome,
                        matricula,
                        centro_custos_id
                    FROM usuarios
                    WHERE id = %s
                      AND ativo = 1
                      AND tem_acesso_sistema = 1
                      AND pode_ser_lider_ssma = 1
                """, (lider_id,))

            else:
                cursor.execute("""
                    SELECT
                        id,
                        nome,
                        matricula,
                        centro_custos_id
                    FROM usuarios
                    WHERE id = %s
                      AND ativo = 1
                      AND tem_acesso_sistema = 1
                      AND pode_ser_lider_ssma = 1
                      AND centro_custos_id = %s
                """, (
                    lider_id,
                    centro_custos_id
                ))

            return cursor.fetchone()

        def buscar_colaborador(
            colaborador_id,
            possui_escopo_global,
            centro_custos_id
        ):
            if possui_escopo_global:
                cursor.execute("""
                    SELECT
                        id,
                        nome,
                        matricula,
                        centro_custos_id
                    FROM usuarios
                    WHERE id = %s
                      AND ativo = 1
                """, (colaborador_id,))

            else:
                cursor.execute("""
                    SELECT
                        id,
                        nome,
                        matricula,
                        centro_custos_id
                    FROM usuarios
                    WHERE id = %s
                      AND ativo = 1
                      AND centro_custos_id = %s
                """, (
                    colaborador_id,
                    centro_custos_id
                ))

            return cursor.fetchone()

        def buscar_agendamento_para_edicao(
            agendamento_id,
            possui_escopo_global,
            centro_custos_id
        ):
            query = """
                SELECT
                    ag.id,
                    ag.lider_id,
                    ag.status,
                    ag.registro_executado_id,
                    lider.centro_custos_id
                FROM agendamentos_ssma ag
                JOIN usuarios lider
                    ON lider.id = ag.lider_id
                WHERE ag.id = %s
            """

            params = [agendamento_id]

            if not possui_escopo_global:
                query += """
                    AND lider.centro_custos_id = %s
                """

                params.append(
                    centro_custos_id
                )

            cursor.execute(
                query,
                params
            )

            return cursor.fetchone()

        def validar_tema(tema_id):
            if not tema_id:
                return True

            cursor.execute("""
                SELECT id
                FROM hs_temas
                WHERE id = %s
                  AND status = 1
            """, (tema_id,))

            return cursor.fetchone() is not None

        def validar_procedimento(procedimento_id):
            if not procedimento_id:
                return True

            cursor.execute("""
                SELECT id
                FROM procedimentos
                WHERE id = %s
                  AND ativo = 1
            """, (procedimento_id,))

            return cursor.fetchone() is not None

        def validar_mes_e_data(
            mes_selecionado,
            data_programada
        ):
            try:
                data_mes = datetime.strptime(
                    mes_selecionado,
                    "%Y-%m"
                )

                data_agendamento = datetime.strptime(
                    data_programada,
                    "%Y-%m-%d"
                )

            except ValueError:
                return (
                    None,
                    "O mês ou a data programada é inválida."
                )

            if (
                data_agendamento.year != data_mes.year
                or data_agendamento.month != data_mes.month
            ):
                return (
                    None,
                    "A data da prática deve pertencer ao mês "
                    "selecionado no cronograma."
                )

            return data_mes, None

        def aplicar_regras_pratica(
            pratica,
            tema_id,
            colaborador_id,
            procedimento_id
        ):
            praticas_validas = {
                "hora_seguranca",
                "auditoria_padrao",
                "ifs"
            }

            if pratica not in praticas_validas:
                return (
                    None,
                    None,
                    None,
                    "Selecione uma prática válida."
                )

            if pratica == "hora_seguranca":
                if not tema_id:
                    return (
                        None,
                        None,
                        None,
                        "Selecione o tema da Hora de Segurança."
                    )

                if not colaborador_id:
                    return (
                        None,
                        None,
                        None,
                        "Selecione o colaborador previsto para "
                        "a Hora de Segurança."
                    )

                procedimento_id = None

            elif pratica == "auditoria_padrao":
                tema_id = None

                if not colaborador_id:
                    return (
                        None,
                        None,
                        None,
                        "Selecione o colaborador previsto para "
                        "a Auditoria de Padrão."
                    )

                if not procedimento_id:
                    return (
                        None,
                        None,
                        None,
                        "Selecione o procedimento da Auditoria "
                        "de Padrão."
                    )

            elif pratica == "ifs":
                tema_id = None
                colaborador_id = None
                procedimento_id = None

            return (
                tema_id,
                colaborador_id,
                procedimento_id,
                None
            )

        def carregar_listas(
            possui_escopo_global,
            centro_custos_id
        ):
            if possui_escopo_global:
                cursor.execute("""
                    SELECT
                        id,
                        nome,
                        matricula,
                        centro_custos_id
                    FROM usuarios
                    WHERE ativo = 1
                      AND tem_acesso_sistema = 1
                      AND pode_ser_lider_ssma = 1
                    ORDER BY nome
                """)

            else:
                cursor.execute("""
                    SELECT
                        id,
                        nome,
                        matricula,
                        centro_custos_id
                    FROM usuarios
                    WHERE ativo = 1
                      AND tem_acesso_sistema = 1
                      AND pode_ser_lider_ssma = 1
                      AND centro_custos_id = %s
                    ORDER BY nome
                """, (centro_custos_id,))

            lideres = cursor.fetchall()

            if possui_escopo_global:
                cursor.execute("""
                    SELECT
                        id,
                        nome,
                        matricula,
                        centro_custos_id
                    FROM usuarios
                    WHERE ativo = 1
                    ORDER BY nome
                """)

            else:
                cursor.execute("""
                    SELECT
                        id,
                        nome,
                        matricula,
                        centro_custos_id
                    FROM usuarios
                    WHERE ativo = 1
                      AND centro_custos_id = %s
                    ORDER BY nome
                """, (centro_custos_id,))

            colaboradores = cursor.fetchall()

            cursor.execute("""
                SELECT
                    p.id,
                    p.numero_documento,
                    p.titulo,
                    td.sigla
                FROM procedimentos p
                JOIN tipos_documento td
                    ON td.id = p.tipo_documento_id
                WHERE p.ativo = 1
                ORDER BY
                    td.sigla,
                    p.numero_documento,
                    p.titulo
            """)

            procedimentos = cursor.fetchall()

            cursor.execute("""
                SELECT
                    id,
                    nome
                FROM hs_temas
                WHERE status = 1
                ORDER BY nome
            """)

            temas = cursor.fetchall()

            return (
                lideres,
                colaboradores,
                procedimentos,
                temas
            )

        def buscar_agendamentos_mes(
            lider_id,
            primeiro_dia_mes,
            ultimo_dia_mes
        ):
            cursor.execute("""
                SELECT
                    ag.id,
                    ag.pratica,
                    ag.lider_id,
                    ag.data_programada,
                    ag.tema_id,
                    ag.colaborador_previsto_id,
                    ag.procedimento_id,
                    ag.observacao,
                    ag.status,

                    tema.nome AS nome_tema,

                    colaborador.nome
                        AS nome_colaborador_previsto,

                    colaborador.matricula
                        AS matricula_colaborador_previsto,

                    CONCAT(
                        td.sigla,
                        ' ',
                        p.numero_documento,
                        ' - ',
                        p.titulo
                    ) AS nome_procedimento

                FROM agendamentos_ssma ag

                LEFT JOIN hs_temas tema
                    ON tema.id = ag.tema_id

                LEFT JOIN usuarios colaborador
                    ON colaborador.id =
                       ag.colaborador_previsto_id

                LEFT JOIN procedimentos p
                    ON p.id = ag.procedimento_id

                LEFT JOIN tipos_documento td
                    ON td.id = p.tipo_documento_id

                WHERE ag.lider_id = %s
                  AND ag.data_programada >= %s
                  AND ag.data_programada <= %s

                ORDER BY
                    ag.data_programada ASC,
                    ag.id ASC
            """, (
                lider_id,
                primeiro_dia_mes,
                ultimo_dia_mes
            ))

            return cursor.fetchall()

        def montar_calendario(
            data_mes,
            agendamentos
        ):
            agendamentos_por_data = {}

            for agendamento in agendamentos:
                data_chave = agendamento.get(
                    "data_programada"
                )

                if hasattr(
                    data_chave,
                    "isoformat"
                ):
                    data_chave = (
                        data_chave.isoformat()
                    )
                else:
                    data_chave = str(
                        data_chave or ""
                    )

                agendamentos_por_data.setdefault(
                    data_chave,
                    []
                ).append(
                    agendamento
                )

            calendario_objeto = calendar.Calendar(
                firstweekday=calendar.MONDAY
            )

            semanas_do_mes = (
                calendario_objeto.monthdatescalendar(
                    data_mes.year,
                    data_mes.month
                )
            )

            calendario_semanas = []

            for semana in semanas_do_mes:
                dias_semana = []

                for data_dia in semana:
                    data_iso = data_dia.isoformat()

                    dias_semana.append({
                        "numero": data_dia.day,
                        "data": data_iso,
                        "no_mes": (
                            data_dia.year
                            == data_mes.year
                            and data_dia.month
                            == data_mes.month
                        ),
                        "agendamentos": (
                            agendamentos_por_data.get(
                                data_iso,
                                []
                            )
                        )
                    })

                calendario_semanas.append(
                    dias_semana
                )

            return calendario_semanas

        # =====================================================
        # VALIDAR USUÁRIO LOGADO
        # =====================================================

        if not usuario_logado_id:
            fechar_conexao()

            flash(
                "Não foi possível identificar o usuário logado.",
                "danger"
            )

            return redirect(
                url_for("main.login")
            )

        usuario_escopo = buscar_usuario_escopo()

        if not usuario_escopo:
            fechar_conexao()

            flash(
                "Não foi possível identificar o escopo do usuário.",
                "danger"
            )

            return redirect(
                url_for("main.dashboard")
            )

        perfil_banco = (
            usuario_escopo.get("perfil")
            or ""
        ).strip().lower()

        centro_custos_id_logado = (
            usuario_escopo.get(
                "centro_custos_id"
            )
        )

        possui_escopo_global = (
            perfil_banco
            in {
                "administrador",
                "avancado"
            }
        )

        if (
            not possui_escopo_global
            and not centro_custos_id_logado
        ):
            fechar_conexao()

            flash(
                "Usuário sem centro de custos vinculado. "
                "Contate o administrador.",
                "danger"
            )

            return redirect(
                url_for("main.dashboard")
            )

        # =====================================================
        # IDENTIFICAR MÊS E LÍDER
        # =====================================================

        origem_dados = (
            request.form
            if request.method == "POST"
            else request.args
        )

        mes_selecionado = (
            origem_dados.get("mes")
            or ""
        ).strip()

        lider_id = (
            origem_dados.get("lider_id")
            or ""
        ).strip()

        # =====================================================
        # POST: INCLUSÃO OU EDIÇÃO
        # =====================================================

        if request.method == "POST":
            agendamento_id = (
                request.form.get(
                    "agendamento_id"
                )
                or ""
            ).strip() or None

            pratica = (
                request.form.get("pratica")
                or ""
            ).strip()

            data_programada = (
                request.form.get(
                    "data_programada"
                )
                or ""
            ).strip()

            tema_id = (
                request.form.get("tema_id")
                or None
            )

            colaborador_previsto_id = (
                request.form.get(
                    "colaborador_previsto_id"
                )
                or None
            )

            procedimento_id = (
                request.form.get(
                    "procedimento_id"
                )
                or None
            )

            observacao = (
                request.form.get("observacao")
                or ""
            ).strip() or None

            if not mes_selecionado:
                flash(
                    "Selecione o mês do cronograma.",
                    "danger"
                )

                fechar_conexao()

                return redirecionar_cronograma(
                    mes_selecionado,
                    lider_id
                )

            if not lider_id:
                flash(
                    "Selecione o líder responsável.",
                    "danger"
                )

                fechar_conexao()

                return redirecionar_cronograma(
                    mes_selecionado,
                    lider_id
                )

            if not data_programada:
                flash(
                    "Informe a data programada.",
                    "danger"
                )

                fechar_conexao()

                return redirecionar_cronograma(
                    mes_selecionado,
                    lider_id
                )

            _, erro_data = validar_mes_e_data(
                mes_selecionado,
                data_programada
            )

            if erro_data:
                flash(
                    erro_data,
                    "warning"
                )

                fechar_conexao()

                return redirecionar_cronograma(
                    mes_selecionado,
                    lider_id
                )

            (
                tema_id,
                colaborador_previsto_id,
                procedimento_id,
                erro_pratica
            ) = aplicar_regras_pratica(
                pratica,
                tema_id,
                colaborador_previsto_id,
                procedimento_id
            )

            if erro_pratica:
                flash(
                    erro_pratica,
                    "warning"
                )

                fechar_conexao()

                return redirecionar_cronograma(
                    mes_selecionado,
                    lider_id
                )

            try:
                lider = buscar_lider(
                    lider_id,
                    possui_escopo_global,
                    centro_custos_id_logado
                )

                if not lider:
                    flash(
                        "O líder selecionado não pertence ao "
                        "seu centro de custos ou não está "
                        "habilitado.",
                        "warning"
                    )

                    fechar_conexao()

                    return redirecionar_cronograma(
                        mes_selecionado,
                        lider_id
                    )

                if not validar_tema(tema_id):
                    flash(
                        "O tema selecionado não foi encontrado "
                        "ou está desabilitado.",
                        "warning"
                    )

                    fechar_conexao()

                    return redirecionar_cronograma(
                        mes_selecionado,
                        lider_id
                    )

                if colaborador_previsto_id:
                    colaborador = buscar_colaborador(
                        colaborador_previsto_id,
                        possui_escopo_global,
                        centro_custos_id_logado
                    )

                    if not colaborador:
                        flash(
                            "O colaborador selecionado não "
                            "pertence ao seu centro de custos "
                            "ou está inativo.",
                            "warning"
                        )

                        fechar_conexao()

                        return redirecionar_cronograma(
                            mes_selecionado,
                            lider_id
                        )

                if not validar_procedimento(
                    procedimento_id
                ):
                    flash(
                        "O procedimento selecionado não foi "
                        "encontrado ou está inativo.",
                        "warning"
                    )

                    fechar_conexao()

                    return redirecionar_cronograma(
                        mes_selecionado,
                        lider_id
                    )

                # ---------------------------------------------
                # UPDATE
                # ---------------------------------------------

                if agendamento_id:
                    agendamento_existente = (
                        buscar_agendamento_para_edicao(
                            agendamento_id,
                            possui_escopo_global,
                            centro_custos_id_logado
                        )
                    )

                    if not agendamento_existente:
                        flash(
                            "Agendamento não encontrado ou "
                            "fora do seu escopo de acesso.",
                            "warning"
                        )

                        fechar_conexao()

                        return redirecionar_cronograma(
                            mes_selecionado,
                            lider_id
                        )

                    if agendamento_existente.get(
                        "registro_executado_id"
                    ):
                        flash(
                            "Não é possível editar um "
                            "agendamento que já possui uma "
                            "prática executada.",
                            "warning"
                        )

                        fechar_conexao()

                        return redirecionar_cronograma(
                            mes_selecionado,
                            lider_id
                        )

                    if (
                        agendamento_existente.get(
                            "status"
                        )
                        != "agendada"
                    ):
                        flash(
                            "Somente agendamentos com status "
                            "'Agendada' podem ser editados.",
                            "warning"
                        )

                        fechar_conexao()

                        return redirecionar_cronograma(
                            mes_selecionado,
                            lider_id
                        )

                    cursor.execute("""
                        UPDATE agendamentos_ssma
                        SET pratica = %s,
                            lider_id = %s,
                            data_programada = %s,
                            tema_id = %s,
                            colaborador_previsto_id = %s,
                            procedimento_id = %s,
                            observacao = %s,
                            atualizado_em = NOW()
                        WHERE id = %s
                    """, (
                        pratica,
                        lider_id,
                        data_programada,
                        tema_id,
                        colaborador_previsto_id,
                        procedimento_id,
                        observacao,
                        agendamento_id
                    ))

                    mensagem_sucesso = (
                        "Agendamento atualizado com sucesso!"
                    )

                # ---------------------------------------------
                # INSERT
                # ---------------------------------------------

                else:
                    cursor.execute("""
                        INSERT INTO agendamentos_ssma (
                            pratica,
                            lider_id,
                            data_programada,
                            tema_id,
                            colaborador_previsto_id,
                            procedimento_id,
                            observacao,
                            status,
                            criado_por,
                            criado_em,
                            houve_alteracao
                        )
                        VALUES (
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            'agendada',
                            %s,
                            NOW(),
                            0
                        )
                    """, (
                        pratica,
                        lider_id,
                        data_programada,
                        tema_id,
                        colaborador_previsto_id,
                        procedimento_id,
                        observacao,
                        usuario_logado_id
                    ))

                    mensagem_sucesso = (
                        "Prática adicionada ao cronograma!"
                    )

                conn.commit()

                flash(
                    mensagem_sucesso,
                    "success"
                )

            except Exception as e:
                conn.rollback()

                flash(
                    f"Erro ao salvar agendamento: {e}",
                    "danger"
                )

            finally:
                fechar_conexao()

            return redirecionar_cronograma(
                mes_selecionado,
                lider_id
            )

        # =====================================================
        # GET: CARREGAR LISTAS E CALENDÁRIO
        # =====================================================

        try:
            (
                lideres,
                colaboradores,
                procedimentos,
                temas
            ) = carregar_listas(
                possui_escopo_global,
                centro_custos_id_logado
            )

            lider_selecionado = None
            agendamentos = []

            mes_exibicao = None
            primeiro_dia_mes = None
            ultimo_dia_mes = None

            calendario_semanas = []

            if mes_selecionado and lider_id:
                try:
                    data_mes = datetime.strptime(
                        mes_selecionado,
                        "%Y-%m"
                    )

                except ValueError:
                    flash(
                        "Selecione um mês válido.",
                        "warning"
                    )

                    mes_selecionado = ""
                    lider_id = ""
                    data_mes = None

                if data_mes:
                    quantidade_dias = monthrange(
                        data_mes.year,
                        data_mes.month
                    )[1]

                    primeiro_dia_mes = (
                        f"{data_mes.year:04d}-"
                        f"{data_mes.month:02d}-01"
                    )

                    ultimo_dia_mes = (
                        f"{data_mes.year:04d}-"
                        f"{data_mes.month:02d}-"
                        f"{quantidade_dias:02d}"
                    )

                    meses_pt_br = [
                        "",
                        "Janeiro",
                        "Fevereiro",
                        "Março",
                        "Abril",
                        "Maio",
                        "Junho",
                        "Julho",
                        "Agosto",
                        "Setembro",
                        "Outubro",
                        "Novembro",
                        "Dezembro"
                    ]

                    mes_exibicao = (
                        f"{meses_pt_br[data_mes.month]} "
                        f"de {data_mes.year}"
                    )

                    lider_selecionado = buscar_lider(
                        lider_id,
                        possui_escopo_global,
                        centro_custos_id_logado
                    )

                    if not lider_selecionado:
                        flash(
                            "O líder selecionado não pertence "
                            "ao seu centro de custos ou não "
                            "está habilitado.",
                            "warning"
                        )

                        mes_selecionado = ""
                        lider_id = ""

                        mes_exibicao = None
                        primeiro_dia_mes = None
                        ultimo_dia_mes = None

                    else:
                        agendamentos = buscar_agendamentos_mes(
                            lider_id,
                            primeiro_dia_mes,
                            ultimo_dia_mes
                        )

                        calendario_semanas = montar_calendario(
                            data_mes,
                            agendamentos
                        )

        except Exception as e:
            flash(
                f"Erro ao carregar o cronograma: {e}",
                "danger"
            )

            lideres = []
            colaboradores = []
            procedimentos = []
            temas = []

            lider_selecionado = None
            agendamentos = []

            mes_exibicao = None
            primeiro_dia_mes = None
            ultimo_dia_mes = None
            calendario_semanas = []

        fechar_conexao()

        return render_template(
            "novo_agendamento_ssma.html",
            lideres=lideres,
            colaboradores=colaboradores,
            procedimentos=procedimentos,
            temas=temas,
            mes_selecionado=mes_selecionado,
            mes_exibicao=mes_exibicao,
            primeiro_dia_mes=primeiro_dia_mes,
            ultimo_dia_mes=ultimo_dia_mes,
            lider_selecionado=lider_selecionado,
            agendamentos=agendamentos,
            calendario_semanas=calendario_semanas
        )

    @blueprint.route(
        "/excluir_agendamento_ssma/<int:id>",
        methods=["POST"]
    )
    @login_required
    @gerenciar_agendamentos_ssma_required
    def excluir_agendamento_ssma(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        mes = (
            request.form.get("mes")
            or ""
        ).strip()

        lider_id = (
            request.form.get("lider_id")
            or ""
        ).strip()

        try:
            cursor.execute("""
                SELECT
                    id,
                    status,
                    registro_executado_id
                FROM agendamentos_ssma
                WHERE id = %s
            """, (id,))

            agendamento = cursor.fetchone()

            if not agendamento:
                flash(
                    "Agendamento não encontrado.",
                    "warning"
                )

            elif agendamento.get("registro_executado_id"):
                flash(
                    "Não é possível excluir um agendamento "
                    "que já possui uma prática executada.",
                    "warning"
                )

            elif agendamento.get("status") not in {
                "agendada",
                "cancelada"
            }:
                flash(
                    "Este agendamento não pode mais ser excluído.",
                    "warning"
                )

            else:
                cursor.execute("""
                    DELETE FROM agendamentos_ssma
                    WHERE id = %s
                """, (id,))

                conn.commit()

                flash(
                    "Agendamento excluído com sucesso!",
                    "success"
                )

        except Exception as e:
            conn.rollback()

            flash(
                f"Erro ao excluir agendamento: {e}",
                "danger"
            )

        finally:
            cursor.close()
            conn.close()

        if mes and lider_id:
            return redirect(
                url_for(
                    "main.novo_agendamento_ssma",
                    mes=mes,
                    lider_id=lider_id
                )
            )

        return redirect(
            url_for("main.listar_agendamentos_ssma")
        )

    @blueprint.route(
        "/meu_calendario_ssma",
        methods=["GET"]
    )
    @login_required
    @lider_ssma_required
    def meu_calendario_ssma():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        usuario_logado_id = session.get("usuario_id")

        # =====================================================
        # FUNÇÃO AUXILIAR PARA FECHAR A CONEXÃO
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

        # =====================================================
        # VALIDAR USUÁRIO LOGADO
        # =====================================================

        if not usuario_logado_id:
            fechar_conexao()

            flash(
                "Não foi possível identificar o usuário logado.",
                "danger"
            )

            return redirect(
                url_for("main.login")
            )

        cursor.execute("""
            SELECT
                id,
                nome,
                matricula,
                perfil,
                centro_custos_id,
                pode_ser_lider_ssma
            FROM usuarios
            WHERE id = %s
              AND ativo = 1
              AND tem_acesso_sistema = 1
        """, (usuario_logado_id,))

        lider = cursor.fetchone()

        if not lider:
            fechar_conexao()

            flash(
                "Usuário não encontrado ou sem acesso ao sistema.",
                "danger"
            )

            return redirect(
                url_for("main.dashboard")
            )

        if not int(lider.get("pode_ser_lider_ssma") or 0):
            fechar_conexao()

            flash(
                "Seu usuário não está habilitado como líder "
                "para receber agendamentos de SSMA.",
                "warning"
            )

            return redirect(
                url_for("main.dashboard")
            )

        # =====================================================
        # IDENTIFICAR O MÊS
        # =====================================================

        hoje = date.today()

        mes_selecionado = (
            request.args.get("mes")
            or hoje.strftime("%Y-%m")
        ).strip()

        try:
            data_mes = datetime.strptime(
                mes_selecionado,
                "%Y-%m"
            )

        except ValueError:
            flash(
                "O mês informado é inválido. "
                "Foi carregado o mês atual.",
                "warning"
            )

            data_mes = datetime(
                hoje.year,
                hoje.month,
                1
            )

            mes_selecionado = data_mes.strftime(
                "%Y-%m"
            )

        ano = data_mes.year
        mes = data_mes.month

        primeiro_dia_mes = date(
            ano,
            mes,
            1
        )

        quantidade_dias = calendar.monthrange(
            ano,
            mes
        )[1]

        ultimo_dia_mes = date(
            ano,
            mes,
            quantidade_dias
        )

        # =====================================================
        # MÊS ANTERIOR E PRÓXIMO MÊS
        # =====================================================

        if mes == 1:
            mes_anterior = date(
                ano - 1,
                12,
                1
            )
        else:
            mes_anterior = date(
                ano,
                mes - 1,
                1
            )

        if mes == 12:
            proximo_mes_data = date(
                ano + 1,
                1,
                1
            )
        else:
            proximo_mes_data = date(
                ano,
                mes + 1,
                1
            )

        mes_anterior = mes_anterior.strftime(
            "%Y-%m"
        )

        proximo_mes = proximo_mes_data.strftime(
            "%Y-%m"
        )

        meses_pt_br = [
            "",
            "Janeiro",
            "Fevereiro",
            "Março",
            "Abril",
            "Maio",
            "Junho",
            "Julho",
            "Agosto",
            "Setembro",
            "Outubro",
            "Novembro",
            "Dezembro"
        ]

        mes_exibicao = (
            f"{meses_pt_br[mes]} de {ano}"
        )

        # =====================================================
        # BUSCAR AGENDAMENTOS DO PRÓPRIO LÍDER
        # =====================================================

        try:
            cursor.execute("""
                SELECT
                    ag.id,
                    ag.pratica,
                    ag.lider_id,
                    ag.data_programada,
                    ag.tema_id,
                    ag.colaborador_previsto_id,
                    ag.procedimento_id,
                    ag.observacao,
                    ag.status,
                    ag.registro_executado_id,
                    ag.houve_alteracao,
                    ag.justificativa_alteracao,

                    tema.nome AS nome_tema,

                    colaborador.nome
                        AS nome_colaborador_previsto,

                    colaborador.matricula
                        AS matricula_colaborador_previsto,

                    CONCAT(
                        COALESCE(td.sigla, ''),
                        CASE
                            WHEN td.sigla IS NOT NULL
                            THEN ' '
                            ELSE ''
                        END,
                        COALESCE(p.numero_documento, ''),
                        CASE
                            WHEN p.numero_documento IS NOT NULL
                            THEN ' - '
                            ELSE ''
                        END,
                        COALESCE(p.titulo, '')
                    ) AS nome_procedimento

                FROM agendamentos_ssma ag

                LEFT JOIN hs_temas tema
                    ON tema.id = ag.tema_id

                LEFT JOIN usuarios colaborador
                    ON colaborador.id =
                       ag.colaborador_previsto_id

                LEFT JOIN procedimentos p
                    ON p.id = ag.procedimento_id

                LEFT JOIN tipos_documento td
                    ON td.id = p.tipo_documento_id

                WHERE ag.lider_id = %s
                  AND ag.data_programada >= %s
                  AND ag.data_programada <= %s

                ORDER BY
                    ag.data_programada ASC,
                    ag.id ASC
            """, (
                usuario_logado_id,
                primeiro_dia_mes,
                ultimo_dia_mes
            ))

            agendamentos = cursor.fetchall()

        except Exception as e:
            fechar_conexao()

            flash(
                f"Erro ao carregar os agendamentos: {e}",
                "danger"
            )

            return redirect(
                url_for("main.dashboard")
            )

        # =====================================================
        # VERIFICAR SE A ROTA DE EXECUÇÃO JÁ EXISTE
        # =====================================================

        endpoint_execucao_disponivel = (
            "main.executar_agendamento_ssma"
            in current_app.view_functions
        )

        # =====================================================
        # CALCULAR STATUS VISUAL E RESUMO
        # =====================================================

        resumo = {
            "agendadas": 0,
            "concluidas": 0,
            "vencidas": 0,
            "com_alteracao": 0
        }

        agendamentos_por_data = {}

        for item in agendamentos:
            data_programada = item.get(
                "data_programada"
            )

            status_banco = (
                item.get("status")
                or "agendada"
            ).strip().lower()

            registro_executado_id = item.get(
                "registro_executado_id"
            )

            houve_alteracao = bool(
                int(
                    item.get("houve_alteracao")
                    or 0
                )
            )

            # ---------------------------------------------
            # STATUS VISUAL
            # ---------------------------------------------

            if status_banco == "cancelada":
                status_visual = "cancelada"

            elif (
                registro_executado_id
                or status_banco.startswith("concluida")
            ):
                if (
                    status_banco
                    == "concluida_com_alteracao"
                    or houve_alteracao
                ):
                    status_visual = (
                        "concluida_com_alteracao"
                    )

                elif (
                    status_banco
                    == "concluida_com_atraso"
                ):
                    status_visual = (
                        "concluida_com_atraso"
                    )

                else:
                    status_visual = "concluida"

            elif (
                status_banco == "agendada"
                and data_programada
            ):
                if data_programada < hoje:
                    status_visual = "vencida"

                elif data_programada == hoje:
                    status_visual = "hoje"

                else:
                    status_visual = "agendada"

            elif status_banco == "vencida":
                status_visual = "vencida"

            else:
                status_visual = status_banco

            item["status_visual"] = status_visual

            # ---------------------------------------------
            # PERMISSÃO VISUAL DE EXECUÇÃO
            # ---------------------------------------------

            item["pode_executar"] = (
                endpoint_execucao_disponivel
                and not registro_executado_id
                and status_visual
                in {
                    "agendada",
                    "hoje",
                    "vencida"
                }
            )

            # ---------------------------------------------
            # RESUMO DO MÊS
            # ---------------------------------------------

            if status_visual in {
                "agendada",
                "hoje"
            }:
                resumo["agendadas"] += 1

            if status_visual == "vencida":
                resumo["vencidas"] += 1

            if status_visual in {
                "concluida",
                "concluida_com_alteracao",
                "concluida_com_atraso"
            }:
                resumo["concluidas"] += 1

            if (
                houve_alteracao
                or status_visual
                == "concluida_com_alteracao"
            ):
                resumo["com_alteracao"] += 1

            # ---------------------------------------------
            # AGRUPAR POR DATA
            # ---------------------------------------------

            if data_programada:
                data_chave = (
                    data_programada.isoformat()
                    if hasattr(
                        data_programada,
                        "isoformat"
                    )
                    else str(data_programada)
                )

                agendamentos_por_data.setdefault(
                    data_chave,
                    []
                ).append(item)

        # =====================================================
        # MONTAR CALENDÁRIO
        # =====================================================

        calendario_objeto = calendar.Calendar(
            firstweekday=calendar.MONDAY
        )

        semanas_do_mes = (
            calendario_objeto.monthdatescalendar(
                ano,
                mes
            )
        )

        calendario_semanas = []

        for semana in semanas_do_mes:
            dias_semana = []

            for data_dia in semana:
                data_iso = data_dia.isoformat()

                dias_semana.append({
                    "numero": data_dia.day,
                    "data": data_iso,
                    "no_mes": (
                        data_dia.year == ano
                        and data_dia.month == mes
                    ),
                    "hoje": (
                        data_dia == hoje
                    ),
                    "agendamentos": (
                        agendamentos_por_data.get(
                            data_iso,
                            []
                        )
                    )
                })

            calendario_semanas.append(
                dias_semana
            )

        fechar_conexao()

        return render_template(
            "meu_calendario_ssma.html",
            lider=lider,
            mes_selecionado=mes_selecionado,
            mes_exibicao=mes_exibicao,
            mes_anterior=mes_anterior,
            proximo_mes=proximo_mes,
            resumo=resumo,
            calendario_semanas=calendario_semanas
        )

    @blueprint.route(
        "/executar_agendamento_ssma/<int:id>",
        methods=["GET"]
    )
    @login_required
    @lider_ssma_required
    def executar_agendamento_ssma(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        usuario_id = session.get("usuario_id")

        try:
            if not usuario_id:
                flash(
                    "Não foi possível identificar o usuário logado.",
                    "danger"
                )

                return redirect(
                    url_for("main.login")
                )

            cursor.execute("""
                SELECT
                    ag.id,
                    ag.pratica,
                    ag.lider_id,
                    ag.data_programada,
                    ag.tema_id,
                    ag.colaborador_previsto_id,
                    ag.procedimento_id,
                    ag.status,
                    ag.registro_executado_id
                FROM agendamentos_ssma ag
                WHERE ag.id = %s
                  AND ag.lider_id = %s
            """, (
                id,
                usuario_id
            ))

            agendamento = cursor.fetchone()

            if not agendamento:
                flash(
                    "Agendamento não encontrado ou não pertence ao seu usuário.",
                    "warning"
                )

                return redirect(
                    url_for("main.meu_calendario_ssma")
                )

            data_programada = agendamento.get(
                "data_programada"
            )

            mes_retorno = (
                data_programada.strftime("%Y-%m")
                if (
                    data_programada
                    and hasattr(
                        data_programada,
                        "strftime"
                    )
                )
                else datetime.today().strftime("%Y-%m")
            )

            next_url = url_for(
                "main.meu_calendario_ssma",
                mes=mes_retorno
            )

            if agendamento.get(
                "registro_executado_id"
            ):
                flash(
                    "Esta prática já foi executada.",
                    "warning"
                )

                return redirect(next_url)

            if (
                agendamento.get("status")
                == "cancelada"
            ):
                flash(
                    "Não é possível executar um agendamento cancelado.",
                    "warning"
                )

                return redirect(next_url)

            pratica = (
                agendamento.get("pratica")
                or ""
            ).strip()

            # =================================================
            # HORA DE SEGURANÇA
            # =================================================

            if pratica == "hora_seguranca":
                return redirect(
                    url_for(
                        "main.lancar_hs",
                        agendamento_id=agendamento["id"],
                        id_tema=(
                            agendamento.get(
                                "tema_id"
                            )
                            or ""
                        ),
                        participante_id=(
                            agendamento.get(
                                "colaborador_previsto_id"
                            )
                            or ""
                        ),
                        next=next_url
                    )
                )

            # =================================================
            # AUDITORIA DE PADRÃO
            # =================================================

            if pratica == "auditoria_padrao":
                return redirect(
                    url_for(
                        "main.lancar_ap",
                        agendamento_id=agendamento["id"],
                        auditado_id=(
                            agendamento.get(
                                "colaborador_previsto_id"
                            )
                            or ""
                        ),
                        procedimento_id=(
                            agendamento.get(
                                "procedimento_id"
                            )
                            or ""
                        ),
                        next=next_url
                    )
                )

            # =================================================
            # INSPEÇÃO DE FRENTE DE SERVIÇO
            # =================================================

            if pratica == "ifs":
                return redirect(
                    url_for(
                        "main.lancar_ifs",
                        agendamento_id=agendamento["id"],
                        next=next_url
                    )
                )

            flash(
                "A prática informada no agendamento é inválida.",
                "danger"
            )

            return redirect(next_url)

        except Exception as e:
            flash(
                f"Erro ao abrir a prática agendada: {e}",
                "danger"
            )

            return redirect(
                url_for("main.meu_calendario_ssma")
            )

        finally:
            try:
                cursor.close()
            except Exception:
                pass

            try:
                conn.close()
            except Exception:
                pass

    @blueprint.route(
        '/relatorio_aderencia_ssma',
        methods=['GET']
    )

    @login_required
    @gerenciar_agendamentos_ssma_required
    def relatorio_aderencia_ssma():

        conn = None
        cursor = None

        usuario_id = session.get('usuario_id')
        centro_custo_usuario_id = session.get(
            'centro_custos_id'
        )

        if not usuario_id:
            flash(
                'Usuário logado não encontrado.',
                'danger'
            )
            return redirect(
                url_for('main.login')
            )

        if not centro_custo_usuario_id:
            flash(
                'Não foi possível identificar o centro de custo do usuário.',
                'danger'
            )
            return redirect(
                url_for('main.dashboard')
            )

        # =========================================================
        # FILTROS
        # =========================================================

        hoje = datetime.today()

        mes_padrao = hoje.strftime(
            '%Y-%m'
        )

        mes_selecionado = (
            request.args.get('mes')
            or mes_padrao
        ).strip()

        pratica = (
            request.args.get('pratica')
            or ''
        ).strip()

        lider_id = request.args.get(
            'lider_id',
            type=int
        )

        # =========================================================
        # ORDENAÇÃO
        # =========================================================

        ordenar_por = (
            request.args.get('ordenar_por')
            or 'data_programada'
        ).strip()

        direcao = (
            request.args.get('direcao')
            or 'desc'
        ).strip().lower()

        if direcao not in [
            'asc',
            'desc'
        ]:
            direcao = 'desc'

        colunas_ordenacao = {
            'agendamento_id': 'vw.agendamento_id',
            'data_programada': 'vw.data_programada',
            'data_realizada': 'vw.data_realizada',
            'pratica': 'vw.pratica',
            'lider': 'lider.nome',
            'resultado_programacao': (
                'vw.resultado_programacao'
            ),
            'classificacao_aderencia': (
                'vw.classificacao_aderencia'
            ),
            'desvios_identificados': (
                'vw.desvios_identificados'
            )
        }

        coluna_ordenacao = colunas_ordenacao.get(
            ordenar_por,
            'vw.data_programada'
        )

        # =========================================================
        # PAGINAÇÃO
        # =========================================================

        pagina = request.args.get(
            'pagina',
            default=1,
            type=int
        )

        pagina = max(
            pagina,
            1
        )

        # Quantidade fixa para manter o padrão do sistema.
        por_pagina = 25

        # =========================================================
        # TRATAMENTO DO MÊS
        # =========================================================

        try:
            ano, mes = map(
                int,
                mes_selecionado.split('-')
            )

            if mes < 1 or mes > 12:
                raise ValueError

            primeiro_dia = datetime(
                ano,
                mes,
                1
            ).date()

            ultimo_dia_numero = calendar.monthrange(
                ano,
                mes
            )[1]

            ultimo_dia = datetime(
                ano,
                mes,
                ultimo_dia_numero
            ).date()

            data_inicio = primeiro_dia.strftime(
                '%Y-%m-%d'
            )

            data_fim = ultimo_dia.strftime(
                '%Y-%m-%d'
            )

        except (
            ValueError,
            TypeError
        ):
            flash(
                'Mês informado inválido.',
                'warning'
            )

            return redirect(
                url_for(
                    'main.relatorio_aderencia_ssma'
                )
            )

        try:
            conn = get_db_connection()

            cursor = conn.cursor(
                dictionary=True
            )

            # =====================================================
            # FILTROS SQL
            # =====================================================

            condicoes = [
                'vw.data_programada BETWEEN %s AND %s',
                'lider.centro_custos_id = %s'
            ]

            parametros = [
                data_inicio,
                data_fim,
                centro_custo_usuario_id
            ]

            if pratica:
                condicoes.append(
                    'vw.pratica = %s'
                )

                parametros.append(
                    pratica
                )

            if lider_id:
                condicoes.append(
                    'vw.lider_id = %s'
                )

                parametros.append(
                    lider_id
                )

            where_sql = ' AND '.join(
                condicoes
            )

            # =====================================================
            # 1. INDICADORES GERAIS
            # =====================================================

            cursor.execute(f"""
                SELECT
                    COUNT(*) AS total_programado,

                    COALESCE(
                        SUM(
                            CASE
                                WHEN vw.registro_executado_id
                                     IS NOT NULL
                                    THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS total_concluido,

                    COALESCE(
                        SUM(
                            CASE
                                WHEN vw.resultado_programacao IN (
                                    'Cumprida na data programada',
                                    'Cumprida antecipadamente'
                                )
                                    THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS total_no_prazo,

                    COALESCE(
                        SUM(
                            CASE
                                WHEN vw.resultado_programacao =
                                     'Cumprida com atraso'
                                    THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS total_com_atraso,

                    COALESCE(
                        SUM(
                            CASE
                                WHEN vw.classificacao_aderencia =
                                     'Aderente'
                                    THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS total_aderente,

                    COALESCE(
                        SUM(
                            CASE
                                WHEN vw.classificacao_aderencia =
                                     'Aderente com ressalva'
                                    THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS total_com_ressalva,

                    COALESCE(
                        SUM(
                            CASE
                                WHEN vw.classificacao_aderencia =
                                     'Não aderente'
                                    THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS total_nao_aderente,

                    COALESCE(
                        SUM(
                            CASE
                                WHEN vw.classificacao_aderencia =
                                     'Pendente'
                                    THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS total_pendente,

                    COALESCE(
                        SUM(
                            CASE
                                WHEN vw.classificacao_aderencia =
                                     'Cancelada'
                                    THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS total_cancelado,

                    COALESCE(
                        ROUND(
                            100.0
                            * SUM(
                                CASE
                                    WHEN vw.classificacao_aderencia =
                                         'Aderente'
                                        THEN 1
                                    ELSE 0
                                END
                            )
                            / NULLIF(
                                SUM(
                                    CASE
                                        WHEN vw.classificacao_aderencia
                                             IN (
                                                'Aderente',
                                                'Aderente com ressalva',
                                                'Não aderente'
                                             )
                                            THEN 1
                                        ELSE 0
                                    END
                                ),
                                0
                            ),
                            2
                        ),
                        0
                    ) AS percentual_aderencia,

                    COALESCE(
                        ROUND(
                            100.0
                            * SUM(
                                CASE
                                    WHEN vw.registro_executado_id
                                         IS NOT NULL
                                        THEN 1
                                    ELSE 0
                                END
                            )
                            / NULLIF(
                                SUM(
                                    CASE
                                        WHEN vw.classificacao_aderencia
                                             <> 'Cancelada'
                                            THEN 1
                                        ELSE 0
                                    END
                                ),
                                0
                            ),
                            2
                        ),
                        0
                    ) AS percentual_execucao

                FROM vw_aderencia_agendamentos_ssma vw

                INNER JOIN usuarios lider
                    ON lider.id = vw.lider_id

                WHERE {where_sql}
            """, tuple(parametros))

            dados_indicadores = (
                cursor.fetchone()
                or {}
            )

            indicadores = {
                'total_programado': int(
                    dados_indicadores.get(
                        'total_programado'
                    )
                    or 0
                ),

                'total_concluido': int(
                    dados_indicadores.get(
                        'total_concluido'
                    )
                    or 0
                ),

                'total_no_prazo': int(
                    dados_indicadores.get(
                        'total_no_prazo'
                    )
                    or 0
                ),

                'total_com_atraso': int(
                    dados_indicadores.get(
                        'total_com_atraso'
                    )
                    or 0
                ),

                'total_aderente': int(
                    dados_indicadores.get(
                        'total_aderente'
                    )
                    or 0
                ),

                'total_com_ressalva': int(
                    dados_indicadores.get(
                        'total_com_ressalva'
                    )
                    or 0
                ),

                'total_nao_aderente': int(
                    dados_indicadores.get(
                        'total_nao_aderente'
                    )
                    or 0
                ),

                'total_pendente': int(
                    dados_indicadores.get(
                        'total_pendente'
                    )
                    or 0
                ),

                'total_cancelado': int(
                    dados_indicadores.get(
                        'total_cancelado'
                    )
                    or 0
                ),

                'percentual_aderencia': float(
                    dados_indicadores.get(
                        'percentual_aderencia'
                    )
                    or 0
                ),

                'percentual_execucao': float(
                    dados_indicadores.get(
                        'percentual_execucao'
                    )
                    or 0
                )
            }

            # =====================================================
            # 2. RESUMO POR PRÁTICA
            # =====================================================

            cursor.execute(f"""
                SELECT
                    vw.pratica,

                    CASE
                        WHEN vw.pratica = 'hora_seguranca'
                            THEN 'Hora de Segurança'

                        WHEN vw.pratica = 'auditoria_padrao'
                            THEN 'Auditoria de Padrão'

                        WHEN vw.pratica = 'ifs'
                            THEN 'IFS'

                        ELSE vw.pratica
                    END AS pratica_nome,

                    COUNT(*) AS total_programado,

                    COALESCE(
                        SUM(
                            CASE
                                WHEN vw.registro_executado_id
                                     IS NOT NULL
                                    THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS total_concluido,

                    COALESCE(
                        SUM(
                            CASE
                                WHEN vw.classificacao_aderencia =
                                     'Aderente'
                                    THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS total_aderente,

                    COALESCE(
                        SUM(
                            CASE
                                WHEN vw.classificacao_aderencia =
                                     'Aderente com ressalva'
                                    THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS total_com_ressalva,

                    COALESCE(
                        SUM(
                            CASE
                                WHEN vw.classificacao_aderencia =
                                     'Não aderente'
                                    THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS total_nao_aderente,

                    COALESCE(
                        SUM(
                            CASE
                                WHEN vw.classificacao_aderencia =
                                     'Pendente'
                                    THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS total_pendente,

                    COALESCE(
                        SUM(
                            CASE
                                WHEN vw.classificacao_aderencia =
                                     'Cancelada'
                                    THEN 1
                                ELSE 0
                            END
                        ),
                        0
                    ) AS total_cancelado,

                    COALESCE(
                        ROUND(
                            100.0
                            * SUM(
                                CASE
                                    WHEN vw.classificacao_aderencia =
                                         'Aderente'
                                        THEN 1
                                    ELSE 0
                                END
                            )
                            / NULLIF(
                                SUM(
                                    CASE
                                        WHEN vw.classificacao_aderencia
                                             IN (
                                                'Aderente',
                                                'Aderente com ressalva',
                                                'Não aderente'
                                             )
                                            THEN 1
                                        ELSE 0
                                    END
                                ),
                                0
                            ),
                            2
                        ),
                        0
                    ) AS percentual_aderencia

                FROM vw_aderencia_agendamentos_ssma vw

                INNER JOIN usuarios lider
                    ON lider.id = vw.lider_id

                WHERE {where_sql}

                GROUP BY
                    vw.pratica

                ORDER BY
                    pratica_nome
            """, tuple(parametros))

            resumo_praticas = (
                cursor.fetchall()
                or []
            )

            for resumo in resumo_praticas:
                resumo['total_programado'] = int(
                    resumo.get('total_programado')
                    or 0
                )

                resumo['total_concluido'] = int(
                    resumo.get('total_concluido')
                    or 0
                )

                resumo['total_aderente'] = int(
                    resumo.get('total_aderente')
                    or 0
                )

                resumo['total_com_ressalva'] = int(
                    resumo.get('total_com_ressalva')
                    or 0
                )

                resumo['total_nao_aderente'] = int(
                    resumo.get('total_nao_aderente')
                    or 0
                )

                resumo['total_pendente'] = int(
                    resumo.get('total_pendente')
                    or 0
                )

                resumo['total_cancelado'] = int(
                    resumo.get('total_cancelado')
                    or 0
                )

                resumo['percentual_aderencia'] = float(
                    resumo.get('percentual_aderencia')
                    or 0
                )

            # =====================================================
            # 3. TOTAL DE REGISTROS
            # =====================================================

            cursor.execute(f"""
                SELECT
                    COUNT(*) AS total_registros

                FROM vw_aderencia_agendamentos_ssma vw

                INNER JOIN usuarios lider
                    ON lider.id = vw.lider_id

                WHERE {where_sql}
            """, tuple(parametros))

            resultado_total = (
                cursor.fetchone()
                or {}
            )

            total_registros = int(
                resultado_total.get(
                    'total_registros'
                )
                or 0
            )

            total_paginas = max(
                (
                    total_registros
                    + por_pagina
                    - 1
                ) // por_pagina,
                1
            )

            if pagina > total_paginas:
                pagina = total_paginas

            offset = (
                pagina - 1
            ) * por_pagina

            # =====================================================
            # 4. TABELA ANALÍTICA
            # =====================================================

            parametros_tabela = (
                parametros
                + [
                    por_pagina,
                    offset
                ]
            )

            cursor.execute(f"""
                SELECT
                    vw.*,

                    lider.nome AS lider_nome,
                    lider.matricula AS lider_matricula,

                    executor.nome AS executor_nome,
                    executor.matricula AS executor_matricula,

                    tema_programado.nome
                        AS tema_programado_nome,

                    tema_realizado.nome
                        AS tema_realizado_nome,

                    colaborador_previsto.nome
                        AS colaborador_previsto_nome,

                    auditado_realizado.nome
                        AS auditado_realizado_nome,

                    procedimento_programado.titulo
                        AS procedimento_programado_nome,

                    procedimento_realizado.titulo
                        AS procedimento_realizado_nome

                FROM vw_aderencia_agendamentos_ssma vw

                INNER JOIN usuarios lider
                    ON lider.id = vw.lider_id

                LEFT JOIN usuarios executor
                    ON executor.id = vw.executor_id

                LEFT JOIN hs_temas tema_programado
                    ON tema_programado.id =
                       vw.tema_programado_id

                LEFT JOIN hs_temas tema_realizado
                    ON tema_realizado.id =
                       vw.tema_realizado_id

                LEFT JOIN usuarios colaborador_previsto
                    ON colaborador_previsto.id =
                       vw.colaborador_previsto_id

                LEFT JOIN usuarios auditado_realizado
                    ON auditado_realizado.id =
                       vw.auditado_realizado_id

                LEFT JOIN procedimentos procedimento_programado
                    ON procedimento_programado.id =
                       vw.procedimento_programado_id

                LEFT JOIN procedimentos procedimento_realizado
                    ON procedimento_realizado.id =
                       vw.procedimento_realizado_id

                WHERE {where_sql}

                ORDER BY
                    {coluna_ordenacao} {direcao.upper()},
                    vw.agendamento_id DESC

                LIMIT %s
                OFFSET %s
            """, tuple(parametros_tabela))

            registros = (
                cursor.fetchall()
                or []
            )

            # =====================================================
            # 5. LÍDERES DO CENTRO DE CUSTO
            # =====================================================

            cursor.execute("""
                SELECT
                    id,
                    nome,
                    matricula
                FROM usuarios
                WHERE ativo = 1
                  AND centro_custos_id = %s
                  AND pode_ser_lider_ssma = 1
                ORDER BY nome
            """, (
                centro_custo_usuario_id,
            ))

            lideres = (
                cursor.fetchall()
                or []
            )

            # Garante que o ID recebido pertence ao CC e é líder SSMA.
            lider_selecionado = None

            if lider_id:
                lider_selecionado = next(
                    (
                        lider
                        for lider in lideres
                        if lider['id'] == lider_id
                    ),
                    None
                )

                if not lider_selecionado:
                    flash(
                        'O líder selecionado não pertence ao seu centro de custo.',
                        'warning'
                    )

                    return redirect(
                        url_for(
                            'main.relatorio_aderencia_ssma',
                            mes=mes_selecionado,
                            pratica=pratica
                        )
                    )

            # =====================================================
            # 6. PAGINAÇÃO
            # =====================================================

            paginacao = {
                'pagina_atual': pagina,
                'por_pagina': por_pagina,
                'total_registros': total_registros,
                'total_paginas': total_paginas,
                'tem_anterior': pagina > 1,
                'tem_proxima': pagina < total_paginas,
                'pagina_anterior': (
                    pagina - 1
                    if pagina > 1
                    else None
                ),
                'pagina_proxima': (
                    pagina + 1
                    if pagina < total_paginas
                    else None
                )
            }

            return render_template(
                'relatorio_aderencia_ssma.html',

                registros=registros,
                indicadores=indicadores,
                resumo_praticas=resumo_praticas,

                lideres=lideres,
                lider_selecionado=lider_selecionado,

                paginacao=paginacao,

                mes_selecionado=mes_selecionado,
                pratica_selecionada=pratica,
                lider_id_selecionado=lider_id,

                ordenar_por=ordenar_por,
                direcao=direcao
            )

        except Exception as e:

            if conn:
                conn.rollback()

            flash(
                f'Erro ao gerar o relatório de aderência: {e}',
                'danger'
            )

            return redirect(
                url_for('main.dashboard')
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

