"""Helpers shared by the test suite."""

import re

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


def ensure_database(url_string: str) -> None:
    """Create the database in ``url_string`` if it does not exist.

    Refuses names that do not end in ``_test`` so a typo can never point the
    destructive tests at a real database.
    """
    url = make_url(url_string)
    name = url.database or ""
    if not name.endswith("_test") or not re.fullmatch(r"[A-Za-z0-9_]+", name):
        raise RuntimeError(
            f"Refusing to run tests: database name must end in _test (got {name!r}). "
            "The tests wipe it."
        )
    admin_engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{name}"'))
    admin_engine.dispose()


def drop_database(url_string: str) -> None:
    """Drop a ``*_test`` database if it exists."""
    url = make_url(url_string)
    name = url.database or ""
    if not name.endswith("_test") or not re.fullmatch(r"[A-Za-z0-9_]+", name):
        raise RuntimeError(f"Refusing to drop {name!r}")
    admin_engine = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin_engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    admin_engine.dispose()
