from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.db.models.merchant_user import MerchantUser
from app.schemas.recovery_outcome import (
    RecoveryOutcomeCreate,
    RecoveryOutcomeResponse,
)
from app.services.recovery_outcome_service import (
    create_recovery_outcome,
    get_case_outcomes,
    get_recovery_outcome,
)


router = APIRouter(
    prefix="/recovery-outcomes",
    tags=["Recovery Outcomes"],
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
    response_model=RecoveryOutcomeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    data: RecoveryOutcomeCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    try:
        return await create_recovery_outcome(
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
    "/case/{case_id}",
    response_model=list[RecoveryOutcomeResponse],
)
async def list_for_case(
    case_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    try:
        return await get_case_outcomes(
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
    "/{outcome_id}",
    response_model=RecoveryOutcomeResponse,
)
async def get_one(
    outcome_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    outcome = await get_recovery_outcome(
        db,
        current_user.merchant_id,
        outcome_id,
    )

    if outcome is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recovery outcome not found",
        )

    return outcome