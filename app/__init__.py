# app/__init__.py
#
# Application factory för Flask.
#
# Denna fil bygger hela applikationen:
#
# 1. Läser konfiguration
# 2. Kopplar databasen
# 3. Aktiverar autentisering
# 4. Registrerar blueprints (routes)
# 5. Lägger till CLI-kommandon
# 6. Registrerar felhantering
#
# Vi använder create_app() istället för en global Flask-instans
# för att undvika cirkulära importer och göra applikationen
# enklare att testa och vidareutveckla.
#

import os
from dotenv import load_dotenv
from flask import Flask, render_template
from sqlalchemy.exc import SQLAlchemyError
from .services.auth import register_auth
from .extensions import db

load_dotenv()

def configure_app(app):
    """
    Grundkonfiguration av Flask-applikationen.

    Här sätts:
    - databasanslutning
    - secret key
    - andra globala Flask-inställningar

    Miljövariabler prioriteras framför standardvärden.
    """
    default_db = "sqlite:///mina_elever.db"
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL",
        default_db
    )
    app.config["SECRET_KEY"] = "en-valfri-hemlig-text-sträng"

def register_extensions(app):
    """
    Kopplar Flask-tillägg till den skapade app-instansen.

    Exempel:
    SQLAlchemy, Mail, LoginManager osv.

    Själva objekten skapas i extensions.py,
    men initieras först här.
    """
    db.init_app(app)

def register_blueprints(app):
    """
    Registrerar applikationens olika delar.

    Varje blueprint ansvarar för ett eget område:
    - students
    - groups
    - assignments
    - statistics osv.

    Detta håller routes separerade och skalbara.
    """
    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.students import students_bp
    from .routes.groups import groups_bp
    from .routes.questions import questions_bp
    from .routes.tags import tags_bp
    from .routes.templates import templates_bp
    from .routes.assignments import assignments_bp
    from .routes.responses import responses_bp
    from .routes.statistics import statistics_bp
    from .routes.gamification import gamification_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(groups_bp)
    app.register_blueprint(questions_bp)
    app.register_blueprint(tags_bp)
    app.register_blueprint(templates_bp)
    app.register_blueprint(assignments_bp)
    app.register_blueprint(responses_bp)
    app.register_blueprint(statistics_bp)
    app.register_blueprint(gamification_bp)

def register_commands(app):
    @app.cli.command("create-db")
    def create_db():
        with app.app_context():
            db.create_all()
            print("Databasen är skapad!")

def register_error_handlers(app):
    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error(error):
        db.session.rollback()
        return (
            render_template(
                "errors/db_error.html",
                error=error
            ),
            500,
        )
    
    @app.errorhandler(404)
    def page_not_found(error):
        return render_template(
            "errors/404.html"
        ), 404
    
    @app.errorhandler(500)
    def internal_server_error(error):
        return render_template(
            "errors/500.html",
            error=error
        ), 500
    
def create_app():
    """
    Skapar och returnerar Flask-applikationen.

    Detta är startpunkten som används av run.py:

        from app import create_app
        app = create_app()

    All uppbyggnad av applikationen sker här.
    """
    app = Flask(__name__,
                template_folder="../templates",
                static_folder="../static")
    configure_app(app)
    register_extensions(app)
    register_auth(app)
    register_blueprints(app)
    register_commands(app)
    register_error_handlers(app) 
    return app