import React from 'react';

export function Card({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <section
      style={{
        background: '#111c33',
        border: '1px solid #1e2a44',
        borderRadius: 12,
        padding: 20,
        minWidth: 320,
        flex: '1 1 340px',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
        <h2 style={{ margin: 0, fontSize: 16 }}>{title}</h2>
        {subtitle ? <span style={{ color: '#8aa0c0', fontSize: 12 }}>{subtitle}</span> : null}
      </div>
      <div style={{ marginTop: 14 }}>{children}</div>
    </section>
  );
}

export function Metric({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: '1px solid #1a2540' }}>
      <span style={{ color: '#8aa0c0', fontSize: 13 }}>{label}</span>
      <strong style={{ fontSize: 14 }}>{value}</strong>
    </div>
  );
}
