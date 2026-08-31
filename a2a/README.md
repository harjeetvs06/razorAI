# RazorAI — Agent-to-Agent Autonomous Negotiator
### Razorpay Hackathon · Track 1: Explainable, Bounded, Gated Financial Actions

---

## What it does

Standard checkouts are binary — pay or leave. **RazorAI** sits on top of Razorpay and lets autonomous AI buyer-agents *negotiate* in real time.

A buyer agent sends:
```json
{
  "sku": "SKU-001",
  "quantity": 50,
  "budget_total": 45000,
  "delivery_deadline_days": 5
}
```

The merchant engine responds in < 50ms with a full explainable decision + a single-use Razorpay payment link.

---

## Track 1 compliance

| Requirement | Implementation |
|---|---|
| **Explainable** | Step-by-step audit_trail with action, value, reason on every decision |
| **Bounded** | guardrails.py enforces hard margin floor + max discount cap — never bypassed |
| **Gated** | 6 sequential gates: catalog → stock → price parse → SLA → bulk curve → financial bounds |
| **Single-use link** | Razorpay payment link created only after all gates pass |

---

## Quick start

### Backend
```bash
cd a2a
pip install -r requirements.txt
cp .env.example .env          # fill in your Razorpay keys
uvicorn app.main:app --reload --port 8000
# API docs: http://localhost:8000/docs
```

### Frontend
```bash
cd a2a-negotiator/frontend
npm install
npm run dev
# http://localhost:5173
```

### Docker
```bash
docker-compose up --build
```

---

## API

### POST /api/v1/negotiate/
Send a buyer-agent negotiation request. Returns status, price, audit trail, and Razorpay payment link.

### GET /api/v1/negotiate/catalog
All products available for negotiation.

### PATCH /api/v1/merchant/rules
Update margin/discount rules for a SKU live.

### POST /api/v1/webhooks/razorpay
Razorpay webhook — handles payment.captured events.

---

## Decision logic

```
implied_unit = budget / quantity

if implied_unit >= bulk_offer   →  ACCEPT  (generate payment link)
elif implied_unit >= floor      →  COUNTER (buyer's price, generate link)
else                            →  REJECT  (no link generated)
```

Tests: pytest tests/ -v

Built for Razorpay Hackathon · Track 1
