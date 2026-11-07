"""Cadastro administrativo das etiquetas NFC usadas pelos checklists."""

import secrets

from flask import flash, redirect, render_template, request, session, url_for

from app.decorators import admin_required, login_required
from app.utils.db import get_db_connection


def _validar_etiqueta(cursor, etiqueta_id=None):
    numero = (request.form.get("numero") or "").strip()
    descricao = (request.form.get("descricao") or "").strip()
    abrangencia = request.form.get("abrangencia") or "global"
    centro_ids = list(dict.fromkeys(request.form.getlist("centro_custos_ids")))
    if not 1 <= len(numero) <= 80:
        raise ValueError("Informe o número da etiqueta, com até 80 caracteres.")
    if not 1 <= len(descricao) <= 255:
        raise ValueError("Informe a descrição da etiqueta, com até 255 caracteres.")
    if abrangencia not in {"global", "centros"}:
        raise ValueError("Confira a abrangência da etiqueta.")
    cursor.execute(
        "SELECT id FROM nfc_etiquetas WHERE numero = %s AND id <> %s LIMIT 1",
        (numero, etiqueta_id or 0),
    )
    if cursor.fetchone():
        raise ValueError("Já existe uma etiqueta com esse número.")
    if abrangencia == "centros":
        if not centro_ids:
            raise ValueError("Selecione ao menos um centro de custos.")
        placeholders = ",".join(["%s"] * len(centro_ids))
        cursor.execute(
            f"SELECT id FROM centros_custos WHERE ativo = 1 AND id IN ({placeholders})",
            centro_ids,
        )
        encontrados = {str(item["id"]) for item in cursor.fetchall()}
        if encontrados != set(centro_ids):
            raise ValueError("Um dos centros de custos selecionados é inválido.")
    else:
        centro_ids = []
    return numero, descricao, abrangencia, centro_ids


def register_etiquetas_nfc_routes(blueprint):
    @blueprint.route("/administracao/etiquetas-nfc", methods=["GET", "POST"])
    @login_required
    @admin_required
    def etiquetas_nfc():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            if request.method == "POST":
                etiqueta_id = request.form.get("id", type=int)
                try:
                    numero, descricao, abrangencia, centro_ids = _validar_etiqueta(
                        cursor, etiqueta_id
                    )
                    if etiqueta_id:
                        cursor.execute("""
                            UPDATE nfc_etiquetas
                               SET numero = %s, descricao = %s, abrangencia = %s,
                                   atualizado_em = CURRENT_TIMESTAMP
                             WHERE id = %s
                        """, (numero, descricao, abrangencia, etiqueta_id))
                        if cursor.rowcount != 1:
                            raise ValueError("Etiqueta NFC não encontrada.")
                        cursor.execute(
                            "DELETE FROM nfc_etiquetas_centros WHERE etiqueta_id = %s",
                            (etiqueta_id,),
                        )
                        mensagem = "Etiqueta NFC atualizada com sucesso."
                    else:
                        cursor.execute("""
                            INSERT INTO nfc_etiquetas (
                                numero, descricao, token, abrangencia, ativo, criado_por
                            ) VALUES (%s, %s, %s, %s, 1, %s)
                        """, (
                            numero, descricao, secrets.token_urlsafe(32), abrangencia,
                            session.get("usuario_id"),
                        ))
                        etiqueta_id = cursor.lastrowid
                        mensagem = "Etiqueta NFC cadastrada com sucesso."
                    for centro_id in centro_ids:
                        cursor.execute("""
                            INSERT INTO nfc_etiquetas_centros (etiqueta_id, centro_custos_id)
                            VALUES (%s, %s)
                        """, (etiqueta_id, centro_id))
                    conn.commit()
                    flash(mensagem, "success")
                    return redirect(url_for("main.etiquetas_nfc"))
                except ValueError as exc:
                    conn.rollback()
                    flash(str(exc), "danger")
                except Exception:
                    conn.rollback()
                    flash("Não foi possível salvar a etiqueta NFC.", "danger")

            editar_id = request.args.get("editar_id", type=int)
            etiqueta_edicao = None
            centros_selecionados = []
            if editar_id:
                cursor.execute("SELECT * FROM nfc_etiquetas WHERE id = %s", (editar_id,))
                etiqueta_edicao = cursor.fetchone()
                if etiqueta_edicao:
                    cursor.execute(
                        "SELECT centro_custos_id FROM nfc_etiquetas_centros WHERE etiqueta_id = %s",
                        (editar_id,),
                    )
                    centros_selecionados = [
                        str(item["centro_custos_id"]) for item in cursor.fetchall()
                    ]
            cursor.execute("""
                SELECT e.id, e.numero, e.descricao, e.abrangencia, e.ativo,
                       GROUP_CONCAT(CONCAT(cc.codigo, ' - ', cc.descricao)
                                    ORDER BY cc.codigo SEPARATOR ', ') AS centros
                  FROM nfc_etiquetas e
             LEFT JOIN nfc_etiquetas_centros ec ON ec.etiqueta_id = e.id
             LEFT JOIN centros_custos cc ON cc.id = ec.centro_custos_id
              GROUP BY e.id, e.numero, e.descricao, e.abrangencia, e.ativo
              ORDER BY e.ativo DESC, e.numero
            """)
            etiquetas = cursor.fetchall()
            cursor.execute("""
                SELECT id, codigo, descricao FROM centros_custos
                 WHERE ativo = 1 ORDER BY codigo
            """)
            centros_custos = cursor.fetchall()
            return render_template(
                "etiquetas_nfc.html", etiquetas=etiquetas,
                etiqueta_edicao=etiqueta_edicao,
                centros_custos=centros_custos,
                centros_selecionados=centros_selecionados,
            )
        finally:
            cursor.close()
            conn.close()

    @blueprint.post("/administracao/etiquetas-nfc/<int:etiqueta_id>/status")
    @login_required
    @admin_required
    def alterar_status_etiqueta_nfc(etiqueta_id):
        ativo = 1 if request.form.get("ativo") == "1" else 0
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE nfc_etiquetas SET ativo = %s, atualizado_em = CURRENT_TIMESTAMP WHERE id = %s",
                (ativo, etiqueta_id),
            )
            conn.commit()
            flash(
                f"Etiqueta NFC {'reativada' if ativo else 'inativada'} com sucesso.",
                "success",
            )
        except Exception:
            conn.rollback()
            flash("Não foi possível alterar o status da etiqueta NFC.", "danger")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for("main.etiquetas_nfc"))
