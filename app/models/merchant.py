import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..database import Base

class Merchant(Base):
    __tablename__ = "merchants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    business_name = Column(String(100), nullable=False)
    contact_email = Column(String(100), nullable=False)
    contact_phone = Column(String(20), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    status = Column(String(50), nullable=False)

    users = relationship("MerchantUser", back_populates="merchant", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="merchant", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="merchant", cascade="all, delete-orphan")
    settlements = relationship("Settlement", back_populates="merchant", cascade="all, delete-orphan")
    events = relationship("MerchantEvent", back_populates="merchant", cascade="all, delete-orphan")
    incidents = relationship("Incident", back_populates="merchant", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="merchant", cascade="all, delete-orphan")


class MerchantUser(Base):
    __tablename__ = "merchant_users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    role = Column(String(100), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    status = Column(String(50), nullable=False)

    merchant = relationship("Merchant", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user")