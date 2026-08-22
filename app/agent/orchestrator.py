"""Entrypoints for first-pass and post-outcome recovery-agent runs."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.graph import build_first_pass_graph, build_retry_graph
from app.agent.nodes import RecoveryAgentNodes, resolve_customer_contact
from app.agent.state import RecoveryState
from app.db.models.enums import RecoveryCaseStatus, RecoveryStage
from app.db.models.escalation import Escalation
from app.db.models.recovery_case import RecoveryCase
from app.services.recovery_case_service import get_recovery_case


async def _load_case(db: AsyncSession, merchant_id: UUID, case_id: UUID) -> RecoveryCase:
    case = await get_recovery_case(db, merchant_id, case_id)
    if case is None:
        raise ValueError("Recovery case not found")
    return case


async def _initial_state(db: AsyncSession, merchant_id: UUID, case: RecoveryCase) -> RecoveryState:
    email, name = await resolve_customer_contact(
        db, merchant_id, str(case.payment_id) if case.payment_id else None
    )
    return RecoveryState(
        case_id=str(case.id), merchant_id=str(merchant_id),
        payment_id=str(case.payment_id) if case.payment_id else None,
        case_type=case.case_type, failure_reason=case.failure_reason,
        amount_at_risk=case.amount_at_risk, currency=case.currency,
        attempt_count=case.attempt_count, customer_email=email, customer_name=name,
        escalated=False,
    )


async def run_case(db: AsyncSession, merchant_id: UUID, case_id: UUID) -> RecoveryState:
    case = await _load_case(db, merchant_id, case_id)
    final_state = await build_first_pass_graph(db, merchant_id).ainvoke(
        await _initial_state(db, merchant_id, case)
    )
    case.stage = RecoveryStage.ESCALATED if final_state.get("escalated") else RecoveryStage.MESSAGING
    await db.commit()
    return final_state


async def resume_after_outcome(
    db: AsyncSession, merchant_id: UUID, case_id: UUID
) -> RecoveryState | None:
    case = await _load_case(db, merchant_id, case_id)
    if case.status == RecoveryCaseStatus.RECOVERED:
        return None
    state = await _initial_state(db, merchant_id, case)
    if case.status == RecoveryCaseStatus.ESCALATED:
        existing = await db.scalar(
            select(Escalation)
            .where(Escalation.case_id == case.id, Escalation.status == "open")
            .order_by(Escalation.created_at.desc())
            .limit(1)
        )
        if existing is not None:
            return {
                **state,
                "escalated": True,
                "escalation_id": str(existing.id),
            }
        result = await RecoveryAgentNodes(db, merchant_id).escalate(
            state, trigger="attempts_exhausted"
        )
        return {**state, **result}
    final_state = await build_retry_graph(db, merchant_id).ainvoke(state)
    case.stage = RecoveryStage.ESCALATED if final_state.get("escalated") else RecoveryStage.RETRY
    await db.commit()
    return final_state
