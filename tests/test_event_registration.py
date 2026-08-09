import re
from datetime import datetime, timedelta

import pytest

from app import create_app, db
from app.models import Event, Registration, User


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


def create_user(app, *, email, role):
    with app.app_context():
        user = User(name=f"Test {role}", email=email, role=role)
        user.set_password("SecurePassword123!")
        db.session.add(user)
        db.session.commit()
        return user.id


def create_event(app, charity_id, *, days_from_now=7, capacity=2):
    with app.app_context():
        event = Event(
            title="Food Bank Volunteer Shift",
            description="Sort and prepare food donations for local families.",
            date_time=datetime.now() + timedelta(days=days_from_now),
            location="Melbourne Community Centre",
            capacity=capacity,
            charity_id=charity_id,
        )
        db.session.add(event)
        db.session.commit()
        return event.id


def login(client, email):
    response = client.post(
        "/login",
        data={
            "login-email": email,
            "login-password": "SecurePassword123!",
        },
    )
    assert response.status_code == 302


def registration_data():
    return {"event-registration-submit": "Register for this event"}


def test_student_can_register_once_and_available_places_decrease(app, client):
    charity_id = create_user(
        app, email="charity-registration@example.com", role="charity"
    )
    student_id = create_user(
        app, email="student-registration@example.com", role="student"
    )
    event_id = create_event(app, charity_id, capacity=2)
    login(client, "student-registration@example.com")

    response = client.post(
        f"/events/{event_id}/register",
        data=registration_data(),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"You are registered for this event." in response.data
    assert b"<strong>Available places:</strong> 1" in response.data

    with app.app_context():
        registrations = db.session.scalars(
            db.select(Registration).where(
                Registration.event_id == event_id
            )
        ).all()
        assert len(registrations) == 1
        assert registrations[0].student_id == student_id
        assert registrations[0].status == "registered"


def test_duplicate_registration_is_rejected(app, client):
    charity_id = create_user(
        app, email="duplicate-charity@example.com", role="charity"
    )
    create_user(app, email="duplicate-student@example.com", role="student")
    event_id = create_event(app, charity_id)
    login(client, "duplicate-student@example.com")

    client.post(f"/events/{event_id}/register", data=registration_data())
    response = client.post(
        f"/events/{event_id}/register",
        data=registration_data(),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"You are already registered for this event." in response.data
    with app.app_context():
        assert db.session.query(Registration).count() == 1


def test_registration_for_full_event_is_rejected(app, client):
    charity_id = create_user(
        app, email="full-charity@example.com", role="charity"
    )
    first_student_id = create_user(
        app, email="first-student@example.com", role="student"
    )
    create_user(app, email="second-student@example.com", role="student")
    event_id = create_event(app, charity_id, capacity=1)

    with app.app_context():
        db.session.add(
            Registration(student_id=first_student_id, event_id=event_id)
        )
        db.session.commit()

    login(client, "second-student@example.com")
    response = client.post(
        f"/events/{event_id}/register",
        data=registration_data(),
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"This event is full." in response.data
    with app.app_context():
        assert db.session.query(Registration).count() == 1


def test_registration_for_past_event_is_rejected(app, client):
    charity_id = create_user(
        app, email="past-charity@example.com", role="charity"
    )
    create_user(app, email="past-student@example.com", role="student")
    event_id = create_event(app, charity_id, days_from_now=-1)
    login(client, "past-student@example.com")

    response = client.post(
        f"/events/{event_id}/register", data=registration_data()
    )

    assert response.status_code == 404
    with app.app_context():
        assert db.session.query(Registration).count() == 0


def test_charity_cannot_register_for_event(app, client):
    charity_id = create_user(
        app, email="owner-charity@example.com", role="charity"
    )
    event_id = create_event(app, charity_id)
    login(client, "owner-charity@example.com")

    response = client.post(
        f"/events/{event_id}/register", data=registration_data()
    )

    assert response.status_code == 403
    with app.app_context():
        assert db.session.query(Registration).count() == 0


def test_registration_requires_login(app, client):
    charity_id = create_user(
        app, email="login-charity@example.com", role="charity"
    )
    event_id = create_event(app, charity_id)

    response = client.post(
        f"/events/{event_id}/register", data=registration_data()
    )

    assert response.status_code == 302
    assert "/account" in response.headers["Location"]
    with app.app_context():
        assert db.session.query(Registration).count() == 0


def test_event_details_show_complete_information_and_registration_button(
    app, client
):
    charity_id = create_user(
        app, email="details-charity@example.com", role="charity"
    )
    create_user(app, email="details-student@example.com", role="student")
    event_id = create_event(app, charity_id)
    login(client, "details-student@example.com")

    response = client.get(f"/events/{event_id}")

    assert response.status_code == 200
    assert b"Food Bank Volunteer Shift" in response.data
    assert b"Sort and prepare food donations" in response.data
    assert b"Test charity" in response.data
    assert b"Melbourne Community Centre" in response.data
    assert b"<strong>Capacity:</strong> 2" in response.data
    assert b"Register for this event" in response.data


def test_full_event_details_hide_registration_button(app, client):
    charity_id = create_user(
        app, email="hidden-charity@example.com", role="charity"
    )
    first_student_id = create_user(
        app, email="occupying-student@example.com", role="student"
    )
    create_user(app, email="viewing-student@example.com", role="student")
    event_id = create_event(app, charity_id, capacity=1)

    with app.app_context():
        db.session.add(
            Registration(student_id=first_student_id, event_id=event_id)
        )
        db.session.commit()

    login(client, "viewing-student@example.com")
    response = client.get(f"/events/{event_id}")

    assert response.status_code == 200
    assert b"This event is full." in response.data
    assert b"Register for this event" not in response.data


def test_registration_without_csrf_token_is_rejected():
    csrf_app = create_app(
        {
            "TESTING": True,
            "SECRET_KEY": "registration-csrf-test-secret",
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": True,
        }
    )
    csrf_client = csrf_app.test_client()

    with csrf_app.app_context():
        charity = User(
            name="CSRF Charity",
            email="csrf-registration-charity@example.com",
            role="charity",
        )
        charity.set_password("SecurePassword123!")
        student = User(
            name="CSRF Student",
            email="csrf-registration-student@example.com",
            role="student",
        )
        student.set_password("SecurePassword123!")
        db.session.add_all([charity, student])
        db.session.flush()
        event = Event(
            title="Secure Volunteer Event",
            description="A future event used to test request protection.",
            date_time=datetime.now() + timedelta(days=7),
            location="Secure Community Hall",
            capacity=5,
            charity_id=charity.id,
        )
        db.session.add(event)
        db.session.commit()
        event_id = event.id

    account_response = csrf_client.get("/account")
    token_match = re.search(
        rb'name="login-csrf_token"[^>]*value="([^"]+)"',
        account_response.data,
    )
    assert token_match is not None
    csrf_client.post(
        "/login",
        data={
            "login-csrf_token": token_match.group(1).decode(),
            "login-email": "csrf-registration-student@example.com",
            "login-password": "SecurePassword123!",
        },
    )

    response = csrf_client.post(
        f"/events/{event_id}/register", data=registration_data()
    )

    assert response.status_code == 400
    with csrf_app.app_context():
        assert db.session.query(Registration).count() == 0
        db.session.remove()
        db.drop_all()
