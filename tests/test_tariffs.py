import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base, get_db
from app.models import Tariff
from app.schemas import TariffResponse


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
    monkeypatch.setattr(main, "SessionLocal", test_session_local)

    def override_get_db():
        db = test_session_local()
        try:
            yield db
        finally:
            db.close()

    main.app.dependency_overrides[get_db] = override_get_db
    yield test_session_local
    main.app.dependency_overrides.clear()
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


def test_get_tariffs_returns_all_tariffs_in_kopecks(isolated_database):
    with TestClient(main.app) as client:
        response = client.get("/tariffs")

    assert response.status_code == 200

    tariffs = response.json()
    assert len(tariffs) == 3
    assert [(t["title"], t["price"]) for t in tariffs] == [
        ("basic", 990_000),
        ("standard", 1_990_000),
        ("premium", 2_990_000),
    ]
    for tariff in tariffs:
        TariffResponse.model_validate(tariff)
        assert set(tariff) == {"id", "title", "price"}
        assert isinstance(tariff["price"], int)
