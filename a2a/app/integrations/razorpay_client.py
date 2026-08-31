"""
Razorpay integration – Orders + Payment Links.
Uses razorpay SDK; falls back to mock link in test/dev.
"""
from __future__ import annotations
import hashlib, hmac, logging
from app.config import settings

log = logging.getLogger(__name__)


def _get_client():
    try:
        import razorpay
        return razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
    except Exception:
        return None


def create_order(amount_inr: float, currency: str = "INR", receipt: str = "") -> dict:
    """Create a Razorpay order for the negotiated amount."""
    amount_paise = int(amount_inr * 100)
    client = _get_client()

    if client is None or settings.APP_ENV == "development":
        log.info(f"[MOCK] Creating order ₹{amount_inr}")
        return {
            "id": f"order_MOCK{hashlib.md5(receipt.encode()).hexdigest()[:12].upper()}",
            "amount": amount_paise,
            "currency": currency,
            "status": "created",
        }

    data = {
        "amount": amount_paise,
        "currency": currency,
        "receipt": receipt[:40],
        "payment_capture": 1,
    }
    return client.order.create(data=data)


def create_payment_link(
    amount_inr: float,
    description: str,
    negotiation_id: str,
    expire_by: int | None = None,
) -> dict:
    """Create a single-use payment link valid for this negotiation only."""
    client = _get_client()

    if client is None or settings.APP_ENV == "development":
        token = hashlib.sha256(f"{negotiation_id}:{amount_inr}".encode()).hexdigest()[:10]
        log.info(f"[MOCK] Payment link for ₹{amount_inr}")
        return {
            "id": f"plink_{token}",
            "short_url": f"https://rzp.io/pay/{negotiation_id.lower()}-{token}",
            "amount": int(amount_inr * 100),
            "status": "created",
        }

    payload: dict = {
        "amount": int(amount_inr * 100),
        "currency": "INR",
        "description": description[:255],
        "reference_id": negotiation_id,
        "callback_url": "https://your-domain.com/api/v1/webhooks/razorpay",
        "callback_method": "get",
    }
    if expire_by:
        payload["expire_by"] = expire_by

    return client.payment_link.create(payload)


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    expected = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
