from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import OrderStatus


class OrderCreate(BaseModel):
    order_id: str = Field(min_length=1, max_length=100)
    amount: int = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    customer_email: str | None = Field(
        default=None,
        max_length=320,
    )


class OrderUpdate(BaseModel):
    status: OrderStatus


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    merchant_id: UUID
    order_id: str
    amount: int
    currency: str
    customer_email: str | None
    status: OrderStatus