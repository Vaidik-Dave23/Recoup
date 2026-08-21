import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from ..database import Base

class UTR(Base):
    __tablename__ = "utrs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    settlement_id = Column(UUID(as_uuid=True), ForeignKey("settlements.id"), nullable=False)
    utr = Column(String(100), nullable=False)
    bank_name = Column(String(100), nullable=False)
    credited_at = Column(DateTime(timezone=True), nullable=True)
    amount = Column(Numeric(18, 2), nullable=False)
    currency = Column(String(10), nullable=False)
    raw_payload = Column(JSONB, nullable=True)

    settlement = relationship("Settlement", back_populates="utrs")