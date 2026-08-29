from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient

# Import your FastAPI app instance
from app.main import app  # Adjust path if your FastAPI app is defined elsewhere

# Instantiate the test client
client = TestClient(app)


def test_negotiation_accepted_flow():
    """Integration Test: Valid offer should return HTTP 200 ACCEPTED and a Razorpay link."""
    payload = {
        "negotiation_id": "test_neg_success_123",
        "product_id": "prod_laptop_001",
        "product_name": "Developer Laptop 16-inch",
        "original_price": 50000.0,
        "proposed_price": 45000.0,  # Above merchant floor of 42000
        "quantity": 1,
        "buyer_agent_id": "agent_test_buyer"
    }

    mock_payment_response = {
        "payment_link_id": "plink_test_12345",
        "short_url": "https://rzp.io/i/test_link",
        "amount": 45000.0,
        "currency": "INR",
        "status": "created",
        "expire_by": 1756450000,
        "is_mock": False
    }

    # Patch the method inside app.integrations.razorpay_client
    with patch(
        "app.integrations.razorpay_client.razorpay_client.create_negotiated_payment_link",
        return_value=mock_payment_response
    ):
        response = client.post("/api/v1/negotiate", json=payload)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ACCEPTED"
        assert "short_url" in data["payment_details"]