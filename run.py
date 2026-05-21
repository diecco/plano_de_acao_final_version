import os
from app import create_app
from app.utils.db_init import init_db

app = create_app()

if os.getenv("INIT_DB", "false").lower() == "true":
    init_db()

if __name__ == '__main__':
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    port = int(os.getenv("PORT", 5000))

    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug
    )