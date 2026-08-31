"""Main negotiation endpoint – handles incoming buyer-agent requests."""
from fastapi import APIRouter, HTTPException
from app.models.schemas import BuyerRequest, NegotiationResult, CatalogItem
from app.engine.negotiator import run_negotiation, get_catalog_items, CATALOG
from app.integrations.razorpay_client import create_payment_link, create_order
from app.audit.logger import emit_negotiation_log
from typing import List

router = APIRouter()


@router.get("/catalog", response_model=List[CatalogItem])
async def catalog():
    """Return all products available for agent negotiation."""
    return get_catalog_items()


@router.post("/", response_model=NegotiationResult)
async def negotiate(req: BuyerRequest):
    """
    Core A2A negotiation endpoint.
    Accepts a buyer-agent's structured request and returns an
    explainable, bounded pricing decision with a Razorpay payment link.
    """
    if req.sku not in CATALOG:
        raise HTTPException(404, f"SKU '{req.sku}' not in catalog.")

    # Run negotiation logic (guardrails + pricing engine)
    result = run_negotiation(req)

    # Only generate payment artifacts on accepted/counter deals
    if result.status.value in ("accepted", "counter") and result.total_price > 0:
        order = create_order(result.total_price, receipt=result.negotiation_id)
        link  = create_payment_link(
            amount_inr=result.total_price,
            description=f"{result.quantity}x {result.product_name} — {result.negotiation_id}",
            negotiation_id=result.negotiation_id,
        )
        result.payment_link      = link.get("short_url", "")
        result.razorpay_order_id = order.get("id", "")

    # Emit structured audit log
    emit_negotiation_log(result)
    return result


@router.get("/product/{sku}")
async def get_product(sku: str):
    if sku not in CATALOG:
        raise HTTPException(404, "SKU not found")
    item = CATALOG[sku].copy()
    item["sku"] = sku
    return item
