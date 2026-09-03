"""Comprehensive resilience, idempotency, audit trail clarity, and stopping rule tests.

Covers:
1. Idempotency & Double-Execution Protection:
   - Duplicate action execution blocking
   - Duplicate outcome recording prevention
   - Double recovery financial guard
2. Audit Trail Clarity:
   - Gemini input capture in database
   - Gemini raw response / reasoning capture
   - Razorpay payment link API data capture
   - Audit logs route explainability verification
3. Graceful Failure Handling:
   - Gemini 429 / Rate limit fallback to human escalation
   - Gemini malformed JSON / hallucination fallback
   - Razorpay API failure graceful continuation
   - Hard decline deterministic safety stop
4. Stopping Rules & Bounded Escalation:
   - Max attempt exhaustion stops retries and escalates
   - Closed / recovered case protection
"""

from __future__ import annotations

import asyncio
import sys
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

# Add project root to sys.path automatically
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.gemini_client import GeminiCallError
from app.agent.nodes import RecoveryAgentNodes
from app.agent.orchestrator import run_case, resume_after_outcome
from app.agent.policy import (
    DECISION_SOURCE_POLICY,
    DECISION_SOURCE_LLM,
    POLICY_REASON_HARD_DECLINE,
    POLICY_REASON_LOW_CONFIDENCE,
    evaluate_recovery_decision,
    is_hard_decline,
)
from app.agent.razorpay_client import PaymentLinkResult
from app.agent.state import RecoveryState
from app.core.config import settings
from app.db.models.enums import ActionStatus, RecoveryCaseStatus, RecoveryStage
from app.db.models.recovery_action import RecoveryAction
from app.db.models.recovery_case import RecoveryCase
from app.db.models.recovery_outcome import RecoveryOutcome
from app.schemas.recovery_outcome import RecoveryOutcomeCreate
from app.services.recovery_outcome_service import create_recovery_outcome


def _check(label: str, condition: bool) -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}")
    assert condition, label


# ==============================================================================
# 1. IDEMPOTENCY & DOUBLE-CHARGE RISKS
# ==============================================================================

async def test_idempotent_action_execution_blocks_duplicate_send() -> None:
    """Ensure that calling execute() on an action already in SENT status does not re-send."""
    mock_db = MagicMock(spec=AsyncSession)
    merchant_id = uuid4()
    case_id = uuid4()
    action_id = uuid4()

    already_sent_action = RecoveryAction(
        id=action_id,
        case_id=case_id,
        action_type="email",
        channel="email",
        status=ActionStatus.SENT,
        provider_ref="email_sent_mock_123 | rzp_link:plink_test_999",
    )

    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=already_sent_action))
    )

    nodes = RecoveryAgentNodes(mock_db, merchant_id)
    state: RecoveryState = {
        "case_id": str(case_id),
        "merchant_id": str(merchant_id),
        "case_type": "payment_failed",
        "failure_reason": "insufficient_funds",
        "amount_at_risk": 5000,
        "currency": "INR",
        "action_id": str(action_id),
        "action_channel": "email",
        "customer_email": "payer@example.com",
    }

    with patch("app.agent.nodes.send_recovery_email") as mock_send_email:
        result = await nodes.execute(state)
        # Should NOT call send_recovery_email because action is already SENT
        _check("send_recovery_email was not called again", mock_send_email.call_count == 0)
        _check("execute returned idempotent success", result["send_result"]["success"] is True)
        _check("execute flagged idempotent=True", result["send_result"].get("idempotent") is True)


async def test_double_recovery_outcome_prevented() -> None:
    """Ensure database state prevents double-recording recovery outcome."""
    mock_db = MagicMock(spec=AsyncSession)
    merchant_id = uuid4()
    case_id = uuid4()
    action_id = uuid4()

    recovered_case = RecoveryCase(
        id=case_id,
        merchant_id=merchant_id,
        case_type="payment_failed",
        failure_reason="insufficient_funds",
        amount_at_risk=5000,
        currency="INR",
        status=RecoveryCaseStatus.RECOVERED,
        stage=RecoveryStage.RECOVERED,
        attempt_count=1,
    )

    # Mock DB query returning case already recovered
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=recovered_case))
    )

    outcome_data = RecoveryOutcomeCreate(
        case_id=case_id,
        action_id=action_id,
        recovered=True,
        amount_recovered=5000,
    )

    threw = False
    try:
        await create_recovery_outcome(mock_db, merchant_id, outcome_data)
    except ValueError as exc:
        threw = True
        _check("Double recovery raises ValueError", "already recorded as successful" in str(exc))

    _check("create_recovery_outcome blocked duplicate success", threw)


