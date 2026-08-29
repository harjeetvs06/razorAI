import logging
import time
from typing import Dict, Any, Optional
import razorpay
from razorpay.errors import BadRequestError, SignatureVerificationError, ServerError
from fastapi import HTTPException, status

from app.config import settings
from app.audit.logger import log_audit_event

logger = logging.getLogger("razorpay_integration")


class RazorpayClientWrapper:
    """
    Razorpay SDK integration wrapper.
    Handles dynamic payment link generation, expiration, and webhook signature verification.
    """

    def __init__(self):
        if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
            self.client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
            logger.info("Razorpay Client SDK initialized.")
        else:
            self.client = None
            logger.warning("Razorpay credentials not found. Running in MOCK mode.")

    def create_negotiated_payment_link(
        self,
        negotiation_id: str,
        amount_inr: float,
        description: str,
        customer_email: Optional[str] = "buyer_agent@a2a-commerce.ai",
        customer_phone: Optional[str] = "9999999999",
        expire_minutes: int = 15
    ) -> Dict[str, Any]:
        """
        Creates a single-use Razorpay payment link for an accepted negotiated deal.
        Converts human/agent INR values to integer paise (Razorpay standard).
        """
        # Convert INR (e.g. 45000.00) to Paise integer (4500000)
        amount_in_paise = int(round(amount_inr * 100))
        expire_timestamp = int(time.time()) + (expire_minutes * 60)

        payload = {
            "amount": amount_in_paise,
            "currency": "INR",
            "accept_partial": False,
            "description": f"A2A Deal [{negotiation_id}]: {description}",
            "customer": {
                "name": f"Agent Buyer ({negotiation_id})",
                "email": customer_email,
                "contact": customer_phone
            },
            "notify": {
                "sms": False,
                "email": True
            },
            "reminder_enable": False,
            "notes": {
                "negotiation_id": negotiation_id,
                "source": "Razorpay_A2A_Negotiator_Engine",
                "track": "Track_1_Agentic_Commerce"
            },
            "expire_by": expire_timestamp
        }

        # Mock Fallback when running local tests without API keys
        if not self.client:
            mock_url = f"https://rzp.io/i/mock_{negotiation_id}"
            log_audit_event(
                negotiation_id=negotiation_id,
                action="RAZORPAY_LINK_MOCK_CREATED",
                requested_amount=amount_inr,
                status="MOCK_GENERATED",
                reasoning="Credentials missing. Emitted mock payment link."
            )
            return {
                "payment_link_id": f"plink_mock_{negotiation_id}",
                "short_url": mock_url,
                "amount": amount_inr,
                "status": "created",
                "is_mock": True
            }

        try:
            # Official SDK call
            response = self.client.payment_link.create(payload)

            log_audit_event(
                negotiation_id=negotiation_id,
                action="RAZORPAY_PAYMENT_LINK_CREATED",
                requested_amount=amount_inr,
                status="SUCCESS",
                reasoning=f"Payment link generated successfully. Link ID: {response.get('id')}"
            )

            return {
                "payment_link_id": response.get("id"),
                "short_url": response.get("short_url"),
                "amount": amount_inr,
                "currency": response.get("currency"),
                "status": response.get("status"),
                "expire_by": response.get("expire_by"),
                "is_mock": False
            }

        except (BadRequestError, ServerError, SignatureVerificationError) as exc:
            error_msg = f"Razorpay API Error: {str(exc)}"
            logger.error(f"[{negotiation_id}] {error_msg}")

            log_audit_event(
                negotiation_id=negotiation_id,
                action="RAZORPAY_PAYMENT_LINK_FAILED",
                requested_amount=amount_inr,
                status="FAILED_HANDLED",
                reasoning=error_msg
            )
            
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "status": "GATEWAY_ERROR",
                    "message": "Offer accepted, but payment link creation failed.",
                    "error": str(exc)
                }
            )

    def verify_webhook_signature(self, body_bytes: bytes, signature: str) -> bool:
        """
        Verifies HMAC SHA256 signature for incoming Razorpay webhook calls.
        """
        if not settings.RAZORPAY_WEBHOOK_SECRET:
            logger.warning("RAZORPAY_WEBHOOK_SECRET not set. Skipping verification.")
            return True

        try:
            self.client.utility.verify_webhook_signature(
                body_bytes.decode("utf-8"),
                signature,
                settings.RAZORPAY_WEBHOOK_SECRET
            )
            return True
        except SignatureVerificationError:
            logger.error("Razorpay webhook signature verification failed.")
            return False


# Shared Singleton Instance
razorpay_client = RazorpayClientWrapper()