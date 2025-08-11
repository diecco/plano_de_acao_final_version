import mysql.connector

# Configurações do banco de dados
config = {
    'host': 'localhost',
    'user': 'root',  # Substitua se seu usuário for diferente
    'password': '7EE@@95a3h',  # Substitua pela sua senha real
    'database': 'plano_de_acao'
}

# Novo hash gerado para senha "admin123"
novo_hash = "pbkdf2:sha256:260000$0Q7Pki9GPtGOay3q$47925d3f0270ec78c8e40557d5200fdc2280e3726dfb93c0e2557aab8b2a4aeb"

try:
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()

    # Atualizar a senha do administrador
    sql = """
    UPDATE usuarios
    SET senha_hash = %s
    WHERE email = 'admin@empresa.com';
    """
    cursor.execute(sql, (novo_hash,))
    conn.commit()

    print("Senha atualizada com sucesso!")

except mysql.connector.Error as err:
    print(f"Erro ao conectar ou atualizar o banco: {err}")

finally:
    if 'conn' in locals() and conn.is_connected():
        cursor.close()
        conn.close()
