from typing import Optional
from pydantic import BaseModel


class ShoppingQuery(BaseModel):
    text: str


class CommandQuery(BaseModel):
    text: str


class OfferRequest(BaseModel):
    customer_score: float
    cart_value: float


class GuardrailsUpdate(BaseModel):
    max_discount_pct: Optional[float] = None
    min_margin_pct: Optional[float] = None
    max_offer_amount: Optional[float] = None
    max_daily_offers: Optional[int] = None
    auto_execute_payments: Optional[bool] = None
    auto_launch_campaigns: Optional[bool] = None
    high_value_requires_approval: Optional[bool] = None
    high_value_threshold: Optional[float] = None


class CreateOrderRequest(BaseModel):
    amount: float  # in INR (rupees, not paise)
    customer_id: Optional[str] = None
    offer_id: Optional[str] = None
