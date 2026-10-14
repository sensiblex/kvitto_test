import os

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Path,
    Query,
    Request,
    Response,
    status,
)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Payment
from app.schemas import MAX_ID, BankWebhook, PaymentCreate, PaymentResponse
from app.services.payment_creation import TariffNotFoundError, create_payment
from app.services.payment_listing import list_payments
from app.services.payments import (
    InvalidStatusTransitionError,
    PaymentStatus,
    validate_status_transition,
)
from app.services.webhook_signature import verify_signature

router = APIRouter(tags=["payments"])


def get_webhook_secret() -> str:
    secret = os.environ.get("WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="WEBHOOK_SECRET is not configured",
        )
    return secret


@router.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def post_payment(
    payment_data: PaymentCreate,
    response: Response,
    idempotency_key: str | None = Header(
        default=None, alias="Idempotency-Key", min_length=1
    ),
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


@router.get("/payments", response_model=list[PaymentResponse])
def get_payment_list(
    email: str | None = None,
    payment_status: PaymentStatus | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
) -> list[PaymentResponse]:
    return list_payments(db, email=email, status=payment_status)


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
def get_payment(
    payment_id: int = Path(ge=1, le=MAX_ID), db: Session = Depends(get_db)
) -> PaymentResponse:
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )
    return payment


@router.post("/webhooks/bank")
async def bank_webhook(
    request: Request,
    db: Session = Depends(get_db),
    webhook_secret: str = Depends(get_webhook_secret),
) -> JSONResponse:
    body = await request.body()
    signature = request.headers.get("X-Signature")
    if not verify_signature(body, signature, webhook_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature",
        )

    try:
        webhook = BankWebhook.model_validate_json(body)
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from exc

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
