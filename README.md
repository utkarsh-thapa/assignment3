# Community Volunteer Board

A Flask prototype that allows charities to publish volunteer opportunities and
students to browse events and register for shifts.

## Technology stack

- Python and Flask
- SQLite and Flask-SQLAlchemy
- Flask-Login and Flask-WTF
- HTML and CSS
- Pytest

## Current status

The Flask application foundation, User, Event and Registration database models,
and secure account authentication are complete. Students and Charities can
create accounts, log in, log out and access a protected dashboard. Event
creation, browsing and volunteer registration will be added in later issues.

## Run the application

From the repository folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
python3 run.py
```

Open <http://127.0.0.1:5055> in your browser.

Before running the application, replace the placeholder `SECRET_KEY` in your
local `.env` file with a securely generated random value. Never commit `.env`.

## Run the tests

```bash
python3 -m pytest
```

## AI-generated code review

All AI-assisted code must be manually reviewed by both team members before its
pull request is approved and merged. The team remains responsible for
architecture, security, testing and ethical compliance.
