"""Serializable working state for one recovery-agent run."""

from __future__ import annotations

from typing import Any, TypedDict


class RecoveryState(TypedDict, total=False):
    case_id: str
    merchant_id: str
    payment_id: str | None
    case_type: str
    failure_reason: str
    amount_at_risk: int
    currency: str
    attempt_count: int
    customer_email: str | None
    customer_name: str | None

    triage: dict[str, Any] | None
    strategy: dict[str, Any] | None
    content: dict[str, Any] | None
    action_id: str | None
    action_channel: str | None
    send_result: dict[str, Any] | None
    escalation_id: str | None

    escalated: bool
    route: str
    decision_source: str | None
    policy_reason: str | None
