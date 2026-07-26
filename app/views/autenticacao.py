import os
import secrets

from flask import flash, redirect, render_template, request, session, url_for
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash

from app import mail
from app.decorators import login_required
from app.utils.db import get_db_connection


_token_serializer = URLSafeTimedSerializer(
    os.getenv('TOKEN_SECRET_KEY') or os.getenv('SECRET_KEY') or secrets.token_hex(32)
)


def register_autenticacao_routes(blueprint):
    @blueprint.route('/')
    def index():
        return redirect('/login')


    @blueprint.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            email = request.form.get('email', '').strip().lower()
            senha = request.form.get('senha', '')

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            cursor.execute("""
                SELECT *
                FROM usuarios
                WHERE email = %s
                  AND ativo = 1
                  AND tem_acesso_sistema = 1
            """, (email,))

            usuario = cursor.fetchone()

            cursor.close()
            conn.close()

            from werkzeug.security import check_password_hash

            if usuario and check_password_hash(usuario['senha_hash'], senha):
                session.clear()

                def permissao(valor):
                    return bool(int(valor or 0))

                # Dados básicos
                session['usuario_id'] = usuario['id']
                session['nome'] = usuario['nome']
                session['perfil'] = usuario['perfil']

                # Escopo
                session['centro_custos_id'] = usuario.get('centro_custos_id')
                session['superintendencia_id'] = usuario.get('superintendencia_id')

                # Permissões por módulo
                session['acesso_plano_acao'] = permissao(usuario.get('acesso_plano_acao'))
                session['acesso_ssma'] = permissao(usuario.get('acesso_ssma'))
                session['acesso_melhoria'] = permissao(usuario.get('acesso_melhoria'))
                session['acesso_gestao_pessoas'] = permissao(usuario.get('acesso_gestao_pessoas'))
                session['acesso_treinamentos'] = permissao(usuario.get('acesso_treinamentos'))
                session['acesso_procedimentos'] = permissao(usuario.get('acesso_procedimentos'))
                session['acesso_pcpm'] = permissao(usuario.get('acesso_pcpm'))
                session['acesso_detectores_gas'] = permissao(
                    usuario.get('acesso_detectores_gas')
                )

                # Flags adicionais
                session['pode_ser_instrutor'] = permissao(usuario.get('pode_ser_instrutor'))
                session['responsavel_revisao_padrao'] = permissao(usuario.get('responsavel_revisao_padrao'))
                session['pode_criar_agendamento_ssma'] = permissao(usuario.get('pode_criar_agendamento_ssma'))
                session['pode_ser_lider_ssma'] = permissao(usuario.get('pode_ser_lider_ssma'))

                # Perfis com escopo local precisam de Centro de Custo.
                if (
                    session['perfil'] in ('basico', 'intermediario')
                    and not session['centro_custos_id']
                ):
                    session.clear()
                    flash(
                        'Usuário com perfil local sem Centro de Custo vinculado. '
                        'Contate o administrador.',
                        'danger'
                    )
                    return redirect('/login')

                # Forçar troca de senha
                if usuario.get('precisa_alterar_senha'):
                    return redirect('/alterar_senha')

                # Redirecionamento
                if session['perfil'] == 'administrador':
                    return redirect('/admin')

                return redirect('/dashboard')

            flash('Email ou senha inválidos.', 'warning')

        return render_template('login.html')

    @blueprint.route('/admin')
    @login_required

    def admin():
        if session.get('perfil') != 'administrador':
            flash('Acesso restrito ao administrador.')
            return redirect('/')
        return render_template('admin.html')

    @blueprint.route('/alterar_senha', methods=['GET', 'POST'])
    @login_required
    def alterar_senha():
        if request.method == 'POST':
            senha_atual = request.form['senha_atual']
            nova_senha = request.form['nova_senha']
            confirmar_senha = request.form['confirmar_senha']

            if nova_senha != confirmar_senha:
                flash("A nova senha e a confirmação não coincidem.", "danger")
                return redirect('/alterar_senha')

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT senha_hash FROM usuarios WHERE id = %s", (session['usuario_id'],))
            usuario = cursor.fetchone()

            from werkzeug.security import check_password_hash, generate_password_hash

            if not usuario or not check_password_hash(usuario['senha_hash'], senha_atual):
                flash("Senha atual incorreta.", "danger")
                conn.close()
                return redirect('/alterar_senha')

            nova_hash = generate_password_hash(nova_senha)
            cursor.execute("UPDATE usuarios SET senha_hash = %s, precisa_alterar_senha = 0 WHERE id = %s", (nova_hash, session['usuario_id']))
            conn.commit()
            conn.close()

            flash("Senha alterada com sucesso!", "success")
            return redirect('/dashboard')

        return render_template('alterar_senha.html')

    @blueprint.route('/logout')
    def logout():
        session.clear()
        return render_template('logout.html')  # ou use redirect('/login')

    @blueprint.route('/esqueci_senha', methods=['GET', 'POST'])
    def esqueci_senha():
        if request.method == 'POST':
            email = request.form['email']

            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM usuarios WHERE email = %s AND ativo = TRUE", (email,))
            usuario = cursor.fetchone()
            conn.close()

            if usuario:
                token = _token_serializer.dumps(email, salt='recuperar-senha')
                link = url_for('main.redefinir_senha', token=token, _external=True)

                # Envia o e-mail com o link
                msg = Message('Redefinição de Senha - TrackPlan',
                              sender='trackplan@trackplan.com.br',
                              recipients=[email])
                msg.body = f'Olá {usuario["nome"]},\n\nClique no link abaixo para redefinir sua senha:\n{link}\n\nEste link é válido por 30 minutos.'
                mail.send(msg)

                flash('Um link para redefinir a senha foi enviado para seu e-mail.', 'success')
            else:
                flash('E-mail não encontrado ou usuário inativo.', 'danger')

        return render_template('esqueci_senha.html')

    @blueprint.route('/redefinir_senha/<token>', methods=['GET', 'POST'])
    def redefinir_senha(token):
        try:
            email = _token_serializer.loads(token, salt='recuperar-senha', max_age=1800)  # 30 min
        except:
            flash('O link expirou ou é inválido.', 'danger')
            return redirect(url_for('main.login'))

        if request.method == 'POST':
            nova_senha = request.form['nova_senha']
            senha_hash = generate_password_hash(nova_senha)

            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE usuarios SET senha_hash = %s, precisa_alterar_senha = 0 WHERE email = %s", (senha_hash, email))
            conn.commit()
            conn.close()

            flash('Senha redefinida com sucesso!', 'success')
            return redirect(url_for('main.login'))

        return render_template('redefinir_senha.html', token=token)

    @blueprint.route('/admin/testar_relatorio', methods=['POST'])
    @login_required
    def testar_relatorio():
        # apenas admin
        if session.get('perfil') != 'administrador':
            flash('Acesso restrito ao administrador.', 'danger')
            return redirect('/')

        try:
            # Import aqui para evitar import cycle
            from app.tasks import send_weekly_reports

            # Executa e pega o resumo
            resumo = send_weekly_reports()  # {'enviados': int, 'sem_acoes': int, 'erros': [(email,msg), ...]}
            enviados = resumo.get('enviados', 0)
            sem_acoes = resumo.get('sem_acoes', 0)
            erros = resumo.get('erros', [])

            msg = f"Relatórios enviados: {enviados}. Usuários sem ações: {sem_acoes}."
            if erros:
                # mostra só os 3 primeiros para não poluir a tela
                preview = "; ".join([f"{e[0]}: {e[1]}" for e in erros[:3]])
                msg += f" Erros ({len(erros)}): {preview}"
            flash(msg, 'success' if enviados or sem_acoes >= 0 else 'warning')

        except Exception as e:
            flash(f'Falha ao enviar relatórios agora: {e}', 'danger')

        return redirect('/admin')
