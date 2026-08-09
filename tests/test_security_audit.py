import re
from datetime import datetime, timedelta

import pytest

from app import create_app, db
from app.models import Event, User


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


@pytest.mark.parametrize(
    "unsafe_secret",
    [
        None,
        "short-secret",
        " " * 32,
        ("a" * 31) + " ",
        "replace-with-a-random-secret-value",
        "  replace-with-a-random-secret-value  ",
    ],
)
def test_non_test_app_rejects_missing_weak_or_placeholder_secret(
    unsafe_secret,
):
    with pytest.raises(RuntimeError, match="surrounding whitespace"):
        create_app(
            {
                "TESTING": False,
                "SECRET_KEY": unsafe_secret,
                "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            }
        )


def test_non_test_app_normalises_surrounding_secret_whitespace():
    valid_secret = "a" * 32
    production_app = create_app(
        {
            "TESTING": False,
            "SECRET_KEY": f"  {valid_secret}  ",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    assert production_app.config["SECRET_KEY"] == valid_secret
    with production_app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/dashboard"),
        ("get", "/events/1"),
        ("post", "/events"),
        ("post", "/events/1/register"),
        ("post", "/logout"),
    ],
)
def test_every_private_route_redirects_unauthenticated_visitors(
    client,
    method,
    path,
):
    response = getattr(client, method)(path)

    assert response.status_code == 302
    assert "/account" in response.headers["Location"]


def test_sql_injection_payload_does_not_authenticate_or_change_database(
    app,
    client,
):
    with app.app_context():
        user = User(
            name="Existing Student",
            email="existing@example.com",
            role="student",
        )
        user.set_password("SecurePassword123!")
        db.session.add(user)
        db.session.commit()

    email_payload = "or'1'='1@example.com"
    password_payload = "' OR '1'='1"
    response = client.post(
        "/login",
        data={
            "login-email": email_payload,
            "login-password": password_payload,
        },
    )

    assert response.status_code == 400
    assert b"Invalid email or password" in response.data
    assert b"Traceback" not in response.data
    assert b"sqlalchemy" not in response.data.lower()
    assert b"SecurePassword123!" not in response.data
    assert client.get("/dashboard").status_code == 302
    with app.app_context():
        assert db.session.query(User).count() == 1
        assert db.session.scalar(
            db.select(User).where(User.email == "existing@example.com")
        ) is not None


def test_user_content_is_html_escaped(app, client):
    with app.app_context():
        charity = User(
            name="Safety Charity",
            email="escaping-charity@example.com",
            role="charity",
        )
        charity.set_password("SecurePassword123!")
        event = Event(
            title="<script>alert('unsafe')</script>",
            description="A description containing enough safe test text.",
            date_time=datetime.now() + timedelta(days=7),
            location="Community Hall",
            capacity=5,
            charity=charity,
        )
        db.session.add_all([charity, event])
        db.session.commit()
        event_id = event.id

    client.post(
        "/login",
        data={
            "login-email": "escaping-charity@example.com",
            "login-password": "SecurePassword123!",
        },
    )
    response = client.get(f"/events/{event_id}")

    assert response.status_code == 200
    assert b"<script>" not in response.data
    assert b"&lt;script&gt;" in response.data


def test_session_cookie_has_http_only_and_same_site_flags(app, client):
    with app.app_context():
        user = User(
            name="Cookie Test Student",
            email="cookie-student@example.com",
            role="student",
        )
        user.set_password("SecurePassword123!")
        db.session.add(user)
        db.session.commit()

    response = client.post(
        "/login",
        data={
            "login-email": "cookie-student@example.com",
            "login-password": "SecurePassword123!",
        },
    )
    session_cookie = response.headers.get("Set-Cookie", "")

    assert "HttpOnly" in session_cookie
    assert "SameSite=Lax" in session_cookie


def test_account_creation_without_csrf_token_is_rejected():
    csrf_app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "account-csrf-audit-test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": True,
        }
    )
    csrf_client = csrf_app.test_client()

    response = csrf_client.post(
        "/register",
        data={
            "register-name": "Forged Student",
            "register-email": "forged@example.com",
            "register-password": "SecurePassword123!",
            "register-role": "student",
        },
    )

    assert response.status_code == 400
    assert b"Invalid or expired form submission" in response.data
    with csrf_app.app_context():
        assert db.session.query(User).count() == 0
        db.session.remove()
        db.drop_all()


def test_logout_without_csrf_token_is_rejected_and_session_remains_active():
    csrf_app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "csrf-audit-test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": True,
        }
    )
    csrf_client = csrf_app.test_client()

    with csrf_app.app_context():
        user = User(
            name="CSRF Audit Student",
            email="csrf-audit-student@example.com",
            role="student",
        )
        user.set_password("SecurePassword123!")
        db.session.add(user)
        db.session.commit()

    account_response = csrf_client.get("/account")
    token_match = re.search(
        rb'name="login-csrf_token"[^>]*value="([^"]+)"',
        account_response.data,
    )
    assert token_match is not None
    login_response = csrf_client.post(
        "/login",
        data={
            "login-csrf_token": token_match.group(1).decode(),
            "login-email": "csrf-audit-student@example.com",
            "login-password": "SecurePassword123!",
        },
    )
    assert login_response.status_code == 302

    logout_response = csrf_client.post("/logout")

    assert logout_response.status_code == 400
    assert b"Invalid or expired form submission" in logout_response.data
    assert csrf_client.get("/dashboard").status_code == 200

    with csrf_app.app_context():
        db.session.remove()
        db.drop_all()
