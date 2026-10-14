-- Odin Markets Operations Platform — Analytics layer (SQL views)
-- Aggregates CRM (HubSpot), Email (Klaviyo) and Fulfillment (Veeqo) raw tables
-- from 0001_init.sql into operations metrics consumed by /analytics endpoints.
-- Run AFTER 0001_init.sql: psql "$DATABASE_URL" -f prisma/migrations/0002_analytics_views.sql

-- ===================== CRM · pipeline & win/close rates =====================
-- Pipeline value + open/close/win rates, overall.
CREATE OR REPLACE VIEW analytics_crm_pipeline AS
SELECT
  COUNT(*)                                                        AS total_deals,
  COALESCE(SUM(amount), 0)                                        AS pipeline_value,
  COALESCE(SUM(amount) FILTER (WHERE is_closed = FALSE), 0)       AS open_value,
  COALESCE(SUM(amount) FILTER (WHERE is_won = TRUE), 0)           AS won_value,
  COUNT(*) FILTER (WHERE is_closed = FALSE)                       AS open_deals,
  COUNT(*) FILTER (WHERE is_closed = TRUE)                        AS closed_deals,
  COUNT(*) FILTER (WHERE is_won = TRUE)                           AS won_deals,
  ROUND(
    COUNT(*) FILTER (WHERE is_won = TRUE)::numeric
    / NULLIF(COUNT(*) FILTER (WHERE is_closed = TRUE), 0), 4)     AS win_rate,
  ROUND(
    COUNT(*) FILTER (WHERE is_closed = TRUE)::numeric
    / NULLIF(COUNT(*), 0), 4)                                     AS close_rate
FROM crm_deals;

-- Pipeline value broken down by stage (for the funnel/bar chart).
CREATE OR REPLACE VIEW analytics_crm_by_stage AS
SELECT
  COALESCE(stage, 'unknown')       AS stage,
  COUNT(*)                         AS deals,
  COALESCE(SUM(amount), 0)         AS value,
  COUNT(*) FILTER (WHERE is_won)   AS won
FROM crm_deals
GROUP BY COALESCE(stage, 'unknown')
ORDER BY value DESC;

-- ===================== EMAIL · campaign opens/clicks =====================
-- Per-campaign engagement rollup joined to campaign name/status.
CREATE OR REPLACE VIEW analytics_email_campaigns AS
SELECT
  c.id                                        AS campaign_id,
  c.name                                      AS name,
  c.status                                    AS status,
  COALESCE(SUM(e.recipients), 0)              AS recipients,
  COALESCE(SUM(e.delivered), 0)               AS delivered,
  COALESCE(SUM(e.opens), 0)                   AS opens,
  COALESCE(SUM(e.clicks), 0)                  AS clicks,
  COALESCE(SUM(e.bounces), 0)                 AS bounces,
  COALESCE(SUM(e.unsubscribes), 0)            AS unsubscribes,
  ROUND(SUM(e.opens)::numeric  / NULLIF(SUM(e.delivered), 0), 4) AS open_rate,
  ROUND(SUM(e.clicks)::numeric / NULLIF(SUM(e.delivered), 0), 4) AS click_rate
FROM email_campaigns c
LEFT JOIN email_engagement e ON e.campaign_id = c.id
GROUP BY c.id, c.name, c.status;

-- Overall email engagement + live/draft campaign counts.
CREATE OR REPLACE VIEW analytics_email_overview AS
SELECT
  (SELECT COUNT(*) FROM email_campaigns)                           AS campaigns,
  (SELECT COUNT(*) FROM email_campaigns WHERE status = 'live')     AS live_campaigns,
  (SELECT COUNT(*) FROM email_campaigns WHERE status = 'draft')    AS draft_campaigns,
  COALESCE(SUM(recipients), 0)                                     AS recipients,
  COALESCE(SUM(delivered), 0)                                      AS delivered,
  COALESCE(SUM(opens), 0)                                          AS opens,
  COALESCE(SUM(clicks), 0)                                         AS clicks,
  COALESCE(SUM(bounces), 0)                                        AS bounces,
  COALESCE(SUM(unsubscribes), 0)                                   AS unsubscribes,
  ROUND(SUM(opens)::numeric  / NULLIF(SUM(delivered), 0), 4)       AS open_rate,
  ROUND(SUM(clicks)::numeric / NULLIF(SUM(delivered), 0), 4)       AS click_rate
FROM email_engagement;

-- ===================== FULFILLMENT · shipment throughput =====================
-- Throughput by shipment status + average ship→deliver time in hours.
CREATE OR REPLACE VIEW analytics_fulfillment_throughput AS
SELECT
  COALESCE(status, 'unknown')                                     AS status,
  COUNT(*)                                                        AS shipments,
  COUNT(*) FILTER (WHERE delivered_at IS NOT NULL)                AS delivered,
  ROUND(AVG(EXTRACT(EPOCH FROM (delivered_at - shipped_at)) / 3600.0)
    FILTER (WHERE delivered_at IS NOT NULL AND shipped_at IS NOT NULL), 2)
                                                                  AS avg_transit_hours
FROM fulfillment_shipments
GROUP BY COALESCE(status, 'unknown')
ORDER BY shipments DESC;

-- Fulfillment overview: order + shipment totals and revenue in flight.
CREATE OR REPLACE VIEW analytics_fulfillment_overview AS
SELECT
  (SELECT COUNT(*) FROM fulfillment_orders)                                 AS orders,
  (SELECT COALESCE(SUM(total_price), 0) FROM fulfillment_orders)            AS order_value,
  (SELECT COUNT(*) FROM fulfillment_shipments)                             AS shipments,
  (SELECT COUNT(*) FROM fulfillment_shipments WHERE status = 'shipped')     AS in_transit,
  (SELECT COUNT(*) FROM fulfillment_shipments WHERE status = 'delivered')   AS delivered,
  (SELECT COUNT(*) FROM fulfillment_shipments WHERE status = 'pending')     AS pending;
