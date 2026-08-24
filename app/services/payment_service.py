from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.enums import PaymentStatus
from app.db.models.order import Order
from app.db.models.payment import Payment
from app.schemas.payment import PaymentCreate



async def create_payment(
    db: AsyncSession,
    merchant_id: UUID,
    data: PaymentCreate,
) -> Payment:
    # Find the order belonging to the current merchant
    result = await db.execute(
        select(Order).where(
            Order.order_id == data.order_id,
            Order.merchant_id == merchant_id,
        )
    )

    order = result.scalar_one_or_none()

    if order is None:
        raise ValueError("Order not found")

    # Prevent duplicate Razorpay/payment transaction IDs
    result = await db.execute(
        select(Payment).where(
            Payment.razorpay_payment_id == data.transaction_id
        )
    )

    existing_payment = result.scalar_one_or_none()

    if existing_payment is not None:
        raise ValueError("Transaction already exists")

    # Create payment
    payment = Payment(

        merchant_id=merchant_id,
        order_id=order.id,
        amount=data.amount,
        currency=data.currency.upper(),
        razorpay_payment_id=data.transaction_id,
        payment_method=data.payment_method,
        status=data.status or PaymentStatus.CREATED,
        failure_reason=data.failure_reason,
    )


    db.add(payment)

    await db.commit()
    await db.refresh(payment)

    return payment


async def get_payments(
    db: AsyncSession,
    merchant_id: UUID,
) -> list[Payment]:
    result = await db.execute(
        select(Payment)
        .where(Payment.merchant_id == merchant_id)
        .order_by(Payment.created_at.desc())
    )

    return list(result.scalars().all())


async def get_payment(
    db: AsyncSession,
    merchant_id: UUID,
    payment_id: UUID,
) -> Payment | None:
    result = await db.execute(
        select(Payment).where(
            Payment.id == payment_id,
            Payment.merchant_id == merchant_id,
        )
    )

    return result.scalar_one_or_none()
