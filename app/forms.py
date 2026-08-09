from datetime import datetime

from flask_wtf import FlaskForm
from wtforms import (
    DateTimeLocalField,
    EmailField,
    IntegerField,
    PasswordField,
    RadioField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    InputRequired,
    Length,
    NumberRange,
    ValidationError,
)


def _strip_whitespace(value):
    return value.strip() if isinstance(value, str) else value


class RegistrationForm(FlaskForm):
    name = StringField(
        "Name or organisation name",
        validators=[DataRequired(), Length(min=2, max=100)],
    )
    email = EmailField(
        "Email",
        validators=[DataRequired(), Email(), Length(max=255)],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(min=8, max=128)],
    )
    role = RadioField(
        "Account type",
        choices=[("student", "Student"), ("charity", "Charity")],
        validators=[DataRequired()],
    )
    submit = SubmitField("Create account")


class LoginForm(FlaskForm):
    email = EmailField(
        "Email",
        validators=[DataRequired(), Email(), Length(max=255)],
    )
    password = PasswordField(
        "Password",
        validators=[DataRequired(), Length(max=128)],
    )
    submit = SubmitField("Log in")


class LogoutForm(FlaskForm):
    submit = SubmitField("Log out")


class EventForm(FlaskForm):
    title = StringField(
        "Title",
        filters=[_strip_whitespace],
        validators=[DataRequired(), Length(min=2, max=150)],
    )
    description = TextAreaField(
        "Description",
        filters=[_strip_whitespace],
        validators=[DataRequired(), Length(min=10, max=2000)],
    )
    date_time = DateTimeLocalField(
        "Date and time",
        format="%Y-%m-%dT%H:%M",
        validators=[DataRequired()],
    )
    location = StringField(
        "Location",
        filters=[_strip_whitespace],
        validators=[DataRequired(), Length(max=255)],
    )
    capacity = IntegerField(
        "Capacity",
        validators=[InputRequired(), NumberRange(min=1, max=10000)],
    )
    submit = SubmitField("Create event")

    def validate_date_time(self, field):
        if field.data is not None and field.data <= datetime.now():
            raise ValidationError(
                "The event date and time must be in the future."
            )
