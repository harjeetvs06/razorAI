"""Main negotiation endpoint – handles incoming buyer-agent requests."""
from fastapi import APIRouter, HTTPException
from app.models.schemas import BuyerRequest, NegotiationResult, CatalogItem
from app.engine.negotiator import run_negotiation, get_catalog_items, CATALOG
from app.integrations.razorpay_client import create_payment_link, create_order
from app.audit.logger import emit_negotiation_log
from typing import List
from pydantic import BaseModel
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

@router.post("/auto")
async def auto_negotiate(req: BuyerRequest):
    """
    Full multi-round A2A negotiation loop.
    
    Buyer agent sends initial request.
    Merchant negotiator responds (accept/counter/reject).
    Buyer agent evaluates and decides next move (accept/counter/walk away).
    Loop continues up to max_rounds or until agreement.
    """
    from app.engine.buyer_agent import BuyerPolicy, decide_buyer_move
    
    transcript = []
    round_num = 1
    current_req = req
    
    # Buyer's negotiation policy (hardcoded for demo; could come from request)
    policy = BuyerPolicy(
        max_budget_per_unit=req.budget_total / req.quantity if req.quantity > 0 else 0,
        min_acceptable_qty=req.quantity,
        max_rounds=3,
        flexibility_pct=5.0,
    )
    
    while round_num <= policy.max_rounds:
        # Merchant negotiates
        merchant_result = run_negotiation(
            current_req,
            razorpay_link="",  # will be generated on final accept
            order_id="",
        )
        
        transcript.append({
            "round": round_num,
            "actor": "merchant",
            "response": merchant_result.model_dump(),
        })
        
        # Buyer decides
        buyer_move = decide_buyer_move(policy, merchant_result, round_num)
        
        transcript.append({
            "round": round_num,
            "actor": "buyer",
            "move": buyer_move.action,
            "reason": buyer_move.reason,
            "proposed_budget": buyer_move.new_budget_per_unit if buyer_move.action == "COUNTER" else None,
        })
        
        # End-state decisions
        if buyer_move.action == "ACCEPT":
            # Generate real payment link for final deal
            razorpay_order = create_order(merchant_result.total_price, "INR", merchant_result.negotiation_id)
            razorpay_link = create_payment_link(
                merchant_result.total_price,
                merchant_result.negotiation_id,
                f"Order {merchant_result.negotiation_id}",
            )
            merchant_result.payment_link = razorpay_link.get("short_url", "")
            merchant_result.razorpay_order_id = razorpay_order.get("id", "")
            
            return {
                "outcome": "DEAL",
                "transcript": transcript,
                "final_agreement": merchant_result.model_dump(),
                "total_rounds": round_num,
            }
        
        if buyer_move.action == "WALK_AWAY":
            return {
                "outcome": "NO_DEAL",
                "transcript": transcript,
                "reason": buyer_move.reason,
                "total_rounds": round_num,
            }
        
        # COUNTER — build new request for next round
        current_req = BuyerRequest(
            sku=req.sku,
            quantity=req.quantity,
            budget_total=buyer_move.new_budget_per_unit * req.quantity,
            delivery_deadline_days=req.delivery_deadline_days,
            buyer_agent_id=req.buyer_agent_id,
        )
        round_num += 1
    
    # Max rounds exhausted
    return {
        "outcome": "NO_DEAL",
        "transcript": transcript,
        "reason": f"Negotiation did not converge after {policy.max_rounds} rounds.",
        "total_rounds": round_num - 1,
    }
class NaturalLanguageRequest(BaseModel):
    message: str
    buyer_agent_id: str = "nl-buyer-agent"

@router.post("/from-text")
async def negotiate_from_text(payload: NaturalLanguageRequest):
    """Accept natural language, parse via AI, run full A2A negotiation."""
    from app.engine.intent_parser import parse_buyer_intent
    from app.engine.negotiator import CATALOG

    catalog_list = [{"sku": k, **v} for k, v in CATALOG.items()]

    try:
        parsed = parse_buyer_intent(payload.message, catalog_list)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not understand request: {str(e)}")

    if not parsed.get("sku") or parsed["sku"] not in CATALOG:
        raise HTTPException(status_code=422, detail=f"Could not match a product to your request.")

    req = BuyerRequest(
        sku=parsed["sku"],
        quantity=parsed["quantity"],
        budget_total=parsed["budget_total"],
        delivery_deadline_days=parsed.get("delivery_deadline_days", 7),
        buyer_agent_id=payload.buyer_agent_id,
    )

    result = await auto_negotiate(req)
    result["ai_parsed_intent"] = parsed  # show judges the AI's interpretation
    return result