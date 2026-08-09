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
server. To prevent simultaneous requests from overbooking the final place,
SQLite obtains a write reservation before capacity is read and holds it through
the registration insert. Other supported databases use a row-level event lock.
An event-owning Charity can view the names of its actively registered Students
on the Event Details screen. This list is protected by a server-side ownership
check, is hidden from Students and other Charities, and queries no Student email
or other unnecessary personal information.

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
local `.env` file with a securely generated random value of at least 32
characters. One way to generate a suitable value is:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Never commit `.env`. The application refuses to start outside testing when the
key is missing, whitespace-only, shorter than 32 characters after surrounding
whitespace is removed, or still set to the public placeholder. These checks do
not prove that a key is unpredictable. Generating and supplying a
cryptographically secure random value remains the operator's responsibility.

## Run the tests

```bash
python3 -m pytest
```

## AI-generated code review

All AI-assisted code must be manually reviewed by both team members before its
pull request is approved and merged. The team remains responsible for
architecture, security, testing and ethical compliance.

## Security audit

The team audited the completed prototype on 9 August 2026 against Issue #10 and
the relevant [OWASP SQL Injection Prevention](https://cheatsheetseries.owasp.org/cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.html),
[OWASP CSRF Prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html)
and [OWASP Password Storage](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html)
guidance.

### Audit results

| Security check | Expected result | Actual evidence and result |
| --- | --- | --- |
| Password storage | No readable passwords in the database | `User.set_password` uses Werkzeug's salted password hashing and login uses `check_password_hash`. Authentication tests confirm the stored hash differs from the password. Passed. |
| Authentication | Private screens and actions require a valid session | Flask-Login protects the Dashboard, Event Details, event creation, event registration and logout routes. Unauthenticated GET and POST tests are redirected to the account screen. Passed. |
| Role and ownership authorization | Students and Charities can perform only their permitted actions | Server-side checks block Students from creating events, block Charities from registering, return HTTP 403 to non-owning Charities and expose registration names only to the event owner. Passed. |
| Input validation and CSRF | Invalid input and forged state-changing requests are rejected | WTForms validates length, email, role, date and capacity. Flask-WTF protects every POST form. Missing-token tests cover login, account creation, logout, event creation and event registration. Passed. |
| SQL injection | SQL-like input is treated only as data | All application-data queries use SQLAlchemy expressions and bound values. The only static SQL statement is the parameter-free SQLite transaction command `BEGIN IMMEDIATE`; no user value is joined to it. Runtime injection evidence is recorded below. Passed. |
| Secrets and sessions | The application rejects clearly unsafe key formats and the operator supplies a random key | `SECRET_KEY` is loaded from `.env`; production strips surrounding whitespace and rejects missing, whitespace-only, short and known-placeholder values. Secure randomness remains the operator's responsibility. Session cookies are `HttpOnly` and `SameSite=Lax`, and Flask-Login uses strong session protection. Passed. |
| Repository hygiene | Secrets and local databases are not published | `.env`, `instance/`, `*.db`, `*.sqlite` and `*.sqlite3` are ignored. Current files and complete Git object names were checked; none of these private files are tracked. Passed. |
| Error and output safety | Responses reveal no stack trace, query internals, password or executable user HTML | Login and validation failures use generic messages. Regression tests confirm no traceback, SQLAlchemy details or password disclosure, and Jinja escapes submitted HTML. Passed. |
| Capacity integrity | Concurrent requests cannot overbook an event | Registration capacity is read and written inside one protected transaction; a two-client concurrency test confirms only one Student receives the final place. Passed. |

### Required SQL injection test

- **Target:** the login database lookup.
- **Input:** email `or'1'='1@example.com` and password `' OR '1'='1`.
- **Expected:** authentication is rejected, the private Dashboard remains
  inaccessible, and no database row is exposed, added, changed or removed.
- **Actual:** login returned HTTP 400 with the generic `Invalid email or
  password` message; the Dashboard still redirected to login; the original
  User was unchanged and remained the database's only User.
- **Static review:** no route builds SQL by concatenating or formatting user
  input. SQLAlchemy generates bound parameters for email, ID, role, status and
  ownership filters.
- **Result:** no SQL injection vulnerability was reproduced.

### Finding, change and retest

The audit found one configuration weakness: a non-test application previously
accepted the public example `SECRET_KEY`, another very short key or a key made
only of whitespace. Those values could weaken the integrity of session and CSRF
signatures. Startup validation now removes surrounding whitespace before
checking length and rejects missing, whitespace-only, short and known-placeholder
values. The application enforces these format checks; the operator remains
responsible for generating the value with a cryptographically secure source.
Regression tests cover each rejected case and accepted-key normalization.

After the change, the focused security tests passed and the complete suite
reported **73 passed**. Dependency consistency, Python compilation and diff
format checks are also part of the pull-request verification.

This is a local prototype. Any future public deployment must additionally use
HTTPS, enable `SESSION_COOKIE_SECURE`, add login rate limiting and repeat the
audit against its production database and hosting configuration.
