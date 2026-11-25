import json
import calendar
from datetime import date, datetime
from zoneinfo import ZoneInfo

from flask import flash, redirect, render_template, request, session, url_for

from app.decorators import gestor_ssma_required, login_required
from app.utils.db import get_db_connection


ORIGEM_IFS_CLIENTE = "IFS do Cliente"
FUSO_BRASILIA = ZoneInfo("America/Sao_Paulo")


def _deslocar_mes(referencia, deslocamento):
    indice = referencia.year * 12 + referencia.month - 1 + deslocamento
    return date(indice // 12, indice % 12 + 1, 1)


def _resolver_periodo(periodo, data_inicio="", data_fim=""):
    hoje = datetime.now(FUSO_BRASILIA).date()
    if periodo == "personalizado":
        try:
            inicio = date.fromisoformat(data_inicio)
            fim = date.fromisoformat(data_fim)
            if inicio > fim:
                inicio, fim = fim, inicio
            return inicio.isoformat(), fim.isoformat()
        except (TypeError, ValueError):
            periodo = "mes_atual"
    deslocamento = {"mes_anterior": -1, "mes_atual": 0, "mes_proximo": 1}.get(periodo, 0)
    inicio = _deslocar_mes(hoje, deslocamento)
    fim = date(inicio.year, inicio.month, calendar.monthrange(inicio.year, inicio.month)[1])
    return inicio.isoformat(), fim.isoformat()


def _peso_nao_conformidade(potencial):
    """Pesos definidos pelo formulario IFS Rev. 13 (abril/2026)."""
    return {"A": 2, "B": 1, "C": 0.5}.get(potencial, 0)


def _carregar_catalogo(cursor):
    cursor.execute("""
        SELECT id, nome FROM ifs_blocos
        WHERE ativo = 1 ORDER BY ordem, id
    """)
    blocos = cursor.fetchall()
    cursor.execute("""
        SELECT id, bloco_id, codigo, descricao, potencial
        FROM ifs_itens WHERE ativo = 1 ORDER BY bloco_id, ordem, id
    """)
    itens = cursor.fetchall()
    itens_por_bloco = {}
    for item in itens:
        itens_por_bloco.setdefault(item["bloco_id"], []).append(item)
    return blocos, itens, itens_por_bloco


def _buscar_origem(cursor, centro_custos_id):
    cursor.execute("""
        SELECT id FROM origens
        WHERE centro_custos_id = %s AND ativo = 1
          AND (nome = %s OR nome IN (
              'Acoes originadas em IFS realizada pelo cliente',
              'Ações originadas em IFS realizada pelo cliente',
              'Acoes originadas em FS realizada pelo cliente',
              'Ações originadas em FS realizada pelo cliente'
          ) OR descricao IN (
              'Acoes originadas em IFS realizada pelo cliente',
              'Ações originadas em IFS realizada pelo cliente',
              'Acoes originadas em FS realizada pelo cliente',
              'Ações originadas em FS realizada pelo cliente'
          ))
        LIMIT 1
    """, (centro_custos_id, ORIGEM_IFS_CLIENTE))
    origem = cursor.fetchone()
    if origem:
        cursor.execute(
            "UPDATE origens SET nome = %s, descricao = %s WHERE id = %s",
            (ORIGEM_IFS_CLIENTE, ORIGEM_IFS_CLIENTE, origem["id"]),
        )
        return origem["id"]
    cursor.execute("""
        INSERT INTO origens (nome, descricao, ativo, centro_custos_id)
        VALUES (%s, %s, 1, %s)
    """, (ORIGEM_IFS_CLIENTE, ORIGEM_IFS_CLIENTE, centro_custos_id))
    return cursor.lastrowid


def _atualizar_status(cursor, inspecao_id):
    cursor.execute("""
        SELECT COUNT(*) total,
               SUM(CASE WHEN a.status IN ('Concluída', 'Concluida') THEN 1 ELSE 0 END) concluidas
        FROM ifs_cliente_desvio_acoes da
        JOIN ifs_cliente_desvios d ON d.id = da.desvio_id
        JOIN acoes a ON a.id = da.acao_id AND a.ativo = 1
        WHERE d.inspecao_id = %s
    """, (inspecao_id,))
    resumo = cursor.fetchone() or {}
    total = int(resumo.get("total") or 0)
    concluidas = int(resumo.get("concluidas") or 0)
    status = "pronta_devolutiva" if total and total == concluidas else "em_tratamento"
    if total == 0:
        status = "sem_desvios"
    cursor.execute("UPDATE ifs_cliente_inspecoes SET status = %s WHERE id = %s", (status, inspecao_id))
    return status


def register_ifs_cliente_routes(blueprint):
    @blueprint.route("/gestao_ssma/ifs_cliente")
    @login_required
    @gestor_ssma_required
    def listar_ifs_cliente():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            filtros = {
                "periodo": (request.args.get("periodo") or "mes_atual").strip(),
                "status": (request.args.get("status") or "").strip(),
                "sort": (request.args.get("sort") or "data_inspecao").strip(),
                "order": (request.args.get("order") or "desc").strip().lower(),
            }
            if filtros["periodo"] not in {"mes_atual", "mes_anterior", "mes_proximo", "personalizado"}:
                filtros["periodo"] = "mes_atual"
            filtros["data_inicio"], filtros["data_fim"] = _resolver_periodo(
                filtros["periodo"],
                (request.args.get("data_inicio") or "").strip(),
                (request.args.get("data_fim") or "").strip(),
            )
            colunas_ordenacao = {
                "data_inspecao": "i.data_inspecao",
                "referencia_cliente": "i.referencia_cliente",
                "descricao_atividade_os": "i.descricao_atividade_os",
                "percentual": "i.percentual",
                "total_nao_conformidades": "i.total_nao_conformidades",
                "total_acoes": "total_acoes",
                "status": "i.status",
            }
            if filtros["sort"] not in colunas_ordenacao:
                filtros["sort"] = "data_inspecao"
            if filtros["order"] not in {"asc", "desc"}:
                filtros["order"] = "desc"
            where = ["i.ativo = 1"]
            params = []
            if session.get("perfil") != "administrador":
                where.append("i.centro_custos_id = %s")
                params.append(session.get("centro_custos_id"))
            if filtros["data_inicio"]:
                where.append("i.data_inspecao >= %s")
                params.append(filtros["data_inicio"])
            if filtros["data_fim"]:
                where.append("i.data_inspecao <= %s")
                params.append(filtros["data_fim"])
            if filtros["status"]:
                where.append("i.status = %s")
                params.append(filtros["status"])
            cursor.execute(f"""
                SELECT i.*, u.nome criado_por_nome,
                       COUNT(DISTINCT da.acao_id) total_acoes,
                       SUM(CASE WHEN a.status IN ('Concluída', 'Concluida') THEN 1 ELSE 0 END) acoes_concluidas
                FROM ifs_cliente_inspecoes i
                JOIN usuarios u ON u.id = i.criado_por
                LEFT JOIN ifs_cliente_desvios d ON d.inspecao_id = i.id
                LEFT JOIN ifs_cliente_desvio_acoes da ON da.desvio_id = d.id
                LEFT JOIN acoes a ON a.id = da.acao_id AND a.ativo = 1
                WHERE {' AND '.join(where)}
                GROUP BY i.id, u.nome
                ORDER BY {colunas_ordenacao[filtros['sort']]} {filtros['order'].upper()}, i.id DESC
            """, tuple(params))
            inspecoes = cursor.fetchall()
            indicadores = {
                "total": len(inspecoes),
                "nota_media": round(
                    sum(float(item.get("percentual") or 0) for item in inspecoes) / len(inspecoes), 2
                ) if inspecoes else 0,
                "nao_conformidades": sum(int(item.get("total_nao_conformidades") or 0) for item in inspecoes),
                "acoes_pendentes": sum(
                    max(int(item.get("total_acoes") or 0) - int(item.get("acoes_concluidas") or 0), 0)
                    for item in inspecoes
                ),
            }
            return render_template(
                "listar_ifs_cliente.html", inspecoes=inspecoes,
                filtros=filtros, indicadores=indicadores,
            )
        finally:
            cursor.close()
            conn.close()

    @blueprint.route("/gestao_ssma/ifs_cliente/nova", methods=["GET", "POST"])
    @login_required
    @gestor_ssma_required
    def nova_ifs_cliente():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            blocos, itens, itens_por_bloco = _carregar_catalogo(cursor)
            centro_custos_id = session.get("centro_custos_id")
            if not centro_custos_id:
                flash("Centro de custos do usuário não identificado.", "danger")
                return redirect(url_for("main.listar_ifs_cliente"))

            cursor.execute("""
                SELECT id, nome, matricula FROM usuarios
                WHERE ativo = 1 AND (%s = 'administrador' OR centro_custos_id = %s)
                ORDER BY nome
            """, (session.get("perfil"), centro_custos_id))
            usuarios = cursor.fetchall()

            if request.method == "GET":
                return render_template(
                    "nova_ifs_cliente.html", blocos=blocos,
                    itens_por_bloco=itens_por_bloco, usuarios=usuarios,
                )

            try:
                respostas = json.loads(request.form.get("respostas_json") or "[]")
                desvios = json.loads(request.form.get("desvios_json") or "[]")
            except (TypeError, json.JSONDecodeError):
                raise ValueError("Dados da avaliação inválidos.")

            if not request.form.get("data_inspecao"):
                raise ValueError("Informe a data da inspeção realizada pelo cliente.")

            itens_validos = {str(item["id"]): item for item in itens}
            if not respostas:
                raise ValueError("Avalie pelo menos um item da IFS.")
            respostas_limpas = []
            for resposta in respostas:
                item = itens_validos.get(str(resposta.get("item_id")))
                resultado = resposta.get("resultado")
                if not item or resultado not in ("S", "N"):
                    raise ValueError("Foi encontrada uma resposta inválida.")
                respostas_limpas.append((item, resultado))

            desvios_por_item = {str(d.get("item_id")): d for d in desvios}
            for item, resultado in respostas_limpas:
                if resultado == "N":
                    desvio = desvios_por_item.get(str(item["id"]))
                    if not desvio or not (desvio.get("desvio_observado") or "").strip():
                        raise ValueError(f"Descreva a não conformidade do item {item['codigo']}.")
                    if not desvio.get("acoes"):
                        raise ValueError(f"Cadastre pelo menos uma ação para o item {item['codigo']}.")

            conformes = sum(
                1
                for item, resultado in respostas_limpas
                if resultado == "S" and item["potencial"] in {"A", "B", "C"}
            )
            nao_conformes = [(item, r) for item, r in respostas_limpas if r == "N"]
            denominador = conformes + sum(
                _peso_nao_conformidade(item["potencial"])
                for item, _ in nao_conformes
            )
            percentual = round((conformes / denominador * 100) if denominador else 0, 2)
            conceito = "Satisfatório" if percentual >= 85 else "Insatisfatório"
            status = "sem_desvios" if not nao_conformes else "em_tratamento"

            cursor.execute("""
                INSERT INTO ifs_cliente_inspecoes (
                    centro_custos_id, data_inspecao, hora_inspecao, local_inspecao,
                    participantes, descricao_atividade_os, referencia_cliente,
                    gerencia, administrador_contrato, contratada,
                    profissional_sesmt_contratada_lideranca,
                    sesmt_gerdau_fiscalizadora,
                    total_itens_avaliados, total_nao_conformidades, percentual,
                    conceito, status, criado_por
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                centro_custos_id, request.form.get("data_inspecao"),
                request.form.get("hora_inspecao") or None,
                (request.form.get("local_inspecao") or "").strip() or None,
                (request.form.get("participantes") or "").strip() or None,
                (request.form.get("descricao_atividade_os") or "").strip() or None,
                (request.form.get("referencia_cliente") or "").strip() or None,
                (request.form.get("gerencia") or "").strip() or None,
                (request.form.get("administrador_contrato") or "").strip() or None,
                (request.form.get("contratada") or "").strip() or None,
                (request.form.get("profissional_sesmt_contratada_lideranca") or "").strip() or None,
                (request.form.get("sesmt_gerdau_fiscalizadora") or "").strip() or None,
                len(respostas_limpas), len(nao_conformes), percentual,
                conceito, status, session.get("usuario_id"),
            ))
            inspecao_id = cursor.lastrowid

            for item, resultado in respostas_limpas:
                cursor.execute("""
                    INSERT INTO ifs_cliente_respostas
                    (inspecao_id,item_id,codigo_item,descricao_item,potencial,resultado)
                    VALUES (%s,%s,%s,%s,%s,%s)
                """, (inspecao_id, item["id"], item["codigo"], item["descricao"], item["potencial"], resultado))

            origem_id = _buscar_origem(cursor, centro_custos_id)
            for item, _ in nao_conformes:
                desvio = desvios_por_item[str(item["id"])]
                cursor.execute("""
                    INSERT INTO ifs_cliente_desvios
                    (inspecao_id,item_id,codigo_item,descricao_item,potencial,desvio_observado)
                    VALUES (%s,%s,%s,%s,%s,%s)
                """, (inspecao_id, item["id"], item["codigo"], item["descricao"], item["potencial"], desvio["desvio_observado"].strip()))
                desvio_id = cursor.lastrowid
                for acao in desvio["acoes"]:
                    descricao = (acao.get("descricao") or "").strip()
                    responsavel_id = acao.get("responsavel_id")
                    prazo = acao.get("prazo")
                    if not descricao or not responsavel_id or not prazo:
                        raise ValueError(f"Preencha descrição, responsável e prazo das ações do item {item['codigo']}.")
                    responsavel = next((u for u in usuarios if str(u["id"]) == str(responsavel_id)), None)
                    if not responsavel:
                        raise ValueError("Responsável fora do seu escopo de acesso.")
                    texto_acao = f"IFS do Cliente - Item {item['codigo']}: {item['descricao']}\n\nNão conformidade: {desvio['desvio_observado'].strip()}\n\nAção: {descricao}"
                    cursor.execute("""
                        INSERT INTO acoes
                        (origem_id,centro_custos_id,descricao,responsavel_id,prazo,status,criado_por)
                        VALUES (%s,%s,%s,%s,%s,'Não iniciada',%s)
                    """, (origem_id, centro_custos_id, texto_acao, responsavel_id, prazo, session.get("usuario_id")))
                    cursor.execute("INSERT INTO ifs_cliente_desvio_acoes (desvio_id,acao_id) VALUES (%s,%s)", (desvio_id, cursor.lastrowid))

            cursor.execute("""
                INSERT INTO ifs_cliente_historico (inspecao_id,usuario_id,evento,descricao)
                VALUES (%s,%s,'criacao','IFS do cliente registrada e plano de ação gerado.')
            """, (inspecao_id, session.get("usuario_id")))
            conn.commit()
            flash("IFS do Cliente registrada com sucesso.", "success")
            return redirect(url_for("main.detalhar_ifs_cliente", id=inspecao_id))
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "warning")
            return redirect(url_for("main.nova_ifs_cliente"))
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

    @blueprint.route("/gestao_ssma/ifs_cliente/<int:id>")
    @login_required
    @gestor_ssma_required
    def detalhar_ifs_cliente(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            where_escopo = "" if session.get("perfil") == "administrador" else " AND i.centro_custos_id = %s"
            params = [id]
            if where_escopo:
                params.append(session.get("centro_custos_id"))
            cursor.execute(f"""
                SELECT i.*, u.nome criado_por_nome
                FROM ifs_cliente_inspecoes i JOIN usuarios u ON u.id=i.criado_por
                WHERE i.id=%s AND i.ativo=1 {where_escopo}
            """, tuple(params))
            inspecao = cursor.fetchone()
            if not inspecao:
                flash("IFS do Cliente não encontrada no seu escopo.", "warning")
                return redirect(url_for("main.listar_ifs_cliente"))
            status = inspecao["status"] if inspecao["status"] == "encerrada" else _atualizar_status(cursor, id)
            inspecao["status"] = status
            conn.commit()
            cursor.execute("""
                SELECT d.*, a.id acao_id, a.descricao acao_descricao,
                       a.responsavel_id, u.nome responsavel_nome, a.prazo,
                       a.status acao_status, a.atualizado_em
                FROM ifs_cliente_desvios d
                LEFT JOIN ifs_cliente_desvio_acoes da ON da.desvio_id=d.id
                LEFT JOIN acoes a ON a.id=da.acao_id
                LEFT JOIN usuarios u ON u.id=a.responsavel_id
                WHERE d.inspecao_id=%s ORDER BY d.codigo_item, a.id
            """, (id,))
            linhas = cursor.fetchall()
            desvios = []
            mapa = {}
            for linha in linhas:
                chave = linha["id"]
                if chave not in mapa:
                    registro = {k: linha[k] for k in ("id", "codigo_item", "descricao_item", "potencial", "desvio_observado")}
                    registro["acoes"] = []
                    mapa[chave] = registro
                    desvios.append(registro)
                if linha.get("acao_id"):
                    mapa[chave]["acoes"].append(linha)
            cursor.execute("""
                SELECT h.*, u.nome usuario_nome FROM ifs_cliente_historico h
                JOIN usuarios u ON u.id=h.usuario_id
                WHERE h.inspecao_id=%s ORDER BY h.criado_em DESC, h.id DESC
            """, (id,))
            historico = cursor.fetchall()
            return render_template("detalhar_ifs_cliente.html", inspecao=inspecao, desvios=desvios, historico=historico)
        finally:
            cursor.close()
            conn.close()

    @blueprint.route("/gestao_ssma/ifs_cliente/<int:id>/encerrar", methods=["POST"])
    @login_required
    @gestor_ssma_required
    def encerrar_ifs_cliente(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            where_escopo = "" if session.get("perfil") == "administrador" else " AND centro_custos_id = %s"
            params = [id]
            if where_escopo:
                params.append(session.get("centro_custos_id"))
            cursor.execute(
                f"SELECT id, status FROM ifs_cliente_inspecoes WHERE id=%s AND ativo=1 {where_escopo}",
                tuple(params),
            )
            if not cursor.fetchone():
                flash("IFS do Cliente não encontrada no seu escopo.", "warning")
                return redirect(url_for("main.listar_ifs_cliente"))
            status = _atualizar_status(cursor, id)
            if status not in ("pronta_devolutiva", "sem_desvios"):
                conn.rollback()
                flash("Conclua todas as ações antes de encerrar a IFS do Cliente.", "warning")
                return redirect(url_for("main.detalhar_ifs_cliente", id=id))
            cursor.execute("UPDATE ifs_cliente_inspecoes SET status='encerrada' WHERE id=%s", (id,))
            cursor.execute("""
                INSERT INTO ifs_cliente_historico (inspecao_id,usuario_id,evento,descricao)
                VALUES (%s,%s,'encerramento','Ciclo encerrado e pronto para devolutiva ao cliente.')
            """, (id, session.get("usuario_id")))
            conn.commit()
            flash("Ciclo da IFS do Cliente encerrado.", "success")
            return redirect(url_for("main.detalhar_ifs_cliente", id=id))
        finally:
            cursor.close()
            conn.close()
