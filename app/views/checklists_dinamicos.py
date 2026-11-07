"""Primeiro núcleo dos checklists configuráveis do TrackPlan.

Cuida do catálogo, abrangência por centro de custos, publicação na sidebar e
definição validada dos itens de verificação.
"""

import json
import unicodedata
import calendar
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from flask import abort, flash, redirect, render_template, request, session, url_for

from app.decorators import admin_required, login_required
from app.utils.db import get_db_connection


MODULOS_MENU = {
    "ssma": "SSMA",
    "gestao_ssma": "Gestão SSMA",
}

TIPOS_RESPOSTA = {
    "conformity": "Conforme / Não conforme / Não aplicável",
    "yes_no": "Sim / Não / Não aplicável",
    "choice": "Seleção de uma opção",
    "multichoice": "Múltipla escolha",
    "matrix": "Matriz de avaliação",
    "ranking": "Ordem de prioridade",
    "rating": "Avaliação por nota",
    "text": "Texto curto",
    "textarea": "Texto longo",
    "number": "Número",
    "counter": "Contador",
    "date": "Data",
    "time": "Hora",
    "person": "Uma pessoa",
    "people": "Várias pessoas",
    "sector": "Setor / Área",
    "nfc_tag": "Etiqueta NFC",
}


def _normalizar_texto(valor):
    valor = unicodedata.normalize("NFKD", valor or "")
    return " ".join(
        "".join(c for c in valor if not unicodedata.combining(c)).lower().split()
    )


def _ajustar_campo_pessoa_do_cabecalho(item):
    """Mantém compatibilidade com cabeçalhos criados antes dos tipos de pessoa."""
    if item.get("type") != "conformity":
        return
    rotulo = _normalizar_texto(item.get("text"))
    for sufixo in (" (opcional)", " opcional"):
        if rotulo.endswith(sufixo):
            rotulo = rotulo[:-len(sufixo)].strip()
    if rotulo in {"auditado", "auditados", "participante", "participantes"}:
        item["type"] = "people"
    elif rotulo in {"auditor", "responsavel", "responsavel pelo preenchimento"}:
        item["type"] = "person"


def _lista_textos(valor, minimo, maximo, mensagem):
    if not isinstance(valor, list) or not minimo <= len(valor) <= maximo:
        raise ValueError(mensagem)
    resultado = []
    for item in valor:
        if not isinstance(item, str) or not 1 <= len(item.strip()) <= 120:
            raise ValueError(mensagem)
        resultado.append(item.strip())
    if len({_normalizar_texto(item) for item in resultado}) != len(resultado):
        raise ValueError("Não repita alternativas no mesmo item.")
    return resultado


