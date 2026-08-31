"""Razorpay webhook listener – handles payment.captured events."""
import json, logging
from fastapi import APIRouter, Request, HTTPException, Header
from app.integrations.razorpay_client import verify_webhook_signature

router = APIRouter()
log    = logging.getLogger("razorai.webhooks")


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    x_razorpay_signature: str = Header(None),
):
    body = await request.body()

    if x_razorpay_signature:
        if not verify_webhook_signature(body, x_razorpay_signature):
            raise HTTPException(400, "Invalid webhook signature.")

    event = json.loads(body)
    log.info("Webhook event: %s", event.get("event", "unknown"))

    if event.get("event") == "payment.captured":
        payment = event["payload"]["payment"]["entity"]
        log.info(
            "Payment captured | order=%s amount=₹%s",
            payment.get("order_id"), payment.get("amount", 0) / 100,
        )
        # TODO: update negotiation status in DB to "payment_captured"

    return {"status": "ok"}
