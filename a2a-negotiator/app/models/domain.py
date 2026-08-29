import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy import (
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    Text,
    ForeignKey,
    JSON,
    Enum as SQLEnum
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.core.database import Base


# --- Enums for Negotiation & Audit States ---

class NegotiationStatus(str, enum.Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    COUNTER_OFFER = "COUNTER_OFFER"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class PaymentStatus(str, enum.Enum):
    UNPAID = "UNPAID"
    LINK_CREATED = "LINK_CREATED"
    PAID = "PAID"
    FAILED = "FAILED"


# --- ORM Entities ---

class MerchantProductRule(Base):
    """
    Stores merchant-configured financial guardrails and inventory constraints per SKU.
    """
    __tablename__ = "merchant_product_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    product_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    product_name: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Financial Boundaries
    original_price: Mapped[float] = mapped_column(Float, nullable=False)
    floor_price: Mapped[float] = mapped_column(Float, nullable=False)  # Absolute min unit price
    max_discount_pct: Mapped[float] = mapped_column(Float, default=0.20)  # e.g., 0.20 = 20%
    
    # Inventory Controls
    inventory_count: Mapped[int] = mapped_column(Integer, default=0)
    is_negotiable: Mapped[bool] = mapped_column(Boolean, default=True)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    negotiations: Mapped[List["NegotiationSession"]] = relationship(back_populates="product_rule")


class NegotiationSession(Base):
    """
    Tracks state machine iterations for agent-to-agent negotiation rounds.
    """
    __tablename__ = "negotiation_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # e.g., "neg_88f91a"
    product_id: Mapped[str] = mapped_column(String(100), ForeignKey("merchant_product_rules.product_id"), nullable=False)
    buyer_agent_id: Mapped[str] = mapped_column(String(100), nullable=False)
    
    # Proposal Tracking
    original_price: Mapped[float] = mapped_column(Float, nullable=False)
    proposed_price: Mapped[float] = mapped_column(Float, nullable=False)
    counter_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    agreed_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    
    # State tracking
    status: Mapped[NegotiationStatus] = mapped_column(
        SQLEnum(NegotiationStatus), default=NegotiationStatus.PENDING, index=True
    )
    payment_status: Mapped[PaymentStatus] = mapped_column(
        SQLEnum(PaymentStatus), default=PaymentStatus.UNPAID, index=True
    )
    
    # Razorpay Details
    razorpay_payment_link_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    razorpay_payment_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    razorpay_payment_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    product_rule: Mapped["MerchantProductRule"] = relationship(back_populates="negotiations")
    audit_logs: Mapped[List["AuditEventLog"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class AuditEventLog(Base):
    """
    Persistent store for explainable financial decision logs and system interventions.
    Directly satisfies Track 1's mandatory audit trail standard.
    """
    __tablename__ = "audit_event_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    negotiation_id: Mapped[str] = mapped_column(String(64), ForeignKey("negotiation_sessions.id"), nullable=False, index=True)
    
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., 'GUARDRAIL_INTERVENTION'
    requested_amount: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., 'APPROVED', 'REJECTED_BOUND_BREACH'
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)  # Explainability text
    
    metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )

    # Relationships
    session: Mapped["NegotiationSession"] = relationship(back_populates="audit_logs")