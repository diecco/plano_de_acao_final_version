import re
from datetime import date

from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from app.decorators import admin_required, login_required
from app.utils.db import get_db_connection


PADRAO_PATRIMONIO = re.compile(r"^[A-Z]{4}-\d{4}$")
STATUS_OPERACIONAIS = {
    "disponivel",
    "em_calibracao",
    "com_defeito",
}
STATUS_DASHBOARD = {
    "disponivel": {
        "rotulo": "Disponível",
        "acao": "Iniciar entrega",
        "icone": "bi-box-arrow-up-right",
    },
    "em_uso": {
        "rotulo": "Em uso",
        "acao": "Registrar devolução",
        "icone": "bi-box-arrow-in-down-left",
    },
    "em_calibracao": {
        "rotulo": "Em calibração",
        "acao": "Indisponível",
        "icone": "bi-tools",
    },
    "com_defeito": {
        "rotulo": "Com defeito",
        "acao": "Indisponível",
        "icone": "bi-exclamation-triangle",
    },
}
CONDICOES_DEVOLUCAO = {"perfeitas_condicoes", "com_defeito"}
ORIGENS_DEFEITO = {"mau_uso", "desgaste_normal"}


def normalizar_patrimonio(valor):
    return (valor or "").strip().upper()


def patrimonio_valido(valor):
    return bool(PADRAO_PATRIMONIO.fullmatch(normalizar_patrimonio(valor)))


def converter_data_opcional(valor):
    valor = (valor or "").strip()
    if not valor:
        return None
    return date.fromisoformat(valor)


def normalizar_rfid(valor):
    return (valor or "").strip()


