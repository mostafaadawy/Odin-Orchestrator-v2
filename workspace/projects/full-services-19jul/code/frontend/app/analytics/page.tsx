import React from 'react';
import Link from 'next/link';
import { api } from '../../lib/api';
import { CrmAnalyticsPanel, EmailAnalyticsPanel, FulfillmentAnalyticsPanel } from '../components/AnalyticsPanels';

// Analytics operations view — server component pulling the unified /analytics
// snapshot (CRM pipeline, Klaviyo engagement, Veeqo throughput) from the API.
async function safe<T>(p: Promise<T>, fallback: T): Promise<T> {
  try {
    return await p;
  } catch {
    return fallback;
  }
}

export default async function AnalyticsPage() {
  const data = await safe<any>(api.analytics(), { crm: null, email: null, fulfillment: null });

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 16 }}>
        <h2 style={{ margin: 0, fontSize: 18 }}>Operations Analytics</h2>
        <Link href="/" style={{ color: '#8aa0c0', fontSize: 13 }}>← Back to dashboard</Link>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 20 }}>
        <CrmAnalyticsPanel crm={data?.crm} />
        <EmailAnalyticsPanel email={data?.email} />
        <FulfillmentAnalyticsPanel fulfillment={data?.fulfillment} />
      </div>
    </div>
  );
}
