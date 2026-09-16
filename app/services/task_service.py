import uuid
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.exceptions import NotFoundError
from app.models.task import Task, TaskPriority, TaskStatus
from app.repositories.task_repository import TaskRepository
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:
    def __init__(self, db: Session):
        self.db = db
        self.tasks = TaskRepository(db)

    def create_task(self, owner_id: uuid.UUID, data: TaskCreate) -> Task:
        task = Task(owner_id=owner_id, **data.model_dump())
        return self.tasks.create(task)

    def get_task(self, task_id: uuid.UUID, owner_id: uuid.UUID) -> Task:
        task = self.tasks.get_for_owner(task_id, owner_id)
        if not task:
            raise NotFoundError("Task not found")
        return task

    def list_tasks(
        self,
        owner_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[TaskStatus] = None,
        priority_filter: Optional[TaskPriority] = None,
        search: Optional[str] = None,
    ) -> Tuple[list[Task], int]:
        return self.tasks.list_for_owner(
            owner_id,
            page=page,
            page_size=page_size,
            status_filter=status_filter,
            priority_filter=priority_filter,
            search=search,
        )

    def update_task(
        self, task_id: uuid.UUID, owner_id: uuid.UUID, data: TaskUpdate
    ) -> Task:
        task = self.get_task(task_id, owner_id)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(task, field, value)
        return self.tasks.update(task)

    def delete_task(self, task_id: uuid.UUID, owner_id: uuid.UUID) -> None:
        task = self.get_task(task_id, owner_id)
        self.tasks.delete(task)
