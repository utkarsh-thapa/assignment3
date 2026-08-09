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


def test_student_sees_upcoming_events_in_date_order(app, client):
    with app.app_context():
        charity = User(
            name="Helping Hands",
            email="charity-dashboard@example.com",
            role="charity",
        )
        charity.set_password("CharityPassword123!")

        student = User(
            name="Dashboard Student",
            email="student-dashboard@example.com",
            role="student",
        )
        student.set_password("StudentPassword123!")

        past_event = Event(
            title="Past Event",
            description="This event has already finished.",
            date_time=datetime.now() - timedelta(days=1),
            location="Old Hall",
            capacity=10,
            charity=charity,
        )
        later_event = Event(
            title="Later Event",
            description="This event happens later.",
            date_time=datetime.now() + timedelta(days=7),
            location="Community Centre",
            capacity=20,
            charity=charity,
        )
        sooner_event = Event(
            title="Sooner Event",
            description="This event happens first.",
            date_time=datetime.now() + timedelta(days=2),
            location="Local Park",
            capacity=15,
            charity=charity,
        )

        db.session.add_all(
            [charity, student, past_event, later_event, sooner_event]
        )
        db.session.commit()

    login_response = client.post(
        "/login",
        data={
            "login-email": "student-dashboard@example.com",
            "login-password": "StudentPassword123!",
        },
    )
    assert login_response.status_code == 302

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert b"Sooner Event" in response.data
    assert b"Later Event" in response.data
    assert b"Past Event" not in response.data
    assert b"<strong>Available places:</strong> 15" in response.data
    assert b"View details" in response.data
    assert b"Manage event" not in response.data
    assert response.data.index(b"Sooner Event") < response.data.index(
        b"Later Event"
    )


def test_available_places_counts_only_registered_students(app):
    with app.app_context():
        charity = User(
            name="Capacity Charity",
            email="capacity-charity@example.com",
            role="charity",
        )
        charity.set_password("CharityPassword123!")

        registered_student = User(
            name="Registered Student",
            email="registered-student@example.com",
            role="student",
        )
        registered_student.set_password("StudentPassword123!")

        cancelled_student = User(
            name="Cancelled Student",
            email="cancelled-student@example.com",
            role="student",
        )
        cancelled_student.set_password("StudentPassword123!")

        event = Event(
            title="Capacity Event",
            description="An event used to test available places.",
            date_time=datetime.now() + timedelta(days=3),
            location="Community Hall",
            capacity=3,
            charity=charity,
        )
        registered = Registration(
            student=registered_student,
            event=event,
            status="registered",
        )
        cancelled = Registration(
            student=cancelled_student,
            event=event,
            status="cancelled",
        )

        db.session.add_all(
            [
                charity,
                registered_student,
                cancelled_student,
                event,
                registered,
                cancelled,
            ]
        )
        db.session.commit()

        assert event.available_places == 2


def test_charity_sees_only_its_own_events_in_date_order(app, client):
    with app.app_context():
        charity = User(
            name="Dashboard Charity",
            email="dashboard-charity@example.com",
            role="charity",
        )
        charity.set_password("CharityPassword123!")

        other_charity = User(
            name="Other Charity",
            email="other-charity@example.com",
            role="charity",
        )
        other_charity.set_password("OtherPassword123!")

        later_own_event = Event(
            title="Later Own Event",
            description="This belongs to the logged-in charity.",
            date_time=datetime.now() + timedelta(days=8),
            location="North Hall",
            capacity=20,
            charity=charity,
        )
        sooner_own_event = Event(
            title="Sooner Own Event",
            description="This also belongs to the logged-in charity.",
            date_time=datetime.now() + timedelta(days=2),
            location="South Hall",
            capacity=10,
            charity=charity,
        )
        other_event = Event(
            title="Other Charity Event",
            description="This must not appear on the dashboard.",
            date_time=datetime.now() + timedelta(days=1),
            location="Other Hall",
            capacity=15,
            charity=other_charity,
        )

        db.session.add_all(
            [
                charity,
                other_charity,
                later_own_event,
                sooner_own_event,
                other_event,
            ]
        )
        db.session.commit()

    login_response = client.post(
        "/login",
        data={
            "login-email": "dashboard-charity@example.com",
            "login-password": "CharityPassword123!",
        },
    )
    assert login_response.status_code == 302

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert b"Sooner Own Event" in response.data
    assert b"Later Own Event" in response.data
    assert b"Other Charity Event" not in response.data
    assert b"Manage event" in response.data
    assert b"View details" not in response.data
    assert response.data.index(b"Sooner Own Event") < response.data.index(
        b"Later Own Event"
    )


def test_charity_past_event_is_not_shown_as_available(app, client):
    with app.app_context():
        charity = User(
            name="Past Event Charity",
            email="past-event-charity@example.com",
            role="charity",
        )
        charity.set_password("CharityPassword123!")

        past_event = Event(
            title="Past Charity Event",
            description="This event has already happened.",
            date_time=datetime.now() - timedelta(days=2),
            location="Old Community Hall",
            capacity=12,
            charity=charity,
        )

        db.session.add_all([charity, past_event])
        db.session.commit()

    login_response = client.post(
        "/login",
        data={
            "login-email": "past-event-charity@example.com",
            "login-password": "CharityPassword123!",
        },
    )
    assert login_response.status_code == 302

    response = client.get("/dashboard")

    assert response.status_code == 200
    assert b"Past Charity Event" in response.data
    past_event_card = response.data.split(b"Past Charity Event", 1)[1].split(
        b"</article>", 1
    )[0]
    assert b"Past event" in past_event_card
    assert b"Available places" not in past_event_card


def test_event_details_enforces_role_and_ownership(app, client):
    with app.app_context():
        owner = User(
            name="Event Owner",
            email="event-owner@example.com",
            role="charity",
        )
        owner.set_password("OwnerPassword123!")

        other_charity = User(
            name="Other Event Charity",
            email="other-event-charity@example.com",
            role="charity",
        )
        other_charity.set_password("OtherPassword123!")

        student = User(
            name="Event Details Student",
            email="event-details-student@example.com",
            role="student",
        )
        student.set_password("StudentPassword123!")

        future_event = Event(
            title="Accessible Future Event",
            description="Students can view this event.",
            date_time=datetime.now() + timedelta(days=4),
            location="Future Hall",
            capacity=10,
            charity=owner,
        )
        past_event = Event(
            title="Hidden Past Event",
            description="Students must not view this event.",
            date_time=datetime.now() - timedelta(days=4),
            location="Past Hall",
            capacity=10,
            charity=owner,
        )

        db.session.add_all(
            [owner, other_charity, student, future_event, past_event]
        )
        db.session.commit()
        future_event_id = future_event.id
        past_event_id = past_event.id

    client.post(
        "/login",
        data={
            "login-email": "event-details-student@example.com",
            "login-password": "StudentPassword123!",
        },
    )

    future_response = client.get(f"/events/{future_event_id}")
    past_response = client.get(f"/events/{past_event_id}")

    assert future_response.status_code == 200
    assert b"Accessible Future Event" in future_response.data
    assert past_response.status_code == 404

    client.post("/logout")
    client.post(
        "/login",
        data={
            "login-email": "other-event-charity@example.com",
            "login-password": "OtherPassword123!",
        },
    )

    unauthorised_response = client.get(f"/events/{future_event_id}")

    assert unauthorised_response.status_code == 403
