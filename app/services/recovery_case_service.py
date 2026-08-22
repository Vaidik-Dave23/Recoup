from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.payment import Payment
from app.db.models.recovery_case import RecoveryCase
from app.schemas.recovery_case import RecoveryCaseCreate, RecoveryCaseUpdate


async def create_recovery_case(
    db: AsyncSession,
    merchant_id: UUID,
    data: RecoveryCaseCreate,
) -> RecoveryCase:
    result = await db.execute(
        select(Payment).where(
            Payment.id == data.payment_id,
            Payment.merchant_id == merchant_id,
        )
    )

    payment = result.scalar_one_or_none()

    if payment is None:
        raise ValueError("Payment not found")

    case = RecoveryCase(
        merchant_id=merchant_id,
        payment_id=payment.id,
        case_type=data.case_type,
        failure_reason=data.failure_reason,
        amount_at_risk=data.amount_at_risk,
        currency=data.currency.upper(),
        stage="new",
        attempt_count=0,
        status="in_progress",
        financial_impact=0,
    )

    db.add(case)

    await db.commit()
    await db.refresh(case)

    return case


async def get_recovery_cases(
    db: AsyncSession,
    merchant_id: UUID,
) -> list[RecoveryCase]:
    result = await db.execute(
        select(RecoveryCase)
        .where(
            RecoveryCase.merchant_id == merchant_id
        )
        .order_by(RecoveryCase.created_at.desc())
    )

    return list(result.scalars().all())


async def get_recovery_case(
    db: AsyncSession,
    merchant_id: UUID,
    case_id: UUID,
) -> RecoveryCase | None:
    result = await db.execute(
        select(RecoveryCase).where(
            RecoveryCase.id == case_id,
            RecoveryCase.merchant_id == merchant_id,
        )
    )

    return result.scalar_one_or_none()


async def update_recovery_case(
    db: AsyncSession,
    merchant_id: UUID,
    case_id: UUID,
    data: RecoveryCaseUpdate,
) -> RecoveryCase | None:
    case = await get_recovery_case(
        db,
        merchant_id,
        case_id,
    )

    if case is None:
        return None

    if data.stage is not None:
        case.stage = data.stage

    if data.status is not None:
        case.status = data.status

    if data.financial_impact is not None:
        case.financial_impact = data.financial_impact

    await db.commit()
    await db.refresh(case)

    return case