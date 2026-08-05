# Community Volunteer Board

A Flask prototype that allows charities to publish volunteer opportunities and
students to browse events and register for shifts.

## Technology stack

- Python and Flask
- SQLite and Flask-SQLAlchemy
- HTML and CSS
- Pytest

## Current status

The initial Flask application structure is complete. The homepage route and a
basic automated test are included. Database models, authentication and event
features will be added in separate issues.

## Run the application

From the repository folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
python3 run.py
```

Open <http://127.0.0.1:5000> in your browser.

Before adding authentication, replace the placeholder `SECRET_KEY` in your
local `.env` file with a securely generated random value. Never commit `.env`.

## Run the tests

```bash
python3 -m pytest
```

## AI-generated code review

All AI-assisted code must be manually reviewed by both team members before it
is committed or pushed. The team remains responsible for architecture,
security, testing and ethical compliance.
