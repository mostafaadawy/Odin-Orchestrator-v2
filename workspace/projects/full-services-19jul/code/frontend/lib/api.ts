// Central API client for the Odin Ops dashboard. Talks to the NestJS backend.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:4000/api';

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`API ${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  deals: () => get<any[]>('/crm/deals'),
  pipeline: () => get<any>('/crm/pipeline'),
  campaigns: () => get<any[]>('/email/campaigns'),
  engagement: () => get<any>('/email/engagement'),
  shipments: () => get<any[]>('/fulfillment/shipments'),
  throughput: () => get<any>('/fulfillment/throughput'),
  supportSummary: () => get<any>('/support/summary'),
  health: () => get<any>('/health'),
  // Analytics operations layer (aggregated metrics from the SQL views).
  analytics: () => get<any>('/analytics'),
  analyticsCrm: () => get<any>('/analytics/crm'),
  analyticsEmail: () => get<any>('/analytics/email'),
  analyticsFulfillment: () => get<any>('/analytics/fulfillment'),
};
