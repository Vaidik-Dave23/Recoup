from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.db.models.merchant_user import MerchantUser
from app.db.models.recovery_case import RecoveryCase
from app.db.models.ai_investigation import AIInvestigation
from app.db.models.recovery_action import RecoveryAction
from app.db.models.recovery_outcome import RecoveryOutcome
from app.db.models.escalation import Escalation

router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit"],
)

CurrentUser = Annotated[
    MerchantUser,
    Depends(get_current_user),
]

DBSession = Annotated[
    AsyncSession,
    Depends(get_db),
]


@router.get("")
async def get_audit_logs(
    current_user: CurrentUser,
    db: DBSession,
    case_id: UUID | None = None,
    limit: int = 100,
):
    merchant_id = current_user.merchant_id

    # 1. Fetch cases
    cases_stmt = (
        select(RecoveryCase)
        .where(RecoveryCase.merchant_id == merchant_id)
    )
    if case_id is not None:
        cases_stmt = cases_stmt.where(RecoveryCase.id == case_id)
    cases_stmt = cases_stmt.order_by(RecoveryCase.created_at.desc()).limit(limit)
    cases = (await db.execute(cases_stmt)).scalars().all()

    # 2. Fetch AI investigations (capturing Gemini inputs, raw responses, and reasoning)
    invs_stmt = (
        select(AIInvestigation)
        .join(RecoveryCase, AIInvestigation.case_id == RecoveryCase.id)
        .where(RecoveryCase.merchant_id == merchant_id)
    )
    if case_id is not None:
        invs_stmt = invs_stmt.where(AIInvestigation.case_id == case_id)
    invs_stmt = invs_stmt.order_by(AIInvestigation.created_at.desc()).limit(limit)
    invs = (await db.execute(invs_stmt)).scalars().all()

    # 3. Fetch actions (capturing payment link refs and execution statuses)
    actions_stmt = (
        select(RecoveryAction)
        .join(RecoveryCase, RecoveryAction.case_id == RecoveryCase.id)
        .where(RecoveryCase.merchant_id == merchant_id)
    )
    if case_id is not None:
        actions_stmt = actions_stmt.where(RecoveryAction.case_id == case_id)
    actions_stmt = actions_stmt.order_by(RecoveryAction.created_at.desc()).limit(limit)
    actions = (await db.execute(actions_stmt)).scalars().all()

    # 4. Fetch outcomes
    outcomes_stmt = (
        select(RecoveryOutcome)
        .join(RecoveryCase, RecoveryOutcome.case_id == RecoveryCase.id)
        .where(RecoveryCase.merchant_id == merchant_id)
    )
    if case_id is not None:
        outcomes_stmt = outcomes_stmt.where(RecoveryOutcome.case_id == case_id)
    outcomes_stmt = outcomes_stmt.order_by(RecoveryOutcome.created_at.desc()).limit(limit)
    outcomes = (await db.execute(outcomes_stmt)).scalars().all()

    # 5. Fetch escalations
    escs_stmt = (
        select(Escalation)
        .join(RecoveryCase, Escalation.case_id == RecoveryCase.id)
        .where(RecoveryCase.merchant_id == merchant_id)
    )
    if case_id is not None:
        escs_stmt = escs_stmt.where(Escalation.case_id == case_id)
    escs_stmt = escs_stmt.order_by(Escalation.created_at.desc()).limit(limit)
    escs = (await db.execute(escs_stmt)).scalars().all()

    logs = []

    for c in cases:
        logs.append(
            {
                "timestamp": c.created_at,
                "actor": "System / Razorpay",
                "action": "CASE_CREATED",
                "entity": "Case",
                "entity_id": str(c.id),
                "status": c.status,
                "metadata": {
                    "case_id": str(c.id),
                    "case_type": c.case_type,
                    "amount": c.amount_at_risk,
                    "currency": c.currency,
                    "failure_reason": c.failure_reason,
                    "stage": c.stage,
                    "attempt_count": c.attempt_count,
                },
            }
        )

    for i in invs:
        resp = i.response_payload or {}
        inp = i.input_payload or {}
        logs.append(
            {
                "timestamp": i.created_at,
                "actor": f"AI Recovery Agent ({i.model_name or 'Gemini'})",
                "action": f"AI_INVESTIGATION_{i.node_name.upper()}",
                "entity": "AI Investigation",
                "entity_id": str(i.id),
                "status": "completed",
                "metadata": {
                    "case_id": str(i.case_id),
                    "node_name": i.node_name,
                    "model_name": i.model_name,
                    "confidence": float(i.confidence) if i.confidence is not None else None,
                    "decision_source": resp.get("decision_source") or ("policy" if i.node_name == "triage" and "stolen_card" in str(inp) else "llm"),
                    "policy_reason": resp.get("policy_reason"),
                    "reasoning": resp.get("reasoning") or resp.get("summary") or resp.get("likely_cause") or "",
                    "recommended_action": resp.get("action_type") or resp.get("effective_action") or "",
                    "input_payload": inp,
                    "raw_inputs": inp,
                    "response_payload": resp,
                    "raw_outputs": resp,
                    "razorpay_payment_link_id": resp.get("payment_link_id"),
                    "razorpay_payment_link_url": resp.get("payment_link_url"),
                    "razorpay_link_created": resp.get("payment_link_created"),
                    "razorpay_link_error": resp.get("payment_link_error"),
                },
            }
        )

    for a in actions:
        logs.append(
            {
                "timestamp": a.created_at,
                "actor": "AI Recovery Agent",
                "action": "ACTION_EXECUTED",
                "entity": "Recovery Action",
                "entity_id": str(a.id),
                "status": a.status,
                "metadata": {
                    "case_id": str(a.case_id),
                    "investigation_id": str(a.investigation_id) if a.investigation_id else None,
                    "action_type": a.action_type,
                    "channel": a.channel,
                    "subject": a.subject,
                    "message_body": a.message_body,
                    "provider_ref": a.provider_ref,
                    "sent_at": a.sent_at.isoformat() if a.sent_at else None,
                },
            }
        )

    for o in outcomes:
        logs.append(
            {
                "timestamp": o.created_at,
                "actor": "System / Razorpay",
                "action": "OUTCOME_RECORDED",
                "entity": "Recovery Outcome",
                "entity_id": str(o.id),
                "status": "recovered" if o.recovered else "failed",
                "metadata": {
                    "case_id": str(o.case_id),
                    "action_id": str(o.action_id),
                    "recovered": o.recovered,
                    "amount_recovered": o.amount_recovered,
                    "recovered_at": o.recovered_at.isoformat() if o.recovered_at else None,
                    "notes": o.notes,
                },
            }
        )

    for e in escs:
        logs.append(
            {
                "timestamp": e.created_at,
                "actor": "AI Recovery Agent",
                "action": "CASE_ESCALATED",
                "entity": "Escalation",
                "entity_id": str(e.id),
                "status": e.status,
                "metadata": {
                    "case_id": str(e.case_id),
                    "priority": e.priority,
                    "reason": e.reason,
                    "summary": e.summary,
                    "notes": e.summary,
                },
            }
        )

    # Sort logs chronologically descending
    logs.sort(key=lambda x: x["timestamp"], reverse=True)

    return logs[:limit]
