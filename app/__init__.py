from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


@login_manager.user_loader
def load_user(user_id):
    """Load a logged-in user from the signed session cookie."""
    from app.models import User

    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


def create_app(test_config=None):
    """Create and configure the Flask application."""
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object("config.Config")

    if test_config:
        app.config.from_mapping(test_config)

    if app.config.get("TESTING") and not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = "test-only-secret"

    if not app.config.get("TESTING") and not app.config.get("SECRET_KEY"):
        raise RuntimeError(
            "SECRET_KEY is required. Copy .env.example to .env and set a random value."
        )

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "main.account"
    login_manager.login_message = "Please log in to continue."
    login_manager.login_message_category = "info"
    login_manager.session_protection = "strong"

    from app import models
    from app.routes import main

    app.register_blueprint(main)

    with app.app_context():
        db.create_all()

    @app.errorhandler(CSRFError)
    def handle_csrf_error(_error):
        return "Invalid or expired form submission. Please try again.", 400

    return app
