"""Admin-only user management."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_admin_user
from app.database import get_db
from app.models.user import User
from app.schemas.common import error_responses
from app.schemas.user import UserResponse

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get(
    "",
    response_model=list[UserResponse],
    summary="List all users (admin only)",
    description="Returns registered users, oldest first. Requires an admin account.",
    responses=error_responses(401, 403),
)
def list_users(
    skip: int = Query(0, ge=0, description="How many users to skip."),
    limit: int = Query(50, ge=1, le=100, description="Maximum users to return."),
    _admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db),
):
    """Return a page of users. Admin only."""
    stmt = select(User).order_by(User.created_at).offset(skip).limit(limit)
    return list(db.execute(stmt).scalars().all())
