from app import create_app
from app.utils.db_init import init_db  # importa a função de inicialização

app = create_app()

# Inicializa o banco (cria tabelas e admin, se não existir)
init_db()

if __name__ == '__main__':
    app.run(debug=True)
