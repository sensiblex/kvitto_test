from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Payment
from app.services.payments import PaymentStatus


def list_payments(
    db: Session,
    email: str | None = None,
    status: PaymentStatus | None = None,
) -> list[Payment]:
    query = select(Payment).order_by(Payment.id)
    if email is not None:
        query = query.where(Payment.email == email)
    if status is not None:
        query = query.where(Payment.status == status)
    return list(db.scalars(query).all())
