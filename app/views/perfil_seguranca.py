import calendar
from datetime import date, datetime

from flask import flash, redirect, render_template, request, session, url_for

from app.decorators import gerenciar_agendamentos_ssma_required, login_required
from app.utils.db import get_db_connection
from app.views.agenda_ssma import _resolver_periodo_aderencia


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


def _linha_tempo(cursor, usuario_id, inicio, fim):
    consultas = (
        ("Hora de Segurança", """
            SELECT DISTINCT r.id, r.data AS data_evento, t.nome AS descricao
            FROM hs_registros r
            LEFT JOIN hs_registros_participantes hp
              ON hp.id_registro = r.id AND hp.usuario_id = %s
            LEFT JOIN hs_temas t ON t.id = r.id_tema
            WHERE (
                hp.usuario_id IS NOT NULL
                OR FIND_IN_SET(
                    CAST(%s AS CHAR),
                    REPLACE(COALESCE(r.participantes, ''), ' ', '')
                ) > 0
            )
              AND r.data BETWEEN %s AND %s
        """, True),
        ("Auditoria de Padrão", """
            SELECT ap.id, ap.data_auditoria AS data_evento,
                   CONCAT_WS(' — ', ap.area_auditada, ap.atividade_auditada) AS descricao
            FROM auditorias_padrao ap
            WHERE ap.auditado_id = %s AND ap.data_auditoria BETWEEN %s AND %s
        """, False),
        ("Recusa à Tarefa", """
            SELECT r.id, r.data_recusa AS data_evento, r.descricao
            FROM recusa_tarefa r
            WHERE r.id_usuario = %s AND r.data_recusa BETWEEN %s AND %s
        """, False),
        ("Melhoria", """
            SELECT m.id, m.data AS data_evento, m.titulo AS descricao
            FROM melhorias m
            WHERE m.executante_id = %s AND m.data BETWEEN %s AND %s
        """, False),
        ("Treinamento", """
            SELECT tr.id, tr.data_treinamento AS data_evento,
                   p.titulo AS descricao
            FROM treinamentos_realizados_participantes trp
            JOIN treinamentos_realizados tr
              ON tr.id = trp.treinamento_realizado_id
            LEFT JOIN procedimentos p ON p.id = tr.procedimento_id
            WHERE trp.usuario_id = %s AND COALESCE(trp.presenca, 1) = 1
              AND tr.data_treinamento BETWEEN %s AND %s
        """, False),
    )
    eventos = []
    for tipo, sql, inclui_legado_hs in consultas:
        parametros = (
            (usuario_id, usuario_id, inicio, fim)
            if inclui_legado_hs
            else (usuario_id, inicio, fim)
        )
        cursor.execute(sql, parametros)
        for item in cursor.fetchall() or []:
            item["tipo"] = tipo
            eventos.append(item)
    return sorted(eventos, key=lambda item: (item.get("data_evento") or date.min, item.get("id") or 0), reverse=True)


