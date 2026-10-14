import React from 'react';

// Dependency-free horizontal bar chart — keeps the frontend build lean
// (no charting library to install) while still visualising analytics rows.
export function BarChart({ data, color = '#4c8dff' }: { data: { label: string; value: number }[]; color?: string }) {
  const max = Math.max(1, ...data.map((d) => d.value || 0));
  return (
    <div style={{ marginTop: 8 }}>
      {data.map((d) => (
        <div key={d.label} style={{ margin: '8px 0' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: '#8aa0c0' }}>
            <span>{d.label}</span>
            <strong style={{ color: '#e6edf6' }}>{Number(d.value || 0).toLocaleString()}</strong>
          </div>
          <div style={{ background: '#1a2540', borderRadius: 6, height: 8, marginTop: 4 }}>
            <div
              style={{
                width: `${Math.round(((d.value || 0) / max) * 100)}%`,
                background: color,
                height: 8,
                borderRadius: 6,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
