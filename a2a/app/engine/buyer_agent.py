"""Buyer-side agent policy: decides when to accept, counter, or walk away."""
import logging
from dataclasses import dataclass
from app.models.schemas import NegotiationResult, NegotiationStatus

log = logging.getLogger("razorai.buyer_agent")

@dataclass
class BuyerPolicy:
    """Buyer agent's negotiation parameters."""
    max_budget_per_unit: float
    min_acceptable_qty: int
    max_rounds: int = 3
    flexibility_pct: float = 5.0  # how much it'll concede per round

@dataclass
class BuyerMove:
    action: str  # "ACCEPT", "COUNTER", "WALK_AWAY"
    reason: str
    new_budget_per_unit: float = 0  # only if action == "COUNTER"

def decide_buyer_move(
    policy: BuyerPolicy,
    merchant_response: NegotiationResult,
    round_num: int,
) -> BuyerMove:
    """Decide what the buyer agent does next."""
    
    if merchant_response.status == NegotiationStatus.ACCEPTED:
        log.info(f"[BUYER] Round {round_num}: Merchant accepted. Deal done.")
        return BuyerMove(
            action="ACCEPT",
            reason="Merchant accepted our first offer.",
        )
    
    if merchant_response.status == NegotiationStatus.REJECTED:
        log.info(f"[BUYER] Round {round_num}: Merchant rejected. Walking away.")
        return BuyerMove(
            action="WALK_AWAY",
            reason=f"Merchant rejected: {merchant_response.explanation}",
        )
    
    if merchant_response.status == NegotiationStatus.COUNTER:
        counter_price = merchant_response.unit_price
        
        # Check if counter is within buyer's ceiling
        if counter_price <= policy.max_budget_per_unit:
            log.info(f"[BUYER] Round {round_num}: Counter ₹{counter_price}/unit ≤ ceiling ₹{policy.max_budget_per_unit}. Accepting.")
            return BuyerMove(
                action="ACCEPT",
                reason=f"Merchant's counter ₹{counter_price}/unit is within our budget ceiling ₹{policy.max_budget_per_unit}.",
            )
        
        # Counter is above budget, but check if we have room to negotiate further
        if round_num >= policy.max_rounds:
            log.info(f"[BUYER] Round {round_num}: Max rounds reached, no agreement.")
            return BuyerMove(
                action="WALK_AWAY",
                reason=f"Merchant countered at ₹{counter_price}/unit, above our ceiling ₹{policy.max_budget_per_unit}. Max {policy.max_rounds} rounds reached.",
            )
        
        # Still have rounds left — propose a middle ground
        gap = counter_price - policy.max_budget_per_unit
        concession = counter_price * (policy.flexibility_pct / 100)
        new_offer = counter_price - min(gap * 0.5, concession)  # move halfway, but respect flexibility limit
        
        log.info(f"[BUYER] Round {round_num}: Counter ₹{counter_price} > ceiling ₹{policy.max_budget_per_unit}. Proposing ₹{new_offer:.2f}.")
        return BuyerMove(
            action="COUNTER",
            reason=f"Merchant countered at ₹{counter_price}/unit (above our ₹{policy.max_budget_per_unit} ceiling). Proposing middle ground ₹{new_offer:.2f}.",
            new_budget_per_unit=new_offer,
        )
    
    # Fallback (shouldn't happen)
    return BuyerMove(
        action="WALK_AWAY",
        reason="Unknown merchant response status.",
    )