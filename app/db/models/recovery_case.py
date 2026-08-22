from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID
from datetime import datetime

from sqlalchemy import ForeignKey, String, BigInteger, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDPrimaryKeyMixin, CreatedAtMixin
from .enums import CaseType, RecoveryStage, RecoveryCaseStatus

if TYPE_CHECKING:
    from .merchant import Merchant
    from .payment import Payment
    from .ai_investigation import AIInvestigation
    from .recovery_action import RecoveryAction
    from .recovery_outcome import RecoveryOutcome
    from .escalation import Escalation


class RecoveryCase(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "recovery_cases"

    merchant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payment_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("payments.id", ondelete="SET NULL"),
        index=True,
    )
    case_type: Mapped[CaseType] = mapped_column(String(30), nullable=False)
    failure_reason: Mapped[str] = mapped_column(String(255), nullable=False)
    amount_at_risk: Mapped[int] = mapped_column(BigInteger, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    stage: Mapped[RecoveryStage] = mapped_column(
        String(30), nullable=False, default=RecoveryStage.NEW
    )
    attempt_count: Mapped[int] = mapped_column(nullable=False, default=0)
    status: Mapped[RecoveryCaseStatus] = mapped_column(
        String(20), nullable=False, default=RecoveryCaseStatus.IN_PROGRESS
    )
    financial_impact: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    merchant: Mapped["Merchant"] = relationship(back_populates="recovery_cases")
    payment: Mapped["Payment | None"] = relationship(back_populates="recovery_cases")

    investigations: Mapped[list["AIInvestigation"]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
    )
    actions: Mapped[list["RecoveryAction"]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
    )
    outcomes: Mapped[list["RecoveryOutcome"]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
    )
    escalations: Mapped[list["Escalation"]] = relationship(
        back_populates="case",
        cascade="all, delete-orphan",
    )