def validar_estrutura(raw):
    """Valida e higieniza a definição recebida do construtor visual."""
    if isinstance(raw, list):
        secoes = raw
    else:
        try:
            secoes = json.loads(raw or "")
        except (TypeError, ValueError):
            raise ValueError("Não foi possível ler os itens de verificação.")
    if not isinstance(secoes, list) or not 1 <= len(secoes) <= 30:
        raise ValueError("Inclua de 1 a 30 seções.")

    limpas = []
    total = 0
    for secao_indice, secao in enumerate(secoes):
        if not isinstance(secao, dict):
            raise ValueError("Seção inválida.")
        titulo = secao.get("title")
        perguntas = secao.get("questions")
        if not isinstance(titulo, str) or not 1 <= len(titulo.strip()) <= 120:
            raise ValueError("Informe o nome de cada seção, com até 120 caracteres.")
        if not isinstance(perguntas, list) or not perguntas:
            raise ValueError("Cada seção precisa ter ao menos um item de verificação.")

        itens = []
        for pergunta in perguntas:
            total += 1
            if total > 200:
                raise ValueError("O limite é de 200 itens por checklist.")
            if not isinstance(pergunta, dict):
                raise ValueError("Item de verificação inválido.")
            texto = pergunta.get("text")
            tipo = pergunta.get("type")
            if (
                not isinstance(texto, str)
                or not 1 <= len(texto.strip()) <= 500
                or tipo not in TIPOS_RESPOSTA
            ):
                raise ValueError("Confira o texto e o tipo de resposta de cada item.")
            for chave in ("required", "negative_comment", "negative_evidence"):
                if type(pergunta.get(chave)) is not bool:
                    raise ValueError("Confira as regras de preenchimento dos itens.")
            if type(pergunta.get("negative_action", False)) is not bool:
                raise ValueError("Confira a integração com o plano de ação.")

            negativo = tipo in {"conformity", "yes_no"}
            item = {
                "text": texto.strip(),
                "type": tipo,
                "required": pergunta["required"],
                "negative_comment": pergunta["negative_comment"] if negativo else False,
                "negative_evidence": pergunta["negative_evidence"] if negativo else False,
                "negative_action": pergunta.get("negative_action", False) if negativo else False,
                "options": [],
            }
            ajuda = pergunta.get("help", "")
            if not isinstance(ajuda, str) or len(ajuda.strip()) > 1000:
                raise ValueError("Use até 1.000 caracteres na orientação de cada item.")
            if ajuda.strip():
                item["help"] = ajuda.strip()

            if tipo in {"choice", "multichoice", "ranking"}:
                item["options"] = _lista_textos(
                    pergunta.get("options"), 2, 20,
                    "Itens de seleção precisam ter de 2 a 20 alternativas.",
                )
            elif tipo == "matrix":
                item["matrix_rows"] = _lista_textos(
                    pergunta.get("matrix_rows"), 1, 20,
                    "A matriz precisa ter de 1 a 20 linhas.",
                )
                item["matrix_columns"] = _lista_textos(
                    pergunta.get("matrix_columns"), 2, 10,
                    "A matriz precisa ter de 2 a 10 alternativas.",
                )
            elif tipo == "rating":
                minimo = pergunta.get("rating_min", 1)
                maximo = pergunta.get("rating_max", 5)
                estilo = pergunta.get("rating_style", "numbers")
                if minimo not in (0, 1) or type(maximo) is not int or not 2 <= maximo <= 10 or maximo <= minimo:
                    raise ValueError("Confira os limites da avaliação por nota.")
                if estilo not in {"numbers", "stars"} or (minimo == 0 and estilo == "stars"):
                    raise ValueError("Confira a apresentação da avaliação por nota.")
                item.update(rating_min=minimo, rating_max=maximo, rating_style=estilo)
                for origem, destino in (("rating_low_label", "rating_low_label"), ("rating_high_label", "rating_high_label")):
                    rotulo = pergunta.get(origem, "")
                    if not isinstance(rotulo, str) or len(rotulo.strip()) > 80:
                        raise ValueError("Use até 80 caracteres nas descrições da escala.")
                    if rotulo.strip():
                        item[destino] = rotulo.strip()
            elif tipo == "number":
                unidade = pergunta.get("measurement_unit", "")
                casas = pergunta.get("decimal_places")
                if not isinstance(unidade, str) or len(unidade.strip()) > 20:
                    raise ValueError("Use até 20 caracteres na unidade de medida.")
                if casas is not None and (type(casas) is not int or not 0 <= casas <= 10):
                    raise ValueError("Confira as casas decimais do item numérico.")
                item.update(measurement_unit=unidade.strip(), decimal_places=casas)
            elif tipo == "counter":
                minimo = pergunta.get("minimum", 0)
                maximo = pergunta.get("maximum", 999)
                inicial = pergunta.get("counter_initial", 0)
                contado = pergunta.get("counted", True)
                if any(type(v) is not int or not 0 <= v <= 1000000 for v in (minimo, maximo, inicial)):
                    raise ValueError("Confira os valores do contador.")
                if minimo > maximo or not minimo <= inicial <= maximo or type(contado) is not bool:
                    raise ValueError("O valor inicial do contador deve estar entre o mínimo e o máximo.")
                item.update(minimum=minimo, maximum=maximo, counter_initial=inicial, counted=contado)
            itens.append(item)
        layout = secao.get("layout")
        if layout is None:
            layout = (
                "header" if secao_indice == 0 and _normalizar_texto(titulo) in {
                    "dados gerais", "identificacao", "cabecalho"
                } else "standard"
            )
        if layout not in {"standard", "header"}:
            raise ValueError("Confira a apresentação de cada seção.")
        if layout == "header":
            for item in itens:
                _ajustar_campo_pessoa_do_cabecalho(item)
        limpas.append({"title": titulo.strip(), "layout": layout, "questions": itens})
    return limpas


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


def _ler_estrutura(valor):
    if isinstance(valor, list):
        return valor
    try:
        estrutura = json.loads(valor or "[]")
    except (TypeError, ValueError):
        return []
    if not isinstance(estrutura, list):
        return []
    for indice, secao in enumerate(estrutura):
        if not isinstance(secao, dict):
            continue
        if "layout" not in secao:
            titulo = _normalizar_texto(secao.get("title"))
            secao["layout"] = (
                "header" if indice == 0 and titulo in {
                    "dados gerais", "identificacao", "cabecalho"
                } else "standard"
            )
        if secao.get("layout") == "header":
            for item in secao.get("questions", []):
                if isinstance(item, dict):
                    _ajustar_campo_pessoa_do_cabecalho(item)
    return estrutura


def _chave_resposta(secao_indice, item_indice):
    return f"q_{secao_indice}_{item_indice}"


