from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AIInvestigationCreate(BaseModel):
    case_id: UUID
    node_name: str
    model_name: str | None = None
    input_payload: dict[str, Any] | None = None
    response_payload: dict[str, Any]
    confidence: Decimal | None = None


class AIInvestigationResponse(BaseModel):
    id: UUID
    case_id: UUID
    node_name: str
    model_name: str | None
    input_payload: dict[str, Any] | None
    response_payload: dict[str, Any]
    confidence: Decimal | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)