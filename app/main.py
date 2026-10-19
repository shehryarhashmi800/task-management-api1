"""Application entry point: builds the FastAPI app and wires everything together."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.logging_config import setup_logging
from app.core.observability import init_sentry
from app.core.rate_limit import limiter
from app.exceptions import register_exception_handlers
from app.middleware import RequestContextMiddleware
from app.routers import auth, debug, health, tasks, users

setup_logging(settings.LOG_LEVEL, settings.LOG_FORMAT)
init_sentry()

logger = logging.getLogger("task_api")

API_DESCRIPTION = """
Backend for the Task Manager capstone: users register, log in and manage their own tasks.

### How to authenticate
1. `POST /api/v1/auth/register` to create an account.
2. `POST /api/v1/auth/login` to get an `access_token` and a `refresh_token`.
3. Click **Authorize** (top right) and paste the `access_token`.
4. When the access token expires, call `POST /api/v1/auth/refresh`.

### Errors
Every error has the same shape: `error` (a short code), `message`, optional
`details` (per-field problems) and `request_id`. Quote the `request_id` when
reporting a problem; it is also in the `X-Request-ID` response header.

### Limits
Login, register and refresh are rate limited per IP address; exceeding the limit
returns `429` with a `Retry-After` header. Request bodies are limited to 1 MB.
"""

TAGS_METADATA = [
    {"name": "auth", "description": "Create an account, log in, refresh tokens."},
    {"name": "tasks", "description": "Create, read, update and delete **your own** tasks."},
    {"name": "users", "description": "Administration. Admin accounts only."},
    {"name": "health", "description": "Is the service (and its database) up?"},
]

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=API_DESCRIPTION,
    version="1.1.0",
    openapi_tags=TAGS_METADATA,
)

app.state.limiter = limiter

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Request-ID", "Retry-After"],
)

register_exception_handlers(app)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tasks.router)
app.include_router(debug.router)


@app.get("/", tags=["health"], summary="API root")
def root():
    """Return a short message pointing at the documentation."""
    return {"message": f"{settings.PROJECT_NAME} is running", "docs": "/docs"}
