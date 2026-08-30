import json
import hashlib
import os
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import flash, redirect, render_template, request, send_file, send_from_directory, session, url_for

from app.decorators import login_required, module_required
from app.upload_security import UploadService, UploadValidationError
from app.utils.db import get_db_connection


EXTENSOES_RESSARCIMENTO = {"pdf", "png", "jpg", "jpeg"}
TAMANHO_MAXIMO_ARQUIVO = 10 * 1024 * 1024
REGISTROS_POR_PAGINA = 30
ORDENACOES_RESSARCIMENTOS = {
    "numero": "(r.ano * 1000000 + r.sequencial)",
    "ocorrencia": "r.ocorrencia_em",
    "equipamento": "e.codigo_frota",
    "empresa": "emp.nome",
    "funcionario": "fun.nome",
    "situacao": "r.status_processo",
    "faturamento": "r.status_faturamento",
}
PADRAO_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _diretorio_ressarcimento(ressarcimento_id):
    return os.path.join("app", "static", "pcpm_ressarcimentos", str(ressarcimento_id))


def _tamanho_upload(arquivo):
    posicao = arquivo.stream.tell()
    arquivo.stream.seek(0, os.SEEK_END)
    tamanho = arquivo.stream.tell()
    arquivo.stream.seek(posicao)
    return tamanho


