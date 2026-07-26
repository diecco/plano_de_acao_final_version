from flask import flash, redirect, render_template, request, url_for
from flask_mail import Message
from werkzeug.security import generate_password_hash

from app import mail
from app.decorators import admin_required, login_required
from app.utils.db import get_db_connection


def register_usuarios_routes(blueprint):
    @blueprint.route('/usuarios', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def usuarios():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == 'POST':
            nome = (request.form.get('nome') or '').strip()
            matricula = (request.form.get('matricula') or '').strip() or None
            uid_rfid = (request.form.get('uid_rfid') or '').strip() or None
            email = (request.form.get('email') or '').strip() or None
            superintendencia_id = request.form.get('superintendencia_id') or None
            centro_custos_id = request.form.get('centro_custos_id') or None
            cargo_id = request.form.get('cargo_id') or None

            funcao_ids = request.form.getlist('funcao_ids[]')
            setor_ids = request.form.getlist('setor_ids[]')

            tem_acesso_sistema = (
                1 if request.form.get('tem_acesso_sistema') == '1' else 0
            )

            pode_ser_instrutor = (
                1 if request.form.get('pode_ser_instrutor') == '1' else 0
            )

            responsavel_revisao_padrao = (
                1
                if request.form.get('responsavel_revisao_padrao') == '1'
                else 0
            )

            pode_criar_agendamento_ssma = (
                1
                if request.form.get('pode_criar_agendamento_ssma') == '1'
                else 0
            )

            pode_ser_lider_ssma = (
                1
                if request.form.get('pode_ser_lider_ssma') == '1'
                else 0
            )

            perfil = (request.form.get('perfil') or '').strip() or None
            senha_plana = request.form.get('senha') or None

            precisa_alterar_senha = (
                1 if request.form.get('precisa_alterar_senha') else 0
            )

            acesso_plano_acao = (
                1 if request.form.get('acesso_plano_acao') else 0
            )

            acesso_ssma = (
                1 if request.form.get('acesso_ssma') else 0
            )

            acesso_melhoria = (
                1 if request.form.get('acesso_melhoria') else 0
            )

            acesso_gestao_pessoas = (
                1 if request.form.get('acesso_gestao_pessoas') else 0
            )

            acesso_treinamentos = (
                1 if request.form.get('acesso_treinamentos') else 0
            )

            acesso_procedimentos = (
                1 if request.form.get('acesso_procedimentos') else 0
            )

            acesso_pcpm = (
                1 if request.form.get('acesso_pcpm') else 0
            )

            acesso_detectores_gas = (
                1 if request.form.get('acesso_detectores_gas') else 0
            )

            if not nome:
                flash('Informe o nome do funcionário.', 'danger')
                conn.close()
                return redirect(url_for('main.usuarios'))

            if not matricula:
                flash('Informe a matrícula do funcionário.', 'danger')
                conn.close()
                return redirect(url_for('main.usuarios'))

            if not matricula.isdigit():
                flash(
                    'A matrícula deve conter apenas números.',
                    'danger'
                )
                conn.close()
                return redirect(url_for('main.usuarios'))

            if len(matricula) != 6:
                flash(
                    'A matrícula deve conter exatamente 6 dígitos.',
                    'danger'
                )
                conn.close()
                return redirect(url_for('main.usuarios'))

            if not centro_custos_id:
                flash('Selecione o centro de custos.', 'danger')
                conn.close()
                return redirect(url_for('main.usuarios'))

            if not superintendencia_id:
                flash(
                    'Selecione um centro de custos válido para preencher '
                    'a superintendência.',
                    'danger'
                )
                conn.close()
                return redirect(url_for('main.usuarios'))

            if not cargo_id:
                flash('Selecione o cargo do funcionário.', 'danger')
                conn.close()
                return redirect(url_for('main.usuarios'))

            if len(funcao_ids) != len(setor_ids):
                flash(
                    'Erro ao processar as habilitações informadas.',
                    'danger'
                )
                conn.close()
                return redirect(url_for('main.usuarios'))

            if (
                responsavel_revisao_padrao == 1
                and tem_acesso_sistema != 1
            ):
                flash(
                    'O responsável por revisão de padrão precisa '
                    'possuir acesso ao TrackPlan.',
                    'danger'
                )
                conn.close()
                return redirect(url_for('main.usuarios'))

            if tem_acesso_sistema == 1:
                if not email:
                    flash(
                        'Funcionários com acesso ao sistema devem '
                        'possuir e-mail.',
                        'danger'
                    )
                    conn.close()
                    return redirect(url_for('main.usuarios'))

                if not perfil:
                    flash(
                        'Funcionários com acesso ao sistema devem '
                        'possuir perfil.',
                        'danger'
                    )
                    conn.close()
                    return redirect(url_for('main.usuarios'))

                if not senha_plana:
                    flash(
                        'Funcionários com acesso ao sistema devem '
                        'possuir senha inicial.',
                        'danger'
                    )
                    conn.close()
                    return redirect(url_for('main.usuarios'))

            else:
                perfil = None
                senha_plana = None
                precisa_alterar_senha = 0

                acesso_plano_acao = 0
                acesso_ssma = 0
                acesso_melhoria = 0
                acesso_gestao_pessoas = 0
                acesso_treinamentos = 0
                acesso_procedimentos = 0
                acesso_pcpm = 0
                acesso_detectores_gas = 0

                responsavel_revisao_padrao = 0
                pode_criar_agendamento_ssma = 0
                pode_ser_lider_ssma = 0

            try:
                cursor.execute("""
                    SELECT id
                    FROM usuarios
                    WHERE matricula = %s
                """, (matricula,))

                matricula_existente = cursor.fetchone()

                if matricula_existente:
                    flash(
                        'Já existe um funcionário cadastrado com '
                        'esta matrícula.',
                        'warning'
                    )
                    conn.close()
                    return redirect(url_for('main.usuarios'))

                if email:
                    cursor.execute("""
                        SELECT id
                        FROM usuarios
                        WHERE email = %s
                    """, (email,))

                    usuario_existente = cursor.fetchone()

                    if usuario_existente:
                        flash(
                            'Já existe um funcionário cadastrado '
                            'com este e-mail.',
                            'warning'
                        )
                        conn.close()
                        return redirect(url_for('main.usuarios'))

                if uid_rfid:
                    cursor.execute("""
                        SELECT id
                        FROM usuarios
                        WHERE uid_rfid = %s
                    """, (uid_rfid,))

                    rfid_existente = cursor.fetchone()

                    if rfid_existente:
                        flash(
                            'Já existe um funcionário cadastrado '
                            'com este RFID.',
                            'warning'
                        )
                        conn.close()
                        return redirect(url_for('main.usuarios'))

                if responsavel_revisao_padrao == 1:
                    cursor.execute("""
                        SELECT id, nome
                        FROM usuarios
                        WHERE responsavel_revisao_padrao = 1
                          AND ativo = 1
                          AND centro_custos_id = %s
                        LIMIT 1
                    """, (centro_custos_id,))

                    responsavel_existente = cursor.fetchone()

                    if responsavel_existente:
                        flash(
                            f"Já existe um responsável ativo por revisão "
                            f"de padrão neste centro de custo: "
                            f"{responsavel_existente['nome']}.",
                            'warning'
                        )
                        conn.close()
                        return redirect(url_for('main.usuarios'))

                hash_senha = None

                if senha_plana:
                    hash_senha = generate_password_hash(
                        senha_plana,
                        method='pbkdf2:sha256'
                    )

                cursor.execute("""
                    INSERT INTO usuarios (
                        nome,
                        matricula,
                        uid_rfid,
                        email,
                        superintendencia_id,
                        centro_custos_id,
                        cargo_id,
                        senha_hash,
                        perfil,
                        ativo,
                        precisa_alterar_senha,
                        tem_acesso_sistema,
                        pode_ser_instrutor,
                        responsavel_revisao_padrao,
                        pode_criar_agendamento_ssma,
                        pode_ser_lider_ssma,
                        acesso_plano_acao,
                        acesso_ssma,
                        acesso_melhoria,
                        acesso_gestao_pessoas,
                        acesso_treinamentos,
                        acesso_procedimentos,
                        acesso_pcpm,
                        acesso_detectores_gas
                    )
                    VALUES (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        1,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                """, (
                    nome,
                    matricula,
                    uid_rfid,
                    email,
                    superintendencia_id,
                    centro_custos_id,
                    cargo_id,
                    hash_senha,
                    perfil,
                    precisa_alterar_senha,
                    tem_acesso_sistema,
                    pode_ser_instrutor,
                    responsavel_revisao_padrao,
                    pode_criar_agendamento_ssma,
                    pode_ser_lider_ssma,
                    acesso_plano_acao,
                    acesso_ssma,
                    acesso_melhoria,
                    acesso_gestao_pessoas,
                    acesso_treinamentos,
                    acesso_procedimentos,
                    acesso_pcpm,
                    acesso_detectores_gas
                ))

                usuario_id = cursor.lastrowid
                combinacoes_inseridas = set()

                for funcao_id, setor_id in zip(
                    funcao_ids,
                    setor_ids
                ):
                    funcao_id = (funcao_id or '').strip()
                    setor_id = (setor_id or '').strip()

                    if not funcao_id or not setor_id:
                        continue

                    chave = (funcao_id, setor_id)

                    if chave in combinacoes_inseridas:
                        continue

                    cursor.execute("""
                        INSERT INTO usuario_funcoes_setores (
                            usuario_id,
                            funcao_id,
                            setor_id,
                            ativo
                        )
                        VALUES (%s, %s, %s, 1)
                    """, (
                        usuario_id,
                        funcao_id,
                        setor_id
                    ))

                    combinacoes_inseridas.add(chave)

                conn.commit()

                if (
                    tem_acesso_sistema == 1
                    and email
                    and senha_plana
                ):
                    try:
                        link_login = url_for(
                            'main.login',
                            _external=True
                        )

                        msg = Message(
                            subject=(
                                'Bem-vindo ao TrackPlan — '
                                'dados de acesso'
                            ),
                            recipients=[email]
                        )

                        msg.html = f"""
                        <div style="
                            font-family: Arial, sans-serif;
                            font-size: 15px;
                            color:#333;
                        ">
                          <div style="
                              text-align:center;
                              margin-bottom:18px;
                          ">
                            <img
                                src="https://www.trackplan.com.br/imagens/barra_email.png"
                                alt="TrackPlan"
                                style="height:50px;"
                            >
                          </div>

                          <p>Olá <strong>{nome}</strong>,</p>

                          <p>
                            Seu acesso ao <strong>TrackPlan</strong>
                            foi criado com sucesso.
                          </p>

                          <div style="
                              background:#f7f7f7;
                              border:1px solid #eee;
                              border-radius:6px;
                              padding:12px 14px;
                              margin:12px 0;
                          ">
                            <p>
                                <strong>Endereço:</strong>
                                <a
                                    href="{link_login}"
                                    target="_blank"
                                >
                                    {link_login}
                                </a>
                            </p>

                            <p>
                                <strong>Usuário:</strong>
                                {email}
                            </p>

                            <p>
                                <strong>Senha inicial:</strong>
                                {senha_plana}
                            </p>
                          </div>

                          <p style="
                              margin:22px 0;
                              text-align:center;
                          ">
                            <a
                                href="{link_login}"
                                target="_blank"
                                style="
                                    display:inline-block;
                                    background:#ea6a23;
                                    color:#fff;
                                    text-decoration:none;
                                    padding:10px 18px;
                                    border-radius:5px;
                                "
                            >
                                Acessar o TrackPlan
                            </a>
                          </p>

                          <p style="
                              font-size:13px;
                              color:#666;
                          ">
                            Equipe TrackPlan
                          </p>
                        </div>
                        """

                        mail.send(msg)

                        flash(
                            'Funcionário cadastrado e e-mail de '
                            'boas-vindas enviado!',
                            'success'
                        )

                    except Exception:
                        flash(
                            'Funcionário cadastrado, mas não foi '
                            'possível enviar o e-mail de boas-vindas.',
                            'warning'
                        )

                else:
                    flash(
                        'Funcionário cadastrado com sucesso!',
                        'success'
                    )

            except Exception as e:
                conn.rollback()
                flash(
                    f'Erro ao cadastrar funcionário: {e}',
                    'danger'
                )

            finally:
                conn.close()

            return redirect(url_for('main.usuarios'))

        cursor.execute("""
            SELECT
                cc.id,
                cc.codigo,
                cc.descricao,
                s.id AS superintendencia_id,
                s.nome AS superintendencia_nome
            FROM centros_custos cc
            LEFT JOIN superintendencias s
                ON s.id = cc.superintendencia_id
            WHERE cc.ativo = 1
            ORDER BY cc.codigo, cc.descricao
        """)
        centros_custos = cursor.fetchall()

        cursor.execute("""
            SELECT id, nome
            FROM setores
            WHERE ativo = 1
            ORDER BY nome
        """)
        setores = cursor.fetchall()

        cursor.execute("""
            SELECT id, nome
            FROM cargos
            WHERE ativo = 1
            ORDER BY nome
        """)
        cargos = cursor.fetchall()

        cursor.execute("""
            SELECT id, nome
            FROM funcoes
            WHERE ativo = 1
            ORDER BY nome
        """)
        funcoes = cursor.fetchall()

        conn.close()

        return render_template(
            'usuarios.html',
            centros_custos=centros_custos,
            setores=setores,
            cargos=cargos,
            funcoes=funcoes
        )


    @blueprint.route(
        '/editar_usuario/<int:id>',
        methods=['GET', 'POST']
    )
    @login_required
    @admin_required
    def editar_usuario(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                u.*,
                s.nome AS nome_superintendencia
            FROM usuarios u
            LEFT JOIN superintendencias s
                ON s.id = u.superintendencia_id
            WHERE u.id = %s
        """, (id,))

        usuario = cursor.fetchone()

        if not usuario:
            conn.close()
            flash(
                'Funcionário não encontrado.',
                'warning'
            )
            return redirect(url_for('main.listar_usuarios'))

        tinha_acesso = (
            1 if usuario.get('tem_acesso_sistema') else 0
        )

        if request.method == 'POST':
            nome = (request.form.get('nome') or '').strip()
            matricula = (
                request.form.get('matricula') or ''
            ).strip() or None

            uid_rfid = (
                request.form.get('uid_rfid') or ''
            ).strip() or None

            email = (
                request.form.get('email') or ''
            ).strip() or None

            superintendencia_id = (
                request.form.get('superintendencia_id')
                or None
            )

            centro_custos_id = (
                request.form.get('centro_custos_id')
                or None
            )

            cargo_id = (
                request.form.get('cargo_id')
                or None
            )

            funcao_ids = request.form.getlist('funcao_ids[]')
            setor_ids = request.form.getlist('setor_ids[]')

            tem_acesso_sistema = (
                1
                if request.form.get('tem_acesso_sistema') == '1'
                else 0
            )

            pode_ser_instrutor = (
                1
                if request.form.get('pode_ser_instrutor') == '1'
                else 0
            )

            responsavel_revisao_padrao = (
                1
                if request.form.get(
                    'responsavel_revisao_padrao'
                ) == '1'
                else 0
            )

            pode_criar_agendamento_ssma = (
                1
                if request.form.get(
                    'pode_criar_agendamento_ssma'
                ) == '1'
                else 0
            )

            pode_ser_lider_ssma = (
                1
                if request.form.get(
                    'pode_ser_lider_ssma'
                ) == '1'
                else 0
            )

            perfil = (
                request.form.get('perfil') or ''
            ).strip() or None

            nova_senha = (
                request.form.get('nova_senha')
                or None
            )

            precisa_alterar_senha = (
                1
                if request.form.get('precisa_alterar_senha')
                else 0
            )

            ativo = (
                1
                if request.form.get('ativo', '1') == '1'
                else 0
            )

            acesso_plano_acao = (
                1 if request.form.get('acesso_plano_acao') else 0
            )

            acesso_ssma = (
                1 if request.form.get('acesso_ssma') else 0
            )

            acesso_melhoria = (
                1 if request.form.get('acesso_melhoria') else 0
            )

            acesso_gestao_pessoas = (
                1
                if request.form.get('acesso_gestao_pessoas')
                else 0
            )

            acesso_treinamentos = (
                1
                if request.form.get('acesso_treinamentos')
                else 0
            )

            acesso_procedimentos = (
                1
                if request.form.get('acesso_procedimentos')
                else 0
            )

            acesso_pcpm = (
                1 if request.form.get('acesso_pcpm') else 0
            )

            acesso_detectores_gas = (
                1 if request.form.get('acesso_detectores_gas') else 0
            )

            if not nome:
                flash(
                    'Informe o nome do funcionário.',
                    'danger'
                )
                conn.close()
                return redirect(
                    url_for('main.editar_usuario', id=id)
                )

            if not matricula:
                flash(
                    'Informe a matrícula do funcionário.',
                    'danger'
                )
                conn.close()
                return redirect(
                    url_for('main.editar_usuario', id=id)
                )

            if not matricula.isdigit():
                flash(
                    'A matrícula deve conter apenas números.',
                    'danger'
                )
                conn.close()
                return redirect(
                    url_for('main.editar_usuario', id=id)
                )

            if len(matricula) != 6:
                flash(
                    'A matrícula deve conter exatamente 6 dígitos.',
                    'danger'
                )
                conn.close()
                return redirect(
                    url_for('main.editar_usuario', id=id)
                )

            if uid_rfid:
                cursor.execute("""
                    SELECT id
                    FROM usuarios
                    WHERE uid_rfid = %s
                      AND id <> %s
                """, (
                    uid_rfid,
                    id
                ))

                rfid_existente = cursor.fetchone()

                if rfid_existente:
                    flash(
                        'Já existe outro funcionário cadastrado '
                        'com este RFID.',
                        'warning'
                    )
                    conn.close()
                    return redirect(
                        url_for('main.editar_usuario', id=id)
                    )

            if not centro_custos_id:
                flash(
                    'Selecione o centro de custos.',
                    'danger'
                )
                conn.close()
                return redirect(
                    url_for('main.editar_usuario', id=id)
                )

            if not superintendencia_id:
                flash(
                    'Selecione um centro de custos válido para '
                    'preencher a superintendência.',
                    'danger'
                )
                conn.close()
                return redirect(
                    url_for('main.editar_usuario', id=id)
                )

            if not cargo_id:
                flash(
                    'Selecione o cargo do funcionário.',
                    'danger'
                )
                conn.close()
                return redirect(
                    url_for('main.editar_usuario', id=id)
                )

            if len(funcao_ids) != len(setor_ids):
                flash(
                    'Erro ao processar as habilitações informadas.',
                    'danger'
                )
                conn.close()
                return redirect(
                    url_for('main.editar_usuario', id=id)
                )

            if (
                responsavel_revisao_padrao == 1
                and tem_acesso_sistema != 1
            ):
                flash(
                    'O responsável por revisão de padrão precisa '
                    'possuir acesso ao TrackPlan.',
                    'danger'
                )
                conn.close()
                return redirect(
                    url_for('main.editar_usuario', id=id)
                )

            if tem_acesso_sistema == 1:
                if not email:
                    flash(
                        'Funcionários com acesso ao sistema devem '
                        'possuir e-mail.',
                        'danger'
                    )
                    conn.close()
                    return redirect(
                        url_for('main.editar_usuario', id=id)
                    )

                if not perfil:
                    flash(
                        'Funcionários com acesso ao sistema devem '
                        'possuir perfil.',
                        'danger'
                    )
                    conn.close()
                    return redirect(
                        url_for('main.editar_usuario', id=id)
                    )

                if tinha_acesso == 0 and not nova_senha:
                    flash(
                        'Ao conceder acesso ao TrackPlan, informe '
                        'uma senha inicial.',
                        'danger'
                    )
                    conn.close()
                    return redirect(
                        url_for('main.editar_usuario', id=id)
                    )

            else:
                perfil = None
                nova_senha = None
                precisa_alterar_senha = 0

                acesso_plano_acao = 0
                acesso_ssma = 0
                acesso_melhoria = 0
                acesso_gestao_pessoas = 0
                acesso_treinamentos = 0
                acesso_procedimentos = 0
                acesso_pcpm = 0
                acesso_detectores_gas = 0

                responsavel_revisao_padrao = 0
                pode_criar_agendamento_ssma = 0
                pode_ser_lider_ssma = 0

            try:
                cursor.execute("""
                    SELECT id
                    FROM usuarios
                    WHERE matricula = %s
                      AND id <> %s
                """, (
                    matricula,
                    id
                ))

                matricula_existente = cursor.fetchone()

                if matricula_existente:
                    flash(
                        'Já existe outro funcionário cadastrado '
                        'com esta matrícula.',
                        'warning'
                    )
                    conn.close()
                    return redirect(
                        url_for('main.editar_usuario', id=id)
                    )

                if email:
                    cursor.execute("""
                        SELECT id
                        FROM usuarios
                        WHERE email = %s
                          AND id <> %s
                    """, (
                        email,
                        id
                    ))

                    existente = cursor.fetchone()

                    if existente:
                        flash(
                            'Já existe outro funcionário cadastrado '
                            'com este e-mail.',
                            'warning'
                        )
                        conn.close()
                        return redirect(
                            url_for('main.editar_usuario', id=id)
                        )

                if responsavel_revisao_padrao == 1:
                    cursor.execute("""
                        SELECT id, nome
                        FROM usuarios
                        WHERE responsavel_revisao_padrao = 1
                          AND ativo = 1
                          AND centro_custos_id = %s
                          AND id <> %s
                        LIMIT 1
                    """, (
                        centro_custos_id,
                        id
                    ))

                    responsavel_existente = cursor.fetchone()

                    if responsavel_existente:
                        flash(
                            f"Já existe um responsável ativo por "
                            f"revisão de padrão neste centro de custo: "
                            f"{responsavel_existente['nome']}.",
                            'warning'
                        )
                        conn.close()
                        return redirect(
                            url_for('main.editar_usuario', id=id)
                        )

                if nova_senha:
                    hash_senha = generate_password_hash(
                        nova_senha,
                        method='pbkdf2:sha256'
                    )

                    cursor.execute("""
                        UPDATE usuarios
                        SET nome = %s,
                            matricula = %s,
                            uid_rfid = %s,
                            email = %s,
                            superintendencia_id = %s,
                            centro_custos_id = %s,
                            cargo_id = %s,
                            perfil = %s,
                            ativo = %s,
                            precisa_alterar_senha = %s,
                            tem_acesso_sistema = %s,
                            pode_ser_instrutor = %s,
                            responsavel_revisao_padrao = %s,
                            pode_criar_agendamento_ssma = %s,
                            pode_ser_lider_ssma = %s,
                            acesso_plano_acao = %s,
                            acesso_ssma = %s,
                            acesso_melhoria = %s,
                            acesso_gestao_pessoas = %s,
                            acesso_treinamentos = %s,
                            acesso_procedimentos = %s,
                            acesso_pcpm = %s,
                            acesso_detectores_gas = %s,
                            senha_hash = %s
                        WHERE id = %s
                    """, (
                        nome,
                        matricula,
                        uid_rfid,
                        email,
                        superintendencia_id,
                        centro_custos_id,
                        cargo_id,
                        perfil,
                        ativo,
                        precisa_alterar_senha,
                        tem_acesso_sistema,
                        pode_ser_instrutor,
                        responsavel_revisao_padrao,
                        pode_criar_agendamento_ssma,
                        pode_ser_lider_ssma,
                        acesso_plano_acao,
                        acesso_ssma,
                        acesso_melhoria,
                        acesso_gestao_pessoas,
                        acesso_treinamentos,
                        acesso_procedimentos,
                        acesso_pcpm,
                        acesso_detectores_gas,
                        hash_senha,
                        id
                    ))

                else:
                    cursor.execute("""
                        UPDATE usuarios
                        SET nome = %s,
                            matricula = %s,
                            uid_rfid = %s,
                            email = %s,
                            superintendencia_id = %s,
                            centro_custos_id = %s,
                            cargo_id = %s,
                            perfil = %s,
                            ativo = %s,
                            precisa_alterar_senha = %s,
                            tem_acesso_sistema = %s,
                            pode_ser_instrutor = %s,
                            responsavel_revisao_padrao = %s,
                            pode_criar_agendamento_ssma = %s,
                            pode_ser_lider_ssma = %s,
                            acesso_plano_acao = %s,
                            acesso_ssma = %s,
                            acesso_melhoria = %s,
                            acesso_gestao_pessoas = %s,
                            acesso_treinamentos = %s,
                            acesso_procedimentos = %s,
                            acesso_pcpm = %s,
                            acesso_detectores_gas = %s
                        WHERE id = %s
                    """, (
                        nome,
                        matricula,
                        uid_rfid,
                        email,
                        superintendencia_id,
                        centro_custos_id,
                        cargo_id,
                        perfil,
                        ativo,
                        precisa_alterar_senha,
                        tem_acesso_sistema,
                        pode_ser_instrutor,
                        responsavel_revisao_padrao,
                        pode_criar_agendamento_ssma,
                        pode_ser_lider_ssma,
                        acesso_plano_acao,
                        acesso_ssma,
                        acesso_melhoria,
                        acesso_gestao_pessoas,
                        acesso_treinamentos,
                        acesso_procedimentos,
                        acesso_pcpm,
                        acesso_detectores_gas,
                        id
                    ))

                cursor.execute("""
                    DELETE FROM usuario_funcoes_setores
                    WHERE usuario_id = %s
                """, (id,))

                combinacoes_inseridas = set()

                for funcao_id, setor_id in zip(
                    funcao_ids,
                    setor_ids
                ):
                    funcao_id = (funcao_id or '').strip()
                    setor_id = (setor_id or '').strip()

                    if not funcao_id or not setor_id:
                        continue

                    chave = (funcao_id, setor_id)

                    if chave in combinacoes_inseridas:
                        continue

                    cursor.execute("""
                        INSERT INTO usuario_funcoes_setores (
                            usuario_id,
                            funcao_id,
                            setor_id,
                            ativo
                        )
                        VALUES (%s, %s, %s, 1)
                    """, (
                        id,
                        funcao_id,
                        setor_id
                    ))

                    combinacoes_inseridas.add(chave)

                conn.commit()

                flash(
                    'Funcionário atualizado com sucesso!',
                    'success'
                )

            except Exception as e:
                conn.rollback()
                flash(
                    f'Erro ao atualizar funcionário: {e}',
                    'danger'
                )

            finally:
                conn.close()

            return redirect(
                url_for('main.listar_usuarios')
            )

        cursor.execute("""
            SELECT
                cc.id,
                cc.codigo,
                cc.descricao,
                s.id AS superintendencia_id,
                s.nome AS superintendencia_nome
            FROM centros_custos cc
            LEFT JOIN superintendencias s
                ON s.id = cc.superintendencia_id
            WHERE cc.ativo = 1
            ORDER BY cc.codigo, cc.descricao
        """)
        centros_custos = cursor.fetchall()

        cursor.execute("""
            SELECT id, nome
            FROM setores
            WHERE ativo = 1
            ORDER BY nome
        """)
        setores = cursor.fetchall()

        cursor.execute("""
            SELECT id, nome
            FROM cargos
            WHERE ativo = 1
            ORDER BY nome
        """)
        cargos = cursor.fetchall()

        cursor.execute("""
            SELECT id, nome
            FROM funcoes
            WHERE ativo = 1
            ORDER BY nome
        """)
        funcoes = cursor.fetchall()

        cursor.execute("""
            SELECT
                ufs.funcao_id,
                ufs.setor_id,
                f.nome AS nome_funcao,
                s.nome AS nome_setor
            FROM usuario_funcoes_setores ufs
            JOIN funcoes f
                ON f.id = ufs.funcao_id
            JOIN setores s
                ON s.id = ufs.setor_id
            WHERE ufs.usuario_id = %s
              AND ufs.ativo = 1
            ORDER BY f.nome, s.nome
        """, (id,))

        habilitacoes = cursor.fetchall()

        conn.close()

        return render_template(
            'editar_usuario.html',
            usuario=usuario,
            centros_custos=centros_custos,
            setores=setores,
            cargos=cargos,
            funcoes=funcoes,
            habilitacoes=habilitacoes
        )

    @blueprint.route('/listar_usuarios', methods=['GET'])
    @login_required
    @admin_required
    def listar_usuarios():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        status = request.args.get('status', '').strip()
        tem_acesso_sistema = request.args.get('tem_acesso_sistema', '').strip()
        pode_ser_instrutor = request.args.get('pode_ser_instrutor', '').strip()
        centro_custos_id = request.args.get('centro_custos_id', '').strip()

        sort = request.args.get('sort', 'nome').strip()
        order = request.args.get('order', 'asc').strip()

        colunas_validas = {
            'nome': 'u.nome',
            'matricula': 'u.matricula',
            'email': 'u.email',
            'cargo': 'c.nome'
        }

        coluna_sort = colunas_validas.get(sort, 'u.nome')
        direcao = 'ASC' if order == 'asc' else 'DESC'

        query = f"""
            SELECT
                u.id,
                u.nome,
                u.matricula,
                u.email,
                u.ativo,
                u.tem_acesso_sistema,
                u.pode_ser_instrutor,
                u.perfil,
                u.centro_custos_id,
                u.superintendencia_id,
                u.cargo_id,

                u.acesso_plano_acao,
                u.acesso_ssma,
                u.acesso_melhoria,
                u.acesso_gestao_pessoas,
                u.acesso_treinamentos,
                u.acesso_procedimentos,
                u.acesso_detectores_gas,

                c.nome AS nome_cargo,

                cc.codigo AS codigo_cc,
                cc.descricao AS descricao_cc,

                s.nome AS nome_superintendencia,

                GROUP_CONCAT(
                    DISTINCT f.nome
                    ORDER BY f.nome
                    SEPARATOR ', '
                ) AS nomes_funcoes,

                GROUP_CONCAT(
                    DISTINCT st.nome
                    ORDER BY st.nome
                    SEPARATOR ', '
                ) AS nomes_setores

            FROM usuarios u
            LEFT JOIN cargos c
                ON c.id = u.cargo_id
            LEFT JOIN centros_custos cc
                ON cc.id = u.centro_custos_id
            LEFT JOIN superintendencias s
                ON s.id = u.superintendencia_id
            LEFT JOIN usuario_funcoes_setores ufs
                ON ufs.usuario_id = u.id
               AND ufs.ativo = 1
            LEFT JOIN funcoes f
                ON f.id = ufs.funcao_id
            LEFT JOIN setores st
                ON st.id = ufs.setor_id
            WHERE 1=1
        """

        params = []

        if status != '':
            query += " AND u.ativo = %s"
            params.append(status)

        if tem_acesso_sistema != '':
            query += " AND u.tem_acesso_sistema = %s"
            params.append(tem_acesso_sistema)

        if pode_ser_instrutor != '':
            query += " AND u.pode_ser_instrutor = %s"
            params.append(pode_ser_instrutor)

        if centro_custos_id:
            query += " AND u.centro_custos_id = %s"
            params.append(centro_custos_id)

        query += f"""
            GROUP BY
                u.id,
                u.nome,
                u.matricula,
                u.email,
                u.ativo,
                u.tem_acesso_sistema,
                u.pode_ser_instrutor,
                u.perfil,
                u.centro_custos_id,
                u.superintendencia_id,
                u.cargo_id,
                u.acesso_plano_acao,
                u.acesso_ssma,
                u.acesso_melhoria,
                u.acesso_gestao_pessoas,
                u.acesso_treinamentos,
                u.acesso_procedimentos,
                u.acesso_detectores_gas,
                c.nome,
                cc.codigo,
                cc.descricao,
                s.nome
            ORDER BY {coluna_sort} {direcao}, u.nome ASC
        """

        cursor.execute(query, params)
        usuarios = cursor.fetchall()

        cursor.execute("""
            SELECT
                cc.id,
                cc.codigo,
                cc.descricao
            FROM centros_custos cc
            WHERE cc.ativo = 1
            ORDER BY cc.codigo, cc.descricao
        """)
        centros_custos = cursor.fetchall()

        conn.close()

        filtros = {
            'status': status,
            'tem_acesso_sistema': tem_acesso_sistema,
            'pode_ser_instrutor': pode_ser_instrutor,
            'centro_custos_id': centro_custos_id,
            'sort': sort,
            'order': order
        }

        return render_template(
            'listar_usuarios.html',
            usuarios=usuarios,
            centros_custos=centros_custos,
            filtros=filtros
        )

    @blueprint.route('/permissoes_usuario/<int:id>', methods=['GET', 'POST'])
    @login_required
    @admin_required
    def permissoes_usuario(id):
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == 'POST':
            perfil = request.form.get('perfil')

            acesso_plano_acao = 1 if request.form.get('acesso_plano_acao') else 0
            acesso_ssma = 1 if request.form.get('acesso_ssma') else 0
            acesso_melhoria = 1 if request.form.get('acesso_melhoria') else 0
            acesso_gestao_pessoas = 1 if request.form.get('acesso_gestao_pessoas') else 0
            acesso_treinamentos = 1 if request.form.get('acesso_treinamentos') else 0
            acesso_procedimentos = 1 if request.form.get('acesso_procedimentos') else 0
            acesso_pcpm = 1 if request.form.get('acesso_pcpm') else 0
            acesso_detectores_gas = (
                1 if request.form.get('acesso_detectores_gas') else 0
            )

            cursor.execute("""
                UPDATE usuarios
                SET perfil = %s,
                    acesso_plano_acao = %s,
                    acesso_ssma = %s,
                    acesso_melhoria = %s,
                    acesso_gestao_pessoas = %s,
                    acesso_treinamentos = %s,
                    acesso_procedimentos = %s,
                    acesso_pcpm = %s,
                    acesso_detectores_gas = %s
                WHERE id = %s
            """, (
                perfil,
                acesso_plano_acao,
                acesso_ssma,
                acesso_melhoria,
                acesso_gestao_pessoas,
                acesso_treinamentos,
                acesso_procedimentos,
                acesso_pcpm,
                acesso_detectores_gas,
                id
            ))

            conn.commit()
            conn.close()

            flash('Permissões atualizadas com sucesso!', 'success')
            return redirect('/usuarios')

        cursor.execute("""
            SELECT *
            FROM usuarios
            WHERE id = %s
        """, (id,))
        usuario = cursor.fetchone()

        conn.close()

        if not usuario:
            flash('Usuário não encontrado.', 'warning')
            return redirect('/usuarios')

        return render_template('permissoes_usuario.html', usuario=usuario)
