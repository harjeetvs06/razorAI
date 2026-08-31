"""Tests for negotiation rounds."""
import pytest
from app.models.schemas import BuyerRequest
from app.engine.negotiator import run_negotiation


def _req(**kwargs):
    defaults = dict(sku="SKU-001", quantity=50, budget_total=100000,
                    buyer_agent_id="test-agent")
    defaults.update(kwargs)
    return BuyerRequest(**defaults)


def test_accepted_when_budget_covers_bulk():
    result = run_negotiation(_req(quantity=50, budget_total=150000))
    assert result.status.value == "accepted"
    assert result.payment_link != ""
    assert result.total_price > 0


def test_counter_when_budget_above_floor():
    # Budget = 800/unit; base 2499, cost 1400, floor ~1652; 800 < floor → rejected
    # Budget = 2000/unit; base 2499, floor ~1652; 2000 > floor → counter
    result = run_negotiation(_req(quantity=10, budget_total=20000))
    assert result.status.value in ("accepted", "counter")


def test_rejected_when_budget_below_floor():
    result = run_negotiation(_req(quantity=10, budget_total=5000))  # 500/unit << floor
    assert result.status.value == "rejected"
    assert result.payment_link == ""


def test_rejected_when_stock_insufficient():
    result = run_negotiation(_req(quantity=9999, budget_total=999_999_999))
    assert result.status.value == "rejected"


def test_rejected_when_sla_unmet():
    result = run_negotiation(_req(quantity=10, budget_total=500000,
                                  delivery_deadline_days=1))  # SKU-001 SLA = 3 days
    assert result.status.value == "rejected"


def test_audit_trail_populated():
    result = run_negotiation(_req(quantity=50, budget_total=150000))
    assert len(result.audit_trail) >= 4
    assert len(result.gates_checked) >= 4


def test_discount_never_exceeds_max():
    result = run_negotiation(_req(quantity=500, budget_total=9_999_999))
    max_disc = 22.0  # SKU-001 cap
    if result.status.value == "accepted":
        assert result.discount_pct <= max_disc + 0.1  # float tolerance
