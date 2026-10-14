import React from 'react';
import Link from 'next/link';
import { api } from '../lib/api';
import { DealsPanel } from './components/DealsPanel';
import { EngagementPanel } from './components/EngagementPanel';
import { ShipmentsPanel } from './components/ShipmentsPanel';

// Odin Ops dashboard. Server component: pulls unified ops data from the NestJS API.
// Each fetch is guarded so the dashboard still renders if a service is offline.
async function safe<T>(p: Promise<T>, fallback: T): Promise<T> {
  try {
    return await p;
  } catch {
    return fallback;
  }
}

export default async function DashboardPage() {
  const [pipeline, deals, engagement, campaigns, throughput, shipments] = await Promise.all([
    safe(api.pipeline(), null),
    safe(api.deals(), []),
    safe(api.engagement(), null),
    safe(api.campaigns(), []),
    safe(api.throughput(), null),
    safe(api.shipments(), []),
  ]);

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
        <Link href="/analytics" style={{ color: '#4c8dff', fontSize: 13 }}>Operations Analytics →</Link>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20 }}>
        <DealsPanel pipeline={pipeline} deals={deals} />
        <EngagementPanel engagement={engagement} campaigns={campaigns} />
        <ShipmentsPanel throughput={throughput} shipments={shipments} />
      </div>
    </div>
  );
}
