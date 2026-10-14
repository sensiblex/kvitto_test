import hashlib
import hmac
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


WEBHOOK_SECRET = "test-webhook-secret"


@pytest.fixture
def client(isolated_database, monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", WEBHOOK_SECRET)
    with TestClient(main.app) as test_client:
        yield test_client


def sign_body(body: bytes) -> str:
    return hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()


def post_signed_webhook(client, payload):
    body = json.dumps(payload).encode()
    return client.post(
        "/webhooks/bank",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Signature": sign_body(body),
        },
    )


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


def test_create_payment_without_promo_returns_full_amount(client):
    tariff_id = get_standard_tariff_id(client)

    response = client.post("/payments", json=payment_payload(tariff_id))

    assert response.status_code == 201
    payment = response.json()
    assert payment["amount"] == 1_990_000
    assert payment["discount"] == 0
    assert payment["status"] == "pending"


def test_create_payment_with_promo_returns_discount_and_amount(client):
    tariff_id = get_standard_tariff_id(client)

    response = client.post(
        "/payments",
        json=payment_payload(tariff_id, promo_code="KVITTO10"),
    )

    assert response.status_code == 201
    payment = response.json()
    assert payment["discount"] == 199_000
    assert payment["amount"] == 1_791_000


def test_create_payment_accepts_lowercase_promo_code(client):
    tariff_id = get_standard_tariff_id(client)

    response = client.post(
        "/payments",
        json=payment_payload(tariff_id, promo_code="kvitto10"),
    )

    assert response.status_code == 201
    payment = response.json()
    assert payment["discount"] == 199_000
    assert payment["amount"] == 1_791_000


@pytest.mark.parametrize("months", [3, 6, 12])
def test_create_installment_payment_has_exact_schedule(client, months):
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
    payment = response.json()
    schedule = payment["schedule"]
    assert len(schedule) == months
    assert all(isinstance(part, int) for part in schedule)
    assert sum(schedule) == payment["amount"] == 1_990_000


def test_repeated_idempotency_key_returns_one_payment(client, isolated_database):
    tariff_id = get_standard_tariff_id(client)
    payload = payment_payload(tariff_id)
    headers = {"Idempotency-Key": "integration-test-key"}

    first_response = client.post("/payments", json=payload, headers=headers)
    repeated_response = client.post("/payments", json=payload, headers=headers)

    assert first_response.status_code == 201
    assert repeated_response.status_code == 200
    assert repeated_response.json() == first_response.json()

    with isolated_database() as db:
        payments = db.scalars(select(Payment)).all()
        assert len(payments) == 1
        assert payments[0].id == first_response.json()["id"]


def test_invalid_transition_returns_409_without_changing_status(client):
    tariff_id = get_standard_tariff_id(client)
    create_response = client.post("/payments", json=payment_payload(tariff_id))
    payment_id = create_response.json()["id"]

    webhook_response = post_signed_webhook(
        client, {"payment_id": payment_id, "status": "refunded"}
    )
    payment_response = client.get(f"/payments/{payment_id}")

    assert webhook_response.status_code == 409
    assert webhook_response.json() == {"error": "invalid_transition"}
    assert payment_response.status_code == 200
    assert payment_response.json()["status"] == "pending"


def test_get_unknown_payment_returns_404(client):
    response = client.get("/payments/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Payment not found"}


def test_root_returns_health_status(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
