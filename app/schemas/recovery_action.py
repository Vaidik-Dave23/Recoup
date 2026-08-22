from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RecoveryActionCreate(BaseModel):
    case_id: UUID
    investigation_id: UUID | None = None
    action_type: str = Field(min_length=1, max_length=100)
    channel: str = Field(min_length=1, max_length=50)
    subject: str | None = Field(
        default=None,
        max_length=255,
    )
    message_body: str | None = None


class RecoveryActionResponse(BaseModel):
    id: UUID
    case_id: UUID
    investigation_id: UUID | None
    action_type: str
    channel: str
    subject: str | None
    message_body: str | None
    provider_ref: str | None
    sent_at: datetime | None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)