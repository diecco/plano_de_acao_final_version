import re
from datetime import date
from html import escape

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from flask_mail import Message

from app import mail
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

STATUS_VALIDACAO_CLIENTE = {
    "nao_iniciado": "Não iniciado",
    "aguardando_validacao": "Aguardando validação",
    "aprovado": "Aprovado",
    "reprovado": "Reprovado",
}

STATUS_PROPOSTA = {
    "nao_enviada": "Não enviada",
    "enviada": "Enviada",
    "aceita": "Aceita",
    "rejeitada": "Rejeitada",
    "sem_retorno": "Sem retorno",
}

STATUS_EXAME_ADMISSIONAL = {
    "aguardando_agendamento": "Aguardando agendamento",
    "agendado": "Agendado",
    "aguardando_resultado": "Aguardando resultado",
    "concluido": "Concluído",
    "cancelado": "Cancelado",
}

RESULTADOS_EXAME_ADMISSIONAL = {
    "apto": "Apto",
    "inapto": "Inapto",
    "apto_restricao": "Apto com restrição",
}

STATUS_DOCUMENTO_ADMISSIONAL = {
    "pendente": "Pendente",
    "recebido": "Recebido",
    "nao_aplicavel": "Não aplicável",
    "inconsistente": "Com inconsistência",
}

STATUS_CANDIDATURA = {
    "cadastrado": "Cadastrado",
    "em_triagem": "Em triagem",
    "aguardando_entrevista_rh": "Aguardando entrevista RH",
    "aguardando_entrevista_gestor": "Aguardando entrevista do gestor",
    "em_avaliacao": "Em avaliação",
    "stand_by": "Stand-by",
    "reprovado": "Reprovado",
    "aguardando_proposta": "Aguardando proposta",
    "proposta_enviada": "Proposta enviada",
    "proposta_recusada": "Proposta recusada",
    "em_pre_admissao": "Em pré-admissão",
    "aguardando_aso": "Aguardando exame admissional",
    "aguardando_documentos": "Aguardando documentos",
    "liberado_admissao": "Liberado para admissão",
    "encerrado": "Cancelado pelo RH",
    "desistente": "Candidato declinou",
}

STATUS_CANDIDATURA_ENCERRADA = ("encerrado", "desistente")
STATUS_CANDIDATURA_BLOQUEADA = (
    "encerrado", "desistente", "liberado_admissao"
)


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
    centro_custos_id = session.get("centro_custos_id")

    if perfil in ("administrador", "avancado"):
        return
    if perfil == "intermediario":
        condicoes.append(f"{alias}.centro_custos_id = %s")
        parametros.append(centro_custos_id)
        return

    condicoes.append(f"{alias}.centro_custos_id = %s")
    parametros.append(centro_custos_id)


def _pode_gerenciar_candidatura(candidatura):
    if session.get("perfil") in ("administrador", "avancado"):
        return True
    return candidatura["centro_custos_id"] == session.get("centro_custos_id")


def _etapas_obrigatorias_concluidas(etapas):
    return all(
        not etapa["obrigatoria"]
        or etapa["status"] in ("realizada", "dispensada")
        for etapa in etapas
    )


