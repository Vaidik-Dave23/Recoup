import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from ..database import Base

class MerchantEvent(Base):
    __tablename__ = "merchant_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    event_type = Column(String(100), nullable=False)
    entity_type = Column(String(100), nullable=False)
    entity_id = Column(String(100), nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=False)
    source = Column(String(100), nullable=False)
    payload = Column(JSONB, nullable=False)

    merchant = relationship("Merchant", back_populates="events")