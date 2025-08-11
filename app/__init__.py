from flask import Flask
from flask_mail import Mail
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from zoneinfo import ZoneInfo  # stdlib (Python 3.9+)

mail = Mail()

def create_app():
    app = Flask(__name__)

    # --- Configs básicas
    app.secret_key = 'sua_chave_secreta_segura'
    app.config['UPLOAD_FOLDER'] = 'app/static/evidencias'

    # --- E-mail
    app.config['MAIL_SERVER'] = 'smtps.uhserver.com'
    app.config['MAIL_PORT'] = 465
    app.config['MAIL_USE_SSL'] = True
    app.config['MAIL_USERNAME'] = 'trackplan@trackplan.com.br'
    app.config['MAIL_PASSWORD'] = '7EE@@95a3h'
    app.config['MAIL_DEFAULT_SENDER'] = 'trackplan@trackplan.com.br'
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

