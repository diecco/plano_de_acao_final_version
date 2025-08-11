# app/utils/db_init.py
from werkzeug.security import generate_password_hash
from .db import get_db_connection

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # --- Tabela usuarios ---
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

    # --- Tabela origens (opcional, caso já use no cadastro de ações) ---
    cur.execute("""
    CREATE TABLE IF NOT EXISTS origens (
        id INT AUTO_INCREMENT PRIMARY KEY,
        nome VARCHAR(100) NOT NULL UNIQUE,
        ativo BOOLEAN NOT NULL DEFAULT TRUE,
        criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # --- Tabela acoes (mínimo necessário p/ dashboard e atualizações por prazo) ---
    # status é VARCHAR para compatibilizar com valores no seu sistema:
    # 'Não iniciada', 'Em andamento', 'Atrasada', 'Concluída'
    cur.execute("""
    CREATE TABLE IF NOT EXISTS acoes (
        id INT AUTO_INCREMENT PRIMARY KEY,
        origem_id INT NULL,
        responsavel_id INT NULL,
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
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
    """)

    # (Opcional) Semeia um registro de origem se a tabela estiver vazia
    cur.execute("SELECT id FROM origens LIMIT 1")
    if not cur.fetchone():
        cur.execute("INSERT INTO origens (nome) VALUES (%s)", ("Reunião mensal",))

    # (Opcional) Semeia um admin se não existir
    cur.execute("SELECT id FROM usuarios WHERE email=%s", ("admin@local",))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO usuarios (nome, email, senha_hash, ativo, perfil) VALUES (%s, %s, %s, %s, %s)",
            ("Administrador", "admin@local", generate_password_hash("Admin@123"), True, "admin")
        )

    conn.commit()
    cur.close()
    conn.close()