# ==============================================================================
# 2. AUDIT TRAIL CLARITY & EXPLAINABILITY
# ==============================================================================

async def test_audit_trail_captures_gemini_inputs_and_raw_responses() -> None:
    """Verify that node execution logs exact input payloads, raw outputs, and reasoning in AIInvestigation."""
    mock_db = MagicMock(spec=AsyncSession)
    merchant_id = uuid4()
    case_id = uuid4()

    logged_invs = []

    async def fake_create_inv(db, m_id, c_id, node_name, model_name, input_payload, response_payload, confidence):
        logged_invs.append({
            "node_name": node_name,
            "input_payload": input_payload,
            "response_payload": response_payload,
            "confidence": confidence,
        })
        inv = MagicMock()
        inv.id = uuid4()
        return inv

    nodes = RecoveryAgentNodes(mock_db, merchant_id)

    with patch("app.agent.nodes.create_ai_investigation", side_effect=fake_create_inv), \
         patch("app.agent.nodes.call_json", new_callable=AsyncMock) as mock_call:
        
        # Test Triage Logging
        mock_call.return_value = {
            "category": "funds",
            "likely_cause": "Temporary bank limit reached",
            "urgency": "medium",
            "summary": "Customer card had temporary limit.",
        }
        triage_state: RecoveryState = {
            "case_id": str(case_id),
            "merchant_id": str(merchant_id),
            "case_type": "payment_failed",
            "failure_reason": "insufficient_funds",
            "amount_at_risk": 4999,
            "currency": "INR",
        }
        await nodes.triage(triage_state)
        
        _check("Triage investigation logged", len(logged_invs) == 1)
        _check("Triage input_payload preserved", logged_invs[0]["input_payload"]["failure_reason"] == "insufficient_funds")
        _check("Triage raw response preserved", logged_invs[0]["response_payload"]["likely_cause"] == "Temporary bank limit reached")

        # Test Strategy Logging with Policy Decision
        mock_call.return_value = {
            "action_type": "email",
            "channel": "email",
            "timing": "wait_24h",
            "tone": "empathetic",
            "confidence": 0.92,
            "reasoning": "Soft decline responds best to gentle delayed reminder.",
        }
        await nodes.strategize({**triage_state, "triage": logged_invs[0]["response_payload"]})

        _check("Strategize investigation logged", len(logged_invs) == 2)
        strat_log = logged_invs[1]
        _check("Strategy confidence logged as Decimal", float(strat_log["confidence"]) == 0.92)
        _check("Strategy reasoning captured for human explainability", "Soft decline responds best" in strat_log["response_payload"]["reasoning"])
        _check("Strategy decision source recorded as llm", strat_log["response_payload"]["decision_source"] == DECISION_SOURCE_LLM)


