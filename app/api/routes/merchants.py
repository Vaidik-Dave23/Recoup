import os
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_current_user
from app.db.database import get_db
from app.db.models.merchant import Merchant
from app.db.models.merchant_user import MerchantUser

router = APIRouter(
    prefix="/merchants",
    tags=["Merchant Settings"],
)

CurrentUser = Annotated[
    MerchantUser,
    Depends(get_current_user),
]

DBSession = Annotated[
    AsyncSession,
    Depends(get_db),
]


class MerchantUpdate(BaseModel):
    name: str | None = None
    business_name: str | None = None
    email: EmailStr | None = None


@router.get("/me")
async def get_merchant(
    current_user: CurrentUser,
    db: DBSession,
):
    merchant_id = current_user.merchant_id
    merchant = await db.get(Merchant, merchant_id)

    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Merchant not found",
        )

    # Check SMTP configuration status from environment variables
    smtp_configured = bool(
        os.getenv("SMTP_HOST")
        and os.getenv("SMTP_USERNAME")
        and os.getenv("SMTP_PASSWORD")
    )

    razorpay_configured = bool(settings.razorpay_key_id and settings.razorpay_key_secret)

    return {
        "id": str(merchant.id),
        "name": merchant.name,
        "business_name": merchant.business_name,
        "email": merchant.email,
        "plan": merchant.plan,
        "status": merchant.status,
        "created_at": merchant.created_at,
        "channels": {
            "email": {
                "configured": smtp_configured,
                "status": "active" if smtp_configured else "not_configured",
                "provider": "SMTP / Gmail",
            },
            "sms": {
                "configured": False,
                "status": "not_configured",
                "provider": "Twilio (Placeholder)",
            },
            "razorpay_retry": {
                "configured": razorpay_configured,
                "status": "active" if razorpay_configured else "not_configured",
                "provider": "Razorpay Payment Links API",
            },
        },
    }


@router.patch("/me")
async def update_merchant(
    data: MerchantUpdate,
    current_user: CurrentUser,
    db: DBSession,
):
    merchant_id = current_user.merchant_id
    merchant = await db.get(Merchant, merchant_id)

    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Merchant not found",
        )

    if data.name is not None:
        merchant.name = data.name
    if data.business_name is not None:
        merchant.business_name = data.business_name
    if data.email is not None:
        merchant.email = data.email

    await db.commit()
    await db.refresh(merchant)

    return {
        "id": str(merchant.id),
        "name": merchant.name,
        "business_name": merchant.business_name,
        "email": merchant.email,
        "plan": merchant.plan,
        "status": merchant.status,
    }


@router.get("/me/users")
async def get_merchant_users(
    current_user: CurrentUser,
    db: DBSession,
):
    merchant_id = current_user.merchant_id
    stmt = select(MerchantUser).where(MerchantUser.merchant_id == merchant_id)
    result = await db.execute(stmt)
    users = result.scalars().all()

    return [
        {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "status": user.status,
            "created_at": user.created_at,
            "last_login_at": user.last_login_at,
        }
        for user in users
    ]