import json

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Payment, Tariff
from app.schemas import PaymentCreate
from app.services.payments import (
    PaymentStatus,
    build_payment_schedule,
    calculate_payment_amount,
)


class TariffNotFoundError(LookupError):
    """Raised when payment creation references an unknown tariff."""


def create_payment(
    db: Session,
    payment_data: PaymentCreate,
    idempotency_key: str | None = None,
) -> tuple[Payment, bool]:
    if idempotency_key is not None:
        existing_payment = db.scalar(
            select(Payment).where(Payment.idempotency_key == idempotency_key)
        )
        if existing_payment is not None:
            return existing_payment, False

    tariff = db.scalar(select(Tariff).where(Tariff.id == payment_data.tariff_id))
    if tariff is None:
        raise TariffNotFoundError(payment_data.tariff_id)

    amount, discount = calculate_payment_amount(tariff.price, payment_data.promo_code)
    schedule = build_payment_schedule(
        amount, payment_data.method, payment_data.installment_months
    )
    payment = Payment(
        status=PaymentStatus.PENDING,
        tariff_id=tariff.id,
        amount=amount,
        discount=discount,
        method=payment_data.method,
        installment_months=payment_data.installment_months,
        schedule=json.dumps(schedule) if schedule is not None else None,
        email=payment_data.email,
        idempotency_key=idempotency_key,
    )
    db.add(payment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if idempotency_key is not None:
            existing_payment = db.scalar(
                select(Payment).where(Payment.idempotency_key == idempotency_key)
            )
            if existing_payment is not None:
                return existing_payment, False
        raise
    db.refresh(payment)
    return payment, True
