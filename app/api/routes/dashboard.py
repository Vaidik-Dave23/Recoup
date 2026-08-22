from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.db.models.merchant_user import MerchantUser
from app.db.models.recovery_case import RecoveryCase
from app.db.models.recovery_outcome import RecoveryOutcome
from app.db.models.recovery_action import RecoveryAction
from app.db.models.enums import RecoveryCaseStatus

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)

CurrentUser = Annotated[
    MerchantUser,
    Depends(get_current_user),
]

DBSession = Annotated[
    AsyncSession,
    Depends(get_db),
]


@router.get("/overview")
async def get_overview(
    current_user: CurrentUser,
    db: DBSession,
):
    merchant_id = current_user.merchant_id

    # 1. KPIs
    # Active cases count
    active_stmt = select(func.count(RecoveryCase.id)).where(
        RecoveryCase.merchant_id == merchant_id,
        RecoveryCase.status == RecoveryCaseStatus.IN_PROGRESS,
    )
    active_count = (await db.execute(active_stmt)).scalar() or 0

    # Total cases count
    total_stmt = select(func.count(RecoveryCase.id)).where(
        RecoveryCase.merchant_id == merchant_id
    )
    total_count = (await db.execute(total_stmt)).scalar() or 0

    # Recovered count
    recovered_stmt = select(func.count(RecoveryCase.id)).where(
        RecoveryCase.merchant_id == merchant_id,
        RecoveryCase.status == RecoveryCaseStatus.RECOVERED,
    )
    recovered_count = (await db.execute(recovered_stmt)).scalar() or 0

    # Total at-risk amount
    at_risk_amt_stmt = select(func.sum(RecoveryCase.amount_at_risk)).where(
        RecoveryCase.merchant_id == merchant_id,
        RecoveryCase.status == RecoveryCaseStatus.IN_PROGRESS,
    )
    at_risk_amount = (await db.execute(at_risk_amt_stmt)).scalar() or 0

    # Total recovered amount
    recovered_amt_stmt = select(
        func.sum(RecoveryOutcome.amount_recovered)
    ).where(
        RecoveryCase.merchant_id == merchant_id,
        RecoveryOutcome.case_id == RecoveryCase.id,
        RecoveryOutcome.recovered == True,
    )
    recovered_amount = (await db.execute(recovered_amt_stmt)).scalar() or 0

    # Recovery rate (percentage)
    recovery_rate = (
        (recovered_count / total_count * 100) if total_count > 0 else 0
    )

    # 2. Priority queue: Top at-risk cases in_progress
    pq_stmt = (
        select(RecoveryCase)
        .where(
            RecoveryCase.merchant_id == merchant_id,
            RecoveryCase.status == RecoveryCaseStatus.IN_PROGRESS,
        )
        .order_by(RecoveryCase.amount_at_risk.desc())
        .limit(5)
    )
    pq_result = await db.execute(pq_stmt)
    pq_cases = pq_result.scalars().all()

    # 3. Recent activity: Recent actions
    actions_stmt = (
        select(RecoveryAction)
        .join(RecoveryCase, RecoveryAction.case_id == RecoveryCase.id)
        .where(RecoveryCase.merchant_id == merchant_id)
        .order_by(RecoveryAction.created_at.desc())
        .limit(5)
    )
    actions_result = await db.execute(actions_stmt)
    recent_actions = actions_result.scalars().all()

    return {
        "kpis": {
            "active_cases": active_count,
            "total_cases": total_count,
            "recovered_cases": recovered_count,
            "amount_at_risk": int(at_risk_amount),
            "amount_recovered": int(recovered_amount),
            "recovery_rate": round(recovery_rate, 1),
        },
        "priority_queue": [
            {
                "id": str(c.id),
                "case_type": c.case_type,
                "failure_reason": c.failure_reason,
                "amount_at_risk": c.amount_at_risk,
                "currency": c.currency,
                "stage": c.stage,
                "status": c.status,
                "created_at": c.created_at,
            }
            for c in pq_cases
        ],
        "recent_activity": [
            {
                "id": str(a.id),
                "case_id": str(a.case_id),
                "action_type": a.action_type,
                "channel": a.channel,
                "status": a.status,
                "created_at": a.created_at,
            }
            for a in recent_actions
        ],
    }
