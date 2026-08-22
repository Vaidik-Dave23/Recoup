from typing import Any

from pydantic import BaseModel


class AgentRunResponse(BaseModel):
    case_id: str
    triage: dict[str, Any] | None = None
    strategy: dict[str, Any] | None = None
    content: dict[str, Any] | None = None
    action_id: str | None = None
    action_channel: str | None = None
    send_result: dict[str, Any] | None = None
    escalated: bool = False
    escalation_id: str | None = None
