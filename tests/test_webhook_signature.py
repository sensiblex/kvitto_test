import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import main
from app.database import Base, get_db
from app.models import Payment
from app.services.webhook_signature import compute_signature, verify_signature

WEBHOOK_SECRET = "test-webhook-secret"


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


@pytest.fixture
def client(isolated_database, monkeypatch):
    monkeypatch.setenv("WEBHOOK_SECRET", WEBHOOK_SECRET)
    with TestClient(main.app) as test_client:
        yield test_client


def webhook_body(payload: dict) -> bytes:
    return json.dumps(payload).encode()


def signed_headers(body: bytes, secret: str = WEBHOOK_SECRET) -> dict:
    return {
        "Content-Type": "application/json",
        "X-Signature": hmac.new(secret.encode(), body, hashlib.sha256).hexdigest(),
    }


def post_webhook(client, body: bytes, headers: dict | None = None):
    return client.post(
        "/webhooks/bank",
        content=body,
        headers=headers or {"Content-Type": "application/json"},
    )


def create_payment(client) -> int:
    tariffs = client.get("/tariffs").json()
    tariff_id = next(t["id"] for t in tariffs if t["title"] == "standard")
    response = client.post(
        "/payments",
        json={
            "tariff_id": tariff_id,
            "email": "student@example.com",
            "method": "card",
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_verify_signature_accepts_correct_signature():
    body = webhook_body({"payment_id": 1, "status": "succeeded"})
    signature = compute_signature(body, WEBHOOK_SECRET)

    assert verify_signature(body, signature, WEBHOOK_SECRET)


def test_verify_signature_rejects_wrong_signature():
    body = webhook_body({"payment_id": 1, "status": "succeeded"})

    assert not verify_signature(body, "0" * 64, WEBHOOK_SECRET)


def test_verify_signature_rejects_missing_signature():
    body = webhook_body({"payment_id": 1, "status": "succeeded"})

    assert not verify_signature(body, None, WEBHOOK_SECRET)


def test_verify_signature_rejects_signature_of_different_body():
    body = webhook_body({"payment_id": 1, "status": "succeeded"})
    tampered_body = webhook_body({"payment_id": 2, "status": "succeeded"})
    signature = compute_signature(tampered_body, WEBHOOK_SECRET)

    assert not verify_signature(body, signature, WEBHOOK_SECRET)


def test_verify_signature_rejects_wrong_secret():
    body = webhook_body({"payment_id": 1, "status": "succeeded"})
    signature = compute_signature(body, "another-secret")

    assert not verify_signature(body, signature, WEBHOOK_SECRET)


def test_webhook_rejects_missing_signature_without_changing_status(
    client, isolated_database
):
    payment_id = create_payment(client)

    response = post_webhook(
        client, webhook_body({"payment_id": payment_id, "status": "succeeded"})
    )

    assert response.status_code == 401
    with isolated_database() as db:
        payment = db.get(Payment, payment_id)
        assert payment is not None
        assert payment.status == "pending"


def test_webhook_rejects_invalid_signature_without_changing_status(
    client, isolated_database
):
    payment_id = create_payment(client)

    response = post_webhook(
        client,
        webhook_body({"payment_id": payment_id, "status": "succeeded"}),
        headers={
            "Content-Type": "application/json",
            "X-Signature": "0" * 64,
        },
    )

    assert response.status_code == 401
    with isolated_database() as db:
        payment = db.get(Payment, payment_id)
        assert payment is not None
        assert payment.status == "pending"


def test_webhook_rejects_signature_of_tampered_body(client):
    payment_id = create_payment(client)
    body = webhook_body({"payment_id": payment_id, "status": "succeeded"})
    signature = compute_signature(b'{"payment_id": 1}', WEBHOOK_SECRET)

    response = post_webhook(
        client,
        body,
        headers={
            "Content-Type": "application/json",
            "X-Signature": signature,
        },
    )

    assert response.status_code == 401


def test_webhook_accepts_valid_signature(client):
    payment_id = create_payment(client)
    body = webhook_body({"payment_id": payment_id, "status": "succeeded"})

    response = post_webhook(client, body, headers=signed_headers(body))

    assert response.status_code == 200
    assert response.json() == {"result": "ok"}
    payment_response = client.get(f"/payments/{payment_id}")
    assert payment_response.json()["status"] == "succeeded"


def test_webhook_returns_404_for_unknown_payment_with_valid_signature(client):
    body = webhook_body({"payment_id": 999_999, "status": "succeeded"})

    response = post_webhook(client, body, headers=signed_headers(body))

    assert response.status_code == 404
    assert response.json() == {"detail": "Payment not found"}


def test_webhook_returns_409_for_invalid_transition_with_valid_signature(
    client,
):
    payment_id = create_payment(client)
    body = webhook_body({"payment_id": payment_id, "status": "refunded"})

    response = post_webhook(client, body, headers=signed_headers(body))

    assert response.status_code == 409
    assert response.json() == {"error": "invalid_transition"}


def test_webhook_returns_422_for_invalid_body_with_valid_signature(client):
    body = webhook_body({"payment_id": "not-an-int", "status": "succeeded"})

    response = post_webhook(client, body, headers=signed_headers(body))

    assert response.status_code == 422
    assert "detail" in response.json()


def test_webhook_returns_500_when_secret_is_not_configured(client, monkeypatch):
    payment_id = create_payment(client)
    monkeypatch.delenv("WEBHOOK_SECRET")
    body = webhook_body({"payment_id": payment_id, "status": "succeeded"})

    response = post_webhook(client, body, headers=signed_headers(body))

    assert response.status_code == 500
    payment_response = client.get(f"/payments/{payment_id}")
    assert payment_response.json()["status"] == "pending"


def test_webhook_returns_500_when_secret_is_empty(client, monkeypatch):
    payment_id = create_payment(client)
    monkeypatch.setenv("WEBHOOK_SECRET", "")
    body = webhook_body({"payment_id": payment_id, "status": "succeeded"})

    response = post_webhook(client, body, headers=signed_headers(body))

    assert response.status_code == 500
    payment_response = client.get(f"/payments/{payment_id}")
    assert payment_response.json()["status"] == "pending"
