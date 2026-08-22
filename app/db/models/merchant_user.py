from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from datetime import datetime

from sqlalchemy import ForeignKey, String, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDPrimaryKeyMixin, CreatedAtMixin
from .enums import MerchantRole

if TYPE_CHECKING:
    from .merchant import Merchant


class MerchantUser(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "merchant_users"

    merchant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[MerchantRole] = mapped_column(
        String(20), nullable=False, default=MerchantRole.MEMBER
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    merchant: Mapped["Merchant"] = relationship(back_populates="users")
