from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID
from datetime import datetime

from sqlalchemy import ForeignKey, BigInteger, Boolean, String, DateTime, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDPrimaryKeyMixin, CreatedAtMixin

if TYPE_CHECKING:
    from .recovery_case import RecoveryCase
    from .recovery_action import RecoveryAction


class RecoveryOutcome(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "recovery_outcomes"

    case_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("recovery_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    action_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("recovery_actions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    recovered: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    amount_recovered: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    recovered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(String(500))

    __table_args__ = (
        UniqueConstraint(
            "case_id",
            "action_id",
            name="uq_recovery_outcomes_case_action",
        ),
    )

    case: Mapped["RecoveryCase"] = relationship(back_populates="outcomes")
    action: Mapped["RecoveryAction"] = relationship(back_populates="outcome")
