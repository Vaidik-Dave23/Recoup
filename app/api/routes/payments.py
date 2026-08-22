from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.db.models.merchant_user import MerchantUser
from app.schemas.payment import PaymentCreate, PaymentResponse
from app.services.payment_service import (
    create_payment,
    get_payment,
    get_payments,
)


router = APIRouter(
    prefix="/payments",
    tags=["Payments"],
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
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    data: PaymentCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    try:
        return await create_payment(
            db,
            current_user.merchant_id,
            data,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=list[PaymentResponse],
)
async def list_all(
    current_user: CurrentUser,
    db: DBSession,
):
    return await get_payments(
        db,
        current_user.merchant_id,
    )


@router.get(
    "/{payment_id}",
    response_model=PaymentResponse,
)
async def get_one(
    payment_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    payment = await get_payment(
        db,
        current_user.merchant_id,
        payment_id,
    )

    if payment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found",
        )

    return payment