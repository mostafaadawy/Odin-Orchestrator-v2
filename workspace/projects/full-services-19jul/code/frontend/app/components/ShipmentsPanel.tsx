import React from 'react';
import { Card, Metric } from './Card';

// Veeqo fulfillment panel — shipment throughput by status.
export function ShipmentsPanel({ throughput, shipments }: { throughput: any; shipments: any[] }) {
  const byStatus = throughput?.byStatus || {};
  return (
    <Card title="Fulfillment · Veeqo Shipments" subtitle="throughput">
      <Metric label="Orders" value={throughput?.orders ?? '—'} />
      <Metric label="Shipments" value={throughput?.shipments ?? shipments?.length ?? '—'} />
      {Object.keys(byStatus).length === 0 ? (
        <em style={{ color: '#8aa0c0' }}>No shipments synced yet — run POST /api/fulfillment/sync.</em>
      ) : (
        Object.entries(byStatus).map(([k, v]) => <Metric key={k} label={k} value={v as number} />)
      )}
    </Card>
  );
}
