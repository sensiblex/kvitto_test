import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base
from app.models import Tariff


@pytest.fixture
def isolated_database(monkeypatch):
    test_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    test_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine,
    )
    monkeypatch.setattr(main, "engine", test_engine)
    monkeypatch.setattr(main, "SessionLocal", test_session_local)
    yield test_session_local
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()


def test_startup_seeds_required_tariffs_idempotently(isolated_database):
    with TestClient(main.app):
        pass
    with TestClient(main.app):
        pass

    with isolated_database() as db:
        tariffs = db.scalars(select(Tariff).order_by(Tariff.title)).all()

    assert [(tariff.title, tariff.price) for tariff in tariffs] == [
        ("basic", 990_000),
        ("premium", 2_990_000),
        ("standard", 1_990_000),
    ]
