import json

from flask import abort, flash, redirect, render_template, request, session, url_for

from app.decorators import admin_required, login_required
from app.utils.db import get_db_connection


TIPOS = {"text", "textarea", "date", "time", "number", "choice", "person", "people", "sector"}
LARGURAS = {3, 4, 6, 8, 9, 12}


def _estrutura(raw):
    try:
        campos = raw if isinstance(raw, list) else json.loads(raw or "[]")
    except (TypeError, ValueError):
        raise ValueError("A estrutura do formulário é inválida.")
    if not isinstance(campos, list) or not campos or len(campos) > 100:
        raise ValueError("Inclua de 1 a 100 campos no formulário.")
    refs = set()
    for campo in campos:
        if not isinstance(campo, dict):
            raise ValueError("A estrutura do formulário é inválida.")
        ref = str(campo.get("ref") or "").strip()
        rotulo = str(campo.get("label") or "").strip()
        tipo = str(campo.get("type") or "").strip()
        largura = int(campo.get("width") or 4)
        if not ref or ref in refs or not rotulo or len(rotulo) > 200 or tipo not in TIPOS or largura not in LARGURAS:
            raise ValueError("Revise o nome, o tipo e a largura dos campos.")
        refs.add(ref)
        campo["ref"], campo["label"], campo["type"], campo["width"] = ref, rotulo, tipo, largura
        campo["required"] = bool(campo.get("required"))
        campo["listable"] = bool(campo.get("listable"))
        campo["filterable"] = bool(campo.get("filterable"))
        campo["options"] = [str(v).strip() for v in campo.get("options", []) if str(v).strip()][:20]
        if tipo == "choice" and len(campo["options"]) < 2:
            raise ValueError(f'Informe ao menos duas alternativas para “{rotulo}”.')
    return campos


def _modelo(cursor, modelo_id):
    cursor.execute("SELECT * FROM formulario_modelos WHERE id=%s", (modelo_id,))
    return cursor.fetchone()


def _centros_permitidos(cursor, perfil, centro_id):
    if perfil in {"administrador", "avancado"}:
        cursor.execute("SELECT id, codigo, descricao FROM centros_custos WHERE ativo=1 ORDER BY codigo")
    else:
        cursor.execute("SELECT id, codigo, descricao FROM centros_custos WHERE id=%s AND ativo=1", (centro_id,))
    return cursor.fetchall()


def _modelo_acessivel(cursor, modelo, centro_id):
    if not modelo or not modelo.get("ativo") or modelo.get("status") != "publicado":
        return False
    if modelo.get("abrangencia") == "global":
        return True
    cursor.execute("SELECT 1 FROM formulario_modelos_centros WHERE modelo_id=%s AND centro_custos_id=%s", (modelo["id"], centro_id))
    return bool(cursor.fetchone())


