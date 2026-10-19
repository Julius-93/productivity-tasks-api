# Productivity Tasks API

A Flask REST API for a personal task tracker with **session-based authentication**, bcrypt-hashed passwords, unique user names, user-owned tasks, full CRUD, pagination, SQLite, migrations, sample data, and pytest coverage. Designed for Moringa School's **Summative Lab: Full Auth Flask Backend – Productivity App**.

## API design

- Authentication: Flask signed sessions; sessions carry only a user ID in an HTTP-only cookie.
- Persistence: SQLite via Flask-SQLAlchemy and tracked migrations using Flask-Migrate.
- Data models: `User(id, username, password_hash)` has many `Task` records. `Task(id, title, description, is_completed, created_at, user_id)` belongs to a `User`.
- Authorization: every `/tasks` handler requires authentication; an ID lookup always filters by current user.
- Passwords: bcrypt hashes, never stored as plaintext and never serialized in responses.

## Requirements

- Python 3.11 (3.8.13+ is specified by the assignment; this project is tested conceptually against the supplied Python 3.11-compatible pins)
- Pipenv, Git, a terminal; optional Node.js/npm for the supplied frontend

## Install and run from WSL Ubuntu

```bash
cd ~/Julius_Dev/productivity-tasks-api
pyenv local 3.11.9    # omit if Python 3.11 is already selected
pipenv install --dev
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
# Set up the schema on first use:
pipenv run flask --app 'app:create_app' db init
pipenv run flask --app 'app:create_app' db migrate -m 'Create users and tasks'
pipenv run flask --app 'app:create_app' db upgrade
# Add development-only sample users and tasks:
pipenv run python seed.py
# Start server on the proxy port used by the supplied session client:
pipenv run flask --app 'app:create_app' --debug run --port 5555
```

The `db init` and `db migrate` commands are **one-time steps** for initial development. On another machine, once the versioned `migrations/` folder has been committed, run only `pipenv run flask --app 'app:create_app' db upgrade`. If `flask db init` says the migrations directory exists, do not initialize again.

Do not use Flask's development server or this sample credential setup for production. Provide a strong `SECRET_KEY` in the deployment environment, use HTTPS with `SESSION_COOKIE_SECURE=1`, enable CSRF protection for cookie-authenticated state changes, configure appropriate logging and rate limiting, and keep the database private. The built-in session cookie is signed but is not a server-side session store.

## Routes

| Method | Path | Auth? | Successful response | Description |
| --- | --- | --- | --- | --- |
| GET | `/` | No | `200` | Health response |
| POST | `/signup` | No | `201` | Register user, hash password, sign in |
| POST | `/login` | No | `200` | Sign in with username/password |
| GET | `/check_session` | Session | `200` / `401` | Current user, or `{}` if anonymous |
| DELETE | `/logout` | No | `200` | Clear session and return `{}` |
| GET | `/tasks?page=1&per_page=10` | Yes | `200` | Paginated tasks **owned by logged-in user** |
| POST | `/tasks` | Yes | `201` | Create task for logged-in user |
| GET | `/tasks/<id>` | Yes | `200` / `404` | Get owned task only |
| PATCH | `/tasks/<id>` | Yes | `200` / `404` | Edit owned task only |
| DELETE | `/tasks/<id>` | Yes | `204` / `404` | Delete owned task only |

### Auth body samples

Sign up: `{"username":"new_user","password":"SecurePass123!","password_confirmation":"SecurePass123!"}`.

Log in: `{"username":"new_user","password":"SecurePass123!"}`.

Successful auth responses contain only `{ "id": 1, "username": "new_user" }`. Authentication errors return `400` for bad inputs, `401` for bad credentials / missing session, and `409` for duplicate usernames.

### Tasks body samples

Create: `{"title":"Complete Flask lab","description":"Test endpoints","is_completed":false}`.

Patch: `{"is_completed":true}`.

The server obtains `user_id` from the logged-in session. Client-provided `user_id` is **not** accepted. Error JSON looks like `{ "error": "..." }`. A task belonging to another user produces `404`, avoiding disclosure of its existence.

Paginated response example:

```json
{
  "items": [],
  "page": 1,
  "per_page": 10,
  "total": 0,
  "pages": 0,
  "has_next": false,
  "has_prev": false
}
```

`page` and `per_page` are positive integers; `per_page` has a maximum of 100.

## Demo data

After `pipenv run python seed.py`, these **development-only** users exist:

| Username | Password |
| --- | --- |
| `demo_julius` | `DemoPass123!` |
| `demo_alex` | `DemoPass456!` |

Each is seeded with five tasks if they have no tasks yet. Running the seed again does not duplicate existing accounts or their tasks. Never run this seeded demo account configuration in production.

## Try the API using curl

Keep the Flask server running in one terminal and run in a second terminal:

```bash
# Cookie jar persists your logged-in Flask session across commands.
curl -i -c cookies.txt -H 'Content-Type: application/json' \
  -d '{"username":"myuser","password":"SecurePass123!","password_confirmation":"SecurePass123!"}' \
  http://127.0.0.1:5555/signup

curl -i -b cookies.txt http://127.0.0.1:5555/check_session

curl -i -b cookies.txt -H 'Content-Type: application/json' \
  -d '{"title":"Finish summative lab","description":"Secure task API"}' \
  http://127.0.0.1:5555/tasks

curl -i -b cookies.txt 'http://127.0.0.1:5555/tasks?page=1&per_page=5'

curl -i -b cookies.txt -X DELETE http://127.0.0.1:5555/logout
curl -i -b cookies.txt http://127.0.0.1:5555/tasks # 401
```

**Tip:** `cookies.txt` is a development credential and should not be committed; delete it after local testing. It is listed in `.gitignore`.

## Automated testing

```bash
pipenv run pytest -v
```

The tests verify all CRUD endpoints, session lifecycle, bcrypt password protection, duplicate usernames, input validation, pagination, `401` authentication rejection, and cross-user IDOR access attempts.

## Frontend integration (optional, no frontend changes)

The supplied session frontend is from [the Moringa client repository](https://github.com/learn-co-curriculum/flask-c10-summative-lab-sessions-and-jwt-clients).

```bash
cd ~/Julius_Dev
git clone https://github.com/learn-co-curriculum/flask-c10-summative-lab-sessions-and-jwt-clients.git frontend-clients
cd frontend-clients/client-with-sessions
npm install
npm start
```

The React app uses port **4000** and proxies to the Flask server on **5555**. It expects `/signup`, `/login`, `/check_session`, and `/logout` responses as described above. It currently includes only auth screens; the task endpoints are exercised with tests/curl/Postman.

## Recommended Git workflow

Create a new public GitHub repository named `productivity-tasks-api`, commit the initialized files on `main`, then open and merge feature branch pull requests. For example, separate `feature/auth`, `feature/task-crud`, and `feature/tests-docs` PRs with descriptive commit messages. Commit `migrations/`, `Pipfile`, tests, and this README. **Do not** commit secrets, the SQLite database, local session cookie jar, or virtual environments.