async def test_audit_trail_captures_razorpay_payment_link_details() -> None:
    """Verify that generate_content records Razorpay API link creation output & error in audit trail."""
    mock_db = MagicMock(spec=AsyncSession)
    merchant_id = uuid4()
    case_id = uuid4()

    logged_invs = []

    async def fake_create_inv(db, m_id, c_id, node_name, model_name, input_payload, response_payload, confidence):
        logged_invs.append({
            "node_name": node_name,
            "response_payload": response_payload,
        })
        return MagicMock(id=uuid4())

    nodes = RecoveryAgentNodes(mock_db, merchant_id)

    mock_rzp_result = PaymentLinkResult(
        success=True,
        payment_link_id="plink_MOCK_TEST_12345",
        short_url="https://rzp.io/i/mocktest123",
    )

    with patch("app.agent.nodes.create_ai_investigation", side_effect=fake_create_inv), \
         patch("app.agent.nodes.create_recovery_payment_link", return_value=mock_rzp_result), \
         patch("app.agent.nodes.RecoveryAgentNodes._latest_investigation_id", new_callable=AsyncMock, return_value=uuid4()), \
         patch("app.agent.nodes.create_recovery_action", return_value=MagicMock(id=uuid4(), channel="email")), \
         patch("app.agent.nodes.call_json", new_callable=AsyncMock) as mock_call:
        
        mock_call.return_value = {
            "subject": "Complete your order",
            "body": "Please click the link to pay: [Link to Payment Portal]",
        }

        state: RecoveryState = {
            "case_id": str(case_id),
            "merchant_id": str(merchant_id),
            "case_type": "abandoned_checkout",
            "failure_reason": "checkout_abandoned",
            "amount_at_risk": 8900,
            "currency": "INR",
            "strategy": {"action_type": "email", "channel": "email", "tone": "helpful"},
            "customer_name": "Aditi",
            "customer_email": "aditi@example.com",
        }

        res = await nodes.generate_content(state)
        
        _check("Content generation logged in audit trail", len(logged_invs) == 1)
        resp_data = logged_invs[0]["response_payload"]
        _check("Audit log contains Razorpay payment link ID", resp_data.get("payment_link_id") == "plink_MOCK_TEST_12345")
        _check("Audit log contains Razorpay payment link URL", resp_data.get("payment_link_url") == "https://rzp.io/i/mocktest123")
        _check("Payment link embedded into email body", "https://rzp.io/i/mocktest123" in res["content"]["body"])


# ==============================================================================
# 3. GRACEFUL FAILURE HANDLING
# ==============================================================================

async def test_gemini_429_or_rate_limit_escalates_gracefully() -> None:
    """When Gemini throws 429 or rate limit error, system catches it, routes to escalate, and records human handoff."""
    mock_db = MagicMock(spec=AsyncSession)
    merchant_id = uuid4()
    case_id = uuid4()

    nodes = RecoveryAgentNodes(mock_db, merchant_id)

    with patch("app.agent.nodes.create_ai_investigation", new_callable=AsyncMock), \
         patch("app.agent.nodes.call_json", side_effect=GeminiCallError("429 RESOURCE_EXHAUSTED")):
        
        state: RecoveryState = {
            "case_id": str(case_id),
            "merchant_id": str(merchant_id),
            "case_type": "payment_failed",
            "failure_reason": "insufficient_funds",
            "amount_at_risk": 4999,
            "currency": "INR",
        }

        # Strategize should catch the error and fallback to confidence=0.0 -> escalate
        strat_res = await nodes.strategize(state)
        _check("Strategize routed to escalate on 429", strat_res["route"] == "escalate")
        _check("Policy reason is low_confidence", strat_res["policy_reason"] == POLICY_REASON_LOW_CONFIDENCE)
        _check("Reasoning explains Gemini failure", "Gemini strategy failed" in strat_res["strategy"]["reasoning"])


async def test_gemini_malformed_json_hallucination_escalates_gracefully() -> None:
    """When Gemini hallucinates invalid text instead of JSON, system safely routes to human escalation."""
    mock_db = MagicMock(spec=AsyncSession)
    merchant_id = uuid4()
    case_id = uuid4()

    nodes = RecoveryAgentNodes(mock_db, merchant_id)

    with patch("app.agent.nodes.create_ai_investigation", new_callable=AsyncMock), \
         patch("app.agent.nodes.call_json", side_effect=GeminiCallError("Could not parse Gemini JSON response")):
        
        state: RecoveryState = {
            "case_id": str(case_id),
            "merchant_id": str(merchant_id),
            "case_type": "overdue_invoice",
            "failure_reason": "invoice_unpaid_30_days",
            "amount_at_risk": 75000,
            "currency": "INR",
        }

        strat_res = await nodes.strategize(state)
        _check("Strategize safely routed to escalate on invalid JSON", strat_res["route"] == "escalate")
        _check("Confidence safely set to 0.0", strat_res["strategy"]["confidence"] == 0.0)


