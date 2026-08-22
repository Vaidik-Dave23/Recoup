from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.enums import RecoveryCaseStatus, RecoveryStage
from app.db.models.recovery_action import RecoveryAction
from app.db.models.recovery_case import RecoveryCase
from app.db.models.recovery_outcome import RecoveryOutcome
from app.schemas.recovery_outcome import RecoveryOutcomeCreate


async def create_recovery_outcome(
    db: AsyncSession,
    merchant_id: UUID,
    data: RecoveryOutcomeCreate,
) -> RecoveryOutcome:
    result = await db.execute(
        select(RecoveryCase).where(
            RecoveryCase.id == data.case_id,
            RecoveryCase.merchant_id == merchant_id,
        )
    )

    case = result.scalar_one_or_none()

    if case is None:
        raise ValueError("Recovery case not found")

    result = await db.execute(
        select(RecoveryAction).where(
            RecoveryAction.id == data.action_id,
            RecoveryAction.case_id == case.id,
        )
    )

    action = result.scalar_one_or_none()

    if action is None:
        raise ValueError("Recovery action not found")

    result = await db.execute(
        select(RecoveryOutcome).where(
            RecoveryOutcome.action_id == action.id
        )
    )

    if result.scalar_one_or_none() is not None:
        raise ValueError(
            "Outcome already exists for this action"
        )

    if data.amount_recovered > case.amount_at_risk:
        raise ValueError(
            "Recovered amount cannot exceed amount at risk"
        )

    recovered_at = (
        datetime.now(timezone.utc)
        if data.recovered
        else None
    )

    outcome = RecoveryOutcome(
        case_id=case.id,
        action_id=action.id,
        recovered=data.recovered,
        amount_recovered=data.amount_recovered,
        recovered_at=recovered_at,
        notes=data.notes,
    )

    db.add(outcome)

    if data.recovered:
        case.financial_impact = (
            case.financial_impact + data.amount_recovered
        )
        case.status = RecoveryCaseStatus.RECOVERED
        case.stage = RecoveryStage.RECOVERED

    else:
        case.attempt_count += 1

        if case.attempt_count >= 3:
            case.status = "escalated"
            case.stage = "escalated"
        else:
            case.status = "in_progress"

    await db.commit()
    await db.refresh(outcome)

    return outcome


async def get_case_outcomes(
    db: AsyncSession,
    merchant_id: UUID,
    case_id: UUID,
) -> list[RecoveryOutcome]:
    result = await db.execute(
        select(RecoveryCase).where(
            RecoveryCase.id == case_id,
            RecoveryCase.merchant_id == merchant_id,
        )
    )

    if result.scalar_one_or_none() is None:
        raise ValueError("Recovery case not found")

    result = await db.execute(
        select(RecoveryOutcome)
        .where(RecoveryOutcome.case_id == case_id)
        .order_by(RecoveryOutcome.created_at.asc())
    )

    return list(result.scalars().all())


async def get_recovery_outcome(
    db: AsyncSession,
    merchant_id: UUID,
    outcome_id: UUID,
) -> RecoveryOutcome | None:
    result = await db.execute(
        select(RecoveryOutcome)
        .join(
            RecoveryCase,
            RecoveryCase.id == RecoveryOutcome.case_id,
        )
        .where(
            RecoveryOutcome.id == outcome_id,
            RecoveryCase.merchant_id == merchant_id,
        )
    )

    return result.scalar_one_or_none()