def register_detectores_gas_routes(blueprint):
    endpoint_lista = "main.detectores_gas"

    def redirecionar_lista():
        return redirect(url_for(endpoint_lista))

    def carregar_formulario():
        patrimonio = normalizar_patrimonio(request.form.get("patrimonio"))
        fabricante = (request.form.get("fabricante") or "").strip()
        marca = (request.form.get("marca") or "").strip()
        modelo = (request.form.get("modelo") or "").strip()
        centro_custos_id = request.form.get("centro_custos_id", type=int)
        status_operacional = (
            request.form.get("status_operacional")
            or "disponivel"
        ).strip()

        if not patrimonio_valido(patrimonio):
            raise ValueError(
                "O patrimônio deve seguir o padrão AAAA-0000, "
                "por exemplo PTDG-1921."
            )

        if not fabricante:
            raise ValueError("Informe o fabricante do detector.")

        if not marca:
            raise ValueError("Informe a marca do detector.")

        if not modelo:
            raise ValueError("Informe o modelo do detector.")

        if not centro_custos_id:
            raise ValueError("Selecione o centro de custos.")

        if status_operacional not in STATUS_OPERACIONAIS:
            raise ValueError("Selecione um status operacional válido.")

        try:
            data_calibracao = converter_data_opcional(
                request.form.get("data_calibracao")
            )
            validade_calibracao = converter_data_opcional(
                request.form.get("validade_calibracao")
            )
        except ValueError as exc:
            raise ValueError("Informe datas de calibração válidas.") from exc

        if (
            data_calibracao
            and validade_calibracao
            and validade_calibracao < data_calibracao
        ):
            raise ValueError(
                "A validade da calibração não pode ser anterior "
                "à data da calibração."
            )

        return {
            "patrimonio": patrimonio,
            "fabricante": fabricante,
            "marca": marca,
            "modelo": modelo,
            "data_calibracao": data_calibracao,
            "validade_calibracao": validade_calibracao,
            "centro_custos_id": centro_custos_id,
            "status_operacional": status_operacional,
        }

    def centro_custos_ativo(cursor, centro_custos_id):
        cursor.execute("""
            SELECT id
            FROM centros_custos
            WHERE id = %s
              AND ativo = 1
        """, (centro_custos_id,))
        return cursor.fetchone() is not None

    def buscar_usuario_por_rfid(cursor, uid_rfid):
        uid_rfid = normalizar_rfid(uid_rfid)
        if not uid_rfid:
            raise ValueError("Aproxime o crachá no leitor RFID.")

        cursor.execute("""
            SELECT id, nome, matricula, uid_rfid
            FROM usuarios
            WHERE uid_rfid = %s
              AND ativo = 1
        """, (uid_rfid,))
        usuario = cursor.fetchone()

        if not usuario:
            raise ValueError(
                "RFID não localizado entre os usuários ativos."
            )

        return usuario

    @blueprint.route("/detectores_gas/painel", methods=["GET"])
    @login_required
    @admin_required
    def painel_detectores_gas():
        busca = (request.args.get("busca") or "").strip()
        status = (request.args.get("status") or "").strip()

        condicoes = ["d.ativo = 1"]
        parametros = []

        if status in STATUS_DASHBOARD:
            condicoes.append("d.status_operacional = %s")
            parametros.append(status)
        else:
            status = ""

        if busca:
            condicoes.append("""
                (
                    d.patrimonio LIKE %s
                    OR d.fabricante LIKE %s
                    OR d.marca LIKE %s
                    OR d.modelo LIKE %s
                )
            """)
            termo = f"%{busca}%"
            parametros.extend([termo, termo, termo, termo])

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(f"""
                SELECT
                    d.id,
                    d.patrimonio,
                    d.fabricante,
                    d.marca,
                    d.modelo,
                    d.status_operacional,
                    d.centro_custos_id,
                    cc.codigo AS centro_custos_codigo,
                    cc.descricao AS centro_custos_descricao,
                    retirada.retirado_por_id,
                    usuario_posse.nome AS usuario_posse_nome,
                    usuario_posse.matricula AS usuario_posse_matricula
                FROM detectores_gas d
                JOIN centros_custos cc
                    ON cc.id = d.centro_custos_id
                LEFT JOIN detectores_gas_movimentacoes retirada
                    ON retirada.detector_id = d.id
                   AND retirada.devolvido_em IS NULL
                LEFT JOIN usuarios usuario_posse
                    ON usuario_posse.id = retirada.retirado_por_id
                WHERE {" AND ".join(condicoes)}
                ORDER BY
                    CAST(RIGHT(d.patrimonio, 4) AS UNSIGNED),
                    d.patrimonio
            """, tuple(parametros))
            detectores = cursor.fetchall()

            cursor.execute("""
                SELECT
                    status_operacional,
                    COUNT(*) AS quantidade
                FROM detectores_gas
                WHERE ativo = 1
                GROUP BY status_operacional
            """)
            totais_status = {
                item["status_operacional"]: item["quantidade"]
                for item in cursor.fetchall()
            }
        finally:
            cursor.close()
            conn.close()

        totais = {
            chave: totais_status.get(chave, 0)
            for chave in STATUS_DASHBOARD
        }
        totais["total"] = sum(totais.values())

        return render_template(
            "painel_detectores_gas.html",
            detectores=detectores,
            filtros={
                "busca": busca,
                "status": status,
            },
            status_dashboard=STATUS_DASHBOARD,
            totais=totais,
        )

    @blueprint.route(
        "/detectores_gas/movimentacoes",
        methods=["GET"],
    )
    @login_required
    @admin_required
    def relatorio_movimentacoes_detectores_gas():
        data_inicio_texto = (request.args.get("data_inicio") or "").strip()
        data_fim_texto = (request.args.get("data_fim") or "").strip()
        detector_id = request.args.get("detector_id", type=int)
        usuario_id = request.args.get("usuario_id", type=int)
        situacao = (request.args.get("situacao") or "").strip()

        situacoes_validas = {
            "aberta",
            "finalizada",
            "perfeitas_condicoes",
            "com_defeito",
        }
        if situacao not in situacoes_validas:
            situacao = ""

        try:
            data_inicio = converter_data_opcional(data_inicio_texto)
            data_fim = converter_data_opcional(data_fim_texto)
        except ValueError:
            flash("Informe um período válido para o relatório.", "warning")
            return redirect(
                url_for("main.relatorio_movimentacoes_detectores_gas")
            )

        if data_inicio and data_fim and data_fim < data_inicio:
            flash(
                "A data final não pode ser anterior à data inicial.",
                "warning",
            )
            return redirect(
                url_for("main.relatorio_movimentacoes_detectores_gas")
            )

        condicoes = ["1 = 1"]
        parametros = []

        if data_inicio:
            condicoes.append("m.retirado_em >= %s")
            parametros.append(data_inicio)

        if data_fim:
            condicoes.append(
                "m.retirado_em < DATE_ADD(%s, INTERVAL 1 DAY)"
            )
            parametros.append(data_fim)

        if detector_id:
            condicoes.append("m.detector_id = %s")
            parametros.append(detector_id)

        if usuario_id:
            condicoes.append(
                "(m.retirado_por_id = %s OR m.devolvido_por_id = %s)"
            )
            parametros.extend([usuario_id, usuario_id])

        if situacao == "aberta":
            condicoes.append("m.devolvido_em IS NULL")
        elif situacao == "finalizada":
            condicoes.append("m.devolvido_em IS NOT NULL")
        elif situacao == "perfeitas_condicoes":
            condicoes.append(
                "m.condicao_devolucao = 'perfeitas_condicoes'"
            )
        elif situacao == "com_defeito":
            condicoes.append("m.condicao_devolucao = 'com_defeito'")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(f"""
                SELECT
                    m.id,
                    m.detector_id,
                    d.patrimonio,
                    d.fabricante,
                    d.marca,
                    d.modelo,
                    m.retirado_em,
                    m.devolvido_em,
                    m.condicao_devolucao,
                    m.origem_defeito,
                    entregue.nome AS entregue_por_nome,
                    entregue.matricula AS entregue_por_matricula,
                    retirante.nome AS retirado_por_nome,
                    retirante.matricula AS retirado_por_matricula,
                    recebido.nome AS recebido_por_nome,
                    recebido.matricula AS recebido_por_matricula
                FROM detectores_gas_movimentacoes m
                JOIN detectores_gas d
                    ON d.id = m.detector_id
                JOIN usuarios entregue
                    ON entregue.id = m.entregue_por_id
                JOIN usuarios retirante
                    ON retirante.id = m.retirado_por_id
                LEFT JOIN usuarios recebido
                    ON recebido.id = m.recebido_por_id
                WHERE {" AND ".join(condicoes)}
                ORDER BY m.retirado_em DESC, m.id DESC
            """, tuple(parametros))
            movimentacoes = cursor.fetchall()

            cursor.execute("""
                SELECT id, patrimonio
                FROM detectores_gas
                ORDER BY
                    CAST(RIGHT(patrimonio, 4) AS UNSIGNED),
                    patrimonio
            """)
            detectores = cursor.fetchall()

            cursor.execute("""
                SELECT id, nome, matricula
                FROM usuarios
                ORDER BY nome
            """)
            usuarios = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

        totais = {
            "total": len(movimentacoes),
            "abertas": sum(
                1
                for item in movimentacoes
                if item["devolvido_em"] is None
            ),
            "finalizadas": sum(
                1
                for item in movimentacoes
                if item["devolvido_em"] is not None
            ),
            "com_defeito": sum(
                1
                for item in movimentacoes
                if item["condicao_devolucao"] == "com_defeito"
            ),
        }

        return render_template(
            "relatorio_movimentacoes_detectores_gas.html",
            movimentacoes=movimentacoes,
            detectores=detectores,
            usuarios=usuarios,
            filtros={
                "data_inicio": data_inicio_texto,
                "data_fim": data_fim_texto,
                "detector_id": detector_id,
                "usuario_id": usuario_id,
                "situacao": situacao,
            },
            totais=totais,
        )

    @blueprint.route(
        "/api/detectores_gas/usuario_rfid",
        methods=["POST"],
    )
    @login_required
    @admin_required
    def api_detector_usuario_rfid():
        dados = request.get_json(silent=True) or {}
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            usuario = buscar_usuario_por_rfid(
                cursor,
                dados.get("uid_rfid"),
            )
            return jsonify({
                "sucesso": True,
                "usuario": {
                    "id": usuario["id"],
                    "nome": usuario["nome"],
                    "matricula": usuario.get("matricula"),
                },
            })
        except ValueError as exc:
            return jsonify({
                "sucesso": False,
                "mensagem": str(exc),
            }), 404
        finally:
            cursor.close()
            conn.close()

    @blueprint.route(
        "/api/detectores_gas/<int:detector_id>/entregar",
        methods=["POST"],
    )
    @login_required
    @admin_required
    def entregar_detector_gas(detector_id):
        dados = request.get_json(silent=True) or {}
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT id, patrimonio, ativo, status_operacional
                FROM detectores_gas
                WHERE id = %s
                FOR UPDATE
            """, (detector_id,))
            detector = cursor.fetchone()

            if not detector or not detector["ativo"]:
                raise ValueError("Detector ativo não encontrado.")

            if detector["status_operacional"] != "disponivel":
                raise ValueError(
                    "Este detector não está disponível para entrega."
                )

            responsavel = buscar_usuario_por_rfid(
                cursor,
                dados.get("rfid_responsavel"),
            )
            retirante = buscar_usuario_por_rfid(
                cursor,
                dados.get("rfid_retirante"),
            )

            if responsavel["id"] != session.get("usuario_id"):
                raise ValueError(
                    "O crachá do responsável deve pertencer ao usuário logado."
                )

            cursor.execute("""
                SELECT id
                FROM detectores_gas_movimentacoes
                WHERE detector_id = %s
                  AND devolvido_em IS NULL
                FOR UPDATE
            """, (detector_id,))
            if cursor.fetchone():
                raise ValueError(
                    "Já existe uma movimentação aberta para este detector."
                )

            cursor.execute("""
                INSERT INTO detectores_gas_movimentacoes (
                    detector_id,
                    entregue_por_id,
                    retirado_por_id,
                    rfid_entrega_responsavel,
                    rfid_retirante
                )
                VALUES (%s, %s, %s, %s, %s)
            """, (
                detector_id,
                responsavel["id"],
                retirante["id"],
                normalizar_rfid(dados.get("rfid_responsavel")),
                normalizar_rfid(dados.get("rfid_retirante")),
            ))

            cursor.execute("""
                UPDATE detectores_gas
                SET status_operacional = 'em_uso',
                    atualizado_por = %s
                WHERE id = %s
            """, (session.get("usuario_id"), detector_id))

            conn.commit()
            return jsonify({
                "sucesso": True,
                "mensagem": (
                    f"{detector['patrimonio']} entregue para "
                    f"{retirante['nome']}."
                ),
            })
        except ValueError as exc:
            conn.rollback()
            return jsonify({
                "sucesso": False,
                "mensagem": str(exc),
            }), 400
        except Exception:
            conn.rollback()
            current_app.logger.exception(
                "Erro ao entregar detector de gás %s",
                detector_id,
            )
            return jsonify({
                "sucesso": False,
                "mensagem": "Não foi possível registrar a entrega.",
            }), 500
        finally:
            cursor.close()
            conn.close()

    @blueprint.route(
        "/api/detectores_gas/<int:detector_id>/devolver",
        methods=["POST"],
    )
    @login_required
    @admin_required
    def devolver_detector_gas(detector_id):
        dados = request.get_json(silent=True) or {}
        condicao = (dados.get("condicao_devolucao") or "").strip()
        origem_defeito = (dados.get("origem_defeito") or "").strip()
        observacao = (dados.get("observacao") or "").strip()

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            if condicao not in CONDICOES_DEVOLUCAO:
                raise ValueError("Informe a condição de devolução.")

            if condicao == "com_defeito":
                if origem_defeito not in ORIGENS_DEFEITO:
                    raise ValueError("Informe a origem provável do defeito.")
                if not observacao:
                    raise ValueError(
                        "Descreva o defeito apresentado pelo aparelho."
                    )
            else:
                origem_defeito = None
                observacao = observacao or None

            cursor.execute("""
                SELECT id, patrimonio, ativo, status_operacional
                FROM detectores_gas
                WHERE id = %s
                FOR UPDATE
            """, (detector_id,))
            detector = cursor.fetchone()

            if (
                not detector
                or not detector["ativo"]
                or detector["status_operacional"] != "em_uso"
            ):
                raise ValueError(
                    "Este detector não possui uma entrega ativa."
                )

            cursor.execute("""
                SELECT id, retirado_por_id
                FROM detectores_gas_movimentacoes
                WHERE detector_id = %s
                  AND devolvido_em IS NULL
                ORDER BY id DESC
                LIMIT 1
                FOR UPDATE
            """, (detector_id,))
            movimentacao = cursor.fetchone()

            if not movimentacao:
                raise ValueError(
                    "Movimentação de entrega não encontrada."
                )

            responsavel = buscar_usuario_por_rfid(
                cursor,
                dados.get("rfid_responsavel"),
            )
            devolvente = buscar_usuario_por_rfid(
                cursor,
                dados.get("rfid_devolvente"),
            )

            if responsavel["id"] != session.get("usuario_id"):
                raise ValueError(
                    "O crachá do responsável deve pertencer ao usuário logado."
                )

            if devolvente["id"] != movimentacao["retirado_por_id"]:
                raise ValueError(
                    "A devolução deve ser realizada pela mesma pessoa "
                    "que retirou o aparelho."
                )

            cursor.execute("""
                UPDATE detectores_gas_movimentacoes
                SET recebido_por_id = %s,
                    devolvido_por_id = %s,
                    rfid_recebimento_responsavel = %s,
                    rfid_devolvente = %s,
                    condicao_devolucao = %s,
                    origem_defeito = %s,
                    observacao_devolucao = %s,
                    devolvido_em = CURRENT_TIMESTAMP
                WHERE id = %s
                  AND devolvido_em IS NULL
            """, (
                responsavel["id"],
                devolvente["id"],
                normalizar_rfid(dados.get("rfid_responsavel")),
                normalizar_rfid(dados.get("rfid_devolvente")),
                condicao,
                origem_defeito,
                observacao,
                movimentacao["id"],
            ))

            novo_status = (
                "com_defeito"
                if condicao == "com_defeito"
                else "disponivel"
            )
            cursor.execute("""
                UPDATE detectores_gas
                SET status_operacional = %s,
                    atualizado_por = %s
                WHERE id = %s
            """, (
                novo_status,
                session.get("usuario_id"),
                detector_id,
            ))

            conn.commit()
            return jsonify({
                "sucesso": True,
                "mensagem": (
                    f"Devolução de {detector['patrimonio']} registrada."
                ),
            })
        except ValueError as exc:
            conn.rollback()
            return jsonify({
                "sucesso": False,
                "mensagem": str(exc),
            }), 400
        except Exception:
            conn.rollback()
            current_app.logger.exception(
                "Erro ao devolver detector de gás %s",
                detector_id,
            )
            return jsonify({
                "sucesso": False,
                "mensagem": "Não foi possível registrar a devolução.",
            }), 500
        finally:
            cursor.close()
            conn.close()

    @blueprint.route("/detectores_gas", methods=["GET"])
    @login_required
    @admin_required
    def detectores_gas():
        status = (request.args.get("status") or "").strip()
        busca = (request.args.get("busca") or "").strip()
        centro_custos_id = request.args.get(
            "centro_custos_id",
            type=int
        )

        condicoes = []
        parametros = []

        if status == "ativos":
            condicoes.append("d.ativo = 1")
        elif status == "inativos":
            condicoes.append("d.ativo = 0")

        if busca:
            condicoes.append("""
                (
                    d.patrimonio LIKE %s
                    OR d.fabricante LIKE %s
                    OR d.marca LIKE %s
                    OR d.modelo LIKE %s
                )
            """)
            termo = f"%{busca}%"
            parametros.extend([termo, termo, termo, termo])

        if centro_custos_id:
            condicoes.append("d.centro_custos_id = %s")
            parametros.append(centro_custos_id)

        where_sql = (
            "WHERE " + " AND ".join(condicoes)
            if condicoes
            else ""
        )

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute(f"""
                SELECT
                    d.id,
                    d.patrimonio,
                    d.fabricante,
                    d.marca,
                    d.modelo,
                    d.data_calibracao,
                    d.validade_calibracao,
                    d.status_operacional,
                    d.ativo,
                    d.centro_custos_id,
                    cc.codigo AS centro_custos_codigo,
                    cc.descricao AS centro_custos_descricao
                FROM detectores_gas d
                JOIN centros_custos cc
                    ON cc.id = d.centro_custos_id
                {where_sql}
                ORDER BY
                    d.ativo DESC,
                    d.patrimonio ASC
            """, tuple(parametros))
            detectores = cursor.fetchall()

            cursor.execute("""
                SELECT id, codigo, descricao
                FROM centros_custos
                WHERE ativo = 1
                ORDER BY codigo, descricao
            """)
            centros_custos = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

        return render_template(
            "detectores_gas.html",
            detectores=detectores,
            centros_custos=centros_custos,
            filtros={
                "status": status,
                "busca": busca,
                "centro_custos_id": centro_custos_id,
            },
            status_operacionais=STATUS_OPERACIONAIS,
        )

    @blueprint.route("/detectores_gas/cadastrar", methods=["POST"])
    @login_required
    @admin_required
    def cadastrar_detector_gas():
        conn = None
        cursor = None

        try:
            dados = carregar_formulario()
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            if not centro_custos_ativo(
                cursor,
                dados["centro_custos_id"]
            ):
                raise ValueError("O centro de custos selecionado é inválido.")

            cursor.execute("""
                SELECT id
                FROM detectores_gas
                WHERE patrimonio = %s
            """, (dados["patrimonio"],))

            if cursor.fetchone():
                raise ValueError(
                    "Já existe um detector cadastrado com esse patrimônio."
                )

            cursor.execute("""
                INSERT INTO detectores_gas (
                    patrimonio,
                    fabricante,
                    marca,
                    modelo,
                    data_calibracao,
                    validade_calibracao,
                    centro_custos_id,
                    status_operacional,
                    ativo,
                    criado_por
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1, %s)
            """, (
                dados["patrimonio"],
                dados["fabricante"],
                dados["marca"],
                dados["modelo"],
                dados["data_calibracao"],
                dados["validade_calibracao"],
                dados["centro_custos_id"],
                dados["status_operacional"],
                session.get("usuario_id"),
            ))

            conn.commit()
            flash("Detector de gás cadastrado com sucesso!", "success")
        except ValueError as exc:
            if conn:
                conn.rollback()
            flash(str(exc), "warning")
        except Exception as exc:
            if conn:
                conn.rollback()
            flash(f"Erro ao cadastrar detector de gás: {exc}", "danger")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

        return redirecionar_lista()

    @blueprint.route(
        "/detectores_gas/<int:detector_id>/editar",
        methods=["POST"]
    )
    @login_required
    @admin_required
    def editar_detector_gas(detector_id):
        conn = None
        cursor = None

        try:
            dados = carregar_formulario()
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT id, status_operacional
                FROM detectores_gas
                WHERE id = %s
            """, (detector_id,))
            detector = cursor.fetchone()

            if not detector:
                raise ValueError("Detector de gás não encontrado.")

            if detector["status_operacional"] == "em_uso":
                raise ValueError(
                    "Não é possível editar um detector que está em uso."
                )

            if not centro_custos_ativo(
                cursor,
                dados["centro_custos_id"]
            ):
                raise ValueError("O centro de custos selecionado é inválido.")

            cursor.execute("""
                SELECT id
                FROM detectores_gas
                WHERE patrimonio = %s
                  AND id <> %s
            """, (dados["patrimonio"], detector_id))

            if cursor.fetchone():
                raise ValueError(
                    "Já existe outro detector com esse patrimônio."
                )

            cursor.execute("""
                UPDATE detectores_gas
                SET patrimonio = %s,
                    fabricante = %s,
                    marca = %s,
                    modelo = %s,
                    data_calibracao = %s,
                    validade_calibracao = %s,
                    centro_custos_id = %s,
                    status_operacional = %s,
                    atualizado_por = %s
                WHERE id = %s
            """, (
                dados["patrimonio"],
                dados["fabricante"],
                dados["marca"],
                dados["modelo"],
                dados["data_calibracao"],
                dados["validade_calibracao"],
                dados["centro_custos_id"],
                dados["status_operacional"],
                session.get("usuario_id"),
                detector_id,
            ))

            conn.commit()
            flash("Detector de gás atualizado com sucesso!", "success")
        except ValueError as exc:
            if conn:
                conn.rollback()
            flash(str(exc), "warning")
        except Exception as exc:
            if conn:
                conn.rollback()
            flash(f"Erro ao atualizar detector de gás: {exc}", "danger")
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

        return redirecionar_lista()

    @blueprint.route(
        "/detectores_gas/<int:detector_id>/inativar",
        methods=["POST"]
    )
    @login_required
    @admin_required
    def inativar_detector_gas(detector_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("""
                SELECT status_operacional, ativo
                FROM detectores_gas
                WHERE id = %s
                FOR UPDATE
            """, (detector_id,))
            detector = cursor.fetchone()

            if not detector:
                raise ValueError("Detector de gás não encontrado.")

            if detector["status_operacional"] == "em_uso":
                raise ValueError(
                    "Não é possível inativar um detector que está em uso."
                )

            cursor.execute("""
                UPDATE detectores_gas
                SET ativo = 0,
                    atualizado_por = %s
                WHERE id = %s
            """, (session.get("usuario_id"), detector_id))
            conn.commit()
            flash("Detector de gás inativado com sucesso!", "success")
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "warning")
        except Exception as exc:
            conn.rollback()
            flash(f"Erro ao inativar detector de gás: {exc}", "danger")
        finally:
            cursor.close()
            conn.close()

        return redirecionar_lista()

    @blueprint.route(
        "/detectores_gas/<int:detector_id>/reativar",
        methods=["POST"]
    )
    @login_required
    @admin_required
    def reativar_detector_gas(detector_id):
        status_operacional = (
            request.form.get("status_operacional")
            or ""
        ).strip()

        if status_operacional not in STATUS_OPERACIONAIS:
            flash(
                "Selecione o status operacional para reativar o detector.",
                "warning"
            )
            return redirecionar_lista()

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                UPDATE detectores_gas
                SET ativo = 1,
                    status_operacional = %s,
                    atualizado_por = %s
                WHERE id = %s
            """, (
                status_operacional,
                session.get("usuario_id"),
                detector_id,
            ))

            if cursor.rowcount != 1:
                raise ValueError("Detector de gás não encontrado.")

            conn.commit()
            flash("Detector de gás reativado com sucesso!", "success")
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "warning")
        except Exception as exc:
            conn.rollback()
            flash(f"Erro ao reativar detector de gás: {exc}", "danger")
        finally:
            cursor.close()
            conn.close()

        return redirecionar_lista()
