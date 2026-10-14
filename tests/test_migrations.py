from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect

from alembic import command
from alembic.config import Config

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def migrated_engine(tmp_path, monkeypatch):
    """Apply Alembic migrations to a fresh temporary SQLite database."""
    db_path = tmp_path / "migrated.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    command.upgrade(config, "head")
    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    yield engine
    engine.dispose()


def test_upgrade_creates_tables(migrated_engine):
    tables = set(inspect(migrated_engine).get_table_names())
    assert {"tariffs", "payments", "alembic_version"} <= tables


def test_upgrade_creates_idempotency_key_unique_constraint(migrated_engine):
    constraints = inspect(migrated_engine).get_unique_constraints("payments")
    assert any(
        constraint["name"] == "uq_payment_idempotency_key"
        and constraint["column_names"] == ["idempotency_key"]
        for constraint in constraints
    )


def test_repeated_upgrade_does_not_fail(tmp_path, monkeypatch):
    db_path = tmp_path / "migrated.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    config = Config(str(PROJECT_ROOT / "alembic.ini"))

    command.upgrade(config, "head")
    command.upgrade(config, "head")
