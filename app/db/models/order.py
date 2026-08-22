from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, BigInteger, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDPrimaryKeyMixin, CreatedAtMixin
from .enums import OrderStatus

if TYPE_CHECKING:
    from .merchant import Merchant
    from .payment import Payment


class Order(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "orders"

    merchant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_id: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    customer_email: Mapped[str | None] = mapped_column(String(320))
    status: Mapped[OrderStatus] = mapped_column(
        String(20), nullable=False, default=OrderStatus.CREATED
    )

    __table_args__ = (
        UniqueConstraint("merchant_id", "order_id", name="uq_orders_merchant_order_id"),
    )

    merchant: Mapped["Merchant"] = relationship(back_populates="orders")
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
    )