def _resolver_periodo_listagem(periodo, mes_referencia=None, data_inicio=None,
                               data_fim=None, hoje=None):
    """Replica as opções de período consolidadas no relatório de aderência."""
    hoje = hoje or date.today()
    periodo = (periodo or "mes_atual").strip()
    if periodo not in {"mes_atual", "mes_anterior", "mes_proximo", "mes_ano", "personalizado"}:
        raise ValueError("Período informado inválido.")
    if periodo == "personalizado":
        try:
            inicio = datetime.strptime((data_inicio or "").strip(), "%Y-%m-%d").date()
            fim = datetime.strptime((data_fim or "").strip(), "%Y-%m-%d").date()
        except (TypeError, ValueError):
            raise ValueError("Informe as datas inicial e final do período personalizado.")
        if inicio > fim:
            raise ValueError("A data inicial não pode ser posterior à data final.")
        if (inicio.year, inicio.month) != (fim.year, fim.month):
            raise ValueError("O período personalizado deve permanecer dentro do mesmo mês.")
        return inicio, fim, inicio.strftime("%Y-%m")
    if periodo == "mes_ano":
        try:
            referencia = datetime.strptime((mes_referencia or "").strip(), "%Y-%m").date()
        except (TypeError, ValueError):
            raise ValueError("Selecione um mês e ano válidos.")
    else:
        deslocamento = {"mes_anterior": -1, "mes_atual": 0, "mes_proximo": 1}[periodo]
        indice = hoje.year * 12 + hoje.month - 1 + deslocamento
        referencia = date(indice // 12, indice % 12 + 1, 1)
    inicio = date(referencia.year, referencia.month, 1)
    fim = date(referencia.year, referencia.month, calendar.monthrange(referencia.year, referencia.month)[1])
    return inicio, fim, inicio.strftime("%Y-%m")


def _opcoes_periodo_listagem(hoje=None):
    hoje = hoje or date.today()
    meses = ("Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
             "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro")
    opcoes = []
    for valor, prefixo in (("mes_atual", "Este mês"), ("mes_anterior", "Mês anterior"),
                           ("mes_proximo", "Próximo mês")):
        inicio, _, _ = _resolver_periodo_listagem(valor, hoje=hoje)
        opcoes.append({"valor": valor, "rotulo": f"{prefixo} — {meses[inicio.month - 1]}/{inicio.year}"})
    return opcoes


def _validar_respostas(estrutura, formulario, pessoas=None, setores=None, etiquetas_nfc=None):
    """Converte e valida as respostas sem confiar nos valores do navegador."""
    pessoas = {str(item["id"]): item for item in (pessoas or [])}
    setores = {str(item["id"]): item for item in (setores or [])}
    etiquetas_nfc = {str(item["id"]): item for item in (etiquetas_nfc or [])}
    respostas = {}
    erros = []
    for secao_indice, secao in enumerate(estrutura):
        for item_indice, item in enumerate(secao.get("questions", [])):
            chave = _chave_resposta(secao_indice, item_indice)
            tipo = item.get("type")
            bruto = formulario.get(chave, "")
            valor = bruto.strip() if isinstance(bruto, str) else bruto

            if tipo == "multichoice":
                valor = [v for v in formulario.getlist(chave) if v in item.get("options", [])]
            elif tipo == "people":
                ids = list(dict.fromkeys(formulario.getlist(chave)))
                valor = [
                    {"id": pessoas[item_id]["id"], "name": pessoas[item_id]["nome"],
                     "registration": pessoas[item_id].get("matricula")}
                    for item_id in ids if item_id in pessoas
                ]
            elif tipo == "person":
                pessoa = pessoas.get(str(valor))
                valor = ({"id": pessoa["id"], "name": pessoa["nome"],
                          "registration": pessoa.get("matricula")} if pessoa else {})
            elif tipo == "sector":
                setor = setores.get(str(valor))
                valor = ({"id": setor["id"], "name": setor["nome"]} if setor else {})
            elif tipo == "nfc_tag":
                etiqueta = etiquetas_nfc.get(str(valor))
                valor = ({
                    "id": etiqueta["id"],
                    "number": etiqueta["numero"],
                    "description": etiqueta["descricao"],
                } if etiqueta else {})
            elif tipo == "matrix":
                valor = {}
                colunas = item.get("matrix_columns", [])
                for linha_indice, linha in enumerate(item.get("matrix_rows", [])):
                    selecionada = formulario.get(f"{chave}_matrix_{linha_indice}", "")
                    if selecionada in colunas:
                        valor[linha] = selecionada
            elif tipo == "ranking":
                valor = [
                    formulario.get(f"{chave}_rank_{indice}", "")
                    for indice in range(len(item.get("options", [])))
                ]
                if set(valor) != set(item.get("options", [])) or len(set(valor)) != len(valor):
                    valor = []
            elif tipo in {"choice"} and valor not in item.get("options", []):
                valor = ""
            elif tipo == "conformity" and valor not in {"conforme", "nao_conforme", "nao_aplicavel"}:
                valor = ""
            elif tipo == "yes_no" and valor not in {"sim", "nao", "nao_aplicavel"}:
                valor = ""
            elif tipo == "rating":
                try:
                    nota = int(valor)
                except (TypeError, ValueError):
                    valor = ""
                else:
                    valor = nota if item.get("rating_min", 1) <= nota <= item.get("rating_max", 5) else ""
            elif tipo == "number":
                try:
                    valor = str(Decimal(str(valor).replace(",", "."))) if valor != "" else ""
                except (InvalidOperation, ValueError):
                    valor = ""
            elif tipo == "counter":
                try:
                    contador = int(valor)
                except (TypeError, ValueError):
                    valor = ""
                else:
                    valor = contador if item.get("minimum", 0) <= contador <= item.get("maximum", 999) else ""
            elif tipo == "date" and valor:
                try:
                    date.fromisoformat(valor)
                except ValueError:
                    valor = ""
            elif tipo == "time" and valor:
                try:
                    datetime.strptime(valor, "%H:%M")
                except ValueError:
                    valor = ""
            elif tipo == "text" and len(valor) > 255:
                valor = ""
                erros.append(f"Use até 255 caracteres em: {item.get('text')}")
            elif tipo == "textarea" and len(valor) > 3000:
                valor = ""
                erros.append(f"Use até 3.000 caracteres em: {item.get('text')}")

            vazio = valor in ("", [], {})
            if item.get("required") and vazio:
                erros.append(f"Responda: {item.get('text')}" )

            negativo = (
                (tipo == "conformity" and valor == "nao_conforme")
                or (tipo == "yes_no" and valor == "nao")
            )
            comentario = (formulario.get(f"{chave}_comment") or "").strip()
            evidencia = (formulario.get(f"{chave}_evidence") or "").strip()
            if negativo and item.get("negative_comment") and not comentario:
                erros.append(f"Informe o comentário do resultado negativo: {item.get('text')}")
            if negativo and item.get("negative_evidence") and not evidencia:
                erros.append(f"Informe a evidência do resultado negativo: {item.get('text')}")

            respostas[chave] = {
                "value": valor,
                "comment": comentario or None,
                "evidence": evidencia or None,
            }
    return respostas, erros


def _validar_acoes_checklist(estrutura, formulario, responsaveis=None):
    """Valida as ações exigidas pelos itens negativos antes de abrir a transação."""
    responsaveis = {str(item["id"]): item for item in (responsaveis or [])}
    propostas = {}
    erros = []
    pode_criar = (
        (session.get("perfil") or "").lower() == "administrador"
        or bool(session.get("acesso_plano_acao"))
    )
    for secao_indice, secao in enumerate(estrutura):
        for item_indice, item in enumerate(secao.get("questions", [])):
            if not item.get("negative_action"):
                continue
            chave = _chave_resposta(secao_indice, item_indice)
            resposta = (formulario.get(chave) or "").strip()
            negativo = (
                (item.get("type") == "conformity" and resposta == "nao_conforme")
                or (item.get("type") == "yes_no" and resposta == "nao")
            )
            if not negativo:
                continue
            if not pode_criar:
                erros.append(
                    f"Seu perfil não permite criar a ação exigida em: {item.get('text')}"
                )
                continue
            descricao = (formulario.get(f"{chave}_action_description") or "").strip()
            responsavel_id = (formulario.get(f"{chave}_action_responsible") or "").strip()
            prazo_texto = (formulario.get(f"{chave}_action_due") or "").strip()
            if not 1 <= len(descricao) <= 3000:
                erros.append(f"Descreva a ação necessária em: {item.get('text')}")
            responsavel = responsaveis.get(responsavel_id)
            if not responsavel:
                erros.append(f"Selecione um responsável válido para: {item.get('text')}")
            try:
                prazo = date.fromisoformat(prazo_texto)
            except ValueError:
                prazo = None
                erros.append(f"Informe um prazo válido para: {item.get('text')}")
            if prazo and prazo < date.today():
                erros.append(f"O prazo da ação não pode estar vencido em: {item.get('text')}")
            if descricao and responsavel and prazo and prazo >= date.today():
                propostas[chave] = {
                    "description": descricao,
                    "responsible_id": responsavel["id"],
                    "due_date": prazo,
                }
    return propostas, erros


def _obter_origem_checklist(cursor, checklist, centro_custos_id):
    nome = f"CHK-{checklist['id']}-CC-{centro_custos_id or 0}"
    descricao = f"Checklist - {checklist['nome']}"[:160]
    cursor.execute("SELECT id, ativo FROM origens WHERE nome = %s LIMIT 1", (nome,))
    origem = cursor.fetchone()
    if origem:
        if not origem.get("ativo"):
            cursor.execute(
                "UPDATE origens SET ativo = 1, descricao = %s WHERE id = %s",
                (descricao, origem["id"]),
            )
        return origem["id"]
    cursor.execute("""
        INSERT INTO origens (nome, descricao, centro_custos_id, ativo)
        VALUES (%s, %s, %s, 1)
    """, (nome, descricao, centro_custos_id))
    return cursor.lastrowid


def _criar_acoes_checklist(cursor, checklist, execucao_id, propostas):
    if not propostas:
        return {}
    centro_custos_id = session.get("centro_custos_id")
    origem_id = _obter_origem_checklist(cursor, checklist, centro_custos_id)
    criadas = {}
    for chave, proposta in propostas.items():
        cursor.execute("""
            INSERT INTO acoes (
                origem_id, responsavel_id, centro_custos_id, descricao,
                prazo, status, criado_por
            ) VALUES (%s, %s, %s, %s, %s, 'Não iniciada', %s)
        """, (
            origem_id, proposta["responsible_id"], centro_custos_id,
            proposta["description"], proposta["due_date"], session.get("usuario_id"),
        ))
        acao_id = cursor.lastrowid
        cursor.execute("""
            INSERT INTO checklist_execucao_acoes (execucao_id, item_chave, acao_id)
            VALUES (%s, %s, %s)
        """, (execucao_id, chave, acao_id))
        criadas[chave] = acao_id
    return criadas


def _execucao_visivel(cursor, execucao_id):
    parametros = [execucao_id]
    escopo = "1 = 1"
    if (session.get("perfil") or "").lower() != "administrador":
        centro_id = session.get("centro_custos_id")
        if centro_id:
            escopo = "ce.centro_custos_id = %s"
            parametros.append(centro_id)
        else:
            escopo = "ce.executor_id = %s"
            parametros.append(session.get("usuario_id"))
    cursor.execute(f"""
        SELECT ce.*, cm.nome AS checklist_nome, u.nome AS executor_nome,
               cc.codigo AS centro_codigo, cc.descricao AS centro_descricao
          FROM checklist_execucoes ce
          JOIN checklist_modelos cm ON cm.id = ce.checklist_id
          JOIN usuarios u ON u.id = ce.executor_id
     LEFT JOIN centros_custos cc ON cc.id = ce.centro_custos_id
         WHERE ce.id = %s AND ({escopo})
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

    @blueprint.route("/admin/checklists/<int:checklist_id>/editar", methods=["GET", "POST"])
    @login_required
    @admin_required
    def editar_checklist_dinamico(checklist_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM checklist_modelos WHERE id = %s", (checklist_id,))
            checklist = cursor.fetchone()
            if not checklist:
                abort(404)

            cursor.execute("""
                SELECT id, codigo, descricao FROM centros_custos
                 WHERE ativo = 1 ORDER BY codigo, descricao
            """)
            centros_custos = cursor.fetchall()
            cursor.execute(
                "SELECT centro_custos_id FROM checklist_modelos_centros WHERE checklist_id = %s",
                (checklist_id,),
            )
            centro_ids_selecionados = [str(item["centro_custos_id"]) for item in cursor.fetchall()]

            if request.method == "POST":
                nome = (request.form.get("nome") or "").strip()
                descricao = (request.form.get("descricao") or "").strip()
                abrangencia = request.form.get("abrangencia") or "global"
                centro_ids_selecionados = list(dict.fromkeys(request.form.getlist("centro_custos_ids")))
                modulo_menu = request.form.get("modulo_menu") or "ssma"
                exibir_menu = 1 if request.form.get("exibir_menu") == "1" else 0
                ordem_menu = _inteiro_nao_negativo(request.form.get("ordem_menu"))
                checklist.update(
                    nome=nome, descricao=descricao, abrangencia=abrangencia,
                    modulo_menu=modulo_menu, exibir_menu=exibir_menu,
                    ordem_menu=ordem_menu,
                )
                try:
                    if not nome:
                        raise ValueError("Informe o nome do checklist.")
                    if abrangencia not in {"global", "centros"}:
                        raise ValueError("Selecione uma abrangência válida.")
                    if abrangencia == "centros" and not centro_ids_selecionados:
                        raise ValueError("Selecione ao menos um centro de custos.")
                    if modulo_menu not in MODULOS_MENU:
                        raise ValueError("Selecione um módulo válido para a sidebar.")
                    cursor.execute("""
                        SELECT id FROM checklist_modelos
                         WHERE LOWER(TRIM(nome)) = LOWER(TRIM(%s)) AND id <> %s
                         LIMIT 1
                    """, (nome, checklist_id))
                    if cursor.fetchone():
                        raise ValueError("Já existe outro checklist com esse nome.")
                    if abrangencia == "centros":
                        cursor.execute(
                            "SELECT id FROM centros_custos WHERE ativo = 1 AND id IN ({})".format(
                                ",".join(["%s"] * len(centro_ids_selecionados))
                            ),
                            centro_ids_selecionados,
                        )
                        if {str(item["id"]) for item in cursor.fetchall()} != set(centro_ids_selecionados):
                            raise ValueError("Um dos centros de custos selecionados é inválido.")
                    estrutura = validar_estrutura(request.form.get("estrutura_json"))
                except ValueError as erro:
                    flash(str(erro), "danger")
                    checklist["estrutura_json"] = request.form.get("estrutura_json") or "[]"
                else:
                    estrutura_json = json.dumps(estrutura, ensure_ascii=False)
                    cursor.execute("""
                        UPDATE checklist_modelos
                           SET nome = %s, descricao = %s, abrangencia = %s,
                               exibir_menu = %s, modulo_menu = %s, ordem_menu = %s,
                               estrutura_json = %s,
                               publicado_em = CASE WHEN status = 'publicado' THEN CURRENT_TIMESTAMP ELSE publicado_em END
                         WHERE id = %s
                    """, (
                        nome, descricao or None, abrangencia, exibir_menu,
                        modulo_menu, ordem_menu, estrutura_json, checklist_id,
                    ))
                    cursor.execute("DELETE FROM checklist_modelos_centros WHERE checklist_id = %s", (checklist_id,))
                    if abrangencia == "centros":
                        cursor.executemany("""
                            INSERT INTO checklist_modelos_centros (checklist_id, centro_custos_id)
                            VALUES (%s, %s)
                        """, [(checklist_id, centro_id) for centro_id in centro_ids_selecionados])
                    conn.commit()
                    flash("Checklist atualizado com sucesso.", "success")
                    return redirect(url_for("main.editar_checklist_dinamico", checklist_id=checklist_id))

            estrutura = json.dumps(
                _ler_estrutura(checklist.get("estrutura_json")), ensure_ascii=False
            )
        finally:
            cursor.close()
            conn.close()

        return render_template(
            "checklist_dinamico_editar.html",
            checklist=checklist,
            estrutura=estrutura,
            tipos_resposta=TIPOS_RESPOSTA,
            centros_custos=centros_custos,
            centro_ids_selecionados=centro_ids_selecionados,
            modulos_menu=MODULOS_MENU,
        )

    @blueprint.post("/admin/checklists/<int:checklist_id>/publicar")
    @login_required
    @admin_required
    def publicar_checklist_dinamico(checklist_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT status, estrutura_json FROM checklist_modelos WHERE id = %s AND ativo = 1",
                (checklist_id,),
            )
            checklist = cursor.fetchone()
            if not checklist:
                abort(404)
            if checklist["status"] == "publicado":
                flash("O checklist já está publicado.", "info")
                return redirect(url_for("main.checklists_dinamicos"))
            try:
                estrutura = validar_estrutura(checklist.get("estrutura_json"))
            except ValueError as erro:
                flash(f"Não foi possível publicar: {erro}", "danger")
                return redirect(url_for("main.editar_checklist_dinamico", checklist_id=checklist_id))
            cursor.execute("""
                UPDATE checklist_modelos
                   SET estrutura_json = %s,
                       status = 'publicado',
                       publicado_em = CURRENT_TIMESTAMP
                 WHERE id = %s AND status = 'rascunho'
            """, (json.dumps(estrutura, ensure_ascii=False), checklist_id))
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
            estrutura = _ler_estrutura(checklist.get("estrutura_json"))
            perfil_admin = (session.get("perfil") or "").lower() == "administrador"
            centro_id = session.get("centro_custos_id")
            executor_id = (request.args.get("executor_id") or "").strip()
            if executor_id and not executor_id.isdigit():
                executor_id = ""
            periodo_selecionado = (request.args.get("periodo") or "mes_atual").strip()
            mes_referencia = (request.args.get("mes_referencia") or date.today().strftime("%Y-%m")).strip()
            data_inicio_informada = (request.args.get("data_inicio") or "").strip()
            data_fim_informada = (request.args.get("data_fim") or "").strip()
            try:
                data_inicio, data_fim, mes_referencia_calculado = _resolver_periodo_listagem(
                    periodo_selecionado, mes_referencia, data_inicio_informada, data_fim_informada
                )
                if periodo_selecionado != "mes_ano":
                    mes_referencia = mes_referencia_calculado
            except ValueError as erro:
                flash(str(erro), "warning")
                periodo_selecionado = "mes_atual"
                data_inicio, data_fim, mes_referencia = _resolver_periodo_listagem("mes_atual")

            parametros = [checklist_id]
            condicoes = []
            if not perfil_admin:
                if centro_id:
                    condicoes.append("ce.centro_custos_id = %s")
                    parametros.append(centro_id)
                else:
                    condicoes.append("ce.executor_id = %s")
                    parametros.append(session.get("usuario_id"))
            if executor_id:
                condicoes.append("ce.executor_id = %s")
                parametros.append(int(executor_id))
            condicoes.append("DATE(ce.concluido_em) >= %s")
            parametros.append(data_inicio.isoformat())
            condicoes.append("DATE(ce.concluido_em) <= %s")
            parametros.append(data_fim.isoformat())
            escopo = " AND ".join(condicoes) or "1 = 1"
            cursor.execute(f"""
                SELECT COUNT(*) AS total_preenchimentos,
                       COUNT(DISTINCT ce.executor_id) AS total_responsaveis,
                       COUNT(DISTINCT DATE(ce.concluido_em)) AS dias_com_atividade,
                       MAX(ce.concluido_em) AS ultimo_preenchimento
                  FROM checklist_execucoes ce
                 WHERE ce.checklist_id = %s AND ({escopo})
            """, parametros)
            indicadores = cursor.fetchone() or {}
            cursor.execute(f"""
                SELECT ce.id, ce.concluido_em, ce.executor_id,
                       u.nome AS executor_nome,
                       cc.codigo AS centro_codigo
                  FROM checklist_execucoes ce
                  JOIN usuarios u ON u.id = ce.executor_id
             LEFT JOIN centros_custos cc ON cc.id = ce.centro_custos_id
                 WHERE ce.checklist_id = %s AND ({escopo})
                 ORDER BY ce.concluido_em DESC, ce.id DESC
                 LIMIT 50
            """, parametros)
            execucoes = cursor.fetchall()

            if perfil_admin:
                cursor.execute("SELECT id, nome, matricula FROM usuarios ORDER BY nome")
            elif centro_id:
                cursor.execute("""
                    SELECT id, nome, matricula
                      FROM usuarios
                     WHERE centro_custos_id = %s
                     ORDER BY nome
                """, (centro_id,))
            else:
                cursor.execute("""
                    SELECT id, nome, matricula FROM usuarios WHERE id = %s
                """, (session.get("usuario_id"),))
            usuarios_filtro = cursor.fetchall()
            executor_selecionado = next(
                (usuario for usuario in usuarios_filtro if str(usuario["id"]) == executor_id),
                None,
            )
            if executor_id and not executor_selecionado:
                executor_id = ""
        finally:
            cursor.close()
            conn.close()
        return render_template(
            "checklist_dinamico_esboco.html",
            checklist=checklist,
            estrutura=estrutura,
            tipos_resposta=TIPOS_RESPOSTA,
            execucoes=execucoes,
            indicadores=indicadores,
            usuarios_filtro=usuarios_filtro,
            executor_selecionado=executor_selecionado,
            opcoes_periodo=_opcoes_periodo_listagem(),
            filtros={
                "executor_id": executor_id,
                "periodo": periodo_selecionado,
                "mes_referencia": mes_referencia,
                "data_inicio": data_inicio.isoformat(),
                "data_fim": data_fim.isoformat(),
            },
        )

    @blueprint.route("/checklists/<int:checklist_id>/aplicar", methods=["GET", "POST"])
    @login_required
    def aplicar_checklist_dinamico(checklist_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            checklist = _buscar_modelo_visivel(cursor, checklist_id)
            if not checklist:
                abort(404)
            if not _pode_acessar_modulo(checklist["modulo_menu"]):
                abort(403)
            estrutura = _ler_estrutura(checklist.get("estrutura_json"))
            if not estrutura:
                flash("Este checklist não possui itens publicados.", "danger")
                return redirect(url_for("main.abrir_checklist_dinamico", checklist_id=checklist_id))

            if ((session.get("perfil") or "").lower() == "administrador"
                    and checklist.get("abrangencia") == "centros"):
                cursor.execute("""
                    SELECT DISTINCT u.id, u.nome, u.matricula
                      FROM usuarios u
                      JOIN checklist_modelos_centros cmc
                        ON cmc.centro_custos_id = u.centro_custos_id
                     WHERE cmc.checklist_id = %s
                       AND u.ativo = 1
                     ORDER BY u.nome
                """, (checklist_id,))
            elif (session.get("perfil") or "").lower() == "administrador":
                cursor.execute("""
                    SELECT id, nome, matricula FROM usuarios
                     WHERE ativo = 1 ORDER BY nome
                """)
            elif session.get("centro_custos_id"):
                cursor.execute("""
                    SELECT id, nome, matricula FROM usuarios
                     WHERE ativo = 1 AND centro_custos_id = %s ORDER BY nome
                """, (session.get("centro_custos_id"),))
            else:
                cursor.execute("""
                    SELECT id, nome, matricula FROM usuarios
                     WHERE ativo = 1 AND id = %s
                """, (session.get("usuario_id"),))
            pessoas = cursor.fetchall()
            if ((session.get("perfil") or "").lower() == "administrador"
                    and checklist.get("abrangencia") == "centros"):
                cursor.execute("""
                    SELECT DISTINCT u.id, u.nome, u.matricula
                      FROM usuarios u
                      JOIN checklist_modelos_centros cmc
                        ON cmc.centro_custos_id = u.centro_custos_id
                     WHERE cmc.checklist_id = %s AND u.ativo = 1
                       AND u.acesso_plano_acao = 1
                     ORDER BY u.nome
                """, (checklist_id,))
            elif (session.get("perfil") or "").lower() == "administrador":
                cursor.execute("""
                    SELECT id, nome, matricula FROM usuarios
                     WHERE ativo = 1 AND acesso_plano_acao = 1 ORDER BY nome
                """)
            elif session.get("centro_custos_id"):
                cursor.execute("""
                    SELECT id, nome, matricula FROM usuarios
                     WHERE ativo = 1 AND acesso_plano_acao = 1
                       AND centro_custos_id = %s ORDER BY nome
                """, (session.get("centro_custos_id"),))
            else:
                cursor.execute("""
                    SELECT id, nome, matricula FROM usuarios
                     WHERE ativo = 1 AND acesso_plano_acao = 1 AND id = %s
                """, (session.get("usuario_id"),))
            responsaveis_acao = cursor.fetchall()
            cursor.execute("SELECT id, nome FROM setores WHERE ativo = 1 ORDER BY nome")
            setores = cursor.fetchall()

            centro_custos_id = session.get("centro_custos_id")
            if centro_custos_id:
                cursor.execute("""
                    SELECT DISTINCT e.id, e.numero, e.descricao
                      FROM nfc_etiquetas e
                      LEFT JOIN nfc_etiquetas_centros ec ON ec.etiqueta_id = e.id
                     WHERE e.ativo = 1
                       AND (e.abrangencia = 'global' OR ec.centro_custos_id = %s)
                     ORDER BY e.descricao, e.numero
                """, (centro_custos_id,))
            elif ((session.get("perfil") or "").lower() == "administrador"
                  and checklist.get("abrangencia") == "centros"):
                cursor.execute("""
                    SELECT DISTINCT e.id, e.numero, e.descricao
                      FROM nfc_etiquetas e
                      LEFT JOIN nfc_etiquetas_centros ec ON ec.etiqueta_id = e.id
                      LEFT JOIN checklist_modelos_centros cmc
                        ON cmc.centro_custos_id = ec.centro_custos_id
                     WHERE e.ativo = 1
                       AND (e.abrangencia = 'global' OR cmc.checklist_id = %s)
                     ORDER BY e.descricao, e.numero
                """, (checklist_id,))
            else:
                cursor.execute("""
                    SELECT e.id, e.numero, e.descricao
                      FROM nfc_etiquetas e
                     WHERE e.ativo = 1 AND e.abrangencia = 'global'
                     ORDER BY e.descricao, e.numero
                """)
            etiquetas_nfc = cursor.fetchall()

            valores = request.form.to_dict(flat=False) if request.method == "POST" else {}
            if request.method == "POST":
                respostas, erros = _validar_respostas(
                    estrutura, request.form, pessoas=pessoas, setores=setores,
                    etiquetas_nfc=etiquetas_nfc
                )
                propostas_acoes, erros_acoes = _validar_acoes_checklist(
                    estrutura, request.form, responsaveis=responsaveis_acao
                )
                erros.extend(erros_acoes)
                observacoes = (request.form.get("observacoes") or "").strip()
                if len(observacoes) > 2000:
                    erros.append("Use até 2.000 caracteres nas observações gerais.")
                if erros:
                    for erro in erros[:8]:
                        flash(erro, "danger")
                else:
                    cursor.execute("""
                        INSERT INTO checklist_execucoes (
                            checklist_id, executor_id, centro_custos_id,
                            respostas_json, estrutura_snapshot_json, observacoes
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        checklist_id,
                        session.get("usuario_id"),
                        session.get("centro_custos_id"),
                        json.dumps(respostas, ensure_ascii=False),
                        json.dumps(estrutura, ensure_ascii=False),
                        observacoes or None,
                    ))
                    execucao_id = cursor.lastrowid
                    acoes_criadas = _criar_acoes_checklist(
                        cursor, checklist, execucao_id, propostas_acoes
                    )
                    if acoes_criadas:
                        for chave, acao_id in acoes_criadas.items():
                            respostas[chave]["action_id"] = acao_id
                        cursor.execute(
                            "UPDATE checklist_execucoes SET respostas_json = %s WHERE id = %s",
                            (json.dumps(respostas, ensure_ascii=False), execucao_id),
                        )
                    conn.commit()
                    flash("Checklist concluído com sucesso.", "success")
                    return redirect(url_for("main.visualizar_execucao_checklist", execucao_id=execucao_id))
        finally:
            cursor.close()
            conn.close()

        return render_template(
            "checklist_dinamico_aplicar.html",
            checklist=checklist,
            estrutura=estrutura,
            valores=valores,
            pessoas=pessoas,
            responsaveis_acao=responsaveis_acao,
            setores=setores,
            etiquetas_nfc=etiquetas_nfc,
            hoje_iso=date.today().isoformat(),
        )

    @blueprint.get("/checklists/execucoes/<int:execucao_id>")
    @login_required
    def visualizar_execucao_checklist(execucao_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            execucao = _execucao_visivel(cursor, execucao_id)
            if not execucao:
                abort(404)
            estrutura = _ler_estrutura(execucao.get("estrutura_snapshot_json"))
            respostas = execucao.get("respostas_json") or {}
            if isinstance(respostas, str):
                try:
                    respostas = json.loads(respostas)
                except ValueError:
                    respostas = {}
        finally:
            cursor.close()
            conn.close()
        return render_template(
            "checklist_dinamico_visualizar.html",
            execucao=execucao,
            estrutura=estrutura,
            respostas=respostas,
        )
