from fastapi import APIRouter, Depends, HTTPException, status
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
    db: Session = Depends(get_db),
) -> PaymentResponse:
    try:
        return create_payment(db, payment_data)
    except TariffNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tariff not found",
        ) from exc
