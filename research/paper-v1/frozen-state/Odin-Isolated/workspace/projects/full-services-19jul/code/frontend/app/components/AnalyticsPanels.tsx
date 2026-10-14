import React from 'react';
import { Card, Metric } from './Card';
import { BarChart } from './BarChart';

const money = (n: any) => `$${Number(n || 0).toLocaleString()}`;
const pct = (n: any) => (n == null ? '—' : `${(Number(n) * 100).toFixed(1)}%`);

// CRM analytics — pipeline value, win/close rates, value by stage.
export function CrmAnalyticsPanel({ crm }: { crm: any }) {
  const s = crm?.summary || {};
  const stages = (crm?.byStage || []).map((r: any) => ({ label: r.stage, value: Number(r.value) }));
  return (
    <Card title="Analytics · CRM Pipeline" subtitle="HubSpot deals">
      <Metric label="Pipeline value" value={money(s.pipeline_value)} />
      <Metric label="Open value" value={money(s.open_value)} />
      <Metric label="Won value" value={money(s.won_value)} />
      <Metric label="Open / Closed deals" value={`${s.open_deals ?? '—'} / ${s.closed_deals ?? '—'}`} />
      <Metric label="Win rate" value={pct(s.win_rate)} />
      <Metric label="Close rate" value={pct(s.close_rate)} />
      {stages.length ? <BarChart data={stages} color="#4c8dff" /> : null}
    </Card>
  );
}

// Email analytics — opens/clicks/deliverability + top campaigns by opens.
export function EmailAnalyticsPanel({ email }: { email: any }) {
  const o = email?.overview || {};
  const top = (email?.campaigns || [])
    .slice(0, 6)
    .map((c: any) => ({ label: c.name, value: Number(c.opens) }));
  return (
    <Card title="Analytics · Email Engagement" subtitle="Klaviyo campaigns">
      <Metric label="Campaigns (live / draft)" value={`${o.campaigns ?? '—'} (${o.live_campaigns ?? 0} / ${o.draft_campaigns ?? 0})`} />
      <Metric label="Delivered" value={Number(o.delivered || 0).toLocaleString()} />
      <Metric label="Opens / Clicks" value={`${Number(o.opens || 0).toLocaleString()} / ${Number(o.clicks || 0).toLocaleString()}`} />
      <Metric label="Open rate" value={pct(o.open_rate)} />
      <Metric label="Click rate" value={pct(o.click_rate)} />
      {top.length ? <BarChart data={top} color="#42c98f" /> : null}
    </Card>
  );
}

// Fulfillment analytics — shipment throughput by status + avg transit time.
export function FulfillmentAnalyticsPanel({ fulfillment }: { fulfillment: any }) {
  const o = fulfillment?.overview || {};
  const rows = (fulfillment?.throughput || []).map((r: any) => ({ label: r.status, value: Number(r.shipments) }));
  return (
    <Card title="Analytics · Fulfillment Throughput" subtitle="Veeqo shipments">
      <Metric label="Orders" value={Number(o.orders || 0).toLocaleString()} />
      <Metric label="Order value" value={money(o.order_value)} />
      <Metric label="Shipments" value={Number(o.shipments || 0).toLocaleString()} />
      <Metric label="In transit / Delivered" value={`${o.in_transit ?? 0} / ${o.delivered ?? 0}`} />
      <Metric label="Pending" value={o.pending ?? 0} />
      {rows.length ? <BarChart data={rows} color="#e0a24c" /> : null}
    </Card>
  );
}
