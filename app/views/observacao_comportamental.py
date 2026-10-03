from datetime import date
from math import ceil

from flask import flash, redirect, render_template, request, session, url_for

from app.decorators import login_required, module_required
from app.utils.db import get_db_connection


AREAS = (
    "Administrativo",
    "Assistência Técnica",
    "Oficina/Manutenção",
    "Operação",
)
POR_PAGINA = 30

EXPLICACOES_ITENS = {
    "A01": (
        "Quando o observador chega à frente de trabalho, os colaboradores "
        "fizeram algum ajuste em seu posicionamento para dar a conotação "
        "de que estão mais seguros?"
    ),
    "A02": (
        "A atividade foi interrompida assim que os colaboradores perceberam "
        "a presença do observador?"
    ),
    "A03": (
        "Algum colaborador colocou, reposicionou ou ajustou o EPI após "
        "perceber a observação?"
    ),
    "A04": (
        "A forma de executar a tarefa foi modificada após a chegada do "
        "observador?"
    ),
    "A05": "Havia pessoas correndo ou se deslocando com pressa de forma insegura?",
    "A06": "Alguma pessoa deixou de utilizar o caminho ou acesso seguro definido?",
    "B01": "A posição adotada criava risco de bater contra algo ou ser atingido?",
    "B02": "Havia risco de aprisionamento, prensamento ou esmagamento?",
    "B03": "A pessoa estava exposta a queda entre níveis diferentes?",
    "B04": "A pessoa estava exposta a tropeço, escorregamento ou queda no mesmo nível?",
    "B05": "A posição ou atividade expunha a pessoa a queimadura térmica ou química?",
    "B06": "Havia exposição a partes energizadas ou possibilidade de choque elétrico?",
    "B07": "Havia possibilidade de inalar ou absorver poeira, vapor, gás ou outro contaminante?",
    "B08": "A tarefa era executada com postura corporal inadequada ou não ergonômica?",
    "B09": "A tarefa exigia força, carga ou esforço físico acima do adequado?",
    "C01": "A cabeça estava desprotegida ou posicionada em uma linha de perigo?",
    "C02": "O sistema respiratório estava exposto a contaminantes sem proteção adequada?",
    "C03": "Os olhos estavam expostos a partículas, produtos ou radiação sem proteção adequada?",
    "C04": "A face estava exposta a impacto, projeção, calor ou produto químico?",
    "C05": "Os ouvidos estavam expostos a ruído sem a proteção necessária?",
    "C06": "As mãos estavam próximas de pontos de corte, impacto, calor ou prensamento?",
    "C07": "Os braços estavam expostos a contato, impacto, corte ou aprisionamento?",
    "C08": "O tronco estava exposto a impacto, produto, calor ou outra fonte de perigo?",
    "C09": "As pernas estavam expostas a impacto, corte, contato ou aprisionamento?",
    "C10": "Os pés estavam expostos a queda de materiais, perfuração ou esmagamento?",
    "C11": "A condição observada colocava todo o corpo na zona de perigo?",
    "D01": "A ferramenta ou o equipamento escolhido era inadequado para a tarefa?",
    "D02": "A ferramenta ou o equipamento estava sendo utilizado de forma incorreta?",
    "E01": "Não existia procedimento ou orientação definida para executar a tarefa?",
    "E02": "O procedimento existente não era adequado à atividade ou à condição real?",
    "E03": "O colaborador desconhecia o procedimento aplicável à tarefa?",
    "E04": "O procedimento era conhecido, mas não foi corretamente compreendido?",
    "E05": "O procedimento aplicável era conhecido, mas não estava sendo seguido?",
    "F01": "O local apresentava sujeira, resíduos ou materiais que comprometiam a segurança?",
    "F02": "Materiais, ferramentas ou equipamentos estavam dispostos de forma desorganizada?",
    "F03": "A organização ou limpeza do local estava diferente do padrão definido?",
}


