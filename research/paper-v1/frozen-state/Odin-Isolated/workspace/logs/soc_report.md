# RedBerry Continuous SOC — Security Health Report

_Automated multi-agent SOC · 2026-07-18 · monitor-and-report only_

**Odin AI Systems** — RedBerry Continuous SOC · Observe → Correlate → Verify → Report → Approve

- **Project:** RedBerry Continuous SOC
- **Run date:** 2026-07-18 03:00
- **Status:** Attention needed
- **Mode:** monitor-and-report only
- **Auto-remediation:** DISABLED (approval-gated)
- **Findings:** C0 H2 M4 L7 I4

## In Plain Words (read this first)

A human-readable summary before the technical detail — understand the whole picture here, then drill into the sections below if you want the evidence.

- In plain words: things are mostly fine, but a few items deserve a look. Nothing was changed — I only observed and am reporting. Here is what stood out and what I'd suggest.
- What stood out: Service health (needs review); Network listeners (needs review); Multi-cloud surface posture (suspicious); Website / endpoint health (suspicious); SSH keys / users (needs review).
- What could go wrong next (so we prevent it now): A transitive npm dependency gains a critical advisory and becomes exploitable The fix before it happens: Pin + monitor (already via OSV); enable Dependabot/renovate; test-gated upgrades; runtime WAF.
- If disaster struck: we have a recent encrypted backup and a smart recovery plan ready.
- Growing safely: Bring 'Revealer' into SOC scope — stack: Python; recommend enrolling it (health + dependency + surface checks apply directly).
- You can act on any recommendation, defer it, or ignore it — the system never changes anything on its own.

## Executive Summary  `Attention needed`

Overall security status: **Attention needed**. Mode: **monitor-and-report only**. No production changes were made. Findings — critical 0, high 2, medium 4, low 7, informational 4. Approval requests raised: 2 (auto-denied while in monitor/test mode — nothing executed).

## Issue Tracker (remembered across runs)

- 🆕 New this run: 0
- 🔓 Still open (unresolved): 13
- ⏸️ Pending / left for now: 0
- 🤝 Accepted risk: 0
- ✅ Resolved: 1

### Open & New Issues

| ID | Title | Severity | Confidence | Class |
| --- | --- | --- | --- | --- |
| SOC-OPS-001 | Service health | medium | low | Needs Review |
| SOC-NET-001 | Network listeners | low | low | Needs Review |
| SOC-CLOUD-004 | Multi-cloud surface posture | medium | medium | Suspicious |
| SOC-NET-002 | Website / endpoint health | high | high | Suspicious |
| SOC-AUTH-002 | SSH keys / users | low | low | Needs Review |
| SOC-HOST-003 | Persistence | low | low | Needs Review |
| SOC-HOST-002 | Crypto-miner / hijack hunt | low | low | Needs Review |
| SOC-APP-001 | Newsletter/registration abuse | medium | low | Needs Review |
| SOC-DB-002 | Database anomaly (read-only) | low | low | Needs Review |
| SOC-APP-004 | Subscriber/account forensics | low | low | Needs Review |
| SOC-IDS-001 | Behavioral intrusion detection | medium | low | Needs Review |
| SOC-SENSOR-008 | 24/7 sensor ingest | low | low | Needs Review |
| SOC-DEP-002 | Dependency vulnerability intelligence | high | medium | Suspicious |

### Resolved

| ID | Title | Resolved by |
| --- | --- | --- |
| SOC-CLOUD-003 | Port hardening (defense-in-depth) | auto (no longer detected) |

## Threat Hunt (ATT&CK hypotheses tested against evidence)

