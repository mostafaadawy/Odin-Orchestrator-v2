# Living Asset & Attack-Surface Inventory  ·  2026-07-15

Maintained by the Asset, Exposure & Attack-Surface Agent. The SOC monitors WHAT WE ACTUALLY RUN; threat intelligence + prediction are filtered to this list (reverse search) to save time and stay precise.

## Reverse-search filter (targets intel to our real stack)
- Ecosystems: —
- Frameworks/stacks: NestJS (Node API), Next.js (SSR/React), Node.js, Prisma/PostgreSQL, Static/landing
- Providers/clouds in use: azure-vm, local/project

## Services & exposure

| Service | Provider | Public | Stacks | In SOC scope |
|---|---|---|---|---|
| organics + bendcore (Azure VM) | azure-vm | https://anchor.odinmarkets.com | Next.js (SSR/React), NestJS (Node API), Prisma/PostgreSQL | yes |
| Odin anchor + web (Azure VM) | azure-vm | https://anchor.odinmarkets.com/odin-anchor, https://anchor.odinmarkets.com/odin-web | Node.js, Static/landing | yes |

## Discovered platform projects (candidates for scope)

| Project | Stacks | In scope |
|---|---|---|
| Fulfillment — VQ status (read-only) | (unknown — no localPath markers) | candidate |
| Email — Klaviyo workflows (read-only) | (unknown — no localPath markers) | candidate |
| Revealer | (unknown — no localPath markers) | candidate |
| Egypt Amazon Daily Social Content Agent | (unknown — no localPath markers) | candidate |
| Zoom Smart Meeting Notification Agent | (unknown — no localPath markers) | candidate |
| Organics Production Deploy (2VM) | (unknown — no localPath markers) | candidate |
| RedBerry Continuous SOC | (unknown — no localPath markers) | candidate |

## Supported provider models (extensible — one dict adds a cloud)

- **azure-vm** — Microsoft Azure — Linux VM: monitors ssh, services, ports/NSG, ufw, processes, db, nginx logs. read-only SSH + `az network nsg` (both already wired)
- **aws-ec2** — AWS EC2: monitors ssh, services, security-groups, processes, db. read-only SSH + `aws ec2 describe-security-groups` (adapter TODO — same check functions)
- **godaddy** — GoDaddy shared/VPS + DNS: monitors dns records, tls/cert expiry, http health, exposed panels. GoDaddy Domains API (read) + public HTTP probes (no SSH on shared hosting)
- **hostinger** — Hostinger VPS/shared: monitors http health, tls/cert expiry, ssh (VPS), exposed panels. public HTTP probes + SSH where a VPS exposes it
- **cloudflare** — Cloudflare (edge/DNS/WAF): monitors dns, waf rules, tls, cache/exposure. Cloudflare API (read) — recommended edge in front of any origin
- **static-cdn** — Static/CDN (Vercel/Netlify/Pages): monitors http health, tls, headers, secrets in bundle. public HTTP + header/CSP probes

_Updated by the Asset, Exposure & Attack-Surface Agent: 2026-07-15._
