from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.escalation import Escalation
from app.db.models.recovery_case import RecoveryCase
from app.schemas.escalation import EscalationCreate, EscalationUpdate


async def create_escalation(
    db: AsyncSession,
    merchant_id: UUID,
    data: EscalationCreate,
) -> Escalation:
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
        select(Escalation).where(
            Escalation.case_id == case.id,
            Escalation.status == "open",
        )
    )

    if result.scalar_one_or_none() is not None:
        raise ValueError(
            "An active escalation already exists for this case"
        )

    escalation = Escalation(
        case_id=case.id,
        reason=data.reason,
        priority=data.priority,
        summary=data.notes or data.reason,
        status="open",
    )

    db.add(escalation)

    case.status = "escalated"
    case.stage = "escalated"

    await db.commit()
    await db.refresh(escalation)

    return escalation


async def get_escalations(
    db: AsyncSession,
    merchant_id: UUID,
) -> list[Escalation]:
    result = await db.execute(
        select(Escalation)
        .join(
            RecoveryCase,
            RecoveryCase.id == Escalation.case_id,
        )
        .where(
            RecoveryCase.merchant_id == merchant_id
        )
        .order_by(Escalation.created_at.desc())
    )

    return list(result.scalars().all())


async def get_case_escalations(
    db: AsyncSession,
    merchant_id: UUID,
    case_id: UUID,
) -> list[Escalation]:
    result = await db.execute(
        select(RecoveryCase).where(
            RecoveryCase.id == case_id,
            RecoveryCase.merchant_id == merchant_id,
        )
    )

    if result.scalar_one_or_none() is None:
        raise ValueError("Recovery case not found")

    result = await db.execute(
        select(Escalation)
        .where(Escalation.case_id == case_id)
        .order_by(Escalation.created_at.desc())
    )

    return list(result.scalars().all())


async def get_escalation(
    db: AsyncSession,
    merchant_id: UUID,
    escalation_id: UUID,
) -> Escalation | None:
    result = await db.execute(
        select(Escalation)
        .join(
            RecoveryCase,
            RecoveryCase.id == Escalation.case_id,
        )
        .where(
            Escalation.id == escalation_id,
            RecoveryCase.merchant_id == merchant_id,
        )
    )

    return result.scalar_one_or_none()


async def update_escalation(
    db: AsyncSession,
    merchant_id: UUID,
    escalation_id: UUID,
    data: EscalationUpdate,
) -> Escalation | None:
    escalation = await get_escalation(
        db,
        merchant_id,
        escalation_id,
    )

    if escalation is None:
        return None

    if data.priority is not None:
        escalation.priority = data.priority

    if data.notes is not None:
        escalation.summary = data.notes

    if data.status is not None:
        escalation.status = data.status

        if data.status == "resolved":
            escalation.resolved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(escalation)

    return escalation
