import hmac
import hashlib
from fastapi import Security, HTTPException, status
from fastapi.security.api_key import APIKeyHeader

from app.config import settings

# Header keys for incoming Agent/Merchant requests
API_KEY_HEADER = APIKeyHeader(name="X-Merchant-API-Key", auto_error=False)


def verify_merchant_api_key(api_key: str = Security(API_KEY_HEADER)) -> str:
    """
    Dependency to protect Merchant configuration endpoints (e.g., setting floor prices).
    """
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required header: X-Merchant-API-Key"
        )
    
    # Simple key verification (in production, compare against hashed DB keys)
    if api_key != settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid Merchant API Key."
        )
    
    return api_key


def generate_hmac_signature(payload_string: str, secret: str) -> str:
    """
    Generates SHA256 HMAC signature for verifying outbound/inbound agent payloads.
    """
    return hmac.new(
        secret.encode("utf-8"),
        payload_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()