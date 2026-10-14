from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Payment
from app.schemas import BankWebhook, PaymentCreate, PaymentResponse
from app.services.payment_creation import TariffNotFoundError, create_payment
from app.services.payments import (
    InvalidStatusTransitionError,
    validate_status_transition,
)

router = APIRouter(tags=["payments"])


@router.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_payment(
    payment_data: PaymentCreate,
    response: Response,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: Session = Depends(get_db),
) -> PaymentResponse:
    try:
        payment, created = create_payment(db, payment_data, idempotency_key)
        if not created:
            response.status_code = status.HTTP_200_OK
        return payment
    except TariffNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tariff not found",
        ) from exc


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: int, db: Session = Depends(get_db)) -> PaymentResponse:
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    return payment


@router.post("/webhooks/bank")
def bank_webhook(webhook: BankWebhook, db: Session = Depends(get_db)) -> JSONResponse:
    payment = db.get(Payment, webhook.payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    try:
        validate_status_transition(payment.status, webhook.status)
    except InvalidStatusTransitionError:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"error": "invalid_transition"},
        )

    payment.status = webhook.status
    db.commit()
    return JSONResponse(content={"result": "ok"})
