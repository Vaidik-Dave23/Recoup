from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.db.models.merchant_user import MerchantUser
from app.schemas.escalation import (
    EscalationCreate,
    EscalationResponse,
    EscalationUpdate,
)
from app.services.escalation_service import (
    create_escalation,
    get_case_escalations,
    get_escalation,
    get_escalations,
    update_escalation,
)


router = APIRouter(
    prefix="/escalations",
    tags=["Escalations"],
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
    response_model=EscalationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    data: EscalationCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    try:
        return await create_escalation(
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
    response_model=list[EscalationResponse],
)
async def list_all(
    current_user: CurrentUser,
    db: DBSession,
):
    return await get_escalations(
        db,
        current_user.merchant_id,
    )


@router.get(
    "/case/{case_id}",
    response_model=list[EscalationResponse],
)
async def list_for_case(
    case_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    try:
        return await get_case_escalations(
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
    "/{escalation_id}",
    response_model=EscalationResponse,
)
async def get_one(
    escalation_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    escalation = await get_escalation(
        db,
        current_user.merchant_id,
        escalation_id,
    )

    if escalation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Escalation not found",
        )

    return escalation


@router.patch(
    "/{escalation_id}",
    response_model=EscalationResponse,
)
async def update(
    escalation_id: UUID,
    data: EscalationUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    escalation = await update_escalation(
        db,
        current_user.merchant_id,
        escalation_id,
        data,
    )

    if escalation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Escalation not found",
        )

    return escalation