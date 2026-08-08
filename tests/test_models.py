from datetime import datetime, timedelta

import pytest
from sqlalchemy.exc import IntegrityError

from app import create_app, db
from app.models import Event, Registration, User


@pytest.fixture
def app():
    test_app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )

    with test_app.app_context():
        db.create_all()
        yield test_app
        db.session.remove()
        db.drop_all()


def test_model_relationships(app):
    charity = User(
        name="Helping Hands",
        email="charity@example.com",
        password_hash="hashed-password",
        role="charity",
    )
    student = User(
        name="Alice Student",
        email="student@example.com",
        password_hash="hashed-password",
        role="student",
    )
    event = Event(
        title="Community Clean-up",
        description="Clean the local park.",
        date_time=datetime.now() + timedelta(days=7),
        location="Central Park",
        capacity=20,
        charity=charity,
    )
    registration = Registration(
        student=student,
        event=event,
    )

    db.session.add_all([charity, student, event, registration])
    db.session.commit()

    assert event.charity is charity
    assert event in charity.events
    assert registration.student is student
    assert registration.event is event
    assert registration in student.registrations
    assert registration in event.registrations


def test_duplicate_email_is_rejected(app):
    first_user = User(
        name="First User",
        email="duplicate@example.com",
        password_hash="hashed-password",
        role="student",
    )
    second_user = User(
        name="Second User",
        email="duplicate@example.com",
        password_hash="hashed-password",
        role="charity",
    )

    db.session.add_all([first_user, second_user])

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_duplicate_registration_is_rejected(app):
    charity = User(
        name="Helping Hands",
        email="charity2@example.com",
        password_hash="hashed-password",
        role="charity",
    )
    student = User(
        name="Bob Student",
        email="student2@example.com",
        password_hash="hashed-password",
        role="student",
    )
    event = Event(
        title="Food Drive",
        description="Collect food donations.",
        date_time=datetime.now() + timedelta(days=7),
        location="Community Hall",
        capacity=10,
        charity=charity,
    )

    db.session.add_all([charity, student, event])
    db.session.commit()

    first_registration = Registration(student=student, event=event)
    db.session.add(first_registration)
    db.session.commit()

    duplicate_registration = Registration(student=student, event=event)
    db.session.add(duplicate_registration)

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_expected_tables_are_created(app):
    expected_tables = {"users", "events", "registrations"}

    assert expected_tables.issubset(db.metadata.tables.keys())


def test_invalid_user_role_is_rejected(app):
    user = User(
        name="Invalid User",
        email="invalid-role@example.com",
        password_hash="hashed-password",
        role="admin",
    )

    db.session.add(user)

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


@pytest.mark.parametrize("capacity", [0, -1])
def test_non_positive_event_capacity_is_rejected(app, capacity):
    charity = User(
        name="Capacity Test Charity",
        email=f"capacity-{capacity}@example.com",
        password_hash="hashed-password",
        role="charity",
    )
    event = Event(
        title="Invalid Capacity Event",
        description="Testing an invalid event capacity.",
        date_time=datetime.now() + timedelta(days=7),
        location="Community Hall",
        capacity=capacity,
        charity=charity,
    )

    db.session.add_all([charity, event])

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()


def test_invalid_registration_status_is_rejected(app):
    charity = User(
        name="Status Test Charity",
        email="status-charity@example.com",
        password_hash="hashed-password",
        role="charity",
    )
    student = User(
        name="Status Test Student",
        email="status-student@example.com",
        password_hash="hashed-password",
        role="student",
    )
    event = Event(
        title="Status Test Event",
        description="Testing an invalid registration status.",
        date_time=datetime.now() + timedelta(days=7),
        location="Community Hall",
        capacity=10,
        charity=charity,
    )

    db.session.add_all([charity, student, event])
    db.session.commit()

    registration = Registration(
        student=student,
        event=event,
        status="pending",
    )
    db.session.add(registration)

    with pytest.raises(IntegrityError):
        db.session.commit()

    db.session.rollback()
