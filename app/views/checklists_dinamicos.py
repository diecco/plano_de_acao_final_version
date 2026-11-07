"""Primeiro núcleo dos checklists configuráveis do TrackPlan.

Esta etapa cuida do catálogo, abrangência por centro de custos e publicação na
sidebar. A definição das perguntas será adicionada sobre este mesmo catálogo.
"""

from flask import abort, flash, redirect, render_template, request, session, url_for

from app.decorators import admin_required, login_required
from app.utils.db import get_db_connection


MODULOS_MENU = {
    "ssma": "SSMA",
    "gestao_ssma": "Gestão SSMA",
}


def carregar_checklists_sidebar():
    """Retorna somente os checklists publicados visíveis no escopo atual.

    Durante a implantação a migração pode ainda não ter sido executada. Nesse
    intervalo a navegação antiga continua funcionando normalmente.
    """
    if not session.get("usuario_id"):
        return {"checklists_sidebar_ssma": [], "checklists_sidebar_gestao": []}

    conn = None
    cursor = None
    try:
        centro_id = session.get("centro_custos_id")
        perfil = (session.get("perfil") or "").lower()
        parametros = []
        escopo = "cm.abrangencia = 'global'"
        if perfil == "administrador":
            escopo = "1 = 1"
        elif centro_id:
            escopo += " OR EXISTS (SELECT 1 FROM checklist_modelos_centros cmc " \
                "WHERE cmc.checklist_id = cm.id AND cmc.centro_custos_id = %s)"
            parametros.append(centro_id)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute(f"""
            SELECT cm.id, cm.nome, cm.modulo_menu
              FROM checklist_modelos cm
             WHERE cm.ativo = 1
               AND cm.status = 'publicado'
               AND cm.exibir_menu = 1
               AND ({escopo})
             ORDER BY cm.modulo_menu, cm.ordem_menu, cm.nome, cm.id
        """, parametros)
        registros = cursor.fetchall()
    except Exception:
        registros = []
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

    return {
        "checklists_sidebar_ssma": [
            item for item in registros if item["modulo_menu"] == "ssma"
        ],
        "checklists_sidebar_gestao": [
            item for item in registros if item["modulo_menu"] == "gestao_ssma"
        ],
    }


def _inteiro_nao_negativo(valor, padrao=0):
    try:
        return max(int(valor), 0)
    except (TypeError, ValueError):
        return padrao


def _pode_acessar_modulo(modulo_menu):
    if (session.get("perfil") or "").lower() == "administrador":
        return True
    if modulo_menu == "ssma":
        return bool(session.get("acesso_ssma") or session.get("pode_ser_lider_ssma"))
    if modulo_menu == "gestao_ssma":
        return bool(
            session.get("gestor_ssma")
            or session.get("pode_criar_agendamento_ssma")
            or session.get("pode_direcionar_desvios")
        )
    return False


def _buscar_modelo_visivel(cursor, checklist_id):
    centro_id = session.get("centro_custos_id")
    perfil = (session.get("perfil") or "").lower()
    parametros = [checklist_id]
    escopo = "cm.abrangencia = 'global'"
    if perfil == "administrador":
        escopo = "1 = 1"
    elif centro_id:
        escopo += " OR EXISTS (SELECT 1 FROM checklist_modelos_centros cmc " \
            "WHERE cmc.checklist_id = cm.id AND cmc.centro_custos_id = %s)"
        parametros.append(centro_id)

    cursor.execute(f"""
        SELECT cm.*
          FROM checklist_modelos cm
         WHERE cm.id = %s
           AND cm.ativo = 1
           AND cm.status = 'publicado'
           AND ({escopo})
         LIMIT 1
    """, parametros)
    return cursor.fetchone()


