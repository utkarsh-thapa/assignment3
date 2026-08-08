from flask_wtf import FlaskForm
from wtforms import EmailField, PasswordField, RadioField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length


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
