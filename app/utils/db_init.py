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

    # --- origens (para o dropdown de origem da ação) ---
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
            ON UPDATE CASCADE ON DELETE SET NULL,
        CONSTRAINT fk_acoes_cc
            FOREIGN KEY (centro_custos_id) REFERENCES centros_custos(id)
            ON UPDATE CASCADE ON DELETE SET NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # Caso a tabela 'acoes' já existisse sem a coluna centro_custos_id, garante inclusão (MySQL 8+)
    cur.execute("""
    ALTER TABLE acoes
    ADD COLUMN IF NOT EXISTS centro_custos_id INT NULL,
    ADD CONSTRAINT IF NOT EXISTS fk_acoes_cc
        FOREIGN KEY (centro_custos_id) REFERENCES centros_custos(id)
        ON UPDATE CASCADE ON DELETE SET NULL;
    """)

    # --- seeds mínimos ---
    # superintendência
    cur.execute("SELECT id FROM superintendencias LIMIT 1")
    if not cur.fetchone():
        cur.execute("INSERT INTO superintendencias (nome) VALUES (%s)", ("Operações",))

    # centro de custos
    cur.execute("SELECT id FROM centros_custos LIMIT 1")
    if not cur.fetchone():
        # Ajuste o código/descrição conforme seu padrão
        cur.execute(
            "INSERT INTO centros_custos (codigo, descricao) VALUES (%s, %s)",
            ("1.10.0052.13", "Manutenção - Empilhadeiras")
        )

    # origem
    cur.execute("SELECT id FROM origens LIMIT 1")
    if not cur.fetchone():
        cur.execute("INSERT INTO origens (nome) VALUES (%s)", ("Reunião mensal",))

    # admin
    cur.execute("SELECT id FROM usuarios WHERE email=%s", ("admin@local",))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO usuarios (nome, email, senha_hash, ativo, perfil) VALUES (%s, %s, %s, %s, %s)",
            ("Administrador", "admin@local", generate_password_hash("Admin@123"), True, "admin")
        )

    conn.commit()
    cur.close()
    conn.close()
