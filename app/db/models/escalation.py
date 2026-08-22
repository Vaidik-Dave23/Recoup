from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDPrimaryKeyMixin, CreatedAtMixin
from .enums import EscalationStatus

if TYPE_CHECKING:
    from .recovery_case import RecoveryCase


class Escalation(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "escalations"

    case_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("recovery_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="medium",
    )
    assigned_to: Mapped[str | None] = mapped_column(String(320))
    status: Mapped[EscalationStatus] = mapped_column(
        String(20), nullable=False, default=EscalationStatus.OPEN
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    case: Mapped["RecoveryCase"] = relationship(back_populates="escalations")
