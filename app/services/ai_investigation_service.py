from uuid import UUID
from typing import Any
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.ai_investigation import AIInvestigation
from app.db.models.recovery_case import RecoveryCase


async def create_ai_investigation(
    db: AsyncSession,
    merchant_id: UUID,
    case_id: UUID,
    node_name: str,
    model_name: str | None,
    input_payload: dict[str, Any] | None,
    response_payload: dict[str, Any],
    confidence: Decimal | None,
) -> AIInvestigation:
    result = await db.execute(
        select(RecoveryCase).where(
            RecoveryCase.id == case_id,
            RecoveryCase.merchant_id == merchant_id,
        )
    )

    case = result.scalar_one_or_none()

    if case is None:
        raise ValueError("Recovery case not found")

    investigation = AIInvestigation(
        case_id=case.id,
        node_name=node_name,
        model_name=model_name,
        input_payload=input_payload,
        response_payload=response_payload,
        confidence=confidence,
    )

    db.add(investigation)

    await db.commit()
    await db.refresh(investigation)

    return investigation


async def get_case_investigations(
    db: AsyncSession,
    merchant_id: UUID,
    case_id: UUID,
) -> list[AIInvestigation]:
    result = await db.execute(
        select(RecoveryCase).where(
            RecoveryCase.id == case_id,
            RecoveryCase.merchant_id == merchant_id,
        )
    )

    if result.scalar_one_or_none() is None:
        raise ValueError("Recovery case not found")

    result = await db.execute(
        select(AIInvestigation)
        .where(AIInvestigation.case_id == case_id)
        .order_by(AIInvestigation.created_at.asc())
    )

    return list(result.scalars().all())


async def get_ai_investigation(
    db: AsyncSession,
    merchant_id: UUID,
    investigation_id: UUID,
) -> AIInvestigation | None:
    result = await db.execute(
        select(AIInvestigation)
        .join(
            RecoveryCase,
            RecoveryCase.id == AIInvestigation.case_id,
        )
        .where(
            AIInvestigation.id == investigation_id,
            RecoveryCase.merchant_id == merchant_id,
        )
    )

    return result.scalar_one_or_none()