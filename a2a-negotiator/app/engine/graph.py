from typing import Dict, Any, Optional, TypedDict, List
from enum import Enum
from pydantic import BaseModel

from app.engine.guardrails import FinancialGuardrailEngine, FinancialGuardrailException
from app.integrations.razorpay import razorpay_client
from app.audit.logger import log_audit_event
from app.config import settings


# --- State Definition ---

class NodeState(str, Enum):
    EVALUATE_OFFER = "EVALUATE_OFFER"
    GENERATE_PAYMENT = "GENERATE_PAYMENT"
    EMIT_COUNTER = "EMIT_COUNTER"
    TERMINATE_REJECTED = "TERMINATE_REJECTED"


class NegotiationGraphState(TypedDict):
    negotiation_id: str
    product_id: str
    product_name: str
    original_price: float
    merchant_floor: float
    buyer_agent_id: str
    current_round: int
    max_rounds: int
    offered_price: float
    quantity: int
    agreed_price: Optional[float]
    counter_price: Optional[float]
    status: str
    message: str
    payment_link: Optional[str]
    audit_history: List[Dict[str, Any]]


# --- Graph Executor Engine ---

class NegotiationGraphEngine:
    """
    Manages state transitions and decision logic for Agent-to-Agent negotiations.
    """

    @classmethod
    async def run_step(
        cls,
        negotiation_id: str,
        product_id: str,
        product_name: str,
        original_price: float,
        merchant_floor: float,
        offered_price: float,
        quantity: int = 1,
        buyer_agent_id: str = "unknown_buyer",
        current_round: int = 1,
        max_rounds: int = 5
    ) -> NegotiationGraphState:
        """
        Executes a single step in the state graph.
        """
        # Initialize Graph State
        state: NegotiationGraphState = {
            "negotiation_id": negotiation_id,
            "product_id": product_id,
            "product_name": product_name,
            "original_price": original_price,
            "merchant_floor": merchant_floor,
            "buyer_agent_id": buyer_agent_id,
            "current_round": current_round,
            "max_rounds": max_rounds,
            "offered_price": offered_price,
            "quantity": quantity,
            "agreed_price": None,
            "counter_price": None,
            "status": "PROCESSING",
            "message": "",
            "payment_link": None,
            "audit_history": []
        }

        # Step 1: Check Round Boundary
        if current_round > max_rounds:
            state["status"] = "REJECTED_MAX_ROUNDS"
            state["message"] = f"Negotiation failed. Exceeded maximum allowed rounds ({max_rounds})."
            
            log_audit_event(
                negotiation_id=negotiation_id,
                action="GRAPH_TERMINATED",
                requested_amount=offered_price,
                status="REJECTED_MAX_ROUNDS",
                reasoning=state["message"]
            )
            return state

        # Step 2: Evaluate Guardrails
        try:
            guardrail_res = FinancialGuardrailEngine.validate_offer(
                negotiation_id=negotiation_id,
                product_id=product_id,
                requested_price=offered_price,
                original_price=original_price,
                merchant_floor=merchant_floor,
                quantity=quantity
            )

            # Node Transition -> GENERATE_PAYMENT
            state["status"] = "ACCEPTED"
            state["agreed_price"] = offered_price
            state["message"] = "Offer accepted. Payment link generated."

            # Invoke Razorpay Integration
            payment_res = razorpay_client.create_negotiated_payment_link(
                negotiation_id=negotiation_id,
                amount_inr=offered_price,
                description=f"Negotiated deal for {quantity}x {product_name}"
            )
            state["payment_link"] = payment_res.get("short_url")

        except FinancialGuardrailException as exc:
            # Node Transition -> EMIT_COUNTER
            state["status"] = "COUNTER_OFFER"
            state["counter_price"] = exc.floor_price
            state["message"] = (
                f"Offered price ₹{offered_price} is below merchant floor. "
                f"Minimum acceptable price is ₹{exc.floor_price}."
            )

            log_audit_event(
                negotiation_id=negotiation_id,
                action="EMIT_COUNTER_OFFER",
                requested_amount=offered_price,
                status="COUNTER_PROPOSED",
                reasoning=f"Round {current_round}/{max_rounds}: Counter-offer ₹{exc.floor_price} emitted."
            )

        return state