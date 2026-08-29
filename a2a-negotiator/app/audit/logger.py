import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Configure standard Python logger for financial audit trails
audit_logger = logging.getLogger("financial_audit")
audit_logger.setLevel(logging.INFO)

# Prevent duplicate handlers if module is re-imported
if not audit_logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # Simple plain-text format wrapping raw structured JSON string
    formatter = logging.Formatter("%(message)s")
    console_handler.setFormatter(formatter)
    audit_logger.addHandler(console_handler)


def log_audit_event(
    negotiation_id: str,
    action: str,
    requested_amount: float,
    status: str,
    reasoning: str,
    extra_metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Emits a structured JSON audit log entry for every financial decision.
    
    Args:
        negotiation_id: Unique identifier for the transaction lifecycle.
        action: System event (e.g., 'GUARDRAIL_INTERVENTION', 'RAZORPAY_LINK_CREATED').
        requested_amount: Offered or calculated monetary value in INR.
        status: Execution status ('APPROVED', 'REJECTED_BOUND_BREACH', 'SUCCESS_PAID').
        reasoning: Human-readable explainability string detailing WHY the decision was made.
        extra_metadata: Additional key-value pairs (e.g., product_id, discount_pct).
        
    Returns:
        Dict representing the exact logged audit record.
    """
    audit_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "negotiation_id": negotiation_id,
        "action": action,
        "requested_amount": requested_amount,
        "status": status,
        "reasoning": reasoning,
        "explainability": {
            "is_bounded": True,
            "rule_engine": "FinancialGuardrailV1"
        }
    }

    if extra_metadata:
        audit_entry["metadata"] = extra_metadata

    # Convert to JSON string for log aggregators (e.g., Datadog, CloudWatch, ELK)
    audit_json = json.dumps(audit_entry)
    audit_logger.info(audit_json)

    # TODO: In production, write asynchronously to PostgreSQL `audit_logs` table
    return audit_entry