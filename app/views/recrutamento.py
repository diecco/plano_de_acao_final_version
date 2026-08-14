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
        f"({alias}.responsavel_rh_id = %s OR {alias}.criado_por = %s)"
    )
    parametros.extend([usuario_id, usuario_id])


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
