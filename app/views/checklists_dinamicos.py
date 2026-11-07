"""Primeiro núcleo dos checklists configuráveis do TrackPlan.

Cuida do catálogo, abrangência por centro de custos, publicação na sidebar e
definição validada dos itens de verificação.
"""

import json
import unicodedata

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
    "text": "Texto",
    "number": "Número",
    "counter": "Contador",
    "date": "Data",
}


def _normalizar_texto(valor):
    valor = unicodedata.normalize("NFKD", valor or "")
    return " ".join(
        "".join(c for c in valor if not unicodedata.combining(c)).lower().split()
    )


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
    for secao in secoes:
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

            negativo = tipo in {"conformity", "yes_no"}
            item = {
                "text": texto.strip(),
                "type": tipo,
                "required": pergunta["required"],
                "negative_comment": pergunta["negative_comment"] if negativo else False,
                "negative_evidence": pergunta["negative_evidence"] if negativo else False,
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
        limpas.append({"title": titulo.strip(), "questions": itens})
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
            if checklist["status"] == "publicado":
                flash("A versão publicada é somente leitura.", "info")
                return redirect(url_for("main.checklists_dinamicos"))

            if request.method == "POST":
                try:
                    estrutura = validar_estrutura(request.form.get("estrutura_json"))
                except ValueError as erro:
                    flash(str(erro), "danger")
                    checklist["estrutura_json"] = request.form.get("estrutura_json") or "[]"
                else:
                    estrutura_json = json.dumps(estrutura, ensure_ascii=False)
                    cursor.execute("""
                        UPDATE checklist_modelos
                           SET estrutura_json = %s
                         WHERE id = %s AND status = 'rascunho'
                    """, (estrutura_json, checklist_id))
                    conn.commit()
                    flash("Itens de verificação salvos.", "success")
                    return redirect(url_for("main.editar_checklist_dinamico", checklist_id=checklist_id))

            estrutura = checklist.get("estrutura_json") or "[]"
            if not isinstance(estrutura, str):
                estrutura = json.dumps(estrutura, ensure_ascii=False)
        finally:
            cursor.close()
            conn.close()

        return render_template(
            "checklist_dinamico_editar.html",
            checklist=checklist,
            estrutura=estrutura,
            tipos_resposta=TIPOS_RESPOSTA,
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
            estrutura = checklist.get("estrutura_json") or []
            if isinstance(estrutura, str):
                try:
                    estrutura = json.loads(estrutura)
                except ValueError:
                    estrutura = []
        finally:
            cursor.close()
            conn.close()
        return render_template(
            "checklist_dinamico_esboco.html",
            checklist=checklist,
            estrutura=estrutura,
            tipos_resposta=TIPOS_RESPOSTA,
        )
