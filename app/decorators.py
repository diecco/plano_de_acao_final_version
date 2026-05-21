from functools import wraps
from flask import redirect, session, flash


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            flash('Faça login para acessar esta página.', 'warning')
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('perfil') != 'administrador':
            flash('Acesso restrito ao administrador.', 'danger')
            return redirect('/')
        return f(*args, **kwargs)
    return decorated_function


def module_required(module_key):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if session.get('perfil') == 'administrador':
                return f(*args, **kwargs)

            if not session.get(module_key):
                flash('Você não possui permissão para acessar este módulo.', 'danger')
                return redirect('/')

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def perfil_required(*perfis_permitidos):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            perfil = session.get('perfil')

            if perfil == 'administrador':
                return f(*args, **kwargs)

            if perfil not in perfis_permitidos:
                flash('Você não possui permissão para executar esta ação.', 'danger')
                return redirect('/')

            return f(*args, **kwargs)
        return decorated_function
    return decorator

# =========================
# FUNÇÕES AUXILIARES DE PERMISSÃO POR REGISTRO
# =========================

def pode_acessar_acao(cursor, acao_id):
    usuario_id = session.get('usuario_id')
    perfil = session.get('perfil')
    centro_custos_id = session.get('centro_custos_id')

    cursor.execute("""
        SELECT 
            a.*,
            u.centro_custos_id AS centro_custos_responsavel_id
        FROM acoes a
        JOIN usuarios u ON a.responsavel_id = u.id
        WHERE a.id = %s
          AND a.ativo = 1
    """, (acao_id,))

    acao = cursor.fetchone()

    if not acao:
        return None

    if perfil in ['administrador', 'avancado']:
        return acao

    if perfil == 'intermediario':
        if acao.get('centro_custos_responsavel_id') == centro_custos_id:
            return acao

    if perfil == 'basico':
        if (
            acao.get('responsavel_id') == usuario_id or
            acao.get('criado_por') == usuario_id
        ):
            return acao

    return None

def pode_acessar_ssma(cursor, tipo_registro, registro_id):
    usuario_id = session.get('usuario_id')
    perfil = session.get('perfil')
    centro_custos_id = session.get('centro_custos_id')

    configuracoes = {
        'hs': {
            'tabela': 'hs_registros',
            'campo_autor': 'id_auditor',
            'usa_ativo': False
        },
        'recusa': {
            'tabela': 'recusa_tarefa',
            'campo_autor': 'criado_por',
            'usa_ativo': False
        },
        'apr': {
            'tabela': 'aprs',
            'campo_autor': 'criado_por',
            'usa_ativo': True
        },
        'auditoria_padrao': {
            'tabela': 'auditorias_padrao',
            'campo_autor': 'criado_por',
            'usa_ativo': True
        },
        'ifs': {
            'tabela': 'ifs_inspecoes',
            'campo_autor': 'criado_por',
            'usa_ativo': True
        }
    }

    config = configuracoes.get(tipo_registro)

    if not config:
        return None

    tabela = config['tabela']
    campo_autor = config['campo_autor']

    filtro_ativo = "AND r.ativo = 1" if config.get('usa_ativo') else ""

    cursor.execute(f"""
        SELECT 
            r.*,
            u.centro_custos_id AS centro_custos_autor_id
        FROM {tabela} r
        JOIN usuarios u ON r.{campo_autor} = u.id
        WHERE r.id = %s
        {filtro_ativo}
    """, (registro_id,))

    registro = cursor.fetchone()

    if not registro:
        return None

    if perfil in ['administrador', 'avancado']:
        return registro

    if perfil == 'intermediario' and registro.get('centro_custos_autor_id') == centro_custos_id:
        return registro

    if perfil == 'basico' and registro.get(campo_autor) == usuario_id:
        return registro

    return None