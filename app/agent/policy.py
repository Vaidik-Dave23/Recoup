"""Deterministic backend safety policies for revenue recovery.

This module is the single source of truth for deterministic recovery rules that
MUST override or constrain LLM strategy decisions before any automated recovery
action can be created or executed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from app.core.config import settings

HARD_DECLINE_REASONS: Final[frozenset[str]] = frozenset({
    "stolen_card_decline",
})

POLICY_REASON_HARD_DECLINE: Final[str] = "hard_decline_requires_human_escalation"
POLICY_REASON_LOW_CONFIDENCE: Final[str] = "low_confidence"

DECISION_SOURCE_POLICY: Final[str] = "policy"
DECISION_SOURCE_LLM: Final[str] = "llm"


@dataclass(frozen=True)
class PolicyDecision:
    """Structured decision outcome after applying deterministic backend policies."""
    effective_action: str
    escalated: bool
    decision_source: str
    policy_reason: str | None
    route: str
    trigger: str


def is_hard_decline(failure_reason: str | None) -> bool:
    """Check whether a failure reason represents a non-recoverable hard decline."""
    if not failure_reason:
        return False
    normalized = failure_reason.strip().lower()
    return normalized in HARD_DECLINE_REASONS


def evaluate_recovery_decision(
    failure_reason: str | None,
    raw_action: str | None,
    raw_channel: str | None,
    confidence: float,
    confidence_threshold: float | None = None,
) -> PolicyDecision:
    """Evaluate effective recovery action and routing under deterministic safety policies.

    Rules:
    1. If failure_reason is in HARD_DECLINE_REASONS (e.g., stolen_card_decline),
       the effective action MUST be 'escalate' regardless of LLM action or confidence.
       decision_source is recorded as 'policy'.
    2. Only 'email' is an executable live channel. Other channels are normalized to email.
    3. For non-hard declines, if confidence is below confidence_threshold, the case
       is escalated to a human with decision_source 'llm' and trigger 'low_confidence'.
    4. For non-hard declines with confidence >= confidence_threshold, the case proceeds
       to automated content generation with decision_source 'llm'.
    """
    threshold = (
        confidence_threshold
        if confidence_threshold is not None
        else settings.recovery_confidence_threshold
    )

    # 1. Deterministic Hard Decline Safety Guard (Zero-Trust on LLM)
    if is_hard_decline(failure_reason):
        return PolicyDecision(
            effective_action="escalate",
            escalated=True,
            decision_source=DECISION_SOURCE_POLICY,
            policy_reason=POLICY_REASON_HARD_DECLINE,
            route="escalate",
            trigger=POLICY_REASON_HARD_DECLINE,
        )

    # 2. Channel normalization (only email is live)
    normalized_action = str(raw_action or "email").lower()
    normalized_channel = str(raw_channel or "email").lower()
    executable_action = (
        "email"
        if normalized_action == "email" and normalized_channel == "email"
        else "email"
    )

    # 3. Confidence Threshold Guardrail
    if confidence < threshold:
        return PolicyDecision(
            effective_action="escalate",
            escalated=True,
            decision_source=DECISION_SOURCE_LLM,
            policy_reason=POLICY_REASON_LOW_CONFIDENCE,
            route="escalate",
            trigger=POLICY_REASON_LOW_CONFIDENCE,
        )

    return PolicyDecision(
        effective_action=executable_action,
        escalated=False,
        decision_source=DECISION_SOURCE_LLM,
        policy_reason=None,
        route="generate_content",
        trigger="",
    )