def _pode_acessar(registro):
    if not registro:
        return False
    if session.get("perfil") == "administrador":
        return True
    return (
        session.get("centro_custos_id")
        and registro.get("centro_custos_id") == session.get("centro_custos_id")
    )


def _categorias_com_itens(cursor):
    cursor.execute("""
        SELECT
            c.id AS categoria_id,
            c.codigo AS categoria_codigo,
            c.nome AS categoria_nome,
            i.id AS item_id,
            i.codigo AS item_codigo,
            i.descricao AS item_descricao
        FROM oc_categorias c
        JOIN oc_itens i ON i.categoria_id = c.id AND i.ativo = 1
        WHERE c.ativo = 1
        ORDER BY c.ordem, i.ordem, i.id
    """)
    categorias = []
    por_id = {}
    for linha in cursor.fetchall():
        categoria = por_id.get(linha["categoria_id"])
        if categoria is None:
            categoria = {
                "id": linha["categoria_id"],
                "codigo": linha["categoria_codigo"],
                "nome": linha["categoria_nome"],
                "itens": [],
            }
            por_id[linha["categoria_id"]] = categoria
            categorias.append(categoria)
        categoria["itens"].append({
            "id": linha["item_id"],
            "codigo": linha["item_codigo"],
            "descricao": linha["item_descricao"],
            "ajuda": EXPLICACOES_ITENS.get(linha["item_codigo"], ""),
        })
    return categorias


def _carregar_formulario(cursor, centro_custos_id=None):
    centro_custos_id = centro_custos_id or session.get("centro_custos_id")
    if not centro_custos_id:
        raise ValueError("Informe o centro de custos da observação.")

    data_observacao = (request.form.get("data_observacao") or "").strip()
    try:
        date.fromisoformat(data_observacao)
    except ValueError as exc:
        raise ValueError("Informe uma data de observação válida.") from exc

    hora_observacao = (request.form.get("hora_observacao") or "").strip()
    local_observado = (request.form.get("local_observado") or "").strip()
    setor_observado = (request.form.get("setor_observado") or "").strip()
    area = (request.form.get("area") or "").strip()
    atividade = (request.form.get("atividade") or "").strip()
    pessoas_observadas = request.form.get("pessoas_observadas", type=int)

    if not hora_observacao:
        raise ValueError("Informe o horário da observação.")
    if not local_observado:
        raise ValueError("Informe o local observado.")
    if not setor_observado:
        raise ValueError("Informe o setor observado.")
    cursor.execute(
        "SELECT id FROM setores WHERE nome = %s LIMIT 1",
        (setor_observado,),
    )
    if not cursor.fetchone():
        raise ValueError("Selecione um setor cadastrado.")
    if area not in AREAS:
        raise ValueError("Selecione uma área de observação válida.")
    if not pessoas_observadas or pessoas_observadas < 1:
        raise ValueError("Informe ao menos uma pessoa observada.")

    cursor.execute(
        "SELECT id FROM centros_custos WHERE id = %s AND ativo = 1",
        (centro_custos_id,),
    )
    if not cursor.fetchone():
        raise ValueError("O centro de custos informado não está ativo.")

    cursor.execute("SELECT id FROM oc_itens WHERE ativo = 1")
    itens_ativos = {linha["id"] for linha in cursor.fetchall()}
    respostas = []
    for item_id in itens_ativos:
        quantidade = request.form.get(f"item_{item_id}", type=int) or 0
        if quantidade < 0 or quantidade > 999:
            raise ValueError("As quantidades devem estar entre 0 e 999.")
        if quantidade:
            respostas.append((item_id, quantidade))

    return {
        "centro_custos_id": centro_custos_id,
        "data_observacao": data_observacao,
        "hora_observacao": hora_observacao,
        "local_observado": local_observado,
        "setor_observado": setor_observado,
        "area": area,
        "atividade": atividade or None,
        "pessoas_observadas": pessoas_observadas,
        "houve_abordagem": 1 if request.form.get("houve_abordagem") else 0,
        "correcao_imediata": 1 if request.form.get("correcao_imediata") else 0,
        "descricao_abordagem": (
            request.form.get("descricao_abordagem") or ""
        ).strip() or None,
        "pontos_positivos": (
            request.form.get("pontos_positivos") or ""
        ).strip() or None,
        "observacoes_gerais": (
            request.form.get("observacoes_gerais") or ""
        ).strip() or None,
        "status": "concluida",
        "respostas": respostas,
    }


