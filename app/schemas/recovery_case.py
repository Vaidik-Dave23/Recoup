from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RecoveryCaseCreate(BaseModel):
    payment_id: UUID
    case_type: str = Field(min_length=1, max_length=100)
    failure_reason: str = Field(min_length=1, max_length=1000)
    amount_at_risk: int = Field(gt=0)
    currency: str = Field(
        default="INR",
        min_length=3,
        max_length=3,
    )


class RecoveryCaseUpdate(BaseModel):
    stage: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )
    status: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )
    financial_impact: int | None = Field(
        default=None,
        ge=0,
    )


class RecoveryCaseResponse(BaseModel):
    id: UUID
    merchant_id: UUID
    payment_id: UUID
    case_type: str
    failure_reason: str
    amount_at_risk: int
    currency: str
    stage: str
    attempt_count: int
    status: str
    financial_impact: int
    updated_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)