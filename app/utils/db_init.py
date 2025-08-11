# app/utils/db_init.py
from werkzeug.security import generate_password_hash
from .db import get_db_connection

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # Tabela de usuários (ajuste nomes/tamanhos se quiser)
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

    # (OPCIONAL) Semeia 1 admin se não existir
    cur.execute("SELECT id FROM usuarios WHERE email=%s", ("admin@local",))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO usuarios (nome, email, senha_hash, ativo, perfil) VALUES (%s, %s, %s, %s, %s)",
            ("Administrador", "admin@local", generate_password_hash("Admin@123"), True, "admin")
        )

    conn.commit()
    cur.close()
    conn.close()
