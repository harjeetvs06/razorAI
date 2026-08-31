"""Merchant dashboard APIs – read catalog & update rules."""
from fastapi import APIRouter, HTTPException
from app.engine.negotiator import CATALOG
from app.models.schemas import MerchantRuleUpdate, CatalogItem
from typing import List

router = APIRouter()


@router.get("/catalog", response_model=List[CatalogItem])
async def merchant_catalog():
    from app.engine.negotiator import get_catalog_items
    return get_catalog_items()


@router.patch("/rules")
async def update_rules(update: MerchantRuleUpdate):
    """Update negotiation rules for a SKU (margin floor, max discount, stock)."""
    if update.sku not in CATALOG:
        raise HTTPException(404, f"SKU '{update.sku}' not found.")
    item = CATALOG[update.sku]
    if update.min_margin_pct is not None:
        item["min_margin_pct"] = update.min_margin_pct
    if update.max_bulk_discount_pct is not None:
        item["max_bulk_discount_pct"] = update.max_bulk_discount_pct
    if update.stock is not None:
        item["stock"] = update.stock
    return {"status": "updated", "sku": update.sku, "rules": {
        "min_margin_pct": item["min_margin_pct"],
        "max_bulk_discount_pct": item["max_bulk_discount_pct"],
        "stock": item["stock"],
    }}


@router.get("/stats")
async def merchant_stats():
    """Quick summary for merchant dashboard."""
    return {
        "total_skus": len(CATALOG),
        "total_stock": sum(v["stock"] for v in CATALOG.values()),
        "avg_base_price": round(
            sum(v["base_price"] for v in CATALOG.values()) / len(CATALOG), 2
        ),
        "categories": list({v["category"] for v in CATALOG.values()}),
    }
