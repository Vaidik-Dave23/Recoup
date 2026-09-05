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
from app.agent.policy import evaluate_recovery_decision, is_hard_decline
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
        amount_fmt = f"{state['amount_at_risk'] / 100:.2f}"
        prompt = prompts.TRIAGE_USER.format(
            case_type=state["case_type"],
            failure_reason=state["failure_reason"],
            amount_at_risk=amount_fmt,
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
        amount_fmt = f"{state['amount_at_risk'] / 100:.2f}"
        prompt = prompts.STRATEGIZE_USER.format(
            triage_json=json.dumps(state.get("triage") or {}),
            case_type=state["case_type"],
            amount_at_risk=amount_fmt,
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

        # Apply deterministic backend safety policy (single source of truth)
        policy_decision = evaluate_recovery_decision(
            failure_reason=state.get("failure_reason"),
            raw_action=result.get("action_type"),
            raw_channel=result.get("channel"),
            confidence=confidence,
            confidence_threshold=settings.recovery_confidence_threshold,
        )

        # Hard guarantee, not just a prompt instruction: only "email" has a
        # live sending provider wired up (see execute node / email_sender.py).
        if result.get("action_type") != "email" or result.get("channel") != "email":
            result["_channel_normalized_from"] = {
                "action_type": result.get("action_type"),
                "channel": result.get("channel"),
            }
            result["action_type"] = "email"
            result["channel"] = "email"

        # Record policy audit information in strategy result
        result["decision_source"] = policy_decision.decision_source
        if policy_decision.policy_reason:
            result["policy_reason"] = policy_decision.policy_reason
        result["effective_action"] = policy_decision.effective_action

        await self._log(
            state["case_id"],
            InvestigationNode.STRATEGIZE,
            {"triage": state.get("triage")},
            result,
            confidence=confidence,
        )
        return {
            "strategy": result,
            "route": policy_decision.route,
            "decision_source": policy_decision.decision_source,
            "policy_reason": policy_decision.policy_reason,
        }

    async def generate_content(self, state: RecoveryState) -> dict[str, Any]:
        if is_hard_decline(state.get("failure_reason")):
            raise ValueError(
                f"Policy violation: Content generation is forbidden for hard decline cases ({state.get('failure_reason')})"
            )

        # Idempotency guard: Return existing action if already created for this case
        existing_action_res = await self.db.execute(
            select(RecoveryAction)
            .where(RecoveryAction.case_id == UUID(state["case_id"]))
            .order_by(RecoveryAction.created_at.desc())
            .limit(1)
        )
        existing_action = existing_action_res.scalar_one_or_none()
        if existing_action is not None:
            return {
                "content": state.get("content") or {},
                "action_id": str(existing_action.id),
                "action_channel": existing_action.channel,
            }

        strategy = state.get("strategy") or {}
        # Create the payment link first so we can supply it directly to the prompt
        link_result = create_recovery_payment_link(
            amount=state["amount_at_risk"],
            currency=state["currency"],
            description=f"{state['case_type']} recovery -- case {state['case_id'][:8]}",
            customer_name=state.get("customer_name"),
            customer_email=state.get("customer_email"),
            reference_id=f"{state['case_id']}-{state.get('attempt_count', 0) + 1}",
        )

        payment_link = link_result.short_url if link_result.success else "N/A"
        amount_fmt = f"{state['amount_at_risk'] / 100:.2f}"

        prompt = prompts.CONTENT_USER.format(
            channel=strategy.get("channel", "email"),
            tone=strategy.get("tone", "informational"),
            customer_name=state.get("customer_name") or "there",
            case_type=state["case_type"],
            amount_at_risk=amount_fmt,
            currency=state["currency"],
            payment_link=payment_link,
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

        content["payment_link_created"] = link_result.success
        if link_result.success:
            content["payment_link_id"] = link_result.payment_link_id
            content["payment_link_url"] = link_result.short_url
            
            # Bulletproof backup: scrub common placeholders with real values
            body = content.get("body", "")
            body = body.replace("[Your Company Name]", "Recoup")
            body = body.replace("[Company Name]", "Recoup")
            body = body.replace("[Support Email/Phone Number]", "support@recoup.com")
            body = body.replace("[Link to Payment Portal]", link_result.short_url)
            
            # If the generated text doesn't contain the payment link, append it at the end
            if link_result.short_url not in body:
                body = f"{body}\n\nPay securely here: {link_result.short_url}"
            content["body"] = body
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
        if is_hard_decline(state.get("failure_reason")):
            raise ValueError(
                f"Policy violation: Automated recovery execution is forbidden for hard decline cases ({state.get('failure_reason')})"
            )

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

        # Idempotency guard: Prevent double execution if action was already sent
        if action.status in (ActionStatus.SENT, ActionStatus.SENT.value, "sent"):
            return {
                "send_result": {
                    "success": True,
                    "provider_ref": action.provider_ref,
                    "idempotent": True,
                    "message": "Action already sent; duplicate execution blocked by idempotency guard.",
                }
            }

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

    async def escalate(self, state: RecoveryState, trigger: str = "low_confidence") -> dict[str, Any]:
        effective_trigger = state.get("policy_reason") or trigger or "low_confidence"
        amount_fmt = f"{state['amount_at_risk'] / 100:.2f}"
        prompt = prompts.ESCALATE_USER.format(
            case_type=state["case_type"],
            amount_at_risk=amount_fmt,
            currency=state["currency"],
            attempt_count=state.get("attempt_count", 0),
            triage_json=json.dumps(state.get("triage") or {}),
            strategy_json=json.dumps(state.get("strategy") or {}),
            trigger=effective_trigger,
        )
        try:
            result = await call_json(prompts.ESCALATE_SYSTEM, prompt)
        except GeminiCallError as exc:
            result = {
                "reason": effective_trigger,
                "priority": "medium",
                "summary": f"Gemini handoff generation failed: {exc}",
            }
        await self._log(state["case_id"], InvestigationNode.ESCALATE, {"trigger": effective_trigger}, result)
        escalation = await create_escalation(
            self.db,
            self.merchant_id,
            EscalationCreate(
                case_id=UUID(state["case_id"]),
                reason=result.get("reason", effective_trigger),
                priority=result.get("priority", "medium"),
                notes=result.get("summary"),
            ),
        )
        return {
            "escalated": True,
            "escalation_id": str(escalation.id),
            "decision_source": state.get("decision_source", "policy" if is_hard_decline(state.get("failure_reason")) else "llm"),
            "policy_reason": state.get("policy_reason"),
        }


async def resolve_customer_contact(
    db: AsyncSession, merchant_id: UUID, payment_id: str | None
) -> tuple[str | None, str | None]:
    email = None
    if payment_id is not None:
        result = await db.execute(
            select(Order.customer_email)
            .join(Payment, Payment.order_id == Order.id)
            .where(Payment.id == UUID(payment_id), Payment.merchant_id == merchant_id)
        )
        row = result.first()
        if row and row[0]:
            email = row[0]

    # If email is missing or an unrouteable dummy @example.com, route to merchant user's real email for testing
    if not email or email.endswith("@example.com"):
        from app.db.models.merchant_user import MerchantUser
        user_res = await db.execute(
            select(MerchantUser.email)
            .where(MerchantUser.merchant_id == merchant_id)
            .limit(1)
        )
        user_row = user_res.first()
        if user_row and user_row[0] and not user_row[0].endswith("@example.com"):
            email = user_row[0]

    return email, None