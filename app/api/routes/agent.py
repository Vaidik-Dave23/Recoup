from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import resume_after_outcome, run_case
from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.db.models.merchant_user import MerchantUser
from app.schemas.agent import AgentRunResponse


router = APIRouter(prefix="/recovery-cases", tags=["Recovery Agent"])
CurrentUser = Annotated[MerchantUser, Depends(get_current_user)]
DBSession = Annotated[AsyncSession, Depends(get_db)]


def response(case_id: UUID, result: dict) -> AgentRunResponse:
    values = {
        key: value
        for key, value in result.items()
        if key in AgentRunResponse.model_fields and key != "case_id"
    }
    return AgentRunResponse(case_id=str(case_id), **values)


@router.post("/{case_id}/agent/run", response_model=AgentRunResponse)
async def run(case_id: UUID, current_user: CurrentUser, db: DBSession):
    try:
        return response(case_id, await run_case(db, current_user.merchant_id, case_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{case_id}/agent/resume", response_model=AgentRunResponse | None)
async def resume(case_id: UUID, current_user: CurrentUser, db: DBSession):
    try:
        result = await resume_after_outcome(db, current_user.merchant_id, case_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return response(case_id, result) if result is not None else None
