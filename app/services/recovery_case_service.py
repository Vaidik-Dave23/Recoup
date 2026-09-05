from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.payment import Payment
from app.db.models.recovery_case import RecoveryCase
from app.schemas.recovery_case import RecoveryCaseCreate, RecoveryCaseUpdate
from app.agent.razorpay_client import fetch_payment_link_status
from app.db.models.recovery_action import RecoveryAction
from app.db.models.recovery_outcome import RecoveryOutcome
from app.schemas.recovery_outcome import RecoveryOutcomeCreate
from app.services.recovery_outcome_service import create_recovery_outcome


from app.db.models.enums import ActionStatus, PaymentStatus, RecoveryCaseStatus, RecoveryStage

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

    if payment.status == PaymentStatus.SUCCEEDED:
        raise ValueError("Cannot create a recovery case for a succeeded payment")

    if data.case_type == "payment_failed" and payment.status not in (PaymentStatus.FAILED, PaymentStatus.CREATED):
        raise ValueError(
            f"Cannot create a 'payment_failed' recovery case for a payment with status '{payment.status}'"
        )

    if data.amount_at_risk is not None and data.amount_at_risk != payment.amount:
        raise ValueError(
            f"Case amount_at_risk ({data.amount_at_risk}) does not match Payment amount ({payment.amount})"
        )
    amount_at_risk = payment.amount

    if data.currency is not None and data.currency.upper() != payment.currency.upper():
        raise ValueError(
            f"Case currency ({data.currency}) does not match Payment currency ({payment.currency})"
        )
    currency = payment.currency

    failure_reason = payment.failure_reason or data.failure_reason or "Payment failed"
    case_type = data.case_type or "payment_failed"

    case = RecoveryCase(
        merchant_id=merchant_id,
        payment_id=payment.id,
        case_type=case_type,
        failure_reason=failure_reason,
        amount_at_risk=amount_at_risk,
        currency=currency.upper(),
        stage=RecoveryStage.NEW,
        attempt_count=0,
        status=RecoveryCaseStatus.IN_PROGRESS,
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

    cases = list(result.scalars().all())
    for c in cases:
        if c.status in (RecoveryCaseStatus.IN_PROGRESS, "in_progress"):
            sync_res = await sync_case_payment_status(db, merchant_id, c)
            if sync_res.get("synced"):
                await db.refresh(c)
    return cases


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

    case = result.scalar_one_or_none()
    if case is not None and case.status in (RecoveryCaseStatus.IN_PROGRESS, "in_progress"):
        sync_res = await sync_case_payment_status(db, merchant_id, case)
        if sync_res.get("synced"):
            await db.refresh(case)
    return case


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


async def sync_case_payment_status(db: AsyncSession, merchant_id: UUID, case: RecoveryCase) -> dict:
    if case.status not in (RecoveryCaseStatus.IN_PROGRESS, "in_progress"):
        return {"synced": False, "reason": "case_not_in_progress", "status": case.status}

    # Find all sent or delivered actions for this case that have a payment link reference
    stmt = select(RecoveryAction).where(
        RecoveryAction.case_id == case.id,
        RecoveryAction.status.in_([ActionStatus.SENT, "sent", ActionStatus.DELIVERED, "delivered"])
    )
    actions_result = await db.execute(stmt)
    actions = actions_result.scalars().all()

    for action in actions:
        if not action.provider_ref or "rzp_link:" not in action.provider_ref:
            continue
        
        try:
            parts = action.provider_ref.split("rzp_link:")
            payment_link_id = parts[1].strip().split()[0]
        except Exception:
            continue
        
        try:
            status_data = fetch_payment_link_status(payment_link_id)
            link_status = status_data.get("status")
            amount_paid = status_data.get("amount_paid", 0)
            paid_at = status_data.get("paid_at")
        except Exception:
            continue
        
        is_paid = link_status == "paid" or (amount_paid and amount_paid > 0) or paid_at is not None
        if is_paid:
            # Record recovery outcome
            outcome_stmt = select(RecoveryOutcome).where(RecoveryOutcome.action_id == action.id)
            existing_outcome = (await db.execute(outcome_stmt)).scalar_one_or_none()
            if not existing_outcome:
                amount_recovered = amount_paid if (amount_paid and amount_paid > 0) else case.amount_at_risk
                outcome_data = RecoveryOutcomeCreate(
                    case_id=case.id,
                    action_id=action.id,
                    recovered=True,
                    amount_recovered=amount_recovered,
                    notes=f"Auto-synced payment via Razorpay link: {payment_link_id}"
                )
                await create_recovery_outcome(db, merchant_id, outcome_data)
                return {
                    "synced": True,
                    "payment_link_id": payment_link_id,
                    "link_status": "paid",
                    "amount_recovered": amount_recovered,
                }
            return {
                "synced": True,
                "payment_link_id": payment_link_id,
                "link_status": "paid",
                "already_recorded": True,
            }
        else:
            return {
                "synced": False,
                "payment_link_id": payment_link_id,
                "link_status": link_status or "issued",
            }

    return {"synced": False, "reason": "no_active_payment_link"}