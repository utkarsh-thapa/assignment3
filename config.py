import os


class Config:
    """Default application configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", "sqlite:///volunteer_board.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
