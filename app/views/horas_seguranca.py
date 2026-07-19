import json
import os
from datetime import date, datetime, timedelta

from flask import flash, redirect, render_template, request, session, url_for

from app.decorators import admin_required, login_required, module_required
from app.utils.db import get_db_connection


def register_horas_seguranca_routes(blueprint):
    @blueprint.route("/cadastrar_hs")
    @login_required
    @admin_required
    def cadastrar_hs():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Busca todos os temas
        cursor.execute("SELECT * FROM hs_temas ORDER BY id DESC")
        temas = cursor.fetchall()

        # Se nenhum tema ainda foi cadastrado
        tema_atual = None
        itens_tema = []

        # Se o usuário passou um id_tema na URL, foca nele
        id_tema = request.args.get("id_tema")
        if id_tema:
            cursor.execute("SELECT * FROM hs_temas WHERE id=%s", (id_tema,))
            tema_atual = cursor.fetchone()

            if tema_atual:
                cursor.execute("""
                    SELECT i.*
                    FROM hs_itens_verificacao i
                    WHERE i.id_tema = %s
                    ORDER BY i.ordem
                """, (id_tema,))
                itens_tema = cursor.fetchall()

        conn.close()
        return render_template("cadastrar_hs.html", temas=temas, tema_atual=tema_atual, itens_tema=itens_tema)


    @blueprint.route("/cadastrar_hs/tema", methods=["POST"])
    @login_required
    @admin_required
    def cadastrar_hs_tema():
        nome_tema = request.form.get("nome_tema")

        if not nome_tema:
            flash("O nome do tema é obrigatório.", "danger")
            return redirect(url_for("main.cadastrar_hs"))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO hs_temas (nome, status) VALUES (%s, 1)", (nome_tema,))
        id_tema = cursor.lastrowid
        conn.commit()
        conn.close()

        flash("Tema cadastrado com sucesso!", "success")
        return redirect(url_for("main.cadastrar_hs", id_tema=id_tema))


    @blueprint.route("/cadastrar_hs/item", methods=["POST"])
    @login_required
    @admin_required
    def cadastrar_hs_item():
        id_tema = request.form.get("id_tema")
        texto = request.form.get("texto")
        ordem = request.form.get("ordem") or None

        if not id_tema or not texto:
            flash("Preencha todos os campos obrigatórios.", "danger")
            return redirect(url_for("main.cadastrar_hs"))

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO hs_itens_verificacao (id_tema, texto, ordem, status)
            VALUES (%s, %s, %s, 1)
        """, (id_tema, texto, ordem))
        conn.commit()
        conn.close()

        flash("Item cadastrado com sucesso!", "success")
        return redirect(url_for("main.cadastrar_hs", id_tema=id_tema))


    @blueprint.route("/editar_hs/item/<int:id>", methods=["GET", "POST"])
    @login_required
    @admin_required
    def editar_hs_item(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == "POST":
            texto = request.form.get("texto")
            ordem = request.form.get("ordem") or None
            if not texto:
                flash("A descrição do item é obrigatória.", "danger")
                return redirect(url_for("main.editar_hs_item", id=id))

            cursor.execute(
                "UPDATE hs_itens_verificacao SET texto=%s, ordem=%s WHERE id=%s",
                (texto, ordem, id)
            )
            conn.commit()
            cursor.execute("SELECT id_tema FROM hs_itens_verificacao WHERE id=%s", (id,))
            item = cursor.fetchone()
            conn.close()

            flash("Item atualizado com sucesso!", "success")
            return redirect(url_for("main.cadastrar_hs", id_tema=item["id_tema"]))

        cursor.execute("SELECT * FROM hs_itens_verificacao WHERE id=%s", (id,))
        item = cursor.fetchone()
        conn.close()
        return render_template("editar_hs_item.html", item=item)


    @blueprint.route("/habilitar_hs/tema/<int:id>")
    @login_required
    @admin_required
    def habilitar_hs_tema(id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE hs_temas SET status=1 WHERE id=%s", (id,))
        conn.commit()
        conn.close()
        flash("Tema habilitado!", "success")
        return redirect(url_for("main.cadastrar_hs", id_tema=id))


    @blueprint.route("/desabilitar_hs/tema/<int:id>")
    @login_required
    @admin_required
    def desabilitar_hs_tema(id):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE hs_temas SET status=0 WHERE id=%s", (id,))
        conn.commit()
        conn.close()
        flash("Tema desabilitado!", "warning")
        return redirect(url_for("main.cadastrar_hs", id_tema=id))


    @blueprint.route("/habilitar_hs/item/<int:id>")
    @login_required
    @admin_required
    def habilitar_hs_item(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id_tema FROM hs_itens_verificacao WHERE id=%s", (id,))
        item = cursor.fetchone()

        cursor.execute("UPDATE hs_itens_verificacao SET status=1 WHERE id=%s", (id,))
        conn.commit()
        conn.close()

        flash("Item habilitado!", "success")
        return redirect(url_for("main.cadastrar_hs", id_tema=item["id_tema"]))


    @blueprint.route("/desabilitar_hs/item/<int:id>")
    @login_required
    @admin_required
    def desabilitar_hs_item(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT id_tema FROM hs_itens_verificacao WHERE id=%s", (id,))
        item = cursor.fetchone()

        cursor.execute("UPDATE hs_itens_verificacao SET status=0 WHERE id=%s", (id,))
        conn.commit()
        conn.close()

        flash("Item desabilitado!", "warning")
        return redirect(url_for("main.cadastrar_hs", id_tema=item["id_tema"]))


    @blueprint.route("/lancar_hs", methods=["GET", "POST"])
    @login_required
    @module_required("acesso_ssma")
    def lancar_hs():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        perfil = (session.get("perfil") or "").strip().lower()
        usuario_id = session.get("usuario_id")
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

        def calcular_turno(hora_str):
            if not hora_str:
                return None

            try:
                hora_int = int(hora_str.split(":")[0])
            except (ValueError, IndexError):
                return None

            if 0 <= hora_int < 12:
                return "Manhã"

            if 12 <= hora_int < 18:
                return "Tarde"

            return "Noite"

        def validar_next_url(valor):
            """
            Aceita somente endereços internos da aplicação.
            """
            valor = (valor or "").strip()

            if valor.startswith("/") and not valor.startswith("//"):
                return valor

            return url_for("main.listar_hs")

        def buscar_agendamento(agendamento_id):
            if not agendamento_id:
                return None

            cursor.execute("""
                SELECT
                    id,
                    pratica,
                    lider_id,
                    data_programada,
                    tema_id,
                    colaborador_previsto_id,
                    status,
                    registro_executado_id,
                    houve_alteracao,
                    justificativa_alteracao
                FROM agendamentos_ssma
                WHERE id = %s
                  AND lider_id = %s
                  AND pratica = 'hora_seguranca'
            """, (
                agendamento_id,
                usuario_id
            ))

            return cursor.fetchone()

        def montar_url_retorno_formulario(
            agendamento_id=None,
            id_tema=None,
            participante_id=None,
            next_url=None
        ):
            parametros = {}

            if agendamento_id:
                parametros["agendamento_id"] = agendamento_id

            if id_tema:
                parametros["id_tema"] = id_tema

            if participante_id:
                parametros["participante_id"] = participante_id

            if next_url:
                parametros["next"] = next_url

            return url_for(
                "main.lancar_hs",
                **parametros
            )

        # =====================================================
        # VALIDAR USUÁRIO LOGADO
        # =====================================================

        if not usuario_id:
            fechar_conexao()

            flash(
                "Não foi possível identificar o usuário logado.",
                "danger"
            )

            return redirect(url_for("main.login"))

        # =====================================================
        # CONTEXTO DO AGENDAMENTO E RETORNO
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
                "ou incompatível com Hora de Segurança.",
                "warning"
            )

            return redirect(
                url_for("main.meu_calendario_ssma")
            )

        if agendamento:
            if agendamento.get("registro_executado_id"):
                fechar_conexao()

                flash(
                    "Esta Hora de Segurança já foi executada.",
                    "warning"
                )

                return redirect(next_url)

            if (
                agendamento.get("status")
                == "cancelada"
            ):
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
            data = request.form.get("data")
            hora = request.form.get("hora")
            turno = calcular_turno(hora)

            local = (
                request.form.get("local")
                or ""
            ).strip()

            id_tema = request.form.get(
                "id_tema",
                type=int
            )

            # Auditor sempre será o usuário logado
            id_auditor = usuario_id

            participantes = [
                str(participante_id).strip()
                for participante_id
                in request.form.getlist("participantes")
                if str(participante_id).strip()
            ]

            justificativa_alteracao = (
                request.form.get(
                    "justificativa_alteracao"
                )
                or ""
            ).strip()

            participante_previsto_id = (
                agendamento.get(
                    "colaborador_previsto_id"
                )
                if agendamento
                else None
            )

            if not (
                data
                and hora
                and id_tema
                and id_auditor
                and turno
            ):
                flash(
                    "Preencha todos os campos obrigatórios.",
                    "danger"
                )

                fechar_conexao()

                return redirect(
                    montar_url_retorno_formulario(
                        agendamento_id=agendamento_id,
                        id_tema=id_tema,
                        participante_id=participante_previsto_id,
                        next_url=next_url
                    )
                )

            # -------------------------------------------------
            # VALIDAR TEMA
            # -------------------------------------------------

            cursor.execute("""
                SELECT id
                FROM hs_temas
                WHERE id = %s
                  AND status = 1
            """, (id_tema,))

            if not cursor.fetchone():
                flash(
                    "O tema selecionado não existe ou está desabilitado.",
                    "warning"
                )

                fechar_conexao()

                return redirect(
                    montar_url_retorno_formulario(
                        agendamento_id=agendamento_id,
                        id_tema=id_tema,
                        participante_id=participante_previsto_id,
                        next_url=next_url
                    )
                )

            # -------------------------------------------------
            # VALIDAR PARTICIPANTES E ESCOPO
            # -------------------------------------------------

            participantes_validos = []

            if participantes:
                participantes_unicos = list(
                    dict.fromkeys(participantes)
                )

                placeholders = ", ".join(
                    ["%s"] * len(participantes_unicos)
                )

                if perfil in {
                    "administrador",
                    "avancado"
                }:
                    query_participantes = f"""
                        SELECT id
                        FROM usuarios
                        WHERE ativo = 1
                          AND id IN ({placeholders})
                    """

                    params_participantes = (
                        participantes_unicos
                    )

                else:
                    query_participantes = f"""
                        SELECT id
                        FROM usuarios
                        WHERE ativo = 1
                          AND centro_custos_id = %s
                          AND id IN ({placeholders})
                    """

                    params_participantes = [
                        centro_custos_id,
                        *participantes_unicos
                    ]

                cursor.execute(
                    query_participantes,
                    params_participantes
                )

                participantes_validos = [
                    str(item["id"])
                    for item in cursor.fetchall()
                ]

                if (
                    len(participantes_validos)
                    != len(participantes_unicos)
                ):
                    flash(
                        "Um ou mais participantes são inválidos "
                        "ou estão fora do seu centro de custos.",
                        "warning"
                    )

                    fechar_conexao()

                    return redirect(
                        montar_url_retorno_formulario(
                            agendamento_id=agendamento_id,
                            id_tema=id_tema,
                            participante_id=participante_previsto_id,
                            next_url=next_url
                        )
                    )

            # -------------------------------------------------
            # COMPARAR EXECUÇÃO COM O AGENDAMENTO
            # -------------------------------------------------

            houve_alteracao = 0

            if agendamento:
                tema_previsto_id = agendamento.get(
                    "tema_id"
                )

                if (
                    tema_previsto_id
                    and int(id_tema)
                    != int(tema_previsto_id)
                ):
                    houve_alteracao = 1

                if participante_previsto_id:
                    if (
                        str(participante_previsto_id)
                        not in participantes_validos
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
                            id_tema=id_tema,
                            participante_id=participante_previsto_id,
                            next_url=next_url
                        )
                    )

            try:
                # ---------------------------------------------
                # LOCALIZAR OU CRIAR ORIGEM
                # ---------------------------------------------

                cursor.execute("""
                    SELECT id
                    FROM origens
                    WHERE descricao = %s
                """, (
                    "Hora de Segurança",
                ))

                origem = cursor.fetchone()

                if origem:
                    origem_hs = origem["id"]

                else:
                    cursor.execute("""
                        INSERT INTO origens (
                            descricao,
                            ativo
                        )
                        VALUES (%s, 1)
                    """, (
                        "Hora de Segurança",
                    ))

                    origem_hs = cursor.lastrowid

                # ---------------------------------------------
                # INSERIR REGISTRO PRINCIPAL
                # ---------------------------------------------

                cursor.execute("""
                    INSERT INTO hs_registros (
                        data,
                        hora,
                        turno,
                        local,
                        id_tema,
                        id_auditor,
                        participantes
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
                    data,
                    hora,
                    turno,
                    local,
                    id_tema,
                    id_auditor,
                    ",".join(participantes_validos)
                ))

                id_registro = cursor.lastrowid

                # ---------------------------------------------
                # ITENS DE VERIFICAÇÃO
                # ---------------------------------------------

                cursor.execute("""
                    SELECT *
                    FROM hs_itens_verificacao
                    WHERE id_tema = %s
                      AND status = 1
                    ORDER BY ordem
                """, (id_tema,))

                itens = cursor.fetchall()

                for item in itens:
                    resultado = request.form.get(
                        f"resultado_{item['id']}"
                    )

                    desvio = (
                        request.form.get(
                            f"desvio_{item['id']}"
                        )
                        or ""
                    ).strip()

                    acao = (
                        request.form.get(
                            f"acao_{item['id']}"
                        )
                        or ""
                    ).strip()

                    prazo = request.form.get(
                        f"prazo_{item['id']}"
                    )

                    id_acao_gerada = None

                    if resultado not in {
                        "C",
                        "NC",
                        "NA"
                    }:
                        flash(
                            f"Selecione o resultado do item "
                            f"'{item['texto']}'.",
                            "danger"
                        )

                        conn.rollback()
                        fechar_conexao()

                        return redirect(
                            montar_url_retorno_formulario(
                                agendamento_id=agendamento_id,
                                id_tema=id_tema,
                                participante_id=participante_previsto_id,
                                next_url=next_url
                            )
                        )

                    if resultado == "NC":
                        if not desvio or not acao or not prazo:
                            flash(
                                f"O item '{item['texto']}' foi marcado "
                                "como NC, mas falta preencher desvio, "
                                "ação ou prazo.",
                                "danger"
                            )

                            conn.rollback()
                            fechar_conexao()

                            return redirect(
                                montar_url_retorno_formulario(
                                    agendamento_id=agendamento_id,
                                    id_tema=id_tema,
                                    participante_id=participante_previsto_id,
                                    next_url=next_url
                                )
                            )

                    else:
                        desvio = ""
                        acao = ""
                        prazo = None

                    if resultado == "NC":
                        cursor.execute("""
                            INSERT INTO acoes (
                                origem_id,
                                responsavel_id,
                                descricao,
                                prazo,
                                status,
                                criado_por
                            )
                            VALUES (
                                %s,
                                %s,
                                %s,
                                %s,
                                %s,
                                %s
                            )
                        """, (
                            origem_hs,
                            id_auditor,
                            acao,
                            prazo,
                            "Não iniciada",
                            id_auditor
                        ))

                        id_acao_gerada = (
                            cursor.lastrowid
                        )

                    cursor.execute("""
                        INSERT INTO hs_respostas (
                            id_registro,
                            id_item,
                            resultado,
                            descricao_desvio,
                            descricao_acao,
                            id_acao_gerada
                        )
                        VALUES (
                            %s,
                            %s,
                            %s,
                            %s,
                            %s,
                            %s
                        )
                    """, (
                        id_registro,
                        item["id"],
                        resultado,
                        desvio,
                        acao,
                        id_acao_gerada
                    ))

                # ---------------------------------------------
                # VINCULAR À EXECUÇÃO AGENDADA
                # ---------------------------------------------

                if agendamento:
                    data_programada = agendamento.get(
                        "data_programada"
                    )

                    data_execucao = datetime.strptime(
                        data,
                        "%Y-%m-%d"
                    ).date()

                    if hasattr(
                        data_programada,
                        "date"
                    ) and not isinstance(
                        data_programada,
                        date
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
                          AND pratica = 'hora_seguranca'
                          AND registro_executado_id IS NULL
                    """, (
                        id_registro,
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

            except Exception as e:
                conn.rollback()
                fechar_conexao()

                flash(
                    f"Erro ao registrar Hora de Segurança: {e}",
                    "danger"
                )

                return redirect(
                    montar_url_retorno_formulario(
                        agendamento_id=agendamento_id,
                        id_tema=id_tema,
                        participante_id=participante_previsto_id,
                        next_url=next_url
                    )
                )

            fechar_conexao()

            flash(
                "Hora de Segurança registrada com sucesso!",
                "success"
            )

            return redirect(next_url)

        # =====================================================
        # GET
        # =====================================================

        cursor.execute("""
            SELECT *
            FROM hs_temas
            WHERE status = 1
            ORDER BY nome
        """)

        temas = cursor.fetchall()

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

        # =====================================================
        # TEMA, PARTICIPANTE E DATA INICIAIS
        # =====================================================

        # Tema escolhido na URL.
        # Isso ocorre tanto no acesso direto quanto quando o usuário
        # troca o tema durante a execução de um agendamento.
        id_tema_url = request.args.get(
            "id_tema",
            type=int
        )

        participante_url = request.args.get(
            "participante_id",
            type=int
        )

        data_inicial = datetime.today().strftime(
            "%Y-%m-%d"
        )

        id_tema_selecionado = id_tema_url
        participante_previsto_id = participante_url

        if agendamento:
            tema_agendado = agendamento.get(
                "tema_id"
            )

            colaborador_agendado = agendamento.get(
                "colaborador_previsto_id"
            )

            data_programada = agendamento.get(
                "data_programada"
            )

            # O tema agendado é usado somente na primeira abertura.
            # Caso exista id_tema na URL, significa que o usuário
            # selecionou outro tema e esse valor deve prevalecer.
            if not id_tema_url and tema_agendado is not None:
                try:
                    id_tema_selecionado = int(
                        tema_agendado
                    )
                except (TypeError, ValueError):
                    id_tema_selecionado = None

            # O participante previsto continua sendo o do agendamento,
            # salvo quando um participante tiver sido explicitamente
            # recebido pela URL.
            if not participante_url:
                participante_previsto_id = (
                    colaborador_agendado
                )

            if (
                data_programada
                and hasattr(data_programada, "strftime")
            ):
                data_inicial = data_programada.strftime(
                    "%Y-%m-%d"
                )

        # =====================================================
        # ITENS DO TEMA SELECIONADO
        # =====================================================

        itens = []

        if id_tema_selecionado:
            cursor.execute("""
                SELECT
                    id,
                    id_tema,
                    texto,
                    ordem,
                    status
                FROM hs_itens_verificacao
                WHERE id_tema = %s
                  AND COALESCE(status, 1) = 1
                ORDER BY
                    COALESCE(ordem, 999999),
                    id
            """, (
                id_tema_selecionado,
            ))

            itens = cursor.fetchall()

        # -------------------------------------------------
        # ÚLTIMOS REGISTROS - LÓGICA ORIGINAL PRESERVADA
        # -------------------------------------------------

        query_registros = """
            SELECT
                r.*,
                t.nome AS nome_tema,
                u.nome AS nome_auditor
            FROM hs_registros r
            JOIN hs_temas t
                ON r.id_tema = t.id
            JOIN usuarios u
                ON r.id_auditor = u.id
            WHERE 1 = 1
        """

        params_registros = []

        if perfil == "basico":
            query_registros += """
                AND r.id_auditor = %s
            """

            params_registros.append(
                usuario_id
            )

        elif perfil == "intermediario":
            query_registros += """
                AND u.centro_custos_id = %s
            """

            params_registros.append(
                centro_custos_id
            )

        query_registros += """
            ORDER BY
                r.data DESC,
                r.hora DESC
            LIMIT 20
        """

        cursor.execute(
            query_registros,
            params_registros
        )

        registros = cursor.fetchall()

        for registro in registros:
            if isinstance(
                registro.get("hora"),
                timedelta
            ):
                total_seconds = (
                    registro["hora"].seconds
                )

                horas = (
                    total_seconds // 3600
                )

                minutos = (
                    total_seconds % 3600
                ) // 60

                registro["hora"] = (
                    f"{horas:02d}:{minutos:02d}"
                )

            elif hasattr(
                registro.get("hora"),
                "strftime"
            ):
                registro["hora"] = (
                    registro["hora"].strftime(
                        "%H:%M"
                    )
                )

            if hasattr(
                registro.get("data"),
                "strftime"
            ):
                registro["data"] = (
                    registro["data"].strftime(
                        "%d/%m/%Y"
                    )
                )

        fechar_conexao()

        return render_template(
            "lancar_hs.html",
            hoje=data_inicial,
            agora=datetime.now().strftime("%H:%M"),
            temas=temas,
            usuarios=usuarios,
            usuarios_json=json.dumps(
                [
                    {
                        "id": usuario["id"],
                        "nome": usuario["nome"],
                        "matricula": usuario.get(
                            "matricula"
                        )
                    }
                    for usuario in usuarios
                ],
                ensure_ascii=False
            ),
            itens=itens,
            registros=registros,
            agendamento_id=agendamento_id,
            agendamento=agendamento,
            participante_previsto_id=(
                participante_previsto_id
            ),
            id_tema_selecionado=(
                id_tema_selecionado
            ),
            next_url=next_url
        )

    @blueprint.route("/editar_hs/<int:id>", methods=["GET", "POST"])
    @login_required
    @module_required('acesso_ssma')
    def editar_hs(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        def calcular_turno(hora_str):
            if not hora_str:
                return None

            try:
                hora_int = int(hora_str.split(":")[0])
            except (ValueError, IndexError):
                return None

            if 0 <= hora_int < 12:
                return "Manhã"
            elif 12 <= hora_int < 18:
                return "Tarde"
            else:
                return "Noite"

        # 🔒 NOVO: validação centralizada
        registro = pode_acessar_ssma(cursor, 'hs', id)

        if not registro:
            conn.close()
            flash("Hora de Segurança não encontrada ou você não possui permissão para acessá-la.", "warning")
            return redirect(url_for("main.listar_hs"))

        # 🔒 REGRA DE NEGÓCIO MANTIDA (não alterei)
        if session.get("perfil") != "administrador" and registro["id_auditor"] != session.get("usuario_id"):
            conn.close()
            flash("Você não tem permissão para editar esta Hora de Segurança.", "warning")
            return redirect(url_for("main.listar_hs"))

        if request.method == "POST":
            next_url = request.form.get("next") or url_for("main.listar_hs")

            data = request.form.get("data")
            hora = request.form.get("hora")
            turno = calcular_turno(hora)
            local = request.form.get("local")
            id_tema = request.form.get("id_tema")
            id_auditor = request.form.get("id_auditor")
            participantes = request.form.getlist("participantes")

            if not (data and hora and id_tema and id_auditor and turno):
                flash("Preencha todos os campos obrigatórios.", "danger")
                conn.close()
                return redirect(next_url)

            if session.get("perfil") != "administrador":
                id_auditor = registro["id_auditor"]

            try:
                cursor.execute("""
                    UPDATE hs_registros
                    SET data=%s,
                        hora=%s,
                        turno=%s,
                        local=%s,
                        id_tema=%s,
                        id_auditor=%s,
                        participantes=%s
                    WHERE id=%s
                """, (
                    data,
                    hora,
                    turno,
                    local,
                    id_tema,
                    id_auditor,
                    ",".join(participantes),
                    id
                ))

                cursor.execute("""
                    SELECT *
                    FROM hs_itens_verificacao
                    WHERE id_tema=%s
                      AND status=1
                """, (id_tema,))
                itens = cursor.fetchall()

                for item in itens:
                    resultado = request.form.get(f"resultado_{item['id']}")
                    desvio = (request.form.get(f"desvio_{item['id']}") or "").strip()
                    acao = (request.form.get(f"acao_{item['id']}") or "").strip()
                    prazo = request.form.get(f"prazo_{item['id']}")

                    cursor.execute("""
                        SELECT id, id_acao_gerada
                        FROM hs_respostas
                        WHERE id_registro=%s
                          AND id_item=%s
                    """, (id, item["id"]))
                    resposta_existente = cursor.fetchone()

                    id_acao_gerada = resposta_existente["id_acao_gerada"] if resposta_existente else None

                    if resultado == "NC":
                        if not desvio or not acao or not prazo:
                            flash(
                                f"O item '{item['texto']}' foi marcado como NC, mas falta preencher desvio, ação ou prazo.",
                                "danger"
                            )
                            conn.rollback()
                            conn.close()
                            return redirect(next_url)
                    else:
                        desvio = ""
                        acao = ""
                        prazo = None

                    if resultado == "NC":
                        if id_acao_gerada:
                            cursor.execute("""
                                UPDATE acoes
                                SET descricao=%s,
                                    prazo=%s,
                                    responsavel_id=%s
                                WHERE id=%s
                            """, (acao, prazo, id_auditor, id_acao_gerada))
                        else:
                            cursor.execute("SELECT id FROM origens WHERE descricao=%s", ("Hora de Segurança",))
                            origem = cursor.fetchone()

                            if origem:
                                origem_hs = origem["id"]
                            else:
                                cursor.execute(
                                    "INSERT INTO origens (descricao, ativo) VALUES (%s, 1)",
                                    ("Hora de Segurança",)
                                )
                                origem_hs = cursor.lastrowid

                            cursor.execute("""
                                INSERT INTO acoes (
                                    origem_id,
                                    responsavel_id,
                                    descricao,
                                    prazo,
                                    status,
                                    criado_por
                                )
                                VALUES (%s, %s, %s, %s, %s, %s)
                            """, (
                                origem_hs,
                                id_auditor,
                                acao,
                                prazo,
                                "Não iniciada",
                                id_auditor
                            ))
                            id_acao_gerada = cursor.lastrowid

                    else:
                        if id_acao_gerada:
                            cursor.execute(
                                "UPDATE hs_respostas SET id_acao_gerada=NULL WHERE id=%s",
                                (resposta_existente["id"],)
                            )
                            cursor.execute("DELETE FROM acoes WHERE id=%s", (id_acao_gerada,))
                            id_acao_gerada = None

                    if resposta_existente:
                        cursor.execute("""
                            UPDATE hs_respostas
                            SET resultado=%s,
                                descricao_desvio=%s,
                                descricao_acao=%s,
                                id_acao_gerada=%s
                            WHERE id=%s
                        """, (
                            resultado,
                            desvio,
                            acao,
                            id_acao_gerada,
                            resposta_existente["id"]
                        ))
                    else:
                        cursor.execute("""
                            INSERT INTO hs_respostas (
                                id_registro,
                                id_item,
                                resultado,
                                descricao_desvio,
                                descricao_acao,
                                id_acao_gerada
                            )
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            id,
                            item["id"],
                            resultado,
                            desvio,
                            acao,
                            id_acao_gerada
                        ))

                conn.commit()
                flash("Hora de Segurança atualizada com sucesso!", "success")

            except Exception as e:
                conn.rollback()
                flash(f"Erro ao atualizar Hora de Segurança: {e}", "danger")

            finally:
                conn.close()

            return redirect(next_url)

        cursor.execute("SELECT * FROM hs_temas WHERE status=1 ORDER BY nome")
        temas = cursor.fetchall()

        cursor.execute("SELECT id, nome, matricula FROM usuarios WHERE ativo=1 ORDER BY nome")
        usuarios = cursor.fetchall()

        cursor.execute("""
            SELECT
                i.*,
                r.resultado,
                r.descricao_desvio,
                r.descricao_acao,
                r.id_acao_gerada,
                a.prazo AS prazo_acao
            FROM hs_itens_verificacao i
            LEFT JOIN hs_respostas r
                ON i.id = r.id_item
               AND r.id_registro = %s
            LEFT JOIN acoes a
                ON a.id = r.id_acao_gerada
            WHERE i.id_tema = %s
            ORDER BY i.ordem
        """, (id, registro["id_tema"]))
        itens = cursor.fetchall()

        conn.close()

        return render_template(
            "editar_hs.html",
            registro=registro,
            temas=temas,
            usuarios=usuarios,
            itens=itens
        )

    @blueprint.route("/excluir_hs/<int:id>", methods=["POST"])
    @login_required
    @module_required('acesso_ssma')
    def excluir_hs(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        registro = pode_acessar_ssma(cursor, 'hs', id)

        if not registro:
            conn.close()
            flash("Hora de Segurança não encontrada ou você não possui permissão para excluí-la.", "warning")
            return redirect(url_for("main.listar_hs"))

        # Regra adicional: somente administrador ou auditor que lançou pode excluir
        if session.get("perfil") != "administrador" and registro["id_auditor"] != session.get("usuario_id"):
            conn.close()
            flash("Você não tem permissão para excluir esta Hora de Segurança.", "warning")
            return redirect(url_for("main.listar_hs"))

        cursor.execute("""
            SELECT id_acao_gerada
            FROM hs_respostas
            WHERE id_registro = %s
              AND id_acao_gerada IS NOT NULL
        """, (id,))
        acoes = cursor.fetchall()

        cursor.execute("DELETE FROM hs_respostas WHERE id_registro = %s", (id,))

        for ac in acoes:
            cursor.execute("DELETE FROM acoes WHERE id = %s", (ac["id_acao_gerada"],))

        cursor.execute("DELETE FROM hs_registros WHERE id = %s", (id,))

        conn.commit()
        conn.close()

        flash("Hora de Segurança e ações vinculadas excluídas com sucesso!", "success")
        return redirect(url_for("main.listar_hs"))


    @blueprint.route('/listar_hs', methods=['GET'])
    @login_required
    @module_required('acesso_ssma')
    def listar_hs():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        usuario_id = session.get('usuario_id')
        perfil = session.get('perfil')
        centro_custos_id = session.get('centro_custos_id')

        if request.args.get('limpar'):
            conn.close()
            return redirect(url_for('main.listar_hs'))

        auditor_id = request.args.get('auditor_id', '')
        tema_id = request.args.get('tema_id', '')
        turno = request.args.get('turno', '')
        local = request.args.get('local', '')
        data_inicio = request.args.get('data_inicio', '')
        data_fim = request.args.get('data_fim', '')
        resultado_nc = request.args.get('resultado_nc', '')

        sort = request.args.get('sort', 'data')
        order = request.args.get('order', 'desc')

        page = request.args.get('page', 1, type=int)
        per_page = 30

        if page < 1:
            page = 1

        offset = (page - 1) * per_page

        colunas_validas = {
            'id': 'r.id',
            'data': 'r.data',
            'hora': 'r.hora',
            'turno': 'r.turno',
            'tema': 't.nome',
            'auditor': 'u.nome',
            'local': 'r.local',
            'possui_nc': 'possui_nc'
        }

        coluna_sort = colunas_validas.get(sort, 'r.data')
        direcao = 'ASC' if order == 'asc' else 'DESC'

        filtros_where = """
            FROM hs_registros r
            JOIN hs_temas t ON r.id_tema = t.id
            JOIN usuarios u ON r.id_auditor = u.id
            LEFT JOIN hs_respostas resp ON resp.id_registro = r.id
            WHERE 1=1
        """

        params = []

        # CONTROLE DE ESCOPO POR PERFIL
        if perfil == 'basico':
            filtros_where += " AND r.id_auditor = %s"
            params.append(usuario_id)

        elif perfil == 'intermediario':
            filtros_where += " AND u.centro_custos_id = %s"
            params.append(centro_custos_id)

        # avancado e administrador veem tudo

        if auditor_id:
            filtros_where += " AND r.id_auditor = %s"
            params.append(auditor_id)

        if tema_id:
            filtros_where += " AND r.id_tema = %s"
            params.append(tema_id)

        if turno:
            filtros_where += " AND r.turno = %s"
            params.append(turno)

        if local:
            filtros_where += " AND r.local LIKE %s"
            params.append(f"%{local}%")

        if data_inicio:
            filtros_where += " AND r.data >= %s"
            params.append(data_inicio)

        if data_fim:
            filtros_where += " AND r.data <= %s"
            params.append(data_fim)

        group_by = """
            GROUP BY
                r.id,
                r.id_auditor,
                r.id_tema,
                r.data,
                r.hora,
                r.turno,
                r.local,
                r.participantes,
                t.nome,
                u.nome
        """

        having_clause = ""
        if resultado_nc == 'sim':
            having_clause = " HAVING possui_nc = 1"
        elif resultado_nc == 'nao':
            having_clause = " HAVING possui_nc = 0"

        count_query = f"""
            SELECT COUNT(*) AS total
            FROM (
                SELECT
                    r.id,
                    MAX(CASE WHEN resp.resultado = 'NC' THEN 1 ELSE 0 END) AS possui_nc
                {filtros_where}
                GROUP BY r.id
                {having_clause}
            ) AS subquery
        """

        cursor.execute(count_query, params)
        total_registros = cursor.fetchone()['total']

        total_paginas = (total_registros + per_page - 1) // per_page

        if total_paginas > 0 and page > total_paginas:
            page = total_paginas
            offset = (page - 1) * per_page

        query = f"""
            SELECT
                r.id,
                r.id_auditor,
                r.id_tema,
                r.data,
                r.hora,
                r.turno,
                r.local,
                r.participantes,
                t.nome AS nome_tema,
                u.nome AS nome_auditor,
                MAX(CASE WHEN resp.resultado = 'NC' THEN 1 ELSE 0 END) AS possui_nc
            {filtros_where}
            {group_by}
            {having_clause}
            ORDER BY {coluna_sort} {direcao}
            LIMIT %s OFFSET %s
        """

        cursor.execute(query, params + [per_page, offset])
        registros = cursor.fetchall()

        if perfil in ['administrador', 'avancado']:
            cursor.execute("""
                SELECT id, nome
                FROM usuarios
                WHERE ativo = 1
                ORDER BY nome
            """)
        else:
            cursor.execute("""
                SELECT id, nome
                FROM usuarios
                WHERE ativo = 1
                  AND centro_custos_id = %s
                ORDER BY nome
            """, (centro_custos_id,))

        usuarios = cursor.fetchall()
        mapa_usuarios = {str(u['id']): u['nome'] for u in usuarios}

        for r in registros:
            if r.get('participantes'):
                ids = [p.strip() for p in r['participantes'].split(',') if p.strip()]
                nomes = [mapa_usuarios.get(pid, f'ID {pid}') for pid in ids]
                r['nomes_participantes'] = ', '.join(nomes)
            else:
                r['nomes_participantes'] = ''

            if r.get('hora') and hasattr(r['hora'], 'strftime'):
                r['hora'] = r['hora'].strftime('%H:%M')

            if r.get('data') and hasattr(r['data'], 'strftime'):
                r['data_iso'] = r['data'].strftime('%Y-%m-%d')
            else:
                r['data_iso'] = r.get('data') or ''

        cursor.execute("SELECT id, nome FROM hs_temas WHERE status = 1 ORDER BY nome")
        temas = cursor.fetchall()

        ids_registros = [r["id"] for r in registros]
        itens_por_registro = {}

        if ids_registros:
            placeholders = ", ".join(["%s"] * len(ids_registros))

            cursor.execute(f"""
                SELECT
                    r.id AS id_registro,
                    i.id AS id_item,
                    i.texto,
                    i.ordem,
                    resp.resultado,
                    resp.descricao_desvio,
                    resp.descricao_acao,
                    resp.id_acao_gerada,
                    a.prazo AS prazo_acao
                FROM hs_registros r
                JOIN hs_itens_verificacao i
                    ON i.id_tema = r.id_tema
                   AND i.status = 1
                LEFT JOIN hs_respostas resp
                    ON resp.id_item = i.id
                   AND resp.id_registro = r.id
                LEFT JOIN acoes a
                    ON a.id = resp.id_acao_gerada
                WHERE r.id IN ({placeholders})
                ORDER BY r.id, i.ordem
            """, ids_registros)

            itens_modal = cursor.fetchall()

            for item in itens_modal:
                registro_id = str(item["id_registro"])

                if item.get("prazo_acao") and hasattr(item["prazo_acao"], "strftime"):
                    item["prazo_acao"] = item["prazo_acao"].strftime("%Y-%m-%d")

                itens_por_registro.setdefault(registro_id, []).append(item)

        conn.close()

        filtros = {
            'auditor_id': auditor_id,
            'tema_id': tema_id,
            'turno': turno,
            'local': local,
            'data_inicio': data_inicio,
            'data_fim': data_fim,
            'resultado_nc': resultado_nc,
            'sort': sort,
            'order': order
        }

        return render_template(
            'listar_hs.html',
            registros=registros,
            usuarios=usuarios,
            temas=temas,
            filtros=filtros,
            itens_por_registro=itens_por_registro,
            page=page,
            per_page=per_page,
            total_registros=total_registros,
            total_paginas=total_paginas
        )

