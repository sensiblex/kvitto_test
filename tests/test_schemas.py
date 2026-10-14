import json
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas import BankWebhook, PaymentCreate, PaymentResponse
from app.services.payments import PaymentMethod, PaymentStatus


@pytest.mark.parametrize(
    ("method", "installment_months"),
    [
        (PaymentMethod.CARD, None),
        (PaymentMethod.SBP, None),
        (PaymentMethod.INSTALLMENT, 3),
        (PaymentMethod.INSTALLMENT, 6),
        (PaymentMethod.INSTALLMENT, 12),
    ],
)
def test_payment_create_accepts_valid_method_and_installment_configuration(
    method, installment_months
):
    payment = PaymentCreate.model_validate(
        {
            "tariff_id": 1,
            "email": "student@example.com",
            "method": method,
            "installment_months": installment_months,
        }
    )

    assert payment.method == method
    assert payment.installment_months == installment_months


def test_payment_create_requires_tariff_email_and_method():
    with pytest.raises(ValidationError):
        PaymentCreate.model_validate({})


def test_payment_create_requires_installment_months_for_installment():
    with pytest.raises(ValidationError):
        PaymentCreate.model_validate(
            {"tariff_id": 1, "email": "student@example.com", "method": "installment"}
        )


@pytest.mark.parametrize("method", [PaymentMethod.CARD, PaymentMethod.SBP])
def test_payment_create_rejects_installment_months_for_other_methods(method):
    with pytest.raises(ValidationError):
        PaymentCreate.model_validate(
            {
                "tariff_id": 1,
                "email": "student@example.com",
                "method": method,
                "installment_months": 3,
            }
        )


@pytest.mark.parametrize("months", [0, 1, 4, 24])
def test_payment_create_rejects_unsupported_installment_months(months):
    with pytest.raises(ValidationError):
        PaymentCreate.model_validate(
            {
                "tariff_id": 1,
                "email": "student@example.com",
                "method": PaymentMethod.INSTALLMENT,
                "installment_months": months,
            }
        )


def test_payment_create_rejects_unknown_method():
    with pytest.raises(ValidationError):
        PaymentCreate.model_validate(
            {"tariff_id": 1, "email": "student@example.com", "method": "cash"}
        )


@pytest.mark.parametrize("promo_code", ["KVITTO10", "kvitto10", "Kvitto10", "KvItTo10"])
def test_payment_create_accepts_case_insensitive_promo_code(promo_code):
    payment = PaymentCreate.model_validate(
        {
            "tariff_id": 1,
            "email": "student@example.com",
            "method": PaymentMethod.CARD,
            "promo_code": promo_code,
        }
    )

    assert payment.promo_code == promo_code


@pytest.mark.parametrize("promo_code", ["UNKNOWN", "KVITTO", ""])
def test_payment_create_rejects_unknown_promo_code(promo_code):
    with pytest.raises(ValidationError):
        PaymentCreate.model_validate(
            {
                "tariff_id": 1,
                "email": "student@example.com",
                "method": PaymentMethod.CARD,
                "promo_code": promo_code,
            }
        )


def test_payment_response_validates_orm_attributes_and_parses_schedule():
    created_at = datetime(2026, 10, 14, tzinfo=timezone.utc)
    payment = SimpleNamespace(
        id=42,
        status="pending",
        tariff_id=2,
        amount=1_990_000,
        discount=0,
        method="installment",
        installment_months=3,
        schedule=json.dumps([663_334, 663_333, 663_333]),
        email="student@example.com",
        created_at=created_at,
    )

    response = PaymentResponse.model_validate(payment)

    assert response.model_dump(mode="json") == {
        "id": 42,
        "status": "pending",
        "tariff_id": 2,
        "amount": 1_990_000,
        "discount": 0,
        "method": "installment",
        "installment_months": 3,
        "schedule": [663_334, 663_333, 663_333],
        "email": "student@example.com",
        "created_at": "2026-10-14T00:00:00Z",
    }


def test_payment_response_marks_sqlite_naive_created_at_as_utc():
    payment = SimpleNamespace(
        id=42,
        status="pending",
        tariff_id=2,
        amount=1_990_000,
        discount=0,
        method="card",
        installment_months=None,
        schedule=None,
        email="student@example.com",
        created_at=datetime(2026, 10, 14),
    )

    response = PaymentResponse.model_validate(payment)

    assert response.model_dump(mode="json")["created_at"] == "2026-10-14T00:00:00Z"


def test_payment_response_preserves_null_schedule():
    payment = SimpleNamespace(
        id=42,
        status="pending",
        tariff_id=2,
        amount=1_990_000,
        discount=0,
        method="card",
        installment_months=None,
        schedule=None,
        email="student@example.com",
        created_at=datetime(2026, 10, 14, tzinfo=timezone.utc),
    )

    assert PaymentResponse.model_validate(payment).schedule is None


@pytest.mark.parametrize("status", list(PaymentStatus))
def test_bank_webhook_accepts_supported_statuses(status):
    webhook = BankWebhook.model_validate({"payment_id": 1, "status": status})

    assert webhook.payment_id == 1
    assert webhook.status == status


def test_bank_webhook_rejects_unknown_status():
    with pytest.raises(ValidationError):
        BankWebhook.model_validate({"payment_id": 1, "status": "cancelled"})
