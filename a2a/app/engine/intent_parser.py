"""Parse natural language buyer requests into structured negotiation intents using AI."""
import json
import logging
from openai import OpenAI
from app.config import settings

log = logging.getLogger("razorai.intent_parser")
client = OpenAI(api_key=settings.OPENAI_API_KEY,base_url="https://api.groq.com/openai/v1")

def parse_buyer_intent(natural_language: str, catalog: list[dict]) -> dict:
    """Use an LLM to translate natural language into a structured purchase intent."""

    catalog_summary = "\n".join(
        [f"- {p['sku']}: {p['name']} (₹{p['base_price']}/unit, stock: {p['stock']})" for p in catalog]
    )

    prompt = f"""You are parsing a buyer's natural language purchase request into structured data.

Available catalog:
{catalog_summary}

Buyer said: "{natural_language}"

Return ONLY valid JSON, no other text, no markdown formatting:
{{
    "sku": "the matching SKU from the catalog above",
    "quantity": <integer>,
    "budget_total": <number, total budget in INR — if buyer states per-unit price, multiply by quantity>,
    "delivery_deadline_days": <integer, default 7 if not mentioned>,
    "confidence": <integer 0-100, how confident you are this matches the buyer's intent>
}}"""

    response = client.chat.completions.create(
        model="groq/compound-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0,
        response_format={"type": "json_object"},
    )

    raw = response.choices[0].message.content.strip()
    # Strip markdown code fences if the model adds them anyway
    raw = raw.replace("```json", "").replace("```", "").strip()

    log.info(f"[AI PARSE] Input: '{natural_language}' -> {raw}")
    return json.loads(raw)