from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Payment
from app.schemas import PaymentCreate, PaymentResponse
from app.services.payment_creation import TariffNotFoundError, create_payment

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
