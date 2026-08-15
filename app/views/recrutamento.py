import re
from datetime import date

from flask import (
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)

from app.decorators import login_required, module_required
from app.upload_security import UploadService, UploadValidationError
from app.utils.db import get_db_connection


ORIGENS_CANDIDATURA = {
    "sine": "SINE",
    "vagas_com": "Vagas.com",
    "indeed": "Indeed",
    "curriculo_presencial": "Currículo presencial",
    "indicacao_funcionario": "Indicação de funcionário",
    "outra_indicacao": "Outra indicação",
    "outros": "Outros",
}

TESTES_PRATICOS = {
    "nao_aplicavel": "Não aplicável",
    "obrigatorio": "Obrigatório",
    "recomendado": "Recomendado",
}

RESULTADOS_ETAPA = {
    "aprovado": "Aprovado",
    "aprovado_restricao": "Aprovado com restrição",
    "reprovado": "Reprovado",
    "stand_by": "Stand-by",
}


def _somente_digitos(valor):
    return re.sub(r"\D", "", valor or "")


def cpf_valido(valor):
    cpf = _somente_digitos(valor)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    for tamanho in (9, 10):
        soma = sum(int(cpf[indice]) * (tamanho + 1 - indice) for indice in range(tamanho))
        digito = (soma * 10) % 11
        if digito == 10:
            digito = 0
        if digito != int(cpf[tamanho]):
            return False
    return True


def telefone_valido(valor):
    telefone = _somente_digitos(valor)
    return len(telefone) in (10, 11) and telefone[:2] != "00"


def _aplicar_escopo(condicoes, parametros, alias="ca"):
    perfil = session.get("perfil")
    usuario_id = session.get("usuario_id")
    centro_custos_id = session.get("centro_custos_id")

    if perfil in ("administrador", "avancado"):
        return
    if perfil == "intermediario":
        condicoes.append(f"{alias}.centro_custos_id = %s")
        parametros.append(centro_custos_id)
        return

    condicoes.append(
        f"({alias}.responsavel_rh_id = %s OR {alias}.criado_por = %s OR EXISTS ("
        "SELECT 1 FROM recrutamento_etapas etapa_escopo "
        f"WHERE etapa_escopo.candidatura_id = {alias}.id "
        "AND etapa_escopo.avaliador_id = %s))"
    )
    parametros.extend([usuario_id, usuario_id, usuario_id])


def _pode_gerenciar_candidatura(candidatura):
    return (
        session.get("perfil") == "administrador"
        or candidatura["responsavel_rh_id"] == session.get("usuario_id")
    )


def _status_apos_avaliacao(etapas):
    resultados = {etapa["resultado"] for etapa in etapas if etapa["resultado"]}
    if "reprovado" in resultados:
        return "reprovado"
    if "stand_by" in resultados:
        return "stand_by"

    pendentes = [
        etapa for etapa in etapas
        if etapa["obrigatoria"] and etapa["status"] not in ("realizada", "dispensada")
    ]
    if any(etapa["tipo"] == "entrevista_comportamental" for etapa in pendentes):
        return "aguardando_entrevista_rh"
    if any(etapa["tipo"] == "entrevista_tecnica" for etapa in pendentes):
        return "aguardando_entrevista_gestor"
    if pendentes:
        return "em_avaliacao"
    return "aguardando_proposta"


