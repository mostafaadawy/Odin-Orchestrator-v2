# Playbook PB-HUNT-APP-001 — Fake-User / App-Abuse Hunting Directive

> **Incident-scoped.** This directive exists solely to hunt the fake-user / app-abuse
> activity tracked under **run-1784584358**. It is not a general threat-hunting guide.
> See the **Boundary** section — broad / general hunting is explicitly out of scope.

## Identity Reconciliation (single reference for all lanes)

Every downstream lane MUST resolve to this one incident. These IDs are the same thing:

| Role | ID |
| --- | --- |
| SOC finding | **SOC-APP-001** |
| Incident | **INC-2026-001** |
| Base response playbook | **PB-APP-001** |
| This hunting playbook | **PB-HUNT-APP-001** |
| Run | **run-1784584358** |

- Charter: [run-1784584358-charter.md](../history/investigations/run-1784584358-charter.md)
- Lock: [ACTIVE-RUN.lock](../history/investigations/ACTIVE-RUN.lock) — held for the duration of the run; released at Lane 13 close.
- Cross-reference index: [incident-history.md](../knowledge/incident-history.md)

If a lane finds a second ID that appears to name a different incident on the same
fake-user / app-abuse surface, treat it as an alias of the above and record the mapping
in `incident-history.md` — do not open a parallel investigation while the lock is held.

## Mode & Scope (inherited from charter — non-negotiable)

- **Mode:** Monitor-and-report-only. No containment, remediation, blocking, credential
  changes, account disable, or any state-changing action. Report findings only.
- **Scope:** Fake-user / app-abuse only — fabricated/synthetic accounts and application-level
  abuse. **Out of scope:** infrastructure, network, host, or VM actions; real-user data
  actions; anything outside the fake-user / app-abuse surface.
- Escalation to any active/response posture requires explicit owner approval outside this
  playbook.

## Abuse Indicators (I1–I9)

Hunt for these signals. Each finding must cite the indicator ID(s) it matches.

| ID | Indicator | What it looks like |
| --- | --- | --- |
| **I1** | Bulk / scripted registration | Many `POST /register` (or signup) events from one IP, ASN, or narrow IP block in a short window. |
| **I2** | Synthetic identity patterns | Sequential / templated usernames & emails (e.g. `user0001@`, disposable-domain emails, `+tag` enumeration on one mailbox). |
| **I3** | Registration/verification velocity | Account creation rate or email-verification rate far above the established per-hour baseline. |
| **I4** | Shared fingerprint reuse | Same User-Agent, device fingerprint, or TLS/JA3 across many "distinct" accounts. |
| **I5** | Credential-stuffing / brute auth | Repeated failed logins across many accounts from few sources; low success-to-attempt ratio in auth logs. |
| **I6** | Promo / quota / referral abuse | Many new accounts each consuming a signup bonus, free-tier quota, or referral credit, then going dormant. |
| **I7** | Disposable-session behavior | Account used once (single session, single high-value action) then never returns. |
| **I8** | Timing regularity | Machine-cadence inter-arrival times (fixed deltas, off-hours bursts) inconsistent with human use. |
| **I9** | Coordinated cluster | Accounts sharing 2+ of the above pivots (IP + fingerprint + email pattern) forming a linked ring. |

## Required Evidence (attach to every finding)

A finding is not actionable/reportable until it carries:

1. **Indicator IDs** matched (I1–I9).
2. **Account identifiers** — user IDs / usernames / emails (mask real-user PII per scope).
3. **Timestamps** — first-seen, last-seen, UTC, with the observation window.
4. **Source pivots** — source IP(s), ASN, User-Agent / fingerprint, referral code if any.
5. **Log excerpt(s)** — the raw lines supporting the claim, with file + line reference.
6. **Baseline delta** — observed rate vs. established baseline for velocity indicators.
7. **False-positive check result** — which FP criterion below was evaluated and its outcome.
8. **Confidence** — low / medium / high, with the reasoning.

## False-Positive Criteria (rule OUT before reporting)

A candidate is a false positive if ANY of these hold:

- **FP1 — Owner / operator activity.** Traffic originates from the owner or SOC operator
  themselves (test accounts, load tests, monitoring, QA signups).
- **FP2 — Shared NAT / CGNAT.** Many accounts behind one IP is a corporate/campus/mobile-carrier
  NAT gateway, not a botnet.
- **FP3 — Legitimate campaign burst.** A marketing launch or referral drive that explains a
  registration spike, corroborated with owner.
- **FP4 — Known integration.** Traffic is a sanctioned partner/API integration or health check.
- **FP5 — Baseline drift.** The "spike" is within normal seasonal/weekly variance once the
  baseline window is corrected.

### FP1 concrete method — separating the owner on a dynamic IP

The owner may connect from a **dynamic** residential IP, so IP alone cannot confirm/exclude
them. Separate owner activity from abuse using stable, non-IP pivots:

1. **Authenticated identity first.** If the session is authenticated as a known owner/operator
   account (from the owner allow-list maintained with this run), attribute to owner regardless
   of IP.
2. **Stable device pivots.** Correlate device fingerprint / User-Agent / JA3 and any persistent
   cookie or client token against the owner's known-good fingerprint set. A match on 2+ stable
   pivots attributes to owner even when the IP has rotated.
3. **ASN / ISP continuity.** A dynamic IP still resolves within the owner's home ISP ASN and
   geo. Owner-consistent ASN + owner fingerprint ⇒ owner; abuse rings typically span multiple
   hosting/VPN ASNs.
