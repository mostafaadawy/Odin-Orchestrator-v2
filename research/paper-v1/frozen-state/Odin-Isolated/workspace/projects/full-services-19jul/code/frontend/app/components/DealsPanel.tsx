import React from 'react';
import { Card, Metric } from './Card';

// HubSpot deals panel — renders CRM pipeline value and top deals.
export function DealsPanel({ pipeline, deals }: { pipeline: any; deals: any[] }) {
  const fmt = (n: number) =>
    new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(n || 0);
  return (
    <Card title="CRM · HubSpot Deals" subtitle="pipeline">
      <Metric label="Total deals" value={pipeline?.deals ?? '—'} />
      <Metric label="Pipeline value" value={pipeline ? fmt(pipeline.totalValue) : '—'} />
      <Metric label="Open" value={pipeline?.open ?? '—'} />
      <Metric label="Won" value={pipeline?.won ?? '—'} />
      <div style={{ marginTop: 12 }}>
        {(deals || []).slice(0, 5).map((d) => (
          <div key={d.id || d.hubspotId} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13, padding: '3px 0' }}>
            <span>{d.name}</span>
            <span style={{ color: '#7fd1a8' }}>{fmt(Number(d.amount))}</span>
          </div>
        ))}
        {(!deals || deals.length === 0) && <em style={{ color: '#8aa0c0' }}>No deals synced yet — run POST /api/crm/sync.</em>}
      </div>
    </Card>
  );
}
