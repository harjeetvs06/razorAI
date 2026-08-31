"""
Structured audit logger – generates explainable AI decision records.
Each negotiation emits a JSON-serialisable log fulfilling Track 1's
"explainable, bounded, gated" requirement.
"""
import json, logging, time
from app.models.schemas import NegotiationResult

_log = logging.getLogger("razorai.audit")


def emit_negotiation_log(result: NegotiationResult) -> dict:
    record = {
        "negotiation_id":   result.negotiation_id,
        "timestamp":        result.timestamp,
        "buyer_agent":      "n/a",
        "sku":              result.sku,
        "product":          result.product_name,
        "quantity":         result.quantity,
        "requested_budget": result.base_price * result.quantity,
        "floor_price":      None,          # populated by guardrail gate
        "final_unit_price": result.unit_price,
        "total_price":      result.total_price,
        "discount_pct":     result.discount_pct,
        "status":           result.status.value,
        "action": (
            "ACCEPT_AND_GENERATE_PAYMENT_LINK" if result.status == "accepted"
            else "COUNTER_AND_GENERATE_PAYMENT_LINK" if result.status == "counter"
            else "REJECT_NO_PAYMENT_LINK"
        ),
        "reason":           result.explanation,
        "razorpay_order_id":result.razorpay_order_id,
        "payment_link":     result.payment_link,
        "gates_checked":    result.gates_checked,
        "audit_trail":      [s.model_dump() for s in result.audit_trail],
    }
    _log.info("AUDIT | %s", json.dumps(record))
    return record
