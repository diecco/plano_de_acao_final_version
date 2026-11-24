import hashlib
import json
from math import ceil

from flask import abort, flash, redirect, render_template, request, session, url_for

from app.decorators import login_required, module_required
from app.services.fluig_relato_ocorrencia_import import (
    RelatoOcorrenciaImportError,
    parse_fluig_relatos_ocorrencias,
)
from app.utils.db import get_db_connection


POR_PAGINA = 30
LIMITE_ARQUIVO = 20 * 1024 * 1024
VALORES_MATRIZ = {"baixa": 1, "media": 2, "alta": 3}


def _calculate_probability(exposure, controls, occurrence):
    values = (exposure, controls, occurrence)
    if any(value not in VALORES_MATRIZ for value in values):
        raise ValueError("Preencha os três critérios de probabilidade.")
    average = sum(VALORES_MATRIZ[value] for value in values) / 3
    if average <= 1.5:
        return "baixa"
    if average <= 2.3:
        return "media"
    return "alta"


def _calculate_risk(severity, probability):
    matrix = {
        "A": {"baixa": "medio", "media": "alto", "alta": "alto"},
        "B": {"baixa": "baixo", "media": "medio", "alta": "alto"},
        "C": {"baixa": "baixo", "media": "medio", "alta": "medio"},
    }
    try:
        return matrix[severity][probability]
    except KeyError as exc:
        raise ValueError("Classificação de risco inválida.") from exc


def _can_classify():
    return session.get("perfil") == "administrador" or bool(session.get("gestor_ssma"))


def _safe_next(value):
    value = (value or "").strip()
    if value.startswith("/") and not value.startswith("//"):
        return value
    return url_for("main.relatos_ocorrencias")


def _scope_filter(alias="r"):
    if session.get("perfil") in {"administrador", "avancado"}:
        return "1 = 1", []
    center_id = session.get("centro_custos_id")
    if not center_id:
        return "1 = 0", []
    return f"{alias}.centro_custos_id = %s", [center_id]


