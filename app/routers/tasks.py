"""Task endpoints. Every route only ever touches the logged-in user's own tasks."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.task import TaskPriority, TaskStatus
from app.models.user import User
from app.schemas.common import PaginatedResponse, error_responses
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services.task_service import TaskService

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

_AUTH_ERRORS = error_responses(401, 403)


@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a task",
    description=(
        "Creates a task owned by the logged-in user. HTML tags are stripped from "
        "the title and description."
    ),
    responses={**_AUTH_ERRORS, **error_responses(413, 422)},
)
def create_task(
    payload: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a task for the current user."""
    return TaskService(db).create_task(current_user.id, payload)


@router.get(
    "",
    response_model=PaginatedResponse[TaskResponse],
    summary="List my tasks",
    description=(
        "Returns one page of the logged-in user's tasks, newest first. Filter by "
        "`status` or `priority`, or search task titles with `search`."
    ),
    responses={**_AUTH_ERRORS, **error_responses(422)},
)
def list_tasks(
    page: int = Query(1, ge=1, description="Page number, starting at 1."),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)."),
    status_filter: TaskStatus | None = Query(
        None, alias="status", description="Only tasks with this status."
    ),
    priority: TaskPriority | None = Query(None, description="Only tasks with this priority."),
    search: str | None = Query(
        None, min_length=1, max_length=200, description="Text to look for in titles."
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return one page of the current user's tasks."""
    items, total = TaskService(db).list_tasks(
        current_user.id,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
        priority_filter=priority,
        search=search,
    )
    return PaginatedResponse[TaskResponse](
        total=total,
        page=page,
        page_size=page_size,
        has_more=page * page_size < total,
        items=[TaskResponse.model_validate(task) for task in items],
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Get one task",
    description="Returns a single task. A task that belongs to someone else returns 404.",
    responses={**_AUTH_ERRORS, **error_responses(404, 422)},
)
def get_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return one of the current user's tasks."""
    return TaskService(db).get_task(task_id, current_user.id)


@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Update a task",
    description="Changes the fields you send. Fields you leave out stay as they are.",
    responses={**_AUTH_ERRORS, **error_responses(404, 413, 422)},
)
def update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update one of the current user's tasks."""
    return TaskService(db).update_task(task_id, current_user.id, payload)


@router.patch(
    "/{task_id}",
    response_model=TaskResponse,
    summary="Partially update a task",
    description="Same behaviour as PUT: only the fields you send are changed.",
    responses={**_AUTH_ERRORS, **error_responses(404, 413, 422)},
)
def partial_update_task(
    task_id: uuid.UUID,
    payload: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Partially update one of the current user's tasks."""
    return TaskService(db).update_task(task_id, current_user.id, payload)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a task",
    description="Permanently deletes a task. Returns no body on success.",
    responses={**_AUTH_ERRORS, **error_responses(404, 422)},
)
def delete_task(
    task_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete one of the current user's tasks."""
    TaskService(db).delete_task(task_id, current_user.id)
