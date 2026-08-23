"""Gemini-backed nodes for the recovery orchestration graph."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import prompts
from app.agent.email_sender import send_recovery_email
from app.agent.gemini_client import GeminiCallError, call_json
from app.agent.razorpay_client import create_recovery_payment_link
from app.agent.state import RecoveryState
from app.core.config import settings
from app.db.models.ai_investigation import AIInvestigation
from app.db.models.enums import ActionStatus, InvestigationNode
from app.db.models.order import Order
from app.db.models.payment import Payment
from app.db.models.recovery_action import RecoveryAction
from app.schemas.escalation import EscalationCreate
from app.schemas.recovery_action import RecoveryActionCreate
from app.services.ai_investigation_service import create_ai_investigation
from app.services.escalation_service import create_escalation
from app.services.recovery_action_service import create_recovery_action


class RecoveryAgentNodes:
    def __init__(self, db: AsyncSession, merchant_id: UUID):
        self.db = db
        self.merchant_id = merchant_id

    async def _log(
        self,
        case_id: str,
        node_name: InvestigationNode,
        input_payload: dict[str, Any] | None,
        response_payload: dict[str, Any],
        confidence: float | None = None,
    ) -> None:
        await create_ai_investigation(
            self.db,
            self.merchant_id,
            UUID(case_id),
            node_name=node_name.value,
            model_name=settings.gemini_model,
            input_payload=input_payload,
            response_payload=response_payload,
            confidence=Decimal(str(round(confidence, 4))) if confidence is not None else None,
        )

    async def triage(self, state: RecoveryState) -> dict[str, Any]:
        prompt = prompts.TRIAGE_USER.format(
            case_type=state["case_type"],
            failure_reason=state["failure_reason"],
            amount_at_risk=state["amount_at_risk"],
            currency=state["currency"],
            attempt_count=state.get("attempt_count", 0),
        )
        try:
            result = await call_json(prompts.TRIAGE_SYSTEM, prompt)
        except GeminiCallError as exc:
            result = {
                "category": "unknown",
                "likely_cause": "triage_failed",
                "urgency": "medium",
                "summary": f"Automated Gemini triage failed: {exc}",
            }
        await self._log(
            state["case_id"],
            InvestigationNode.TRIAGE,
            {"case_type": state["case_type"], "failure_reason": state["failure_reason"]},
            result,
        )
        return {"triage": result}

    async def strategize(self, state: RecoveryState) -> dict[str, Any]:
        prompt = prompts.STRATEGIZE_USER.format(
            triage_json=json.dumps(state.get("triage") or {}),
            case_type=state["case_type"],
            amount_at_risk=state["amount_at_risk"],
            currency=state["currency"],
            attempt_number=state.get("attempt_count", 0) + 1,
        )
        try:
            result = await call_json(prompts.STRATEGIZE_SYSTEM, prompt)
            confidence = float(result.get("confidence", 0.0))
        except (GeminiCallError, TypeError, ValueError) as exc:
            result = {
                "action_type": "email",
                "channel": "email",
                "timing": "immediate",
                "tone": "informational",
                "confidence": 0.0,
                "reasoning": f"Gemini strategy failed; routing to human: {exc}",
            }
            confidence = 0.0

        # Hard guarantee, not just a prompt instruction: only "email" has a
        # live sending provider wired up (see execute node / email_sender.py).
        # If the model ever ignores the prompt and picks sms/razorpay_retry,
        # normalize it here rather than silently burning a no-op attempt.
        if result.get("action_type") != "email" or result.get("channel") != "email":
            result["_channel_normalized_from"] = {
                "action_type": result.get("action_type"),
                "channel": result.get("channel"),
            }
            result["action_type"] = "email"
            result["channel"] = "email"

        await self._log(
            state["case_id"],
            InvestigationNode.STRATEGIZE,
            {"triage": state.get("triage")},
            result,
            confidence=confidence,
        )
        return {
            "strategy": result,
            "route": (
                "generate_content"
                if confidence >= settings.recovery_confidence_threshold
                else "escalate"
            ),
        }

    async def generate_content(self, state: RecoveryState) -> dict[str, Any]:
        strategy = state.get("strategy") or {}
        prompt = prompts.CONTENT_USER.format(
            channel=strategy.get("channel", "email"),
            tone=strategy.get("tone", "informational"),
            customer_name=state.get("customer_name") or "there",
            case_type=state["case_type"],
            amount_at_risk=state["amount_at_risk"],
            currency=state["currency"],
            triage_summary=(state.get("triage") or {}).get("summary", ""),
            strategy_reasoning=strategy.get("reasoning", ""),
        )
        try:
            content = await call_json(prompts.CONTENT_SYSTEM, prompt)
        except GeminiCallError as exc:
            content = {
                "subject": "Regarding your recent payment",
                "body": "We noticed an issue with your recent payment. Please contact us so we can help resolve it.",
                "_generation_error": str(exc),
            }

        # Real Razorpay test-mode payment link: gives the customer an
        # actual payable checkout instead of a stubbed retry channel.
        link_result = create_recovery_payment_link(
            amount=state["amount_at_risk"],
            currency=state["currency"],
            description=f"{state['case_type']} recovery -- case {state['case_id'][:8]}",
            customer_name=state.get("customer_name"),
            customer_email=state.get("customer_email"),
            reference_id=f"{state['case_id']}-{state.get('attempt_count', 0) + 1}",
        )
        content["payment_link_created"] = link_result.success
        if link_result.success:
            content["payment_link_id"] = link_result.payment_link_id
            content["payment_link_url"] = link_result.short_url
            content["body"] = (
                f"{content.get('body', '')}\n\nPay securely here: {link_result.short_url}"
            )
        else:
            content["payment_link_error"] = link_result.error

        await self._log(
            state["case_id"],
            InvestigationNode.GENERATE_CONTENT,
            {"strategy": strategy},
            content,
        )
        investigation_id = await self._latest_investigation_id(state["case_id"])
        action = await create_recovery_action(
            self.db,
            self.merchant_id,
            RecoveryActionCreate(
                case_id=UUID(state["case_id"]),
                investigation_id=investigation_id,
                action_type=strategy.get("action_type", "email"),
                channel=strategy.get("channel", "email"),
                subject=content.get("subject"),
                message_body=content.get("body"),
            ),
        )
        return {"content": content, "action_id": str(action.id), "action_channel": action.channel}

    async def _latest_investigation_id(self, case_id: str) -> UUID | None:
        result = await self.db.execute(
            select(AIInvestigation)
            .where(AIInvestigation.case_id == UUID(case_id))
            .order_by(AIInvestigation.created_at.desc())
            .limit(1)
        )
        row = result.scalar_one_or_none()
        return row.id if row else None

    async def execute(self, state: RecoveryState) -> dict[str, Any]:
        action_id = state.get("action_id")
        if not action_id:
            raise ValueError("Recovery action is missing")
        result = await self.db.execute(
            select(RecoveryAction).where(
                RecoveryAction.id == UUID(action_id),
                RecoveryAction.case_id == UUID(state["case_id"]),
            )
        )
        action = result.scalar_one_or_none()
        if action is None:
            raise ValueError("Recovery action disappeared before execution")

        if state.get("action_channel") == "email" and state.get("customer_email"):
            sent = send_recovery_email(
                state["customer_email"],
                (state.get("content") or {}).get("subject", ""),
                (state.get("content") or {}).get("body", ""),
            )
            send_result = {"success": sent.success, "provider_ref": sent.provider_ref, "error": sent.error}
        elif state.get("action_channel") == "email":
            send_result = {"success": False, "error": "No customer email on file"}
        else:
            send_result = {
                "success": False,
                "error": f"Channel {state.get('action_channel')} is not configured",
            }

        action.status = ActionStatus.SENT if send_result["success"] else ActionStatus.FAILED
        provider_ref = send_result.get("provider_ref")
        link_id = (state.get("content") or {}).get("payment_link_id")
        if link_id:
            provider_ref = f"{provider_ref or 'unsent'} | rzp_link:{link_id}"
        action.provider_ref = provider_ref
        if send_result["success"]:
            action.sent_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self._log(
            state["case_id"], InvestigationNode.EXECUTE,
            {"action_id": action_id, "channel": state.get("action_channel")}, send_result,
        )
        return {"send_result": send_result}

    async def escalate(self, state: RecoveryState, trigger: str) -> dict[str, Any]:
        prompt = prompts.ESCALATE_USER.format(
            case_type=state["case_type"],
            amount_at_risk=state["amount_at_risk"],
            currency=state["currency"],
            attempt_count=state.get("attempt_count", 0),
            triage_json=json.dumps(state.get("triage") or {}),
            strategy_json=json.dumps(state.get("strategy") or {}),
            trigger=trigger,
        )
        try:
            result = await call_json(prompts.ESCALATE_SYSTEM, prompt)
        except GeminiCallError as exc:
            result = {
                "reason": trigger,
                "priority": "medium",
                "summary": f"Gemini handoff generation failed: {exc}",
            }
        await self._log(state["case_id"], InvestigationNode.ESCALATE, {"trigger": trigger}, result)
        escalation = await create_escalation(
            self.db,
            self.merchant_id,
            EscalationCreate(
                case_id=UUID(state["case_id"]),
                reason=result.get("reason", trigger),
                priority=result.get("priority", "medium"),
                notes=result.get("summary"),
            ),
        )
        return {"escalated": True, "escalation_id": str(escalation.id)}


async def resolve_customer_contact(
    db: AsyncSession, merchant_id: UUID, payment_id: str | None
) -> tuple[str | None, str | None]:
    if payment_id is None:
        return None, None
    result = await db.execute(
        select(Order.customer_email)
        .join(Payment, Payment.order_id == Order.id)
        .where(Payment.id == UUID(payment_id), Payment.merchant_id == merchant_id)
    )
    row = result.first()
    return (row[0] if row else None), None