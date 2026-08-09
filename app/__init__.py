from dotenv import load_dotenv
from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

_SECRET_KEY_PLACEHOLDER = "replace-with-a-random-secret-value"
_MINIMUM_SECRET_KEY_LENGTH = 32


@login_manager.user_loader
def load_user(user_id):
    """Load a logged-in user from the signed session cookie."""
    from app.models import User

    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None


def _validate_secret_key(app):
    """Enforce production key format outside the test environment."""
    if app.config.get("TESTING"):
        if not app.config.get("SECRET_KEY"):
            app.config["SECRET_KEY"] = "test-only-secret"
        return

    configured_secret = app.config.get("SECRET_KEY")
    secret_key = (
        configured_secret.strip()
        if isinstance(configured_secret, str)
        else None
    )
    if (
        secret_key is None
        or len(secret_key) < _MINIMUM_SECRET_KEY_LENGTH
        or secret_key == _SECRET_KEY_PLACEHOLDER
    ):
        raise RuntimeError(
            "SECRET_KEY must contain at least 32 characters after "
            "surrounding whitespace is removed and cannot use the public "
            "placeholder. See README.md for setup instructions."
        )

    app.config["SECRET_KEY"] = secret_key


def create_app(test_config=None):
    """Create and configure the Flask application."""
    load_dotenv()
    app = Flask(__name__)
    app.config.from_object("config.Config")

    if test_config:
        app.config.from_mapping(test_config)

    _validate_secret_key(app)

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
