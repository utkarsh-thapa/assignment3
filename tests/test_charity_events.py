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


def login_as_charity(app, client):
    with app.app_context():
        charity = User(
            name="Helping Hands",
            email="charity-events@example.com",
            role="charity",
        )
        charity.set_password("CharityPassword123!")
        db.session.add(charity)
        db.session.commit()

    response = client.post(
        "/login",
        data={
            "login-email": "charity-events@example.com",
            "login-password": "CharityPassword123!",
        },
    )
    assert response.status_code == 302


def login_as_student(app, client):
    with app.app_context():
        student = User(
            name="Volunteer Student",
            email="student-events@example.com",
            role="student",
        )
        student.set_password("StudentPassword123!")
        db.session.add(student)
        db.session.commit()

    response = client.post(
        "/login",
        data={
            "login-email": "student-events@example.com",
            "login-password": "StudentPassword123!",
        },
    )
    assert response.status_code == 302


def test_charity_dashboard_shows_event_creation_form(app, client):
    login_as_charity(app, client)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert b"Create volunteer event" in response.data
    assert b'name="event-title"' in response.data
    assert b'name="event-description"' in response.data
    assert b'name="event-date_time"' in response.data
    assert b'name="event-location"' in response.data
    assert b'name="event-capacity"' in response.data


def test_charity_can_create_valid_event(app, client):
    login_as_charity(app, client)
    future_date = (
        datetime.now() + timedelta(days=7)
    ).replace(second=0, microsecond=0)

    response = client.post(
        "/events",
        data={
            "event-title": "Community Garden Day",
            "event-description": (
                "Help prepare the local community garden."
            ),
            "event-date_time": future_date.strftime("%Y-%m-%dT%H:%M"),
            "event-location": "Carlton Community Garden",
            "event-capacity": "20",
        },
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/dashboard")

    with app.app_context():
        event = db.session.scalar(
            db.select(Event).where(
                Event.title == "Community Garden Day"
            )
        )
        charity = db.session.scalar(
            db.select(User).where(
                User.email == "charity-events@example.com"
            )
        )

        assert event is not None
        assert event.description == (
            "Help prepare the local community garden."
        )
        assert event.date_time == future_date
        assert event.location == "Carlton Community Garden"
        assert event.capacity == 20
        assert event.charity_id == charity.id

@pytest.mark.parametrize(
    ("field_name", "invalid_value"),
    [
        ("event-title", "   "),
        ("event-title", " A "),
        ("event-description", "          "),
        ("event-description", " 12345678 "),
        ("event-date_time", "2000-01-01T12:00"),
        ("event-location", "   "),
        ("event-capacity", "0"),
    ],
    ids=[
        "blank-title",
        "short-title-after-trimming",
        "blank-description",
        "short-description-after-trimming",
        "past-date",
        "blank-location",
        "zero-capacity",
    ],
)
def test_invalid_event_information_is_rejected(
    app,
    client,
    field_name,
    invalid_value,
):
    login_as_charity(app, client)
    future_date = (
        datetime.now() + timedelta(days=7)
    ).replace(second=0, microsecond=0)

    event_data = {
        "event-title": "Food Bank Support",
        "event-description": (
            "Help organise food donations for local families."
        ),
        "event-date_time": future_date.strftime("%Y-%m-%dT%H:%M"),
        "event-location": "Melbourne Community Centre",
        "event-capacity": "15",
    }
    event_data[field_name] = invalid_value

    response = client.post("/events", data=event_data)

    assert response.status_code == 400
    assert b"Traceback" not in response.data
    assert b"sqlalchemy" not in response.data.lower()
    if field_name == "event-capacity":
        assert b"Number must be between 1 and 10000" in response.data

    with app.app_context():
        assert db.session.query(Event).count() == 0


def test_student_dashboard_hides_event_creation_form(app, client):
    login_as_student(app, client)

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert b"Create volunteer event" not in response.data
    assert b'name="event-title"' not in response.data


def test_student_cannot_create_event(app, client):
    login_as_student(app, client)
    future_date = (
        datetime.now() + timedelta(days=7)
    ).replace(second=0, microsecond=0)

    response = client.post(
        "/events",
        data={
            "event-title": "Unauthorised Event",
            "event-description": (
                "A Student must not be allowed to create this event."
            ),
            "event-date_time": future_date.strftime("%Y-%m-%dT%H:%M"),
            "event-location": "Student Hall",
            "event-capacity": "20",
        },
    )

    assert response.status_code == 403

    with app.app_context():
        assert db.session.query(Event).count() == 0


def test_event_creation_requires_login(app, client):
    response = client.post("/events")

    assert response.status_code == 302
    assert "/account" in response.headers["Location"]

    with app.app_context():
        assert db.session.query(Event).count() == 0


def test_event_creation_without_csrf_token_is_rejected():
    csrf_app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "event-csrf-test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": True,
        }
    )
    csrf_client = csrf_app.test_client()

    with csrf_app.app_context():
        charity = User(
            name="CSRF Test Charity",
            email="csrf-charity@example.com",
            role="charity",
        )
        charity.set_password("CharityPassword123!")
        db.session.add(charity)
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
            "login-email": "csrf-charity@example.com",
            "login-password": "CharityPassword123!",
        },
    )
    assert login_response.status_code == 302

    future_date = (
        datetime.now() + timedelta(days=7)
    ).replace(second=0, microsecond=0)
    response = csrf_client.post(
        "/events",
        data={
            "event-title": "Missing CSRF Event",
            "event-description": (
                "This request intentionally has no CSRF token."
            ),
            "event-date_time": future_date.strftime("%Y-%m-%dT%H:%M"),
            "event-location": "Security Test Hall",
            "event-capacity": "10",
        },
    )

    assert response.status_code == 400
    assert b"Invalid or expired form submission" in response.data

    with csrf_app.app_context():
        assert db.session.query(Event).count() == 0
        db.session.remove()
        db.drop_all()
