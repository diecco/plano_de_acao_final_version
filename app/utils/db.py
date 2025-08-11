import os
import mysql.connector
from urllib.parse import urlparse, parse_qs

def get_db_connection():
    # Lê a URL do banco das variáveis de ambiente
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL não está definida nas variáveis de ambiente.")

    # Ajusta para o urlparse entender
    if db_url.startswith("mysql+mysqlconnector://"):
        db_url = db_url.replace("mysql+mysqlconnector://", "mysql://", 1)

    # Faz o parse da URL
    parsed_url = urlparse(db_url)
    query_params = parse_qs(parsed_url.query)

    # Nome do banco
    db_name = parsed_url.path.lstrip("/")

    # Configuração de SSL
    ssl_mode = query_params.get("ssl-mode", ["DISABLED"])[0].upper()
    ssl_disabled = not (ssl_mode == "REQUIRED")

    # Conecta usando as credenciais da DATABASE_URL
    conn = mysql.connector.connect(
        host=parsed_url.hostname,
        port=parsed_url.port or 3306,
        user=parsed_url.username,
        password=parsed_url.password,
        database=db_name,
        ssl_disabled=ssl_disabled,
        connection_timeout=10
    )
    return conn