def register_formularios_configuraveis_routes(blueprint):
    @blueprint.route("/administracao/formularios", methods=["GET", "POST"])
    @login_required
    @admin_required
    def formularios_configuraveis():
        conn = get_db_connection(); cur = conn.cursor(dictionary=True)
        if request.method == "POST":
            nome = (request.form.get("nome") or "").strip()
            descricao = (request.form.get("descricao") or "").strip()
            abrangencia = request.form.get("abrangencia") or "global"
            centros = list(dict.fromkeys(request.form.getlist("centro_custos_ids")))
            if not nome or len(nome) > 150 or abrangencia not in {"global", "centros"} or (abrangencia == "centros" and not centros):
                flash("Informe o nome e a abrangência do formulário.", "warning")
            else:
                cur.execute("INSERT INTO formulario_modelos (nome,descricao,abrangencia,criado_por) VALUES (%s,%s,%s,%s)", (nome, descricao or None, abrangencia, session.get("usuario_id")))
                modelo_id = cur.lastrowid
                for centro in centros if abrangencia == "centros" else []:
                    cur.execute("INSERT INTO formulario_modelos_centros (modelo_id,centro_custos_id) VALUES (%s,%s)", (modelo_id, centro))
                conn.commit(); cur.close(); conn.close()
                return redirect(url_for("main.editar_formulario_configuravel", modelo_id=modelo_id))
        cur.execute("""SELECT m.*, GROUP_CONCAT(cc.codigo ORDER BY cc.codigo SEPARATOR ', ') centros
                         FROM formulario_modelos m LEFT JOIN formulario_modelos_centros mc ON mc.modelo_id=m.id
                         LEFT JOIN centros_custos cc ON cc.id=mc.centro_custos_id GROUP BY m.id ORDER BY m.id DESC""")
        modelos = cur.fetchall()
        cur.execute("SELECT id,codigo,descricao FROM centros_custos WHERE ativo=1 ORDER BY codigo")
        centros = cur.fetchall(); cur.close(); conn.close()
        return render_template("formularios_configuraveis.html", modelos=modelos, centros=centros)

    @blueprint.route("/administracao/formularios/<int:modelo_id>/editar", methods=["GET", "POST"])
    @login_required
    @admin_required
    def editar_formulario_configuravel(modelo_id):
        conn=get_db_connection(); cur=conn.cursor(dictionary=True); modelo=_modelo(cur, modelo_id)
        if not modelo: cur.close(); conn.close(); abort(404)
        if request.method == "POST":
            try:
                campos=_estrutura(request.form.get("estrutura_json"))
                nome=(request.form.get("nome") or "").strip()
                if not nome or len(nome)>150: raise ValueError("Informe o nome do formulário.")
                cur.execute("UPDATE formulario_modelos SET nome=%s,descricao=%s,estrutura_json=%s WHERE id=%s", (nome,(request.form.get("descricao") or "").strip() or None,json.dumps(campos,ensure_ascii=False),modelo_id))
                conn.commit(); flash("Formulário salvo com sucesso.", "success")
                return redirect(url_for("main.formularios_configuraveis"))
            except ValueError as exc:
                flash(str(exc), "warning"); modelo["nome"]=request.form.get("nome"); modelo["descricao"]=request.form.get("descricao"); modelo["estrutura_json"]=request.form.get("estrutura_json")
        cur.close(); conn.close()
        return render_template("formulario_configuravel_editar.html", modelo=modelo, estrutura=modelo.get("estrutura_json") or "[]")

    @blueprint.post("/administracao/formularios/<int:modelo_id>/publicar")
    @login_required
    @admin_required
    def publicar_formulario_configuravel(modelo_id):
        conn=get_db_connection(); cur=conn.cursor(dictionary=True); modelo=_modelo(cur, modelo_id)
        if not modelo: cur.close(); conn.close(); abort(404)
        try: _estrutura(modelo.get("estrutura_json"))
        except ValueError as exc: flash(str(exc), "warning")
        else: cur.execute("UPDATE formulario_modelos SET status='publicado',ativo=1 WHERE id=%s",(modelo_id,));conn.commit();flash("Formulário publicado.","success")
        cur.close();conn.close();return redirect(url_for("main.formularios_configuraveis"))

    @blueprint.post("/administracao/formularios/<int:modelo_id>/status")
    @login_required
    @admin_required
    def alternar_formulario_configuravel(modelo_id):
        conn=get_db_connection();cur=conn.cursor();cur.execute("UPDATE formulario_modelos SET ativo=IF(ativo=1,0,1) WHERE id=%s",(modelo_id,));conn.commit();cur.close();conn.close()
        return redirect(url_for("main.formularios_configuraveis"))

    @blueprint.route("/formularios/<int:modelo_id>/novo", methods=["GET", "POST"])
    @login_required
    def preencher_formulario_configuravel(modelo_id):
        conn=get_db_connection();cur=conn.cursor(dictionary=True);modelo=_modelo(cur,modelo_id)
        if not _modelo_acessivel(cur,modelo,session.get("centro_custos_id")):cur.close();conn.close();abort(403)
        campos=_estrutura(modelo.get("estrutura_json")); valores={}
        cur.execute("SELECT id,nome FROM setores WHERE ativo=1 ORDER BY nome")
        setores=cur.fetchall()
        cur.execute("SELECT id,nome,matricula FROM usuarios WHERE ativo=1" + ("" if session.get("perfil") in {"administrador","avancado"} else " AND centro_custos_id=%s") + " ORDER BY nome", () if session.get("perfil") in {"administrador","avancado"} else (session.get("centro_custos_id"),))
        usuarios=cur.fetchall()
        usuarios_ids={str(usuario["id"]) for usuario in usuarios}
        setores_ids={str(setor["id"]) for setor in setores}
        if request.method=="POST":
            erros=[]
            for campo in campos:
                chave=f"campo_{campo['ref']}"
                valor=request.form.getlist(chave) if campo["type"]=="people" else (request.form.get(chave) or "").strip()
                if campo["required"] and not valor: erros.append(campo["label"])
                if campo["type"]=="choice" and valor and valor not in campo["options"]: erros.append(campo["label"])
                if campo["type"]=="person" and valor and valor not in usuarios_ids: erros.append(campo["label"])
                if campo["type"]=="people" and any(item not in usuarios_ids for item in valor): erros.append(campo["label"])
                if campo["type"]=="sector" and valor and valor not in setores_ids: erros.append(campo["label"])
                valores[campo["ref"]]=valor
            if erros: flash("Preencha corretamente: " + ", ".join(erros), "warning")
            else:
                cur.execute("INSERT INTO formulario_registros (modelo_id,respostas_json,centro_custos_id,criado_por) VALUES (%s,%s,%s,%s)",(modelo_id,json.dumps(valores,ensure_ascii=False),session.get("centro_custos_id"),session.get("usuario_id")));conn.commit();flash("Registro salvo com sucesso.","success");cur.close();conn.close();return redirect(url_for("main.listar_registros_formulario",modelo_id=modelo_id))
        cur.close();conn.close();return render_template("formulario_configuravel_aplicar.html",modelo=modelo,campos=campos,valores=valores,usuarios=usuarios,setores=setores)

    @blueprint.get("/formularios/<int:modelo_id>/registros")
    @login_required
    def listar_registros_formulario(modelo_id):
        conn=get_db_connection();cur=conn.cursor(dictionary=True);modelo=_modelo(cur,modelo_id)
        if not _modelo_acessivel(cur,modelo,session.get("centro_custos_id")):cur.close();conn.close();abort(403)
        campos=_estrutura(modelo.get("estrutura_json")); params=[modelo_id]; where="r.modelo_id=%s"
        if session.get("perfil")=="basico":where+=" AND r.criado_por=%s";params.append(session.get("usuario_id"))
        elif session.get("perfil")=="intermediario":where+=" AND r.centro_custos_id=%s";params.append(session.get("centro_custos_id"))
        cur.execute(f"SELECT r.*,u.nome autor FROM formulario_registros r JOIN usuarios u ON u.id=r.criado_por WHERE {where} ORDER BY r.id DESC LIMIT 30",params)
        registros=cur.fetchall()
        for reg in registros:
            reg["respostas"]=json.loads(reg.get("respostas_json") or "{}")
        cur.close();conn.close();return render_template("formulario_configuravel_registros.html",modelo=modelo,campos=[c for c in campos if c.get('listable')][:5],registros=registros)
