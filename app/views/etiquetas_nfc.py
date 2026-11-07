"""Cadastro administrativo das etiquetas NFC usadas pelos checklists."""

import math
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
        erro_formulario = False
        try:
            if request.method == "POST":
                etiqueta_id = request.form.get("id", type=int)
                try:
                    numero, descricao, abrangencia, centro_ids = _validar_etiqueta(cursor, etiqueta_id)
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
                    erro_formulario = True
                    flash(str(exc), "danger")
                except Exception:
                    conn.rollback()
                    erro_formulario = True
                    flash("Não foi possível salvar a etiqueta NFC.", "danger")

            busca = (request.args.get("busca") or "").strip()
            abrangencia_filtro = request.args.get("abrangencia") or ""
            status_filtro = request.args.get("status") or ""
            centro_filtro = request.args.get("centro_custos_id", type=int)
            pagina = max(request.args.get("page", 1, type=int), 1)
            por_pagina = request.args.get("per_page", 20, type=int)
            if por_pagina not in {20, 50, 100}:
                por_pagina = 20
            ordenar = request.args.get("sort") or "numero"
            direcao = "desc" if request.args.get("order") == "desc" else "asc"
            colunas_ordenacao = {
                "numero": "e.numero", "descricao": "e.descricao",
                "abrangencia": "e.abrangencia", "status": "e.ativo",
            }
            ordenar = ordenar if ordenar in colunas_ordenacao else "numero"

            condicoes = []
            parametros = []
            if busca:
                condicoes.append("(e.numero LIKE %s OR e.descricao LIKE %s)")
                termo = f"%{busca}%"
                parametros.extend([termo, termo])
            if abrangencia_filtro in {"global", "centros"}:
                condicoes.append("e.abrangencia = %s")
                parametros.append(abrangencia_filtro)
            if status_filtro in {"1", "0"}:
                condicoes.append("e.ativo = %s")
                parametros.append(int(status_filtro))
            if centro_filtro:
                condicoes.append("""(
                    e.abrangencia = 'global' OR EXISTS (
                        SELECT 1 FROM nfc_etiquetas_centros ef
                         WHERE ef.etiqueta_id = e.id AND ef.centro_custos_id = %s
                    )
                )""")
                parametros.append(centro_filtro)
            where_sql = " WHERE " + " AND ".join(condicoes) if condicoes else ""

            cursor.execute(f"SELECT COUNT(*) AS total FROM nfc_etiquetas e{where_sql}", parametros)
            total_filtrado = cursor.fetchone()["total"]
            total_paginas = max(math.ceil(total_filtrado / por_pagina), 1)
            pagina = min(pagina, total_paginas)
            offset = (pagina - 1) * por_pagina
            cursor.execute(f"""
                SELECT e.id, e.numero, e.descricao, e.abrangencia, e.ativo,
                       (SELECT GROUP_CONCAT(CONCAT(cc.codigo, ' - ', cc.descricao)
                                            ORDER BY cc.codigo SEPARATOR ', ')
                          FROM nfc_etiquetas_centros ec
                          JOIN centros_custos cc ON cc.id = ec.centro_custos_id
                         WHERE ec.etiqueta_id = e.id) AS centros
                  FROM nfc_etiquetas e
                  {where_sql}
              ORDER BY {colunas_ordenacao[ordenar]} {direcao.upper()}, e.id
                 LIMIT %s OFFSET %s
            """, parametros + [por_pagina, offset])
            etiquetas = cursor.fetchall()

            cursor.execute("""
                SELECT COUNT(*) AS total,
                       COALESCE(SUM(ativo = 1), 0) AS ativas,
                       COALESCE(SUM(ativo = 0), 0) AS inativas,
                       COALESCE(SUM(abrangencia = 'global'), 0) AS globais
                  FROM nfc_etiquetas
            """)
            indicadores = cursor.fetchone()

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
                    centros_selecionados = [str(item["centro_custos_id"]) for item in cursor.fetchall()]
            elif erro_formulario:
                centros_selecionados = request.form.getlist("centro_custos_ids")

            cursor.execute("""
                SELECT id, codigo, descricao FROM centros_custos
                 WHERE ativo = 1 ORDER BY codigo
            """)
            centros_custos = cursor.fetchall()
            filtros = {
                "busca": busca, "abrangencia": abrangencia_filtro,
                "status": status_filtro,
                "centro_custos_id": str(centro_filtro or ""),
                "sort": ordenar, "order": direcao, "per_page": por_pagina,
            }
            return render_template(
                "etiquetas_nfc.html", etiquetas=etiquetas,
                etiqueta_edicao=etiqueta_edicao,
                centros_custos=centros_custos,
                centros_selecionados=centros_selecionados,
                indicadores=indicadores, filtros=filtros,
                pagina=pagina, total_paginas=total_paginas,
                total_filtrado=total_filtrado, erro_formulario=erro_formulario,
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
            flash(f"Etiqueta NFC {'reativada' if ativo else 'inativada'} com sucesso.", "success")
        except Exception:
            conn.rollback()
            flash("Não foi possível alterar o status da etiqueta NFC.", "danger")
        finally:
            cursor.close()
            conn.close()
        return redirect(request.referrer or url_for("main.etiquetas_nfc"))
