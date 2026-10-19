"""Health check used by Docker, Railway and uptime monitors."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    summary="Health check",
    description=(
        "Returns 200 when the API and its database are reachable, and 503 when "
        "the database is down."
    ),
    responses={503: {"description": "The database is unreachable."}},
)
def health_check(db: Session = Depends(get_db)):
    """Report whether the API and the database are working."""
    db_status = "up"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "down"

    body = {
        "status": "ok" if db_status == "up" else "degraded",
        "database": db_status,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    return JSONResponse(body, status_code=200 if db_status == "up" else 503)
