"""Pure business logic for payment amount, promo codes, installments, and statuses."""

from enum import StrEnum


class PaymentMethod(StrEnum):
    CARD = "card"
    SBP = "sbp"
    INSTALLMENT = "installment"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"


PROMO_CODE = "KVITTO10"
PROMO_DISCOUNT_PERCENT = 10
ALLOWED_INSTALLMENT_MONTHS = (3, 6, 12)

ALLOWED_STATUS_TRANSITIONS = {
    PaymentStatus.PENDING: {PaymentStatus.SUCCEEDED, PaymentStatus.FAILED},
    PaymentStatus.SUCCEEDED: {PaymentStatus.REFUNDED},
    PaymentStatus.FAILED: set(),
    PaymentStatus.REFUNDED: set(),
}


class PaymentLogicError(ValueError):
    """Base class for payment business logic errors."""


class InvalidPromoCodeError(PaymentLogicError):
    """Raised when a provided promo code is not recognized."""


class InvalidInstallmentError(PaymentLogicError):
    """Raised when installment configuration is invalid."""


class InvalidStatusTransitionError(PaymentLogicError):
    """Raised when a payment status transition is not allowed."""


def calculate_discount(price: int, promo_code: str | None = None) -> int:
    if promo_code is None:
        return 0

    if promo_code.strip().upper() != PROMO_CODE:
        raise InvalidPromoCodeError(f"Unknown promo code: {promo_code!r}")

    return (price * PROMO_DISCOUNT_PERCENT) // 100


def calculate_payment_amount(
    price: int, promo_code: str | None = None
) -> tuple[int, int]:
    discount = calculate_discount(price, promo_code)
    return price - discount, discount


def calculate_installment_schedule(amount: int, months: int) -> list[int]:
    if amount < 0:
        raise InvalidInstallmentError("Amount must not be negative")
    if months not in ALLOWED_INSTALLMENT_MONTHS:
        raise InvalidInstallmentError(
            f"Installment months must be one of {ALLOWED_INSTALLMENT_MONTHS}"
        )

    base = amount // months
    remainder = amount % months
    return [base + 1] * remainder + [base] * (months - remainder)


def build_payment_schedule(
    amount: int, method: str, installment_months: int | None = None
) -> list[int] | None:
    if method == PaymentMethod.INSTALLMENT:
        if installment_months is None:
            raise InvalidInstallmentError(
                "installment_months is required for installment payments"
            )
        return calculate_installment_schedule(amount, installment_months)

    if installment_months is not None:
        raise InvalidInstallmentError(
            "installment_months is only allowed for installment payments"
        )
    return None


def can_transition_status(current_status: str, new_status: str) -> bool:
    allowed = ALLOWED_STATUS_TRANSITIONS.get(current_status, set())
    return new_status in allowed


def validate_status_transition(current_status: str, new_status: str) -> None:
    if not can_transition_status(current_status, new_status):
        raise InvalidStatusTransitionError(
            f"Cannot transition from {current_status!r} to {new_status!r}"
        )
