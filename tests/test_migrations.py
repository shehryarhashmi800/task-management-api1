import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url

from app.config import settings
from tests.utils import drop_database, ensure_database

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def scratch_db_url():
    url = make_url(settings.TEST_DATABASE_URL).set(database="taskdb_migrations_test")
    rendered = url.render_as_string(hide_password=False)
    drop_database(rendered)
    ensure_database(rendered)
    yield rendered
    drop_database(rendered)


def alembic(url, *args):
    env = {**os.environ, "DATABASE_URL": url}
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def task_indexes(url):
    engine = create_engine(url)
    try:
        return {i["name"] for i in inspect(engine).get_indexes("tasks")}
    finally:
        engine.dispose()


def test_migrations_apply_cleanly_and_match_the_models(scratch_db_url):
    upgrade = alembic(scratch_db_url, "upgrade", "head")
    assert upgrade.returncode == 0, upgrade.stderr
    indexes = task_indexes(scratch_db_url)
    assert "ix_tasks_owner_created" in indexes
    assert not {"ix_tasks_owner_id", "ix_tasks_title"} & indexes

    drift = alembic(scratch_db_url, "check")
    assert drift.returncode == 0, drift.stdout + drift.stderr


def test_migrations_can_be_rolled_back_and_reapplied(scratch_db_url):
    assert alembic(scratch_db_url, "upgrade", "head").returncode == 0
    assert alembic(scratch_db_url, "downgrade", "0001").returncode == 0
    assert "ix_tasks_owner_id" in task_indexes(scratch_db_url)
    assert alembic(scratch_db_url, "downgrade", "base").returncode == 0
    assert alembic(scratch_db_url, "upgrade", "head").returncode == 0
