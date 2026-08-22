from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.db.models.merchant_user import MerchantUser
from app.schemas.recovery_action import (
    RecoveryActionCreate,
    RecoveryActionResponse,
)
from app.services.recovery_action_service import (
    create_recovery_action,
    get_case_actions,
    get_recovery_action,
)


router = APIRouter(
    prefix="/recovery-actions",
    tags=["Recovery Actions"],
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
    response_model=RecoveryActionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    data: RecoveryActionCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    try:
        return await create_recovery_action(
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
    "/case/{case_id}",
    response_model=list[RecoveryActionResponse],
)
async def list_for_case(
    case_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    try:
        return await get_case_actions(
            db,
            current_user.merchant_id,
            case_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "/{action_id}",
    response_model=RecoveryActionResponse,
)
async def get_one(
    action_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    action = await get_recovery_action(
        db,
        current_user.merchant_id,
        action_id,
    )

    if action is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recovery action not found",
        )

    return action