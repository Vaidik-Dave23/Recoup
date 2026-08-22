from typing import Annotated
from fastapi import APIRouter, Depends
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
):
    merchant_id = current_user.merchant_id

    # 1. Fetch recent cases
    cases_stmt = (
        select(RecoveryCase)
        .where(RecoveryCase.merchant_id == merchant_id)
        .order_by(RecoveryCase.created_at.desc())
        .limit(20)
    )
    cases = (await db.execute(cases_stmt)).scalars().all()

    # 2. Fetch recent investigations
    invs_stmt = (
        select(AIInvestigation)
        .join(RecoveryCase, AIInvestigation.case_id == RecoveryCase.id)
        .where(RecoveryCase.merchant_id == merchant_id)
        .order_by(AIInvestigation.created_at.desc())
        .limit(20)
    )
    invs = (await db.execute(invs_stmt)).scalars().all()

    # 3. Fetch recent actions
    actions_stmt = (
        select(RecoveryAction)
        .join(RecoveryCase, RecoveryAction.case_id == RecoveryCase.id)
        .where(RecoveryCase.merchant_id == merchant_id)
        .order_by(RecoveryAction.created_at.desc())
        .limit(20)
    )
    actions = (await db.execute(actions_stmt)).scalars().all()

    # 4. Fetch recent outcomes
    outcomes_stmt = (
        select(RecoveryOutcome)
        .join(RecoveryCase, RecoveryOutcome.case_id == RecoveryCase.id)
        .where(RecoveryCase.merchant_id == merchant_id)
        .order_by(RecoveryOutcome.created_at.desc())
        .limit(20)
    )
    outcomes = (await db.execute(outcomes_stmt)).scalars().all()

    # 5. Fetch recent escalations
    escs_stmt = (
        select(Escalation)
        .join(RecoveryCase, Escalation.case_id == RecoveryCase.id)
        .where(RecoveryCase.merchant_id == merchant_id)
        .order_by(Escalation.created_at.desc())
        .limit(20)
    )
    escs = (await db.execute(escs_stmt)).scalars().all()

    # Merge and format
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
                    "case_type": c.case_type,
                    "amount": c.amount_at_risk,
                    "currency": c.currency,
                    "failure_reason": c.failure_reason,
                },
            }
        )

    for i in invs:
        logs.append(
            {
                "timestamp": i.created_at,
                "actor": "AI Recovery Agent",
                "action": "AI_INVESTIGATION",
                "entity": "AI Investigation",
                "entity_id": str(i.id),
                "status": "completed",
                "metadata": {
                    "case_id": str(i.case_id),
                    "node_name": i.node_name,
                    "model_name": i.model_name,
                    "confidence": float(i.confidence)
                    if i.confidence
                    else None,
                    "finding": i.response_payload.get("finding", ""),
                    "recommended_action": i.response_payload.get(
                        "recommended_action", ""
                    ),
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
                    "action_type": a.action_type,
                    "channel": a.channel,
                    "subject": a.subject,
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
                    "recovered": o.recovered,
                    "amount_recovered": o.amount_recovered,
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
                    "notes": e.notes,
                },
            }
        )

    # Sort logs by timestamp descending
    logs.sort(key=lambda x: x["timestamp"], reverse=True)

    return logs[:50]
