"""
RevenueOS agent logic.

Each function below is a pure, testable unit representing one agent in the
architecture described in the product spec:

    Intent Agent -> Discovery Agent -> Offer Agent -> Conversion Agent
    -> Experiment Agent -> Churn Agent -> Payment Agent

They are deliberately implemented as rule-based / statistical logic first,
so the system is transparent, cheap to run, and demoable without an LLM key.
Swap `parse_intent` for an LLM-backed structured-output call (see the
commented block at the bottom) once you want free-text understanding beyond
the regex heuristics below -- everything downstream is unaffected because it
consumes the same `Intent` shape either way.
"""

import random
import re
from dataclasses import dataclass, field
from typing import Optional


# --------------------------------------------------------------------------- #
# Intent Agent
# --------------------------------------------------------------------------- #

CATEGORY_KEYWORDS = {
    "laptop": "laptop", "notebook": "laptop",
    "mouse": "mouse",
    "keyboard": "keyboard",
    "headphone": "headphones", "headset": "headphones",
    "monitor": "monitor",
    "phone": "phone", "mobile": "phone",
    "camera": "accessory", "webcam": "accessory",
}
USE_CASE_KEYWORDS = ["coding", "gaming", "photography", "office", "editing", "portable", "performance"]


@dataclass
class Intent:
    raw_text: str
    budget: Optional[float] = None
    category: Optional[str] = None
    use_cases: list = field(default_factory=list)


def parse_intent(text: str) -> Intent:
    t = text.lower()

    budget = None
    k_match = re.search(r"(\d+(?:\.\d+)?)\s*k", t)
    raw_match = re.search(r"₹?\s?(\d{4,7})", t)
    if k_match:
        budget = float(k_match.group(1)) * 1000
    elif raw_match:
        budget = float(raw_match.group(1))

    category = None
    for kw, cat in CATEGORY_KEYWORDS.items():
        if kw in t:
            category = cat
            break

    use_cases = [u for u in USE_CASE_KEYWORDS if u in t]

    return Intent(raw_text=text, budget=budget, category=category, use_cases=use_cases)


# --------------------------------------------------------------------------- #
# Discovery Agent
# --------------------------------------------------------------------------- #

def score_product(product: dict, intent: Intent) -> int:
    score = 0
    if intent.category and product["category"] == intent.category:
        score += 50
    for u in intent.use_cases:
        if u in product.get("tags", []):
            score += 18
    if intent.budget:
        if product["price"] <= intent.budget:
            score += 10
        else:
            score -= 25
    return score


def search_catalog(catalog: list[dict], intent: Intent) -> list[dict]:
    ranked = [{**p, "score": score_product(p, intent)} for p in catalog]
    return sorted(ranked, key=lambda p: p["score"], reverse=True)


def build_bundle(catalog: list[dict], intent: Intent) -> dict:
    ranked = search_catalog(catalog, intent)
    budget = intent.budget or 100_000
    primary_cat = intent.category or "laptop"

    primary = next((p for p in ranked if p["category"] == primary_cat), ranked[0])
    bundle = [primary]
    total = float(primary["price"])

    addon_cats = {"mouse", "keyboard", "headphones"}
    for p in ranked:
        if p["category"] in addon_cats and p["score"] > 0 and total + p["price"] <= budget:
            bundle.append(p)
            total += float(p["price"])

    return {"bundle": bundle, "total": total, "budget": budget}


# --------------------------------------------------------------------------- #
# Offer Agent (guardrail-enforced)
# --------------------------------------------------------------------------- #

@dataclass
class OfferResult:
    pct: float
    amount: float
    needs_approval: bool
    trace: list[str]


