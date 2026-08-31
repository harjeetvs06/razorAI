"""
LangGraph-style state machine for the negotiation lifecycle.
States: INCOMING_INTENT → EVALUATE_REQUEST → CHECK_GUARDRAILS
        → COUNTER / ACCEPT → CREATE_RAZORPAY_LINK → RETURN_PAYLOAD
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class NegotiationState(str, Enum):
    INCOMING_INTENT      = "incoming_intent"
    EVALUATE_REQUEST     = "evaluate_request"
    CHECK_GUARDRAILS     = "check_guardrails"
    COUNTER              = "counter"
    ACCEPT               = "accept"
    CREATE_PAYMENT_LINK  = "create_payment_link"
    RETURN_PAYLOAD       = "return_payload"
    REJECTED             = "rejected"


@dataclass
class NegotiationContext:
    buyer_agent_id: str
    sku: str
    quantity: int
    budget_total: float
    delivery_deadline_days: Optional[int] = None
    current_state: NegotiationState = NegotiationState.INCOMING_INTENT
    agreed_price: Optional[float] = None
    rejection_reason: Optional[str] = None
    history: List[str] = field(default_factory=list)

    def transition(self, to: NegotiationState, note: str = ""):
        self.history.append(f"{self.current_state.value} → {to.value}" + (f": {note}" if note else ""))
        self.current_state = to


def build_graph_trace(ctx: NegotiationContext) -> List[str]:
    """Return the full state transition trace for audit purposes."""
    return ctx.history
