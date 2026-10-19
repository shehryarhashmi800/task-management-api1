"""Speed up the task list: one composite index, drop two unusable ones.

The list query filters by owner and sorts by newest first, so a single index on
(owner_id, created_at) serves it. The separate owner_id index is redundant (the
composite starts with owner_id) and the title index can never be used by the
`ILIKE '%text%'` search, so both only slow down writes.

Revision ID: 0002
Revises: 0001
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add the composite index, then drop the two redundant ones."""
    op.create_index("ix_tasks_owner_created", "tasks", ["owner_id", "created_at"])
    op.drop_index("ix_tasks_owner_id", table_name="tasks")
    op.drop_index("ix_tasks_title", table_name="tasks")


def downgrade() -> None:
    """Restore the original indexes."""
    op.create_index("ix_tasks_title", "tasks", ["title"])
    op.create_index("ix_tasks_owner_id", "tasks", ["owner_id"])
    op.drop_index("ix_tasks_owner_created", table_name="tasks")
