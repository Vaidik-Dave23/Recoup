from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.ai_investigation import AIInvestigation
from app.db.models.recovery_action import RecoveryAction
from app.db.models.recovery_case import RecoveryCase
from app.schemas.recovery_action import RecoveryActionCreate


async def create_recovery_action(
    db: AsyncSession,
    merchant_id: UUID,
    data: RecoveryActionCreate,
) -> RecoveryAction:
    result = await db.execute(
        select(RecoveryCase).where(
            RecoveryCase.id == data.case_id,
            RecoveryCase.merchant_id == merchant_id,
        )
    )

    case = result.scalar_one_or_none()

    if case is None:
        raise ValueError("Recovery case not found")

    if data.investigation_id is not None:
        result = await db.execute(
            select(AIInvestigation).where(
                AIInvestigation.id == data.investigation_id,
                AIInvestigation.case_id == case.id,
            )
        )

        if result.scalar_one_or_none() is None:
            raise ValueError("AI investigation not found")

    action = RecoveryAction(
        case_id=case.id,
        investigation_id=data.investigation_id,
        action_type=data.action_type,
        channel=data.channel,
        subject=data.subject,
        message_body=data.message_body,
        status="queued",
    )

    db.add(action)

    await db.commit()
    await db.refresh(action)

    return action


async def get_case_actions(
    db: AsyncSession,
    merchant_id: UUID,
    case_id: UUID,
) -> list[RecoveryAction]:
    result = await db.execute(
        select(RecoveryCase).where(
            RecoveryCase.id == case_id,
            RecoveryCase.merchant_id == merchant_id,
        )
    )

    if result.scalar_one_or_none() is None:
        raise ValueError("Recovery case not found")

    result = await db.execute(
        select(RecoveryAction)
        .where(RecoveryAction.case_id == case_id)
        .order_by(RecoveryAction.created_at.asc())
    )

    return list(result.scalars().all())


async def get_recovery_action(
    db: AsyncSession,
    merchant_id: UUID,
    action_id: UUID,
) -> RecoveryAction | None:
    result = await db.execute(
        select(RecoveryAction)
        .join(
            RecoveryCase,
            RecoveryCase.id == RecoveryAction.case_id,
        )
        .where(
            RecoveryAction.id == action_id,
            RecoveryCase.merchant_id == merchant_id,
        )
    )

    return result.scalar_one_or_none()