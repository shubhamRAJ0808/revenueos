"""
RevenueOS API.

Runs standalone (in-memory state) so it's trivial to demo:

    pip install -r requirements.txt --break-system-packages
    uvicorn app.main:app --reload

For the persistent version, wire these endpoints to the SQLAlchemy models in
app/models.py against the schema in schema.sql (a Postgres instance with the
pgvector extension). The in-memory version below intentionally keeps the same
function signatures from app/agents.py so that swap is mechanical.
"""

from datetime import datetime, timezone
from typing import Optional
import hmac
import hashlib

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

import razorpay

from app import agents
from app.config import settings
from app.schemas import ShoppingQuery, CommandQuery, GuardrailsUpdate, CreateOrderRequest
from app.seed_data import CATALOG, FUNNEL, CUSTOMERS, DEFAULT_GUARDRAILS

app = FastAPI(title="RevenueOS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten before production; "*" also allows the
    # demo HTML file (served from a file:// origin) to call this API directly
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """
    This is an API-only server, so the bare URL has no page to show -- that's
    expected, not a bug. Use /docs for interactive testing, or open
    revenueos-demo.html, which now calls this API directly (see /api/health).
    """
    return {"service": "RevenueOS API", "docs": "/docs", "health": "/api/health"}

# ------------------------------------------------------------------ #
# In-memory demo state (swap for DB-backed state -- see app/models.py)
# ------------------------------------------------------------------ #
STATE = {
    "guardrails": dict(DEFAULT_GUARDRAILS),
    "activity_log": [],
    "offers": [],
    "experiments": [],
}


def log_activity(agent_name: str, action: str, details: Optional[dict] = None, requires_approval: bool = False):
    entry = {
        "agent_name": agent_name,
        "action": action,
        "details": details or {},
        "requires_approval": requires_approval,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    STATE["activity_log"].insert(0, entry)
    STATE["activity_log"] = STATE["activity_log"][:100]
    return entry


@app.on_event("startup")
def seed_log():
    log_activity("System", "Analyzed 12,482 customer events across the last 30 days.")
    log_activity("Intent Agent", "Detected 342 high-intent customers.")
    log_activity("Discovery Agent", "Generated 87 personalized bundles.")
    log_activity("Conversion Agent", "Identified 3 conversion leaks.")
    log_activity("Experiment Agent", "Proposed 2 experiments.", requires_approval=True)


# ------------------------------------------------------------------ #
# Dashboard
# ------------------------------------------------------------------ #

@app.get("/api/dashboard")
def dashboard():
    insight = agents.funnel_insight(FUNNEL)
    return {
        "funnel": FUNNEL,
        "funnel_insight": insight,
        "revenue_30d": 2_480_000,
        "ai_attributed_revenue": 370_000,
        "open_opportunities_value": 520_000,
    }


# ------------------------------------------------------------------ #
# AI Command Center
# ------------------------------------------------------------------ #

@app.post("/api/command")
def command(query: CommandQuery):
    t = query.text.lower()
    insight = agents.funnel_insight(FUNNEL)

    if "why" in t and "revenue" in t:
        log_activity("Conversion Agent", "Explained revenue drop from funnel analysis.")
        return {
            "agent": "Conversion Agent",
            "answer": (
                f"Revenue decreased due to a spike in drop-off between "
                f"{insight['biggest_drop']['from']} and {insight['biggest_drop']['to']} "
                f"({insight['biggest_drop']['drop_rate']}% loss, {insight['biggest_drop']['lost']} customers)."
            ),
            "data": insight,
        }

    if "leak" in t or "biggest" in t:
        return {
            "agent": "Revenue Agent",
            "answer": (
                f"Biggest leak: {insight['biggest_drop']['from']} -> {insight['biggest_drop']['to']} "
                f"at {insight['biggest_drop']['drop_rate']}% loss."
            ),
            "data": insight,
        }

    if "bundle" in t:
        intent = agents.parse_intent(query.text if any(c.isdigit() for c in query.text) else "laptop under 80k for coding and gaming")
        result = agents.build_bundle(CATALOG, intent)
        log_activity("Discovery Agent", "Generated a personalized bundle recommendation.", {"total": result["total"]})
        return {"agent": "Discovery Agent", "answer": "Bundle generated.", "data": result}

    if "offer" in t and "high" in t:
        offer = agents.compute_offer(91, 42999, STATE["guardrails"])
        log_activity("Offer Agent", "Drafted guardrail-checked discount for high-intent customers.", {"pct": offer.pct})
        return {"agent": "Offer Agent", "answer": "Offer drafted.", "data": offer.__dict__}

    if "launch" in t and "experiment" in t:
        result = agents.run_experiment()
        log_activity("Experiment Agent", "Launched mobile checkout experiment (simulated).", result)
        return {"agent": "Experiment Agent", "answer": "Experiment launched.", "data": result}

    return {"agent": "RevenueOS", "answer": "I can help with revenue drops, leaks, bundling, offers and experiments.", "data": None}


# ------------------------------------------------------------------ #
# Shopping experience
# ------------------------------------------------------------------ #

@app.post("/api/shopping/query")
def shopping_query(query: ShoppingQuery):
    intent = agents.parse_intent(query.text)
    result = agents.build_bundle(CATALOG, intent)
    offer = agents.compute_offer(customer_score=91, cart_value=result["total"], guardrails=STATE["guardrails"])
    log_activity("Intent Agent", f"Parsed customer query: {query.text}")
    log_activity("Discovery Agent", "Assembled bundle from live catalog.", {"total": result["total"]})
    return {
        "intent": intent.__dict__,
        "bundle": result["bundle"],
        "total": result["total"],
        "offer": offer.__dict__,
        "final_total": round(result["total"] - offer.amount, 2),
    }


# ------------------------------------------------------------------ #
# Growth opportunities
# ------------------------------------------------------------------ #

@app.get("/api/opportunities")
def opportunities():
    insight = agents.funnel_insight(FUNNEL)
    return {
        "opportunities": [
            {
                "id": "opp-1",
                "impact": "high",
                "title": "Mobile checkout abandonment",
                "revenue_per_month": 184000,
                "confidence_pct": 92,
                "action": "Introduce 'Buy Now + UPI' as the primary checkout CTA on mobile.",
            },
            {
                "id": "opp-2",
                "impact": "medium",
                "title": "Underpriced accessory attach rate",
                "revenue_per_month": 96000,
                "confidence_pct": 81,
                "action": "Auto-suggest keyboard + mouse bundle whenever a gaming laptop is added to cart.",
            },
        ],
        "funnel_insight": insight,
    }


@app.post("/api/opportunities/{opp_id}/approve")
def approve_opportunity(opp_id: str):
    result = agents.run_experiment()
    log_activity("Experiment Agent", f"Merchant approved {opp_id}; experiment launched.", result)
    return {"status": "launched", "result": result}


# ------------------------------------------------------------------ #
# Churn & win-back
# ------------------------------------------------------------------ #

@app.get("/api/churn")
def churn():
    return {"customers": agents.churn_risk(CUSTOMERS, STATE["guardrails"])}


@app.post("/api/churn/{customer_id}/send-offer")
def send_winback_offer(customer_id: str):
    log_activity("Churn Agent", f"Win-back offer sent to customer {customer_id}.")
    return {"status": "sent"}


# ------------------------------------------------------------------ #
# Guardrails
# ------------------------------------------------------------------ #

@app.get("/api/guardrails")
def get_guardrails():
    return STATE["guardrails"]


@app.put("/api/guardrails")
def update_guardrails(update: GuardrailsUpdate):
    changes = {k: v for k, v in update.dict().items() if v is not None}
    STATE["guardrails"].update(changes)
    log_activity("System", "Merchant updated guardrails.", changes)
    return STATE["guardrails"]


# ------------------------------------------------------------------ #
# Agent activity log
# ------------------------------------------------------------------ #

@app.get("/api/activity")
def activity():
    return {"activity": STATE["activity_log"]}


# ------------------------------------------------------------------ #
# Payments (Razorpay test mode)
# ------------------------------------------------------------------ #

def get_razorpay_client() -> razorpay.Client:
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(500, "Razorpay keys are not configured. Set RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET in .env")
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


@app.post("/api/payments/create-order")
def create_order(req: CreateOrderRequest):
    """Creates a Razorpay TEST MODE order. Amount is rupees; Razorpay wants paise."""
    client = get_razorpay_client()
    order = client.order.create({
        "amount": int(req.amount * 100),
        "currency": "INR",
        "payment_capture": 1,
        "notes": {"customer_id": req.customer_id or "", "offer_id": req.offer_id or ""},
    })
    log_activity("Payment Agent", f"Created Razorpay test order for INR {req.amount}.", {"order_id": order["id"]})
    return {"order_id": order["id"], "key_id": settings.RAZORPAY_KEY_ID, "amount": order["amount"], "currency": order["currency"]}


@app.post("/api/payments/webhook")
async def razorpay_webhook(request: Request):
    """
    Verifies Razorpay's webhook signature before trusting the payload.
    Point your Razorpay TEST MODE webhook (dashboard > Webhooks) at this URL,
    subscribed to `payment.captured`.
    """
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")

    if settings.RAZORPAY_WEBHOOK_SECRET:
        expected = hmac.new(
            settings.RAZORPAY_WEBHOOK_SECRET.encode(), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(400, "Invalid webhook signature")

    payload = await request.json()
    event = payload.get("event")
    log_activity("Payment Agent", f"Webhook received: {event}", payload)
    return {"status": "ok"}


@app.get("/api/health")
def health():
    return {"status": "ok"}
