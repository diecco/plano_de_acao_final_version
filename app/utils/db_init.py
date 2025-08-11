# app/utils/db_init.py
from werkzeug.security import generate_password_hash
from .db import get_db_connection

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # --- usuarios ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(100) NOT NULL,
        email VARCHAR(120) NOT NULL UNIQUE,
        senha_hash VARCHAR(255) NOT NULL,
        ativo BOOLEAN NOT NULL DEFAULT TRUE,
        perfil VARCHAR(50) DEFAULT 'basico',
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # --- superintendencias ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS superintendencias (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(120) NOT NULL UNIQUE,
        ativo BOOLEAN NOT NULL DEFAULT TRUE,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # --- centros_custos ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS centros_custos (
        id INT AUTO_INCREMENT PRIMARY KEY,
        codigo VARCHAR(32) NOT NULL UNIQUE,
        descricao VARCHAR(160) NOT NULL,
        superintendencia_id INT NULL,
        ativo BOOLEAN NOT NULL DEFAULT TRUE,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        CONSTRAINT fk_cc_sup
            FOREIGN KEY (superintendencia_id) REFERENCES superintendencias(id)
            ON UPDATE CASCADE ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # --- origens ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS origens (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(100) NOT NULL UNIQUE,
        ativo BOOLEAN NOT NULL DEFAULT TRUE,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # --- acoes ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS acoes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        origem_id INT NULL,
        responsavel_id INT NULL,
        centro_custos_id INT NULL,
        descricao TEXT NOT NULL,
        prazo DATE NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'Não iniciada',
        ativo BOOLEAN NOT NULL DEFAULT TRUE,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        atualizado_em TIMESTAMP NULL DEFAULT NULL,
        CONSTRAINT fk_acoes_origem
            FOREIGN KEY (origem_id) REFERENCES origens(id)
            ON UPDATE CASCADE ON DELETE SET NULL,
        CONSTRAINT fk_acoes_responsavel
            FOREIGN KEY (responsavel_id) REFERENCES usuarios(id)
            ON UPDATE CASCADE ON DELETE SET NULL
        -- OBS: fk_acoes_cc será adicionada abaixo de forma condicional
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # --------- Ajustes condicionais (sem IF NOT EXISTS no SQL) ---------

    # 1) Garante a coluna centro_custos_id
    cur.execute("""
        SELECT 1
          FROM INFORMATION_SCHEMA.COLUMNS
         WHERE TABLE_SCHEMA = DATABASE()
           AND TABLE_NAME = 'acoes'
           AND COLUMN_NAME = 'centro_custos_id'
        LIMIT 1
    """)
    has_cc_col = cur.fetchone() is not None
    if not has_cc_col:
        cur.execute("ALTER TABLE acoes ADD COLUMN centro_custos_id INT NULL")

    # 2) Garante a FK fk_acoes_cc
    cur.execute("""
        SELECT 1
          FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS
         WHERE TABLE_SCHEMA = DATABASE()
           AND TABLE_NAME = 'acoes'
           AND CONSTRAINT_TYPE = 'FOREIGN KEY'
           AND CONSTRAINT_NAME = 'fk_acoes_cc'
        LIMIT 1
    """)
    has_cc_fk = cur.fetchone() is not None
    if not has_cc_fk:
        cur.execute("""
            ALTER TABLE acoes
            ADD CONSTRAINT fk_acoes_cc
            FOREIGN KEY (centro_custos_id)
            REFERENCES centros_custos(id)
            ON UPDATE CASCADE ON DELETE SET NULL
        """)

    # -------------------- Seeds mínimos --------------------
    cur.execute("SELECT id FROM superintendencias LIMIT 1")
    if not cur.fetchone():
        cur.execute("INSERT INTO superintendencias (nome) VALUES (%s)", ("Operações",))

    cur.execute("SELECT id FROM centros_custos LIMIT 1")
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO centros_custos (codigo, descricao) VALUES (%s, %s)",
            ("1.10.0052.13", "Manutenção - Empilhadeiras")
        )

    cur.execute("SELECT id FROM origens LIMIT 1")
    if not cur.fetchone():
        cur.execute("INSERT INTO origens (nome) VALUES (%s)", ("Reunião mensal",))

    cur.execute("SELECT id FROM usuarios WHERE email=%s", ("admin@local",))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO usuarios (nome, email, senha_hash, ativo, perfil) VALUES (%s, %s, %s, %s, %s)",
            ("Administrador", "admin@local", generate_password_hash("Admin@123"), True, "admin")
        )

    conn.commit()
    cur.close()
    conn.close()
