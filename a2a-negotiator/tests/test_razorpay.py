import time
import logging
from typing import Dict, Any, Optional
import razorpay
from razorpay.errors import BadRequestError, SignatureVerificationError

from app.config import settings
from app.audit.logger import log_audit_event

logger = logging.getLogger("razorpay_client")


class RazorpayClientWrapper:
    """
    Wrapper for official Razorpay SDK.
    Handles order creation, single-use payment links, and webhook verification.
    """

    def __init__(self):
        # Initialize official Razorpay Client
        if settings.RAZORPAY_KEY_ID and settings.RAZORPAY_KEY_SECRET:
            self.client = razorpay.Client(
                auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
            )
            logger.info("Razorpay SDK initialized successfully.")
        else:
            self.client = None
            logger.warning("Razorpay API credentials missing! Running in Mock Client mode.")

    def create_negotiated_payment_link(
        self,
        negotiation_id: str,
        amount_in_inr: float,
        description: str,
        customer_name: Optional[str] = "AI Buyer Agent",
        customer_email: Optional[str] = "buyer@agentic-commerce.ai",
        customer_contact: Optional[str] = "9999999999",
        expire_minutes: int = 15
    ) -> Dict[str, Any]:
        """
        Creates a dynamic, single-use Razorpay Payment Link for an accepted offer.
        Amounts are automatically converted from INR to paise (Razorpay standard: ₹100 = 10000 paise).
        """
        # Convert INR to Paise (integer)
        amount_in_paise = int(round(amount_in_inr * 100))
        expire_timestamp = int(time.time()) + (expire_minutes * 60)

        payload = {
            "amount": amount_in_paise,
            "currency": "INR",
            "accept_partial": False,
            "description": f"A2A Deal [{negotiation_id}]: {description}",
            "customer": {
                "name": customer_name,
                "email": customer_email,
                "contact": customer_contact
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

        # Mock fallback mode if SDK credentials are not configured
        if not self.client:
            mock_id = f"plink_mock_{negotiation_id}"
            mock_url = f"https://rzp.io/i/mock_{negotiation_id}"
            
            log_audit_event(
                negotiation_id=negotiation_id,
                action="CREATE_PAYMENT_LINK_MOCK",
                requested_amount=amount_in_inr,
                status="MOCK_GENERATED",
                reasoning="Razorpay credentials missing. Mock link created."
            )
            return {
                "payment_link_id": mock_id,
                "short_url": mock_url,
                "amount": amount_in_inr,
                "currency": "INR",
                "status": "created",
                "is_mock": True
            }

        try:
            # Official Razorpay SDK Call
            response = self.client.payment_link.create(payload)

            log_audit_event(
                negotiation_id=negotiation_id,
                action="RAZORPAY_PAYMENT_LINK_CREATED",
                requested_amount=amount_in_inr,
                status="SUCCESS",
                reasoning=f"Payment link generated successfully. Link ID: {response.get('id')}"
            )

            return {
                "payment_link_id": response.get("id"),
                "short_url": response.get("short_url"),
                "amount": amount_in_inr,
                "currency": response.get("currency"),
                "status": response.get("status"),
                "expire_by": response.get("expire_by"),
                "is_mock": False
            }

        except RazorpayError as e:
            # Graceful Failure Handling: Catch SDK error, log audit, re-raise structured error
            error_msg = f"Razorpay Gateway Error: {str(e)}"
            logger.error(f"[{negotiation_id}] {error_msg}", exc_info=True)

            log_audit_event(
                negotiation_id=negotiation_id,
                action="RAZORPAY_PAYMENT_LINK_FAILED",
                requested_amount=amount_in_inr,
                status="FAILED_HANDLED",
                reasoning=error_msg
            )
            raise RuntimeError(error_msg) from e

    def verify_webhook_signature(self, body_bytes: bytes, signature: str) -> bool:
        """
        Verifies incoming webhook payload signature from Razorpay.
        """
        if not settings.RAZORPAY_WEBHOOK_SECRET:
            logger.warning("Webhook secret not set. Skipping signature verification.")
            return True

        try:
            self.client.utility.verify_webhook_signature(
                body_bytes.decode("utf-8"),
                signature,
                settings.RAZORPAY_WEBHOOK_SECRET
            )
            return True
        except SignatureVerificationError:
            logger.error("Razorpay Webhook Signature Verification Failed!")
            return False


# Global singleton instance
razorpay_client = RazorpayClientWrapper()