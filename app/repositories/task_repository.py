import uuid
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.task import Task, TaskPriority, TaskStatus
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    def __init__(self, db: Session):
        super().__init__(Task, db)

    def get_for_owner(self, task_id: uuid.UUID, owner_id: uuid.UUID) -> Optional[Task]:
        stmt = select(Task).where(Task.id == task_id, Task.owner_id == owner_id)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_for_owner(
        self,
        owner_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        status_filter: Optional[TaskStatus] = None,
        priority_filter: Optional[TaskPriority] = None,
        search: Optional[str] = None,
    ) -> Tuple[List[Task], int]:
        stmt = select(Task).where(Task.owner_id == owner_id)
        count_stmt = (
            select(func.count()).select_from(Task).where(Task.owner_id == owner_id)
        )

        if status_filter is not None:
            stmt = stmt.where(Task.status == status_filter)
            count_stmt = count_stmt.where(Task.status == status_filter)
        if priority_filter is not None:
            stmt = stmt.where(Task.priority == priority_filter)
            count_stmt = count_stmt.where(Task.priority == priority_filter)
        if search:
            like_pattern = f"%{search }%"
            stmt = stmt.where(Task.title.ilike(like_pattern))
            count_stmt = count_stmt.where(Task.title.ilike(like_pattern))

        total = self.db.execute(count_stmt).scalar_one()

        stmt = (
            stmt.order_by(Task.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list(self.db.execute(stmt).scalars().all())
        return items, total
