# ODIN — Structuring → Registry → Middleware → Leverage (Phased Plan with Passing Points)

**Rule for every phase:** it is "DONE" only when its **Passing Point** is 100% green. If red → revert (the
archive + additive design make it clean), fix, retry. No phase starts before the previous one passed.

**Standing guardrails (all phases):** archive kept as rollback · additive & reversible · external deploy
targets (organics, etc.) NEVER enter the workspace — only referenced · shared chat pool untouched · desktop /
web / mobile cards must always match · nothing deleted until its replacement is proven.

---

## Phase 0 — Baseline (safety net, zero changes)
Capture the golden snapshot of TODAY: each project's `status`/`run` output, every endpoint, and the exact card
JSON desktop/web/mobile render. Build the harness that replays it.
- **Passing Point:** baseline snapshot captured + reproducible; nothing changed yet.

## Phase 1 — Structure the CURRENT projects (files into their places)
Move the existing projects/agents/chats/connectors/shared/app into the target folders and **fix their paths**:
```
workspace/  app/  projects/<id>/(directions.md, files/)  agents/<id>/files/  chats/<id>/
            connectors/<id>/  shared/(utils, scripts, directions/)  external-refs/(pointers only)
```
Deployment‑type projects: their OWN files (scripts, configs, cheat‑sheets, DEPLOY‑PROMPT) go inside the
project folder; the deployed target folders stay outside, referenced. Then **run everything**.
- **Passing Point:** the app runs; **every current project still works** — reads all the files it must use,
  keeps its properties, stays smart & consistent; behavior identical to the Phase‑0 baseline; zero regressions.

## Phase 2 — STRONG E2E of the structuring (not a token test)
A real test that the structuring didn't harm anything: **open each project, rerun its tasks**, and we **monitor
together via the bridge**. If a problem appears → decide *is it caused by the structuring?* → if yes,
**consolidate the structure** to remove that class of problem.
- **Passing Point:** every project opens and **reruns its tasks correctly**, matching baseline; any issue is
  proven NOT structuring‑caused (or fixed by consolidating the structure). 100% green.

## Phase 3 — The database (`odin_core`) + seed from the STRUCTURED state
Create the registry matching the structure (places for directions, projects, chats, agents, connectors,
assets). **Seed it from the current projects AFTER structuring** — a reference for every file created for each
project and its agents (post‑structure, never pre‑structure). Index only (refs + short_desc + relations), no
content.
- **Passing Point:** the registry holds a correct ref for **every** on‑disk file/entity; a query returns each
  project + its agents + its files matching disk **1:1**; seed test green.

## Phase 4 — The tight middleware (the single door)
No write/create of any project/agent/chat/connector is allowed unless it BOTH (a) creates the files in the
required place AND (b) writes/updates the reference in the DB. Same for edit and delete (delete folder →
then ref). Whoever/whatever asks, it must pass this door.
- **Passing Point:** all create/update/delete flows route through the middleware; create ⇒ folder+ref, edit ⇒
  both, delete ⇒ folder then ref — enforced, with a write‑guard that rejects any workspace write lacking a ref.

## Phase 5 — Test the middleware HARD (solidify until airtight)
Create, delete, and recreate projects; confirm the middleware **restricts** correctly and works on
update/delete/create. Make the E2E strong enough that **if anything is written outside the structure it is
caught** — then tighten until nothing can escape.
- **Passing Point:** E2E proves **nothing** enters the workspace without a ref; create/update/delete keep
  folder + DB in lockstep; zero orphans/strays; **100% "everything created in its place."**

## Phase 6 — Leverage: directions + CTO short‑path (anti‑hallucination)
Read the schema through **directions** (extract them, wire the short path). The schema is visible to BOTH the
CTO thread and the chief thread, so before creating an agent the CTO **sees what already exists** and reuses
the most appropriate one instead of duplicating it. Stress it: create many projects, test, delete, recreate
via the structure; **compare speed + consistency**.
- **Passing Point:** CTO plans from the schema, **reuses existing agents (no duplicate creation)**; new‑project
  creation is measurably **faster and consistent**; directions correctly force required docs (e.g. deployment).

## Phase 7 — Fast / lazy loading + sync + notifications
Cards load from the registry **short messages** (fast/lazy); opening one entity retrieves its **full** content
from its place. A local DB update → **notification + anchor/web/mobile sync** using short payloads only;
approvals notify instantly (short ref pushed, full content retrieved on press). **Measure** the performance
gain. Then: keep the current projects if good, or recreate them cleanly under the new topology.
- **Passing Point:** cards load fast + identical on desktop/web/mobile; updates notify quickly via short
  payloads; full data lazy‑loads on demand; measured performance improvement; type‑features (recurring ⇒ Run
  button, zoom ⇒ voice/timing) come from directions, not hand‑coded.

---

## Why this kills the failures you keep hitting
- Agents/projects can no longer land in the wrong place or get missed → the **middleware door** forbids it.
- The CTO stops **duplicating agents it already has** → it reads one **schema** it can see.
- Rule/protocol breaks (like the `az` incident) → **directions are read and enforced first**, not ignored.
- The current working system is protected the whole way → **baseline + E2E gate + additive/reversible phases**.
