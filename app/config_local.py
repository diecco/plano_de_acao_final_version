import os

class Config:
    SQLALCHEMY_DATABASE_URI = (
        "mysql+mysqlconnector://trackplan:Trackplan%40123@localhost:3306/plano_de_acao_teste"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # E-mail local (não obrigatório funcionar agora)
    MAIL_SERVER = 'smtps.uhserver.com'
    MAIL_PORT = 465
    MAIL_USE_SSL = True
    MAIL_USERNAME = 'trackplan@trackplan.com.br'
    MAIL_PASSWORD = '7EE@@95a3h'
    MAIL_DEFAULT_SENDER = 'trackplan@trackplan.com.br'
