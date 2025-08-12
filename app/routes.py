from flask import Blueprint, render_template, request, redirect, session, flash, current_app, url_for
from app.utils.db import get_db_connection
from werkzeug.security import generate_password_hash
from functools import wraps
from flask import session, redirect
from app.decorators import login_required
from werkzeug.utils import secure_filename
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Mail, Message
from app import mail
import os
# Configuração do token seguro
s = URLSafeTimedSerializer('CHAVE_SECRETA_DO_SISTEMA')  # Substitua por sua chave secreta

UPLOAD_FOLDER = 'app/static/evidencias'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'docx', 'xlsx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function


main_routes = Blueprint('main', __name__)

@main_routes.route('/')
def index():
    return redirect('/login')

@main_routes.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE email = %s AND ativo = TRUE", (email,))
        usuario = cursor.fetchone()
        conn.close()

        from werkzeug.security import check_password_hash  # certifique-se que essa importação está no topo
        if usuario and check_password_hash(usuario['senha_hash'], senha):

            session['usuario_id'] = usuario['id']
            session['nome'] = usuario['nome']
            session['perfil'] = usuario['perfil']

            # 👇 Redireciona para alteração de senha caso seja obrigatório
            if usuario.get('precisa_alterar_senha'):
                return redirect('/alterar_senha')

            if usuario['perfil'] == 'administrador':
                return redirect('/admin')
            else:
                return redirect('/dashboard')
        else:
            flash('Email ou senha inválidos.')
    
    return render_template('login.html')

@main_routes.route('/admin')
@login_required

def admin():
    if session.get('perfil') != 'administrador':
        flash('Acesso restrito ao administrador.')
        return redirect('/')
    return render_template('admin.html')

@main_routes.route('/centros_custos', methods=['GET', 'POST'])
@login_required
def centros_custos():
    if session.get('perfil') != 'administrador':
        flash('Acesso restrito ao administrador.')
        return redirect('/')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        codigo = request.form['codigo']
        descricao = request.form['descricao']
        superintendencia_id = request.form['superintendencia_id']
        cursor.execute("""
            INSERT INTO centros_custos (codigo, descricao, superintendencia_id)
            VALUES (%s, %s, %s)
        """, (codigo, descricao, superintendencia_id))
        conn.commit()
        flash('Centro de Custo cadastrado com sucesso!')

    cursor.execute("""
        SELECT cc.*, s.nome AS nome_superintendencia
        FROM centros_custos cc
        LEFT JOIN superintendencias s ON cc.superintendencia_id = s.id
    """)
    centros = cursor.fetchall()

    cursor.execute("SELECT * FROM superintendencias WHERE ativo = TRUE")
    superintendencias = cursor.fetchall()

    conn.close()
    return render_template('centros_custos.html', centros=centros, superintendencias=superintendencias)

