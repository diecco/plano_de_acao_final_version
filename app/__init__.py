from flask import Flask
from flask_mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo  # stdlib (Python 3.9+)
from dotenv import load_dotenv, find_dotenv
import os
import secrets

mail = Mail()

# Força carregar o .env e sobrescrever variáveis existentes
load_dotenv(find_dotenv())

def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config_local.Config")

    # --- Configs básicas
    app.secret_key = os.getenv('SECRET_KEY') or secrets.token_hex(32)
    app.config['UPLOAD_FOLDER'] = 'app/static/evidencias'
    # Limite total por requisição, incluindo os campos do formulário.
    app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024

    # No servidor, direciona todos os uploads para o disco persistente.
    # Em desenvolvimento local, sem UPLOAD_ROOT, nada é alterado.
    from app.upload_security import configurar_uploads_persistentes
    configurar_uploads_persistentes(app)

    # --- E-mail
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', '465'))
    app.config['MAIL_USE_SSL'] = os.getenv('MAIL_USE_SSL', 'true').lower() == 'true'
    app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = (
        os.getenv('MAIL_DEFAULT_SENDER') or app.config['MAIL_USERNAME']
    )
    mail.init_app(app)

    # --- Blueprints (importe aqui para evitar import circular)
    from app.routes import main_routes
    app.register_blueprint(main_routes)

    # --- Scheduler (definido dentro da factory para ter app_context)
    def _job_send_reports():
        with app.app_context():
            try:
                from app.tasks import send_weekly_reports  # import tardio evita circularidade
                send_weekly_reports()
            except Exception as e:
                # Se tiver logger, troque por logger.exception(...)
                print(f"[Scheduler] Falha no envio de relatórios: {e}")

    scheduler = BackgroundScheduler(timezone=ZoneInfo("America/Sao_Paulo"))
    # Segunda-feira às 03:00
    scheduler.add_job(
        _job_send_reports,
        trigger=CronTrigger(day_of_week='mon', hour=3, minute=0)
    )
    scheduler.start()

    return app
