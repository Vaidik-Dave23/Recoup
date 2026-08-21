import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from ..database import Base

class FaultExecution(Base):
    __tablename__ = "fault_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fault_scenario_id = Column(UUID(as_uuid=True), ForeignKey("fault_scenarios.id"), nullable=False)
    executed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    status = Column(String(50), nullable=False)
    details = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    fault_scenario = relationship("FaultScenario", back_populates="executions")