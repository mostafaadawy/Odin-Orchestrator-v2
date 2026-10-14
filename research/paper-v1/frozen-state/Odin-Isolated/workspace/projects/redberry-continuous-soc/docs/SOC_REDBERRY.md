# RedBerry Continuous SOC — Architecture, Operations & Rollback

A production‑grade, multi‑agent Security Operations Center built **inside** the Odin agent platform,
reusing its conventions (projects, agents, scheduler, scopes/chat pool, approvals, store persistence,
notifications). Operating principle: **Observe → Correlate → Verify → Report → Request approval → Act only
if approved.** Ships in **monitor‑and‑report‑only** mode; **autonomous remediation is disabled**.

## Agents (controlled hierarchy — one authoritative investigator)
- **CTO Orchestrator** — the only agent that presents decisions to the owner; initiates runs, prevents
  overlapping investigations, produces owner + technical reports, raises approval requests. Never approves
  its own action.
- **Security Intelligence & Threat‑Hunting Architect** — owns the knowledge base, playbooks, detection
  rules; never touches production.
- **Security Operations Investigator** — the single primary read‑only investigator.
- **Reporting & Documentation Agent** — reusable asset (`report_engine`); styles/exports the report as
  MD/DOCX/PDF/PPTX with brand (logo + info). Usable by any project.

## Files (source)
- `server/soc_run.py` — the run engine (checks, classification, false‑positive analysis, early‑stop,
  memorizing findings registry, owner+technical reports, approval requests, persistence).
- `server/report_engine.py` — reusable branded reporting (md/docx/pdf/pptx).
- `server/soc_api.py` — `/soc/status`, `/soc/settings` (GET/POST), `/soc/run`, `/soc/report?fmt=`, `/soc/finding`.
- `server/scheduler.py` — added **timezone‑aware daily** (America/New_York) + **catch‑up** for missed runs.
- Knowledge base: `data/projects/redberry-continuous-soc/soc/{knowledge,playbooks,detections,history,schedules}` (43 files).
- Settings: `data/soc_settings.json`; findings registry: `data/projects/<pid>/soc_findings_registry.json`.

## Data model (persistent — not transient chat memory)
Run record, per‑check finding (id, severity, confidence, classification, evidence, false‑positive
analysis, data‑source state, blast radius, remediation + risk), **findings registry** (memorizing:
first_seen, last_seen, occurrences, owner_status = open|pending|accepted|resolved, notes), baseline,
approvals, reports index, last‑run summary.

## Memorizing report (owner lifecycle)
Every run reconciles detected issues with the registry and emits: **🆕 New this run · 🔓 Still open ·
⏸️ Pending/left‑for‑now · 🤝 Accepted risk · ✅ Resolved.** Owner actions via `POST /soc/finding`
(`resolved|pending|accepted|open`) persist and are remembered across runs. Reports post to the **same
project chat pool** as everything else (consistency).

## Scheduling & the desktop caveat
Primary daily run **11:00 PM America/New_York** (DST‑aware). The scheduler runs inside the brain (desktop/
DMG). If the desktop is off at 11 PM, the run would be missed — so the task is flagged **`catchup: true`**:
on the next launch the missed daily run fires once. For true 24/7 coverage keep the desktop running (a
future enhancement could add a VM‑resident agent).

## Safety / authorization (mandatory)
Default: read‑only, non‑disruptive. A read‑only guard in `_ssh_ro` refuses any mutating command. Any
production‑affecting action becomes an **approval request** (exact action, target, evidence, impact,
downtime, rollback, alternatives). In monitor/test mode approvals are **auto‑DENIED and never executed**.
`SOC_AUTO_REMEDIATION_ENABLED = false` (mandatory). Secrets/2FA/tokens are never printed.

## Runtime settings (`/soc/settings`, DB‑backed, live)
22 `SOC_*` settings incl. schedule, timezone, monitor‑only, per‑domain monitoring toggles, retention, and
the mandatory `SOC_AUTO_REMEDIATION_ENABLED=false`.

## Deployment
1. Backend files live in the repo the DMG runs (`/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Isolated`).
2. `pip install reportlab python-pptx python-docx` in `.venv` (done) for exports.
3. Brain auto‑loads `soc_api` (included in `app.py`); scheduler picks up the SOC task.
4. Web/desktop pick up new agents automatically via the org roster (`/agents/all` mirror). Run `npm run
   dist` to bundle desktop UI; the DMG runs the brain from the repo so all SOC endpoints are available.

## Rollback
- Disable: set `SOC_ENABLED=false` (or `SOC_SCHEDULE_ENABLED=false`) via `POST /soc/settings` — no redeploy.
- Remove: delete the scheduler task (`scheduler.delete_task`), archive/delete the `redberry-continuous-soc`
  project. Knowledge base + reports are plain files under `data/projects/redberry-continuous-soc/soc/`.
- Nothing on the VM is changed by the SOC, so there is no VM rollback.

## Security & privacy review
Read‑only by construction; approval‑gated; no autonomous remediation; secrets/2FA/tokens redacted; raw‑IP
retention setting; reports are project‑scoped. The RedBerry incident is preserved as **app‑level abuse —
NOT VM compromise** (no malware/persistence/exfil claimed without evidence).