def register_perfil_seguranca_routes(blueprint):
    @blueprint.route("/perfil-seguranca-colaborador", methods=["GET"])
    @login_required
    @gerenciar_agendamentos_ssma_required
    def perfil_seguranca_colaborador():
        usuario_id = request.args.get("usuario_id", type=int)
        hoje = date.today()
        nomes_meses = (
            "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
            "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
        )
        opcoes_periodo = []
        for valor, prefixo in (
            ("mes_atual", "Este mês"),
            ("mes_anterior", "Mês anterior"),
            ("mes_proximo", "Próximo mês"),
        ):
            inicio_opcao, _, _ = _resolver_periodo_aderencia(valor, hoje=hoje)
            opcoes_periodo.append({
                "valor": valor,
                "rotulo": f"{prefixo} — {nomes_meses[inicio_opcao.month - 1]}/{inicio_opcao.year}",
            })
        mes_legado = (request.args.get("mes") or "").strip()
        periodo = (request.args.get("periodo") or ("mes_ano" if mes_legado else "mes_atual")).strip()
        mes_referencia = (request.args.get("mes_referencia") or mes_legado or hoje.strftime("%Y-%m")).strip()
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
        centro_id = session.get("centro_custos_id")
        global_ = perfil in {"administrador", "avancado"}
        sql_usuarios = """
            SELECT u.id, u.nome, u.matricula, u.centro_custos_id,
                   c.nome AS cargo_nome, cc.codigo AS centro_codigo
            FROM usuarios u
            LEFT JOIN cargos c ON c.id = u.cargo_id
            LEFT JOIN centros_custos cc ON cc.id = u.centro_custos_id
            WHERE u.ativo = 1
        """
        params = []
        if not global_:
            sql_usuarios += " AND u.centro_custos_id = %s"
            params.append(centro_id)
        sql_usuarios += " ORDER BY u.nome"
        cursor.execute(sql_usuarios, params)
        usuarios = cursor.fetchall() or []
        permitidos = {item["id"] for item in usuarios}
        selecionado = next((item for item in usuarios if item["id"] == usuario_id), None)
        indicadores = None
        eventos = []
        if usuario_id in permitidos:
            cursor.execute("""
                SELECT
                  (SELECT COUNT(DISTINCT r.id)
                   FROM hs_registros r
                   LEFT JOIN hs_registros_participantes hp
                     ON hp.id_registro=r.id AND hp.usuario_id=%s
                   WHERE (
                       hp.usuario_id IS NOT NULL
                       OR FIND_IN_SET(
                           CAST(%s AS CHAR),
                           REPLACE(COALESCE(r.participantes, ''), ' ', '')
                       ) > 0
                   )
                     AND r.data BETWEEN %s AND %s) AS horas_seguranca,
                  (SELECT COUNT(*) FROM auditorias_padrao ap
                   WHERE ap.auditado_id=%s AND ap.data_auditoria BETWEEN %s AND %s) AS auditorias_padrao,
                  (SELECT COUNT(*) FROM recusa_tarefa rt
                   WHERE rt.id_usuario=%s AND rt.data_recusa BETWEEN %s AND %s) AS recusas,
                  (SELECT COUNT(*) FROM melhorias m
                   WHERE m.executante_id=%s AND m.data BETWEEN %s AND %s) AS melhorias,
                  (SELECT COALESCE(SUM(TIMESTAMPDIFF(MINUTE, tr.hora_inicio, tr.hora_fim)),0)
                   FROM treinamentos_realizados_participantes trp
                   JOIN treinamentos_realizados tr ON tr.id=trp.treinamento_realizado_id
                   WHERE trp.usuario_id=%s AND COALESCE(trp.presenca,1)=1
                     AND tr.data_treinamento BETWEEN %s AND %s) AS minutos_treinamento
            """, (
                usuario_id, usuario_id, inicio, fim, usuario_id, inicio, fim,
                usuario_id, inicio, fim, usuario_id, inicio, fim,
                usuario_id, inicio, fim,
            ))
            indicadores = cursor.fetchone() or {}
            minutos = int(indicadores.get("minutos_treinamento") or 0)
            indicadores["horas_treinamento"] = round(minutos / 60, 1)
            eventos = _linha_tempo(cursor, usuario_id, inicio, fim)
        cursor.close()
        conn.close()
        return render_template(
            "perfil_seguranca_colaborador.html",
            usuarios=usuarios,
            colaborador=selecionado,
            usuario_id=usuario_id,
            mes=mes,
            periodo_selecionado=periodo,
            opcoes_periodo=opcoes_periodo,
            mes_referencia=mes_referencia,
            data_inicio_selecionada=inicio.strftime("%Y-%m-%d"),
            data_fim_selecionada=fim.strftime("%Y-%m-%d"),
            inicio=inicio,
            fim=fim,
            indicadores=indicadores,
            eventos=eventos,
        )

