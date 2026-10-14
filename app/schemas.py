import json
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.services.payments import PaymentMethod, PaymentStatus, validate_promo_code


class TariffResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    price: int


class PaymentCreate(BaseModel):
    tariff_id: int
    email: str
    method: PaymentMethod
    installment_months: Literal[3, 6, 12] | None = None
    promo_code: str | None = None

    @field_validator("promo_code")
    @classmethod
    def validate_promo(cls, value: str | None) -> str | None:
        validate_promo_code(value)
        return value

    @model_validator(mode="after")
    def validate_installment_months(self) -> "PaymentCreate":
        if (
            self.method == PaymentMethod.INSTALLMENT
            and self.installment_months is None
        ):
            raise ValueError("installment_months is required for installment payments")
        if (
            self.method != PaymentMethod.INSTALLMENT
            and self.installment_months is not None
        ):
            raise ValueError(
                "installment_months is only allowed for installment payments"
            )
        return self


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: PaymentStatus
    tariff_id: int
    amount: int
    discount: int
    method: PaymentMethod
    installment_months: int | None
    schedule: list[int] | None
    email: str
    created_at: datetime

    @field_validator("schedule", mode="before")
    @classmethod
    def parse_schedule(cls, value: str | list[int] | None) -> list[int] | None:
        if isinstance(value, str):
            return json.loads(value)
        return value


class BankWebhook(BaseModel):
    payment_id: int
    status: PaymentStatus
