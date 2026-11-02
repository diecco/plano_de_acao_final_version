import calendar
import math
from datetime import date, datetime

from flask import flash, redirect, render_template, request, session, url_for

from app.decorators import gerenciar_agendamentos_ssma_required, login_required
from app.utils.db import get_db_connection
from app.views.agenda_ssma import _resolver_periodo_aderencia


POR_PAGINA = 25


def _periodo_perfil(valor, hoje=None):
    hoje = hoje or date.today()
    valor = (valor or hoje.strftime("%Y-%m")).strip()
    try:
        referencia = datetime.strptime(valor, "%Y-%m").date()
    except ValueError:
        referencia = hoje.replace(day=1)
        valor = referencia.strftime("%Y-%m")
    inicio = referencia.replace(day=1)
    fim = referencia.replace(day=calendar.monthrange(referencia.year, referencia.month)[1])
    return valor, inicio, fim


def _parametros_indicadores(inicio, fim):
    return (inicio, fim, inicio, fim, inicio, fim, inicio, fim, inicio, fim)


def _colunas_indicadores():
    return """
        (SELECT COUNT(DISTINCT r.id)
           FROM hs_registros r
           LEFT JOIN hs_registros_participantes hp
             ON hp.id_registro = r.id AND hp.usuario_id = u.id
          WHERE (hp.usuario_id IS NOT NULL
                 OR FIND_IN_SET(CAST(u.id AS CHAR),
                     REPLACE(COALESCE(r.participantes, ''), ' ', '')) > 0)
            AND r.data BETWEEN %s AND %s) AS horas_seguranca,
        (SELECT COUNT(*) FROM auditorias_padrao ap
          WHERE ap.auditado_id = u.id
            AND ap.data_auditoria BETWEEN %s AND %s) AS auditorias_padrao,
        (SELECT COUNT(*) FROM recusa_tarefa rt
          WHERE rt.id_usuario = u.id
            AND rt.data_recusa BETWEEN %s AND %s) AS recusas,
        (SELECT COUNT(*) FROM melhorias m
          WHERE m.executante_id = u.id
            AND m.data BETWEEN %s AND %s) AS melhorias,
        (SELECT COALESCE(SUM(TIMESTAMPDIFF(MINUTE, tr.hora_inicio, tr.hora_fim)), 0)
           FROM treinamentos_realizados_participantes trp
           JOIN treinamentos_realizados tr
             ON tr.id = trp.treinamento_realizado_id
          WHERE trp.usuario_id = u.id AND COALESCE(trp.presenca, 1) = 1
            AND tr.data_treinamento BETWEEN %s AND %s) AS minutos_treinamento
    """


def _filtros_usuarios(
    global_, centro_escopo, busca="", centro_id=None, cargo_id=None,
    status="ativo",
):
    clausulas = []
    parametros = []
    if status == "ativo":
        clausulas.append("u.ativo = 1")
    elif status == "inativo":
        clausulas.append("u.ativo = 0")
    if not global_:
        clausulas.append("u.centro_custos_id = %s")
        parametros.append(centro_escopo)
    elif centro_id:
        clausulas.append("u.centro_custos_id = %s")
        parametros.append(centro_id)
    if cargo_id:
        clausulas.append("u.cargo_id = %s")
        parametros.append(cargo_id)
    if busca:
        clausulas.append("(u.nome LIKE %s OR u.matricula LIKE %s)")
        termo = f"%{busca}%"
        parametros.extend((termo, termo))
    return " AND ".join(clausulas) or "1 = 1", parametros


def _preparar_indicadores(item):
    minutos = int(item.get("minutos_treinamento") or 0)
    item["horas_treinamento"] = round(minutos / 60, 1)
    quantidade = sum(int(item.get(chave) or 0) for chave in (
        "horas_seguranca", "auditorias_padrao", "recusas", "melhorias"
    ))
    item["tem_registros"] = quantidade > 0 or minutos > 0
    item["total_praticas"] = quantidade
    return item


