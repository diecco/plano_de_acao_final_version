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


def _linha_tempo(cursor, usuario_id, inicio, fim):
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
                 ORDER BY u.nome
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
            eventos = _linha_tempo(cursor, usuario_id, inicio, fim)

        cursor.close()
        conn.close()
        return render_template(
            "perfil_seguranca_colaborador.html",
            visao=visao, usuarios=usuarios, colaborador=selecionado,
            usuario_id=usuario_id, resumo=resumo, centros=centros,
            cargos=cargos, centro_filtro=centro_filtro, cargo_filtro=cargo_filtro,
            status_filtro=status_filtro,
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