def register_checklists_dinamicos_routes(blueprint):
    @blueprint.route("/admin/checklists", methods=["GET", "POST"])
    @login_required
    @admin_required
    def checklists_dinamicos():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            if request.method == "POST":
                nome = (request.form.get("nome") or "").strip()
                descricao = (request.form.get("descricao") or "").strip()
                abrangencia = request.form.get("abrangencia") or "global"
                centro_ids = list(dict.fromkeys(request.form.getlist("centro_custos_ids")))
                modulo_menu = request.form.get("modulo_menu") or "ssma"
                exibir_menu = 1 if request.form.get("exibir_menu") == "1" else 0
                ordem_menu = _inteiro_nao_negativo(request.form.get("ordem_menu"))

                if not nome:
                    flash("Informe o nome do checklist.", "danger")
                    return redirect(url_for("main.checklists_dinamicos"))
                if abrangencia not in {"global", "centros"}:
                    flash("Selecione uma abrangência válida.", "danger")
                    return redirect(url_for("main.checklists_dinamicos"))
                if abrangencia == "centros" and not centro_ids:
                    flash("Selecione ao menos um centro de custos.", "danger")
                    return redirect(url_for("main.checklists_dinamicos"))
                if modulo_menu not in MODULOS_MENU:
                    flash("Selecione um módulo válido para a sidebar.", "danger")
                    return redirect(url_for("main.checklists_dinamicos"))

                cursor.execute(
                    "SELECT id FROM checklist_modelos WHERE LOWER(TRIM(nome)) = LOWER(TRIM(%s)) LIMIT 1",
                    (nome,),
                )
                if cursor.fetchone():
                    flash("Já existe um checklist com esse nome.", "danger")
                    return redirect(url_for("main.checklists_dinamicos"))

                if abrangencia == "centros":
                    cursor.execute(
                        "SELECT id FROM centros_custos WHERE ativo = 1 AND id IN ({})".format(
                            ",".join(["%s"] * len(centro_ids))
                        ),
                        centro_ids,
                    )
                    centros_validos = {str(item["id"]) for item in cursor.fetchall()}
                    if centros_validos != set(centro_ids):
                        flash("Um dos centros de custos selecionados é inválido.", "danger")
                        return redirect(url_for("main.checklists_dinamicos"))

                cursor.execute("""
                    INSERT INTO checklist_modelos (
                        nome, descricao, abrangencia, status, ativo,
                        exibir_menu, modulo_menu, ordem_menu, criado_por
                    ) VALUES (%s, %s, %s, 'rascunho', 1, %s, %s, %s, %s)
                """, (
                    nome, descricao or None, abrangencia, exibir_menu,
                    modulo_menu, ordem_menu, session.get("usuario_id"),
                ))
                checklist_id = cursor.lastrowid
                if abrangencia == "centros":
                    cursor.executemany("""
                        INSERT INTO checklist_modelos_centros (
                            checklist_id, centro_custos_id
                        ) VALUES (%s, %s)
                    """, [(checklist_id, centro_id) for centro_id in centro_ids])
                conn.commit()
                flash(
                    "Esboço do checklist criado como rascunho. "
                    "Publique quando estiver pronto para disponibilizá-lo.",
                    "success",
                )
                return redirect(url_for("main.checklists_dinamicos"))

            cursor.execute("""
                SELECT id, codigo, descricao
                  FROM centros_custos
                 WHERE ativo = 1
                 ORDER BY codigo, descricao
            """)
            centros_custos = cursor.fetchall()
            cursor.execute("""
                SELECT cm.*,
                       GROUP_CONCAT(
                           DISTINCT CONCAT(cc.codigo, ' - ', cc.descricao)
                           ORDER BY cc.codigo SEPARATOR ', '
                       ) AS centros_custos
                  FROM checklist_modelos cm
             LEFT JOIN checklist_modelos_centros cmc
                    ON cmc.checklist_id = cm.id
             LEFT JOIN centros_custos cc
                    ON cc.id = cmc.centro_custos_id
              GROUP BY cm.id
              ORDER BY cm.ativo DESC, cm.ordem_menu, cm.nome
            """)
            checklists = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

        return render_template(
            "checklists_dinamicos.html",
            checklists=checklists,
            centros_custos=centros_custos,
            modulos_menu=MODULOS_MENU,
        )

    @blueprint.post("/admin/checklists/<int:checklist_id>/publicar")
    @login_required
    @admin_required
    def publicar_checklist_dinamico(checklist_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE checklist_modelos
                   SET publicado_em = CASE
                       WHEN status = 'publicado' THEN NULL
                       ELSE CURRENT_TIMESTAMP
                   END,
                       status = CASE
                       WHEN status = 'publicado' THEN 'rascunho'
                       ELSE 'publicado'
                   END
                 WHERE id = %s AND ativo = 1
            """, (checklist_id,))
            conn.commit()
        finally:
            cursor.close()
            conn.close()
        flash("Publicação do checklist atualizada.", "success")
        return redirect(url_for("main.checklists_dinamicos"))

    @blueprint.post("/admin/checklists/<int:checklist_id>/situacao")
    @login_required
    @admin_required
    def alternar_checklist_dinamico(checklist_id):
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE checklist_modelos
                   SET ativo = CASE WHEN ativo = 1 THEN 0 ELSE 1 END
                 WHERE id = %s
            """, (checklist_id,))
            conn.commit()
        finally:
            cursor.close()
            conn.close()
        flash("Situação do checklist atualizada.", "success")
        return redirect(url_for("main.checklists_dinamicos"))

    @blueprint.get("/checklists/<int:checklist_id>")
    @login_required
    def abrir_checklist_dinamico(checklist_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            checklist = _buscar_modelo_visivel(cursor, checklist_id)
            if not checklist:
                abort(404)
            if not _pode_acessar_modulo(checklist["modulo_menu"]):
                abort(403)
        finally:
            cursor.close()
            conn.close()
        return render_template("checklist_dinamico_esboco.html", checklist=checklist)
