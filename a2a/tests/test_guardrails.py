"""Tests ensuring floor prices are never breached."""
from app.engine.guardrails import check_financial_bounds, check_stock, check_shipping_sla


def test_floor_respected_when_offer_above():
    # SKU-001: cost=1400, base=2499, min_margin=18%, max_discount=22%
    # margin_floor = 1400 * 1.18 = 1652; discount_floor = 2499 * 0.78 = 1949.22
    # effective_floor = max(1652, 1949.22) = 1949.22
    r = check_financial_bounds(2000.0, 1400, 2499, 18, 22)
    assert r.passed, f"2000 should pass floor {r.effective_floor}"


def test_floor_breached_when_offer_below():
    r = check_financial_bounds(1000.0, 1400, 2499, 18, 22)
    assert not r.passed
    assert "floor" in r.reason.lower()


def test_margin_floor_wins_when_stricter():
    # Make margin floor higher: cost=2000, min_margin=50% -> floor=3000
    # base=4000, max_discount=10% -> discount_floor=3600; effective=3600
    r = check_financial_bounds(3500.0, 2000, 4000, 50, 10)
    assert r.effective_floor == 3600.0


def test_stock_gate_pass():
    assert check_stock(50, 120).passed


def test_stock_gate_fail():
    assert not check_stock(200, 120).passed


def test_sla_gate_pass():
    assert check_shipping_sla(5, 3).passed


def test_sla_gate_fail():
    assert not check_shipping_sla(1, 3).passed


def test_sla_gate_no_deadline():
    assert check_shipping_sla(None, 3).passed
