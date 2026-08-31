"""SQLAlchemy ORM models."""
from sqlalchemy import Column, String, Float, Integer, JSON, DateTime, Enum as SAEnum
from sqlalchemy.ext.declarative import declarative_base
import datetime, enum

Base = declarative_base()


class NegotiationStatusEnum(str, enum.Enum):
    accepted = "accepted"
    counter  = "counter"
    rejected = "rejected"
    pending  = "pending"


class Negotiation(Base):
    __tablename__ = "negotiations"

    id               = Column(String, primary_key=True)
    buyer_agent_id   = Column(String, index=True)
    sku              = Column(String, index=True)
    quantity         = Column(Integer)
    budget_total     = Column(Float)
    final_price      = Column(Float, nullable=True)
    total_price      = Column(Float, nullable=True)
    status           = Column(SAEnum(NegotiationStatusEnum))
    razorpay_order_id= Column(String, nullable=True)
    payment_link     = Column(String, nullable=True)
    created_at       = Column(DateTime, default=datetime.datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    negotiation_id   = Column(String, index=True)
    step             = Column(Integer)
    action           = Column(String)
    value            = Column(Float)
    reason           = Column(String)
    created_at       = Column(DateTime, default=datetime.datetime.utcnow)


class MerchantRule(Base):
    __tablename__ = "merchant_rules"

    sku                   = Column(String, primary_key=True)
    min_margin_pct        = Column(Float, default=18.0)
    max_bulk_discount_pct = Column(Float, default=22.0)
    stock                 = Column(Integer, default=100)
    updated_at            = Column(DateTime, default=datetime.datetime.utcnow,
                                   onupdate=datetime.datetime.utcnow)
