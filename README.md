# RevenueOS — backend

An autonomous AI growth engine for agentic commerce: it observes customer and
payment behavior, reasons about the best growth action, checks that action
against merchant-defined guardrails, executes or queues it for approval, then
measures the outcome and feeds it back into future decisions.

```
MERCHANT DATA → AGENTS (Intent, Discovery, Offer, Conversion, Experiment, Churn)
             → GUARDRAIL CHECK → ACTION → RAZORPAY PAYMENT → OUTCOME → LEARN
```

## Quick start (in-memory demo — no database needed)

```bash
cd revenueos-backend
python -m venv .venv && source .venv/bin/activate
pip install fastapi uvicorn pydantic python-dotenv razorpay
cp .env.example .env   # fill in Razorpay TEST keys if you want real checkout
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` for interactive API docs. This mode keeps
all state in memory (`app/main.py: STATE`) so it runs instantly with zero
infra — good for the pitch video and local development.

## Full setup (persistent, Postgres + pgvector)

```bash
docker compose up -d          # starts Postgres with pgvector, loads schema.sql
pip install -r requirements.txt
# wire app/main.py's endpoints to app/models.py via app/database.py's get_db()
# dependency instead of the in-memory STATE dict — the function signatures in
# app/agents.py don't change either way.
uvicorn app.main:app --reload
```

`schema.sql` includes a `products.embedding VECTOR(384)` column so Discovery
Agent can move from tag-matching to real semantic search once you embed the
catalog (e.g. with a sentence-transformers model or an embeddings API).

## Architecture

| Agent | File | Responsibility |
|---|---|---|
| Intent Agent | `app/agents.py::parse_intent` | Extracts budget, category, use-case from free text |
| Discovery Agent | `app/agents.py::search_catalog`, `build_bundle` | Ranks catalog, assembles a bundle within budget |
| Offer Agent | `app/agents.py::compute_offer` | Proposes a discount, **enforces guardrails**, returns a reasoning trace |
| Conversion Agent | `app/agents.py::funnel_insight` | Finds the largest funnel drop-off and its revenue impact |
| Experiment Agent | `app/agents.py::run_experiment` | Proposes/launches an A/B test; results always labeled `is_simulated` until real traffic exists |
| Churn Agent *(new)* | `app/agents.py::churn_risk` | Flags high-LTV customers going quiet, drafts a guardrail-checked win-back offer |
| Payment Agent | `app/main.py` (`/api/payments/*`) | Creates Razorpay test orders, verifies webhook signatures |

Every agent decision is written to `agent_activity_log` (see `schema.sql`)
so a merchant — or an evaluator — can see exactly what the system observed,
decided, and why, in order. That audit trail is the explainability layer:
nothing acts silently.

## Guardrails

`GET/PUT /api/guardrails` control every agent's ceiling: max discount, max
offer value per customer, whether payments/campaigns can auto-execute, and
the high-value threshold above which a human must approve. `compute_offer`
never exceeds these — it revises its own proposal down and records why in
`reasoning_trace`, rather than silently blocking or silently overriding.

## Razorpay integration

- `POST /api/payments/create-order` creates a **TEST MODE** order via the
  official `razorpay` Python SDK.
- `POST /api/payments/webhook` verifies the `X-Razorpay-Signature` header
  with HMAC-SHA256 against `RAZORPAY_WEBHOOK_SECRET` before trusting any
  payload — configure this URL under Razorpay Dashboard → Webhooks,
  subscribed to `payment.captured`.
- Only test-mode keys should ever go in `.env`. Never commit real keys.

## What's simulated vs real

Being upfront about this is deliberate — a credible prototype beats an
invented one. Real: HTTP API, guardrail enforcement, funnel math, intent
parsing, Razorpay test-mode order creation and webhook verification. Labeled
simulation: experiment outcomes (`is_simulated: true` everywhere they
appear), the underlying customer/event dataset. Swapping in live Razorpay
data and a production experimentation service is a data-source change, not
an architecture change.
