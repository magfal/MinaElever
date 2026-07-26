import os
from dotenv import load_dotenv
from flask import Flask

load_dotenv()

from .extensions import db
from .auth.service import init_auth

def configure_app(app):
    """Konfigurera Flask-applikationen."""
    default_db = "sqlite:///mina_elever.db"
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
        "DATABASE_URL",
        default_db
    )
    app.config["SECRET_KEY"] = "en-valfri-hemlig-text-sträng"

def register_extensions(app):
    """Initiera Flask-tillägg."""
    db.init_app(app)

def register_blueprints(app):
    """Registrera alla blueprints."""
    from .routes.auth import auth_bp
    from .routes.dashboard import dashboard_bp
    from .routes.students import students_bp
    from .routes.groups import groups_bp
    from .routes.questions import questions_bp
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

def create_app():
    app = Flask(__name__,
                template_folder="../templates",
                static_folder="../static")
    configure_app(app)
    register_extensions(app)
    init_auth(app)
    register_blueprints(app)
    register_commands(app)
    return app