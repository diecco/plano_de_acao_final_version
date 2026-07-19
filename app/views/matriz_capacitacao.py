from datetime import date, datetime, timedelta
from io import BytesIO

from flask import flash, redirect, render_template, request, send_file, session, url_for
from openpyxl import Workbook

from app.decorators import login_required, module_required
from app.utils.db import get_db_connection


def register_matriz_capacitacao_routes(blueprint):
    # =============================== #
    # MATRIZ DE CAPACITAÇÃO           #
    # =============================== #
    
    def _mc_validar_vinculo(
        cursor,
        cargo_id,
        procedimento_id=None,
        nivel_aplicacao=None,
        funcao_id=None,
        setor_id=None,
        exigir_vinculo=False,
    ):
        """Valida no servidor as entidades usadas para montar a matriz."""
        cursor.execute("SELECT id FROM cargos WHERE id = %s AND ativo = 1", (cargo_id,))
        if not cursor.fetchone():
            return "Cargo inválido ou inativo."
    
        if funcao_id:
            cursor.execute("SELECT id FROM funcoes WHERE id = %s AND ativo = 1", (funcao_id,))
            if not cursor.fetchone():
                return "Função inválida ou inativa."
            if exigir_vinculo:
                cursor.execute("""
                    SELECT id FROM matriz_cargo_funcoes
                    WHERE cargo_id = %s AND funcao_id = %s AND ativo = 1
                    LIMIT 1
                """, (cargo_id, funcao_id))
                if not cursor.fetchone():
                    return "A função não está vinculada ao cargo selecionado."
    
        if setor_id:
            cursor.execute("SELECT id FROM setores WHERE id = %s AND ativo = 1", (setor_id,))
            if not cursor.fetchone():
                return "Setor inválido ou inativo."
            if exigir_vinculo:
                cursor.execute("""
                    SELECT id FROM matriz_cargo_setores
                    WHERE cargo_id = %s AND setor_id = %s AND ativo = 1
                    LIMIT 1
                """, (cargo_id, setor_id))
                if not cursor.fetchone():
                    return "O setor não está vinculado ao cargo selecionado."
    
        if procedimento_id:
            cursor.execute("""
                SELECT p.id
                FROM procedimentos p
                JOIN procedimento_niveis_aplicacao pna
                  ON pna.procedimento_id = p.id
                 AND pna.ativo = 1
                 AND pna.nivel_aplicacao = %s
                WHERE p.id = %s AND p.ativo = 1
                LIMIT 1
            """, (nivel_aplicacao, procedimento_id))
            if not cursor.fetchone():
                return f"Procedimento inválido para o nível {nivel_aplicacao}."
    
        return None
    
    
    @blueprint.route('/matriz_capacitacao', methods=['GET'])
    @login_required
    @module_required('acesso_procedimentos')
    def matriz_capacitacao():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
    
        cargo_id = request.args.get('cargo_id', type=int)
    
        # Inicialização
        cargos = []
        procedimentos_cargo_disponiveis = []
        procedimentos_cargo = []
        funcoes_disponiveis = []
        funcoes_vinculadas = []
        setores_disponiveis = []
        setores_vinculados = []
        procedimentos_funcao_disponiveis = []
        procedimentos_setor_disponiveis = []
    
        # =========================
        # CARGOS
        # =========================
        cursor.execute("""
            SELECT id, nome
            FROM cargos
            WHERE ativo = 1
            ORDER BY nome
        """)
        cargos = cursor.fetchall()
    
        if cargo_id:
    
            # =========================
            # CAMADA 1 - DISPONÍVEIS (CARGO)
            # =========================
            cursor.execute("""
                SELECT
                    p.id,
                    td.sigla,
                    p.numero_documento,
                    p.titulo
                FROM procedimentos p
                INNER JOIN tipos_documento td
                    ON td.id = p.tipo_documento_id
                INNER JOIN procedimento_niveis_aplicacao pna
                    ON pna.procedimento_id = p.id
                WHERE p.ativo = 1
                  AND pna.ativo = 1
                  AND pna.nivel_aplicacao = 'cargo'
                ORDER BY td.sigla, p.numero_documento, p.titulo
            """)
            procedimentos_cargo_disponiveis = cursor.fetchall()
    
            # =========================
            # CAMADA 1 - VINCULADOS
            # =========================
            cursor.execute("""
                SELECT
                    mcp.id,
                    td.sigla,
                    p.numero_documento,
                    p.titulo
                FROM matriz_cargo_procedimentos mcp
                INNER JOIN procedimentos p
                    ON p.id = mcp.procedimento_id
                INNER JOIN tipos_documento td
                    ON td.id = p.tipo_documento_id
                WHERE mcp.cargo_id = %s
                  AND mcp.ativo = 1
                  AND p.ativo = 1
                ORDER BY td.sigla, p.numero_documento, p.titulo
            """, (cargo_id,))
            procedimentos_cargo = cursor.fetchall()
    
            # =========================
            # FUNÇÕES DISPONÍVEIS
            # =========================
            cursor.execute("""
                SELECT id, nome
                FROM funcoes
                WHERE ativo = 1
                ORDER BY nome
            """)
            funcoes_disponiveis = cursor.fetchall()
    
            # =========================
            # CAMADA 2 - DISPONÍVEIS (FUNÇÃO)
            # =========================
            cursor.execute("""
                SELECT
                    p.id,
                    td.sigla,
                    p.numero_documento,
                    p.titulo
                FROM procedimentos p
                INNER JOIN tipos_documento td
                    ON td.id = p.tipo_documento_id
                INNER JOIN procedimento_niveis_aplicacao pna
                    ON pna.procedimento_id = p.id
                WHERE p.ativo = 1
                  AND pna.ativo = 1
                  AND pna.nivel_aplicacao = 'funcao'
                ORDER BY td.sigla, p.numero_documento, p.titulo
            """)
            procedimentos_funcao_disponiveis = cursor.fetchall()
    
            # =========================
            # FUNÇÕES VINCULADAS AO CARGO
            # =========================
            cursor.execute("""
                SELECT
                    mcf.id,
                    mcf.funcao_id,
                    f.nome
                FROM matriz_cargo_funcoes mcf
                INNER JOIN funcoes f
                    ON f.id = mcf.funcao_id
                WHERE mcf.cargo_id = %s
                  AND mcf.ativo = 1
                  AND f.ativo = 1
                ORDER BY f.nome
            """, (cargo_id,))
            funcoes_raw = cursor.fetchall()
    
            for funcao in funcoes_raw:
                cursor.execute("""
                    SELECT
                        mfp.id,
                        td.sigla,
                        p.numero_documento,
                        p.titulo
                    FROM matriz_funcao_procedimentos mfp
                    INNER JOIN procedimentos p
                        ON p.id = mfp.procedimento_id
                    INNER JOIN tipos_documento td
                        ON td.id = p.tipo_documento_id
                    WHERE mfp.cargo_id = %s
                      AND mfp.funcao_id = %s
                      AND mfp.ativo = 1
                      AND p.ativo = 1
                    ORDER BY td.sigla, p.numero_documento, p.titulo
                """, (cargo_id, funcao['funcao_id']))
    
                procedimentos = cursor.fetchall()
    
                funcoes_vinculadas.append({
                    'id': funcao['id'],
                    'funcao_id': funcao['funcao_id'],
                    'nome': funcao['nome'],
                    'procedimentos': procedimentos
                })
    
            # =========================
            # SETORES DISPONÍVEIS
            # =========================
            cursor.execute("""
                SELECT id, nome
                FROM setores
                WHERE ativo = 1
                ORDER BY nome
            """)
            setores_disponiveis = cursor.fetchall()
    
            # =========================
            # CAMADA 3 - DISPONÍVEIS (SETOR)
            # =========================
            cursor.execute("""
                SELECT
                    p.id,
                    td.sigla,
                    p.numero_documento,
                    p.titulo
                FROM procedimentos p
                INNER JOIN tipos_documento td
                    ON td.id = p.tipo_documento_id
                INNER JOIN procedimento_niveis_aplicacao pna
                    ON pna.procedimento_id = p.id
                WHERE p.ativo = 1
                  AND pna.ativo = 1
                  AND pna.nivel_aplicacao = 'setor'
                ORDER BY td.sigla, p.numero_documento, p.titulo
            """)
            procedimentos_setor_disponiveis = cursor.fetchall()
    
            # =========================
            # SETORES VINCULADOS AO CARGO
            # =========================
            cursor.execute("""
                SELECT
                    mcs.id,
                    mcs.setor_id,
                    s.nome
                FROM matriz_cargo_setores mcs
                INNER JOIN setores s
                    ON s.id = mcs.setor_id
                WHERE mcs.cargo_id = %s
                  AND mcs.ativo = 1
                  AND s.ativo = 1
                ORDER BY s.nome
            """, (cargo_id,))
            setores_raw = cursor.fetchall()
    
            for setor in setores_raw:
                cursor.execute("""
                    SELECT
                        msp.id,
                        td.sigla,
                        p.numero_documento,
                        p.titulo
                    FROM matriz_setor_procedimentos msp
                    INNER JOIN procedimentos p
                        ON p.id = msp.procedimento_id
                    INNER JOIN tipos_documento td
                        ON td.id = p.tipo_documento_id
                    WHERE msp.cargo_id = %s
                      AND msp.setor_id = %s
                      AND msp.ativo = 1
                      AND p.ativo = 1
                    ORDER BY td.sigla, p.numero_documento, p.titulo
                """, (cargo_id, setor['setor_id']))
    
                procedimentos = cursor.fetchall()
    
                setores_vinculados.append({
                    'id': setor['id'],
                    'setor_id': setor['setor_id'],
                    'nome': setor['nome'],
                    'procedimentos': procedimentos
                })
    
        conn.close()
    
        return render_template(
            'matriz_capacitacao.html',
            cargos=cargos,
            cargo_id=cargo_id,
            procedimentos_cargo_disponiveis=procedimentos_cargo_disponiveis,
            procedimentos_cargo=procedimentos_cargo,
            funcoes_disponiveis=funcoes_disponiveis,
            funcoes_vinculadas=funcoes_vinculadas,
            setores_disponiveis=setores_disponiveis,
            setores_vinculados=setores_vinculados,
            procedimentos_funcao_disponiveis=procedimentos_funcao_disponiveis,
            procedimentos_setor_disponiveis=procedimentos_setor_disponiveis
        )
    
    @blueprint.route('/salvar_procedimento_cargo', methods=['POST'])
    @login_required
    @module_required('acesso_procedimentos')
    def salvar_procedimento_cargo():
        cargo_id = request.form.get('cargo_id', type=int)
        procedimento_id = request.form.get('procedimento_id', type=int)
        criado_por = session.get('usuario_id')
    
        if not cargo_id or not procedimento_id:
            flash('Cargo e procedimento são obrigatórios.', 'warning')
            return redirect(url_for('main.matriz_capacitacao', cargo_id=cargo_id))
    
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
    
        erro = _mc_validar_vinculo(
            cursor, cargo_id, procedimento_id=procedimento_id, nivel_aplicacao="cargo"
        )
        if erro:
            conn.close()
            flash(erro, 'warning')
            return redirect(url_for('main.matriz_capacitacao', cargo_id=cargo_id))
    
        cursor.execute("""
            SELECT id
            FROM matriz_cargo_procedimentos
            WHERE cargo_id = %s
              AND procedimento_id = %s
            LIMIT 1
        """, (cargo_id, procedimento_id))
        existente = cursor.fetchone()
    
        if existente:
            cursor.execute("""
                UPDATE matriz_cargo_procedimentos
                SET ativo = 1
                WHERE id = %s
            """, (existente['id'],))
        else:
            cursor.execute("""
                INSERT INTO matriz_cargo_procedimentos
                    (cargo_id, procedimento_id, obrigatorio, criado_por, ativo)
                VALUES (%s, %s, 1, %s, 1)
            """, (cargo_id, procedimento_id, criado_por))
    
        conn.commit()
        conn.close()
    
        flash('Procedimento vinculado ao cargo com sucesso.', 'success')
        return redirect(url_for('main.matriz_capacitacao', cargo_id=cargo_id))
    
    @blueprint.route('/excluir_procedimento_cargo/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_procedimentos')
    def excluir_procedimento_cargo(id):
        cargo_id = request.form.get('cargo_id', type=int)
    
        conn = get_db_connection()
        cursor = conn.cursor()
    
        cursor.execute("""
            UPDATE matriz_cargo_procedimentos
            SET ativo = 0
            WHERE id = %s
        """, (id,))
    
        conn.commit()
        conn.close()
    
        flash('Procedimento removido do cargo.', 'success')
        return redirect(url_for('main.matriz_capacitacao', cargo_id=cargo_id))
    
    @blueprint.route('/adicionar_funcao_cargo', methods=['POST'])
    @login_required
    @module_required('acesso_procedimentos')
    def adicionar_funcao_cargo():
        cargo_id = request.form.get('cargo_id', type=int)
        funcao_id = request.form.get('funcao_id', type=int)
        criado_por = session.get('usuario_id')
    
        if not cargo_id or not funcao_id:
            flash('Cargo e função são obrigatórios.', 'warning')
            return redirect(url_for('main.matriz_capacitacao', cargo_id=cargo_id))
    
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
    
        erro = _mc_validar_vinculo(cursor, cargo_id, funcao_id=funcao_id)
        if erro:
            conn.close()
            flash(erro, 'warning')
            return redirect(url_for('main.matriz_capacitacao', cargo_id=cargo_id))
    
        cursor.execute("""
            SELECT id
            FROM matriz_cargo_funcoes
            WHERE cargo_id = %s
              AND funcao_id = %s
            LIMIT 1
        """, (cargo_id, funcao_id))
        existente = cursor.fetchone()
    
        if existente:
            cursor.execute("""
                UPDATE matriz_cargo_funcoes
                SET ativo = 1
                WHERE id = %s
            """, (existente['id'],))
        else:
            cursor.execute("""
                INSERT INTO matriz_cargo_funcoes
                    (cargo_id, funcao_id, criado_por, ativo)
                VALUES (%s, %s, %s, 1)
            """, (cargo_id, funcao_id, criado_por))
    
        conn.commit()
        conn.close()
    
        flash('Função vinculada ao cargo com sucesso.', 'success')
        return redirect(url_for('main.matriz_capacitacao', cargo_id=cargo_id))
    
    @blueprint.route('/remover_funcao_cargo/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_procedimentos')
    def remover_funcao_cargo(id):
        cargo_id = request.form.get('cargo_id', type=int)
    
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
    
        cursor.execute("""
            SELECT cargo_id, funcao_id
            FROM matriz_cargo_funcoes
            WHERE id = %s
            LIMIT 1
        """, (id,))
        vinculo = cursor.fetchone()
    
        if not vinculo:
            conn.close()
            flash('Função não encontrada.', 'warning')
            return redirect(url_for('main.matriz_capacitacao', cargo_id=cargo_id))
    
        cursor.execute("""
            UPDATE matriz_cargo_funcoes
            SET ativo = 0
            WHERE id = %s
        """, (id,))
    
        cursor.execute("""
            UPDATE matriz_funcao_procedimentos
            SET ativo = 0
            WHERE cargo_id = %s
              AND funcao_id = %s
        """, (vinculo['cargo_id'], vinculo['funcao_id']))
    
        conn.commit()
        conn.close()
    
        flash('Função removida do cargo.', 'success')
        return redirect(url_for('main.matriz_capacitacao', cargo_id=cargo_id or vinculo['cargo_id']))
    
    @blueprint.route('/adicionar_procedimento_funcao', methods=['POST'])
    @login_required
    @module_required('acesso_procedimentos')
    def adicionar_procedimento_funcao():
        cargo_id = request.form.get('cargo_id', type=int)
        funcao_id = request.form.get('funcao_id', type=int)
        procedimento_id = request.form.get('procedimento_id', type=int)
        criado_por = session.get('usuario_id')
    
        if not cargo_id or not funcao_id or not procedimento_id:
            flash('Cargo, função e procedimento são obrigatórios.', 'warning')
            return redirect(url_for('main.matriz_capacitacao', cargo_id=cargo_id))
    
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
    
        erro = _mc_validar_vinculo(
            cursor, cargo_id, procedimento_id=procedimento_id,
            nivel_aplicacao="funcao", funcao_id=funcao_id, exigir_vinculo=True,
        )
        if erro:
            conn.close()
            flash(erro, 'warning')
            return redirect(url_for('main.matriz_capacitacao', cargo_id=cargo_id))
    
        cursor.execute("""
            SELECT id
            FROM matriz_funcao_procedimentos
            WHERE cargo_id = %s
              AND funcao_id = %s
              AND procedimento_id = %s
            LIMIT 1
        """, (cargo_id, funcao_id, procedimento_id))
        existente = cursor.fetchone()
    
        if existente:
            cursor.execute("""
                UPDATE matriz_funcao_procedimentos
                SET ativo = 1
                WHERE id = %s
            """, (existente['id'],))
        else:
            cursor.execute("""
                INSERT INTO matriz_funcao_procedimentos
                    (cargo_id, funcao_id, procedimento_id, obrigatorio, criado_por, ativo)
                VALUES (%s, %s, %s, 1, %s, 1)
            """, (cargo_id, funcao_id, procedimento_id, criado_por))
    
        conn.commit()
        conn.close()
    
        flash('Procedimento vinculado à função com sucesso.', 'success')
        return redirect(url_for('main.matriz_capacitacao', cargo_id=cargo_id))
    
    @blueprint.route('/remover_procedimento_funcao/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_procedimentos')
    def remover_procedimento_funcao(id):
        cargo_id = request.form.get('cargo_id', type=int)
    
        conn = get_db_connection()
        cursor = conn.cursor()
    
        cursor.execute("""
            UPDATE matriz_funcao_procedimentos
            SET ativo = 0
            WHERE id = %s
        """, (id,))
    
        conn.commit()
        conn.close()
    
        flash('Procedimento removido da função.', 'success')
        return redirect(url_for('main.matriz_capacitacao', cargo_id=cargo_id))
    
    @blueprint.route('/adicionar_setor_cargo', methods=['POST'])
    @login_required
    @module_required('acesso_procedimentos')
    def adicionar_setor_cargo():
        cargo_id = request.form.get('cargo_id', type=int)
        setor_id = request.form.get('setor_id', type=int)
        criado_por = session.get('usuario_id')
    
        if not cargo_id or not setor_id:
            flash('Cargo e setor são obrigatórios.', 'warning')
            return redirect(url_for('main.matriz_capacitacao', cargo_id=cargo_id))
    
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
    
        erro = _mc_validar_vinculo(cursor, cargo_id, setor_id=setor_id)
        if erro:
            conn.close()
            flash(erro, 'warning')
            return redirect(url_for('main.matriz_capacitacao', cargo_id=cargo_id))
    
        cursor.execute("""
            SELECT id
            FROM matriz_cargo_setores
            WHERE cargo_id = %s
              AND setor_id = %s
            LIMIT 1
        """, (cargo_id, setor_id))
        existente = cursor.fetchone()
    
        if existente:
            cursor.execute("""
                UPDATE matriz_cargo_setores
                SET ativo = 1
                WHERE id = %s
            """, (existente['id'],))
        else:
            cursor.execute("""
                INSERT INTO matriz_cargo_setores
                    (cargo_id, setor_id, criado_por, ativo)
                VALUES (%s, %s, %s, 1)
            """, (cargo_id, setor_id, criado_por))
    
        conn.commit()
        conn.close()
    
        flash('Setor vinculado ao cargo com sucesso.', 'success')
        return redirect(url_for('main.matriz_capacitacao', cargo_id=cargo_id))
    
    @blueprint.route('/remover_setor_cargo/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_procedimentos')
    def remover_setor_cargo(id):
        cargo_id = request.form.get('cargo_id', type=int)
    
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
    
        cursor.execute("""
            SELECT cargo_id, setor_id
            FROM matriz_cargo_setores
            WHERE id = %s
            LIMIT 1
        """, (id,))
        vinculo = cursor.fetchone()
    
        if not vinculo:
            conn.close()
            flash('Setor não encontrado.', 'warning')
            return redirect(url_for('main.matriz_capacitacao', cargo_id=cargo_id))
    
        cursor.execute("""
            UPDATE matriz_cargo_setores
            SET ativo = 0
            WHERE id = %s
        """, (id,))
    
        cursor.execute("""
            UPDATE matriz_setor_procedimentos
            SET ativo = 0
            WHERE cargo_id = %s
              AND setor_id = %s
        """, (vinculo['cargo_id'], vinculo['setor_id']))
    
        conn.commit()
        conn.close()
    
        flash('Setor removido do cargo.', 'success')
        return redirect(url_for('main.matriz_capacitacao', cargo_id=cargo_id or vinculo['cargo_id']))
    
    @blueprint.route('/adicionar_procedimento_setor', methods=['POST'])
    @login_required
    @module_required('acesso_procedimentos')
    def adicionar_procedimento_setor():
        cargo_id = request.form.get('cargo_id', type=int)
        setor_id = request.form.get('setor_id', type=int)
        procedimento_id = request.form.get('procedimento_id', type=int)
        criado_por = session.get('usuario_id')
    
        if not cargo_id or not setor_id or not procedimento_id:
            flash('Cargo, setor e procedimento são obrigatórios.', 'warning')
            return redirect(url_for('main.matriz_capacitacao', cargo_id=cargo_id))
    
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
    
        erro = _mc_validar_vinculo(
            cursor, cargo_id, procedimento_id=procedimento_id,
            nivel_aplicacao="setor", setor_id=setor_id, exigir_vinculo=True,
        )
        if erro:
            conn.close()
            flash(erro, 'warning')
            return redirect(url_for('main.matriz_capacitacao', cargo_id=cargo_id))
    
        cursor.execute("""
            SELECT id
            FROM matriz_setor_procedimentos
            WHERE cargo_id = %s
              AND setor_id = %s
              AND procedimento_id = %s
            LIMIT 1
        """, (cargo_id, setor_id, procedimento_id))
        existente = cursor.fetchone()
    
        if existente:
            cursor.execute("""
                UPDATE matriz_setor_procedimentos
                SET ativo = 1
                WHERE id = %s
            """, (existente['id'],))
        else:
            cursor.execute("""
                INSERT INTO matriz_setor_procedimentos
                    (cargo_id, setor_id, procedimento_id, obrigatorio, criado_por, ativo)
                VALUES (%s, %s, %s, 1, %s, 1)
            """, (cargo_id, setor_id, procedimento_id, criado_por))
    
        conn.commit()
        conn.close()
    
        flash('Procedimento vinculado ao setor com sucesso.', 'success')
        return redirect(url_for('main.matriz_capacitacao', cargo_id=cargo_id))
    
    @blueprint.route('/remover_procedimento_setor/<int:id>', methods=['POST'])
    @login_required
    @module_required('acesso_procedimentos')
    def remover_procedimento_setor(id):
        cargo_id = request.form.get('cargo_id', type=int)
    
        conn = get_db_connection()
        cursor = conn.cursor()
    
        cursor.execute("""
            UPDATE matriz_setor_procedimentos
            SET ativo = 0
            WHERE id = %s
        """, (id,))
    
        conn.commit()
        conn.close()
    
        flash('Procedimento removido do setor.', 'success')
        return redirect(url_for('main.matriz_capacitacao', cargo_id=cargo_id))
    
    @blueprint.route('/listar_matrizes_capacitacao', methods=['GET'])
    @login_required
    @module_required('acesso_procedimentos')
    def listar_matrizes_capacitacao():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
    
        cargo_id = request.args.get('cargo_id', type=int)
    
        # =========================
        # LISTA DE CARGOS (FILTRO)
        # =========================
        cursor.execute("""
            SELECT id, nome
            FROM cargos
            WHERE ativo = 1
            ORDER BY nome
        """)
        cargos = cursor.fetchall()
    
        # =========================
        # QUERY PRINCIPAL
        # =========================
        query = """
            SELECT
                c.id,
                c.nome,
    
                COUNT(DISTINCT mcp.id) AS qtd_procedimentos,
                COUNT(DISTINCT mcf.id) AS qtd_funcoes,
                COUNT(DISTINCT mcs.id) AS qtd_setores
    
            FROM cargos c
    
            LEFT JOIN matriz_cargo_procedimentos mcp
                ON mcp.cargo_id = c.id AND mcp.ativo = 1
    
            LEFT JOIN matriz_cargo_funcoes mcf
                ON mcf.cargo_id = c.id AND mcf.ativo = 1
    
            LEFT JOIN matriz_cargo_setores mcs
                ON mcs.cargo_id = c.id AND mcs.ativo = 1
    
            WHERE c.ativo = 1
        """
    
        params = []
    
        if cargo_id:
            query += " AND c.id = %s"
            params.append(cargo_id)
    
        query += """
            GROUP BY c.id, c.nome
            ORDER BY c.nome
        """
    
        cursor.execute(query, params)
        matrizes = cursor.fetchall()
    
        conn.close()
    
        return render_template(
            'listar_matrizes_capacitacao.html',
            matrizes=matrizes,
            cargos=cargos,
            cargo_id=cargo_id
        )
    
    @blueprint.route('/exportar_matriz_capacitacao/<int:cargo_id>')
    @login_required
    @module_required('acesso_procedimentos')
    def exportar_matriz_capacitacao(cargo_id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
    
        cursor.execute("""
            SELECT nome
            FROM cargos
            WHERE id = %s
        """, (cargo_id,))
        cargo = cursor.fetchone()
    
        if not cargo:
            conn.close()
            flash('Cargo não encontrado.', 'warning')
            return redirect(url_for('main.listar_matrizes_capacitacao'))
    
        # CAMADA 1 - CARGO
        cursor.execute("""
            SELECT
                'CARGO' AS camada,
                '' AS referencia,
                CONCAT(td.sigla, ' - ', p.numero_documento, ' - ', p.titulo) AS procedimento
            FROM matriz_cargo_procedimentos mcp
            JOIN procedimentos p ON p.id = mcp.procedimento_id
            JOIN tipos_documento td ON td.id = p.tipo_documento_id
            WHERE mcp.cargo_id = %s
              AND mcp.ativo = 1
              AND p.ativo = 1
            ORDER BY td.sigla, p.numero_documento, p.titulo
        """, (cargo_id,))
        cargo_proc = cursor.fetchall()
    
        # CAMADA 2 - FUNÇÃO
        cursor.execute("""
            SELECT
                'FUNÇÃO' AS camada,
                f.nome AS referencia,
                CONCAT(td.sigla, ' - ', p.numero_documento, ' - ', p.titulo) AS procedimento
            FROM matriz_funcao_procedimentos mfp
            JOIN matriz_cargo_funcoes mcf
              ON mcf.cargo_id = mfp.cargo_id
             AND mcf.funcao_id = mfp.funcao_id
             AND mcf.ativo = 1
            JOIN funcoes f ON f.id = mfp.funcao_id
            JOIN procedimentos p ON p.id = mfp.procedimento_id
            JOIN tipos_documento td ON td.id = p.tipo_documento_id
            WHERE mfp.cargo_id = %s
              AND mfp.ativo = 1
              AND p.ativo = 1
            ORDER BY f.nome, td.sigla, p.numero_documento, p.titulo
        """, (cargo_id,))
        func_proc = cursor.fetchall()
    
        # CAMADA 3 - SETOR
        cursor.execute("""
            SELECT
                'SETOR' AS camada,
                s.nome AS referencia,
                CONCAT(td.sigla, ' - ', p.numero_documento, ' - ', p.titulo) AS procedimento
            FROM matriz_setor_procedimentos msp
            JOIN matriz_cargo_setores mcs
              ON mcs.cargo_id = msp.cargo_id
             AND mcs.setor_id = msp.setor_id
             AND mcs.ativo = 1
            JOIN setores s ON s.id = msp.setor_id
            JOIN procedimentos p ON p.id = msp.procedimento_id
            JOIN tipos_documento td ON td.id = p.tipo_documento_id
            WHERE msp.cargo_id = %s
              AND msp.ativo = 1
              AND p.ativo = 1
            ORDER BY s.nome, td.sigla, p.numero_documento, p.titulo
        """, (cargo_id,))
        setor_proc = cursor.fetchall()
    
        conn.close()
    
        dados = cargo_proc + func_proc + setor_proc
    
        wb = Workbook()
        ws = wb.active
        ws.title = "Matriz"
    
        # Cabeçalhos
        ws.append(["Camada", "Referência", "Procedimento"])
    
        # Linhas
        for linha in dados:
            ws.append([
                linha["camada"],
                linha["referencia"],
                linha["procedimento"]
            ])
    
        # Ajuste simples de largura
        ws.column_dimensions["A"].width = 15
        ws.column_dimensions["B"].width = 30
        ws.column_dimensions["C"].width = 80
    
        output = BytesIO()
        wb.save(output)
        output.seek(0)
    
        nome_arquivo = f"matriz_{cargo['nome'].replace(' ', '_')}.xlsx"
    
        return send_file(
            output,
            as_attachment=True,
            download_name=nome_arquivo,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    
    @blueprint.route('/verificar_matriz_funcionario', methods=['GET'])
    @login_required
    @module_required('acesso_procedimentos')
    def verificar_matriz_funcionario():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
    
        usuario_id = request.args.get('usuario_id', type=int)
    
        usuarios = []
        usuario = None
        procedimentos_cargo = []
        funcoes_com_procedimentos = []
        setores_com_procedimentos = []
    
        # -------------------------------------------------
        # Helpers internos
        # -------------------------------------------------
        def get_table_columns(table_name):
            try:
                cursor.execute(f"SHOW COLUMNS FROM {table_name}")
                return [col["Field"] for col in cursor.fetchall()]
            except Exception:
                return []
    
        def table_exists(table_name):
            try:
                cursor.execute("SHOW TABLES LIKE %s", (table_name,))
                return cursor.fetchone() is not None
            except Exception:
                return False
    
        def first_existing(columns, options):
            for option in options:
                if option in columns:
                    return option
            return None
    
        def to_date(value):
            if value is None:
                return None
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, date):
                return value
            if isinstance(value, str):
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
                    try:
                        return datetime.strptime(value, fmt).date()
                    except ValueError:
                        continue
            return None
    
        def resolver_campos_procedimento():
            colunas_procedimentos = get_table_columns("procedimentos")
            colunas_tipos_documento = get_table_columns("tipos_documento")
    
            if "titulo" in colunas_procedimentos:
                campo_titulo = "p.titulo"
            elif "titulo_documento" in colunas_procedimentos:
                campo_titulo = "p.titulo_documento"
            elif "nome" in colunas_procedimentos:
                campo_titulo = "p.nome"
            else:
                campo_titulo = "''"
    
            if "numero_documento" in colunas_procedimentos:
                campo_numero = "p.numero_documento"
            else:
                campo_numero = "''"
    
            join_tipo_documento = ""
            if "sigla" in colunas_procedimentos:
                campo_sigla = "p.sigla"
            elif "tipo_documento_id" in colunas_procedimentos and "sigla" in colunas_tipos_documento:
                join_tipo_documento = "LEFT JOIN tipos_documento td ON td.id = p.tipo_documento_id"
                campo_sigla = "td.sigla"
            else:
                campo_sigla = "''"
    
            filtro_ativo_procedimento = ""
            if "ativo" in colunas_procedimentos:
                filtro_ativo_procedimento = "AND p.ativo = 1"
    
            return {
                "campo_titulo": campo_titulo,
                "campo_numero": campo_numero,
                "campo_sigla": campo_sigla,
                "join_tipo_documento": join_tipo_documento,
                "filtro_ativo_procedimento": filtro_ativo_procedimento
            }
    
        status_procedimentos = {}
    
        def obter_status_procedimento(usuario_id_local, procedimento_id):
            """
            Retorna: 'Realizado', 'Vencido' ou 'Pendente'
            """
            chave_status = (usuario_id_local, procedimento_id)
            if chave_status in status_procedimentos:
                return status_procedimentos[chave_status]
    
            if not table_exists("treinamentos_realizados_participantes") or not table_exists("treinamentos_realizados"):
                return "Pendente"
    
            cols_trp = get_table_columns("treinamentos_realizados_participantes")
            cols_trr = get_table_columns("treinamentos_realizados")
            cols_t = get_table_columns("treinamentos") if table_exists("treinamentos") else []
    
            # Coluna do usuário/participante
            usuario_col_trp = first_existing(cols_trp, ["usuario_id", "participante_id", "colaborador_id"])
            if not usuario_col_trp:
                return "Pendente"
    
            # Chaves de ligação
            trp_to_trr = first_existing(cols_trp, [
                "treinamento_realizado_id",
                "treinamentos_realizados_id",
                "realizado_id"
            ])
    
            trr_pk = first_existing(cols_trr, ["id"])
            if not trp_to_trr or not trr_pk:
                return "Pendente"
    
            if "procedimento_revisao_id" not in cols_trr or not table_exists("procedimento_revisoes"):
                return "Pendente"
    
            cursor.execute("""
                SELECT id
                FROM procedimento_revisoes
                WHERE procedimento_id = %s
                  AND vigente = 1
                  AND requer_treinamento = 1
                ORDER BY data_revisao DESC, id DESC
                LIMIT 1
            """, (procedimento_id,))
            revisao_vigente = cursor.fetchone()
            if not revisao_vigente:
                status_procedimentos[chave_status] = "Não requerido"
                return status_procedimentos[chave_status]
    
            # Como relacionar o realizado ao procedimento
            join_treinamentos = ""
            filtro_procedimento = ""
            params = [usuario_id_local]
    
            if "procedimento_id" in cols_trr:
                filtro_procedimento = "trr.procedimento_id = %s"
                params.append(procedimento_id)
            else:
                trr_to_t = first_existing(cols_trr, ["treinamento_id"])
                t_pk = first_existing(cols_t, ["id"]) if cols_t else None
                t_procedimento = first_existing(cols_t, ["procedimento_id"])
    
                if trr_to_t and t_pk and t_procedimento:
                    join_treinamentos = f"INNER JOIN treinamentos t ON t.{t_pk} = trr.{trr_to_t}"
                    filtro_procedimento = "t.procedimento_id = %s"
                    params.append(procedimento_id)
                else:
                    return "Pendente"
    
            filtro_revisao = "AND trr.procedimento_revisao_id = %s"
            params.append(revisao_vigente["id"])
    
            # Data de realização
            data_realizacao_col = first_existing(cols_trr, [
                "data_realizacao",
                "data_treinamento",
                "realizado_em",
                "data",
                "created_at"
            ])
    
            # Data de validade/vencimento já pronta
            validade_col = first_existing(cols_trr, [
                "data_validade",
                "validade_ate",
                "data_vencimento",
                "vencimento"
            ])
    
            # Dias de validade no treinamento
            validade_dias_col = first_existing(cols_t, [
                "validade_dias",
                "dias_validade",
                "prazo_validade_dias"
            ]) if cols_t else None
    
            # Filtros ativos
            filtro_ativo_trp = "AND trp.ativo = 1" if "ativo" in cols_trp else ""
            filtro_ativo_trr = "AND trr.ativo = 1" if "ativo" in cols_trr else ""
            filtro_ativo_t = "AND t.ativo = 1" if "ativo" in cols_t and join_treinamentos else ""
    
            select_data_realizacao = f"trr.{data_realizacao_col} AS data_realizacao" if data_realizacao_col else "NULL AS data_realizacao"
            select_validade = f"trr.{validade_col} AS data_validade" if validade_col else "NULL AS data_validade"
            select_validade_dias = f"t.{validade_dias_col} AS validade_dias" if validade_dias_col and join_treinamentos else "NULL AS validade_dias"
    
            order_by = f"ORDER BY trr.{data_realizacao_col} DESC, trr.id DESC" if data_realizacao_col else "ORDER BY trr.id DESC"
    
            query = f"""
                SELECT
                    trr.id,
                    {select_data_realizacao},
                    {select_validade},
                    {select_validade_dias}
                FROM treinamentos_realizados_participantes trp
                INNER JOIN treinamentos_realizados trr
                    ON trr.{trr_pk} = trp.{trp_to_trr}
                {join_treinamentos}
                WHERE trp.{usuario_col_trp} = %s
                  AND {filtro_procedimento}
                  {filtro_revisao}
                  {filtro_ativo_trp}
                  {filtro_ativo_trr}
                  {filtro_ativo_t}
                {order_by}
                LIMIT 1
            """
    
            cursor.execute(query, tuple(params))
            registro = cursor.fetchone()
    
            if not registro:
                status_procedimentos[chave_status] = "Pendente"
                return status_procedimentos[chave_status]
    
            data_validade = to_date(registro.get("data_validade"))
            data_realizacao = to_date(registro.get("data_realizacao"))
            validade_dias = registro.get("validade_dias")
    
            if not data_validade and data_realizacao and validade_dias:
                try:
                    validade_dias = int(validade_dias)
                    data_validade = data_realizacao + timedelta(days=validade_dias)
                except Exception:
                    data_validade = None
    
            hoje = date.today()
    
            if not data_validade:
                status_procedimentos[chave_status] = "Pendente"
            elif data_validade < hoje:
                status_procedimentos[chave_status] = "Vencido"
            else:
                status_procedimentos[chave_status] = "Realizado"
    
            return status_procedimentos[chave_status]
    
        def aplicar_status(lista_procedimentos):
            for item in lista_procedimentos:
                status = obter_status_procedimento(usuario_id, item["id"])
                if not item.get("obrigatorio") and status in ("Pendente", "Vencido"):
                    status = "Opcional"
                item["status"] = status
            return lista_procedimentos
    
        def buscar_procedimentos_cargo(cargo_id):
            if not cargo_id:
                return []
    
            if not table_exists("matriz_cargo_procedimentos"):
                return []
    
            colunas_mcp = get_table_columns("matriz_cargo_procedimentos")
            cfg = resolver_campos_procedimento()
    
            filtro_ativo_mcp = "AND mcp.ativo = 1" if "ativo" in colunas_mcp else ""
    
            query = f"""
                SELECT
                    p.id,
                    {cfg['campo_sigla']} AS sigla,
                    {cfg['campo_numero']} AS numero_documento,
                    {cfg['campo_titulo']} AS titulo,
                    {'mcp.obrigatorio' if 'obrigatorio' in colunas_mcp else '1'} AS obrigatorio
                FROM matriz_cargo_procedimentos mcp
                INNER JOIN procedimentos p ON p.id = mcp.procedimento_id
                {cfg['join_tipo_documento']}
                WHERE mcp.cargo_id = %s
                  {filtro_ativo_mcp}
                  {cfg['filtro_ativo_procedimento']}
                ORDER BY {cfg['campo_numero']}, p.id
            """
            cursor.execute(query, (cargo_id,))
            return aplicar_status(cursor.fetchall())
    
        def buscar_procedimentos_funcao(cargo_id, funcao_id):
            if not cargo_id or not funcao_id:
                return []
    
            cfg = resolver_campos_procedimento()
            colunas_mfp = get_table_columns("matriz_funcao_procedimentos")
            filtro_ativo_mfp = "AND mfp.ativo = 1" if "ativo" in colunas_mfp else ""
    
            query = f"""
                SELECT
                    p.id,
                    {cfg['campo_sigla']} AS sigla,
                    {cfg['campo_numero']} AS numero_documento,
                    {cfg['campo_titulo']} AS titulo,
                    {'mfp.obrigatorio' if 'obrigatorio' in colunas_mfp else '1'} AS obrigatorio
                FROM matriz_funcao_procedimentos mfp
                INNER JOIN matriz_cargo_funcoes mcf
                    ON mcf.cargo_id = mfp.cargo_id
                   AND mcf.funcao_id = mfp.funcao_id
                   AND mcf.ativo = 1
                INNER JOIN procedimentos p ON p.id = mfp.procedimento_id
                {cfg['join_tipo_documento']}
                WHERE mfp.cargo_id = %s
                  AND mfp.funcao_id = %s
                  {filtro_ativo_mfp}
                  {cfg['filtro_ativo_procedimento']}
                ORDER BY {cfg['campo_numero']}, p.id
            """
            cursor.execute(query, (cargo_id, funcao_id))
            return aplicar_status(cursor.fetchall())
    
        def buscar_procedimentos_setor(cargo_id, setor_id):
            if not cargo_id or not setor_id:
                return []
    
            if not table_exists("matriz_setor_procedimentos"):
                return []
    
            colunas_msp = get_table_columns("matriz_setor_procedimentos")
            if "setor_id" not in colunas_msp:
                return []
    
            cfg = resolver_campos_procedimento()
            filtro_ativo_msp = "AND msp.ativo = 1" if "ativo" in colunas_msp else ""
    
            query = f"""
                SELECT
                    p.id,
                    {cfg['campo_sigla']} AS sigla,
                    {cfg['campo_numero']} AS numero_documento,
                    {cfg['campo_titulo']} AS titulo,
                    {'msp.obrigatorio' if 'obrigatorio' in colunas_msp else '1'} AS obrigatorio
                FROM matriz_setor_procedimentos msp
                INNER JOIN matriz_cargo_setores mcs
                    ON mcs.cargo_id = msp.cargo_id
                   AND mcs.setor_id = msp.setor_id
                   AND mcs.ativo = 1
                INNER JOIN procedimentos p ON p.id = msp.procedimento_id
                {cfg['join_tipo_documento']}
                WHERE msp.cargo_id = %s
                  AND msp.setor_id = %s
                  {filtro_ativo_msp}
                  {cfg['filtro_ativo_procedimento']}
                ORDER BY {cfg['campo_numero']}, p.id
            """
            cursor.execute(query, (cargo_id, setor_id))
            return aplicar_status(cursor.fetchall())
    
        # -------------------------------------------------
        # Lista de usuários
        # -------------------------------------------------
        cursor.execute("""
            SELECT
                u.id,
                u.matricula,
                u.nome
            FROM usuarios u
            WHERE u.ativo = 1
            ORDER BY u.nome
        """)
        usuarios = cursor.fetchall()
    
        # -------------------------------------------------
        # Dados do usuário selecionado
        # -------------------------------------------------
        if usuario_id:
            cargo_nome_expr = "CAST(u.cargo_id AS CHAR)"
            if table_exists("cargos"):
                colunas_cargos = get_table_columns("cargos")
                if "nome" in colunas_cargos:
                    cargo_nome_expr = "c.nome"
                elif "descricao" in colunas_cargos:
                    cargo_nome_expr = "c.descricao"
    
                cursor.execute(f"""
                    SELECT
                        u.id,
                        u.nome,
                        u.matricula,
                        u.cargo_id,
                        {cargo_nome_expr} AS cargo_nome
                    FROM usuarios u
                    LEFT JOIN cargos c ON c.id = u.cargo_id
                    WHERE u.id = %s
                      AND u.ativo = 1
                    LIMIT 1
                """, (usuario_id,))
            else:
                cursor.execute("""
                    SELECT
                        u.id,
                        u.nome,
                        u.matricula,
                        u.cargo_id,
                        CAST(u.cargo_id AS CHAR) AS cargo_nome
                    FROM usuarios u
                    WHERE u.id = %s
                      AND u.ativo = 1
                    LIMIT 1
                """, (usuario_id,))
    
            usuario = cursor.fetchone()
    
            if usuario:
                procedimentos_cargo = buscar_procedimentos_cargo(usuario["cargo_id"])
    
                cursor.execute("""
                    SELECT DISTINCT
                        f.id,
                        f.nome
                    FROM usuario_funcoes_setores ufs
                    INNER JOIN funcoes f ON f.id = ufs.funcao_id
                    WHERE ufs.usuario_id = %s
                      AND ufs.ativo = 1
                      AND ufs.funcao_id IS NOT NULL
                    ORDER BY f.nome
                """, (usuario_id,))
                funcoes_usuario = cursor.fetchall()
    
                for funcao in funcoes_usuario:
                    funcoes_com_procedimentos.append({
                        "id": funcao["id"],
                        "nome": funcao["nome"],
                        "procedimentos": buscar_procedimentos_funcao(usuario["cargo_id"], funcao["id"])
                    })
    
                cursor.execute("""
                    SELECT DISTINCT
                        s.id,
                        s.nome
                    FROM usuario_funcoes_setores ufs
                    INNER JOIN setores s ON s.id = ufs.setor_id
                    WHERE ufs.usuario_id = %s
                      AND ufs.ativo = 1
                      AND ufs.setor_id IS NOT NULL
                    ORDER BY s.nome
                """, (usuario_id,))
                setores_usuario = cursor.fetchall()
    
                for setor in setores_usuario:
                    setores_com_procedimentos.append({
                        "id": setor["id"],
                        "nome": setor["nome"],
                        "procedimentos": buscar_procedimentos_setor(usuario["cargo_id"], setor["id"])
                    })
    
        conn.close()
    
        return render_template(
            "verificar_matriz_funcionario.html",
            usuarios=usuarios,
            usuario=usuario,
            usuario_id=usuario_id,
            procedimentos_cargo=procedimentos_cargo,
            funcoes_com_procedimentos=funcoes_com_procedimentos,
            setores_com_procedimentos=setores_com_procedimentos
        )
    

