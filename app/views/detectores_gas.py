import re
from datetime import date

from flask import flash, redirect, render_template, request, session, url_for

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


def normalizar_patrimonio(valor):
    return (valor or "").strip().upper()


def patrimonio_valido(valor):
    return bool(PADRAO_PATRIMONIO.fullmatch(normalizar_patrimonio(valor)))


def converter_data_opcional(valor):
    valor = (valor or "").strip()
    if not valor:
        return None
    return date.fromisoformat(valor)


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
                    cc.descricao AS centro_custos_descricao
                FROM detectores_gas d
                JOIN centros_custos cc
                    ON cc.id = d.centro_custos_id
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
