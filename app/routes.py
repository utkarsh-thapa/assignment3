from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from app import db
from app.forms import LoginForm, LogoutForm, RegistrationForm
from app.models import User

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
        existing_user = db.session.scalar(db.select(User).where(User.email == email))

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
    return render_template("dashboard.html", logout_form=LogoutForm())
