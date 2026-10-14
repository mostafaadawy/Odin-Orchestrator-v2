# ROADMAP — Modularization Program (gated phases, one at a time)

> RULE: phases run **one at a time**. Phase X+1 is only started after the owner confirms Phase X is done.
> The scheduler holds the phase queue; nothing auto-advances without owner confirmation.
> Aggressive by design (archive backup exists) — but must never break modularity or the schema.

## Phase 0 — Structure & Type System  ✅ DONE
Canonical workspace schema enforced: every project = the 16-entry skeleton, every agent = the 8-entry skeleton,
connectors/features/project-types defined, each owner carries `type` + `typeConfig` pointing to its shared
definition. Verified: 0 gaps, no stray root folders, app healthy.

## Phase 1 — `odin_core` database schema (Postgres)
**Goal:** a relational schema that mirrors the fixed structure — **one table per SUBFOLDER type** (projects,
agents, connectors, chats, instructions, restrictions, plan, code, dependencies, data, docs, files, deploy,
schedule, features, tests, outputs, capability, handoff, shared/*), plus a `files` table (metadata only).
**Relations (FK):** project→its subfolders→their files; project→agents (M:N); agent→dependencies→shared
capability; file→owner; dependency→shared source. So from a project you reach its children, its agents, and
any shared capability a dependency points to.
**Columns:** id, owner ref, path (reference to real location), kind (json/md/code/shell/py), short description,
created/modified date, size, type/category. **No file CONTENT stored** — metadata + short description + path only.
**Done when:** schema created in `odin_core`, FKs enforce the relations, and a test query walks project→agents→shared.

## Phase 2 — Seed `odin_core` from the current files
**Goal:** populate the schema from the existing (already-conformed) workspace. Every file gets a row with a
**short, agentic-friendly description** ("uses shared deploy 1,2,3 + custom X" style) so a rig can find the
bundle it needs by search/similarity.
**Done when:** every current file/subfolder is indexed with description + path + dates; spot-check queries return
correct bundles (e.g. "deployment files" → shared engine + organics custom overlay).

## Phase 3 — Middleware (single creation door)
**Goal:** every create/update/delete of workspace content passes through ONE middleware that (a) places the file
in the correct schema slot, (b) writes/updates its `odin_core` row, (c) detects+blocks violations at write time.
**Done when:** creating anything via the app routes it through middleware; DB + folder stay in lockstep; a
deliberately-misplaced create is corrected/blocked.

## Phase 4 — Directions (schema-backed knowledge layer)
**Goal:** the entrypoint read FIRST by the CTO brain, agents, and every chat. It reads `odin_core` (not each
project) to answer: where does X live, what capabilities exist, similar prior work, resources/keys, connectors,
statuses, history. Keeps the context pool consistent — every chat starts here, so it always knows what the system
already has and never duplicates.

**ALWAYS-CURRENT (no manual update):** Directions is a LIVE VIEW over `odin_core`. Because the Phase-3 middleware
keeps the DB in lockstep on every create/update/delete, directions reflects every new script/file the moment it is
written — full vision, always synchronized, nothing to "refresh."

**CAPABILITY-REUSE ADVISORY (the anti-duplication core — a MUST, not optional):** before anything new is created
(a new script, a new project, a new agent capability), the creator asks directions:
  1. "Does a capability for <need> already exist?" → directions returns the SHARED capability (path) AND every
     project/agent that already uses or customized it, from `dependencies` + `shared_capabilities`.
  2. "Does it match my requirement?" → directions surfaces the distinguishing facts (e.g. deployment: is it the
     sandbox flow or the production flow? which folders/commands? which shared protocol — the az dynamic-IP +
     SSH steps — is reusable as-is?).
  3. The RULE it enforces: **do NOT create a parallel `deploy_2` / `deploy_othername` / duplicate function.** Reuse
     the shared capability; if you need a difference, reuse the shared part UP TO A POINT and add ONLY the custom
     delta (different target folder / extra command) as an overlay in your own `code/`, recorded in your
     `dependencies/manifest.json` (`mode: extend|subset|override`). This is the same base+overlay model the schema
     already carries — directions just makes the existing capability discoverable so it is actually reused.

This closes the recurring failure of re-implementing the same function under a new name (deploy/mobile-post/etc.)
by making "what we already have" answerable before "what to create."
**Done when:** a fresh chat/agent asks "I need to deploy X" → directions returns the existing shared deploy engine,
who already customized it and how, and the reuse recipe (shared + your custom delta) — so no duplicate is created;
updates made mid-session by another actor are visible on the next query (live, via the DB).

## Phase 5 — Audit / Observer (debounced self-healing)
**Goal:** watches for NEW interesting files (json/md/code/shell/py) inside `workspace/` AND the root — **excluding
the core-app folders** (server, orchestrator, voice, desktop, odin_app, dashboard) and existing core files.
**Trigger model:** debounced — a **silence gap** (configurable, e.g. 30–60 min); sets a flag, acts only after the
gap so it doesn't respond to every file. Owner can enable/disable and set the interval.
**On check, per file:** correct place? in the DB? duplicating a shared capability instead of using it?
**On violation, it:** (1) finds the root cause, (2) fixes the SOURCE — edits the **application code** that generated
it and sets a rule so it can't recur (it does NOT self-heal in a way that hides the bug; remove the audit and the
underlying fix remains), (3) if a functionality now exists in ≥2 projects → moves it to `shared/` and repoints
both to use it (with a 100%-match custom-delta where a project needs ~10% different).
**UI:** its own **page/tab** (not a top button) with: run-now, view all violations + how each was solved, why-a-problem
detail, enable/disable, interval control.
**Done when:** run 1 catches ~all, run 2 fewer, converging to zero; each run leaves the system more correct.

## Phase 6 — UI adaptation (desktop / web / mobile / anchor)
**Goal:** make the clients configurable + data-driven. Project lists = `array.map` from `odin_core` (8 or 20,000,
just scroll). Per-card controls derive from `type`: `recurring/periodical` → play/run button; `vertical` → timeout
control; features → icons (voice-streaming icon when `features:["voice"]`). No hardcoded assumptions.
**Anchor:** sync the DB efficiently across web/mobile; fetch on demand, push only notifications — one source, responsive.
**Done when:** a project's card shows exactly the controls its type dictates; adding a feature shows its icon; no
hardcoded project/agent lists remain.

## Phase 7 — Non-production testing
**Goal:** integrate each project's `tests/` into ONE test per project that (a) confirms the project still works —
**with good performance** — using the SHARED capability (not its old bundled custom), (b) validates the new
architecture end-to-end. Then: create 2–3 NEW projects (modeled on existing ones) via the new methodology, and
delete them — confirming clean creation (middleware places correctly, DB seeded) and clean deletion (removes its
own, KEEPS shared it promoted). Confirm: audit → 0 violations, middleware correct, chat knows everything, dedup→shared
+ custom-delta works, structure not violated inside or outside the workspace.
**EXCLUDE:** the real production deploy project (organics / bendcore front+back) — **do not touch its tests at all**;
that's a later phase.
**Done when:** all non-prod project tests pass, create+delete cycle is clean, audit reaches zero violations.

## Phase 8 — Environment + production shell tests (later)
Adapt `shells/phase2_up.sh` (environment) and `shells/phase3_up.sh` (production) to the new architecture and run the
environment + production validation. Only after Phases 1–7 are green.
