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


def create_registration_list_scenario(app, *, include_registrations=True):
    with app.app_context():
        owner = User(
            name="Helping Hands",
            email="owner-list@example.com",
            role="charity",
        )
        owner.set_password("CharityPassword123!")

        other_charity = User(
            name="Another Charity",
            email="other-list@example.com",
            role="charity",
        )
        other_charity.set_password("CharityPassword123!")

        registered_student = User(
            name="Registered Volunteer",
            email="registered-list@example.com",
            role="student",
        )
        registered_student.set_password("StudentPassword123!")

        cancelled_student = User(
            name="Cancelled Volunteer",
            email="cancelled-list@example.com",
            role="student",
        )
        cancelled_student.set_password("StudentPassword123!")

        viewing_student = User(
            name="Viewing Student",
            email="viewer-list@example.com",
            role="student",
        )
        viewing_student.set_password("StudentPassword123!")

        event = Event(
            title="Community Food Drive",
            description="Help prepare food parcels for local families.",
            date_time=datetime.now() + timedelta(days=7),
            location="Melbourne Community Centre",
            capacity=10,
            charity=owner,
        )

        db.session.add_all(
            [
                owner,
                other_charity,
                registered_student,
                cancelled_student,
                viewing_student,
                event,
            ]
        )

        if include_registrations:
            db.session.add_all(
                [
                    Registration(
                        student=registered_student,
                        event=event,
                        status="registered",
                    ),
                    Registration(
                        student=cancelled_student,
                        event=event,
                        status="cancelled",
                    ),
                ]
            )

        db.session.commit()
        return event.id


def login(client, email, password):
    response = client.post(
        "/login",
        data={
            "login-email": email,
            "login-password": password,
        },
    )
    assert response.status_code == 302


def test_event_owner_sees_only_registered_student_names(app, client):
    event_id = create_registration_list_scenario(app)
    login(client, "owner-list@example.com", "CharityPassword123!")

    response = client.get(f"/events/{event_id}")

    assert response.status_code == 200
    assert b"Registered Students" in response.data
    assert b"Registered Volunteer" in response.data
    assert b"Cancelled Volunteer" not in response.data
    assert b"registered-list@example.com" not in response.data
    assert b"cancelled-list@example.com" not in response.data


def test_event_owner_sees_empty_registration_state(app, client):
    event_id = create_registration_list_scenario(
        app,
        include_registrations=False,
    )
    login(client, "owner-list@example.com", "CharityPassword123!")

    response = client.get(f"/events/{event_id}")

    assert response.status_code == 200
    assert b"Registered Students" in response.data
    assert b"No students have registered for this event yet." in response.data


def test_owner_sees_registrations_for_selected_event_only(app, client):
    event_id = create_registration_list_scenario(app)

    with app.app_context():
        owner = db.session.scalar(
            db.select(User).where(User.email == "owner-list@example.com")
        )
        other_student = User(
            name="Different Event Volunteer",
            email="different-event@example.com",
            role="student",
        )
        other_student.set_password("StudentPassword123!")
        other_event = Event(
            title="Community Garden Day",
            description="Help prepare a different community event.",
            date_time=datetime.now() + timedelta(days=8),
            location="Carlton Community Garden",
            capacity=10,
            charity=owner,
        )
        other_registration = Registration(
            student=other_student,
            event=other_event,
            status="registered",
        )
        db.session.add_all(
            [other_student, other_event, other_registration]
        )
        db.session.commit()

    login(client, "owner-list@example.com", "CharityPassword123!")
    response = client.get(f"/events/{event_id}")

    assert response.status_code == 200
    assert b"Registered Volunteer" in response.data
    assert b"Different Event Volunteer" not in response.data
    assert b"different-event@example.com" not in response.data


def test_other_charity_cannot_view_registration_list(app, client):
    event_id = create_registration_list_scenario(app)
    login(client, "other-list@example.com", "CharityPassword123!")

    response = client.get(f"/events/{event_id}")

    assert response.status_code == 403
    assert b"Registered Volunteer" not in response.data
    assert b"registered-list@example.com" not in response.data


def test_student_cannot_view_full_registration_list(app, client):
    event_id = create_registration_list_scenario(app)
    login(client, "viewer-list@example.com", "StudentPassword123!")

    response = client.get(f"/events/{event_id}")

    assert response.status_code == 200
    assert b"Registered Students" not in response.data
    assert b"Registered Volunteer" not in response.data
    assert b"registered-list@example.com" not in response.data
