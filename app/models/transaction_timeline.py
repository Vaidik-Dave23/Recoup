import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from ..database import Base

class TransactionTimeline(Base):
    __tablename__ = "transactions_timeline"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False)
    step_order = Column(Integer, nullable=False)
    step_name = Column(String(100), nullable=False)
    status = Column(String(50), nullable=False)
    actor = Column(String(100), nullable=False)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    details = Column(JSONB, nullable=True)

    payment = relationship("Payment", back_populates="transaction_timelines")