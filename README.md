# RazorAI — Bounded Agent-to-Agent Negotiation for Razorpay Merchants

**Track 1 Submission — Razorpay AI Buildathon**

RazorAI lets a buyer agent (human or AI-driven) negotiate directly with a merchant's pricing engine, autonomously, across multiple rounds — within hard guardrails the merchant controls — and settles the deal with a real Razorpay payment link.

No human sales rep. No fixed "take it or leave it" checkout. Two agents, a bounded negotiation, and a real transaction.

---

## What it does

1. A buyer states what they want — either by filling structured fields, or in plain English:
   > "I need 20 water bottles, budget around ₹18,500, need it in 5 days."

2. If typed in natural language, an AI (Groq LLM) parses it into a structured intent.

3. A **buyer agent** and a **merchant negotiation engine** negotiate autonomously, back and forth, up to a bounded number of rounds:
   - The merchant engine checks stock, shipping SLA, margin floor, and discount cap before proposing any price.
   - The buyer agent evaluates each counter-offer against its own budget ceiling and either accepts, counters again, or walks away.

4. If they reach agreement, a **real Razorpay test-mode payment link** is generated automatically — no manual checkout step.

5. Every decision, on both sides, is logged with a plain-English reason — nothing is a black box.

---

## Why this fits Track 1

Razorpay's brief asks for agentic commerce that **grows merchant revenue** and makes merchants **sellable to AI buyers**, with every money-touching action **bounded, gated, explainable, and auditable**, including graceful failure handling.

RazorAI is built around that requirement, not bolted on after:

- **Bounded** — hard quantity caps, merchant-set margin floors, and a maximum negotiation round count that can never be exceeded.
- **Gated** — a deal cannot be reached unless it clears every guardrail: stock availability, shipping SLA, and margin floor, in that order.
- **Explainable** — every negotiation round (on both the buyer and merchant side) returns a human-readable reason, not just a status code.
- **Auditable** — the full multi-round transcript, including rejected offers, is returned with the final result.
- **Graceful failure** — if agents can't agree, or a downstream Razorpay call fails, the negotiation ends cleanly with a stated reason instead of crashing or silently producing a bad deal.

---

## Architecture

```text
Buyer (typed sentence)          Buyer (manual sliders)
          │                              │
          ▼                              │
   AI intent parser                      │
        (Groq)                           │
          │                              │
          └───────────────┬──────────────┘
                          ▼
              Structured negotiation request
                          │
                          ▼
              ┌──────────────────────────────┐
              │       Multi-round A2A loop   │
              │                              │
              │ Merchant Negotiation Engine  │
              │ (stock / SLA / margin / cap) │
              │              ↕               │
              │ Buyer Agent Policy           │
              │ (budget ceiling, flexibility)│
              └──────────────┬───────────────┘
                             │
                    DEAL ─────/───── NO_DEAL
                             │
                             ▼
              Real Razorpay order + payment link
                   (test-mode API, webhook-verified)
```

### Backend — FastAPI (Python)

- `app/engine/negotiator.py` — merchant-side pricing logic and guardrails
- `app/engine/guardrails.py` — stock, SLA, and margin-floor checks
- `app/engine/buyer_agent.py` — buyer-side negotiation policy (accept / counter / walk away)
- `app/engine/intent_parser.py` — Groq-powered natural language → structured intent
- `app/integrations/razorpay_client.py` — real Razorpay order + payment link creation
- `app/api/v1/negotiate.py` — `/negotiate` (single round), `/negotiate/auto` (multi-round loop), `/negotiate/from-text` (AI-parsed)
- `app/api/v1/webhooks.py` — signature-verified Razorpay webhook handling

### Frontend — React + TanStack Start

- Manual negotiation builder (sliders, live JSON payload preview)
- AI Agent tab (natural language input)
- Live gate-by-gate guardrail breakdown
- Price tug-of-war visual
- Full audit trail

---

## Running it locally

### Requirements

- Python 3.11+
- Node 20+
- A free Razorpay test-mode account
- A free Groq API key

### 1. Get free API keys

- **Razorpay test keys:** [Razorpay Dashboard](https://dashboard.razorpay.com/) → switch to **Test Mode** (top-left) → Settings → API Keys → Generate Test Key
- **Groq key:** [Groq Console](https://console.groq.com/keys)

### 2. Configure environment

```bash
cp .env.example .env
# then fill in your real test-mode Razorpay keys and Groq key
```

> `APP_ENV` must **not** be `development` — that value intentionally forces all Razorpay calls into mock mode (used during early development to avoid hitting real APIs by accident). Use `staging` for real test-mode calls.

### 3. Run with Docker (recommended)

```bash
docker compose up --build
```

- Backend: `http://localhost:8001`
- Frontend: `http://localhost:8082`
- API docs: `http://localhost:8001/docs`

### 4. Or run manually

**Backend:**

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8001
```

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

---

## Try it

### Guaranteed instant accept

SKU-002, small gap:

```bash
curl -X POST http://localhost:8001/api/v1/negotiate/auto \
  -H "Content-Type: application/json" \
  -d '{"sku": "SKU-002", "quantity": 20, "budget_total": 18600, "delivery_deadline_days": 5, "buyer_agent_id": "demo-buyer"}'
```

### Real multi-round negotiation

Budget below the merchant's ideal price, above its floor:

```bash
curl -X POST http://localhost:8001/api/v1/negotiate/auto \
  -H "Content-Type: application/json" \
  -d '{"sku": "SKU-002", "quantity": 20, "budget_total": 18000, "delivery_deadline_days": 5, "buyer_agent_id": "demo-buyer"}'
```

### Natural language

AI-parsed intent:

```bash
curl -X POST http://localhost:8001/api/v1/negotiate/from-text \
  -H "Content-Type: application/json" \
  -d '{"message": "I need 20 water bottles, budget around 18500 rupees, need it in 5 days"}'
```

### Deliberate rejection

Budget below margin floor, demonstrating the guardrail refusing to sell at a loss:

```bash
curl -X POST http://localhost:8001/api/v1/negotiate/auto \
  -H "Content-Type: application/json" \
  -d '{"sku": "SKU-002", "quantity": 20, "budget_total": 15000, "delivery_deadline_days": 5, "buyer_agent_id": "demo-buyer"}'
```

---

## Tests

```bash
pytest tests/ -v
```

Tests cover:

- Guardrail logic
- Margin floor precedence
- Stock/SLA gates
- Full negotiation outcomes (accept / counter / reject)
- Razorpay mock-mode order/payment-link generation

---

## What's real vs. mocked

- **Merchant negotiation logic, guardrails, buyer agent** — fully real, no mocking.
- **Razorpay integration** — real test-mode API calls when `APP_ENV != development` and valid test keys are provided; falls back to a clearly labeled mock response otherwise (used only during early local development).
- **AI parsing** — real Groq LLM call via the OpenAI-compatible SDK.
- **Catalog** — in-memory for this demo; swappable for a real merchant database without touching negotiation logic.

---

## Roadmap

### Beyond this submission

- Per-buyer-agent authentication (API keys instead of free-text agent IDs)
- Rate limiting on negotiation endpoints
- Persistent catalog + order history (Postgres, schema already scaffolded)
- Configurable buyer policies (currently a single hardcoded flexibility curve)