def register_recrutamento_routes(blueprint):
    @blueprint.route("/recrutamento/candidatos")
    @login_required
    @module_required("acesso_recrutamento")
    def recrutamento_candidatos():
        busca = (request.args.get("busca") or "").strip()
        status = (request.args.get("status") or "").strip()
        condicoes = ["1 = 1"]
        parametros = []
        _aplicar_escopo(condicoes, parametros)

        if busca:
            termo = f"%{busca}%"
            condicoes.append("(c.nome LIKE %s OR c.cpf LIKE %s OR ca.cargo_pretendido LIKE %s)")
            parametros.extend([termo, termo, termo])
        if status:
            condicoes.append("ca.status = %s")
            parametros.append(status)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(f"""
                SELECT
                    ca.id AS candidatura_id,
                    c.id AS candidato_id,
                    c.nome,
                    c.cpf,
                    c.telefone,
                    c.telefone_alternativo,
                    ca.cargo_pretendido,
                    ca.origem,
                    ca.status,
                    ca.data_entrada,
                    cc.codigo AS centro_custos_codigo,
                    u.nome AS responsavel_rh_nome
                FROM recrutamento_candidaturas ca
                JOIN recrutamento_candidatos c ON c.id = ca.candidato_id
                JOIN centros_custos cc ON cc.id = ca.centro_custos_id
                JOIN usuarios u ON u.id = ca.responsavel_rh_id
                WHERE {" AND ".join(condicoes)}
                ORDER BY ca.criado_em DESC
            """, tuple(parametros))
            candidaturas = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

        return render_template(
            "recrutamento_candidatos.html",
            candidaturas=candidaturas,
            origens=ORIGENS_CANDIDATURA,
            busca=busca,
            status=status,
        )

    @blueprint.route("/recrutamento/candidatos/novo", methods=["GET", "POST"])
    @login_required
    @module_required("acesso_recrutamento")
    def novo_candidato_recrutamento():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        try:
            cursor.execute("SELECT id, nome FROM cargos WHERE ativo = 1 ORDER BY nome")
            cargos = cursor.fetchall()
            cursor.execute("""
                SELECT id, codigo, descricao
                FROM centros_custos
                WHERE ativo = 1
                ORDER BY codigo
            """)
            centros_custos = cursor.fetchall()

            if request.method == "POST":
                cpf = _somente_digitos(request.form.get("cpf"))
                nome = (request.form.get("nome") or "").strip()
                telefone = _somente_digitos(request.form.get("telefone"))
                telefone_alternativo = _somente_digitos(
                    request.form.get("telefone_alternativo")
                ) or None
                email = (request.form.get("email") or "").strip().lower() or None
                cidade = (request.form.get("cidade") or "").strip() or None
                estado = (request.form.get("estado") or "").strip().upper() or None
                cargo_id = request.form.get("cargo_id", type=int)
                cargo_pretendido = (request.form.get("cargo_pretendido") or "").strip()
                origem = (request.form.get("origem") or "").strip()
                detalhe_origem = (request.form.get("detalhe_origem") or "").strip() or None
                teste_pratico = (request.form.get("exige_teste_pratico") or "nao_aplicavel").strip()
                observacoes = (request.form.get("observacoes") or "").strip() or None

                if session.get("perfil") in ("basico", "intermediario"):
                    centro_custos_id = session.get("centro_custos_id")
                else:
                    centro_custos_id = request.form.get("centro_custos_id", type=int)

                if not cpf_valido(cpf):
                    raise ValueError("Informe um CPF válido.")
                if not nome:
                    raise ValueError("Informe o nome do candidato.")
                if not telefone_valido(telefone):
                    raise ValueError(
                        "Informe um telefone válido com DDD, no formato "
                        "(##) ####-#### ou (##) #####-####."
                    )
                if telefone_alternativo and not telefone_valido(
                    telefone_alternativo
                ):
                    raise ValueError(
                        "Informe um telefone alternativo válido com DDD."
                    )
                if estado and len(estado) != 2:
                    raise ValueError("Informe a UF com duas letras.")
                if not cargo_pretendido:
                    raise ValueError("Informe o cargo pretendido.")
                if origem not in ORIGENS_CANDIDATURA:
                    raise ValueError("Selecione uma origem válida.")
                if teste_pratico not in TESTES_PRATICOS:
                    raise ValueError("Selecione uma regra válida para o teste prático.")
                if not centro_custos_id:
                    raise ValueError("Não foi possível determinar o centro de custos.")

                experiencias = []
                for ordem in range(1, 4):
                    empresa = (request.form.get(f"experiencia_empresa_{ordem}") or "").strip()
                    cargo = (request.form.get(f"experiencia_cargo_{ordem}") or "").strip()
                    inicio = request.form.get(f"experiencia_inicio_{ordem}") or None
                    fim = request.form.get(f"experiencia_fim_{ordem}") or None
                    emprego_atual = 1 if request.form.get(f"experiencia_atual_{ordem}") else 0
                    if not empresa and not cargo and not inicio and not fim:
                        continue
                    if not empresa or not cargo:
                        raise ValueError(
                            f"Informe empresa e cargo na experiência profissional {ordem}."
                        )
                    experiencias.append(
                        (ordem, empresa, cargo, inicio, None if emprego_atual else fim, emprego_atual)
                    )

                cursor.execute("SELECT id FROM recrutamento_candidatos WHERE cpf = %s", (cpf,))
                if cursor.fetchone():
                    raise ValueError("Já existe um candidato cadastrado com este CPF.")

                curriculo = None
                arquivo = request.files.get("curriculo")
                if arquivo and arquivo.filename:
                    curriculo = UploadService.salvar(
                        arquivo,
                        {"pdf", "doc", "docx"},
                        "curriculo",
                        "app/static/recrutamento_curriculos",
                    )

                cursor.execute("""
                    INSERT INTO recrutamento_candidatos (
                        cpf, nome, telefone, telefone_alternativo,
                        email, cidade, estado,
                        curriculo_arquivo, observacoes, criado_por
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    cpf, nome, telefone, telefone_alternativo,
                    email, cidade, estado,
                    curriculo, observacoes, session["usuario_id"],
                ))
                candidato_id = cursor.lastrowid

                for ordem, empresa, cargo, inicio, fim, emprego_atual in experiencias:
                    cursor.execute("""
                        INSERT INTO recrutamento_experiencias (
                            candidato_id, ordem, empresa, cargo,
                            data_inicio, data_fim, emprego_atual
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        candidato_id, ordem, empresa, cargo,
                        inicio, fim, emprego_atual,
                    ))

                cursor.execute("""
                    INSERT INTO recrutamento_candidaturas (
                        candidato_id, cargo_id, cargo_pretendido,
                        centro_custos_id, origem, detalhe_origem,
                        responsavel_rh_id, exige_teste_pratico,
                        status, data_entrada, criado_por
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                              'em_triagem', %s, %s)
                """, (
                    candidato_id, cargo_id, cargo_pretendido,
                    centro_custos_id, origem, detalhe_origem,
                    session["usuario_id"], teste_pratico,
                    date.today(), session["usuario_id"],
                ))
                candidatura_id = cursor.lastrowid

                etapas = [
                    ("entrevista_comportamental", "Entrevista comportamental", 1, "rh"),
                    ("entrevista_tecnica", "Entrevista técnica", 2, "gestor"),
                ]
                if teste_pratico != "nao_aplicavel":
                    etapas.append(("teste_pratico", "Teste prático", 3, "gestor"))

                for tipo, etapa_nome, ordem, papel in etapas:
                    cursor.execute("""
                        INSERT INTO recrutamento_etapas (
                            candidatura_id, tipo, nome, ordem,
                            obrigatoria, papel_responsavel
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        candidatura_id, tipo, etapa_nome, ordem,
                        1 if tipo != "teste_pratico" or teste_pratico == "obrigatorio" else 0,
                        papel,
                    ))

                cursor.execute("""
                    INSERT INTO recrutamento_historico (
                        candidatura_id, evento, descricao, usuario_id
                    ) VALUES (%s, 'candidatura_criada', %s, %s)
                """, (
                    candidatura_id,
                    "Candidato cadastrado e encaminhado para triagem.",
                    session["usuario_id"],
                ))
                conn.commit()
                flash("Candidato cadastrado e encaminhado para triagem.", "success")
                return redirect(url_for("main.recrutamento_candidatos"))

        except (ValueError, UploadValidationError) as exc:
            conn.rollback()
            flash(str(exc), "danger")
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()

        return render_template(
            "novo_candidato_recrutamento.html",
            cargos=cargos,
            centros_custos=centros_custos,
            origens=ORIGENS_CANDIDATURA,
            testes_praticos=TESTES_PRATICOS,
            centro_custos_usuario=session.get("centro_custos_id"),
            permite_escolher_centro=session.get("perfil") in ("administrador", "avancado"),
        )

    @blueprint.route("/recrutamento/candidaturas/<int:candidatura_id>")
    @login_required
    @module_required("acesso_recrutamento")
    def detalhe_candidatura_recrutamento(candidatura_id):
        condicoes = ["ca.id = %s"]
        parametros = [candidatura_id]
        _aplicar_escopo(condicoes, parametros)
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(f"""
                SELECT ca.*, c.nome, c.cpf, c.telefone, c.telefone_alternativo,
                       c.email, c.cidade, c.estado, c.curriculo_arquivo,
                       c.observacoes, cc.codigo AS centro_custos_codigo,
                       cc.descricao AS centro_custos_descricao,
                       rh.nome AS responsavel_rh_nome
                FROM recrutamento_candidaturas ca
                JOIN recrutamento_candidatos c ON c.id = ca.candidato_id
                JOIN centros_custos cc ON cc.id = ca.centro_custos_id
                JOIN usuarios rh ON rh.id = ca.responsavel_rh_id
                WHERE {" AND ".join(condicoes)}
            """, tuple(parametros))
            candidatura = cursor.fetchone()
            if candidatura is None:
                abort(404)
            cursor.execute("""
                SELECT e.*, u.nome AS avaliador_nome
                FROM recrutamento_etapas e
                LEFT JOIN usuarios u ON u.id = e.avaliador_id
                WHERE e.candidatura_id = %s ORDER BY e.ordem, e.id
            """, (candidatura_id,))
            etapas = cursor.fetchall()
            cursor.execute("""
                SELECT h.*, u.nome AS usuario_nome
                FROM recrutamento_historico h
                JOIN usuarios u ON u.id = h.usuario_id
                WHERE h.candidatura_id = %s
                ORDER BY h.criado_em DESC, h.id DESC
            """, (candidatura_id,))
            historico = cursor.fetchall()
            cursor.execute("""
                SELECT id, nome, matricula FROM usuarios
                WHERE ativo = 1 AND tem_acesso_sistema = 1
                  AND centro_custos_id = %s
                  AND (acesso_recrutamento = 1 OR perfil = 'administrador')
                ORDER BY nome
            """, (candidatura["centro_custos_id"],))
            avaliadores = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
        return render_template(
            "recrutamento_candidatura_detalhe.html",
            candidatura=candidatura, etapas=etapas, historico=historico,
            avaliadores=avaliadores, resultados=RESULTADOS_ETAPA,
            origens=ORIGENS_CANDIDATURA,
            pode_gerenciar=_pode_gerenciar_candidatura(candidatura),
        )

    @blueprint.route("/recrutamento/candidaturas/<int:candidatura_id>/iniciar-selecao", methods=["POST"])
    @login_required
    @module_required("acesso_recrutamento")
    def iniciar_selecao_recrutamento(candidatura_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM recrutamento_candidaturas WHERE id = %s FOR UPDATE", (candidatura_id,))
            candidatura = cursor.fetchone()
            if candidatura is None:
                abort(404)
            if not _pode_gerenciar_candidatura(candidatura):
                abort(403)
            if candidatura["status"] not in ("cadastrado", "em_triagem"):
                raise ValueError("A seleção desta candidatura já foi iniciada.")
            cursor.execute("""
                UPDATE recrutamento_etapas SET avaliador_id = %s, status = 'pendente'
                WHERE candidatura_id = %s AND tipo = 'entrevista_comportamental'
            """, (candidatura["responsavel_rh_id"], candidatura_id))
            cursor.execute("UPDATE recrutamento_candidaturas SET status = 'aguardando_entrevista_rh' WHERE id = %s", (candidatura_id,))
            cursor.execute("""
                INSERT INTO recrutamento_historico
                    (candidatura_id, evento, descricao, usuario_id)
                VALUES (%s, 'selecao_iniciada', %s, %s)
            """, (candidatura_id, "Seleção iniciada e entrevista comportamental encaminhada ao RH.", session["usuario_id"]))
            conn.commit()
            flash("Seleção iniciada. A entrevista comportamental já pode ser registrada.", "success")
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "danger")
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for("main.detalhe_candidatura_recrutamento", candidatura_id=candidatura_id))

    @blueprint.route("/recrutamento/candidaturas/<int:candidatura_id>/etapas/<int:etapa_id>/atribuir", methods=["POST"])
    @login_required
    @module_required("acesso_recrutamento")
    def atribuir_etapa_recrutamento(candidatura_id, etapa_id):
        avaliador_id = request.form.get("avaliador_id", type=int)
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM recrutamento_candidaturas WHERE id = %s", (candidatura_id,))
            candidatura = cursor.fetchone()
            if candidatura is None:
                abort(404)
            if not _pode_gerenciar_candidatura(candidatura):
                abort(403)
            cursor.execute("SELECT * FROM recrutamento_etapas WHERE id = %s AND candidatura_id = %s", (etapa_id, candidatura_id))
            etapa = cursor.fetchone()
            if etapa is None:
                abort(404)
            if etapa["tipo"] == "entrevista_comportamental":
                raise ValueError("A entrevista comportamental pertence ao RH responsável.")
            cursor.execute("""
                SELECT id, nome FROM usuarios
                WHERE id = %s AND ativo = 1 AND tem_acesso_sistema = 1
                  AND centro_custos_id = %s
                  AND (acesso_recrutamento = 1 OR perfil = 'administrador')
            """, (avaliador_id, candidatura["centro_custos_id"]))
            avaliador = cursor.fetchone()
            if avaliador is None:
                raise ValueError("Selecione um avaliador habilitado do mesmo centro de custos.")
            cursor.execute("UPDATE recrutamento_etapas SET avaliador_id = %s, status = 'pendente' WHERE id = %s", (avaliador_id, etapa_id))
            cursor.execute("""
                INSERT INTO recrutamento_historico
                    (candidatura_id, evento, descricao, usuario_id)
                VALUES (%s, 'etapa_atribuida', %s, %s)
            """, (candidatura_id, f"{etapa['nome']} atribuída a {avaliador['nome']}.", session["usuario_id"]))
            conn.commit()
            flash("Avaliador definido com sucesso.", "success")
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "danger")
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for("main.detalhe_candidatura_recrutamento", candidatura_id=candidatura_id))

    @blueprint.route("/recrutamento/candidaturas/<int:candidatura_id>/etapas/<int:etapa_id>/avaliar", methods=["POST"])
    @login_required
    @module_required("acesso_recrutamento")
    def avaliar_etapa_recrutamento(candidatura_id, etapa_id):
        resultado = (request.form.get("resultado") or "").strip()
        parecer = (request.form.get("parecer") or "").strip()
        restricao = (request.form.get("restricao") or "").strip() or None
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM recrutamento_candidaturas WHERE id = %s FOR UPDATE", (candidatura_id,))
            candidatura = cursor.fetchone()
            if candidatura is None:
                abort(404)
            cursor.execute("SELECT * FROM recrutamento_etapas WHERE id = %s AND candidatura_id = %s FOR UPDATE", (etapa_id, candidatura_id))
            etapa = cursor.fetchone()
            if etapa is None:
                abort(404)
            if session.get("perfil") != "administrador" and etapa["avaliador_id"] != session.get("usuario_id"):
                abort(403)
            if candidatura["status"] in ("reprovado", "encerrado", "desistente"):
                raise ValueError("Esta candidatura não aceita novas avaliações.")
            if resultado not in RESULTADOS_ETAPA:
                raise ValueError("Selecione um resultado válido.")
            if not parecer:
                raise ValueError("O parecer da avaliação é obrigatório.")
            if resultado == "aprovado_restricao" and not restricao:
                raise ValueError("Descreva a restrição identificada.")
            cursor.execute("""
                UPDATE recrutamento_etapas
                SET status = 'realizada', resultado = %s, parecer = %s,
                    restricao = %s, realizada_em = NOW(), registrado_por = %s
                WHERE id = %s
            """, (resultado, parecer, restricao, session["usuario_id"], etapa_id))
            cursor.execute("SELECT tipo, status, resultado, obrigatoria FROM recrutamento_etapas WHERE candidatura_id = %s", (candidatura_id,))
            novo_status = _status_apos_avaliacao(cursor.fetchall())
            cursor.execute("UPDATE recrutamento_candidaturas SET status = %s WHERE id = %s", (novo_status, candidatura_id))
            cursor.execute("""
                INSERT INTO recrutamento_historico
                    (candidatura_id, evento, descricao, usuario_id)
                VALUES (%s, 'etapa_avaliada', %s, %s)
            """, (candidatura_id, f"{etapa['nome']} registrada: {RESULTADOS_ETAPA[resultado]}.", session["usuario_id"]))
            conn.commit()
            flash("Parecer registrado com sucesso.", "success")
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "danger")
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for("main.detalhe_candidatura_recrutamento", candidatura_id=candidatura_id))

    @blueprint.route("/recrutamento/curriculos/<path:nome>")
    @login_required
    @module_required("acesso_recrutamento")
    def baixar_curriculo_recrutamento(nome):
        condicoes = ["c.curriculo_arquivo = %s"]
        parametros = [nome]
        _aplicar_escopo(condicoes, parametros)

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(f"""
                SELECT c.id
                FROM recrutamento_candidatos c
                JOIN recrutamento_candidaturas ca ON ca.candidato_id = c.id
                WHERE {" AND ".join(condicoes)}
                LIMIT 1
            """, tuple(parametros))
            if cursor.fetchone() is None:
                abort(404)
        finally:
            cursor.close()
            conn.close()

        diretorio = UploadService.resolver_diretorio(
            "app/static/recrutamento_curriculos"
        )
        return send_from_directory(diretorio, nome, as_attachment=True)
