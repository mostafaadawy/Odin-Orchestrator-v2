-- Odin Markets Operations Platform — PostgreSQL schema
-- Covers CRM (HubSpot), Email engagement (Klaviyo), Fulfillment (Veeqo) and Support.
-- Run: psql "$DATABASE_URL" -f prisma/migrations/0001_init.sql

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================ CRM (HubSpot) ============================
CREATE TABLE IF NOT EXISTS crm_contacts (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  hubspot_id    TEXT UNIQUE,
  email         TEXT,
  first_name    TEXT,
  last_name     TEXT,
  company       TEXT,
  lifecycle     TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS crm_deals (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  hubspot_id    TEXT UNIQUE,
  name          TEXT NOT NULL,
  stage         TEXT,
  pipeline      TEXT,
  amount        NUMERIC(14,2) DEFAULT 0,
  close_date    TIMESTAMPTZ,
  is_closed     BOOLEAN DEFAULT FALSE,
  is_won        BOOLEAN DEFAULT FALSE,
  contact_id    UUID REFERENCES crm_contacts(id) ON DELETE SET NULL,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_crm_deals_stage ON crm_deals(stage);

-- ======================= EMAIL ENGAGEMENT (Klaviyo) =======================
CREATE TABLE IF NOT EXISTS email_campaigns (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  klaviyo_id    TEXT UNIQUE,
  name          TEXT NOT NULL,
  status        TEXT,                 -- live | draft
  channel       TEXT DEFAULT 'email',
  send_time     TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS email_engagement (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  campaign_id   UUID REFERENCES email_campaigns(id) ON DELETE CASCADE,
  klaviyo_id    TEXT,
  recipients    INTEGER DEFAULT 0,
  delivered     INTEGER DEFAULT 0,
  opens         INTEGER DEFAULT 0,
  clicks        INTEGER DEFAULT 0,
  bounces       INTEGER DEFAULT 0,
  unsubscribes  INTEGER DEFAULT 0,
  recorded_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_email_engagement_campaign ON email_engagement(campaign_id);

-- ========================= FULFILLMENT (Veeqo) =========================
CREATE TABLE IF NOT EXISTS fulfillment_orders (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  veeqo_id      TEXT UNIQUE,
  number        TEXT,
  status        TEXT,
  total_price   NUMERIC(14,2) DEFAULT 0,
  customer_name TEXT,
  placed_at     TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fulfillment_shipments (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  veeqo_id      TEXT UNIQUE,
  order_id      UUID REFERENCES fulfillment_orders(id) ON DELETE CASCADE,
  carrier       TEXT,
  tracking_no   TEXT,
  status        TEXT,                 -- pending | shipped | delivered
  shipped_at    TIMESTAMPTZ,
  delivered_at  TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_shipments_status ON fulfillment_shipments(status);

-- ========================= CUSTOMER SUPPORT =========================
CREATE TABLE IF NOT EXISTS support_tickets (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subject       TEXT NOT NULL,
  body          TEXT,
  status        TEXT DEFAULT 'open',  -- open | pending | resolved | closed
  priority      TEXT DEFAULT 'normal',
  contact_id    UUID REFERENCES crm_contacts(id) ON DELETE SET NULL,
  assignee      TEXT,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON support_tickets(status);