def _linha_tempo(cursor, usuario_id, inicio, fim, url_retorno):
    consultas = (
        ("Hora de Segurança", """
            SELECT DISTINCT r.id, r.data AS data_evento, t.nome AS descricao
              FROM hs_registros r
              LEFT JOIN hs_registros_participantes hp
                ON hp.id_registro = r.id AND hp.usuario_id = %s
              LEFT JOIN hs_temas t ON t.id = r.id_tema
             WHERE (hp.usuario_id IS NOT NULL
                    OR FIND_IN_SET(CAST(%s AS CHAR),
                        REPLACE(COALESCE(r.participantes, ''), ' ', '')) > 0)
               AND r.data BETWEEN %s AND %s
        """, (usuario_id, usuario_id, inicio, fim)),
        ("Auditoria de Padrão", """
            SELECT ap.id, ap.data_auditoria AS data_evento,
                   CONCAT_WS(' — ', ap.area_auditada, ap.atividade_auditada) AS descricao
              FROM auditorias_padrao ap
             WHERE ap.auditado_id = %s AND ap.data_auditoria BETWEEN %s AND %s
        """, (usuario_id, inicio, fim)),
        ("Recusa à Tarefa", """
            SELECT r.id, r.data_recusa AS data_evento, r.descricao
              FROM recusa_tarefa r
             WHERE r.id_usuario = %s AND r.data_recusa BETWEEN %s AND %s
        """, (usuario_id, inicio, fim)),
        ("Melhoria", """
            SELECT m.id, m.data AS data_evento, m.titulo AS descricao
              FROM melhorias m
             WHERE m.executante_id = %s AND m.data BETWEEN %s AND %s
        """, (usuario_id, inicio, fim)),
        ("Treinamento", """
            SELECT tr.id, tr.data_treinamento AS data_evento, p.titulo AS descricao
              FROM treinamentos_realizados_participantes trp
              JOIN treinamentos_realizados tr ON tr.id = trp.treinamento_realizado_id
              LEFT JOIN procedimentos p ON p.id = tr.procedimento_id
             WHERE trp.usuario_id = %s AND COALESCE(trp.presenca, 1) = 1
               AND tr.data_treinamento BETWEEN %s AND %s
        """, (usuario_id, inicio, fim)),
    )
    eventos = []
    for tipo, sql, parametros in consultas:
        cursor.execute(sql, parametros)
        for item in cursor.fetchall() or []:
            item["tipo"] = tipo
            tipos_url = {
                "Hora de Segurança": "hora-seguranca",
                "Auditoria de Padrão": "auditoria-padrao",
                "Recusa à Tarefa": "recusa-tarefa",
                "Melhoria": "melhoria",
                "Treinamento": "treinamento",
            }
            item["url_pratica"] = url_for(
                "main.visualizar_pratica_perfil_seguranca",
                tipo=tipos_url[tipo], registro_id=item["id"],
                usuario_id=usuario_id, next=url_retorno,
            )
            eventos.append(item)
    return sorted(eventos, key=lambda item: (
        item.get("data_evento") or date.min, item.get("id") or 0
    ), reverse=True)


