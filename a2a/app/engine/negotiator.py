"""
Negotiation engine – stateless pricing logic.
All decisions produce a full audit trail so every rupee action is explainable.
"""
from __future__ import annotations
import uuid, time
from typing import List

from app.models.schemas import (
    BuyerRequest, NegotiationResult, NegotiationStatus, AuditStep,
)
from app.engine.guardrails import (
    check_stock, check_shipping_sla, check_financial_bounds,
)

# In-memory catalog (replace with DB queries in prod)
CATALOG: dict = {
    "SKU-001": {
        "name": "Wireless Earbuds Pro",
        "base_price": 2499, "stock": 120,
        "min_margin_pct": 18, "cost_price": 1400,
        "max_bulk_discount_pct": 22, "shipping_sla_days": 3,
        "image_key": "earbuds", "category": "Electronics",
    },
    "SKU-002": {
        "name": "Smart Water Bottle",
        "base_price": 999, "stock": 45,
        "min_margin_pct": 20, "cost_price": 550,
        "max_bulk_discount_pct": 18, "shipping_sla_days": 2,
        "image_key": "bottle", "category": "Lifestyle",
    },
    "SKU-003": {
        "name": "Mechanical Keyboard",
        "base_price": 4999, "stock": 30,
        "min_margin_pct": 15, "cost_price": 2800,
        "max_bulk_discount_pct": 20, "shipping_sla_days": 4,
        "image_key": "keyboard", "category": "Electronics",
    },
    "SKU-004": {
        "name": "Bamboo Desk Organiser",
        "base_price": 599, "stock": 200,
        "min_margin_pct": 25, "cost_price": 250,
        "max_bulk_discount_pct": 30, "shipping_sla_days": 2,
        "image_key": "organiser", "category": "Lifestyle",
    },
    "SKU-005": {
        "name": "USB-C Hub 7-in-1",
        "base_price": 1799, "stock": 80,
        "min_margin_pct": 20, "cost_price": 950,
        "max_bulk_discount_pct": 25, "shipping_sla_days": 3,
        "image_key": "hub", "category": "Electronics",
    },
    "SKU-006": {
        "name": "Ergonomic Mouse Pad XL",
        "base_price": 449, "stock": 300,
        "min_margin_pct": 30, "cost_price": 150,
        "max_bulk_discount_pct": 35, "shipping_sla_days": 2,
        "image_key": "mousepad", "category": "Lifestyle",
    },
}


def _bulk_discount_pct(qty: int, max_pct: float) -> float:
    """Smooth tiered curve, capped at max_pct."""
    tiers = [(500, 1.0), (200, 0.85), (100, 0.70), (50, 0.55), (20, 0.40), (10, 0.25)]
    for threshold, ratio in tiers:
        if qty >= threshold:
            return round(min(max_pct, max_pct * ratio), 2)
    return 0.0