def _hash_arquivo(caminho):
    digest = hashlib.sha256()
    with open(caminho, "rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def _normalizar_telefone(valor):
    digitos = re.sub(r"\D", "", valor or "")
    if len(digitos) not in {10, 11}:
        raise ValueError("Informe um telefone válido com DDD.")
    if len(digitos) == 11:
        return f"({digitos[:2]}) {digitos[2:7]}-{digitos[7:]}"
    return f"({digitos[:2]}) {digitos[2:6]}-{digitos[6:]}"


def _salvar_anexo(cursor, ressarcimento_id, arquivo, categoria, prefixo, orcamento_id=None):
    tamanho = _tamanho_upload(arquivo)
    if tamanho <= 0:
        raise ValueError("Um dos arquivos selecionados está vazio.")
    if tamanho > TAMANHO_MAXIMO_ARQUIVO:
        raise ValueError("Cada arquivo deve possuir no máximo 10 MB.")
    nome_original = os.path.basename(arquivo.filename.replace("\\", "/"))[:255]
    diretorio = _diretorio_ressarcimento(ressarcimento_id)
    nome = UploadService.salvar(arquivo, EXTENSOES_RESSARCIMENTO, prefixo=prefixo, diretorio=diretorio)
    caminho_absoluto = os.path.join(UploadService.resolver_diretorio(diretorio), nome)
    cursor.execute(
        """
        INSERT INTO pcpm_ressarcimentos_anexos (
            ressarcimento_id, orcamento_id, categoria, nome_original, nome_armazenado,
            caminho_arquivo, mime_type, tamanho_bytes, hash_sha256, criado_por
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            ressarcimento_id, orcamento_id, categoria, nome_original, nome,
            f"pcpm_ressarcimentos/{ressarcimento_id}/{nome}",
            (arquivo.mimetype or "application/octet-stream")[:120], tamanho,
            _hash_arquivo(caminho_absoluto), session.get("usuario_id"),
        ),
    )
    return nome, diretorio


def _usuario_admin():
    return session.get("perfil") == "administrador"


def _centro_usuario_obrigatorio():
    centro_id = session.get("centro_custos_id")
    if not _usuario_admin() and not centro_id:
        raise ValueError("O usuário não possui centro de custos configurado.")
    return centro_id


def _registrar_historico(cursor, ressarcimento_id, evento, descricao, anteriores=None, posteriores=None, etapa=None):
    cursor.execute(
        """
        INSERT INTO pcpm_ressarcimentos_historico (
            ressarcimento_id, etapa, evento, descricao,
            dados_anteriores, dados_posteriores, usuario_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            ressarcimento_id,
            etapa,
            evento,
            descricao,
            json.dumps(anteriores, ensure_ascii=False, default=str) if anteriores else None,
            json.dumps(posteriores, ensure_ascii=False, default=str) if posteriores else None,
            session.get("usuario_id"),
        ),
    )


def _buscar_processo_autorizado(cursor, ressarcimento_id, for_update=False):
    query = """
        SELECT r.*, cc.codigo AS centro_codigo, cc.descricao AS centro_descricao,
               e.codigo_frota, e.marca, e.modelo,
               emp.nome AS empresa_ocorrencia_nome,
               op.nome AS operador_nome, op.matricula AS operador_matricula,
               fun.nome AS funcionario_nome, fun.matricula AS funcionario_matricula
        FROM pcpm_ressarcimentos r
        JOIN centros_custos cc ON cc.id = r.centro_custos_id
        JOIN pcpm_equipamentos e ON e.id = r.equipamento_id
        JOIN pcpm_empresas emp ON emp.id = r.empresa_ocorrencia_id
        LEFT JOIN pcpm_pessoas op ON op.id = r.operador_id
        JOIN usuarios fun ON fun.id = r.funcionario_id
        WHERE r.id = %s
    """
    params = [ressarcimento_id]
    if not _usuario_admin():
        query += " AND r.centro_custos_id = %s"
        params.append(_centro_usuario_obrigatorio())
    if for_update:
        query += " FOR UPDATE"
    cursor.execute(query, params)
    return cursor.fetchone()


def _buscar_dominios_cadastro(cursor, centro_id):
    cursor.execute(
        """
        SELECT id, codigo_frota, marca, modelo
        FROM pcpm_equipamentos
        WHERE ativo = 1 AND centro_custo_id = %s
        ORDER BY codigo_frota
        """,
        (centro_id,),
    )
    equipamentos = cursor.fetchall()
    cursor.execute("SELECT id, nome FROM pcpm_empresas WHERE ativo = 1 ORDER BY nome")
    empresas = cursor.fetchall()
    cursor.execute(
        """
        SELECT p.id, p.nome, p.matricula, p.empresa_id, emp.nome AS empresa_nome
        FROM pcpm_pessoas p
        LEFT JOIN pcpm_empresas emp ON emp.id = p.empresa_id
        WHERE p.ativo = 1
        ORDER BY p.nome
        """
    )
    operadores = cursor.fetchall()
    cursor.execute(
        """
        SELECT id, nome, matricula
        FROM usuarios
        WHERE ativo = 1 AND centro_custos_id = %s
        ORDER BY nome
        """,
        (centro_id,),
    )
    funcionarios = cursor.fetchall()
    return equipamentos, empresas, operadores, funcionarios


def register_pcpm_ressarcimentos_routes(blueprint):
    @blueprint.route("/pcpm/ressarcimentos")
    @login_required
    @module_required("acesso_pcpm")
    @module_required("acesso_pcpm_ressarcimentos")
    def pcpm_ressarcimentos():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            if request.args.get("limpar"):
                return redirect(url_for("main.pcpm_ressarcimentos"))
            filtros = {
                "busca": (request.args.get("busca") or "").strip(),
                "status": (request.args.get("status") or "").strip(),
                "faturamento": (request.args.get("faturamento") or "").strip(),
                "data_inicio": (request.args.get("data_inicio") or "").strip(),
                "data_fim": (request.args.get("data_fim") or "").strip(),
            }
            sort = (request.args.get("sort") or "ocorrencia").strip()
            order = (request.args.get("order") or "desc").lower().strip()
            if sort not in ORDENACOES_RESSARCIMENTOS:
                sort = "ocorrencia"
            if order not in {"asc", "desc"}:
                order = "desc"
            page = max(request.args.get("page", 1, type=int) or 1, 1)

            base = """
                FROM pcpm_ressarcimentos r
                JOIN pcpm_equipamentos e ON e.id = r.equipamento_id
                JOIN pcpm_empresas emp ON emp.id = r.empresa_ocorrencia_id
                JOIN usuarios fun ON fun.id = r.funcionario_id
                WHERE 1 = 1
            """
            condicoes = []
            params = []
            if not _usuario_admin():
                condicoes.append("r.centro_custos_id = %s")
                params.append(_centro_usuario_obrigatorio())
            if filtros["busca"]:
                condicoes.append("(r.numero LIKE %s OR e.codigo_frota LIKE %s OR emp.nome LIKE %s OR fun.nome LIKE %s)")
                termo = f"%{filtros['busca']}%"
                params.extend([termo, termo, termo, termo])
            if filtros["status"]:
                condicoes.append("r.status_processo = %s")
                params.append(filtros["status"])
            if filtros["faturamento"]:
                condicoes.append("r.status_faturamento = %s")
                params.append(filtros["faturamento"])
            if filtros["data_inicio"]:
                condicoes.append("DATE(r.ocorrencia_em) >= %s")
                params.append(filtros["data_inicio"])
            if filtros["data_fim"]:
                condicoes.append("DATE(r.ocorrencia_em) <= %s")
                params.append(filtros["data_fim"])
            if condicoes:
                base += " AND " + " AND ".join(condicoes)

            cursor.execute("SELECT COUNT(*) AS total " + base, params)
            total_registros = cursor.fetchone()["total"]
            total_paginas = max((total_registros + REGISTROS_POR_PAGINA - 1) // REGISTROS_POR_PAGINA, 1)
            if page > total_paginas:
                page = total_paginas
            offset = (page - 1) * REGISTROS_POR_PAGINA
            query = """
                SELECT r.id, r.numero, r.ocorrencia_em, r.status_processo,
                       r.status_faturamento, e.codigo_frota,
                       emp.nome AS empresa_nome, fun.nome AS funcionario_nome
            """ + base
            query += f" ORDER BY {ORDENACOES_RESSARCIMENTOS[sort]} {order.upper()}, r.id DESC LIMIT %s OFFSET %s"
            cursor.execute(query, params + [REGISTROS_POR_PAGINA, offset])
            processos = cursor.fetchall()
            return render_template(
                "pcpm_ressarcimentos.html", processos=processos,
                filtros=filtros, sort=sort, order=order, page=page,
                total_paginas=total_paginas, total_registros=total_registros,
            )
        finally:
            conn.close()

    @blueprint.route("/pcpm/ressarcimentos/novo", methods=["GET", "POST"])
    @login_required
    @module_required("acesso_pcpm")
    @module_required("acesso_pcpm_ressarcimentos")
    def novo_pcpm_ressarcimento():
        centro_id = _centro_usuario_obrigatorio()
        if _usuario_admin() and not centro_id:
            flash("Para cadastrar, o administrador deve possuir um centro de custos na sessão.", "warning")
            return redirect(url_for("main.pcpm_ressarcimentos"))
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        arquivos_salvos = []
        try:
            if request.method == "GET":
                dominios = _buscar_dominios_cadastro(cursor, centro_id)
                return render_template(
                    "novo_pcpm_ressarcimento.html",
                    equipamentos=dominios[0], empresas=dominios[1],
                    operadores=dominios[2], funcionarios=dominios[3],
                )

            equipamento_id = request.form.get("equipamento_id", type=int)
            empresa_id = request.form.get("empresa_ocorrencia_id", type=int)
            operador_id = request.form.get("operador_id", type=int)
            funcionario_id = request.form.get("funcionario_id", type=int)
            ocorrencia_raw = (request.form.get("ocorrencia_em") or "").strip()
            descricao = (request.form.get("descricao_ocorrencia") or "").strip()
            if not all((equipamento_id, empresa_id, funcionario_id, ocorrencia_raw, descricao)):
                raise ValueError("Preencha todos os campos obrigatórios da ocorrência.")
            ocorrencia_em = datetime.fromisoformat(ocorrencia_raw)

            cursor.execute(
                """
                SELECT e.id, e.codigo_frota, e.marca, e.modelo
                FROM pcpm_equipamentos e
                WHERE e.id = %s AND e.ativo = 1 AND e.centro_custo_id = %s
                """, (equipamento_id, centro_id),
            )
            equipamento = cursor.fetchone()
            cursor.execute("SELECT id, nome FROM pcpm_empresas WHERE id = %s AND ativo = 1", (empresa_id,))
            empresa = cursor.fetchone()
            cursor.execute(
                "SELECT id, nome, matricula FROM usuarios WHERE id = %s AND ativo = 1 AND centro_custos_id = %s",
                (funcionario_id, centro_id),
            )
            funcionario = cursor.fetchone()
            operador = None
            if operador_id:
                cursor.execute("SELECT id, nome, matricula FROM pcpm_pessoas WHERE id = %s AND ativo = 1", (operador_id,))
                operador = cursor.fetchone()
            if not equipamento or not empresa or not funcionario or (operador_id and not operador):
                raise ValueError("Um dos cadastros selecionados é inválido ou está fora do centro de custos.")

            ano = ocorrencia_em.year
            cursor.execute("SELECT COALESCE(MAX(sequencial), 0) + 1 AS proximo FROM pcpm_ressarcimentos WHERE ano = %s FOR UPDATE", (ano,))
            sequencial = cursor.fetchone()["proximo"]
            numero = f"RES-{sequencial:03d}/{ano}"
            equipamento_snapshot = f"{equipamento['codigo_frota']} - {equipamento['marca']} {equipamento['modelo']}"
            cursor.execute(
                """
                INSERT INTO pcpm_ressarcimentos (
                    ano, sequencial, numero, centro_custos_id, equipamento_id,
                    empresa_ocorrencia_id, ocorrencia_em, descricao_ocorrencia,
                    operador_id, operador_nome_snapshot, operador_matricula_snapshot,
                    funcionario_id, funcionario_nome_snapshot, funcionario_matricula_snapshot,
                    equipamento_snapshot, empresa_ocorrencia_snapshot,
                    criado_por, atualizado_por
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    ano, sequencial, numero, centro_id, equipamento_id, empresa_id,
                    ocorrencia_em, descricao, operador_id,
                    operador["nome"] if operador else None,
                    operador["matricula"] if operador else None,
                    funcionario_id, funcionario["nome"], funcionario["matricula"],
                    equipamento_snapshot, empresa["nome"],
                    session.get("usuario_id"), session.get("usuario_id"),
                ),
            )
            ressarcimento_id = cursor.lastrowid
            fotos = [item for item in request.files.getlist("fotos_avaria") if item and item.filename]
            checklist = request.files.get("checklist_movimentacao")
            for indice, arquivo in enumerate(fotos, start=1):
                arquivos_salvos.append(_salvar_anexo(cursor, ressarcimento_id, arquivo, "foto_avaria", f"avaria_{indice}"))
            if checklist and checklist.filename:
                arquivos_salvos.append(_salvar_anexo(cursor, ressarcimento_id, checklist, "checklist", "checklist"))
            _registrar_historico(cursor, ressarcimento_id, "Criação", f"Processo {numero} criado.", posteriores={"numero": numero, "etapa": 1}, etapa=1)
            conn.commit()
            flash(f"Processo {numero} criado com sucesso.", "success")
            return redirect(url_for("main.detalhar_pcpm_ressarcimento", ressarcimento_id=ressarcimento_id))
        except (ValueError, TypeError, UploadValidationError) as exc:
            conn.rollback()
            for nome, diretorio in arquivos_salvos:
                UploadService.excluir(nome, diretorio)
            flash(str(exc), "warning")
            return redirect(url_for("main.novo_pcpm_ressarcimento"))
        except Exception as exc:
            conn.rollback()
            for nome, diretorio in arquivos_salvos:
                UploadService.excluir(nome, diretorio)
            flash(f"Erro ao cadastrar o ressarcimento: {exc}", "danger")
            return redirect(url_for("main.novo_pcpm_ressarcimento"))
        finally:
            conn.close()

    @blueprint.route("/pcpm/ressarcimentos/<int:ressarcimento_id>")
    @login_required
    @module_required("acesso_pcpm")
    @module_required("acesso_pcpm_ressarcimentos")
    def detalhar_pcpm_ressarcimento(ressarcimento_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            processo = _buscar_processo_autorizado(cursor, ressarcimento_id)
            if not processo:
                flash("Processo não encontrado ou fora do seu centro de custos.", "warning")
                return redirect(url_for("main.pcpm_ressarcimentos"))
            cursor.execute(
                """SELECT h.*, u.nome AS usuario_nome
                   FROM pcpm_ressarcimentos_historico h
                   JOIN usuarios u ON u.id = h.usuario_id
                   WHERE h.ressarcimento_id = %s ORDER BY h.criado_em DESC, h.id DESC""",
                (ressarcimento_id,),
            )
            historico = cursor.fetchall()
            cursor.execute(
                """SELECT id, orcamento_id, categoria, nome_original, tamanho_bytes, criado_em
                   FROM pcpm_ressarcimentos_anexos
                   WHERE ressarcimento_id = %s AND ativo = 1
                   ORDER BY criado_em, id""", (ressarcimento_id,),
            )
            anexos = cursor.fetchall()
            cursor.execute(
                """SELECT o.*, u.nome AS criado_por_nome,
                          (SELECT COUNT(*) FROM pcpm_ressarcimentos_anexos a
                           WHERE a.orcamento_id=o.id AND a.categoria='orcamento' AND a.ativo=1) AS possui_orcamento,
                          (SELECT COUNT(*) FROM pcpm_ressarcimentos_anexos a
                           WHERE a.orcamento_id=o.id AND a.categoria='aprovacao_cliente' AND a.ativo=1) AS possui_aprovacao
                   FROM pcpm_ressarcimentos_orcamentos o
                   JOIN usuarios u ON u.id=o.criado_por
                   WHERE o.ressarcimento_id=%s
                   ORDER BY o.versao DESC""",
                (ressarcimento_id,),
            )
            orcamentos = cursor.fetchall()
            pode_gerar_book = (
                any(item["vigente"] and item["status"] == "Aprovado" for item in orcamentos)
                and any(item["categoria"] == "documentacao" for item in anexos)
            )
            dominios = _buscar_dominios_cadastro(cursor, processo["centro_custos_id"])
            return render_template(
                "pcpm_ressarcimento_detalhe.html", processo=processo,
                historico=historico, anexos=anexos, orcamentos=orcamentos,
                pode_gerar_book=pode_gerar_book,
                hoje_iso=datetime.now().date().isoformat(),
                equipamentos=dominios[0], empresas=dominios[1],
                operadores=dominios[2], funcionarios=dominios[3],
            )
        finally:
            conn.close()

    @blueprint.route("/pcpm/ressarcimentos/<int:ressarcimento_id>/ocorrencia", methods=["POST"])
    @login_required
    @module_required("acesso_pcpm")
    @module_required("acesso_pcpm_ressarcimentos")
    def atualizar_ocorrencia_pcpm_ressarcimento(ressarcimento_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        arquivos_salvos = []
        try:
            processo = _buscar_processo_autorizado(cursor, ressarcimento_id, for_update=True)
            if not processo:
                raise ValueError("Processo não encontrado ou fora do seu centro de custos.")
            if processo["status_processo"] == "Cancelado":
                raise ValueError("Reabra o processo antes de alterar a ocorrência.")

            equipamento_id = request.form.get("equipamento_id", type=int)
            empresa_id = request.form.get("empresa_ocorrencia_id", type=int)
            operador_id = request.form.get("operador_id", type=int)
            funcionario_id = request.form.get("funcionario_id", type=int)
            ocorrencia_raw = (request.form.get("ocorrencia_em") or "").strip()
            descricao = (request.form.get("descricao_ocorrencia") or "").strip()
            if not all((equipamento_id, empresa_id, funcionario_id, ocorrencia_raw, descricao)):
                raise ValueError("Preencha todos os campos obrigatórios da ocorrência.")
            ocorrencia_em = datetime.fromisoformat(ocorrencia_raw)

            centro_id = processo["centro_custos_id"]
            cursor.execute(
                """SELECT id, codigo_frota, marca, modelo FROM pcpm_equipamentos
                   WHERE id=%s AND ativo=1 AND centro_custo_id=%s""",
                (equipamento_id, centro_id),
            )
            equipamento = cursor.fetchone()
            cursor.execute("SELECT id, nome FROM pcpm_empresas WHERE id=%s AND ativo=1", (empresa_id,))
            empresa = cursor.fetchone()
            cursor.execute(
                """SELECT id, nome, matricula FROM usuarios
                   WHERE id=%s AND ativo=1 AND centro_custos_id=%s""",
                (funcionario_id, centro_id),
            )
            funcionario = cursor.fetchone()
            operador = None
            if operador_id:
                cursor.execute(
                    "SELECT id, nome, matricula FROM pcpm_pessoas WHERE id=%s AND ativo=1",
                    (operador_id,),
                )
                operador = cursor.fetchone()
            if not equipamento or not empresa or not funcionario or (operador_id and not operador):
                raise ValueError("Um dos cadastros selecionados é inválido ou está fora do centro de custos.")

            anteriores = {
                "equipamento": processo["equipamento_snapshot"],
                "empresa": processo["empresa_ocorrencia_snapshot"],
                "ocorrencia_em": processo["ocorrencia_em"],
                "descricao": processo["descricao_ocorrencia"],
                "operador": processo["operador_nome_snapshot"],
                "funcionario": processo["funcionario_nome_snapshot"],
            }
            equipamento_snapshot = f"{equipamento['codigo_frota']} - {equipamento['marca']} {equipamento['modelo']}"
            posteriores = {
                "equipamento": equipamento_snapshot,
                "empresa": empresa["nome"], "ocorrencia_em": ocorrencia_em,
                "descricao": descricao,
                "operador": operador["nome"] if operador else None,
                "funcionario": funcionario["nome"],
            }
            cursor.execute(
                """UPDATE pcpm_ressarcimentos SET
                       equipamento_id=%s, empresa_ocorrencia_id=%s, ocorrencia_em=%s,
                       descricao_ocorrencia=%s, operador_id=%s,
                       operador_nome_snapshot=%s, operador_matricula_snapshot=%s,
                       funcionario_id=%s, funcionario_nome_snapshot=%s,
                       funcionario_matricula_snapshot=%s, equipamento_snapshot=%s,
                       empresa_ocorrencia_snapshot=%s, atualizado_por=%s
                   WHERE id=%s""",
                (
                    equipamento_id, empresa_id, ocorrencia_em, descricao, operador_id,
                    operador["nome"] if operador else None,
                    operador["matricula"] if operador else None,
                    funcionario_id, funcionario["nome"], funcionario["matricula"],
                    equipamento_snapshot, empresa["nome"], session.get("usuario_id"),
                    ressarcimento_id,
                ),
            )
            fotos = [item for item in request.files.getlist("fotos_avaria") if item and item.filename]
            checklist = request.files.get("checklist_movimentacao")
            for indice, arquivo in enumerate(fotos, start=1):
                arquivos_salvos.append(_salvar_anexo(cursor, ressarcimento_id, arquivo, "foto_avaria", f"avaria_adicional_{indice}"))
            if checklist and checklist.filename:
                arquivos_salvos.append(_salvar_anexo(cursor, ressarcimento_id, checklist, "checklist", "checklist_adicional"))
            _registrar_historico(
                cursor, ressarcimento_id, "Atualização da ocorrência",
                "Dados da avaria atualizados.", anteriores, posteriores, etapa=1,
            )
            conn.commit()
            flash("Dados da ocorrência atualizados com sucesso.", "success")
        except (ValueError, TypeError, UploadValidationError) as exc:
            conn.rollback()
            for nome, diretorio in arquivos_salvos:
                UploadService.excluir(nome, diretorio)
            flash(str(exc), "warning")
        except Exception as exc:
            conn.rollback()
            for nome, diretorio in arquivos_salvos:
                UploadService.excluir(nome, diretorio)
            flash(f"Erro ao atualizar a ocorrência: {exc}", "danger")
        finally:
            conn.close()
        return redirect(url_for("main.detalhar_pcpm_ressarcimento", ressarcimento_id=ressarcimento_id))

    @blueprint.route("/pcpm/ressarcimentos/<int:ressarcimento_id>/orcamentos", methods=["POST"])
    @login_required
    @module_required("acesso_pcpm")
    @module_required("acesso_pcpm_ressarcimentos")
    def adicionar_orcamento_pcpm_ressarcimento(ressarcimento_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        arquivos_salvos = []
        try:
            processo = _buscar_processo_autorizado(cursor, ressarcimento_id, for_update=True)
            if not processo:
                raise ValueError("Processo não encontrado ou fora do seu centro de custos.")
            if processo["status_processo"] == "Cancelado":
                raise ValueError("Reabra o processo antes de incluir um orçamento.")
            if not processo["empresa_cliente_id"]:
                raise ValueError("Conclua os dados do cliente antes de incluir o orçamento.")

            numero = (request.form.get("numero_orcamento_totvs") or "").strip()
            valor_raw = (request.form.get("valor_orcamento") or "").strip()
            if "," in valor_raw:
                valor_raw = valor_raw.replace(".", "").replace(",", ".")
            arquivo = request.files.get("arquivo_orcamento")
            if not numero or not valor_raw or not arquivo or not arquivo.filename:
                raise ValueError("Informe o número, o valor e anexe o orçamento do TOTVS.")
            if len(numero) > 80:
                raise ValueError("O número do orçamento deve possuir no máximo 80 caracteres.")
            try:
                valor = Decimal(valor_raw).quantize(Decimal("0.01"))
            except (InvalidOperation, ValueError):
                raise ValueError("Informe um valor de orçamento válido.")
            if valor <= 0:
                raise ValueError("O valor do orçamento deve ser maior que zero.")

            cursor.execute(
                "SELECT COALESCE(MAX(versao), 0) + 1 AS proxima FROM pcpm_ressarcimentos_orcamentos WHERE ressarcimento_id=%s FOR UPDATE",
                (ressarcimento_id,),
            )
            versao = cursor.fetchone()["proxima"]
            cursor.execute(
                "UPDATE pcpm_ressarcimentos_orcamentos SET vigente=0 WHERE ressarcimento_id=%s AND vigente=1",
                (ressarcimento_id,),
            )
            cursor.execute(
                """INSERT INTO pcpm_ressarcimentos_orcamentos
                       (ressarcimento_id, versao, numero_orcamento_totvs, valor_orcamento, criado_por)
                   VALUES (%s,%s,%s,%s,%s)""",
                (ressarcimento_id, versao, numero, valor, session.get("usuario_id")),
            )
            orcamento_id = cursor.lastrowid
            arquivos_salvos.append(
                _salvar_anexo(cursor, ressarcimento_id, arquivo, "orcamento", f"orcamento_v{versao}", orcamento_id)
            )
            cursor.execute(
                """UPDATE pcpm_ressarcimentos
                   SET etapa_atual=GREATEST(etapa_atual, 3), atualizado_por=%s WHERE id=%s""",
                (session.get("usuario_id"), ressarcimento_id),
            )
            _registrar_historico(
                cursor, ressarcimento_id, "Nova versão do orçamento",
                f"Versão {versao} do orçamento {numero} incluída.",
                posteriores={"versao": versao, "numero": numero, "valor": str(valor), "status": "Não enviado"}, etapa=3,
            )
            conn.commit()
            flash(f"Versão {versao} do orçamento incluída com sucesso.", "success")
        except (ValueError, TypeError, UploadValidationError) as exc:
            conn.rollback()
            for nome, diretorio in arquivos_salvos:
                UploadService.excluir(nome, diretorio)
            flash(str(exc), "warning")
        except Exception as exc:
            conn.rollback()
            for nome, diretorio in arquivos_salvos:
                UploadService.excluir(nome, diretorio)
            flash(f"Erro ao incluir o orçamento: {exc}", "danger")
        finally:
            conn.close()
        return redirect(url_for("main.detalhar_pcpm_ressarcimento", ressarcimento_id=ressarcimento_id))

    @blueprint.route("/pcpm/ressarcimentos/<int:ressarcimento_id>/orcamentos/<int:orcamento_id>/status", methods=["POST"])
    @login_required
    @module_required("acesso_pcpm")
    @module_required("acesso_pcpm_ressarcimentos")
    def atualizar_status_orcamento_pcpm_ressarcimento(ressarcimento_id, orcamento_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        arquivos_salvos = []
        try:
            processo = _buscar_processo_autorizado(cursor, ressarcimento_id, for_update=True)
            if not processo:
                raise ValueError("Processo não encontrado ou fora do seu centro de custos.")
            if processo["status_processo"] == "Cancelado":
                raise ValueError("Reabra o processo antes de alterar o orçamento.")
            cursor.execute(
                """SELECT * FROM pcpm_ressarcimentos_orcamentos
                   WHERE id=%s AND ressarcimento_id=%s AND vigente=1 FOR UPDATE""",
                (orcamento_id, ressarcimento_id),
            )
            orcamento = cursor.fetchone()
            if not orcamento:
                raise ValueError("Somente a versão vigente do orçamento pode ser alterada.")
            status = (request.form.get("status") or "").strip()
            permitidos = {"Não enviado", "Aguardando aprovação", "Aprovado", "Reprovado"}
            if status not in permitidos:
                raise ValueError("Selecione um status válido para o orçamento.")
            data_raw = (request.form.get("data_envio") or "").strip()
            data_envio = None
            if status != "Não enviado":
                if not data_raw:
                    raise ValueError("Informe a data de envio do orçamento.")
                data_envio = datetime.strptime(data_raw, "%Y-%m-%d").date()
            aprovacao = request.files.get("arquivo_aprovacao")
            if status == "Aprovado":
                cursor.execute(
                    """SELECT COUNT(*) AS total FROM pcpm_ressarcimentos_anexos
                       WHERE orcamento_id=%s AND categoria='aprovacao_cliente' AND ativo=1""",
                    (orcamento_id,),
                )
                possui_aprovacao = cursor.fetchone()["total"] > 0
                if not possui_aprovacao and (not aprovacao or not aprovacao.filename):
                    raise ValueError("Anexe o e-mail de aprovação do cliente para aprovar o orçamento.")
            if aprovacao and aprovacao.filename:
                arquivos_salvos.append(
                    _salvar_anexo(cursor, ressarcimento_id, aprovacao, "aprovacao_cliente", f"aprovacao_v{orcamento['versao']}", orcamento_id)
                )
            cursor.execute(
                """UPDATE pcpm_ressarcimentos_orcamentos
                   SET status=%s, data_envio=%s WHERE id=%s""",
                (status, data_envio, orcamento_id),
            )
            cursor.execute(
                "UPDATE pcpm_ressarcimentos SET atualizado_por=%s WHERE id=%s",
                (session.get("usuario_id"), ressarcimento_id),
            )
            _registrar_historico(
                cursor, ressarcimento_id, "Status do orçamento",
                f"Orçamento versão {orcamento['versao']} alterado para {status}.",
                anteriores={"status": orcamento["status"], "data_envio": orcamento["data_envio"]},
                posteriores={"status": status, "data_envio": data_envio}, etapa=3,
            )
            conn.commit()
            flash("Status do orçamento atualizado com sucesso.", "success")
        except (ValueError, TypeError, UploadValidationError) as exc:
            conn.rollback()
            for nome, diretorio in arquivos_salvos:
                UploadService.excluir(nome, diretorio)
            flash(str(exc), "warning")
        except Exception as exc:
            conn.rollback()
            for nome, diretorio in arquivos_salvos:
                UploadService.excluir(nome, diretorio)
            flash(f"Erro ao atualizar o orçamento: {exc}", "danger")
        finally:
            conn.close()
        return redirect(url_for("main.detalhar_pcpm_ressarcimento", ressarcimento_id=ressarcimento_id))

    @blueprint.route("/pcpm/ressarcimentos/<int:ressarcimento_id>/cliente", methods=["POST"])
    @login_required
    @module_required("acesso_pcpm")
    @module_required("acesso_pcpm_ressarcimentos")
    def atualizar_cliente_pcpm_ressarcimento(ressarcimento_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            processo = _buscar_processo_autorizado(cursor, ressarcimento_id, for_update=True)
            if not processo:
                raise ValueError("Processo não encontrado ou fora do seu centro de custos.")
            if processo["status_processo"] == "Cancelado":
                raise ValueError("Reabra o processo antes de alterar os dados do cliente.")

            empresa_cliente_id = request.form.get("empresa_cliente_id", type=int)
            cliente_centro_custos = (request.form.get("cliente_centro_custos") or "").strip()
            cliente_area = (request.form.get("cliente_area") or "").strip()
            aprovador_email = (request.form.get("aprovador_email") or "").strip().lower()
            aprovador_telefone_raw = (request.form.get("aprovador_telefone") or "").strip()
            if not all((empresa_cliente_id, cliente_centro_custos, cliente_area, aprovador_email, aprovador_telefone_raw)):
                raise ValueError("Preencha todos os dados do cliente e do aprovador.")
            if len(cliente_centro_custos) > 150 or len(cliente_area) > 150:
                raise ValueError("Centro de custos e área devem possuir no máximo 150 caracteres.")
            if len(aprovador_email) > 150 or not PADRAO_EMAIL.fullmatch(aprovador_email):
                raise ValueError("Informe um e-mail válido para o aprovador.")
            aprovador_telefone = _normalizar_telefone(aprovador_telefone_raw)
            cursor.execute(
                "SELECT id, nome FROM pcpm_empresas WHERE id=%s AND ativo=1",
                (empresa_cliente_id,),
            )
            empresa = cursor.fetchone()
            if not empresa:
                raise ValueError("A empresa do cliente selecionada é inválida ou está inativa.")

            anteriores = {
                "empresa_cliente": processo["empresa_cliente_snapshot"],
                "centro_custos_cliente": processo["cliente_centro_custos"],
                "area_cliente": processo["cliente_area"],
                "email_aprovador": processo["aprovador_email"],
                "telefone_aprovador": processo["aprovador_telefone"],
            }
            posteriores = {
                "empresa_cliente": empresa["nome"],
                "centro_custos_cliente": cliente_centro_custos,
                "area_cliente": cliente_area,
                "email_aprovador": aprovador_email,
                "telefone_aprovador": aprovador_telefone,
            }
            cursor.execute(
                """UPDATE pcpm_ressarcimentos SET
                       empresa_cliente_id=%s, empresa_cliente_snapshot=%s,
                       cliente_centro_custos=%s, cliente_area=%s,
                       aprovador_email=%s, aprovador_telefone=%s,
                       etapa_atual=GREATEST(etapa_atual, 2), atualizado_por=%s
                   WHERE id=%s""",
                (
                    empresa_cliente_id, empresa["nome"], cliente_centro_custos,
                    cliente_area, aprovador_email, aprovador_telefone,
                    session.get("usuario_id"), ressarcimento_id,
                ),
            )
            evento = "Atualização dos dados do cliente" if processo["empresa_cliente_id"] else "Cadastro dos dados do cliente"
            _registrar_historico(
                cursor, ressarcimento_id, evento,
                "Dados do cliente e do aprovador registrados.",
                anteriores if processo["empresa_cliente_id"] else None,
                posteriores, etapa=2,
            )
            conn.commit()
            flash("Dados do cliente atualizados com sucesso.", "success")
        except (ValueError, TypeError) as exc:
            conn.rollback()
            flash(str(exc), "warning")
        except Exception as exc:
            conn.rollback()
            flash(f"Erro ao atualizar os dados do cliente: {exc}", "danger")
        finally:
            conn.close()
        return redirect(url_for("main.detalhar_pcpm_ressarcimento", ressarcimento_id=ressarcimento_id))

    @blueprint.route("/pcpm/ressarcimentos/<int:ressarcimento_id>/documentos", methods=["POST"])
    @login_required
    @module_required("acesso_pcpm")
    @module_required("acesso_pcpm_ressarcimentos")
    def adicionar_documentos_pcpm_ressarcimento(ressarcimento_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        arquivos_salvos = []
        try:
            processo = _buscar_processo_autorizado(cursor, ressarcimento_id, for_update=True)
            if not processo:
                raise ValueError("Processo não encontrado ou fora do seu centro de custos.")
            if processo["status_processo"] == "Cancelado":
                raise ValueError("Reabra o processo antes de incluir documentos.")
            documentos = [item for item in request.files.getlist("documentos") if item and item.filename]
            if not documentos:
                raise ValueError("Selecione ao menos um documento comprobatório.")
            nomes = []
            for indice, arquivo in enumerate(documentos, start=1):
                nomes.append(os.path.basename(arquivo.filename.replace("\\", "/"))[:255])
                arquivos_salvos.append(
                    _salvar_anexo(
                        cursor, ressarcimento_id, arquivo, "documentacao",
                        f"documentacao_{datetime.now().strftime('%Y%m%d%H%M%S')}_{indice}",
                    )
                )
            cursor.execute(
                """UPDATE pcpm_ressarcimentos
                   SET etapa_atual=GREATEST(etapa_atual, 4), atualizado_por=%s WHERE id=%s""",
                (session.get("usuario_id"), ressarcimento_id),
            )
            _registrar_historico(
                cursor, ressarcimento_id, "Inclusão de documentação",
                f"{len(nomes)} documento(s) comprobatório(s) incluído(s).",
                posteriores={"arquivos": nomes}, etapa=4,
            )
            conn.commit()
            flash(f"{len(nomes)} documento(s) incluído(s) com sucesso.", "success")
        except (ValueError, TypeError, UploadValidationError) as exc:
            conn.rollback()
            for nome, diretorio in arquivos_salvos:
                UploadService.excluir(nome, diretorio)
            flash(str(exc), "warning")
        except Exception as exc:
            conn.rollback()
            for nome, diretorio in arquivos_salvos:
                UploadService.excluir(nome, diretorio)
            flash(f"Erro ao incluir a documentação: {exc}", "danger")
        finally:
            conn.close()
        return redirect(url_for("main.detalhar_pcpm_ressarcimento", ressarcimento_id=ressarcimento_id))

    @blueprint.route("/pcpm/ressarcimentos/<int:ressarcimento_id>/documentos/<int:anexo_id>/remover", methods=["POST"])
    @login_required
    @module_required("acesso_pcpm")
    @module_required("acesso_pcpm_ressarcimentos")
    def remover_documento_pcpm_ressarcimento(ressarcimento_id, anexo_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            processo = _buscar_processo_autorizado(cursor, ressarcimento_id, for_update=True)
            if not processo:
                raise ValueError("Processo não encontrado ou fora do seu centro de custos.")
            if processo["status_processo"] == "Cancelado":
                raise ValueError("Reabra o processo antes de remover documentos.")
            cursor.execute(
                """SELECT id, nome_original FROM pcpm_ressarcimentos_anexos
                   WHERE id=%s AND ressarcimento_id=%s
                     AND categoria='documentacao' AND ativo=1 FOR UPDATE""",
                (anexo_id, ressarcimento_id),
            )
            anexo = cursor.fetchone()
            if not anexo:
                raise ValueError("Documento não encontrado ou já removido.")
            cursor.execute(
                "UPDATE pcpm_ressarcimentos_anexos SET ativo=0 WHERE id=%s",
                (anexo_id,),
            )
            cursor.execute(
                "UPDATE pcpm_ressarcimentos SET atualizado_por=%s WHERE id=%s",
                (session.get("usuario_id"), ressarcimento_id),
            )
            _registrar_historico(
                cursor, ressarcimento_id, "Remoção de documentação",
                f"Documento {anexo['nome_original']} removido da visualização.",
                anteriores={"anexo_id": anexo_id, "arquivo": anexo["nome_original"], "ativo": True},
                posteriores={"anexo_id": anexo_id, "arquivo": anexo["nome_original"], "ativo": False}, etapa=4,
            )
            conn.commit()
            flash("Documento removido com sucesso.", "success")
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "warning")
        except Exception as exc:
            conn.rollback()
            flash(f"Erro ao remover o documento: {exc}", "danger")
        finally:
            conn.close()
        return redirect(url_for("main.detalhar_pcpm_ressarcimento", ressarcimento_id=ressarcimento_id))

    @blueprint.route("/pcpm/ressarcimentos/<int:ressarcimento_id>/book.pdf")
    @login_required
    @module_required("acesso_pcpm")
    @module_required("acesso_pcpm_ressarcimentos")
    def gerar_book_pcpm_ressarcimento(ressarcimento_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            processo = _buscar_processo_autorizado(cursor, ressarcimento_id)
            if not processo:
                flash("Processo não encontrado ou fora do seu centro de custos.", "warning")
                return redirect(url_for("main.pcpm_ressarcimentos"))
            cursor.execute(
                """SELECT o.*, u.nome AS criado_por_nome
                   FROM pcpm_ressarcimentos_orcamentos o
                   JOIN usuarios u ON u.id=o.criado_por
                   WHERE o.ressarcimento_id=%s ORDER BY o.versao DESC""",
                (ressarcimento_id,),
            )
            orcamentos = cursor.fetchall()
            if not any(item["vigente"] and item["status"] == "Aprovado" for item in orcamentos):
                raise ValueError("É necessário possuir um orçamento vigente aprovado para gerar o book.")
            cursor.execute(
                """SELECT id, orcamento_id, categoria, nome_original, nome_armazenado,
                          tamanho_bytes, criado_em
                   FROM pcpm_ressarcimentos_anexos
                   WHERE ressarcimento_id=%s AND ativo=1 ORDER BY criado_em, id""",
                (ressarcimento_id,),
            )
            anexos = cursor.fetchall()
            if not any(item["categoria"] == "documentacao" for item in anexos):
                raise ValueError("Inclua ao menos um documento comprobatório antes de gerar o book.")
            diretorio = UploadService.resolver_diretorio(_diretorio_ressarcimento(ressarcimento_id))
            for item in anexos:
                item["caminho_absoluto"] = os.path.join(diretorio, item["nome_armazenado"])
            cursor.execute(
                """SELECT h.*, u.nome AS usuario_nome
                   FROM pcpm_ressarcimentos_historico h
                   JOIN usuarios u ON u.id=h.usuario_id
                   WHERE h.ressarcimento_id=%s ORDER BY h.criado_em, h.id""",
                (ressarcimento_id,),
            )
            historico = cursor.fetchall()
            from app.utils.pcpm_ressarcimentos_pdf import gerar_book_ressarcimento
            logo_path = os.path.join("app", "static", "imagens", "logo_trackplan.png")
            pdf = gerar_book_ressarcimento(processo, orcamentos, anexos, historico, logo_path)
            _registrar_historico(
                cursor, ressarcimento_id, "Geração do book",
                "Book consolidado do processo gerado em PDF.", etapa=4,
            )
            conn.commit()
            return send_file(
                pdf, mimetype="application/pdf", as_attachment=True,
                download_name=f"book_ressarcimento_{processo['numero'].replace('/', '_')}.pdf",
            )
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "warning")
        except Exception as exc:
            conn.rollback()
            flash(f"Erro ao gerar o book de ressarcimento: {exc}", "danger")
        finally:
            conn.close()
        return redirect(url_for("main.detalhar_pcpm_ressarcimento", ressarcimento_id=ressarcimento_id))

    @blueprint.route("/pcpm/ressarcimentos/<int:ressarcimento_id>/faturamento", methods=["POST"])
    @login_required
    @module_required("acesso_pcpm")
    @module_required("acesso_pcpm_ressarcimentos")
    def atualizar_faturamento_pcpm_ressarcimento(ressarcimento_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            processo = _buscar_processo_autorizado(cursor, ressarcimento_id, for_update=True)
            if not processo:
                raise ValueError("Processo não encontrado ou fora do seu centro de custos.")
            if processo["status_processo"] == "Cancelado":
                raise ValueError("Reabra o processo antes de alterar o faturamento.")
            if processo["status_faturamento"] == "Realizado":
                raise ValueError("O faturamento já foi realizado e não pode ser revertido.")
            status = (request.form.get("status_faturamento") or "").strip()
            if status not in {"Pendente", "Realizado"}:
                raise ValueError("Selecione um status de faturamento válido.")
            data_raw = (request.form.get("data_faturamento") or "").strip()
            data_faturamento = None
            status_processo = processo["status_processo"]
            if status == "Realizado":
                if not data_raw:
                    raise ValueError("Informe a data do faturamento.")
                data_faturamento = datetime.strptime(data_raw, "%Y-%m-%d").date()
                if data_faturamento > datetime.now().date():
                    raise ValueError("A data do faturamento não pode ser futura.")
                cursor.execute(
                    """SELECT COUNT(*) AS total FROM pcpm_ressarcimentos_orcamentos
                       WHERE ressarcimento_id=%s AND vigente=1 AND status='Aprovado'""",
                    (ressarcimento_id,),
                )
                if cursor.fetchone()["total"] == 0:
                    raise ValueError("É necessário possuir um orçamento vigente aprovado antes do faturamento.")
                cursor.execute(
                    """SELECT COUNT(*) AS total FROM pcpm_ressarcimentos_anexos
                       WHERE ressarcimento_id=%s AND categoria='documentacao' AND ativo=1""",
                    (ressarcimento_id,),
                )
                if cursor.fetchone()["total"] == 0:
                    raise ValueError("Inclua a documentação comprobatória antes do faturamento.")
                status_processo = "Concluído"
            cursor.execute(
                """UPDATE pcpm_ressarcimentos
                   SET status_faturamento=%s, data_faturamento=%s,
                       status_processo=%s, etapa_atual=GREATEST(etapa_atual, 5),
                       atualizado_por=%s WHERE id=%s""",
                (
                    status, data_faturamento, status_processo,
                    session.get("usuario_id"), ressarcimento_id,
                ),
            )
            _registrar_historico(
                cursor, ressarcimento_id, "Atualização do faturamento",
                f"Faturamento alterado para {status}.",
                anteriores={
                    "status_faturamento": processo["status_faturamento"],
                    "data_faturamento": processo["data_faturamento"],
                    "status_processo": processo["status_processo"],
                },
                posteriores={
                    "status_faturamento": status,
                    "data_faturamento": data_faturamento,
                    "status_processo": status_processo,
                }, etapa=5,
            )
            conn.commit()
            flash(
                "Faturamento registrado e processo concluído."
                if status == "Realizado" else "Status do faturamento atualizado.",
                "success",
            )
        except (ValueError, TypeError) as exc:
            conn.rollback()
            flash(str(exc), "warning")
        except Exception as exc:
            conn.rollback()
            flash(f"Erro ao atualizar o faturamento: {exc}", "danger")
        finally:
            conn.close()
        return redirect(url_for("main.detalhar_pcpm_ressarcimento", ressarcimento_id=ressarcimento_id))

    @blueprint.route("/pcpm/ressarcimentos/<int:ressarcimento_id>/anexos/<int:anexo_id>")
    @login_required
    @module_required("acesso_pcpm")
    @module_required("acesso_pcpm_ressarcimentos")
    def baixar_anexo_pcpm_ressarcimento(ressarcimento_id, anexo_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            if not _buscar_processo_autorizado(cursor, ressarcimento_id):
                flash("Anexo não encontrado ou fora do seu centro de custos.", "warning")
                return redirect(url_for("main.pcpm_ressarcimentos"))
            cursor.execute(
                """SELECT nome_original, nome_armazenado
                   FROM pcpm_ressarcimentos_anexos
                   WHERE id = %s AND ressarcimento_id = %s AND ativo = 1""",
                (anexo_id, ressarcimento_id),
            )
            anexo = cursor.fetchone()
            if not anexo:
                flash("Anexo não encontrado.", "warning")
                return redirect(url_for("main.detalhar_pcpm_ressarcimento", ressarcimento_id=ressarcimento_id))
            return send_from_directory(
                UploadService.resolver_diretorio(_diretorio_ressarcimento(ressarcimento_id)),
                anexo["nome_armazenado"], as_attachment=True,
                download_name=anexo["nome_original"],
            )
        finally:
            conn.close()

    @blueprint.route("/pcpm/ressarcimentos/<int:ressarcimento_id>/cancelar", methods=["POST"])
    @login_required
    @module_required("acesso_pcpm")
    @module_required("acesso_pcpm_ressarcimentos")
    def cancelar_pcpm_ressarcimento(ressarcimento_id):
        motivo = (request.form.get("motivo") or "").strip()
        if not motivo:
            flash("Informe a justificativa do cancelamento.", "warning")
            return redirect(url_for("main.detalhar_pcpm_ressarcimento", ressarcimento_id=ressarcimento_id))
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            processo = _buscar_processo_autorizado(cursor, ressarcimento_id, for_update=True)
            if not processo:
                raise ValueError("Processo não encontrado ou fora do seu centro de custos.")
            if processo["status_faturamento"] == "Realizado":
                raise ValueError("Um processo com faturamento realizado não pode ser cancelado.")
            if processo["status_processo"] == "Cancelado":
                raise ValueError("O processo já está cancelado.")
            cursor.execute(
                """UPDATE pcpm_ressarcimentos
                   SET status_processo='Cancelado', status_faturamento='Cancelado',
                       cancelado_em=NOW(), cancelado_por=%s, motivo_cancelamento=%s,
                       atualizado_por=%s WHERE id=%s""",
                (session.get("usuario_id"), motivo, session.get("usuario_id"), ressarcimento_id),
            )
            _registrar_historico(cursor, ressarcimento_id, "Cancelamento", motivo, anteriores={"status": processo["status_processo"], "faturamento": processo["status_faturamento"]}, posteriores={"status": "Cancelado", "faturamento": "Cancelado"})
            conn.commit()
            flash("Processo cancelado.", "success")
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "warning")
        finally:
            conn.close()
        return redirect(url_for("main.detalhar_pcpm_ressarcimento", ressarcimento_id=ressarcimento_id))

    @blueprint.route("/pcpm/ressarcimentos/<int:ressarcimento_id>/reabrir", methods=["POST"])
    @login_required
    @module_required("acesso_pcpm")
    @module_required("acesso_pcpm_ressarcimentos")
    def reabrir_pcpm_ressarcimento(ressarcimento_id):
        motivo = (request.form.get("motivo") or "").strip()
        if not motivo:
            flash("Informe a justificativa da reabertura.", "warning")
            return redirect(url_for("main.detalhar_pcpm_ressarcimento", ressarcimento_id=ressarcimento_id))
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            processo = _buscar_processo_autorizado(cursor, ressarcimento_id, for_update=True)
            if not processo:
                raise ValueError("Processo não encontrado ou fora do seu centro de custos.")
            if processo["status_processo"] != "Cancelado":
                raise ValueError("Somente processos cancelados podem ser reabertos.")
            cursor.execute(
                """UPDATE pcpm_ressarcimentos
                   SET status_processo='Em andamento', status_faturamento='Pendente',
                       reaberto_em=NOW(), reaberto_por=%s, motivo_reabertura=%s,
                       atualizado_por=%s WHERE id=%s""",
                (session.get("usuario_id"), motivo, session.get("usuario_id"), ressarcimento_id),
            )
            _registrar_historico(cursor, ressarcimento_id, "Reabertura", motivo, anteriores={"status": "Cancelado", "faturamento": "Cancelado"}, posteriores={"status": "Em andamento", "faturamento": "Pendente"})
            conn.commit()
            flash("Processo reaberto.", "success")
        except ValueError as exc:
            conn.rollback()
            flash(str(exc), "warning")
        finally:
            conn.close()
        return redirect(url_for("main.detalhar_pcpm_ressarcimento", ressarcimento_id=ressarcimento_id))
