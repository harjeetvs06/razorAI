from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional

router = APIRouter()

# --- Schemas ---

class ProductRuleCreate(BaseModel):
    product_id: str = Field(
        ..., 
        json_schema_extra={"example": "prod_laptop_001"}
    )
    product_name: str = Field(
        ..., 
        json_schema_extra={"example": "Developer Laptop 16-inch"}
    )
    original_price: float = Field(
        ..., 
        gt=0, 
        json_schema_extra={"example": 50000.0}
    )
    floor_price: float = Field(
        ..., 
        gt=0, 
        json_schema_extra={"example": 42000.0}
    )  # Absolute hard boundary
    max_discount_pct: float = Field(
        default=0.20, 
        ge=0.0, 
        le=0.50, 
        json_schema_extra={"example": 0.20}
    )
    inventory_count: int = Field(default=10, ge=0)
    is_negotiable: bool = Field(default=True)


class ProductRuleResponse(ProductRuleCreate):
    id: str
    active: bool = True


# --- API Endpoints ---

@router.post("/rules", response_model=ProductRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_guardrail(rule: ProductRuleCreate):
    """
    Merchant Endpoint: Set hard bounds for a specific product SKU.
    These bounds will be strictly checked by app/engine/guardrails.py.
    """
    # Guardrail Check: Ensure merchant doesn't accidentally set floor higher than original price
    if rule.floor_price > rule.original_price:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Floor price cannot be greater than the original listing price."
        )

    # Return response using Pydantic V2 model_dump unpack
    return ProductRuleResponse(
        id="rule_99x12a",
        **rule.model_dump()
    )


@router.get("/rules/{product_id}", response_model=ProductRuleResponse)
async def get_product_guardrail(product_id: str):
    """
    Fetch active negotiation rules and floor prices for a specific SKU.
    """
    # Placeholder returning mock DB entity
    return ProductRuleResponse(
        id="rule_99x12a",
        product_id=product_id,
        product_name="Developer Laptop 16-inch",
        original_price=50000.0,
        floor_price=42000.0,
        max_discount_pct=0.20,
        inventory_count=15,
        is_negotiable=True
    )


@router.get("/audit-logs", status_code=status.HTTP_200_OK)
async def get_financial_audit_logs(limit: int = 20):
    """
    Merchant Dashboard Endpoint: Inspect real-time negotiation decisions,
    explainability statements, and interventions.
    """
    return {
        "total": 1,
        "logs": [
            {
                "timestamp": "2026-08-29T11:30:00Z",
                "negotiation_id": "neg_88f91a",
                "product_id": "prod_laptop_001",
                "requested_price": 40000.0,
                "floor_price": 42000.0,
                "action": "GUARDRAIL_INTERVENTION",
                "status": "REJECTED_BOUND_BREACH",
                "reasoning": "Offered price ₹40,000 breached the floor boundary of ₹42,000."
            }
        ]
    }