def run_negotiation(req: BuyerRequest, razorpay_link: str = "", order_id: str = "") -> NegotiationResult:
    neg_id = f"NEG-{uuid.uuid4().hex[:10].upper()}"
    item   = CATALOG[req.sku]
    audit: List[AuditStep] = []
    gates: List[str] = []
    step = 0

    def add(action: str, value: float, reason: str, gate: str | None = None):
        nonlocal step
        step += 1
        audit.append(AuditStep(step=step, action=action, value=value, reason=reason))
        if gate:
            gates.append(gate)

    # GATE 1 – catalog check
    add("catalog_check", 1, f"SKU {req.sku} resolved to '{item['name']}'",
        f"✓ Product found: {item['name']}")

    # GATE 2 – stock
    stock_r = check_stock(req.quantity, item["stock"])
    add("stock_gate", item["stock"], stock_r.reason,
        f"{'✓' if stock_r.passed else '✗'} Stock: {stock_r.reason}")
    if not stock_r.passed:
        return _reject(neg_id, req, item, audit, gates, stock_r.reason, razorpay_link)

    # GATE 3 – implied unit price
    implied_unit = round(req.budget_total / req.quantity, 2)
    add("price_parse", implied_unit,
        f"₹{req.budget_total} ÷ {req.quantity} units = ₹{implied_unit}/unit",
        f"✓ Implied unit price: ₹{implied_unit}")

    # GATE 4 – shipping SLA
    sla_r = check_shipping_sla(req.delivery_deadline_days, item["shipping_sla_days"])
    add("sla_gate", item["shipping_sla_days"], sla_r.reason,
        f"{'✓' if sla_r.passed else '✗'} SLA: {sla_r.reason}")
    if not sla_r.passed:
        return _reject(neg_id, req, item, audit, gates, sla_r.reason, razorpay_link)

    # GATE 5 – bulk discount offer
    bulk_pct      = _bulk_discount_pct(req.quantity, item["max_bulk_discount_pct"])
    offered_price = round(item["base_price"] * (1 - bulk_pct / 100), 2)
    add("bulk_curve", bulk_pct,
        f"Qty {req.quantity} → {bulk_pct}% bulk discount → ₹{offered_price}/unit",
        f"✓ Bulk offer computed: ₹{offered_price}/unit ({bulk_pct}% off)")

    # GATE 6 – financial bounds
    target = min(implied_unit, offered_price)  # never charge more than buyer's budget
    fin_r  = check_financial_bounds(
        offer_price=target,
        cost_price=item["cost_price"],
        base_price=item["base_price"],
        min_margin_pct=item["min_margin_pct"],
        max_bulk_discount_pct=item["max_bulk_discount_pct"],
    )
    add("financial_bounds", fin_r.effective_floor, fin_r.reason,
        f"{'✓' if fin_r.passed else '✗'} Margin floor: ₹{fin_r.effective_floor}")

    # ── Decision ──────────────────────────────────────────────────────────────
    if implied_unit >= offered_price and fin_r.passed:
        final_price = offered_price
        status      = NegotiationStatus.ACCEPTED
        explanation = (
            f"Buyer budget ₹{implied_unit}/unit ≥ bulk-discounted offer ₹{offered_price}/unit "
            f"({bulk_pct}% off). Deal accepted immediately."
        )
        add("ACCEPT_AND_GENERATE_PAYMENT_LINK", final_price, explanation,
            "✓ ACCEPTED — payment link generated")

    elif fin_r.passed:
        # buyer's price is between floor and our standard offer → counter-accept at buyer's price
        final_price = implied_unit
        status      = NegotiationStatus.COUNTER
        explanation = (
            f"Buyer price ₹{implied_unit}/unit < our offer ₹{offered_price}/unit "
            f"but ≥ margin floor ₹{fin_r.effective_floor}. Counter-accepted at buyer's price."
        )
        add("COUNTER_ACCEPT", final_price, explanation,
            f"✓ COUNTER-ACCEPTED at ₹{final_price}")

    else:
        gates.append(f"✗ REJECTED — below floor ₹{fin_r.effective_floor}")
        return _reject(neg_id, req, item, audit, gates, fin_r.reason, razorpay_link)

    total    = round(final_price * req.quantity, 2)
    disc_pct = round((1 - final_price / item["base_price"]) * 100, 1)

    return NegotiationResult(
        negotiation_id=neg_id,
        status=status,
        sku=req.sku,
        product_name=item["name"],
        quantity=req.quantity,
        unit_price=final_price,
        total_price=total,
        discount_pct=disc_pct,
        base_price=item["base_price"],
        stock_available=item["stock"],
        shipping_days=item["shipping_sla_days"],
        payment_link=razorpay_link or f"https://rzp.io/pay/{neg_id.lower()}",
        razorpay_order_id=order_id or None,
        audit_trail=audit,
        explanation=explanation,
        gates_checked=gates,
        timestamp=time.time(),
    )


def _reject(neg_id, req, item, audit, gates, reason, link="") -> NegotiationResult:
    import time
    return NegotiationResult(
        negotiation_id=neg_id,
        status=NegotiationStatus.REJECTED,
        sku=req.sku,
        product_name=item["name"],
        quantity=req.quantity,
        unit_price=0, total_price=0, discount_pct=0,
        base_price=item["base_price"],
        stock_available=item["stock"],
        shipping_days=item["shipping_sla_days"],
        payment_link="",
        razorpay_order_id=None,
        audit_trail=audit,
        explanation=reason,
        gates_checked=gates,
        timestamp=time.time(),
    )


def get_catalog_items():
    from app.models.schemas import CatalogItem
    return [
        CatalogItem(
            sku=sku, name=d["name"], base_price=d["base_price"],
            stock=d["stock"], category=d["category"],
            shipping_sla_days=d["shipping_sla_days"],
            image_key=d["image_key"],
        )
        for sku, d in CATALOG.items()
    ]
