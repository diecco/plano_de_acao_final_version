from datetime import date

from flask import flash, redirect, render_template, request, session, url_for

from app.decorators import admin_required, login_required
from app.upload_security import UploadService, UploadValidationError
from app.utils.db import get_db_connection


EXTENSOES_COMUNICADOS = {"png", "jpg", "jpeg"}
DIRETORIO_COMUNICADOS = "static/comunicados"


def register_inicio_routes(blueprint):
    @blueprint.route("/inicio")
    @login_required
    def inicio():
        centro_custos_id = session.get("centro_custos_id")
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            parametros = []
            escopo = "cv.corporativo = 1"
            if centro_custos_id:
                escopo += " OR EXISTS (" \
                    "SELECT 1 FROM comunicados_visuais_centros cvc " \
                    "WHERE cvc.comunicado_id = cv.id " \
                    "AND cvc.centro_custos_id = %s)"
                parametros.append(centro_custos_id)

            cursor.execute(f"""
                SELECT cv.id, cv.imagem
                FROM comunicados_visuais cv
                WHERE cv.ativo = 1
                  AND (cv.data_inicio IS NULL OR cv.data_inicio <= %s)
                  AND (cv.data_fim IS NULL OR cv.data_fim >= %s)
                  AND ({escopo})
                ORDER BY cv.ordem ASC, cv.criado_em DESC, cv.id DESC
            """, [date.today(), date.today()] + parametros)
            comunicados = [
                comunicado
                for comunicado in cursor.fetchall()
                if UploadService.existe(
                    comunicado.get("imagem"),
                    DIRETORIO_COMUNICADOS,
                )
            ]
        finally:
            cursor.close()
            conn.close()

        return render_template("inicio.html", comunicados=comunicados)

    @blueprint.route("/admin/comunicados", methods=["GET", "POST"])
    @login_required
    @admin_required
    def comunicados_visuais():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            if request.method == "POST":
                nome_interno = (request.form.get("nome_interno") or "").strip()
                data_inicio = request.form.get("data_inicio") or None
                data_fim = request.form.get("data_fim") or None
                corporativo = 1 if request.form.get("corporativo") == "1" else 0
                centro_ids = request.form.getlist("centro_custos_ids")

                try:
                    ordem = max(int(request.form.get("ordem") or 0), 0)
                except ValueError:
                    ordem = 0

                if not nome_interno:
                    flash("Informe um nome interno para o comunicado.", "danger")
                    return redirect(url_for("main.comunicados_visuais"))
                if data_inicio and data_fim and data_fim < data_inicio:
                    flash("A data final não pode ser anterior à data inicial.", "danger")
                    return redirect(url_for("main.comunicados_visuais"))
                if not corporativo and not centro_ids:
                    flash(
                        "Selecione ao menos um centro de custos ou marque como corporativo.",
                        "danger",
                    )
                    return redirect(url_for("main.comunicados_visuais"))

                try:
                    imagem = UploadService.salvar(
                        request.files.get("imagem"),
                        EXTENSOES_COMUNICADOS,
                        "comunicado",
                        DIRETORIO_COMUNICADOS,
                    )
                except UploadValidationError as erro:
                    flash(str(erro), "danger")
                    return redirect(url_for("main.comunicados_visuais"))

                if not imagem:
                    flash("Selecione a imagem do comunicado.", "danger")
                    return redirect(url_for("main.comunicados_visuais"))

                try:
                    cursor.execute("""
                        INSERT INTO comunicados_visuais (
                            nome_interno, imagem, corporativo, data_inicio,
                            data_fim, ordem, ativo, criado_por
                        ) VALUES (%s, %s, %s, %s, %s, %s, 1, %s)
                    """, (
                        nome_interno,
                        imagem,
                        corporativo,
                        data_inicio,
                        data_fim,
                        ordem,
                        session["usuario_id"],
                    ))
                    comunicado_id = cursor.lastrowid
                    if not corporativo:
                        cursor.executemany("""
                            INSERT INTO comunicados_visuais_centros (
                                comunicado_id, centro_custos_id
                            ) VALUES (%s, %s)
                        """, [
                            (comunicado_id, centro_id)
                            for centro_id in dict.fromkeys(centro_ids)
                        ])
                    conn.commit()
                except Exception:
                    conn.rollback()
                    UploadService.excluir(imagem, DIRETORIO_COMUNICADOS)
                    raise

                flash("Comunicado visual cadastrado com sucesso.", "success")
                return redirect(url_for("main.comunicados_visuais"))

            cursor.execute("""
                SELECT id, codigo, descricao
                FROM centros_custos
                WHERE ativo = 1
                ORDER BY codigo, descricao
            """)
            centros_custos = cursor.fetchall()

            cursor.execute("""
                SELECT
                    cv.id,
                    cv.nome_interno,
                    cv.imagem,
                    cv.corporativo,
                    cv.data_inicio,
                    cv.data_fim,
                    cv.ordem,
                    cv.ativo,
                    GROUP_CONCAT(
                        DISTINCT CONCAT(cc.codigo, ' - ', cc.descricao)
                        ORDER BY cc.codigo SEPARATOR ', '
                    ) AS centros_custos
                FROM comunicados_visuais cv
                LEFT JOIN comunicados_visuais_centros cvc
                    ON cvc.comunicado_id = cv.id
                LEFT JOIN centros_custos cc
                    ON cc.id = cvc.centro_custos_id
                GROUP BY
                    cv.id, cv.nome_interno, cv.imagem, cv.corporativo,
                    cv.data_inicio, cv.data_fim, cv.ordem, cv.ativo
                ORDER BY cv.ativo DESC, cv.ordem ASC, cv.criado_em DESC
            """)
            comunicados = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

        return render_template(
            "comunicados_visuais.html",
            centros_custos=centros_custos,
            comunicados=comunicados,
        )

    @blueprint.route(
        "/admin/comunicados/<int:comunicado_id>/imagem",
        methods=["POST"],
    )
    @login_required
    @admin_required
    def substituir_imagem_comunicado_visual(comunicado_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        nova_imagem = None
        try:
            cursor.execute(
                "SELECT imagem FROM comunicados_visuais WHERE id = %s",
                (comunicado_id,),
            )
            comunicado = cursor.fetchone()
            if not comunicado:
                flash("Comunicado não encontrado.", "danger")
                return redirect(url_for("main.comunicados_visuais"))

            try:
                nova_imagem = UploadService.salvar(
                    request.files.get("imagem"),
                    EXTENSOES_COMUNICADOS,
                    "comunicado",
                    DIRETORIO_COMUNICADOS,
                )
            except UploadValidationError as erro:
                flash(str(erro), "danger")
                return redirect(url_for("main.comunicados_visuais"))

            if not nova_imagem:
                flash("Selecione a nova imagem do comunicado.", "danger")
                return redirect(url_for("main.comunicados_visuais"))

            try:
                cursor.execute(
                    "UPDATE comunicados_visuais SET imagem = %s WHERE id = %s",
                    (nova_imagem, comunicado_id),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                UploadService.excluir(nova_imagem, DIRETORIO_COMUNICADOS)
                raise

            UploadService.excluir(
                comunicado.get("imagem"),
                DIRETORIO_COMUNICADOS,
            )
            flash("Imagem do comunicado atualizada com sucesso.", "success")
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for("main.comunicados_visuais"))

    @blueprint.route(
        "/admin/comunicados/<int:comunicado_id>/alternar",
        methods=["POST"],
    )
    @login_required
    @admin_required
    def alternar_comunicado_visual(comunicado_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE comunicados_visuais
                SET ativo = CASE WHEN ativo = 1 THEN 0 ELSE 1 END
                WHERE id = %s
            """, (comunicado_id,))
            conn.commit()
        finally:
            cursor.close()
            conn.close()
        flash("Situação do comunicado atualizada.", "success")
        return redirect(url_for("main.comunicados_visuais"))
