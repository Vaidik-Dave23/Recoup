from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import ForeignKey, String, Numeric
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, UUIDPrimaryKeyMixin, CreatedAtMixin
from .enums import InvestigationNode

if TYPE_CHECKING:
    from .recovery_case import RecoveryCase
    from .recovery_action import RecoveryAction


class AIInvestigation(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "ai_investigations"

    case_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("recovery_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    node_name: Mapped[InvestigationNode] = mapped_column(
        String(30), nullable=False
    )
    model_name: Mapped[str | None] = mapped_column(String(100))
    input_payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    response_payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 4))
    case: Mapped["RecoveryCase"] = relationship(back_populates="investigations")
    actions: Mapped[list["RecoveryAction"]] = relationship(
        back_populates="investigation"
    )
