from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.enums import OrderStatus
from app.db.models.order import Order
from app.schemas.order import OrderCreate, OrderUpdate
from app.db.models.enums import OrderStatus


async def create_order(
    db: AsyncSession,
    merchant_id: UUID,
    data: OrderCreate,
) -> Order:
    order = Order(
        merchant_id=merchant_id,
        order_id=data.order_id,
        amount=data.amount,
        currency=data.currency.upper(),
        customer_email=data.customer_email,
        status=OrderStatus.CREATED,
    )

    db.add(order)

    await db.commit()
    await db.refresh(order)

    return order


async def get_orders(
    db: AsyncSession,
    merchant_id: UUID,
) -> list[Order]:
    result = await db.execute(
        select(Order)
        .where(Order.merchant_id == merchant_id)
        .order_by(Order.created_at.desc())
    )

    return list(result.scalars().all())


async def get_order(
    db: AsyncSession,
    merchant_id: UUID,
    order_id: UUID,
) -> Order | None:
    result = await db.execute(
        select(Order).where(
            Order.id == order_id,
            Order.merchant_id == merchant_id,
        )
    )

    return result.scalar_one_or_none()


async def update_order(
    db: AsyncSession,
    merchant_id: UUID,
    order_id: UUID,
    data: OrderUpdate,
) -> Order | None:
    order = await get_order(
        db,
        merchant_id,
        order_id,
    )

    if order is None:
        return None

    order.status = data.status

    await db.commit()
    await db.refresh(order)

    return order


async def delete_order(
    db: AsyncSession,
    merchant_id: UUID,
    order_id: UUID,
) -> bool:
    order = await get_order(
        db,
        merchant_id,
        order_id,
    )

    if order is None:
        return False

    await db.delete(order)
    await db.commit()

    return True