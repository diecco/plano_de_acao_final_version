from datetime import date

from flask import flash, redirect, render_template, request, session, url_for

from app.decorators import login_required, module_required
from app.utils.db import get_db_connection


STATUS_ACR = {
    "Rascunho",
    "Em Investigação",
    "Aguardando Informações",
    "Concluída",
    "Cancelada",
}

ORDENACOES_ACR = {
    "numero": "i.ano",
    "ocorrencia": "COALESCE(i.equipamento_processo, i.descricao_ocorrencia)",
    "classificacao": "c.nome",
    "gravidade": "g.ordem",
    "responsavel": "u.nome",
    "status": "i.status",
    "data": "i.data_ocorrencia",
}


def _aplicar_escopo(query, params, alias="i"):
    perfil = session.get("perfil")
    usuario_id = session.get("usuario_id")

    if perfil == "basico":
        query += f"""
            AND (
                {alias}.criador_id = %s
                OR {alias}.responsavel_id = %s
                OR EXISTS (
                    SELECT 1
                    FROM acr_participantes ap
                    WHERE ap.investigacao_id = {alias}.id
                      AND ap.usuario_id = %s
                      AND ap.ativo = 1
                )
            )
        """
        params.extend([usuario_id, usuario_id, usuario_id])
    elif perfil == "intermediario":
        query += f" AND {alias}.centro_custos_id = %s"
        params.append(session.get("centro_custos_id"))

    return query, params


def _buscar_dominios(cursor):
    dominios = {}
    for chave, tabela in (
        ("origens", "acr_origens"),
        ("classificacoes", "acr_classificacoes"),
        ("gravidades", "acr_gravidades"),
        ("metodologias", "acr_metodologias"),
    ):
        filtro_implementada = (
            " AND implementada = 1"
            if tabela == "acr_metodologias"
            else ""
        )
        cursor.execute(
            f"""
            SELECT id, nome
            FROM {tabela}
            WHERE ativo = 1
            {filtro_implementada}
            ORDER BY ordem, nome
            """
        )
        dominios[chave] = cursor.fetchall()
    return dominios


def _buscar_centros_e_responsaveis(cursor):
    centro_sessao = session.get("centro_custos_id")

    cursor.execute(
        """
        SELECT id, codigo, descricao, superintendencia_id
        FROM centros_custos
        WHERE ativo = 1
          AND id = %s
        """,
        (centro_sessao,),
    )
    centros = cursor.fetchall()

    cursor.execute(
        """
        SELECT id, nome, matricula, centro_custos_id
        FROM usuarios
        WHERE ativo = 1
          AND tem_acesso_sistema = 1
          AND (acesso_acr = 1 OR perfil = 'administrador')
          AND centro_custos_id = %s
        ORDER BY nome
        """,
        (centro_sessao,),
    )

    return centros, cursor.fetchall()


def _validar_id_no_dominio(cursor, tabela, registro_id):
    cursor.execute(
        f"SELECT id FROM {tabela} WHERE id = %s AND ativo = 1",
        (registro_id,),
    )
    return cursor.fetchone() is not None


def _buscar_investigacao_acessivel(cursor, investigacao_id):
    query = """
        SELECT
            i.*,
            o.nome AS origem,
            c.nome AS classificacao,
            g.nome AS gravidade,
            m.nome AS metodologia,
            m.codigo AS metodologia_codigo,
            u.nome AS responsavel,
            uc.nome AS criador,
            cc.codigo AS centro_codigo,
            cc.descricao AS centro_descricao
        FROM acr_investigacoes i
        LEFT JOIN acr_origens o ON o.id = i.origem_id
        LEFT JOIN acr_classificacoes c ON c.id = i.classificacao_id
        LEFT JOIN acr_gravidades g ON g.id = i.gravidade_id
        LEFT JOIN acr_metodologias m ON m.id = i.metodologia_id
        LEFT JOIN usuarios u ON u.id = i.responsavel_id
        LEFT JOIN usuarios uc ON uc.id = i.criador_id
        LEFT JOIN centros_custos cc ON cc.id = i.centro_custos_id
        WHERE i.id = %s
          AND i.ativo = 1
    """
    params = [investigacao_id]
    query, params = _aplicar_escopo(query, params)
    cursor.execute(query, params)
    return cursor.fetchone()


