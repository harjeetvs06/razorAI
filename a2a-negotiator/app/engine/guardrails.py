import logging
from typing import Dict, Any, Optional
from app.audit.logger import log_audit_event

logger = logging.getLogger("guardrails_engine")


class FinancialGuardrailException(Exception):
    """
    Raised when an incoming agent proposal violates hard merchant constraints.
    Contains metadata required to generate automated counter-offers.
    """
    def __init__(
        self, 
        message: str, 
        floor_price: float, 
        requested_price: float, 
        violation_code: str
    ):
        super().__init__(message)
        self.message = message
        self.floor_price = floor_price
        self.requested_price = requested_price
        self.violation_code = violation_code


class FinancialGuardrailEngine:
    """
    Deterministic mathematical guardrail validator.
    Ensures buyer agent proposals strictly conform to business rules.
    """

    @classmethod
    def validate_offer(
        cls,
        negotiation_id: str,
        product_id: str,
        requested_price: float,
        original_price: float,
        merchant_floor: float,
        quantity: int = 1,
        max_discount_pct: float = 0.20
    ) -> Dict[str, Any]:
        """
        Validates an incoming price proposal against guardrail policies.
        
        Raises:
            FinancialGuardrailException: If requested price breaches the hard floor or caps.
            ValueError: If payload data contains invalid numeric values.
        """
        # Step 1: Sanity & Input Integrity Checks
        if requested_price <= 0:
            log_audit_event(
                negotiation_id=negotiation_id,
                action="GUARDRAIL_BLOCKED_ZERO_OR_NEGATIVE",
                requested_amount=requested_price,
                status="REJECTED_ANOMALY",
                reasoning="Requested price must be greater than zero."
            )
            raise ValueError("Requested price must be greater than zero.")

        if quantity < 1:
            raise ValueError("Order quantity must be at least 1.")

        # Step 2: Compute Maximum Allowed Discount Price
        effective_floor = max(merchant_floor, original_price * (1.0 - max_discount_pct))

        # Step 3: Hard Floor Validation
        if requested_price < effective_floor:
            reasoning_msg = (
                f"Proposed price ₹{requested_price:,.2f} is below effective floor "
                f"of ₹{effective_floor:,.2f} (Original: ₹{original_price:,.2f}, Floor: ₹{merchant_floor:,.2f})."
            )

            log_audit_event(
                negotiation_id=negotiation_id,
                action="GUARDRAIL_FLOOR_BREACH",
                requested_amount=requested_price,
                status="COUNTER_PROPOSED",
                reasoning=reasoning_msg,
                extra_metadata={
                    "original_price": original_price,
                    "effective_floor": effective_floor,
                    "delta": effective_floor - requested_price
                }
            )

            raise FinancialGuardrailException(
                message=reasoning_msg,
                floor_price=effective_floor,
                requested_price=requested_price,
                violation_code="BELOW_MERCHANT_FLOOR"
            )

        # Step 4: Upper Limit Sanity Check
        if requested_price > original_price:
            logger.warning(
                f"[{negotiation_id}] Buyer offered ₹{requested_price}, which is above list price ₹{original_price}."
            )

        # Step 5: Successful Guardrail Pass
        log_audit_event(
            negotiation_id=negotiation_id,
            action="GUARDRAIL_EVALUATION_PASSED",
            requested_amount=requested_price,
            status="PASSED",
            reasoning=f"Requested price ₹{requested_price:,.2f} meets or exceeds floor ₹{effective_floor:,.2f}."
        )

        return {
            "is_valid": True,
            "agreed_price": requested_price,
            "effective_floor": effective_floor,
            "original_price": original_price,
            "savings_for_buyer": original_price - requested_price
        }