def _validar_candidatura_aberta(candidatura):
    if candidatura["status"] in STATUS_CANDIDATURA_BLOQUEADA:
        raise ValueError("Esta candidatura já foi encerrada e não aceita alterações.")


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
            status_candidatura=STATUS_CANDIDATURA,
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
                if cargo_id:
                    cargo_selecionado = next(
                        (cargo for cargo in cargos if cargo["id"] == cargo_id),
                        None,
                    )
                    if cargo_selecionado is None:
                        raise ValueError("Selecione um cargo pretendido válido.")
                    cargo_pretendido = cargo_selecionado["nome"]
                origem = (request.form.get("origem") or "").strip()
                detalhe_origem = (request.form.get("detalhe_origem") or "").strip() or None
                teste_pratico = (request.form.get("exige_teste_pratico") or "").strip()
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
                SELECT pc.*, u.nome AS autor_nome
                FROM recrutamento_pareceres_complementares pc
                JOIN usuarios u ON u.id = pc.autor_id
                JOIN recrutamento_etapas e ON e.id = pc.etapa_id
                WHERE e.candidatura_id = %s
                ORDER BY pc.criado_em, pc.id
            """, (candidatura_id,))
            complementos_por_etapa = {}
            for complemento in cursor.fetchall():
                complementos_por_etapa.setdefault(
                    complemento["etapa_id"], []
                ).append(complemento)
            cursor.execute("""
                SELECT h.*,
                       DATE_SUB(h.criado_em, INTERVAL 3 HOUR) AS criado_em,
                       u.nome AS usuario_nome
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
                ORDER BY nome
            """, (candidatura["centro_custos_id"],))
            avaliadores = cursor.fetchall()
            cursor.execute("SELECT id, nome FROM cargos WHERE ativo = 1 ORDER BY nome")
            cargos = cursor.fetchall()
            cursor.execute("""
                SELECT ch.*, u.nome AS arquivado_por_nome
                FROM recrutamento_ciclos_historico ch
                JOIN usuarios u ON u.id = ch.arquivado_por
                WHERE ch.candidatura_id = %s
                ORDER BY ch.numero_ciclo DESC
            """, (candidatura_id,))
            ciclos_anteriores = cursor.fetchall()
            etapas_ciclos = {}
            complementos_ciclos = {}
            if ciclos_anteriores:
                ids_ciclos = [ciclo["id"] for ciclo in ciclos_anteriores]
                placeholders = ", ".join(["%s"] * len(ids_ciclos))
                cursor.execute(f"""
                    SELECT eh.*, u.nome AS avaliador_nome
                    FROM recrutamento_etapas_historico eh
                    LEFT JOIN usuarios u ON u.id = eh.avaliador_id
                    WHERE eh.ciclo_historico_id IN ({placeholders})
                    ORDER BY eh.ordem, eh.id
                """, tuple(ids_ciclos))
                etapas_anteriores = cursor.fetchall()
                for etapa_anterior in etapas_anteriores:
                    etapas_ciclos.setdefault(
                        etapa_anterior["ciclo_historico_id"], []
                    ).append(etapa_anterior)
                ids_etapas_historicas = [etapa["id"] for etapa in etapas_anteriores]
                if ids_etapas_historicas:
                    placeholders = ", ".join(["%s"] * len(ids_etapas_historicas))
                    cursor.execute(f"""
                        SELECT ch.*, u.nome AS autor_nome
                        FROM recrutamento_complementos_historico ch
                        LEFT JOIN usuarios u ON u.id = ch.autor_id
                        WHERE ch.etapa_historico_id IN ({placeholders})
                        ORDER BY ch.criado_em, ch.id
                    """, tuple(ids_etapas_historicas))
                    for complemento_anterior in cursor.fetchall():
                        complementos_ciclos.setdefault(
                            complemento_anterior["etapa_historico_id"], []
                        ).append(complemento_anterior)
            cursor.execute("""
                SELECT vc.*
                FROM recrutamento_validacoes_cliente vc
                WHERE vc.candidatura_id = %s
                ORDER BY vc.id DESC
                LIMIT 1
            """, (candidatura_id,))
            pre_cadastro_cliente = cursor.fetchone()
            cursor.execute("""
                SELECT * FROM recrutamento_propostas
                WHERE candidatura_id = %s
                ORDER BY id DESC LIMIT 1
            """, (candidatura_id,))
            proposta = cursor.fetchone()
            cursor.execute("""
                SELECT * FROM recrutamento_pre_admissao
                WHERE candidatura_id = %s
            """, (candidatura_id,))
            pre_admissao = cursor.fetchone()
            documentos_admissionais = []
            if pre_admissao:
                cursor.execute("""
                    SELECT dc.*, td.nome
                    FROM recrutamento_documentos_candidatura dc
                    JOIN recrutamento_tipos_documento td
                      ON td.id = dc.tipo_documento_id
                    WHERE dc.candidatura_id = %s
                    ORDER BY td.nome
                """, (candidatura_id,))
                documentos_admissionais = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
        pode_gerenciar_base = _pode_gerenciar_candidatura(candidatura)
        candidatura_encerrada = candidatura["status"] in STATUS_CANDIDATURA_BLOQUEADA
        return render_template(
            "recrutamento_candidatura_detalhe.html",
            candidatura=candidatura, etapas=etapas, historico=historico,
            avaliadores=avaliadores, cargos=cargos, resultados=RESULTADOS_ETAPA,
            complementos_por_etapa=complementos_por_etapa,
            etapas_concluidas=_etapas_obrigatorias_concluidas(etapas),
            origens=ORIGENS_CANDIDATURA,
            pode_gerenciar=pode_gerenciar_base and not candidatura_encerrada,
            pode_encerrar=(
                pode_gerenciar_base
                and candidatura["status"] not in STATUS_CANDIDATURA_ENCERRADA
            ),
            candidatura_encerrada=candidatura_encerrada,
            status_candidatura=STATUS_CANDIDATURA,
            hoje=date.today(),
            ciclos_anteriores=ciclos_anteriores,
            etapas_ciclos=etapas_ciclos,
            complementos_ciclos=complementos_ciclos,
            pre_cadastro_cliente=pre_cadastro_cliente,
            status_validacao_cliente=STATUS_VALIDACAO_CLIENTE,
            proposta=proposta,
            status_proposta=STATUS_PROPOSTA,
            pre_admissao=pre_admissao,
            status_exame_admissional=STATUS_EXAME_ADMISSIONAL,
            resultados_exame_admissional=RESULTADOS_EXAME_ADMISSIONAL,
            documentos_admissionais=documentos_admissionais,
            status_documento_admissional=STATUS_DOCUMENTO_ADMISSIONAL,
        )

    @blueprint.route("/recrutamento/candidaturas/<int:candidatura_id>/encerrar", methods=["POST"])
    @login_required
    @module_required("acesso_recrutamento")
    def encerrar_candidatura_recrutamento(candidatura_id):
        tipo = (request.form.get("tipo_encerramento") or "").strip()
        justificativa = (request.form.get("justificativa") or "").strip()
        encerramentos = {
            "desistencia": (
                "desistente",
                "candidato_declinou",
                "O candidato declinou da continuidade do processo seletivo.",
            ),
            "cancelamento_rh": (
                "encerrado",
                "processo_cancelado_rh",
                "O processo de recrutamento foi cancelado pelo RH.",
            ),
        }
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM recrutamento_candidaturas WHERE id = %s FOR UPDATE",
                (candidatura_id,),
            )
            candidatura = cursor.fetchone()
            if candidatura is None:
                abort(404)
            if not _pode_gerenciar_candidatura(candidatura):
                abort(403)
            if candidatura["status"] in STATUS_CANDIDATURA_ENCERRADA:
                raise ValueError("Esta candidatura já possui um encerramento registrado.")
            if tipo not in encerramentos:
                raise ValueError("Selecione o motivo do encerramento.")
            if len(justificativa) < 10:
                raise ValueError("Informe uma justificativa com pelo menos 10 caracteres.")

            novo_status, evento, descricao = encerramentos[tipo]
            cursor.execute("""
                UPDATE recrutamento_candidaturas
                SET status = %s, encerrado_em = NOW()
                WHERE id = %s
            """, (novo_status, candidatura_id))
            cursor.execute("""
                INSERT INTO recrutamento_historico
                    (candidatura_id, evento, descricao, usuario_id)
                VALUES (%s, %s, %s, %s)
            """, (
                candidatura_id,
                evento,
                f"{descricao} Justificativa: {justificativa}",
                session["usuario_id"],
            ))
            conn.commit()
            flash("Candidatura encerrada com sucesso.", "success")
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "danger")
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for(
            "main.detalhe_candidatura_recrutamento",
            candidatura_id=candidatura_id,
        ))

    @blueprint.route("/recrutamento/candidaturas/<int:candidatura_id>/reaproveitar", methods=["POST"])
    @login_required
    @module_required("acesso_recrutamento")
    def reaproveitar_candidatura_recrutamento(candidatura_id):
        cargo_id = request.form.get("cargo_id", type=int)
        cargo_pretendido = (request.form.get("cargo_pretendido") or "").strip()
        teste_pratico = (request.form.get("exige_teste_pratico") or "").strip()
        justificativa = (request.form.get("justificativa") or "").strip()
        etapas_reabrir = {
            int(valor) for valor in request.form.getlist("etapas_reabrir")
            if valor.isdigit()
        }
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM recrutamento_candidaturas WHERE id = %s FOR UPDATE",
                (candidatura_id,),
            )
            candidatura = cursor.fetchone()
            if candidatura is None:
                abort(404)
            if not _pode_gerenciar_candidatura(candidatura):
                abort(403)
            if not candidatura.get("decisao_resultado"):
                raise ValueError(
                    "Conclua o ciclo atual com uma decisão consolidada antes de "
                    "reaproveitar a candidatura."
                )
            if not cargo_pretendido:
                raise ValueError("Informe o cargo da nova oportunidade.")
            if teste_pratico not in TESTES_PRATICOS:
                raise ValueError("Selecione a regra de teste prático do novo ciclo.")
            if len(justificativa) < 10:
                raise ValueError(
                    "Informe uma justificativa com pelo menos 10 caracteres."
                )
            if cargo_id:
                cursor.execute(
                    "SELECT id FROM cargos WHERE id = %s AND ativo = 1",
                    (cargo_id,),
                )
                if cursor.fetchone() is None:
                    raise ValueError("Selecione um cargo ativo.")

            cursor.execute(
                "SELECT * FROM recrutamento_etapas WHERE candidatura_id = %s ORDER BY ordem, id FOR UPDATE",
                (candidatura_id,),
            )
            etapas_atuais = cursor.fetchall()
            ids_etapas = {etapa["id"] for etapa in etapas_atuais}
            if not etapas_reabrir.issubset(ids_etapas):
                raise ValueError("Foi selecionada uma etapa inválida para reabertura.")

            cursor.execute(
                "SELECT COALESCE(MAX(numero_ciclo), 0) + 1 AS numero FROM recrutamento_ciclos_historico WHERE candidatura_id = %s",
                (candidatura_id,),
            )
            numero_ciclo = cursor.fetchone()["numero"]
            cursor.execute("""
                SELECT cliente, status, observacao_operacional
                FROM recrutamento_validacoes_cliente
                WHERE candidatura_id = %s
                ORDER BY id DESC LIMIT 1
            """, (candidatura_id,))
            pre_cadastro_atual = cursor.fetchone() or {}
            cursor.execute("""
                SELECT status, enviada_em FROM recrutamento_propostas
                WHERE candidatura_id = %s ORDER BY id DESC LIMIT 1
            """, (candidatura_id,))
            proposta_atual = cursor.fetchone() or {}
            cursor.execute("""
                SELECT aso_status, aso_resultado, aso_data_prevista,
                       documentos_status
                FROM recrutamento_pre_admissao WHERE candidatura_id = %s
            """, (candidatura_id,))
            pre_admissao_atual = cursor.fetchone() or {}
            cursor.execute("""
                INSERT INTO recrutamento_ciclos_historico (
                    candidatura_id, numero_ciclo, cargo_id, cargo_pretendido,
                    exige_teste_pratico, status, decisao_resultado,
                    decisao_parecer, decisao_por,
                    decisao_em, justificativa_reaproveitamento, arquivado_por,
                    pre_cadastro_cliente, pre_cadastro_status,
                    pre_cadastro_observacao, proposta_status,
                    proposta_enviada_em, aso_status, aso_resultado,
                    aso_data_prevista, documentos_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                          %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                candidatura_id, numero_ciclo, candidatura.get("cargo_id"),
                candidatura["cargo_pretendido"],
                candidatura["exige_teste_pratico"], candidatura["status"],
                candidatura.get("decisao_resultado"),
                candidatura.get("decisao_parecer"),
                candidatura.get("decisao_por"), candidatura.get("decisao_em"),
                justificativa, session["usuario_id"],
                pre_cadastro_atual.get("cliente"),
                pre_cadastro_atual.get("status"),
                pre_cadastro_atual.get("observacao_operacional"),
                proposta_atual.get("status"),
                proposta_atual.get("enviada_em"),
                pre_admissao_atual.get("aso_status"),
                pre_admissao_atual.get("aso_resultado"),
                pre_admissao_atual.get("aso_data_prevista"),
                pre_admissao_atual.get("documentos_status"),
            ))
            ciclo_historico_id = cursor.lastrowid
            cursor.execute("""
                INSERT INTO recrutamento_etapas_historico (
                    ciclo_historico_id, etapa_origem_id, tipo, nome, ordem,
                    obrigatoria, papel_responsavel, avaliador_id, status,
                    resultado, parecer, restricao, motivo_dispensa,
                    data_prevista, realizada_em, registrado_por,
                    criado_em, atualizado_em
                )
                SELECT %s, id, tipo, nome, ordem, obrigatoria,
                       papel_responsavel, avaliador_id, status, resultado,
                       parecer, restricao, motivo_dispensa, data_prevista,
                       realizada_em, registrado_por, criado_em, atualizado_em
                FROM recrutamento_etapas WHERE candidatura_id = %s
            """, (ciclo_historico_id, candidatura_id))

            cursor.execute("""
                INSERT INTO recrutamento_complementos_historico (
                    etapa_historico_id, parecer, autor_id, criado_em
                )
                SELECT eh.id, pc.parecer, pc.autor_id, pc.criado_em
                FROM recrutamento_pareceres_complementares pc
                JOIN recrutamento_etapas_historico eh
                  ON eh.etapa_origem_id = pc.etapa_id
                 AND eh.ciclo_historico_id = %s
            """, (ciclo_historico_id,))

            etapa_pratica = next(
                (etapa for etapa in etapas_atuais if etapa["tipo"] == "teste_pratico"),
                None,
            )
            if teste_pratico == "nao_aplicavel" and etapa_pratica:
                cursor.execute(
                    "DELETE FROM recrutamento_pareceres_complementares WHERE etapa_id = %s",
                    (etapa_pratica["id"],),
                )
                cursor.execute(
                    "DELETE FROM recrutamento_etapas WHERE id = %s",
                    (etapa_pratica["id"],),
                )
            elif teste_pratico != "nao_aplicavel" and etapa_pratica is None:
                cursor.execute("""
                    INSERT INTO recrutamento_etapas (
                        candidatura_id, tipo, nome, ordem,
                        obrigatoria, papel_responsavel
                    ) VALUES (%s, 'teste_pratico', 'Teste prático', 3, %s, 'gestor')
                """, (
                    candidatura_id,
                    1 if teste_pratico == "obrigatorio" else 0,
                ))
            elif etapa_pratica:
                cursor.execute(
                    "UPDATE recrutamento_etapas SET obrigatoria = %s WHERE id = %s",
                    (1 if teste_pratico == "obrigatorio" else 0, etapa_pratica["id"]),
                )

            for etapa_id in etapas_reabrir:
                cursor.execute(
                    "DELETE FROM recrutamento_pareceres_complementares WHERE etapa_id = %s",
                    (etapa_id,),
                )
                cursor.execute("""
                    UPDATE recrutamento_etapas
                    SET avaliador_id = NULL, status = 'pendente', resultado = NULL,
                        parecer = NULL, restricao = NULL, motivo_dispensa = NULL,
                        data_prevista = NULL, realizada_em = NULL,
                        registrado_por = NULL
                    WHERE id = %s AND candidatura_id = %s
                """, (etapa_id, candidatura_id))

            cursor.execute("""
                UPDATE recrutamento_candidaturas
                SET cargo_id = %s, cargo_pretendido = %s,
                    exige_teste_pratico = %s,
                    status = 'em_avaliacao', decisao_resultado = NULL,
                    decisao_parecer = NULL, decisao_por = NULL,
                    decisao_em = NULL, encerrado_em = NULL
                WHERE id = %s
            """, (cargo_id, cargo_pretendido, teste_pratico, candidatura_id))
            cursor.execute(
                "DELETE FROM recrutamento_validacoes_cliente WHERE candidatura_id = %s",
                (candidatura_id,),
            )
            cursor.execute(
                "DELETE FROM recrutamento_documentos_candidatura WHERE candidatura_id = %s",
                (candidatura_id,),
            )
            cursor.execute(
                "DELETE FROM recrutamento_pre_admissao WHERE candidatura_id = %s",
                (candidatura_id,),
            )
            cursor.execute(
                "DELETE FROM recrutamento_propostas WHERE candidatura_id = %s",
                (candidatura_id,),
            )
            cursor.execute("""
                INSERT INTO recrutamento_historico
                    (candidatura_id, evento, descricao, usuario_id)
                VALUES (%s, 'candidatura_reaproveitada', %s, %s)
            """, (
                candidatura_id,
                f"Candidatura reaproveitada de {candidatura['cargo_pretendido']} "
                f"para {cargo_pretendido}. {len(etapas_reabrir)} etapa(s) reaberta(s). "
                f"Justificativa: {justificativa}",
                session["usuario_id"],
            ))
            conn.commit()
            flash(
                "Novo ciclo iniciado. O ciclo anterior foi preservado no histórico.",
                "success",
            )
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "danger")
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for(
            "main.detalhe_candidatura_recrutamento",
            candidatura_id=candidatura_id,
        ))

    @blueprint.route("/recrutamento/candidaturas/<int:candidatura_id>/pre-cadastro-cliente", methods=["POST"])
    @login_required
    @module_required("acesso_recrutamento")
    def salvar_pre_cadastro_cliente_recrutamento(candidatura_id):
        cliente = (request.form.get("cliente") or "").strip()
        status = (request.form.get("status") or "").strip()
        observacao = (request.form.get("observacao") or "").strip() or None
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM recrutamento_candidaturas WHERE id = %s",
                (candidatura_id,),
            )
            candidatura = cursor.fetchone()
            if candidatura is None:
                abort(404)
            if not _pode_gerenciar_candidatura(candidatura):
                abort(403)
            _validar_candidatura_aberta(candidatura)
            if candidatura["status"] in ("cadastrado", "em_triagem"):
                raise ValueError("Inicie a seleção antes do pré-cadastro no cliente.")
            if not cliente:
                raise ValueError("Informe o cliente.")
            if status not in STATUS_VALIDACAO_CLIENTE:
                raise ValueError("Selecione uma situação válida.")
            if status == "reprovado" and not observacao:
                raise ValueError("Informe o motivo operacional da reprovação.")

            cursor.execute("""
                SELECT id FROM recrutamento_validacoes_cliente
                WHERE candidatura_id = %s ORDER BY id DESC LIMIT 1 FOR UPDATE
            """, (candidatura_id,))
            registro = cursor.fetchone()
            if registro:
                cursor.execute("""
                    UPDATE recrutamento_validacoes_cliente
                    SET cliente = %s, status = %s,
                        observacao_operacional = %s, atualizado_por = %s
                    WHERE id = %s
                """, (
                    cliente, status, observacao, session["usuario_id"],
                    registro["id"],
                ))
            else:
                cursor.execute("""
                    INSERT INTO recrutamento_validacoes_cliente (
                        candidatura_id, cliente, documento_identidade,
                        obrigatoria, status, observacao_operacional, criado_por
                    ) VALUES (%s, %s, '-', 1, %s, %s, %s)
                """, (
                    candidatura_id, cliente, status, observacao,
                    session["usuario_id"],
                ))
            cursor.execute("""
                INSERT INTO recrutamento_historico
                    (candidatura_id, evento, descricao, usuario_id)
                VALUES (%s, 'pre_cadastro_cliente', %s, %s)
            """, (
                candidatura_id,
                f"Pré-cadastro no cliente {cliente}: "
                f"{STATUS_VALIDACAO_CLIENTE[status]}.",
                session["usuario_id"],
            ))
            conn.commit()
            flash("Etapa de pré-cadastro atualizada.", "success")
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "danger")
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for(
            "main.detalhe_candidatura_recrutamento",
            candidatura_id=candidatura_id,
        ))

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
            _validar_candidatura_aberta(candidatura)
            if candidatura["status"] not in ("cadastrado", "em_triagem"):
                raise ValueError("A seleção desta candidatura já foi iniciada.")
            cursor.execute("""
                UPDATE recrutamento_etapas SET status = 'pendente'
                WHERE candidatura_id = %s
            """, (candidatura_id,))
            cursor.execute("UPDATE recrutamento_candidaturas SET status = 'em_avaliacao' WHERE id = %s", (candidatura_id,))
            cursor.execute("""
                INSERT INTO recrutamento_historico
                    (candidatura_id, evento, descricao, usuario_id)
                VALUES (%s, 'selecao_iniciada', %s, %s)
            """, (candidatura_id, "Seleção iniciada com etapas independentes e paralelas.", session["usuario_id"]))
            conn.commit()
            flash("Seleção iniciada. As etapas já podem ser conduzidas em paralelo.", "success")
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
        prazo_texto = (request.form.get("data_prevista") or "").strip()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM recrutamento_candidaturas WHERE id = %s", (candidatura_id,))
            candidatura = cursor.fetchone()
            if candidatura is None:
                abort(404)
            if not _pode_gerenciar_candidatura(candidatura):
                abort(403)
            _validar_candidatura_aberta(candidatura)
            if candidatura["status"] in ("cadastrado", "em_triagem"):
                raise ValueError("Inicie a seleção antes de atribuir as avaliações.")
            cursor.execute("SELECT * FROM recrutamento_etapas WHERE id = %s AND candidatura_id = %s FOR UPDATE", (etapa_id, candidatura_id))
            etapa = cursor.fetchone()
            if etapa is None:
                abort(404)
            if etapa["tipo"] == "entrevista_comportamental":
                raise ValueError("A entrevista comportamental pertence ao RH responsável.")
            if etapa.get("avaliador_id"):
                raise ValueError(
                    "Esta avaliação já foi atribuída e não pode ser reatribuída."
                )
            if not prazo_texto:
                raise ValueError("Informe o prazo para conclusão da avaliação.")
            try:
                prazo = date.fromisoformat(prazo_texto)
            except ValueError as exc:
                raise ValueError("Informe um prazo válido para a avaliação.") from exc
            if prazo < date.today():
                raise ValueError("O prazo da avaliação não pode ser anterior à data atual.")
            cursor.execute("""
                SELECT id, nome, email FROM usuarios
                WHERE id = %s AND ativo = 1 AND tem_acesso_sistema = 1
                  AND centro_custos_id = %s
            """, (avaliador_id, candidatura["centro_custos_id"]))
            avaliador = cursor.fetchone()
            if avaliador is None:
                raise ValueError("Selecione um avaliador habilitado do mesmo centro de custos.")
            cursor.execute("""
                UPDATE recrutamento_etapas
                SET avaliador_id = %s, data_prevista = %s, status = 'pendente'
                WHERE id = %s
            """, (avaliador_id, prazo, etapa_id))
            cursor.execute("""
                INSERT INTO recrutamento_historico
                    (candidatura_id, evento, descricao, usuario_id)
                VALUES (%s, 'etapa_atribuida', %s, %s)
            """, (
                candidatura_id,
                f"{etapa['nome']} atribuída a {avaliador['nome']} com prazo até "
                f"{prazo.strftime('%d/%m/%Y')}.",
                session["usuario_id"],
            ))
            conn.commit()
            flash("Avaliador definido com sucesso.", "success")

            if avaliador.get("email"):
                try:
                    cursor.execute("""
                        SELECT c.nome AS candidato_nome, ca.cargo_pretendido
                        FROM recrutamento_candidaturas ca
                        JOIN recrutamento_candidatos c ON c.id = ca.candidato_id
                        WHERE ca.id = %s
                    """, (candidatura_id,))
                    dados_email = cursor.fetchone() or {}
                    link_avaliacao = url_for(
                        "main.detalhe_minha_avaliacao_recrutamento",
                        etapa_id=etapa_id,
                        _external=True,
                    )
                    msg = Message(
                        subject="Nova avaliação atribuída a você - TrackPlan",
                        recipients=[avaliador["email"]],
                    )
                    msg.html = f"""
                    <div style="font-family:Arial,sans-serif;font-size:15px;color:#343a40;">
                        <div style="text-align:center;">
                            <img src="https://www.trackplan.com.br/imagens/barra_email.png"
                                 alt="TrackPlan" style="height:50px;margin-bottom:20px;">
                        </div>
                        <p>Olá <strong>{escape(avaliador['nome'])}</strong>,</p>
                        <p>Uma nova avaliação de candidato foi atribuída a você no TrackPlan.</p>
                        <p>
                            <strong>Etapa:</strong> {escape(etapa['nome'])}<br>
                            <strong>Candidato:</strong> {escape(dados_email.get('candidato_nome') or '-')}<br>
                            <strong>Cargo pretendido:</strong> {escape(dados_email.get('cargo_pretendido') or '-')}<br>
                            <strong>Prazo:</strong> {prazo.strftime('%d/%m/%Y')}
                        </p>
                        <p>Acesse a área restrita da avaliação para consultar as informações permitidas e registrar seu parecer.</p>
                        <p>
                            <a href="{link_avaliacao}"
                               style="display:inline-block;background:#ea6a23;color:#fff;padding:10px 18px;text-decoration:none;border-radius:5px;">
                                Abrir avaliação
                            </a>
                        </p>
                        <p style="font-size:13px;color:#666;">Equipe TrackPlan</p>
                    </div>
                    """
                    mail.send(msg)
                except Exception:
                    current_app.logger.exception(
                        "Falha ao enviar notificação da etapa de recrutamento %s.",
                        etapa_id,
                    )
                    flash(
                        "A atribuição foi salva, mas o e-mail de notificação não pôde ser enviado.",
                        "warning",
                    )
            else:
                flash(
                    "A atribuição foi salva, mas o avaliador não possui e-mail cadastrado.",
                    "warning",
                )
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
            avaliacao_rh = (
                etapa["tipo"] == "entrevista_comportamental"
                and session.get("acesso_recrutamento")
                and _pode_gerenciar_candidatura(candidatura)
            )
            avaliacao_atribuida = etapa["avaliador_id"] == session.get("usuario_id")
            if session.get("perfil") != "administrador" and not avaliacao_rh and not avaliacao_atribuida:
                abort(403)
            _validar_candidatura_aberta(candidatura)
            if candidatura["status"] in ("reprovado", "encerrado", "desistente"):
                raise ValueError("Esta candidatura não aceita novas avaliações.")
            if candidatura.get("decisao_resultado"):
                raise ValueError("A decisão consolidada já foi registrada.")
            if candidatura["status"] in ("cadastrado", "em_triagem"):
                raise ValueError("A seleção ainda não foi iniciada.")
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
            cursor.execute("UPDATE recrutamento_candidaturas SET status = 'em_avaliacao' WHERE id = %s", (candidatura_id,))
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
        if etapa and etapa["tipo"] != "entrevista_comportamental":
            return redirect(url_for("main.detalhe_minha_avaliacao_recrutamento", etapa_id=etapa_id))
        return redirect(url_for("main.detalhe_candidatura_recrutamento", candidatura_id=candidatura_id))

    @blueprint.route("/recrutamento/candidaturas/<int:candidatura_id>/etapas/<int:etapa_id>/complementar", methods=["POST"])
    @login_required
    @module_required("acesso_recrutamento")
    def complementar_parecer_recrutamento(candidatura_id, etapa_id):
        parecer = (request.form.get("parecer_complementar") or "").strip()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM recrutamento_candidaturas WHERE id = %s", (candidatura_id,))
            candidatura = cursor.fetchone()
            if candidatura is None:
                abort(404)
            if not _pode_gerenciar_candidatura(candidatura):
                abort(403)
            _validar_candidatura_aberta(candidatura)
            cursor.execute("""
                SELECT * FROM recrutamento_etapas
                WHERE id = %s AND candidatura_id = %s
            """, (etapa_id, candidatura_id))
            etapa = cursor.fetchone()
            if etapa is None:
                abort(404)
            if etapa["tipo"] != "entrevista_comportamental" or etapa["status"] != "realizada":
                raise ValueError("O complemento exige um parecer comportamental concluído.")
            if not parecer:
                raise ValueError("Informe o parecer complementar.")
            cursor.execute("""
                INSERT INTO recrutamento_pareceres_complementares
                    (etapa_id, parecer, autor_id)
                VALUES (%s, %s, %s)
            """, (etapa_id, parecer, session["usuario_id"]))
            cursor.execute("""
                INSERT INTO recrutamento_historico
                    (candidatura_id, evento, descricao, usuario_id)
                VALUES (%s, 'parecer_complementar', %s, %s)
            """, (candidatura_id, "Parecer complementar do RH registrado.", session["usuario_id"]))
            conn.commit()
            flash("Parecer complementar registrado e preservado no histórico.", "success")
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

    @blueprint.route("/recrutamento/candidaturas/<int:candidatura_id>/decidir", methods=["POST"])
    @login_required
    @module_required("acesso_recrutamento")
    def decidir_candidatura_recrutamento(candidatura_id):
        resultado = (request.form.get("decisao_resultado") or "").strip()
        parecer = (request.form.get("decisao_parecer") or "").strip()
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM recrutamento_candidaturas WHERE id = %s FOR UPDATE", (candidatura_id,))
            candidatura = cursor.fetchone()
            if candidatura is None:
                abort(404)
            if not _pode_gerenciar_candidatura(candidatura):
                abort(403)
            _validar_candidatura_aberta(candidatura)
            if candidatura.get("decisao_resultado"):
                raise ValueError("A decisão consolidada já foi registrada.")
            cursor.execute("SELECT obrigatoria, status FROM recrutamento_etapas WHERE candidatura_id = %s", (candidatura_id,))
            if not _etapas_obrigatorias_concluidas(cursor.fetchall()):
                raise ValueError("Conclua todas as etapas obrigatórias antes da decisão final.")
            cursor.execute("""
                SELECT status FROM recrutamento_validacoes_cliente
                WHERE candidatura_id = %s ORDER BY id DESC LIMIT 1
            """, (candidatura_id,))
            pre_cadastro = cursor.fetchone()
            if pre_cadastro is None or pre_cadastro["status"] == "nao_iniciado":
                raise ValueError(
                    "Inicie o pré-cadastro no cliente antes da decisão consolidada."
                )
            if resultado not in RESULTADOS_ETAPA:
                raise ValueError("Selecione uma decisão válida.")
            if pre_cadastro["status"] == "reprovado" and resultado != "reprovado":
                raise ValueError(
                    "O cliente reprovou o pré-cadastro; a decisão consolidada "
                    "deve ser Reprovado."
                )
            if not parecer:
                raise ValueError("A justificativa da decisão consolidada é obrigatória.")
            novo_status = {
                "aprovado": "aguardando_proposta",
                "aprovado_restricao": "aguardando_proposta",
                "reprovado": "reprovado",
                "stand_by": "stand_by",
            }[resultado]
            cursor.execute("""
                UPDATE recrutamento_candidaturas
                SET status = %s, decisao_resultado = %s, decisao_parecer = %s,
                    decisao_por = %s, decisao_em = NOW()
                WHERE id = %s
            """, (novo_status, resultado, parecer, session["usuario_id"], candidatura_id))
            cursor.execute("""
                INSERT INTO recrutamento_historico
                    (candidatura_id, evento, descricao, usuario_id)
                VALUES (%s, 'decisao_consolidada', %s, %s)
            """, (candidatura_id, f"Decisão consolidada: {RESULTADOS_ETAPA[resultado]}.", session["usuario_id"]))
            conn.commit()
            flash("Decisão consolidada registrada com sucesso.", "success")
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

    @blueprint.route("/recrutamento/candidaturas/<int:candidatura_id>/proposta", methods=["POST"])
    @login_required
    @module_required("acesso_recrutamento")
    def salvar_proposta_recrutamento(candidatura_id):
        acao = (request.form.get("acao") or "").strip()
        status = (request.form.get("status") or "").strip()
        data_envio = request.form.get("data_envio") or None
        observacoes = (request.form.get("observacoes") or "").strip() or None
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM recrutamento_candidaturas WHERE id = %s FOR UPDATE",
                (candidatura_id,),
            )
            candidatura = cursor.fetchone()
            if candidatura is None:
                abort(404)
            if not _pode_gerenciar_candidatura(candidatura):
                abort(403)
            _validar_candidatura_aberta(candidatura)
            if candidatura.get("decisao_resultado") not in (
                "aprovado", "aprovado_restricao"
            ):
                raise ValueError(
                    "A proposta exige decisão consolidada favorável do RH."
                )
            if candidatura["status"] == "liberado_admissao":
                raise ValueError("A pré-admissão já foi concluída.")
            cursor.execute("""
                SELECT * FROM recrutamento_propostas
                WHERE candidatura_id = %s ORDER BY id DESC LIMIT 1 FOR UPDATE
            """, (candidatura_id,))
            proposta = cursor.fetchone()
            status_anterior = proposta["status"] if proposta else "nao_enviada"
            if acao in ("registrar_envio", "editar_envio"):
                if acao == "editar_envio" and not proposta:
                    raise ValueError("O envio da proposta ainda não foi registrado.")
                status = status_anterior if acao == "editar_envio" else "enviada"
            elif acao == "registrar_retorno":
                if status not in ("aceita", "rejeitada", "sem_retorno"):
                    raise ValueError("Selecione o retorno do candidato.")
                if not proposta or not proposta.get("enviada_em"):
                    raise ValueError(
                        "Marque a proposta como Enviada antes de registrar o retorno."
                    )
                data_envio = proposta["enviada_em"]
            else:
                raise ValueError("Operação inválida para a proposta.")

            data_envio = data_envio or (proposta or {}).get("enviada_em")
            if not data_envio:
                raise ValueError("Informe a data de envio da proposta.")
            try:
                data_envio_valida = (
                    date.fromisoformat(str(data_envio)[:10]) if data_envio else None
                )
            except ValueError as exc:
                raise ValueError("Informe uma data de envio válida.") from exc
            if data_envio_valida and data_envio_valida > date.today():
                raise ValueError("A data de envio não pode ser futura.")

            if proposta:
                cursor.execute("""
                    UPDATE recrutamento_propostas
                    SET status = %s, enviada_em = %s, observacoes = %s
                    WHERE id = %s
                """, (status, data_envio_valida, observacoes, proposta["id"]))
            else:
                cursor.execute("""
                    INSERT INTO recrutamento_propostas (
                        candidatura_id, status, enviada_em, observacoes, criado_por
                    ) VALUES (%s, %s, %s, %s, %s)
                """, (
                    candidatura_id, status, data_envio_valida, observacoes,
                    session["usuario_id"],
                ))

            status_candidatura = {
                "nao_enviada": "aguardando_proposta",
                "enviada": "proposta_enviada",
                "aceita": "em_pre_admissao",
                "rejeitada": "proposta_recusada",
                "sem_retorno": "proposta_enviada",
            }[status]
            cursor.execute(
                "UPDATE recrutamento_candidaturas SET status = %s WHERE id = %s",
                (status_candidatura, candidatura_id),
            )
            if status == "aceita":
                cursor.execute("""
                    INSERT IGNORE INTO recrutamento_pre_admissao (candidatura_id)
                    VALUES (%s)
                """, (candidatura_id,))
                cursor.execute("""
                    INSERT IGNORE INTO recrutamento_documentos_candidatura (
                        candidatura_id, tipo_documento_id, obrigatorio, status
                    )
                    SELECT %s, id, 1, 'pendente'
                    FROM recrutamento_tipos_documento WHERE ativo = 1
                """, (candidatura_id,))
            elif status in ("rejeitada", "sem_retorno") and status_anterior == "aceita":
                cursor.execute(
                    "DELETE FROM recrutamento_documentos_candidatura WHERE candidatura_id = %s",
                    (candidatura_id,),
                )
                cursor.execute(
                    "DELETE FROM recrutamento_pre_admissao WHERE candidatura_id = %s",
                    (candidatura_id,),
                )
            cursor.execute("""
                INSERT INTO recrutamento_historico
                    (candidatura_id, evento, descricao, usuario_id)
                VALUES (%s, 'proposta_atualizada', %s, %s)
            """, (
                candidatura_id,
                f"Proposta atualizada para {STATUS_PROPOSTA[status]}.",
                session["usuario_id"],
            ))
            conn.commit()
            flash("Situação da proposta atualizada.", "success")
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "danger")
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for(
            "main.detalhe_candidatura_recrutamento",
            candidatura_id=candidatura_id,
        ))

    @blueprint.route("/recrutamento/candidaturas/<int:candidatura_id>/pre-admissao/exame", methods=["POST"])
    @login_required
    @module_required("acesso_recrutamento")
    def salvar_exame_admissional_recrutamento(candidatura_id):
        status = (request.form.get("status") or "").strip()
        data_exame = request.form.get("data_exame") or None
        resultado = (request.form.get("resultado") or "").strip() or None
        observacoes_enviadas = "observacoes" in request.form
        observacoes = (request.form.get("observacoes") or "").strip() or None
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM recrutamento_candidaturas WHERE id = %s",
                (candidatura_id,),
            )
            candidatura = cursor.fetchone()
            if candidatura is None:
                abort(404)
            if not _pode_gerenciar_candidatura(candidatura):
                abort(403)
            _validar_candidatura_aberta(candidatura)
            cursor.execute("""
                SELECT status FROM recrutamento_propostas
                WHERE candidatura_id = %s ORDER BY id DESC LIMIT 1
            """, (candidatura_id,))
            proposta = cursor.fetchone()
            if not proposta or proposta["status"] != "aceita":
                raise ValueError("A pré-admissão exige uma proposta aceita.")
            cursor.execute(
                "SELECT * FROM recrutamento_pre_admissao WHERE candidatura_id = %s",
                (candidatura_id,),
            )
            pre_admissao_atual = cursor.fetchone()
            if pre_admissao_atual is None:
                raise ValueError("A pré-admissão ainda não foi iniciada.")
            if not observacoes_enviadas:
                observacoes = pre_admissao_atual.get("observacoes")
            if status not in STATUS_EXAME_ADMISSIONAL:
                raise ValueError("Selecione uma situação válida para o exame.")
            if status != "agendado":
                data_exame = pre_admissao_atual.get("aso_data_prevista")
            if status == "agendado" and not data_exame:
                raise ValueError("Informe a data do exame admissional.")
            if status in ("aguardando_resultado", "concluido") and not data_exame:
                raise ValueError("Agende o exame antes de avançar esta etapa.")
            try:
                data_exame_valida = (
                    data_exame
                    if isinstance(data_exame, date)
                    else date.fromisoformat(data_exame) if data_exame else None
                )
            except ValueError as exc:
                raise ValueError("Informe uma data válida para o exame.") from exc
            if status == "concluido" and resultado not in RESULTADOS_EXAME_ADMISSIONAL:
                raise ValueError("Informe o resultado do exame concluído.")
            if status != "concluido":
                resultado = None
            if status == "cancelado" and not observacoes:
                raise ValueError("Justifique o cancelamento do exame.")
            if resultado == "apto_restricao" and not observacoes:
                raise ValueError("Registre a orientação operacional da restrição.")
            cursor.execute("""
                UPDATE recrutamento_pre_admissao
                SET aso_status = %s, aso_data_prevista = %s,
                    aso_resultado = %s,
                    aso_resultado_em = CASE WHEN %s = 'concluido' THEN CURDATE() ELSE NULL END,
                    observacoes = %s
                WHERE candidatura_id = %s
            """, (
                status, data_exame_valida, resultado, status,
                observacoes, candidatura_id,
            ))
            cursor.execute("""
                INSERT INTO recrutamento_historico
                    (candidatura_id, evento, descricao, usuario_id)
                VALUES (%s, 'exame_admissional', %s, %s)
            """, (
                candidatura_id,
                f"Exame admissional atualizado para {STATUS_EXAME_ADMISSIONAL[status]}.",
                session["usuario_id"],
            ))
            conn.commit()
            flash("Exame admissional atualizado.", "success")
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "danger")
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for(
            "main.detalhe_candidatura_recrutamento",
            candidatura_id=candidatura_id,
        ))

    @blueprint.route("/recrutamento/candidaturas/<int:candidatura_id>/pre-admissao/documentos", methods=["POST"])
    @login_required
    @module_required("acesso_recrutamento")
    def salvar_documentos_pre_admissao_recrutamento(candidatura_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM recrutamento_candidaturas WHERE id = %s",
                (candidatura_id,),
            )
            candidatura = cursor.fetchone()
            if candidatura is None:
                abort(404)
            if not _pode_gerenciar_candidatura(candidatura):
                abort(403)
            _validar_candidatura_aberta(candidatura)
            cursor.execute("""
                SELECT dc.id FROM recrutamento_documentos_candidatura dc
                WHERE dc.candidatura_id = %s
            """, (candidatura_id,))
            documentos = cursor.fetchall()
            if not documentos:
                raise ValueError("A pré-admissão ainda não foi iniciada.")
            for documento in documentos:
                documento_id = documento["id"]
                status = (request.form.get(f"status_{documento_id}") or "").strip()
                observacao = (
                    request.form.get(f"observacao_{documento_id}") or ""
                ).strip() or None
                if status not in STATUS_DOCUMENTO_ADMISSIONAL:
                    raise ValueError("Foi informada uma situação documental inválida.")
                if status == "inconsistente" and not observacao:
                    raise ValueError(
                        "Descreva a inconsistência do documento correspondente."
                    )
                cursor.execute("""
                    UPDATE recrutamento_documentos_candidatura
                    SET status = %s, observacoes = %s,
                        recebido_em = CASE WHEN %s = 'recebido' THEN NOW() ELSE NULL END,
                        conferido_em = NOW(), conferido_por = %s
                    WHERE id = %s AND candidatura_id = %s
                """, (
                    status, observacao, status, session["usuario_id"],
                    documento_id, candidatura_id,
                ))
            cursor.execute("""
                SELECT COUNT(*) AS pendentes
                FROM recrutamento_documentos_candidatura
                WHERE candidatura_id = %s AND obrigatorio = 1
                  AND status NOT IN ('recebido', 'nao_aplicavel')
            """, (candidatura_id,))
            documentos_status = (
                "completo" if cursor.fetchone()["pendentes"] == 0 else "pendente"
            )
            cursor.execute("""
                UPDATE recrutamento_pre_admissao SET documentos_status = %s
                WHERE candidatura_id = %s
            """, (documentos_status, candidatura_id))
            cursor.execute("""
                INSERT INTO recrutamento_historico
                    (candidatura_id, evento, descricao, usuario_id)
                VALUES (%s, 'documentos_pre_admissao', %s, %s)
            """, (
                candidatura_id, "Checklist documental atualizado.",
                session["usuario_id"],
            ))
            conn.commit()
            flash("Checklist documental atualizado.", "success")
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "danger")
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for(
            "main.detalhe_candidatura_recrutamento",
            candidatura_id=candidatura_id,
        ))

    @blueprint.route("/recrutamento/candidaturas/<int:candidatura_id>/pre-admissao/concluir", methods=["POST"])
    @login_required
    @module_required("acesso_recrutamento")
    def concluir_pre_admissao_recrutamento(candidatura_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM recrutamento_candidaturas WHERE id = %s FOR UPDATE",
                (candidatura_id,),
            )
            candidatura = cursor.fetchone()
            if candidatura is None:
                abort(404)
            if not _pode_gerenciar_candidatura(candidatura):
                abort(403)
            _validar_candidatura_aberta(candidatura)
            cursor.execute("""
                SELECT status FROM recrutamento_propostas
                WHERE candidatura_id = %s ORDER BY id DESC LIMIT 1
            """, (candidatura_id,))
            proposta = cursor.fetchone()
            cursor.execute("""
                SELECT status FROM recrutamento_validacoes_cliente
                WHERE candidatura_id = %s ORDER BY id DESC LIMIT 1
            """, (candidatura_id,))
            validacao_cliente = cursor.fetchone()
            cursor.execute(
                "SELECT * FROM recrutamento_pre_admissao WHERE candidatura_id = %s",
                (candidatura_id,),
            )
            pre_admissao = cursor.fetchone()
            if not proposta or proposta["status"] != "aceita":
                raise ValueError("A proposta ainda não foi aceita.")
            if not validacao_cliente or validacao_cliente["status"] != "aprovado":
                raise ValueError("O pré-cadastro do cliente ainda não foi aprovado.")
            if not pre_admissao or pre_admissao["aso_status"] != "concluido":
                raise ValueError("O exame admissional ainda não foi concluído.")
            if pre_admissao.get("aso_resultado") not in ("apto", "apto_restricao"):
                raise ValueError("O resultado do exame não permite a admissão.")
            if pre_admissao["documentos_status"] != "completo":
                raise ValueError("Conclua o checklist de documentos obrigatórios.")
            cursor.execute("""
                UPDATE recrutamento_pre_admissao
                SET liberado_admissao_em = NOW(), liberado_por = %s
                WHERE candidatura_id = %s
            """, (session["usuario_id"], candidatura_id))
            cursor.execute("""
                UPDATE recrutamento_candidaturas
                SET status = 'liberado_admissao', encerrado_em = NOW()
                WHERE id = %s
            """, (candidatura_id,))
            cursor.execute("""
                INSERT INTO recrutamento_historico
                    (candidatura_id, evento, descricao, usuario_id)
                VALUES (%s, 'pre_admissao_concluida', %s, %s)
            """, (
                candidatura_id, "Candidato liberado para admissão.",
                session["usuario_id"],
            ))
            conn.commit()
            flash("Candidato liberado para admissão.", "success")
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "danger")
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()
            conn.close()
        return redirect(url_for(
            "main.detalhe_candidatura_recrutamento",
            candidatura_id=candidatura_id,
        ))

    @blueprint.route("/recrutamento/minhas-avaliacoes")
    @login_required
    def minhas_avaliacoes_recrutamento():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT e.id AS etapa_id, e.nome AS etapa_nome, e.status,
                       e.resultado, e.data_prevista, e.realizada_em,
                       c.nome AS candidato_nome, c.telefone,
                       ca.cargo_pretendido, ca.status AS candidatura_status,
                       ca.decisao_resultado
                FROM recrutamento_etapas e
                JOIN recrutamento_candidaturas ca ON ca.id = e.candidatura_id
                JOIN recrutamento_candidatos c ON c.id = ca.candidato_id
                WHERE e.avaliador_id = %s
                  AND e.tipo <> 'entrevista_comportamental'
                ORDER BY (e.status = 'realizada'), e.data_prevista, c.nome
            """, (session["usuario_id"],))
            avaliacoes = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
        return render_template("recrutamento_minhas_avaliacoes.html", avaliacoes=avaliacoes, resultados=RESULTADOS_ETAPA)

    @blueprint.route("/recrutamento/minhas-avaliacoes/<int:etapa_id>")
    @login_required
    def detalhe_minha_avaliacao_recrutamento(etapa_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT e.*, ca.cargo_pretendido, ca.decisao_resultado,
                       ca.status AS candidatura_status,
                       c.id AS candidato_id, c.nome AS candidato_nome,
                       c.telefone, c.curriculo_arquivo
                FROM recrutamento_etapas e
                JOIN recrutamento_candidaturas ca ON ca.id = e.candidatura_id
                JOIN recrutamento_candidatos c ON c.id = ca.candidato_id
                WHERE e.id = %s AND e.avaliador_id = %s
                  AND e.tipo <> 'entrevista_comportamental'
            """, (etapa_id, session["usuario_id"]))
            etapa = cursor.fetchone()
            if etapa is None:
                abort(404)
            cursor.execute("""
                SELECT e.parecer, e.restricao, e.realizada_em,
                       u.nome AS autor_nome
                FROM recrutamento_etapas e
                LEFT JOIN usuarios u ON u.id = e.registrado_por
                WHERE e.candidatura_id = %s
                  AND e.tipo = 'entrevista_comportamental'
                  AND e.parecer IS NOT NULL
            """, (etapa["candidatura_id"],))
            parecer_rh = cursor.fetchone()
            cursor.execute("""
                SELECT pc.parecer, pc.criado_em, u.nome AS autor_nome
                FROM recrutamento_pareceres_complementares pc
                JOIN usuarios u ON u.id = pc.autor_id
                JOIN recrutamento_etapas e ON e.id = pc.etapa_id
                WHERE e.candidatura_id = %s
                  AND e.tipo = 'entrevista_comportamental'
                ORDER BY pc.criado_em, pc.id
            """, (etapa["candidatura_id"],))
            pareceres_complementares = cursor.fetchall()
            cursor.execute("""
                SELECT ordem, empresa, cargo, data_inicio, data_fim, emprego_atual
                FROM recrutamento_experiencias
                WHERE candidato_id = %s
                ORDER BY ordem, id
            """, (etapa["candidato_id"],))
            experiencias = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
        return render_template(
            "recrutamento_minha_avaliacao_detalhe.html", etapa=etapa,
            parecer_rh=parecer_rh,
            pareceres_complementares=pareceres_complementares,
            experiencias=experiencias,
            resultados=RESULTADOS_ETAPA,
        )

    @blueprint.route("/recrutamento/minhas-avaliacoes/<int:etapa_id>/curriculo")
    @login_required
    def curriculo_minha_avaliacao_recrutamento(etapa_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT c.curriculo_arquivo
                FROM recrutamento_etapas e
                JOIN recrutamento_candidaturas ca ON ca.id = e.candidatura_id
                JOIN recrutamento_candidatos c ON c.id = ca.candidato_id
                WHERE e.id = %s AND e.avaliador_id = %s
                  AND e.tipo <> 'entrevista_comportamental'
            """, (etapa_id, session["usuario_id"]))
            registro = cursor.fetchone()
            if registro is None or not registro["curriculo_arquivo"]:
                abort(404)
        finally:
            cursor.close()
            conn.close()
        diretorio = UploadService.resolver_diretorio("app/static/recrutamento_curriculos")
        return send_from_directory(diretorio, registro["curriculo_arquivo"], as_attachment=True)

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
