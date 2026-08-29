from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


# --- Enums ---

class NegotiationStatusEnum(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    COUNTER_OFFER = "COUNTER_OFFER"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class PaymentStatusEnum(str, Enum):
    UNPAID = "UNPAID"
    LINK_CREATED = "LINK_CREATED"
    PAID = "PAID"
    FAILED = "FAILED"


# --- Request Schemas ---

class NegotiationRequest(BaseModel):
    """
    Inbound proposal payload sent by a Buyer Agent.
    """
    negotiation_id: str = Field(
        ..., 
        example="neg_88f91a", 
        description="Unique identifier for the negotiation lifecycle session."
    )
    product_id: str = Field(
        ..., 
        example="prod_laptop_001", 
        description="Target SKU or product identifier."
    )
    buyer_agent_id: str = Field(
        ..., 
        example="agent_buyer_v2", 
        description="Identifier for the initiating autonomous buyer agent."
    )
    offered_unit_price: float = Field(
        ..., 
        gt=0, 
        example=45000.0, 
        description="Proposed unit price in INR offered by the buyer agent."
    )
    quantity: int = Field(
        default=1, 
        ge=1, 
        example=1, 
        description="Number of units requested."
    )


class MerchantRuleCreateOrUpdate(BaseModel):
    """
    Payload for merchants to update financial guardrail constraints per SKU.
    """
    product_id: str = Field(..., example="prod_laptop_001")
    product_name: str = Field(..., example="Developer Laptop Pro")
    original_price: float = Field(..., gt=0, example=50000.0)
    floor_price: float = Field(..., gt=0, example=42000.0, description="Hard minimum floor price per unit.")
    max_discount_pct: float = Field(default=0.20, ge=0.0, le=0.90, example=0.20)
    inventory_count: int = Field(default=10, ge=0)
    is_negotiable: bool = Field(default=True)


class RazorpayWebhookPayload(BaseModel):
    """
    Minimal payload representation for Razorpay payment webhooks.
    """
    event: str = Field(..., example="payment.link.paid")
    payload: Dict[str, Any] = Field(..., description="Raw nested webhook data payload.")


# --- Response Schemas ---

class NegotiationResponse(BaseModel):
    """
    Outbound structured evaluation response sent back to the Buyer Agent.
    """
    negotiation_id: str
    product_id: str
    status: NegotiationStatusEnum
    agreed_price: Optional[float] = None
    counter_offered_price: Optional[float] = None
    reasoning: str = Field(
        ..., 
        description="Explainability string detailing why the decision was made."
    )
    razorpay_payment_url: Optional[str] = Field(
        None, 
        description="Dynamic payment link URL generated upon offer acceptance."
    )
    is_bounded: bool = Field(
        True, 
        description="Flag proving financial bounds were evaluated and enforced."
    )

    model_config = ConfigDict(from_attributes=True)


class MerchantRuleResponse(MerchantRuleCreateOrUpdate):
    """
    Serialized output for active merchant product rules.
    """
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogResponse(BaseModel):
    """
    Output model for querying audit history logs.
    """
    id: str
    negotiation_id: str
    action: str
    requested_amount: float
    status: str
    reasoning: str
    metadata_json: Optional[Dict[str, Any]] = None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)