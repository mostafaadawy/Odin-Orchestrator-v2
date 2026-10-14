# Odin Markets — Operations Platform (full-stack)

Internal operations platform unifying **CRM (HubSpot)**, **Email engagement (Klaviyo)** and
**Fulfillment (Veeqo)** into a single dashboard, backed by PostgreSQL.

## Layout
```
code/
├── backend/                 NestJS API (TypeScript)
│   ├── src/
│   │   ├── main.ts          bootstrap (port 4000, prefix /api)
│   │   ├── app.module.ts    TypeORM + feature modules
│   │   ├── crm/             HubSpot deals/contacts  (module/controller/service/client/entities)
│   │   ├── email/           Klaviyo campaigns/engagement
│   │   ├── fulfillment/     Veeqo orders/shipments
│   │   ├── support/         customer-support ticket workflow
│   │   └── health/          health check
│   └── prisma/migrations/0001_init.sql   PostgreSQL schema (CRM/email/fulfillment/support)
└── frontend/                Next.js 14 App Router dashboard
    ├── app/page.tsx         dashboard (deals + engagement + shipments)
    ├── app/components/       DealsPanel · EngagementPanel · ShipmentsPanel
    └── lib/api.ts           API client
```

## API endpoints
| Method | Path | Purpose |
|--------|------|---------|
| GET  | /api/health              | liveness |
| GET  | /api/crm/deals           | HubSpot deals |
| GET  | /api/crm/pipeline        | pipeline value / open / won |
| POST | /api/crm/sync            | pull live deals from HubSpot |
| GET  | /api/email/campaigns     | Klaviyo campaigns/flows |
| GET  | /api/email/engagement    | opens/clicks/rates |
| POST | /api/email/sync          | pull live flows from Klaviyo |
| GET  | /api/fulfillment/shipments | Veeqo shipments |
| GET  | /api/fulfillment/throughput | shipment counts by status |
| POST | /api/fulfillment/sync    | pull live orders from Veeqo |
| GET/POST/PATCH | /api/support/tickets | support workflow |

## Run (local / sandbox)
```bash
# backend
cd backend && npm install
cp .env.example .env          # set DATABASE_URL + HUBSPOT/KLAVIYO/VEEQO keys (from env)
psql "$DATABASE_URL" -f prisma/migrations/0001_init.sql
npm run start

# frontend
cd frontend && npm install
cp .env.local.example .env.local
npm run dev
```

Integration keys are read from the **environment** (`HUBSPOT_API_KEY`, `KLAVIYO_API_KEY`,
`VEEQO_API_KEY`) — never hardcoded. Deploys to a VM **sandbox** with its own DB and internal
port, never touching production.
