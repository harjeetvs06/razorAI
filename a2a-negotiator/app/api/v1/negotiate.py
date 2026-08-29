import uuid
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, status, Request
from pydantic import BaseModel, Field

from app.engine.guardrails import FinancialGuardrailEngine, FinancialGuardrailException
from app.integrations.razorpay_client import razorpay_client
from app.audit.logger import log_audit_event

router = APIRouter()

# --- Request / Response Pydantic Schemas ---

class BuyerAgentOfferRequest(BaseModel):
    negotiation_id: Optional[str] = Field(
        default=None, 
        json_schema_extra={"example": "neg_77a90b"}
    )
    product_id: str = Field(
        ..., 
        json_schema_extra={"example": "prod_laptop_001"}
    )
    product_name: str = Field(
        ..., 
        json_schema_extra={"example": "Developer Laptop 16-inch"}
    )
    original_price: float = Field(
        ..., 
        gt=0, 
        json_schema_extra={"example": 50000.0}
    )
    proposed_price: float = Field(
        ..., 
        gt=0, 
        json_schema_extra={"example": 43000.0}
    )
    quantity: int = Field(
        default=1, 
        ge=1, 
        json_schema_extra={"example": 1}
    )
    buyer_agent_id: str = Field(
        ..., 
        json_schema_extra={"example": "agent_claude_buyer_01"}
    )
    buyer_notes: Optional[str] = Field(
        default=None, 
        json_schema_extra={"example": "Bulk order requirement for developer onboarding."}
    )


class NegotiationResponse(BaseModel):
    negotiation_id: str
    status: str = Field(..., json_schema_extra={"example": "ACCEPTED"})  # ACCEPTED, COUNTER_OFFER, REJECTED
    agreed_price: Optional[float] = None
    counter_price: Optional[float] = None
    message: str
    razorpay_payment_link: Optional[str] = None
    payment_link_id: Optional[str] = None
    audit_trail: Dict[str, Any]


# --- API Endpoint ---

@router.post("", response_model=NegotiationResponse, status_code=status.HTTP_200_OK)
async def process_buyer_negotiation(payload: BuyerAgentOfferRequest, request: Request):
    """
    Primary Agent-to-Agent (A2A) Endpoint.
    Interacts with external AI buyers, enforces merchant guardrails, 
    and issues dynamic Razorpay payment links.
    """
    negotiation_id = payload.negotiation_id or f"neg_{uuid.uuid4().hex[:8]}"
    
    # Merchant guardrail rules
    merchant_floor = 42000.0
    merchant_max_discount = 0.20

    try:
        # Step 1: Validate proposed offer against hard financial bounds
        guardrail_result = FinancialGuardrailEngine.validate_offer(
            negotiation_id=negotiation_id,
            product_id=payload.product_id,
            requested_price=payload.proposed_price,
            original_price=payload.original_price,
            merchant_floor=merchant_floor,
            max_discount_pct=merchant_max_discount,
            quantity=payload.quantity
        )

        # Step 2: Offer ACCEPTED -> Gate check passed, generate dynamic Razorpay Link
        payment_link_data = razorpay_client.create_negotiated_payment_link(
            negotiation_id=negotiation_id,
            amount_inr=payload.proposed_price,
            description=f"Negotiated deal for {payload.quantity}x {payload.product_name}",
            expire_minutes=15
        )

        return NegotiationResponse(
            negotiation_id=negotiation_id,
            status="ACCEPTED",
            agreed_price=payload.proposed_price,
            message="Offer accepted. Dynamic Razorpay payment link generated.",
            razorpay_payment_link=payment_link_data.get("short_url"),
            payment_link_id=payment_link_data.get("payment_link_id"),
            audit_trail={
                "bounded": True,
                "effective_floor": guardrail_result.get("effective_floor"),
                "savings_for_buyer": guardrail_result.get("savings_for_buyer")
            }
        )

    except FinancialGuardrailException as exc:
        # Step 3: Offer REJECTED (Below Floor) -> Return structured Counter-Offer cleanly
        log_audit_event(
            negotiation_id=negotiation_id,
            action="EMIT_COUNTER_OFFER",
            requested_amount=payload.proposed_price,
            status="COUNTER_PROPOSED",
            reasoning=f"Proposed price ₹{payload.proposed_price} breached floor. Countered with ₹{exc.floor_price}."
        )

        return NegotiationResponse(
            negotiation_id=negotiation_id,
            status="COUNTER_OFFER",
            counter_price=exc.floor_price,
            message=f"Proposed offer ₹{payload.proposed_price} is below merchant floor. Minimum acceptable price is ₹{exc.floor_price}.",
            audit_trail={
                "bounded": True,
                "rejection_reason": exc.message,
                "floor_price": exc.floor_price,
                "action_taken": "COUNTER_OFFER"
            }
        )

    except Exception as exc:
        # Step 4: Graceful Gateway Failure Handling (Razorpay API down/error)
        log_audit_event(
            negotiation_id=negotiation_id,
            action="GATEWAY_FAILURE_HANDLED",
            requested_amount=payload.proposed_price,
            status="SERVICE_DEGRADED",
            reasoning=str(exc)
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "SERVICE_DEGRADED",
                "message": "Offer accepted, but payment gateway connection failed transiently.",
                "negotiation_id": negotiation_id,
                "recovery_action": "Retry payment link generation using existing negotiation_id."
            }
        )