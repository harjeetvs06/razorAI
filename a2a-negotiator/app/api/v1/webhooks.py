import logging
from typing import Dict, Any
from fastapi import APIRouter, Request, Header, HTTPException, status
from app.integrations.razorpay_client import razorpay_client
from app.audit.logger import log_audit_event

logger = logging.getLogger("razorpay_webhooks")
router = APIRouter()


@router.post("", status_code=status.HTTP_200_OK)
async def handle_razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None, alias="X-Razorpay-Signature")
):
    """
    Razorpay Webhook Handler.
    Verifies payload signatures and processes payment events 
    (payment.captured, payment_link.paid) to finalize A2A negotiations.
    """
    body_bytes = await request.body()

    # Step 1: Mandatory Security Signature Verification
    if x_razorpay_signature and not razorpay_client.verify_webhook_signature(body_bytes, x_razorpay_signature):
        log_audit_event(
            negotiation_id="unknown",
            action="WEBHOOK_SIGNATURE_FAILED",
            requested_amount=0.0,
            status="REJECTED_UNAUTHORIZED",
            reasoning="Incoming webhook signature failed HMAC verification."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature."
        )

    # Step 2: Parse Webhook Payload JSON
    try:
        payload: Dict[str, Any] = await request.json()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Malformed JSON payload: {str(e)}"
        )

    event_type = payload.get("event")
    logger.info(f"Received Razorpay Webhook Event: {event_type}")

    # Step 3: Extract Payment Metadata
    if event_type in ["payment_link.paid", "payment.captured"]:
        payment_entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        payment_link_entity = payload.get("payload", {}).get("payment_link", {}).get("entity", {})

        # Retrieve metadata attached during link creation
        notes = payment_link_entity.get("notes") or payment_entity.get("notes") or {}
        negotiation_id = notes.get("negotiation_id", "unknown_neg_id")
        
        amount_in_paise = payment_entity.get("amount", 0)
        amount_in_inr = amount_in_paise / 100.0
        payment_id = payment_entity.get("id")
        payment_link_id = payment_link_entity.get("id")

        # Step 4: Finalize Negotiation State & Audit
        log_audit_event(
            negotiation_id=negotiation_id,
            action="TRANSACTION_FINALIZED",
            requested_amount=amount_in_inr,
            status="SUCCESS_PAID",
            reasoning=(
                f"Payment captured successfully via Razorpay. "
                f"Payment ID: {payment_id} | Link ID: {payment_link_id}"
            )
        )

        logger.info(
            f"[Negotiation: {negotiation_id}] Payment of ₹{amount_in_inr} confirmed. "
            f"Transaction successfully closed."
        )

        # TODO: Update DB record status to 'COMPLETED' and decrement merchant inventory

        return {
            "status": "processed",
            "event": event_type,
            "negotiation_id": negotiation_id,
            "payment_id": payment_id
        }

    # Handle unhandled event types gracefully without failing
    logger.info(f"Ignored unhandled webhook event: {event_type}")
    return {"status": "ignored", "event": event_type}