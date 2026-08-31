"""
Guardrails – hard financial boundaries enforced before any money action.
Every check is explicit, ordered, and returns a reason string so the
audit trail is always populated even on rejection.
"""
from dataclasses import dataclass
from typing import Tuple


@dataclass
class GuardrailResult:
    passed: bool
    reason: str
    effective_floor: float = 0.0


def check_stock(requested: int, available: int) -> GuardrailResult:
    if requested > available:
        return GuardrailResult(
            passed=False,
            reason=f"Insufficient stock: requested {requested}, available {available}.",
        )
    return GuardrailResult(
        passed=True,
        reason=f"Stock OK: {available} units available, {requested} requested.",
    )


def check_shipping_sla(deadline_days: int | None, sla_days: int) -> GuardrailResult:
    if deadline_days is None:
        return GuardrailResult(passed=True, reason="No delivery deadline specified.")
    if deadline_days < sla_days:
        return GuardrailResult(
            passed=False,
            reason=f"Shipping SLA unmet: buyer needs {deadline_days}d, our SLA is {sla_days}d.",
        )
    return GuardrailResult(
        passed=True,
        reason=f"Shipping SLA met: {deadline_days}d deadline ≥ {sla_days}d SLA.",
    )


def check_financial_bounds(
    offer_price: float,
    cost_price: float,
    base_price: float,
    min_margin_pct: float,
    max_bulk_discount_pct: float,
) -> GuardrailResult:
    """
    Dual guard:
      1. Cost + minimum margin floor
      2. Maximum bulk discount cap off base price
    The effective floor is the stricter of the two.
    """
    margin_floor   = round(cost_price * (1 + min_margin_pct / 100), 2)
    discount_floor = round(base_price * (1 - max_bulk_discount_pct / 100), 2)
    effective_floor = max(margin_floor, discount_floor)

    if offer_price < effective_floor:
        return GuardrailResult(
            passed=False,
            reason=(
                f"Price ₹{offer_price} < floor ₹{effective_floor} "
                f"(margin floor ₹{margin_floor}, discount floor ₹{discount_floor})."
            ),
            effective_floor=effective_floor,
        )
    return GuardrailResult(
        passed=True,
        reason=(
            f"Price ₹{offer_price} ≥ floor ₹{effective_floor}. "
            f"Margin floor ₹{margin_floor}, discount floor ₹{discount_floor}."
        ),
        effective_floor=effective_floor,
    )
