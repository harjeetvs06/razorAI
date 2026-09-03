"""Pydantic schemas – all request/response shapes."""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from enum import Enum
import uuid


class NegotiationStatus(str, Enum):
    ACCEPTED = "accepted"
    COUNTER  = "counter"
    REJECTED = "rejected"
    PENDING  = "pending"


class BuyerRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "sku": "SKU-001",
                "quantity": 50,
                "budget_total": 45000,
                "delivery_deadline_days": 5,
                "buyer_agent_id": "buyer-acme-corp",
            }
        }
    )

    sku: str
    quantity: int = Field(..., gt=0, le=10_000, description="Units requested")
    budget_total: float = Field(..., gt=0, description="Total ₹ budget")
    delivery_deadline_days: Optional[int] = Field(None, gt=0)
    buyer_agent_id: str = Field(default_factory=lambda: f"buyer-{uuid.uuid4().hex[:8]}")
    note: Optional[str] = None


class AuditStep(BaseModel):
    step: int
    action: str
    value: float
    reason: str


class NegotiationResult(BaseModel):
    negotiation_id: str
    status: NegotiationStatus
    sku: str
    product_name: str
    quantity: int
    unit_price: float
    total_price: float
    discount_pct: float
    base_price: float
    stock_available: int
    shipping_days: int
    effective_floor: float = 0.0 
    payment_link: str
    razorpay_order_id: Optional[str] = None
    audit_trail: List[AuditStep]
    explanation: str
    gates_checked: List[str]
    timestamp: float


class CatalogItem(BaseModel):
    sku: str
    name: str
    base_price: float
    stock: int
    category: str
    shipping_sla_days: int
    image_key: str


class MerchantRuleUpdate(BaseModel):
    sku: str
    min_margin_pct: Optional[float] = None
    max_bulk_discount_pct: Optional[float] = None
    stock: Optional[int] = None


class RazorpayWebhookPayload(BaseModel):
    event: str
    payload: dict
