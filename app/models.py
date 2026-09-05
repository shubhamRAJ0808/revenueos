import uuid
from sqlalchemy import (
    Column, String, Numeric, Integer, Boolean, ForeignKey, TIMESTAMP, JSON, ARRAY, BigInteger, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


def uuid_col():
    return Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class Merchant(Base):
    __tablename__ = "merchants"
    id = uuid_col()
    name = Column(String, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class Guardrail(Base):
    __tablename__ = "guardrails"
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"), primary_key=True)
    max_discount_pct = Column(Numeric(5, 2), default=10)
    min_margin_pct = Column(Numeric(5, 2), default=15)
    max_offer_amount = Column(Numeric(10, 2), default=2000)
    max_daily_offers = Column(Integer, default=500)
    auto_execute_payments = Column(Boolean, default=False)
    auto_launch_campaigns = Column(Boolean, default=False)
    high_value_requires_approval = Column(Boolean, default=True)
    high_value_threshold = Column(Numeric(10, 2), default=40000)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class Product(Base):
    __tablename__ = "products"
    id = uuid_col()
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"))
    name = Column(String, nullable=False)
    category = Column(String, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    tags = Column(ARRAY(String), default=[])
    stock = Column(Integer, default=100)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    # NOTE: embedding VECTOR(384) column exists in schema.sql for pgvector semantic
    # search; omitted here to keep this file runnable without the pgvector SQLAlchemy
    # type installed. Add `from pgvector.sqlalchemy import Vector` and
    # `embedding = Column(Vector(384))` once pgvector is set up in your environment.


class Customer(Base):
    __tablename__ = "customers"
    id = uuid_col()
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"))
    name = Column(String)
    email = Column(String)
    ltv = Column(Numeric(10, 2), default=0)
    propensity_score = Column(Numeric(5, 2), default=50)
    last_order_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class Event(Base):
    __tablename__ = "events"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"))
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"))
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id", ondelete="SET NULL"))
    event_type = Column(String, nullable=False)
    device = Column(String, default="unknown")
    metadata_json = Column("metadata", JSON, default={})
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class Offer(Base):
    __tablename__ = "offers"
    id = uuid_col()
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"))
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"))
    cart_value = Column(Numeric(10, 2), nullable=False)
    proposed_discount_pct = Column(Numeric(5, 2), nullable=False)
    final_discount_pct = Column(Numeric(5, 2), nullable=False)
    discount_amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String, default="pending")
    reasoning_trace = Column(JSON, default=[])
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class Experiment(Base):
    __tablename__ = "experiments"
    id = uuid_col()
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"))
    title = Column(String, nullable=False)
    hypothesis = Column(String)
    control_metric = Column(Numeric(10, 4))
    variant_metric = Column(Numeric(10, 4))
    lift_pct = Column(Numeric(6, 3))
    confidence_pct = Column(Numeric(5, 2))
    status = Column(String, default="proposed")
    is_simulated = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class Order(Base):
    __tablename__ = "orders"
    id = uuid_col()
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"))
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="SET NULL"))
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id", ondelete="SET NULL"))
    razorpay_order_id = Column(String)
    razorpay_payment_id = Column(String)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String, default="INR")
    status = Column(String, default="created")
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class AgentActivityLog(Base):
    __tablename__ = "agent_activity_log"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    merchant_id = Column(UUID(as_uuid=True), ForeignKey("merchants.id", ondelete="CASCADE"))
    agent_name = Column(String, nullable=False)
    action = Column(String, nullable=False)
    details = Column(JSON, default={})
    requires_approval = Column(Boolean, default=False)
    approved_at = Column(TIMESTAMP(timezone=True))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
