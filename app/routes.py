from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from app import db
from app.forms import (
    EventForm,
    EventRegistrationForm,
    LoginForm,
    LogoutForm,
    RegistrationForm,
)
from app.models import Event, Registration, User

main = Blueprint("main", __name__)


def _account_forms():
    return RegistrationForm(prefix="register"), LoginForm(prefix="login")


@main.get("/")
@main.get("/account")
def account():
    registration_form, login_form = _account_forms()
    return render_template(
        "account.html",
        registration_form=registration_form,
        login_form=login_form,
        logout_form=LogoutForm(),
    )


@main.post("/register")
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    registration_form = RegistrationForm(prefix="register")
    login_form = LoginForm(prefix="login")

    if registration_form.validate_on_submit():
        email = registration_form.email.data.strip().lower()
        existing_user = db.session.scalar(
            db.select(User).where(User.email == email)
        )

        if existing_user is not None:
            registration_form.email.errors.append(
                "An account with this email already exists."
            )
        else:
            user = User(
                name=registration_form.name.data.strip(),
                email=email,
                role=registration_form.role.data,
            )
            user.set_password(registration_form.password.data)
            db.session.add(user)

            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                registration_form.email.errors.append(
                    "Unable to create this account. Please check your details."
                )
            else:
                login_user(user)
                flash("Your account was created successfully.", "success")
                return redirect(url_for("main.dashboard"))

    return (
        render_template(
            "account.html",
            registration_form=registration_form,
            login_form=login_form,
            logout_form=LogoutForm(),
        ),
        400,
    )


@main.post("/login")
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    registration_form = RegistrationForm(prefix="register")
    login_form = LoginForm(prefix="login")

    if login_form.validate_on_submit():
        email = login_form.email.data.strip().lower()
        user = db.session.scalar(db.select(User).where(User.email == email))

        if user is not None and user.check_password(login_form.password.data):
            login_user(user)
            flash("You are now logged in.", "success")
            return redirect(url_for("main.dashboard"))

        login_form.password.errors.append("Invalid email or password.")

    return (
        render_template(
            "account.html",
            registration_form=registration_form,
            login_form=login_form,
            logout_form=LogoutForm(),
        ),
        400,
    )


@main.post("/logout")
@login_required
def logout():
    form = LogoutForm()
    if not form.validate_on_submit():
        return "Invalid or expired form submission. Please try again.", 400

    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("main.account"))


@main.get("/dashboard")
@login_required
def dashboard():
    events = []
    event_form = None

    if current_user.role == "student":
        events = db.session.scalars(
            db.select(Event)
            .where(Event.date_time >= datetime.now())
            .order_by(Event.date_time.asc())
        ).all()
    elif current_user.role == "charity":
        events = db.session.scalars(
            db.select(Event)
            .where(Event.charity_id == current_user.id)
            .order_by(Event.date_time.asc())
        ).all()
        event_form = EventForm(prefix="event")

    return render_template(
        "dashboard.html",
        events=events,
        event_form=event_form,
        logout_form=LogoutForm(),
    )


@main.post("/events")
@login_required
def create_event():
    if current_user.role != "charity":
        abort(403)

    event_form = EventForm(prefix="event")

    if event_form.validate_on_submit():
        event = Event(
            title=event_form.title.data,
            description=event_form.description.data,
            date_time=event_form.date_time.data,
            location=event_form.location.data,
            capacity=event_form.capacity.data,
            charity_id=current_user.id,
        )
        db.session.add(event)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash(
                "Unable to create the event. Please check the details.",
                "error",
            )
        else:
            flash("Event created successfully.", "success")
            return redirect(url_for("main.dashboard"))

    events = db.session.scalars(
        db.select(Event)
        .where(Event.charity_id == current_user.id)
        .order_by(Event.date_time.asc())
    ).all()

    return (
        render_template(
            "dashboard.html",
            events=events,
            event_form=event_form,
            logout_form=LogoutForm(),
        ),
        400,
    )


@main.get("/events/<int:event_id>")
@login_required
def event_details(event_id):
    event = db.get_or_404(Event, event_id)

    if current_user.role == "student" and event.is_past:
        abort(404)

    if current_user.role == "charity" and event.charity_id != current_user.id:
        abort(403)

    registration = None
    registration_form = None

    if current_user.role == "student":
        registration = db.session.scalar(
            db.select(Registration).where(
                Registration.student_id == current_user.id,
                Registration.event_id == event.id,
            )
        )
        registration_form = EventRegistrationForm(
            prefix="event-registration"
        )

    return render_template(
        "event_details.html",
        event=event,
        registration=registration,
        registration_form=registration_form,
        logout_form=LogoutForm(),
    )


@main.post("/events/<int:event_id>/register")
@login_required
def register_for_event(event_id):
    if current_user.role != "student":
        abort(403)

    event = db.get_or_404(Event, event_id)

    if event.is_past:
        abort(404)

    registration_form = EventRegistrationForm(
        prefix="event-registration"
    )
    if not registration_form.validate_on_submit():
        return "Invalid or expired form submission. Please try again.", 400

    existing_registration = db.session.scalar(
        db.select(Registration).where(
            Registration.student_id == current_user.id,
            Registration.event_id == event.id,
        )
    )
    if existing_registration is not None:
        flash("You are already registered for this event.", "error")
        return redirect(url_for("main.event_details", event_id=event.id))

    if event.available_places <= 0:
        flash("This event is full.", "error")
        return redirect(url_for("main.event_details", event_id=event.id))

    registration = Registration(
        student_id=current_user.id,
        event_id=event.id,
        status="registered",
    )
    db.session.add(registration)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(
            "Unable to register. You may already be registered or the "
            "event may no longer be available.",
            "error",
        )
    else:
        flash("You are registered for this event.", "success")

    return redirect(url_for("main.event_details", event_id=event.id))
