from app import db


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (
        db.CheckConstraint(
            "role IN ('student', 'charity')",
            name="ck_users_role",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(
        db.String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False)

    events = db.relationship("Event", back_populates="charity")
    registrations = db.relationship(
        "Registration",
        back_populates="student",
    )


class Event(db.Model):
    """Charity ownership is enforced by server-side event routes."""

    __tablename__ = "events"
    __table_args__ = (
        db.CheckConstraint(
            "capacity > 0",
            name="ck_events_capacity_positive",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    date_time = db.Column(db.DateTime, nullable=False, index=True)
    location = db.Column(db.String(255), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    charity_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    charity = db.relationship("User", back_populates="events")
    registrations = db.relationship(
        "Registration",
        back_populates="event",
    )


class Registration(db.Model):
    """Student eligibility is enforced by server-side registration routes."""

    __tablename__ = "registrations"
    __table_args__ = (
        db.UniqueConstraint(
            "student_id",
            "event_id",
            name="uq_registrations_student_event",
        ),
        db.CheckConstraint(
            "status IN ('registered', 'cancelled')",
            name="ck_registrations_status",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id"),
        nullable=False,
        index=True,
    )
    registration_date = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.now(),
    )
    status = db.Column(
        db.String(20),
        nullable=False,
        default="registered",
    )

    student = db.relationship("User", back_populates="registrations")
    event = db.relationship("Event", back_populates="registrations")