def register_investigacao_causa_raiz_routes(blueprint):
    @blueprint.route("/acr")
    @login_required
    @module_required("acesso_acr")
    def investigacoes_acr():
        busca = (request.args.get("busca") or "").strip()
        status = (request.args.get("status") or "").strip()
        origem_id = request.args.get("origem_id", type=int)
        classificacao_id = request.args.get("classificacao_id", type=int)
        gravidade_id = request.args.get("gravidade_id", type=int)
        data_inicio = (request.args.get("data_inicio") or "").strip()
        data_fim = (request.args.get("data_fim") or "").strip()
        ordenacao = (request.args.get("ordenacao") or "numero").strip()
        direcao = (request.args.get("direcao") or "desc").strip().lower()

        if ordenacao not in ORDENACOES_ACR:
            ordenacao = "numero"
        if direcao not in ("asc", "desc"):
            direcao = "desc"

        for valor, rotulo in (
            (data_inicio, "inicial"),
            (data_fim, "final"),
        ):
            if valor:
                try:
                    date.fromisoformat(valor)
                except ValueError:
                    flash(f"Informe uma data {rotulo} válida.", "warning")
                    if rotulo == "inicial":
                        data_inicio = ""
                    else:
                        data_fim = ""
        if data_inicio and data_fim and data_inicio > data_fim:
            flash(
                "A data inicial não pode ser posterior à data final.",
                "warning",
            )
            data_inicio = ""
            data_fim = ""

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            dominios = _buscar_dominios(cursor)
            query = """
                SELECT
                    i.id,
                    i.numero,
                    i.data_ocorrencia,
                    i.equipamento_processo,
                    i.descricao_ocorrencia,
                    i.status,
                    i.criado_em,
                    o.nome AS origem,
                    c.nome AS classificacao,
                    g.nome AS gravidade,
                    m.nome AS metodologia,
                    u.nome AS responsavel,
                    cc.codigo AS centro_codigo,
                    cc.descricao AS centro_descricao
                FROM acr_investigacoes i
                LEFT JOIN acr_origens o ON o.id = i.origem_id
                LEFT JOIN acr_classificacoes c ON c.id = i.classificacao_id
                LEFT JOIN acr_gravidades g ON g.id = i.gravidade_id
                LEFT JOIN acr_metodologias m ON m.id = i.metodologia_id
                LEFT JOIN usuarios u ON u.id = i.responsavel_id
                LEFT JOIN centros_custos cc ON cc.id = i.centro_custos_id
                WHERE i.ativo = 1
            """
            params = []
            query, params = _aplicar_escopo(query, params)

            if busca:
                termo = f"%{busca}%"
                query += """
                    AND (
                        i.numero LIKE %s
                        OR i.equipamento_processo LIKE %s
                        OR i.descricao_ocorrencia LIKE %s
                        OR u.nome LIKE %s
                    )
                """
                params.extend([termo, termo, termo, termo])
            if status in STATUS_ACR:
                query += " AND i.status = %s"
                params.append(status)
            if origem_id:
                query += " AND i.origem_id = %s"
                params.append(origem_id)
            if classificacao_id:
                query += " AND i.classificacao_id = %s"
                params.append(classificacao_id)
            if gravidade_id:
                query += " AND i.gravidade_id = %s"
                params.append(gravidade_id)
            if data_inicio:
                query += " AND i.data_ocorrencia >= %s"
                params.append(data_inicio)
            if data_fim:
                query += " AND i.data_ocorrencia <= %s"
                params.append(data_fim)

            coluna_ordenacao = ORDENACOES_ACR[ordenacao]
            direcao_sql = direcao.upper()
            if ordenacao == "numero":
                query += (
                    f" ORDER BY {coluna_ordenacao} {direcao_sql}, "
                    f"i.sequencial {direcao_sql}"
                )
            else:
                query += (
                    f" ORDER BY {coluna_ordenacao} {direcao_sql}, "
                    "i.ano DESC, i.sequencial DESC"
                )
            cursor.execute(query, params)
            investigacoes = cursor.fetchall()

            indicadores = {
                "total": len(investigacoes),
                "em_andamento": sum(
                    item["status"] in (
                        "Em Investigação",
                        "Aguardando Informações",
                    )
                    for item in investigacoes
                ),
                "rascunhos": sum(
                    item["status"] == "Rascunho" for item in investigacoes
                ),
                "concluidas": sum(
                    item["status"] == "Concluída" for item in investigacoes
                ),
            }
            return render_template(
                "investigacoes_causa_raiz.html",
                investigacoes=investigacoes,
                indicadores=indicadores,
                dominios=dominios,
                status_acr=sorted(STATUS_ACR),
                filtros={
                    "busca": busca,
                    "status": status,
                    "origem_id": origem_id,
                    "classificacao_id": classificacao_id,
                    "gravidade_id": gravidade_id,
                    "data_inicio": data_inicio,
                    "data_fim": data_fim,
                },
                ordenacao=ordenacao,
                direcao=direcao,
            )
        finally:
            cursor.close()
            conn.close()

    @blueprint.route("/acr/<int:investigacao_id>")
    @login_required
    @module_required("acesso_acr")
    def detalhar_investigacao_acr(investigacao_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            investigacao = _buscar_investigacao_acessivel(
                cursor,
                investigacao_id,
            )
            if not investigacao:
                flash("Investigação não encontrada ou fora do seu escopo.", "danger")
                return redirect(url_for("main.investigacoes_acr"))

            cursor.execute(
                """
                SELECT ordem, pergunta, resposta, causa_raiz, atualizado_em
                FROM acr_5_porques
                WHERE investigacao_id = %s
                ORDER BY ordem
                """,
                (investigacao_id,),
            )
            respostas_banco = {
                item["ordem"]: item for item in cursor.fetchall()
            }
            porques = [
                {
                    "ordem": ordem,
                    "pergunta": (
                        respostas_banco.get(ordem, {}).get("pergunta") or ""
                    ),
                    "resposta": (
                        respostas_banco.get(ordem, {}).get("resposta") or ""
                    ),
                    "causa_raiz": bool(
                        respostas_banco.get(ordem, {}).get("causa_raiz")
                    ),
                }
                for ordem in range(1, 6)
            ]
            cursor.execute(
                """
                SELECT status, atualizado_em
                FROM acr_etapas
                WHERE investigacao_id = %s
                  AND codigo = '5_porques'
                """,
                (investigacao_id,),
            )
            etapa = cursor.fetchone() or {
                "status": "Não iniciada",
                "atualizado_em": None,
            }
            return render_template(
                "investigacao_causa_raiz_detalhe.html",
                investigacao=investigacao,
                porques=porques,
                etapa=etapa,
                somente_leitura=investigacao["status"] in (
                    "Concluída",
                    "Cancelada",
                ),
            )
        finally:
            cursor.close()
            conn.close()

    @blueprint.route(
        "/acr/<int:investigacao_id>/5-porques",
        methods=["POST"],
    )
    @login_required
    @module_required("acesso_acr")
    def salvar_5_porques_acr(investigacao_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            investigacao = _buscar_investigacao_acessivel(
                cursor,
                investigacao_id,
            )
            if not investigacao:
                flash("Investigação não encontrada ou fora do seu escopo.", "danger")
                return redirect(url_for("main.investigacoes_acr"))
            if investigacao["status"] in ("Concluída", "Cancelada"):
                flash(
                    "Esta investigação não permite alterações no estado atual.",
                    "warning",
                )
                return redirect(
                    url_for(
                        "main.detalhar_investigacao_acr",
                        investigacao_id=investigacao_id,
                    )
                )
            if investigacao["metodologia_codigo"] != "5_porques":
                flash("A metodologia desta investigação não é 5 Porquês.", "danger")
                return redirect(
                    url_for(
                        "main.detalhar_investigacao_acr",
                        investigacao_id=investigacao_id,
                    )
                )

            perguntas = [
                (request.form.get(f"pergunta_{ordem}") or "").strip()
                for ordem in range(1, 6)
            ]
            respostas = [
                (request.form.get(f"resposta_{ordem}") or "").strip()
                for ordem in range(1, 6)
            ]
            acao_formulario = (request.form.get("acao") or "salvar").strip()
            causa_raiz_ordem = request.form.get("causa_raiz_ordem", type=int)

            if acao_formulario not in ("salvar", "concluir"):
                raise ValueError("Ação inválida para a etapa dos 5 Porquês.")
            if not any(perguntas) and not any(respostas):
                raise ValueError("Registre ao menos a primeira pergunta e resposta.")
            if any(len(pergunta) > 500 for pergunta in perguntas):
                raise ValueError(
                    "Cada pergunta deve possuir no máximo 500 caracteres."
                )
            if any(len(resposta) > 4000 for resposta in respostas):
                raise ValueError(
                    "Cada resposta deve possuir no máximo 4.000 caracteres."
                )
            encontrou_vazio = False
            for pergunta, resposta in zip(perguntas, respostas):
                if bool(pergunta) != bool(resposta):
                    raise ValueError(
                        "Cada nível preenchido precisa ter pergunta e resposta."
                    )
                if not pergunta:
                    encontrou_vazio = True
                elif encontrou_vazio:
                    raise ValueError(
                        "Preencha os Porquês em sequência, sem deixar lacunas."
                    )

            ultima_resposta = max(
                indice
                for indice, resposta in enumerate(respostas, start=1)
                if resposta
            )
            concluir_etapa = acao_formulario == "concluir"
            if concluir_etapa:
                if causa_raiz_ordem not in range(1, ultima_resposta + 1):
                    raise ValueError(
                        "Selecione qual resposta representa a causa raiz."
                    )

            for ordem, (pergunta, resposta) in enumerate(
                zip(perguntas, respostas),
                start=1,
            ):
                if not pergunta:
                    cursor.execute(
                        """
                        DELETE FROM acr_5_porques
                        WHERE investigacao_id = %s AND ordem = %s
                        """,
                        (investigacao_id, ordem),
                    )
                    continue
                cursor.execute(
                    """
                    INSERT INTO acr_5_porques (
                        investigacao_id, ordem, pergunta, resposta,
                        causa_raiz, respondido_por
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        pergunta = VALUES(pergunta),
                        resposta = VALUES(resposta),
                        causa_raiz = VALUES(causa_raiz),
                        respondido_por = VALUES(respondido_por)
                    """,
                    (
                        investigacao_id,
                        ordem,
                        pergunta,
                        resposta,
                        int(concluir_etapa and ordem == causa_raiz_ordem),
                        session.get("usuario_id"),
                    ),
                )

            status_etapa = "Concluída" if concluir_etapa else "Em andamento"
            cursor.execute(
                """
                INSERT INTO acr_etapas (
                    investigacao_id, codigo, status, iniciado_em,
                    concluido_em, atualizado_por
                )
                VALUES (
                    %s, '5_porques', %s, NOW(),
                    CASE WHEN %s = 'Concluída' THEN NOW() ELSE NULL END,
                    %s
                )
                ON DUPLICATE KEY UPDATE
                    status = VALUES(status),
                    iniciado_em = COALESCE(iniciado_em, NOW()),
                    concluido_em = CASE
                        WHEN VALUES(status) = 'Concluída' THEN NOW()
                        ELSE NULL
                    END,
                    atualizado_por = VALUES(atualizado_por)
                """,
                (
                    investigacao_id,
                    status_etapa,
                    status_etapa,
                    session.get("usuario_id"),
                ),
            )
            if investigacao["status"] == "Rascunho":
                cursor.execute(
                    """
                    UPDATE acr_investigacoes
                    SET status = 'Em Investigação'
                    WHERE id = %s
                    """,
                    (investigacao_id,),
                )

            if concluir_etapa:
                descricao_causa = respostas[causa_raiz_ordem - 1]
                cursor.execute(
                    """
                    SELECT id
                    FROM acr_causas
                    WHERE investigacao_id = %s
                      AND confirmada = 1
                    ORDER BY id
                    LIMIT 1
                    """,
                    (investigacao_id,),
                )
                causa_existente = cursor.fetchone()
                if causa_existente:
                    cursor.execute(
                        """
                        UPDATE acr_causas
                        SET descricao = %s,
                            metodologia_id = %s,
                            identificada_por = %s,
                            identificada_em = NOW()
                        WHERE id = %s
                        """,
                        (
                            descricao_causa,
                            investigacao["metodologia_id"],
                            session.get("usuario_id"),
                            causa_existente["id"],
                        ),
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO acr_causas (
                            investigacao_id, metodologia_id, descricao,
                            confirmada, identificada_por
                        )
                        VALUES (%s, %s, %s, 1, %s)
                        """,
                        (
                            investigacao_id,
                            investigacao["metodologia_id"],
                            descricao_causa,
                            session.get("usuario_id"),
                        ),
                    )
            else:
                cursor.execute(
                    """
                    UPDATE acr_causas
                    SET confirmada = 0,
                        invalidada_em = NOW(),
                        motivo_invalidacao = %s
                    WHERE investigacao_id = %s
                      AND confirmada = 1
                    """,
                    (
                        "Etapa dos 5 Porquês reaberta para revisão.",
                        investigacao_id,
                    ),
                )

            cursor.execute(
                """
                INSERT INTO acr_historico (
                    investigacao_id, usuario_id, evento, etapa
                )
                VALUES (%s, %s, %s, '5_porques')
                """,
                (
                    investigacao_id,
                    session.get("usuario_id"),
                    (
                        "Etapa 5 Porquês concluída"
                        if concluir_etapa
                        else "Rascunho dos 5 Porquês salvo"
                    ),
                ),
            )
            conn.commit()
            flash(
                (
                    "Causa raiz confirmada com sucesso."
                    if concluir_etapa
                    else "Investigação salva como rascunho."
                ),
                "success",
            )
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "danger")
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

        return redirect(
            url_for(
                "main.detalhar_investigacao_acr",
                investigacao_id=investigacao_id,
            )
        )

    @blueprint.route("/acr/nova", methods=["GET", "POST"])
    @login_required
    @module_required("acesso_acr")
    def nova_investigacao_acr():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            dominios = _buscar_dominios(cursor)
            centros, responsaveis = _buscar_centros_e_responsaveis(cursor)
            if not centros:
                flash(
                    "Seu usuário precisa estar vinculado a um centro de custos "
                    "ativo para criar uma ACR.",
                    "danger",
                )
                return redirect(url_for("main.investigacoes_acr"))

            if request.method == "GET":
                return render_template(
                    "nova_investigacao_causa_raiz.html",
                    dominios=dominios,
                    centros=centros,
                    responsaveis=responsaveis,
                    hoje=date.today().isoformat(),
                )

            origem_id = request.form.get("origem_id", type=int)
            classificacao_id = request.form.get("classificacao_id", type=int)
            gravidade_id = request.form.get("gravidade_id", type=int)
            metodologia_id = request.form.get("metodologia_id", type=int)
            centro_custos_id = session.get("centro_custos_id")
            responsavel_id = request.form.get("responsavel_id", type=int)
            data_ocorrencia = (request.form.get("data_ocorrencia") or "").strip()
            equipamento = (
                request.form.get("equipamento_processo") or ""
            ).strip()
            descricao = (
                request.form.get("descricao_ocorrencia") or ""
            ).strip()
            origem_outros = (
                request.form.get("origem_outros") or ""
            ).strip() or None

            obrigatorios = (
                origem_id,
                classificacao_id,
                gravidade_id,
                metodologia_id,
                centro_custos_id,
                responsavel_id,
                data_ocorrencia,
                descricao,
            )
            if not all(obrigatorios):
                raise ValueError("Preencha todos os campos obrigatórios.")
            try:
                data_ocorrencia_convertida = date.fromisoformat(data_ocorrencia)
            except ValueError as exc:
                raise ValueError("Informe uma data de ocorrência válida.") from exc
            if data_ocorrencia_convertida > date.today():
                raise ValueError("A data da ocorrência não pode ser futura.")

            if not _validar_id_no_dominio(cursor, "acr_origens", origem_id):
                raise ValueError("Origem inválida.")
            if not _validar_id_no_dominio(
                cursor, "acr_classificacoes", classificacao_id
            ):
                raise ValueError("Classificação inválida.")
            if not _validar_id_no_dominio(
                cursor, "acr_gravidades", gravidade_id
            ):
                raise ValueError("Gravidade inválida.")

            cursor.execute(
                """
                SELECT id
                FROM acr_metodologias
                WHERE id = %s AND ativo = 1 AND implementada = 1
                """,
                (metodologia_id,),
            )
            if not cursor.fetchone():
                raise ValueError("A metodologia selecionada não está disponível.")

            centros_validos = {item["id"]: item for item in centros}
            responsaveis_validos = {item["id"]: item for item in responsaveis}
            if centro_custos_id not in centros_validos:
                raise ValueError("Centro de custos fora do seu escopo.")
            if responsavel_id not in responsaveis_validos:
                raise ValueError("Responsável fora do seu escopo.")
            if (
                responsaveis_validos[responsavel_id]["centro_custos_id"]
                != centro_custos_id
            ):
                raise ValueError(
                    "O responsável deve pertencer ao centro de custos da ACR."
                )
            origem_outros_registro = next(
                (
                    item
                    for item in dominios["origens"]
                    if item["id"] == origem_id
                ),
                None,
            )
            if (
                origem_outros_registro
                and origem_outros_registro["nome"].strip().lower() == "outros"
                and not origem_outros
            ):
                raise ValueError("Detalhe a origem selecionada como Outros.")

            ano = date.today().year
            cursor.execute(
                """
                INSERT INTO acr_sequencias (ano, ultimo_numero)
                VALUES (%s, 0)
                ON DUPLICATE KEY UPDATE ano = VALUES(ano)
                """,
                (ano,),
            )
            cursor.execute(
                """
                SELECT ultimo_numero
                FROM acr_sequencias
                WHERE ano = %s
                FOR UPDATE
                """,
                (ano,),
            )
            sequencial = cursor.fetchone()["ultimo_numero"] + 1
            cursor.execute(
                """
                UPDATE acr_sequencias
                SET ultimo_numero = %s
                WHERE ano = %s
                """,
                (sequencial, ano),
            )
            numero = f"ACR-{sequencial:03d}/{ano}"
            centro = centros_validos[centro_custos_id]

            cursor.execute(
                """
                INSERT INTO acr_investigacoes (
                    ano, sequencial, numero, origem_id, origem_outros,
                    classificacao_id, gravidade_id, metodologia_id,
                    data_ocorrencia, data_investigacao,
                    equipamento_processo, descricao_ocorrencia,
                    responsavel_id, criador_id, centro_custos_id,
                    superintendencia_id, status
                )
                VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, CURRENT_DATE,
                    %s, %s, %s, %s, %s,
                    %s, 'Rascunho'
                )
                """,
                (
                    ano,
                    sequencial,
                    numero,
                    origem_id,
                    origem_outros,
                    classificacao_id,
                    gravidade_id,
                    metodologia_id,
                    data_ocorrencia,
                    equipamento,
                    descricao,
                    responsavel_id,
                    session.get("usuario_id"),
                    centro_custos_id,
                    centro.get("superintendencia_id"),
                ),
            )
            investigacao_id = cursor.lastrowid
            cursor.execute(
                """
                INSERT INTO acr_participantes (
                    investigacao_id, usuario_id, adicionado_por
                )
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE ativo = 1
                """,
                (
                    investigacao_id,
                    responsavel_id,
                    session.get("usuario_id"),
                ),
            )
            cursor.execute(
                """
                INSERT INTO acr_historico (
                    investigacao_id, usuario_id, evento, etapa
                )
                VALUES (%s, %s, 'Investigação criada', 'Cadastro')
                """,
                (investigacao_id, session.get("usuario_id")),
            )
            conn.commit()
            flash(f"{numero} criada com sucesso.", "success")
            return redirect(url_for("main.investigacoes_acr"))
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "danger")
            return render_template(
                "nova_investigacao_causa_raiz.html",
                dominios=dominios,
                centros=centros,
                responsaveis=responsaveis,
                hoje=date.today().isoformat(),
            )
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