def _registrar_historico(cursor, registro_id, evento, detalhes=None):
    cursor.execute("""
        INSERT INTO oc_historico (registro_id, usuario_id, evento, detalhes)
        VALUES (%s, %s, %s, %s)
    """, (registro_id, session["usuario_id"], evento, detalhes))


def register_observacao_comportamental_routes(blueprint):
    @blueprint.route("/observacoes_comportamentais")
    @login_required
    @module_required("acesso_observacao_comportamental")
    def observacoes_comportamentais():
        observador_id = request.args.get("observador_id", type=int)
        observador_busca = (
            request.args.get("observador_busca") or ""
        ).strip()
        data_inicio = (request.args.get("data_inicio") or "").strip()
        data_fim = (request.args.get("data_fim") or "").strip()
        sort = (request.args.get("sort") or "data").strip()
        order = (request.args.get("order") or "desc").strip()
        page = max(request.args.get("page", 1, type=int), 1)

        colunas_validas = {
            "id": "r.id",
            "data": "r.data_observacao",
            "local": "r.local_observado",
            "area": "r.area",
            "observador": "u.nome",
            "pessoas": "r.pessoas_observadas",
            "marcacoes": "total_marcacoes",
            "status": "r.status",
        }
        if sort not in colunas_validas:
            sort = "data"
        if order not in {"asc", "desc"}:
            order = "desc"
        coluna_sort = colunas_validas[sort]
        direcao = order.upper()

        condicoes = ["1 = 1"]
        parametros = []
        if session.get("perfil") != "administrador":
            condicoes.append("r.centro_custos_id = %s")
            parametros.append(session.get("centro_custos_id") or 0)
        if observador_id:
            condicoes.append("r.observador_id = %s")
            parametros.append(observador_id)
        elif observador_busca:
            termo = f"%{observador_busca}%"
            condicoes.append("(u.nome LIKE %s OR u.matricula LIKE %s)")
            parametros.extend([termo, termo])
        if data_inicio:
            condicoes.append("r.data_observacao >= %s")
            parametros.append(data_inicio)
        if data_fim:
            condicoes.append("r.data_observacao <= %s")
            parametros.append(data_fim)

        onde = " AND ".join(condicoes)
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(f"""
                SELECT COUNT(*) AS total
                FROM oc_registros r
                JOIN usuarios u ON u.id = r.observador_id
                WHERE {onde}
            """, tuple(parametros))
            total = cursor.fetchone()["total"]
            total_paginas = ceil(total / POR_PAGINA) if total else 0
            if total_paginas and page > total_paginas:
                page = total_paginas
            offset = (page - 1) * POR_PAGINA

            cursor.execute(f"""
                SELECT
                    r.id, r.data_observacao, r.hora_observacao,
                    r.local_observado, r.setor_observado, r.area,
                    r.pessoas_observadas, r.status,
                    u.nome AS observador_nome,
                    cc.codigo AS centro_custos_codigo,
                    COALESCE(SUM(resp.quantidade), 0) AS total_marcacoes
                FROM oc_registros r
                JOIN usuarios u ON u.id = r.observador_id
                JOIN centros_custos cc ON cc.id = r.centro_custos_id
                LEFT JOIN oc_respostas resp ON resp.registro_id = r.id
                WHERE {onde}
                GROUP BY r.id, r.data_observacao, r.hora_observacao,
                         r.local_observado, r.setor_observado, r.area,
                         r.pessoas_observadas, r.status, u.nome, cc.codigo
                ORDER BY {coluna_sort} {direcao}, r.id DESC
                LIMIT %s OFFSET %s
            """, tuple(parametros + [POR_PAGINA, offset]))
            registros = cursor.fetchall()

            parametros_observadores = []
            escopo_observadores = ""
            if session.get("perfil") != "administrador":
                escopo_observadores = "AND centro_custos_id = %s"
                parametros_observadores.append(
                    session.get("centro_custos_id") or 0
                )
            cursor.execute(f"""
                SELECT id, nome, matricula
                FROM usuarios
                WHERE ativo = 1
                  AND tem_acesso_sistema = 1
                  {escopo_observadores}
                ORDER BY nome
            """, tuple(parametros_observadores))
            observadores = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

        return render_template(
            "observacoes_comportamentais.html",
            registros=registros,
            observadores=observadores,
            filtros={
                "observador_id": observador_id or "",
                "observador_busca": observador_busca,
                "data_inicio": data_inicio,
                "data_fim": data_fim,
                "sort": sort,
                "order": order,
            },
            page=page,
            per_page=POR_PAGINA,
            total_paginas=total_paginas,
            total_registros=total,
        )

    @blueprint.route("/observacoes_comportamentais/nova", methods=["GET", "POST"])
    @login_required
    @module_required("acesso_observacao_comportamental")
    def nova_observacao_comportamental():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            categorias = _categorias_com_itens(cursor)
            cursor.execute("""
                SELECT id, codigo, descricao
                FROM centros_custos
                WHERE id = %s
                LIMIT 1
            """, (session.get("centro_custos_id") or 0,))
            centro_custo = cursor.fetchone()
            cursor.execute("""
                SELECT id, nome
                FROM setores
                WHERE ativo = 1
                ORDER BY nome
            """)
            setores = cursor.fetchall()

            if request.method == "POST":
                try:
                    dados = _carregar_formulario(cursor)
                    cursor.execute("""
                        INSERT INTO oc_registros (
                            centro_custos_id, observador_id, data_observacao,
                            hora_observacao, local_observado, setor_observado,
                            area, atividade, pessoas_observadas, houve_abordagem,
                            correcao_imediata, descricao_abordagem,
                            pontos_positivos, observacoes_gerais, status,
                            concluido_em
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s,
                            CASE WHEN %s = 'concluida' THEN NOW() ELSE NULL END
                        )
                    """, (
                        dados["centro_custos_id"], session["usuario_id"],
                        dados["data_observacao"], dados["hora_observacao"],
                        dados["local_observado"], dados["setor_observado"],
                        dados["area"], dados["atividade"], dados["pessoas_observadas"],
                        dados["houve_abordagem"], dados["correcao_imediata"],
                        dados["descricao_abordagem"], dados["pontos_positivos"],
                        dados["observacoes_gerais"], dados["status"], dados["status"],
                    ))
                    registro_id = cursor.lastrowid
                    if dados["respostas"]:
                        cursor.executemany(
                            "INSERT INTO oc_respostas (registro_id, item_id, quantidade) VALUES (%s, %s, %s)",
                            [(registro_id, item_id, quantidade) for item_id, quantidade in dados["respostas"]],
                        )
                    _registrar_historico(
                        cursor,
                        registro_id,
                        "criada_e_concluida",
                        "Observação comportamental registrada.",
                    )
                    conn.commit()
                    flash("Observação comportamental salva com sucesso.", "success")
                    return redirect(url_for("main.detalhar_observacao_comportamental", registro_id=registro_id))
                except ValueError as exc:
                    conn.rollback()
                    flash(str(exc), "warning")
                except Exception:
                    conn.rollback()
                    raise

            return render_template(
                "form_observacao_comportamental.html",
                categorias=categorias,
                centro_custo=centro_custo,
                setores=setores,
                areas=AREAS,
                registro=None,
                respostas={},
            )
        finally:
            cursor.close()
            conn.close()

    @blueprint.route("/observacoes_comportamentais/<int:registro_id>")
    @login_required
    @module_required("acesso_observacao_comportamental")
    def detalhar_observacao_comportamental(registro_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT r.*, u.nome AS observador_nome,
                       cc.codigo AS centro_custos_codigo,
                       cc.descricao AS centro_custos_descricao
                FROM oc_registros r
                JOIN usuarios u ON u.id = r.observador_id
                JOIN centros_custos cc ON cc.id = r.centro_custos_id
                WHERE r.id = %s
            """, (registro_id,))
            registro = cursor.fetchone()
            if not _pode_acessar(registro):
                flash("Observação não encontrada ou fora do seu centro de custos.", "danger")
                return redirect(url_for("main.observacoes_comportamentais"))

            cursor.execute("""
                SELECT c.codigo AS categoria_codigo, c.nome AS categoria_nome,
                       i.descricao AS item_descricao, resp.quantidade
                FROM oc_respostas resp
                JOIN oc_itens i ON i.id = resp.item_id
                JOIN oc_categorias c ON c.id = i.categoria_id
                WHERE resp.registro_id = %s
                ORDER BY c.ordem, i.ordem
            """, (registro_id,))
            marcacoes = cursor.fetchall()
            cursor.execute("""
                SELECT h.*, u.nome AS usuario_nome
                FROM oc_historico h JOIN usuarios u ON u.id = h.usuario_id
                WHERE h.registro_id = %s ORDER BY h.criado_em DESC, h.id DESC
            """, (registro_id,))
            historico = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

        return render_template(
            "detalhe_observacao_comportamental.html",
            registro=registro,
            marcacoes=marcacoes,
            historico=historico,
            total_marcacoes=sum(item["quantidade"] for item in marcacoes),
        )

    @blueprint.route("/observacoes_comportamentais/<int:registro_id>/editar", methods=["GET", "POST"])
    @login_required
    @module_required("acesso_observacao_comportamental")
    def editar_observacao_comportamental(registro_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM oc_registros WHERE id = %s", (registro_id,))
            registro = cursor.fetchone()
            if not _pode_acessar(registro):
                flash("Observação não encontrada ou fora do seu centro de custos.", "danger")
                return redirect(url_for("main.observacoes_comportamentais"))
            if registro["status"] == "cancelada":
                flash("Reabra a observação antes de editá-la.", "warning")
                return redirect(url_for("main.detalhar_observacao_comportamental", registro_id=registro_id))

            categorias = _categorias_com_itens(cursor)
            cursor.execute("SELECT item_id, quantidade FROM oc_respostas WHERE registro_id = %s", (registro_id,))
            respostas = {linha["item_id"]: linha["quantidade"] for linha in cursor.fetchall()}
            cursor.execute("""
                SELECT id, codigo, descricao
                FROM centros_custos
                WHERE id = %s
                LIMIT 1
            """, (registro["centro_custos_id"],))
            centro_custo = cursor.fetchone()
            cursor.execute("""
                SELECT id, nome
                FROM setores
                WHERE ativo = 1 OR nome = %s
                ORDER BY nome
            """, (registro["setor_observado"],))
            setores = cursor.fetchall()

            if request.method == "POST":
                try:
                    dados = _carregar_formulario(
                        cursor,
                        registro["centro_custos_id"],
                    )
                    cursor.execute("""
                        UPDATE oc_registros SET
                            centro_custos_id=%s, data_observacao=%s, hora_observacao=%s,
                            local_observado=%s, setor_observado=%s, area=%s,
                            atividade=%s, pessoas_observadas=%s, houve_abordagem=%s,
                            correcao_imediata=%s, descricao_abordagem=%s,
                            pontos_positivos=%s, observacoes_gerais=%s, status=%s,
                            concluido_em=CASE WHEN %s='concluida' THEN COALESCE(concluido_em, NOW()) ELSE NULL END
                        WHERE id=%s
                    """, (
                        dados["centro_custos_id"], dados["data_observacao"], dados["hora_observacao"],
                        dados["local_observado"], dados["setor_observado"], dados["area"],
                        dados["atividade"], dados["pessoas_observadas"], dados["houve_abordagem"],
                        dados["correcao_imediata"], dados["descricao_abordagem"], dados["pontos_positivos"],
                        dados["observacoes_gerais"], dados["status"], dados["status"], registro_id,
                    ))
                    cursor.execute("DELETE FROM oc_respostas WHERE registro_id = %s", (registro_id,))
                    if dados["respostas"]:
                        cursor.executemany(
                            "INSERT INTO oc_respostas (registro_id, item_id, quantidade) VALUES (%s, %s, %s)",
                            [(registro_id, item_id, quantidade) for item_id, quantidade in dados["respostas"]],
                        )
                    _registrar_historico(cursor, registro_id, "editada", "Dados e marcações atualizados.")
                    conn.commit()
                    flash("Observação atualizada com sucesso.", "success")
                    return redirect(url_for("main.detalhar_observacao_comportamental", registro_id=registro_id))
                except ValueError as exc:
                    conn.rollback()
                    flash(str(exc), "warning")
                except Exception:
                    conn.rollback()
                    raise

            return render_template(
                "form_observacao_comportamental.html",
                categorias=categorias, centro_custo=centro_custo,
                setores=setores,
                areas=AREAS, registro=registro, respostas=respostas,
            )
        finally:
            cursor.close()
            conn.close()

    @blueprint.route("/observacoes_comportamentais/<int:registro_id>/cancelar", methods=["POST"])
    @login_required
    @module_required("acesso_observacao_comportamental")
    def cancelar_observacao_comportamental(registro_id):
        justificativa = (request.form.get("justificativa") or "").strip()
        if not justificativa:
            flash("Informe a justificativa do cancelamento.", "warning")
            return redirect(url_for("main.detalhar_observacao_comportamental", registro_id=registro_id))
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM oc_registros WHERE id=%s", (registro_id,))
            registro = cursor.fetchone()
            if not _pode_acessar(registro):
                flash("Observação não encontrada ou fora do seu centro de custos.", "danger")
                return redirect(url_for("main.observacoes_comportamentais"))
            cursor.execute("""
                UPDATE oc_registros SET status='cancelada', cancelado_em=NOW(),
                    cancelado_por=%s, justificativa_cancelamento=%s WHERE id=%s
            """, (session["usuario_id"], justificativa, registro_id))
            _registrar_historico(cursor, registro_id, "cancelada", justificativa)
            conn.commit()
            flash("Observação cancelada.", "success")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for("main.detalhar_observacao_comportamental", registro_id=registro_id))

    @blueprint.route("/observacoes_comportamentais/<int:registro_id>/reabrir", methods=["POST"])
    @login_required
    @module_required("acesso_observacao_comportamental")
    def reabrir_observacao_comportamental(registro_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM oc_registros WHERE id=%s", (registro_id,))
            registro = cursor.fetchone()
            if not _pode_acessar(registro):
                flash("Observação não encontrada ou fora do seu centro de custos.", "danger")
                return redirect(url_for("main.observacoes_comportamentais"))
            cursor.execute("""
                UPDATE oc_registros SET status='concluida', cancelado_em=NULL,
                    cancelado_por=NULL, justificativa_cancelamento=NULL WHERE id=%s
            """, (registro_id,))
            _registrar_historico(cursor, registro_id, "reaberta", "Observação reaberta.")
            conn.commit()
            flash("Observação reaberta com sucesso.", "success")
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for("main.detalhar_observacao_comportamental", registro_id=registro_id))
