from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.db.models.merchant_user import MerchantUser
from app.schemas.recovery_case import (
    RecoveryCaseCreate,
    RecoveryCaseResponse,
    RecoveryCaseUpdate,
)
from app.services.recovery_case_service import (
    create_recovery_case,
    get_recovery_case,
    get_recovery_cases,
    sync_case_payment_status,
    update_recovery_case,
)


router = APIRouter(
    prefix="/recovery-cases",
    tags=["Recovery Cases"],
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
    response_model=RecoveryCaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    data: RecoveryCaseCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    try:
        return await create_recovery_case(
            db,
            current_user.merchant_id,
            data,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "",
    response_model=list[RecoveryCaseResponse],
)
async def list_all(
    current_user: CurrentUser,
    db: DBSession,
):
    return await get_recovery_cases(
        db,
        current_user.merchant_id,
    )


@router.get(
    "/{case_id}",
    response_model=RecoveryCaseResponse,
)
async def get_one(
    case_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    case = await get_recovery_case(
        db,
        current_user.merchant_id,
        case_id,
    )

    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recovery case not found",
        )

    return case


@router.post(
    "/{case_id}/verify-payment",
)
async def verify_payment(
    case_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    case = await get_recovery_case(
        db,
        current_user.merchant_id,
        case_id,
    )

    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recovery case not found",
        )

    sync_result = await sync_case_payment_status(db, current_user.merchant_id, case)
    # Reload case to reflect updated fields
    updated_case = await get_recovery_case(db, current_user.merchant_id, case_id)
    return {
        "sync_result": sync_result,
        "case": updated_case,
    }


@router.patch(
    "/{case_id}",
    response_model=RecoveryCaseResponse,
)
async def update(
    case_id: UUID,
    data: RecoveryCaseUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    case = await update_recovery_case(
        db,
        current_user.merchant_id,
        case_id,
        data,
    )

    if case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recovery case not found",
        )

    return case