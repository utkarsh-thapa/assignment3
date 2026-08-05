from flask import Flask


def create_app(test_config=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)

    if test_config:
        app.config.from_mapping(test_config)

    from app.routes import main

    app.register_blueprint(main)
    return app
