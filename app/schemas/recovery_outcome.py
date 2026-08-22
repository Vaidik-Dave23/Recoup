from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RecoveryOutcomeCreate(BaseModel):
    case_id: UUID
    action_id: UUID
    recovered: bool
    amount_recovered: int = Field(default=0, ge=0)
    notes: str | None = None


class RecoveryOutcomeResponse(BaseModel):
    id: UUID
    case_id: UUID
    action_id: UUID
    recovered: bool
    amount_recovered: int
    recovered_at: datetime | None
    notes: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)