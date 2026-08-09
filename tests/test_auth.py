import re

import pytest

from app import create_app, db
from app.models import User


@pytest.fixture
def app():
    test_app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        }
    )

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def register(client, *, email="student@example.com", role="student"):
    return client.post(
        "/register",
        data={
            "register-name": "Test User",
            "register-email": email,
            "register-password": "SecurePassword123!",
            "register-role": role,
        },
    )


def test_password_is_hashed_and_checked():
    user = User()

    user.set_password("SecurePassword123!")

    assert user.password_hash != "SecurePassword123!"
    assert user.check_password("SecurePassword123!") is True
    assert user.check_password("WrongPassword") is False


def test_user_supports_login_session():
    user = User(id=42)

    assert user.get_id() == "42"
    assert user.is_authenticated is True


def test_account_screen_loads(client):
    response = client.get("/account")

    assert response.status_code == 200
    assert b"Create account" in response.data
    assert b"Log in" in response.data


@pytest.mark.parametrize("role", ["student", "charity"])
def test_account_can_be_created_for_each_role(app, client, role):
    response = register(client, email=f"{role}@example.com", role=role)

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")

    with app.app_context():
        user = db.session.scalar(
            db.select(User).where(User.email == f"{role}@example.com")
        )
        assert user is not None
        assert user.role == role
        assert user.password_hash != "SecurePassword123!"
        assert user.check_password("SecurePassword123!") is True


def test_invalid_registration_is_rejected(app, client):
    response = client.post(
        "/register",
        data={
            "register-name": "A",
            "register-email": "not-an-email",
            "register-password": "short",
            "register-role": "admin",
        },
    )

    assert response.status_code == 400
    with app.app_context():
        assert db.session.scalar(db.select(User)) is None


def test_duplicate_email_is_rejected_case_insensitively(app, client):
    first_response = register(client, email="Person@Example.com")
    assert first_response.status_code == 302

    client.post("/logout")
    duplicate_response = register(client, email="person@example.com")

    assert duplicate_response.status_code == 400
    assert b"already exists" in duplicate_response.data
    with app.app_context():
        assert db.session.query(User).count() == 1


def test_valid_user_can_log_in_and_log_out(client):
    register(client)
    client.post("/logout")

    login_response = client.post(
        "/login",
        data={
            "login-email": "STUDENT@example.com",
            "login-password": "SecurePassword123!",
        },
    )
    assert login_response.status_code == 302
    assert login_response.headers["Location"].endswith("/dashboard")

    dashboard_response = client.get("/dashboard")
    assert dashboard_response.status_code == 200
    assert b"Test User" in dashboard_response.data

    logout_response = client.post("/logout")
    assert logout_response.status_code == 302
    assert logout_response.headers["Location"].endswith("/account")


def test_incorrect_password_uses_safe_error(client):
    register(client)
    client.post("/logout")

    response = client.post(
        "/login",
        data={
            "login-email": "student@example.com",
            "login-password": "WrongPassword",
        },
    )

    assert response.status_code == 400
    assert b"Invalid email or password" in response.data
    assert b"SecurePassword123" not in response.data


def test_private_dashboard_requires_login(client):
    response = client.get("/dashboard")

    assert response.status_code == 302
    assert "/account" in response.headers["Location"]


def test_sql_injection_style_login_does_not_authenticate(client):
    response = client.post(
        "/login",
        data={
            "login-email": "' OR '1'='1@example.com",
            "login-password": "' OR '1'='1",
        },
    )

    assert response.status_code == 400
    dashboard_response = client.get("/dashboard")
    assert dashboard_response.status_code == 302
    assert "/account" in dashboard_response.headers["Location"]


def test_post_without_csrf_token_is_rejected():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "csrf-test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": True,
        }
    )
    client = app.test_client()

    response = client.post(
        "/login",
        data={
            "login-email": "student@example.com",
            "login-password": "SecurePassword123!",
        },
    )

    assert response.status_code == 400
    assert b"Invalid or expired form submission" in response.data


def test_registration_succeeds_with_real_csrf_token():
    app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "csrf-test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": True,
        }
    )
    client = app.test_client()

    account_response = client.get("/account")
    token_match = re.search(
        rb'name="register-csrf_token"[^>]*value="([^"]+)"',
        account_response.data,
    )
    assert token_match is not None

    response = client.post(
        "/register",
        data={
            "register-csrf_token": token_match.group(1).decode(),
            "register-name": "CSRF Test Student",
            "register-email": "csrf-student@example.com",
            "register-password": "SecurePassword123!",
            "register-role": "student",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")
