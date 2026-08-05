from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


def create_app(test_config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object("config.Config")

    if test_config:
        app.config.from_mapping(test_config)

    db.init_app(app)

    from app import models
    from app.routes import main

    app.register_blueprint(main)
    return app
