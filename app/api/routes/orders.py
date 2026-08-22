from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.db.models.merchant_user import MerchantUser
from app.schemas.order import (
    OrderCreate,
    OrderResponse,
    OrderUpdate,
)
from app.services.order_service import (
    create_order,
    delete_order,
    get_order,
    get_orders,
    update_order,
)


router = APIRouter(
    prefix="/orders",
    tags=["Orders"],
)


CurrentUser = Annotated[
    MerchantUser,
    Depends(get_current_user),
]

DBSession = Annotated[
    AsyncSession,
    Depends(get_db),
]


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_order_endpoint(
    data: OrderCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    return await create_order(
        db,
        current_user.merchant_id,
        data,
    )


@router.get(
    "",
    response_model=list[OrderResponse],
)
async def list_orders(
    current_user: CurrentUser,
    db: DBSession,
):
    return await get_orders(
        db,
        current_user.merchant_id,
    )


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
)
async def get_order_endpoint(
    order_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    order = await get_order(
        db,
        current_user.merchant_id,
        order_id,
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return order


@router.patch(
    "/{order_id}",
    response_model=OrderResponse,
)
async def update_order_endpoint(
    order_id: UUID,
    data: OrderUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    order = await update_order(
        db,
        current_user.merchant_id,
        order_id,
        data,
    )

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return order


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_order_endpoint(
    order_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    deleted = await delete_order(
        db,
        current_user.merchant_id,
        order_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return None