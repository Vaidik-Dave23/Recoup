import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..database import Base

class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_event_id = Column(UUID(as_uuid=True), ForeignKey("payment_events.id"), nullable=False)
    webhook_url = Column(String(500), nullable=False)
    http_status = Column(Integer, nullable=False)
    response_body = Column(Text, nullable=True)
    attempt = Column(Integer, nullable=False)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    success = Column(Boolean, nullable=False)

    payment_event = relationship("PaymentEvent", back_populates="webhook_deliveries")