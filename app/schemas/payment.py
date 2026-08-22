from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PaymentCreate(BaseModel):
    order_id: str = Field(min_length=1, max_length=255)
    amount: Decimal = Field(gt=0)
    currency: str = Field(
        default="INR",
        min_length=3,
        max_length=3,
    )
    payment_method: str = Field(
        min_length=1,
        max_length=50,
    )
    transaction_id: str = Field(
        min_length=1,
        max_length=100,
    )


class PaymentResponse(BaseModel):
    id: UUID
    merchant_id: UUID
    order_id: UUID
    amount: Decimal
    currency: str
    payment_method: str
    transaction_id: str = Field(validation_alias="razorpay_payment_id")
    status: str

    model_config = ConfigDict(from_attributes=True)