4. **Behavior signature.** Owner/test traffic hits admin/health/QA endpoints and follows human
   cadence; abuse matches I1–I9 machine patterns. Divergence here breaks ties.
5. **Confirm out-of-band.** If 1–4 are ambiguous, ask the owner to confirm the IP/session
   before classifying — do not guess. Record the confirmed IP against the owner allow-list so
   the next dynamic IP is faster to separate.

Record the FP evaluation outcome in the finding's Required-Evidence item #7.

## Read-Only Safe Commands

All commands below are **read-only observation**. Do NOT run anything that writes, blocks,
kills, disables, or mutates state. VM/host commands are executed by Odin, not by this lane —
do not touch the VM. Paths are illustrative; adapt to the confirmed deployment.

### Application logs
```
tail -n 500 /var/log/app/app.log
grep -iE 'register|signup|verify' /var/log/app/app.log
grep -iE 'referral|promo|bonus|credit' /var/log/app/app.log
```

### Nginx / web tier
```
grep -E 'POST /(register|signup|login)' /var/log/nginx/access.log
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head    # top source IPs
grep -F '"user-agent"' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head
```

### Auth
```
grep -iE 'failed|invalid|denied' /var/log/auth.log
grep -iE 'authentication (failure|success)' /var/log/app/auth.log
```

### systemd / service state (observe only)
```
systemctl status <app-service>        # status read only — no start/stop/restart
journalctl -u <app-service> --since '-6h' --no-pager
```

### Database (READ-ONLY queries only — no writes/DDL/DML mutations)
```
-- registrations per hour
SELECT date_trunc('hour', created_at) AS hr, count(*) FROM users GROUP BY 1 ORDER BY 1 DESC LIMIT 48;
-- accounts sharing a source IP
SELECT signup_ip, count(*) c FROM users GROUP BY signup_ip HAVING count(*) > 5 ORDER BY c DESC;
-- templated email patterns
SELECT split_part(email,'@',2) AS domain, count(*) c FROM users GROUP BY 1 ORDER BY c DESC LIMIT 25;
-- single-session / dormant accounts
SELECT id, created_at, last_login_at, login_count FROM users WHERE login_count <= 1 ORDER BY created_at DESC LIMIT 100;
```

> Never issue `UPDATE`, `DELETE`, `INSERT`, `ALTER`, `DROP`, account-disable, or session-kill
> statements. If a query would lock or heavily load the DB, skip it and report the limitation.

## Early-Stop Rules

Stop hunting and report immediately when any of these is true:

- **ES1 — Confirmed clean:** the candidate resolves to a false positive (FP1–FP5). Record and
  stop that thread.
- **ES2 — Owner attribution:** activity attributes to the owner/operator via the FP1 method.
- **ES3 — Sufficient evidence:** the ring is characterized with full Required Evidence — stop
  collecting and hand off; do not over-collect.
- **ES4 — Out of scope:** the thread leaves fake-user/app-abuse (into infra/network/host/
  real-user data) — stop and defer; do not follow it.
- **ES5 — Would require state change:** the only next step is a state-changing action — stop;
  escalate for owner approval, do not act.
- **ES6 — Lock/charter conflict:** any signal that the run lock is released or the charter mode
  changed — stop and re-read the charter before continuing.

## Recheck Cadence

- **Active window:** re-run the read-only sweeps every **30 minutes** while the incident is open
  and indicators are live.
- **Steady / low-signal:** back off to **every 2 hours** once no new I1–I9 hits appear across
  two consecutive sweeps.
- **Baseline refresh:** recompute velocity baselines (I3) at least **once per 24h** so drift
  (FP5) is not mistaken for abuse.
- **On new signal:** any fresh I9 cluster resets cadence to the 30-minute active window.
- Every sweep appends to the run investigation record; no silent gaps.

## Current UEBA Watch-List

Entities under active behavioral watch for this incident. Add/close entries as the hunt
progresses; each entry cites the indicator that put it on the list.

| Entity | Type | Reason (indicator) | Status |
| --- | --- | --- | --- |
| _synthetic-registration cluster_ | account ring | I1 + I2 + I9 | watching |
| _high-velocity signup source_ | source IP / ASN | I1 + I3 | watching |
| _shared-fingerprint cohort_ | device fingerprint | I4 | watching |
| _promo/referral drainers_ | account cohort | I6 + I7 | watching |
| _off-hours cadence burst_ | timing signature | I8 | watching |
| _owner dynamic-IP sessions_ | owner allow-list | FP1 (exclude, do not report) | monitoring-to-exclude |

> The owner allow-list row is a **suppression** entry: its purpose is to keep owner
> dynamic-IP activity from being reported as abuse. Keep it current as owner IPs rotate.

## Boundary — Incident-Only, No Broad Threat Hunting

**Hard boundary.** This directive authorizes hunting the **fake-user / app-abuse** activity of
**INC-2026-001 (run-1784584358)** and nothing else.

- **No broad or general threat hunting.** Do not scan for unrelated malware, lateral movement,
  network intrusions, or other incidents "while you're in there."
- Every action must trace to an I1–I9 indicator for this incident.
- Anything outside the fake-user / app-abuse surface → stop (ES4) and defer.
- One reference for all lanes: **SOC-APP-001 = INC-2026-001 = PB-APP-001**, hunted via
  **PB-HUNT-APP-001**. Do not fork the investigation.
