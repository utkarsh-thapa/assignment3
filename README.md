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
secure account authentication, role-based dashboard and Charity event creation
are complete. Charities can publish validated future events, while Students can
browse upcoming opportunities, open their details and register once when places
are available. Duplicate, full and past-event registrations are rejected by the
server. Charity registration viewing will be added in a later issue.

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
