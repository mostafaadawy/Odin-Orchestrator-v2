# Snapshot: snap-0004-dispatcher-mobile

**Created (UTC):** 2026-06-21T14:00:00Z
**By:** CTO Brain
**Reason:** Restore point after building the dispatcher and mobile access — all three backbone
pending items now built and wired.

## What changed since snap-0003
- Added `orchestrator/dispatcher.py` — deterministic Brain↔agent router (classify, load-rules,
  approval-check, lifecycle hooks, `respond()` adapter). Routing telemetry → `history/routing.jsonl`.
- `server/app.py` — added `/dispatch`; `/chat` (and voice) now answer through the dispatcher;
  added optional `ODIN_ACCESS_TOKEN` middleware gating `/chat`,`/dispatch`,`/voice/*`.
- Added `dashboard/mobile.html` (phone voice+chat) and a footer link from the dashboard.
- Added `runbooks/mobile-access.md`.
- `rules/core-rules.md` ADR-008; `orchestrator/ORCHESTRATOR.md` dispatcher note; `PENDING.md`
  all backbone items marked done + next-items list; history + state updated.

## Verified
Routing unit tests 6/6; live `/chat` 401 without token & 200 with token; gated requests
return an approval message and are NOT executed; `/dispatch` returns routing JSON with hooks;
`/mobile.html` served; graceful fallback without Ollama.

## To revert here
Follow `runbooks/revert.md` (a pre-revert snapshot is taken first, so this is reversible).
