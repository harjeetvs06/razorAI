"""Mocked Razorpay payment link generation tests."""
import pytest
from unittest.mock import patch, MagicMock
from app.integrations.razorpay_client import create_order, create_payment_link


def test_mock_order_created():
    order = create_order(45000.0, receipt="NEG-TEST001")
    assert "id" in order
    assert order["amount"] == 4500000
    assert order["currency"] == "INR"


def test_mock_payment_link_created():
    link = create_payment_link(45000.0, "50x Earbuds", "NEG-TEST001")
    assert "short_url" in link
    assert "rzp.io" in link["short_url"]
    assert link["amount"] == 4500000


def test_payment_link_unique_per_negotiation():
    l1 = create_payment_link(45000.0, "test", "NEG-AAA")
    l2 = create_payment_link(45000.0, "test", "NEG-BBB")
    assert l1["short_url"] != l2["short_url"]
