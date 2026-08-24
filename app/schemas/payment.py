from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field
from app.db.models.enums import PaymentStatus



class PaymentCreate(BaseModel):
    order_id: str = Field(min_length=1, max_length=255)
    amount: int = Field(gt=0)
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
    status: PaymentStatus | None = Field(default=PaymentStatus.CREATED)
    failure_reason: str | None = Field(default=None, max_length=255)



class PaymentResponse(BaseModel):
    id: UUID
    merchant_id: UUID
    order_id: UUID
    amount: int
    currency: str
    payment_method: str
    transaction_id: str = Field(validation_alias="razorpay_payment_id")
    status: str

    model_config = ConfigDict(from_attributes=True)