def _save_import(cursor, records, errors, filename, file_hash):
    cursor.execute("""
        INSERT INTO relatos_ocorrencias_importacoes
            (nome_arquivo, arquivo_hash, usuario_id, total_linhas, erros)
        VALUES (%s, %s, %s, %s, %s)
    """, (
        filename[:255], file_hash, session["usuario_id"],
        len(records) + len(errors), len(errors),
    ))
    import_id = cursor.lastrowid

    if errors:
        cursor.executemany("""
            INSERT INTO relatos_ocorrencias_importacao_erros
                (importacao_id, linha, solicitacao, motivo)
            VALUES (%s, %s, %s, %s)
        """, [
            (import_id, item["linha"], item.get("solicitacao") or None, item["erro"][:1000])
            for item in errors
        ])

    request_numbers = [item["solicitacao"] for item in records]
    existing = {}
    for start in range(0, len(request_numbers), 500):
        batch = request_numbers[start:start + 500]
        placeholders = ", ".join(["%s"] * len(batch))
        cursor.execute(f"""
            SELECT id, solicitacao, conteudo_hash
            FROM relatos_ocorrencias
            WHERE solicitacao IN ({placeholders})
        """, tuple(batch))
        existing.update({row["solicitacao"]: row for row in cursor.fetchall()})

    cursor.execute("SELECT id, codigo FROM centros_custos WHERE ativo = 1")
    center_ids = {
        (row.get("codigo") or "").strip(): row["id"]
        for row in cursor.fetchall()
        if (row.get("codigo") or "").strip()
    }

    changed = []
    inserted = updated = unchanged = 0
    for record in records:
        prior = existing.get(record["solicitacao"])
        if prior and prior["conteudo_hash"] == record["conteudo_hash"]:
            unchanged += 1
            continue
        record["centro_custos_id"] = center_ids.get(record["centro_custos_codigo"])
        changed.append(record)
        if prior:
            updated += 1
        else:
            inserted += 1

    if changed:
        values = [(
            item["solicitacao"], item["situacao_fluig"],
            item["requisitante_identificador"], item["requisitante_nome"],
            item["localizacao_fluxo"], item["responsavel_fluxo"],
            item["inicio_em"], item["fim_em"], item["acao_tomada"],
            item["area_ocorrencia"], item["centro_custos_id"],
            item["centro_custos_codigo"], item["centro_custos_original"],
            item["classificacao_ocorrencia"], item["data_ocorrencia"],
            item["hora_ocorrencia"], item["descricao_ocorrencia"],
            item["local_ocorrencia"], item["responsavel_registro"],
            item["tipo_relato"], item["tipo_origem"], item["turno"],
            item["responsavel_turno"], item["membros_atingidos"],
            json.dumps(item["dados_origem"], ensure_ascii=False),
            item["conteudo_hash"], import_id,
        ) for item in changed]
        cursor.executemany("""
            INSERT INTO relatos_ocorrencias (
                solicitacao, situacao_fluig, requisitante_identificador,
                requisitante_nome, localizacao_fluxo, responsavel_fluxo,
                inicio_em, fim_em, acao_tomada, area_ocorrencia,
                centro_custos_id, centro_custos_codigo, centro_custos_original,
                classificacao_ocorrencia, data_ocorrencia, hora_ocorrencia,
                descricao_ocorrencia, local_ocorrencia, responsavel_registro,
                tipo_relato, tipo_origem, turno, responsavel_turno,
                membros_atingidos, dados_origem, conteudo_hash, importacao_id
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON DUPLICATE KEY UPDATE
                situacao_fluig=VALUES(situacao_fluig),
                requisitante_identificador=VALUES(requisitante_identificador),
                requisitante_nome=VALUES(requisitante_nome),
                localizacao_fluxo=VALUES(localizacao_fluxo),
                responsavel_fluxo=VALUES(responsavel_fluxo),
                inicio_em=VALUES(inicio_em), fim_em=VALUES(fim_em),
                acao_tomada=VALUES(acao_tomada), area_ocorrencia=VALUES(area_ocorrencia),
                centro_custos_id=VALUES(centro_custos_id),
                centro_custos_codigo=VALUES(centro_custos_codigo),
                centro_custos_original=VALUES(centro_custos_original),
                classificacao_ocorrencia=VALUES(classificacao_ocorrencia),
                data_ocorrencia=VALUES(data_ocorrencia),
                hora_ocorrencia=VALUES(hora_ocorrencia),
                descricao_ocorrencia=VALUES(descricao_ocorrencia),
                local_ocorrencia=VALUES(local_ocorrencia),
                responsavel_registro=VALUES(responsavel_registro),
                tipo_relato=VALUES(tipo_relato), tipo_origem=VALUES(tipo_origem),
                turno=VALUES(turno), responsavel_turno=VALUES(responsavel_turno),
                membros_atingidos=VALUES(membros_atingidos),
                dados_origem=VALUES(dados_origem), conteudo_hash=VALUES(conteudo_hash),
                importacao_id=VALUES(importacao_id)
        """, values)

        changed_numbers = [item["solicitacao"] for item in changed]
        ids = {}
        for start in range(0, len(changed_numbers), 500):
            batch = changed_numbers[start:start + 500]
            placeholders = ", ".join(["%s"] * len(batch))
            cursor.execute(f"""
                SELECT id, solicitacao FROM relatos_ocorrencias
                WHERE solicitacao IN ({placeholders})
            """, tuple(batch))
            ids.update({row["solicitacao"]: row["id"] for row in cursor.fetchall()})

        changed_ids = list(ids.values())
        for start in range(0, len(changed_ids), 500):
            batch = changed_ids[start:start + 500]
            placeholders = ", ".join(["%s"] * len(batch))
            cursor.execute(
                f"DELETE FROM relatos_ocorrencias_envolvidos "
                f"WHERE relato_id IN ({placeholders})",
                tuple(batch),
            )
        involved_values = [
            (
                ids[item["solicitacao"]], order, involved.get("nome"),
                involved.get("matricula"), involved.get("email"),
                involved.get("centro_custos"), involved.get("descricao"),
            )
            for item in changed
            for order, involved in enumerate(item["envolvidos"], start=1)
        ]
        if involved_values:
            cursor.executemany("""
                INSERT INTO relatos_ocorrencias_envolvidos
                    (relato_id, ordem, nome, matricula, email, centro_custos, descricao)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, involved_values)

    cursor.execute("""
        UPDATE relatos_ocorrencias_importacoes
        SET inseridos=%s, atualizados=%s, inalterados=%s
        WHERE id=%s
    """, (inserted, updated, unchanged, import_id))
    return inserted, updated, unchanged


def register_relatos_ocorrencias_routes(blueprint):
    @blueprint.route("/relatos_ocorrencias")
    @login_required
    @module_required("acesso_ssma")
    def relatos_ocorrencias():
        filters = {
            "busca": (request.args.get("busca") or "").strip(),
            "tipo": (request.args.get("tipo") or "").strip(),
            "data_inicio": (request.args.get("data_inicio") or "").strip(),
            "data_fim": (request.args.get("data_fim") or "").strip(),
            "sort": (request.args.get("sort") or "data").strip(),
            "order": (request.args.get("order") or "desc").strip(),
        }
        page = max(request.args.get("page", 1, type=int), 1)
        sort_columns = {
            "solicitacao": "r.solicitacao",
            "data": "r.data_ocorrencia",
            "tipo": "r.tipo_relato",
            "status": "r.situacao_fluig",
        }
        if filters["sort"] not in sort_columns:
            filters["sort"] = "data"
        if filters["order"] not in {"asc", "desc"}:
            filters["order"] = "desc"

        conditions = []
        parameters = []
        scope, scope_parameters = _scope_filter()
        conditions.append(scope)
        parameters.extend(scope_parameters)
        if filters["busca"]:
            term = f"%{filters['busca']}%"
            conditions.append("""(
                r.solicitacao LIKE %s OR r.requisitante_nome LIKE %s OR
                r.descricao_ocorrencia LIKE %s OR r.local_ocorrencia LIKE %s
            )""")
            parameters.extend([term, term, term, term])
        if filters["tipo"]:
            conditions.append("r.tipo_relato = %s")
            parameters.append(filters["tipo"])
        if filters["data_inicio"]:
            conditions.append("r.data_ocorrencia >= %s")
            parameters.append(filters["data_inicio"])
        if filters["data_fim"]:
            conditions.append("r.data_ocorrencia <= %s")
            parameters.append(filters["data_fim"])
        where = " AND ".join(conditions)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                f"SELECT COUNT(*) total FROM relatos_ocorrencias r WHERE {where}",
                tuple(parameters),
            )
            total = cursor.fetchone()["total"]
            pages = ceil(total / POR_PAGINA) if total else 0
            if pages and page > pages:
                page = pages
            offset = (page - 1) * POR_PAGINA
            cursor.execute(f"""
                SELECT r.id, r.solicitacao, r.data_ocorrencia, r.hora_ocorrencia,
                       TIME_FORMAT(r.hora_ocorrencia, '%H:%i') hora_ocorrencia_exibicao,
                       r.tipo_relato, r.classificacao_ocorrencia, r.tipo_origem,
                       r.local_ocorrencia,
                       r.requisitante_nome, r.situacao_fluig,
                       r.centro_custos_codigo, r.descricao_ocorrencia,
                       r.acao_tomada, c.id classificacao_id,
                       c.severidade, c.matriz_exposicao, c.matriz_controles,
                       c.matriz_ocorrencia, c.probabilidade, c.nivel_risco,
                       c.justificativa
                FROM relatos_ocorrencias r
                LEFT JOIN relatos_ocorrencias_classificacoes c ON c.relato_id = r.id
                WHERE {where}
                ORDER BY {sort_columns[filters['sort']]} {filters['order'].upper()},
                         r.id DESC
                LIMIT %s OFFSET %s
            """, tuple(parameters + [POR_PAGINA, offset]))
            records = cursor.fetchall()
            classification_data = {
                str(row["id"]): {
                    "solicitacao": row["solicitacao"],
                    "data": row["data_ocorrencia"].strftime("%d/%m/%Y"),
                    "tipo": row["tipo_relato"],
                    "descricao": row["descricao_ocorrencia"],
                    "acao_tomada": row.get("acao_tomada") or "Não informada",
                    "severidade": row.get("severidade") or "",
                    "matriz_exposicao": row.get("matriz_exposicao") or "",
                    "matriz_controles": row.get("matriz_controles") or "",
                    "matriz_ocorrencia": row.get("matriz_ocorrencia") or "",
                    "justificativa": row.get("justificativa") or "",
                }
                for row in records
            }
            scope_types, scope_type_parameters = _scope_filter()
            cursor.execute(f"""
                SELECT DISTINCT tipo_relato
                FROM relatos_ocorrencias r
                WHERE {scope_types} AND tipo_relato IS NOT NULL AND tipo_relato <> ''
                ORDER BY tipo_relato
            """, tuple(scope_type_parameters))
            types = [row["tipo_relato"] for row in cursor.fetchall()]
        finally:
            cursor.close()
            conn.close()
        return render_template(
            "relatos_ocorrencias.html", records=records, types=types,
            filters=filters, page=page, total_pages=pages,
            total_records=total, per_page=POR_PAGINA,
            can_classify=_can_classify(), classification_data=classification_data,
        )

    @blueprint.route(
        "/relatos_ocorrencias/<int:record_id>/classificar", methods=["POST"]
    )
    @login_required
    @module_required("acesso_ssma")
    def classificar_relato_ocorrencia(record_id):
        next_url = _safe_next(request.form.get("next"))
        if not _can_classify():
            abort(403)

        severity = (request.form.get("severidade") or "").strip().upper()
        exposure = (request.form.get("matriz_exposicao") or "").strip()
        controls = (request.form.get("matriz_controles") or "").strip()
        occurrence = (request.form.get("matriz_ocorrencia") or "").strip()
        justification = (request.form.get("justificativa") or "").strip()
        try:
            if severity not in {"A", "B", "C"}:
                raise ValueError("Selecione a severidade da consequência.")
            if len(justification) > 2000:
                raise ValueError("A justificativa deve ter no máximo 2.000 caracteres.")
            probability = _calculate_probability(exposure, controls, occurrence)
            risk = _calculate_risk(severity, probability)
        except ValueError as exc:
            flash(str(exc), "warning")
            return redirect(next_url)

        scope, scope_parameters = _scope_filter()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                f"SELECT r.id FROM relatos_ocorrencias r "
                f"WHERE r.id = %s AND {scope} FOR UPDATE",
                tuple([record_id] + scope_parameters),
            )
            if not cursor.fetchone():
                abort(404)
            cursor.execute("""
                SELECT id FROM relatos_ocorrencias_classificacoes
                WHERE relato_id = %s FOR UPDATE
            """, (record_id,))
            current = cursor.fetchone()
            if current:
                classification_id = current["id"]
                cursor.execute("""
                    UPDATE relatos_ocorrencias_classificacoes
                    SET severidade=%s, matriz_exposicao=%s, matriz_controles=%s,
                        matriz_ocorrencia=%s, probabilidade=%s, nivel_risco=%s,
                        justificativa=%s, atualizado_por=%s,
                        atualizado_em=CURRENT_TIMESTAMP
                    WHERE id=%s
                """, (
                    severity, exposure, controls, occurrence, probability, risk,
                    justification, session["usuario_id"], classification_id,
                ))
            else:
                cursor.execute("""
                    INSERT INTO relatos_ocorrencias_classificacoes (
                        relato_id, severidade, matriz_exposicao, matriz_controles,
                        matriz_ocorrencia, probabilidade, nivel_risco,
                        justificativa, classificado_por
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    record_id, severity, exposure, controls, occurrence,
                    probability, risk, justification, session["usuario_id"],
                ))
                classification_id = cursor.lastrowid
            cursor.execute("""
                SELECT COALESCE(MAX(versao), 0) + 1 versao
                FROM relatos_ocorrencias_classificacoes_historico
                WHERE classificacao_id = %s
            """, (classification_id,))
            version = cursor.fetchone()["versao"]
            cursor.execute("""
                INSERT INTO relatos_ocorrencias_classificacoes_historico (
                    classificacao_id, relato_id, versao, severidade,
                    matriz_exposicao, matriz_controles, matriz_ocorrencia,
                    probabilidade, nivel_risco, justificativa, usuario_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                classification_id, record_id, version, severity, exposure,
                controls, occurrence, probability, risk, justification,
                session["usuario_id"],
            ))
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
        flash("Potencial de severidade classificado com sucesso.", "success")
        return redirect(next_url)

    @blueprint.route("/relatos_ocorrencias/importar", methods=["GET", "POST"])
    @login_required
    @module_required("acesso_ssma")
    def importar_relatos_ocorrencias():
        if session.get("perfil") != "administrador" and not session.get("gestor_ssma"):
            abort(403)
        result = None
        errors = []
        if request.method == "POST":
            file = request.files.get("arquivo")
            if not file or not file.filename:
                flash("Selecione a planilha exportada do Fluig.", "warning")
            elif not file.filename.lower().endswith(".xlsx"):
                flash("Envie um arquivo Excel no formato .xlsx.", "danger")
            else:
                content = file.read(LIMITE_ARQUIVO + 1)
                if len(content) > LIMITE_ARQUIVO:
                    flash("O arquivo excede o limite de 20 MB.", "danger")
                else:
                    try:
                        records, errors = parse_fluig_relatos_ocorrencias(content)
                        conn = get_db_connection()
                        cursor = conn.cursor(dictionary=True)
                        try:
                            inserted, updated, unchanged = _save_import(
                                cursor, records, errors, file.filename,
                                hashlib.sha256(content).hexdigest(),
                            )
                            conn.commit()
                        except Exception:
                            conn.rollback()
                            raise
                        finally:
                            cursor.close()
                            conn.close()
                        result = {
                            "total": len(records) + len(errors),
                            "inseridos": inserted,
                            "atualizados": updated,
                            "inalterados": unchanged,
                            "erros": len(errors),
                        }
                        flash("Importação dos relatos concluída.", "success")
                    except RelatoOcorrenciaImportError as exc:
                        flash(str(exc), "danger")

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT i.*, u.nome usuario_nome
                FROM relatos_ocorrencias_importacoes i
                JOIN usuarios u ON u.id = i.usuario_id
                ORDER BY i.id DESC LIMIT 20
            """)
            history = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
        return render_template(
            "importar_relatos_ocorrencias.html", result=result,
            errors=errors[:100], history=history,
        )

    @blueprint.route("/relatos_ocorrencias/<int:record_id>")
    @login_required
    @module_required("acesso_ssma")
    def detalhar_relato_ocorrencia(record_id):
        scope, parameters = _scope_filter()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(f"""
                SELECT r.*, cc.descricao centro_custos_descricao,
                       TIME_FORMAT(r.hora_ocorrencia, '%H:%i') hora_ocorrencia_exibicao,
                       c.severidade, c.matriz_exposicao, c.matriz_controles,
                       c.matriz_ocorrencia, c.probabilidade, c.nivel_risco,
                       c.justificativa, c.classificado_em, c.atualizado_em,
                       uc.nome classificado_por_nome, ua.nome atualizado_por_nome
                FROM relatos_ocorrencias r
                LEFT JOIN centros_custos cc ON cc.id = r.centro_custos_id
                LEFT JOIN relatos_ocorrencias_classificacoes c ON c.relato_id = r.id
                LEFT JOIN usuarios uc ON uc.id = c.classificado_por
                LEFT JOIN usuarios ua ON ua.id = c.atualizado_por
                WHERE r.id = %s AND {scope}
            """, tuple([record_id] + parameters))
            record = cursor.fetchone()
            if not record:
                abort(404)
            cursor.execute("""
                SELECT * FROM relatos_ocorrencias_envolvidos
                WHERE relato_id = %s ORDER BY ordem, id
            """, (record_id,))
            involved = cursor.fetchall()
            cursor.execute("""
                SELECT h.*, u.nome usuario_nome
                FROM relatos_ocorrencias_classificacoes_historico h
                JOIN usuarios u ON u.id = h.usuario_id
                WHERE h.relato_id = %s ORDER BY h.versao DESC
            """, (record_id,))
            classification_history = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
        return render_template(
            "detalhe_relato_ocorrencia.html", record=record, involved=involved,
            classification_history=classification_history,
        )
