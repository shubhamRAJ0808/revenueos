-- RevenueOS database schema
-- Run: psql $DATABASE_URL -f schema.sql

CREATE EXTENSION IF NOT EXISTS pgvector;
CREATE EXTENSION IF NOT EXISTS vector; -- pgvector's actual extension name

CREATE TABLE IF NOT EXISTS merchants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS guardrails (
    merchant_id UUID PRIMARY KEY REFERENCES merchants(id) ON DELETE CASCADE,
    max_discount_pct NUMERIC(5,2) NOT NULL DEFAULT 10,
    min_margin_pct NUMERIC(5,2) NOT NULL DEFAULT 15,
    max_offer_amount NUMERIC(10,2) NOT NULL DEFAULT 2000,
    max_daily_offers INT NOT NULL DEFAULT 500,
    auto_execute_payments BOOLEAN NOT NULL DEFAULT false,
    auto_launch_campaigns BOOLEAN NOT NULL DEFAULT false,
    high_value_requires_approval BOOLEAN NOT NULL DEFAULT true,
    high_value_threshold NUMERIC(10,2) NOT NULL DEFAULT 40000,
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID REFERENCES merchants(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    price NUMERIC(10,2) NOT NULL,
    tags TEXT[] DEFAULT '{}',
    stock INT DEFAULT 100,
    embedding VECTOR(384), -- semantic search over name+description+tags
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID REFERENCES merchants(id) ON DELETE CASCADE,
    name TEXT,
    email TEXT,
    ltv NUMERIC(10,2) DEFAULT 0,
    propensity_score NUMERIC(5,2) DEFAULT 50, -- 0-100, output of the propensity model
    last_order_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Funnel / behavioral events: view, add_to_cart, checkout_started, payment_completed
CREATE TABLE IF NOT EXISTS events (
    id BIGSERIAL PRIMARY KEY,
    merchant_id UUID REFERENCES merchants(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
    product_id UUID REFERENCES products(id) ON DELETE SET NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('view','add_to_cart','checkout_started','payment_completed','payment_failed')),
    device TEXT DEFAULT 'unknown', -- mobile / desktop
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_events_merchant_type ON events(merchant_id, event_type);
CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);

CREATE TABLE IF NOT EXISTS offers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID REFERENCES merchants(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(id) ON DELETE CASCADE,
    cart_value NUMERIC(10,2) NOT NULL,
    proposed_discount_pct NUMERIC(5,2) NOT NULL,
    final_discount_pct NUMERIC(5,2) NOT NULL,
    discount_amount NUMERIC(10,2) NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','approved','rejected','auto_applied','expired')),
    reasoning_trace JSONB DEFAULT '[]', -- explainability: each guardrail check step
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS experiments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID REFERENCES merchants(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    hypothesis TEXT,
    control_metric NUMERIC(10,4),
    variant_metric NUMERIC(10,4),
    lift_pct NUMERIC(6,3),
    confidence_pct NUMERIC(5,2),
    status TEXT NOT NULL DEFAULT 'proposed' CHECK (status IN ('proposed','running','completed','rejected')),
    is_simulated BOOLEAN NOT NULL DEFAULT true, -- always label simulated results explicitly
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    merchant_id UUID REFERENCES merchants(id) ON DELETE CASCADE,
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
    offer_id UUID REFERENCES offers(id) ON DELETE SET NULL,
    razorpay_order_id TEXT,
    razorpay_payment_id TEXT,
    amount NUMERIC(10,2) NOT NULL,
    currency TEXT DEFAULT 'INR',
    status TEXT NOT NULL DEFAULT 'created' CHECK (status IN ('created','paid','failed')),
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Full audit trail of every agent decision, for the "Agent Activity" screen and for
-- demonstrating explainability/trust to evaluators.
CREATE TABLE IF NOT EXISTS agent_activity_log (
    id BIGSERIAL PRIMARY KEY,
    merchant_id UUID REFERENCES merchants(id) ON DELETE CASCADE,
    agent_name TEXT NOT NULL, -- IntentAgent, DiscoveryAgent, OfferAgent, ConversionAgent, ExperimentAgent, ChurnAgent, PaymentAgent
    action TEXT NOT NULL,
    details JSONB DEFAULT '{}',
    requires_approval BOOLEAN DEFAULT false,
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_activity_merchant_time ON agent_activity_log(merchant_id, created_at DESC);
