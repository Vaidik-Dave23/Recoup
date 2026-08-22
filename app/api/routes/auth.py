from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from app.db.database import get_db
from app.db.models.merchant import Merchant
from app.db.models.merchant_user import MerchantUser
from app.schemas.auth import (
    LoginRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserResponse,
)


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    data: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    existing_user = await db.execute(
        select(MerchantUser).where(
            MerchantUser.email == data.email
        )
    )

    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email is already registered",
        )

    existing_merchant = await db.execute(
        select(Merchant).where(
            Merchant.business_name == data.business_name
        )
    )

    if existing_merchant.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Business name is already registered",
        )

    merchant = Merchant(
        name=data.name,
        business_name=data.business_name,
        email=data.email,
        plan="free",
        status="active",
    )

    db.add(merchant)

    await db.flush()

    user = MerchantUser(
        merchant_id=merchant.id,
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role="owner",
        status="active",
    )

    db.add(user)

    await db.flush()

    access_token = create_access_token(
        user_id=str(user.id),
        merchant_id=str(merchant.id),
    )

    await db.commit()

    return RegisterResponse(
        user=UserResponse(
            id=str(user.id),
            merchant_id=str(merchant.id),
            name=user.name,
            email=user.email,
            role=user.role,
            status=user.status,
        ),
        access_token=access_token,
    )


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    data: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(MerchantUser).where(
            MerchantUser.email == data.email
        )
    )

    user = result.scalar_one_or_none()

    if user is None or not verify_password(
        data.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active",
        )

    user.last_login_at = datetime.now(timezone.utc)

    access_token = create_access_token(
        user_id=str(user.id),
        merchant_id=str(user.merchant_id),
    )

    await db.commit()

    return TokenResponse(
        access_token=access_token,
    )


@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_me(
    current_user: Annotated[
        MerchantUser,
        Depends(get_current_user),
    ],
):
    return UserResponse(
        id=str(current_user.id),
        merchant_id=str(current_user.merchant_id),
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        status=current_user.status,
    )