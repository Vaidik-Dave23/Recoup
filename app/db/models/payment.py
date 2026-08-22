from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, BigInteger, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDPrimaryKeyMixin, CreatedAtMixin
from .enums import PaymentStatus

if TYPE_CHECKING:
    from .merchant import Merchant
    from .order import Order
    from .recovery_case import RecoveryCase


class Payment(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "payments"

    merchant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    razorpay_payment_id: Mapped[str | None] = mapped_column(
        String(100), unique=True, index=True
    )
    payment_method: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        String(20), nullable=False, default=PaymentStatus.CREATED
    )
    failure_reason: Mapped[str | None] = mapped_column(String(255))
    attempt_count: Mapped[int] = mapped_column(nullable=False, default=0)

    merchant: Mapped["Merchant"] = relationship(back_populates="payments")
    order: Mapped["Order"] = relationship(back_populates="payments")
    recovery_cases: Mapped[list["RecoveryCase"]] = relationship(
        back_populates="payment",
    )