@main_routes.route('/editar_centro/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_centro(id):
    if session.get('perfil') != 'administrador':
        flash('Acesso restrito ao administrador.')
        return redirect('/')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        novo_codigo = request.form['codigo']
        nova_descricao = request.form['descricao']
        nova_superintendencia_id = request.form['superintendencia_id']
        cursor.execute("""
            UPDATE centros_custos
            SET codigo = %s, descricao = %s, superintendencia_id = %s
            WHERE id = %s
        """, (novo_codigo, nova_descricao, nova_superintendencia_id, id))
        conn.commit()
        conn.close()
        flash('Centro de Custo atualizado com sucesso!')
        return redirect('/centros_custos')

    cursor.execute("SELECT * FROM centros_custos WHERE id = %s", (id,))
    centro = cursor.fetchone()

    cursor.execute("SELECT * FROM superintendencias WHERE ativo = TRUE")
    superintendencias = cursor.fetchall()

    conn.close()

    return render_template('editar_centro.html', centro=centro, superintendencias=superintendencias)

@main_routes.route('/superintendencias', methods=['GET', 'POST'])
@login_required
def superintendencias():
    if session.get('perfil') != 'administrador':
        flash('Acesso restrito ao administrador.')
        return redirect('/')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        nome = request.form['nome']
        cursor.execute("INSERT INTO superintendencias (nome) VALUES (%s)", (nome,))
        conn.commit()
        flash('Superintendência cadastrada com sucesso!')

    cursor.execute("SELECT * FROM superintendencias")
    superintendencias = cursor.fetchall()
    conn.close()

    return render_template('superintendencias.html', superintendencias=superintendencias)

@main_routes.route('/editar_superintendencia/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_superintendencia(id):
    if session.get('perfil') != 'administrador':
        flash('Acesso restrito ao administrador.')
        return redirect('/')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        novo_nome = request.form['nome']
        cursor.execute("UPDATE superintendencias SET nome = %s WHERE id = %s", (novo_nome, id))
        conn.commit()
        flash('Superintendência atualizada com sucesso!')
        conn.close()
        return redirect('/superintendencias')

    cursor.execute("SELECT * FROM superintendencias WHERE id = %s", (id,))
    superintendencia = cursor.fetchone()
    conn.close()

    if not superintendencia:
        flash('Superintendência não encontrada.')
        return redirect('/superintendencias')

    return render_template('editar_superintendencia.html', superintendencia=superintendencia)

@main_routes.route('/origens', methods=['GET', 'POST'])
@login_required
def origens():
    if session.get('perfil') != 'administrador':
        flash('Acesso restrito ao administrador.')
        return redirect('/')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        descricao = (request.form.get('descricao') or '').strip()

        if not descricao:
            flash('Informe a descrição da origem.', 'danger')
            conn.close()
            return redirect('/origens')

        try:
            # produção exige `nome` NOT NULL + UNIQUE
            cursor.execute(
                "INSERT INTO origens (descricao, nome) VALUES (%s, %s)",
                (descricao, descricao)
            )
            conn.commit()
            flash('Origem cadastrada com sucesso!', 'success')

        except Exception as e:
            # Trata UNIQUE KEY 'nome' duplicado (1062)
            msg = str(e)
            if '1062' in msg or 'Duplicate entry' in msg:
                flash('Já existe uma origem com esse nome/descrição.', 'warning')
            else:
                flash(f'Erro ao salvar origem: {e}', 'danger')
            conn.rollback()

    # LISTAGEM normal
    cursor.execute("SELECT id, descricao, ativo FROM origens ORDER BY id DESC")
    origens = cursor.fetchall()
    conn.close()

    return render_template('origens.html', origens=origens)

@main_routes.route('/editar_origem/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_origem(id):
    if session.get('perfil') != 'administrador':
        flash('Acesso restrito ao administrador.')
        return redirect('/')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        nova_descricao = (request.form.get('descricao') or '').strip()
        if not nova_descricao:
            flash('Informe a descrição.', 'danger')
            conn.close()
            return redirect(f'/editar_origem/{id}')

        try:
            # Atualiza `descricao` e `nome` juntos para respeitar NOT NULL + UNIQUE
            cursor.execute(
                "UPDATE origens SET descricao = %s, nome = %s WHERE id = %s",
                (nova_descricao, nova_descricao, id)
            )
            conn.commit()
            flash('Origem atualizada com sucesso!', 'success')
            conn.close()
            return redirect('/origens')

        except Exception as e:
            msg = str(e)
            if '1062' in msg or 'Duplicate entry' in msg:
                flash('Já existe outra origem com esse nome/descrição.', 'warning')
            else:
                flash(f'Erro ao atualizar origem: {e}', 'danger')
            conn.rollback()
            conn.close()
            return redirect(f'/editar_origem/{id}')

    # GET original
    cursor.execute("SELECT * FROM origens WHERE id = %s", (id,))
    origem = cursor.fetchone()
    conn.close()

    if not origem:
        flash('Origem não encontrada.')
        return redirect('/origens')

    return render_template('editar_origens.html', origem=origem)

@main_routes.route('/usuarios', methods=['GET', 'POST'])
@login_required
def usuarios():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        superintendencia_id = request.form['superintendencia_id']
        centro_custos_id = request.form['centro_custos_id']
        senha_plana = request.form['senha']
        perfil = request.form['perfil']

        hash_senha = generate_password_hash(senha_plana, method="pbkdf2:sha256")

        # Inserir usuário
        cursor.execute(
            """
            INSERT INTO usuarios
              (nome, email, superintendencia_id, centro_custos_id, senha_hash, perfil, ativo, precisa_alterar_senha)
            VALUES (%s,   %s,    %s,                 %s,               %s,         %s,     TRUE, 1)
            """,
            (nome, email, superintendencia_id, centro_custos_id, hash_senha, perfil)
        )
        conn.commit()
        novo_usuario_id = cursor.lastrowid  # se precisar pra algo futuro

        # --- Envio do e-mail de boas-vindas ---
        try:
            link_login = url_for('main.login', _external=True)

            msg = Message(
                subject="Bem-vindo ao TrackPlan — dados de acesso",
                recipients=[email]
            )
            # HTML bonitinho
            msg.html = f"""
            <div style="font-family: Arial, sans-serif; font-size: 15px; color:#333;">
              <div style="text-align:center; margin-bottom:18px;">
                <img src="https://www.trackplan.com.br/imagens/barra_email.png" alt="TrackPlan" style="height:50px;">
              </div>

              <p>Olá <strong>{nome}</strong>,</p>
              <p>Seu acesso ao <strong>TrackPlan</strong> foi criado com sucesso. Seguem seus dados de login:</p>

              <div style="background:#f7f7f7; border:1px solid #eee; border-radius:6px; padding:12px 14px; margin:12px 0;">
                <p style="margin:6px 0;"><strong>Endereço:</strong> <a href="{link_login}" target="_blank">{link_login}</a></p>
                <p style="margin:6px 0;"><strong>Usuário (e-mail):</strong> {email}</p>
                <p style="margin:6px 0;"><strong>Senha inicial:</strong> {senha_plana}</p>
              </div>

              <p>Por segurança, ao entrar pela primeira vez você poderá alterar sua senha.</p>

              <p style="margin:22px 0; text-align:center;">
                <a href="{link_login}" target="_blank"
                   style="display:inline-block; background:#ea6a23; color:#fff; text-decoration:none; padding:10px 18px; border-radius:5px;">
                  Acessar o TrackPlan
                </a>
              </p>

              <p style="font-size:13px; color:#666;">Equipe TrackPlan</p>
            </div>
            """
            mail.send(msg)
            flash('Usuário cadastrado e e-mail de boas-vindas enviado!', 'success')
        except Exception as e:
            # Logue e.getMessage() se quiser; aqui só informamos
            flash('Usuário cadastrado, mas não foi possível enviar o e-mail de boas-vindas.', 'warning')

        conn.close()
        return redirect('/usuarios')

    # GET — carregar dados para o formulário e tabela
    cursor.execute("""
        SELECT cc.id, cc.codigo, cc.descricao,
               s.id AS superintendencia_id, s.nome AS superintendencia_nome
        FROM centros_custos cc
        LEFT JOIN superintendencias s ON s.id = cc.superintendencia_id
        WHERE cc.ativo = 1
        ORDER BY cc.codigo, cc.descricao
    """)
    centros_custos = cursor.fetchall()

    cursor.execute("SELECT id, nome FROM superintendencias ORDER BY nome")
    superintendencias = cursor.fetchall()

    cursor.execute("""
        SELECT u.*, cc.codigo AS codigo_cc, cc.descricao AS descricao_cc, s.nome AS nome_superintendencia
        FROM usuarios u
        JOIN centros_custos cc ON u.centro_custos_id = cc.id
        JOIN superintendencias s ON u.superintendencia_id = s.id
        ORDER BY u.nome
    """)
    usuarios = cursor.fetchall()

    conn.close()

    return render_template(
        'usuarios.html',
        superintendencias=superintendencias,
        centros_custos=centros_custos,
        usuarios=usuarios
    )

# Rota para edição de usuário
@main_routes.route('/editar_usuario/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        nome = request.form['nome']
        email = request.form['email']
        superintendencia_id = request.form['superintendencia_id']
        centro_custos_id = request.form['centro_custos_id']
        perfil = request.form['perfil']
        ativo = request.form['ativo']
        nova_senha = request.form.get('nova_senha')

        if nova_senha:
            hash_senha = generate_password_hash(nova_senha, method="pbkdf2:sha256")
            cursor.execute("""
                UPDATE usuarios SET nome=%s, email=%s, superintendencia_id=%s, centro_custos_id=%s,
                perfil=%s, ativo=%s, senha_hash=%s WHERE id=%s
            """, (nome, email, superintendencia_id, centro_custos_id, perfil, ativo, hash_senha, id))
        else:
            cursor.execute("""
                UPDATE usuarios SET nome=%s, email=%s, superintendencia_id=%s, centro_custos_id=%s,
                perfil=%s, ativo=%s WHERE id=%s
            """, (nome, email, superintendencia_id, centro_custos_id, perfil, ativo, id))

        conn.commit()
        conn.close()
        flash('Usuário atualizado com sucesso!')
        return redirect('/usuarios')

    # Dados do usuário atual
    cursor.execute("SELECT * FROM usuarios WHERE id = %s", (id,))
    usuario = cursor.fetchone()

    # Superintendências ativas
    cursor.execute("SELECT * FROM superintendencias WHERE ativo = 1")
    superintendencias = cursor.fetchall()

    # Centros de custos com dados da superintendência associada
    cursor.execute("""
        SELECT cc.id, cc.codigo, cc.descricao, cc.superintendencia_id, s.nome AS superintendencia_nome
        FROM centros_custos cc
        JOIN superintendencias s ON cc.superintendencia_id = s.id
        WHERE cc.ativo = 1 AND s.ativo = 1
    """)
    centros_custos = cursor.fetchall()

    conn.close()

    return render_template(
        'editar_usuario.html',
        usuario=usuario,
        superintendencias=superintendencias,
        centros_custos=centros_custos
    )

@main_routes.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    from datetime import date

    # Atualiza status para "Vencida" quando ultrapassar o prazo
    cursor.execute("""
        UPDATE acoes
        SET status = 'Vencida'
        WHERE status NOT IN ('Concluída', 'Cancelada')
          AND prazo < %s
    """, (date.today(),))
    conn.commit()

    usuario_id = session['usuario_id']
    perfil = session.get('perfil')

    # Coleta de filtros
    responsavel_id = request.args.get('responsavel')
    superintendencia_id = request.args.get('superintendencia')
    centro_custos_id = request.args.get('centro_custos')
    origem_id = request.args.get('origem')
    status = request.args.get('status')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')

    # Filtros dinâmicos
    filtros = []
    valores = []

    if responsavel_id:
        filtros.append("a.responsavel_id = %s")
        valores.append(responsavel_id)

    if superintendencia_id:
        filtros.append("u.superintendencia_id = %s")
        valores.append(superintendencia_id)

    if centro_custos_id:
        filtros.append("u.centro_custos_id = %s")
        valores.append(centro_custos_id)

    if origem_id:
        filtros.append("a.origem_id = %s")
        valores.append(origem_id)

    if status:
        filtros.append("a.status = %s")
        valores.append(status)

    if data_inicio:
        filtros.append("a.prazo >= %s")
        valores.append(data_inicio)

    if data_fim:
        filtros.append("a.prazo <= %s")
        valores.append(data_fim)

    # Controle por perfil
    if perfil == 'basico':
        filtros.append("a.responsavel_id = %s")
        valores.append(usuario_id)
    elif perfil == 'intermediario':
        cursor.execute("SELECT superintendencia_id FROM usuarios WHERE id = %s", (usuario_id,))
        superintendencia_usuario = cursor.fetchone()['superintendencia_id']
        filtros.append("u.superintendencia_id = %s")
        valores.append(superintendencia_usuario)
    elif perfil == 'avancado':
        cursor.execute("SELECT centro_custos_id FROM usuarios WHERE id = %s", (usuario_id,))
        centro_custos_usuario = cursor.fetchone()['centro_custos_id']
        filtros.append("u.centro_custos_id = %s")
        valores.append(centro_custos_usuario)
    # administrador: sem filtro extra

    where_clause = " AND ".join(filtros)
    if where_clause:
        where_clause = "WHERE " + where_clause

    # Consulta principal de ações
    query_acoes = f"""
        SELECT 
            a.*,
            u.nome  AS nome_responsavel,
            uc.nome AS nome_criador,
            cc.codigo   AS codigo_cc,
            cc.descricao AS descricao_cc,
            o.descricao AS descricao_origem
        FROM acoes a
        JOIN usuarios u  ON a.responsavel_id = u.id
        JOIN usuarios uc ON a.criado_por    = uc.id
        JOIN centros_custos cc ON u.centro_custos_id = cc.id
        JOIN origens o ON a.origem_id = o.id
        {where_clause}
        ORDER BY a.prazo ASC
    """
    cursor.execute(query_acoes, valores)
    acoes = cursor.fetchall()

    # Consulta para ações criadas pelo usuário logado
    cursor.execute("""
        SELECT 
            a.*,
            u.nome  AS nome_responsavel,
            uc.nome AS nome_criador,
            cc.codigo   AS codigo_cc,
            cc.descricao AS descricao_cc,
            o.descricao AS descricao_origem
        FROM acoes a
        JOIN usuarios u  ON a.responsavel_id = u.id
        JOIN usuarios uc ON a.criado_por    = uc.id
        JOIN centros_custos cc ON u.centro_custos_id = cc.id
        JOIN origens o ON a.origem_id = o.id
        WHERE a.criado_por = %s
        ORDER BY a.prazo ASC
    """, (usuario_id,))
    acoes_criadas = cursor.fetchall()

    # Gráfico de ações por Status
    query_status = f"""
        SELECT a.status, COUNT(*) AS total
        FROM acoes a
        JOIN usuarios u ON a.responsavel_id = u.id
        {where_clause}
        GROUP BY a.status
    """
    cursor.execute(query_status, valores)
    status_data = cursor.fetchall()
    labels_status = [d['status'] for d in status_data]
    dados_status = [d['total'] for d in status_data]

    # Gráfico de ações por Origem
    query_origem = f"""
        SELECT o.descricao AS origem, COUNT(*) AS total
        FROM acoes a
        JOIN origens o ON a.origem_id = o.id
        JOIN usuarios u ON a.responsavel_id = u.id
        {where_clause}
        GROUP BY o.descricao
    """
    cursor.execute(query_origem, valores)
    origem_data = cursor.fetchall()
    labels_origem = [d['origem'] for d in origem_data]
    dados_origem = [d['total'] for d in origem_data]

    # Dados para os filtros
    cursor.execute("SELECT id, nome FROM usuarios WHERE nome != 'administrador'")
    responsaveis = cursor.fetchall()

    cursor.execute("SELECT id, nome FROM superintendencias")
    superintendencias = cursor.fetchall()

    cursor.execute("SELECT id, codigo, descricao FROM centros_custos")
    centros_custos = cursor.fetchall()

    cursor.execute("SELECT id, descricao FROM origens")
    origens = cursor.fetchall()

    conn.close()

    return render_template(
        'dashboard.html',
        acoes=acoes,
        acoes_criadas=acoes_criadas,
        responsaveis=responsaveis,
        superintendencias=superintendencias,
        centros_custos=centros_custos,
        origens=origens,
        labels_status=labels_status,
        dados_status=dados_status,
        labels_origem=labels_origem,
        dados_origem=dados_origem
    )

@main_routes.route('/cadastrar_acao', methods=['GET', 'POST'])
@login_required
def cadastrar_acao():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        origem_id = request.form['origem_id']
        responsavel_id = request.form['responsavel_id']
        descricao = request.form['descricao']
        prazo = request.form['prazo']
        status = request.form['status']

        # Quem está criando
        criado_por = session.get('usuario_id')

        # 1) Inserir ação no banco já com criado_por
        cursor.execute("""
            INSERT INTO acoes (origem_id, responsavel_id, descricao, prazo, status, criado_por)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (origem_id, responsavel_id, descricao, prazo, status, criado_por))
        conn.commit()

        # 2) ID da ação recém-cadastrada
        acao_id = cursor.lastrowid

        # 3) Buscar dados do responsável
        cursor.execute("SELECT nome, email FROM usuarios WHERE id = %s", (responsavel_id,))
        responsavel = cursor.fetchone()

        # 4) Prazo dd/mm/aaaa
        from datetime import datetime
        prazo_formatado = datetime.strptime(prazo, '%Y-%m-%d').strftime('%d/%m/%Y')

        # 5) Link direto para editar a ação
        link_edicao = url_for('main.editar_acao', id=acao_id, _external=True)

        # 6) Enviar e-mail (não interrompe o fluxo se falhar)
        try:
            msg = Message(
                subject="Nova Ação Atribuída a Você - TrackPlan",
                recipients=[responsavel['email']]
            )
            msg.html = f"""
            <div style="font-family: Arial, sans-serif; font-size: 15px;">
                <div style="text-align: center;">
                    <img src="https://www.trackplan.com.br/imagens/barra_email.png" alt="TrackPlan" style="height: 50px; margin-bottom: 20px;">
                </div>
                <p>Olá <strong>{responsavel['nome']}</strong>,</p>

                <p>Uma nova ação foi atribuída a você no sistema TrackPlan.</p>

                <p><strong>Descrição:</strong> {descricao}<br>
                <strong>Prazo:</strong> {prazo_formatado}<br>
                <strong>Status:</strong> {status}</p>

                <p>Acesse o sistema para mais detalhes:</p>

                <p>
                    <a href="{link_edicao}" style="display: inline-block; background-color: #ea6a23; color: white; padding: 10px 18px; text-decoration: none; border-radius: 5px;">
                        Editar Ação
                    </a>
                </p>

                <br>
                <p style="font-size: 13px; color: #666;">Equipe TrackPlan</p>
            </div>
            """
            mail.send(msg)
        except Exception as e:
            # Log opcional: print(e)
            flash('Ação criada. Falha ao enviar o e-mail de notificação.', 'warning')

        conn.close()
        flash('Ação cadastrada com sucesso!')
        return redirect('/dashboard')

    # --- GET: carregar dados para o formulário ---
    cursor.execute("SELECT * FROM origens WHERE ativo = 1")
    origens = cursor.fetchall()

    usuario_id = session.get('usuario_id')
    perfil = session.get('perfil')

    # Buscar dados do usuário logado
    cursor.execute("""
        SELECT id, nome, superintendencia_id, centro_custos_id
        FROM usuarios
        WHERE id = %s
    """, (usuario_id,))
    usuario_logado = cursor.fetchone()

    # Filtrar responsáveis conforme perfil
    if perfil == 'basico':
        cursor.execute("""
            SELECT id, nome FROM usuarios
            WHERE ativo = TRUE AND centro_custos_id = %s
        """, (usuario_logado['centro_custos_id'],))
    elif perfil == 'intermediario':
        cursor.execute("""
            SELECT id, nome FROM usuarios
            WHERE ativo = TRUE AND superintendencia_id = %s
        """, (usuario_logado['superintendencia_id'],))
    else:  # avançado ou administrador
        cursor.execute("""
            SELECT id, nome FROM usuarios
            WHERE ativo = TRUE
        """)

    usuarios = cursor.fetchall()
    conn.close()

    return render_template('cadastrar_acao.html', origens=origens, usuarios=usuarios)

# Rota para editar ação existente
@main_routes.route('/editar_acao/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_acao(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        origem_id = request.form['origem_id']
        responsavel_id = request.form['responsavel_id']
        descricao = request.form['descricao']
        prazo = request.form['prazo']
        status = request.form['status']

        cursor.execute("""
            UPDATE acoes
            SET origem_id=%s, responsavel_id=%s, descricao=%s, prazo=%s, status=%s
            WHERE id=%s
        """, (origem_id, responsavel_id, descricao, prazo, status, id))

        conn.commit()
        conn.close()
        flash('Ação atualizada com sucesso!')
        return redirect('/dashboard')

    # GET
    cursor.execute("SELECT * FROM acoes WHERE id = %s", (id,))
    acao = cursor.fetchone()

    cursor.execute("SELECT * FROM origens WHERE ativo = 1")
    origens = cursor.fetchall()

    # Obter dados do usuário logado
    usuario_id = session.get('usuario_id')
    perfil = session.get('perfil')

    cursor.execute("""
        SELECT id, nome, superintendencia_id, centro_custos_id
        FROM usuarios
        WHERE id = %s
    """, (usuario_id,))
    usuario_logado = cursor.fetchone()

    # Selecionar os usuários disponíveis de acordo com o perfil
    if perfil == 'basico':
        cursor.execute("""
            SELECT id, nome FROM usuarios
            WHERE ativo = TRUE AND centro_custos_id = %s
        """, (usuario_logado['centro_custos_id'],))
    elif perfil == 'intermediario':
        cursor.execute("""
            SELECT id, nome FROM usuarios
            WHERE ativo = TRUE AND superintendencia_id = %s
        """, (usuario_logado['superintendencia_id'],))
    else:  # avançado e administrador
        cursor.execute("""
            SELECT id, nome FROM usuarios
            WHERE ativo = TRUE
        """)

    usuarios = cursor.fetchall()

    conn.close()
    return render_template('editar_acao.html', acao=acao, origens=origens, usuarios=usuarios)

@main_routes.route('/anexar_evidencia/<int:acao_id>', methods=['GET', 'POST'])
@login_required
def anexar_evidencia(acao_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Busca a ação correspondente
    cursor.execute("""
        SELECT a.*, u.nome AS nome_responsavel 
        FROM acoes a 
        JOIN usuarios u ON a.responsavel_id = u.id
        WHERE a.id = %s
    """, (acao_id,))
    acao = cursor.fetchone()

    if not acao:
        flash("Ação não encontrada.", "danger")
        conn.close()
        return redirect('/dashboard')

    if request.method == 'POST':
        if 'arquivo' not in request.files:
            flash("Nenhum arquivo enviado.", "danger")
            conn.close()
            return redirect(request.url)

        arquivo = request.files['arquivo']

        if arquivo.filename == '':
            flash("Nenhum arquivo selecionado.", "warning")
            conn.close()
            return redirect(request.url)

        if arquivo and allowed_file(arquivo.filename):
            filename = secure_filename(arquivo.filename)
            caminho = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            arquivo.save(caminho)

            # Atualiza a ação com o nome do arquivo
            cursor.execute("UPDATE acoes SET arquivo_evidencia = %s WHERE id = %s", (filename, acao_id))
            conn.commit()
            conn.close()

            flash("Evidência anexada com sucesso!", "success")
            return redirect('/dashboard')
        else:
            flash("Tipo de arquivo não permitido.", "danger")
            conn.close()
            return redirect(request.url)

    # GET
    conn.close()
    return render_template('anexar_evidencia.html', acao=acao)

@main_routes.route('/desabilitar_origem/<int:id>', methods=['POST'])
@login_required
def desabilitar_origem(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE origens SET ativo = FALSE WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    flash('Origem desabilitada com sucesso!', 'success')
    return redirect('/origens')

@main_routes.route('/habilitar_origem/<int:id>', methods=['POST'])
@login_required
def habilitar_origem(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE origens SET ativo = TRUE WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    flash('Origem habilitada com sucesso!', 'success')
    return redirect('/origens')

@main_routes.route('/habilitar_superintendencia/<int:id>',methods=['POST'])
@login_required
def habilitar_superintendencia(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE superintendencias SET ativo = TRUE WHERE id = %s", (id,))
    conn.commit()
    conn.close()   
    flash('Superintendência habilitada com sucesso!', 'sucess')
    return redirect('/superintendencias')

@main_routes.route('/desabilitar_superintendencia/<int:id>', methods=['POST'])
@login_required
def desabilitar_superintendencia(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE superintendencias SET ativo = FALSE WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    flash('Superintendencia desabilitada com sucesso!', 'success')
    return redirect('/superintendencias')

@main_routes.route('/habilitar_centrocusto/<int:id>',methods=['POST'])
@login_required
def habilitar_centrocusto(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE centros_custos SET ativo = TRUE WHERE id = %s", (id,))
    conn.commit()
    conn.close()   
    flash('Centro de Custos habilitado com sucesso!', 'sucess')
    return redirect('/centros_custos')

@main_routes.route('/desabilitar_centrocusto/<int:id>', methods=['POST'])
@login_required
def desabilitar_centrocusto(id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE centros_custos SET ativo = FALSE WHERE id = %s", (id,))
    conn.commit()
    conn.close()
    flash('Centro de Custos desabilitado com sucesso!', 'success')
    return redirect('/centros_custos')

@main_routes.route('/alterar_senha', methods=['GET', 'POST'])
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

@main_routes.route('/logout')
def logout():
    session.clear()
    return render_template('logout.html')  # ou use redirect('/login')

@main_routes.route('/esqueci_senha', methods=['GET', 'POST'])
def esqueci_senha():
    if request.method == 'POST':
        email = request.form['email']

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM usuarios WHERE email = %s AND ativo = TRUE", (email,))
        usuario = cursor.fetchone()
        conn.close()

        if usuario:
            token = s.dumps(email, salt='recuperar-senha')
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

@main_routes.route('/redefinir_senha/<token>', methods=['GET', 'POST'])
def redefinir_senha(token):
    try:
        email = s.loads(token, salt='recuperar-senha', max_age=1800)  # 30 min
    except:
        flash('O link expirou ou é inválido.', 'danger')
        return redirect(url_for('main_routes.login'))

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

@main_routes.route('/admin/testar_relatorio', methods=['POST'])
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
