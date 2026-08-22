from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID
from datetime import datetime

from sqlalchemy import ForeignKey, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDPrimaryKeyMixin, CreatedAtMixin
from .enums import ActionType, ActionChannel, ActionStatus

if TYPE_CHECKING:
    from .recovery_case import RecoveryCase
    from .ai_investigation import AIInvestigation
    from .recovery_outcome import RecoveryOutcome


class RecoveryAction(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "recovery_actions"

    case_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("recovery_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    investigation_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("ai_investigations.id", ondelete="SET NULL"),
        index=True,
    )
    action_type: Mapped[ActionType] = mapped_column(String(20), nullable=False)
    channel: Mapped[ActionChannel] = mapped_column(String(30), nullable=False)
    subject: Mapped[str | None] = mapped_column(String(255))
    message_body: Mapped[str | None] = mapped_column(Text)
    provider_ref: Mapped[str | None] = mapped_column(String(255))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[ActionStatus] = mapped_column(
        String(20), nullable=False, default=ActionStatus.QUEUED
    )

    case: Mapped["RecoveryCase"] = relationship(back_populates="actions")
    investigation: Mapped["AIInvestigation | None"] = relationship(
        back_populates="actions"
    )
    outcome: Mapped["RecoveryOutcome | None"] = relationship(
        back_populates="action",
        uselist=False,
    )