def register_perfil_seguranca_routes(blueprint):
    @blueprint.route("/perfil-seguranca-colaborador", methods=["GET"])
    @login_required
    @gerenciar_agendamentos_ssma_required
    def perfil_seguranca_colaborador():
        visao = (request.args.get("visao") or "geral").strip().lower()
        if visao not in {"geral", "individual"}:
            visao = "geral"
        usuario_id = request.args.get("usuario_id", type=int)
        centro_filtro = request.args.get("centro_custos_id", type=int)
        cargo_filtro = request.args.get("cargo_id", type=int)
        status_filtro = (request.args.get("status") or "ativo").strip().lower()
        if status_filtro not in {"ativo", "inativo", "todos"}:
            status_filtro = "ativo"
        ordenar = (request.args.get("ordenar") or "nome").strip().lower()
        direcao = (request.args.get("direcao") or "asc").strip().lower()
        colunas_ordenacao = {
            "nome": "u.nome",
            "funcao": "c.nome",
            "hs": "horas_seguranca",
            "auditorias": "auditorias_padrao",
            "recusas": "recusas",
            "melhorias": "melhorias",
            "treinamentos": "minutos_treinamento",
        }
        if ordenar not in colunas_ordenacao:
            ordenar = "nome"
        if direcao not in {"asc", "desc"}:
            direcao = "asc"
        pagina = max(request.args.get("pagina", 1, type=int), 1)

        hoje = date.today()
        nomes_meses = (
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
        )
        opcoes_periodo = []
        for valor, prefixo in (("mes_atual", "Este mês"),
                               ("mes_anterior", "Mês anterior"),
                               ("mes_proximo", "Próximo mês")):
            inicio_opcao, _, _ = _resolver_periodo_aderencia(valor, hoje=hoje)
            opcoes_periodo.append({
                "valor": valor,
                "rotulo": f"{prefixo} — {nomes_meses[inicio_opcao.month - 1]}/{inicio_opcao.year}",
            })
        mes_legado = (request.args.get("mes") or "").strip()
        periodo = (request.args.get("periodo") or
                   ("mes_ano" if mes_legado else "mes_atual")).strip()
        mes_referencia = (request.args.get("mes_referencia") or mes_legado or
                          hoje.strftime("%Y-%m")).strip()
        data_inicio = (request.args.get("data_inicio") or "").strip()
        data_fim = (request.args.get("data_fim") or "").strip()
        try:
            inicio, fim, mes = _resolver_periodo_aderencia(
                periodo, mes_referencia, data_inicio, data_fim, hoje
            )
        except ValueError as exc:
            flash(str(exc), "warning")
            return redirect(url_for("main.perfil_seguranca_colaborador"))

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        perfil = (session.get("perfil") or "").lower()
        centro_escopo = session.get("centro_custos_id")
        global_ = perfil in {"administrador", "avancado"}

        escopo_sql, escopo_params = _filtros_usuarios(
            global_, centro_escopo, status="todos"
        )
        cursor.execute(f"""
            SELECT u.id, u.nome, u.matricula, u.centro_custos_id,
                   c.nome AS cargo_nome, cc.codigo AS centro_codigo
              FROM usuarios u
              LEFT JOIN cargos c ON c.id = u.cargo_id
              LEFT JOIN centros_custos cc ON cc.id = u.centro_custos_id
             WHERE {escopo_sql}
             ORDER BY u.nome
        """, escopo_params)
        usuarios = cursor.fetchall() or []

        cursor.execute("SELECT id, nome FROM cargos WHERE ativo = 1 ORDER BY nome")
        cargos = cursor.fetchall() or []
        centros = []
        if global_:
            cursor.execute("""
                SELECT id, codigo, descricao FROM centros_custos
                WHERE ativo = 1
                ORDER BY codigo, descricao
            """)
            centros = cursor.fetchall() or []
        elif centro_escopo:
            cursor.execute("""
                SELECT id, codigo, descricao FROM centros_custos
                WHERE id = %s
                LIMIT 1
            """, (centro_escopo,))
            centros = cursor.fetchall() or []
            centro_filtro = centro_escopo
        pode_escolher_centro = len(centros) > 1

        resumo = []
        total_colaboradores = total_com_registros = totais_praticas = 0
        total_paginas = 0
        if visao == "geral":
            filtros_sql, filtros_params = _filtros_usuarios(
                global_, centro_escopo, "", centro_filtro, cargo_filtro,
                status_filtro,
            )
            cursor.execute(
                f"SELECT COUNT(*) AS total FROM usuarios u WHERE {filtros_sql}",
                filtros_params,
            )
            total_colaboradores = int((cursor.fetchone() or {}).get("total") or 0)
            total_paginas = max(math.ceil(total_colaboradores / POR_PAGINA), 1)
            pagina = min(pagina, total_paginas)

            cursor.execute(f"""
                SELECT u.id, u.nome, u.matricula, c.nome AS cargo_nome,
                       cc.codigo AS centro_codigo, {_colunas_indicadores()}
                  FROM usuarios u
                  LEFT JOIN cargos c ON c.id = u.cargo_id
                  LEFT JOIN centros_custos cc ON cc.id = u.centro_custos_id
                 WHERE {filtros_sql}
                 ORDER BY {colunas_ordenacao[ordenar]} {direcao.upper()}, u.nome
                 LIMIT %s OFFSET %s
            """, list(_parametros_indicadores(inicio, fim)) + filtros_params +
                 [POR_PAGINA, (pagina - 1) * POR_PAGINA])
            resumo = [_preparar_indicadores(item) for item in (cursor.fetchall() or [])]

            # Os cartões consideram todo o conjunto filtrado, não apenas a página atual.
            cursor.execute(f"""
                SELECT u.id, {_colunas_indicadores()}
                  FROM usuarios u
                 WHERE {filtros_sql}
            """, list(_parametros_indicadores(inicio, fim)) + filtros_params)
            todos = [_preparar_indicadores(item) for item in (cursor.fetchall() or [])]
            total_com_registros = sum(1 for item in todos if item["tem_registros"])
            totais_praticas = sum(item["total_praticas"] for item in todos)

        permitidos = {item["id"] for item in usuarios}
        selecionado = next((item for item in usuarios if item["id"] == usuario_id), None)
        indicadores = None
        eventos = []
        if visao == "individual" and usuario_id in permitidos:
            cursor.execute(
                f"SELECT {_colunas_indicadores()} FROM usuarios u WHERE u.id = %s",
                _parametros_indicadores(inicio, fim) + (usuario_id,),
            )
            indicadores = _preparar_indicadores(cursor.fetchone() or {})
            url_retorno = url_for(
                "main.perfil_seguranca_colaborador", visao="individual",
                usuario_id=usuario_id, periodo=periodo,
                mes_referencia=mes_referencia,
                data_inicio=inicio.strftime("%Y-%m-%d"),
                data_fim=fim.strftime("%Y-%m-%d"),
            )
            eventos = _linha_tempo(
                cursor, usuario_id, inicio, fim, url_retorno
            )

        cursor.close()
        conn.close()
        return render_template(
            "perfil_seguranca_colaborador.html",
            visao=visao, usuarios=usuarios, colaborador=selecionado,
            usuario_id=usuario_id, resumo=resumo, centros=centros,
            cargos=cargos, centro_filtro=centro_filtro, cargo_filtro=cargo_filtro,
            status_filtro=status_filtro,
            ordenar=ordenar, direcao=direcao,
            pode_escolher_centro=pode_escolher_centro,
            global_=global_, pagina=pagina, por_pagina=POR_PAGINA,
            total_paginas=total_paginas, total_colaboradores=total_colaboradores,
            total_com_registros=total_com_registros,
            total_sem_registros=max(total_colaboradores - total_com_registros, 0),
            totais_praticas=totais_praticas, mes=mes,
            periodo_selecionado=periodo, opcoes_periodo=opcoes_periodo,
            mes_referencia=mes_referencia,
            data_inicio_selecionada=inicio.strftime("%Y-%m-%d"),
            data_fim_selecionada=fim.strftime("%Y-%m-%d"),
            inicio=inicio, fim=fim, indicadores=indicadores, eventos=eventos,
        )

    @blueprint.route(
        "/perfil-seguranca-colaborador/pratica/<tipo>/<int:registro_id>",
        methods=["GET"],
    )
    @login_required
    @gerenciar_agendamentos_ssma_required
    def visualizar_pratica_perfil_seguranca(tipo, registro_id):
        usuario_id = request.args.get("usuario_id", type=int)
        retorno = (request.args.get("next") or "").strip()
        if not retorno.startswith("/") or retorno.startswith("//"):
            retorno = url_for(
                "main.perfil_seguranca_colaborador", visao="individual",
                usuario_id=usuario_id or "",
            )

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        perfil = (session.get("perfil") or "").lower()
        centro_escopo = session.get("centro_custos_id")
        parametros_usuario = [usuario_id]
        sql_usuario = "SELECT id FROM usuarios WHERE id = %s"
        if perfil not in {"administrador", "avancado"}:
            sql_usuario += " AND centro_custos_id = %s"
            parametros_usuario.append(centro_escopo)
        cursor.execute(sql_usuario, parametros_usuario)
        usuario_permitido = cursor.fetchone()

        consultas = {
            "hora-seguranca": ("Hora de Segurança", """
                SELECT r.data, r.hora, r.turno, r.local,
                       t.nome AS tema, a.nome AS auditor,
                       r.observacoes_gerais AS observacoes
                  FROM hs_registros r
                  JOIN hs_temas t ON t.id = r.id_tema
                  JOIN usuarios a ON a.id = r.id_auditor
                  LEFT JOIN hs_registros_participantes hp
                    ON hp.id_registro = r.id AND hp.usuario_id = %s
                 WHERE r.id = %s
                   AND (hp.usuario_id IS NOT NULL OR FIND_IN_SET(
                       CAST(%s AS CHAR),
                       REPLACE(COALESCE(r.participantes, ''), ' ', '')
                   ) > 0)
            """, (usuario_id, registro_id, usuario_id), (
                ("Data", "data"), ("Hora", "hora"), ("Turno", "turno"),
                ("Local", "local"), ("Tema", "tema"),
                ("Auditor", "auditor"), ("Observações", "observacoes"),
            )),
            "auditoria-padrao": ("Auditoria de Padrão", """
                SELECT ap.data_auditoria AS data, auditor.nome AS auditor,
                       auditado.nome AS auditado, ap.area_auditada AS area,
                       ap.atividade_auditada AS atividade,
                       ap.pontos_observados AS pontos,
                       CONCAT_WS(' — ', td.sigla, p.numero_documento, p.titulo)
                           AS procedimento
                  FROM auditorias_padrao ap
                  JOIN usuarios auditor ON auditor.id = ap.auditor_id
                  JOIN usuarios auditado ON auditado.id = ap.auditado_id
                  LEFT JOIN procedimentos p ON p.id = ap.procedimento_id
                  LEFT JOIN tipos_documento td ON td.id = p.tipo_documento_id
                 WHERE ap.id = %s AND ap.auditado_id = %s
            """, (registro_id, usuario_id), (
                ("Data", "data"), ("Auditor", "auditor"),
                ("Auditado", "auditado"), ("Procedimento", "procedimento"),
                ("Área auditada", "area"), ("Atividade", "atividade"),
                ("Pontos observados", "pontos"),
            )),
            "recusa-tarefa": ("Recusa à Tarefa", """
                SELECT r.id, r.data_recusa AS data, r.hora_recusa AS hora,
                       u.nome AS colaborador, r.local, r.classificacao,
                       r.potencial_severidade AS potencial,
                       c.descricao AS causa, r.descricao,
                       criador.nome AS registrado_por
                  FROM recusa_tarefa r
                  JOIN usuarios u ON u.id = r.id_usuario
                  LEFT JOIN causas_recusa c ON c.id = r.id_causa
                  LEFT JOIN usuarios criador ON criador.id = r.criado_por
                 WHERE r.id = %s AND r.id_usuario = %s
            """, (registro_id, usuario_id), (
                ("Data", "data"), ("Hora", "hora"),
                ("Colaborador", "colaborador"), ("Local", "local"),
                ("Classificação", "classificacao"),
                ("Potencial", "potencial"), ("Causa", "causa"),
                ("Descrição", "descricao"),
            )),
            "melhoria": ("Melhoria", """
                SELECT m.data, u.nome AS executante, m.titulo,
                       m.tipo_ganho, m.descricao_antes, m.acao_realizada,
                       m.descricao_depois, m.resultados_alcancados,
                       m.economia_estimada, m.observacoes
                  FROM melhorias m
                  JOIN usuarios u ON u.id = m.executante_id
                 WHERE m.id = %s AND m.executante_id = %s
            """, (registro_id, usuario_id), (
                ("Data", "data"), ("Executante", "executante"),
                ("Título", "titulo"), ("Tipo de ganho", "tipo_ganho"),
                ("Situação anterior", "descricao_antes"),
                ("Ação realizada", "acao_realizada"),
                ("Situação posterior", "descricao_depois"),
                ("Resultados alcançados", "resultados_alcancados"),
                ("Economia estimada", "economia_estimada"),
                ("Observações", "observacoes"),
            )),
            "treinamento": ("Treinamento", """
                SELECT tr.data_treinamento AS data, tr.hora_inicio,
                       tr.hora_fim, tr.local_treinamento AS local,
                       p.titulo AS procedimento, pr.numero_revisao AS revisao,
                       CASE WHEN tr.tipo_instrutor = 'interno' THEN ui.nome
                            WHEN tr.tipo_instrutor = 'externo' THEN ie.nome
                            ELSE '-' END AS instrutor,
                       tr.observacoes
                  FROM treinamentos_realizados tr
                  JOIN treinamentos_realizados_participantes trp
                    ON trp.treinamento_realizado_id = tr.id
                  LEFT JOIN procedimentos p ON p.id = tr.procedimento_id
                  LEFT JOIN procedimento_revisoes pr
                    ON pr.id = tr.procedimento_revisao_id
                  LEFT JOIN usuarios ui ON ui.id = tr.instrutor_usuario_id
                  LEFT JOIN instrutores_externos ie
                    ON ie.id = tr.instrutor_externo_id
                 WHERE tr.id = %s AND trp.usuario_id = %s
                   AND COALESCE(trp.presenca, 1) = 1
            """, (registro_id, usuario_id), (
                ("Data", "data"), ("Hora inicial", "hora_inicio"),
                ("Hora final", "hora_fim"), ("Local", "local"),
                ("Procedimento", "procedimento"), ("Revisão", "revisao"),
                ("Instrutor", "instrutor"), ("Observações", "observacoes"),
            )),
        }

        configuracao = consultas.get(tipo)
        registro = None
        itens_hs = []
        if usuario_permitido and tipo == "hora-seguranca":
            cursor.execute(consultas[tipo][1], consultas[tipo][2])
            registro_vinculado = cursor.fetchone()
            if registro_vinculado:
                from app.views.horas_seguranca import (
                    _buscar_detalhes_hora_seguranca,
                )

                registro, itens_hs = _buscar_detalhes_hora_seguranca(
                    cursor, registro_id
                )
            titulo, campos = consultas[tipo][0], consultas[tipo][3]
        elif usuario_permitido and tipo == "auditoria-padrao":
            cursor.execute("""
                SELECT ap.id, ap.data_auditoria, ap.area_auditada,
                       ap.atividade_auditada, ap.pontos_observados,
                       ap.necessita_revisao_padrao,
                       ap.oportunidade_revisao, ap.justificativa_revisao,
                       ap.sugestao_revisao, ap.acao_revisao_id,
                       auditor.nome AS auditor_nome,
                       auditor.matricula AS auditor_matricula,
                       auditado.nome AS auditado_nome,
                       auditado.matricula AS auditado_matricula,
                       p.numero_documento, p.titulo AS procedimento_titulo,
                       td.sigla AS procedimento_sigla,
                       pr.numero_revisao,
                       ar.status AS status_acao_revisao
                  FROM auditorias_padrao ap
                  JOIN usuarios auditor ON auditor.id = ap.auditor_id
                  JOIN usuarios auditado ON auditado.id = ap.auditado_id
                  LEFT JOIN procedimentos p ON p.id = ap.procedimento_id
                  LEFT JOIN tipos_documento td ON td.id = p.tipo_documento_id
                  LEFT JOIN procedimento_revisoes pr
                    ON pr.id = ap.procedimento_revisao_id
                  LEFT JOIN acoes ar ON ar.id = ap.acao_revisao_id
                 WHERE ap.id = %s AND ap.auditado_id = %s
                   AND COALESCE(ap.ativo, 1) = 1
            """, (registro_id, usuario_id))
            registro = cursor.fetchone()
            if registro:
                cursor.execute("""
                    SELECT r.numero_item, r.item_verificacao, r.resultado,
                           d.desvio_observado, d.acao_proposta,
                           d.responsavel_id, d.prazo, d.acao_id,
                           responsavel.nome AS responsavel_nome,
                           a.status AS status_acao
                      FROM auditoria_padrao_respostas r
                      LEFT JOIN auditoria_padrao_desvios d
                        ON d.auditoria_id = r.auditoria_id
                       AND d.numero_item = r.numero_item
                      LEFT JOIN usuarios responsavel
                        ON responsavel.id = d.responsavel_id
                      LEFT JOIN acoes a ON a.id = d.acao_id
                     WHERE r.auditoria_id = %s
                     ORDER BY r.numero_item
                """, (registro_id,))
                itens_hs = cursor.fetchall()
            titulo, campos = consultas[tipo][0], consultas[tipo][3]
        elif usuario_permitido and configuracao:
            titulo, sql, parametros, campos = configuracao
            cursor.execute(sql, parametros)
            registro = cursor.fetchone()
        else:
            titulo, campos = "Prática de segurança", ()
        cursor.close()
        conn.close()

        if not registro:
            flash("Prática não encontrada ou fora do seu escopo de acesso.", "warning")
            return redirect(retorno)
        template = (
            "visualizar_recusa_perfil_seguranca.html"
            if tipo == "recusa-tarefa"
            else "visualizar_hora_seguranca_perfil.html"
            if tipo == "hora-seguranca"
            else "visualizar_auditoria_padrao_perfil.html"
            if tipo == "auditoria-padrao"
            else "visualizar_pratica_perfil_seguranca.html"
        )
        return render_template(
            template,
            titulo_pratica=titulo, registro=registro, campos=campos,
            itens_hs=itens_hs, url_retorno=retorno,
        )
