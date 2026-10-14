import React from 'react';
import { Card, Metric } from './Card';

// Klaviyo engagement panel — opens/clicks/deliverability + campaign/flow counts.
export function EngagementPanel({ engagement, campaigns }: { engagement: any; campaigns: any[] }) {
  const pct = (n: number) => `${((n || 0) * 100).toFixed(1)}%`;
  const live = (campaigns || []).filter((c) => c.status === 'live').length;
  const draft = (campaigns || []).filter((c) => c.status === 'draft').length;
  return (
    <Card title="Email · Klaviyo Engagement" subtitle="opens / clicks">
      <Metric label="Campaigns / flows" value={engagement?.campaigns ?? campaigns?.length ?? '—'} />
      <Metric label="Live / Draft" value={`${live} / ${draft}`} />
      <Metric label="Delivered" value={engagement?.delivered ?? '—'} />
      <Metric label="Opens" value={engagement?.opens ?? '—'} />
      <Metric label="Clicks" value={engagement?.clicks ?? '—'} />
      <Metric label="Open rate" value={engagement ? pct(engagement.openRate) : '—'} />
      <Metric label="Click rate" value={engagement ? pct(engagement.clickRate) : '—'} />
    </Card>
  );
}
