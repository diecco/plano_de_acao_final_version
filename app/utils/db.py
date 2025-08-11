import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='7EE@@95a3h',
        database='plano_de_acao'
    )
