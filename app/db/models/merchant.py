from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from .enums import MerchantStatus

if TYPE_CHECKING:
    from .merchant_user import MerchantUser
    from .order import Order
    from .payment import Payment
    from .recovery_case import RecoveryCase


class Merchant(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "merchants"

    name: Mapped[str] = mapped_column(String(150), nullable=False)
    business_name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    plan: Mapped[str] = mapped_column(String(50), nullable=False, default="free")
    status: Mapped[MerchantStatus] = mapped_column(
        String(20), nullable=False, default=MerchantStatus.ACTIVE
    )

    __table_args__ = (
        UniqueConstraint("business_name", name="uq_merchants_business_name"),
    )

    users: Mapped[list["MerchantUser"]] = relationship(
        back_populates="merchant",
        cascade="all, delete-orphan",
    )
    orders: Mapped[list["Order"]] = relationship(
        back_populates="merchant",
        cascade="all, delete-orphan",
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="merchant",
        cascade="all, delete-orphan",
    )
    recovery_cases: Mapped[list["RecoveryCase"]] = relationship(
        back_populates="merchant",
        cascade="all, delete-orphan",
    )
