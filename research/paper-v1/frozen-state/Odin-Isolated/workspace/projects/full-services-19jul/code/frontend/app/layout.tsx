import React from 'react';

export const metadata = {
  title: 'Odin Markets — Operations Platform',
  description: 'Unified CRM, Email and Fulfillment operations dashboard',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, sans-serif',
          background: '#0b1220',
          color: '#e6edf6',
        }}
      >
        <header style={{ padding: '18px 28px', borderBottom: '1px solid #1e2a44' }}>
          <h1 style={{ margin: 0, fontSize: 20 }}>Odin Markets · Operations Platform</h1>
          <p style={{ margin: '4px 0 0', color: '#8aa0c0', fontSize: 13 }}>
            CRM (HubSpot) · Email (Klaviyo) · Fulfillment (Veeqo)
          </p>
        </header>
        <main style={{ padding: 28 }}>{children}</main>
      </body>
    </html>
  );
}