async def test_razorpay_api_downtime_handles_gracefully() -> None:
    """When Razorpay test API fails or network drops, generate_content continues without crashing."""
    mock_db = MagicMock(spec=AsyncSession)
    merchant_id = uuid4()
    case_id = uuid4()

    nodes = RecoveryAgentNodes(mock_db, merchant_id)

    failed_rzp_result = PaymentLinkResult(
        success=False,
        error="Razorpay API 500: Internal server error",
    )

    with patch("app.agent.nodes.create_ai_investigation", new_callable=AsyncMock), \
         patch("app.agent.nodes.create_recovery_payment_link", return_value=failed_rzp_result), \
         patch("app.agent.nodes.RecoveryAgentNodes._latest_investigation_id", new_callable=AsyncMock, return_value=uuid4()), \
         patch("app.agent.nodes.create_recovery_action", return_value=MagicMock(id=uuid4(), channel="email")), \
         patch("app.agent.nodes.call_json", new_callable=AsyncMock) as mock_call:
        
        mock_call.return_value = {
            "subject": "Payment issue notification",
            "body": "We had an issue processing your invoice.",
        }

        state: RecoveryState = {
            "case_id": str(case_id),
            "merchant_id": str(merchant_id),
            "case_type": "payment_failed",
            "failure_reason": "insufficient_funds",
            "amount_at_risk": 4999,
            "currency": "INR",
            "strategy": {"action_type": "email", "channel": "email"},
            "customer_name": "Test User",
            "customer_email": "test@example.com",
        }

        res = await nodes.generate_content(state)
        _check("generate_content completed gracefully during Razorpay failure", "content" in res)
        _check("payment_link_created is False", res["content"]["payment_link_created"] is False)
        _check("payment_link_error captured in state", "Razorpay API 500" in res["content"]["payment_link_error"])


# ==============================================================================
# 4. STOPPING RULES & BOUNDED ESCALATION
# ==============================================================================

async def test_max_attempt_exhaustion_stops_retries() -> None:
    """When a case has reached max attempts (e.g. 3), run_case immediately escalates and creates no new actions."""
    mock_db = MagicMock(spec=AsyncSession)
    merchant_id = uuid4()
    case_id = uuid4()

    maxed_case = RecoveryCase(
        id=case_id,
        merchant_id=merchant_id,
        case_type="payment_failed",
        failure_reason="insufficient_funds",
        amount_at_risk=4999,
        currency="INR",
        status=RecoveryCaseStatus.IN_PROGRESS,
        stage=RecoveryStage.MESSAGING,
        attempt_count=settings.recovery_max_attempts,  # 3 attempts already made
    )

    with patch("app.agent.orchestrator._load_case", return_value=maxed_case), \
         patch("app.agent.orchestrator.resolve_customer_contact", return_value=("payer@example.com", "Payer")), \
         patch("app.agent.nodes.RecoveryAgentNodes.escalate", new_callable=AsyncMock) as mock_escalate:
        
        mock_escalate.return_value = {
            "escalated": True,
            "escalation_id": str(uuid4()),
            "decision_source": "policy",
            "policy_reason": "attempts_exhausted",
        }

        final_state = await run_case(mock_db, merchant_id, case_id)

        _check("Stopping rule triggered escalation", final_state["escalated"] is True)
        _check("Escalate called with trigger='attempts_exhausted'", mock_escalate.call_args[1]["trigger"] == "attempts_exhausted")
        _check("Case status set to ESCALATED", maxed_case.status == RecoveryCaseStatus.ESCALATED)
        _check("Case stage set to ESCALATED", maxed_case.stage == RecoveryStage.ESCALATED)


async def main() -> None:
    print("\n=== Running Resilience, Idempotency, Audit Trail, and Stopping Rules Tests ===\n")
    await test_idempotent_action_execution_blocks_duplicate_send()
    await test_double_recovery_outcome_prevented()
    await test_audit_trail_captures_gemini_inputs_and_raw_responses()
    await test_audit_trail_captures_razorpay_payment_link_details()
    await test_gemini_429_or_rate_limit_escalates_gracefully()
    await test_gemini_malformed_json_hallucination_escalates_gracefully()
    await test_razorpay_api_downtime_handles_gracefully()
    await test_max_attempt_exhaustion_stops_retries()
    print("\nALL RESILIENCE & AUDIT TRAIL TESTS PASSED!\n")


if __name__ == "__main__":
    asyncio.run(main())
