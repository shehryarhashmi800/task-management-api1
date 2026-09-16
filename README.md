# Task Management API

[![CI](https://github.com/shehryarhashmi800/task-management-api1/actions/workflows/ci.yml/badge.svg)]
(https://github.com/shehryarhashmi800/task-management-api1/actions/workflows/ci.yml)

A production-grade Task Management API built with FastAPI, PostgreSQL, SQLAlchemy, and Alembic.
This is the backend for the Week 5 Flutter capstone client.

**Author:** Muhammad Shehryar Hashmi . Full-Stack Engineering: FastAPI Backend and Flutter Client
**Week:** 4 of 8 , Docker and Deployment

**Live API:** `https://task-management-api1-production.up.railway.app`
**Live docs:** `https://task-management-api1-production.up.railway.app/docs`

---

## Features

- Full task CRUD with Pydantic validation and correct HTTP status codes
- PostgreSQL persistence via SQLAlchemy 2.0, with Alembic migrations
- JWT authentication: register, login, refresh, current-user (`/me`)
- Passwords hashed with bcrypt, never stored or returned in plain text
- Tasks are strictly scoped to their owner — one user cannot see or modify another's tasks
- Layered architecture: routers → services → repositories → models, with Pydantic schemas at the boundary
- Custom exception hierarchy with a consistent JSON error shape across the whole API
- CORS middleware, request-logging middleware, and a `/health` endpoint that checks DB connectivity
- Pagination + filtering (by status, priority, and title search) on the task list endpoint
- Role-based access control: an `is_admin` flag gates an admin-only `/api/v1/users` listing
- 35 automated tests covering success paths, auth failures, cross-user authorization failures,
  validation errors, and edge cases

---

## Project layout

```
app/
  main.py              # FastAPI app, middleware, router registration
  config.py            # pydantic-settings, reads from .env
  database.py           # SQLAlchemy engine/session/Base
  exceptions.py          # Custom exceptions + exception handlers
  middleware.py           # Request logging middleware
  core/
    security.py          # Password hashing, JWT create/decode
    deps.py               # get_current_user / get_current_admin_user
  models/                 # SQLAlchemy ORM models (User, Task)
  schemas/                # Pydantic request/response schemas
  repositories/            # Data access layer (repository pattern)
  services/                # Business logic layer
  routers/                 # HTTP layer (auth, tasks, users, health)
alembic/
  env.py, versions/         # Database migrations
tests/
  conftest.py                # Fixtures (test DB, test client, auth headers)
  test_auth.py, test_tasks.py, test_health.py
requirements.txt
.env.example
.env.docker.example
alembic.ini
pytest.ini
Dockerfile
.dockerignore
docker-compose.yml
Makefile
.github/workflows/ci.yml
```

---

## Run it with Docker (recommended, easiest)

This spins up the API, PostgreSQL, and pgAdmin together with one command. You do not need
Python or PostgreSQL installed on your machine for this — only Docker.

### 1. Prerequisites

- Docker and Docker Compose installed ([get Docker](https://docs.docker.com/get-docker/))

### 2. Configure environment

```bash
cp .env.docker.example .env
# open .env and change SECRET_KEY to something random, e.g.
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 3. Start everything

```bash
make up
```

This builds the API image, starts Postgres (with a health check so the API waits for the
database to actually be ready), runs Alembic migrations automatically, and starts the API.
It also starts pgAdmin so you can browse the database visually.

- API: http://localhost:8000
- Swagger docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health
- pgAdmin: http://localhost:5050 (login with the email/password from your `.env`)

### 4. Other useful commands

```bash
make logs      # tail logs from all containers
make migrate   # run alembic migrations manually inside the running api container
make test      # run the test suite inside the running api container
make down      # stop and remove containers (data survives, see below)
```

### 5. Data persistence

Postgres data is stored in a named Docker volume (`db_data`), not inside the container itself.
That means running `make down` followed by `make up` again brings the containers back with all
your data intact. Data is only lost if you explicitly remove the volume:

```bash
docker compose down -v   # this DOES wipe the database volume, use with care
```

### How the services talk to each other

Inside `docker-compose.yml`, the API connects to Postgres using the **service name** `db` as the
hostname (`db:5432`), not `localhost`. Docker Compose gives every service its own DNS name on an
internal network, so `db` resolves to the Postgres container automatically — this is why the
`DATABASE_URL` inside the compose file points at `@db:5432/...` instead of `@localhost:5432/...`.

---

## Setup (without Docker, running Python directly)

### 1. Prerequisites

- Python 3.11+
- PostgreSQL 14+ running locally (or reachable over the network)

### 2. Create the databases

```bash
psql -U postgres -c "CREATE USER taskuser WITH PASSWORD 'taskpass';"
psql -U postgres -c "CREATE DATABASE taskdb OWNER taskuser;"
psql -U postgres -c "CREATE DATABASE taskdb_test OWNER taskuser;"
```

(Match these to whatever you put in `.env` — the names above match `.env.example`.)

### 3. Install dependencies

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env: set DATABASE_URL, TEST_DATABASE_URL, and a real SECRET_KEY
```

Generate a strong `SECRET_KEY` with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 5. Run migrations

```bash
alembic upgrade head
```

### 6. Run the server

```bash
uvicorn app.main:app --reload
```

- API root: http://localhost:8000/
- Interactive docs (Swagger): http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Health check: http://localhost:8000/health

### 7. Run the tests

Tests run against `TEST_DATABASE_URL` (a separate database from your dev data — tables are
dropped and recreated per test):

```bash
pytest
```

---

## Authentication flow

1. `POST /api/v1/auth/register` — create an account (email, username, password)
2. `POST /api/v1/auth/login` — exchange email + password for an `access_token` + `refresh_token`
3. Include `Authorization: Bearer <access_token>` on every protected request
4. When the access token expires (default 30 min), call `POST /api/v1/auth/refresh` with the
   `refresh_token` (default 7-day lifetime) to get a new access token — no need to log in again
5. `GET /api/v1/auth/me` returns the currently authenticated user

Access tokens and refresh tokens are distinct JWT types (checked via a `type` claim), so a
refresh token can't be used to authenticate a normal request and vice versa.

---

## Endpoints

### Health

| Method | Path      | Auth | Description                          |
|--------|-----------|------|---------------------------------------|
| GET    | `/`       | No   | Root — service status + docs link     |
| GET    | `/health` | No   | Health check, includes DB connectivity |

### Auth (`/api/v1/auth`)

| Method | Path       | Auth | Description                                  |
|--------|------------|------|------------------------------------------------|
| POST   | `/register`| No   | Create a new user account                      |
| POST   | `/login`   | No   | Log in, returns access + refresh tokens        |
| POST   | `/refresh` | No   | Exchange a refresh token for a new access token |
| GET    | `/me`      | Yes  | Get the current authenticated user             |

### Tasks (`/api/v1/tasks`) — all require auth, all scoped to the caller

| Method | Path         | Description                                                        |
|--------|--------------|----------------------------------------------------------------------|
| POST   | ``           | Create a task                                                        |
| GET    | ``           | List the caller's tasks. Query params: `page`, `page_size`, `status`, `priority`, `search` |
| GET    | `/{task_id}` | Get one task (404 if it doesn't exist or belongs to someone else)    |
| PUT    | `/{task_id}` | Full update                                                           |
| PATCH  | `/{task_id}` | Partial update                                                        |
| DELETE | `/{task_id}` | Delete a task (204 No Content)                                        |

### Users (`/api/v1/users`) — admin only (RBAC stretch goal)

| Method | Path | Auth        | Description                    |
|--------|------|-------------|----------------------------------|
| GET    | ``   | Admin only  | List all users in the system     |

---

## Error shape

Every error response — validation failures, auth errors, not-found, conflicts, and unhandled
server errors — comes back in the same JSON shape:

```json
{
  "error": "not_found",
  "message": "Task not found",
  "details": null
}
```

Validation errors additionally populate `details` with one entry per invalid field:

```json
{
  "error": "validation_error",
  "message": "One or more fields failed validation",
  "details": [
    {"field": "password", "message": "password must be at least 8 characters long"}
  ]
}
```

---

## Task fields

| Field         | Type                                  | Notes                          |
|---------------|----------------------------------------|----------------------------------|
| `title`       | string, 1–200 chars                    | required                        |
| `description` | string or null                          | optional                        |
| `status`      | `todo` \| `in_progress` \| `done`      | defaults to `todo`               |
| `priority`    | `low` \| `medium` \| `high`             | defaults to `medium`             |
| `due_date`    | ISO 8601 datetime or null               | optional                        |

---

## Design notes

- **Repository pattern**: routers never touch SQLAlchemy directly. Routers call services, services
  call repositories, repositories talk to the database. This keeps business rules (like "you can
  only see your own tasks") in one place (`TaskService`/`TaskRepository`) rather than scattered
  across endpoints.
- **Ownership scoping**: `TaskRepository.get_for_owner` filters by `owner_id` at the query level,
  so a request for another user's task simply returns nothing — the service layer turns that into
  a 404, which also avoids leaking whether a given task ID exists at all.
- **Migrations are hand-authored** for the initial schema (rather than autogenerated) so that the
  Postgres `ENUM` types for `status`/`priority` are created explicitly and safely reversible.

## Continuous Integration

Every push and pull request to `main` runs a GitHub Actions pipeline (`.github/workflows/ci.yml`)
with three jobs, each depending on the last:

1. **lint** — runs `ruff check` over `app/` and `tests/`
2. **test** — spins up a real PostgreSQL 16 service container, runs the full pytest suite against
   it (not sqlite, not mocks — the same database engine used in production)
3. **build** — builds the Docker image with the same `Dockerfile` used for deployment, to catch
   any Dockerfile breakage early

If any job fails, the ones after it don't run, and the badge at the top of this README turns red.

---

## Deployment

The API is deployed to [Railway](https://railway.app) (swap in Render if you used that instead)
with a managed PostgreSQL database.

**Live URL:** `PUT_YOUR_RAILWAY_OR_RENDER_URL_HERE`

### How it was deployed

1. Created a new Railway project and added a **PostgreSQL** plugin — Railway gives it a
   `DATABASE_URL` automatically.
2. Added a second service in the same project from this GitHub repo. Railway detects the
   `Dockerfile` and builds from it.
3. Set the API service's environment variables (`SECRET_KEY`, `ALGORITHM`,
   `ACCESS_TOKEN_EXPIRE_MINUTES`, `REFRESH_TOKEN_EXPIRE_DAYS`, `CORS_ORIGINS`, `ENVIRONMENT`), and
   pointed `DATABASE_URL` at the Postgres plugin's connection string (Railway lets you reference
   another service's variable directly, e.g. `${{Postgres.DATABASE_URL}}`, so it's always in sync).
4. Ran the migration against the remote database once, from a local machine with the remote
   `DATABASE_URL` exported:
   ```bash
   export DATABASE_URL="<the remote Railway Postgres URL>"
   alembic upgrade head
   ```
5. Railway auto-deploys on every push to `main` (this satisfies the auto-deploy stretch goal) —
   no extra webhook setup needed once the GitHub repo is connected.

### Verifying the live deployment

```bash
curl https://YOUR-LIVE-URL/health
```
should return `{"status": "ok", "database": "up", ...}`. From there, `/docs` on the live URL
gives an interactive Swagger UI to exercise every endpoint the same way as local.

---

## Postman collection

Import `postman_collection.json`. It includes a collection-level `{{base_url}}` variable
(default `http://localhost:8000`) and automatically stores `{{access_token}}` /
`{{refresh_token}}` / `{{task_id}}` from responses so requests can be run top-to-bottom without
manual copy-pasting.