| Technique | Hunt | Verdict | Evidence |
| --- | --- | --- | --- |
| T1190→T1496 | Public-app exploit → resource hijack (mining) | inconclusive | dependency risk present but no host miner evidence |
| T1190 | Known-exploited vulnerability exposure | refuted | none of our runtime CVEs are on the KEV list |
| T1583/T1586 | Automated account/newsletter abuse | inconclusive | no strong automation signal this run |
| T1498/T1499 | Service availability / DoS | supported | service/website health degraded |
| T1078 | Unauthorized access / new SSH key or user | inconclusive | could not read ssh/users (compare to known-good baseline) |
| T1485/T1486 | Recoverability if data is destroyed | supported | encrypted dated backups + smart date-aware recovery are in place |
| T1190/T1189 | Weak public surface (headers/TLS) | supported | anchor.odinmarkets.com: missing headers ['strict-transport-security']; anchor.odinmarkets.com: missing headers ['strict- |

## Prediction & Prevention (proactive hardening before exploitation)

| Likelihood | Area | Prediction | Prevent by | Vector |
| --- | --- | --- | --- | --- |
| high | NestJS (Node API) · dependency surface | A transitive npm dependency gains a critical advisory and becomes exploitable | Pin + monitor (already via OSV); enable Dependabot/renovate; test-gated upgrades; runtime WAF. | T1190 → T1496 (as in the mining incident) |
| high | Static/landing · form abuse | Guest/newsletter forms become bot-abuse + third-party quota drains (the RedBerry class) | CAPTCHA + single-use tokens + rate-limit on ALL guest-triggerable endpoints; edge bot control. | business-logic abuse T1583/T1586 |
| high | Prisma/PostgreSQL · backup/DR | No verified, dated, encrypted backups → unrecoverable data loss on abuse/ransomware | Enable the Recovery agent's encrypted dated backups + periodic restore test. | T1485/T1486 data destruction |
| high | dependency drift | A currently runtime-reachable vulnerable package will be the next exploited entry point if left unpatched (this is exactly how the mining/502 incident started). | Prioritized, test-gated upgrade of runtime-reachable packages; keep OSV monitoring daily; add a WAF/edge in front; least-privilege runtime user so an exploit can't mine freely. | T1190 → T1496 resource hijacking |
| medium | NestJS (Node API) · authz | Broken object-level authorization as endpoints grow | Central guard + per-resource ownership checks; add authz tests. | T1078 valid accounts abuse |
| medium | Next.js (SSR/React) · SSR request handling | SSRF / header-injection via SSR data fetching is a recurring Next.js class | Add strict allow-lists for server-side fetch targets; security headers (CSP, HSTS, X-Content-Type-Options); disable source maps in prod. | T1190 exploit public-facing app |
| medium | Next.js (SSR/React) · client bundle | API keys/secrets accidentally shipped in the client bundle | Scan build output for secrets; keep secrets server-side only; rotate any NEXT_PUBLIC_* misuse. | T1552 unsecured credentials |
| medium | single-origin exposure | A single origin VM with no edge WAF is the likely next DoS/abuse pressure point. | Put Cloudflare/edge WAF in front; keep only 80/443 public via reverse proxy; SSH restricted to your single (dynamic) IP with a refresh protocol; ufw on. | T1498/T1499 DoS |
| medium | resilience | Without verified encrypted backups, any successful abuse/ransomware/DB corruption becomes unrecoverable. | Enable the Recovery & Resilience agent: dated, checksummed, ENCRYPTED config+DB backups + periodic restore tests + smart date-aware recovery. | T1485/T1486 data destruction |
| low | Prisma/PostgreSQL · exposure | DB drifts to a non-localhost bind or weak creds as infra changes | Keep localhost-only bind + firewall; strong rotated creds; monitor (already). | T1210 |

## Resilience & Recovery

- Encrypted-backup key fingerprint: 21242bd4a3b3299d (held on local desktop only; encryption: Fernet/AES-128-CBC+HMAC)
- Backups retained: 3 · last-backup age (days): 1.8
- Readiness: ready
- Smart recovery decision logic: recover-from-pre-problem — Restore from db-20260716T085616.enc (dated 2026-07-16T08:56:16.515605) — the newest CLEAN point BEFORE the problem. Skip newer backups (they may carry the damage). Verify sha256 before restore; restore is approval-gated.
- Narrowing rule: First confirm the ACTUAL damaged component (DB rows? config? a package?) so recovery is surgical — do not restore the whole system for a scoped problem, and do not trust a symptom as the source (verify the root cause found in the correlation phase).

## Scope Recommendations (grow the SOC to more services/clouds)

- Bring 'Revealer' into SOC scope — stack: Python; recommend enrolling it (health + dependency + surface checks apply directly).
- Bring 'Egypt Amazon Daily Social Content Agent' into SOC scope — stack: Python; recommend enrolling it (health + dependency + surface checks apply directly).
- Consider putting Cloudflare (WAF/edge) in front of the origin — adds rate-limiting/bot control the SOC can then monitor; reduces app-abuse + DoS exposure at the edge.

### Monitored Attack Surface (reverse-search targeting)

- Ecosystems: pypi
- Frameworks/stacks: NestJS (Node API), Next.js (SSR/React), Node.js, Prisma/PostgreSQL, Python, Static/landing
- Providers/clouds: azure-vm, local/project
- Provider models supported: azure-vm (live), aws-ec2, godaddy, hostinger, cloudflare, static-cdn

## All Checks (this run)

| ID | Title | Severity | Class | Data source |
| --- | --- | --- | --- | --- |
| SOC-OPS-001 | Service health | medium | Needs Review | Data unavailable |
| SOC-NET-001 | Network listeners | low | Needs Review | Data unavailable |
| SOC-CLOUD-003 | Port / firewall hardening | informational | Benign/Expected | Checked and healthy |
| SOC-CLOUD-004 | Multi-cloud surface posture | medium | Suspicious | Checked and finding detected |
| SOC-NET-002 | Website / endpoint health | high | Suspicious | Checked and finding detected |
| SOC-WEB-005 | Clickjacking / iframe-embedding protection | informational | Benign/Expected | Checked and healthy |
| SOC-AUTH-002 | SSH keys / users | low | Needs Review | Data unavailable |
| SOC-HOST-003 | Persistence | low | Needs Review | Data unavailable |
| SOC-HOST-002 | Crypto-miner / hijack hunt | low | Needs Review | Data unavailable |
| SOC-APP-001 | Newsletter/registration abuse | medium | Needs Review | Data unavailable |
| SOC-DB-002 | Database anomaly (read-only) | low | Needs Review | Data unavailable |
| SOC-APP-004 | Subscriber/account forensics | low | Needs Review | Data unavailable |
| SOC-IDS-001 | Behavioral intrusion detection | medium | Needs Review | Data unavailable |
| SOC-EXT-006 | Third-party quota monitor | informational | Benign/Expected | Checked and healthy |
| SOC-SENSOR-008 | 24/7 sensor ingest | low | Needs Review | Data unavailable |
| SOC-DEP-002 | Dependency vulnerability intelligence | high | Suspicious | Checked and finding detected |
| SOC-INTEL-007 | Fused threat intelligence (KEV + abuse.ch) | informational | Benign/Expected | Checked and healthy |

### SOC-OPS-001 — Service health  `medium`

**Confidence:** low · **Asset:** VM systemd · **Data:** Data unavailable

- Evidence: could not read systemd: ssh: connect to host 52.180.154.225 port 22: Operation timed out
- False-positive analysis: n/a

### SOC-NET-001 — Network listeners  `low`

**Confidence:** low · **Asset:** VM ports · **Data:** Data unavailable

- Evidence: could not enumerate listeners
- False-positive analysis: n/a

### SOC-CLOUD-004 — Multi-cloud surface posture  `medium`

**Confidence:** medium · **Asset:** public endpoints (any cloud) · **Data:** Checked and finding detected

- Evidence: anchor.odinmarkets.com: missing headers ['strict-transport-security']; anchor.odinmarkets.com: missing headers ['strict-transport-security']; anchor.odinmarkets.com: missing headers ['strict-transport-security'] | anchor.odinmarkets.com: TLS 76d; anchor.odinmarkets.com: TLS 76d; anchor.odinmarkets.com: TLS 76d
- False-positive analysis: credential-free probe across providers; TLS/near-expiry + missing headers are hardening signals
- Blast radius: the affected public host(s)
- Recommended remediation (approval-gated): Recommend (approval-gated): renew/auto-renew TLS; add HSTS + X-Frame-Options/CSP at the edge for every host.
- Remediation risk / downtime: none (edge/header config)

### SOC-NET-002 — Website / endpoint health  `high`

**Confidence:** high · **Asset:** public endpoints · **Data:** Checked and finding detected

- Evidence: anchor=200 web=200 organics-api=unreachable
- False-positive analysis: a non-2xx/expected status is a signal, not proof — correlate with service health

### SOC-AUTH-002 — SSH keys / users  `low`

**Confidence:** low · **Asset:** VM ssh · **Data:** Data unavailable

- Evidence: could not read ssh/users
- False-positive analysis: n/a

### SOC-HOST-003 — Persistence  `low`

**Confidence:** low · **Asset:** VM cron/systemd · **Data:** Data unavailable

- Evidence: could not read cron/timers
- False-positive analysis: n/a

### SOC-HOST-002 — Crypto-miner / hijack hunt  `low`

**Confidence:** low · **Asset:** VM processes/egress · **Data:** Data unavailable

- Evidence: could not read processes/egress
- False-positive analysis: n/a

### SOC-APP-001 — Newsletter/registration abuse  `medium`

**Confidence:** low · **Asset:** nginx access log · **Data:** Data unavailable

- Evidence: nginx abuse logs unavailable/empty: ssh: connect to host 52.180.154.225 port 22: Operation timed out
- False-positive analysis: cannot conclude healthy from missing data

### SOC-DB-002 — Database anomaly (read-only)  `low`

**Confidence:** low · **Asset:** PostgreSQL organics · **Data:** Data unavailable

- Evidence: DB read-only query unavailable: ssh: connect to host 52.180.154.225 port 22: Operation timed out
- False-positive analysis: cannot conclude healthy from missing data

### SOC-APP-004 — Subscriber/account forensics  `low`

**Confidence:** low · **Asset:** users/subscribers DB · **Data:** Data unavailable

- Evidence: DB read-only query unavailable: ssh: connect to host 52.180.154.225 port 22: Operation timed out
- False-positive analysis: cannot conclude healthy from missing data

### SOC-IDS-001 — Behavioral intrusion detection  `medium`

**Confidence:** low · **Asset:** visitor behavior (nginx) · **Data:** Data unavailable

- Evidence: no access-log behavior available to profile
- False-positive analysis: cannot conclude healthy from missing data

### SOC-SENSOR-008 — 24/7 sensor ingest  `low`

**Confidence:** low · **Asset:** VM sensor (events.jsonl) · **Data:** Data unavailable

- Evidence: sensor log not found — the 24/7 sensor is not installed yet (approval-gated: see workspace/projects/redberry-continuous-soc/code/sensor/INSTALL_SOC_SENSOR.md). Once installed it provides continuous catch-up evidence.
- False-positive analysis: not installed is not 'healthy' — install to enable 24/7 coverage

### SOC-DEP-002 — Dependency vulnerability intelligence  `high`

**Confidence:** medium · **Asset:** npm dependencies · **Data:** Checked and finding detected

- Evidence: OSV.dev: scanned 1149 pkgs; 36 vulnerable (18 runtime-reachable). Top: axios@1.13.2(23 vulns,MODERATE,runtime), next@16.1.6(19 vulns,HIGH,runtime), nodemailer@7.0.10(7 vulns,MODERATE,runtime), multer@2.0.2(5 vulns,MODERATE,runtime), lodash@4.17.21(3 vulns,MODERATE,runtime)
- False-positive analysis: PRESENCE of a CVE is NOT compromise — reachability + evidence required. See knowledge/live-dependency-intel.md
- Blast radius: the affected application
- Recommended remediation (approval-gated): Recommend (approval-gated): upgrade runtime-reachable vulnerable packages to fixed versions after regression testing.
- Remediation risk / downtime: upgrades can break functionality — test in staging first

---
Generated by the Reporting & Documentation Agent · Odin-Orchestrator. Read-only SOC — no production changes. Secrets/2FA/tokens redacted. Confidential.
