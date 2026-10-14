import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base, get_db
from app.models import Payment


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


@pytest.fixture
def client(isolated_database):
    with TestClient(main.app) as test_client:
        yield test_client


def get_standard_tariff_id(client):
    tariffs = client.get("/tariffs").json()
    return next(tariff["id"] for tariff in tariffs if tariff["title"] == "standard")


def payment_payload(tariff_id, **overrides):
    payload = {
        "tariff_id": tariff_id,
        "email": "student@example.com",
        "method": "card",
    }
    payload.update(overrides)
    return payload


@pytest.mark.parametrize("method", ["card", "sbp"])
def test_create_payment_returns_and_persists_payment(
    client, isolated_database, method
):
    tariff_id = get_standard_tariff_id(client)

    response = client.post(
        "/payments",
        json=payment_payload(tariff_id, method=method),
    )

    assert response.status_code == 201
    payment_data = response.json()
    assert set(payment_data) == {
        "id",
        "status",
        "tariff_id",
        "amount",
        "discount",
        "method",
        "installment_months",
        "schedule",
        "email",
        "created_at",
    }
    assert payment_data["status"] == "pending"
    assert payment_data["tariff_id"] == tariff_id
    assert payment_data["amount"] == 1_990_000
    assert payment_data["discount"] == 0
    assert payment_data["method"] == method
    assert payment_data["installment_months"] is None
    assert payment_data["schedule"] is None
    assert payment_data["email"] == "student@example.com"
    assert payment_data["created_at"]

    with isolated_database() as db:
        payment = db.get(Payment, payment_data["id"])
        assert payment is not None
        assert payment.status == "pending"
        assert payment.amount == 1_990_000
        assert payment.discount == 0
        assert payment.schedule is None


def test_create_payment_applies_case_insensitive_promo_code(client):
    tariff_id = get_standard_tariff_id(client)

    response = client.post(
        "/payments",
        json=payment_payload(tariff_id, promo_code="kvitto10"),
    )

    assert response.status_code == 201
    assert response.json()["amount"] == 1_791_000
    assert response.json()["discount"] == 199_000


@pytest.mark.parametrize("months", [3, 6, 12])
def test_create_installment_payment_has_exact_schedule(
    client, isolated_database, months
):
    tariff_id = get_standard_tariff_id(client)

    response = client.post(
        "/payments",
        json=payment_payload(
            tariff_id,
            method="installment",
            installment_months=months,
        ),
    )

    assert response.status_code == 201
    payment_data = response.json()
    schedule = payment_data["schedule"]
    base, remainder = divmod(1_990_000, months)
    expected_schedule = [base + 1] * remainder + [base] * (months - remainder)
    assert schedule == expected_schedule
    assert all(isinstance(amount, int) for amount in schedule)
    assert sum(schedule) == payment_data["amount"] == 1_990_000

    with isolated_database() as db:
        payment = db.scalar(select(Payment))
        assert payment is not None
        assert json.loads(payment.schedule) == schedule


@pytest.mark.parametrize(
    "overrides",
    [
        {"method": "cash"},
        {"method": "installment"},
        {"method": "sbp", "installment_months": 3},
        {"promo_code": "UNKNOWN"},
    ],
)
def test_create_payment_rejects_invalid_payload_without_saving(
    client, isolated_database, overrides
):
    tariff_id = get_standard_tariff_id(client)

    response = client.post(
        "/payments",
        json=payment_payload(tariff_id, **overrides),
    )

    assert response.status_code == 422
    with isolated_database() as db:
        assert db.scalars(select(Payment)).all() == []


def test_create_payment_returns_404_for_unknown_tariff(client, isolated_database):
    response = client.post("/payments", json=payment_payload(999_999))

    assert response.status_code == 404
    assert response.json() == {"detail": "Tariff not found"}
    with isolated_database() as db:
        assert db.scalars(select(Payment)).all() == []
