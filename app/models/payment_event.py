import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from ..database import Base

class PaymentEvent(Base):
    __tablename__ = "payment_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False)
    event_id = Column(String(100), nullable=False)
    event_type = Column(String(100), nullable=False)
    source = Column(String(100), nullable=False)
    provider = Column(String(100), nullable=False)
    provider_timestamp = Column(DateTime(timezone=True), nullable=False)
    received_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    payload_hash = Column(String(255), nullable=False)
    raw_payload = Column(JSONB, nullable=False)

    payment = relationship("Payment", back_populates="events")
    webhook_deliveries = relationship("WebhookDelivery", back_populates="payment_event", cascade="all, delete-orphan")