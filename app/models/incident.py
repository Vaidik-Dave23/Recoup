import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Numeric, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from ..database import Base

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False)
    incident_type = Column(String(100), nullable=False)
    severity = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    financial_impact = Column(Numeric(18, 2), nullable=True)
    affected_count = Column(Integer, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    merchant = relationship("Merchant", back_populates="incidents")
    evidence = relationship("IncidentEvidence", back_populates="incident", cascade="all, delete-orphan")
    ai_investigations = relationship("AIInvestigation", back_populates="incident", cascade="all, delete-orphan")
    ai_recommendations = relationship("AIRecommendation", back_populates="incident", cascade="all, delete-orphan")