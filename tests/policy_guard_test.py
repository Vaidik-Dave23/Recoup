"""Unit tests for deterministic recovery safety policies and hard-decline guardrails.

Validates that:
1. stolen_card_decline + Gemini says email + high confidence -> final action MUST be escalate (source: policy)
2. stolen_card_decline + Gemini says email + low confidence -> final action MUST be escalate (source: policy)
3. stolen_card_decline must never reach automated email/payment-link execution (generate_content & execute raise ValueError)
4. insufficient_funds / soft_decline + valid email strategy -> remains eligible for automated recovery
5. abandoned_checkout + valid strategy -> remains eligible for automated recovery
6. overdue_invoice + valid strategy -> remains eligible for automated recovery
7. Existing retry and confidence guardrails continue working (low confidence escalates with trigger=low_confidence)
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Add project root to sys.path automatically
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agent.nodes import RecoveryAgentNodes
from app.agent.policy import (
    DECISION_SOURCE_LLM,
    DECISION_SOURCE_POLICY,
    POLICY_REASON_HARD_DECLINE,
    POLICY_REASON_LOW_CONFIDENCE,
    evaluate_recovery_decision,
    is_hard_decline,
)
from app.agent.state import RecoveryState
from app.core.config import settings


def _check(label: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    assert condition, label


def test_stolen_card_high_confidence_escalates() -> None:
    """1. stolen_card_decline + Gemini says email + high confidence -> escalate via policy."""
    decision = evaluate_recovery_decision(
        failure_reason="stolen_card_decline",
        raw_action="email",
        raw_channel="email",
        confidence=0.95,
        confidence_threshold=0.55,
    )
    _check("stolen_card + high conf -> effective_action is escalate", decision.effective_action == "escalate")
    _check("stolen_card + high conf -> escalated is True", decision.escalated is True)
    _check("stolen_card + high conf -> route is escalate", decision.route == "escalate")
    _check("stolen_card + high conf -> decision_source is policy", decision.decision_source == DECISION_SOURCE_POLICY)
    _check("stolen_card + high conf -> policy_reason is recorded", decision.policy_reason == POLICY_REASON_HARD_DECLINE)


def test_stolen_card_low_confidence_escalates() -> None:
    """2. stolen_card_decline + Gemini says email + low confidence -> escalate via policy."""
    decision = evaluate_recovery_decision(
        failure_reason="stolen_card_decline",
        raw_action="email",
        raw_channel="email",
        confidence=0.20,
        confidence_threshold=0.55,
    )
    _check("stolen_card + low conf -> effective_action is escalate", decision.effective_action == "escalate")
    _check("stolen_card + low conf -> escalated is True", decision.escalated is True)
    _check("stolen_card + low conf -> decision_source is policy", decision.decision_source == DECISION_SOURCE_POLICY)
    _check("stolen_card + low conf -> policy_reason is recorded", decision.policy_reason == POLICY_REASON_HARD_DECLINE)


def test_stolen_card_normalization_and_whitespace() -> None:
    """Case-insensitive and whitespace-tolerant matching for hard decline."""
    _check("is_hard_decline with mixed case", is_hard_decline("  Stolen_Card_Decline  "))
    _check("is_hard_decline with lowercase", is_hard_decline("stolen_card_decline"))
    _check("is_hard_decline with None is False", not is_hard_decline(None))
    _check("is_hard_decline with empty string is False", not is_hard_decline(""))
    _check("is_hard_decline with insufficient_funds is False", not is_hard_decline("insufficient_funds"))


async def test_stolen_card_blocks_content_and_execute() -> None:
    """3. stolen_card_decline must never reach automated email/payment-link execution."""
    mock_db = MagicMock()
    nodes = RecoveryAgentNodes(mock_db, uuid4())

    hard_state: RecoveryState = {
        "case_id": str(uuid4()),
        "merchant_id": str(uuid4()),
        "case_type": "payment_failed",
        "failure_reason": "stolen_card_decline",
        "amount_at_risk": 12500,
        "currency": "INR",
        "attempt_count": 0,
        "customer_email": "fraud@example.com",
    }

    # Verify generate_content throws ValueError on hard decline
    content_threw = False
    try:
        await nodes.generate_content(hard_state)
    except ValueError as exc:
        content_threw = True
        _check("generate_content error mentions policy violation", "policy violation" in str(exc).lower())
    _check("generate_content refuses hard decline", content_threw)

    # Verify execute throws ValueError on hard decline
    execute_threw = False
    try:
        await nodes.execute(hard_state)
    except ValueError as exc:
        execute_threw = True
        _check("execute error mentions policy violation", "policy violation" in str(exc).lower())
    _check("execute refuses hard decline", execute_threw)


def test_soft_decline_eligible_for_automated_recovery() -> None:
    """4. insufficient_funds / soft_decline + valid email strategy -> eligible for automated recovery."""
    decision = evaluate_recovery_decision(
        failure_reason="insufficient_funds",
        raw_action="email",
        raw_channel="email",
        confidence=0.85,
        confidence_threshold=0.55,
    )
    _check("soft_decline + high conf -> effective_action is email", decision.effective_action == "email")
    _check("soft_decline + high conf -> escalated is False", decision.escalated is False)
    _check("soft_decline + high conf -> route is generate_content", decision.route == "generate_content")
    _check("soft_decline + high conf -> decision_source is llm", decision.decision_source == DECISION_SOURCE_LLM)
    _check("soft_decline + high conf -> policy_reason is None", decision.policy_reason is None)


def test_abandoned_checkout_eligible_for_automated_recovery() -> None:
    """5. abandoned_checkout + valid strategy -> eligible for automated recovery."""
    decision = evaluate_recovery_decision(
        failure_reason="checkout_abandoned",
        raw_action="email",
        raw_channel="email",
        confidence=0.75,
        confidence_threshold=0.55,
    )
    _check("abandoned_checkout + high conf -> effective_action is email", decision.effective_action == "email")
    _check("abandoned_checkout + high conf -> escalated is False", decision.escalated is False)
    _check("abandoned_checkout + high conf -> route is generate_content", decision.route == "generate_content")
    _check("abandoned_checkout + high conf -> decision_source is llm", decision.decision_source == DECISION_SOURCE_LLM)


def test_overdue_invoice_eligible_for_automated_recovery() -> None:
    """6. overdue_invoice + valid strategy -> eligible for automated recovery."""
    decision = evaluate_recovery_decision(
        failure_reason="invoice_unpaid_30_days",
        raw_action="email",
        raw_channel="email",
        confidence=0.80,
        confidence_threshold=0.55,
    )
    _check("overdue_invoice + high conf -> effective_action is email", decision.effective_action == "email")
    _check("overdue_invoice + high conf -> escalated is False", decision.escalated is False)
    _check("overdue_invoice + high conf -> route is generate_content", decision.route == "generate_content")
    _check("overdue_invoice + high conf -> decision_source is llm", decision.decision_source == DECISION_SOURCE_LLM)


def test_existing_confidence_guardrail_continues_working() -> None:
    """7. Low confidence (< threshold) on recoverable scenarios escalates with decision_source=llm."""
    decision = evaluate_recovery_decision(
        failure_reason="insufficient_funds",
        raw_action="email",
        raw_channel="email",
        confidence=0.40,
        confidence_threshold=0.55,
    )
    _check("low confidence soft_decline -> effective_action is escalate", decision.effective_action == "escalate")
    _check("low confidence soft_decline -> escalated is True", decision.escalated is True)
    _check("low confidence soft_decline -> route is escalate", decision.route == "escalate")
    _check("low confidence soft_decline -> decision_source is llm", decision.decision_source == DECISION_SOURCE_LLM)
    _check("low confidence soft_decline -> policy_reason is low_confidence", decision.policy_reason == POLICY_REASON_LOW_CONFIDENCE)


async def test_node_strategize_override_integration() -> None:
    """Test RecoveryAgentNodes.strategize applying policy when LLM returns email for stolen card."""
    mock_db = MagicMock()
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()

    nodes = RecoveryAgentNodes(mock_db, uuid4())

    fake_case_id = str(uuid4())
    state: RecoveryState = {
        "case_id": fake_case_id,
        "merchant_id": str(uuid4()),
        "case_type": "payment_failed",
        "failure_reason": "stolen_card_decline",
        "amount_at_risk": 20000,
        "currency": "INR",
        "attempt_count": 0,
        "triage": {"category": "hard_decline", "likely_cause": "stolen card"},
    }

    # Mock Gemini call_json to simulate LLM hallucinating high confidence email
    with patch("app.agent.nodes.call_json", new_callable=AsyncMock) as mock_gemini, \
         patch.object(nodes, "_log", new_callable=AsyncMock) as mock_log:
        mock_gemini.return_value = {
            "action_type": "email",
            "channel": "email",
            "timing": "immediate",
            "tone": "informational",
            "confidence": 0.92,
            "reasoning": "Send email asking to update card",
        }

        result = await nodes.strategize(state)

        _check("node strategize route is escalate", result["route"] == "escalate")
        _check("node strategize decision_source is policy", result["decision_source"] == DECISION_SOURCE_POLICY)
        _check("node strategize policy_reason recorded", result["policy_reason"] == POLICY_REASON_HARD_DECLINE)
        _check("strategy dictionary contains effective_action escalate", result["strategy"]["effective_action"] == "escalate")
        _check("strategy dictionary contains decision_source policy", result["strategy"]["decision_source"] == DECISION_SOURCE_POLICY)


def main() -> None:
    print("=== Running Policy Guard Unit Tests ===")
    test_stolen_card_high_confidence_escalates()
    test_stolen_card_low_confidence_escalates()
    test_stolen_card_normalization_and_whitespace()
    asyncio.run(test_stolen_card_blocks_content_and_execute())
    test_soft_decline_eligible_for_automated_recovery()
    test_abandoned_checkout_eligible_for_automated_recovery()
    test_overdue_invoice_eligible_for_automated_recovery()
    test_existing_confidence_guardrail_continues_working()
    asyncio.run(test_node_strategize_override_integration())
    print("\nALL POLICY GUARD TESTS PASSED!")


if __name__ == "__main__":
    main()
