from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EscalationCreate(BaseModel):
    case_id: UUID
    reason: str = Field(min_length=1, max_length=1000)
    priority: str = Field(
        default="medium",
        min_length=1,
        max_length=20,
    )
    notes: str | None = None


class EscalationUpdate(BaseModel):
    status: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )
    priority: str | None = Field(
        default=None,
        min_length=1,
        max_length=20,
    )
    notes: str | None = None


class EscalationResponse(BaseModel):
    id: UUID
    case_id: UUID
    reason: str
    priority: str
    status: str
    notes: str = Field(validation_alias="summary")
    resolved_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
