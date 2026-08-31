"""API key validation and signature verification helpers."""
from fastapi import HTTPException, Security
from fastapi.security import APIKeyHeader

API_KEY_HEADER = APIKeyHeader(name="X-Agent-Key", auto_error=False)

# In prod, load from DB; here hardcoded for demo
VALID_KEYS = {"demo-buyer-key-001", "demo-buyer-key-002"}


def verify_agent_key(key: str = Security(API_KEY_HEADER)):
    if key and key not in VALID_KEYS:
        raise HTTPException(403, "Invalid agent API key.")
    return key  # None = unauthenticated (allowed in dev)
