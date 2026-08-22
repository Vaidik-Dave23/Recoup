from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.db.models.merchant_user import MerchantUser
from app.schemas.ai_investigation import (
    AIInvestigationCreate,
    AIInvestigationResponse,
)
from app.services.ai_investigation_service import (
    create_ai_investigation,
    get_ai_investigation,
    get_case_investigations,
)


router = APIRouter(
    prefix="/ai-investigations",
    tags=["AI Investigations"],
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
    response_model=AIInvestigationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create(
    data: AIInvestigationCreate,
    current_user: CurrentUser,
    db: DBSession,
):
    try:
        return await create_ai_investigation(
            db=db,
            merchant_id=current_user.merchant_id,
            case_id=data.case_id,
            node_name=data.node_name,
            model_name=data.model_name,
            input_payload=data.input_payload,
            response_payload=data.response_payload,
            confidence=data.confidence,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


@router.get(
    "/case/{case_id}",
    response_model=list[AIInvestigationResponse],
)
async def list_for_case(
    case_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    try:
        return await get_case_investigations(
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
    "/{investigation_id}",
    response_model=AIInvestigationResponse,
)
async def get_one(
    investigation_id: UUID,
    current_user: CurrentUser,
    db: DBSession,
):
    investigation = await get_ai_investigation(
        db,
        current_user.merchant_id,
        investigation_id,
    )

    if investigation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI investigation not found",
        )

    return investigation