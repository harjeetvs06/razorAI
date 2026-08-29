from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from app.config import settings
from app.audit.logger import log_audit_event


class FinancialGuardrailException(Exception):
    """
    Raised when an incoming buyer offer or LLM counter-offer 
    violates merchant guardrails or global safety bounds.
    """
    def __init__(
        self, 
        message: str, 
        requested_price: float, 
        floor_price: float, 
        negotiation_id: Optional[str] = None
    ):
        super().__init__(message)
        self.message = message
        self.requested_price = requested_price
        self.floor_price = floor_price
        self.negotiation_id = negotiation_id


class GuardrailEvaluationResult(BaseModel):
    is_valid: bool
    requested_price: float
    calculated_floor: float
    applied_discount_pct: float
    rule_applied: str
    rejection_reason: Optional[str] = None


class FinancialGuardrailEngine:
    """
    Enforces deterministic financial rules over dynamic AI negotiations.
    Never relies on the LLM to perform bound checks.
    """

    @staticmethod
    def calculate_floor_price(
        original_price: float,
        merchant_floor: Optional[float] = None,
        merchant_max_discount_pct: Optional[float] = None
    ) -> float:
        """
        Calculates the highest valid floor price considering global settings 
        and specific merchant product overrides.
        """
        # 1. Start with global max discount cap
        global_floor = original_price * (1.0 - settings.GLOBAL_MAX_DISCOUNT_PCT)
        
        # 2. Apply merchant-specific max discount pct override if set
        if merchant_max_discount_pct is not None:
            merchant_pct_floor = original_price * (1.0 - merchant_max_discount_pct)
            global_floor = max(global_floor, merchant_pct_floor)

        # 3. Apply absolute hard floor price if set by merchant
        if merchant_floor is not None:
            final_floor = max(global_floor, merchant_floor)
        else:
            final_floor = global_floor

        # Round up to 2 decimal places
        return round(final_floor, 2)

    @classmethod
    def validate_offer(
        cls,
        negotiation_id: str,
        product_id: str,
        requested_price: float,
        original_price: float,
        merchant_floor: Optional[float] = None,
        merchant_max_discount_pct: Optional[float] = None,
        quantity: int = 1
    ) -> GuardrailEvaluationResult:
        """
        Strictly validates an offer against floor prices, discount caps, and volume constraints.
        Raises FinancialGuardrailException if bounds are breached.
        """
        # Step 1: Compute floor price dynamically
        floor_price = cls.calculate_floor_price(
            original_price=original_price,
            merchant_floor=merchant_floor,
            merchant_max_discount_pct=merchant_max_discount_pct
        )

        effective_unit_price = requested_price / quantity if quantity > 1 else requested_price
        applied_discount = round((1.0 - (effective_unit_price / original_price)) * 100, 2)

        # Step 2: Bound Check 1 - Price below floor threshold
        if effective_unit_price < floor_price:
            reasoning = (
                f"Offered unit price ₹{effective_unit_price:.2f} violates hard floor boundary "
                f"of ₹{floor_price:.2f} (Max allowed discount applied)."
            )
            
            # Log structured audit entry
            log_audit_event(
                negotiation_id=negotiation_id,
                action="GUARDRAIL_INTERVENTION",
                requested_amount=requested_price,
                status="REJECTED_BOUND_BREACH",
                reasoning=reasoning
            )

            raise FinancialGuardrailException(
                message=reasoning,
                requested_price=requested_price,
                floor_price=floor_price * quantity,
                negotiation_id=negotiation_id
            )

        # Step 3: Bound Check 2 - Price exceeds original price (Sanity check)
        if effective_unit_price > original_price * 1.5:
            reasoning = f"Offered price ₹{requested_price} exceeds reasonable upper bounds."
            
            log_audit_event(
                negotiation_id=negotiation_id,
                action="SANITY_INTERVENTION",
                requested_amount=requested_price,
                status="REJECTED_OUTLIER",
                reasoning=reasoning
            )
            
            raise FinancialGuardrailException(
                message=reasoning,
                requested_price=requested_price,
                floor_price=original_price * quantity,
                negotiation_id=negotiation_id
            )

        # Step 4: Approved Execution Log
        log_audit_event(
            negotiation_id=negotiation_id,
            action="OFFER_VALIDATED",
            requested_amount=requested_price,
            status="APPROVED",
            reasoning=f"Offer of ₹{requested_price} for Qty {quantity} is within safe floor limit of ₹{floor_price * quantity}."
        )

        return GuardrailEvaluationResult(
            is_valid=True,
            requested_price=requested_price,
            calculated_floor=floor_price * quantity,
            applied_discount_pct=applied_discount,
            rule_applied="FloorAndMarginGuardrailV1"
        )