def compute_offer(customer_score: float, cart_value: float, guardrails: dict) -> OfferResult:
    """
    guardrails expects keys: max_discount_pct, max_offer_amount,
    high_value_requires_approval, high_value_threshold
    """
    trace = []
    pct = 8 if customer_score > 85 else 5 if customer_score > 70 else 2
    trace.append(f"Customer score {customer_score}/100 -> base offer {pct}%.")

    max_discount = float(guardrails["max_discount_pct"])
    if pct > max_discount:
        trace.append(f"Guardrail: max discount is {max_discount}% -> revised down to {max_discount}%.")
        pct = max_discount
    else:
        trace.append(f"Guardrail: within max discount of {max_discount}% -> approved.")

    amount = cart_value * pct / 100
    max_offer = float(guardrails["max_offer_amount"])
    if amount > max_offer:
        capped_pct = max_offer / cart_value * 100
        trace.append(
            f"Offer value ₹{amount:.0f} exceeds per-customer cap of ₹{max_offer:.0f} "
            f"-> capped to ₹{max_offer:.0f} ({capped_pct:.1f}%)."
        )
        amount = max_offer
        pct = capped_pct

    hv_threshold = float(guardrails["high_value_threshold"])
    needs_approval = bool(guardrails["high_value_requires_approval"]) and cart_value > hv_threshold
    trace.append(
        "Cart value exceeds high-value threshold -> routed to merchant for approval."
        if needs_approval else
        "Below high-value threshold -> eligible for auto-execution per current settings."
    )

    return OfferResult(pct=round(pct, 1), amount=round(amount), needs_approval=needs_approval, trace=trace)


# --------------------------------------------------------------------------- #
# Conversion Agent
# --------------------------------------------------------------------------- #

def funnel_insight(funnel: dict) -> dict:
    """funnel: {'view':int,'cart':int,'checkout':int,'payment':int}"""
    stages = [("view", "cart"), ("cart", "checkout"), ("checkout", "payment")]
    drops = []
    for a, b in stages:
        lost = funnel[a] - funnel[b]
        rate = lost / funnel[a] if funnel[a] else 0
        drops.append({"from": a, "to": b, "lost": lost, "drop_rate": round(rate * 100, 1)})
    biggest = max(drops, key=lambda d: d["lost"])
    overall_conversion = round(funnel["payment"] / funnel["view"] * 100, 2) if funnel["view"] else 0
    return {"drops": drops, "biggest_drop": biggest, "overall_conversion_pct": overall_conversion}


# --------------------------------------------------------------------------- #
# Experiment Agent
# --------------------------------------------------------------------------- #

def run_experiment(seed: Optional[int] = None) -> dict:
    """
    Simulated A/B result. Clearly labeled `is_simulated=True` everywhere this
    is surfaced (UI + DB), per the "don't fake production numbers" principle.
    Swap in a real experimentation/statistics service once live traffic exists.
    """
    rng = random.Random(seed)
    lift_pct = round(8 + rng.random() * 4, 1)
    confidence_pct = round(92 + rng.random() * 5, 1)
    return {"lift_pct": lift_pct, "confidence_pct": confidence_pct, "is_simulated": True}


# --------------------------------------------------------------------------- #
# Churn Agent  (new feature beyond the original spec)
# --------------------------------------------------------------------------- #

def churn_risk(customers: list[dict], guardrails: dict, inactivity_days_threshold: int = 45) -> list[dict]:
    """
    Flags high-LTV customers who have gone quiet and drafts a guardrail-checked
    win-back offer for each. This closes the loop the original spec left open:
    RevenueOS should not just grow new revenue, it should also protect existing
    revenue that is at risk of churning.
    """
    results = []
    for c in customers:
        inactive = c["last_order_days_ago"] > inactivity_days_threshold
        if not inactive:
            risk = "low"
        elif c["ltv"] > 30_000:
            risk = "high"
        else:
            risk = "medium"

        offer = None
        if risk != "low":
            win_back_cart_value = min(c["ltv"] * 0.1, 15_000)
            offer = compute_offer(c["score"], win_back_cart_value, guardrails)

        results.append({**c, "risk": risk, "offer": offer})

    return sorted(results, key=lambda r: {"high": 0, "medium": 1, "low": 2}[r["risk"]])


# --------------------------------------------------------------------------- #
# Optional: LLM-backed intent parsing (structured outputs)
# --------------------------------------------------------------------------- #
#
# from anthropic import Anthropic
# from app.config import settings
#
# def parse_intent_llm(text: str) -> Intent:
#     client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
#     resp = client.messages.create(
#         model="claude-sonnet-4-6",
#         max_tokens=300,
#         system=(
#             "Extract shopping intent as JSON only, no prose: "
#             '{"budget": number|null, "category": string|null, "use_cases": string[]}'
#         ),
#         messages=[{"role": "user", "content": text}],
#     )
#     import json
#     data = json.loads(resp.content[0].text)
#     return Intent(raw_text=text, **data)
