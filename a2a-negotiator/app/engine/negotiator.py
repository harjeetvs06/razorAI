import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.engine.graph import NegotiationGraphEngine, NegotiationGraphState
from app.audit.logger import log_audit_event
from app.models.schemas import NegotiationRequest, NegotiationResponse, NegotiationStatusEnum

logger = logging.getLogger("negotiator_engine")


class A2ANegotiatorEngine:
    """
    High-level Orchestration Engine for Agent-to-Agent Price Negotiations.
    Converts API requests into evaluated graph decisions and counter-offers.
    """

    def __init__(self, db_session: Optional[Session] = None):
        self.db = db_session

    async def process_proposal(
        self,
        payload: NegotiationRequest,
        current_round: int = 1,
        max_rounds: int = 5
    ) -> NegotiationResponse:
        """
        Orchestrates the lifecycle of a buyer agent proposal.
        Fetches merchant context, evaluates bounds, and returns structured API responses.
        """
        # Step 1: Hydrate Product Guardrails & Constraints
        # (In production, load via self.db.query(MerchantProductRule)...)
        merchant_config = self._get_merchant_config(payload.product_id)

        if not merchant_config["is_negotiable"]:
            log_audit_event(
                negotiation_id=payload.negotiation_id,
                action="NEGOTIATION_REJECTED_NON_NEGOTIABLE",
                requested_amount=payload.offered_unit_price,
                status="REJECTED",
                reasoning=f"Product {payload.product_id} is set as non-negotiable by merchant."
            )
            return NegotiationResponse(
                negotiation_id=payload.negotiation_id,
                product_id=payload.product_id,
                status=NegotiationStatusEnum.REJECTED,
                agreed_price=None,
                counter_offered_price=None,
                reasoning="This item has a fixed price and is non-negotiable.",
                razorpay_payment_url=None,
                is_bounded=True
            )

        # Step 2: Execute State Machine Graph
        graph_result: NegotiationGraphState = await NegotiationGraphEngine.run_step(
            negotiation_id=payload.negotiation_id,
            product_id=payload.product_id,
            product_name=merchant_config["product_name"],
            original_price=merchant_config["original_price"],
            merchant_floor=merchant_config["merchant_floor"],
            offered_price=payload.offered_unit_price,
            quantity=payload.quantity,
            buyer_agent_id=payload.buyer_agent_id,
            current_round=current_round,
            max_rounds=max_rounds
        )

        # Step 3: Compute Strategic Counter-Offer (if status is COUNTER_OFFER)
        counter_price = None
        if graph_result["status"] == "COUNTER_OFFER":
            counter_price = self._calculate_concession_counter(
                original_price=merchant_config["original_price"],
                merchant_floor=merchant_config["merchant_floor"],
                current_round=current_round,
                max_rounds=max_rounds
            )

        # Step 4: Map Graph State to API Output Schema
        status_enum_map = {
            "ACCEPTED": NegotiationStatusEnum.ACCEPTED,
            "COUNTER_OFFER": NegotiationStatusEnum.COUNTER_OFFER,
            "REJECTED_MAX_ROUNDS": NegotiationStatusEnum.REJECTED,
            "REJECTED": NegotiationStatusEnum.REJECTED
        }

        return NegotiationResponse(
            negotiation_id=payload.negotiation_id,
            product_id=payload.product_id,
            status=status_enum_map.get(graph_result["status"], NegotiationStatusEnum.REJECTED),
            agreed_price=graph_result["agreed_price"],
            counter_offered_price=counter_price,
            reasoning=graph_result["message"],
            razorpay_payment_url=graph_result["payment_link"],
            is_bounded=True
        )

    def _calculate_concession_counter(
        self,
        original_price: float,
        merchant_floor: float,
        current_round: int,
        max_rounds: int
    ) -> float:
        """
        Calculates a dynamic concession price step-down per turn.
        Prevents giving away the bottom floor price on Round 1.
        """
        if current_round >= max_rounds:
            return round(merchant_floor, 2)

        # Linear decay concession curve from Original Price to Floor Price
        price_delta = original_price - merchant_floor
        step = price_delta / max_rounds
        calculated_counter = original_price - (step * current_round)

        return round(max(calculated_counter, merchant_floor), 2)

    def _get_merchant_config(self, product_id: str) -> Dict[str, Any]:
        """
        Fallback mock context solver (Replace with SQLAlchemy DB queries).
        """
        return {
            "product_id": product_id,
            "product_name": "Developer Laptop Pro",
            "original_price": 50000.00,
            "merchant_floor": 42000.00,
            "is_negotiable": True
        }