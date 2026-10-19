# MASTER_FEATURE_INVENTORY: Odin-Orchestrator v1

**Phase 1, final. Updated 2026-10-11.**

**How the inventory was built:**
1. **Docs and history** (Parts A–D, 575 rows), read in full.
2. **Every source file**, read in full (Parts K1–K5B, about 1,380 rows, each with file:line). This covers:
   - 81 server modules, the orchestrator and voice;
   - all of `workspace/shared` scripts and project code;
   - all shells;
   - the Electron/React desktop, the 31 Flutter files and the dashboard;
   - the Anchor pages;
   - the odin_core and odin_anchor schemas (read-only `pg_dump -s`).
3. **All 357 chat files** (4,049 messages), read in full as the final gap check (Parts CH0–CH5, 114 added rows, plus contradictions).

**Not in the source snapshot:** credentials, compiled bundles, logs and binary data were left out on purpose. The chats were read separately in step 3. `desktop/build/afterpack-sign.cjs` was read directly; see §0.6.

**Rule for every later phase:** every row is required in v2. **A past run (VERIFIED-RUN with a date) counts for the inventory only; every feature must still be re-proven in v2 in Phase 7 (owner, 2026-10-11).** **A feature counts as preserved only when a run proves the same behaviour in v1 and v2.** Anything added, changed, stopped or removed must be flagged to the owner, never passed silently. Jev, if adopted, goes into this same v2.

## §0.8 Inventory corrections (owner-approved 2026-10-11; old wording kept, nothing removed)

**Rule:** a past run counts for the inventory only; every feature must still be re-proven in v2 in Phase 7.

| C | Row | Correction (old wording above is kept) | Evidence |
|---|---|---|---|
| C-1 | MFI l.904, persistent chat memory | PENDING → VERIFIED-RUN (2026-06-22, chat) | chat 2e6a41cd6e97 @1782161107 ("FALCON-77") |
| C-2 | A-063 Six specialist agents | Row KEPT. **Superseded by the owner on 2026-07-08:** the front/back split is the old version; Fullstack is one merged role (K1-101). The `agents/*.agent.md` files are stale but kept. The semantic router's 7 specialist names still differ from the role catalogue (recorded, unchanged). | company/d7a7b2bad54e @1783547762 |
| C-3 | Veeqo carrier-tracking fallback | "not built" → **built and observed: Veeqo → EasyPost fallback**; the tracking-source decision stays open | chats c8038d310db7 1785414074, 55f61b99d233 1785415484; `getEasyPostConfig` in the organics code |
| C-4 | `CFG_BACKEND_MIG` | "reset" → **"new"** (one-time reset reverted by an approved proposal) | v1 `workspace/shared/infra/deploy.config.sh` l.12 reads `"new"`; chat d0127007bda4 / f7928b560cf6 |
| C-5 | P-01 daily-egypt-amazon-product-poster | Note: a working pipeline exists in the owner's Odin Testing/testing folder; a local launchd fires at **08:50**, while the project schedule says 09:00. **What triggers the 08:50 run → tracker F-34.** | CH2-016 |
| C-6 | K5A-038 SOC explainer | Note: the explainer post shows 8 lanes; the CTO plan in the chats runs 13 lanes | CH2-019 |
| C-7 | K2A-185 background-run message | "dead code" → **UNDETERMINED**: the message appears in chats dated 2026-07-25; settle by a run in Phase 6 | RDD chats 2026-07-25 |
| C-8 | P-08 SOC team size | Note: 8 agents in the SOC chats (CTO + 7 lanes; `soc_blueprint.SECURITY_TEAM` = 8); the live roster has 12; the 13 names in P-08 include aliases | CH3 chats; `agents.json` |
| C-9 | P-10 vm-sentinel | Note: project schedule is `{}`, yet daily runs at about 08:00 on 2026-07-19, 07-24, 07-25. **What triggers them → tracker F-35.** | CH5 chats |
| C-10 | T-17 Revealer (note only) | Row KEPT as written: it correctly describes the test script `testing/sandbox_revealer_multiagent.py`, which asks for a NestJS backend + Next.js frontend. **Note:** the Revealer actually delivered (owner decision, CH5-002) is a backend-only Python FastAPI service on the sandbox VM, with no frontend. **Phase 7 proves BOTH** (owner, 2026-10-11): the test script as written, and the delivered FastAPI service. | CH5-002; the test script l.10 |
| C-11 | A-229 SOC checks catalogue | Note: the owner moved the fake-user problem to the Klaviyo side (CH4-002); no vendor-side fake-contact check exists (SOC-EXT-006 tracks quota only). A new check would be a new feature → owner decision. | CH4-002 |

## §0.4 Feature categories (complete, from the files; the named examples are only instances)

| Category | Where its full list is | Approx. rows |
|---|---|---|
| Structural (folder skeletons, workspace schema, shared/delta placement) | K1 §1, §3(a); B, A | ≈60 |
| Orchestration core (intake, team, CTO/agents, create/route/reuse/delta/shared, runs, QA/CTO review, retries, approvals) | K2A, K2B, C | ≈330 |
| Audit and consistency | K1 §3(d), K2A (truth gate, audit eye, artifact/build gates), K5A/K5B | ≈110 |
| Middleware and database registry | K1 §3(b), (c), (e) | ≈95 |
| Synchronization and Anchor (live sync, sequence/delta, mirror, queue, poller, callbacks, commands) | K3, K4A, K4B | ≈180 |
| Per-project features and integrations (SOC, Zoom/meeting, reporter/export, HubSpot, Klaviyo, Veeqo, EasyPost, sentinel, the ops platform, Egypt-Amazon poster, Revealer) | K5A, K5B, K2B, K3, CH | ≈250 |
| Build, packaging, run and clients (desktop dev/build/DMG and signing, Flutter web/iOS, Anchor, dashboard, env and phase scripts) | D, K4A, K4B, K5B | ≈210 |
| Safety and approvals | K2A, K1, K5A, K5B | ≈180 |
| Voice (STT/TTS EN/AR, speech normaliser) | K3, K4A | ≈80 |
| Auth and security (login, 2FA, Manage, tokens, hooks) | K3, K4A, K4B | ≈100 |
| Scheduling and notifications | K2B, K3, K4A | ≈75 |
| Testing (e2e, phase gates, harnesses, regression) | K5A, K5B, D | ≈120 |

## §0.5 Explicit confirmations you asked for (by file and line)

| Item | Result | Where (v1) |
|---|---|---|
| Folder-structuring rules | **FOUND** | `workspace_mw.py`: subfolder and root-file sets l.19–28, `validate` l.55, `route` l.103, owner-scope redirect l.153, skeletons l.625–628, `create_owner` l.661, promotion l.371/434. `store.py` l.70–150 (shards). `WORKSPACE-SCHEMA.md` §1–6. **Note: the doc and the code disagree** (the on-disk project has 14 subfolders, not the 9 in the doc; K1 §3(a)). |
| Database schema | **FOUND** | odin_core has 13 tables plus 16 views; odin_anchor has `anchor_requests`. Every column, key and FK, with writer and reader functions per table: K1 §3(b). No secondary indexes in odin_core; `files.path` has no UNIQUE constraint. |
| Middleware | **FOUND** | Every `workspace_mw` function (K1-005…043). Prompt guards: `scope_answer_guard` :770, `read_execute_guard` :804, `agent_scope_guard` :890, `vm_diagnosis_guard` :966, `tutorial_guard` :1001. Also `cached_modules` DECIDE rule :62–72 and `readonly_hook` :65–76. |
| Audit layer and all consistency rules | **FOUND** | `workspace_audit.scan` l.104: misplaced, unindexed, db-orphan, parallel-registry, agent-incomplete/invisible/unregistered, root-stray, duplicate (identical and different), foreign-ref, external-write. `heal` l.350, `sentinel` l.314. Truth gate and audit eye in `api_v2.py` :2316/:2777/:2782/:2818. "Announce-only turn = FAILURE" :1396/:1745. Scope-answer rules (`scope_guide_test`, `scope_reasoning_test`). |
| Stuck replies | **FOUND** | `claude_cli.py` :217/:296 (`ODIN_CLAUDE_IDLE` 420 s), heartbeat :218, no-progress guard `ODIN_CLAUDE_MAXWALL` 900 s :278. Desktop stuck banner after more than 5 min (K4B). |
| Generic-reply detector | **NOT FOUND** in any file | Related rules that do exist: scope rules (false refusal, unnecessary clarification, leakage), fake success, announce-only turn. |
| Wrong-format replies | **PARTIAL** | Robust PASS/FAIL verdict parsing, JSON extractors, proposal parser (K2A, K2B). No general wrong-format rule. |
| Synchronization features | **FOUND** | Desktop brain → `local_poller_http.sync_push` → Anchor `POST /anchor/v1/sync` (`local_poller_http.py:276`; `anchor_remote.py:504`). Per-scope sequence numbers (`scopes.py:117`). Delta pull `/pool/{pid}?since=` with `max_seq` (`anchor_remote.py:400–410`). Durable mirror. 10 Anchor command kinds. Delta self-heal in the mobile app (K4A). |
| Live web/mobile/desktop sync | **FOUND, with gaps** | Mobile/web: 12 s fingerprint loop and a delta cursor (K4A). Desktop: 3 s pool poll with count-only change detection; **it never sends `since`** (K4B). |
| **UDP connections** | **NOT FOUND anywhere in v1** (code, shells, clients, project code, chats) | The transports actually used are HTTP/HTTPS (FastAPI/uvicorn, `http.server`), urllib clients, short polling (5 s / 3 s / 2.5 s / 12 s), and server-sent events (`app.py:259/373`). No WebSocket and no raw socket. |
| Clone projects | **PARTIAL** | Found: the **WhatsApp-clone mode** in the Flutter app (`odin_app/lib/screens/whatsapp.dart`, `shell.dart:45`) and WhatsApp-style mirror semantics on the server. **No "project clone" function exists** in any file. |

## §0.6 Additions and corrections from this pass

- **Desktop signing:** `desktop/build/afterpack-sign.cjs` l.1–10 performs ad-hoc `codesign --force --deep --sign -` plus verify after packing, and clears quarantine with `xattr -cr`. This is required for the DMG.
- **Security:**
  - The Anchor API key **and the Anchor Manage password and email are hard-coded in `desktop/src/App.jsx` l.351–353**, so they ship inside the DMG.
  - The Anchor key is also in `anchor_prod.js` and `anchor_seed.js`, and in the Flutter client source.
  - Values were not copied anywhere.
- **Dry run (`workspace/shared/infra/deploy.sh`) against your rule:**
  - NSG single-IP update l.163–181: **complies** (updated in place, never stacked).
  - ufw rotation l.183–209: **not dry-run-guarded**. It adds `deny 22/tcp`, re-adds 80/443 and reloads, so it **violates** your rule.
  - sshd enable/restart self-heal l.223–246: **violates**.
  - rsync uses `-n` and build/migrate/extra steps are skipped: **complies**.
  - Baseline re-dated by `deploy_changes.py update` l.376–394: **violates** (it also runs before verify and on partial runs).
- **Chats raised 42 contradictions** (CH0–CH5 §3). Examples: runs reporting "All requirements addressed ✅" while reviews say "Needs fix" (the same issue as G1); SOC auto-resolving findings it never checked; scope or read-execute guards failing in some turns; a launchd job reinstalled after you asked for its removal; the Zoom "live capture" narration contradicting the code; `~/Bendcore` vs `~/bendcore`. Each item is listed with its source.
- **Correction to K1 §3(a):** `workspace/chats` and `workspace/logs` **do exist** in v1. They were left out of the snapshot on purpose and the chats were read separately.


## §0.7 Two full categories added after your Phase 1 answer ("examples are only instances")

**Communication and connection mechanisms (part CAT_COMMS).**
- 114 mechanisms, each with every file:line.
- A 17-link component connection map.
- 13 transports confirmed absent, with the grep evidence. **No UDP and no WebSocket**; everything is HTTP(S), polling, server-sent events, subprocess pipes, Electron IPC, file bridges, database connections, queues and webhooks, CLI calls and third-party APIs.
- 8 new findings:
  - N1: the brain token gate covers only `/chat*`, `/dispatch` and `/voice*`.
  - N2: `/activity/stream` has no consumer.
  - N3: the desktop Anchor view shows the local queue, not the VM Anchor.
  - N4: the Egypt pipeline scrapes amazon.eg and has a Meta publisher.
  - N5: a JSON queue file may be shared by two processes.
  - N6: `phase_ctl send` registers a localhost callback the VM cannot reach.
  - N7: the desktop hard-codes the production Anchor URL for the pending-code poll.
  - N8: IP enrichment sends client IPs to ip-api.com over plain HTTP.

**App modes, clones and UI variants (part CAT_MODES).**
- 110 modes across desktop, web, mobile, the Anchor and server-driven modes.
- 13 fully new, 9 partly new, and 8 that were only in the K parts.
- Confirmed absent: light theme, push-to-talk, kiosk, tablet layout, multi-role views.

---

**Date:** 2026-10-11.

**What this is:** the checklist every later phase must keep passing. **Everything listed is required unless the owner approves removing it.**

**Sources:**
- **The original v1,** read in full through 8 bundles (`odin-v2-staging/_phase1_bundles/B1–B7`). Together they cover 192 docs, the history and decision log, every agent and project file, the build, run and release scripts, the code and route inventory, and the paper work in Odin-Isolated.
- **The Phase 2 run evidence** in `odin_scenario_verification.md`.

**Status legend:**
- **VERIFIED-RUN (Phase 2):** proven by a run in this program.
- **VERIFIED-RUN (date):** a run recorded in your own history or docs.
- **BUILT / DESCRIBED / PLANNED:** found in the code or docs, but not yet run in this program.
- **PARTIAL:** proven by a run, with a known gap; see the G-items in `REQUIREMENTS_TRACKER.md`.
- **UNDETERMINED:** suspected from reading only. A run is needed before it can be called broken.

**How to read it:**
- §0 is the overlay from this program: Phase 2 run statuses, hidden features confirmed in the code, and corrections to the sub-inventories.
- Parts A–D (about 575 rows) follow it. Their IDs (A-…, B-…, C-…, D-…) are the IDs used in every later phase.

---

## §0.1 Status overlay from the Phase 2 runs (18 runs on Odin-Consolidated)

| Feature (IDs in parts A–D) | Phase 2 status | Evidence |
|---|---|---|
| Main chat: create a project / ask about the system | VERIFIED-RUN (Phase 2) | S1–S5, 15 runs |
| Intake interview: platform, team, features, readiness, recommendations | VERIFIED-RUN (Phase 2) | 12/12 |
| Negation-aware team ("no QA", "deploy when finished" → DevOps) | VERIFIED-RUN (Phase 2) | S4 3/3 |
| Recommended new members are never auto-staffed | VERIFIED-RUN (Phase 2) | 12/12 |
| Company agents auto-added to every project (EasyPost) | PARTIAL → G12 (owner decision: recommend per project) | 12/12 |
| Agent reuse; no duplicate agent rows; Fullstack owns the whole web app | VERIFIED-RUN (Phase 2) | 12/12, database checked |
| Agent strengthening (add a skill without deleting) | PARTIAL → G13 | 0/3 |
| The reuse path overwrites a shared agent's role and title | PARTIAL → G10 | S1, S4 |
| Build step routed to DevOps instead of Fullstack | PARTIAL → G11 | S4 3/3 |
| Meaning-based reuse of a shared script and a system-generated delta | VERIFIED-RUN (Phase 2) | S2 3/3 |
| Delta saved to disk and registered in the manifest and database | PARTIAL → G3, G4 | 1/3 on disk, 0/3 registered |
| Middleware door: owner-scope redirect, placement redirect | VERIFIED-RUN (Phase 2) | S6 3/3 |
| Audit: unindexed, misplaced, identical duplicate, foreign reference | VERIFIED-RUN (Phase 2) | S6 |
| Audit: duplicate plus foreign reference leaves a dangling reference | PARTIAL → G6 | 2/2 |
| Audit: per-project delta flagged as a "duplicate" | PARTIAL → G5 | S2 |
| Audit: `tests/` copies not scanned | PARTIAL → G7 | S6 r1 |
| Audit: creator tracing / automatic rule update | PARTIAL → G8 (tracing); automatic rule update UNDETERMINED | 0/3 |
| Truth gate: CTO "Needs fix" review does not block success | PARTIAL → G1 | 10/12 |
| `_touches_vm` treats "do not deploy" as VM work | PARTIAL → G2 | 6/6 |
| Per-project credential: never falls back to the default key | VERIFIED-RUN (Phase 2) | S3 3/3 |
| Per-project credential recorded in `agent_scope` or a delta | PARTIAL → G9 | 0/3 |
| Approval gate for file changes and VM work | VERIFIED-RUN (Phase 2) | S2 r2, S4 |
| Refusing to fabricate (keys, VM health) | VERIFIED-RUN (Phase 2) | 6/6 |
| Main-chat lookup of existing capability through the database or directions | PARTIAL (not observed) | S5 0/3 |
| Regression suite (paper copy) | VERIFIED-RUN (Phase 2) | 31/32 before and after; the single failure is the same as the baseline |

Not yet run in this program (Phase 7 must run them): Anchor queue, live sync, scheduler, SOC runs, voice, desktop dev, desktop build and DMG, Flutter web and mobile, the local React desktop client, third-party simulator round-trips, the certified deployment, and notifications.

## §0.2 Hidden features confirmed in the code (not all are in the docs)

| Feature | Where | Status |
|---|---|---|
| **Stuck-reply detection:** an engine call with no output for `ODIN_CLAUDE_IDLE` (420 s) is terminated and reported | `server/claude_cli.py` l.210–300 | BUILT |
| **Scope behaviour and reasoning tests:** semantic tests of the guards; misses are logged as `scope-answer` (55 recorded) | `server/scope_guide_test.py`, `server/scope_reasoning_test.py` | VERIFIED-RUN (2026-07-20, audit log) |
| **Fake-success and hidden-fault gate:** `claims_success`, `gate_success`, `scan_hidden_faults`, `correction_prompt`, `engine_audit` | `server/audit.py`; used at `api_v2.py:2682`, `:2776` | BUILT; the step-level gap is G1 |
| **Middleware prompt guards:** `scope_answer_guard`, `read_execute_guard`, `agent_scope_guard`, `vm_diagnosis_guard`, `tutorial_guard`, `write_external_report` (single-file rule) | `server/workspace_mw.py` l.770–1007 | BUILT; `agent_scope_guard` VERIFIED-RUN (Phase 2, S3) |
| **Per-project credential table:** `agent_scope` (live rows for real-deployment-and-diagnosis: Fulfillment/veeqo, Email/klaviyo, HubSpot/hubspot) | `workspace_mw.py` l.831–888; odin_core | VERIFIED (database dump) |
| **`_ensure_member`:** never invents an agent and never resurrects a removed one | `api_v2.py` ~l.2088 | VERIFIED-RUN (Phase 2) |
| **`_suggest_rule`:** no agent starts without rules | `projects.py` l.373 | BUILT |
| **`PROTECTED_PROJECTS`:** production is never auto-touched by the audit | `workspace_audit.py` l.33 | BUILT |
| **P2 scope hook and door CLI** (paper copy only) | `Odin-Isolated/server/scope_hook.py`, `door_cli.py` | VERIFIED-RUN (paper, D-series) |
| **Third-party simulator pages** | `workspace/anchor-layer/third_party_sim.html`, `anchor_sim.html` | DESCRIBED (runs in Phase 6) |

## §0.3 Corrections to part D §6 ("missing") after checking v1 on disk

Several items were listed as missing only because they were not in the bundles. Checked on v1:

- **They exist:** `server/deploy_ssh.py`, `anchor_queue.py`, `anchor_manage.py`, `readonly_hook.py`, `run_timer.py`, `soc_run.py`, `gen_test_keys.py`, `server/requirements.txt`, `workspace/shared/infra/deploy.config.sh`, `server/integrations/{cred,easypost,hubspot,klaviyo,veeqo}.py`, `odin_app/lib/screens/whatsapp.dart`, `desktop/build/icon.png`, `odin_app/assets/icon/odin_icon.png`, `voice/backend` and `voice/frontend`.
- **Confirmed absent:**
  - `tests/e2e.py` (the `npm run e2e` target);
  - `phase3_up.sh`;
  - `workspace/shared/logs/zoom_spec.txt`;
  - `data/_e2e_sandbox_config.sh`;
  - `data/_e2e_phase1_sandbox.sh`;
  - `real_production_deploy_devops_only.py` (not in v1);
  - `ODIN_DEFECTS_AND_FIXES.md`, which is **not found anywhere on your Mac** (Spotlight search). Please say where it should come from.
- **Code reading only, so UNDETERMINED until Phase 6:**
  - `development_full_checker.sh` l.164 runs `bash phase_ctl.sh` with the current directory at the repository root, while the file is `shells/phase_ctl.sh`. The control bridge may not start.
  - No Android build command is present.

---


<!-- ==================== PART A ==================== -->

# Odin-Orchestrator v1 — Master Feature Inventory (Part A: core docs + history)

Sources read in full:
- `B1_core_docs.txt` (CLAUDE.md, README.md, server/desktop/dashboard/odin_app READMEs, workspace/agents/README.md, workspace/docs/*.md)
- `B3_history.txt` (history/HISTORY.md, history/log.jsonl, snapshots snap-0001..0006, logs/NIGHT_WORK_STATUS.md, logs/TASK2_STATUS.md, logs/soc_report.md)

Secrets policy for this file: key values, the seeded password, the VM IP, VM SSH password and signing team id that appear in the sources are NOT copied — they are named only.

Source abbreviations used in the Evidence column:
- CLAUDE = CLAUDE.md · README = README.md · SRV = server/README.md · DESK = desktop/README.md · DASH = dashboard/README.md · APP = odin_app/README.md · AGENTS = workspace/agents/README.md
- ARCH = AGENT-ARCHITECTURE-ANALYSIS.md · CONV = AGENT-CONVERSION-PLAN.md · CONTRACT = ANCHOR_CONTRACT.md · FEAT = FEATURES.md · ISO = ISOLATION_STATE.md · TECH = ODIN_PHASES_TECH_DOC.md · RAI = README_ANCHOR_AND_INTEGRATIONS.md · REQ = REQUIREMENTS_AUDIT.md · RUFLO = RUFLO-COMPARISON.md · SETUP = SETUP-AND-TEST.md · VAN = VOICE-ANALYSIS.md · VRD = VOICE-README.md · WMV = WEB_MOBILE_VOICE_PLAN.md · NEW = WHATS_NEW.md
- HIST = history/HISTORY.md · LOG = history/log.jsonl (ADR refs) · SNAPn = snapshots/snap-000n · NIGHT = logs/NIGHT_WORK_STATUS.md · TASK2 = logs/TASK2_STATUS.md · SOC = logs/soc_report.md

Evidence status tags: **VERIFIED-RUN (date)** = the doc records an actual run/test result; **BUILT** = doc says built/compiles/bundles but no functional run recorded; **DESCRIBED** = documented behavior/rule only; **PLANNED/PENDING** = not built or awaiting confirmation; **PARTIAL** = doc says partially done.

---

## 1. Feature table

| ID | Feature | Description | Where it lives | How it is run or tested | Evidence |
|---|---|---|---|---|---|
| **Engine & brain** ||||||
| A-001 | Claude CLI engine (core brain) | Claude Code CLI is the primary engine, runs in the project with terminal tools (Read/Glob/Grep/Bash), streams live work | `server/claude_cli.py`, `server/brain_handler.py`; env `ODIN_ENGINE=claude` (default) | `/health` reports active engine; dispatcher auto-detects `claude` binary | FEAT #1 "Live"; LOG ADR-014; VERIFIED-RUN 2026-06-21T19:05 (owner installed Claude Code 2.1.185, engine auto-switched); SNAP5 |
| A-002 | Ollama offline fallback brain | Local qwen model used when Claude CLI unavailable; graceful reply if Ollama absent | `server/brain_handler.py`; model `qwen2.5:7b-instruct-q4_K_M`; env `ODIN_OLLAMA_MODEL` | `brew services start ollama`; `ollama pull …`; `POST /chat` | SRV; SETUP §0; VERIFIED-RUN 2026-06-21T12:00 (/chat 200 graceful EN+AR fallback) and 2026-06-21T15:00 (owner: real Ollama reply via dispatcher) |
| A-003 | Pluggable brain handler | Brain is any object exposing `respond(text, lang)`; voice loop/dashboard unchanged when swapped | `server/brain_handler.py` | not stated | SRV; LOG ADR-007 (DESCRIBED) |
| A-004 | Engine terminal access (configurable tools) | Claude CLI allowedTools includes Bash so engine can run az/ssh/ls and self-solve infra | `claude_cli` allowedTools; env `ODIN_CLAUDE_TOOLS` | not stated | LOG 2026-06-22T16:50 + ADR-016 (BUILT) |
| A-005 | No interactive questions from engine | Engine must never use AskUserQuestion / option menus (hangs headless); act on best assumption, state it in one line | CLAUDE.md "NEVER ask interactive questions"; `--disallowedTools AskUserQuestion` on all 3 claude CLI call sites | not stated | CLAUDE; LOG ADR-023 (BUILT) |
| A-006 | Live engine streaming (tool calls visible) | `--output-format stream-json` surfaces each tool call (bash/az, read, grep) and streams answer text as SSE | `claude_cli.stream_session`, `chats_stream` | not stated | LOG ADR-020 (BUILT; owner rejected "took too long" timeout behaviour) |
| A-007 | Intent interpretation / fuzzy matching | Fix human slips (reversed paths), fuzzy-match names, search wider (`find -iname`) before "not found", apply defaults, be persistent | CLAUDE.md "Interpret like a smart human" + "Be FAST" | Owner smart-test | CLAUDE; LOG ADR-021; ADR-022 records engine PASSED owner smart-test (found organics-frontend, compared 627 vs 625 files) — VERIFIED-RUN 2026-06-22 |
| A-008 | Azure 4KB output truncation workaround | Engine chunks large VM outputs via gzip+base64 to bypass az run-command 4KB truncation | engine behaviour (no module named) | observed in owner smart-test | LOG ADR-022 (observed in a run, 2026-06-22) |
| A-009 | Answer-first reply style | First sentence answers the question ("Yes, …/No, …"), then 1–3 lines; no repeated caveats/boilerplate | CLAUDE.md "Style" | not stated | CLAUDE (DESCRIBED) |
| A-010 | Server no-reload default (timeout root-cause fix) | uvicorn `--reload` killed in-flight requests because server writes its own data files; reload now opt-in and scoped | `server/run.sh`; env `ODIN_RELOAD=1` (watches server/ + orchestrator/ only), `ODIN_HOST` | `./server/run.sh` | LOG ADR-022 (BUILT) |
| A-011 | Backend lifecycle hardening | run.sh frees the port; Electron detached spawn + killBackend on every exit path + single-instance lock (no zombie port) | `server/run.sh`, `desktop/electron/main.cjs` | not stated | LOG 2026-06-23T09:00 note (BUILT) |
| A-012 | Per-scope model control | Pick model for main / project / member (cheap local vs paid); default main = claude-cli, Ollama opt-in | `server/models_config.py` (`DEFAULT_MAIN`, `get_model()`), `data/models.json` | E2E "models 3-levels" | FEAT #20; LOG ADR-028; E2E validated per ADR-034 (2026-06-23) |
| A-013 | Conversation memory in scoped chat | Claude `--resume` session per chat PLUS injection of last 8 scope messages into prompt | `api_v2` scoped stream, `server/chats.py` | `npm run e2e` (chat memory check) | LOG ADR-017, ADR-034 (WARN fixed after owner E2E run 2026-06-23) |
| **Routing / dispatcher** ||||||
| A-014 | Deterministic Brain↔agent dispatcher | classify → load-rules → approval-check → lifecycle hooks → route; brain behind /chat and voice | `orchestrator/dispatcher.py`; `POST /dispatch` | `curl -X POST :8000/dispatch …`; routing unit tests | HIST + LOG ADR-008; VERIFIED-RUN 2026-06-21T14:00 (routing tests 6/6, /dispatch JSON with hooks); SNAP4 |
| A-015 | Routing telemetry log | Each routing decision logged separately from main audit log | `history/routing.jsonl` | `tail history/routing.jsonl` | HIST 2026-06-21; SETUP §4E (DESCRIBED) |
| A-016 | Lifecycle hooks | Named hooks: pre-task rule-load, pre-approval, post-task logging (adapted from Ruflo) | `orchestrator/dispatcher.py` | fired in /dispatch output | RUFLO §2/§9; LOG ADR-005; verified "hooks fired" 2026-06-21T14:00 |
| A-017 | Semantic router (intent understanding) | Local qwen model classifies intent → {agent, action read/change}; keyword scorer = fallback + safety floor (ALWAYS_GATE: secrets/prod-data/sensitive/active-scan) | `orchestrator/semantic_router.py`, `dispatcher.route()`; env `ODIN_SEMANTIC_ROUTER=0` forces keywords | not stated | FEAT #3; LOG ADR-024 (BUILT) |
| A-018 | Name/path masking + DevOps pin | classify() masks names/paths/quoted/hyphenated tokens before scoring and pins DevOps lead for VM/server/folder tasks | `dispatcher.classify()` | not stated | LOG ADR-023 (BUILT) |
| A-019 | Hidden routing label in speech | "[Routed to …]" no longer spoken; kept in /dispatch + routing.jsonl | dispatcher / voice path | not stated | LOG ADR-010 |
| **Approval & safety** ||||||
| A-020 | Approval gate (conversational protocol) | Reads/compare/diff/list run immediately; any change → exact command + impact + rollback + "Approve?" then STOP; execute only on in-conversation approval | CLAUDE.md "Approval protocol"; `orchestrator/dispatcher.py`; `rules/core-rules.md` | `curl -X POST :8000/dispatch -d '{"text":"deploy the backend…"}'` expects `"approval":{"required":true}` | FEAT #4; LOG ADR-019; VERIFIED-RUN 2026-06-21T14:00 (gated request not executed), 2026-06-21T15:00 owner acceptance, 2026-06-22T17:20 gate tests 8/8 |
| A-021 | Advisory gate indicator | Deterministic gate became an advisory status indicator; chat always goes through engine session so "approved" attaches to prior proposal | `dispatcher`, chat stream | not stated | LOG ADR-019 (BUILT) |
| A-022 | Approval request files | `approvals/pending|approved|rejected` folders, template, example APR | `approvals/`, `runbooks/approval-template.md`, `EXAMPLE-APR-0000`, `state/approvals.json` | dashboard reads state/approvals.json | README folder map; SNAP1 (BUILT 2026-06-20) |
| A-023 | Security & Compliance veto | Security agent can block any change touching sensitive data | `agents/security-compliance.agent.md` | not stated | AGENTS (DESCRIBED) |
| A-024 | Secret non-disclosure | Never read/print/copy/log `.env` or any secrets/keys/passwords; stop and say so | CLAUDE.md SAFETY RULES | not stated | CLAUDE (DESCRIBED) |
| A-025 | Mandatory sync secret excludes | Every rsync also excludes `.backup-env`, `.env*`, `*.pem`, `*.key`, `*.bak`, `*.tmp`, `*.copy`, `config/*.json`, `*google-oauth*` (`.backup-env` leaked once) | CLAUDE.md; deploy excludes | not stated | CLAUDE (DESCRIBED; references a past leak incident) |
| A-026 | Production-site protection | All running sites treated as PRODUCTION (organics, bendcore, odinmarkets, odinmedicalsupplies, omh, redfend, odin-travel-desk…) — no state change without explicit approval | CLAUDE.md SAFETY RULES | not stated | CLAUDE (DESCRIBED) |
| A-027 | Attached source folders read-only | Existing `sources` folders are read and considered but never rewritten/scaffolded/deleted unless explicitly asked | CLAUDE.md | not stated | CLAUDE; NEW ⑩ (source-of-truth folders read-only) |
| A-028 | Work inside project localPath | All project builds/scaffolds inside its `localPath`; never at Odin repo root; ask if none set | CLAUDE.md; project cwd fix | not stated | CLAUDE; LOG ADR-039 item 6 ("agents build in the chosen folder") |
| A-029 | Ports 80/443 sacred | Firewall changes keep 80/443 ALLOW; rotation touches only port 22 single-IP; never `ufw reset/disable` | `infra_rotate._ufw_script` | not stated | CLAUDE "CONNECTION SAFETY"; TECH §4 |
| A-030 | Additive-only connection recovery | Recovery only opens ports and reports; never denies/flushes/disables/restarts | `infra/ensure-connection.sh` | run the script | CLAUDE (DESCRIBED) |
| A-031 | Test sandbox isolation + prod deploy guard | Tests only touch `/home/mostafa/_e2e_sandbox` + `organics_e2e_sandbox` DB, never reboot; real prod deploy behind env flag | env `ODIN_ALLOW_PROD_DEPLOY=1` | not stated | CLAUDE (DESCRIBED) |
| A-032 | Two-channel VM access | Control plane (root) ONLY for firewall; everything else (rsync/build/migrate/reboot) via SSH as user `mostafa` with password auth from `oth/.cred` key `azvmcred` | CLAUDE.md; deploy path | sshpass/rsync commands in CLAUDE.md | CLAUDE; TECH §4 (DESCRIBED as automated in deploy path) |
| A-033 | Auto firewall refresh to owner IP | Before SSH steps Odin resets NSG/ufw port-22 rule to owner's current public IP (single IP, old rules deleted) | owner's `reset_ssh_ip` logic via control plane; `server/infra_rotate.py` | not stated | CLAUDE; LOG 2026-06-21T19:45 |
| A-034 | Truth rules / success gate | "Done/passed/deployed" only with real evidence (exit-0, HTTP 200, file check); claims gated and contradictory ones blocked | `server/audit.py` (`audit.gate_success`), QA audit override | not stated | CLAUDE TRUTH RULES (DESCRIBED) |
| A-035 | Hidden-fault scan ("snake in the food") | Even exit-0 runs scanned for Prisma P####, TS errors, ELIFECYCLE, missing modules, port/permission/disk/OOM, FAIL lines | `audit.scan_hidden_faults` | not stated | CLAUDE; ARCH §6 (DESCRIBED) |
| A-036 | Bounded self-heal | Concern-specific analysis → safe fix → re-run, up to 10 rounds; stop for destructive fix/missing info; honest failure after cap | `server/deploy_agent.py` | not stated | CLAUDE; TECH §4 (10-round protocol, retry failed step only) |
| A-037 | Fault learning | Solved faults saved and recognised next time | `data/deploy_faults.json` | not stated | CLAUDE (DESCRIBED) |
| A-038 | Senior-engineer operating discipline | Never fake; start simple; real reason on failure; second solution; same error 2–3x ⇒ widen scope; use tools; persist | CLAUDE.md "HOW TO OPERATE" | not stated | CLAUDE (DESCRIBED) |
| A-039 | Safe migrations only | `prisma migrate deploy` only; `migrate dev/reset` never on VM without explicit approval | CLAUDE.md; `infra/deploy.config.sh` migrate mode | not stated | CLAUDE; NEW ⑩ (never silently set back to reset) |
| A-040 | Speed/efficiency rules | Batch az calls into one script (~15s each); skip node_modules/.next/dist/.git/uploads/build; light diffs | CLAUDE.md "Be FAST" | not stated | CLAUDE (DESCRIBED) |
| A-041 | Protected projects list | Customer project `organics-prod-deploy` excluded from tests and never touched; list later repointed | `PROTECTED_PROJECTS` (scope_guide_test / workspace) | guide tests skip it | NIGHT; TASK2 S4 (repointed) |
| **Azure / infrastructure** ||||||
| A-042 | Azure VM connection via control plane | `az vm run-command invoke` (Azure agent, root) — no SSH/key/IP; lists VM home | `server/infra_az.py`; `GET /infra/connect-test`; `infra/azure/connection.profile.json` | `/infra/connect-test`; dashboard VmStatus chip | FEAT #8; VERIFIED-RUN 2026-06-22T17:00 (owner: listed /home/mostafa, saw organics, bendcore + others); SNAP6 |
| A-043 | VM identity + RG auto-discovery | django-vm / RG DJANGO-PROJECT / centralus; auto-discovers RG from VM name | `infra_az.py`; `connection.profile.json` → `azure` | not stated | LOG 2026-06-22T16:30/16:50; SNAP6 |
| A-044 | SSH reachability helpers | current public IP + read-only reachability + gated `run()` | `server/infra_ssh.py`; `/infra/ip`, `/infra/reachable` | endpoints | FEAT #9 "Built"; LOG 2026-06-21T19:30 |
| A-045 | Dynamic-IP rotation | `az network nsg rule update` (single /32) + ufw via run-command; approval-gated | `server/infra_rotate.py` | not stated | FEAT #9; LOG 2026-06-21T19:45 (BUILT; "used only if needed") |
| A-046 | Azure secure-connection procedure | Strict dynamic-IP procedure: two-place IP update, systemd not PM2, scp, folder mapping | `runbooks/azure-secure-connection.md`; core-rules §5.1 | not stated | HIST + LOG ADR-006; SNAP2 |
| A-047 | Folder mapping local↔VM | `frontend/organics` ↔ `~/organics`; `backend/organics-backend` ↔ `~/Bendcore` (never cross) | CLAUDE.md; projects mapping | not stated | CLAUDE; TECH §4; ADR-006 |
| A-048 | Azure VM status chip | Live VM connected/not + vm/rg on dashboard, checked on mount + click | desktop dashboard `VmStatus`; `/infra/connect-test` | click chip | LOG ADR-028 (BUILT) |
| A-049 | Azure inventory docs | Azure access framework + inventory | `infra/azure/{README.md,connection.profile.json,inventory.md}` | n/a | README; SNAP1 |
| **Deploy / sync** ||||||
| A-050 | Deterministic deploy pipeline | Deploy = `infra/deploy.sh` configured by `infra/deploy.config.sh` (excludes, commands, migration mode, services, subdomain/proxy); AI is the brain on top | `infra/deploy.sh`, `infra/deploy.config.sh` | not stated | CLAUDE "Deploy = pipeline + brain"; NEW ⑩ |
| A-051 | Deploy playbook (owner standing rules) | Never node_modules; ask public/upload/logs; npm install only on dep change; never prod .env; remove dest before rebuild; rebuild both; systemd not npm start; prefer service restart over reboot | `infra/DEPLOY-PLAYBOOK.md` | not stated | LOG 2026-06-23T09:00 note; CLAUDE "Local → VM sync" |
| A-052 | Smart sync/deploy pre-flight | Inspect real content (diff -rq, rsync --dry-run, du, package-lock, git status, detect production), ask context-aware questions, propose + rollback, execute after approval | `projects.sync_proposal/sync_run/deploy_proposal/deploy_run`; `/projects/{pid}/sync/run`, `/projects/{pid}/deploy/run`; "Run sync/Run deploy" buttons | buttons (confirm = approval) | FEAT #21; LOG ADR-033, ADR-037 (BUILT; "engine behavior runs on owner's machine") |
| A-053 | Post-deploy online verification | QA polls health URL every ~10s up to 2–3 min until HTTP 200; else last error + journalctl + rollback suggestion; project `url` field used by checker | CLAUDE.md step 6; project `url` field | not stated | CLAUDE; LOG ADR-038 |
| A-054 | DevOps production deployment flow | Source = local, destination = VM; read-only source-of-truth folders; working copy + `.git` baseline under `~/Desktop/misc/Odin/`; `.deploy_state` first-time flag; later deploys ship only changed files; exclusion list; DB reset first time only then ask; post-reboot health checks (domain/backend/frontend/nginx/systemd) | deployment project (DevOps-only intake), `infra/deploy.config.sh` | deploy from the project (preview rsync+build+reboot) | NEW ⑩ (DESCRIBED); TASK2 S5 VERIFIED-RUN (rsync dry-run = 0 files → no deploy; 14 ok / 0 fail) |
| A-055 | One-step non-recurring deploy w/ isolated retry | 10-round failure protocol isolates the failed step, retries only it, never re-runs reboot/reset | deploy agent | not stated | TECH §4 |
| A-056 | Deploy source-fingerprint gate | If server/testing/dart source changed since last deploy → force full redeploy incl. web rebuild; fingerprint saved only after success | phase3 gate; env `ODIN_FORCE_DEPLOY=1`; `logs/FORCE_DEPLOY` | `touch logs/FORCE_DEPLOY` then `phase3` | ISO; REQ #14 "verified in code" |
| A-057 | Phase-3 smart gate | Skips VM deploy when anchor+web already healthy (fast path) | phase3 script | `phase3` in loop | ISO (DESCRIBED) |
| A-058 | Production full checker (ex phase3_up.sh) | Deploys ANCHOR (VM :48619) + WEB (VM :48620) behind nginx 443 at anchor.odinmarkets.com via phase3_gate deploy-anchor/deploy-web; pre-deploy read-only validation; first run deploys, changed asks; launches supervised poller | `shells/production_full_checker.sh` (renamed from `phase3_up.sh`), `workspace/shared/infra/phase3_gate.py` (`validate`, `deploy-anchor`, `deploy-web`); env `ODIN_PHASE3_YES=1` | `ODIN_PHASE3_YES=1 bash shells/phase3_up.sh`; `phase3_gate validate` must exit 0 | NIGHT recon + FINAL: VERIFIED-RUN 2026-07-21 (anchor+web live, health 200, prod e2e PASS, anon 401, login OK) |
| A-059 | Development full checker (ex phase2_up.sh) | One command: brain :8000 + anchor :9100 + poller + desktop + web :8080 + iOS sim, prints test keys; asks "use anchor? [Y/n]" | `shells/development_full_checker.sh` (renamed from `phase2_up.sh`); env `OPEN_DESKTOP=0` | `./phase2_up.sh` | TECH §12.1; RAI; REQ #5; NIGHT FINAL (rename, `bash -n` OK) |
| A-060 | Forced fresh Flutter rebuild | On forced deploy runs `flutter clean` so web+mobile rebuild fresh (stale build caused 404) | `phase3_up.sh` | forced deploy | ISO fix #5 (in code) |
| A-061 | Web deploy leaves nginx alone | Web deploy no longer edits nginx; anchor owns single `odin-proxy` site (stops 404 flip-flop) | `test_web_online.py` | not stated | ISO fix #6 |
| A-062 | Turnkey one-click VM deploy | Intentionally left as gated proposal ("not rigid enough to touch running sites") | — | — | FEAT "Still parked" (PARKED) |
| **Multi-agent organisation** ||||||
| A-063 | Six specialist agents | Frontend, Backend, DevOps & Cloud, Security & Compliance, QA & Testing, Database with triggers/hand-offs | `agents/*.agent.md` (`frontend`, `backend`, `devops-cloud`, `security-compliance`, `qa-testing`, `database`) | not stated | AGENTS; FEAT #11; SNAP1 **[corrected: see §0.8 C-2]** |
| A-064 | Scoped multi-agent org | company → project:<id> → member:<pid>:<agent> scopes, each own pool; upward sync; drill-down; same member across projects | `server/scopes.py`, `server/store.py`, `design/SCOPED-MEMORY-SPEC.md` | backend smoke tests | FEAT #15; LOG 2026-06-22T02:00 spec, ADR-025 (backend smoke + route + regression PASS) |
| A-065 | Delegation + live activity | Project CTO delegates a turn to responsible member; heartbeat avatars; flow rail | `server/api_v2.py` (`_scoped_gen`), `server/activity.py` | not stated | FEAT #16; ADR-025 |
| A-066 | Autonomous team run (multi-agent chaining) | `plan_pipeline` returns ordered [{member, task}] (heuristic fallback Backend→Frontend→DevOps); SSE run auto-hands off member→member | `projects.plan_pipeline()`; `GET/SSE /projects/{pid}/orchestrate`; `_orchestrate_gen`; TeamRun panel in ProjectView | `npm run e2e` team-run test | LOG ADR-030; ADR-034 E2E validated delegation Backend→Frontend→DevOps (owner run 2026-06-23) |
| A-067 | Agent-to-agent dialogue | Chief→Project CTO brief/plan/final report; per member CTO brief → member works → CTO reviews; chats become documentation | `_orchestrate_gen` | E2E fails unless project chat ≥3 msgs and member chat roles [user,assistant,user] | LOG ADR-035 (BUILT; "owner runs npm run e2e") |
| A-068 | Live phase visibility | Activity carries phase (CTO→X briefing / X working / CTO reviewing X); shown on project cards, LiveAgents, MemberView | `activity.py`, desktop views | not stated | LOG ADR-035 |
| A-069 | CTO hires a new agent on the fly | Planner keeps a new proposed role; orchestrate auto-registers missing member (suggest_agent) and emits "CTO hired a new member" | `plan_pipeline`, `agents_registry.suggest_agent` | not stated | LOG ADR-038 |
| A-070 | Smart team inference | `infer_team()` negation-aware ("no backend", "deploy later"), static-only short-circuit; no hallucinated agents | `projects.infer_team` | 5 cases verified; `npm run e2e` | LOG ADR-032, ADR-034 (E2E FAIL fixed; verified 5 cases) |
| A-071 | Project creation from description | Engine plans components; create REAL folder at any chosen absolute path; registry | `server/projects.py` (`create_project`) | verified creates landing/shop/deskapp dirs | FEAT #17; LOG ADR-032 (verified on disk) |
| A-072 | Project presets | One-click Deployable web app / Static landing / Mobile in New Project | desktop New Project modal | not stated | LOG ADR-039 |
| A-073 | Adaptive intake (conversational project creation) | `intake_step` adaptive Q&A → spec; open-ended any software type; dependency-aware | `projects.intake_step()`, `capabilities.py` | `npm run e2e` intake check | LOG ADR-033; ADR-034 ("adaptive intake adapted to answer"); ADR-032 had listed conversational creation as NOT done earlier |
| A-074 | Agents registry + rules engine | Add member by description (suggest name), per-project skills folder, restrictions, save-as-rule, interrupt chat | `server/agents_registry.py`, MemberView | not stated | FEAT #18; ADR-025 |
| A-075 | Usage stats | Per-agent invocation counts + % of work, animated bars | `agents_registry.stats`, `views.jsx` | not stated | FEAT #19 |
| A-076 | Company-level agents | Company agents CRUD; auto-seeded into every new project; CompanyAgents panel | `agents_registry` company CRUD; `/company/agents` | E2E company-agent auto-seed check; verified team included company agent | LOG ADR-039 (verified) |
| A-077 | External connectors registry | Connectors CRUD with keys in gitignored file; status badge; Connectors panel | `capabilities` connectors; `connector_keys.json`; `/connectors` | E2E connectors check | LOG ADR-039 |
| A-078 | Per-project custom rules | Owner add/edit/discard rules live; written to file engine reads | `proj['rules']`; `/projects/{pid}/rules` (GET/POST/update/DELETE); `skills/_custom-rules.md`; ProjectRules UI | not stated | LOG ADR-038 |
| A-079 | Per-project scheduler | Schedule prompts daily / interval / once; background runner; periodic task assigned to a member (runs as that agent) | `server/scheduler.py` | E2E "agent-assigned periodic schedule" | FEAT #22; LOG ADR-025, ADR-039 (cross-agent auto-delegation is engine-guided, PARTIAL) |
| A-080 | Member activity log timeline | Every task the member received/did as a timeline | `MemberActivityLog` | not stated | LOG ADR-033 |
| A-081 | Hierarchy monitoring feed | Company page shows what projects do; project page shows what members do | `MonitorFeed`, `scopes.get_summary(scope).feed` | not stated | LOG ADR-033 |
| A-082 | Live agents strip + premium avatars | Every member across projects; idle avatars static, working ones heartbeat ring/glow/conic halo; "WORKING ON NOW" banner | desktop `ui.jsx`, `views.jsx` | E2E "no fake activity when idle" | LOG ADR-031, ADR-032 (activity empty after create verified) |
| A-083 | Member self-report prompt | Each agent restates understanding, reports what it tested + open questions | member work prompt | not stated | LOG ADR-036 |
| A-084 | Archived projects view | "Archived" nav entry (tooltip listed) | desktop nav | not stated | LOG ADR-036 (mention only) |
| A-085 | Agent scope (delta-first credentials) | `agent_scope` table + `agent_scope_guard`: delta-first → default, reports `credential_source`, read-only, non-blocking; bindings Fulfillment/Email/HubSpot | `workspace_mw.py`, `agents_registry.py`, `api_v2.py` (`_run_gated`, line ~983) | live agent-scope tests 6/6 | TASK2 S4 + test phase: VERIFIED-RUN (6/6; credential_source=delta; unbound Analytics=default; caveat closed on real `_run_gated`) |
| A-086 | Dual-scope injection | Binding-gated injection of agent scope in `_run_gated` | `api_v2._run_gated` | live test | TASK2 S4 |
| A-087 | External single-file report rule | External reports written only via enforced single-path writer | `external_report` table + `write_external_report`; output `VolatileWorkSpace/AI_DIAGNOSIS_REPORT.md` | S6/S8 run | TASK2 (VERIFIED-RUN) |
| A-088 | Extra agents: HubSpot, CloudDebug, Email, Shipping, Live Meeting, Reporting & Documentation, Recovery & Resilience | Domain agents beyond the six core | `agents_registry`; referenced in TECH §2/§3, NEW ⑨, SOC | n/a | TASK2 (HubSpot+CloudDebug registered); TECH; NEW; SOC |
| **Planned orchestration upgrade (Main Task)** ||||||
| A-089 | Main Task shared-state object | Each prompt becomes a persistent MainTask {objective, brief_verbatim, requirements[], decisions, plan[], status} | new `server/main_task.py` (planned) | unit create/update/reload | CONV Phase A (PLANNED) |
| A-090 | Requirements extraction + completeness gate | Parse brief → checkable requirements; verify every requirement maps to ≥1 mandate, else re-plan | `projects.intake_step`, `_orchestrate_gen` | frozen E2E MINING metric | CONV Phase B; ARCH §6 (PLANNED) |
| A-091 | Structured mandates | `plan_main_task()` emits {member, objective, inputs, deliverable, acceptance, depends_on, hand_off} instead of one-line task | `server/projects.py` | PROPAGATION metric | CONV Phase C; ARCH Gap 1/2 (PLANNED) |
| A-092 | Write-back + alignment loop + Main-Task final verification | Deliverables written into status; CTO re-checks and re-dispatches gaps; done only when all requirements done + QA/audit clean | `api_v2._orchestrate_gen` | CRYSTALLIZATION / TRUTHFULNESS metrics | CONV Phases D–E (PLANNED) |
| A-093 | Route by task type | Sequential ops (deploy) → single-agent hybrid + deterministic execution; parallel builds → crew | dispatcher/orchestrate | not stated | ARCH §5–6; CONV routing note (PLANNED/DESCRIBED) |
| A-094 | Frozen AI capability E2E | Measures MINING / PROPAGATION / CRYSTALLIZATION / TRUTHFULNESS; frozen, untouched | `server/e2e_ai_capability.py` | run per phase | CONV §5 (exists; no run result recorded here) |
| **Scope middleware & audit** ||||||
| A-095 | Scope answer guard (system middleware) | Answer within current project scope first; never removes knowledge; owner never blocked/approved; external out-of-scope needs owner approval; status = project's own state, not repo/cwd | `server/workspace_mw.py` `scope_answer_guard(project_name, external)`; used by `api_v2._scoped_gen` (/scope/stream) and `anchor.process` | `server/scope_guide_test.py`, `server/scope_reasoning_test.py` | NIGHT: VERIFIED-RUN 2026-07-20 ~02:07 ("how many profiles" answered in-scope); FINAL 2026-07-21 "0 violations" |
| A-096 | Read-execute guard ("a read is not a change") | Owner reads auto-execute GET-only connector/data queries and return live value; use read-only command forms; plain follow-up offers; never proposal/approval for reads; writes still use PROPOSE_RULES | `workspace_mw.read_execute_guard(connectors)`; `api_v2._scoped_gen` `_is_read = not _is_work_request(text)` | live bridge test (Klaviyo) | NIGHT VERIFIED-RUN 2026-07-20 ~02:50 ("16 profiles … via read-only integration", had_propose=false); FINAL fixes 2026-07-21 |
| A-097 | External out-of-scope → owner approval request | Third-party insisting on out-of-scope info triggers `approvals.create()` to owner; answer after approval | `anchor.process`, `approvals.create` | not stated | NIGHT "STILL PENDING" — no completion recorded (PENDING) |
| A-098 | External request scope + privacy guard | External path answers within project scope; no leak of internals/other projects | `server/anchor.py` | live | NIGHT "LIVE in server/anchor.py" (2026-07-20) |
| A-099 | Guard token budget | Guards add no extra LLM call; compressed ~1104 → ~355–397 tokens per owner read | `workspace_mw.py` (backups `.bak_precompress`, `.bak_reasoning`) | token count | NIGHT 2026-07-20 ~08:20 / ~09:35 |
| A-100 | Scope guide test (LLM judge) | Generates 3–4 probes per project from own metadata; judge classes ANSWERED_IN_SCOPE / UNNECESSARY_CLARIFICATION / WRONG_SCOPE / BLOCKED_OR_APPROVAL / LEGIT_CLARIFICATION; logs `scope-answer` violations | `server/scope_guide_test.py` (`_judge`, `_evaluate`, `run_all`); `workspace/history/scope-probes.jsonl`; `workspace/history/audit-log.jsonl` | `run_all()` over non-protected projects; progress `/tmp/guide_progress*.jsonl` | NIGHT passes 1–9 (grader unit tests 6/6 then 7/7; real-model pass-6 6/7 clean) |
| A-101 | Scope reasoning test (metric scorecard) | Fresh diverse questions per project in 4 categories (IN_SCOPE_DEEP, CROSS_SCOPE_TRAP, AMBIGUOUS, OOS_OWNER); metrics FALSE_REFUSAL / LEAKAGE / WRONG_AMBIGUITY / WRONG_OOS; fail-closed judge; answer cap 600s; runs with production model claude-cli, judge on haiku | `server/scope_reasoning_test.py` | `run_all()`; parallel x4; `/tmp/reason_progress.jsonl` | NIGHT parallel pass 1 (11/14 clean, LEAKAGE=0); FINAL VERIFIED-RUN 2026-07-21 "Giant test GREEN (0 violations)" |
| A-102 | Generalisation test projects | 4 temporary projects (support-desk, finance-invoices-expenses, analytics-product-metrics, hr-recruiting-pipeline) proved generalisation, then deleted; backup kept | `TEST_PROJECTS_BACKUP.json` | reasoning test | NIGHT FINAL (created, tested, deleted; 11 originals kept) |
| A-103 | Workspace structural / DB audit | Detects misplaced / unindexed / db-orphan / duplicate / foreign-ref / root-stray / parallel-registry (JSON-as-DB) issues; self-heal | `workspace_audit.scan`, `wa.heal()` | scan | NIGHT VERIFIED-RUN 2026-07-20 (0 issues) and FINAL (4 issues in full-services-19jul healed → 0) |
| A-104 | Audit page on every surface ("silence page") | Bundle of status + config + issues + violations shown on desktop, web, mobile, dashboard; poller mirrors key "audit" to anchor | backend `/audit/mirror`; `odin_app/lib/screens/audit_screen.dart` (nav "Audit" in `shell.dart`, `anchor_api.dart`); `dashboard/audit.html`; desktop | not stated | NIGHT 2026-07-20 ~08:45 "CODE GAPS CLOSED" (BUILT) |
| A-105 | Audit commands in loop bridge | `audit` / `auditfix` commands; audit 0 violations reported | `logs/phase_ctl/CMD` | bridge | ISO tools list; NIGHT ("Audit: 0 violations") |
| A-106 | Generic project report endpoint | `/project/report` with no per-project hardcode | backend | not stated | NIGHT (VERIFIED DONE list) |
| A-107 | Audit rules for stuck/generic/wrong-format replies | Not described in these two bundles; the only reply-quality violation types here are scope-answer classes (A-100/A-101), fake-success gate (A-034) and hidden faults (A-035) | — | — | Not stated in B1/B3 |
| **Chat & UI (dashboard / cockpit / desktop)** ||||||
| A-108 | Persistent chats | One JSON per conversation; new/rename/delete; history reload; resumes Claude session per chat; robust logical delete | `server/chats.py`; `/chats` CRUD; `/chats/{id}/stream` | not stated | FEAT #5; LOG ADR-017 |
| A-109 | Streaming cockpit console | SSE `/chat/stream` animated status steps with icons, token streaming, code rendering, activity rail, voice | `dashboard/console.html` | not stated | FEAT #6; LOG ADR-015 ("Verified streaming + approval flow in sandbox"); SNAP5 owner-accepted |
| A-110 | Markdown renderer + speech cleaner | Tables, bold, lists, headers, inline/block code with copy; `OdinMD.toSpeech` strips markdown for TTS | `dashboard/odin-md.js` | not stated | LOG ADR-018; ADR-037 (verified renderer works) |
| A-111 | Chat persistence bug fixes | Assistant reply persisted before streaming; reuse empty "New chat"; junk test chats cleaned | `server/chats.py` | not stated | LOG ADR-018 |
| A-112 | Static dashboard | Reads state/project.json, tasks.json, approvals.json, history/log.jsonl; built-in snapshot offline; responsive phone/desktop | `dashboard/index.html`, `dashboard/artifact.html` | `python3 -m http.server 8080` → `/dashboard/index.html`; or served at `http://localhost:8000/` | DASH; README; SETUP §4A |
| A-113 | Live Cowork artifact dashboard | Persistent dashboard reopenable across sessions; accessible from Claude desktop/mobile apps | Cowork artifact | "open the Odin dashboard" | DASH §2; RUFLO §6 |
| A-114 | Voice Console card | Dashboard card: Record → STT → Brain → TTS, EN/AR toggle | `dashboard/index.html` | open `http://localhost:8000/` | SRV; SNAP3; SETUP §4B |
| A-115 | Desktop company dashboard | Big company-scope chat, live statuses, all projects, agents-live count, new project; System Status panel (API, engine, voice EN/AR, Azure VM, main model, projects, agents-live) | `desktop/src/views.jsx` (Dashboard) | not stated | FEAT #14; LOG ADR-031 |
| A-116 | Desktop project & member pages | ProjectView (project CTO, TeamRun, rules, toolbar Plan/Schedule/Map/Sync/Deploy), MemberView (activity, phase), modals | `desktop/src/views.jsx`, `App.jsx` | not stated | DESK; ADR-025/030/036 |
| A-117 | Multi-level chat panel | Chat at every scope with streaming + voice + markdown; left date-grouped sidebar (Today/Yesterday/date); scope label header | `desktop/src/ChatPanel.jsx` | not stated | FEAT #23; LOG ADR-036 |
| A-118 | Hover tooltips | Tooltips on nav, toolbar, add member, team-run, save-rule, chat controls | desktop | not stated | LOG ADR-036 |
| A-119 | RTL/LTR auto-direction | Arabic (U+0600–06FF) messages rendered RTL/right-aligned | desktop chat | not stated | LOG ADR-037 |
| A-120 | Markdown in Plan/Sync/Deploy result panel | Result panel renders markdown (was raw) | desktop | not stated | LOG ADR-037 |
| A-121 | File/folder attach in chat | ＋ button opens native picker for files/folders; PATHS injected for engine to read (no binary upload) | `preload` pickFiles/pickFolders + `main.cjs` handlers | not stated | LOG ADR-039 (PARTIAL: paths only) |
| A-122 | Native project folder picker | Electron dialog to choose project location | preload pick-folder | verified dir creation | LOG ADR-032 |
| A-123 | Desktop settings | ⚙️ change backend URL / access token | desktop Settings | not stated | DESK |
| A-124 | Desktop "Connecting with Anchor" indicator | Topbar blinks when anchor generates a Manage login code; dialog shows email/password/code to copy | desktop topbar (new) | — | REQ #19 "NEW — to build next" (PLANNED) |
| A-125 | In-app docs bell | Bell on web + Flutter + desktop holds styled doc cards (Caching & implementation; Klaviyo/Veeqo/Azure/Anchor; per-feature tabs); badge = number of tabs | `WHATS_NEW.md`, docs/*.pdf | open bell | TECH §14; NEW header + "Notification bell" fix |
| A-126 | Mode switch button | CTO↔Group mode switch always visible in top bar (moved out of ⋮ menu) | `odin_app` | not stated | NIGHT (VERIFIED DONE list) |
| A-127 | Usage-bars / heartbeat UI kit | Animated avatars, markdown, modal, usage bars | `desktop/src/ui.jsx` | not stated | DESK |
| A-128 | Cost tracking | No explicit cost/billing tracker in these docs; only per-agent usage stats (A-075), guard token budget (A-099), cheap-vs-paid model choice (A-012); custom billing model is a placeholder | `rules/core-rules.md §6.1` | — | HIST 2026-06-20 NOTE; SETUP "NOT tested" (PLACEHOLDER) |
| **Flutter app (web + mobile)** ||||||
| A-129 | Flutter companion app | One Dart codebase for web + Android + iOS; pure client of anchor contract + project/chat API | `odin_app/` (`lib/`, `pubspec.yaml`, `lib/api/anchor_api.dart`) | `flutter run -d chrome` / device id | APP; CONTRACT Phase 2 |
| A-130 | Projects screen | Lists projects (`GET /api/v1/projects`) with on-click refresh; ＋ New project | `odin_app` | app | APP; RAI §5 |
| A-131 | On-demand project chat | `POST /api/v1/p/{id}/ask` grounded in project brief + shared context; direct (sync) vs anchor (async) transport | `odin_app`, `server/external_api.py` | app | APP; CONTRACT |
| A-132 | Anchor status page | Counts + full requests feed + form to send external request and watch lifecycle | `odin_app` Anchor tab | app | APP |
| A-133 | Local notifications | Newly finished/failed anchor requests raise mobile local notification / web in-app banner (conditional import) | `odin_app` | refresh in app | APP (DESCRIBED) |
| A-134 | Settings + connection profiles | Base URL + two API keys, Test connection, persisted via shared_preferences; profiles Local (Phase 2) / Anchor sim (Phase 3 test) / Deployed (Phase 3); modes direct/anchor; `apiBaseUrl` + `anchorBaseUrl` | `odin_app` `config.dart`, Settings | "Test connection" | APP; CONTRACT; ISO fix #4 (Deployed profile → anchor domain) |
| A-135 | Group chat mode (WhatsApp-style) | Shared group thread on same /scope pool; text, camera/photo, files (docx/zip), voice notes with transcript under bubble (server faster-whisper), reply via long-press, in-bubble audio | `odin_app/lib/screens/whatsapp.dart` | app | APP (DESCRIBED); WMV notes attachments blocked in anchor mode |
| A-136 | Shared chat pool | Company (`scope=company`) and project (`scope=<pid>`) chat share the same /scope store as desktop and agents | `/scope/*` endpoints | app | APP; RAI |
| A-137 | Live sync web+mobile | Per-scope keys, 5s live pull, write path (post/delete) via anchor | `odin_app`, anchor | stack run | NIGHT "VERIFIED DONE" (2026-07-20) |
| A-138 | Pure-anchor mode (Phase 2 mimics 3) | Web/mobile go ONLY through anchor (apiBase empty); all reads from anchor mirror | `anchor_api.dart`; `/anchor/v1/pool/{id}`, `/anchor/v1/mirror/{key}` | kill anchor → app gets nothing | REQ #1–2 "verified in code" |
| A-139 | Offline sensing | "You are offline / Try again" when anchor unreachable; retry spinner ~0.8s; no stale data | `odin_app` | offline drill | REQ #4 (code done; live drill PENDING) |
| A-140 | bootAuth anchor-mode fix + auto profile switch | Skip local `/auth/config` in anchor/production mode (fixed "connecting to your machine…" hang); auto-switch to Deployed profile if local brain unreachable; clean errors not raw HTML | `odin_app/lib/state/app_state.dart` (`bootAuth`, `refreshDashboard`), `anchor_api.dart` | rebuild + open deployed web | ISO fixes #1–3 (in code; live confirm was blocked at time) |
| A-141 | Release web build served statically | Phase 2 builds release web (debug dev-server caused splash hang), auto-opens, served no-cache | phase2 script | `./phase2_up.sh` | REQ #6 |
| A-142 | Chat header items | Title, sync spinner, "Copy all", Reload (must not be displaced by new speaker icon) | `chat_screen.dart`, `whatsapp.dart` | — | WMV A3 (mentions existing) |
| **Authentication & access** ||||||
| A-143 | Login on web + mobile | Required login; seeded owner account (owner email + seeded password — not copied) stored hashed; change password in Settings → Account | `oth/.auth` (gitignored); web + Flutter Settings | log in at :8080 | TECH §9; NIGHT FINAL (login OK, anon blocked 401, 7-day session) VERIFIED-RUN 2026-07-21 |
| A-144 | 2FA | Functional machinery, default OFF | `oth/auth_config.json` `twofa_enabled` | toggle config | TECH §9 (DESCRIBED) |
| A-145 | Verify email | Functional, default OFF | `verify_email_enabled` | toggle config | TECH §9 (DESCRIBED) |
| A-146 | Forgot password | Available on web + mobile | auth | not stated | TECH §9 table |
| A-147 | Face ID first access | iPhone 13 Face ID gates first access on mobile | `faceid_first_access` | not stated | TECH §9 (DESCRIBED) |
| A-148 | Desktop open (no login) | Local desktop needs no login | `desktop_open: true` | — | TECH §9 |
| A-149 | Auth config flags | `require_login_web`, `require_login_mobile`, `twofa_enabled`, `verify_email_enabled`, `faceid_first_access`, `desktop_open` | `oth/auth_config.json` | edit file | TECH §9 |
| A-150 | Machine-to-machine API keys | `X-API-Key` ANCHOR_API_KEY for /anchor/v1, ODIN_API_KEY for /api/v1; session token / `X-Odin-Token` for native brain routes; poller uses anchor key | `oth/.cred`; `server/gen_test_keys.py` | `python3 server/gen_test_keys.py` | TECH §9; CONTRACT Auth; RAI (key values exist in docs — must be rotated) |
| A-151 | Shared-secret mobile token gate | Optional `ODIN_ACCESS_TOKEN` (header or query) gates /chat, /dispatch, /voice/*, /chats | `server/app.py` middleware | `/chat` without/with token | HIST; VERIFIED-RUN 2026-06-21T14:00 (401 without / 200 with) |
| A-152 | Credentials reader | Reads `oth/.cred` in both `KEY=value` and `key: value` formats | `server/integrations/cred.py` | — | RAI Files |
| A-153 | HMAC-signed webhooks + per-device tokens | Webhook signing header and per-device tokens for production | anchor config | — | TECH §8, §9, §13 (PLANNED Phase 3) |
| A-154 | Anchor "Manage" protected area | Login (email + password + random confirmation code), "remember this device & browser", full CRUD on requests, allow/stop mobile and web toggles | anchor landing page | — | REQ #18 "NEW — to build next" (PLANNED) |
| A-155 | Remote phone access options | Tailscale (recommended), Cloudflare quick tunnel, or LAN; internet exposure approval-gated | `runbooks/phone-access.md`, `runbooks/mobile-access.md` | runbook | LOG 2026-06-22T18:20 |
| **Voice** ||||||
| A-156 | Voice service router | FastAPI router adding `POST /voice/stt` (multipart `file`, `?language=en|ar`) and `GET /voice/tts?text&lang` → audio/wav; gated by `USE_VOICE=1` | `voice/backend/voice_service.py` (`build_router`), `voice/backend/tts.py`, `requirements-voice.txt` | `USE_VOICE=1 ./server/run.sh`; 503 if voice off, 500 if deps missing | VRD; SRV; VERIFIED-RUN 2026-06-21T12:00 (routes confirmed; STT 422 on missing file) |
| A-157 | Local Whisper STT (EN+AR) | faster-whisper offline, auto language detect; model selectable | `voice_service.py`; env `ODIN_WHISPER_MODEL` (tiny…large-v3) | `/voice/stt` | VAN §3; LOG ADR-004 |
| A-158 | English TTS = Kokoro | Kokoro-82M American voice `af_heart` | `voice/backend/tts.py` | `/voice/tts?lang=en` | LOG ADR-010; VERIFIED-RUN 2026-06-21T18:00 (EN 200) |
| A-159 | Arabic TTS = Coqui XTTS-v2 | Offline, free, no API key; final choice after Maged → Piper → MMS → Azure Salma iterations | `voice_service.py` Arabic branch; `pip install coqui-tts` | `/voice/tts?lang=ar` | LOG ADR-011/012; VERIFIED-RUN 2026-06-21T18:00 (HTTP 200, first call 19.5s) + owner VOICE ACCEPTED 2026-06-21T18:15 |
| A-160 | Earlier Arabic TTS options (superseded) | Piper (`ODIN_PIPER_AR_MODEL`), macOS `Maged` (`ODIN_MAC_AR_VOICE`), MMS-TTS, Azure Neural (`AZURE_SPEECH_KEY`/`REGION`) | SRV, SETUP §6, VRD | — | LOG ADR-007/009/011/012 (superseded; SRV/SETUP docs still describe Piper/Maged — stale) |
| A-161 | Arabic speech speed control | Coqui speed forwarded (`ODIN_XTTS_SPEED`, default 1.3); desktop Arabic speed tuned to 1.15 (localStorage `odin.speed.ar`) | `voice_service.py`, desktop `speak()` | not stated | LOG ADR-029, ADR-031 |
| A-162 | TTS pre-warm | XTTS + Kokoro warmed at startup so first user request is fast | server startup | not stated | LOG 2026-06-21T18:00 |
| A-163 | Browser autoplay unlock | Persistent `<audio>` unlocked on user gesture | dashboard/desktop | not stated | LOG ADR-010 |
| A-164 | Desktop mic behaviour | Iterated: live browser SpeechRecognition (ar-EG/en-US) primary + Whisper fallback (ADR-029), then Whisper-only near-real-time (base model partials every 0.9s + accurate final), visible errors (ADR-037) | `desktop/src/ChatPanel.jsx`, `api.js` `transcribe()`; Electron media permission handler | not stated | LOG ADR-028 (422 field-name fix), ADR-029, ADR-031, ADR-037 |
| A-165 | EN/AR toggle (desktop) | Visible EN/ع toggle drives stream + STT + TTS; Arabic sets RTL + Arabic placeholder; moved into chat header | `ChatPanel.jsx` | not stated | LOG ADR-028, ADR-036 |
| A-166 | Voice overlap prevention | Single global audio; stopSpeech() before each speak + on send; 🔇 button | desktop | not stated | LOG ADR-032 ("DONE+verified") |
| A-167 | Voice never uses OS voice (desktop) | Desktop EN = Kokoro, AR = Coqui XTTS via backend; no macOS/browser TTS fallback | DESK; ADR-009 | — | DESK; LOG ADR-009 |
| A-168 | React voice hook | `useVoice({lang})` → `toggleMic(setInput)`, `speak(reply)` | `voice/frontend/useVoice.ts` | — | VRD; VAN §4 |
| A-169 | Voice self-test script | Voice self-test | `scripts/voice_selftest.py` | `python scripts/voice_selftest.py` | LOG ADR-009 |
| A-170 | Flutter device voice | OS speech engine via `flutter_tts` + `speech_to_text`; 🔊 reads replies, 🎤 dictates; iOS Info.plist mic/speech/camera/photo keys | `odin_app/lib/services/voice.dart` | app | APP (DESCRIBED) |
| A-171 | Enhanced web/mobile voice (plan) | On-device Kokoro (`kokoro-js` web, `sherpa_onnx` mobile) with native fallback; text normalizer (strip code/markdown/URLs/emoji, script-aware); speaker icon in header of BOTH normal and chat modes; mic EN/AR locale; fix stale-buffer `_mic()` bug; remove record→upload from mic; feature-detect unsupported browsers; no audio stored | `voice.dart`, new `tts_kokoro_web.dart`, `tts_sherpa_mobile.dart`, `text_normalizer.dart`, `whatsapp.dart`, `chat_screen.dart`, `web/index.html`, `pubspec.yaml` | test on real iPhone + Chrome EN/AR | WMV (PENDING — "implement when Mostafa returns") |
| A-172 | Mobile keyboard dismissal (plan) | Scroll-to-dismiss, translucent tap-outside unfocus, resizeToAvoidBottomInset + auto-scroll, explicit hide-keyboard button with managed FocusNode, remove stray autofocus | `whatsapp.dart`, `chat_screen.dart`, `shell.dart`, `dashboard.dart`, `login.dart` | verify on real iPhone | WMV Part B (PENDING, HIGH-PRIORITY BLOCKER) |
| A-173 | Live Meeting → smart report | Speaking-head icon opens dialog/sheet; live mic with sensitivity, VAD, noise, language, chunk counter; pause/resume; per-chunk transcription + confidence flags; refine + merge into 13-section report in majority language; embedded in project chat | `dashboard/meeting_monitor.html`, `server/meeting_api.py` (`/meeting/*`), `scopes.transcribe`, `projects._engine`, `odin_app/lib/screens/meeting_sheet.dart`, `assets/global_voice_streaming_asset.md` | in app | NEW ⑨ (DESCRIBED; no run recorded) |
| A-174 | Meeting report export | Markdown or Word (.docx), Arabic (RTL) or English, or "All 4" zip | `python-docx` export in meeting API | in dialog | NEW ⑨ |
| **Anchor Connect** ||||||
| A-175 | Anchor smart queue | Durable queue + lifecycle + webhook + ack + retry | `server/anchor_queue.py`; `data/anchor_queue.json` | `python3 server/e2e_anchor.py` | CONTRACT; TECH §6 |
| A-176 | Request status lifecycle | received → queued → sent_to_local → processing → response_received → webhook_sent → acknowledged → finished; branches ack_pending / failed / cancelled; delete = status flag; finished/failed never re-polled | `anchor_queue.py` | e2e suites | CONTRACT; TECH §5 |
| A-177 | Retry policy | retry_count=4, retry_interval_sec=600, poll_limit; configurable; exhausted → failed (record kept) | `/anchor/v1/admin/config` | e2e flaky/failing webhook checks | CONTRACT |
| A-178 | Anchor HTTP API | `_status`, `POST /requests`, `GET /requests/{id}`, `POST /requests/{id}/ack`, `GET /poll`, `POST /requests/{id}/result` (idempotent), admin requests/counts/config | `server/anchor.py` (`/anchor/v1` router) | `python3 server/e2e_anchor_http.py` | CONTRACT; TECH §10 |
| A-179 | Webhook delivery + ack | POST to caller `webhook_url` with result; 2xx = ack; non-2xx retried | `anchor_queue.py` | webhook receiver | CONTRACT |
| A-180 | Anchor process() | Real CTO→team orchestration grounded in live read-only data | `server/anchor.py` `process()` | `e2e_anchor_live.py` | TECH §6 |
| A-181 | Deployed-anchor stand-in | Real HTTP `/anchor/v1` on chosen port backed by same queue; owns webhook delivery + retry sweep | `server/anchor_remote.py` | `python3 server/anchor_remote.py --port 9100` | CONTRACT Phase 2; TECH §12.4 |
| A-182 | Local HTTP poller | Mac pulls tasks from anchor over HTTP, runs orchestration, posts results; also syncs projects/pools/statuses/keys to anchor mirror | `server/local_poller_http.py` | `python3 server/local_poller_http.py --anchor http://localhost:9100` | CONTRACT; ISO (syncs continuously, no 502); NIGHT FINAL (11 projects / 14 pools / 12 keys every 4s) |
| A-183 | Durable anchor mirror | `/sync` push persisted and reloaded on startup; `/projects` returns `updated`, `age_seconds`, `stale` | `anchor_remote.py`; `data/anchor_sync.json` | live anchor GET | ISO root-cause fix (Jul 4); REQ #3 |
| A-184 | Anchor mirror read endpoints | `/anchor/v1/projects`, `/anchor/v1/pool/{id}`, `/anchor/v1/mirror/{key}` for projects, health, roles, company agents, connectors, activity, pools | anchor | — | REQ #2; ISO |
| A-185 | Supervised poller | Poller auto-restarts (proven back in 9s); wired into phase2/phase3 scripts | `poller_supervisor.sh $ANCHOR_BASE 4` | kill test | NIGHT VERIFIED-RUN 2026-07-20 |
| A-186 | Electron poller self-heal | Packaged app's `startPoller()` restarts poller 3s after crash unless quitting (`_pollerKilled`) — so `npm run dist` doesn't miss the poller | `desktop/electron/main.cjs` (backup `main.cjs.bak_poller`) | `node --check` | NIGHT 2026-07-20 ~05:50 (BUILT; node --check passes) |
| A-187 | Anchor landing page | Browser gets HTML, API gets JSON; opens only when anchor = yes | anchor | phase2 | REQ #10 |
| A-188 | Standalone anchor run | Run anchor alone for second-terminal drill | `anchor_up.sh` | `./anchor_up.sh` | REQ #5 |
| A-189 | Loop bridge (phase control) | Commands: health, send <project> <prompt>, tail <comp>, vm, redeploy, audit, auditfix, trace | `./anchor_loop.sh`; `logs/phase_ctl/CMD` | type command | ISO "Tools available" |
| A-190 | Chain trace | Traces desktop → anchor local → anchor public → Mac-external → web → nginx | `testing/trace_chain.py` | `trace` | ISO |
| A-191 | Deployed anchor + web (production) | `https://anchor.odinmarkets.com/odin-anchor` and `/odin-web`; nginx `odin-proxy`; Let's Encrypt; systemd service; odin_anchor DB linked | VM ports :48619/:48620 | production checker; prod e2e | ISO (proven public anchor + real round trip "46 orders"); NIGHT FINAL VERIFIED-RUN 2026-07-21 |
| A-192 | Anchor storage → PostgreSQL | Postgres store; big responses saved to `active_requests/<request_id>/<random>.json` with path in DB | anchor storage | needs `agent_terminal_bridge.sh` | REQ #16 (PENDING) |
| A-193 | Anchor Phase 3 containerisation | Dockerize anchor + systemd, TLS 443, web same-origin | — | — | TECH §8; RAI (PLANNED; systemd/TLS later live per NIGHT, Docker not recorded) |
| A-194 | External project API | `/api/v1` projects list + per-project ask | `server/external_api.py` | app | RAI Files |
| A-195 | Third-party simulator | Browser page + CLI to submit prompt to anchor | `third_party_sim.html`, `server/third_party.py` | `python3 server/third_party.py --anchor … --project … --prompt …` | TECH §7; RAI §4 |
| A-196 | Request page (sim server) | SQLite + response files; persists across refresh/close; ↻ Refresh statuses; ✕ delete; fast-ack feedback ("ACKNOWLEDGED"/"Anchor offline"); always opens | `server/sim_server.py` (port 9104) | "Tested end-to-end" | REQ #11–12 (live persistence confirm PENDING) |
| A-197 | Request page "Clear all" | Bulk clean request DB from a button | `sim_server.py` | — | REQ #17 (PLANNED) |
| A-198 | Webhook receiver page | Receives anchor webhook at `/cb`, viewer at `/` with Acknowledge button | `server/webhook_receiver.py` | `python3 server/webhook_receiver.py --port 9300` | TECH §11.1 |
| A-199 | Seed request | Seed via `anchor_seed.js`; sim seed 404 fixed (self-healing) | `anchor_seed.js` | stack run | NIGHT |
| A-200 | Async queue pattern | Unique ID + return URL; immediate ack (no wait/502); out-of-band work; retrievable by ID | anchor | — | REQ #13 |
| **Tests & harnesses** ||||||
| A-201 | Anchor E2E suites | Logic (queue/webhook/retry/fail), HTTP contract (+auth), live read-only data via CTO→team; runner | `server/e2e_anchor.py`, `e2e_anchor_http.py`, `e2e_anchor_live.py`, `e2e_anchor_all.py` | `python3 server/e2e_anchor_all.py` | CONTRACT DoD; TECH §12.2 (expected output shown; no dated run result recorded in these docs) |
| A-202 | Phase 2 topology E2E | `--smoke` fast plumbing; default real orchestration + real Klaviyo/Veeqo numbers | `server/e2e_phase2.py` | `python3 server/e2e_phase2.py [--smoke]` | CONTRACT Phase 2 DoD (checkboxes unticked) |
| A-203 | Desktop/backend E2E harness | Status, capabilities, creation location, smart team, no fake activity, agents+rules, models, scheduling, multi-level chat, voice, real-engine intake/memory/team-run; Azure read-only only; writes report | `tests/e2e.py`; `e2e-report.md` + `.json` | `npm run e2e` / `npm run e2e:quick` | LOG ADR-033; VERIFIED-RUN 2026-06-23 by owner (33 PASS, 1 FAIL, 1 WARN → fixed, re-run expected 35/35) |
| A-204 | Smoke test | Health, dashboard, mobile, chat, approval gate, voice | `scripts/smoke_test.sh` | `bash scripts/smoke_test.sh` | SETUP §3 |
| A-205 | Web online test | Web deploy test / rebuild | `test_web_online.py` | phase3 | ISO |
| A-206 | Desktop dev logging | Electron main, Python backend and React console all in terminal; DevTools auto-open (docked) | `npm run dev` (concurrently Vite + Electron, `ODIN_DEV=1`, `ELECTRON_ENABLE_LOGGING=1`) | `npm run dev` | DESK; LOG ADR-027, ADR-028 |
| **Integrations** ||||||
| A-207 | Klaviyo (Email) | Generic `call()` + wrappers (lists, campaigns, flows, metrics); read-only `flows_summary()` | `server/integrations/klaviyo.py`; env/cred `KLAVIYO_API_KEY`, `KLAVIYO_BASE_URL`, `KLAVIYO_API_REVISION` | Test Set A (`email-klaviyo`, "How many flows…") | TECH §2 (50 flows 28/22 cited); NIGHT live reads (16 profiles; later "Live 47 / Draft 3") |
| A-208 | Veeqo (Shipping) | Generic `call()` + wrappers (orders, shipments, create_shipment, carriers, current_user); read-only `orders_summary(since)` | `server/integrations/veeqo.py`; `VEEQO_API_KEY` | Test Set B (`shipping-veeqo`) | TECH §3 (26 orders); ISO VERIFIED round trip (46 orders since 2026-06-27) |
| A-209 | HubSpot connector | HubSpot service read via organics DB runtime_settings and HubSpot agent | `getHubspotConfig` (organics); HubSpot agent | agent-scope tests | TASK2; NIGHT (hubspot project clean in pass-6) |
| A-210 | Read-only integration testing | All integration tests are GET-only — never change accounts | integrations | — | TECH §3; RAI |
| A-211 | Email + Fulfillment project types | Email agent on email projects, Shipping agent on fulfillment projects | project types | — | TECH §2–3; RAI Phases |
| A-212 | Stripe checkout finalize idempotency (customer project) | After 3DS, finalize returns success if webhook captured order first; Stripe-only, Elavon untouched | organics checkout (customer code) | not stated | NEW "Other recent reliability fixes" |
| A-213 | Real Veeqo diagnosis (organics) | Read-only VM+DB diagnosis: order PAID, veeqo order id set but shipment id empty, decision window expired → root cause; single report | project `real-deployment-and-diagnosis-organics-07d7`; `VolatileWorkSpace/AI_DIAGNOSIS_REPORT.md` | S5–S8 run | TASK2 VERIFIED-RUN |
| **Rules, memory, history, ops** ||||||
| A-214 | Core rules (persistent memory) | Source of truth for business logic/ADRs, loaded before every task; billing placeholder §6.1; voice §6.2–6.3; Azure §5.1 | `rules/core-rules.md`; `workspace/shared/directions/core-rules.md` | — | README; AGENTS; FEAT #12 |
| A-215 | Audit history (human + machine) | HISTORY.md newest-first; log.jsonl append-only; entry types DECISION/BUILD/CHANGE/PROBLEM/SOLUTION/APPROVAL/SNAPSHOT/REVERT/NOTE (+VERIFY/FIX used) | `history/HISTORY.md`, `history/log.jsonl`, `history/daily/` | `cat history/HISTORY.md` | HIST; README |
| A-216 | Snapshots + revert | Restore points snap-0001…0006; revert takes a pre-revert snapshot first | `history/snapshots/`, `runbooks/revert.md` | follow runbook | SNAP1–6; SETUP §4E |
| A-217 | Pending backlog | Pending items revisited after every task | `PENDING.md` | — | HIST; FEAT #12 |
| A-218 | Live state files | progress/phases/features, tasks/owners, approvals for dashboard | `state/project.json`, `state/tasks.json`, `state/approvals.json` | dashboard | README; DASH |
| A-219 | Config files | Orchestrator settings/paths/gates; Odin Markets project profile | `config/system.config.json`, `config/project.config.json` | — | README |
| A-220 | Orchestrator operating manual | How the CTO Brain thinks/acts | `orchestrator/ORCHESTRATOR.md` | — | README |
| A-221 | Runbooks | deploy, ssl-certificate, security-scan, revert, approval-template, azure-secure-connection, mobile-access, phone-access | `runbooks/*.md` | — | SNAP1; HIST |
| A-222 | Design specs | Conversational cockpit spec (two-brain, SSE, activity log, artifact rendering, phases A–D); scoped memory spec | `design/CONVERSATIONAL-UX-SPEC.md`, `design/SCOPED-MEMORY-SPEC.md` | — | LOG ADR-013; 2026-06-22T02:00 |
| A-223 | Agent terminal bridge | Controlled terminal access the owner grants (Ctrl-C revokes); write CMD, read OUT.log; hang-proof (output to file, stdin detached, timeout watchdog) | `agent_terminal_bridge.sh`; `workspace/logs/agent_term/CMD`, `OUT.log` | run script | REQ #15; NEW reliability fixes; NIGHT "HOW TO RESUME" |
| A-224 | Clean dev-session control | Ctrl-C closes everything (brain, anchor, web, sim, webhook, desktop:5173); quitting mobile doesn't end session; no port spam | phase2 script | — | REQ #7–9 |
| A-225 | Local semantic memory | Read-only retrieval index over history/docs | — | — | RUFLO §3/§9; ADR-005 (PLANNED "later") |
| A-226 | Autonomous continuation (scheduled wakeups) | send_later loop for overnight autonomous work; all fired + disabled at end | scheduled tasks | — | NIGHT 02:18 + FINAL |
| **RedBerry Continuous SOC (project capability)** ||||||
| A-227 | Continuous SOC (monitor-and-report) | Multi-agent SOC: Observe → Correlate → Verify → Report → Approve; auto-remediation DISABLED; approval requests auto-denied in monitor/test mode | `workspace/projects/redberry-continuous-soc/` | scheduled run (2026-07-18 03:00) | SOC (VERIFIED-RUN report 2026-07-18; findings C0 H2 M4 L7 I4) |
| A-228 | SOC issue tracker across runs | New / still open / pending / accepted risk / resolved, auto-resolved when no longer detected | SOC | per run | SOC (13 open, 1 resolved) |
| A-229 | SOC checks catalogue | Service health, listeners, port hardening, multi-cloud surface (TLS/headers), endpoint health, clickjacking, SSH keys/users, persistence, crypto-miner hunt, newsletter abuse, DB anomaly, subscriber forensics, behavioural IDS, third-party quota, 24/7 sensor, OSV.dev dependency intel, KEV + abuse.ch intel | SOC agents | per run | SOC "All Checks" **[corrected: see §0.8 C-11]** |
| A-230 | ATT&CK threat hunt + prediction/prevention | Hypotheses tested vs evidence (supported/refuted/inconclusive); likelihood-ranked predictions with prevention | SOC report | per run | SOC |
| A-231 | Encrypted backups + smart recovery | Fernet-encrypted dated backups, key held on local desktop; recover-from-pre-problem logic; sha256 verify; restore approval-gated; narrowing rule | Recovery & Resilience agent | per run | SOC (3 backups, readiness ready) |
| A-232 | SOC 24/7 sensor | VM sensor events.jsonl; install approval-gated | `workspace/projects/redberry-continuous-soc/code/sensor/INSTALL_SOC_SENSOR.md` | install per doc | SOC (not installed); NIGHT FINAL (doc promoted to shared/utils) |
| A-233 | SOC scope growth + provider models | Recommends enrolling more projects; providers azure-vm (live), aws-ec2, godaddy, hostinger, cloudflare, static-cdn | SOC | — | SOC |
| A-234 | Plain-words + redaction | Human-readable summary first; secrets/2FA/tokens redacted | Reporting & Documentation agent | — | SOC footer |
| **Comparisons / analyses (decision inputs)** ||||||
| A-235 | Ruflo comparison verdicts | Adopt hooks, lean dispatcher, later semantic memory; reject swarm scale, self-evolving rules, stub tools, 3-runtime/federation | `RUFLO-COMPARISON.md` | — | RUFLO; ADR-005 |
| A-236 | Multi-agent gap analysis | MAST lens: shallow decomposition, raw-dump hand-off, no plan-completeness check, thin termination, multi-agent on sequential tasks | `AGENT-ARCHITECTURE-ANALYSIS.md` | — | ARCH (analysis; drives A-089..A-093) |
| A-237 | Voice analysis | Prototype's "Arabic" claim not backed by code; hybrid reuse/rebuild decision | `VOICE-ANALYSIS.md` | — | VAN; ADR-004 |
| **Builds / packaging / devices** ||||||
| A-238 | Desktop installable DMG | electron-builder mac dmg (appId ai.odin.orchestrator, productName Odin, unsigned, 1024px icon); thin shell that finds backend via ODIN_ROOT → saved userData root.txt → dev path → ~/Desktop default; spawns backend + poller | `desktop/package.json` build config, `build/icon.png`, `electron/main.cjs` (`backendRoot()`, `startPoller()`) | `npm run dist` → `desktop/release/Odin-1.0.0.dmg`; `npm run pack` → `release/mac/Odin.app` | DESK; LOG ADR-026/027 (BUILT; `node --check` + JSON valid); NIGHT FINAL: dist still an owner action |
| A-239 | Real iPhone install | App signed with dev team (id not copied), built, installed + launched on owner's iPhone with production profile (not simulator) | `odin_app` iOS | Xcode/flutter device run | NIGHT FINAL VERIFIED-RUN 2026-07-21 |
| A-240 | Mobile HTML cockpit (legacy) | Phone voice+chat page with persistent chats, chat menu, voice, token | `dashboard/mobile.html` | `http://<mac-ip>:8000/mobile.html` (LAN, uvicorn `--host 0.0.0.0`) | FEAT #10 "Basic"; VERIFIED-RUN 2026-06-21T14:00 (/mobile.html served) |

---

## 2. Owner rules and constraints (binding, as stated in these docs)

1. Never fake a response; "done/passed/deployed" only with real evidence (exit code, HTTP 200, file check). — CLAUDE "HOW TO OPERATE" + "TRUTH RULES"; NIGHT ("never fake done").
2. Work like a senior engineer: simple first → real reason → second solution → after same error 2–3x widen the scope → persist. — CLAUDE.
3. Interpret intent, not literal words; fix slips (reversed paths), fuzzy-match names, search wider before saying "not found". — CLAUDE; ADR-021.
4. Never ask interactive/menu questions in headless runs; act on the most reasonable reading and state the assumption in one line; "redo last X" = literal last thing. — CLAUDE; ADR-023.
5. Never claim "can't connect / SSH blocked / read-only mode / approve in permissions"; Odin handles connectivity. — CLAUDE.
6. Control plane (root) only for firewall; everything else as SSH user `mostafa`; never run app commands as root. — CLAUDE; TECH §4.
7. Always exclude secrets/backups from any sync even if not listed (`.backup-env`, `.env*`, `*.pem`, `*.key`, `*.bak`, `*.tmp`, `*.copy`, credential/oauth JSON). — CLAUDE.
8. Never read/print/copy/log `.env` or secrets. — CLAUDE.
9. Ports 80/443 are sacred; firewall rotation touches only port 22 single-IP; never `ufw reset/disable`. — CLAUDE; TECH §4.
10. Recovery is additive-only (`infra/ensure-connection.sh`). — CLAUDE.
11. Tests sandbox-isolated (`_e2e_sandbox`, `organics_e2e_sandbox`, no reboot); prod deploy guarded by `ODIN_ALLOW_PROD_DEPLOY=1`. — CLAUDE.
12. Attached source folders are read-only unless explicitly asked; change only what was asked. — CLAUDE; NEW ⑩.
13. Build only inside the project's `localPath`; never at the Odin repo root; ask if none. — CLAUDE.
14. READ-ONLY by default; no state change (deploy, scp, git pull/push, systemctl, rm, mv, writes, installs, firewall, migrations, rebuilds) without explicit approval; system "not rigid enough yet to touch the running websites" — all running sites are PRODUCTION. — CLAUDE; FEAT parked items.
15. Approval protocol: reads run immediately, never ask approval for a read; changes → command + impact + rollback + "Approve?" then stop; on "approved" execute and show result. — CLAUDE; ADR-019.
16. Migrations: `prisma migrate deploy` only; `migrate dev/reset` never without explicit approval; deploy config never silently set back to reset; DB reset only first deploy, later ask. — CLAUDE; NEW ⑩.
17. Deploy playbook defaults: never touch node_modules; never production `.env`; remove destination before rebuild; rebuild both; restart via systemd not npm start; prefer service restart over reboot; ask about public/upload/logs; npm install only on real dep change. — CLAUDE; LOG 2026-06-23T09:00.
18. Folder mapping never crossed: frontend → `~/organics`, backend → `~/Bendcore`/`~/bendcore`. — CLAUDE; TECH §4.
19. Deploy is pipeline + brain; after deploy the checker must confirm online (HTTP 200) before reporting success. — CLAUDE.
20. Be fast: batch VM calls into one script; never scan large/generated dirs. — CLAUDE.
21. Style: answer first in the first sentence; brief; no repeated caveats. — CLAUDE.
22. Security & Compliance holds veto over sensitive-data changes; all agents read core-rules and operate behind the approval gate. — AGENTS.
23. Rules change only via explicit, logged, approved edits — no self-evolving rules (fintech). — RUFLO §3.
24. Custom billing model must not be assumed (placeholder until owner specifies). — HIST 2026-06-20; LOG core-rules#6.1.
25. Audio must stay on-device (privacy/fintech); voice never uses the OS voice on desktop. — VAN; DESK; ADR-009.
26. Voice is a core accessibility requirement; on-screen text always kept; no audio stored/synced; desktop voice pipeline untouched by web/mobile voice work; "enhanced voice via anchor/XTTS" shelved. — WMV A0.
27. Keep the mic button on both web and mobile; mic must never hit the backend. — WMV A4.
28. Owner wants "all phases, full implementation, no omit/simplify/postpone". — LOG ADR-025.
29. Owner wants a real installable .dmg (drag to Applications, pin, double-click), plus `npm run dev` for testing and `npm run dist` only for the final installer. — LOG ADR-026/027.
30. Fix the system generically, "not case by case" (no keyword/sentence patches); scope is a reasoning capability. — LOG ADR-024; NIGHT "MAJOR REFRAME".
31. Scope: answer intuitively from THIS project's data; never cut knowledge ("must still know his father"); owner never blocked or asked approval (even out-of-scope); clarify only on genuine ambiguity; external out-of-scope + insist → owner approval; a read is never proposed/gated; owner seeing an approval on a read = violation. — NIGHT 02:05–03:35.
32. Quality bar ranking: direct correct answer (best) > one clarifying question on genuine ambiguity > wrong-scope answer (bad) > "I can't"/proposal blocking a read (worst). — NIGHT 02:18.
33. Guide/reasoning test must show ZERO violations from a clean first pass across every non-protected project, plus structural/DB audit zero — no bending the test. — NIGHT 07:30 + "OWNER FINAL STOP CRITERIA".
34. Don't re-run the full development checker repeatedly; work in background via the bridge / one server instance. — NIGHT 02:30.
35. Never touch/run the customer `organics-prod-deploy` project. — NIGHT.
36. Middleware must not add delay per response (no extra LLM call; compact prompt). — NIGHT 08:20.
37. Stop criteria order: zero → delete 4 test projects (keep 11) → production checker exit 0 → deploy with owner go at exact command → autostart → confirm poller + dist keeps poller → stop scheduling, honest report. — NIGHT 09:00.
38. Deploy authorization: initially "do NOT deploy", later reversed ("DEPLOY IS NOW AUTHORIZED") with owner go at the one irreversible command. — NIGHT 02:18 vs 03:35.
39. Desktop must not be affected by web/mobile work (new desktop features only when explicitly requested). — REQ Notes; WMV.
40. Phase 3 paused until Phase 2 fully confirmed (at time of REQ). — REQ Notes.
41. Isolate the failing point (web render); don't re-debug the proven backend or rerun the whole system to test. — ISO.
42. Integration tests are read-only (GET only). — TECH §3; RAI.
43. Rotate any key shared in plaintext before real/remote exposure. — RAI; TECH §9/§13.
44. Discussion-before-confirming-prompt default: run intake but allow skip with one click (proposed default, awaiting owner confirmation). — CONV §4.
45. Keep "fewer but real" tools; reject swarm scale. — RUFLO §9; ADR-005.
46. Web/mobile UI: speaker icon must not displace existing header items; keyboard must be dismissible; verify on real iPhone. — WMV.
47. Agent scope: read-only, delta-first credentials, non-blocking; external outputs to a single file; final report = only the real issue. — TASK2.
48. SOC is monitor-and-report only; remediation approval-gated; the system never changes anything on its own. — SOC.

---

## 3. Open / pending / known-broken items

| # | Item | Source |
|---|---|---|
| P-01 | Mobile / phone-terminal connection "owner kept this pending" (later superseded by Flutter app + real iPhone install) | FEAT "Still parked" |
| P-02 | Turnkey one-click VM deploy intentionally left as gated proposal | FEAT |
| P-03 | Custom billing/subscription model is a placeholder (core-rules §6.1) | HIST 2026-06-20; SETUP |
| P-04 | Main-Task conversion phases A–E (main_task.py, requirements gate, mandates, write-back loop, Main-Task verification) not built; owner confirmation on skippable discussion pending | CONV §3–4; ARCH §6 |
| P-05 | ADR-031 partials list: auto file-gen on create, member tools-in-use live detail, project-level model picker UI, view member chats from project page, self-healing automation, suggest-agent-on-pattern, speaking animation (some later closed by ADR-033/036) | LOG ADR-031 |
| P-06 | ADR-032: strategic→PM→member monitoring UX incomplete; strategic dashboard discussion not done | LOG ADR-032 |
| P-07 | ADR-035 pending: full intervention loop; deeper multi-turn discussion + explicit QA test-and-bug-report step | LOG ADR-035/036 |
| P-08 | Periodic-agent cross-agent delegation is engine-guided, not hard-wired; attachments pass paths not binary | LOG ADR-039 |
| P-09 | E2E re-run to confirm 35/35 after fixes — expected, not recorded | LOG ADR-034 |
| P-10 | Anchor Phase 1 DoD and Phase 2 DoD checklists are unticked in the contract doc (no recorded pass there) | CONTRACT |
| P-11 | Offline→online drill on web + mobile with latest fixes; request page persistence in live run — "PENDING your run" | REQ |
| P-12 | Anchor storage → PostgreSQL with large responses as files — needs terminal bridge | REQ #16 |
| P-13 | Request page "Clear all" button — to build | REQ #17 |
| P-14 | Anchor landing "Manage" protected area (login + code + remember device + CRUD + mobile/web allow toggles) — to build | REQ #18 |
| P-15 | Desktop "Connecting with Anchor" blinking code indicator — to build | REQ #19 |
| P-16 | Web/mobile enhanced voice (normalizer, on-device Kokoro/sherpa, speaker in both modes, mic EN/AR) — PENDING | WMV Part A |
| P-17 | KNOWN BUG: mic "returns the previous message" in `chat_screen.dart._mic()` | WMV A4 |
| P-18 | KNOWN BROKEN: `whatsapp.dart` mic record→upload path hard-blocked in anchor mode ("backend is not reachable — this must go through the anchor"); speaker toggle missing in chat mode | WMV A3/A4 |
| P-19 | KNOWN BROKEN (HIGH-PRIORITY BLOCKER): mobile keyboard never dismisses; stray `autofocus` (whatsapp.dart ~105, shell.dart ~391) | WMV Part B |
| P-20 | Known issue: file/photo attachments through the anchor (same upload limitation) — out of scope | WMV non-goals |
| P-21 | ISO (Jul 4): web stuck at "connecting to your machine…" and mobile `ApiException(404)`; fixes in code; next suspected cause CORS/preflight; Mac Phase-3 loop was closed at the time | ISO (later production live per NIGHT FINAL) |
| P-22 | External out-of-scope + insist → `approvals.create()` to owner — listed STILL PENDING; no completion recorded | NIGHT |
| P-23 | Owner action remaining: run `npm run dist` to build the .dmg | NIGHT FINAL |
| P-24 | Anchor Phase 3 items: Docker containerisation, HMAC-signed webhooks, per-device tokens, rotated strong keys, real caller HTTPS webhook URLs | TECH §8/§13; RAI |
| P-25 | Test API key values for anchor/odin are printed in plaintext in TECH §9/§11 — must be rotated | TECH §9 |
| P-26 | Local semantic memory (read-only retrieval) — later | RUFLO; ADR-005 |
| P-27 | snap-0006 "Next": IP rotation needs NSG + SSH-rule names; .env-safe deploy; wire VM commands into cockpit (largely addressed later) | SNAP6 |
| P-28 | TASK2: deploy-on-modify not triggered because organics code intentionally unmodified (by design) | TASK2 |
| P-29 | Stale docs: SRV/SETUP/VRD still describe Piper/macOS Maged Arabic TTS and Ollama-as-brain; superseded by Coqui XTTS (ADR-012) and Claude CLI (ADR-014); FEAT #7 says mic = browser Web Speech while ADR-037 says Whisper-only | SRV; SETUP; FEAT vs LOG |
| P-30 | SOC open findings: 13 open (2 high: endpoint health organics-api unreachable, dependency vulns 36 pkgs/18 runtime-reachable incl. next/axios); missing HSTS on anchor domain; SSH probe from SOC timed out (data unavailable for most host checks); 24/7 sensor not installed; Cloudflare/WAF recommended; enrol Revealer and Egypt Amazon content agent | SOC |
| P-31 | TECH doc file `docs/ODIN_PHASES_TECH_DOC.pdf` referenced as companion (existence not verified here) | TECH header |
| P-32 | Server is local-only/unauthenticated by design; add auth before any network exposure; voice loop is record→stop→process (not streaming) in v1 | SRV notes |
| P-33 | Phone mic needs HTTPS (blocked on plain http LAN) | SETUP §4D/§7 |

---

## 4. Clients and build targets

| Client / target | What it is | How the docs say to run / build | Status per docs |
|---|---|---|---|
| **Brain / local server (FastAPI)** | `server/app.py` on :8000 — dashboard, chat, SSE, chats, voice, infra, `/api/v1`, `/scope`, `/projects`, anchor routes | One-time: `python3.12 -m venv .venv`, `pip install -r server/requirements.txt`, `pip install -r voice/backend/requirements-voice.txt`; run `USE_VOICE=1 ./server/run.sh` (or `bash server/run.sh`; `PORT=8010` if busy); LAN: `uvicorn server.app:app --host 0.0.0.0 --port 8000` with `ODIN_ACCESS_TOKEN`; env `ODIN_RELOAD=1`, `ODIN_HOST` | Live; verified boots/health 200 (2026-06-21) |
| **Static / legacy dashboard** | `dashboard/index.html` (+ Voice Console), `console.html` cockpit, `mobile.html`, `audit.html`, `meeting_monitor.html` | Double-click `index.html` (snapshot) or `python3 -m http.server 8080` → `/dashboard/index.html`; served by brain at `http://localhost:8000/` | Live (old console at `/`) |
| **Live Cowork artifact dashboard** | Persistent dashboard re-openable across sessions, accessible from Claude desktop + mobile apps | Ask "open the Odin dashboard" | Described |
| **Desktop app — Electron + React + Vite + Framer Motion** | `desktop/` (`src/App.jsx`, `views.jsx`, `ChatPanel.jsx`, `ui.jsx`, `api.js`, `electron/main.cjs`, preload) — the original rich cockpit; no login | `cd desktop && npm install`; dev: `npm run dev` (hot reload, all logs in terminal, DevTools, backend auto-start; `USE_VOICE=0 npm run dev` for faster start); alt `npm run start`; tests `npm run e2e` / `npm run e2e:quick` | Built; dev verified bundles/compiles |
| **Desktop DMG build** | Unsigned macOS installer `desktop/release/Odin-1.0.0.dmg`; or `release/mac/Odin.app` | `npm run dist` (vite build + `electron-builder --mac dmg`); `npm run pack` for .app only; first open: right-click → Open; update = re-run dist and replace; backend located via `ODIN_ROOT`/userData/dev path/~/Desktop; spawns backend + self-healing poller | Build config done (ADR-026); final `npm run dist` is an outstanding owner action (NIGHT FINAL) |
| **Flutter app — web (odin-web)** | `odin_app/` web build, "Remote Anchor · Web"; login required | `flutter create . --platforms web,android,ios --project-name odin_app --org com.odin`; `git checkout -- lib/`; `flutter pub get`; `flutter run -d chrome`; served at `http://localhost:8080` by phase2 (release build, no-cache); production at `https://anchor.odinmarkets.com/odin-web` (VM :48620) via production checker; troubleshoot `tail -n 40 logs/app_web.log` | Production live 2026-07-21 (NIGHT FINAL); earlier render hang fixed in code (ISO) |
| **Flutter app — mobile / iPhone** | Same codebase, mobile layout; login + Face ID first access; Android also a target | `flutter run -d <ios-device-id>` (needs Xcode) / `<android-device-id>`; iOS Info.plist mic/speech/camera/photo keys; on a phone set base URL to Mac LAN IP (direct) or Deployed profile (anchor); phase2 opens iOS simulator | Real iPhone signed, built, installed + launched with production profile (VERIFIED 2026-07-21); keyboard + voice items pending (WMV) |
| **Mobile HTML cockpit (legacy)** | `dashboard/mobile.html` phone voice+chat with token | Bind LAN, open `http://<mac-ip>:8000/mobile.html`, paste token; remote via Tailscale/Cloudflare tunnel (`runbooks/phone-access.md`) | Basic; served verified 2026-06-21 |
| **Anchor (local stand-in)** | `server/anchor_remote.py` on :9100 (queue + auth + webhooks + mirror) | `python3 server/anchor_remote.py --port 9100`; `./anchor_up.sh`; `./anchor_loop.sh` + `phase3` | Working locally (ISO proven) |
| **Anchor (production)** | Deployed on Azure VM :48619 behind nginx 443 at `https://anchor.odinmarkets.com/odin-anchor`, Let's Encrypt, systemd | `ODIN_PHASE3_YES=1 bash shells/phase3_up.sh` (now `production_full_checker.sh`); `phase3_gate validate` | Live, health 200, prod e2e PASS (2026-07-21) |
| **Local poller** | `server/local_poller_http.py` — Mac ↔ anchor over HTTP; supervised | `python3 server/local_poller_http.py --anchor <url>`; `poller_supervisor.sh $ANCHOR_BASE 4`; also spawned by Electron | Syncing 11 projects / 14 pools / 12 keys every 4s (2026-07-21) |
| **Request page / third-party sim** | `server/sim_server.py` (:9104, SQLite) + `third_party_sim.html` + `server/third_party.py` | CLI `python3 server/third_party.py --anchor … --project … --prompt …`; open html | Tested end-to-end (REQ #11) |
| **Webhook receiver** | `server/webhook_receiver.py` (:9300) | `python3 server/webhook_receiver.py --port 9300`; open `http://localhost:9300/` | Described |
| **React desktop client (voice hook)** | `voice/frontend/useVoice.ts` React hook for chat input (EN/AR) | import `useVoice` | Built (extracted module) |
| **One-command stacks** | Development: `development_full_checker.sh` (ex `phase2_up.sh`) — brain + anchor + poller + desktop + web + iOS sim + keys; Production: `production_full_checker.sh` (ex `phase3_up.sh`) | `./phase2_up.sh` (`OPEN_DESKTOP=0` to skip desktop); Ctrl-C stops all | Renamed + `bash -n` OK (2026-07-21) |


<!-- ==================== PART B ==================== -->

# Inventory B — Directions / Infra / Runbooks / Testing (Odin-Orchestrator v1)

Source: `_phase1_bundles/B2_directions.txt` (2757 lines, 41 source files, read in full).
Evidence key: **VERIFIED-RUN** = a recorded run with date + result; **DOC-ONLY** = described as built/rule but no run recorded in this bundle; **PLANNED/PENDING/PLACEHOLDER** as stated. Secret values are never copied; only key names (e.g. `azvmcred`, `VEEQO_API_KEY`) appear.

## 1. Master feature table

| ID | Feature | Description | Where it lives | How run/tested | Evidence |
|---|---|---|---|---|---|
| B-001 | CTO Brain 10-step loop | Understand → Load rules → Assess → Plan → Clarify → Gate → Execute → Verify → Log → Report; never skip step 2 or 6 | `directions/ORCHESTRATOR.md` §My loop; `skills/odin-cto-brain/SKILL.md` | not stated | ORCHESTRATOR.md; DOC-ONLY |
| B-002 | Agent trigger routing table | Request keywords map to Frontend/Backend/DevOps&Cloud/Security&Compliance/QA&Testing/Database | ORCHESTRATOR.md §When I activate; SKILL.md §Specialized agents | not stated | DOC-ONLY |
| B-003 | Security & Compliance veto | Security agent has veto on anything touching sensitive data | ORCHESTRATOR.md; `utils/security-and-compliance.md`; SKILL.md | not stated | DOC-ONLY |
| B-004 | Deterministic dispatcher | Lean router classify→load-rules→approval-check→hooks→route (not a swarm) | `orchestrator/dispatcher.py` | `POST /dispatch` returns agents, approval requirement, hooks | ORCHESTRATOR.md; core-rules ADR-008; DOC-ONLY |
| B-005 | Chat/voice answer via dispatcher | `/chat` and voice loop answer through dispatcher so approval gate applies on every channel incl. voice/mobile | `server/app.py`, dispatcher | `POST /chat` | ORCHESTRATOR.md; ADR-008; e2e-report 2026-06-23 checks engine via /health (VERIFIED-RUN 45/45) |
| B-006 | Routing telemetry | Routing decisions appended to JSONL, kept out of main audit log | `history/routing.jsonl` | not stated | ADR-008; DOC-ONLY |
| B-007 | Pluggable sub-agent interface | Real sub-agents plug in behind same dispatcher interface without changing server/UI | dispatcher | not stated | ORCHESTRATOR.md; DOC-ONLY |
| B-008 | Approval gate (mandatory) | Actions in `approvalGate.requiresApprovalFor` need an approval request; system stops until owner YES | `config/system.config.json`; `approvals/pending/` | not stated | ORCHESTRATOR.md; ADR-002; DOC-ONLY |
| B-009 | Approval request contents | What (exact commands), Why, Impact/blast radius, Risk level, Rollback, Approval line | `runbooks/approval-template.md` | not stated | ORCHESTRATOR.md §Approval Gate |
| B-010 | Approval lifecycle folders | pending → approved (sign-off) / rejected (reason); logged to HISTORY.md + log.jsonl | `approvals/pending|approved|rejected/` | not stated | approval-template.md footer; DOC-ONLY |
| B-011 | Approval template APR-NNNN | Request ID, date, requester, category, 6 sections, owner decision checkboxes | `runbooks/approval-template.md` | not stated | DOC-ONLY |
| B-012 | Approval categories | code-change, config-change, azure-vm-action, deployment, ssl-certificate, security-scan-active, database-migration, production-data-access, dependency-install, secret-change | approval-template.md | not stated | DOC-ONLY |
| B-013 | Example approval APR-0000 | Illustrative SSL renewal request (certbot renew + nginx reload hook), not live | `utils/approval-template.md` | not stated | Explicitly "EXAMPLE, not a live request" |
| B-014 | Long-term rules memory | core-rules.md is memory of custom logic; new requirements appended dated | `directions/core-rules.md` | not stated | ORCHESTRATOR.md §memory |
| B-015 | History/audit log | Every significant action → line in log.jsonl + entry in HISTORY.md; daily journals | `history/log.jsonl`, `history/HISTORY.md`, `history/daily/` | not stated | ORCHESTRATOR.md; DOC-ONLY |
| B-016 | Snapshots / revert | Named restore points `snap-NNNN-<slug>`; restore is approval-gated; pre-revert snapshot always taken | `history/snapshots/`; `runbooks/revert.md` | not stated | DOC-ONLY |
| B-017 | Structured reporting style | Each turn: plan, decisions, risks, ready-to-test, single next decision | ORCHESTRATOR.md §communication | not stated | DOC-ONLY |
| B-018 | Revisit PENDING after every task | Brain ends each task by reminding owner of PENDING.md items | SKILL.md §On finishing; PENDING.md header | not stated | DOC-ONLY |
| B-019 | Streaming cockpit + persistent chats | Dashboard cockpit with persistent chats/memory; sidebar new/rename/delete | dashboard, server | e2e-report "Real engine answers + keeps chat memory across turns" | PENDING.md Done; VERIFIED-RUN 2026-06-23 PASS |
| B-020 | Voice EN (Kokoro) + AR (Coqui XTTS-v2), offline | Local TTS; browser speech mic | `voice/`, `/voice/tts`, `/voice/stt` | e2e-report "TTS endpoint returns audio (EN)" HTTP 200 | PENDING Done; CONVERSATIONAL-UX-SPEC §C "accepted by owner"; VERIFIED-RUN 2026-06-23 |
| B-021 | Claude CLI = engine | Claude Code is core engine; Ollama is fast front/fallback; ODIN_ENGINE=claude | `server/claude_cli.py` | e2e-report "Engine is Claude CLI" PASS | core-rules §6.4; VERIFIED-RUN 2026-06-23 |
| B-022 | Mobile access + token gate | `dashboard/mobile.html`; `ODIN_ACCESS_TOKEN` gates /chat,/dispatch,/voice/*,/chats | `dashboard/mobile.html`; server | runbooks mobile-access / phone-access commands | ADR-008; PENDING Done (basic); DOC-ONLY |
| B-023 | Azure VM read-only inspection | django-vm / DJANGO-PROJECT inspected via `az vm run-command` | Azure CLI on Mac | e2e-report "Azure connect-test is READ-ONLY" PASS | PENDING Done; VERIFIED-RUN 2026-06-23 |
| B-024 | Scoped multi-agent org | company→project→member pools, upward sync, drill-down | `server/scopes.py`, `server/api_v2.py` | e2e-report chat at scope company/project/member PASS | PENDING Done 2026-06-22; VERIFIED-RUN 2026-06-23 |
| B-025 | Premium desktop app | Electron+React+Vite+Framer Motion | `desktop/` | "React bundle compiles" | PENDING Done 2026-06-22 (FEATURES.md rows 13–23 referenced, not in bundle) |
| B-026 | Projects/agents/model/scheduling/mapping/sync-deploy proposals | Built and verified per PENDING | server modules | "Backend smoke + route + regression tests PASS" | PENDING Done 2026-06-22; claim only |
| B-027 | Mapped VM apps comparison | Read-only comparison: `~/organics` (Next.js), `~/bendcore` (NestJS+Prisma), both have .env, not git repos; profile casing fixed to lowercase | PENDING Parked notes | not stated | PENDING.md; DOC-ONLY |
| B-028 | Agent terminal bridge | Mac-side bridge; write command to CMD file, read `.run_out`/`OUT.log`; STATUS READY/RUNNING/IDLE/STOPPED | `shells/agent_terminal_bridge.sh`; `workspace/logs/agent_term/` | `bash shells/agent_terminal_bridge.sh`; verify with unique echo MARKER in OUT.log | PHASE7-HANDOFF; VEEQO handoff §8; known stale-CMD issue |
| B-029 | Running services baseline | brain :8000, anchor :9100, poller; host python `.venv/bin/python` | PHASE7-HANDOFF header | not stated | DOC-ONLY |
| B-030 | Role statement: make the app smart | Fix origin in owner's code; proof from his audit, never assistant assertion | PHASE7-HANDOFF §0 | not stated | Owner rule |
| B-031 | PROTECTED_PROJECTS | Production organics-prod-deploy/bendcore/organics excluded from audit/heal and tests | `server/workspace_audit.py` | Phase 7 runs excluded prod | PHASE7-RESULTS/RUN2: production untouched (VERIFIED-RUN 2026-07-19) |
| B-032 | Generic engine + per-project delta | Shared scripts know nothing project-specific; per-project paths/VM/DB/ports under `projects/<pid>/deploy/` | `workspace/projects/<pid>/deploy/` | not stated | PHASE7-HANDOFF §1 |
| B-033 | provision_capability | System generates a project's deploy delta (not hand-written) | `server/workspace_mw.py::provision_capability` | Hand-written delta deleted → regenerated → deploy green | PHASE7-HANDOFF §2 VERIFIED (date ~2026-07-19 handoff) |
| B-034 | Owner-scoping write guard | `put_file(actor=)` enforces owner scoping | `workspace_mw.put_file` | phase7_strong | PHASE7-HANDOFF §3 |
| B-035 | promote_to_shared | Moves duplicated functionality to shared and repoints | `workspace_mw.promote_to_shared` | phase7 suites | PHASE7-HANDOFF §3 |
| B-036 | repoint_reference / add_dependency / customize_shared / resolve_capability | Middleware helpers for dependency pointers and custom delta | `server/workspace_mw.py` | phase7 suites | PHASE7-HANDOFF §3 |
| B-037 | create_owner / delete_owner | FK-safe owner create/delete; link rows cleaned | `workspace_mw.py` | phase7_lifecycle | PHASE7-HANDOFF §3 |
| B-038 | Workspace audit detections | misplaced / unindexed / duplicate / foreign-ref detection + heal at source | `server/workspace_audit.py` | `open_issues` count | PHASE7 VERIFIED-RUN 2026-07-19 open_issues=0 |
| B-039 | Bidirectional audit (DB→disk orphans) | Added orphan detection + heal; cleaned 2 stale rows first run | `workspace_audit.py` | independent sweep db_orphan=0 | PHASE7-RESULTS origin fix #2; VERIFIED-RUN 2026-07-19 |
| B-040 | Agent registration contract audit | `agent-incomplete` / `agent-invisible` / `agent-unregistered` raised by scan | `workspace_audit.scan` | not stated | PHASE7-RESULTS addendum 2026-07-30; WORKSPACE-SCHEMA §3; DOC-ONLY |
| B-041 | register_agent / remove_agent | Upsert COMPLETE agents row + project_agents link; remove drops link + orphan row | `agents_registry.register_agent/remove_agent` | not stated | Addendum 2026-07-30 (prod code); earlier claim was test-only |
| B-042 | Roster from DB | `all_agents` and `/agents/all` read the DB | `agents_registry`, `/agents/all` | `GET /agents/all` | Addendum 2026-07-30 |
| B-043 | UI API | `/ui/projects|agents|types|connectors`, type and agent driven controls, pagination | `server/ui_api.py` | endpoints named | PHASE7-HANDOFF §3 |
| B-044 | Generic change detector | `--project <pid>`, per-project baselines | `workspace/shared/infra/deploy_changes.py` | `scan`/`changed`/`seed-old`/`update` | PHASE7-HANDOFF §3; DEPLOY-PROMPT Step 0 |
| B-045 | deploy.sh engine | Verify port from delta, empty-services skip, logs to `workspace/logs/`, baseline update gated on verification | `workspace/shared/infra/deploy.sh` | `bash infra/deploy.sh` | Revealer deploy 18 ok/0 warn/0 fail (PHASE7-HANDOFF §2) |
| B-046 | Revealer sandbox mirror | Own DB, ports 4113/3112 (200), no domain, systemd user units revealer-be/revealer-fe | VM sandbox | deploy.sh | PHASE7-HANDOFF §2 VERIFIED |
| B-047 | Production health snapshot | organics :3012→200, bendcore :4013→200 | VM | not stated | PHASE7-HANDOFF §2 |
| B-048 | Seed connectors | Seeds 5 connectors: hubspot, klaviyo, veeqo, claude-cli, az-cli | `seed_connectors.py` | not stated | PHASE7-HANDOFF §3,§6; DB connectors 5 |
| B-049 | UI requirements (Electron main) | Desktop/web/mobile render from same `/ui` payload; buttons from type+agents+connectors; recurring shows run/play; Reporting agent adds export; dashboard landing-only | Desktop/web/mobile | "verify on real surfaces" | PHASE7-HANDOFF §6; requirement |
| B-050 | Phase 7 real runs (8 projects) | Triggered ▶ Run, watched to real output, audited | `phase7_realrun.py` | `.venv/bin/python workspace/shared/testing/phase7_realrun.py` | RUN1 2026-07-19 7/8 first pass; RUN2 8/8 total 369.0s |
| B-051 | Prompt-create 4 new projects | create → run → strong acceptance → clean delete | `phase7_prompt4.py`, `phase7_prompt_loop.py` | `.venv/bin/python workspace/shared/testing/phase7_prompt_loop.py` | RUN1 0/4→4/4; RUN2 4/4 first pass (2026-07-19) |
| B-052 | Scheduler persists deterministic runs | Operator runs persist result as project scope message | `server/scheduler.py` | hubspot run 32.3s real data | Origin fix #1 VERIFIED-RUN 2026-07-19 |
| B-053 | project_agents link on create (+broadened infer_team) | Agents appear on cards; mixed brief → 5 agents | `workspace_mw.py`, `agents_registry.py`, `projects.py` | phase7_prompt4 | Origin fix #3 (later found test-only; fixed in prod 2026-07-30) |
| B-054 | Clean delete purges run scopes | Deletes `chats/scopes/project__<pid>/…`; one-time sweep removed 107 orphaned scopes | `workspace_mw.py` | lifecycle exact baseline | Origin fix #4 VERIFIED-RUN 2026-07-19 |
| B-055 | Create reuses shared deploy | Deploy-intent prompt auto-wires shared deploy engine (pointer + delta) | `server/projects.py` | Project D Sandbox Deploy Mirror | Origin fix #5 VERIFIED-RUN 2026-07-19 |
| B-056 | Independent audit cross-check | Separate sweep not using audit logic: unindexed/db_orphan/cross_owner | phase7 harness | sweep results 0/0/0 | VERIFIED-RUN 2026-07-19 RUN1+RUN2 |
| B-057 | Phase 7 DB state | projects 9, agents 28, project_agents 32, files 609, connectors 5, 0 orphans | odin_core | not stated | PHASE7-RESULTS final gate |
| B-058 | Modularization program gating | Phases one at a time; X+1 only after owner confirms X; scheduler holds queue | `directions/ROADMAP.md` | not stated | Rule |
| B-059 | Roadmap Phase 0 type system | 16-entry project skeleton, 8-entry agent skeleton, owner `type`+`typeConfig` | ROADMAP §Phase 0 | "0 gaps, no stray root folders" | ROADMAP: ✅ DONE (no date). Note conflict: WORKSPACE-SCHEMA says 9 project entries |
| B-060 | Roadmap Phase 1 odin_core schema | One table per subfolder type + files metadata table; FK relations; no content | Postgres `odin_core` | "test query walks project→agents→shared" | ROADMAP; status not marked |
| B-061 | Roadmap Phase 2 seed | Every file indexed with agentic-friendly short description | odin_core | spot-check queries | ROADMAP; not marked |
| B-062 | Roadmap Phase 3 middleware single door | Create/update/delete places file, writes row, blocks violations | middleware | deliberately misplaced create corrected | ROADMAP; implemented per PHASE7 (workspace_mw) |
| B-063 | Roadmap Phase 4 Directions live view | Entrypoint read first; live view over odin_core | directions | "I need to deploy X" query | ROADMAP; not marked |
| B-064 | Capability-reuse advisory | Ask directions if capability exists/matches; forbid deploy_2 duplicates; overlay delta `mode: extend|subset|override` in `dependencies/manifest.json` | directions + dependencies | not stated | ROADMAP Phase 4 (MUST) |
| B-065 | Roadmap Phase 5 debounced audit/observer | Watches new json/md/code/shell/py excluding core-app folders; silence gap 30–60 min; fixes at source; promote ≥2 projects to shared; own UI tab with run-now/violations/enable/interval | audit | not stated | ROADMAP; UI tab not evidenced |
| B-066 | Roadmap Phase 6 UI adaptation | Data-driven cards via array.map; type-driven controls (recurring→play, vertical→timeout, features→icons); anchor sync | clients | not stated | ROADMAP; partially per PHASE7 §6 |
| B-067 | Roadmap Phase 7 non-prod testing | One test per project using shared capability; create/delete 2–3 new; exclude prod | testing | phase7 suites | VERIFIED-RUN 2026-07-19 |
| B-068 | Roadmap Phase 8 env + prod shell tests | Adapt `shells/phase2_up.sh` and `shells/phase3_up.sh` | shells | not stated | PLANNED (later) |
| B-069 | Structuring plan passing points | Each phase DONE only at 100% green; revert if red | `directions/STRUCTURING-PLAN.md` | not stated | Rule |
| B-070 | Standing guardrails (structuring) | archive rollback, additive/reversible, external deploy targets referenced only, shared chat pool untouched, cards must match, nothing deleted until replacement proven | STRUCTURING-PLAN | not stated | Rule |
| B-071 | SP Phase 0 baseline harness | Golden snapshot of status/run output, endpoints, card JSON; replay harness | STRUCTURING-PLAN | not stated | PLAN (status not recorded) |
| B-072 | SP Phase 1 structure projects | Target layout app/projects/agents/chats/connectors/shared/external-refs | STRUCTURING-PLAN | run everything | PLAN |
| B-073 | SP Phase 2 strong E2E of structuring | Rerun each project's tasks, monitor via bridge | STRUCTURING-PLAN | not stated | PLAN |
| B-074 | SP Phase 3 registry seed post-structure | Ref for every on-disk file, 1:1 | STRUCTURING-PLAN | seed test | PLAN |
| B-075 | SP Phase 4 tight middleware + write-guard | Rejects workspace write lacking a ref; delete folder then ref | STRUCTURING-PLAN | not stated | PLAN |
| B-076 | SP Phase 5 middleware hard test | Create/delete/recreate; zero orphans/strays | STRUCTURING-PLAN | not stated | PLAN |
| B-077 | SP Phase 6 CTO short-path anti-hallucination | CTO plans from schema, reuses agents; measure speed | STRUCTURING-PLAN | not stated | PLAN |
| B-078 | SP Phase 7 lazy loading + sync + notifications | Short payload cards, full lazy-load, anchor/web/mobile sync, instant approval notify; measured gain | STRUCTURING-PLAN | not stated | PLAN |
| B-079 | Placement decision Q1/Q2 | Scope then type → unique destination | `directions/WORKSPACE-SCHEMA.md` §1 | not stated | Rule |
| B-080 | Canonical project skeleton | index.json, rules.md, agents.json, docs/, files/, jsons/, approvals/, scripts/, deploy/ (empty kept) | WORKSPACE-SCHEMA §2 | audit | Rule |
| B-081 | Canonical agent skeleton | index.json, capability.md, handoff.json + instructions/ restrictions/ dependencies/ code/ outputs/ | WORKSPACE-SCHEMA §3 | audit | Rule |
| B-082 | Agent registration contract | create → DB complete row → project_agents → visible | WORKSPACE-SCHEMA §3 | audit codes | Enforced (doc) |
| B-083 | Shared layer layout | core-registry, config, directions, runbooks, skills, infra, testing, utils, assets, oth (secrets, gitignored), cached_modules | WORKSPACE-SCHEMA §4 | not stated | Rule |
| B-084 | Non-project roots | chats, anchor-layer, docs, state, history, logs | WORKSPACE-SCHEMA §5 | not stated | Rule |
| B-085 | Schema invariants | Same entries, nothing loose, shared vs owner, empty folders kept with .gitkeep, one canonical file per function | WORKSPACE-SCHEMA §6 | audit | Rule |
| B-086 | core-rules loaded first | Must be read in full before planning; wins over defaults | `directions/core-rules.md` §0 | not stated | Rule |
| B-087 | Rule versioning | Changes logged; superseded rules struck through not deleted | core-rules §0 | not stated | Rule |
| B-088 | Inviolable operating rules 1–8 | Read rules, custom first, no prod/VM w/o approval, never break working, history, ask, clean output, respect security posture | core-rules §1 | not stated | Rule |
| B-089 | ADR-001..008 | Platform layout; approval artifact; SSH via sandboxed shell; hybrid voice; Ruflo adapt/reject; dynamic-IP + systemd; voice FastAPI wiring; dispatcher + mobile | core-rules §2 | not stated | Accepted 2026-06-20/21 (ADR-003 pending access details; ADR-004 integration pending at time) |
| B-090 | Coding standards | Clarity; money in integer minor units/decimal never floats; validate input; no hard-coded secrets; explicit errors; basic tests per module | core-rules §3 | QA agent enforces | Rule |
| B-091 | Security/compliance rules | PII/PHI/payment → review; no raw PAN; PCI minimization; PHI encrypted + access logged; append-only audit logs; no new inbound port | core-rules §4; utils/security-and-compliance.md | not stated | Rule |
| B-092 | DevOps/Azure rules | Runbook deploys; SSL via runbook; respect sync method; every VM command shown + approved | core-rules §5 | not stated | Rule |
| B-093 | Azure dynamic-IP procedure (custom) | One IP at a time; update OS firewall + NSG; systemd; scp; proxies; automation policy | core-rules §5.1; `runbooks/azure-secure-connection.md` | see §2 | Rule (older; superseded in practice by DEPLOY-PROMPT az-replace flow) |
| B-094 | Billing model placeholder | Non-standard subscription; must not implement with standard assumptions | core-rules §6.1 | n/a | PLACEHOLDER, blocked on owner |
| B-095 | Voice on-device rule | Local Whisper/TTS; EN+AR; no cloud speech | core-rules §6.2 | not stated | Rule |
| B-096 | No mostafa-app dependency | Nothing may import/reference mostafa-app | core-rules §6.3 | "Verified for voice module 2026-06-21" | VERIFIED (voice only) |
| B-097 | Engine & cockpit UX binding | Claude CLI core; humanized triage; cockpit phases A–D | core-rules §6.4 | not stated | Rule |
| B-098 | Visible scheduler panel | Per-project "Scheduled tasks" with cadence/runs/assignee, add/remove | AGENTS-CONNECTORS-BACKLOG | e2e "Create + list per-project schedule" | ✅ verified (sandbox) 2026-06-23 |
| B-099 | Periodic agent | Scheduled task assigned to agent (e.g. SecMan hourly), logged + rolled up to CTO | backlog | e2e "Periodic task assignable to a specific agent" | VERIFIED-RUN 2026-06-23 |
| B-100 | Company-level agents auto-added | Created once, auto-added to every new project | backlog | e2e company agent checks | VERIFIED-RUN 2026-06-23 |
| B-101 | External connectors w/ API key + badge | Add GA/Klaviyo/MCP etc.; keys stored privately (gitignored) | backlog | e2e "Add external connector..." PASS | VERIFIED-RUN 2026-06-23 |
| B-102 | Project presets | Deployable web app (FE+BE+DevOps+QA), Static landing, Mobile | backlog | not stated | DONE (no run evidence) |
| B-103 | Chat attachments (＋) | Attach file/folder paths via native picker; paths passed to engine (no vector store) | backlog | not stated | DONE; partial note |
| B-104 | Build inside chosen folder | Agents run with cwd = project folder | backlog | e2e "folder created on disk at chosen location" | VERIFIED-RUN 2026-06-23 |
| B-105 | Periodic agent auto-triggering others | Finding → FE bump → DevOps redeploy chain | backlog §Partial | e2e "A finding auto-triggers the team to fix (DevOps redeploy stays gated)" PASS | PARTIAL per backlog ("not yet a fixed loop") |
| B-106 | Two-brain triage (fast front + engine) | Direct answers fast; deep work asks "go deeper?" then calls Claude CLI | CONVERSATIONAL-UX-SPEC §A | not stated | Spec A1–A7 |
| B-107 | Progress narration | Intermediary keeps owner company while engine works | UX-SPEC A5 | not stated | Spec |
| B-108 | Cockpit UI B1–B8 | Bigger window, live processor view, animated, status icons, continuous progress, streamed answers, artifact rendering | UX-SPEC §B | not stated | Spec; Phase C/D deprioritized (PENDING) |
| B-109 | SSE streaming bridge | Spawn `claude --output-format stream-json`, parse events, forward as SSE | UX-SPEC §Architecture | not stated | Spec |
| B-110 | Cockpit build phases A–D | A streaming console; B triage; C live CLI bridge; D artifact rendering | UX-SPEC | not stated | A/B implied done; C/D deferred (PENDING) |
| B-111 | Master blueprint architecture | Electron app (company dashboard / project page / member page) over FastAPI with scope store, project registry, agent registry, per-scope model config, scheduler | `design/MASTER-BLUEPRINT.md` | not stated | Plan 2026-06-22 |
| B-112 | Blueprint phases 0–7 | Plan, desktop shell, scoped org, live agent characters, agent mgmt & rules, model control, project ops & self-healing, scheduling | MASTER-BLUEPRINT | regression check each phase | Plan |
| B-113 | Add member by description → suggested name | Registers new role | blueprint Phase 4 | e2e "Add-member: suggests a name + role" (Testwright) | VERIFIED-RUN 2026-06-23 |
| B-114 | Save custom rule on member | Save-as-rule | blueprint Phase 4 | e2e PASS (1 rule) | VERIFIED-RUN 2026-06-23 |
| B-115 | Per-project skills folder | `data/projects/<id>/skills` | blueprint Phase 4 | e2e PASS | VERIFIED-RUN 2026-06-23 |
| B-116 | Usage stats per agent | % FE vs BE vs deploy | blueprint Phase 4/5 | e2e PASS (2 agents) | VERIFIED-RUN 2026-06-23 |
| B-117 | Model control | Catalog + set model per member/project/main | blueprint Phase 5 | e2e "Model catalog listed" (6), "Set model 3 levels" | VERIFIED-RUN 2026-06-23 |
| B-118 | Interrupt + correct + save-as-rule loop | Interrupt working member mid-task | blueprint Phase 4 | e2e "Intervening on a member feeds back up to the CTO" | VERIFIED-RUN 2026-06-23 (feedback part) |
| B-119 | Live agent characters/heartbeat | Avatars, heartbeat animation, flow indicators | blueprint Phase 3 | not stated | Plan |
| B-120 | Preserve guarantee | Regression check of engine, router, gate, voice, chats, Azure each phase | blueprint | not stated | Rule |
| B-121 | Scoped memory spec | Company CTO → Project CTO → member; delegation pipeline; drill-down; upward sync; scope-relative context; ownership persists; storage keys `company`/`project:<id>`/`member:<project>:<agent>` | `design/SCOPED-MEMORY-SPEC.md` | e2e scope isolation + delegation checks | Spec says PARKED; PENDING says BUILT 2026-06-22 |
| B-122 | Owner deploy standing rules | node_modules never; ask on public/upload/logs; lockfile only if deps changed; .env excluded; ask npm install; remove dest before rebuild; rebuild FE+BE; systemd restart; suggest service restart over reboot | `infra/DEPLOY-PLAYBOOK.md` | not stated | Rule 2026-06-23 |
| B-123 | Smart pre-flight | Read/analyze folders, detect prod, ask context-aware questions, respect answers, present commands+impact+rollback | DEPLOY-PLAYBOOK | not stated | NOT BUILT (status section) |
| B-124 | Post-deploy QA checker | Poll health endpoint ~10s up to 2–3 min for 200; else journalctl + rollback suggestion | DEPLOY-PLAYBOOK | `journalctl -u <svc> --no-pager -n 50` | Rule; implemented as deploy_verify.py (B-130) |
| B-125 | DevOps-only deploy prompt | Organics deploy uses DevOps agent only | `infra/DEPLOY-PROMPT.md` | not stated | Rule |
| B-126 | One-command deploy chain | change-detection → rsync→migrate→build→restart bendcore-staging+organics-staging → strong verify → update lists only on pass | `infra/deploy_run.sh` | `bash infra/deploy_run.sh [--bootstrap]` | DEPLOY-PROMPT; no dated run recorded here |
| B-127 | Change detection (Step 0) | Two lists (FE/BE) of deployable files + mtime; added/modified/removed; no changes ⇒ stop | `infra/deploy_changes.py` | `python infra/deploy_changes.py scan` | DEPLOY-PROMPT Step 0 |
| B-128 | Changed-files-only rsync | Feeds rsync `--files-from` | deploy_changes.py | `python infra/deploy_changes.py changed <backend|frontend>` | DEPLOY-PROMPT |
| B-129 | Bootstrap baseline | Baseline dated 2 years ago so everything is changed | deploy_changes.py | `python infra/deploy_changes.py seed-old` | DEPLOY-PROMPT |
| B-130 | Strong deploy verify | Poll :4014 + frontend to 200; DB users>0, rbacRoles>0, ≥1 isSuperadmin, products/appSettings seeded; auto-remediate by `systemctl restart bendcore-staging`; PASS verdict | `infra/deploy_verify.py` | `python infra/deploy_verify.py` | DEPLOY-PROMPT (born of incident 2026-07-16) |
| B-131 | Baseline update after verify | Save real mtimes as new baseline | deploy_changes.py | `python infra/deploy_changes.py update` | DEPLOY-PROMPT |
| B-132 | Smart DB-change gate | Schema/seed file change → `DB_SENSITIVE: YES` + recommendation; deploy_run.sh stops and asks | deploy_changes.py + deploy_run.sh | `ODIN_DB_REBASE=approve|deny` | DEPLOY-PROMPT |
| B-133 | Migration override | Deploy with no migration | deploy.sh | `ODIN_MIG_OVERRIDE=none` | VEEQO handoff §0, §9 |
| B-134 | SSH as mostafa, password auth | sshpass with PreferredAuthentications=password, PubkeyAuthentication=no; password from `oth/.cred` key `azvmcred` | DEPLOY-PROMPT §Connectivity | command shown (no value) | Rule |
| B-135 | Firewall refresh to current IP | NSG port-22 + ufw single-IP; keep 80/443; never widen | DEPLOY-PROMPT; testing prompt §7 | not stated | Rule |
| B-136 | No root app commands | Only `sudo reboot` elevated via `sudo -S` | DEPLOY-PROMPT | not stated | Rule (reboot later replaced by service restart) |
| B-137 | Folder mapping RBO-Staging | Local `RBO-Staging/f`→VM `/home/mostafa/RBO-Staging/f`; `b`→`/home/mostafa/RBO-Staging/b` | DEPLOY-PROMPT | not stated | Rule |
| B-138 | Never-sync exclude list | .env*, .backup-env, *.pem, *.key, google-oauth json, *.mp4/5, *.copy/bak/tmp, .DS_Store, node_modules, dist, logs, prisma/migrations, .next, package*.json, public, uploads, organics-local-vm-deploy-sync | DEPLOY-PROMPT | not stated | Rule |
| B-139 | Backend DB options | (A) `npx prisma generate && npx prisma migrate deploy`; (B) `npx prisma migrate reset --force` only on explicit "reset this run" | DEPLOY-PROMPT | n/a | Rule |
| B-140 | Build commands | BE `rm -rf dist && npm run build`; FE `rm -rf .next && npm run build` | DEPLOY-PROMPT | n/a | Rule |
| B-141 | Strict restrictions | Only listed commands; no npm run start; no system installs; never read/sync secrets | DEPLOY-PROMPT | n/a | Rule |
| B-142 | Per-run authorization | DB choice for this run only; re-confirm excludes + commands next run | DEPLOY-PROMPT §This run vs future | n/a | Rule |
| B-143 | Azure connection framework | Non-secret `connection.profile.json`; first read-only command as approval | `infra/azure/README.md` | not stated | "awaiting owner-provided access details" (superseded by later live access) |
| B-144 | Azure inventory | VMs, TLS certs, open ports tables | `infra/azure/inventory.md` | n/a | PLACEHOLDER (all _TBD_) |
| B-145 | Anchor standalone service | Dockerized `server/anchor_remote.py` `/anchor/v1` queue/auth/webhook; Dockerfile, compose, systemd unit, nginx TLS | `infra/anchor/` | `docker compose up -d --build`; `curl http://127.0.0.1:9100/health`; `/anchor/v1/_status` | "prepared, not executed" |
| B-146 | Runbook index | approval-template, deploy, ssl-certificate, security-scan, revert | `runbooks/README.md` | n/a | DOC |
| B-147 | Azure secure-connection runbook | 9-step IP rotation + scp sync + systemd + proxy + verify + log | `runbooks/azure-secure-connection.md` | commands listed | DOC; placeholders to confirm |
| B-148 | Safe deployment runbook | Preconditions (rules, QA go/no-go, security, backup) → Prepare/Approval/Stage/Cutover/Verify/Log | `runbooks/deploy.md` | not stated | DOC |
| B-149 | Mobile access runbook | LAN token option; internet exposure gated via Azure proxy+TLS+allowlist+token | `runbooks/mobile-access.md` | `uvicorn server.app:app --host 0.0.0.0 --port 8000` with USE_VOICE=1 | DOC |
| B-150 | Phone access runbook | Tailscale serve (recommended), Cloudflare quick tunnel, LAN | `runbooks/phone-access.md` | `tailscale serve --bg https / http://localhost:8000`; `cloudflared tunnel --url http://localhost:8000` | DOC; phone terminal parked |
| B-151 | Revert runbook | Identify → Diff → Approval → Restore → Verify → Log | `runbooks/revert.md` | n/a | DOC |
| B-152 | Security scan runbook | Passive allowed; active (traffic to VM) needs APR security-scan-active | `runbooks/security-scan.md` | n/a | DOC |
| B-153 | SSL runbook | Renew before 14 days; dry run, approval, backup, renew, verify, log | `runbooks/ssl-certificate.md` | `certbot renew --dry-run` | DOC |
| B-154 | 24/7 SOC sensor | Read-only, capped (CPUQuota 4%, MemoryMax 48M, idle IO, nice 19), JSON line every 5 min | `utils/INSTALL_SOC_SENSOR.md`; `infra/soc_sensor.sh`, `soc-sensor.service/.timer` | scp + `systemctl enable --now soc-sensor.timer` | Owner-approved; install run not dated here (redberry-continuous-soc ran in Phase 7) |
| B-155 | DevOps agent charter | Owns all cloud/CI-CD; no feature code; runs last after QA; must-honor gate | `utils/devops-deployment-safety.md` | n/a | DOC |
| B-156 | Security direction (company-level) | Hard rules incl. no new exposure (the `az` incident); veto; required reviewer | `utils/security-and-compliance.md` | n/a | DOC |
| B-157 | Tutorials golden rule | Read provider tutorial first; derive state from documented request/response | `tutorials/INDEX.md` | n/a | DOC (klaviyo/hubspot tutorials pending) |
| B-158 | EasyPost tutorial | Read-only GET whitelist; Basic auth with `EASYPOST_API_KEY`; tracker status enum; null-field rules | `tutorials/easypost_tracking_api.md` | not stated | DOC; not listed in INDEX.md |
| B-159 | EasyPost GET-only guard | Non-GET or other endpoint raises PermissionError before request | (integration code, not named) | not stated | DOC |
| B-160 | Veeqo tutorial | Catalog mandatory; order status enum stops at shipped; true shipped signals; tracking_events; responsibility map; mapping to our status | `tutorials/veeqo_fulfillment_api.md` | not stated | DOC |
| B-161 | Veeqo persistence shape rule | Extract scalars (tracking_number.tracking_number, carrier.name) before Prisma write; audit syncOrder path | veeqo tutorial | not stated | DOC |
| B-162 | Veeqo catalog rule in project rules | Durable rule added to two projects' index.json rules[] | `projects/fulfillment-vq-status-read-only-dc1e/index.json`, `projects/real-deployment-and-diagnosis-organics-07d7/index.json` | n/a | VEEQO handoff §4 (done) |
| B-163 | Veeqo order-lifecycle carrier fallback | Fallback to USPS/aggregator when tracking_events empty; normalize 3 frontend surfaces | bendcore `src/veeqo/veeqo-order-sync.service.ts` (sync path) | strong test: simulator + real reference order must reach DELIVERED | `handoffs/VEEQO_ORDER_LIFECYCLE_HANDOFF.md` §6 NOT BUILT; decision open |
| B-164 | Read-only prod VM access via az run-command | `az vm run-command invoke -g DJANGO-PROJECT -n django-vm --command-id RunShellScript`; output capped (read ≤150-line chunks) | VEEQO handoff §8 | command shown | DOC |
| B-165 | Delta-scoped Veeqo key | Use AppSetting.RUNTIME_OPERATIONAL_SETTINGS veeqoApiKey, not default env key; never print | VEEQO handoff §0,§8 | n/a | Rule |
| B-166 | Test brief T2 Fulfillment/Veeqo read-only | Connection status, total orders, channels; Fulfillment agent only | `testing/PROMPTS_USED_IN_TESTS.md` §1 | `python3 testing/readonly_shipping_vq_status.py` | DOC; Phase 7 fulfillment-vq ran clean 2026-07-19 |
| B-167 | Test brief T3 Email/Klaviyo read-only | Live/draft/total workflows, metrics, lists; Email agent only | PROMPTS §1 | `python3 testing/readonly_email_klaviyo_workflows.py` | Phase 7 email-klaviyo clean 2026-07-19 |
| B-168 | Test brief T4 Revealer multi-agent | Build → QA → DevOps sandbox deploy `/home/mostafa/sandbox-revealer` port 8531 → operators post live data → cURL verify | PROMPTS §1 | `python3 testing/sandbox_revealer_multiagent.py` | Revealer-6978 clean in Phase 7 2026-07-19; sandbox deploy 18 ok |
| B-169 | Test T5 redeploy/overwrite | Deploy → edit unique token → redeploy rsync --checksum → harness re-reads to prove overwrite | `testing/sandbox_deploy_overwrite_check.py` | not stated | DOC; no result recorded |
| B-170 | CTO planning prompt | Requirements first, smart key assignment, no no-op steps, QA automatic, reason not keyword, role boundaries, ordering 0–5, JSON pipeline output | `projects.plan_pipeline` | n/a | PROMPTS §2 |
| B-171 | Agent readiness check | REQUIRES/HAVE/MISSING then Ready or ask CTO once | `api_v2` execution prompt | n/a | PROMPTS §3 |
| B-172 | Build directive | Write real files to disk, `ls -R` proof, <15 min, lean stack, no prod build, no foreground servers | `api_v2` | n/a | PROMPTS §3 |
| B-173 | Per-agent resources blocks | Fullstack, Mobile, DevOps, QA, Fulfillment, Email, Security, Data, Designer permissions/keys/needs | `projects.resources_block` | n/a | PROMPTS §4 |
| B-174 | Key lookup order | (1) mandate ENV block, (2) shared pool, (3) project .env, (4) oth/.cred | resources_block | n/a | PROMPTS §4 |
| B-175 | Operator key protocol | Use CTO-stated key; ask once only if silent; never loop | Fulfillment/Email blocks | n/a | PROMPTS §4 |
| B-176 | DevOps per-command verification + content-level overwrite | Read exit code + output each command; rsync --checksum; verify zero pending via `--checksum --dry-run --itemize-changes` or md5sum | DevOps resources block; deploy directive | n/a | PROMPTS §4, §7 |
| B-177 | QA gate | Read-only; `ls -R` first; FAIL if empty; <5 min; verify code not live data; reply PASS:/FAIL: | `api_v2.qa_gate` | n/a | PROMPTS §5 |
| B-178 | CTO review after each member | "Confirmed:" or "Needs fix:" in 1–3 sentences | api_v2 | n/a | PROMPTS §6 |
| B-179 | Deploy directive (DevOps authoritative) | Channel, migrations, excludes, `bash infra/deploy.sh` optional, ignore stale scripts, exact target paths, firewall scope, truth rule | DevOps prompt | n/a | PROMPTS §7 |
| B-180 | Stale deploy scripts flagged | `organics-local-vm-deploy-sync/sync-backend-to-vm.sh`, `preflight-sync.sh` deprecated/broken | project folder | n/a | PROMPTS §7 |
| B-181 | Owner auto-answer in tests | Harness answers as owner (T4 default keys; T5 azvmcred, sandbox only) | harness | n/a | PROMPTS §8 |
| B-182 | Test harness core | Smart time limits, auto CTO-dialog handling, post-test clean-up/keep-as-seed prompt; shared pool preserved | `testing/harness.py` | `ODIN_TEST_KEEP=1` / `ODIN_TEST_CLEAN=1` | testing/README |
| B-183 | Real prod deploy test | DevOps-only REAL organics/bendcore deploy to live VM, owner prompt verbatim; DESTRUCTIVE | `testing/real_production_deploy_devops_only.py` | `ODIN_TEST_PROD_DEPLOY=1 python3 testing/real_production_deploy_devops_only.py` | DOC; no run recorded |
| B-184 | Old e2e suite retirement | server/e2e_*.py (14 files) superseded; owner to delete on Mac | `server/e2e_*.py` | rm command in README | PENDING owner action |
| B-185 | E2E report 2026-06-23 | 45 checks, 45 pass (status, deps, loc, plan, fake, agent, models, sched, chat, custom, scope, company, connect, infra, voice, intake, smart, memory, convo, feedback, auto, cleanup) | `testing/results/e2e-report.md` | Base `http://localhost:8000` (script not named) | VERIFIED-RUN 2026-06-23 23:06:50, 45/0/0/0 |
| B-186 | Capabilities awareness | Knows connected (Claude Code, Ollama, Azure CLI, Azure VM); recommends integrations | server | e2e deps checks | VERIFIED-RUN 2026-06-23 |
| B-187 | Team planning w/o hallucinated agents | Correct teams for Landing/Shop/Desk; no hallucinated agents; no fake active agents | projects plan | e2e plan/fake | VERIFIED-RUN 2026-06-23 |
| B-188 | Adaptive intake | Asks then adapts; gathers enough info (digest) before starting | intake | e2e intake/smart | VERIFIED-RUN 2026-06-23 |
| B-189 | Project creation honors choices | type/stack/team respected | projects | e2e custom | VERIFIED-RUN 2026-06-23 |
| B-190 | Member chat isolation | No cross-project leak | scopes | e2e scope | VERIFIED-RUN 2026-06-23 |
| B-191 | CTO delegation + dialogues | CTO delegates with auto hand-off; Chief↔CTO and member brief→work→review dialogues | api_v2 | e2e convo | VERIFIED-RUN 2026-06-23 |
| B-192 | Test cleanup | Removes run's test projects | harness | e2e cleanup (deleted 5) | VERIFIED-RUN 2026-06-23 |
| B-193 | odin-cto-brain skill | Packaged skill enforcing the loop and hard rules | `skills/odin-cto-brain/SKILL.md` | n/a | DOC (its pending list is stale) |
| B-194 | Global voice streaming asset | Capture, noise cancel, language detect, live chunking, report, embed in chat pool, export | `assets/global_voice_streaming_asset.md` | n/a | DOC |
| B-195 | Meeting API | `/meeting/capable|state|clear|chunk|finish|finish_text|view|report|report_all` | `server/meeting_api.py`; `dashboard/meeting_monitor.html` | endpoints | DOC |
| B-196 | Meeting transcription + report | `scopes.transcribe` (faster-whisper); `projects._engine` Claude CLI EN/AR templates (no approval gate) | server | n/a | DOC |
| B-197 | Meeting export | AR/EN MD + AR/EN DOCX (python-docx, RTL) or zip of all four | server | n/a | DOC |
| B-198 | Mobile meeting sheet | Flutter on-device speech_to_text → anchor `meeting_report` → `local_poller_http.py` → `/meeting/finish_text` | `odin_app/lib/screens/meeting_sheet.dart` | n/a | DOC |
| B-199 | Meeting capability gating | Button only when project owns asset | `projects.project_has_meeting_asset(pid)`; agent `asset="meeting_monitor"` | n/a | DOC |
| B-200 | Meeting dialogue UI integration | Desktop ChatPanel.jsx modal iframe; web Flutter iframe dialog; mobile bottom sheet | `ChatPanel.jsx` etc. | n/a | "integration plan" |
| B-201 | Chunk record + refinement rules | Chunk metadata; protected-token preservation; low-confidence marking | asset §4–5 | n/a | DOC |
| B-202 | Bilingual handling | AR/EN/mixed rules; normalize to selected output language | asset §6 | n/a | DOC |
| B-203 | Asset auto-activation | Owning agent attaches asset when project needs voice/meeting capabilities | asset §9 | n/a | DOC |
| B-204 | Cached modules pool | Role folders DevOps/Frontend/Backend/Miscellaneous; role agents (not CTO) check metadata and reuse | `shared/cached_modules/` | n/a | DOC |
| B-205 | Cached module metadata sidecar | `<name>.meta.json` name/role/summary/does/inputs/status/safety/provenance | cached_modules README | n/a | DOC |
| B-206 | Add-only-proven rule | Modules added only after proving in a real task | cached_modules README | n/a | Rule |
| B-207 | Phase 7 monitor suite | 8/8 projects health ~221ms avg | `phase7_monitor.py` | not stated (via .venv python) | VERIFIED-RUN 2026-07-19 |
| B-208 | Phase 7 strong suite | Adversarial injected violations really corrected | `phase7_strong.py` | not stated | VERIFIED-RUN 2026-07-19 ALL GREEN |
| B-209 | Phase 7 lifecycle suite | create→clean, exact baseline restore, shared deploy survives (17 files) | `phase7_lifecycle.py` | not stated | VERIFIED-RUN 2026-07-19 |
| B-210 | Phase 7 shared lib | Common helpers for suites | `phase7_lib.py` | n/a | DOC |

## 2. The certified end-to-end deploy process

Source of truth: `infra/DEPLOY-PROMPT.md` (Organics/RBO-Staging), reinforced by `PHASE7-HANDOFF.md` §1, `PROMPTS_USED_IN_TESTS.md` §7, and `VEEQO_ORDER_LIFECYCLE_HANDOFF.md` §9. One command: `bash infra/deploy_run.sh` (add `--bootstrap` for a full clean redeploy). Each stage gates the next. **[VM]** = changes the VM; **[AZURE]** = changes Azure.

1. **Change detection (always first).** `python infra/deploy_changes.py scan` (generic form supports `--project <pid>`, per-project baselines). Compares current mtimes of local `RBO-Staging/f` and `RBO-Staging/b` (never-sync list excluded) to the saved FE/BE lists. Reports added/modified/removed.
   - No changes and a baseline exists → **STOP, report "no changes", do not deploy.**
   - No reliable baseline → one-time `python infra/deploy_changes.py seed-old` (baseline dated 2 years ago), so everything counts as changed.
2. **Approval of the changed files.** Show the changed files to the owner and ask for approval. Only changed files are deployed (`python infra/deploy_changes.py changed <backend|frontend>` feeds rsync `--files-from`).
3. **DB rebase prompt (smart DB-change gate).** If any changed file is schema (`prisma/schema.prisma`, `prisma/migrations/**`) or seed (`src/seed/**`, `prisma/seed*`, `seed-data/**`, `*seed-reference*`), `scan` prints `DB_SENSITIVE: YES` with a recommendation to rebase/reseed. `deploy_run.sh` STOPS and asks. Owner sets `ODIN_DB_REBASE=approve` (→ `migrate reset --force` + reseed, data loss) or `deny` (code-only, data kept). The owner may refuse. No schema/seed change → non-destructive by default. Override with no migration: `ODIN_MIG_OVERRIDE=none`.
4. **Firewall IP replacement. [AZURE] [VM]** `az` runs on the Mac only to REPLACE the dynamic IP: NSG port-22 rule + ufw, single-IP allow. Never open new ports, never open 22 to Any/0.0.0.0/0, never close or reorder 80/443. If 22 is blocked, re-pin to the current IP and retry before aborting.
5. **SSH as `mostafa`.** Never root. Password from `oth/.cred` key `azvmcred`; force password auth (`sshpass … ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=no mostafa@<vm-ip>`). Never run app commands via `az vm run-command`.
6. **Sync. [VM]** `rsync -az -e 'ssh <same opts>' <excludes> <local>/ mostafa@<vm-ip>:<dest>/`, with `--checksum` so changed files overwrite by content. Verify with `--checksum --dry-run --itemize-changes` (zero pending) or md5sum. Targets: `/home/mostafa/RBO-Staging/f` and `/home/mostafa/RBO-Staging/b`. Excludes: the never-sync list (B-138).
7. **Migrate. [VM]** In `/home/mostafa/RBO-Staging/b` as mostafa: (A) default `npx prisma generate && npx prisma migrate deploy`; (B) only on explicit approval `npx prisma migrate reset --force`. Never `prisma migrate dev`.
8. **Build. [VM]** Backend `rm -rf dist && npm run build`; frontend `rm -rf .next && npm run build`. (VEEQO handoff note: for bendcore the backend runs live from the repo — restart, no `npm run dist`.)
9. **Service restart (the reboot solution). [VM]** Restart ONLY `bendcore-staging` + `organics-staging` (systemd). This re-runs bendcore's boot self-seed and loads the new frontend build. Never full-reboot the shared VM; never touch nginx, ports or the other 5 sites; never `npm run start`. (The older text in the same file still says a final `sudo reboot`; the "reboot solution" paragraph replaces it.)
10. **Endpoint + DB verification.** `python infra/deploy_verify.py`:
    - polls backend `http://127.0.0.1:4014` and frontend (`:3001`) to a real HTTP 200, with retries;
    - over SSH as mostafa checks `users > 0`, `rbacRoles > 0`, at least one `isSuperadmin=true`, and `products` / `appSettings` seeded;
    - if the DB is empty but the service is up, auto-runs `sudo systemctl restart bendcore-staging` **[VM]** so `seedIfNeeded()` refills it, then re-checks;
    - PASS only when endpoints are 200 AND the DB is seeded with a superadmin. Also check `systemctl status` for both services, plus mtime evidence (PHASE7-HANDOFF).
    - On FAIL: report the last error + journalctl + a rollback suggestion. Never report a fake success.
11. **Baseline update (only after PASS).** `python infra/deploy_changes.py update` saves real mtimes as the new baseline. A failed verify never updates the lists.
12. **Report.** Sync summary, build output, service status, DB health numbers, timing, PASS/FAIL.
13. **Per-run authorization.** The DB choice applies to this run only. Next run: re-confirm the excludes and commands.

Scripts involved: `infra/deploy_run.sh`, `infra/deploy_changes.py` (scan/changed/seed-old/update), `infra/deploy.sh` (generic engine: firewall → rsync → migrate deploy → build → restart → verify; verify port from delta; baseline gated), `infra/deploy_verify.py`, project delta under `workspace/projects/<pid>/deploy/` generated by `workspace_mw.provision_capability`.

Run evidence: Revealer sandbox deploy = 18 ok · 0 warn · 0 fail (PHASE7-HANDOFF, ~2026-07-19). Phase 7 Project D "Sandbox Deploy Mirror" reused the shared deploy (2026-07-19). No dated production deploy run is recorded in this bundle.

Older parallel procedure (`runbooks/azure-secure-connection.md`, core-rules §5.1): detect IP (`curl -s https://api.ipify.org`) → ufw via Serial Console **[VM, manual]** → NSG in Portal **[AZURE, manual]** → SSH check → `scp` **[VM]** → `systemctl restart organics.service bendcore.service` **[VM]** → `nginx -t && reload` **[VM]** → journalctl verify → log. It is superseded in practice by the rsync/az-replace flow above.

## 3. Test harness inventory

| Script / suite | What it proves | How to run |
|---|---|---|
| `testing/harness.py` | Shared base: smart time limits, auto CTO-dialog handling, cleanup/keep-as-seed prompt, shared pool preserved | Imported by tests; `ODIN_TEST_KEEP=1` / `ODIN_TEST_CLEAN=1` |
| `testing/readonly_shipping_vq_status.py` | Veeqo read-only status, orders, channels; Fulfillment agent only | `python3 testing/readonly_shipping_vq_status.py` |
| `testing/readonly_email_klaviyo_workflows.py` | Klaviyo live/draft/total workflows, metrics, lists; Email agent only | `python3 testing/readonly_email_klaviyo_workflows.py` |
| `testing/sandbox_revealer_multiagent.py` | Full multi-agent build→QA→sandbox deploy→operators post live data→cURL verify | `python3 testing/sandbox_revealer_multiagent.py` |
| `testing/real_production_deploy_devops_only.py` | REAL prod deploy, DevOps only; DESTRUCTIVE (wipes DB + reboot) | `ODIN_TEST_PROD_DEPLOY=1 python3 testing/real_production_deploy_devops_only.py` |
| `testing/sandbox_deploy_overwrite_check.py` | DevOps redeploy overwrites by content (unique token re-read) | not stated |
| `workspace/shared/testing/phase7_realrun.py` | 8 existing projects, real timed runs, audited | `.venv/bin/python workspace/shared/testing/phase7_realrun.py` |
| `workspace/shared/testing/phase7_prompt_loop.py` | prompt→plan→watch→audit→delete loop | `.venv/bin/python workspace/shared/testing/phase7_prompt_loop.py` |
| `workspace/shared/testing/phase7_prompt4.py` | Reproducible 4-new-project journey (create→run→strong acceptance→clean delete) | not stated (.venv python implied) |
| `phase7_monitor.py` | All projects healthy, 0 violations (~221ms avg) | not stated |
| `phase7_strong.py` | Adversarial: injected violations really corrected | not stated |
| `phase7_lifecycle.py` | create→clean, exact baseline, shared deploy survives | not stated |
| `phase7_lib.py` | Shared helpers | n/a |
| `seed_connectors.py` | Seeds 5 connectors | not stated |
| E2E report generator (script not named) | 45 checks across status/plan/agents/models/sched/scopes/connectors/infra/voice/intake/memory/delegation/cleanup | Base `http://localhost:8000`; result 45/45 on 2026-06-23 |
| `server/e2e_*.py` (14 old files) | Superseded old suite | To be deleted on the Mac (rm command in testing/README) |
| `shells/phase2_up.sh`, `shells/phase3_up.sh` | Environment / production validation | Roadmap Phase 8 (later) |
| `infra/deploy_verify.py` | Deploy truth gate (endpoints + DB seed) | `python infra/deploy_verify.py` |
| Anchor health checks | Anchor container up | `curl -s http://127.0.0.1:9100/health`; `/anchor/v1/_status` |

Recorded results: Phase 7 RUN1 2026-07-19 ~16:01–17:15 EEST (5 origin fixes; 8/8 and 4/4 after fixes). RUN2 17:22–17:34 EEST (all first pass, 0 violations, 0 fixes). E2E 2026-06-23 23:06:50 (45 pass).

## 4. Owner rules (binding)

1. Read core-rules first; custom logic (§6) overrides defaults — core-rules §0–1; ORCHESTRATOR; SKILL.md.
2. No prod/VM action without an approval artifact; stop until explicit YES — core-rules §1.3, ADR-002; ORCHESTRATOR.
3. Never break working logic; full timestamped history; ask when unclear — core-rules §1.
4. Never widen network exposure; no new inbound port without approval and justification — core-rules §1.8, §4; security-and-compliance.md.
5. NEVER touch real production (organics-prod-deploy/bendcore/organics: DB, config, nginx, ports, deploy behaviour); PROTECTED_PROJECTS — PHASE7-HANDOFF §1.
6. Deploy protocol: change detection first; `az` only replaces the dynamic IP; SSH as mostafa; DB rebase asked with a recommendation; reload services, don't reboot; verify; update baseline only after verification — PHASE7-HANDOFF §1; DEPLOY-PROMPT.
7. Generic engine + per-project delta; the system generates the delta, not a human — PHASE7-HANDOFF §1.
8. Don't stop or report done until 0 violations, 0 cross-violations; fix at origin — PHASE7-HANDOFF §1.
9. Proof comes from the owner's audit, not assistant assertion — PHASE7-HANDOFF §0; PHASE7-RESULTS.
10. Never report a fake success; HTTP 200 alone isn't proof — DEPLOY-PROMPT; PROMPTS §7.
11. DevOps-only for the organics deploy; no other agents — DEPLOY-PROMPT.
12. Never root app commands; never `npm run start`; no system installs; never read/sync secrets — DEPLOY-PROMPT.
13. Never-sync list (.env*, keys, node_modules, builds, migrations, package*.json, public, uploads, logs…) — DEPLOY-PROMPT; DEPLOY-PLAYBOOK.
14. Ask each time about public/upload/logs, npm install; lockfile only if deps changed; .env never by default — DEPLOY-PLAYBOOK.
15. Restart only affected systemd services; never full-reboot the shared VM; never touch nginx/ports/other 5 sites — DEPLOY-PROMPT.
16. Authorization is per run; re-confirm excludes and commands next run — DEPLOY-PROMPT.
17. Do not run sync/deploy on production until the smart pre-flight is built — DEPLOY-PLAYBOOK §Status.
18. Turnkey VM sync stays a gated proposal ("not rigid enough to touch running sites") — PENDING.
19. Phases run one at a time; next only after owner confirms — ROADMAP; STRUCTURING-PLAN.
20. Anti-duplication: reuse shared capability + custom delta; no deploy_2 copies; one canonical file per function — ROADMAP Phase 4; WORKSPACE-SCHEMA §6.
21. Placement via Q1/Q2; canonical skeletons; empty folders kept — WORKSPACE-SCHEMA.
22. Agent create → complete DB row → project_agents → visible; partial or invisible = bug — WORKSPACE-SCHEMA §3.
23. Billing: must not use standard recurring assumptions; ask owner — core-rules §6.1.
24. Voice on-device, EN+AR, no cloud speech — core-rules §6.2.
25. No dependency on mostafa-app — core-rules §6.3.
26. Claude CLI is the engine; never limited; never a silent/frozen window — core-rules §6.4; UX-SPEC.
27. Nothing in the UX spec may be discarded; preserve everything built — UX-SPEC; MASTER-BLUEPRINT.
28. Money as integer minor units/decimal, never floats; secrets never hard-coded/logged/committed — core-rules §3.
29. Provider state from official docs/tutorials, never guessed field names — tutorials INDEX, Veeqo, EasyPost.
30. Use the delta-scoped Veeqo key (AppSetting), not the default env key; Claude never handles new secrets (owner pastes key) — VEEQO handoff §0, §7.
31. Never say "done" before strong testing; no fake checkmarks — VEEQO handoff §0.
32. Exclude production project tests from Phase 7 — ROADMAP Phase 7.
33. Cached modules added only after proving in a real task — cached_modules README.
34. Don't ask to restart the bridge when it's running (PHASE7-HANDOFF header), but restart it if it stops picking up CMDs (VEEQO handoff §8).

## 5. Pending / placeholders / known issues

- **Billing model** placeholder; blocked on owner — core-rules §6.1; PENDING.
- **CFG_BACKEND_MIG="reset"** still set in `deploy.config.sh` from a one-time 2026-07-16 authorization. A production deploy would wipe the DB. Left untouched by design — PHASE7-HANDOFF §5. **[corrected: see §0.8 C-4]**
- **Smart pre-flight** not built — DEPLOY-PLAYBOOK §Status.
- **Turnkey one-click VM sync/deploy** parked (gated proposal) — PENDING.
- **Mobile/phone terminal** parked — PENDING; SCOPED-MEMORY-SPEC; MASTER-BLUEPRINT.
- **Per-chat project scoping**, IP rotation (NSG+ufw), cockpit Phase C/D deferred — PENDING.
- **Test persistent chat memory** listed as next (later e2e memory PASS 2026-06-23) — **VERIFIED-RUN (2026-06-22, chat 2e6a41cd6e97: 2-turn recall "FALCON-77"). Inventory correction 1, owner-approved 2026-10-11. A past run counts for the inventory only; it must still be re-proven in v2 in Phase 7.** Previously: PENDING.
- **Periodic agent auto-delegation chain** partial (engine-guided, not a fixed loop) — backlog.
- **Attachments** are paths only, no upload/vector store — backlog.
- **Anchor on VM** prepared, not executed; `anchor.YOURDOMAIN` placeholder — infra/anchor/DEPLOY.md.
- **Azure inventory** all _TBD_; azure README "awaiting owner access details" (stale) — infra/azure.
- **Runbook placeholders** `<vm-host>`, `<user>`, firewall tool, unit names, proxy software; `connection.profile.json` — azure-secure-connection.md.
- **Veeqo carrier-tracking fallback** not built; tracking source decision open (USPS / EasyPost-AfterShip recommended / Amazon SP-API); no USPS/aggregator key present — VEEQO handoff §6–7, §10. **[corrected: see §0.8 C-3]**
- **Bridge** stopped picking up new CMDs at end of a session (stale .run_out) — VEEQO handoff §8.
- **Bridge exit codes lie about SSH** (exit 255 on success); macOS has no `timeout`; Postgres deadlock when holding a transaction during `sync_row`/`sync_folders`; 900s bridge timeout (use `nohup … & disown`) — PHASE7-HANDOFF §5.
- **project_agents** fix was first only in a test script; corrected in prod 2026-07-30 — PHASE7-RESULTS addendum.
- **Old e2e suite** (14 `server/e2e_*.py`) awaiting deletion on the Mac — testing/README.
- **Stale deploy scripts** (`sync-backend-to-vm.sh`, `preflight-sync.sh`) known-bad — PROMPTS §7.
- **Roadmap Phases 1–6 and 8** have no done-marker in ROADMAP; Phase 8 explicitly later. Conflict: ROADMAP says 16-entry project / 8-entry agent skeleton; WORKSPACE-SCHEMA says 9 project entries.
- **Structuring-plan phases 0–7** have no recorded pass status in this bundle.
- **Debounced audit UI tab** (run-now, interval, enable) not evidenced — ROADMAP Phase 5.
- **SCOPED-MEMORY-SPEC** still says PARKED / do not build, while PENDING says BUILT 2026-06-22 (doc drift).
- **SKILL.md** pending list (Brain↔agent connection, mobile dispatcher, end-to-end voice) is stale.
- **DEPLOY-PROMPT** internal inconsistency: "Final step `sudo reboot`" vs "NEVER full-reboot; restart only services".
- **ADR numbering**: ADR-008 listed before ADR-007.
- **Tutorials** for klaviyo/hubspot not yet written; easypost tutorial missing from INDEX.md.
- **`real_production_deploy_devops_only.py`** destructive (wipes prod DB + reboots), which conflicts with the later restart-only rule.
- **`sandbox_deploy_overwrite_check.py`** has no recorded result.
- **ADR-004/007**: Piper vs Coqui XTTS for Arabic TTS — final per UX-SPEC is Coqui XTTS-v2 ("no macOS voice anywhere"), which supersedes the Piper/`say` mention.


<!-- ==================== PART C ==================== -->

# Odin-Orchestrator v1 — Master Feature Inventory (Part C: agents, projects, server, clients)

Sources: `_phase1_bundles/B4_agents_projects.txt` (152 files, all read) and `_phase1_bundles/B6_code_inventory.txt` (all read).
Secret values were not copied. Paths to credential files (for example `workspace/shared/oth/.cred`) are named only as references.
Legend: Nature/Type columns come from each agent's `index.json` (`nature` and `type`). "Projects" lists what `index.json` says, unchanged.

---

## 1. Agents roster (32 agent folders under `workspace/agents/`)

| # | Slug | Name | Role | Nature / Type | Group | Company flag | Key restrictions / instructions (1 line) | Handoff (after → before / collab) | Dependencies (shared files / assets) | Projects (index.json) |
|---|---|---|---|---|---|---|---|---|---|---|
| A-01 | asset-exposure-attack-surface-agent | Asset, Exposure & Attack-Surface Agent | same | operational / security | asset | – | Living asset and attack-surface inventory across clouds; builds the reverse-search filter; not intel, detection or prediction | none | `server/soc_inventory.py` (asset `soc_inventory`) | RedBerry Continuous SOC |
| A-02 | audio-capture-agent | Audio Capture Agent | same | technical / operational | voice-pipeline | – | Owns the Global Voice Streaming Asset (mic, noise, language detection, chunking, MD/DOCX AR/EN export); the rule appears twice (duplicate) | none | `dashboard/meeting_monitor.html`, `server/meeting_api.py`, `odin_app/lib/screens/meeting_sheet.dart`, scopes.transcribe (Whisper), python-docx, `shared/assets/global_voice_streaming_asset.md` (asset `meeting_monitor`) | Zoom Smart Meeting Notification Agent |
| A-03 | chunk-analysis-agent | Chunk Analysis Agent | same | technical / operational | voice-pipeline | – | Generic stub ("specialist for Zoom…"); the binding rules live in the project description | none | Claude engine, with Ollama qwen2.5 as fallback (per project stack) | Zoom… |
| A-04 | chunking-agent | Chunking Agent | same | technical / operational | voice-pipeline | – | Generic stub; chunks of 2–5 min max | none | – | Zoom… |
| A-05 | compliance-config-baseline-agent | Compliance & Config-Baseline Agent | same | operational / security | compliance | – | Read-only; never changes config, firewall or services; never root (SSH as mostafa only); masks secrets | after Asset, IAM → before Reporting & Doc, CTO; collab IAM, Vuln | instructions/ and restrictions/ folders | redberry-continuous-soc (slug) |
| A-06 | content-creator | Content Creator | same | technical / operational | content | – | Generic stub; the capability.md also holds an "[archived] merged from duplicate agent 'marketing'" block | none | – | Egypt Amazon Daily Social Content Agent |
| A-07 | content | Content | Content (capability title says "Content Creator") | operational / operational | content | – | Non-technical; posts, copy and content calendar; writes no code | none | – | Egypt Amazon… (but excluded in that project) |
| A-08 | cto-orchestrator | CTO Orchestrator | same | operational / operational | orchestration | – | The only agent that presents decisions to the owner; never approves its own action; prevents overlapping investigations | none | `server/soc_run.py` (asset `soc_run` / `soc_engine`) | RedBerry Continuous SOC |
| A-09 | detection-engineering-purple-team-validation-agent | Detection Engineering & Purple-Team Validation Agent | same | operational / security | detection | – | Benign, non-disruptive validations only; anything active is approval-gated; read-only on production | after Architect, Investigator, UEBA → before UEBA, Investigator; collab Architect, UEBA | instructions/ and restrictions/ | redberry-continuous-soc |
| A-10 | devops | DevOps | DevOps & Cloud | technical / technical | cloud | – | Deploys and operates any cloud and CI/CD; writes no feature code; runs LAST after QA. Rules in project resources: SSH as mostafa, port 22 pinned to one IP, 80/443 untouched, rsync --checksum, verify every exit code | none | `workspace/shared/oth/.cred` (reference), `shared/infra/deploy.sh`, `deploy_changes.py` | Organics Production Deploy (2VM), Revealer |
| A-11 | easypost | EasyPost | EasyPost Shipping & Tracking Operator | operational / operational | shipping | **true** | Read-only multi-carrier tracking after shipping (Veeqo handles pre-shipping); holds the EasyPost key; writes no app code | collab: fulfillment | `oth/.cred` (reference) | *(no projects field)* |
| A-12 | email | Email | Email & Lifecycle (other projects say "Email Specialist" or "Email") | operational / operational | marketing | – | Non-technical Klaviyo and Mailchimp operator; holds the key; key protocol is "use what the CTO told you, ask once only if it was silent" | none | `oth/.cred` default Klaviyo key | Email — Klaviyo workflows (read-only), Revealer |
| A-13 | final-summary-agent | Final Summary Agent | same | technical / operational | voice-pipeline | – | Generic stub; merges into the 13-section report | none | – | Zoom… |
| A-14 | fulfillment | Fulfillment | Fulfillment Operations | operational / operational | fulfillment | – | Non-technical operator for Veeqo, ShipBob and other 3PLs; holds the key; follows the VEEQO CATALOG RULE in projects | none | `oth/.cred`, `workspace/shared/tutorials/veeqo_fulfillment_api.md` | Egypt Amazon…, Fulfillment — VQ status, Revealer |
| A-15 | fullstack | Fullstack | Full-Stack Engineer | technical / technical | fullstack | – | Builds the whole web app (any stack, Flutter for web only); writes every third-party integration; no mobile, no deploy | none | env order: brief → shared pool → project `.env` → `oth/.cred` | Revealer |
| A-16 | hubspot | HubSpot | HubSpot CRM Operator (capability.md title says "HubSpot CRM Specialist") | operational / operational | crm | – | Project rules: token from `oth/.cred` and never printed; answer only within the 35 granted scopes (`data/hubspot_scopes.json`); read-only by default. **capability.md description is corrupted** ("please use the next commands to get the reason for the 400 b") | none | `server/hubspot_api.py`, `data/hubspot_scopes.json` | HubSpot CRM — Account Analytics |
| A-17 | identity-access-governance-agent | Identity & Access Governance Agent | same | operational / security | iam | – | Read-only; never creates, modifies or deletes accounts, keys or privileges; never root; no credential exfiltration | after Asset → before Investigator, Compliance; collab Asset | instructions/ and restrictions/ | redberry-continuous-soc |
| A-18 | intrusion-detection-behavioral-analytics-agent | Intrusion Detection & Behavioral Analytics Agent | same | operational / security | ueba | – | Behaviour-based UEBA; separates the owner's dynamic IP from attackers; UFW and edge blocks are always approval-gated | none | `server/soc_behavior.py` (asset `soc_behavior`) | RedBerry Continuous SOC |
| A-19 | memory-and-storage-agent | Memory and Storage Agent | same | technical / operational | storage | – | Generic stub; SQLite/JSON keyed by chunk ID | none | – | Zoom… |
| A-20 | notification-agent | Notification Agent | same | technical / operational | notification | – | Generic stub; turns the final report into smart notifications | none | – | Zoom… |
| A-21 | qa-reviewer-operational | QA / Reviewer (operational) | Content Reviewer Agent | technical / operational | review | – | Fact-check, style and gatekeeper review with mandatory web search; bilingual AR/EN. **The rule text is stored three times** and includes a pasted chatbot tail ("Would you like me to adjust…") | none | web search (mandatory) | Egypt Amazon… |
| A-22 | qa | QA | QA & Testing | technical / technical | qa | – | Read-only verifier; runs `ls -R` first and reports FAIL if nothing was built; no prod build | none | `shared/testing/run_all.py` (via manifests) | Revealer |
| A-23 | recovery-resilience-agent | Recovery & Resilience Agent | same | operational / security | recovery | – | Encrypted, checksummed backups with the key on the local desktop; smart date-aware restore; restore is always approval-gated, capture is automatic | none | `server/soc_recovery.py` (asset `soc_recovery`), Fernet/AES, pg_dump | RedBerry Continuous SOC |
| A-24 | reporter | Reporter | Reporting & Documentation Agent | – / operational (stub index: id, name, role, type, description `__auto_link_stub__`) | – | – | Same capability as A-25 (reusable branded MD/DOCX/PDF/PPTX report) | empty | `server/report_engine.py` (asset `report_engine`) | – |
| A-25 | reporting-documentation-agent | Reporting & Documentation Agent | same | operational / operational | reporting | – | Reusable reporting asset; writes no app code | none | `server/report_engine.py` | RedBerry Continuous SOC |
| A-26 | sales | Sales | Sales & Outreach | – / operational (`__auto_link_stub__`) | – | – | Non-technical CRM operator; writes no code | empty | `oth/.cred` default CRM key | – |
| A-27 | security-intelligence-threat-hunting-architect | Security Intelligence & Threat-Hunting Architect | same | operational / security | intel | – | Never touches production; OSV, CISA KEV and abuse.ch filtered to our stack; vulnerability presence is not compromise. In the SOC project its mode is `theoretical` | none | `server/soc_intel.py`, `soc_intel_fusion.py` (asset `soc_intel`) | RedBerry Continuous SOC |
| A-28 | security-operations-investigator | Security Operations Investigator | same | operational / security | investigation | – | The single read-only present-state investigator; a guard refuses mutating commands; every finding needs a false-positive analysis | none | `server/soc_run.py` (`_ssh_ro` guard) | RedBerry Continuous SOC |
| A-29 | security | Security | Security & Threat Hunting | – / technical (`__auto_link_stub__`) | – | – | Generic code and cloud security plus periodic checks; overlaps the SOC team | empty | – | – |
| A-30 | threat-prediction-prevention-agent | Threat Prediction & Prevention Agent | same | operational / security | prediction | – | Forward-looking: predicts the next weakness and recommends hardening | none | `server/soc_predict.py` (asset `soc_predict`) | RedBerry Continuous SOC |
| A-31 | transcription-agent | Transcription Agent | same | technical / operational | voice-pipeline | – | Generic stub; faster-whisper or Whisper | none | voice/backend `/stt` | Zoom… |
| A-32 | vulnerability-patch-management-agent | Vulnerability & Patch-Management Agent | same | operational / security | vulnerability | – | Never applies patches (approval-gated); read-only SSH as mostafa; never root; never az; no secret exfiltration | after Asset → before Predictor, Investigator; collab Asset, Compliance | instructions/ and restrictions/ | redberry-continuous-soc |

### 1b. Agents referenced in projects that have no agent folder

| Name seen | Where | Note |
|---|---|---|
| Analytics | Organics project (agents.json, members, plan/analytics.md) | Google Analytics operator; no `workspace/agents/analytics/` |
| CloudDebug | Organics `index.json` members | The Cloud-Diagnosis/SRE agent from the description; missing from agents.json and from the agent folders |
| AssetSurface, Predictor, Recovery, BehaviorIDS | SOC `index.json` members and instructions.md | Alias duplicates of A-01, A-30, A-23, A-18 |
| ZzTestMember, ZzGapMember | Organics `excluded` and instructions.md | Test leftovers |
| Mobile | Fullstack description ("Mobile" builds apps) | No agent |
| Marketing | content-creator capability.md (archived merge) | Merged away |
| "Enrich/Intel" | SOC `req-app-abuse.md` | No such agent; `server/soc_enrich.py` and `soc_hunt.py` have no owning agent |

**Unusual flags**
- `company:true` is set only on **EasyPost**. It shows up in `fulfillment-vq-status-read-only-dc1e/agents.json` but not in that project's `members`, which looks like an auto-add. No other project has it, so whether it is "added to every project" needs checking.
- Three agents (reporter, sales, security) have stub index files with the description `__auto_link_stub__` and no nature, group or typeConfig. This looks like an auto-link mechanism created them.
- `nature` and `type` often conflict. For example, the voice-pipeline agents are nature technical but type operational, and the SOC agents are nature operational but type security.
- The `projects` field mixes display names ("RedBerry Continuous SOC") and slugs ("redberry-continuous-soc").
- Every `index.json` that has a `note` says "INDEX/REFERENCE ONLY — not moved yet (Phase 1a)". `skill_file_hint` points to `data/projects/<pid>/skills/<slug>.md`.
- Only 5 of the 32 agents have non-empty `handoff.json` (compliance, detection, IAM, vuln, easypost).
- Several `index.json` files carry `mode: normal`. In the SOC, the Architect's mode is `theoretical`.

---

## 2. Projects (11 under `workspace/projects/`)

| # | ID | Name | Type / category | Cadence / schedule | Members (index.json) | Purpose (1 line) | Special flags |
|---|---|---|---|---|---|---|---|
| P-01 | daily-egypt-amazon-product-poster | Egypt Amazon Daily Social Content Agent | content / content (typeConfig periodical.json) | periodical; periodic enabled, daily 09:00, requireApproval true | Content Creator, QA / Reviewer (operational) | Every day, find the top 3 Amazon Egypt products and draft one Facebook and one Instagram post, all locally | localPath set to the owner's local test folder; no VM or DevOps; `qa_declined`; excluded agents Content and Fulfillment (with reasons and dates); approved features: Meta auto-publish, poster image generation, approval preview; owner text duplicated in description **[corrected: see §0.8 C-5]** |
| P-02 | email-klaviyo-workflows-read-only-18ca | Email — Klaviyo workflows (read-only) | email / email (normal.json) | once; periodic off | Email | Read-only count of live, draft and total Klaviyo workflows, plus metrics and lists | read-only; `qa_declined`; uses only the Email agent |
| P-03 | fulfillment-vq-status-read-only-dc1e | Fulfillment — VQ status (read-only) | fulfillment (normal.json) | once; periodic off | Fulfillment (agents.json also has EasyPost) | Veeqo connection status, order total, channels, and readiness for later questions | VEEQO CATALOG RULE (official API catalog plus tutorial md); `qa_declined`; EasyPost auto-added |
| P-04 | full-services-19jul | Full Services Platform (19 Jul) | fulfillment / "" (no typeConfig) | recurring; periodic off | 16: Fullstack, DevOps, Security, Fulfillment, Email, Sales, Reporter, QA, CTO Orchestrator, Architect, Investigator, Asset, UEBA, Predictor, Recovery, Reporting & Doc | Internal Ops Platform (NestJS + Postgres + dashboard) with HubSpot, Klaviyo and Veeqo; sandbox VM deploy; CircleCI; SOC | **auto_approve: true**; `soc_provisioned: true`; qa_asked; never touch production (organics/bendcore); manifest: `deploy_changes.py`, `INSTALL_SOC_SENSOR.md` (as-is); requested roles not recruited: analytics, customer support, HubSpot operator, Vuln, IAM, Compliance |
| P-05 | hubspot-crm-operator | HubSpot CRM — Account Analytics | crm (recurring.json) | recurring; periodic off | HubSpot | Confirm the connection and report contacts, companies, deals and contacts created this month | 4 agent rules (token never printed, 35 scopes, guidance for out-of-scope asks, read-only); connector: HubSpot (`hubspot_api.py`) |
| P-06 | odin-external-arms | Odin Platform — External Arms | **arm** / build (normal.json) | recurring; periodic off | none (agents.json empty) | The protected company "arm" that points to the server, orchestrator, voice, desktop, Flutter and anchor code | **protected: true, arm: true** (cannot be deleted or split); manifest `anchor_web_deploy` → `shared/infra/phase3_gate.py`; docs/references.md maps code locations; doctrine `workspace/shared/directions/ORCHESTRATOR.md` |
| P-07 | real-deployment-and-diagnosis-organics-07d7 | Real Deployment & Diagnosis — Organics | operational / "Azure 2VM deploy + read-only cloud diagnosis" | recurring; periodic off | DevOps, Fulfillment, Email, Analytics, Reporter, HubSpot, CloudDebug | Deploy the RBO **staging** backend and frontend (2VM) when changes are found, then run a read-only multi-agent diagnosis | STAGING only, never production; **external report path**: exactly one file, `AI_DIAGNOSIS_REPORT.md`, at the local RBO-Staging root; **delta/agent-scope**: scoped keys via runtime_settings pointers (getVeeqoConfig, getKlaviyoConfig, getHubspotConfig) with `credential_source` delta or default; odin_core DB is the source of truth; `OWNER_RUN_FLOW.md` (one gate per turn); VEEQO CATALOG RULE; plan/*.md per agent; `qa_declined` |
| P-08 | redberry-continuous-soc | RedBerry Continuous SOC | operational (periodical.json) | periodical; daily 23:00 America/New_York (DST-aware, catch-up), requireApproval **false** | 13 names, including aliases (AssetSurface, Predictor, Recovery, BehaviorIDS, Reporter) | Production-grade read-only multi-agent SOC: Observe → Correlate → Verify → Report → Approve → Act | monitor-only; `SOC_AUTO_REMEDIATION_ENABLED=false`; 22 SOC_* settings in `data/soc_settings.json`; findings registry; KB of 43 files; docs SOC_REDBERRY.md and SOC_SECURITY_ROLES.md; req-app-abuse.md (owner-added 2026-07-19); manifest `INSTALL_SOC_SENSOR.md`; agents.json has 13 agents, including 4 expansion agents not in members **[corrected: see §0.8 C-8]** |
| P-09 | revealer-6978 | Revealer | web (normal.json) | once; periodic off | Fullstack, DevOps, Fulfillment, Email, QA | Sandbox end-to-end web app (Veeqo shipping status plus Klaviyo metrics), deployed to a VM sandbox on port 8531 | **auto_approve: true**; sources: local frontend and backend sandbox folders; manifest **extend + overlay**: `run_all.py` → `tests/`, `deploy_changes.py` → `deploy/revealer-6978.config.sh` |
| P-10 | vm-sentinel | VM Security Sentinel | **marketing** (type looks wrong) / "" | periodical; periodic enabled but **schedule {}** | Fullstack, DevOps, QA | Daily VM security health check (RED/GREEN) from sensor facts; raises security-alarm approvals | No security agents among the members; ties to `server/security_sentinel.py` and `/sentinel/*` **[corrected: see §0.8 C-9]** |
| P-11 | zoom-real-flow | Zoom Smart Meeting Notification Agent | operational (periodical.json) | periodical; daily 06:00, requireApproval false | 7 voice-pipeline agents | Live meeting audio → chunks → per-chunk analysis → 13-section report → smart notifications | features: `["voice"]`; strict "only these 7 agents, 15 rules, 8 steps" contract; docs/references.md → `shared/assets/global_voice_streaming_asset.md`; docs/final_report.md is an **empty-transcript run** |

---

## 3. Server capabilities by module

Route prefixes are inferred from the `app.py` `_status` probes: `/auth`, `/v2` (api_v2), `/api/v1` (external_api), `/anchor/v1` (anchor), `/soc`, `/notifications`, `/meeting`, `/hubspot`, `/directions`, `/audit` (workspace_audit), `/ui` (ui_api), `/voice`. Exact mounts need checking in `app.py`.

| ID | Capability | Module / file | Key routes (file:line) | What it does |
|---|---|---|---|---|
| C-001 | Auth, login, 2FA, password, verification | server/auth.py (199) | auth.py:126 GET /config, :130 POST /config, :139 POST /login, :149 POST /2fa, :158 GET /me, :165 POST /logout, :170 POST /change-password, :182 POST /forgot, :186 POST /verify/send, :190 POST /verify/confirm; app.py:115 /auth/_status | Auth for the web and Flutter apps; the local desktop stays open |
| C-002 | Project registry CRUD and archive | server/projects.py (1488), api_v2.py | api_v2.py:98 GET /projects, :103 GET /projects/archived, :108 POST /projects/{pid}/archive, :113 /unarchive, :118 POST /projects, :127 GET /projects/suggest-id, :299 GET /projects/{pid}, :309 POST /update, :317 DELETE /projects/{pid}, :322 POST /mappings | Project registry (Phase 2 + 6): create, read, update, delete, archive, ID suggestion, folder mappings |
| C-003 | Project types, roles, capabilities | api_v2.py, server/capabilities.py (160), shared/config/project-types/*, agent-types/* | api_v2.py:132 GET /project-types, :144 POST /projects/{pid}/capability, :151 GET /roles, :185 GET /capabilities | Type and role catalog; registry of integrations already connected and what can be added |
| C-004 | Project intake (CTO planning) | api_v2.py, projects.py | api_v2.py:156 POST /projects/intake, :162 GET /projects/intake/readiness | Turns a prompt into a project plan and team, with a readiness check |
| C-005 | Company agents and org roster | server/agents_registry.py (476), api_v2.py | api_v2.py:192 GET /company/agents, :199 GET /agents/all, :204 POST /company/agents, :210 DELETE /company/agents/{name}, :137 POST /agents/validate | Agent registry and skills/rules engine; company-level agents; validation; `/agents/all` mirror used by web and desktop |
| C-006 | Project agents, per-agent rules, suggestions | agents_registry.py, api_v2.py | api_v2.py:490 GET /projects/{pid}/agents, :500 POST /agents/suggest, :505 POST /agents, :514 GET /agents/{name}, :522 POST /agents/{name}/update, :530 DELETE /agents/{name}, :535 POST /agents/{name}/rule | Team management per project: hire, edit, remove, rules |
| C-007 | Project rules | api_v2.py | api_v2.py:342 GET /projects/{pid}/rules, :347 POST, :352 POST /rules/{rid}, :357 DELETE /rules/{rid} | Project-level rule CRUD (for example the VEEQO CATALOG RULE) |
| C-008 | Plan and remediation | api_v2.py | api_v2.py:330 GET /projects/{pid}/plan, :335 POST /projects/{pid}/remediate | View the plan; trigger remediation |
| C-009 | Usage stats | agents_registry.py | api_v2.py:495 GET /projects/{pid}/stats | Invocations and lastActive per agent |
| C-010 | Connectors (integrations) | api_v2.py, capabilities.py, ui_api.py | api_v2.py:216 GET /connectors, :221 POST, :226 DELETE /connectors/{cid}; ui_api.py:211 GET /connectors | Register and remove third-party connectors (Veeqo, Klaviyo, HubSpot…); seeded by `testing/seed_connectors.py` |
| C-011 | Approval gate | server/approvals.py (162), api_v2.py, soc_api.py | api_v2.py:232 GET /approvals, :239 GET /approvals/count, :244 POST /approvals/{aid}/approve, :276 POST /reject; soc_api.py:120 POST /approvals/approve-all | The owner must approve before any agent changes files or runs a write; bulk approve-all |
| C-012 | Sync and deploy (deterministic plus AI) | server/deploy_runner.py (469), deploy_agent.py (202), deploy_ssh.py (155), shared/infra/deploy*.{sh,py} | api_v2.py:362 GET /projects/{pid}/sync, :367 GET /deploy, :372 POST /sync/run, :377 POST /deploy/run, :389 GET /deploy/config, :394 POST /deploy/config, :399 POST /deploy/request, :472 POST /deploy/operation | Change detection (`deploy_changes.py scan`), a deterministic deploy runner, a self-healing deploy agent (fixed script plus AI brain), and an SSH channel that logs in with a password |
| C-013 | Orchestrate and run (main task) | server/main_task.py (293), claude_cli.py (360), intent.py (141), orchestrator/dispatcher.py (286), orchestrator/semantic_router.py (91), cached_modules.py (77) | api_v2.py:382 GET /projects/{pid}/orchestrate, :423 POST /orchestrate/start, :427 GET /orchestrate/status, :431 POST /orchestrate/stop, :482 POST /projects/{pid}/run-now | Each prompt becomes one persistent shared-state task; the Claude CLI engine works in the project folder; intent-first routing; pool of cached modules |
| C-014 | Operations (running-task source of truth) | server/operations.py (185) | api_v2.py:436 GET /operations, :441 GET /operations/latest, :447 GET /operations/{oid}, :452 POST /stop, :459 POST /provide | Track, stop and feed input to running operations (deploy, sync…) |
| C-015 | Per-scope model control | server/models_config.py (79), shared/config/models.json | api_v2.py:544 GET /models, :550 POST /models/set | Choose the model per scope (Phase 5) |
| C-016 | Scoped memory, chat and streaming | server/scopes.py (318) | api_v2.py:556 GET /scope/chats, :561 POST /scope/chats, :566 GET /scope/chat, :574 POST /scope/chat/rename, :582 DELETE /scope/chat, :587 GET /scope/summary, :592 GET /scope/children, :597 GET /scope/stream (SSE), :605 GET /scope/messages, :734 DELETE /scope/message, :740 POST /scope/message, :759 POST /scope/upload, :767 GET /scope/file/{fid} | Hierarchical scoped memory (company → project → agent), the shared chat pool, uploads, and the SSE stream |
| C-017 | v2 chats | server/chats.py (96), api_v2.py | api_v2.py:691 GET /chats, :696 POST /chats, :706 POST /chats/rename, :721 DELETE /chats/{scope:path} | Persistent chat store, one JSON file per conversation |
| C-018 | Project report export | server/report_engine.py (194) | api_v2.py:623 GET /project/report | Branded MD, DOCX, PDF and PPTX reports (Reporter asset) |
| C-019 | Live activity bus | server/activity.py (66) | api_v2.py:776 GET /activity, :781 GET /activity/stream | Heartbeat agent indicators (Phase 3) |
| C-020 | Scheduler and periodic gate | server/scheduler.py (473) | api_v2.py:793 GET /schedules, :798 POST, :803 POST /schedules/{tid}/update, :811 DELETE, :817 GET /schedules/pending, :822 POST /approve, :830 POST /skip | Per-project task scheduler; timezone-aware daily runs; catch-up; approve or skip periodic runs |
| C-021 | Legacy cockpit chat and dispatch | server/app.py (461), brain_handler.py (65), orchestrator/* | app.py:207 POST /chat, :213 POST /dispatch, :220 GET /chat/stream, :267 GET /chats, :273 POST /chats, :279 GET /chats/{cid}, :288 DELETE, :294 POST /rename, :303 GET /chats/{cid}/stream | The original local server's brain ↔ agent dispatch and its own chat store (duplicates C-017) |
| C-022 | Infra connectivity (Azure, SSH, dynamic IP) | server/infra_az.py (193), infra_ssh.py (77), infra_rotate.py (152), shared/infra/ensure-connection.sh, azure/connection.profile.json | app.py:377 GET /infra/ip, :384 GET /infra/reachable, :391 GET /infra/connect-test | `az` control plane on the Mac; SSH connector; keeps the NSG pinned to a single dynamic IP |
| C-023 | Health and status probes | app.py | app.py:70 /voice/_status, :79 /v2/_status, :88 /soc/_status, :97 /notifications/_status, :106 /meeting/_status, :115 /auth/_status, :124 /api/v1/_status, :134 /anchor/v1/_status, :159 /hubspot/_status, :168 /directions/_status, :177 /audit/_status, :186 /ui/_status, :439 /health | Status for each sub-router plus overall health |
| C-024 | External API (single access layer) | server/external_api.py (84) | external_api.py:45 GET /health, :49 GET /projects, :57 POST /p/{identifier}/ask | Third parties ask a project questions; keys from `gen_test_keys.py` |
| C-025 | Anchor Connect: request lifecycle and poller | server/anchor.py (320), anchor_queue.py (449), local_poller_http.py (369), anchor_remote.py (583), shared/infra/anchor/* (Dockerfile, compose, nginx, systemd) | anchor.py:58 POST /requests, :69 GET /requests/{rid}, :76 POST /requests/{rid}/ack, :81 GET /poll, :86 POST /requests/{rid}/result | Smart queue; the remote anchor (with a stand-in now) is polled by the local Mac; external request → local execution → result |
| C-026 | Anchor admin and landing management | anchor.py, anchor_manage.py (165) | anchor.py:92 GET /admin/config, :96 POST /admin/config, :100 GET /admin/requests, :104 GET /admin/counts | Admin config, request listing and counts; protected landing-page management |
| C-027 | Anchor simulators and test harness | sim_server.py (276), webhook_receiver.py (115), third_party.py (66), e2e_anchor*.py, e2e_phase2*.py, shared/infra/phase3_e2e.py, phase3_gate.py, testing/isolate_anchor.py, test_anchor_online.py | (own servers; no routes listed) | Third-party request page (anchor_sim.html, SQLite), webhook reply viewer, CLI third-party, Phase 1–3 E2E and gates |
| C-028 | Workspace audit and observer | server/workspace_audit.py (528), shared/config/audit-config.json | workspace_audit.py:489 GET /status, :493 GET /scan, :497 POST /run, :501 GET /violations, :505 GET /config, :509 POST /config, :513 GET /mirror | Debounced, self-healing safety net; scope violations; mirror |
| C-029 | Truth gate, creation door, read-only hook | server/audit.py (198), workspace_mw.py (1007), readonly_hook.py (81) | (internal) | Verifies every agent's success claims; single door for creating workspace content; Claude Code PreToolUse read-only enforcement |
| C-030 | Directions (knowledge layer) | server/directions.py (149), workspace/shared/directions/ | directions.py:129 GET /overview, :133 GET /find, :137 GET /capability, :141 GET /resources, :145 GET /similar | Schema-backed knowledge: find a capability, resources, similar projects (Phase 4) |
| C-031 | UI contract (generic) | server/ui_api.py (215) | ui_api.py:191 GET /projects, :197 GET /project/{pid}, :201 GET /agents, :207 GET /types, :211 GET /connectors | Read model for all clients (Phase 6) |
| C-032 | Notifications | server/notifications_api.py (37), notifications_store.py (63) | notifications_api.py:9 GET /notifications, :14 GET /count, :19 POST /read, :25 POST /clear, :31 POST /test | Sync feed for recurring and periodic work (separate from the Guide / "What's new" feed) |
| C-033 | SOC core: status, settings, run, report | server/soc_api.py (125), soc_run.py (1343), soc_blueprint.py (124) | soc_api.py:14 GET /soc/status, :26 GET /soc/settings, :31 POST /soc/settings, :36 POST /soc/run, :42 GET /soc/report?fmt= | RedBerry SOC run engine with live DB settings; the blueprint turns any project into a SOC |
| C-034 | SOC findings lifecycle | soc_run.py | soc_api.py:97 POST /soc/finding | Owner status per finding (open, pending, accepted, resolved) in the findings registry |
| C-035 | SOC asset inventory | server/soc_inventory.py (204) | soc_api.py:57 GET /soc/inventory | Asset and attack-surface map; stack fingerprints |
| C-036 | SOC recovery, backup, escrow | server/soc_recovery.py (225) | soc_api.py:64 GET /soc/recovery, :71 POST /soc/backup, :78 POST /soc/escrow | Encrypted backups and registry, smart restore plan, key escrow |
| C-037 | SOC quota and abuse-cost monitor | server/soc_quota.py (106) | soc_api.py:85 GET /soc/quota | Generic third-party quota and spend monitor (Klaviyo/HubSpot drain) |
| C-038 | SOC UEBA behaviour | server/soc_behavior.py (161) | soc_api.py:91 GET /soc/behavior | Per-IP behaviour profiles; low-and-slow detection |
| C-039 | SOC intel, fusion, hunting, enrichment, prediction | soc_intel.py (144), soc_intel_fusion.py (139), soc_hunt.py (94), soc_enrich.py (89), soc_predict.py (103) | (via /soc/run) | OSV, KEV and abuse.ch intel; hypothesis hunting; auto-triage and enrichment; threat prediction |
| C-040 | VM Security Sentinel | server/security_sentinel.py (155), testing/vm_security_audit.py | soc_api.py:105 GET /sentinel/status, :111 POST /sentinel/run | Vertical VM security monitor with RED/GREEN output |
| C-041 | HubSpot operator API | server/hubspot_api.py (136) | hubspot_api.py:105 GET /status, :113 GET /overview, :119 GET /scopes, :127 POST /run, :132 POST /ask | Endpoints for the HubSpot operator agent (scope-aware) |
| C-042 | Meeting monitor (voice asset) | server/meeting_api.py (548), zoom_pipeline_run.py (183), dashboard/meeting_monitor.html | meeting_api.py:397 GET /meeting/capable, :408 GET /state, :420 POST /clear, :431 POST /chunk, :457 POST /finish, :474 POST /finish_text, :504 GET /view, :508 GET /report, :528 GET /report_all | Live meeting capture → chunks → report and export; one UI shared by web, desktop and mobile; autonomous Zoom pipeline run |
| C-043 | Voice STT and TTS | voice/backend/voice_service.py, voice/frontend, shared/config/features/voice.json | voice_service.py:165 POST /stt, :178 GET /tts | Speech to text and text to speech for voice-first use |
| C-044 | Shared JSON store | server/store.py (183) | (internal) | Persistence for projects, agents, scopes, models… |
| C-045 | E2E capability and timing tests | e2e_ai_capability.py (318, "frozen measuring stick"), e2e_cache_timing.py, e2e_phase1_*.py (hard_deploy, shared_context, strong), run_timer.py, data/run_timings.json | (scripts) | Capability benchmark; caching timing; Phase-1 shared-context and hand-off tests |
| C-046 | Scope behaviour tests | scope_guide_test.py (341), scope_reasoning_test.py (257), test_intent.py (54) | (scripts) | Behavioural and reasoning-level audit of the smart-scope middleware; intent tests |
| C-047 | Test keys | gen_test_keys.py (60) | (script) | Ensures test auth keys exist |
| C-048 | Shared testing harness | workspace/shared/testing/* (harness, run_all, preflight, phase7_*, e2e_real_flow, e2e_soc, trace_chain, loop/monitor.sh, readonly_* per project, sandbox_*_check, seed_connectors, test_web_online, voice_test.html, PROMPTS_USED_IN_TESTS.md) | (scripts) | Reusable test framework that projects extend through manifests (Revealer overlay `tests/`) |
| C-049 | Shared deploy tooling | workspace/shared/infra/* (DEPLOY-PLAYBOOK.md, DEPLOY-PROMPT.md, deploy.sh, deploy.config.sh, deploy_run.sh, deploy_changes.py, deploy_verify.py, deploy-lists/, manifests/, azure/) | (scripts) | One deploy protocol shared by all projects (firewall IP refresh → SSH → rsync → build → restart → verify) |
| C-050 | System config | workspace/shared/config/ (company-profile.json, system-identity.json, models.json, audit-config.json, agent-types {operational, security, technical}, project-types {normal, one-time, periodical, recurring, vertical}, features/voice.json) | – | Typing and identity configuration behind agents, projects and features |

---

## 4. Clients

### 4a. Desktop (Electron + React): `desktop/`
| File | Lines | Suggests |
|---|---|---|
| src/App.jsx | 498 | Shell, routing and layout |
| src/views.jsx | 2961 | The main views (projects, agents, approvals, schedules, SOC, audit…); a monolith |
| src/ChatPanel.jsx | 553 | Scoped chat panel with streaming and a stop control |
| src/Conversations.jsx | 179 | Conversation list (chats) |
| src/api.js | 242 | REST/SSE client to the local brain |
| src/ui.jsx | 137 | Shared UI primitives |
| src/theme.css | 250 | Theme |
| src/main.jsx | 6 | Entry point |
| electron/main.cjs | 229 | Electron main (starts the brain, DMG) |
| electron/preload.cjs | 11 | Preload bridge |
| Backups | – | ChatPanel.jsx.bak_banner (520), ChatPanel.jsx.bak_nostop (553), electron/main.cjs.bak_poller (220) |

### 4b. Flutter web and mobile: `odin_app/lib/` (10,306 lines in total)
| File | Lines | Screen / feature it suggests |
|---|---|---|
| screens/whatsapp.dart | 881 | WhatsApp-style chat UI (main conversation screen) |
| screens/bell.dart | 780 | Bell, notifications and approvals centre |
| screens/project_detail.dart | 758 | Project detail (team, rules, runs, deploy) |
| screens/new_project.dart | 369 | New-project and intake wizard |
| screens/docs.dart | 214 | Docs and reports viewer |
| screens/meeting_sheet.dart | 211 | Live meeting / voice capture sheet (voice asset) |
| screens/audit_screen.dart | 206 | Workspace audit and violations |
| screens/notifications_panel.dart | 180 | Notifications feed |
| screens/schedule_editor.dart | 163 | Scheduler editor (daily/periodic) |
| screens/agent_detail.dart | 155 | Agent detail and rules |
| screens/ui_agents.dart | 128 | Agents roster (ui_api) |
| screens/projects_screen.dart, home_screen.dart | 1 each | Empty or stub screens |
| api/anchor_api.dart | 838 | API client (anchor-aware: talks to the remote anchor or local) |
| main.dart / config.dart / theme.dart | 77 / 125 / 169 | Bootstrap, endpoint config, theming |
| services/voice.dart, speech_text.dart, speech_web(_stub).dart | 148 / 59 / 44+5 | Voice input and STT |
| services/sse*.dart | 8 / 28 / 27 / 3 | SSE streaming (io, web, stub) |
| services/notifications*.dart | 12 / 42 / 12 | Local and mobile push notifications |
| services/biometric*.dart | 7 / 30 / 10 | Biometric unlock (mobile) |
| services/cert_override*.dart | 4 / 19 / 2 | TLS certificate override for self-signed anchor certs |
| services/web_open*.dart, recpath*.dart | 48+6 / 5+4+1 | Open URLs on web; recording path |

### 4c. Dashboard (static web): `dashboard/`
| File | Suggests |
|---|---|
| index.html | Main web cockpit |
| console.html | Console / chat |
| mobile.html | Mobile web view |
| audit.html | Workspace audit viewer |
| meeting_monitor.html | Live meeting / voice asset UI |
| artifact.html | Artifact / report viewer |
| odin-md.js | Markdown renderer |
| README.md | Docs |

Also present: `voice/frontend/` (voice UI) and `workspace/shared/testing/voice_test.html`.

---

## 5. Suspicious / to verify

1. **Referenced files that are missing from the bundles (verify):** `shared/utils/INSTALL_SOC_SENSOR.md` (manifests P-04 and P-08; B6 does not list shared/utils), `deploy/revealer-6978.config.sh` (overlay), `workspace/shared/tutorials/veeqo_fulfillment_api.md`, `workspace/shared/directions/ORCHESTRATOR.md`, `shared/assets/global_voice_streaming_asset.md`, `workspace/anchor-layer/`, `data/hubspot_scopes.json`, `data/soc_settings.json`, the `anchor_sim.html` page, and the `data/projects/<pid>/skills/*.md` files.
2. **Agents referenced with no folder:** Analytics, CloudDebug (an Organics member, also missing from its agents.json), Mobile, "Enrich/Intel"; SOC aliases AssetSurface, Predictor, Recovery and BehaviorIDS; test members ZzTestMember and ZzGapMember (still in Organics instructions.md).
3. **Duplicate agents:** reporter = reporting-documentation-agent (identical capability); content and content-creator (plus the archived "marketing"); qa and qa-reviewer-operational; the generic security agent overlaps the 11-agent SOC team.
4. **Stub or corrupted agent records:** reporter, sales and security index.json have `__auto_link_stub__`; hubspot capability.md has a truncated garbage description (also stored in the Organics agents.json, where the avatar is devops and nature technical); qa-reviewer-operational's rule text is stored three times with a pasted chatbot tail; the audio-capture rule is duplicated.
5. **company:true** is set only on EasyPost, and it was auto-added to P-03 without appearing in `members`. Confirm the "auto-add to every project" behaviour; other projects don't have it.
6. **Project member drift:** P-08 members include aliases and lack the 4 expansion agents that are in its agents.json; P-03 members lack EasyPost; P-01 instructions.md still lists excluded agents; P-04 doesn't recruit the analytics, customer-support, HubSpot or extra security roles its own description asks for.
7. **Type and taxonomy inconsistencies:** project `type` values (content, email, fulfillment, crm, arm, operational, web, marketing) don't match `config/project-types` (normal, one-time, periodical, recurring, vertical); cadence "once" vs config "one-time"; **vm-sentinel type = marketing** with schedule `{}` while periodic is enabled, and no security agents; agent `nature` vs `type` mismatches; the `projects` field mixes names and slugs; devops lists the project "Organics Production Deploy (2VM)", which doesn't exist (the real project is the staging Organics one).
8. **Risky flags:** `auto_approve: true` on P-04 and P-09; SOC and Zoom `requireApproval: false`; `deploy_ssh.py` and the DevOps resources use **password SSH** from `oth/.cred`; DevOps `index.json` names a production deploy while P-07 is staging-only.
9. **Duplicate or overlapping server modules and routes:** two chat systems (app.py `/chats*` and `/chat/stream` vs api_v2 `/chats*` + `chats.py` + scope chats); `/projects` in api_v2, ui_api and external_api; `/connectors` in api_v2 and ui_api; `/health` in app.py and external_api; `/status`, `/overview` and `/config` in several routers; approvals split between api_v2 and soc_api (`/approvals/approve-all`); `/sentinel/*` lives inside soc_api.
10. **Modules with no routes listed:** anchor_remote.py (583 lines, a "stand-in deployed anchor"; its routes didn't appear in the grep, so check the decorator style), anchor_manage.py, sim_server.py, webhook_receiver.py, local_poller_http.py. There is also a gap in app.py routes at lines 134–159 (possibly mounts).
11. **Test code inside `server/`:** 12 e2e_* files, scope_*_test.py, test_intent.py (empty docstring), gen_test_keys.py, third_party.py. These should move to testing/.
12. **Monoliths:** api_v2.py (3568 lines), projects.py (1488), soc_run.py (1343, hard-coded "RedBerry" in a generic server), workspace_mw.py (1007), desktop views.jsx (2961).
13. **The B6 grep for `voice/*.py` failed:** there are no top-level voice modules (only voice/backend/voice_service.py), so voice module docstrings weren't captured.
14. **Empty or stub Flutter files:** projects_screen.dart and home_screen.dart (1 line each), recpath_stub.dart (1 line).
15. **.bak files of note:** desktop ChatPanel.jsx.bak_banner, .bak_nostop, electron/main.cjs.bak_poller (a poller was once in Electron); infra DEPLOY-PROMPT.md, deploy.config.sh, deploy.sh, deploy_run.sh, deploy_changes.py and deploy_verify.py `.bak_staging_<ts>`, deploy.sh.bak_ufwfix, azure/connection.profile.json.bak_staging_*; `__pycache__` folders in shared infra and testing.
16. **Data quality:** P-01 description has a duplicated owner paragraph; the zoom-real-flow final_report.md came from an empty transcript (the capture pipeline didn't record); the P-07 description says "odin_core DB stores a reference to the external report path", so check that the field exists (it isn't in index.json).
17. **Path inconsistency in the SOC docs:** the KB is under `data/projects/redberry-continuous-soc/soc/` vs a separate folder `~/Desktop/AiAgentWorkSpace/RedBerry-Continuous-SOC/soc/`; the run engine is named `soc_engine` (asset in SOC agents.json) vs `soc_run` (full-services agents.json).
18. **"Phase 1a INDEX/REFERENCE ONLY" notes** on most agent and project index files mean the real data still lives in `data/projects/<pid>`, so the workspace/ copies may be stale.


<!-- ==================== PART D ==================== -->

# Inventory D — Build/Run/Release, Environments, Third-party Sim, Tests, Paper Additions, Missing Items

Sources: `_phase1_bundles/B5a_build_full.txt` (full), `B5b_build_heads.txt` (first 60 lines per file + extracts), `B7_paper.txt` (research notes, paper sections, P2 diff, new files).
Rules applied: no secret values copied (API keys, passwords, VM password, sandbox DB password, app login password are all present in sources — only their existence is noted). The VM is called "the VM".
Caveat: B5b shows only file heads, so behaviour beyond line 60 is not confirmed.

---

## 1. Build, run and release machinery

| ID | Target / script | What it does | Exact command(s) | Files / env vars it depends on | Touches VM/cloud? | Notes |
|---|---|---|---|---|---|---|
| D-001 | `desktop/package.json` → `dev` | Desktop cockpit in dev mode: starts Vite (:5173), waits for the port, then launches Electron with logging | `cd desktop && npm install && npm run dev` (runs `concurrently -k "vite" "wait-on tcp:5173 && ODIN_DEV=1 ELECTRON_ENABLE_LOGGING=1 electron ."`) | `vite.config.js` (port 5173, strictPort), `electron/main.cjs`, `ODIN_DEV=1` (loads the Vite dev server) | No | Electron 31, React 18, Vite 5, Framer Motion 11. Product name "Odin", appId `ai.odin.orchestrator` |
| D-002 | `desktop` → `build` | Production web bundle of the React UI into `desktop/dist` (base `./` so it loads from `file://`) | `cd desktop && npm run build` | `vite.config.js` (`base:"./"`, `outDir: dist`, `emptyOutDir`) | No | |
| D-003 | `desktop` → `dist` (DMG release) | Builds with the production env baked in, then packages a macOS DMG via electron-builder | `cd desktop && npm run dist` (= `VITE_ODIN_ENV=production vite build && electron-builder --mac dmg`) | `VITE_ODIN_ENV=production`; `build` block in package.json (output `release/`, `buildResources: build`, files `dist/**`, `electron/**`, `package.json`, icon `build/icon.png`, category developer-tools, DMG title "Odin ${version}"); `afterPack: ./build/afterpack-sign.cjs` | No | `mac.identity: null` → no Developer ID signing; ad-hoc signing done in afterPack (D-005). Output: `desktop/release/*.dmg` |
| D-004 | `desktop` → `pack` | Unpacked app directory (no DMG) for quick local testing | `cd desktop && npm run pack` (= `npm run build && electron-builder --dir`) | same as D-003 | No | Does NOT set `VITE_ODIN_ENV=production` (unlike `dist`) |
| D-005 | `desktop/build/afterpack-sign.cjs` | electron-builder afterPack hook: `xattr -cr` on the .app, then `codesign --force --deep --sign -` (ad-hoc) and `codesign --verify --deep --strict` | runs automatically during D-003 / D-004 | macOS `xattr`, `codesign` | No | Ad-hoc signature only; Gatekeeper will still treat it as unidentified developer |
| D-006 | `desktop` → `vite`, `electron` | Run Vite alone or Electron alone | `npm run vite`, `npm run electron` | — | No | |
| D-007 | `desktop` → `e2e`, `e2e:quick` | Intended desktop e2e | `npm run e2e` → `python3 ../tests/e2e.py`; `npm run e2e:quick` → `python3 ../tests/e2e.py --quick` | `../tests/e2e.py` | Unknown | **Target not found** in any listing (see section 6) |
| D-008 | `desktop/electron/main.cjs` (packaged app launch) | On launch: checks `127.0.0.1:<port>/health`; if down, finds the project root and spawns `bash server/run.sh` with Homebrew PATH restored and `USE_VOICE` default 1; also holds a `poller` handle bridging to the online anchor | Double-click Odin.app (from DMG) or D-001 | `ODIN_DEV`, `ODIN_PORT` (default 8000), `ODIN_ANCHOR` (default the production anchor URL `https://anchor.odinmarkets.com/odin-anchor`), `ODIN_ROOT`; saved root in `userData/root.txt`; fallback `~/Desktop/AiAgentWorkSpace/Odin-Orchestrator` | Yes (poller talks to the online anchor in production) | Heavy Python/venv/voice stays in the project folder, not in the .app. Preload exposes `window.odin.{pickFolder, pickFolders, pickFiles, startRequestPage, isDesktop}` |
| D-009 | `server/run.sh` | Launches the local brain (FastAPI `server.app:app` via `python -m uvicorn`) with voice + chat; frees the port first (kills stale pids) | `bash server/run.sh` (or `USE_VOICE=1 ./server/run.sh`) | `ODIN_VENV`/`.venv`/`venv`/`../.venv`/`~/.venvs/odin`; `PORT` (8000); `USE_VOICE` (1); `ODIN_OLLAMA_MODEL` (qwen2.5:7b-instruct-q4_K_M); `ODIN_WHISPER_MODEL` (medium); optional `ODIN_PIPER_AR_MODEL`; `ODIN_HOST` (127.0.0.1); `ODIN_RELOAD=1` (reload dirs `server`, `orchestrator` only) | No | Reload is OFF by default because the server writes its own data files (failure #4 in the paper timeline) |
| D-010 | `server/app.py` (manual) | Same brain; docstring run form | `pip install -r server/requirements.txt -r voice/backend/requirements-voice.txt` then `USE_VOICE=1 uvicorn server.app:app --reload --port 8000` | `ODIN_ACCESS_TOKEN` (optional gate: `/chat`, `/dispatch`, `/voice` need `X-Odin-Token` header or `?token=`) | No | Endpoints: `/`, `/state/*`, `/history/*`, `POST /voice/stt`, `GET /voice/tts`, `POST /chat`, `/health`. CORS `*`. App version 0.4.0 |
| D-011 | `shells/development_full_checker.sh` (= **Phase 2, development**) | Full local stack: venv + pip (+ faster-whisper), `gen_test_keys.py`, deletes `anchor_prod.js`, asks "Run WITH the anchor? [Y/n]", starts brain (:8000), anchor_remote (:9100, Postgres DSN with JSON fallback) + supervised poller, webhook receiver (:9300), writes `workspace/anchor-layer/anchor_seed.js`, starts `sim_server.py` (:9104) and opens `anchor_sim.html`, opens anchor landing page, starts control bridge `phase_ctl.sh`, launches desktop (`npm run dev`), Flutter: create platforms once, `pub get`, launcher icons, `flutter analyze` compile check, **release web build** with `ODIN_FORCE_ENV=phase2` served by a no-cache Python server on :8080 and auto-opened, iOS simulator clean build + `simctl install/launch` | `bash shells/development_full_checker.sh` (non-interactive: `USE_ANCHOR=1 bash shells/development_full_checker.sh`) | Env: `ODIN_VENV`, `BRAIN_PORT` 8000, `ANCHOR_PORT` 9100, `WEB_PORT` 8080, `ANCHOR_SIM_PORT` 9104, `WEBHOOK_PORT` 9300, `USE_ANCHOR`, `USE_VOICE` (0), `ANCHOR_PG_DSN` (`dbname=odin_anchor`), `OPEN_SIM` (1), `OPEN_DESKTOP` (1). Files: `server/requirements.txt`, `server/gen_test_keys.py`, `workspace/shared/oth/.cred` (ANCHOR_API_KEY), `odin_app/`, `desktop/`, Flutter at `~/development/flutter/bin` or brew cask | No (local only; bridge can reach the VM via `vm` command) | Ctrl-C cleanup kills every port it opened (9100, 8080, 9300, 9104, 5173, and 8000 only if it started the brain), Electron/Vite scoped to project path, flutter web-server. Prints the dev app login (credential present in script — not copied). Logs: `workspace/logs/{brain,anchor_remote,local_poller,poller_supervisor,webhook,anchor_sim,phase_ctl,desktop,analyze,web_build,app_web,app_ios}.log` |
| D-012 | Flutter web build (dev) | Release web build pointing at the local anchor only (empty apiBase) | `cd odin_app && flutter build web --release --dart-define=ODIN_FORCE_ENV=phase2` then serve `odin_app/build/web` (script writes `workspace/logs/_web_serve.py <port> <dir>`) | `--dart-define=ODIN_FORCE_ENV=phase2` | No | Chosen over `flutter run -d web-server` because the debug build hangs on the splash in a plain browser |
| D-013 | Flutter web build (production) | Production web build with sub-path and online anchor baked in | `cd odin_app && flutter build web --release --base-href /odin-web/ --dart-define=ODIN_FORCE_ENV=production --dart-define=ODIN_ANCHOR=https://<domain>/odin-anchor` | `ODIN_FORCE_ENV=production`, `ODIN_ANCHOR` | Built locally; shipped to the VM by D-020 | |
| D-014 | iOS simulator install (dev) | Clean simulator build then install + launch via simctl (avoids Xcode error 74 on incremental `flutter run`) | `flutter build ios --simulator --debug --dart-define=ODIN_FORCE_ENV=phase2` → `xcrun simctl install <UDID> build/ios/iphonesimulator/Runner.app` → `xcrun simctl launch <UDID> <bundle id>` | `xcrun`, Simulator; boots first available iPhone if none booted; bundle id read via PlistBuddy (fallback `com.mostafaadawy.mobileapp`) | No | `flutter config --no-enable-swift-package-manager` is set first |
| D-015 | iPhone (real device) install (production) | Phase 3 prefers a physical iPhone; never falls back to a simulator; waits up to ~15 min (180×5 s) for a trusted USB device | `cd odin_app && flutter run --release -d <device id> --dart-define=ODIN_FORCE_ENV=production --dart-define=ODIN_ANCHOR=<anchor base>` | `flutter devices --machine` (non-emulator iOS); Xcode signing team required (Runner ▸ Signing); `ODIN_SKIP_MOBILE=1` defers | No | Final banner text still says "MOBILE sim … iOS simulator" — inconsistent with the no-simulator policy |
| D-016 | Android | Platform folder scaffolded only | `flutter create . --platforms web,android,ios --project-name odin_app --org com.odin` (run once by D-011); launcher icons: `dart run flutter_launcher_icons` (android adaptive icon background `#0E1320`, fg `assets/icon/odin_icon_fg.png`) | `pubspec.yaml` | No | **No Android build/install command exists in any script** (no `flutter build apk/appbundle`, no `flutter run -d android`) |
| D-017 | `odin_app/pubspec.yaml` | Flutter companion app "Phase 2": projects, chat, Anchor Connect status page; web/Android/iOS | `flutter pub get`; `dart run flutter_launcher_icons` | Flutter ≥3.27, Dart ≥3.6; deps: http, provider, shared_preferences, intl, flutter_local_notifications, flutter_tts, speech_to_text, local_auth (Face/Touch ID), image_picker, file_picker, record, audioplayers, cross_file | No | `main.dart`: error widget instead of white screen, `runZonedGuarded`, `installOdinCertOverride()` (trusts the VM's self-signed cert on mobile/desktop), title "Odin — Remote Anchor", login gate |
| D-018 | `shells/production_full_checker.sh` (= **Phase 3, production/online**) | 1) `phase3_gate.py init` + `compare` → DECISION FIRST_RUN / CHANGED / SAME; 2) FIRST_RUN always deploys; CHANGED asks `[y/N]` (or `ODIN_PHASE3_YES=1`); SAME just starts; 3) on deploy: `phase3_gate.py validate` (read-only VM checks), `deploy-anchor` (overwrite VM anchor folder from deploy copy, Postgres link, restart existing service), production web build (D-013) + `deploy-web`, `phase3_e2e.py`, then `snapshot` (stamps first-run flag); exits 1 on failure; 4) writes `anchor_prod.js` (window.ODIN_PROD with empty brain, anchor/wh = online anchor base, key) and production `anchor_seed.js`; 5) starts local brain, supervised poller → online anchor, webhook receiver; 6) opens request page `anchor_sim.html?env=prod` (served by plain `http.server` on :9104 from `workspace/anchor-layer`), online web, online anchor landing; desktop with `VITE_ODIN_ENV=production npm run dev`; Flutter web-server on :8080 with production defines; real iPhone (D-015) | `bash shells/production_full_checker.sh` (automation: `ODIN_PHASE3_YES=1 bash shells/production_full_checker.sh`) | Env: `BRAIN_PORT` 8000, `ODIN_ANCHOR_PORT` 48619, `WEB_PORT` 8080, `WEB_VM_PORT` 48620, `WEBHOOK_PORT` 9300, `ANCHOR_SIM_PORT` 9104, `ODIN_SERVER_NAME` (default `anchor.odinmarkets.com`), `ODIN_PHASE3_YES`, `OPEN_DESKTOP`, `ODIN_SKIP_MOBILE`. Files: `workspace/shared/infra/phase3_gate.py`, `phase3_e2e.py`, `.cred`, `server/requirements.txt` | **Yes** — SSH to the VM, overwrites `/home/mostafa/anchor-online` and `/home/mostafa/odin-web`, restarts service `odin-anchor-online` and the web service, Postgres on the VM; reached via nginx 443 at `/odin-anchor` and `/odin-web` (existing SSL reused) | Never touches Phase 2 config or original folders; deploy copies live in `workspace/projects/odin-external-arms/deploy/{anchor,web}`; first-run flag `workspace/logs/.phase3_firstrun_done`. Logs: `phase3_compare/validate/deploy/e2e.log` |
| D-019 | `workspace/shared/infra/phase3_gate.py` | Decision brain for Phase 3 | `python3 workspace/shared/infra/phase3_gate.py init|compare|validate|snapshot|deploy-anchor|deploy-web` | Exit codes: compare 0=SAME, 10=CHANGED, 20=FIRST_RUN; validate 0/1. Anchor files shipped: `store.py, anchor.py, anchor_queue.py, anchor_manage.py, anchor_remote.py, local_poller_http.py` + `.cred`; web = `odin_app/build/web`; web fingerprint from `lib/**/*.dart`, `web/**`, `pubspec.yaml` | Yes (validate = read-only SSH/proxy/SSL/paths/PostgreSQL/env/firewall; deploy-* = writes) | `deploy-anchor`/`deploy-web` are called by D-018 but not in the docstring's subcommand list (only head seen) |
| D-020 | `shells/anchor_loop.sh` | One long-running controller for both phases, agent-driven through files: RUN file = `phase2` / `phase3` / `stop` / `done` (alias close/exit/quit); also accepts typed commands in the foreground | `nohup bash shells/anchor_loop.sh > workspace/logs/anchor_loop.log 2>&1 &` (header says `bash anchor_loop.sh`) | `workspace/logs/phase_ctl/{RUN,STATUS}`; frees ports 9100, 9104, 9300, 8080 | Phase 3 path yes | `phase3` is a "hybrid gate": only when owner and agent agree Phase 2 is good. On close, the online VM anchor stays up as its own service. Run logs `workspace/logs/phase2_run.log`, `phase3_run.log` |
| D-021 | `shells/anchor_up.sh` | Offline drill companion: brings up ONLY anchor (:9100) + poller (4 s) in a separate terminal; starts the brain if absent; opens anchor landing page | `bash shells/anchor_up.sh` | `BRAIN_PORT` 8000, `ANCHOR_PORT` 9100, `ANCHOR_PG_DSN`, `ODIN_VENV` | No | Drill: start Phase 2, answer "n" → web/Flutter must show "You are offline" and no data; then run this and refresh → data appears. Ctrl-C stops only anchor + poller |
| D-022 | `shells/poller_supervisor.sh` | Keeps `local_poller_http.py` alive forever; relaunches within ~5 s if `pgrep -f "[l]ocal_poller_http.py --anchor"` finds nothing | `nohup bash shells/poller_supervisor.sh <anchor url> <interval> &` (dev: `http://localhost:9100 4`; prod: online anchor base, 4) | `workspace/logs/local_poller.log`, `poller_supervisor.log`; venv | Prod: yes (polls the online anchor) | Fixes the "queue silently stops" crash (SIGHUP on detach) |
| D-023 | `server/local_poller_http.py` | The Mac's worker: `GET /anchor/v1/poll`, runs each task through the real CTO→team orchestration (`anchor.process`) with read-only connector data, posts the result back; pushes project list / pools / mirror to the anchor | `python3 server/local_poller_http.py --anchor http://localhost:9100 [--interval 4]` | `ANCHOR_API_KEY` via `integrations.cred` → `X-API-Key` | Prod: yes | Accepts self-signed HTTPS (`CERT_NONE`) |
| D-024 | `server/anchor_remote.py` | Stand-in (and the deployed) anchor serving `/anchor/v1` over HTTP, no local processor; WhatsApp-style durable sync store (`anchor_sync.json`: projects, agents, pools, mirror, updated) | `python3 server/anchor_remote.py --host 0.0.0.0 --port 9100` (dev scripts run it from `server/` with `ANCHOR_PG_DSN=dbname=odin_anchor`) | `anchor_queue`, `anchor_manage`, `store`; `ANCHOR_API_KEY` | On the VM in Phase 3 (port 48619 behind nginx) | Third-party intake open; key needed on poll/result/admin |
| D-025 | `shells/phase_ctl.sh` | Control bridge (agent writes one command into `workspace/logs/phase_ctl/CMD`, reads `OUT.log`/`STATUS`). Commands: `health`/`status`, `send <project_id> <prompt…>`, `tail <brain|anchor_remote|local_poller|webhook|anchor_sim|phase3_deploy>`, `vm`, `redeploy`, `trace`, `isolate`, `audit`, `auditfix` | started by D-011 (`bash phase_ctl.sh` — see section 6) | `BRAIN_PORT`, `ODIN_ANCHOR_PORT`/`ANCHOR_PORT`, `ANCHOR_SIM_PORT`, `WEBHOOK_PORT`, `VM_IP`, `PROXY_HOST`; `.cred` ANCHOR_API_KEY | `vm` (read-only SSH via `deploy_ssh`), `redeploy` (runs `test_anchor_online.py`), `trace`, `isolate`, `audit` read the VM; **`auditfix` changes ufw + NSG** (removes 48619/48620) | `send` polls up to 40×3 s and returns as soon as `result` is filled (status may stay `ack_pending` because the VM cannot reach the Mac's localhost webhook). Help text omits trace/isolate |
| D-026 | `shells/agent_terminal_bridge.sh` | Lets the agent run commands in the owner's Mac shell: agent writes `workspace/logs/agent_term/CMD`; loop prints, runs with stdin `/dev/null`, output to file (not `$()` pipe), hard timeout watchdog; output in `OUT.log`, state in `STATUS` | `bash shells/agent_terminal_bridge.sh` (Ctrl-C revokes) | `ODIN_VENV`, `ODIN_CMD_TIMEOUT` (default 900 s) | Indirectly (owner shell has az/ssh) | Hang-proof design documented. Proposal P1 moves its runtime files out of the git folder |
| D-027 | `workspace/shared/infra/deploy.sh` (RBO / organics deploy engine) | Phase A read-only preflight (cred `azvmcred` from `.cred`, tools sshpass/rsync/ssh/az/curl, local folders, public IP, VM IP via `az vm show`, NSG port-22 rule → my /32, ufw rotation via `az vm run-command` keeping 80/443 open, SSH test ×3, self-heal sshd restart via control plane); Phase B rsync (no `--delete`, big exclude list), migration (`new` = `prisma generate && migrate deploy`; `reset` = destructive), build, extra steps, restart configured services (or full reboot if none + `CFG_REBOOT=1`), verify backend port; updates baseline lists only on full success; summary table | `bash workspace/shared/infra/deploy.sh` · `--dry-run` · `backend` · `frontend <subfolder>` · `--print-config` | `deploy.config.sh` (optional, `CFG_*` overrides) or `ODIN_DEPLOY_CONFIG`; `ODIN_MIG_OVERRIDE`; `.cred` (`azvmcred`); hardcoded RG/VM name/IP fallback/backend port 4013, local paths under `~/Desktop/VolatileWorkSpace/RBO-Staging/{b,f}`, VM `/home/mostafa/RBO-Staging/{b,f}` | **Yes** — NSG + ufw + SSH + rsync + build + service restart / reboot | Prints `__ODIN_REBOOTED__` commit marker (agent must not re-run after it). Normalises `/home/mustafa` typo. Log `workspace/logs/e2e-deploy-<ts>.log` |
| D-028 | `workspace/shared/infra/deploy_run.sh` | One-command organics deploy: STEP 0 `deploy_changes.py scan` (stop if no change), 0b `dbscan` → asks approve/deny destructive DB rebase (or `ODIN_DB_REBASE`), STEP 1 `deploy.sh`, STEP 2 `deploy_verify.py --since-epoch`, STEP 3 `deploy_changes.py update` | `bash workspace/shared/infra/deploy_run.sh` · `--bootstrap` (seed-old: everything changed) | `ODIN_DB_REBASE=approve|deny`, `ODIN_MIG_OVERRIDE` (exported), `.venv/bin/python` | **Yes** | Exit 3 when DB decision is needed non-interactively. Rules: SSH as mostafa, az only for firewall, never touch nginx/ports/other sites, never `npm run start` |
| D-029 | `workspace/shared/infra/deploy_changes.py` | Change detection by mtime against saved front/back lists; generic per project | `python …/deploy_changes.py scan | seed-old | update | changed backend | dbscan` (`--project <pid>` or `ODIN_DEPLOY_PROJECT`, default `organics-prod-deploy`) | per-project delta `workspace/projects/<pid>/deploy/deploy-config.json`; lists in `infra/deploy-lists/[<pid>/]` | No (local scan) | Excludes node_modules, dist, .next, logs, .git, migrations, env files, lockfiles |
| D-030 | `workspace/shared/infra/deploy_verify.py` | Strong post-deploy gate over SSH: fresh `dist/` and `.next/BUILD_ID`, backend :4014 and frontend :3001 return 200, DB users>0 / rbacRoles>0 / superadmin>0 / appSettings>0 (Prisma JS), auto-restart `bendcore-staging` once if DB empty | `python …/deploy_verify.py --since-epoch <ts>` · (default 45-min window) · `--no-fix` | `server/deploy_ssh.py` | **Yes** (SSH; restart once) | Born from 2026-07-16 incidents (reset under a running process; wrong port 3000 vs 3001; stale build passed) |
| D-031 | `workspace/shared/infra/ensure-connection.sh` | Run ON the VM: only opens 80/443 in ufw, reports ufw, running services, `nginx -t`, local 80/443/4013 — never denies/restarts | `bash ensure-connection.sh` (on the VM) | — | **Yes** (VM ufw allow only) | |
| D-032 | `workspace/shared/testing/loop.sh` | Autonomous test daemon: agent writes filter word into `testing/results/RUN_NOW` (restart) or touches `STOP`; runs `python3 testing/ <filter>` with `ODIN_TEST_SEED_ON_PASS=1`, `ODIN_GATE_MODEL=haiku`; results `latest.log`, `STATUS`, `RUN_SEQ` | `nohup bash testing/loop.sh > testing/results/daemon.log 2>&1 &` | `ODIN_GATE_MODEL`, `ODIN_TEST_PROD_DEPLOY=1` (Test 1 real prod deploy), `.venv` | Depends on filter (sandbox VM tests, Test 1) | Kills `claude -p You are` agents on stop. Path mismatch — see section 6 |
| D-033 | `workspace/shared/testing/monitor.sh` | Permanent live view: `tail -n 200 -F testing/results/latest.log` in a relaunch loop | `bash testing/monitor.sh` | — | No | |
| D-034 | `server/webhook_receiver.py` | Stand-in third-party webhook endpoint + viewer (section 3) | `python3 server/webhook_receiver.py --port 9300` | — | No | |
| D-035 | `server/sim_server.py` | Serves the request page + durable SQLite request log (section 3) | `python3 -u server/sim_server.py --host 127.0.0.1 --port 9104` | `ODIN_SIM_DATA` (default `workspace/anchor-layer`) | No | |
| D-036 | `server/third_party.py` | CLI third-party simulator (section 3) | `python3 server/third_party.py [--anchor http://localhost:9100] --project <pid> --prompt "…"` | `ANCHOR_API_KEY` | Only if `--anchor` is the online URL | |
| D-037 | Env/example files: `workspace/projects/full-services-19jul/code/frontend/.env.local.example` | Frontend API base | copy to `.env.local` | `NEXT_PUBLIC_API_BASE=http://localhost:4000/api` | Sandbox on the VM (internal port) | |
| D-038 | `workspace/projects/full-services-19jul/code/backend/.env.example` | "Odin Ops Platform" backend env template | copy to `.env` | `DATABASE_URL` (Postgres on :5544, db `odin_ops_sandbox`, placeholder password), `PORT=4000`, `HUBSPOT_API_KEY`, `KLAVIYO_API_KEY`, `VEEQO_API_KEY` (blank; provisioned from `.cred`), `*_BASE_URL` for HubSpot/Klaviyo/Veeqo | Sandbox DB on the VM | |
| D-039 | `anchor_prod.js` (repo root, generated) | `window.ODIN_PROD = {brain:"", anchor, wh, key}` — its presence makes the request page default to PRODUCTION | written by D-018; deleted by D-011 | — | Points at the online anchor | **Contains a live anchor API key in plain text** (value not copied) |
| D-040 | `anchor_seed.js` (repo root + `workspace/anchor-layer/`) | `window.ODIN_SEED = {key, webhook}` for the request page | written by D-011 (webhook `http://localhost:9300`) and D-018 (webhook = online anchor base) | `.cred` ANCHOR_API_KEY | — | Also holds the key in plain text |
| D-041 | Dashboard pages (served by the brain) | `dashboard/index.html` (CTO Brain dashboard + voice EN/AR), `console.html` (Odin Cockpit chat), `mobile.html` (phone UI with token field), `audit.html` (Audit/Observer: scan, run-now heal, silence-gap config), `meeting_monitor.html` (Live Meeting: chunked listening → report, export MD/Word), `artifact.html` (static snapshot dated 2026-06-21, 78 %) | open `http://localhost:8000/` , `/mobile.html`, etc. | `ODIN_ACCESS_TOKEN` for mobile | No | |
| D-042 | `server/scheduler.py` | Per-project scheduled prompts (once / interval / daily HH:MM) in a background thread; "Phase 3 periodic gate": due tasks with `requireApproval` go to `pending_approval`; missed runs roll forward without running | in-process (brain) | `schedules.json` via `store` | Depends on prompt | Statuses idle / pending_approval / running |
| D-043 | `server/claude_cli.py` | Engine wrapper around the `claude` CLI; read-only mode registers a PreToolUse Bash guard (`readonly_hook.py`, settings `.readonly-settings.json`); `--model` only for explicit haiku/sonnet/opus/claude-* (test loop uses haiku for gates); P2 adds scope hook (section 5) | in-process | `ODIN_GATE_MODEL` (via callers), `ODIN_SCOPE_HOOK` | No | |

Row count: 43

---

## 2. Environment and phases

### What the phase names mean (they are overloaded — four different meanings)
| Name | Meaning in these files |
|---|---|
| Phase 1 (anchor) | `server/anchor.py`: anchor API + poller **in-process** in the brain; contract `/anchor/v1`; tests `e2e_anchor*.py` |
| Phase 1 (context) | The single growing shared-context pool across agents; tests `e2e_phase1_*.py`, gate `e2e_phase2_gate.py` ("are we ready for Phase 2?") |
| Phase 2 | **Local development**: `development_full_checker.sh`; anchor = `anchor_remote.py` on localhost:9100 (stand-in for the VM); web/mobile built with `ODIN_FORCE_ENV=phase2` (anchor-only mode, empty apiBase); request page defaults to the local anchor. Also the name of the Flutter companion app ("Phase 2" in pubspec) |
| Phase 3 | **Online / production**: `production_full_checker.sh`; anchor and web deployed to the VM behind nginx 443 at `https://<domain>/odin-anchor` and `/odin-web`; clients built with `ODIN_FORCE_ENV=production` + `ODIN_ANCHOR`; brain stays local on the Mac and is only reached via poller ↔ anchor. Scheduler also uses "Phase 3" for its periodic approval gate (separate meaning) |
| Phase 7 | Workspace middleware / audit / lifecycle test harness (`phase7_*.py`) |
| Development vs production | Development = Phase 2 (all localhost). Production = Phase 3 (VM). Desktop: `VITE_ODIN_ENV=production` (DMG `dist` and Phase 3 dev run). `ODIN_DEV=1` = Electron loads Vite dev server |

### Selectors (env files / vars / flags)
- Flutter: `--dart-define=ODIN_FORCE_ENV=phase2|production`, `--dart-define=ODIN_ANCHOR=<url>`, `--base-href /odin-web/` (prod web).
- Desktop: `VITE_ODIN_ENV=production`, `ODIN_DEV=1`, `ODIN_PORT`, `ODIN_ANCHOR`, `ODIN_ROOT`.
- Request page: presence of `anchor_prod.js` (window.ODIN_PROD) → defaults to production; `anchor_sim.html?env=prod`; `anchor_seed.js` (window.ODIN_SEED); `anchor_env.json` (fetched by the page).
- Phase scripts: `USE_ANCHOR`, `OPEN_SIM`, `OPEN_DESKTOP`, `USE_VOICE`, `ODIN_PHASE3_YES`, `ODIN_SKIP_MOBILE`, `ODIN_SERVER_NAME`, `ODIN_ANCHOR_PORT`, `WEB_VM_PORT`, `VM_IP`, `PROXY_HOST`, `ANCHOR_PG_DSN`, `ODIN_VENV`, `ODIN_CMD_TIMEOUT`.
- Brain: `PORT`, `ODIN_HOST`, `ODIN_RELOAD`, `ODIN_OLLAMA_MODEL`, `ODIN_WHISPER_MODEL`, `ODIN_PIPER_AR_MODEL`, `ODIN_ACCESS_TOKEN`.
- Deploy: `ODIN_DEPLOY_CONFIG`, `ODIN_MIG_OVERRIDE`, `ODIN_DB_REBASE`, `ODIN_DEPLOY_PROJECT`, `deploy.config.sh` (`CFG_*`), `deploy-config.json` per project.
- Tests: `ODIN_GATE_MODEL`, `ODIN_TEST_SEED_ON_PASS`, `ODIN_TEST_KEEP`, `ODIN_TEST_CLEAN`, `ODIN_TEST_PROD_DEPLOY`, `ODIN_TEST_MAX_SECONDS`, `ODIN_DISABLE_CACHE`, `ODIN_ANCHOR_NO_POLLER`, `ODIN_ANCHOR_NGINX`, `ODIN_WEB_PORT`, `ODIN_ANCHOR_BASE`, `ODIN_E2E_REEXEC`, `ODIN_RUNALL_REEXEC`, `ODIN_SIM_DATA`.
- P2: `ODIN_SCOPE_HOOK=off|watch|enforce` (default enforce), `ODIN_SCOPE_HOOK_TRACE=1`, `ODIN_ACTOR_PID`, `ODIN_ACTOR_WORKDIR`, `ODIN_ROOT`. Proposed: `ODIN_BRIDGE_DIR` (P1).
- Credentials file: `workspace/shared/oth/.cred` (ANCHOR_API_KEY, azvmcred, VEEQO/KLAVIYO/HUBSPOT keys).

### Ports
| Port | Use |
|---|---|
| 8000 | Local brain (FastAPI) — internal, never opened as a page |
| 9100 | Local anchor (`anchor_remote.py`) in Phase 2 |
| 48619 | Online anchor on the VM (behind nginx 443, path `/odin-anchor`) |
| 48620 | Online web on the VM (behind nginx 443, path `/odin-web`) |
| 8080 | Local Flutter web (static release in Phase 2; `flutter run -d web-server` in Phase 3) |
| 9104 | Request page / CD-flow simulator (`sim_server.py` dev; `http.server` prod) |
| 9300 | Local webhook receiver |
| 5173 | Desktop Vite dev server |
| 443 / 80 / 22 | VM nginx (SSL reused) / existing sites / SSH (single /32) |
| 4013 | Organics backend verify port in `deploy.sh` and `ensure-connection.sh` |
| 4014 / 3001 | Staging backend (bendcore-staging) / staging frontend (organics-staging) in `deploy_verify.py` |
| 8531 | Sandbox port for Revealer / overwrite tests on the VM |
| 4000 / 5544 | full-services sandbox backend / its Postgres |
| 5432 | Postgres (owner's local; VM sandbox DB in `e2e_phase2_gate.py`) |
| Isolated copy | 18000, 19100, 19104, 19300, 18080; private Postgres 15432–15435; experiment servers 181xx |

---

## 3. Third-party request test & simulator

### Contract (`/anchor/v1`, from `anchor.py` / `anchor_remote.py`)
- Third party: `POST /anchor/v1/requests` `{project, prompt|payload, webhook_url, sender}` → `{request_id, status}`; `GET /anchor/v1/requests/{id}` → status, result, webhook_attempts, acked, error, history; `POST /anchor/v1/requests/{id}/ack` explicit acknowledgement.
- Local machine: `GET /anchor/v1/poll` → `{tasks:[…]}` (only un-handed-out, never finished); `POST /anchor/v1/requests/{id}/result {result}` → stored + webhook delivered with retries.
- Admin: `GET/POST /anchor/v1/admin/config` (retry_count, retry_interval_sec, poll_limit), `/admin/requests`, `/admin/counts`.
- Read side for clients: `GET /anchor/v1/projects`, `/anchor/v1/_status`, landing page `/`, `/health`; sync store pushed by the poller.
- Auth: `X-API-Key` = ANCHOR_API_KEY from `.cred` when set.
- Final statuses: finished / failed / cancelled; `ack_pending` while the webhook is not acknowledged.

### Flow
1. Owner opens the request page (`anchor_sim.html`, :9104) — two sections: left = seeded data + request + live Command/Data flow; right = webhook responses. It loads `anchor_seed.js` / `anchor_env.json`, lists projects via `GET <anchor>/anchor/v1/projects`, offers suggested prompts per project type (Klaviyo/email → workflow question; Veeqo/fulfilment → orders question).
2. Send → page records a card locally (`POST /sim/requests`, works even offline), then `POST <anchor>/anchor/v1/requests {project, prompt, webhook_url}` where `webhook_url = <wh>/cb/<project>`. Anchor ON → immediate ACK (queued); anchor OFF → "anchor is offline — not received".
3. Request sits **queued** at the anchor.
4. Local poller (`local_poller_http.py`, supervised) pulls `/poll`, runs the real CTO→team orchestration with read-only connector data, posts `/requests/{id}/result`.
5. Anchor POSTs the result to the webhook (retries until 2xx = acknowledged). In dev, `webhook_receiver.py` (:9300) records it; viewer at `/`, lists at `/list`, `/list/<project>`, `/list?project=`. In production the `wh` is the online anchor base (VM cannot reach the Mac's localhost).
6. Page polls `GET <anchor>/anchor/v1/requests/<anchorId>` and `GET <wh>/list/<project>`; updates the card with `PUT /sim/requests/<rid>`; response stored to a file.

### Components
| Component | Role | Endpoints |
|---|---|---|
| `workspace/anchor-layer/anchor_sim.html` (353 lines) | Main 3rd-party request page; dev vs prod via `window.ODIN_PROD`/`?env=prod` | Calls anchor `/projects`, `/requests`, `/requests/<id>`; webhook `/list/<project>`, `/cb/<project>`; sim store `/sim/*` |
| `workspace/anchor-layer/third_party_sim.html` (95 lines, older) | Minimal HTML third party | `POST /anchor/v1/requests` (sender `third-party-sim`), `GET /anchor/v1/requests/<id>` |
| `server/sim_server.py` | Serves the page + durable SQLite log `sim_requests.db` (table `reqs`: rid, project, prompt, webhook, status, anchor_id, response_path, created, updated; no WAL); responses as files `sim_responses/<id>.json` | `GET/POST /sim/requests`, `PUT/DELETE /sim/requests/<rid>`, `DELETE /sim/requests` (clear all, used by page), `GET /sim/response/<rid>`; static files otherwise |
| `server/webhook_receiver.py` | Stand-in third-party endpoint; replies 2xx = ack; HTML viewer to re-ack via the anchor's ack endpoint | `POST /cb[/<project>]`, `GET /list[/<pid>]`, `GET /` |
| `server/third_party.py` | CLI third party; posts with `webhook_url:""`, sender `third-party-cli`; polls every 3 s up to 200 times; prints status changes, acked, webhook attempts, result | anchor `/requests`, `/requests/<id>` |
| `shells/phase_ctl.sh send` | Agent-driven send through the same contract (webhook `http://localhost:9300/cb`) | |
| `workspace/anchor-layer/` contents | anchor_config.json, anchor_env.json, anchor_manage.json, anchor_queue.json, anchor_seed.js, anchor_sim.html, anchor_sync.json (~780 KB mirror), index.html, sim_requests.db, sim_responses/, third_party_sim.html | |
| Klaviyo etc. | Real read-only Klaviyo/Veeqo data is used by the local processor (`e2e_anchor_live.py` scenarios: "How many workflows — live vs draft?" and "How many orders this week?") | |

Note: in Phase 3 the request page is served by plain `python -m http.server`, not `sim_server.py`, so the `/sim/*` durable log endpoints are not available there (see section 6).

---

## 4. Test scripts

| # | Name | Purpose | How to run | Touches VM? |
|---|---|---|---|---|
| T-01 | `server/e2e_anchor.py` | Anchor Phase-1 lifecycle in-process: enqueue → poll → process → result → webhook → ACK → FINISHED; retry on flaky webhook; FAILED after retries; finished never re-handed | `python3 server/e2e_anchor.py` | No |
| T-02 | `server/e2e_anchor_http.py` | Same over the real FastAPI `/anchor/v1` router (TestClient) incl. X-API-Key auth | `python3 server/e2e_anchor_http.py` | No |
| T-03 | `server/e2e_anchor_live.py` | Real projects + live read-only Klaviyo/Veeqo through the anchor lifecycle | `python3 server/e2e_anchor_live.py` (on the Mac) | No (external SaaS reads) |
| T-04 | `server/e2e_anchor_all.py` | Runs T-01..T-03 in separate processes, one summary | `python3 server/e2e_anchor_all.py` | No |
| T-05 | `server/e2e_phase2.py` | Topology e2e app ⇄ remote anchor ⇄ local machine over real HTTP; `--smoke` = transport-only echo | `python3 server/e2e_phase2.py [--smoke]` | No |
| T-06 | `server/e2e_phase2_gate.py` | Single "ready for Phase 2" gate: Part A multi-hop token context test; Part B throwaway Postgres DB on the VM, `migrate deploy` + `reset`, drop, production fingerprint unchanged | `python3 server/e2e_phase2_gate.py` | **Yes** (VM sandbox DB) |
| T-07 | `server/e2e_phase1_shared_context.py` | Backend invents token, Frontend must reuse it (context propagation) | `python3 server/e2e_phase1_shared_context.py` | No |
| T-08 | `server/e2e_phase1_strong.py` | 3-agent, 2-hop token test + Frontend→Backend hand-off | `python3 server/e2e_phase1_strong.py` | No |
| T-09 | `server/e2e_phase1_hard_deploy.py` | Real deploy brief through DevOps+QA+Security; critical details must survive; production fingerprint before/after | `python3 server/e2e_phase1_hard_deploy.py` | **Yes** (VM sandbox `/home/mostafa/_e2e_sandbox`) |
| T-10 | `server/e2e_ai_capability.py` | "Frozen measuring stick": AI deploy capability in VM sandbox across Mining / Propagation / Crystallization / Truthfulness / Adaptation; hard guard on production paths, reboot, prisma migrate | `python3 server/e2e_ai_capability.py` | **Yes** (VM sandbox) |
| T-11 | `server/e2e_cache_timing.py` | Same task without vs with cache (`ODIN_DISABLE_CACHE`), timed by `run_timer` | `python3 server/e2e_cache_timing.py` | **Yes** (sandbox VM read-only health check) |
| T-12 | `workspace/shared/testing/__main__.py` + `run_all.py` | Auto-discovers every test with `main()`; known order starts readonly_shipping, readonly_email, sandbox_revealer…; aggregate summary | `python3 testing/` or `python3 testing/run_all.py` (or via loop.sh) | Depends on tests |
| T-13 | `testing/harness.py` | Shared core: smart_timeout (quick 120 / single 300 / multi 900 / deploy 1200 / revealer 2400 s), SeedingPrompt keep/clean, auto_resolve_dialogs, assert_cto_present, provider truth helpers | library | — |
| T-14 | `testing/preflight.py` | Fast GO/NO-GO: engine + tools (build agents have Write/Edit/Bash, QA read-only), credentials, roles have Resources & Dependencies, optional cheap haiku plan dry-run | `python3 testing/preflight.py [--plan "<brief>"] [--keys VEEQO,KLAVIYO]` | No |
| T-15 | `testing/readonly_shipping_vq_status.py` (Test 2) | Fulfillment/Veeqo read-only; no folder needed; agent must report real order count | via run_all / `python3 …` | No (Veeqo read) |
| T-16 | `testing/readonly_email_klaviyo_workflows.py` (Test 3) | Klaviyo read-only: live/draft/total workflows, metrics, lists; count integrity | via run_all | No (Klaviyo read) |
| T-17 | `testing/sandbox_revealer_multiagent.py` (Test 4) | "Revealer": NestJS + Next.js app with Veeqo/Klaviyo; CTO derives team; build → QA → deploy to VM sandbox `/home/mostafa/sandbox-revealer` port 8531; plan graded | via run_all / filter `revealer` | **Yes** (VM sandbox) **[note: see §0.8 C-10]** |
| T-18 | `testing/sandbox_deploy_overwrite_check.py` (Test 5) | DevOps agent redeploys with a unique per-run token; harness reads it back over SSH; SKIP if VM unreachable | `python3 testing/sandbox_deploy_overwrite_check.py` (filter `overwrite`) | **Yes** |
| T-19 | `testing/test_anchor_online.py` (Test 6) | Deploys anchor to VM dir `/home/mostafa/anchor-online`, starts it, verifies round-trip and existing site health; optional guarded nginx (`ODIN_ANCHOR_NGINX=1`) | `python3 testing/test_anchor_online.py` (also `phase_ctl redeploy`) | **Yes** |
| T-20 | `testing/test_web_online.py` (Test 7) | Builds Flutter web with online anchor, rsyncs to `/home/mostafa/odin-web`, serves, verifies, keeps as systemd service | `python3 testing/test_web_online.py` | **Yes** |
| T-21 | `testing/trace_chain.py` | Traces brain → anchor local on VM → anchor public → web public → nginx site owner, to locate a 404 | `python3 …/trace_chain.py` (phase_ctl `trace`) | **Yes** (read) |
| T-22 | `testing/isolate_anchor.py` | Proves the anchor node 100 %: T1–T3 forward read, T4 the 404 cause, T5 async queue (fast ACK then later result) — from outside over HTTPS | `python3 …/isolate_anchor.py` (phase_ctl `isolate`) | **Yes** (public endpoint) |
| T-23 | `testing/vm_security_audit.py` | Read-only ufw / NSG / listeners / nginx audit; `--fix` removes only 48619/48620 | `python3 testing/vm_security_audit.py [--fix]` (phase_ctl `audit`/`auditfix`) | **Yes** (fix changes firewall) |
| T-24 | `testing/e2e_real_flow.py` | Zoom Smart Meeting Notification Agent through real HTTP: intake → no-deviation check (forbidden technical roles) → create → `/agents/all` → run-now | `python testing/e2e_real_flow.py` | No |
| T-25 | `testing/e2e_soc.py` | RedBerry Continuous SOC: 8 agents, safety guards (auto-remediation off, monitor-only, read-only SSH guard), findings registry, approvals auto-denied, false positives, owner resolve | run from the agent bridge shell | Read-only SSH via guard |
| T-26 | `testing/phase7_lib.py` | Shared per-project child test: skeleton, odin_core row, every file indexed, no violations, capability integrity | library (used by each project's `tests/project_test.py`) | No |
| T-27 | `testing/phase7_monitor.py` | Parent monitor: runs each child test then placement / lockstep / audit-heal checks | `python3 workspace/shared/testing/phase7_monitor.py` | No |
| T-28 | `testing/phase7_lifecycle.py` | Creates 4 projects (schedule, reader, deploy-reuse, revealer-multi) through `create_owner`, monitors, deletes, proves exact baseline | `python3 workspace/shared/testing/phase7_lifecycle.py` | No |
| T-29 | `testing/phase7_strong.py` | Adversarial: injects every violation type, proves real correction, promote-to-shared, custom-over-shared, 0 violations, restore | `python3 workspace/shared/testing/phase7_strong.py` | No |
| T-30 | `testing/phase7_prompt_loop.py` | Prompt → plan → approve → create → timed output → audit → delete (3 specs mixing HubSpot/Veeqo/Klaviyo/SOC) | `python3 workspace/shared/testing/phase7_prompt_loop.py` | No |
| T-31 | `testing/phase7_prompt4.py` | Owner journey with 4 prompt-created projects, strong acceptance points, reuse, exact-baseline delete | `python3 workspace/shared/testing/phase7_prompt4.py` | Spec D asks for sandbox deployment (skipped in the paper study) |
| T-32 | `testing/phase7_realrun.py` | Real first run of every project, timed, with audit monitoring | `python3 workspace/shared/testing/phase7_realrun.py [<pid>…]` | Depends on project |
| T-33 | `testing/seed_connectors.py` | Seeds connectors (hubspot, klaviyo, veeqo, claude-cli, az-cli) into `workspace/connectors/` and odin_core, deadlock-safe | `python3 workspace/shared/testing/seed_connectors.py` | No |
| T-34 | `workspace/shared/infra/phase3_e2e.py` | Production e2e with fixed expectations against the online anchor/web; real SSL required | `ODIN_SERVER_NAME=<domain> python3 workspace/shared/infra/phase3_e2e.py` | **Yes** (read) |
| T-35 | `real_production_deploy_devops_only.py` (Test 1) | Real production deploy (propose-only unless `ODIN_TEST_PROD_DEPLOY=1`) | via run_all / loop | **Yes** (production) — file not in bundles |
| T-36 | `_research/regression/regress.py` | Isolated-copy regression suite: 18 checks baseline → 32 checks after P2 | (isolated copy) | No |
| T-37 | `_research/exp/sandbox_revealer_local.py`, `_research/exp/phase7_prompt4_local.py` | Local adaptations of T-17 and T-31 for the paper study | (isolated copy) | No |
| T-38 | `npm run e2e` → `tests/e2e.py` | Desktop e2e | `cd desktop && npm run e2e[:quick]` | Unknown — target missing |

Row count: 38

---

## 5. Paper additions

### 5a. Code changes (P2 and fixes; applied ONLY in the isolated copy, handed over as a promotion package, NOT applied to production)
| # | Change | File | Detail |
|---|---|---|---|
| C1 | P2a agent start folder | `server/projects.py` `agent_workdir(pid)` | Returns project `localPath` if set, else `workspace/projects/<pid>/code` (created) |
| C2 | P2a used in runs | `server/api_v2.py` `_scoped_gen` | `fp = localPath or agent_workdir(pid)` |
| C3 | P2a docs | CLAUDE-facing docs | Absolute workspace path replaced by `<odin-repo-root>` |
| C4 | P2b hook registration | `server/claude_cli.py` `_scope_settings_file(readonly)` | PreToolUse matcher `Write|Edit|MultiEdit|NotebookEdit|Bash` → `scope_hook.py`; combined with read-only Bash guard in read-only runs; files `.scope-settings.json` / `.scope-settings-ro.json`; `ODIN_SCOPE_HOOK=off` disables |
| C5 | Actor detection | `claude_cli._actor_for(cwd)` | Owner project from `workspace/projects/<pid>/…` or a project's localPath |
| C6 | Env injection | `ClaudeCLIBrain` run | Sets `ODIN_ROOT`, `ODIN_ACTOR_PID`, `ODIN_ACTOR_WORKDIR`; adds `--settings` for write runs when an actor exists; Popen gets `env=_env` |
| C7 | New `server/scope_hook.py` | hook | Modes watch/enforce/off; allow temp + own workdir; shared → block with door command; other project → block; repo root / system area → block; own project non-canonical slot → redirect via `workspace_mw.route`; quote-aware shlex Bash parser (redirects, tee, mkdir, touch, cp/mv/install dest), drops heredoc bodies, ignores fd dups; door calls refused under a foreign `ODIN_ACTOR_PID`; door does not excuse chained raw writes; log `workspace/history/scope-hook.jsonl`; exit 2 with message in enforce |
| C8 | New `server/door_cli.py` | agents' door | `promote <path in own project>` → `workspace_mw.promote_to_shared`; `put <sub> <name> <src>` → `workspace_mw.put_file`; actor from env only |
| C9 | EasyPost role fix | `projects.OPERATIONAL_MEMBERS` | Added "EasyPost Shipping & Tracking Operator" (deps easypost, read-only, post-shipping carrier tracking) so Revealer pre-flight passes |
| C10 | delete_owner scope cleanup | `server/workspace_mw.delete_owner` | Also removes `chats/scopes/project__<pid>` and `member__<pid>__*` folders and their `files`/`folders` rows (LIKE with escaping) |
| C11 | Experiment safety | regress.py / experiment scripts / mkroot.sh | Refuse to run unless root under `_research/tmp` with `server/`; regress chdirs to throwaway root; mkroot makes copies writable |
| C12 | Isolation shims | `_isolation/shims`, copy `.venv/bin` | Block az, ssh, scp, sftp, rsync, sshpass, gh; claude cost wrapper; log `_isolation/blocked_calls.log` |

### 5b. Proposals (`05_proposals.md` + paper §Proposals)
| ID | Proposal | Status |
|---|---|---|
| P1 | Move terminal bridge runtime files outside the git folder (`ODIN_BRIDGE_DIR`, default `~/Library/Application Support/Odin/agent_term`) | Written only |
| P2 | Agent writes through the door (agent workdir + PreToolUse hook) | Implemented + measured in isolated copy (D17–D34); not applied to production |
| P3 | Connection pool inside `workspace_mw._db()` (door latency 6.4× at 10 projects) | Written only; needs benchmark + approval |
| P4 | Job B: MiniLM embedding as second ranking signal for finding reusable scripts; benchmark protocol (top-1/top-3/MRR, paired test) | Written only, not run (needs owner labels) |
| P5 | RAG for the story-writing project only (chunking ~800/100, bge-small or MiniLM, Chroma/FAISS, top-20 → cross-encoder → 5, hash re-index) | Design only |
| P6 | Webhook duplicate tolerance: dedupe by `request_id`, send `Idempotency-Key` | Written only |
| P7 | Measure the semantic router on the 162 requests before changing anything (keyword dispatcher agrees 43 %) | Written only (in 05_proposals; not listed in paper) |
| P8 | Project delete should also stop that project's running agent processes | Paper only (from D30) |
| P9 | Derive prompt-journey teams from required capabilities before adding newly registered roles | Paper only |
| P10 | Make modules that write relative to CWD use the workspace root | Paper only (from D25) |

### 5c. Decisions D1–D37 (one line each)
- D1 Paper anonymous ("Keel") and named (Odin); only own measurements; no benchmark rank; framework unnamed.
- D2 Private throwaway PostgreSQL 14 cluster on 15432 from read-only dumps (odin_core data+schema, odin_anchor schema); experiments on 15433; production DB only read.
- D3 Cloud/remote tools shimmed and blocked; copy has no credentials; VM steps reported "skipped (cloud blocked)".
- D4 Isolated server on 18000, voice off, Claude auto-memory off; experiment servers 181xx in throwaway roots.
- D5 Report ratios, record M4 environment, process CPU/memory, load.
- D6 Incident: empty-root trial ran against the copy; repaired (git checkout, quarantine); guard added.
- D7 run.sh put Homebrew first and bypassed shims; shims also installed in copy's `.venv/bin`.
- D8 Job B written as proposal, not run.
- D9 Owner tests: lifecycle unmodified ×3; Revealer as local adaptation; production deploy and live-key read-only tests not run.
- D10 Named paper uses affiliation/e-mail placeholders.
- D11 LLM runs use haiku; rep 0 at N=10 reused 5 names → 4 collisions, 8 projects affected; later reps use unique names.
- D12 Router agreement measured for keyword dispatcher only.
- D13 Experiment roots and clusters under `_research/tmp`, removed after packaging; raw results in `_research/results`.
- D14 Finding: 2/36 LLM runs wrote into the main copy by following the absolute path in CLAUDE.md; quarantined.
- D15 Escape guard: copy's `workspace/` made read-only during LLM tests.
- D16 `phase7_prompt4.py` run with specs A–C only (D needs cloud).
- D17 P2a: agents start in own project code folder; absolute path removed from agent docs.
- D18 P2b: `scope_hook.py` + `door_cli.py`; actor from engine.
- D19 Watch stage: 0 would-redirect, 0 would-block of 58 hook calls.
- D20 Enforce stage: hook blocked nothing in normal workload; P2a alone fixed placement.
- D21 Adversarial: hook off → all 5 raw-wrote to shared + other project; hook on → 9 shared + 6 cross-project blocked; all 5 used the door.
- D22 Hardening: door no longer excuses chained raw writes; door refused under foreign actor.
- D23 Hook false positives fixed (quoted sed `>`, heredoc bodies, `2>&1`); regression checks added.
- D24 First Revealer-after run invalid (own regression reset the DB under it); re-run.
- D25 Regression hygiene: regress chdirs to throwaway root; CWD-relative writes recorded as proposal (P10).
- D26 mkroot.sh makes copied roots user-writable (first enforce run failed due to D15).
- D27 `chmod +x` in the VM changed 75 file modes in the copy; restored.
- D28 Bug fixes: `delete_owner` removes chat-scope folders/rows; EasyPost added to role catalogue.
- D29 Second Revealer-after attempt aborted (port 18000 still held); re-run cleanly.
- D30 Finding: agent processes outlive test and deleted project; stopped; proposal P8.
- D31 Remaining "+1 file row" is the system audit log, not the deleted project.
- D32 Regression after all changes: 32/32 pass, 0 regressions vs 18-check baseline.
- D33 Revealer after: pre-flight passes; CTO stopped truthfully (no credentials); scorecard 5/10; one unauthenticated read probe (HTTP 401).
- D34 Adversarial re-run with final hook (rep 32): 9 shared + 5 cross-project blocked, 0 cross-project modules, 5/5 via door, 4/5 tests pass.
- D35 Total model cost 16.46 USD (cap 20).
- D36 Replication packages rebuilt and scanned (0 DB dumps, e-mails, IPs, secrets); private clusters and throwaway roots deleted; production Postgres untouched.
- D37 LaTeX author-block fix; acknowledgment thanks the CEO and Founder.

### 5d. The 11 features F1–F11 and claims
| F | Feature | Origin claimed | Claims in the paper |
|---|---|---|---|
| F1 | Component reuse (DRY): shared scripts = components, deltas = props | React/React Native DRY; delta-oriented product lines | Total match → pointer to shared base; near match → small delta; different job → different agent. Duplicates promoted to `shared/utils` |
| F2 | Delta + middleware semantic router | Backend middleware | Routes to reuse / base+delta / new work; deterministic keyword floor under local semantic classifier; keyword dispatcher agrees with logged lead agent 43 % (162 requests), stated as a baseline |
| F3 | Shared-script library + context-indexed DB, one creation door | — | DB is the only registry (parallel JSON registry = violation); door validates placement, redirects, owner-scope guard, writes file + row together; CTO asks "use existing key?" |
| F4 | WhatsApp-style live sync | Local-first / Lamport clocks | Durable mirror, per-scope monotonic sequence, delta pulls, stale flag; forced by 4 July in-memory mirror loss |
| F5 | Queue at the anchor (RabbitMQ-style) | Message brokers | Pull model, no inbound connection or static IP; 97–99 % of request time is queue wait |
| F6 | Callback / return URL (Stripe-style) | Webhooks with retries | Two-way contract; with 20 % injected callback failures, eventual delivery 100 % (one at the next sweep) |
| F7 | Cross-project agent reuse | — | Org-wide roster; projects link agents; lifecycle test re-links 3 agents with 0 duplicates |
| F8 | Dynamic-IP firewall | Zero trust / port knocking | Single /32 rule rotated, replaced never stacked |
| F9 | Smart mapping-file deploy flow | Incremental deploy / RTS | Change detection by date; ask before update; seed/DB files excluded; DB rebase asked separately; real endpoint + seed verification |
| F10 | Smart CI/CD, self-healing deploy agent | LLM repair agents | Deterministic hands + AI brain with learned-faults memory; probes by area; one safe fix; re-run; stops for human-only failures |
| F11 | Audit layer + truth gate | Reflexion models / runtime enforcement | Checks structure, folder, foreign refs, bidirectional registry lockstep; heals (move, promote, re-point, re-index); truth gate rejects unevidenced "done"; historical counts 18 misplaced, 16 duplicate, 15 foreign-ref, 5 external-write, 3 parallel-registry, 33 redirected writes (07-17→07-30) |
| (context) | Also in system | — | On-device Whisper STT/TTS EN+AR, Zoom meeting pipeline, phone/web control via the anchor; connectors not a contribution |

Extra features found (01_extra_features.md, 21 items): truth gate; approval gate + read-only hook; scoped memory (company → project → member); Main Task object; intelligence-first intent routing; per-scope model choice (Ollama fallback); operations record; self-healing deploy agent; project scheduler; SOC blueprint (12 security agents); VM Security Sentinel; generic UI contract; reporting engine (md/docx/pdf/pptx); live activity bus; capabilities registry; auth (hashed passwords, 2FA, e-mail verification; anchor manage login + one-time code on desktop); third-party simulator + webhook receiver; cache-vs-no-cache run timer; bilingual voice (Kokoro, Coqui XTTS, optional Azure TTS); WhatsApp-clone mobile mode; owner's e2e harness.

### 5e. Measured results claimed
| Area | Result |
|---|---|
| RQ1 (scripted, 40 trials, 5 seeds) | Door: 0 violations ± 0 for N=1,2,5,10 (36–360 writes, 3–30 agents); no door: .217 / .289 / .307 / .308; after heal without door .000 / .106 / .118 / .108 remain (cross-project); lockstep 1.00 vs .05; residual door audit findings 0.07–0.10 per write, healed to 0 |
| Door cost | 10–19× slower per write than raw; median latency 1.5× / 3.3× / 6.4× at N=2/5/10 |
| RQ2 before (54 tasks) | Success 1.00 / 1.00 / .93 / .97 (52/54); own code slot .67 / .50 / .40 / .17; files outside project per task 1.0 / 1.5 / 1.2 / 1.7; 1 cross-project module; 2 writes into the main workspace; audit flag ratio 1.0 for stray paths |
| Watch stage | 28 tasks, 58 hook calls, 0 would-redirect/block |
| RQ2 after | Own slot 1.00 at all N; success 54/54; 0 files outside; cost per task × 0.79 / 0.90 / 0.80 / 0.75 vs before; growth vs N=1: 1.13 / 1.19 / 1.06 (before 0.99 / 1.18 / 1.13) |
| Adversarial (N=5) | Hook off: 5/5 raw shared writes, 5 modules in other projects, 0 audit flags on shared writes, 5/5 tests; hook on: 0 (9 blocked) shared, 0 (5 blocked) cross-project, 5/5 via door, 4/5 tests; first hook version: 15 blocked, 0 cross-project |
| RQ3 | Lifecycle all green 3/3 before and after; adversarial 32/32 ×3 before and after (and one correct fail before); Revealer pre-flight blocked → passes; scorecard 5/10 (no creds); prompt journey clean delete 0/3 → 2/3 (+1 system row); team coverage 1/3 both; 2/3 produced output; regression 18/18 → 32/32 |
| RQ4 | Queue wait 97–99 % of time; 4 clients = 2.1× throughput; 20 % callback failures → 199/200 in run, last at next sweep, 100 % eventual, retry waits 66–76 % of time; live sync visible in < 0.1 % of push interval; after restart mirror + 20 sequenced messages present; delta from seq 15 returns 16–20 |
| Environment | MacBook Pro M4 Pro, 12 cores, 24 GB, macOS 26.5; load 3.4, 9 % CPU; production < 1 % CPU |
| Cost | 16.46 USD total |
| Timeline facts | 33 PASS / 1 FAIL (06-23); phase-7 journey 0/4 → 4/4 (07-19); references: 33 cited checked, 13 corrected, 1 preprint-only (SkillOps), 0 removed |
| Isolation | 252 files / 7,042 references re-pathed; 54 secret values redacted; 56 files remapped for DB/ports; 5 scheduled tasks disabled; copy of HEAD af2cbd8 |
| Benchmark rank | NOT FOUND — paper states no rank |

Row counts: 5a 12 · 5b 10 · 5c 37 · 5d 12 (+21 extra features) · 5e 15

---

## 6. Missing / referenced-but-absent

1. **`tests/e2e.py`** — `desktop/package.json` scripts `e2e` / `e2e:quick` run `python3 ../tests/e2e.py`; no `tests/` folder appears in any bundle (tests live in `server/e2e_*.py` and `workspace/shared/testing/`). Broken script.
2. **`phase_ctl.sh` path** — `development_full_checker.sh` runs `bash phase_ctl.sh` from the repo root, but the file is `shells/phase_ctl.sh` → the control bridge likely never starts in Phase 2 (anchor_loop.sh correctly uses `shells/…`).
3. **`phase3_up.sh`** — referenced in `anchor_sim.html` text ("phase3_up.sh injects window.ODIN_PROD"), `test_anchor_online.py` and `test_web_online.py` docstrings; not present. Superseded by `production_full_checker.sh`.
4. **`phase3_gate.py deploy-anchor` / `deploy-web`** — called by `production_full_checker.sh` but not in the docstring's subcommand list (init/compare/validate/snapshot); only first 60 of 447 lines seen — unverified.
5. **Phase 3 request page store** — Phase 3 serves `anchor_sim.html` with plain `http.server`, not `sim_server.py`, so `/sim/requests` and `/sim/response` (durable log) are absent in production mode.
6. **`testing/` path mismatch** — `loop.sh` and `monitor.sh` live in `workspace/shared/testing/` but `cd` three levels up to the repo root and use `testing/results` and `python3 testing/`; docstrings across tests also say `python3 testing/<x>.py`. No root `testing/` in listings → legacy path. `deploy.sh`/`deploy_run.sh`/`deploy_changes.py` usage text likewise says `infra/…` instead of `workspace/shared/infra/…`.
7. **`deploy.config.sh`** — optional override file for `deploy.sh`; not in bundles. Also `data/_e2e_sandbox_config.sh` (T-10) and `data/_e2e_phase1_sandbox.sh` (T-09) not seen.
8. **`server/deploy_ssh.py`** — used by phase_ctl `vm`, deploy_verify, all VM tests; not included in bundles.
9. **Referenced server modules not in bundles** — `anchor_queue.py`, `anchor_manage.py`, `store.py`, `readonly_hook.py`, `workspace_mw.py`, `workspace_audit.py`, `api_v2.py`, `projects.py` (only diff), `run_timer.py`, `soc_run.py`, `scopes.py`, `agents_registry.py`, `integrations/cred`, `integrations/klaviyo`, `integrations/veeqo`, `gen_test_keys.py`, `server/requirements.txt`, `voice/backend/requirements-voice.txt`.
10. **Voice `*.py`** — the task list expected voice files in B5b; none are included (only `app.py` mentions `/voice/stt`, `/voice/tts`).
11. **`real_production_deploy_devops_only.py`** (Test 1) — named in D9 and run_all context; not in the testing heads.
12. **`logs/zoom_spec.txt`** — `e2e_real_flow.py` reads `ROOT/logs/zoom_spec.txt` where ROOT = `workspace/shared` → `workspace/shared/logs/zoom_spec.txt`; not seen.
13. **Android build** — no `flutter build apk/appbundle` or Android run in any script; only the platform folder is scaffolded.
14. **Desktop assets** — `desktop/build/icon.png`, Flutter `assets/icon/odin_icon.png`, `odin_icon_fg.png` referenced; not listed.
15. **Help text gaps** — `phase_ctl.sh` header omits `trace`, `isolate`, `audit`, `auditfix`; Phase 3 banner says "MOBILE sim" though policy forbids simulator.
16. **`.bak` copy** of `development_full_checker.sh` mentioned in ISOLATION.md; not in bundle.
17. **Research artefacts** referenced but not bundled: `_research/regression/regress.py`, `_research/exp/*`, `_isolation/pg_up.sh`, `_isolation/shims`, `mkroot.sh`, `pkgcheck.py`, `repath_changed_files.json`, `db_port_remap_files.json`, `schedules_original_enabled.json`, `workspace/docs/RUFLO-COMPARISON.md`, `ISOLATION_STATE.md`, `PHASE7-RESULTS.md`, `STRUCTURING-PLAN.md`, `WORKSPACE-SCHEMA.md`, `orchestrator/dispatcher.py`, `orchestrator/semantic_router.py`, `odin_app/lib/screens/whatsapp.dart`.
18. **Proposal numbering** — paper lists P1, P3–P6, P8–P10; P7 (router measurement) exists only in `05_proposals.md`; P8–P10 exist only in the paper.
19. **Security notes (values not copied)** — live anchor API key committed in `anchor_prod.js` and `anchor_seed.js`; dev app login password printed by `development_full_checker.sh`; sandbox DB password hardcoded in `e2e_phase2_gate.py`; VM IP fallback hardcoded in `deploy.sh`; poller/tests disable TLS verification (`CERT_NONE`) for the VM.

Row count: 19


<!-- ==================== PART K1 ==================== -->

# K1 — Middleware, audit, DB schema, registry, structure (v1src)

Files read in full: server/workspace_mw.py (1007), workspace_audit.py (528), store.py (183), directions.py (149), audit.py (198), readonly_hook.py (81), agents_registry.py (476), cached_modules.py (77), chats.py (96), scope_guide_test.py (341), scope_reasoning_test.py (257); odin_core_schema.sql (804), odin_anchor_schema.sql (60); workspace/shared/directions/WORKSPACE-SCHEMA.md (115), STRUCTURING-PLAN.md (80); every file under workspace/shared/config/ (13 files), workspace/shared/features/ (only voice/.gitkeep, empty), workspace/shared/cached_modules/ (README.md + a binary macOS .DS_Store, no modules). Folder tree from `find workspace -maxdepth 3 -type d`.
Secrets note: `vm_diagnosis_guard` (workspace_mw.py:966-977) hard-codes an SSH user@IP and a credential-file grep in prompt text. The IP and key are not copied here.

## 1. Capabilities found

| ID | Category | Capability | What it does | Evidence | Triggered by | In MFI? |
|---|---|---|---|---|---|---|
| K1-001 | Middleware & DB registry | Single creation door (module) | Every workspace create/update/delete is meant to go through one module that validates placement, writes the file and keeps odin_core in lockstep. DB sync is best-effort. | workspace_mw.py:1-11 | other modules | B-062, C-029 |
| K1-002 | Structural | PROJECT_SUBFOLDERS rule set | Allowed project top-level subfolders: instructions, restrictions, plan, connectors, schedule, dependencies, code, features, chat, tests, data, docs, files, deploy, jsons | workspace_mw.py:19-25 | validate/route | B-080 (differs from doc) |
| K1-003 | Structural | AGENT_SUBFOLDERS rule set | Allowed agent subfolders: instructions, restrictions, dependencies, code, outputs | workspace_mw.py:26 | validate/route | B-081 |
| K1-004 | Structural | Allowed root files | Project root may hold only index.json and agents.json. Agent root may hold only index.json, capability.md and handoff.json. | workspace_mw.py:27-28 | validate/route | B-080/B-081 |
| K1-005 | Middleware & DB registry | Violation exception | Exception class reserved for placement violations. It is never raised in this file. | workspace_mw.py:31 `Violation` | — | no |
| K1-006 | Middleware & DB registry | File-kind classifier | Maps a file extension to a kind (json/md/shell/py/html/txt/pdf/unit/secret/jsonl/code/other), stored in files.kind | workspace_mw.py:35 `_kind` | sync_row, route | no |
| K1-007 | Middleware & DB registry | Best-effort DB connection | Connects with psycopg2 to dbname=odin_core and returns None on failure, so file operations never break | workspace_mw.py:43 `_db` | all DB writers | no (P3 pool only) |
| K1-008 | Structural | Area mapping | Maps owner types project/agent/connector/chat to the folders projects/, agents/, connectors/, chats/ | workspace_mw.py:51 `_area` | resolve_path etc. | no |
| K1-009 | Structural | Placement validator | Returns (ok, reason). Project and agent subfolders must be canonical, root files must be on the allowlist, connector/chat/shared/workspace always pass, and an unknown owner type is a violation. | workspace_mw.py:55 `validate` | scan_violations | B-062 |
| K1-010 | Structural | Canonical path resolver | Builds workspace/<area>/<id>/<sub>/<name>. Shared files go to workspace/shared/<id>, everything else to workspace/<id>. | workspace_mw.py:79 `resolve_path` | put_file, heal, agents_registry | no |
| K1-011 | Structural | Owner inference from path | Derives (owner_type, owner_id, subfolder) from a path. Excludes projects/_shared. Area-level files map to "workspace". Chats map to <stem> or _pool. | workspace_mw.py:85 `_infer_owner` | sync_row, scan, promote | no |
| K1-012 | Structural | Placement routing and redirect rules | A valid subfolder is respected and root files are moved to the owner root. Otherwise the file is redirected and never blocked. Agent: handoff/capability/index go to root, code goes to code/, md to instructions/, the rest to outputs/. Project: test/e2e/spec go to tests/, deploy to deploy/, code to code/, md/pdf/html to docs/, json goes to data/approvals if the name has "approval", else data/jsons, the rest to files/. | workspace_mw.py:103 `route` | put_file, heal | B-062; §0 l.39 |
| K1-013 | Safety & approvals | Owner-scope (cross-owner) write guard | If the actor is not the target owner, the write is redirected into the actor's own folder (prevent-and-correct) and flagged scope_redirected | workspace_mw.py:153-164 `put_file` | put_file(actor=) | B-034 |
| K1-014 | Middleware & DB registry | put_file door | Routes, writes (dicts are JSON-dumped), runs sync_row, logs any correction, and returns path/corrected/note/final_subfolder | workspace_mw.py:143 `put_file` | agents_registry:72/94, capabilities.py:95, zoom_pipeline_run:153, phase7 tests | B-034, B-062 |
| K1-015 | Audit & consistency | Middleware correction log | Appends every redirect to workspace/history/mw-corrections.jsonl and indexes that log too | workspace_mw.py:178 `_log_correction` | put_file | no |
| K1-016 | Middleware & DB registry | sync_row lockstep upsert | For an existing workspace file: auto-upserts the owner row (projects/agents/connectors/chats) using its index.json, upserts the folders row, then DELETE+INSERTs the files row with kind, description, size and timestamps | workspace_mw.py:192 `sync_row` | store.write_json, put_file, audit heal, agents_registry._index, many | B-062/B-075 (lockstep) |
| K1-017 | Middleware & DB registry | Owner-row auto-create from index.json | sync_row makes sure a project row (name/type/category/features), agent row (name/role/type/group/nature/description), connector or chat row exists, so a file never dangles | workspace_mw.py:210-240 | sync_row | no |
| K1-018 | Middleware & DB registry | remove_file | Unlinks the file and deletes its files row | workspace_mw.py:270 `remove_file` | promote, heal (misplaced, db-orphan, parallel-registry) | no |
| K1-019 | Middleware & DB registry | add_dependency | Writes or updates the owner's dependencies/manifest.json entry (name/source/kind/mode/overlay; upgrades as-is to a custom mode) and inserts shared_capabilities and dependencies rows idempotently | workspace_mw.py:300 | promote, customize, provision, request_capability | B-036 |
| K1-020 | Middleware & DB registry | Rewrite owner references | Rewrites an owner's own .py/.sh/.js/.ts/.dart/.json/.md files from the old path to the new shared path, then re-syncs | workspace_mw.py:346 `_rewrite_owner_refs` | promote_to_shared | no |
| K1-021 | Middleware & DB registry | promote_to_shared | Moves an owner's file to shared/<cat>/ (cat is infra for deploy, testing for test/e2e/spec, else utils), drops the duplicate, re-indexes, and repoints the original owner and extra consumers | workspace_mw.py:371 | request_capability, audit heal (duplicate/foreign-ref), door_cli | B-035 |
| K1-021a | Middleware & DB registry | repoint_reference | Rewrites a referrer's source so it reads from the new shared path (with or without the workspace/ prefix) | workspace_mw.py:409 | heal foreign-ref | B-036 |
| K1-022 | Middleware & DB registry | request_capability (anti-duplication) | Order: if the need is in shared/, add a pointer; if it is in another owner's code/deploy/tests/files/connectors/schedule, promote it and repoint; otherwise create it new in the actor's own folder | workspace_mw.py:434 | provision_capability | no |
| K1-023 | Middleware & DB registry | customize_shared (base + overlay) | Keeps the shared base untouched. The owner's delta overlay goes into its own code/ and the manifest records mode=extend/subset/override | workspace_mw.py:469 | callers/tests | B-036, B-064 |
| K1-024 | Middleware & DB registry | provision_capability | The system finds the shared capability. For a deploy need it generates <owner>.config.sh (CFG_BACKEND_*/CFG_FRONTEND_*/RESTART/REBOOT) in deploy/ and registers mode=extend; otherwise it adds an as-is pointer | workspace_mw.py:487 | callers/tests | B-033 |
| K1-025 | Middleware & DB registry | resolve_capability | Resolves the effective shared base plus the owner overlay from the manifest, with existence checks | workspace_mw.py:533 | tests | B-036 |
| K1-026 | Middleware & DB registry | DB-is-the-only-registry guard constants | REGISTRY_GUARD names projects.json, connectors.json and company_agents.json under shared/core-registry as parallel registries | workspace_mw.py:563-571 | scan_registry_violations | A-103, F3 |
| K1-027 | Middleware & DB registry | scan_registry_violations | For each such file present, compares its ids with the DB table and reports a "parallel source of truth" violation plus any orphan ids | workspace_mw.py:574 | workspace_audit.scan | A-103 |
| K1-028 | Audit & consistency | scan_violations | Walks workspace/ (skipping .gitkeep, .DS_Store, __pycache__ and logs/) and validates every file's placement | workspace_mw.py:608 | workspace_audit.scan | A-103, B-038 |
| K1-029 | Structural | PROJECT_SKELETON (17 entries) | instructions, restrictions, plan, connectors, schedule, dependencies, code, features, features/voice, chat, tests, data, data/jsons, data/approvals, docs, files, deploy | workspace_mw.py:625 | create_owner | B-080 (doc says 9 entries), B-059 |
| K1-030 | Structural | AGENT_SKELETON | instructions, restrictions, dependencies, code, outputs | workspace_mw.py:628 | create_owner | B-081 |
| K1-031 | Middleware & DB registry | sync_folders | Inserts a folders row for every on-disk subfolder, including empty ones | workspace_mw.py:631 | create_owner | no |
| K1-032 | Middleware & DB registry | create_owner | Stamps the full skeleton with .gitkeep, writes index.json, then agents.json for a project or capability.md and handoff.json for an agent, inserts the project/agent row, syncs folders and indexes the root files | workspace_mw.py:661 | projects.py:756, phase7 tests | B-037 |
| K1-033 | Middleware & DB registry | delete_owner (FK-safe) | rmtree the folder, then delete files, folders and dependencies rows, then the link rows (project_agents/connectors/chats), then the owner row. It does not purge chats/scopes in this snapshot. | workspace_mw.py:724 | projects.py:945, agents_registry:91, capabilities.py:106 | B-037 (B-054/C10 claim scope purge, not present here) |
| K1-034 | Orchestration core | scope_answer_guard (prompt guard) | Owner text: search this project's own scope first, never substitute another scope's value, never falsely refuse, ask one narrow X-or-Y only on real ambiguity, and go find out-of-scope answers globally. External text: closest in-scope answer, never leak, gate insisted out-of-scope requests behind owner approval. | workspace_mw.py:770 | api_v2:3486 (owner /scope/stream), anchor.py:249 (external) | A-095 |
| K1-035 | Orchestration core | read_execute_guard (prompt guard) | "A read is not a change": run GET/list/status reads and give the live value, optionally naming connected services. Never propose or ask approval for a read, switch to the read-only form, try the live query before saying "not there", no trailing "want me to…?", be decisive. | workspace_mw.py:804 | api_v2:3507, scope_guide_test:114 | A-096 |
| K1-036 | Middleware & DB registry | agent_scope table bootstrap | CREATE TABLE IF NOT EXISTS agent_scope (PK project_id+agent) | workspace_mw.py:831 `_ensure_agent_scope` | set/get/list agent scope | A-085 |
| K1-037 | Auth & security | set_agent_scope | Upserts a scoped credential reference (service, credential_ref, read_only) per project and agent | workspace_mw.py:845 | admin/tests | A-085 |
| K1-038 | Auth & security | agent_credential_ref / list_agent_scope | Reads a single delta binding, or all bindings for a project | workspace_mw.py:862, :878 | agent_scope_guard, tutorial_guard | A-085 |
| K1-039 | Safety & approvals | agent_scope_guard (prompt guard) | For a borrowed helper agent: use the scoped credential when a delta is set, else the default. State credential_source (delta/default/unresolved). Read-only, writes must be proposed, never blocks. | workspace_mw.py:890 | api_v2:1007, :3239 | A-085, §0 l.63 |
| K1-040 | Safety & approvals | External single-file report rule | The external_report table (PK project_id) stores the one allowed external path. set_external_report_ref, external_report_ref and _ensure_external_report manage it. | workspace_mw.py:909-946 | api_v2:1010 | A-087 |
| K1-041 | Safety & approvals | write_external_report enforcement | Refuses any path other than the registered one with "VIOLATION", otherwise writes the file | workspace_mw.py:948 | diagnosis flow | A-087 |
| K1-042 | Safety & approvals | vm_diagnosis_guard (prompt guard) | For diagnosis projects: run read-only VM checks yourself through sshpass+ssh with an allowlist of remote commands (psql SELECT, tail, grep, ls, cat…), never use > or >> redirects (pipe instead), point to the staging DB URL location and the scoped key field; only writes are proposed. Embeds a hard-coded host. | workspace_mw.py:966 | api_v2:1011 (when external_report_ref set) | §0 l.63 (no row ID) |
| K1-043 | Per-project features & integrations | tutorial_guard (prompt guard) | Maps agent_scope services and project members (fulfillment→veeqo, email→klaviyo, hubspot) to shared tutorials (only veeqo is mapped). Rule: read the tutorial first, never guess fields, Veeqo "shipped" means dispatch_date, shipped_by_id or a tracking label, and the tutorial is updated if the live API differs | workspace_mw.py:984-1007 `_TUTORIAL_MAP`, `tutorial_guard` | api_v2:1015, :3231 | §0 l.63; B-157/B-160 related |
| K1-044 | Audit & consistency | Audit/observer module (debounced self-heal net) | Heals at the source (index, move, promote) and flags what it cannot decide. It is the safety net behind the middleware. | workspace_audit.py:1-18 | scheduler, routes | A-103, B-065, C-028 |
| K1-045 | Audit & consistency | CORE_APPS / CORE_ROOT_FILES | Repo-root items the root-stray rule ignores: server, orchestrator, voice, desktop, odin_app, dashboard, shells, data, .git, .venv, workspace, plus CLAUDE.md, README.md, anchor_seed.js, anchor_prod.js, anchor_sim.html… | workspace_audit.py:24-28 | scan | A-103 |
| K1-046 | Audit & consistency | INTERESTING extensions | Only json/md/sh/py/ts/js/jsx/tsx/dart/html/jsonl files count for indexing and quiet-time | workspace_audit.py:29, :76 `_interesting` | scan, quiet_for | B-065 |
| K1-047 | Safety & approvals | PROTECTED_PROJECTS | real-deployment-and-diagnosis-organics-07d7 is never auto-touched. Its issues are dropped by scan and skipped by heal. | workspace_audit.py:32-43 `_is_protected` | scan, heal, scope tests | A-041, B-031, §0 l.67 |
| K1-048 | Audit & consistency | Audit config | audit-config.json defaults: enabled true, silence_minutes 30, watch_root true. config() reads it; set_config writes it and syncs the row | workspace_audit.py:44-65; shared/config/audit-config.json | /audit/config | B-065, C-028 |
| K1-049 | Audit & consistency | Debounce (silence gap) | quiet_for gives minutes since the newest interesting write. should_run requires enabled and quiet ≥ silence_minutes | workspace_audit.py:81, :95 | heal, /audit/status | B-065 |
| K1-050 | Audit & consistency | Rule: misplaced | Detected by mw.scan_violations. Healed by moving to the routed slot via mw.route, then remove_file on the old path and sync_row on the new one | workspace_audit.py:108, :368 | scan/heal | A-103, B-038 |
| K1-051 | Audit & consistency | Rule: unindexed | An interesting workspace file with no files row. Healed with sync_row | workspace_audit.py:116-120, :365 | scan/heal | A-103, B-038 |
| K1-052 | Audit & consistency | Rule: db-orphan (DB to disk) | A files row whose workspace/ file is missing. Healed with remove_file (deletes the row) | workspace_audit.py:121-128, :412 | scan/heal | B-039 |
| K1-053 | Audit & consistency | Rule: parallel-registry | From scan_registry_violations. Healed by deleting projects.json; connectors.json and company_agents.json are FLAGGED as pending reader migration | workspace_audit.py:136-142, :415-429 | scan/heal | A-103 |
| K1-054 | Audit & consistency | Rule: agent-incomplete | An agents row with NULL nature. The doc says nature or group, but the code checks only nature. Flag only (heal no-op). | workspace_audit.py:147-156 | scan | B-040 |
| K1-055 | Audit & consistency | Rule: agent-invisible | A DB agent name that is missing from agents_registry.all_agents(), the /agents/all roster. Flag only. | workspace_audit.py:157-165 | scan | B-040 |
| K1-056 | Audit & consistency | Rule: agent-unregistered | A project agents.json roster member with no agents row (checked by lower(name) or slug). Flag only. | workspace_audit.py:168-186 | scan | B-040 |
| K1-057 | Audit & consistency | Rule: root-stray | When watch_root is on, any repo-root item outside the core apps/files and not a dotfile is FLAGGED for owner review | workspace_audit.py:187-192, :410 | scan/heal | A-103 |
| K1-058 | Audit & consistency | Rule: duplicate (identical) | A matching sha256 across ≥2 projects' code/deploy files. Healed by promote_to_shared of the first copy, repointing the others and deleting their copies | workspace_audit.py:197-215, :382-394 | scan/heal | A-103, B-038 |
| K1-059 | Audit & consistency | Rule: duplicate (same name, different content) | FLAGGED: promote a shared base plus custom deltas after review | workspace_audit.py:216-225, :408 | scan/heal | B-038 |
| K1-060 | Audit & consistency | Rule: foreign-ref | A project file that references a real file inside another real project (regex projects/<id>/<tail>). Healed by promoting the target, repointing, and rewriting the referrer source; unresolvable targets are FLAGGED | workspace_audit.py:226-254, :395-407 | scan/heal | A-103, B-038 |
| K1-061 | Audit & consistency | Rule: external-write | A project whose localPath is outside workspace and holds generated dirs (soc/knowledge/reports/history/intel-cache/enrich-cache/findings) or generated files (soc_inventory.json, run-*.json, *-report-*, *-health-*, findings*.json, asset-inventory.md) is flagged | workspace_audit.py:263, :294 `_external_writes`, `_gen_files` | scan | F11 (count only); no row |
| K1-062 | Scheduling & notifications | Audit sentinel (proactive) | Runs heal(force) then scan. If any HARD issue remains (external-write, foreign-ref, parallel-registry, misplaced, duplicate) it raises a notifications_store finding (critical when an external-write exists) | workspace_audit.py:314 `sentinel` | scheduler.py:450 loop | no |
| K1-063 | Audit & consistency | Audit log | Appends each heal action to workspace/history/audit-log.jsonl and syncs the row | workspace_audit.py:45, :338 `_log` | heal | C-028, A-104 |
| K1-064 | Audit & consistency | heal() | Respects the debounce unless forced, skips protected projects, applies the fix per type and returns healed/flagged counts | workspace_audit.py:350 | /audit/run, sentinel | A-103 |
| K1-065 | Middleware & DB registry | Legacy _add_dependency (dead code) | An older duplicate of mw.add_dependency, projects only, with a non-idempotent dependencies insert. Nothing calls it. | workspace_audit.py:443 | none | no |
| K1-066 | Audit & consistency | violations() / status() | Last N audit-log records, and {config, debounce, open_issues} | workspace_audit.py:469, :481 | routes | C-028 |
| K1-067 | Audit & consistency | HTTP /audit routes | GET /status, GET /scan, POST /run(force), GET /violations, GET/POST /config | workspace_audit.py:485-511 | app.py:175 router | C-028 |
| K1-068 | Synchronization & Anchor | GET /audit/mirror | A compact bundle (25 issues, 20 violations, detail capped at 120 chars) mirrored to the anchor so it never exceeds the 413 size limit | workspace_audit.py:513 | local poller | A-104 |
| K1-069 | Middleware & DB registry | store _REMAP (legacy JSON relocation) | Repoints flat data/*.json to workspace homes: core-registry (projects, company_agents, connectors, connector_keys), config/models.json, utils (soc_settings, hubspot_scopes), chats (chat_registry, _seq_counters), anchor-layer (anchor_config/manage/queue/sync) | store.py:21-40 | read_json/write_json | no |
| K1-070 | Structural | store path router _p | projects/* goes to workspace/projects, scope_files goes to chats/files, scopes goes to chats/scopes, anything else to data/ | store.py:43 | all store callers | A-064, C-044 |
| K1-071 | Middleware & DB registry | Per-project sharded JSON stores | main_tasks/operations/run_timings/approvals/schedules/notifications .json are split by pid into projects/<pid>/data/jsons/, with unknown pids going to projects/_shared. Reads merge them; writes delete and rewrite all shards under a lock | store.py:70-150 `_SHARDED`, `_real_pids`, `_shard_dir`, `_read_sharded`, `_write_sharded` | read_json/write_json | no |
| K1-072 | Middleware & DB registry | read_json / write_json / ensure_dir / now | Atomic tmp-and-replace write, then best-effort workspace_mw.sync_row lockstep. Note that sharded writes skip sync_row. | store.py:61, :153, :166, :182 | everywhere | C-044 |
| K1-073 | Orchestration core | directions.overview | Live counts for every odin_core table, plus agent and project type histograms | directions.py:37 | GET /directions/overview | B-063, C-030 |
| K1-074 | Orchestration core | directions.find | ILIKE search over projects, agents, connectors, chats, shared_capabilities and files | directions.py:53 | GET /directions/find | C-030 |
| K1-075 | Orchestration core | directions.capability (reuse advisory) | Shared capabilities, used_by (dependencies), also_built_in (custom code/deploy/tests files) give the verdict EXISTS in shared / EXISTS as custom / NOT FOUND, plus a reuse recipe (no `_2` duplicates) | directions.py:67 | GET /directions/capability | B-064, C-030 |
| K1-076 | Orchestration core | directions.resources / similar | An owner's files, dependencies, connectors and agents (via the link tables). similar() does a keyword ILIKE over files.description | directions.py:102, :113 | GET /directions/resources, /similar | C-030 |
| K1-077 | Orchestration core | /directions router | Five GET routes | directions.py:125 | app.py:166 | C-030 |
| K1-078 | Audit & consistency | Truth gate: claims_success / assess | Success regex plus hedge regex give VERIFIED/FAKE/UNVERIFIED/NO-CLAIM and a fake_risk (1.0/0.7/0.4) | audit.py:17-46 | gate_success | A-034, §0 l.62 |
| K1-079 | Audit & consistency | gate_success | Passes the text only if verified. Otherwise "BLOCKED FAKE CLAIM" (the check failed) or "UNVERIFIED" | audit.py:49 | agent final messages | A-034 |
| K1-080 | Audit & consistency | correction_prompt | Re-prompts an agent that claimed success without evidence | audit.py:62 | orchestration | §0 l.62 |
| K1-081 | Audit & consistency | Hidden-fault scan ("snake") | _DANGER signatures (Prisma P####, drift, TS errors, ELIFECYCLE, missing module, port, cmd not found, timeouts, EACCES, ENOSPC, OOM, fatal, unhandled rejection, FAIL/exit≠0, security deprecation). Matches are excluded by _BENIGN. | audit.py:74-98, :111 `scan_hidden_faults` | api_v2:1662/2315/2682/2776, e2e tests | A-035 |
| K1-082 | Audit & consistency | Build-mode transient tolerance | When build=True, transient labels (module/TS/tool/port/npm/connection) count only within the final 20 lines | audit.py:105-108, :128 | api_v2:2315/2776 | no |
| K1-083 | Safety & approvals | audit_deploy_proposal | Flags a placeholder host (@VM), rsync --delete without REQUIRED_EXCLUDES (.env, .backup-env, *.pem, *.key, public, uploads, prisma/migrations), or `az` over SSH | audit.py:140-157 | e2e_ai_capability:218 | no |
| K1-084 | Safety & approvals | audit_prompt (broken directives) | Flags prompts that request az run-command/control plane, `migrate dev`, or `migrate reset/--force` | audit.py:160-177 | api_v2:1634 | no |
| K1-085 | Audit & consistency | engine_audit | LLM second-opinion auditor that returns fake_risk, unverified_claims and a verdict as JSON | audit.py:180 | orchestration | §0 l.62 |
| K1-086 | Safety & approvals | Read-only PreToolUse hook DENY list | Blocks rm/mv/cp/tee/dd/truncate, sed/perl -i, mkdir/touch/ln/chmod/chown, npm/yarn/pnpm installs/builds, eslint --fix, prettier --write, prisma, git mutations, systemctl/service control, sudo, reboot, kill, docker, pm2, scp/sftp, rsync without dry-run, az vm run-command and az mutations, curl POST/PUT/DELETE/PATCH, and wget -O | readonly_hook.py:12-34 | claude_cli.py:20 (read-only runs) | D-043, C-029 |
| K1-087 | Safety & approvals | Safe-redirect rule | Redirects to /dev/null, /dev/std*, fd dups, /tmp/ and /var/tmp/ are allowed. Any other > or >> blocks with exit 2. | readonly_hook.py:36-53, :64 `_has_unsafe_redirect` | hook main | no |
| K1-088 | Safety & approvals | Hook block messages | The block messages tell the agent to PROPOSE edits and commands for approval and not to work around the block | readonly_hook.py:65-76 | hook main | D-043 |
| K1-089 | Middleware & DB registry | Company agents come from the DB | No company_agents.json. A company agent is a DB agent whose own index.json has company:true | agents_registry.py:22-56 `_db_agent_ids`, `_agent_cfg`, `list_company_agents` | GET /company/agents (api_v2:195), projects.py:784 | A-076, C-005 |
| K1-090 | Middleware & DB registry | add_company_agent | Writes the agent's own index.json (company:true, type operational) via put_file | agents_registry.py:59 | POST /company/agents | A-076 |
| K1-091 | Middleware & DB registry | remove_company_agent | If project_agents refs = 0, delete_owner; otherwise keep the agent and unmark company. On error it keeps the agent. | agents_registry.py:78 | DELETE /company/agents/{name} | A-076 |
| K1-092 | Middleware & DB registry | all_agents roster (DB-surfaced) | Project rosters plus company agents plus every odin_core agent not yet shown (tagged with its linked project or "Company", level=db) | agents_registry.py:108 | GET /agents/all (api_v2:202), audit agent-invisible | B-042 |
| K1-093 | Orchestration core | Excluded agents | A removed agent goes into agents.json "excluded" and is never auto-re-added unless force=True | agents_registry.py:150-157, :181 | register_agent, projects.py:391, api_v2:2096 | no |
| K1-094 | Middleware & DB registry | register_agent (DB contract) | Adds the agent to the roster JSON (resources default from projects.resources_block), writes the capability doc, appends a project rule, upserts a complete agents row (nature defaults to operational) and a project_agents link | agents_registry.py:175 | api_v2:267/509/2099, projects.py:772/785, soc_blueprint | B-041, B-053 |
| K1-095 | Orchestration core | update_agent / get_agent / list_agents / _save | Roster JSON CRUD at projects/<pid>/agents.json | agents_registry.py:104, :160, :167, :242 | api_v2:525 | C-006 |
| K1-096 | Middleware & DB registry | remove_agent DB lockstep | Drops the link. If there are no links and no agent folder, deletes the agents row | agents_registry.py:255 | api_v2:533/870/876 | B-041 |
| K1-097 | Orchestration core | record_usage / stats | Invocation counts, lastActive and percent share | agents_registry.py:280, :290 | api_v2:306/498/2106/3394, projects.py:1424 | A-075, C-009 |
| K1-098 | Orchestration core | save_rule ("save as permanent rule") | Adds a rule to the agent and appends "- RULE:" to its capability doc | agents_registry.py:306 | api_v2:538, projects.py:780/790 | A-074 |
| K1-099 | Structural | Agent skill doc at agents/<slug>/capability.md | One home per agent (falls back to projects/<pid>/plan/<slug>.md). Writes Skills, Restrictions and Custom rules, then indexes it | agents_registry.py:317-359 `_skill_path`, `_write_skill_file`, `_append_skill`, `_index` | register/update/save_rule | A-074 (path not stated) |
| K1-100 | Orchestration core | Project team rule line | Appends "- **name** (role): desc" to projects/<pid>/instructions/instructions.md | agents_registry.py:362 `_append_project_rule` | register_agent | no |
| K1-101 | Orchestration core | ROLE_HINTS (Fullstack merge) | Keyword-to-role map. front/ui/back/api/web/sql/db all map to Full-Stack Engineer; also mobile, devops, security, qa and data | agents_registry.py:377 | suggest_agent | §0 l.33 (Fullstack) only |
| K1-102 | Orchestration core | _default_resources template | Allowed-Resources & Dependencies text. Operational: default-vs-app key from oth/.cred, works after deploy, ask the CTO once. Technical: permissions, env/keys, needs | agents_registry.py:393 | suggest_agent | no (B-173 is projects.resources_block) |
| K1-103 | Orchestration core | suggest_agent | Keyword role and nature (operational keyword list), then an LLM draft (name/role/nature/desc/resources/env JSON) with template fallback | agents_registry.py:416, :468 `_safe_json_obj` | POST /agents/suggest, api_v2:2098, projects.py:417 | A-069, A-074 |
| K1-104 | Orchestration core | AVATARS set | frontend, backend, devops, security, qa, database, generic | agents_registry.py:15 | register/add | no |
| K1-105 | Orchestration core | Cached-modules pool access | list_for_role reads <Role>/*.meta.json plus Miscellaneous. _role_dir maps to DevOps/Mobile/Fullstack | cached_modules.py:23, :36 | index_text | B-204 |
| K1-106 | Orchestration core | index_text (pool prompt) | "CACHED MODULES POOL" catalog with the rule "DECIDE: reuse if it fits; only status 'working'" | cached_modules.py:55 | api_v2:2457 | B-204 |
| K1-107 | Testing | ODIN_DISABLE_CACHE flag | ODIN_DISABLE_CACHE=1 hides the pool (baseline timing) | cached_modules.py:18 `cache_enabled` | env | T-11, A list l.1146 |
| K1-108 | Orchestration core | has_pool_for | Bool helper | cached_modules.py:76 | — | no |
| K1-109 | Orchestration core | Persistent chats store | One JSON per chat in workspace/chats. list (skips logically deleted), create (reuses an empty "New chat"), get, add_message (title from the first user message, 40 chars), set_session (Claude resume id), rename, delete (falls back to a logical delete) | chats.py:18-96 | app.py:270-350 /chats routes | A-108, A-111, C-017 |
| K1-110 | Testing | Scope guide test: probes | 4 probes per project (read count by noun, status read, ambiguous, owner out-of-scope VM). The noun comes from type/category | scope_guide_test.py:57-89 `_scope_noun`, `probes_for` | CLI `__main__` | A-100 |
| K1-111 | Testing | Run probe through the real stack | scope_answer_guard, then read_execute_guard (if a read), then api_v2._engine_stream (read-only unless auto_approve). Flags propose, clarify and refuse | scope_guide_test.py:93 `_run_probe` | audit_project; scope_reasoning_test | A-100 |
| K1-112 | Audit & consistency | Heuristic reply-quality signals | _PROPOSE_SIGNALS (proposal, approval, "I'm blocked", /permissions, "shall I run"…), _CLARIFY_SIGNALS, _REFUSE_SIGNALS. _grade means the owner is never proposed to, gated or refused | scope_guide_test.py:32-53, :143 | _evaluate (judge off) | A-100 |
| K1-113 | Audit & consistency | LLM judge classes | ANSWERED_IN_SCOPE / UNNECESSARY_CLARIFICATION / WRONG_SCOPE / BLOCKED_OR_APPROVAL / LEGIT_CLARIFICATION. An offer after an answer still passes. An unparseable verdict defaults to a pass | scope_guide_test.py:197-283 `_judge`, `_evaluate` | audit_project | A-100 |
| K1-114 | Audit & consistency | scope-answer violation logging | Writes type "scope-answer" to audit-log.jsonl and the probes to history/scope-probes.jsonl, both synced to the DB | scope_guide_test.py:163, :181 | audit_project | A-100, §0 l.61 |
| K1-115 | Testing | Scope guide run_all | Every non-protected project, aiming for zero violations; CLI --dry / --model= | scope_guide_test.py:287-341 | CLI | A-100, C-046 |
| K1-116 | Testing | Scope reasoning test: generated probes | LLM generates fresh IN_SCOPE_DEEP / CROSS_SCOPE_TRAP / AMBIGUOUS / OOS_OWNER questions from a project brief (including company connectors), with fallback probes | scope_reasoning_test.py:40-131 | audit_project | A-101 |
| K1-117 | Audit & consistency | Reasoning judge metrics | Per-category rubric gives FALSE_REFUSAL / LEAKAGE / WRONG_AMBIGUITY / WRONG_OOS. An unparseable verdict is a FAIL (fail-closed). An answer under 15 chars is ENGINE_EMPTY | scope_reasoning_test.py:135-220 | audit_project | A-101 |
| K1-118 | Testing | Reasoning run_all scorecard | Fail counts by type, skips protected projects, logs scope-answer | scope_reasoning_test.py:223-257 | CLI/import | A-101, C-046 |
| K1-119 | Middleware & DB registry | odin_core schema | 14 tables plus 16 file-by-folder views (see §3b) | odin_core_schema.sql | Postgres | B-060, B-057 |
| K1-120 | Middleware & DB registry | v_* per-folder views | v_capability, chat, code, connectors, data, dependencies, deploy, docs, features, handoff, instructions, outputs, plan, restrictions, schedule, tests, each a JOIN of files and folders on folder name. No view for files/ or jsons/. v_capability and v_handoff match folder names that are only root files. | odin_core_schema.sql:269-601 | none in my files | no |
| K1-121 | Synchronization & Anchor | odin_anchor schema | anchor_requests(id PK, status, created, data jsonb) plus idx_ar_created and idx_ar_status | odin_anchor_schema.sql:27-54 | anchor (not my files) | A-191 (DB only) |
| K1-122 | Structural | Placement decision Q1/Q2 | Scope picks projects/shared/chats/agents/anchor-layer. Type picks docs/files/scripts/jsons/approvals/deploy/index.json/rules.md | WORKSPACE-SCHEMA.md:11-32 | agents/CTO read | B-079 |
| K1-123 | Structural | Doc project skeleton (9 entries) | index.json, rules.md, agents.json, docs, files, jsons, approvals, scripts, deploy. This conflicts with the code (K1-002/029) and the real disk (14 subfolders, no rules.md/jsons/approvals/scripts at project root). | WORKSPACE-SCHEMA.md:36-55 | doc | B-080 |
| K1-124 | Structural | Doc agent skeleton and registration contract | 3 root files plus 5 subfolders, no rules.md/files. create → complete DB row → project_agents → visible on /agents/all, enforced by agent-incomplete/agent-invisible | WORKSPACE-SCHEMA.md:57-78 | doc/audit | B-081, B-082 |
| K1-125 | Structural | Shared layer and non-project roots | core-registry, config, directions, runbooks, skills, infra, testing, utils, assets, oth, cached_modules. Roots: chats, anchor-layer, docs, state, history, logs | WORKSPACE-SCHEMA.md:80-106 | doc | B-083, B-084 |
| K1-126 | Structural | Schema invariants 1-6 | Same entries, nothing loose, shared vs owner, empty folders kept with .gitkeep, one canonical file per function | WORKSPACE-SCHEMA.md:108-115 | doc | B-085 |
| K1-127 | Other | Structuring plan phases 0-7 and guardrails | Each phase is done only at 100% green and is reverted if red. Covers baseline, structure, E2E, odin_core seed, middleware door plus write-guard, hard test, directions short-path, lazy load/sync/notify | STRUCTURING-PLAN.md:1-80 | doc | B-069…B-078 |
| K1-128 | Orchestration core | Project-type configs | normal (on-demand), one-time (run-once, followups), periodical (play+period, schedule required), recurring (play+cadence, schedule required), vertical (timeout). Each has a UI chip and controls | shared/config/project-types/*.json | GET /project-types | C-003, C-050 |
| K1-129 | Orchestration core | Agent-type configs | operational, security and technical, each with an allowed group list and UI chip | shared/config/agent-types/*.json | UI/agents | C-050 |
| K1-130 | Safety & approvals | System identity and approval gate config | requiresApprovalFor 10 classes; autoAllowed: read-only analysis, planning, drafting, history-logging, dashboard-render; blockProductionWithoutApproval; riskLevels; operatingPrinciples; paths | shared/config/system-identity.json | orchestrator | C-050; B-008 (cites system.config.json) |
| K1-131 | Other | Company profile | Owner/domain, Azure tech profile (many TBD), compliance (fintech-payments, HIPAA), security posture (closed ports, IP allowlist), phases, open questions | shared/config/company-profile.json | CTO context | C-050 |
| K1-132 | Orchestration core | Model scopes config | main=claude-cli plus per-project/member overrides (leftover e2e-landing qwen entries) | shared/config/models.json | models_config | A-012, C-015 |
| K1-133 | Voice | Voice feature registry | feature voice, icon streaming-voice, capability shared/features/voice. That folder holds only an empty .gitkeep | shared/config/features/voice.json; shared/features/voice/.gitkeep | project features | C-043, C-050 |
| K1-134 | Orchestration core | Cached modules pool doctrine | Role folders, .meta.json sidecar schema, status working/needs-update/not-working, add-only-proven rule. The pool is empty on disk (README plus .DS_Store only) | shared/cached_modules/README.md | role agents | B-204, B-205, B-206 |

## 2. Not in MFI

K1-005 Violation class (unused); K1-006 _kind; K1-007 _db best-effort; K1-008 _area; K1-010 resolve_path; K1-011 _infer_owner; K1-015 mw-corrections.jsonl correction log; K1-017 owner-row auto-create from index.json in sync_row; K1-018 remove_file; K1-020 _rewrite_owner_refs; K1-022 request_capability; K1-031 sync_folders; K1-061 external-write audit rule (_external_writes/_gen_files; only a count in paper F11); K1-062 workspace_audit.sentinel proactive heal and notify (scheduler.py:450); K1-065 dead legacy _add_dependency; K1-069 store _REMAP; K1-071 per-project sharded JSON stores (data/jsons, _shared bucket); K1-082 build-mode transient-fault tolerance; K1-083 audit_deploy_proposal + REQUIRED_EXCLUDES; K1-084 audit_prompt broken directives; K1-087 safe-redirect rule; K1-093 excluded-agents never auto-re-added; K1-100 _append_project_rule; K1-102 _default_resources template; K1-104 AVATARS; K1-108 has_pool_for; K1-120 v_* views.
Partial or conflicting: K1-033 delete_owner has no chats/scopes purge in this snapshot (MFI B-054/C10 says it does); K1-054 checks only nature, not group (the doc says both); K1-123 three different skeletons exist (doc 9, code 17, ROADMAP 16) and disk follows the code.

## 3. Requested-category confirmations

**(a) Folder-structuring rules: FOUND.**
- Code: PROJECT_SUBFOLDERS/AGENT_SUBFOLDERS/ROOT_FILES (workspace_mw.py:19-28), validate (:55), route redirect rules (:103), owner-scope redirect (:153), PROJECT_SKELETON/AGENT_SKELETON (:625-628), create_owner (:661), shared-vs-owner promotion (:371, :434).
- Store: per-project shard placement (store.py:70-150).
- Doc: WORKSPACE-SCHEMA.md §1-6 (conflicts with code), STRUCTURING-PLAN.md.
- Real tree on disk:
  - `workspace/{shared,backups,projects,history/{snapshots,daily},agents,connectors,anchor-layer/sim_responses,state,docs}`.
  - shared/ holds skills/odin-cto-brain, config/{project-types,features,agent-types}, oth, assets, features/voice, runbooks, tutorials, handoffs, cached_modules, connectors, testing/results, infra/{anchor,azure,deploy-lists,manifests}, directions/design, utils, core-registry.
  - 11 projects plus `_shared/data`. Each real project has exactly 14 subfolders: dependencies, deploy, plan, instructions, code, features, restrictions, files, chat, tests, data, schedule, connectors, docs. There is no jsons/, scripts/ or approvals/ at the root.
  - 32 agents, each with dependencies/instructions/code/restrictions/outputs.
  - Connectors: veeqo, hubspot, klaviyo, claude-cli and az-cli each have config/code/docs, plus 4 hash-named dirs (c2907f27, a320ce72, 5145865a, ea9eedee) with no subfolders.
  - There is no workspace/chats or workspace/logs directory, although the doc and code reference both.

**(b) Full DB schema: FOUND.**

*odin_core tables:*

| Table | Columns | Keys and constraints |
|---|---|---|
| agent_scope | project_id text NN, agent text NN, service, credential_ref, read_only bool default true | PK(project_id, agent) |
| agents | id NN, name, role, type, "group", nature, mode, path, description, created_at, modified_at | PK id |
| chats | id NN, title, path, description, created_at, modified_at | PK id |
| connectors | id NN, name, path, description, created_at, modified_at, registry_id | PK id |
| dependencies | id bigint (dependencies_id_seq), owner_type NN, owner_id NN, name, source_path, shared_capability_id, kind, mode, overlay_path, description | PK id; FK shared_capability_id→shared_capabilities(id), no cascade |
| external_report | project_id NN, path NN | PK project_id |
| files | id bigint (files_id_seq), folder_id, owner_type, owner_id, name, path NN, kind, description, size_bytes, created_at, modified_at | PK id; FK folder_id→folders(id) ON DELETE CASCADE; no UNIQUE on path |
| folders | id bigint (seq), owner_type NN, owner_id NN, name NN, path NN, description | PK id; UNIQUE(owner_type, owner_id, name); CHECK owner_type IN (project, agent, connector, chat, shared, workspace) |
| project_agents | project_id, agent_id | PK(both); FK→projects and →agents, ON DELETE CASCADE |
| project_chats | project_id, chat_id | PK(both); FK→projects and →chats, CASCADE |
| project_connectors | project_id, connector_id | PK(both); FK→projects and →connectors, CASCADE |
| projects | id NN, name, type, category, cadence, config jsonb default '{}', status, path, description, created_at, modified_at, features jsonb default '[]' | PK id |
| shared_capabilities | id NN, category, name, path, description, created_at, modified_at | PK id |

- 16 views (see K1-120).
- No secondary indexes in odin_core.

*odin_anchor:* anchor_requests(id PK, status, created double, data jsonb), with btree idx_ar_created and idx_ar_status.

*Writers and readers per table (file:line):*

| Table | Writers | Readers |
|---|---|---|
| projects | workspace_mw.sync_row:222 (upsert); create_owner:693; delete_owner:744 | directions overview:43,48 / find:58; agents_registry.all_agents:137 (join); mw.scan_registry_violations:594 |
| agents | sync_row:228; create_owner:698; delete_owner:747; agents_registry.register_agent:229; remove_agent:273 | agents_registry._db_agent_ids:30, all_agents:132, register:225, remove:266; workspace_audit.scan:151,175-176; directions:44,47,59,109 |
| connectors | sync_row:236 | directions find:60, resources:108; scan_registry_violations:594 |
| chats | sync_row:239 | directions:45,61 |
| folders | sync_row:245; sync_folders:644; delete_owner:737 | v_* views only |
| files | sync_row:250-251 (delete + insert); remove_file:281; delete_owner:736 | workspace_audit.scan:113; directions find:63, capability:76, resources:106, similar:121 |
| dependencies | add_dependency:331; workspace_audit._add_dependency:460 (dead); delete_owner:738 | directions capability:73, resources:107 |
| shared_capabilities | add_dependency:327; workspace_audit._add_dependency:458 | directions capability:72, find:62 |
| project_agents | register_agent:235; remove_agent:268; delete_owner:741,746 | remove_company_agent:86; all_agents:137; remove_agent:269; directions:46,109 |
| project_connectors | delete_owner:742 (delete only; no inserter in my files) | directions:46,108 |
| project_chats | delete_owner:743 (delete only) | none |
| agent_scope | _ensure_agent_scope:837 (DDL); set_agent_scope:852 | agent_credential_ref:869; list_agent_scope:885 |
| external_report | _ensure_external_report:929 (DDL); set_external_report_ref:916 | external_report_ref:942 |
| anchor_requests | none in my files | none in my files |

**(c) Middleware functions and prompt guards: FOUND.**
- Every workspace_mw function is listed above (K1-005…K1-043).
- Prompt guards:
  - scope_answer_guard (:770)
  - read_execute_guard (:804)
  - agent_scope_guard (:890)
  - vm_diagnosis_guard (:966)
  - tutorial_guard (:1001)
- Other prompt-injected rules: cached_modules.index_text DECIDE rule (:62-72), audit.correction_prompt (:62), and the readonly_hook block messages (:65-76).

**(d) Audit and consistency rules: FOUND.**
- Rules: misplaced, unindexed, db-orphan, parallel-registry, agent-incomplete, agent-invisible, agent-unregistered, root-stray, duplicate (identical and different), foreign-ref, external-write. Each one's detection and healing is in K1-050…K1-061.
- Mechanics: protected-project skip, debounce, sentinel notify, truth gate (FAKE/UNVERIFIED), hidden-fault scan, deploy-proposal and broken-directive audits.
- Reply quality: scope-answer reply rules cover blocked/proposed/refused, unnecessary clarification, wrong scope/leakage, false refusal, wrong ambiguity, wrong OOS, and an empty engine reply.
- Stuck, generic and wrong-format reply rules: NOT FOUND in my files. Only the classes above and fake-success exist (consistent with MFI A-107).

**(e) Database-registry rules: FOUND.**
- The DB is the only registry: workspace_mw.py:563-605 (REGISTRY_GUARD, scan_registry_violations), workspace_audit.py:129-142 and :415-429 (projects.json deleted; connectors.json and company_agents.json flagged pending), agents_registry.py:22-25 (no company_agents.json) and :125 (roster from the DB).
- Lockstep: sync_row on every put_file, store.write_json (store.py:176) and audit write; remove_file; create_owner/delete_owner; register_agent/remove_agent; bidirectional audit with unindexed and db-orphan.
- Parallel-registry guard: K1-026/027/053.
- Gaps:
  - store._REMAP still routes projects/company_agents/connectors/connector_keys.json to shared/core-registry, so those readers remain live.
  - Sharded store writes skip sync_row.
  - All DB sync is best-effort and silently skipped when odin_core is down.


<!-- ==================== PART K2A ==================== -->

# K2A — server/api_v2.py (3,568 lines, read in full, lines 1–3568)

Scope: `/home/claude/v1src/server/api_v2.py` only. Secrets are named, never copied. MFI = `/home/claude/MFI.md`.
"no (near X)" means a related MFI row exists, but this specific behaviour is not described there. These rows are counted as **not in MFI**.

## 1. Capabilities found

| ID | Category | Capability | What it does | Evidence | Triggered by | In MFI? |
|---|---|---|---|---|---|---|
| K2A-001 | Structural | v2 API router module | Builds the FastAPI `APIRouter` holding all v2 routes; mounted by server/app.py | api_v2.py:94 `build_router` | app.py mount (`/v2`) | C-002 (module listed) |
| K2A-002 | Structural | Request body models | Pydantic bodies: ProjectIn (name, identifier, description, localPath, members, type, stack, url, mode build/deploy, sources, autoApprove, periodic, cadence), MappingIn, AgentIn (nature, resources, env), DescIn, IntakeIn, RuleIn, TitleIn, ModelIn, ScheduleIn | api_v2.py:26–87 classes | every POST route | C-002 |
| K2A-003 | Structural | SSE formatter | `event:/data:` server-sent-event string builder used by every stream | api_v2.py:90 `sse` | all streams | no |
| K2A-004 | Structural | Unused ROOT constant | `ROOT` (repo root path) is defined but never used | api_v2.py:22 | — | no |
| K2A-005 | Orchestration core | List active projects | GET /projects, excluding archived | api_v2.py:98 `projects_list` | UI project list | C-002 |
| K2A-006 | Orchestration core | List archived projects | GET /projects/archived | api_v2.py:103 `projects_archived` | Archived view | C-002, A-084 |
| K2A-007 | Orchestration core | Archive / unarchive project | POST /projects/{pid}/archive and /unarchive | api_v2.py:108, :113 | UI action | C-002 |
| K2A-008 | Orchestration core | Create project | POST /projects, passing mode (build vs deploy an existing app), read-only sources, autoApprove (pre-authorization), periodic schedule, cadence (once/recurring/periodical) and owner identifier | api_v2.py:118 `projects_create` | New-project / intake confirm | C-002, A-071 |
| K2A-009 | Orchestration core | Suggest project identifier | GET /projects/suggest-id from name + localPath | api_v2.py:127 | New-project form | C-002 |
| K2A-010 | Orchestration core | Project types + operational members | GET /project-types returns types and the operational member catalogue | api_v2.py:132 | New-project form | C-003 |
| K2A-011 | Safety & approvals | Validate proposed agent names | POST /agents/validate classifies names as known catalogue roles vs unknown (a confirmation is needed before creating them), which prevents silent agent invention | api_v2.py:137 `agents_validate` → `projects.classify_team` | Intake / team UI | C-005 |
| K2A-011a | Orchestration core | CTO capability-gap dialog | POST /projects/{pid}/capability returns ranked existing agents for a task plus a suggested new custom agent (name/role/rules). Read-only, creates nothing | api_v2.py:144 `project_capability` → `projects.capability_options` | CTO capability dialog | C-003 (route only; reuse-vs-create ranking not described) |
| K2A-012 | Orchestration core | Roles readiness | GET /roles returns role readiness | api_v2.py:151 | UI | C-003 |
| K2A-013 | Orchestration core | Adaptive intake step | POST /projects/intake: next question or final proposal with dependencies | api_v2.py:156 `projects_intake` → `projects.intake_step` | Intake chat | C-004, A-073 |
| K2A-014 | Orchestration core | Intake resource readiness check | GET /projects/intake/readiness tests whether Claude CLI is available, Azure is reachable (`infra_az.connect_test`) and which connectors exist | api_v2.py:162 `intake_readiness` | Intake confirm screen | C-004 |
| K2A-015 | Per-project features & integrations | Capabilities snapshot | GET /capabilities: what is connected and what can be connected | api_v2.py:185 | UI | C-003, B-186 |
| K2A-016 | Orchestration core | Company agents list/add/remove | GET/POST /company/agents and DELETE /company/agents/{name} (defined once, auto-added to new projects) | api_v2.py:192, :204, :210 | Company agents panel | C-005, A-076 |
| K2A-017 | Orchestration core | Org-wide actual-agent roster | GET /agents/all: every project's agents + company agents (not the 20-role catalogue) | api_v2.py:199 `agents_all` | Main page | C-005, B-042 |
| K2A-018 | Per-project features & integrations | Connectors CRUD | GET/POST /connectors, DELETE /connectors/{cid} (API-key integrations with a status badge) | api_v2.py:216, :221, :226 | Connectors panel | C-010, A-077 |
| K2A-019 | Safety & approvals | List approvals | GET /approvals (pending by default; `all=1` for full history; per pid) | api_v2.py:232 `approvals_list` | Approval popup/panel | C-011 |
| K2A-020 | Safety & approvals | Pending approval count | GET /approvals/count | api_v2.py:239 | Badge | C-011 |
| K2A-021 | Safety & approvals | Approve, dispatched by kind | POST /approvals/{aid}/approve routes by `kind`: deploy / synclist / db-migrate / qa-recommendation; anything else not yet applied runs `_apply_approval_bg` in a background thread | api_v2.py:244 `approvals_approve` | Approve button | C-011 |
| K2A-022 | Safety & approvals | Deploy-approval execution | An approved `deploy` creates an operation. For a deploy-type project it runs `_op_after_deploy` (deploy, then the DB gate or the diagnosis); otherwise it runs `_deploy_bg` | api_v2.py:248–256 | Approve (kind=deploy) | no (near C-011/C-012) |
| K2A-023 | Safety & approvals | Synclist-approval execution | An approved `synclist` runs `_op_apply_synclist` (re-baseline) | api_v2.py:257–259 | Approve (kind=synclist) | no |
| K2A-024 | Safety & approvals | DB-migrate-approval execution | An approved `db-migrate` runs `_op_apply_dbmigrate` | api_v2.py:260–262 | Approve (kind=db-migrate) | no (near B-132) |
| K2A-025 | Safety & approvals | QA-recommendation approve | On approval, registers a QA agent ("Added on the owner's approval") if missing and sets the flags qa_asked=True, qa_declined=False; QA gates from the next task | api_v2.py:263–269 | Approve (kind=qa-recommendation) | no |
| K2A-026 | Safety & approvals | Reject, dispatched by kind | POST /approvals/{aid}/reject. qa-recommendation → qa_declined=True ("never ask again"). Deploy on a deploy project → opens the separate re-baseline gate. synclist → posts "leaving the change-list as is… press play" and stops (no silent jump to diagnosis). db-migrate → skips it and runs the diagnosis | api_v2.py:276 `approvals_reject` | Reject button | no (near C-011) |
| K2A-027 | Orchestration core | Get project + agents + stats + schedules | GET /projects/{pid} merges project, agents, usage stats and scheduler tasks | api_v2.py:299 | Project page | C-002 |
| K2A-028 | Orchestration core | Update / delete project | POST /projects/{pid}/update, DELETE /projects/{pid} | api_v2.py:309, :317 | Project settings | C-002 |
| K2A-029 | Per-project features & integrations | Local↔cloud folder mapping | POST /projects/{pid}/mappings (local, cloud, role) | api_v2.py:322 `projects_map` | Map toolbar | C-002, A-047 |
| K2A-030 | Orchestration core | View project plan | GET /projects/{pid}/plan → `projects.generate_plan` | api_v2.py:330 | Plan toolbar | C-008 |
| K2A-031 | Orchestration core | Auto cross-agent remediation | POST /projects/{pid}/remediate: finding → CTO → FE/BE fix → DevOps redeploy proposal | api_v2.py:335 → `projects.auto_remediate` | UI / SOC finding | C-008, B-105 |
| K2A-032 | Orchestration core | Per-project custom rules CRUD | GET/POST /projects/{pid}/rules, POST/DELETE /rules/{rid}; edited live | api_v2.py:342–360 | Rules panel | C-007, A-078 |
| K2A-033 | Build, packaging, run & clients | Sync / deploy proposals | GET /projects/{pid}/sync and /deploy return proposals | api_v2.py:362, :367 | Sync/Deploy toolbar | C-012, B-026 |
| K2A-034 | Build, packaging, run & clients | Sync / deploy run (legacy) | POST /projects/{pid}/sync/run and /deploy/run → `projects.sync_run` / `deploy_run` | api_v2.py:372, :377 | Toolbar | C-012 |
| K2A-035 | Orchestration core | Static team orchestration SSE | GET /projects/{pid}/orchestrate?goal= streams `_orchestrate_gen`. This is the only remaining entry to the static pipeline (see K2A-072) | api_v2.py:382 `projects_orchestrate` | TeamRun panel (SSE) | C-013, A-066 |
| K2A-036 | Build, packaging, run & clients | Deterministic deploy config | GET/POST /projects/{pid}/deploy/config (targets local/vm/excludes/commands/migration, reboot) | api_v2.py:389, :394 → `deploy_runner` | Deploy config UI | C-012 |
| K2A-037 | Safety & approvals | Deploy request = one previewed approval | POST /projects/{pid}/deploy/request builds the exact command preview (an rsync per target with its exclude count, the migration command, target commands, optional `sudo reboot`) and creates ONE approval (kind=deploy, member DevOps). It refuses when no targets are configured | api_v2.py:399 `deploy_run_now` | Deploy button | C-012 |
| K2A-038 | Orchestration core | Background team run start/status/stop | POST /orchestrate/start, GET /orchestrate/status, POST /orchestrate/stop. The run lives on the server, so UI navigation cannot kill it | api_v2.py:423–433 → `start_run`/`run_status`/`stop_run` | ▶ Play / UI poll / Stop | C-013 |
| K2A-039 | Orchestration core | Operations list/latest/get/stop | GET /operations, /operations/latest, /operations/{oid}; POST /operations/{oid}/stop | api_v2.py:436–455 | Ops watcher UI | C-014 |
| K2A-040 | Orchestration core | Smart continue (provide answers) | POST /operations/{oid}/provide stores the owner's answers to a blocked operation, then resumes it in a thread (`_resume_operation`) | api_v2.py:459 `operations_provide` | Blocked-op answer form | C-014 |
| K2A-041 | Build, packaging, run & clients | Direct deploy operation | POST /projects/{pid}/deploy/operation runs `_deploy_bg` as a watchable, stoppable operation (used once a deploy was already approved this session) | api_v2.py:472 `deploy_operation` | Deploy button (post-approval) | C-012 |
| K2A-042 | Scheduling & notifications | ▶ Run now | POST /projects/{pid}/run-now fires a scheduled task or a one-off prompt in the background via `scheduler.run_now` | api_v2.py:482 | ▶ Run button | C-013 |
| K2A-043 | Orchestration core | Project agents list / stats | GET /projects/{pid}/agents and /stats | api_v2.py:490, :495 | Project page | C-006, C-009 |
| K2A-044 | Orchestration core | Suggest agent from description | POST /projects/{pid}/agents/suggest | api_v2.py:500 | Add-member dialog | C-006, A-074 |
| K2A-045 | Orchestration core | Explicit owner add re-allows a removed agent | POST /projects/{pid}/agents registers with `force=True`, which clears the exclusion; carries nature, resources and env | api_v2.py:505 `agents_add` | Add-member | no (near C-006) |
| K2A-046 | Orchestration core | Agent get / update / remove / save rule | GET, POST update, DELETE /projects/{pid}/agents/{name}; POST …/rule saves a rule | api_v2.py:514–541 | MemberView | C-006, B-114 |
| K2A-047 | Orchestration core | Per-scope model control | GET /models (catalogue + config), POST /models/set | api_v2.py:544, :550 | Model picker | C-015, A-012 |
| K2A-048 | Orchestration core | Scope chats CRUD | GET/POST /scope/chats, GET /scope/chat, POST /scope/chat/rename, DELETE /scope/chat | api_v2.py:556–585 | Chat sidebar | C-016 |
| K2A-049 | Orchestration core | Scope summary / child chats | GET /scope/summary, GET /scope/children (drill-down) | api_v2.py:587, :592 | Hierarchy views | C-016, B-024 |
| K2A-050 | Orchestration core | Scoped chat stream (SSE) | GET /scope/stream → `_scoped_gen` | api_v2.py:597 | Chat send | C-016, A-065 |
| K2A-051 | Synchronization & Anchor | Delta-sync message pool | GET /scope/messages?since=<seq> returns only newer messages plus `max_seq` (since=0 returns the full pool, for backward compatibility) | api_v2.py:605 `scope_all_messages` | Web/mobile/desktop pollers | no (near C-016/A-137) |
| K2A-052 | Per-project features & integrations | Generic project report export | GET /project/report?fmt=pdf/docx/md/pptx. Serves the newest pre-rendered report from localPath/soc/reports, localPath/reports or workspace/projects/<pid>/{data/soc/reports,data/reports,reports}; otherwise generates Overview / Team / last 400 pool messages via `report_engine.render` | api_v2.py:618 `_RPT_MIME`, :623 `project_report` | ▶ Export button | C-018, A-106 |
| K2A-053 | Build, packaging, run & clients | Standalone chats registry | GET/POST /chats, POST /chats/rename, DELETE /chats/{scope:path}; server-side `chat_registry.json`, each chat its own `chat:<id>` scope, shared by web/mobile/desktop | api_v2.py:691–732 | Chat list on all clients | C-017 |
| K2A-054 | Orchestration core | Delete scope message | DELETE /scope/message | api_v2.py:734 | Chat UI | C-016 |
| K2A-055 | Synchronization & Anchor | Group-chat post without AI turn (idempotent) | POST /scope/message posts text or media (role, sender, kind, attachment, reply_to) into the shared pool. `client_msg_id` makes retries not duplicate | api_v2.py:740 `scope_post_message` | Group chat / media / replies | C-016, A-135 (idempotency not described) |
| K2A-056 | Build, packaging, run & clients | Attachment upload / fetch | POST /scope/upload (multipart) → descriptor; GET /scope/file/{fid} | api_v2.py:759, :767 | Camera/mic/file/zip in chat | C-016 |
| K2A-057 | Orchestration core | Activity snapshot + SSE | GET /activity; GET /activity/stream pushes a snapshot every 2 s | api_v2.py:776, :781 | Heartbeat avatars | C-019 |
| K2A-058 | Scheduling & notifications | Schedules CRUD | GET/POST /schedules, POST /schedules/{tid}/update, DELETE | api_v2.py:793–814 | Scheduler panel | C-020 |
| K2A-059 | Scheduling & notifications | Periodic run gate | GET /schedules/pending, POST /schedules/{tid}/approve, /skip | api_v2.py:817–836 | Due periodic task alert | C-020, D-042 |
| K2A-060 | Orchestration core | Plain-language team controls in chat | "remove X / don't use / do not use / stop using / without X" removes and excludes the member (never auto-returns). "only use X / use only X" removes every other member | api_v2.py:842 `_apply_agent_controls` | Project chat message | no |
| K2A-061 | Safety & approvals | CTO is never removable | The CTO names ("project cto", "cto", "cto brain") are excluded from the remove / only-use controls | api_v2.py:850–852 | same | no |
| K2A-062 | Orchestration core | Fuzzy member resolution, no DevOps bias | Maps the router's lead agent to a project member by role/name/keyword. With no confident match it returns None (the CTO handles it itself) and never falls back to the first member | api_v2.py:882 `_resolve_member` | `_scoped_gen` | A-065 (no-fallback rule not described) |
| K2A-063 | Orchestration core | Engine selector stream | Uses the Claude CLI (`ClaudeCLIBrain.stream_session`, cwd = project folder, readonly flag, model) when the model is claude/haiku/sonnet/opus/claude-* and `ODIN_ENGINE` is "claude"; otherwise falls back to the Ollama `OllamaBrain` (single reply) | api_v2.py:902 `_engine_stream` | every agent/CTO call | A-001, A-002, B-104 |
| K2A-064 | Safety & approvals | PROPOSE_RULES prompt (propose-first) | Injected text: Odin runs you propose-first by design; never tell the owner to lift a mode, run /permissions or "approve in the harness"; never claim to be blocked; end with ONE fenced `proposal` JSON {summary, files[path,action,why], commands[cmd,where local/vm,why]}; no block if no change is needed | api_v2.py:930 `PROPOSE_RULES` | `_run_gated` read-only pass; `_scoped_gen` write requests | A-096 (named), A-020 |
| K2A-065 | Safety & approvals | Proposal parser | Pulls the proposal from a ```proposal/json fence or a bare balanced {…} containing "files"/"commands"; normalises files (preview capped at 800 chars) and commands (default where=local); summary capped at 600 chars | api_v2.py:949 `_parse_proposal` | `_run_gated`, `_scoped_gen` | no |
| K2A-066 | Safety & approvals | Gated agent run | Runs a member read-only; a proposal becomes an approval (kind vm if any VM command, else change), an `approval` SSE, a 🔔 status and a chat note; then STOPS. Execution happens on approve, independent of the run (fixes "approved 19 times and nothing ran") | api_v2.py:994 `_run_gated`, :1149–1177 | `_orchestrate_gen` member/fix steps | C-011, A-020 |
| K2A-067 | Middleware & DB registry | Agent-scope guard injection (delta credentials) | If the (project, member) pair has `agent_credential_ref`, appends `agent_scope_guard` to the prompt; otherwise nothing changes | api_v2.py:1002–1007 | `_run_gated` | A-085, A-086 |
| K2A-068 | Middleware & DB registry | VM-diagnosis guard injection | If the project has an `external_report_ref` (a diagnosis project), appends `vm_diagnosis_guard` so members may run read-only VM diagnostics themselves | api_v2.py:1008–1013 | `_run_gated` | no (only named in MFI §0.2) |
| K2A-069 | Middleware & DB registry | Tutorial guard injection | Appends `tutorial_guard(pid)` (provider tutorials) to member prompts | api_v2.py:1014–1019 | `_run_gated` | B-157 |
| K2A-070 | Orchestration core | Guaranteed liveness beater | A background thread calls `activity.beat` every 8 s during any engine call, so a long quiet build is not killed by the watchdog; a truly stuck call is still ended by the engine idle-timeout | api_v2.py:1023–1059 `_stream._beater` | every `_run_gated` call | no |
| K2A-071 | Safety & approvals | Authorized EXECUTE-NOW path | When auto_approve is on, runs write-enabled with the prompt "EXECUTE NOW — YOU ARE AUTHORIZED": run the owner's exact commands in order, report real output, no describing/proposing/confirming; VM via the Azure control plane; rsync with an SSH key file path; do not abort on the first transport hiccup | api_v2.py:1064–1147 | Pre-authorized projects/runs | no |
| K2A-072 | Build, packaging, run & clients | Build directive (in EXECUTE-NOW) | For non-DevOps, non-operator members: write real files to disk, prove with `ls -R`; slice under 15 min (project ~30); lightest stack; no production build; no foreground dev servers (background + one curl + kill); minimal installs; first actions must be Write/Bash; an empty folder is an automatic FAIL; never report results that were not run | api_v2.py:1092–1123 | `_run_gated` authorized | B-172 |
| K2A-073 | Safety & approvals | VM access refreshed once per run (TTL cache) | When a technical member's prompt mentions vm/rsync/ssh/reboot/deploy/sync/prisma/migrate, refreshes firewall access once per pid and reuses it for `ODIN_VM_ACCESS_TTL` (default 600 s); operators skip it; phase breadcrumbs go to main_task | api_v2.py:1068–1088, :1245 `_vm_access_cache` | Authorized member run | no (near A-033) |
| K2A-074 | Orchestration core | Phase breadcrumbs for monitors | Writes "⏳ phase: …" / "✓ phase: … in Ns" entries (VM access, engine call start/return, chars) to the main_task pool | api_v2.py:1078–1141, :2252–2273 | Member and QA engine calls | no |
| K2A-075 | Other | Unreachable inline-apply block | The "auto_approve → apply inline now" section (VM SSH apply, local apply via engine, `apply_id` always None) cannot run, because both auto_approve branches return earlier | api_v2.py:1179–1242 | — (dead code) | no |
| K2A-076 | Safety & approvals | VM commands run over SSH as mostafa | Approved VM commands run via `deploy_ssh.ssh_exec` as user mostafa (never root); the control plane is used only to open the firewall | api_v2.py:1199–1216, :1337–1349 | Apply paths | A-032, B-134 |
| K2A-077 | Safety & approvals | Firewall refresh with hard time budget | `_ensure_vm_access` runs `infra_rotate.rotate()` (single-IP firewall) and resolves the VM IP on a thread bounded by `ODIN_VM_ACCESS_TIMEOUT` (default 60 s). If it hangs, it proceeds without it rather than freezing the run | api_v2.py:1248 `_ensure_vm_access` | Apply / migrate / authorized runs | A-033 (timeout not described) |
| K2A-078 | Safety & approvals | VM host placeholder substitution | Rewrites `m[ou]stafa@<hostname>:` and `VM:` placeholders to `mostafa@<real ip>:` so rsync/ssh resolve | api_v2.py:1284 `_vm_subst` | Apply paths | no |
| K2A-079 | Auth & security | Rsync password auth rewrite | Prefixes rsync with `sshpass -p <VM password from deploy_ssh.vm_password()>` and forces password auth / no pubkey / no strict host-key checking, so it cannot fail with "too many authentication failures". Risk: the password is embedded in the command string | api_v2.py:1295 `_fix_rsync_auth` | Apply paths | B-134 |
| K2A-080 | Safety & approvals | Background approval applier | Executes an approved change outside any run: VM commands over SSH, local files/commands through a write-enabled engine with an "apply EXACTLY, nothing more" prompt; logs ▶/↳ lines into the member chat; `mark_applied` | api_v2.py:1310 `_apply_approval_bg` | Approve (generic kinds), chat "approve" | no (near C-011) |
| K2A-081 | Safety & approvals | Double-apply guard | The `_APPLYING` set plus `_APPLY_LOCK` stop a double-click, or chat + popup together, from applying twice | api_v2.py:1318–1322, :1427–1428, :1419 | `_apply_approval_bg` | no |
| K2A-082 | Orchestration core | Auto-continue after an applied gate | For operational/diagnosis/deploy/ops projects, re-invokes the CTO brain with "[system] gate APPROVED… do ONLY the next step": DB gate if schema/seed changed, else post-deploy TEST, then the full read-only diagnosis (Klaviyo, Veeqo, EasyPost, HubSpot/Analytics). An announce-only turn counts as a FAILURE; the run is marked RUNNING meanwhile | api_v2.py:1375–1418 | After `_apply_approval_bg` | no |
| K2A-083 | Orchestration core | Server-side run registry | `_RUNS[pid]` {running, cancel, goal, started} under `_RUNS_LOCK` | api_v2.py:1425–1426 | start/stop/status | C-013 |
| K2A-084 | Orchestration core | Brain-first run (static pipeline retired) | `_bg_orchestrate` forces `_operational = True`. Every ▶ run is either the deterministic deploy gate (deploy projects) or a CTO `_scoped_gen` turn. The static plan→members→QA pipeline below it is unreachable from start_run | api_v2.py:1431–1476 (`_operational = True` at :1444) | `start_run`, `orchestrate_blocking` | no |
| K2A-085 | Orchestration core | Run error surfaced + CTO idle on finish | A run exception is posted as "[Project CTO] Run hit an error"; the finally block marks the CTO idle and clears running | api_v2.py:1460–1475 | `_bg_orchestrate` | no |
| K2A-086 | Orchestration core | Stale ("ghost") run detection | A run flagged running for more than 90 s with no active agent counts as dead, so a new run can start | api_v2.py:1495 `_run_is_stale` | `start_run`, `orchestrate_blocking` | no |
| K2A-087 | Orchestration core | Start run with concurrency guard | Rejects a second run (`already: True`) unless the current one is stale; spawns `_bg_orchestrate` in a daemon thread | api_v2.py:1507 `start_run` | /orchestrate/start | C-013 |
| K2A-088 | Scheduling & notifications | Blocking orchestration for the scheduler | Runs the full orchestration in the calling thread (used by scheduler.py:309), with the same concurrency guard | api_v2.py:1517 `orchestrate_blocking` | scheduler / ▶ Run | no (near A-079) |
| K2A-089 | Orchestration core | Run status | Returns running / goal / started | api_v2.py:1531 `run_status` | UI poll | C-013 |
| K2A-090 | Orchestration core | One Stop = real stop | Sets cancel and also `request_stop` on every running operation for the pid (the watchdog kills the subprocess within ~1 s) | api_v2.py:1537 `stop_run` | Stop button | no (near C-014) |
| K2A-091 | Orchestration core | Shared group pool post | Posts into the project's single "▶ Team pool" chat with a `sender` label, and appends to `main_task` (durable shared context) | api_v2.py:1555 `_pool_post` | Deploy / QA / operator / blocked messages | no (near A-136/A-089) |
| K2A-092 | Build, packaging, run & clients | Smart resume of a blocked deploy | Applies the provided `local_*` folders to project sources, then re-runs `deploy_runner.run_decision` (when resuming a deploy decision) or the deterministic deploy; posts the verdict and outcome | api_v2.py:1576 `_resume_operation` | /operations/{oid}/provide | C-014 |
| K2A-093 | Build, packaging, run & clients | Self-healing deterministic deploy operation | Creates or uses an operation, posts "🚀 Deploy started — self-healing run", runs `deploy_agent.run`, and posts its log to the project chat | api_v2.py:1618 `_deploy_bg` | Deploy approve / deploy/operation / resume | C-012, A-036 |
| K2A-094 | Audit & consistency | Prompt-audit of the project brief | Before deploying, `audit.audit_prompt(description)` lists confirmed-broken methods the brief asks for; the pipeline overrides them (SSH-as-mostafa + `migrate deploy`). Informational only | api_v2.py:1629–1642 | `_deploy_bg` | no |
| K2A-095 | Audit & consistency | Deploy truth: success only on verified exit-0 | Success only when `res.ok`; stopped → "stopped"; needs_owner → "⛔ needs your decision" with a suggested fix that is NOT auto-run; otherwise "❌ failed after N attempts" | api_v2.py:1653–1681 | `_deploy_bg` | A-034, A-036 |
| K2A-096 | Audit & consistency | Snake hunt on green deploy | Even on exit-0, `audit.scan_hidden_faults(op log)`; any hit makes it NOT clean (state failed, red card) | api_v2.py:1657–1668 | `_deploy_bg` | A-035 |
| K2A-097 | Scheduling & notifications | Outcome breadcrumb | `activity.log_flow(pid, kind, "owner", ✅/⚠️ text)`, best-effort; the finish card is driven by operation state | api_v2.py:1684 `_emit_outcome` | Deploy/resume finish | no |
| K2A-098 | Safety & approvals | Deploy-project detection | A project counts as an operational deploy project if type/category/description contains "deploy" plus operational/diagnos/ops/deploy | api_v2.py:1707 `_op_is_deploy_project` | Approve/reject, `_bg_orchestrate` | no |
| K2A-099 | Structural | Project run chat resolver | Returns (project scope, first chat id), creating "Run" if none | api_v2.py:1717 `_op_cid` | `_op_*` gates | no |
| K2A-100 | Build, packaging, run & clients | Deterministic change scan | Runs `workspace/shared/infra/deploy_changes.py scan --project <pid>` (120 s timeout) and parses DEPLOY_REQUIRED, DB_SENSITIVE and the `~ ` changed-file lines | api_v2.py:1724 `_op_scan` | Deploy gate, after-deploy | B-127, D-029 |
| K2A-101 | Per-project features & integrations | Diagnosis prompt (hardcoded providers) | "[system] deploy phase resolved… ANNOUNCE then EXECUTE read-only reads": Klaviyo profile count; Veeqo order count + the known DELIVERED order → EasyPost status compared with the DB; HubSpot/Analytics; GREEN/exact reason; write AI_DIAGNOSIS_REPORT.md only on a real problem; announce-only = FAILURE | api_v2.py:1738 `_op_diag_prompt` | `_op_run_diagnosis` | no (near A-213) |
| K2A-102 | Orchestration core | Run diagnosis via CTO brain | Drains `_scoped_gen` with the diagnosis prompt either inline or in a thread that manages the RUNNING flag and CTO activity | api_v2.py:1750 `_op_run_diagnosis` | Gates / reject db-migrate / no-change | no |
| K2A-103 | Safety & approvals | Sequential deploy gate (play → "Deploy these N files?") | Supersedes stale pending deploy/synclist/db-migrate approvals ("a new run started"), scans, posts the changed list + DB sensitivity, creates ONE deploy approval with a `recommended` note, and STOPS. Nothing changed → runs the diagnosis inline | api_v2.py:1784 `_op_open_deploy_gate` | ▶ play on a deploy project | no (near B-126/B-127) |
| K2A-104 | Safety & approvals | Re-baseline (synclist) gate | After a declined deploy: a separate approval to run `deploy_changes.py update --project` (no VM change) | api_v2.py:1820 `_op_open_sync_gate` | Reject deploy | no (near B-131) |
| K2A-105 | Safety & approvals | DB migration gate | Schema/seed changed → separate "Migrate/rebase the database?" approval: additive only, never reset unless the owner says so; reject = skip to diagnosis | api_v2.py:1837 `_op_open_db_gate` | After deploy | B-132 |
| K2A-106 | Build, packaging, run & clients | Post-approval deploy chain | Captures DB sensitivity BEFORE the deploy, runs `_deploy_bg`, then the DB gate or the diagnosis | api_v2.py:1852 `_op_after_deploy` | Approve deploy | no |
| K2A-107 | Build, packaging, run & clients | Apply re-baseline | Runs `deploy_changes.py update`, marks applied, posts the result (no auto-diagnosis; "press play") | api_v2.py:1870 `_op_apply_synclist` | Approve synclist | no (near B-131) |
| K2A-108 | Build, packaging, run & clients | Apply additive DB migration | Refreshes VM access, runs `cd <target vm dir> && <migrate deploy cmd>` over SSH for every configured target; with no target it skips ("no guess on production"); then runs the diagnosis | api_v2.py:1887 `_op_apply_dbmigrate` | Approve db-migrate | A-039, B-139 |
| K2A-109 | Orchestration core | Static team pipeline generator | Chief → CTO plan → per-step member work → audit → CTO review → QA → completion report; every message saved to scope chats | api_v2.py:1918 `_orchestrate_gen` | GET /orchestrate SSE | A-066, A-067, B-191 |
| K2A-110 | Orchestration core | QA gate only if QA is on the team | `qa_enabled` = project folder exists AND "qa" is on the team; QA is never auto-hired otherwise | api_v2.py:1937–1944 | `_orchestrate_gen` | no |
| K2A-111 | Orchestration core | Goal-phrase restriction of QA | "no qa / without qa / remove qa / no quality / only devops / devops only / no other agent / do not involve / don't involve / not add or activate any agents other" switches QA off | api_v2.py:1946–1950 | `_orchestrate_gen` | no (§0.1 negation at intake only) |
| K2A-112 | Safety & approvals | Run authorization decision | auto_approve = project `auto_approve` OR (`_run_preauthorized(goal)` AND not VM work). A text-only "authorized" claim never auto-executes VM/Azure work; status "🔒 every change will wait" | api_v2.py:1960–1966 | `_orchestrate_gen` | no |
| K2A-113 | Safety & approvals | Deselected QA recorded as declined | If QA is not on the team, sets `qa_declined=True` so QA is never re-suggested or re-hired | api_v2.py:1971–1977 | `_orchestrate_gen` | no |
| K2A-114 | Safety & approvals | CTO recommends QA once (qa-recommendation gate) | Only for code work (not VM/deploy), when not already asked or declined: the engine judges whether QA is "genuinely IMPORTANT" (JSON); if so, creates a qa-recommendation approval; always sets qa_asked | api_v2.py:1979–1996 | `_orchestrate_gen` | no |
| K2A-115 | Orchestration core | One shared pool reused across runs | Reuses the project's first chat ("▶ Team pool") instead of a new chat per run | api_v2.py:1998–2001 | `_orchestrate_gen` | no (near A-136) |
| K2A-116 | Orchestration core | Chief Engineer → Project CTO brief | "[Chief Engineer → Project CTO] For '<name>': <goal>. Plan it, assign the team, and report back."; CTO animated as planning | api_v2.py:2003–2009 | `_orchestrate_gen` | A-067 |
| K2A-117 | Orchestration core | Intelligence-first intent gate (direct mode) | `intent.classify_request(goal)` → mode direct: ONE member (`_direct_member`), objective "Do EXACTLY what the owner asked — nothing else", no team, no brief expansion; `forbid` deploy adds "do NOT deploy/rsync/build on VM/migrate/reboot; local edits allowed" | api_v2.py:2012–2032 | `_orchestrate_gen` | C-013 (intent-first) |
| K2A-118 | Orchestration core | Brief as constraints, not tasks | Appends the project description as "PROJECT CONSTRAINTS (guardrails… NOT tasks to complete this turn)" to the planning request | api_v2.py:2034–2038 | `_orchestrate_gen` | no |
| K2A-119 | Orchestration core | Plan + coverage gate + re-plan | `plan_pipeline(pid, full_req)` then `check_plan_coverage(goal, steps)`; any uncovered part → "CTO caught N uncovered part(s)… re-planning" with "Also cover (from YOUR request, not the brief)" | api_v2.py:2039–2049 | `_orchestrate_gen` | A-090 |
| K2A-120 | Build, packaging, run & clients | Pure-deploy collapse to one DevOps step | Only when DevOps is on the team and no build roles are (the fullstack…analytics list): a single "rsync → build → migrate → reboot → verify" DevOps step. A multi-agent build is never collapsed | api_v2.py:2050–2066 | `_orchestrate_gen` | A-093 |
| K2A-121 | Orchestration core | CTO is never a worker step | Drops plan steps assigned to cto / chief / orchestrator / coordinator / owner / user / you (unless that would empty the plan) | api_v2.py:2067–2074 | `_orchestrate_gen` | no |
| K2A-122 | Orchestration core | Plan announcement + plan SSE | "[Project CTO → Chief] Plan: 1) member → task (after deps)…" plus a QA note; `plan` event | api_v2.py:2075–2084 | `_orchestrate_gen` | A-067 |
| K2A-123 | Orchestration core | `_ensure_member` safe hire | Hires a missing member only if it is a known catalogue role and not owner-excluded; never invents a role, never resurrects a removed one; always `record_usage` | api_v2.py:2088 `_ensure_member` | Each step, QA gate, fixer | A-069 (§0.2) |
| K2A-124 | Safety & approvals | Source/folder location rules (prompt) | Existing sources READ-ONLY unless explicitly asked; all file work INSIDE the project folder; never at the Odin repo root; with no folder → ASK first | api_v2.py:2110–2116 | Member prompts | A-027, A-028 |
| K2A-125 | Safety & approvals | Owner brief verbatim (prompt) | "OWNER'S FULL INSTRUCTIONS — AUTHORITATIVE… do NOT summarize, drop, reorder, or invent any rule, path, command, excluded file; honour 'this time only' vs 'ask me next time'; production changes follow the owner's approval rules" + the full request | api_v2.py:2122–2131 | Member and fixer prompts | no (near B-142) |
| K2A-126 | Per-project features & integrations | Live connector facts grounding | `anchor._connector_facts(proj, goal)` (GET-only Klaviyo/Veeqo); facts injected into owner_brief ("GROUND your answer in THESE exact numbers") and the shared pool | api_v2.py:2133–2147, :2162–2163 | `_orchestrate_gen` | no (near A-180) |
| K2A-127 | Testing | E2E run timer | `run_timer.Timer(pid, goal)` at start (cached vs no-cache baseline); stopped at the end with `compare` | api_v2.py:2152–2157, :2967–2975 | `_orchestrate_gen` | no (near C-045) |
| K2A-128 | Orchestration core | Main-task requirements checklist (omission guard) | `main_task.create(pid, goal)` seeds the plan and live data into the pool; announces "N item(s) tracked — nothing is 'done' until all are addressed" | api_v2.py:2158–2169 | `_orchestrate_gen` | A-089, A-090 |
| K2A-129 | Other | Unused `_run_engine` helper | Engine streaming helper defined inside `_orchestrate_gen` but never called | api_v2.py:2174 | — (dead code) | no |
| K2A-130 | Testing | QA gate | QA runs READ-ONLY (enforced), in its own `member:<pid>:QA` chat "▶ Test: …"; flow logged | api_v2.py:2188 `qa_gate` | After each non-operator step | B-177 |
| K2A-131 | Testing | QA prompt rules | Run `ls -R` first; empty → FAIL "only DESCRIBED"; don't trust the developer's report or acceptance table; lint/type-check/tests; deploy matches the exact owner instructions; under ~5 min; no prod build/dev servers; verify CODE not live Veeqo/Klaviyo data; reply exactly PASS:/FAIL: | api_v2.py:2218–2243 | `qa_gate` | B-177 |
| K2A-132 | Testing | Fast gate model (testing only) | `ODIN_GATE_MODEL` sets the model for the QA gate and the CTO review; production leaves it unset (full model) | api_v2.py:2198, :2870 | env | D-043, D-032 |
| K2A-133 | Testing | Bounded QA cycle | MAX_ATTEMPTS=2 (one fix cycle); wall-clock `ODIN_QA_BUDGET` (default 720 s): no new fix cycle once exceeded | api_v2.py:2206–2213 | `qa_gate` | no |
| K2A-134 | Orchestration core | QA verdict mirrored into the shared pool | "🧪 QA review of X (attempt n)" posted with sender QA, plus a main_task entry | api_v2.py:2278–2287 | `qa_gate` | no |
| K2A-135 | Audit & consistency | Robust QA verdict parsing (wrong-format handling) | Looks for PASS:/FAIL: anywhere (despite a preamble); FAIL wins; if both, the first token wins; with no token, fails only on explicit "not built / folder is empty / no source files…"; the word "error" alone does not fail | api_v2.py:2289–2307 | `qa_gate` | no (A-107 says not described) |
| K2A-136 | Audit & consistency | Audit override of a fake PASS | `scan_hidden_faults(QA tool evidence, build=True)` turns a PASS into "FAIL (audit override)"; non-zero exploratory commands do not flip it | api_v2.py:2308–2324 | `qa_gate` | A-034, A-035 |
| K2A-137 | Orchestration core | CTO routes the QA fix to an existing member | Engine JSON {member, fix}: owner of the area (whole web app → Fullstack; mobile → Mobile; deploy → DevOps); no invented or obsolete Frontend/Backend/Database roles; fuzzy match, falling back to the area member | api_v2.py:2331–2345 | QA FAIL | no (near §0.1 "Fullstack owns web app") |
| K2A-138 | Orchestration core | Fixer run (reassign) | Fixer briefed with owner_brief + QA errors + CTO instruction, run through `_run_gated` (proposal/approval unless authorized); then QA re-tests | api_v2.py:2351–2374 | QA FAIL (attempt < max) | no |
| K2A-139 | Orchestration core | Dependency wait (soft) | A step whose dependency has not passed QA proceeds "with caution" (it does not block); a passed dependency is announced | api_v2.py:2400–2410 | Each step | A-091 (non-blocking behaviour not described) |
| K2A-140 | Testing | Owner-requirements step auto-resolved | A step for owner/user/you is answered deterministically ("requirements confirmed — env/keys/target provided in the brief"), with no engine call and no QA. Bug: `owner_answer` is never defined (`'owner_answer' in dir()` is always False) | api_v2.py:2415–2437 | Planner emits an owner step | B-181 |
| K2A-141 | Orchestration core | Structured mandate + hand-off | OBJECTIVE / DELIVERABLE / ACCEPTANCE CRITERIA + only the upstream deliverables the step depends on (600 chars each); "own EXACTLY this mandate" | api_v2.py:2443–2469 | Each step | A-091 |
| K2A-142 | Orchestration core | Member prompt context assembly | Pool text + checklist + cached-modules index for the role + resources + orientation + mandate + deps + owner rules | api_v2.py:2449–2507 | Each step | A-089, B-204 |
| K2A-143 | Per-project features & integrations | Per-agent resources + env vars | Owner-editable stored `resources`, else `projects.resources_block(role)`; per-agent env rows injected as "PROJECT ENV VARS… use directly — do NOT ask" | api_v2.py:2474–2493 | Each step | B-173, B-174 |
| K2A-144 | Orchestration core | Readiness check prompt (STEP 1) | REQUIRES / HAVE (allowed resources, brief, pool, project .env, the shared `.cred` file; a key may be a path) / MISSING; empty → "Ready" and proceed, never ask twice; else ask the CTO ONCE | api_v2.py:2508–2522 | Each step | B-171 |
| K2A-145 | Testing | Step-start diagnostic breadcrumb | Logs is_devops / deploy_ctx / auto_approve / deployed_once at each step start, plus "▶ starting step i/N" | api_v2.py:2395–2399, :2525–2533 | Each step | no |
| K2A-146 | Per-project features & integrations | Instant operator key hand-off | An operational member whose task matches `_HANDOFF_RE` (provide/share/… api key/credential/token…) gets a deterministic "key SAVED and available for Fullstack" reply: no engine call, no audit, no QA | api_v2.py:2535–2553 | Operator step | no (near B-175) |
| K2A-147 | Build, packaging, run & clients | Deploy runs once per run | After the first DevOps deploy, later DevOps deploy steps are marked covered (stops repeated reboots) | api_v2.py:2557–2570, :2392 `_deployed_once` | DevOps step | A-055 |
| K2A-148 | Build, packaging, run & clients | Deploy context only from the owner's ask | deploy_ctx = (mode deploy or `_touches_vm(goal)`), not direct mode, not forbidden, and not "no deploy / don't deploy / read-only…" phrases | api_v2.py:2385–2390 | `_orchestrate_gen` | no |
| K2A-149 | Build, packaging, run & clients | Hybrid DevOps deploy: restate brief specifics | Regex-extracts /home paths, excludes, prisma/build/rm/reboot commands from the brief and posts them; runs the change scan; posts "Deploy check — changed: …" and the DB note | api_v2.py:2571–2604 | DevOps step with deploy_ctx | A-093 |
| K2A-150 | Safety & approvals | No-change → re-sync baseline approval | If DEPLOY_REQUIRED is NO: no deploy; opens "Re-sync deploy baseline (no deploy)" with the local `deploy_changes.py update` command | api_v2.py:2606–2623 | DevOps step | no (near B-131) |
| K2A-151 | Build, packaging, run & clients | AI deploy decision, code-only | `deploy_runner.ai_decide_deploy(owner_brief + step)`; forces migration_intent / target migration to "none"; a deploy never migrates the DB on its own | api_v2.py:2624–2632 | DevOps step | A-093, B-133 |
| K2A-152 | Safety & approvals | Separate DB-migration approval (hardcoded path) | On a DB-sensitive change, creates a kind=vm approval running `npx prisma migrate deploy` in a hardcoded RBO-Staging backend path on the VM | api_v2.py:2633–2643 | DevOps step | B-132 (hardcoded path not noted) |
| K2A-153 | Safety & approvals | Missing target → ask owner | No usable decision → "need the target app named (backend/frontend)"; step not clean; posted to the pool | api_v2.py:2644–2649 | DevOps step | no |
| K2A-154 | Safety & approvals | Propose-only deploy plan when not authorized | Without auto_approve: "📋 PROPOSED deploy plan (awaiting approval — nothing executed)"; decision cleared so nothing runs | api_v2.py:2650–2675 | DevOps step | no (near A-062) |
| K2A-155 | Build, packaging, run & clients | Deterministic execution of the decision + audit | `run_decision` as operation "<member> hybrid deploy"; `ok` and no snakes → "✅ Deploy VERIFIED"; needs_owner → "⛔ blocked" in the pool; else "❌ not clean" + hidden faults; op state set | api_v2.py:2676–2701 | DevOps step (authorized) | A-093, A-035 |
| K2A-156 | Audit & consistency | Audit-eye retry loop | Up to 3 tries for build members, 1 for operators, 0 for the DevOps deploy; each retry gets "AUDIT FEEDBACK — previous attempt REJECTED… fix EXACTLY this" | api_v2.py:2703–2743 | Each step | no (near A-038) |
| K2A-157 | Audit & consistency | Widen-the-scope escalation | Try ≥3 adds "WIDEN THE SCOPE — failed twice the same way… search wider codebase/system/configs/logs for ROOT cause" | api_v2.py:2719–2724 | Audit retry | A-038 |
| K2A-158 | Audit & consistency | Per-try scan (this try's tool output only) | Scans only the new assistant messages of this try; separates tool output (🔧/↳) from prose so explained past errors don't count | api_v2.py:2731–2765 | Audit eye | no |
| K2A-159 | Audit & consistency | Forbidden-method checks | Rejects `az vm run-command` in tool output ("az is on the Mac, use SSH as mostafa") and `prisma migrate dev` ("use migrate deploy") | api_v2.py:2767–2770 | Audit eye | no (rules A-032/A-039 exist, this check does not) |
| K2A-160 | Audit & consistency | Hidden faults + fake success claim | `scan_hidden_faults(tool, build=True)`; `claims_success(prose)` together with snakes → "you CLAIMED success while errors are present" | api_v2.py:2776–2781 | Audit eye | A-034, A-035 |
| K2A-161 | Audit & consistency | Artifact gate (files on disk) | A build/implement/create/develop/scaffold/write task with fewer than 2 files in the folder (excluding node_modules/.git/.next/dist) is rejected with the "ZERO real files… use the WRITE tool… `ls -R`" correction | api_v2.py:2782–2805 | Audit eye | no (near B-172) |
| K2A-162 | Audit & consistency | Hard build gate stops the run | After all retries, still fewer than 2 non-hidden files → "⛔ BUILD FAILED… narrated a build"; the whole run stops | api_v2.py:2818–2846 | After the audit loop | no |
| K2A-163 | Orchestration core | Quota / rate-limit pause | A reply containing session/usage/rate limit, quota, insufficient_quota or overloaded → "⛔ RESOURCE/QUOTA limit hit… not retried"; the run stops | api_v2.py:2848–2861 | After each step | no |
| K2A-164 | Orchestration core | CTO review of each member | Engine "Confirmed:" / "Needs fix:" in 1–3 sentences; stored in the member chat and in results | api_v2.py:2863–2872 | After each step | B-178 |
| K2A-165 | Orchestration core | Deliverable write-back to the shared pool | Member reply + CTO review appended to main_task; `write_deliverable(done=step_clean)`; deliverables map for downstream hand-off | api_v2.py:2873–2882 | After each step | A-092 |
| K2A-166 | Testing | QA skipped for operators and the DevOps deploy | No per-step QA for operational members or a DevOps deploy (self-verifying; the final QA does curl) | api_v2.py:2884–2900 | After each step | no |
| K2A-167 | Audit & consistency | Step acceptance = QA ok AND audit clean | Only then is the member added to passed_members; "[member → Project CTO] ✅ passed / ⚠️ flagged" | api_v2.py:2901–2915 | After each step | A-092 (CTO "Needs fix" not part of it; G1) |
| K2A-168 | Synchronization & Anchor | Upward scope sync | `scopes.sync_up(member scope, "delivered; QA…; audit…")` and (project scope, "team completed…") roll results up to ancestors | api_v2.py:2904, :2966, :3548 | Steps / chat end | A-064, B-024 |
| K2A-169 | Audit & consistency | Completion omission guard | `main_task.reconcile(pid, deliverables)` → "⚠️ Incomplete — N requirement(s) NOT addressed"; ignored when every step's member passed (keyword false negative) | api_v2.py:2920–2928, :2955–2960 | Run end | A-092 |
| K2A-170 | Audit & consistency | Engine auth-failure guard | Deliverables/reviews containing "oauth access token has expired / re-authenticate / hit your weekly limit" → run NOT done; advises re-login | api_v2.py:2932–2954 | Run end | no |
| K2A-171 | Audit & consistency | Deploy truth overrides the verdict | For a deploy run, the latest operation (kind deploy, state done) → all_ok and "✅ Deploy verified successful" | api_v2.py:2941–2951 | Run end | no (near A-034) |
| K2A-172 | Orchestration core | Completion report + RUN FINISHED + done SSE | "[Project CTO → Chief] verdict + summary"; "✅ RUN FINISHED" or "⏹️ (open items remain)"; `done` with ok and timing | api_v2.py:2961–2982 | Run end | A-067 |
| K2A-173 | Safety & approvals | Root-only command classifier (unused) | Lists commands that genuinely need root (reboot, shutdown, ufw, systemctl, apt, chown, chmod, usermod, service); defined but never called | api_v2.py:2987 `_vm_needs_root` | — (dead code) | B-136 |
| K2A-174 | Safety & approvals | DevOps deployment knowledge block (unused) | Senior-DevOps rails: SSH as mostafa with the `.cred` password, control plane only for the firewall; `migrate deploy` only; never-sync excludes; optional deploy.sh; ignore stale scripts; exact target paths; single-IP 22, 80/443 untouched; per-command verification; rsync --checksum overwrite + dry-run zero check; TRUTH. Defined but referenced nowhere | api_v2.py:2995 `_DEVOPS_KNOWLEDGE` | — (dead constant) | B-179, B-176, B-180 |
| K2A-175 | Orchestration core | Direct-mode single member picker | For ops keywords (vm, ssh, deploy, rsync, server, log, journalctl, firewall, nsg, ufw, trigger, script, psql, db, az) prefers devops/cloud/sre/backend/fullstack; else fullstack/backend/frontend/analytics/reporter; else the first non-QA member; else "DevOps" | api_v2.py:3035 `_direct_member` | Direct-mode intent | no |
| K2A-176 | Orchestration core | Operational member detection | Agent `nature=operational`, or catalogue (ALL_MEMBERS + OPERATIONAL_MEMBERS) nature operational: one attempt, no QA, no VM refresh | api_v2.py:3064 `_is_operational` | Many branches | no |
| K2A-177 | Orchestration core | DevOps detection | avatar devops, role contains devops, or the name contains devops; routes deploys to the proven pipeline | api_v2.py:3080 `_is_devops` | Many branches | no |
| K2A-178 | Orchestration core | Agent orientation block | Live map: the agent's `workspace/agents/<slug>/capability.md` (fuzzy slug match), the shared tools (deploy_changes scan/dbscan/update, deploy.sh only after approval, SSH/IP mechanics internal and never surfaced), provider tutorials INDEX, scoped credentials via delta (getVeeqoConfig/getKlaviyoConfig/getHubspotConfig from odin_core) else the default `.cred`, report credential_source, never print a key, governance (core-rules.md, ORCHESTRATOR.md, odin_core as source of truth) | api_v2.py:3093 `_orientation_block` | Member prompts, CTO brain | no |
| K2A-179 | Safety & approvals | VM-touch classifier | Keywords azure, " vm", "vm ", django-vm, rsync, /home/, deploy, sync, reboot, prisma migrate, ssh, run-command, /bendcore, /organics, control plane. Known issue: "do not deploy" also matches (G2) | api_v2.py:3145 `_touches_vm` | Authorization, deploy_ctx | no (§0.1 G2 only) |
| K2A-180 | Safety & approvals | Run pre-authorization phrases | About 30 phrases ("approval already granted", "do not ask for approval", "pre-approved", "this time only", "execute exactly", "run these commands", "allow the data reset"…) | api_v2.py:3155 `_run_preauthorized` | Authorization | no (near B-142) |
| K2A-181 | Orchestration core | Work-request heuristic | Strong verbs (add/create/build/fix/deploy…) → work; soft verbs (test/update/change/migrate/verify) → work unless the message opens as a question | api_v2.py:3178 `_is_work_request` | `_scoped_gen` | A-096 (named) |
| K2A-182 | Orchestration core | CTO brain orientation | Team roster ("don't invent work for idle roles"), CONNECTED services to read live, orientation block, tutorial guard, agent-scope guard, audit-broken methods to avoid, and "BE SMART & AVOID DUPLICATION: read what exists, reuse/extend, stay in THIS project's scope, never import another project's requirements, don't invent missing requirements" | api_v2.py:3200 `_brain_orientation` | `_scoped_gen` | no (near B-064/B-077) |
| K2A-183 | Safety & approvals | "approve" in chat = approve all | In a project scope, a message matching approve/approved/accept/approve all/run it/go ahead and run approves ALL pending approvals and fires every approved-but-unapplied one. Risk: matches inside "don't approve" too | api_v2.py:3269–3289 | Project chat | no (near A-021) |
| K2A-184 | Audit & consistency | Deterministic status answer (anti-loop) | A short project message (<90 chars) asking status/result/"is it done"/"?" is answered from _RUNS + approvals records (pending, approved-executing, last executed + output, "nothing executed yet"), never by the LLM | api_v2.py:3291–3322 | Project chat | no |
| K2A-185 | Orchestration core | Chat never fans out to the static pipeline | `_use_pipeline = False`: work requests in the CTO chat fall through to the brain; the background-run message is dead code | api_v2.py:3324–3351 | Project chat | no **[corrected: see §0.8 C-7]** |
| K2A-186 | Orchestration core | Dispatcher routing in chat | `dispatcher.default_dispatcher.route(text, lang)` → leadAgent and approval.required/categories; falls back to "CTO Brain"; "⛔ Change (cats) — will propose & wait" status | api_v2.py:3356–3363, :3409–3411 | `_scoped_gen` | A-014, B-004, A-021 |
| K2A-187 | Orchestration core | CTO delegation in chat | Project scope: CTO animated; team controls applied; `_resolve_member` → "Project CTO → delegating to X", delegate SSE, flow log, usage | api_v2.py:3367–3396 | Project chat | A-065 |
| K2A-188 | Orchestration core | Capability-dialog resolve marker | The `⟦resolve⟧` marker in text means the owner resolved the capability dialog, so it is not reopened (marker stripped) | api_v2.py:3369–3372 | Capability dialog | no |
| K2A-189 | Orchestration core | Member-scope and company-scope chat | member:<pid>:<name> → that member works directly; other scopes → "Company CTO (coarse overview)" | api_v2.py:3397–3407 | Member / company chat | A-064 |
| K2A-190 | Orchestration core | Per-scope model + session resume | Model from `models_config.get_model(scope or member scope)`; stored `session_id` reused and new sid persisted via `scopes.set_session` | api_v2.py:3413–3416, :3530–3531 | `_scoped_gen` | A-012, A-013 |
| K2A-191 | Orchestration core | Project brief as standing context | "[PROJECT BRIEF & CAPABILITIES — standing context… NOT a checklist]" + the first 1500 chars of the description | api_v2.py:3425–3429 | `_scoped_gen` | no |
| K2A-192 | Orchestration core | OWNER_RUN_FLOW.md injection | If `workspace/projects/<pid>/OWNER_RUN_FLOW.md` exists: "AUTHORITATIVE step-by-step… one approval at a time… never bundle; report only on a real problem" (up to 4000 chars) | api_v2.py:3434–3446 | `_scoped_gen` | no |
| K2A-193 | Safety & approvals | Chat sources/folder notes + cwd | Sources READ-ONLY note; project folder note; engine cwd = localPath | api_v2.py:3447–3455 | `_scoped_gen` | A-027, A-028, B-104 |
| K2A-194 | Safety & approvals | Read-only chat by default | Project chat engine runs readonly unless the project has `auto_approve` | api_v2.py:3458–3467 | `_scoped_gen` | A-020 |
| K2A-195 | Middleware & DB registry | Scope answer guard (owner path) | Prepends `scope_answer_guard(project name, external=False)` | api_v2.py:3477–3486 | `_scoped_gen` | A-095 |
| K2A-196 | Middleware & DB registry | Read-execute vs propose | Reads (non-work) get `read_execute_guard(connected connector names)` so they EXECUTE; work requests in read-only projects get PROPOSE_RULES | api_v2.py:3488–3511 | `_scoped_gen` | A-096 |
| K2A-197 | Orchestration core | Conversation memory injection | Last 8 prior user/assistant messages injected as "Conversation so far (for your memory)" | api_v2.py:3496–3501 | `_scoped_gen` | A-013 |
| K2A-198 | Safety & approvals | Chat proposal → real approval | In a read-only project chat, a parsed proposal becomes an approval (kind vm/change) plus an `approval` SSE, so Approve really executes | api_v2.py:3534–3546 | `_scoped_gen` | no (near A-021/C-011) |
| K2A-199 | Orchestration core | Intervention feedback to the CTO | An owner instruction to a member is relayed into the project's "↳ team updates" chat ("[member → CTO] Owner instruction…" / "[CTO] Noted…") | api_v2.py:3549–3560 | Member chat | B-118 |
| K2A-200 | Orchestration core | Chat stream finish events | Member set idle, "✅ Done" status, `done` SSE with approval info, `error` SSE on exception | api_v2.py:3561–3568 | `_scoped_gen` | C-016 |
| K2A-201 | Safety & approvals | Approvals are per run | A new play supersedes old pending deploy/synclist/db-migrate approvals ("superseded — a new run started") | api_v2.py:1789–1794 | `_op_open_deploy_gate` | no |
| K2A-202 | Auth & security | VM password and SSH key references | Names `deploy_ssh.vm_password()` (the `.cred` key azvmcred) and an SSH key file path in the EXECUTE-NOW prompt (no value). This conflicts with the CLAUDE.md password-auth rule and with the audit-eye ban on `az vm run-command` (K2A-159) | api_v2.py:1124–1131, :1299 | Authorized runs | no |
| K2A-203 | Other | Prompt/code channel contradiction | PROPOSE_RULES (:939) and the apply prompts say VM commands run "via the Azure control plane", but the code runs them over SSH as mostafa (:1199); the EXECUTE-NOW prompt tells agents to use `az vm run-command`, which the audit eye then rejects (:2767) | api_v2.py:939, :1124, :1199, :2767 | — | no |
| K2A-204 | Per-project features & integrations | Hardcoded provider names in generic code | The diagnosis/continue prompts name Klaviyo/Veeqo/EasyPost/HubSpot in shared code for any "operational" project | api_v2.py:1387–1399, :1738–1747 | Ops projects | no |

## 2. Not in MFI

| ID | Capability | Evidence |
|---|---|---|
| K2A-003 | SSE formatter | :90 `sse` |
| K2A-004 | Unused ROOT constant | :22 |
| K2A-022 | Deploy-approval execution branch (deploy project → `_op_after_deploy`) | :248–256 |
| K2A-023 | Synclist-approval execution | :257 |
| K2A-024 | DB-migrate-approval execution | :260 |
| K2A-025 | QA-recommendation approve → register QA | :263 |
| K2A-026 | Reject dispatched by kind (QA never ask again, deploy→re-baseline gate, synclist stop, db-migrate skip→diagnosis) | :276 |
| K2A-045 | Explicit add re-allows a removed agent (`force=True`) | :505 |
| K2A-051 | Delta-sync `/scope/messages?since=` + `max_seq` | :605 |
| K2A-060 | Chat team controls "remove X" / "only use X" (persisted exclusion) | :842 |
| K2A-061 | CTO never removable | :850 |
| K2A-065 | Proposal parser | :949 |
| K2A-068 | VM-diagnosis guard injection (named only in §0.2) | :1008 |
| K2A-070 | Liveness beater (8 s heartbeat during engine calls) | :1023 |
| K2A-071 | EXECUTE-NOW authorized prompt | :1093 |
| K2A-073 | VM access cached once per run (`ODIN_VM_ACCESS_TTL`) | :1068, :1245 |
| K2A-074 | Phase breadcrumbs for monitors | :1078, :2252 |
| K2A-075 | Unreachable inline-apply block (dead code) | :1179–1242 |
| K2A-078 | VM host placeholder substitution | :1284 |
| K2A-080 | Background approval applier | :1310 |
| K2A-081 | Double-apply guard | :1318, :1427 |
| K2A-082 | Auto-continue after an applied gate (diagnosis chain) | :1375 |
| K2A-084 | Brain-first run: static pipeline retired from start_run | :1444 |
| K2A-085 | Run error surfaced + CTO idle | :1460 |
| K2A-086 | Stale ghost-run detection (90 s) | :1495 |
| K2A-088 | `orchestrate_blocking` for the scheduler | :1517 |
| K2A-090 | One Stop also stops running operations | :1537 |
| K2A-091 | Shared group pool post with sender label | :1555 |
| K2A-094 | Prompt-audit of the brief before deploy | :1629 |
| K2A-097 | Outcome breadcrumb | :1684 |
| K2A-098 | Deploy-project detection heuristic | :1707 |
| K2A-099 | Run chat resolver | :1717 |
| K2A-101 | Diagnosis prompt (Klaviyo/Veeqo/EasyPost/HubSpot) | :1738 |
| K2A-102 | Run diagnosis via CTO brain | :1750 |
| K2A-103 | Sequential "Deploy these N files?" gate | :1784 |
| K2A-104 | Re-baseline (synclist) gate | :1820 |
| K2A-106 | Post-approval deploy chain | :1852 |
| K2A-107 | Apply re-baseline | :1870 |
| K2A-110 | QA gate only if QA is on the team | :1944 |
| K2A-111 | Goal-phrase QA off ("no qa", "only devops"…) | :1946 |
| K2A-112 | Run authorization decision (text claim never authorizes VM work) | :1960 |
| K2A-113 | Deselected QA recorded as declined | :1971 |
| K2A-114 | CTO recommends QA once (qa-recommendation) | :1979 |
| K2A-115 | One shared pool reused across runs | :1998 |
| K2A-118 | Brief as constraints, not tasks | :2034 |
| K2A-121 | CTO never a worker step | :2067 |
| K2A-125 | Owner brief verbatim prompt | :2122 |
| K2A-126 | Live connector facts grounding in the team run | :2133 |
| K2A-127 | E2E run timer | :2152 |
| K2A-129 | Unused `_run_engine` (dead) | :2174 |
| K2A-133 | Bounded QA cycle (`ODIN_QA_BUDGET`, 2 attempts) | :2206 |
| K2A-134 | QA verdict mirrored into the pool | :2278 |
| K2A-135 | Robust PASS/FAIL verdict parsing | :2289 |
| K2A-137 | CTO routes the QA fix to an existing member (JSON) | :2331 |
| K2A-138 | Fixer run (reassign) through the gate | :2351 |
| K2A-145 | Step-start diagnostic breadcrumbs | :2395, :2525 |
| K2A-146 | Instant operator key hand-off | :2535 |
| K2A-148 | Deploy context only from the owner's ask | :2385 |
| K2A-150 | No change → re-sync baseline approval | :2606 |
| K2A-153 | Missing target → ask owner | :2644 |
| K2A-154 | Propose-only deploy plan | :2669 |
| K2A-156 | Audit-eye retry loop (3 / 1 / 0 tries) | :2709 |
| K2A-158 | Per-try tool-vs-prose scan | :2731 |
| K2A-159 | Forbidden-method checks (az run-command, migrate dev) | :2767 |
| K2A-161 | Artifact gate (<2 files) | :2782 |
| K2A-162 | Hard build gate stops the run | :2818 |
| K2A-163 | Quota/rate-limit pause | :2848 |
| K2A-166 | QA skipped for operators / DevOps deploy | :2893 |
| K2A-170 | Engine auth-failure guard | :2935 |
| K2A-171 | Deploy op truth overrides the verdict | :2941 |
| K2A-175 | Direct-mode member picker | :3035 |
| K2A-176 | Operational member detection | :3064 |
| K2A-177 | DevOps detection | :3080 |
| K2A-178 | Agent orientation block | :3093 |
| K2A-179 | `_touches_vm` classifier (G2 only, no row) | :3145 |
| K2A-180 | Run pre-authorization phrase list | :3155 |
| K2A-182 | CTO brain orientation (anti-duplication / scope) | :3200 |
| K2A-183 | "approve" in chat approves ALL pending (regex risk) | :3274 |
| K2A-184 | Deterministic status answer | :3293 |
| K2A-185 | Chat pipeline disabled (`_use_pipeline=False`) | :3339 **[corrected: see §0.8 C-7]** |
| K2A-188 | `⟦resolve⟧` capability-dialog marker | :3370 |
| K2A-191 | Project brief as standing context | :3425 |
| K2A-192 | OWNER_RUN_FLOW.md injection | :3436 |
| K2A-198 | Chat proposal → real approval | :3537 |
| K2A-201 | Approvals are per run (supersede stale) | :1789 |
| K2A-202 | VM password / SSH key references in prompt/code | :1124, :1299 |
| K2A-203 | Prompt vs code channel contradiction | :939, :1124, :1199, :2767 |
| K2A-204 | Hardcoded provider names in generic code | :1387, :1738 |

Partial matches (an MFI row exists but this detail is missing): K2A-011a (reuse ranking), K2A-055 (idempotent client_msg_id), K2A-062 (no first-member fallback), K2A-077 (timeout budget), K2A-139 (non-blocking dependency wait), K2A-140 (`owner_answer` bug), K2A-152 (hardcoded migration path), K2A-167 (CTO "Needs fix" ignored = G1), K2A-173/K2A-174 (the MFI rules exist, but these code objects are dead).

## 3. Requested-category confirmations

**(a) Full project lifecycle**
- **Intake:** FOUND. :156 `/projects/intake`, :162 readiness.
- **Create:** FOUND. :118.
- **Run / orchestrate:** FOUND.
  - Routes: :382 SSE, :423 start, :1507 `start_run`.
  - `_bg_orchestrate` (:1431) forces the brain-first path (:1444).
  - `_orchestrate_gen` (:1918) is reachable only through the GET SSE route.
- **CTO planning:** FOUND. :2003–2084: intent gate, `plan_pipeline`, coverage re-plan, pure-deploy collapse, CTO-step drop.
- **Delegation:** FOUND. :2411 `delegate` SSE; chat delegation at :3383–3396.
- **Member hire / `_ensure_member`:** FOUND. :2088.
- **QA gate:** FOUND. :2188 `qa_gate`.
- **CTO review:** FOUND. :2866.
- **Audit / truth gate:** FOUND.
  - Audit eye: :2744–2812.
  - Fake-PASS override: :2308.
  - Hard build gate: :2818.
  - Deploy snake hunt: :1657 and :2682.
- **Retries / reassign:** FOUND.
  - Up to 3 audit tries with widen-scope: :2709.
  - QA fix routed to an existing member: :2331–2374 (2 attempts, budget).
- **Done:** FOUND. :2917–2982: reconcile, engine-fail guard, deploy truth, "RUN FINISHED", `done` SSE.

**(b) Create / route / reuse / strengthen / delta / shared logic**
- FOUND:
  - Agent create/reuse: `_ensure_member` known-role only and no resurrection (:2088); `/agents/validate` (:137); capability-gap ranking of existing agents vs a new agent (:144); `force=True` re-add (:505); exclusion via chat controls (:842).
  - Routing: dispatcher (:3359), `_resolve_member` (:882), `_direct_member` (:3035), QA-fix routing (:2331).
  - Reuse / anti-duplication prompt: :3253.
  - Cached-modules reuse: :2456.
  - Delta credentials: `agent_scope_guard` (:1005, :3239); orientation block (:3135, delta then default `.cred`).
  - Shared pool: :1555, :2161.
- **"Strengthen" (add a skill without deleting):** NOT FOUND in this file. It is only reachable through the generic `agents_update` (:522).
- **Delta file creation / registration:** NOT FOUND here (it lives in workspace_mw).

**(c) Every approval gate**
- **VM work:** FOUND. kind `vm` at :1171 and :3544; `_touches_vm` forces the popup (:1961, :3145); VM migration approval (:2636).
- **Preauthorized runs:** FOUND. `_run_preauthorized` (:3155); auto_approve logic (:1960–1966); EXECUTE-NOW (:1064).
- **Change proposals:** FOUND. PROPOSE_RULES (:930), `_parse_proposal` (:949), `_run_gated` (:1168), chat proposal → approval (:3537), background apply (:1310), chat "approve" (:3274).
- **Deploy:** FOUND. `/deploy/request` (:399); "Deploy these N files?" (:1806); approve branch (:248); propose-only plan (:2669).
- **db-migrate:** FOUND. :1837 gate, :260 approve, :294 reject, :1887 apply.
- **synclist:** FOUND. :1820 gate, :257 approve, :286 reject, :1870 apply; also the un-kinded re-sync baseline at :2611.
- **qa-recommendation:** FOUND. :1990 create, :263 approve, :280 reject.
- **Periodic schedule gate:** FOUND. :817–836.
- **Per-run supersede:** FOUND. :1789.

**(d) Chat / scope streaming and the agent orientation prompts**
- **Streaming:** FOUND. `/scope/stream` (:597) → `_scoped_gen` (:3261).
- **Injected rules, in order:**
  1. Chat "approve" shortcut (:3274).
  2. Deterministic status answer (:3295).
  3. Team controls (:3376).
  4. PROJECT BRIEF standing context, "not a checklist" (:3427).
  5. `_brain_orientation` (:3200), which contains:
     - the team roster, with "do not invent work for idle roles";
     - CONNECTED SERVICES, with "never guess a value you can fetch";
     - `_orientation_block`: capability.md; deploy_changes scan/dbscan/update; deploy.sh only after approval, SSH/IP plumbing internal and never surfaced to the Chief; read provider tutorials first; scoped credentials delta → default, report credential_source, never print a key; core-rules.md, ORCHESTRATOR.md and odin_core as source of truth;
     - tutorial_guard;
     - agent_scope_guard;
     - AUDIT broken methods to avoid;
     - BE SMART & AVOID DUPLICATION: read existing work first, reuse/extend, stay in scope, never import another project's requirements, don't invent requirements.
  6. OWNER_RUN_FLOW.md: authoritative, one approval at a time, never bundle (:3441).
  7. Sources read-only (:3450).
  8. Project folder only, never the repo root (:3454).
  9. scope_answer_guard (:3486).
  10. Conversation memory, last 8 messages (:3499).
  11. read_execute_guard for reads, or PROPOSE_RULES for work (:3504–3511).
- **Member-run prompts** (`_orchestrate_gen`):
  - loc rules (:2110);
  - owner_brief verbatim (:2122);
  - LIVE READ-ONLY DATA (:2142);
  - mandate / hand-off (:2446);
  - resources + env (:2485);
  - orientation (:2495);
  - readiness STEP 1/2 (:2508);
  - audit feedback and widen scope (:2716);
  - EXECUTE-NOW + build directive + time budget (:1093);
  - QA prompt (:2218);
  - fix prompt (:2359);
  - CTO route / review / QA-recommend prompts (:2331, :2866, :1982);
  - apply prompts (:1223, :1355);
  - auto-continue and diagnosis prompts (:1387, :1738).
- **Defined but unused:** `_DEVOPS_KNOWLEDGE` (:2995).

**(e) Deploy / operations flows**
- FOUND:
  - Deterministic config/request/operation routes: :389–479.
  - `_deploy_bg` self-heal + prompt-audit + snake hunt: :1618.
  - `_resume_operation`: :1576.
  - Sequential gates (`_op_*`): :1695–1915.
  - Hybrid DevOps deploy in the pipeline (scan → ai_decide_deploy → run_decision, once per run): :2554–2701.
  - VM access / SSH / rsync auth: :1248–1307.
  - Operations stop/provide: :452–468.
  - Stop cascades to operations: :1537.
  - Legacy sync/deploy run: :372–380.

**(f) Synchronization, live sync, anchor, UDP, clones**
- **Partly FOUND:**
  - Delta sync `/scope/messages?since=` (:605).
  - Idempotent `client_msg_id` post (:753).
  - Server-side chat registry shared across clients (:689).
  - Upward `scopes.sync_up` (:2904, :2966, :3548).
  - Anchor: `anchor._connector_facts` live data grounding (:2139).
  - "synclist" = change-list re-baseline, not data sync (:1820).
- **NOT FOUND** in this file: UDP, clones, an anchor queue/poller, or a live-sync push.

**(g) Hallucination / stuck / generic / wrong-format reply handling**
- **Hallucination, FOUND:**
  - No invented agents: :2088, :137.
  - Audit eye catches fake success: :2777.
  - Fake-PASS override: :2316.
  - Artifact gate and hard build gate (narrated builds): :2782, :2818.
  - QA "don't trust the report": :2223.
  - "Never claim blocked / harness" rule: :933.
  - Announce-only turn = FAILURE: :1396, :1745.
  - Deterministic status answer, never the LLM: :3291.
  - Don't invent requirements: :3253.
  - Engine-auth failure guard: :2935.
- **Stuck, FOUND:**
  - Liveness beater: :1034.
  - VM-access timeout: :1274.
  - Stale-run detection: :1495.
  - QA time budget: :2207.
  - Quota pause: :2851.
  - Status anti-loop: :3291.
  - Deploy runs once: :2557.
- **Generic replies:** partly FOUND. Scope guard + brain orientation: :3486, :3253.
- **Wrong format, FOUND:**
  - Tolerant proposal parse: :949.
  - Robust PASS/FAIL parse: :2289.
  - JSON extraction fallback for CTO routing: :2339.
- **Not found here:** a dedicated "generic reply" detector (only prompt-level).


<!-- ==================== PART K2B ==================== -->

# K2B — Capability inventory (orchestration core, engine, scheduler, approvals, reports, meeting, dispatcher)

Scope: `server/` projects.py, claude_cli.py, brain_handler.py, approvals.py, operations.py, main_task.py, scheduler.py, activity.py, models_config.py, capabilities.py, run_timer.py, intent.py, test_intent.py, notifications_store.py, notifications_api.py, report_engine.py, deploy_agent.py, deploy_runner.py, meeting_api.py, zoom_pipeline_run.py; `orchestrator/` dispatcher.py, semantic_router.py. All files read in full. MFI = /home/claude/MFI.md. "§0.2" = the MFI hidden-features table, which has no row IDs. Secrets are named only (CRED_PATH `workspace/shared/oth/.cred`, key `azvmcred`); no values are copied.

## 1. Capabilities found

| ID | Category | Capability | What it does | Evidence | Triggered by | In MFI? |
|---|---|---|---|---|---|---|
| K2B-001 | Structural | Technical role catalogue (ALL_MEMBERS) | 10 technical roles: Fullstack, Mobile, DevOps, QA, Security, Embedded, Data, GameDev, XR, Designer, each with nature/group/deps/icon/description | projects.py:21 `ALL_MEMBERS` | role_catalog, infer_team, create_project | C-003, A-15 |
| K2B-002 | Structural | "One owner" staffing principle | Rule text: web UI+API+DB is ONE Fullstack owner; roles split only for different disciplines; no two people editing the same folders | projects.py:15-20, :23 | catalogue and planner prompts | A-15 |
| K2B-003 | Structural | Operational role catalogue (OPERATIONAL_MEMBERS) | Non-technical operators: HubSpot, CloudDebug, Marketing, Email, Content, Support, Sales, Fulfillment, Analytics, Writer, Finance, SEO | projects.py:49 | role_catalog, infer_team | A-07, A-12, A-14, A-26 |
| K2B-004 | Safety & approvals | Operator rule | Operators never write or edit app code and never define API contracts. Each holds one platform API key, may be asked early only for that key, and does its real work after deploy | projects.py:44-48 (comment), :52-61 (descriptions) | planner and resources prompts | B-175, B-170 |
| K2B-005 | Per-project features & integrations | Reporter agent (report_engine asset) | Catalogue role that owns the reusable branded report or export asset (MD/DOCX/PDF/PPTX) | projects.py:62 `Reporter` (asset="report_engine") | project team seeding | A-24, A-25 |
| K2B-006 | Per-project features & integrations | Security team catalogue entries | SecCTO (governance; never approves its own action), SecArchitect (intel/OSV/KEV), SecInvestigator (read-only; mutating commands refused), AssetSurface, Predictor, Recovery (encrypted backups, approval-gated restore), BehaviorIDS (UEBA; UFW blocks always approval-gated) | projects.py:70-124 | SOC blueprint, team seeding | A-08, A-01, A-28, A-23, C-033 |
| K2B-007 | Voice | MeetingVoice agent (meeting_monitor asset) | Catalogue role that brings the 🎙 live-meeting capability (capture, transcribe, language detect, 13-section report, MD/Word AR/EN) to any project it joins | projects.py:125 `MeetingVoice` | team seeding | B-203, A-173 |
| K2B-008 | Voice | Meeting asset signature | `MEETING_ASSET="meeting_monitor"` plus keyword signature (meeting, voice stream, transcription, …) used to detect meeting-capable agents | projects.py:131-133 | project_has_meeting_asset | B-199 |
| K2B-009 | Voice | project_has_meeting_asset | True if any project agent carries the asset or matches the signature, so the UI shows 🎙 | projects.py:136 `project_has_meeting_asset` | GET /meeting/capable | B-199 |
| K2B-010 | Structural | Connector dependency labels | DEP_LABELS maps role deps (azure, klaviyo, veeqo, easypost, analytics, helpdesk, crm) to friendly names for readiness warnings | projects.py:151 `DEP_LABELS` | roles_readiness, resources_block | no |
| K2B-011 | Auth & security | Credential path and key lookup order | `CRED_PATH` (shared oth/.cred) and ENV_SOURCES order: (1) mandate ENV block, (2) shared pool, (3) project .env, (4) .cred | projects.py:155-156 | resources_block, plan_pipeline | B-174 |
| K2B-012 | Orchestration core | resources_block (per-agent "Allowed Resources & Dependencies") | Injects the per-role permissions/keys/needs section with the REASON-BEFORE-ASK rule into the agent prompt | projects.py:159 `resources_block` | agent execution prompts, capability_options | B-173 |
| K2B-013 | Safety & approvals | Fullstack/Mobile resource rules | Full read/write; say so explicitly if Write/Edit fails; read keys from env, never from operators; ask the CTO once only if missing | projects.py:174-184 | resources_block | B-173 |
| K2B-014 | Safety & approvals | DevOps firewall/port rule text | SSH 22 only to the current single IP; never 0.0.0.0/0; never touch 80/443; re-pin 22 and retry before aborting; SSH as mostafa; az runs on the Mac | projects.py:185-194 | resources_block (DevOps) | B-135, A-029 |
| K2B-015 | Safety & approvals | DevOps verify-every-command and content-level overwrite | Read exit code and output of each remote command; rsync `--checksum`; prove zero pending via `--dry-run --itemize-changes` or md5sum | projects.py:195-204 | resources_block (DevOps) | B-176 |
| K2B-016 | Safety & approvals | DevOps boundary | Needs a deploy target and a QA-approved build; ask once if missing; writes no feature code; runs last | projects.py:205-207 | resources_block | B-173 |
| K2B-017 | Safety & approvals | QA read-only resource rule | Read-only tools; `ls -R` first; reply FAIL if the folder is empty; quick checks only; never invent a pass | projects.py:208-214 | resources_block (QA) | B-177, B-173 |
| K2B-018 | Safety & approvals | Operator default-key protocol | Use the default key from .cred if told; use a given key if provided; ask the CTO at most once only if the mandate is silent; work after deploy; never fabricate data | projects.py:215-235 | resources_block (operators with deps) | B-175 |
| K2B-019 | Safety & approvals | Non-key operator and other-specialist rules | Non-technical artifact producers: no code, no keys, ask once for missing input. Other technical roles read creds from ENV_SOURCES | projects.py:236-247 | resources_block | B-173 |
| K2B-020 | Orchestration core | resources_hint | One-line summary per member of what it already has, injected into the CTO planner so it does not re-request things | projects.py:250 `resources_hint` | plan_pipeline | no |
| K2B-021 | Structural | Project types catalogue (PROJECT_TYPES) | 19 types (12 tech, 7 operational), each with group, label, icon and suggested members | projects.py:273 `PROJECT_TYPES`; :834 `project_types` | GET /project-types (api_v2) | C-003, A-211 |
| K2B-022 | Orchestration core | recommend_type | Keyword recommender that suggests a project type from the description (a suggestion, not a lock) | projects.py:300 `recommend_type` | create_project (empty type) | no |
| K2B-023 | Structural | member_def | Looks up a role in the technical or operational registry | projects.py:325 | create_project, resources | no |
| K2B-024 | Orchestration core | _dep_met (connector readiness probe) | Checks whether a role's dependency is connected (azure via capabilities snapshot; others via user connectors with status=connected) | projects.py:330 `_dep_met` | roles_readiness | no |
| K2B-025 | Structural | role_catalog | Full roster (technical + operational) with deps for the dashboard | projects.py:346 | GET /roles, capability_options | C-003 |
| K2B-026 | Safety & approvals | known_role guard | TRUE only for catalogued roles; stops the system from silently inventing an agent from a typed provider word (e.g. "Vapi") | projects.py:351 `known_role` | classify_team | no |
| K2B-027 | Safety & approvals | classify_team | Splits proposed names into known and unknown; unknown ones need owner confirmation | projects.py:365 | create/intake confirmation | no |
| K2B-028 | Safety & approvals | _suggest_rule (no rule-less agent) | Default editable rule for a new agent: scope limit, no prod or destructive commands without approval, verified results only, ask the pool | projects.py:373 | capability_options | §0.2 (no ID) |
| K2B-029 | Orchestration core | capability_options (CTO "rules don't cover it" dialog) | Returns 3 choices: (1) ranked existing/catalogue agents, (2) a suggested new agent (name/role/description/resources/env/rules), (3) expand an existing member's editable role | projects.py:383 | POST /projects/{pid}/capability | C-003 |
| K2B-030 | Safety & approvals | Excluded agents never offered | Owner-removed agents are filtered out of every capability-dialog choice | projects.py:391, :399, :406, :442 | capability_options | no |
| K2B-031 | Safety & approvals | Non-intersection guard for new roles | If a suggested role overlaps an existing one (score ≥2 or same role), flags "overlaps … prefer expanding" | projects.py:414-436 | capability_options | no |
| K2B-032 | Orchestration core | Choice 3: expand existing member | Lists each project member with role, rules, resources block and env for in-dialog editing | projects.py:438-447 | capability_options | no |
| K2B-033 | Orchestration core | roles_readiness | Roster annotated with missing deps; warns but never blocks | projects.py:452 | roles UI | no |
| K2B-034 | Orchestration core | infer_team (negation-aware) | Derives the team from the description, respecting negation and intent | projects.py:463 `infer_team` | create_project (direct path) | A-070 |
| K2B-035 | Orchestration core | "Only DevOps" restriction | Phrases like "only devops" or "no other agent" return [DevOps] only | projects.py:470-474 | infer_team | A-070 |
| K2B-036 | Orchestration core | "No QA" negation | "no qa", "without qa", "don't involve" etc. drop QA | projects.py:475-476, :549-551 | infer_team | A-070 |
| K2B-037 | Orchestration core | Operational-only staffing | With no build intent, staffs only operators derived from the brief (Content/Marketing/SEO/Email/Analytics/Fulfillment; default Content); never Fullstack/QA. Fulfillment only for real shipping operations | projects.py:491-522 | infer_team | no |
| K2B-038 | Orchestration core | Build-team derivation | Fullstack always; DevOps unless "later/phase 2"; Security on auth/payment/PII; Mobile on mobile app; Fulfillment/Email/Analytics from brief domain; QA unless negated | projects.py:524-558 | infer_team | A-070, B-053 |
| K2B-039 | Structural | Unique slug identifier | Slugifies and appends a suffix on clash with an active project, a leftover record dir or a non-empty target folder | projects.py:561 `_slug`, :566 `_id_taken`, :586 `unique_identifier` | create_project | C-002 |
| K2B-040 | Structural | suggest_identifier | Recommended editable identifier for the create dialog | projects.py:599 | GET /projects/suggest-id; intake spec | C-002 |
| K2B-041 | Middleware & DB registry | DB is the source of truth for projects | `SELECT id FROM projects` in odin_core; falls back to on-disk folders; no global projects.json | projects.py:604 `_db_project_ids`, :642 `list_projects` | all project reads | B-060, B-057 |
| K2B-042 | Middleware & DB registry | Per-project canonical index.json persistence | Merges config into projects/<pid>/index.json via store.write_json, which re-indexes odin_core | projects.py:617, :623 `_persist_one`, :669 `_save_all`, :843 `_update` | every project write | B-080 |
| K2B-043 | Middleware & DB registry | _synth_project fallback | Builds a config from index.json defaults when the DB knows a project with no registry entry | projects.py:634 | list_projects | no |
| K2B-044 | Structural | get_project | Fetches one project by id | projects.py:662 | many callers / GET /projects/{pid} | C-002 |
| K2B-045 | Orchestration core | set_flags (qa_asked / qa_declined) | Persists small per-project flags | projects.py:676 | api_v2 QA prompt flow | no |
| K2B-046 | Orchestration core | create_project | Creates the project: id, type, cadence, periodic, folder, record, DB skeleton, team, company agents, SOC, schedule, feed entry | projects.py:687 | POST /projects | C-002 |
| K2B-047 | Structural | Custom project types | Keeps a known type, slugifies a custom one, or recommends one if empty | projects.py:698-702 | create_project | no |
| K2B-048 | Scheduling & notifications | Project cadence (once / recurring / periodical) | Normalises cadence; periodical forces periodic.enabled; requireApproval defaults True | projects.py:703-713, :737-739 | create_project | B-066 |
| K2B-049 | Structural | Create the project folder on disk | A given parent path gets a <pid> subfolder; an existing matching folder is used as-is | projects.py:716-726 | create_project | A-203 |
| K2B-050 | Middleware & DB registry | Single-door create (workspace_mw.create_owner) | Stamps the canonical skeleton and seeds the odin_core row on create | projects.py:752-762 | create_project | B-037 |
| K2B-051 | Orchestration core | Team seeding with canonical metadata | Registers each seeded member with canonical nature/mode/asset/description | projects.py:764-775 | create_project | B-053 |
| K2B-052 | Safety & approvals | Confirmed custom agents carry owner rules | Saves the rules supplied with a confirmed custom agent (list or string) so it never starts rule-less | projects.py:776-782 | create_project | no |
| K2B-053 | Orchestration core | Company agents auto-added | Every company-level agent and its rules are registered into the new project | projects.py:783-790 | create_project | A-076, B-100 |
| K2B-054 | Per-project features & integrations | SOC blueprint auto-provision | Security intent or type=security provisions the 8-agent SOC, knowledge base and monitor schedule, then posts a feed line | projects.py:794-814 | create_project | C-033 |
| K2B-055 | Scheduling & notifications | Periodic project registers its recurring run | Creates a scheduler task (kind_tag project-periodic) with requireApproval | projects.py:816-827 | create_project | D-042, C-020 |
| K2B-056 | Synchronization & Anchor | Company feed sync_up on create | Posts "Project created" upward to the company scope | projects.py:829-830 | create_project | A-064 |
| K2B-057 | Structural | operational_members() | Lists operator roles for the creation UI | projects.py:839 | creation UI | C-003 |
| K2B-058 | Structural | update_project | Updates the given non-None fields | projects.py:849 | POST /projects/{pid}/update | C-002 |
| K2B-059 | Orchestration core | add_sources | Adds owner-supplied local folders (e.g. answering a deploy block) to project sources for the deploy resolver | projects.py:857 | deploy block answer / resume | no |
| K2B-060 | Structural | add_mapping | Appends a local↔cloud mapping with a role | projects.py:872 | POST /projects/{pid}/mappings | C-002, A-047 |
| K2B-061 | Orchestration core | Per-project custom rules | list/add/update/remove rules; writes plan/_custom-rules.md for the engine | projects.py:880 `_write_project_rules`, :889, :894, :905, :917 | /projects/{pid}/rules | A-078 |
| K2B-062 | Structural | archive / unarchive | Sets status archived/active | projects.py:927, :931 | POST archive/unarchive | C-002 |
| K2B-063 | Safety & approvals | Protected "arm" projects not deletable | delete_project refuses if `protected` or type=="arm" (anchor/backend/desktop/mobile arms) | projects.py:937-939 | DELETE /projects/{pid} | no |
| K2B-064 | Middleware & DB registry | Full purge on delete | Removes DB rows (delete_owner), project and scope folders, member chats, main_tasks, operations, schedules, approvals, deploy-config and activity, so a re-created id starts fresh | projects.py:940-987 | DELETE /projects/{pid} | B-054, B-037 |
| K2B-065 | Orchestration core | _engine (Claude to Ollama fallback) | Calls ClaudeCLIBrain if available, else OllamaBrain, else an offline message; optional model | projects.py:990 | planner, intake, proposals, meeting | A-001, A-002 |
| K2B-066 | Safety & approvals | sync_proposal (read-only pre-flight) | Engine reads DEPLOY-PLAYBOOK, diffs local vs VM, detects production and asks context-aware questions; executes nothing | projects.py:1004 | GET /projects/{pid}/sync | A-052, B-123 |
| K2B-067 | Safety & approvals | deploy_proposal | Engine drafts exact commands, impact and rollback, treats the site as production and asks approval; no execution | projects.py:1024 | GET /deploy; auto_remediate | A-052 |
| K2B-068 | Orchestration core | plan_pipeline (Project CTO planner) | Ordered resource-aware pipeline [{member, objective, deliverable, acceptance_criteria, depends_on}] | projects.py:1035 | orchestrate (api_v2) | A-066, B-170 |
| K2B-069 | Orchestration core | Planner team context | Tags each member TECHNICAL/OPERATIONAL with description and resources_hint; includes capabilities.summary_text | projects.py:1053-1071 | plan_pipeline | B-170 |
| K2B-070 | Orchestration core | Requirements-first rule (Owner step) | Missing env/keys/target become a first step assigned to "Owner"; never ask operators for the app key | projects.py:1076-1085 | plan_pipeline prompt | B-170 |
| K2B-071 | Orchestration core | Smart key assignment rule | CTO states "use your default key" or "use this project key" in each mandate so agents never round-trip | projects.py:1086-1093 | plan_pipeline prompt | B-170 |
| K2B-072 | Orchestration core | No no-op steps / QA automatic rule | Forbids busywork steps; no standalone QA step because the QA gate runs after each build | projects.py:1094-1100 | plan_pipeline prompt | B-170 |
| K2B-073 | Orchestration core | Reason-not-keyword plus role boundaries | Match by real work; Fullstack owns all web in any stack; operators never code; check existing fields before naming a new role | projects.py:1101-1124 | plan_pipeline prompt | B-170 |
| K2B-074 | Orchestration core | Ordering 0–5 rule | Owner reqs → Fullstack build → QA → DevOps deploy (link) → operators' live data → final cURL verification | projects.py:1125-1139 | plan_pipeline prompt | B-170 |
| K2B-075 | Orchestration core | Mandate-shaped JSON output | Each step = objective, deliverable, acceptance_criteria, depends_on | projects.py:1140-1147 | plan_pipeline | A-091 |
| K2B-076 | Orchestration core | Fuzzy member snap; keeps new roles | Snaps names and deps to real members; keeps a brand-new proposed role to be hired on the fly | projects.py:1159-1176 | plan_pipeline | A-069 |
| K2B-077 | Orchestration core | Offline heuristic chain | Falls back to Fullstack→Mobile→Security→QA→DevOps over the real team (the MFI text still says Backend→Frontend→DevOps) | projects.py:1177-1181 | plan_pipeline | A-066 |
| K2B-078 | Orchestration core | Drops redundant pre-deploy QA step | Deterministically removes QA steps placed before DevOps (unless last), preventing QA-ing QA loops | projects.py:1182-1194 | plan_pipeline | no |
| K2B-079 | Audit & consistency | check_plan_coverage (CTO self-QA) | Engine lists goal requirements no step covers | projects.py:1198 | orchestrate | A-090 |
| K2B-080 | Structural | JSON extractors | Robust array and object extraction from engine prose | projects.py:1216, :1227 | planner, intake | no |
| K2B-081 | Orchestration core | intake_step (adaptive intake) | Engine CTO returns ask / propose / digest JSON with spec (name, type, stack, description, features, team, recommendations, readiness, dependencies) | projects.py:1245 | POST /projects/intake | A-073, B-188 |
| K2B-082 | Orchestration core | Intake: read attachments, research, ask only if critical | Opens ATTACHED FILES with Read; may web-search; asks one question at a time only for critical gaps; existing projects are not rewritten | projects.py:1261-1271 | intake_step prompt | A-073 |
| K2B-083 | Orchestration core | Intake: confirm platform/team/features plus nature decision | Decides build vs operational nature; picks only real roles; no Fulfillment just because Amazon is mentioned | projects.py:1272-1290 | intake_step prompt | A-073 |
| K2B-084 | Safety & approvals | ANTI-DEVIATION rule | If the brief defines its own agents and says use only those, propose exactly those and nothing else | projects.py:1291-1293 | intake_step prompt | no |
| K2B-085 | Orchestration core | Recommendations never auto-staffed | Extra features/members are recommended with a WHY and need owner approval | projects.py:1294-1295 | intake_step prompt | A-073 |
| K2B-086 | Orchestration core | Intake readiness mapping | Maps each capability to ready or needs (new member / API to connect) before generation | projects.py:1296-1300 | intake_step | C-004 |
| K2B-087 | Audit & consistency | FAITHFULNESS rule | Keep the owner's requirements, paths, commands, excludes and run rules verbatim in the description | projects.py:1315-1318 | intake_step prompt | no |
| K2B-088 | Structural | Identifier injected into the proposed spec | Adds a suggested identifier if the spec has none | projects.py:1322-1323 | intake_step | C-002 |
| K2B-089 | Orchestration core | _engine_research (web tools for intake) | Temporarily sets ODIN_CLAUDE_TOOLS to include WebSearch/WebFetch, then restores it | projects.py:1328 | intake_step | no |
| K2B-090 | Orchestration core | _intake_fallback | Deterministic intake when the model is down: asks for the full description, then derives team, naive features and readiness | projects.py:1342 | intake_step | no |
| K2B-091 | Orchestration core | _engine_cwd | Runs a streaming engine session with cwd = project folder | projects.py:1385 | auto_remediate | A-028 |
| K2B-092 | Safety & approvals | auto_remediate (cross-agent fix chain) | A finding makes Fullstack/Mobile apply a safe fix in the project folder (no prod or .env); DevOps redeploy comes back as a gated proposal | projects.py:1402 | POST /projects/{pid}/remediate; scheduler finding | B-105, C-008 |
| K2B-093 | Build, packaging, run & clients | sync_run | Executes the approved local→VM sync per playbook and owner decisions; never node_modules or prod .env; systemd restart; stops if risky | projects.py:1436 | POST /projects/{pid}/sync/run | A-052 |
| K2B-094 | Build, packaging, run & clients | deploy_run | The owner's click is the approval: sync excluding secrets, install, build, systemd restart, report rollback | projects.py:1455 | POST /projects/{pid}/deploy/run | A-052 |
| K2B-095 | Orchestration core | generate_plan | Read-only component, team and build-order plan; offline canned plan | projects.py:1468 | GET /projects/{pid}/plan | C-008 |
| K2B-096 | Orchestration core | Claude CLI availability check | `shutil.which("claude")` | claude_cli.py:24 `available` | all engine callers | A-001 |
| K2B-097 | Safety & approvals | Read-only engine mode (PreToolUse Bash hook) | Writes .readonly-settings.json that registers readonly_hook.py; read-only mode removes Write/Edit/MultiEdit/NotebookEdit | claude_cli.py:28 `_readonly_settings_file`, :59 `_tool_flags` | stream_session(readonly=True) | D-043, C-029 |
| K2B-098 | Orchestration core | Write tools for build agents | Non-read-only runs allow Read,Glob,Grep,Bash,Write,Edit,MultiEdit (fixes the "0 files on disk" narration bug) | claude_cli.py:63-74 | stream_session | A-004 |
| K2B-099 | Orchestration core | ODIN_CLAUDE_TOOLS env | Overrides the allowed toolset (default includes Bash; can force read-only) | claude_cli.py:66, :91, :124 | env | A-004 |
| K2B-100 | Orchestration core | Explicit model selection (`--model`) | Passes --model only for haiku/sonnet/opus/claude-*; "claude-cli" means CLI default (production unchanged); the test loop uses a fast model for gates | claude_cli.py:47 `_model_flags` | respond/stream_session(model=) | D-043 |
| K2B-101 | Orchestration core | respond (one-shot JSON) | Runs `claude -p --output-format json` in ROOT and returns .result | claude_cli.py:80 | projects._engine, main_task, deploy | A-001 |
| K2B-102 | Voice | Arabic dialect instruction | Arabic requests get the prefix "answer in Egyptian dialect, briefly" | claude_cli.py:85-86, :122, :160 | lang=ar | no |
| K2B-103 | Safety & approvals | No interactive questions | `--disallowedTools AskUserQuestion` on every call | claude_cli.py:69, :74, :96, :126 | all engine calls | A-005 |
| K2B-104 | Orchestration core | ODIN_CLAUDE_TIMEOUT (600 s) | Hard timeout for respond/respond_with_session, with a "took too long" reply | claude_cli.py:98-102, :129 | env | no |
| K2B-105 | Orchestration core | respond_with_session (session memory) | Uses `--resume <session_id>` and returns the new session id | claude_cli.py:116 | chat callers | A-013 |
| K2B-106 | Orchestration core | stream_session (live stream-json) | Yields status/text/tool_result/session/final events from `--output-format stream-json --verbose` | claude_cli.py:147 | scoped chat, orchestrate, _engine_cwd | A-006 |
| K2B-107 | Orchestration core | Hermetic agent runs (--strict-mcp-config) | Skips spawning global MCP servers (about 90 s silence); ODIN_AGENT_MCP=1 restores them | claude_cli.py:163-169 | env | no |
| K2B-108 | Orchestration core | Project-folder cwd plus --add-dir | Runs in the project folder (created if missing), adds the Odin ROOT and the parent folder for sibling multi-folder writes | claude_cli.py:170-189 | stream_session(cwd=) | A-028 |
| K2B-109 | Orchestration core | Live tool-step briefs and tool results | Icons/briefs for Bash/Read/Edit/Grep; tool_result text (280 chars) with error flag | claude_cli.py:193-204, :327-343 | stream_session | A-006 |
| K2B-110 | Orchestration core | Heartbeat (ODIN_CLAUDE_HEARTBEAT, 15 s) | Emits a "still working… Ns since last output" status during quiet work | claude_cli.py:218, :292-295 | stream_session | no |
| K2B-111 | Orchestration core | Stuck/idle detection (ODIN_CLAUDE_IDLE, 420 s) | No output for the idle window terminates the call as stuck, with the stderr tail | claude_cli.py:217, :296-303 | stream_session | §0.2 (no ID) |
| K2B-112 | Orchestration core | No-tool-progress guard (ODIN_CLAUDE_MAXWALL, 900 s) | Terminates narration runaways with no tool_use/tool_result in the window; real tool work keeps the call alive; 0 disables | claude_cli.py:272-287 | stream_session | no |
| K2B-113 | Orchestration core | Background stdout reader plus stderr drain | Threads prevent the pipe deadlock; stderr kept for diagnosis and logged live to workspace/logs/engine_stderr_live.log | claude_cli.py:221-266 | stream_session | no |
| K2B-114 | Orchestration core | default_handler singleton | ClaudeCLIBrain instance | claude_cli.py:360 | importers | A-001 |
| K2B-115 | Orchestration core | OllamaBrain (local fallback) | Calls a local Ollama chat model (ODIN_OLLAMA_URL/ODIN_OLLAMA_MODEL) with EN/AR spoken-style system prompts | brain_handler.py:17-55 | dispatcher, projects._engine | A-002 |
| K2B-116 | Voice | Spoken-friendly failure | Returns an EN or AR message instead of crashing when Ollama is down | brain_handler.py:56-61 | OllamaBrain.respond | A-002 |
| K2B-117 | Orchestration core | Pluggable brain swap point | `default_handler` is any object exposing respond(text, lang) | brain_handler.py:64-65 | voice loop | A-003 |
| K2B-118 | Safety & approvals | Approval request store | pending→approved/rejected plus applied; files/commands/cwd/kind/inline flag in approvals.json | approvals.py:53 `create`, :45-50 | agents/CTO proposals, GET /approvals | C-011 |
| K2B-119 | Safety & approvals | Severity classification | critical (file writes, VM, rsync/scp/ssh, destructive regex), caution (env-changing commands), routine (qa-recommendation) | approvals.py:18-42 `severity_of`, `_DESTRUCTIVE`, `_WRITECMD` | create | no |
| K2B-120 | Safety & approvals | Security alarm channel | security=True gives a red "🔴 SECURITY:" alarm with recommended action and fix_plan; must be approved individually | approvals.py:63-83, :97 `create_security` | SOC/security agents | no |
| K2B-121 | Safety & approvals | Bulk listing excludes security items | list_pending(bulk=True) drops security approvals | approvals.py:108 | approve-all | no |
| K2B-122 | Safety & approvals | approve_all_safe | Approves all non-security pending items and reports the security items skipped | approvals.py:119 | POST /approvals/approve-all | C-011 |
| K2B-123 | Safety & approvals | decide / mark_applied / list_for / pending_count / get | Owner decision with note; applied result (4000 chars); history; count | approvals.py:104, :132, :139, :151, :161 | approve/reject endpoints, executors | C-011 |
| K2B-124 | Orchestration core | Operation record (single source of truth for a running task) | Live log, state, stop flag, steps, meta, result; in memory plus operations.json | operations.py:46 `create` | deploy/sync endpoints | C-014 |
| K2B-125 | Orchestration core | Restart marks running ops interrupted | On load, running becomes stopped with "interrupted by a backend restart" | operations.py:30-38 `_load` | process start | no |
| K2B-126 | Orchestration core | Block→ask→resume | ask() sets state blocked with question and needs fields; provide() records answers for the resume | operations.py:65 `ask`, :91 `provide` | deploy_runner.run_decision; POST /operations/{oid}/provide | C-014 |
| K2B-127 | Orchestration core | Stop request | request_stop sets the flag; stop_requested is polled by executors | operations.py:138, :150 | POST /operations/{oid}/stop | C-014 |
| K2B-128 | Orchestration core | log / step / set_state / set_meta | Line log capped at 800, steps, terminal-state timestamps, metadata | operations.py:82, :103, :115, :124 | deploy_runner, deploy_agent | C-014 |
| K2B-129 | Middleware & DB registry | operations.purge | Removes all operations for a project | operations.py:155 | delete_project | no |
| K2B-130 | Orchestration core | list_for / latest / get | Light list without logs; latest per project | operations.py:168-185 | GET /operations, /operations/latest | C-014 |
| K2B-131 | Orchestration core | Main Task shared-state object | Per-project persistent {objective, brief_verbatim, requirements, decisions, plan, status, pool} | main_task.py:87 `create` | orchestrate | A-089, C-013 |
| K2B-132 | Audit & consistency | extract_requirements (omission guard) | Engine splits the brief into checkable items, with a line/sentence fallback (≤20) | main_task.py:47 | main_task.create | A-090 |
| K2B-133 | Audit & consistency | Constraint filter | Drops standing rules/meta ("do not", "never", "from next time"…) so constraints don't mark a good run incomplete | main_task.py:70-82 `_is_constraint` | extract_requirements | no |
| K2B-134 | Orchestration core | Shared context pool append | Appends every CTO decision and member output (whole, cap 16000 chars per entry) in order | main_task.py:101 `append` | orchestrate | C-013 |
| K2B-135 | Orchestration core | pool_text with faithful compaction | Full pool verbatim; above ODIN_POOL_LIMIT (120000) the older part becomes a cached engine summary and recent context (70%) stays verbatim | main_task.py:135 `pool_text`, :115 `_engine_compact` | agent prompts | no |
| K2B-136 | Orchestration core | set_plan / write_deliverable | Stores mandates; records a member's deliverable and flips covered requirements done | main_task.py:180, :188 | orchestrate | A-092 |
| K2B-137 | Audit & consistency | coverage / open_requirements | Plan-to-requirement coverage check; lists open items | main_task.py:202, :215 | orchestrate | A-090 |
| K2B-138 | Orchestration core | big_picture | Curated hand-off: objective, verbatim brief, live checklist, delivered items | main_task.py:221 | member prompts | no |
| K2B-139 | Orchestration core | mandate_text | A member's bounded slice: objective, inputs, deliverable, acceptance, depends_on, no fake done | main_task.py:242 | member prompts | A-091 |
| K2B-140 | Audit & consistency | checklist_text | Whole-job checklist kept in view by every member | main_task.py:258 | member prompts | no |
| K2B-141 | Audit & consistency | reconcile | Heuristic term match marks requirements done and returns those still open (final completeness check) | main_task.py:268 | orchestrate final | A-092 |
| K2B-142 | Orchestration core | upstream_deliverables | Injects the done deliverables of depends_on members | main_task.py:286 | member prompts | no |
| K2B-143 | Scheduling & notifications | Scheduled-task CRUD | list/get/create/update/delete tasks in schedules.json (status idle/pending_approval/running, runs, skips) | scheduler.py:29-80 | /schedules endpoints | C-020 |
| K2B-144 | Scheduling & notifications | Schedule kinds once / interval / daily | Next-run computation; interval minimum 5 s | scheduler.py:121 `_next_run` | create/update/tick | D-042 |
| K2B-145 | Scheduling & notifications | Calendar schedule kind | Several times per day, weekday and monthday filters, scans a year ahead; default timezone Africa/Cairo | scheduler.py:83 `DEFAULT_TZ`, :85 `_next_calendar` | _next_run | C-020 |
| K2B-146 | Scheduling & notifications | Timezone-aware daily (DST-correct) | A daily task with tz uses zoneinfo | scheduler.py:131-144 | _next_run | C-020 |
| K2B-147 | Scheduling & notifications | Grace window plus missed-run roll-forward | daily/calendar 2 h; interval half the interval (1–30 min); once never misses; overdue tasks roll forward without running | scheduler.py:153 `_grace`, :165 `_next_future`, :403-416 | _tick | D-042 |
| K2B-148 | Safety & approvals | Approval-gated recurring runs | A due task with requireApproval goes to pending_approval instead of running | scheduler.py:417-422 | _tick | D-042, C-020 |
| K2B-149 | Scheduling & notifications | list_pending / approve / skip | Approve runs now and reschedules; skip rolls to the next slot; a "once" task is disabled after either | scheduler.py:176, :180, :201 | GET /schedules/pending, POST approve/skip | C-020 |
| K2B-150 | Scheduling & notifications | _run_task scope routing | Runs as the assignee member scope or the project scope; a manual run posts into the current chat, a cron run creates a ⏰ chat | scheduler.py:219-230 | tick, approve, run_now | A-079, B-099 |
| K2B-151 | Scheduling & notifications | Started/finished notifications | Adds "▶ started" and "✅/⚠️ finished" notifications with pid/cid deep link | scheduler.py:238-244, :285-293, :319-324 | _run_task | C-032 |
| K2B-152 | Orchestration core | run_cmd autonomous pipeline execution | A task with run_cmd runs the shell pipeline directly ({pid}/{cid} substituted, 1800 s timeout), not through the propose-first engine | scheduler.py:245-294 | _run_task | B-052 |
| K2B-153 | Scheduling & notifications | Guaranteed visible start and result lines | Posts "▶ Running…" first, then ✅ with the stdout tail or ⚠️ with exit code and tail | scheduler.py:253-280 | _run_task | B-052 |
| K2B-154 | Orchestration core | Project-level team run (autonomous authorisation) | A run with no assignee calls api_v2.orchestrate_blocking. Non-VM goals get a "[Scheduled autonomous run — approval already granted…]" suffix. VM/Azure changes still hit the gate | scheduler.py:299-325 | _run_task | no |
| K2B-155 | Scheduling & notifications | Single-agent periodic task via dispatcher | Focused reply as the member through default_dispatcher.respond | scheduler.py:326-335 | _run_task | A-079 |
| K2B-156 | Safety & approvals | Finding → auto_remediate trigger | Reply keywords (vulnerab, cve-, outdated, critical…) start projects.auto_remediate | scheduler.py:336-343 | _run_task | B-105 |
| K2B-157 | Scheduling & notifications | run_now (▶ Run button) | Fires the project's tasks now in background threads; optional task_id/prompt/cid; ad-hoc default run if no task | scheduler.py:348-388 | POST /projects/{pid}/run-now | C-013 |
| K2B-158 | Per-project features & integrations | HubSpot deterministic ▶ Run | pid hubspot-crm-operator returns hubspot_api.run_overview synchronously (real counts plus notification) | scheduler.py:355-364 | run_now | B-052 |
| K2B-159 | Scheduling & notifications | Background tick loop | Daemon thread every 20 s runs _tick, then the audit sentinel | scheduler.py:391 `_tick`, :455 `start_background` | server start | A-079, D-042 |
| K2B-160 | Scheduling & notifications | Catch-up tasks | A task with catchup=True missed while offline runs once at launch, then reschedules | scheduler.py:403-412 | _tick | C-020 |
| K2B-161 | Audit & consistency | Debounced workspace audit sentinel | About every 15 min calls workspace_audit.sentinel() (heal and notify on violations) | scheduler.py:440-452 `_audit_sentinel_maybe` | scheduler loop | B-065 |
| K2B-162 | Orchestration core | Live activity bus | mark_active/beat/mark_idle with a 180 s TTL prune; snapshot of active agents and the last 60 flow events | activity.py:21-62 | GET /activity, /activity/stream | C-019 |
| K2B-163 | Orchestration core | Hand-off flow log | log_flow records from→to hand-offs (last 300 kept) | activity.py:42 | orchestrate | A-065 |
| K2B-164 | Orchestration core | activity.clear on delete (call site) | delete_project clears the live marker | projects.py:982-986 | delete_project | no |
| K2B-165 | Orchestration core | Per-scope model resolution | member → project → main → default (ODIN_MAIN_MODEL, default claude-cli) | models_config.py:21, :39 `get_model` | engine callers | A-012, C-015 |
| K2B-166 | Orchestration core | set_model | Sets main/company or a scope's model in models.json | models_config.py:54 | POST /models/set | C-015 |
| K2B-167 | Orchestration core | Model catalogue with cost tags | claude-cli (paid), Qwen 7B/14B (free), plus live local Ollama models | models_config.py:24 `CATALOG`, :64 `available_models` | GET /models | B-117, A-128 |
| K2B-168 | Per-project features & integrations | Connectable-integrations catalogue | App Store, Google Play, Cloudinary, Stripe, GitHub, Vercel/Netlify with needs and how-to | capabilities.py:18 `CATALOG` | snapshot / intake | B-186 |
| K2B-169 | Middleware & DB registry | Connectors listed from odin_core | DB ids plus per-folder index.json; disk fallback | capabilities.py:48, :59, :70 | GET /connectors, _dep_met | A-077 |
| K2B-170 | Auth & security | add/remove connector, secret stored separately | Single-door put_file; API key kept in connector_keys.json, never in the registry; remove flushes the DB row and key | capabilities.py:87, :103 | /connectors CRUD | A-077 |
| K2B-171 | Per-project features & integrations | Capabilities snapshot | have (Claude engine, Ollama models, Azure CLI, Azure VM from connection profile, user connectors) and available | capabilities.py:117 `snapshot` | GET /capabilities | B-186 |
| K2B-172 | Orchestration core | summary_text for prompts | "Already connected … / NOT yet connected …" text for CTO prompts | capabilities.py:155 | plan_pipeline, intake_step | B-186 |
| K2B-173 | Testing | Run timer | Times a run (cached flag from ODIN_DISABLE_CACHE) into data/run_timings.json (last 200 kept) | run_timer.py:30 `Timer` | orchestrate / e2e | C-045 |
| K2B-174 | Testing | Cached vs non-cached comparison | Latest pair, speedup and saved seconds; CLI entry | run_timer.py:52 `compare`, :64 | CLI | C-045 |
| K2B-175 | Safety & approvals | Owner veto detection (forbidden) | Detects ruled-out actions this turn: deploy (negation / read-only / only diagnose/logs) and db_rebase | intent.py:18 `forbidden` | classify_request | no |
| K2B-176 | Orchestration core | Approval-phrase detection | is_approval regex ("i approve", "go ahead", "proceed"…) | intent.py:34, :42 | classify_request | no |
| K2B-177 | Orchestration core | classify_request (intelligence-first scope) | Engine-first JSON {mode direct/orchestrate, forbid}; heuristic fallback (scoped/question/build/deploy regexes) | intent.py:46 | orchestrate entry (api_v2) | C-013 |
| K2B-178 | Orchestration core | requirements_for_run | Requirements come from the owner's message, not the brief; a direct ask gives 1 item, multi-part asks split (≤8) | intent.py:113 | orchestrate | no |
| K2B-179 | Audit & consistency | accept_done evidence gate | A completion claim is accepted only with evidence keys (diff, exit_code, http_status…) | intent.py:127 | orchestrate | no (cf. A-034) |
| K2B-180 | Testing | test_intent unit suite | 7 cases: scoped direct, diagnosis forbids deploy, approval binds, fake done blocked, real build orchestrates, db_rebase veto, question direct | test_intent.py:1-54 | CLI | C-046 |
| K2B-181 | Scheduling & notifications | Notification store | add with kind (started/finished/finding/info), severity (info/attention/critical), pid+cid deep link; newest first, capped at 300; RLock | notifications_store.py:14-37 | scheduler, other modules | C-032 |
| K2B-182 | Scheduling & notifications | Unread tracking / mark read / clear | list(unread_only), unread_count, mark_read(one or all), clear(read-only or all) | notifications_store.py:39-63 | API | C-032 |
| K2B-183 | Scheduling & notifications | GET /notifications | Items plus unread count | notifications_api.py:9 | UI bell | C-032 |
| K2B-184 | Scheduling & notifications | GET /notifications/count | Unread count | notifications_api.py:14 | UI bell | C-032 |
| K2B-185 | Scheduling & notifications | POST /notifications/read | Mark one or all read | notifications_api.py:19 | UI | C-032 |
| K2B-186 | Scheduling & notifications | POST /notifications/clear | Clear read items or all | notifications_api.py:25 | UI | C-032 |
| K2B-187 | Scheduling & notifications | POST /notifications/test | Emits a sample notification | notifications_api.py:31 | UI wiring | C-032 |
| K2B-188 | Per-project features & integrations | Report engine brand | DEFAULT_BRAND (name, info, logo desktop/build/icon.png, colours), overridable per spec | report_engine.py:21, :27 | Reporter asset | C-018 |
| K2B-189 | Per-project features & integrations | Markdown export | Title, brand, meta, sections with badges/bullets/tables, footer | report_engine.py:30 `to_md` | render | C-018 |
| K2B-190 | Per-project features & integrations | DOCX export | Logo, shaded title, coloured headings, badge shading, bullet lists, grid tables | report_engine.py:57 `to_docx` | render | C-018 |
| K2B-191 | Per-project features & integrations | PDF export | ReportLab A4 with logo, meta table, styled headings and badges, striped tables | report_engine.py:105 `to_pdf` | render | C-018 |
| K2B-192 | Per-project features & integrations | PPTX export | Title slide with logo, one slide per section | report_engine.py:156 `to_pptx` | render | C-018 |
| K2B-193 | Per-project features & integrations | render / render_to_file | EXPORTERS map (format→fn, mime, ext; md default); writes <stem>.<ext> | report_engine.py:180-194 | GET /project/report | C-018 |
| K2B-194 | Build, packaging, run & clients | Self-healing deploy loop | Runs deploy.sh, analyses on failure, fixes, re-runs; up to MAX_ROUNDS=10; success only on a real exit 0 | deploy_agent.py:29, :134 `run` | run_decision / deploy endpoints | A-036, A-034 |
| K2B-195 | Safety & approvals | Destructive-fix block (_UNSAFE) | migrate reset/--force/drop/truncate/delete from/rm -rf //db push/reset --hard are never auto-run; needs_owner | deploy_agent.py:33, :184-187 | run | A-036 |
| K2B-196 | Audit & consistency | Learned faults memory | Signature (P####, TS errors, E-codes…) → saved reason+fix in deploy_faults.json (≤100); a known safe fix is applied instantly | deploy_agent.py:58-84, :172-175 | run | A-037 |
| K2B-197 | Build, packaging, run & clients | Concern-specific VM probes | prisma status / build log / ports / journalctl bendcore-staging / perms / disk+mem, chosen by the error | deploy_agent.py:95 `_gather` | run | A-036 |
| K2B-198 | Build, packaging, run & clients | diagnose (engine root cause) | JSON {reason, one VM fix, needs_owner}; never loses data | deploy_agent.py:118 | run | A-036 |
| K2B-199 | Safety & approvals | Reboot commit point | After the VM rebooted, never re-run (avoids a reboot/reset loop); returns needs_owner | deploy_agent.py:158-166 | run | A-055 |
| K2B-200 | Safety & approvals | Same-fix loop guard plus fix-failed stop | Stops if the same fix repeats or the fix command fails | deploy_agent.py:189-199 | run | no |
| K2B-201 | Build, packaging, run & clients | run_script (proven deploy.sh) | Streams workspace/shared/infra/deploy.sh line by line into the operation log and chat | deploy_runner.py:42, :45 | deploy_agent.run | A-050, C-012 |
| K2B-202 | Orchestration core | Stop watchdog | Polls the stop flag every 1 s, independent of stdout; terminate/kill | deploy_runner.py:64-84 | run_script | C-014 |
| K2B-203 | Build, packaging, run & clients | ✓/✗ lines become operation steps | Real pipeline lines become UI step indicators | deploy_runner.py:90, :101-108 | run_script | no |
| K2B-204 | Build, packaging, run & clients | __ODIN_REBOOTED__ marker | Detects the commit point and hides the marker | deploy_runner.py:95-97 | run_script | D-027 |
| K2B-205 | Safety & approvals | HARD_EXCLUDES secrets list | .env*, .backup-env, *.copy, *.bak, *.tmp, *.pem, *.key, google-oauth json are always excluded | deploy_runner.py:129 | _rsync | A-025, B-138 |
| K2B-206 | Build, packaging, run & clients | Per-project deploy config | workspace/projects/<pid>/deploy/deploy-config.json get/save | deploy_runner.py:133-152 | GET/POST /deploy/config | C-012 |
| K2B-207 | Build, packaging, run & clients | ai_decide_deploy (AI brain decision) | Engine returns targets/reboot/excludes/verify_port/migration_intent from the brief; channel fixed to SSH-as-mostafa plus migrate deploy; `.last` diagnosis | deploy_runner.py:155 | deploy request flow | C-012 |
| K2B-208 | Build, packaging, run & clients | write_decision_config | Turns the decision into CFG_* shell vars (frontend/backend only) in shared/infra/_ai_decision_config.sh; syncs the odin_core row | deploy_runner.py:199 | run_decision | no |
| K2B-209 | Safety & approvals | Owner-selected source resolution | Repairs placeholder/missing local paths from the project's sources, mappings and localPath (fuzzy name match) | deploy_runner.py:232-285 `_project_sources`, `_bad_local`, `_match_source`, `_resolve_locals` | run_decision | no |
| K2B-210 | Safety & approvals | run_decision: stop and ask on unresolved folders | Blocks the operation with needs fields and stores the decision for resume; never guesses a path | deploy_runner.py:288-309 | deploy flow | no |
| K2B-211 | Testing | ODIN_DEPLOY_CONFIG harness lock | An existing env lock (e.g. sandbox) wins over the AI decision; frontend-only/backend-only args | deploy_runner.py:310-319 | run_decision | D-027 |
| K2B-212 | Testing | config_from_prompt | Extracts deploy targets from a prompt to verify the prompt reproduces the working config | deploy_runner.py:322 | tests | no |
| K2B-213 | Safety & approvals | Migration modes | reset (destructive, explicit each run) / new (`prisma migrate deploy`) / none | deploy_runner.py:342 `_migration_cmd` | run_deploy | A-039 |
| K2B-214 | Build, packaging, run & clients | rsync push plus content-level verify | Push with merged excludes and no --delete, then verify_sync (checksum dry-run); stale files fail the step | deploy_runner.py:369 `_rsync` | run_deploy | B-176 |
| K2B-215 | Build, packaging, run & clients | run_deploy (deterministic) | firewall refresh (the only control-plane action) → per target sync + migration/commands as mostafa → optional sudo reboot; stop-aware | deploy_runner.py:398 | deploy endpoints | A-032, A-033 |
| K2B-216 | Voice | GET /meeting/capable | Shows whether the project owns the meeting asset | meeting_api.py:397 | app 🎙 visibility | B-199, C-042 |
| K2B-217 | Voice | GET /meeting/state | Chunk count/meta, low-confidence count, hasReport, majority language | meeting_api.py:408 | meeting UI | B-195 |
| K2B-218 | Voice | POST /meeting/clear | Deletes the saved chunk files | meeting_api.py:420 | "clean & start fresh" | B-195 |
| K2B-219 | Voice | POST /meeting/chunk | Saves the audio chunk, transcribes it (scopes.transcribe), builds the chunk meta and invalidates cached reports | meeting_api.py:431 | live mic | B-195, B-196 |
| K2B-220 | Voice | POST /meeting/finish | Majority/forced language report, posted into a new project chat as the Live Meeting agent | meeting_api.py:457 | Stop | A-173 |
| K2B-221 | Voice | POST /meeting/finish_text (mobile) | Stores on-device transcribed texts as the manifest, then builds the report | meeting_api.py:474 | mobile sheet | B-198 |
| K2B-222 | Voice | GET /meeting/view | Builds or caches the report in a language for display | meeting_api.py:504 | meeting UI | B-195 |
| K2B-223 | Voice | GET /meeting/report | Downloads md / docx / pdf in ar/en | meeting_api.py:508 | export button | A-174, B-197 |
| K2B-224 | Voice | GET /meeting/report_all | Zip of AR/EN × MD/DOCX/PDF (6 files) | meeting_api.py:528 | export "all" | A-174 |
| K2B-225 | Voice | Language detection and majority language | Arabic-script vs ASCII count per chunk; majority weighted by text length | meeting_api.py:56, :208 | chunk/finish | A-173, B-202 |
| K2B-226 | Voice | Bilingual refinement | Removes EN/Egyptian-Arabic fillers, minority-language noise, 1-char fragments and repeated 2-3-word phrases; preserves protected tokens (CamelCase, paths, ALLCAPS, tech words, names, numbers) | meeting_api.py:68-155 `_refine`, `_is_protected` | _chunk_meta | B-201 |
| K2B-227 | Voice | Noise score and confidence | noise = fraction removed; confidence from length, real-word ratio and noise | meeting_api.py:158, :166 | _chunk_meta | B-201 |
| K2B-228 | Voice | Chunk record | id, timestamps, lang, speaker, raw/clean, topic, operational points (decision/action/deadline/risk incl. Arabic), low_confidence <0.35 with review note | meeting_api.py:179 `_chunk_meta` | chunk/finish_text | B-201 |
| K2B-229 | Voice | Raw engine call bypassing the approval gate | Calls projects._engine with read-only tools, not /chat (which would refuse "sensitive" content); treats refusal or offline text as empty | meeting_api.py:221; zoom_pipeline_run.py:25 | report build | B-196 |
| K2B-230 | Voice | 13-section EN/AR report prompts | Fixed sections, merge duplicates, confirmed vs proposed, "not mentioned", invent nothing | meeting_api.py:235, :243 | _build_report | A-173 |
| K2B-231 | Voice | Fallback report | Structural EN/AR report when the engine is offline | meeting_api.py:252 | _build_report | no |
| K2B-232 | Voice | Report cache plus invalidation | report_<lang>.md cached; deleted on a new chunk or finish_text | meeting_api.py:277-290, :449-452, :490-492 | view/report | no |
| K2B-233 | Voice | Low-confidence flags in the transcript | Merged transcript lines tagged ⚠️ when confidence <0.35 | meeting_api.py:264 `_transcript` | _build_report | B-201 |
| K2B-234 | Voice | Styled DOCX export (RTL) | Brand-coloured shaded title/headings, lists, bold spans, right alignment for Arabic | meeting_api.py:293, :337 | /meeting/report, report_all | A-174 |
| K2B-235 | Voice | Styled PDF export | ReportLab with brand colours; right-aligned body for Arabic | meeting_api.py:303 `_md_to_pdf_bytes` | /meeting/report, report_all | no |
| K2B-236 | Voice | Zoom autonomous pipeline run | 7 attributed agents (Audio Capture, Transcription, Chunking, Chunk Analysis, Memory and Storage, Final Summary, Notification) post into the project chat with no approval step | zoom_pipeline_run.py:21, :91 `run` | ▶ Run (run_cmd) / CLI | C-042 |
| K2B-237 | Voice | Transcript discovery | Uses live_transcript.txt in project data/files, then sample_meeting.txt candidates | zoom_pipeline_run.py:95-102 | run | no |
| K2B-238 | Voice | Smart chunking | Splits on speaker change (≥3 lines) or 14 lines; ids and 3-min timestamps | zoom_pipeline_run.py:42 `chunk_transcript` | run | no |
| K2B-239 | Voice | Chunk-analysis and final-summary prompts | CHUNK_FMT (9 sections, "Owner/Deadline/Dependency not mentioned") and FINAL_FMT (13 sections) | zoom_pipeline_run.py:59, :65 | run | A-13, A-03 |
| K2B-240 | Voice | Deterministic chunk fallback | Keyword-based importance and section skeleton so no chunk is left unanalysed | zoom_pipeline_run.py:72 `_fallback_chunk` | run | no |
| K2B-241 | Orchestration core | Usage stats recorded per pipeline agent | agents_registry.record_usage for each agent step (avoids 0% bars) | zoom_pipeline_run.py:104-106; projects.py:1424 | run, auto_remediate | A-075 |
| K2B-242 | Voice | Final report saved via the single door | workspace_mw.put_file project docs/final_report.md | zoom_pipeline_run.py:149-156 | run | no |
| K2B-243 | Voice | Smart notifications from the report | Title / what / why / who / next action / priority, invent nothing | zoom_pipeline_run.py:159-163 | run | A-20 |
| K2B-244 | Voice | CLI entry (--pid/--cid/--transcript) | Command-line runner printing a summary | zoom_pipeline_run.py:176-183 | scheduler run_cmd / CLI | C-042 |
| K2B-245 | Orchestration core | Specialist trigger map (AGENT_TRIGGERS) | Keywords for Frontend, Backend, DevOps & Cloud, Security & Compliance, QA & Testing, Database | dispatcher.py:27 | classify | A-063 |
| K2B-246 | Safety & approvals | Approval categories (APPROVAL_TRIGGERS) | 11 categories: deployment, azure-vm-action, code-change, config-change, ssl-certificate, database-migration, security-scan-active, production-data-access, sensitive-data-handling, dependency-install, secret-or-credential-change | dispatcher.py:45 | approval_check | B-012 |
| K2B-247 | Safety & approvals | SENSITIVE list and Security co-owner | Sensitive words add Security & Compliance to the agents | dispatcher.py:61, :161-163, :196-197 | classify / route | A-023 |
| K2B-248 | Safety & approvals | Read vs change hints | READONLY_HINTS / CHANGE_HINTS decide pure reads | dispatcher.py:64-73 | approval_check | A-020 |
| K2B-249 | Safety & approvals | Read-bypass categories | Only azure-vm-action/deployment/config-change can be bypassed by a pure read; never data/secrets | dispatcher.py:75 `READ_BYPASS_CATEGORIES` | approval_check | no |
| K2B-250 | Safety & approvals | ALWAYS_GATE safety floor | secret change, prod data, sensitive data and active scans are always gated, even with a semantic "read" | dispatcher.py:78, :198 | route | A-017 |
| K2B-251 | Orchestration core | Lifecycle hooks | pre-rule-load (core-rules.md present?), pre-approval STOP note, post-log | dispatcher.py:96-115 | route | A-016 |
| K2B-252 | Orchestration core | Name/path masking | Blanks quoted strings, named tokens, paths and hyphenated names before scoring | dispatcher.py:127 `_mask_names` | classify | A-018 |
| K2B-253 | Orchestration core | Keyword classify with DevOps pin | Scores agents; pins DevOps lead for VM/server/remote; falls back to CTO Brain | dispatcher.py:144 | route (fallback) | A-018 |
| K2B-254 | Safety & approvals | approval_check | Matched categories, minus the pure-read bypass, give required / readOnly | dispatcher.py:167 | route | A-020 |
| K2B-255 | Orchestration core | route: semantic primary, keyword fallback | ODIN_SEMANTIC_ROUTER=1 uses semantic_router; approval = change intent OR hard gate; notes router:semantic / keyword-fallback | dispatcher.py:180 | POST /dispatch, respond | A-017, A-014 |
| K2B-256 | Audit & consistency | Routing telemetry | Writes a ROUTE line to workspace/history/routing.jsonl (separate from the main audit log) | dispatcher.py:226 `_log` | route | A-015, B-006 |
| K2B-257 | Safety & approvals | respond: gate message (EN/AR) | A gated request returns "That's a X task and it needs your approval first (cats)…"; otherwise a clean engine reply with no routing label | dispatcher.py:242 | /chat, voice, scheduler single-agent | A-014, A-019, B-005 |
| K2B-258 | Orchestration core | _get_brain engine selection | ODIN_ENGINE=claude (default) uses ClaudeCLIBrain if installed, else Ollama | dispatcher.py:264 | respond | A-001, B-021 |
| K2B-259 | Orchestration core | Semantic router (Ollama JSON) | Local qwen classifies {agent, secondary, action read/change}; temperature 0; unsure → change | semantic_router.py:28, :53 `classify` | dispatcher.route | A-017 |
| K2B-260 | Orchestration core | Router model and timeout env | ODIN_ROUTER_MODEL (falls back to ODIN_OLLAMA_MODEL), ODIN_ROUTER_TIMEOUT (12 s) | semantic_router.py:21-22, :55 | env | no |
| K2B-261 | Orchestration core | Near-miss agent-name tolerance | Maps "DevOps", "devops & cloud" etc. to canonical agents; None → keyword fallback | semantic_router.py:79-91 | classify | no |

## 2. Not in MFI

| ID | Capability | Evidence |
|---|---|---|
| K2B-010 | Connector dependency labels (DEP_LABELS) | projects.py:151 |
| K2B-020 | resources_hint (one-line resources for the CTO planner) | projects.py:250 |
| K2B-022 | recommend_type (project type from description) | projects.py:300 |
| K2B-023 | member_def | projects.py:325 |
| K2B-024 | _dep_met connector readiness probe | projects.py:330 |
| K2B-026 | known_role guard (no silent agent invention, e.g. "Vapi") | projects.py:351 |
| K2B-027 | classify_team known/unknown split | projects.py:365 |
| K2B-030 | Excluded (owner-removed) agents never offered | projects.py:391 |
| K2B-031 | Non-intersection guard for new roles | projects.py:414 |
| K2B-032 | Capability dialog Choice 3 (expand an existing member) | projects.py:438 |
| K2B-033 | roles_readiness (warn, never block) | projects.py:452 |
| K2B-037 | Operational-only staffing (no Fullstack/QA without build intent) | projects.py:491 |
| K2B-043 | _synth_project fallback | projects.py:634 |
| K2B-045 | set_flags qa_asked/qa_declined | projects.py:676 |
| K2B-047 | Custom project types | projects.py:698 |
| K2B-052 | Confirmed custom agents carry owner rules | projects.py:776 |
| K2B-059 | add_sources (deploy block answer) | projects.py:857 |
| K2B-063 | Protected "arm" projects cannot be deleted | projects.py:937 |
| K2B-078 | Drop redundant pre-deploy QA step | projects.py:1182 |
| K2B-080 | JSON extractors | projects.py:1216 |
| K2B-084 | ANTI-DEVIATION intake rule | projects.py:1291 |
| K2B-087 | FAITHFULNESS intake rule | projects.py:1315 |
| K2B-089 | _engine_research (WebSearch/WebFetch for intake) | projects.py:1328 |
| K2B-090 | _intake_fallback | projects.py:1342 |
| K2B-102 | Egyptian-dialect Arabic instruction to the engine | claude_cli.py:85 |
| K2B-104 | ODIN_CLAUDE_TIMEOUT 600 s | claude_cli.py:98 |
| K2B-107 | Hermetic runs --strict-mcp-config / ODIN_AGENT_MCP | claude_cli.py:163 |
| K2B-110 | Engine heartbeat ODIN_CLAUDE_HEARTBEAT | claude_cli.py:218 |
| K2B-112 | No-tool-progress guard ODIN_CLAUDE_MAXWALL 900 s | claude_cli.py:272 |
| K2B-113 | stderr drain plus live engine_stderr_live.log | claude_cli.py:232 |
| K2B-119 | Approval severity critical/caution/routine | approvals.py:28 |
| K2B-120 | Security-alarm approval channel | approvals.py:63, :97 |
| K2B-121 | Bulk list excludes security items | approvals.py:108 |
| K2B-125 | Restart marks running operations interrupted | operations.py:30 |
| K2B-129 | operations.purge | operations.py:155 |
| K2B-133 | Requirement constraint filter | main_task.py:73 |
| K2B-135 | pool_text faithful compaction (ODIN_POOL_LIMIT) | main_task.py:135 |
| K2B-138 | big_picture curated hand-off | main_task.py:221 |
| K2B-140 | checklist_text | main_task.py:258 |
| K2B-142 | upstream_deliverables | main_task.py:286 |
| K2B-154 | Scheduled project-level autonomous team run (orchestrate_blocking plus autonomy suffix, _touches_vm) | scheduler.py:299 |
| K2B-164 | activity.clear on project delete | projects.py:982 |
| K2B-175 | intent.forbidden owner veto (deploy, db_rebase) | intent.py:18 |
| K2B-176 | intent.is_approval | intent.py:42 |
| K2B-178 | requirements_for_run (from the message, not the brief) | intent.py:113 |
| K2B-179 | accept_done evidence gate (intent.py; MFI only has audit.gate_success A-034) | intent.py:127 |
| K2B-200 | Same-fix loop guard / fix-failed stop | deploy_agent.py:189 |
| K2B-203 | ✓/✗ pipeline lines become operation steps | deploy_runner.py:90 |
| K2B-208 | write_decision_config (AI decision → CFG_* shell config) | deploy_runner.py:199 |
| K2B-209 | Owner-selected source path resolution | deploy_runner.py:232 |
| K2B-210 | run_decision stop-and-ask on unresolved folders | deploy_runner.py:288 |
| K2B-212 | config_from_prompt | deploy_runner.py:322 |
| K2B-231 | Meeting fallback report | meeting_api.py:252 |
| K2B-232 | Meeting report cache plus invalidation | meeting_api.py:277 |
| K2B-235 | Meeting PDF export (MFI lists only MD/DOCX; report_all actually zips 6 files incl. PDF) | meeting_api.py:303, :528 |
| K2B-237 | Zoom transcript discovery | zoom_pipeline_run.py:95 |
| K2B-238 | Zoom chunk_transcript | zoom_pipeline_run.py:42 |
| K2B-240 | Zoom deterministic chunk fallback | zoom_pipeline_run.py:72 |
| K2B-242 | Zoom final report saved via workspace_mw | zoom_pipeline_run.py:149 |
| K2B-249 | READ_BYPASS_CATEGORIES | dispatcher.py:75 |
| K2B-260 | ODIN_ROUTER_MODEL / ODIN_ROUTER_TIMEOUT | semantic_router.py:21 |
| K2B-261 | Router near-miss name tolerance | semantic_router.py:79 |

MFI discrepancies seen while checking (not new capabilities):
- A-066 says the heuristic fallback is Backend→Frontend→DevOps. The code is Fullstack→Mobile→Security→QA→DevOps (projects.py:1178).
- A-089 and A-091 are marked PLANNED, with `plan_main_task()`. main_task.py exists and is built; the mandate fields live in plan_pipeline and mandate_text.
- A-174 and B-197 say "all four" (MD/DOCX). report_all writes 6 files, including PDF.
- D-042 omits the calendar kind, catch-up, run_cmd and run_now.

## 3. Requested-category confirmations

**(a) Project types, intake, team inference, role catalogue, capability dialog, agent creation/strengthening rules: FOUND**
- Types: projects.py:273 PROJECT_TYPES (19 types); :300 recommend_type; :698 custom types.
- Intake: projects.py:1245 intake_step, with its rules at :1257-1318; :1328 _engine_research; :1342 _intake_fallback.
- Team inference: projects.py:463 infer_team, including negation, only-DevOps, no-QA and operational-only.
- Role catalogue: projects.py:21 ALL_MEMBERS, :49 OPERATIONAL_MEMBERS, :346 role_catalog, :452 roles_readiness.
- Capability dialog: projects.py:383 capability_options (3 choices, overlap guard, excluded agents).
- Agent creation/strengthening rules: :351 known_role, :365 classify_team, :373 _suggest_rule, :776 confirmed-agent rules saved, :159 resources_block.

**(b) CTO/agent model and how members are hired: FOUND**
- Project CTO planner: projects.py:1035 plan_pipeline. It keeps a brand-new proposed role so it can be hired on the fly (:1172). The actual hiring (suggest_agent/register) happens in agents_registry/api_v2, outside these files.
- Seeding on create: projects.py:764 (infer_team or explicit members) and :784 (company agents).
- SOC team: projects.py:801 soc_blueprint.provision.
- Choices offered to the owner: capability_options (:383).
- Main Task shared state and mandates: main_task.py:87, :242.

**(c) Scheduler jobs, cadences and approval-gated recurring runs: FOUND**
- Kinds: scheduler.py:121 (once/interval/daily), :85 calendar (default Africa/Cairo).
- Grace and catch-up: :153, :403-416.
- Approval gate: :417 sets pending_approval; :180 approve; :201 skip.
- Execution: :219 _run_task (run_cmd, team run or single agent); :348 run_now with the HubSpot special case; :455 20 s loop; :441 15-min audit sentinel.
- Project cadence and periodic registration: projects.py:703, :816.

**(d) Reporter, report engine and export: FOUND**
- Reporter role: projects.py:62.
- report_engine.py:30/57/105/156: MD/DOCX/PDF/PPTX, branded.
- report_engine.py:184 render and :191 render_to_file.
- The meeting-specific exports are in meeting_api.py:303/:337/:508/:528.

**(e) Zoom/meeting pipeline: FOUND**
- zoom_pipeline_run.py:91 run (7 agents, chunking, analysis, 13-section summary, notifications).
- meeting_api.py: 9 routes (:397-:528), refinement, confidence and language detection (:56-:208).
- projects.py:125 MeetingVoice and :136 project_has_meeting_asset.

**(f) Engine (Claude CLI) controls: FOUND**
- claude_cli.py:47 _model_flags (model selection); :59 _tool_flags and :28 read-only hook; :66/:91 ODIN_CLAUDE_TOOLS; :98 ODIN_CLAUDE_TIMEOUT.
- Stuck/idle detection: :217/:296 ODIN_CLAUDE_IDLE (420 s); :218 heartbeat; :278 ODIN_CLAUDE_MAXWALL no-tool-progress guard.
- :168 strict MCP; :170-189 project cwd/--add-dir; :116 --resume sessions.
- Per-scope models: models_config.py:39 get_model (member→project→main), :54 set_model, :24 CATALOG.
- Cost: there is no spend tracking in these files. The only cost signal is the cost tag ("paid"/"free") in the model catalogue (models_config.py:24-27). run_timer.py measures time only. Spend tracking NOT FOUND.

**(g) Dispatcher, semantic router and approval categories: FOUND**
- dispatcher.py:45 APPROVAL_TRIGGERS (11 categories), :78 ALWAYS_GATE, :75 READ_BYPASS_CATEGORIES, :167 approval_check, :180 route, :242 respond.
- semantic_router.py:53 classify.
- Approval store and severity: approvals.py:28/53/97/119.
- Intent veto and classification: intent.py:18/46.

**(h) Notifications: FOUND**
- notifications_store.py:28-63 (add, list, unread, mark read, clear; cap 300).
- notifications_api.py:9-31 (5 routes).
- Emitters: scheduler.py:238, :285, :319 (started/finished).
- The audit sentinel (scheduler.py:441) delegates its notification to workspace_audit, which is outside these files.


<!-- ==================== PART K3 ==================== -->

# K3 — Capability inventory: Anchor, sync, third-party, auth, voice, integrations

Scope: the K3 file set under /home/claude/v1src. Every file was read in full; anchor_sync.json was read for its structure only.

**Duplicate copies.** The five `.py` files in `workspace/projects/odin-external-arms/deploy/anchor/` (anchor, anchor_remote, anchor_queue, anchor_manage, local_poller_http) are byte-identical to the `server/` copies (checked with `cmp`). `deploy/anchor/store.py` is identical to `server/store.py`. The rows below cite the `server/` line numbers, which are the same in the deploy copies.

**Secrets.** Secret values (API keys, password hash, seed password, session tokens, VM IP) are named only, never copied.

## 1. Capabilities found

| ID | Category | Capability | What it does | Evidence | Triggered by | In MFI? |
|---|---|---|---|---|---|---|
| K3-001 | Structural | Anchor VM deploy bundle | Self-contained copy of the anchor modules plus store.py for the VM (byte-identical to server/) | workspace/projects/odin-external-arms/deploy/anchor/*.py | VM deploy (phase3) | C-025 (shared/infra/anchor listed) |
| K3-002 | Synchronization & Anchor | Anchor request schema | Pydantic AnchorIn {project, prompt, payload, webhook_url, sender} | server/anchor.py:31 AnchorIn | POST /anchor/v1/requests | A-178 |
| K3-003 | Auth & security | Anchor X-API-Key check (in-process) | Must equal ANCHOR_API_KEY from .cred; open when unset | anchor.py:39 _check_key | /requests, /poll, /result | A-150 |
| K3-004 | Synchronization & Anchor | Public request projection | Returns only id, project, status, result, webhook_attempts, acked, error, created, updated, history | anchor.py:49 _public; anchor_remote.py:39 | status/admin reads | A-178 |
| K3-005 | Synchronization & Anchor | POST /anchor/v1/requests (in-process) | Key check; 404 if project unknown; payload defaults to {prompt}; enqueue; fast ack message | anchor.py:58 create_request | third party / app | A-178 / C-025 |
| K3-006 | Synchronization & Anchor | GET /anchor/v1/requests/{rid} | Status + rehydrated result; NO key check on the in-process router | anchor.py:69 request_status | caller polling | A-178 |
| K3-007 | Synchronization & Anchor | POST /requests/{rid}/ack | Explicit ack → acknowledged → finished; no auth | anchor.py:76 acknowledge | third party | A-178 |
| K3-008 | Synchronization & Anchor | GET /anchor/v1/poll | Hands out queued tasks (→ sent_to_local) | anchor.py:81 poll | local machine | A-178 |
| K3-009 | Synchronization & Anchor | POST /requests/{rid}/result | Stores result + delivers webhook | anchor.py:86 submit | local machine | A-178 |
| K3-010 | Synchronization & Anchor | Admin config GET/POST (in-process) | retry_count / retry_interval_sec / poll_limit; NO auth on the in-process router | anchor.py:92 get_cfg, :96 set_cfg | admin / dashboard | A-177 / C-026 |
| K3-011 | Synchronization & Anchor | Admin requests + counts | List (optional ?status filter) and per-status counts | anchor.py:100 admin_requests, :104 admin_counts | admin | C-026 |
| K3-012 | Per-project features & integrations | Connector-facts grounding | Routes by project type or prompt keywords to Klaviyo flows_summary or Veeqo orders over the last 7 days (read-only) | anchor.py:112 _connector_facts | process() | A-180 |
| K3-013 | Synchronization & Anchor | LLM-free fact formatter | Formats Veeqo / Klaviyo live data as text (raw capped at 700–800 chars) | anchor.py:134 _format_facts | fast path | no |
| K3-014 | Orchestration core | Deliverable extractor with noise filter | Uses the newest member deliverable, else the last substantive pool reply; skips CTO plan/review lines and telemetry breadcrumbs | anchor.py:163 _last_answer | Tier-3 orchestration | no |
| K3-015 | Synchronization & Anchor | Tier 1 fast read-only answer | When connector facts exist and have no error, answers in seconds without the engine; ODIN_ANCHOR_FAST=0 disables | anchor.py:224 process | poller | no |
| K3-016 | Synchronization & Anchor | Heavy-verb classifier | payload.orchestrate or build/deploy/fix/continue… verbs send the request to the full CTO→team run | anchor.py:239 process (heavy) | process() | no |
| K3-017 | Safety & approvals | External scope/privacy guard | Prefixes the shared workspace_mw.scope_answer_guard(external=True), with a hard-coded fallback text | anchor.py:247-252 | process() | A-095 |
| K3-018 | Synchronization & Anchor | Tier 2 single grounded engine call | One read-only Claude engine stream, hard-capped at 90 s; ODIN_ANCHOR_SINGLE=0 disables | anchor.py:253 process | non-heavy requests | no |
| K3-019 | Orchestration core | Tier 3 full CTO→team run | api_v2.start_run, then polls run_status every 2 s (300 s timeout) | anchor.py:274 process | heavy requests | A-180 |
| K3-020 | Synchronization & Anchor | In-process local poller loop | Daemon every 5 s: next_pending → mark_processing → process → submit_result, then retry_due | anchor.py:296 start_local_poller | app.py startup | C-025 |
| K3-021 | Testing | ODIN_ANCHOR_NO_POLLER flag | Disables the in-process poller for deterministic HTTP-contract tests | anchor.py:302 | env | no |
| K3-022 | Synchronization & Anchor | Pluggable queue storage | Postgres when ANCHOR_PG_DSN is reachable, else a JSON fallback; chosen at import | anchor_queue.py:82 _pg_init, :449 | import | A-192 |
| K3-023 | Synchronization & Anchor | anchor_requests table | Creates the table (id, status, created, data jsonb) with status and created indexes | anchor_queue.py:92-95 | _pg_init | A-192 |
| K3-024 | Synchronization & Anchor | JSON queue cap | JSON fallback keeps only the last 2000 rows | anchor_queue.py:118 _json_save | every write | no |
| K3-025 | Synchronization & Anchor | Backend-agnostic row primitives | all / get / put (upsert) / by_status / counts / delete / delete_all | anchor_queue.py:123-233 | lifecycle functions | A-192 |
| K3-026 | Synchronization & Anchor | Big-result file offload | Results over 32,000 chars go to anchor-layer/active_requests/<rid>/<random>.json; the row stores a pointer; inline if the write fails | anchor_queue.py:33, :237 _offload | _update(result) | A-192 |
| K3-027 | Synchronization & Anchor | Result rehydrate / file cleanup | Resolves {__file__} pointers on read; removes a request's files on delete | anchor_queue.py:265 _rehydrate, :275 _remove_files | get / list / remove | A-192 |
| K3-028 | Synchronization & Anchor | Status lifecycle constants | received, queued, sent_to_local, received_by_local, processing, processed, response_received, webhook_sent, ack_pending, acknowledged, finished, failed, cancelled. received_by_local, processed and _PICKABLE are defined but never used | anchor_queue.py:37-52 | lifecycle | A-176 |
| K3-029 | Synchronization & Anchor | Terminal-state set | acknowledged / finished / failed / cancelled are never re-delivered or overwritten | anchor_queue.py:52 _TERMINAL | submit / deliver | A-176 |
| K3-030 | Synchronization & Anchor | Queue config defaults | retry_count 4, retry_interval_sec 600, poll_limit 5; set_cfg whitelists keys and casts to int | anchor_queue.py:54, :58 cfg, :63 set_cfg | admin config | A-177 |
| K3-031 | Synchronization & Anchor | Status history trail | Every status change is appended to history with a timestamp; updated stamp refreshed | anchor_queue.py:299 _update | all transitions | A-176 |
| K3-032 | Synchronization & Anchor | Enqueue | id req_+16 hex; history received→queued; api_key_id field always empty | anchor_queue.py:314 enqueue | POST /requests | A-175 |
| K3-033 | Synchronization & Anchor | Hand-out (no prioritisation) | FIFO by created; queued → sent_to_local; up to poll_limit; no priority field anywhere | anchor_queue.py:327 next_pending | /poll | A-176 |
| K3-034 | Synchronization & Anchor | mark_processing | Sets processing (in-process poller only; the HTTP poller never sets it) | anchor_queue.py:340 | anchor.py loop | A-176 |
| K3-035 | Synchronization & Anchor | Idempotent result submit | Unknown id → error; terminal → {already}; else response_received, then webhook | anchor_queue.py:344 submit_result | /result | A-178 |
| K3-036 | Synchronization & Anchor | Webhook POST | JSON POST, 20 s timeout; 2xx = ack | anchor_queue.py:354 _post | deliver_webhook | A-179 |
| K3-037 | Synchronization & Anchor | Webhook delivery + retry state machine | No URL → finished; attempt → webhook_sent; 2xx → acknowledged → finished; attempts ≥ retry_count → failed with error; else ack_pending with next_retry_at | anchor_queue.py:367 deliver_webhook | submit / retry | A-179 / A-177 |
| K3-038 | Synchronization & Anchor | Manual ack | Marks acked → acknowledged → finished | anchor_queue.py:392 ack | /ack | A-178 |
| K3-039 | Scheduling & notifications | Retry sweep | Re-delivers ack_pending rows whose next_retry_at has passed | anchor_queue.py:401 retry_due | pollers / _retry_sweep | A-177 |
| K3-040 | Synchronization & Anchor | List requests / counts | Newest first, limit 200, rehydrated; per-status counts | anchor_queue.py:412, :420 | admin / manage | C-026 |
| K3-041 | Synchronization & Anchor | Cancel | Sets cancelled; no route calls it (unreachable) | anchor_queue.py:424 cancel | none | A-176 |
| K3-042 | Synchronization & Anchor | Hard delete / clear all | remove() deletes the row and its files; clear_all wipes the table and active_requests. This contradicts MFI "delete = status flag" | anchor_queue.py:428 remove, :436 clear_all | Manage UI | A-154 |
| K3-043 | Auth & security | Manage owner credentials | Defaults to owner email + SHA-256 hash in source (value not copied); overridable via ANCHOR_MANAGE_EMAIL / ANCHOR_MANAGE_PWSHA; the hash is unsalted | anchor_manage.py:26-27, :37 _creds | login | A-154 |
| K3-044 | Auth & security | Manage TTLs | Confirmation code 10 min, session 7 days, remembered device 30 days | anchor_manage.py:29-31 | login / session checks | A-143 / A-154 |
| K3-045 | Auth & security | Web/mobile allow-stop toggles | allow_mobile / allow_web settings; client_allowed() | anchor_manage.py:60 settings, :64 set_settings, :74 client_allowed | Manage UI / _client_blocked | A-154 |
| K3-046 | Auth & security | Per-target confirmation code | Targets web / mobile / manage / anchor; new random 6-digit code on every request | anchor_manage.py:86 _norm_target, :91 request_code | POST manage/request-code | A-154 |
| K3-047 | Auth & security | Desktop pending-code read | Live codes per target (or all targets) plus back-compat single fields for the desktop badge | anchor_manage.py:102 _live_code, :106 pending_code | GET manage/pending-code (desktop) | A-124 |
| K3-048 | Auth & security | Remembered device check | Device id valid for 30 days → skip the code | anchor_manage.py:126 check_device | manage page init | A-154 |
| K3-049 | Auth & security | Manage/web/mobile login (2-factor via desktop code) | Email + password hash + one-time per-target code (skipped on a remembered device); issues a session token; optionally remembers the device | anchor_manage.py:132 login | POST manage/login | A-154 |
| K3-050 | Auth & security | Session validate / logout | 7-day session check; logout pops the token | anchor_manage.py:156, :161 | all gated routes | A-154 / A-143 |
| K3-051 | Synchronization & Anchor | Remote anchor stand-in / deployed anchor | ThreadingHTTPServer serving /anchor/v1 with no local processor; CLI --host 0.0.0.0 --port 9100 | anchor_remote.py:227 Handler, :571 serve, :578 | CLI / systemd | A-181 / D-024 |
| K3-052 | Auth & security | Remote API-key check | X-API-Key must equal ANCHOR_API_KEY; open when unset | anchor_remote.py:31 _want_key, :260 _auth_ok | most routes | A-150 |
| K3-053 | Synchronization & Anchor | Durable sync store | SYNC {projects, agents, pools, mirror, updated} loaded with defensive shape checks at startup; persisted to anchor_sync.json on every push | anchor_remote.py:54-80 _load_sync, _persist_sync | startup / POST /sync | A-183 |
| K3-054 | Build, packaging, run & clients | Anchor landing page | HTML "ONLINE" card with projects synced, last-sync age, per-status pills and a Manage button; a browser Accept header gets HTML, otherwise JSON health | anchor_remote.py:83 _landing_html, :100, :326 | GET / | A-187 |
| K3-055 | Build, packaging, run & clients | Manage owner UI | Login card (email / password / code / remember), resend code, requests table with delete, Clear all, mobile/web toggles, sign out; proxy-aware base; token + device id kept in localStorage | anchor_remote.py:132 _MANAGE_TMPL, :184-223 | GET /manage | A-154 |
| K3-056 | Auth & security | CORS on the remote anchor | Allows any origin; headers Content-Type, X-API-Key, X-Manage-Token, X-Odin-Client | anchor_remote.py:231 _send | every response | no |
| K3-057 | Safety & approvals | Crash-proof request wrappers | Any route exception returns a clean 500 and the server keeps serving (fix for the 502 loop) | anchor_remote.py:274-299 do_GET / do_POST / do_DELETE | every request | no |
| K3-058 | Auth & security | Web/mobile client gate | X-Odin-Client web/mobile: 403 if stopped in Manage, 401 if no valid manage session; third parties (no header) are not affected | anchor_remote.py:305 _client, :308 _client_blocked | /projects, /mirror, /pool, POST /requests | A-143 (partial) |
| K3-059 | Synchronization & Anchor | URL-decoded path segments | unquote so that chat:<id> / project:<id> scopes match | anchor_remote.py:325, :448, :544 | routing | no |
| K3-060 | Build, packaging, run & clients | Health endpoints | / /health /healthz JSON with auth_required and an endpoint list; /anchor/v1/_status | anchor_remote.py:331, :344 | probes | A-178 / C-023 |
| K3-061 | Auth & security | GET manage/pending-code | Desktop reads codes with the anchor key | anchor_remote.py:350 | desktop poll | A-124 |
| K3-062 | Auth & security | GET manage/me | Says whether a saved session is still valid | anchor_remote.py:354 | web / mobile / manage | no |
| K3-063 | Synchronization & Anchor | GET manage/requests + manage/settings | Session-gated full request list with counts; settings read | anchor_remote.py:358, :360 | Manage UI | A-154 |
| K3-064 | Synchronization & Anchor | GET /anchor/v1/projects (mirror) | Mirrored projects + agents + updated + age_seconds; stale when there was no push or the last one is over 90 s old | anchor_remote.py:365-379 | web / mobile / request page | A-183 / A-184 |
| K3-065 | Synchronization & Anchor | GET /anchor/v1/mirror/{key} | Returns the brain's raw JSON for a mirrored key | anchor_remote.py:380 | web / mobile | A-184 |
| K3-066 | Synchronization & Anchor | GET /anchor/v1/pool/{pid} paginated | Newest-last lazy scroll-up window (offset/limit, default 30), has_more, max_seq | anchor_remote.py:386-415 | web / mobile chat | A-184 |
| K3-067 | Synchronization & Anchor | Delta sync by sequence | ?since=<seq> returns only messages with seq > since, plus max_seq and total | anchor_remote.py:400-410 | web / mobile live pull | F4 (paper row) / A-137 |
| K3-068 | Synchronization & Anchor | Remote poll + status + admin reads | /poll, /requests/{id}, admin/requests, counts, config, all key-gated | anchor_remote.py:417-442 | poller / third party | A-178 / C-026 |
| K3-069 | Auth & security | Manage public code/device/login routes | request-code (public on purpose), check-device, login | anchor_remote.py:457-466 | Manage page | A-154 |
| K3-070 | Synchronization & Anchor | Manage session routes | logout, settings write, requests/clear; DELETE manage/requests/{id} | anchor_remote.py:470-476, :547 | Manage UI | A-154 |
| K3-071 | Synchronization & Anchor | Remote intake with chat/command bypass | Key required (contradicts the docstring, which says intake is open); client gate; sender chat/command skips the project-existence check | anchor_remote.py:480-501 | third party / web / mobile | A-178 / A-137 |
| K3-072 | Synchronization & Anchor | POST /anchor/v1/sync merge push | Key-gated; projects/agents replaced; pools and mirror merged per key; updated stamped; persisted | anchor_remote.py:504-525 | local poller | A-183 |
| K3-073 | Synchronization & Anchor | Remote ack / result / admin config write | /ack has no auth; /result and admin/config are key-gated | anchor_remote.py:527-538 | third party / poller | A-178 / A-177 |
| K3-074 | Scheduling & notifications | Remote webhook retry sweep | Daemon calls retry_due every 30 s | anchor_remote.py:554 _retry_sweep | serve() | A-181 |
| K3-075 | Synchronization & Anchor | HTTP poller transport | urllib JSON with X-API-Key; accepts a self-signed HTTPS cert (CERT_NONE); 60 s timeout | local_poller_http.py:26 _key, :34 _req | poll / sync | D-023 |
| K3-076 | Synchronization & Anchor | poll_once dispatcher | sender=command → _run_command; sender=chat → brain chat stream; else anchor.process; posts the result; never sets the processing status | local_poller_http.py:54 poll_once | run loop | A-182 |
| K3-077 | Synchronization & Anchor | Immediate mirror push after chat/command | sync_push right away so other surfaces update | local_poller_http.py:92-96 | poll_once | A-137 |
| K3-078 | Synchronization & Anchor | Brain HTTP helpers | GET / POST / DELETE to the local brain (ODIN_BRAIN, default localhost:8000) | local_poller_http.py:100, :110, :265 | commands / sync | no |
| K3-079 | Synchronization & Anchor | Command create_project | Creates a project via brain POST /projects (mode build, cadence once, autoApprove True) | local_poller_http.py:123 | web / mobile command | no |
| K3-080 | Synchronization & Anchor | Commands create_chat / rename_chat / delete_chat | Standalone chat CRUD on the brain; create returns the new scope | local_poller_http.py:131, :138, :146 | web / mobile command | no |
| K3-081 | Synchronization & Anchor | Command clear_scope | Deletes every chat in a scope | local_poller_http.py:153 | web / mobile command | no |
| K3-082 | Synchronization & Anchor | Command run_now | Triggers brain /projects/{pid}/run-now with prompt + cid | local_poller_http.py:165 | web / mobile command | no |
| K3-083 | Synchronization & Anchor | Command mark_notif | Marks one or all notifications read on the brain | local_poller_http.py:174 | web / mobile | no |
| K3-084 | Synchronization & Anchor | Command post_message (rich, idempotent) | Reply / attachment / voice / forward posts with client_msg_id to /scope/message | local_poller_http.py:181 | web / mobile | A-137 |
| K3-085 | Synchronization & Anchor | Command delete_message | Propagates the delete to the brain; the mirror removes it everywhere | local_poller_http.py:197 | web / mobile | A-137 |
| K3-086 | Voice | Command meeting_report | Phone-transcribed chunk texts → brain /meeting/finish_text bilingual report | local_poller_http.py:208 | mobile live meeting | A-173 (partial) |
| K3-087 | Synchronization & Anchor | Ensure scope chat | Uses the first chat of a scope or creates "App chat" | local_poller_http.py:222 | chat / post_message | no |
| K3-088 | Synchronization & Anchor | Chat via the brain's /scope/stream | Same path as the desktop: drains the SSE (90 s cap), reads back the last assistant message | local_poller_http.py:235 _brain_chat_stream | sender=chat | A-137 |
| K3-089 | Synchronization & Anchor | sync_push mirror | Pushes projects, pools (company + every project + every standalone chat), agents (active / tasks / health) and 13 mirror keys (roles, company_agents, all_agents, connectors, activity, hubspot, notifications, ui_projects, ui_agents, ui_types, ui_connectors, chats). No "audit" key, though MFI A-104 says one is mirrored | local_poller_http.py:276-347 | run loop / after chat | A-182 / A-184 |
| K3-090 | Synchronization & Anchor | Pool cap of 60 messages per push | Prevents a sync body over size (HTTP 413) from killing the whole sync | local_poller_http.py:300-303 | sync_push | no |
| K3-091 | Synchronization & Anchor | Poller main loop + CLI | poll_once then sync_push every --interval (default 5 s); --anchor base URL | local_poller_http.py:350 run, :364 | CLI / supervisor / Electron | A-182 |
| K3-092 | Orchestration core | Scope hierarchy | company → project:<pid> → member:<pid>:<agent>; parent_of / ancestors | scopes.py:28, :39 | all scope ops | A-064 |
| K3-093 | Structural | Scope path encoding + meta | ":"→"__" folder names; meta.json with summary + feed | scopes.py:24 _safe, :55 _meta | scope ops | A-064 |
| K3-094 | Orchestration core | Scope chats list/create/get | Skips deleted chats; sorted by mtime; reuses an empty "New chat" | scopes.py:68, :84, :96 | /scope/chats | C-016 |
| K3-095 | Synchronization & Anchor | Whole-pool merge ordered by seq | All chats of a scope merged and sorted by (seq, ts) | scopes.py:100 all_messages | /scope/messages, sync_push | A-136 |
| K3-096 | Synchronization & Anchor | Per-scope monotonic sequence numbers | Backend-assigned seq in _seq_counters.json; detects gaps | scopes.py:117 _next_seq | add_message | F4 (paper row) |
| K3-097 | Synchronization & Anchor | add_message rich + idempotent | kind / attachment / reply_to / sender fields; a duplicate client_msg_id returns the existing message | scopes.py:129-166 | /scope/message, chat streams | A-135 (idempotency: no) |
| K3-098 | Orchestration core | Auto chat title | First user message (40 chars) becomes the chat title | scopes.py:160 | add_message | no |
| K3-099 | Synchronization & Anchor | Upward sync feed | A user message appends an event to every ancestor's feed (capped at 200) | scopes.py:164, :280 sync_up | add_message, hubspot _report | A-064 |
| K3-100 | Per-project features & integrations | Attachment store + kind detection | Files saved under scope_files; image / audio / zip / file by extension | scopes.py:169 save_attachment | /scope/upload | A-135 |
| K3-101 | Voice | Voice-note auto-transcription | Audio uploads transcribed with faster-whisper base (or whisper); returns "" on failure | scopes.py:188, :196 transcribe | save_attachment | A-135 |
| K3-102 | Orchestration core | Attachment path / delete message / session / rename / soft delete chat | attachment_path; delete_message; engine session id per chat; rename; tombstone delete | scopes.py:222, :230, :244, :251, :260 | /scope/* routes | C-016 |
| K3-103 | Orchestration core | Summaries + drill-down | get / set summary; children_of from agents_registry; read_child_chats | scopes.py:289, :293, :301, :313 | /scope/summary, /scope/children | A-064 |
| K3-104 | Build, packaging, run & clients | UI contract data source | Reads odin_core over psycopg2 plus type / agent-type / feature JSON definitions | ui_api.py:20 _db, :25-51 | /ui/* | C-031 / C-050 |
| K3-105 | Build, packaging, run & clients | Project cards | Per project: counts (agents / connectors / files), connectors, features, ui {chip, controls, icons} | ui_api.py:54 project_cards | /ui/projects | C-031 |
| K3-106 | Build, packaging, run & clients | Cadence-driven run controls | recurring → play + cadence; periodical → play + period; once → run-once, when the type gives no run control | ui_api.py:73-81 | project_cards | B-049 |
| K3-107 | Build, packaging, run & clients | Agent-driven controls/icons | A report/export agent adds an export button; a voice agent adds the streaming-voice icon; agent cards get voice/export controls | ui_api.py:82-86, :119-124 | /ui/projects, /ui/agents | B-049 |
| K3-108 | Build, packaging, run & clients | Agent roster / type catalog / connector badges | agent_cards, type_catalog, connector_cards with live connected status (which claude / az, capabilities, default True) | ui_api.py:107, :134, :151 _connector_connected, :169 | /ui/agents, /ui/types, /ui/connectors | C-031 (_connector_connected: no) |
| K3-109 | Build, packaging, run & clients | /ui routes | /projects and /agents with offset/limit, /project/{pid}, /types, /connectors. _features_of is defined but unused | ui_api.py:187-215; :46 | clients + mirror | C-031 |
| K3-110 | Auth & security | External API key | X-API-Key = ODIN_API_KEY; open when unset | external_api.py:28, :36 | /api/v1 | A-150 |
| K3-111 | Per-project features & integrations | External API health + projects | /api/v1/health; projects list (description capped at 200) | external_api.py:45, :49 | external callers / app | C-024 / A-194 |
| K3-112 | Per-project features & integrations | Per-project ask | Context = brief (1500) + main_task pool (4000) → dispatcher.respond | external_api.py:57 ask | POST /api/v1/p/{id}/ask | A-131 |
| K3-113 | Testing | Webhook receiver callback | POST /cb[/<pid>] records (path pid wins) and replies 200 = ack; in-memory list | webhook_receiver.py:21, :57 do_POST | anchor webhook | A-198 |
| K3-114 | Testing | Webhook list + viewer | /list, /list/<pid>, ?project=; HTML viewer auto-refreshes every 3 s with an "Acknowledge again" button that calls the anchor ack | webhook_receiver.py:37, :78-103 | browser / request page | A-198 |
| K3-115 | Testing | Webhook receiver CLI | Serves on 0.0.0.0:--port (default 9300) | webhook_receiver.py:106 | CLI | D-034 |
| K3-116 | Testing | Request-page SQLite log | Table reqs (rid, project, prompt, webhook, status, anchor_id, response_path); no WAL; ALTER migration | sim_server.py:48 _init | import | A-196 |
| K3-117 | Testing | Response-as-file store | Each response saved to sim_responses/<rid>.json; the row keeps the path | sim_server.py:71, :106 upsert | PUT /sim/requests | A-196 |
| K3-118 | Testing | Sim CRUD routes | GET/POST /sim/requests, PUT/DELETE /sim/requests/<rid>, GET /sim/response/<rid>, DELETE /sim/requests clears all | sim_server.py:200-235; :82, :91, :136, :152 | anchor_sim.html | A-196 / A-197 |
| K3-119 | Testing | Self-healing static/seed serving | Serves from DATA, else falls back to the repo root (fixes the seed 404); path-traversal guard | sim_server.py:237-263 _static | page assets | A-199 |
| K3-120 | Testing | Sim server config/CLI | ODIN_SIM_DATA (default workspace/anchor-layer); 127.0.0.1:9104 | sim_server.py:34, :266 | CLI | D-035 |
| K3-121 | Testing | CLI third party | POST with sender third-party-cli and an empty webhook; polls every 3 s ×200; prints status changes + result | third_party.py:38 main, :27 call | CLI | A-195 / D-036 |
| K3-122 | Auth & security | Web/Flutter auth store | PBKDF2-SHA256 (120k) hash in oth/.auth; seed account created on first run (seed password hard-coded in source, not copied) | auth.py:55 _hash, :59 _load_auth, :38-39 | router build | A-143 |
| K3-123 | Auth & security | Auth config flags | require_login_web / mobile, twofa_enabled, verify_email_enabled, faceid_first_access, desktop_open, email_verified. POST /auth/config is unauthenticated | auth.py:41, :126, :130 | GET/POST /auth/config | A-149 |
| K3-124 | Auth & security | Login with 2FA branch | Wrong credentials → 401; when 2FA is on returns twofa_required, else a token | auth.py:139 login | POST /auth/login | C-001 |
| K3-125 | Auth & security | 2FA code check | Fixed dev code (value not copied); issues a token straight away when 2FA is off | auth.py:52, :149 twofa | POST /auth/2fa | A-144 |
| K3-126 | Auth & security | In-memory tokens / me / logout | tok_ tokens in a process dict (no expiry, lost on restart) | auth.py:51, :91, :158, :165 | /auth/me, /auth/logout | C-001 (no-expiry: no) |
| K3-127 | Auth & security | Change password | Checks the old password (not the email); new password at least 6 chars; re-salts | auth.py:170 | POST /auth/change-password | A-143 |
| K3-128 | Auth & security | Forgot / verify-email stubs | forgot returns a message only; verify/send echoes the dev code; verify/confirm sets email_verified | auth.py:182, :186, :190 | /auth/forgot, /auth/verify/* | A-146 / A-145 |
| K3-129 | Structural | Brain app bootstrap | sys.path (voice / orchestrator / server); FastAPI v0.4.0 | app.py:31-35 | uvicorn | D-010 |
| K3-130 | Auth & security | Brain CORS allow-all | allow_origins * | app.py:38-46 | every request | no |
| K3-131 | Auth & security | ODIN_ACCESS_TOKEN gate | /chat*, /dispatch, /voice need X-Odin-Token or ?token= (the /chat prefix also covers /chats) | app.py:52 access_token_gate | middleware | A-151 |
| K3-132 | Structural | Sub-router mounts with _status fallbacks | voice, v2, soc, notifications, meeting, auth, api/v1, anchor (+ starts the poller), hubspot, directions, audit, ui | app.py:66-188 | startup | C-023 |
| K3-133 | Per-project features & integrations | Auto-register connectors | Adds Klaviyo / Veeqo / HubSpot / EasyPost connectors when their keys are in .cred and the connector is missing | app.py:139-152 | startup | no |
| K3-134 | Orchestration core | Brain selector | ODIN_USE_DISPATCHER=1 (default) dispatcher, else raw Ollama handler | app.py:197 _brain | /chat | no |
| K3-135 | Orchestration core | Legacy /chat, /dispatch, /chat/stream SSE | Status icons, approval-gate notice, token chunking for the typing effect | app.py:207, :213, :220 | dashboard / cockpit | C-021 |
| K3-136 | Orchestration core | Legacy /chats CRUD + /chats/{cid}/stream | Persistent chats; resumes the Claude CLI session; live tool status; Ollama/dispatcher fallback | app.py:267-373 | dashboard | C-021 / A-006 |
| K3-137 | Per-project features & integrations | Infra probes | /infra/ip, /infra/reachable, /infra/connect-test (read-only) | app.py:377-396 | dashboard / desktop | C-022 |
| K3-138 | Voice | TTS/STT pre-warm | When USE_VOICE=1, loads XTTS, Kokoro and fast Whisper in a background thread | app.py:399 _prewarm_voice | startup | A-162 |
| K3-139 | Scheduling & notifications | Scheduler start | scheduler.start_background at startup | app.py:429 | startup | C-020 |
| K3-140 | Build, packaging, run & clients | Brain /health + static mounts | Reports the active engine (ODIN_ENGINE), voice_enabled, Ollama model; serves /state, /history and the dashboard | app.py:439, :459-461 | probes / browser | C-023 / A-112 |
| K3-141 | Per-project features & integrations | HubSpot run overview | Connection + real counts, then a notification + upward feed event | hubspot_api.py:26 _notify, :34 _report, :42 run_overview | POST /hubspot/run, scheduler ▶ | C-041 |
| K3-142 | Per-project features & integrations | HubSpot query mapper | Keywords → this-month / companies / deals / contacts counts; out of scope → guidance (never fabricates) | hubspot_api.py:63 _answer_query | POST /hubspot/ask | C-041 |
| K3-143 | Per-project features & integrations | HubSpot routes | status, overview (mirrored), scopes + how-to-add, run, ask | hubspot_api.py:105-134 | desktop / mirror | C-041 |
| K3-144 | Auth & security | Credential reader | Parses .cred in both KEY=value and key: value formats | integrations/cred.py:15 load, :34 get | all integrations | A-152 |
| K3-145 | Safety & approvals | EasyPost tracking-only gate | GET only on trackers/shipments/addresses/parcels/users; POST allowed only for /trackers; off-base URLs rejected. The call() docstring says "GET only", which contradicts the code. _allowed_path is unused | integrations/easypost.py:31, :52, :58-80 call | integration calls | B-159 |
| K3-146 | Per-project features & integrations | EasyPost key + Basic auth + wrappers | Key order production → plain → test; Basic key:""; trackers / shipments / user; create_tracker | easypost.py:34 _key, :46, :104-115 | callers | B-158 |
| K3-147 | Per-project features & integrations | HubSpot client scope-aware | Bearer token; granted scopes + capability requirements from hubspot_scopes.json; scope_guidance text | integrations/hubspot.py:29, :37-64 | hubspot_api | C-041 |
| K3-148 | Per-project features & integrations | HubSpot analytics | call; account; object_count via search total; contacts_this_month (UTC month start); connection_check; account_overview | hubspot.py:68, :94, :99, :117, :126, :137 | hubspot_api | C-041 (contacts_this_month: no) |
| K3-149 | Safety & approvals | Klaviyo read-only gate | call() is GET-only and rejects a body; create_campaign is disabled | integrations/klaviyo.py:30, :69 | callers | A-207 / A-210 |
| K3-150 | Per-project features & integrations | Klaviyo wrappers + flows_summary | lists / campaigns (email filter) / profiles / metrics / accounts; flows counted by status; config defaults (revision 2025-01-15) | klaviyo.py:19 _cfg, :66-73, :121 | anchor facts | A-207 |
| K3-151 | Per-project features & integrations | Klaviyo metric aggregates | The one allowed reporting POST (/metric-aggregates) | klaviyo.py:76 metric_aggregates | callers | no |
| K3-152 | Safety & approvals | Veeqo read-only gate | GET only, no body, endpoint whitelist (orders / shipments / carriers / current_user), off-base reject; create_shipment disabled (MFI A-208 lists it as a wrapper) | integrations/veeqo.py:27, :38, :44, :95 | callers | A-208 / A-210 |
| K3-153 | Per-project features & integrations | Veeqo wrappers + orders_summary | orders / order / shipments / carriers / user; order count since a date (page_size 100) | veeqo.py:89-94, :99 | anchor facts | A-208 |
| K3-154 | Middleware & DB registry | Shared JSON store (anchor copy) | _REMAP sends anchor files to workspace/anchor-layer; sharded per-project stores; atomic tmp+replace writes; best-effort workspace_mw.sync_row lockstep | deploy/anchor/store.py:21, :43, :71, :153, :166 | anchor modules | C-044 |
| K3-155 | Voice | Whisper STT (accurate) | faster-whisper medium, int8 on CPU (ODIN_WHISPER_MODEL) | voice_service.py:39 _load_whisper | /voice/stt | A-157 |
| K3-156 | Voice | Whisper fast model for partials | base model (ODIN_WHISPER_FAST_MODEL), greedy beam 1 | voice_service.py:61 | /voice/stt?fast=1, prewarm | A-164 |
| K3-157 | Voice | transcribe EN/AR auto-detect | language auto/None; VAD filter; temperature 0; returns lang + lang_prob | voice_service.py:73 | /voice/stt | A-157 |
| K3-158 | Voice | TTS routing EN/AR | Arabic → Coqui XTTS (speed default 1.15, ODIN_XTTS_SPEED); English → Kokoro af_heart. The docstring says Azure Egyptian, which contradicts the code | voice_service.py:93 synthesize | /voice/tts | A-158 / A-159 / A-161 |
| K3-159 | Voice | Piper / macOS Maged Arabic (dead code) | _synthesize_arabic and _piper_synthesize are never called | voice_service.py:107, :143 | none | A-160 |
| K3-160 | Voice | Voice router | POST /voice/stt (upload saved as temp .webm; language, fast); GET /voice/tts (text 1–4000, speed 0.5–2.0) → WAV; both return 503 unless USE_VOICE=1 | voice_service.py:158-191 | clients | A-156 |
| K3-161 | Voice | Kokoro English TTS | Lazy KPipeline lang 'a'; robust to Kokoro versions; 24 kHz WAV | voice/backend/tts.py:32 _load, :55 synthesize | voice_service | A-158 |
| K3-162 | Voice | Coqui XTTS-v2 Arabic TTS | Auto-accepts the license (COQUI_TOS_AGREED); speaker / model / speed env settings; surfaces the real import error | voice/backend/coqui_tts.py:25, :45 | voice_service | A-159 |
| K3-163 | Voice | MMS-TTS EN/AR (not wired) | VITS facebook/mms-tts-eng / ara with uroman romanisation; nothing imports it | voice/backend/neural_tts.py:19, :24, :40, :54 | none | A-160 |
| K3-164 | Voice | Azure Neural ar-EG TTS (not wired) | SSML REST call with AZURE_SPEECH_KEY / REGION; Salma voice by default; nothing imports it | voice/backend/azure_tts.py:21, :25 | none | A-160 |
| K3-165 | Voice | React useVoice hook | Local record → /voice/stt; optional browser SpeechRecognition (ar-EG / en-US); speak via /voice/tts, falling back to browser SpeechSynthesis; stopSpeaking | voice/frontend/useVoice.ts:28, :64, :88, :95, :122 | React UI | A-168 |
| K3-166 | Build, packaging, run & clients | Voice requirements file | Lists faster-whisper + MMS deps and says "Kokoro dropped", yet the code uses Kokoro + coqui-tts, which are not listed | voice/backend/requirements-voice.txt:11-21 | pip install | A-156 (mismatch: no) |
| K3-167 | Build, packaging, run & clients | Production client config | window.ODIN_PROD {brain:"", anchor, wh, key}; brain URL deliberately empty; a live key is embedded (not copied) | anchor_prod.js:2-8 | anchor_sim.html | D-039 |
| K3-168 | Build, packaging, run & clients | Seed configs | window.ODIN_SEED {key, webhook}: root copy points the webhook at local :9300, anchor-layer copy at the online anchor; both embed the key | anchor_seed.js:1; workspace/anchor-layer/anchor_seed.js:1 | request page | D-040 / A-199 |
| K3-169 | Build, packaging, run & clients | anchor-layer index redirect | Meta refresh to anchor_sim.html | workspace/anchor-layer/index.html:3 | GET :9104/ | no |
| K3-170 | Testing | Request page env selector | Dev (localhost 8000/9100/9300) vs Prod (ODIN_PROD); ?env= override; defaults to Prod when ODIN_PROD exists | anchor_sim.html:54, :150-154, :343-350 | page load | D-039 |
| K3-171 | Testing | Seeded projects + prompts | Loads anchor_env.json seeded_prompts; lists projects from the anchor (not the backend); per-project webhook /cb/<pid>; one-click seeded send; key prefilled from ODIN_SEED | anchor_sim.html:121, :165-198 | page load / click | A-199 / A-196 |
| K3-172 | Testing | Send with immediate card + offline detection | The card is created before the network call; network error → "offline · not received", else "rejected" | anchor_sim.html:200-235 | Send | A-196 |
| K3-173 | Testing | Live CD-flow chain | 7-step visual (sent → queued → pulled → processing → result → webhook → done). paintStatus maps handed_out / done / completed, which the queue never emits, so the chain under-reports | anchor_sim.html:85-94, :156-162, :238 | polling | A-196 (status mismatch: no) |
| K3-174 | Testing | Result capture | Checks the webhook /list/<project> for its own request_id; else uses the anchor result directly (online flow, ack_pending); polls every 2.5 s | anchor_sim.html:248-281 | after send | A-196 |
| K3-175 | Testing | Durable request log client | simRecord / simUpdate / simDelete; remove card; Clear all; refresh statuses by anchor id; restore on load | anchor_sim.html:288-337 | page load / buttons | A-196 / A-197 |
| K3-176 | Build, packaging, run & clients | Hide/show env variables | Toggles the config panel | anchor_sim.html:142 toggleVars | button | no |
| K3-177 | Testing | Legacy third-party HTML sim | Sends with sender third-party-sim and no webhook; polls every 3 s ×200. Line 35 hard-codes an anchor API key (not copied; the MFI security note lists only anchor_prod.js / anchor_seed.js) | third_party_sim.html:35, :57-92 | browser | A-195 |
| K3-178 | Synchronization & Anchor | Anchor environments SSOT | dev / prod endpoints, VM local ports (behind nginx), seeded prompts, contract links; contains the VM IP (not copied) | workspace/anchor-layer/anchor_env.json:4-41 | sim page / desktop / app | no (MFI D §3 text only) |
| K3-179 | Synchronization & Anchor | Queue config / manage / queue state files | anchor_config.json = defaults; anchor_manage.json holds a legacy pending_code field plus pending_codes (web / mobile), sessions and devices; anchor_queue.json has 8 finished sender=odin_app rows whose history has no "processing" | workspace/anchor-layer/anchor_config.json, anchor_manage.json, anchor_queue.json | runtime | A-175 / A-177 |
| K3-180 | Synchronization & Anchor | Mirror snapshot shape | Keys projects (11), agents {active, tasks, health}, pools (69: 49 project:, 15 chat:, company, 4 legacy bare-pid keys), mirror (13 keys incl. legacy hubspot_status no longer pushed), updated; messages carry seq | workspace/anchor-layer/anchor_sync.json | /sync, startup | A-183 |
| K3-181 | Synchronization & Anchor | Cross-surface live sync (web / mobile / desktop) | Desktop brain = source of truth; poller pushes to the anchor; web/mobile read the anchor and write via chat/command requests | anchor_remote.py:44-57; local_poller_http.py:276 | continuous | A-137 / A-138 |

## 2. Not in MFI

| ID | Capability | Evidence |
|---|---|---|
| K3-013 | LLM-free fact formatter for fast answers | anchor.py:134 |
| K3-014 | Deliverable extractor with telemetry-noise filter | anchor.py:163 |
| K3-015 | Tier 1 fast read-only path (ODIN_ANCHOR_FAST) | anchor.py:224 |
| K3-016 | Heavy-verb classifier (build/deploy/fix… → full orchestration) | anchor.py:239 |
| K3-018 | Tier 2 single grounded engine call, 90 s cap (ODIN_ANCHOR_SINGLE) | anchor.py:253 |
| K3-021 | ODIN_ANCHOR_NO_POLLER test flag | anchor.py:302 |
| K3-024 | JSON queue capped at 2000 rows | anchor_queue.py:118 |
| K3-028 (part) | Unused statuses received_by_local / processed and unused _PICKABLE | anchor_queue.py:40,42,51 |
| K3-033 (part) | No prioritisation: FIFO hand-out only | anchor_queue.py:327 |
| K3-041 (part) | cancel() is unreachable (no route) | anchor_queue.py:424 |
| K3-042 (part) | Delete is a hard delete, not a status flag (MFI A-176 says otherwise) | anchor_queue.py:428 |
| K3-043 (part) | Manage password hash is unsalted SHA-256, with defaults in source | anchor_manage.py:27,137 |
| K3-056 | CORS allow-all on the remote anchor | anchor_remote.py:236 |
| K3-057 | Crash-proof route wrappers (500 instead of 502) | anchor_remote.py:274 |
| K3-059 | URL-decoded scope path segments | anchor_remote.py:325 |
| K3-062 | GET manage/me session check | anchor_remote.py:354 |
| K3-071 (part) | Intake requires the key, contradicting the docstring ("intake stays open") | anchor_remote.py:16-17 vs :481 |
| K3-073 (part) | /requests/{id}/ack has no auth (remote and in-process); in-process GET status and admin config have no auth | anchor_remote.py:527; anchor.py:69,76,92-96 |
| K3-078 | ODIN_BRAIN env + brain HTTP helpers | local_poller_http.py:100 |
| K3-079 | Command create_project (autoApprove True) | local_poller_http.py:123 |
| K3-080 | Commands create / rename / delete chat | local_poller_http.py:131-152 |
| K3-081 | Command clear_scope | local_poller_http.py:153 |
| K3-082 | Command run_now | local_poller_http.py:165 |
| K3-083 | Command mark_notif | local_poller_http.py:174 |
| K3-087 | Ensure-scope-chat "App chat" | local_poller_http.py:222 |
| K3-089 (part) | Mirror has no "audit" key (MFI A-104 claims one) | local_poller_http.py:326-336 |
| K3-090 | 60-message pool cap per push (413 fix) | local_poller_http.py:300 |
| K3-097 (part) | Idempotent message add by client_msg_id | scopes.py:144 |
| K3-098 | Auto chat title from first message | scopes.py:160 |
| K3-108 (part) | _connector_connected live badge probe | ui_api.py:151 |
| K3-109 (part) | _features_of defined but unused | ui_api.py:46 |
| K3-126 (part) | Auth tokens in memory, with no expiry; POST /auth/config unauthenticated | auth.py:51,130 |
| K3-130 | Brain CORS allow-all | app.py:38 |
| K3-133 | Auto-register Klaviyo / Veeqo / HubSpot / EasyPost connectors at startup | app.py:139 |
| K3-134 | ODIN_USE_DISPATCHER brain selector | app.py:197 |
| K3-145 (part) | EasyPost allows POST /trackers (B-159 says GET-only); docstring contradiction; unused _allowed_path | easypost.py:58-80 |
| K3-148 (part) | HubSpot contacts_this_month analytics | hubspot.py:117 |
| K3-151 | Klaviyo metric_aggregates reporting POST | klaviyo.py:76 |
| K3-158 (part) | voice_service synthesize docstring says Azure; code uses Coqui | voice_service.py:94 |
| K3-166 (part) | requirements-voice.txt omits kokoro and coqui-tts, which the code uses | requirements-voice.txt |
| K3-169 | anchor-layer index.html redirect | index.html:3 |
| K3-173 (part) | Request-page status mapping mismatch (handed_out / done / completed never emitted) | anchor_sim.html:238 |
| K3-176 | Hide/show env variables toggle | anchor_sim.html:142 |
| K3-177 (part) | third_party_sim.html hard-codes an anchor API key | third_party_sim.html:35 |
| K3-178 | anchor_env.json as the environments SSOT (no row ID) | anchor_env.json |

## 3. Requested-category confirmations

**(a) Synchronization: FOUND**
- **Live sync across web, mobile and desktop:**
  - Desktop brain → local_poller_http.sync_push → anchor POST /anchor/v1/sync (local_poller_http.py:276; anchor_remote.py:504).
  - Web and mobile read /projects, /mirror/{key} and /pool/{pid} (anchor_remote.py:365-415).
  - Writes go back as chat/command requests (local_poller_http.py:65-81).
  - After a chat or command, a push runs immediately (:92).
- **Sequence numbers:** per-scope monotonic `_next_seq` stored in `_seq_counters.json` (scopes.py:117); the merged pool is sorted by seq (scopes.py:113).
- **Delta sync:** `/pool/{pid}?since=<seq>` with max_seq (anchor_remote.py:400-410).
- **Pull/push:**
  - The poller pulls `/poll` and pushes `/sync` (local_poller_http.py:56, :344).
  - Clients pull paginated pools with offset/limit/has_more (anchor_remote.py:411-415).
- **Durable mirror:** anchor_sync.json is reloaded at startup and persisted on every push, with a stale flag after 90 s (anchor_remote.py:54-80, :376).
- **Scope upward sync:** a separate "sync" meaning (scopes.py:280).

**(b) UDP / socket / datagram / websocket: NOT FOUND** — there is no UDP, raw socket, datagram or websocket anywhere in these files (grep is empty). The transports actually used are:
- HTTP/HTTPS request–response only: http.server ThreadingHTTPServer (anchor_remote, webhook_receiver, sim_server) and FastAPI/uvicorn (app.py).
- urllib clients (poller, queue webhooks, integrations).
- Short polling: poller every 5 s, request page every 2.5 s, third-party sims every 3 s.
- Server-Sent Events (text/event-stream) for /chat/stream, /chats/{cid}/stream and the brain /scope/stream drained by the poller (app.py:259, :373; local_poller_http.py:246).
- Production goes through nginx HTTPS (443) reverse-proxy paths.

**(c) Anchor: FOUND**
- **Queue:** anchor_queue.py, with Postgres or JSON storage and large-result offload.
- **Statuses:** 13 constants (anchor_queue.py:37-49), but only 9 are ever set. received_by_local and processed are dead; processing is set only by the in-process poller; cancelled has no route.
- **Prioritisation: NOT FOUND** — strict FIFO by created, up to poll_limit (anchor_queue.py:327).
- **Callbacks / return URLs:** webhook_url per request, with 2xx = ack, ack_pending, retries (retry_count / retry_interval_sec), failed, and manual /ack (anchor_queue.py:367-408). The request page uses per-project /cb/<pid> return URLs (anchor_sim.html:204).
- **Auth / keys:**
  - X-API-Key ANCHOR_API_KEY (anchor.py:39; anchor_remote.py:260).
  - Manage sessions: email + password hash + desktop confirmation code + remembered device (anchor_manage.py).
  - X-Odin-Client web/mobile gate (anchor_remote.py:308).
  - Gaps: unauthenticated /ack; in-process GET status and admin config are open; the key is embedded in anchor_prod.js, anchor_seed.js and third_party_sim.html.
- **Remote vs local:** anchor.py is the in-process router plus in-process poller (Phase 1); anchor_remote.py is the stand-in/deployed relay with no processor (Phase 3); deploy/anchor holds identical copies.
- **Poller:** in-process (anchor.py:296) and HTTP (local_poller_http.py:350). The poller supports 10 command kinds and a three-tier processor (fast read-only / single call / full orchestration).

**(d) Third-party request flow and simulators: FOUND**
- Contract: anchor.py:1-18 and anchor_remote.py.
- anchor_sim.html CD-flow request page, with sim_server.py SQLite + response files.
- webhook_receiver.py (callback + viewer + re-ack).
- third_party.py CLI.
- Legacy third_party_sim.html.
- Seeds in anchor_seed.js and anchor_prod.js; environments in anchor_env.json.
- External /api/v1 ask (external_api.py:57).

**(e) Auth / 2FA / login: FOUND**
- **auth.py:**
  - PBKDF2 login with a seed account.
  - 2FA, default off, using a fixed dev code.
  - verify-email; the forgot-password endpoint is a stub.
  - change-password.
  - Config flags, including Face ID and desktop_open; their POST is unauthenticated.
  - In-memory tokens.
- **Anchor Manage login** (anchor_manage.py:132): per-target 6-digit code read by the desktop (pending-code), 7-day sessions, 30-day remembered devices, web/mobile allow/stop.
- **Other gates:**
  - ODIN_ACCESS_TOKEN gate (app.py:52).
  - ODIN_API_KEY for /api/v1 (external_api.py:36).
- **Two parallel login systems:** auth.py tokens are not checked by any anchor route.

**(f) Voice STT/TTS EN/AR: FOUND**
- **STT:** faster-whisper medium/base with EN/AR auto-detect (voice_service.py:39-87); voice-note transcription (scopes.py:196).
- **TTS EN:** Kokoro (tts.py).
- **TTS AR:** Coqui XTTS-v2 (coqui_tts.py) via voice_service.synthesize (:93).
- **Unwired alternatives:** MMS-TTS (neural_tts.py), Azure ar-EG (azure_tts.py), and Piper / macOS say (voice_service.py:107-152, dead code).
- **Routes and client:** /voice/stt and /voice/tts behind USE_VOICE; pre-warm at app.py:399; React useVoice.ts hook.
- **Meeting report via anchor:** local_poller_http.py:208.

**(g) Clone features: NOT FOUND**
- There is no WhatsApp clone app and no project-clone function in these files.
- What does exist is "WhatsApp-style" sync and messaging semantics: a durable mirror, a seq/delta pull, message delete propagation, and replies, attachments and voice notes (anchor_remote.py:44; local_poller_http.py:181-207; scopes.py:129, :230).
- The only "cloning" mention is a comment that Egyptian Arabic would need XTTS-v2 voice cloning (neural_tts.py:18), which is not implemented.


<!-- ==================== PART K4A ==================== -->

# K4A — Flutter companion app (`odin_app`) capability inventory

Scope read in full: every `.dart` file under `odin_app/lib` (52 files, 10,306 lines; `home_screen.dart` and `projects_screen.dart` are 1-line stubs), plus `pubspec.yaml`, `web/index.html`, `ios/Runner/Info.plist` and `android/app/src/main/AndroidManifest.xml`. Secrets are named, not copied. Paths are relative to `odin_app/lib/` unless shown otherwise.

"In MFI?" values:
- **ID**: a row in `/home/claude/MFI.md` covers it.
- **partial: ID**: a row touches it, but the specific behaviour here is not listed.
- **no**: no MFI row matches.

## 1. Capabilities found

| ID | Category | Capability | What it does | Evidence | Triggered by | In MFI? |
|---|---|---|---|---|---|---|
| K4A-001 | Build, packaging, run & clients | Single API client `OdinApi` (three auth surfaces) | One client for brain native routes (`X-Odin-Token`), `/api/v1` (`X-API-Key` = ODIN_API_KEY) and `/anchor/v1` (`X-API-Key` = ANCHOR_API_KEY) | api/anchor_api.dart:24-97 `OdinApi`, `_native`, `_apiKey`, `_anchorKey` | every screen | A-150 |
| K4A-002 | Auth & security | Client identification header `X-Odin-Client: web\|mobile` + `X-Manage-Token` session on every anchor call | Lets the anchor's Manage "allow/stop mobile/web" toggles gate a client and require a valid login for every read/command | anchor_api.dart:28-31, 91-97 `_anchorKey`, `mngToken`, `_target` | every anchor call | partial: A-154 (listed as PLANNED; header not listed) |
| K4A-003 | Synchronization & Anchor | Cursor-based DELTA sync of a scope pool | First read does a full pull and caches it. Later reads call `/anchor/v1/pool/{scope}?since=<lastSeq>`, merge by id, sort by `seq` and advance the cursor to `max_seq` | anchor_api.dart:33-81 `_anchorPoolDelta`, `_deltaCache`, `_lastSeq`, `_maxSeqOf` | `scopeMessages` / `scopeMessagesRich` / `scopeAllMessages` in anchor mode (5 s chat timers) | no |
| K4A-004 | Synchronization & Anchor | Delta self-heal on deletions | If the server `total` differs from the cached count (a delete or clear), the client does one authoritative full re-pull and re-seeds the cursor | anchor_api.dart:65-73 | delta read | no |
| K4A-005 | Auth & security | Anchor login: request a desktop code | POST `/anchor/v1/manage/request-code {target}`; a random, target-specific code appears on the desktop badge | anchor_api.dart:101-103 `anchorRequestCode`; app_state.dart:133-136 `requestLoginCode` | Login "Get code" button | partial: A-154 (PLANNED in MFI; built here) |
| K4A-006 | Auth & security | Anchor login: email + password + code | POST `/anchor/v1/manage/login` (remember, target, optional device_id). The returned token is saved to SharedPreferences `odin.authToken` | anchor_api.dart:105-113 `anchorLogin`; app_state.dart:139-154 `loginViaAnchor` | Login "Sign in" in anchor mode | A-143 / partial: A-154 |
| K4A-007 | Auth & security | 7-day session resume / validation | On boot the saved token is checked with GET `/anchor/v1/manage/me`. An invalid token is purged and login is required again | anchor_api.dart:115-123 `anchorSessionValid`; app_state.dart:68-94 `bootAuth` | app start | A-143, A-140 |
| K4A-008 | Auth & security | Logout (anchor or brain) | Anchor POST `/manage/logout` or brain `/auth/logout`. Clears the token, the biometric flag and stored prefs | anchor_api.dart:125-128, 688; app_state.dart:187-202 `logout` | top-bar Log out, ⋮ Log out, Settings "Sign out" | no |
| K4A-009 | Safety & approvals | HARD GUARANTEE: no backend URL in anchor mode | `_api()` throws `ApiException(0, 'backend is not reachable…')` whenever mode=anchor and apiBase is empty, so web/mobile can never call the brain directly | anchor_api.dart:130-138 `_api`, 166-168 `_anchorRead` | any direct-only call in anchor mode | A-138 |
| K4A-010 | Other | Clean error decoding | Non-2xx HTML error pages become "the anchor returned an error page (HTTP n)". Long bodies are cut to 160 chars. A 200 response with an HTML body is reported as "misrouted" | anchor_api.dart:141-158 `_decode`, `ApiException` (10-16) | every GET/POST | A-140 |
| K4A-011 | Other | 15 s HTTP timeout | Every GET and POST is wrapped with `.timeout(15s)` | anchor_api.dart:160-164 | every GET/POST | no |
| K4A-012 | Synchronization & Anchor | Generic mirror read | GET `/anchor/v1/mirror/{key}` for notifications, audit, roles, company_agents, all_agents, connectors, ui_projects, ui_agents, ui_types, ui_connectors, hubspot, chats, activity | anchor_api.dart:170-175 `_anchorMirror` + callers 202-399, 413-418 | anchor-mode reads | A-184 |
| K4A-013 | Synchronization & Anchor | Paged full pool read | GET `/anchor/v1/pool/{scope}?offset&limit=200`; the scope key is passed through unchanged (`company` / `project:<id>` / `chat:…`) | anchor_api.dart:177-185 `_anchorPool` | delta seed / self-heal | A-184 |
| K4A-014 | Synchronization & Anchor | Health via anchor or brain | Anchor mode: GET `<anchor>/health` → engine 'anchor', voice off. Direct mode: brain `/health` | anchor_api.dart:188-194 `health` | `refreshDashboard`, `testConnection` | C-023 |
| K4A-015 | Synchronization & Anchor | Mirror freshness capture (`lastSync`) | Stores `updated`, `age_seconds` and `stale` from `/anchor/v1/projects` | anchor_api.dart:196-198, 246-259 `projects` | dashboard refresh | A-183 |
| K4A-016 | Synchronization & Anchor | "offline · last synced Xm/h/d ago" label | Computes "live · synced just now" or "offline · last synced …". **Never rendered**: `syncLabel` and `syncStale` have no UI caller | app_state.dart:230-242 `syncStale`, `syncLabel` | none (dead) | no |
| K4A-017 | Scheduling & notifications | Notifications feed read | Direct: `/notifications?unread=&limit=100`. Anchor: mirror 'notifications'. Never throws (returns empty) | anchor_api.dart:200-214 `notifications` | `refreshNotifs` (12 s timer, panel open) | C-032 |
| K4A-018 | Scheduling & notifications | Mark notification(s) read | Direct: POST `/notifications/read {id, all}`. Anchor: queued command `mark_notif` | anchor_api.dart:216-223 `markNotifRead`; app_state.dart:390-391 | notification tap, "Mark all read" | partial: C-032 (anchor command path not listed) |
| K4A-019 | Audit & consistency | Audit bundle read | Direct: `/audit/mirror`. Anchor: `/anchor/v1/mirror/audit` | anchor_api.dart:225-233 `auditData` | Audit screen load + 12 s timer | A-104 |
| K4A-020 | Audit & consistency | Audit run-now | POST `/audit/run?force=true`. In anchor mode it returns `{ran:false, note:'run the observer from the desktop app'}` | anchor_api.dart:235-239 `auditRun` | Audit "Run now" | C-028 |
| K4A-021 | Audit & consistency | Audit config write (unused) | POST `/audit/config?enabled&silence_minutes`. No-op in anchor mode. No UI caller | anchor_api.dart:241-244 `auditConfig` | none | C-028 |
| K4A-022 | Per-project features & integrations | Project list | Anchor: `/anchor/v1/projects`. Direct: `/projects` | anchor_api.dart:246-259 `projects` | `refreshDashboard` | A-184, C-002 |
| K4A-023 | Per-project features & integrations | Create project (direct) | POST `/projects` with name, identifier, description, type, mode=build, cadence, autoApprove, optional `members` (owner-confirmed team) | anchor_api.dart:261-286 `createProject`; app_state.dart:557-568 | New-project sheet "Create" | C-002, A-071 |
| K4A-024 | Per-project features & integrations | Validate proposed agents | POST `/agents/validate {names}` → known vs unknown + catalog | anchor_api.dart:288-293 `validateAgents`; app_state.dart:571 | New-project create (when a team was suggested) | C-005 |
| K4A-025 | Orchestration core | Capability-gap options | POST `/projects/{pid}/capability {task}` → recommended, editable, suggestion (+overlaps) | anchor_api.dart:295-299 `capability` | chat capability-gap detector (K4A-118) | C-003 |
| K4A-026 | Per-project features & integrations | Add / remove project agent | POST `/projects/{pid}/agents`; DELETE `/projects/{pid}/agents/{name}` (persistent exclusion) | anchor_api.dart:301-310 `addAgent`, `removeAgent` | capability dialog, member add, member remove | C-006 |
| K4A-027 | Per-project features & integrations | Suggest identifier (unused) | GET `/projects/suggest-id?name=` (never throws). No UI caller | anchor_api.dart:312-319 `suggestIdentifier` | none | C-002 |
| K4A-028 | Per-project features & integrations | Project detail fetch | GET `/projects/{pid}` | anchor_api.dart:321-322 `project` | ProjectDetail, AgentDetail | C-002 |
| K4A-029 | Per-project features & integrations | Roles / company agents / org roster / connectors reads | `/roles`, `/company/agents`, `/agents/all`, `/connectors`, or the matching mirror keys | anchor_api.dart:324-344 | background dashboard enrichment | C-003, C-005, B-042, C-010 |
| K4A-030 | Build, packaging, run & clients | Generic UI contract reads | `/ui/projects`, `/ui/agents`, `/ui/project/{pid}`, `/ui/types`, `/ui/connectors`, or mirror keys `ui_projects`, `ui_agents`, `ui_types`, `ui_connectors`. `uiProject` is derived from the list in anchor mode. `uiProject`, `uiTypes` and `uiConnectors` have no UI caller | anchor_api.dart:346-382 | Projects / Agents nav screens | B-043, C-031 |
| K4A-031 | Per-project features & integrations | HubSpot overview | `/hubspot/overview` or mirror 'hubspot'. Never throws (returns `{connected:false}`) | anchor_api.dart:384-393 `hubspotOverview` | HubSpot chip (60 s) | partial: A-209 (route not listed) |
| K4A-032 | Per-project features & integrations | Standalone chats registry (direct) | GET/POST `/chats`, DELETE `/chats/{scope}`, POST `/chats/rename?scope=` | anchor_api.dart:395-411 | sidebar CHATS section | C-017 |
| K4A-033 | Orchestration core | Live activity read | `/activity[?pid]` or mirror 'activity' | anchor_api.dart:413-418 `activity` | dashboard, 12 s change detector, project/agent load | C-019 |
| K4A-034 | Per-project features & integrations | Project agents list (unused) | GET `/projects/{pid}/agents`; no caller | anchor_api.dart:420-423 `agents` | none | C-006 |
| K4A-035 | Orchestration core | Project plan | GET `/projects/{pid}/plan` | anchor_api.dart:425-426 `plan` | ProjectDetail load | C-008 |
| K4A-036 | Per-project features & integrations | Project rules read / update / delete | GET `/projects/{pid}/rules` (plain and with ids), POST `/rules/{rid}` (`updateRule`, unused), DELETE `/rules/{rid}` | anchor_api.dart:428-439, 474-477 | ProjectDetail rules card | A-078, C-007 |
| K4A-037 | Per-project features & integrations | Project stats (unused) | GET `/projects/{pid}/stats`; no caller | anchor_api.dart:441-442 | none | C-009 |
| K4A-038 | Scheduling & notifications | Schedules list / update / approve / skip | `/schedules[?pid]`, `/schedules/{tid}/update`, `/approve`, `/skip` | anchor_api.dart:444-447, 492-495 | ProjectDetail, Recurring card, schedule editor | C-020 |
| K4A-039 | Orchestration core | Operations list / stop / provide | `/operations[?pid]`, `/operations/{oid}/stop`, `/operations/{oid}/provide {answers}` | anchor_api.dart:449-452, 536-539 | ProjectDetail / AgentDetail | C-014 |
| K4A-040 | Build, packaging, run & clients | Azure VM connect test | `/infra/connect-test`; returns `{}` in anchor mode (no infra probe from remote) | anchor_api.dart:454-457 `connectTest`; app_state.dart:496 | dashboard background | A-048, C-022 |
| K4A-041 | Per-project features & integrations | Archive lifecycle API | `/projects/archived`, `/archive` (**no UI button anywhere**), `/unarchive`, DELETE `/projects/{pid}` | anchor_api.dart:459-466, 496-498 | Archived screen | C-002, A-084 |
| K4A-042 | Per-project features & integrations | Web-parity project/agent edits | `/projects/{pid}/update`, `/mappings`, `/agents/suggest`, `/agents/{name}/update`, GET `/agents/{name}` | anchor_api.dart:468-485 | ProjectDetail dialogs | C-002, C-006, B-113 |
| K4A-043 | Per-project features & integrations | Scope chat rename + summary | POST `/scope/chat/rename?scope&cid`; GET `/scope/summary?scope` | anchor_api.dart:486-491 | ChatView ⋮ menu | C-016 |
| K4A-044 | Per-project features & integrations | Company agents and connectors add/remove | POST/DELETE `/company/agents`, `/connectors` | anchor_api.dart:500-505 | dashboard cards | A-076, A-077, C-005, C-010 |
| K4A-045 | Safety & approvals | Approvals API | `/approvals[?pid]`, `/approvals/count` (unused), `/approvals/{aid}/approve\|reject {note}` | anchor_api.dart:507-521 | Approval center | C-011 |
| K4A-046 | Orchestration core | Team run start / status / stop | `/projects/{pid}/orchestrate/start {goal}`, `/status`, `/stop` | anchor_api.dart:523-528 | Operations card, ChatView 5 s run-status poll | C-013 |
| K4A-047 | Orchestration core | Sync / deploy / request deploy | `/projects/{pid}/sync/run`, `/deploy/run`, `/deploy/request` | anchor_api.dart:529-534 | Operations card | C-012 |
| K4A-048 | Orchestration core | Conversational intake | POST `/projects/intake {history}` → spec (type, team, identifier) | anchor_api.dart:541-543 `intake` | "Let the CTO suggest the type & team" | C-004, A-073 |
| K4A-049 | Orchestration core | Company monitor feed | GET `/scope/children?scope=company` | anchor_api.dart:545-549 `scopeChildren` | dashboard monitor card | A-081, C-016 |
| K4A-050 | Orchestration core | Legacy company chat (unused) | POST `/chat {text, lang}`. `AppState.companyChat` has no caller | anchor_api.dart:551-555; app_state.dart:555 | none | C-021 |
| K4A-051 | Synchronization & Anchor | Ensure scope chat | GET/POST `/scope/chats?scope` (creates 'App chat'). Returns the sentinel `'anchor'` in anchor mode | anchor_api.dart:557-567 `ensureScopeChat` | Conversation / ChatView init, forward | C-016 |
| K4A-052 | Synchronization & Anchor | Scope message reads (3 shapes) | `scopeMessages` (role/content), `scopeMessagesRich` (unused), `scopeAllMessages` (`/scope/messages`, whole pool). Anchor mode uses delta pool | anchor_api.dart:569-598 | chat timers | A-136, C-016 |
| K4A-053 | Synchronization & Anchor | Delete message | Direct: DELETE `/scope/message`. Anchor: command `delete_message` (propagates to every device) | anchor_api.dart:600-607 | WhatsApp multi-select delete | A-137 |
| K4A-054 | Per-project features & integrations | Attachment upload | Multipart POST `/scope/upload` with `X-Odin-Token`. **Direct mode only**: it throws in anchor mode, so attachments fail on web/mobile production | anchor_api.dart:609-621 `uploadScopeFile` | attach sheet | A-135 (WMV: blocked in anchor mode) |
| K4A-055 | Synchronization & Anchor | Rich post into pool (no AI turn) | Direct: POST `/scope/message`. Anchor: command `post_message` with `kind` renamed to `msg_kind`, nulls dropped | anchor_api.dart:623-639 `postScopeMessage` | reply, forward, attachment post | A-137 |
| K4A-056 | Per-project features & integrations | Attachment URL resolution | Absolute URLs pass through; relative URLs get the apiBase prefix (anchor-served media is already absolute) | anchor_api.dart:641-644 `fileUrl` | image/audio bubbles | no |
| K4A-057 | Orchestration core | SSE token streaming (direct only) | GET `/scope/stream?scope&text&lang&cid`. Hard-refused in anchor mode | anchor_api.dart:646-655 `streamScope`; services/sse*.dart | chat send (direct) | B-109, C-016 |
| K4A-058 | Orchestration core | Non-streaming scope send fallback | GET `/scope/stream` with Accept event-stream, waits for completion. In anchor mode it routes to `chatViaAnchor` | anchor_api.dart:657-668 `scopeSend` | stream failure | C-016 |
| K4A-059 | Auth & security | Brain auth API (direct mode) | `/auth/config` GET/POST, `/auth/login`, `/auth/2fa`, `/auth/me` (X-Auth-Token), `/auth/logout`, `/auth/change-password`, `/auth/forgot` | anchor_api.dart:670-694 | login, settings | C-001 |
| K4A-060 | Synchronization & Anchor | Synchronous ask (direct) | POST `/api/v1/p/{identifier}/ask` with X-API-Key | anchor_api.dart:696-700 `askDirect`; app_state.dart:544-553 `ask` (no UI caller) | none in UI | A-131, C-024 |
| K4A-061 | Synchronization & Anchor | Anchor admin reads | `/anchor/v1/admin/counts`, `/admin/requests[?status]`, `/admin/config` | anchor_api.dart:702-716 | Anchor screen, 12 s change detector | C-026 |
| K4A-062 | Synchronization & Anchor | Third-party style request submit + status | POST `/anchor/v1/requests {project, prompt, webhook_url, sender:'odin_app'}`; GET `/requests/{id}` | anchor_api.dart:718-728 | Anchor "Send request" sheet | A-178, A-132 |
| K4A-063 | Synchronization & Anchor | CHAT through the anchor | Submits `{project:scope, prompt, sender:'chat'}`, then polls every 2 s for up to 8 min, with onStatus callbacks. Returns result text or throws on timeout | anchor_api.dart:730-754 `chatViaAnchor` | chat send in anchor mode | A-131, A-200 |
| K4A-064 | Synchronization & Anchor | COMMAND queue through the anchor | Write actions become `{project:'__command__', sender:'command', prompt:kind, payload:{kind,…}}`. The client polls every 2 s for up to 3 min. **It returns silently on timeout and on errors** | anchor_api.dart:756-773 `commandViaAnchor` | every anchor-mode write | no |
| K4A-065 | Synchronization & Anchor | Command kinds emitted by the app | `mark_notif`, `delete_message`, `post_message`, `run_now`, `meeting_report`, `create_chat`, `rename_chat`, `create_project`, `delete_chat`, `clear_scope` | anchor_api.dart:219, 603, 634, 779, 791; app_state.dart:277, 293, 309, 327, 332 | UI writes in anchor mode | no |
| K4A-066 | Scheduling & notifications | Run Now (recurring task) | Anchor: command `run_now {pid, prompt, cid}`. Direct: POST `/projects/{pid}/run-now` → message | anchor_api.dart:775-784 `runNow` | ▶ in chat header, project "Run" button | C-013 |
| K4A-067 | Voice | Mobile meeting report | Anchor: command `meeting_report {pid, texts, lang}`, then polls the project pool 8×2 s for a "Live Meeting" sender message to show inline. Direct: POST `/meeting/finish_text?pid` | anchor_api.dart:786-811 `meetingReport` | MeetingSheet "Stop & finish" | B-198 |
| K4A-068 | Synchronization & Anchor | Async ask via anchor | `sendRequest`, then polls every 3 s for up to 8 min to a terminal state | anchor_api.dart:813-837 `askViaAnchor` | `AppState.ask` (no UI caller) | A-131, A-200 |
| K4A-069 | Build, packaging, run & clients | Access modes direct / anchor | `AccessMode` enum: direct = same network as brain; anchor = remote, async via the anchor | config.dart:4-11 | profile selection | A-134 |
| K4A-070 | Build, packaging, run & clients | Environment profile model | name, apiBaseUrl, anchorBaseUrl, mode, token, odinApiKey, anchorApiKey; trailing-slash normalisation; JSON round-trip; clone | config.dart:13-58 `EnvProfile` | Settings | A-134 |
| K4A-071 | Build, packaging, run & clients | Default profiles | "Local (Phase 2)" direct localhost:8000; "Anchor (local — Phase 2)" anchor localhost:9100 with EMPTY apiBase; "Deployed (Phase 3)" anchor `https://anchor.odinmarkets.com/odin-anchor` with empty apiBase | config.dart:60-86 `defaults` | first launch | A-134 (MFI still names an "Anchor sim (Phase 3 test)" profile — outdated) |
| K4A-072 | Auth & security | Hard-coded ANCHOR_API_KEY in default profiles | The anchor key literal is compiled into the two anchor profiles (value not copied) | config.dart:77, 84 | build | partial: A-150 (MFI notes keys in docs, not in client source) |
| K4A-073 | Build, packaging, run & clients | Versioned profile persistence | SharedPreferences `odin.profiles.v3` / `odin.selected.v3`. The v3 key bump discards stale profiles that allowed the backend shortcut | config.dart:89-125 `AppConfig` | load/save | partial: A-134 |
| K4A-074 | Build, packaging, run & clients | `ODIN_FORCE_ENV` auto-select | `--dart-define=ODIN_FORCE_ENV=production` picks the anchor profile with a non-localhost URL; `phase2` picks the localhost anchor profile. User edits are kept | state/app_state.dart:22-49 `AppState.create` | build flag at launch | D-012, D-013 |
| K4A-075 | Build, packaging, run & clients | `ODIN_ANCHOR` dart-define NOT read | Docs and the build commands pass `--dart-define=ODIN_ANCHOR=…`, but no Dart code reads it; the anchor URL comes only from profiles | docs.dart:104 (text); absent elsewhere | — | partial: D-013 (MFI lists it as a selector) |
| K4A-076 | Auth & security | bootAuth direct mode, FAIL-CLOSED | If `/auth/config` cannot be read, login is REQUIRED ("locked when unsure beats open when unsure") | app_state.dart:95-104 | app start (direct profile) | partial: A-149 (fail-closed not listed) |
| K4A-077 | Auth & security | Per-platform login requirement | Web uses `require_login_web`; mobile uses `require_login_mobile`. Saved token is checked via `/auth/me` | app_state.dart:96-128 | app start | A-149 |
| K4A-078 | Auth & security | Face ID resume gate | If `faceid_first_access` is on and a mobile session is saved, `pendingBiometric` is set and the session resumes only after `resumeAfterBiometric` | app_state.dart:55, 62-66, 114-117 | app start, login screen | A-147 |
| K4A-079 | Auth & security | Password login blocked in anchor mode | `login()` returns "Use the desktop code to sign in" in anchor mode. In direct mode a `twofa_required` response hands off to the 2FA flow | app_state.dart:156-176 `login`, `submit2fa`, `_finishLogin` | Login | A-143, A-144 |
| K4A-080 | Auth & security | Change password / forgot / auth flags | `changePassword` (falls back to the hard-coded owner email if none), `forgot`, `setAuthFlag` | app_state.dart:204-224 | Settings → Account, Login | A-143, A-146, A-149 |
| K4A-081 | Synchronization & Anchor | Active chat scope selection | `activeChatScope` / `activeChatTitle` (default company "Company — Chief Engineer"), `openChat`; driven by the sidebar | app_state.dart:254-262 | sidebar clicks | A-136 |
| K4A-082 | Synchronization & Anchor | In-memory pool cache (instant reopen) | `poolCache[scope]` is shown immediately on reopen, then refreshed in the background (WhatsApp-style) | app_state.dart:249-252; whatsapp.dart:389-409; chat_screen.dart:168-191 | opening a chat | no |
| K4A-083 | Per-project features & integrations | Create / rename standalone chat everywhere | Anchor: `create_chat` / `rename_chat` commands plus a 900/700 ms wait. Direct: `/chats`. New-chat scope = `chats.first` (race-prone guess) | app_state.dart:268-302 `refreshChats`, `newAdhocChat`, `renameChat` | sidebar ＋New / Rename | partial: C-017 (anchor command path not listed) |
| K4A-084 | Per-project features & integrations | Create project via anchor | Anchor: `create_project {name}` + 1 s wait + refresh. Direct: `createProject` | app_state.dart:304-320 `createProjectAnywhere` | only the dead `WhatsApp._newProject` (unreachable) | partial: C-002 |
| K4A-085 | Per-project features & integrations | Delete / clear conversation | `chat:` scopes: anchor `delete_chat` or DELETE `/chats`. Other scopes: anchor `clear_scope`. **In direct mode, non-chat scopes do nothing** | app_state.dart:322-337 `clearConversation` | sidebar Delete, WhatsApp ⋮ (dead) | partial: C-017 |
| K4A-086 | Synchronization & Anchor | OFFLINE state (anchor-only door) | If health or projects fail in anchor mode, `offline=true`, all caches are wiped (no stale data) and the spinner is held at least 800 ms (`_minSpin`) so the retry is visible | app_state.dart:357-361, 421-428, 437-484 | `refreshDashboard` | A-139 |
| K4A-087 | Synchronization & Anchor | Auto-switch to Deployed profile | In direct mode with an unreachable brain, the client switches to the anchor profile whose name contains 'deployed' and retries health | app_state.dart:458-470 | `refreshDashboard` | A-140 |
| K4A-088 | Build, packaging, run & clients | Essentials-first dashboard load + background enrichment | Projects paint first. `_bg()` then loads chats, roles, companyAgents, allAgents, connectors, activity and vm, each updating the UI on arrival; errors are swallowed | app_state.dart:430-501 `refreshDashboard`, `_bg` | Shell start, route to dashboard, refresh | A-140 |
| K4A-089 | Scheduling & notifications | Anchor terminal-state alerts | `refreshAnchor` loads counts, requests and config in parallel. `_detect` seeds silently on first load, then for each newly terminal request sets a banner, increments `newEvents` and fires a local OS notification | app_state.dart:510-542 | Shell start, 12 s change detector, Anchor page | A-133 |
| K4A-090 | Scheduling & notifications | Unread pulse | If the unread count rises, `notifPulse=true` for 3 s, which makes the bell shake | app_state.dart:373-389 `refreshNotifs` | 12 s timer, panel open | no |
| K4A-091 | Scheduling & notifications | Notification → project redirect hook | `navToProject` is set by the Shell; `openProjectById(pid)` navigates | app_state.dart:392-394; shell.dart:52 | notification tap | no |
| K4A-092 | Build, packaging, run & clients | Bell count = number of guide tabs + new events | `bellCount => kBellTabs.length + newEvents` (getter itself unused; badges use `kBellTabs.length`) | app_state.dart:366-368 | — | A-125 |
| K4A-093 | Synchronization & Anchor | Light change detector | Fingerprint of `anchorCounts` + activity length. Only a change triggers `refreshAnchor` (and dashboard refresh when on it) | app_state.dart:576-596 `pollForChanges`; shell.dart:60-67 | 12 s Shell timer | no |
| K4A-094 | Build, packaging, run & clients | Profile select / save | Rebuilds `OdinApi`, clears the alert set, persists | app_state.dart:407-419 | Settings, Ports sheet | A-134 |
| K4A-095 | Build, packaging, run & clients | Test connection | Brain health + anchor counts, each with an error string | app_state.dart:598-612 `testConnection`; settings_screen.dart:98-108 | Settings button | A-134 |
| K4A-096 | Other | Crash-proof UI | `ErrorWidget.builder` shows "Something hiccuped… Pull to refresh" instead of a white screen (accessibility rationale). `runZonedGuarded` swallows uncaught async errors | main.dart:13-41 | any build error | no |
| K4A-097 | Auth & security | TLS cert override (mobile/desktop) | `HttpOverrides.global` accepts bad certificates ONLY for a hard-coded VM IP (not copied) and the anchor domain; other hosts stay strict. No-op on web | main.dart:34; services/cert_override*.dart (`_trustedHosts`, `_OdinHttpOverrides`) | app start | no (MFI only lists the file in §4b) |
| K4A-098 | Auth & security | Auth gate | Spinner until `authResolved`, then Shell if `gateOpen` else LoginScreen | main.dart:61-77 `_Gate`; app_state.dart:130 | app start / auth change | A-143 |
| K4A-099 | Build, packaging, run & clients | Shell router (11 routes) | dashboard, project, agent, anchor, settings, docs, archived, projects, agents, approvals, audit. Project and agent views are keyed by id to force a fresh State | screens/shell.dart:28-145 `Route`, `_ShellState._content` | sidebar/nav | A-129 |
| K4A-100 | Synchronization & Anchor | Shell 12 s background loop | Every 12 s: `refreshNotifs`, then `pollForChanges` → `refreshAnchor` (+ `refreshDashboard` if on dashboard). The startup post-frame load also runs the three refreshes | shell.dart:47-68 | timer | no |
| K4A-101 | Build, packaging, run & clients | Conversations (WhatsApp-clone) mode toggle | The `_chat` flag replaces the content area with `WhatsAppMode`. Always-visible forum icon on wide AND narrow layouts | shell.dart:45, 115, 545-554 | top-bar icon | A-126, A-135 |
| K4A-102 | Build, packaging, run & clients | Single sidebar | Brand, "Remote Anchor · Web/Mobile", engine label. Company → company chat. PROJECTS (+New sheet). CHATS (+New with mandatory name, ⋮ Rename/Delete, long-press rename). Nav: Projects, Agents, Anchor Connect, Approvals, Audit, Archived, Docs, Settings. In chat mode, project taps open `project:<pid>` conversations | shell.dart:200-368, 407-496 `_Sidebar`, `_askChatName`, `_confirmDelete`, `_ChatRow` | user | A-108, A-130, A-135 |
| K4A-103 | Build, packaging, run & clients | Sidebar status dots | Connected/Offline, Voice ready/off, and (if login required) "Signed in · 7-day session" / "Login required — connect" | shell.dart:353-363 | state | A-143 |
| K4A-104 | Build, packaging, run & clients | Responsive layout | At ≥900 px wide: permanent 264 px sidebar with inline actions. Narrow: Drawer plus ⋮ menu (prevents top-bar overflow) | shell.dart:150-165, 555-610 | screen width | partial: A-172 |
| K4A-105 | Build, packaging, run & clients | Narrow ⋮ "Conversations" item does nothing (bug) | The menu offers value 'chat', but `onSelected` handles only ports/refresh/guide/logout | shell.dart:594-604 | ⋮ menu | no |
| K4A-106 | Build, packaging, run & clients | Top bar actions | Title tap → home. Ports & env. Env chip. HubSpot chip. Refresh (dashboard + anchor + notifs). Logout. Notifications bell with unread badge. Guide with tab-count badge | shell.dart:498-660 `_TopBar` | user | A-125, A-126 |
| K4A-107 | Build, packaging, run & clients | Ports & Environment sheet + Dev↔Prod flip | Shows dev ports (8000/9100/9104/9300/8080) and prod (anchor + web via 443). "Use Development (local)" / "Use Production (online)" select the profile and refresh | shell.dart:662-774 `showPortsSheet` | top-bar icon / env chip / Docs "Switch" | no |
| K4A-108 | Per-project features & integrations | HubSpot chip | Polls the overview every 60 s. Dot is yellow (unknown), green or red. Dialog shows portal id plus contacts, companies, deals and contacts this month ("scope needed" if a count is a map). Hint names HUBSPOT_SECRET_KEY | shell.dart:776-852 `_HubSpotChip` | timer / tap | partial: A-209 |
| K4A-109 | Build, packaging, run & clients | Environment chip | Shows `name · mode` (compact: mode); warn colour in anchor mode | shell.dart:854-868 `_EnvChip` | wide top bar | no |
| K4A-110 | Scheduling & notifications | Banner bar | In-app banner for anchor terminal events, with close | shell.dart:187, 870-891 `_BannerBar` | `_detect` | A-133 |
| K4A-111 | Build, packaging, run & clients | WhatsApp mode = conversation for the sidebar-selected scope | `WhatsAppMode.build` renders `Conversation(scope: activeChatScope)` keyed by scope | screens/whatsapp.dart:78-88 | chat mode | A-135 |
| K4A-112 | Other | Dead WhatsApp list code | `_projectConvs`, `_chatConvs`, `_tile`, `_sectionHeader`, `_open`, `_prompt`, `_newChat`, `_newProject`, `_clearChat` are unreachable (old list column) | whatsapp.dart:27-147 | none | no |
| K4A-113 | Synchronization & Anchor | Conversation live sync | Init → `ensureScopeChat` + reload. A 5 s periodic reload runs when not busy. Shows the cache first. Never replaces a shown conversation with an empty read. Resets on scope change | whatsapp.dart:358-409 | timer | A-137 |
| K4A-114 | Per-project features & integrations | Send in Conversations | A reply is a group post with `reply_to` (no AI). Plain text goes to the CTO: `chatViaAnchor` in anchor mode (no reload, so the conversation isn't wiped), or SSE streaming with a `scopeSend` fallback. Optimistic bubbles; `_sending` re-entrancy guard; dictation is stopped on send | whatsapp.dart:411-472 `_sendText` | Send / Enter | A-135, A-137 |
| K4A-115 | Per-project features & integrations | Attach camera / gallery / file | Bottom sheet: image_picker (quality 82) or file_picker (withData), then upload + post with kind, attachment and transcript (+reply_to) | whatsapp.dart:474-572 | ＋ button | A-135 |
| K4A-116 | Per-project features & integrations | Multi-select message toolbar | Long-press toggles selection. Toolbar: Reply (single), Copy, Forward, Delete; × to exit | whatsapp.dart:269-316, 604-617 | long-press | partial: A-135 (reply only) |
| K4A-117 | Per-project features & integrations | Forward messages | Picker of Company + projects → `ensureScopeChat(target)` → `postScopeMessage` with sender "(forwarded)" and attachment | whatsapp.dart:318-350 `_forwardSelected` | Forward | no |
| K4A-118 | Per-project features & integrations | Copy all / copy selected | Clipboard lines `who: body [attachment]` | whatsapp.dart:273-300, 679 | Copy all / Copy | A-142 |
| K4A-119 | Per-project features & integrations | Sender tagging | `<email local-part> · via Conversations` so posts are recognisable in normal view | whatsapp.dart:352-356 `_sender` | posts | no |
| K4A-120 | Scheduling & notifications | ▶ Run-now in chat header (recurring projects) | Shown when the project has `periodic.enabled` or a label. Posts an "autonomous (no approval prompt)" notice, calls `runNow`, then reloads at 3/9/16/25 s | whatsapp.dart:175-195, 632-641; chat_screen.dart:35-55, 479-487 | ▶ icon | B-049 |
| K4A-121 | Voice | Meeting-capability client heuristic | Shows the speaking-head button when the project name, description or members contain meeting / voice / audio capture / transcription / streaming / live meeting / zoom | whatsapp.dart:196-208; chat_screen.dart:57-67 `_meetingCapable` | header build | partial: B-199 (MFI gates server-side via `project_has_meeting_asset`) |
| K4A-122 | Per-project features & integrations | Report-capability heuristic + export menu | Matches reporting / report / soc / security operations / redberry / documentation agent (or recurring). Menu offers PDF/DOCX/MD/PPTX. WhatsApp mode opens `<brainBase>/soc/report?pid&fmt`; ChatView opens `<brainBase>/project/report?pid&fmt`; mobile shows a snackbar instead | whatsapp.dart:210-232, 642-654; chat_screen.dart:96-118, 488-501 | PDF icon | C-033, C-018, A-106 |
| K4A-123 | Voice | Live meeting launcher | Web: in-app dialog with an iframe of brain `/meeting_monitor.html?pid` (mic allowed). Mobile: `MeetingSheet` bottom sheet; reloads chat on close | whatsapp.dart:234-263; chat_screen.dart:69-94 | speaking-head icon | A-173, B-200 |
| K4A-124 | Voice | Voice replies toggle | Speaker icon on/off. Turning on says "Voice on" (unlocks web audio inside the tap). Replies are spoken when on | whatsapp.dart:665-678, 444, 457; chat_screen.dart:511-524, 288 | icon | A-170, A-163 |
| K4A-125 | Voice | Dictation mic + EN/ع locale toggle | Device STT into the input box; toggle en_US / ar_SA. A fresh session each time; late results are ignored once stopped or sent | whatsapp.dart:519-545, 757-767; chat_screen.dart:426-449, 632-641 | mic icon | A-170, A-171 |
| K4A-126 | Build, packaging, run & clients | Lazy message rendering | Renders the last 200; a "Load earlier (N more)" button adds 200 | whatsapp.dart:268, 708-738; chat_screen.dart:123, 604-625 | scroll/top button | partial: B-078 (PLAN) |
| K4A-127 | Build, packaging, run & clients | Keyboard handling | Tap-outside unfocus, drag-to-dismiss, explicit "Hide keyboard" button with a managed FocusNode | whatsapp.dart:713, 774, 779-784; chat_screen.dart:609, 648, 653-658 | user | A-172 |
| K4A-128 | Per-project features & integrations | Rich bubbles | Sender label, reply quote, image (`Image.network`), voice-note play button (audioplayers) + italic transcript, file/zip icon, selectable text, selection highlight | whatsapp.dart:801-881 `_Bubble` | render | A-135 |
| K4A-129 | Build, packaging, run & clients | Syncing indicators + empty/error states | Header spinner, "Syncing…" strip, "Syncing your messages…", "Could not reach the chat pool" | whatsapp.dart:627-707; chat_screen.dart:579-603 | state | A-142 |
| K4A-130 | Synchronization & Anchor | ChatView (normal mode) shared-pool chat | 5 s timer reloads the pool. For project scopes it also polls `runStatus`, which **always throws in anchor mode** (caught silently) | screens/chat_screen.dart:125-191 | timer | A-137 |
| K4A-131 | Synchronization & Anchor | ChatView anchor-mode send with status | Bubble shows "(sending…)" → "(queued…)/(processing…)" → reply, or "(offline — could not reach the anchor)" | chat_screen.dart:250-296 `_stream` | send | A-131 |
| K4A-132 | Orchestration core | Run-state banner | "⏳ WORKING — the CTO is on it" while busy or a team run is active; "✅ FINISHED — the CTO's final answer is below" otherwise (project scopes) | chat_screen.dart:547-578 | state | no |
| K4A-133 | Per-project features & integrations | Chat summary / rename | ⋮ → "Summarize this chat" dialog; "Rename chat" dialog | chat_screen.dart:193-232, 531-543 | ⋮ menu | C-016 |
| K4A-134 | Orchestration core | Capability-gap 4-way dialog | When a reply contains "No current agent's rules fully cover this", the client fetches `/capability` and offers: I'll do it (CTO) / Embed existing / Expand a role (edit rules → `updateAgent`) / Create new (name, role, rules → `addAgent`, overlap warning). It then sends a `⟦resolve⟧ …` message into the same pool. Skipped for `⟦resolve⟧` tasks and non-project scopes | chat_screen.dart:298-424 `_maybeCapabilityGap`, `_capabilityDialog` | after each send | partial: C-003, A-069 (client dialog not listed) |
| K4A-135 | Per-project features & integrations | Project detail page | Seeds instantly from the dashboard list, then enriches with project, rules (plain + ids), schedules, operations, plan and activity in parallel (`safe` wrappers) | screens/project_detail.dart:11-81 | open project | C-002 |
| K4A-136 | Scheduling & notifications | Project "Run" button | Shown when schedules exist → `runNow` → snackbar | project_detail.dart:30-40, 348-359 | button | C-013 |
| K4A-137 | Per-project features & integrations | Edit project / add folder mapping | ⋮ → name and description dialog → `/update`; local ↔ cloud/VM folder pair → `/mappings` | project_detail.dart:106-135, 272-299, 360-371 | ⋮ menu | C-002, A-047 |
| K4A-138 | Per-project features & integrations | Team grid + member actions | Project CTO + members with live heartbeat ('working'). Tap → AgentDetail. Long-press (not CTO) → Edit resources & env, or Remove (confirm) | project_detail.dart:83-104, 254-270, 387-425 | tap / long-press | C-006 |
| K4A-139 | Per-project features & integrations | Suggest & add member (review before create) | Describe a skill → `suggestAgent` → editable review of name, role, description, "Allowed Resources & Dependencies" and env KEY=VALUE lines (`_parseEnv`) → `addAgent` with `force:true`, nature | project_detail.dart:137-252 `_suggestAndAddMember`, `_memberEditDialog`, `_editMemberResources`, `_parseEnv` | Team "Add" | B-113, C-006 |
| K4A-140 | Orchestration core | Latest operation card | Status colour; "⛔ Needs you: question"; log (first 40 lines) | project_detail.dart:560-608 `_OperationCard` | load | C-014 |
| K4A-141 | Orchestration core | Plan card | First 12 plan steps | project_detail.dart:430-452 | load | C-008 |
| K4A-142 | Per-project features & integrations | Rules card with delete | Uses id'd rules when available (× delete), else plain strings | project_detail.dart:453-488, 301-307 | × | A-078 |
| K4A-143 | Scheduling & notifications | Schedules card | Each task shows name/goal and cron/every, with Edit (schedule editor), Approve (due run) and Skip (next run) | project_detail.dart:489-530, 309-325 | buttons | C-020 |
| K4A-144 | Orchestration core | Operations controls card | Run team (goal dialog) / Stop, Sync, and for the deployment type only Deploy and Request deploy. When blocked: Provide answer, Stop operation. Running pill from `runStatus` | project_detail.dart:610-758 `_ControlsCard` | buttons | C-012, C-013, C-014 |
| K4A-145 | Build, packaging, run & clients | Dashboard offline view | "You are offline" + offline message + Try again / Reconnecting… | screens/dashboard.dart:22-24, 107-139 `_OfflineView` | `s.offline` | A-139 |
| K4A-146 | Per-project features & integrations | Agent roster card | Every actual agent (all projects + company) deduped by name, grouped Operational / Technical, scrollable (max 320 px) | dashboard.dart:240-303, 369-381 `_AgentRoster`, `_agentsByNature` | dashboard | B-042 |
| K4A-147 | Scheduling & notifications | Recurring & scheduled card | Periodic projects with cadence; a pulsing red dot when there are unread notifications; edit-schedule shortcut (first task, else open project) | dashboard.dart:608-687 `_RecurringCard`, `_PulseDot` | dashboard | partial: B-098 |
| K4A-148 | Build, packaging, run & clients | System status card | Projects KPI, agents-live KPI, API ready, engine, Voice, Azure VM connected/checking, model pill (Claude Code / ollama model), `dashError` | dashboard.dart:141-190 `_StatusPanel` | dashboard | A-048, C-023 |
| K4A-149 | Orchestration core | Live agents card | Working agents with phase and task → AgentDetail | dashboard.dart:192-238 `_LiveAgents` | dashboard | A-082 |
| K4A-150 | Per-project features & integrations | Company agents card add/remove | name + role → POST (avatar generic); × removes | dashboard.dart:305-367 `_CompanyAgents` | dashboard | A-076 |
| K4A-151 | Per-project features & integrations | Connectors card add/remove | name, type and obscured API key; status dot; × removes | dashboard.dart:383-444 `_Connectors` | dashboard | A-077, B-101 |
| K4A-152 | Orchestration core | Company monitor feed card (wide layout only) | Top 8 children of the company scope with their last line | dashboard.dart:446-492 `_MonitorFeed` | dashboard load / refresh | A-081 |
| K4A-153 | Per-project features & integrations | Projects grouped by type | Groups ordered by `kTypeMeta` (unknown types last). Cards show icon, id, periodic pill, live count and member avatars. "New project" when empty | dashboard.dart:494-606 | dashboard | A-130 |
| K4A-154 | Build, packaging, run & clients | Dashboard layouts | Wide: chat area (flex 5) + cards (flex 4). Narrow: pull-to-refresh list with the chat (460 px) at the bottom | dashboard.dart:26-87 | width | no |
| K4A-155 | Per-project features & integrations | New project sheet | Name, unique editable identifier, type (19 types), description, cadence once / recurring / periodical | screens/new_project.dart:8-164 | ＋ New (sidebar / dashboard) | C-002, A-071 |
| K4A-156 | Orchestration core | "Let the CTO suggest the type & team" | `intake` with the description → type, team and identifier prefill (identifier only if empty) | new_project.dart:36-65 `_suggest` | button | A-073 |
| K4A-157 | Voice | Long-streaming project chunking dialog | Keyword detection (zoom, meeting, transcrib, stream, microphone, 2 hour, chunk, speech to text, …) → mandatory dialog explaining chunked processing → "I understand — create it" | new_project.dart:166-212 `_isStreaming`, `_confirmChunking` | Create | no |
| K4A-158 | Safety & approvals | Unknown-agent confirmation gate | Validates the suggested team. Each unknown name needs Create new (role + rules required) / Use existing (catalog pick) / Remove. Nothing is created on cancel; with no suggestion the backend infers the team | new_project.dart:214-368 `_create`, `_confirmUnknownAgents` | Create | partial: C-005, B-187 |
| K4A-159 | Per-project features & integrations | New-project sheet is direct-only (bug) | Calls `AppState.createProject` → `api.createProject` → `_api` throws in anchor mode, so project creation fails on web/mobile production | new_project.dart:249-256 | Create in anchor mode | no |
| K4A-160 | Synchronization & Anchor | Anchor Connect page | Count chips in lifecycle order, config (retry count, retry interval, poll limit), lifecycle legend (queued → sent_to_local → processing → response_received → ack_pending → finished / failed / cancelled), request rows with detail dialog, error card + Retry, pull-to-refresh | screens/anchor_screen.dart:9-213, 296-325 | nav "Anchor Connect" | A-132, A-176 |
| K4A-161 | Synchronization & Anchor | Send external request sheet | Target project + prompt → `sendRequest` → "Queued: id (status)" → refresh | anchor_screen.dart:215-294 `_SendSheet` | "Send request" | A-132 |
| K4A-162 | Build, packaging, run & clients | Help & Testing Guide (searchable) | Cards: environments, production support, Dev↔Prod switching, LIVE active environment, phase shells 2/3, anchor_loop, phase-3 lessons, Phase-3 testing, simulator vs device, "#1 mistake", login and sessions, real-iPhone install (`ODIN_FORCE_ENV`/`ODIN_ANCHOR` flags). Live env banner with Switch | screens/docs.dart:10-214 | nav "Docs" | no |
| K4A-163 | Voice | Native mobile meeting sheet | On-device speech_to_text in continuous mode (restarts on done/notListening). listenFor 30 s, pauseFor 4 s, partial results. Final results become numbered chunks. A big mic scales with sound level, plus a level bar and partial text | screens/meeting_sheet.dart:14-167 | MeetingSheet | B-198 |
| K4A-164 | Voice | Meeting stop → report | Appends the pending partial. No speech → hint. Else `buildReport(chunks)`, then shows inline markdown (RTL for Arabic) or "posted to the project chat". Copy / New / Close | meeting_sheet.dart:70-91, 169-210 | "Stop & finish" | B-198, A-174 |
| K4A-165 | Audit & consistency | Audit / Observer screen | 12 s silent reload. Observer ON/off, silence gap (default 30), Run now (result: healed/flagged/debounced), open issues, violations log (newest 60, scope-answer highlighted) | screens/audit_screen.dart:8-206 | nav "Audit" | A-104, C-028 |
| K4A-166 | Auth & security | Login screen | Email (prefilled with the owner email, not copied), password. Anchor mode adds the desktop Code field + "Get code" and a hint about the desktop badge. Sign in, Forgot password. Face ID button when pending; "Face ID unavailable" note | screens/login.dart:10-205 | gate closed | A-143, A-146, A-147 |
| K4A-167 | Auth & security | Auto Face ID prompt + 2FA dialog | Prompts Face ID automatically on open if pending and available. Direct-mode 2FA dialog with a dev hint for the code | login.dart:26-41, 76-95 | screen open / 2FA response | A-147, A-144 |
| K4A-168 | Build, packaging, run & clients | Settings: profiles + editor + test | Radio list of profiles (brain/anchor URLs). Editor for brain URL, anchor URL, X-Odin-Token, ODIN_API_KEY, ANCHOR_API_KEY (obscured) and direct/anchor mode; **saves on every keystroke**. Test-connection output | screens/settings_screen.dart:10-194 | nav "Settings" | A-134 |
| K4A-169 | Auth & security | Account section | Signed-in identity, Sign out, change password, toggles: 2FA, require verified email, Face ID first access | screens/account.dart:8-104 | Settings | A-143, A-144, A-145, A-147, A-149 |
| K4A-170 | Scheduling & notifications | Shaking notifications bell | Rotational shake animation while `pulse`; red icon | screens/notifications_panel.dart:8-46 `NotifShakeBell` | `notifPulse` | no |
| K4A-171 | Scheduling & notifications | Notifications panel | Refreshes on open; "Mark all read"; severity colours (critical / attention / info); body; "project · tap to open". Tap → mark read + redirect to the project | notifications_panel.dart:48-180 `showNotifications`, `_NotifPanel` | bell tap | C-032 |
| K4A-172 | Scheduling & notifications | Schedule editor | daily / weekly (weekday chips; empty = all days) / monthly (days 1–31). Multiple times with a time picker (＋ time, delete). Timezone list defaulting to Africa/Cairo. Saves `{kind:'calendar', times, tz, weekdays\|monthdays}` | screens/schedule_editor.dart:5-163 | Edit-schedule icons | C-020 |
| K4A-173 | Per-project features & integrations | Agent detail | Avatar + working pill; catalog role match (technical/operational, ready / needs setup, missing connections warning); live activity; last 12 operations | screens/agent_detail.dart:9-155 | tap member / live agent | C-003, A-116 |
| K4A-174 | Build, packaging, run & clients | Generic Projects screen (type-driven) | Cards from `ui_projects`: chip, category + icons (streaming-voice 🎙️, notification 🔔), counts, controls play / run-once / export (open project) / cadence / period / timeout (default 300 s); 'on-demand' if none | screens/ui_projects.dart:8-152 | nav "Projects" | B-043, B-049, C-031 |
| K4A-175 | Build, packaging, run & clients | Generic Agents screen | Agents grouped by type with chip, group, role, "used by N projects", control badges voice/export | screens/ui_agents.dart:8-128 | nav "Agents" | B-043, C-031 |
| K4A-176 | Safety & approvals | Approval center | Lists pending approvals (kind, project, summary, detail) with Approve / Reject. Text: "Nothing touches your code, config, or the VM until you approve it here." | screens/approvals.dart:8-114 | nav "Approvals" | C-011, B-008 |
| K4A-177 | Per-project features & integrations | Archived projects | List with Unarchive and Delete (confirm: "Removes the project + its chats (files on disk are kept)") | screens/archived.dart:9-112 | nav "Archived" | A-084, C-002 |
| K4A-178 | Build, packaging, run & clients | Guide tabs single source of truth | `kBellTabs` = 11 tabs: Story, Caching, Klaviyo, Veeqo, Anchor, Changes, Tests, Links, Live Meeting, Deploy, Security SOC; the badge equals the count | screens/bell.dart:6-11 | — | A-125 |
| K4A-179 | Build, packaging, run & clients | Animated "New in Odin" guide panel | Invite view → tabbed details; fade/scale/stagger animations; animated Story (shared context) and Pipeline (TP → Anchor → Local → Agents → Klav/VQ, result/webhook return) painters | bell.dart:13-389, 751-780 | Guide icon / ⋮ Guide | A-125 |
| K4A-180 | Other | Guide content tabs | Caching (cached_modules reuse, add-only-proven), Klaviyo/Veeqo connect docs and live numbers, Anchor flow/endpoints/lifecycle/ports, Changes, E2E tests list, important files/links, Live Meeting tutorial, DevOps Deploy tutorial, RedBerry SOC (8 agents, daily 11 PM NY, API list) | bell.dart:391-749 | Guide tabs | A-125, B-204, A-227, A-173 |
| K4A-181 | Structural | Defensive data models | Health (isClaude), Project (periodic enabled/cadence, `avatarFor`), Role, Connector (connected), CompanyAgent, Activity (key pid:agent), Operation, AnchorRequest (`isTerminal` = finished/failed/cancelled) | models/models.dart:1-201 | API parsing | A-129, A-176 |
| K4A-182 | Structural | Design tokens + role colours/glyphs + anchor status colours | Mirrors desktop theme.css; `avatarKey` normalises 'project cto' / 'cto brain' | theme.dart:3-131 `Odin` | all UI | partial: A-127 |
| K4A-183 | Per-project features & integrations | Project type taxonomy (19 types, tech/operational) | `kTypeMeta` mirrors desktop TYPE_META (web … fulfillment) + `typeByKey` | theme.dart:133-169 | new project, grouping, icons | C-003 |
| K4A-184 | Structural | Shared widgets | GlassCard, Pill (removable), StatusDot, Kpi, SectionTitle, OdinButton, EmptyHint | widgets.dart:4-116, 194-232 | all UI | no |
| K4A-185 | Orchestration core | Heartbeat avatar = really working | Pulsing ring + glow only when `active` | widgets.dart:118-192 `Avatar` | activity | A-082, B-119 |
| K4A-186 | Voice | Device TTS layer | Lazy engines; `SpeechText` cleanup; Arabic script → ar-SA else en-US; rates 0.58 / 0.54; web goes to the Web Speech API; stop; never throws | services/voice.dart:23-68 `Voice.speak`, `stopSpeaking` | voice replies | A-170, A-171 |
| K4A-187 | Voice | Device STT layer | Lazy init. Locale resolved against installed locales (en/ar, platform format). Fresh session per start. listenFor 30 s, pauseFor 4 s, partial results, cancelOnError; `cancel`, `ttsDiag` | voice.dart:70-147 | mic | A-170, A-171 |
| K4A-188 | Voice | Speech text normaliser | Code blocks → "code block"; links → text; URLs → "link"; strips headings, bullets, emphasis, pipes, emoji and symbols (keeps Arabic punctuation); 1,500-char cap; `isArabic` | services/speech_text.dart:5-59 | TTS | partial: A-171 (listed as plan; built), A-110 |
| K4A-189 | Voice | Web Speech synthesis bypass | Uses `speechSynthesis` directly (flutter_tts web stalls): cancel queue, pick a matching voice, rates 1.15 (ar) / 1.08 (en), diagnostics | services/speech_web.dart:1-44; speech_web_stub.dart | web TTS | partial: A-171 |
| K4A-190 | Orchestration core | SSE client (io + web + stub) | io: line parser on `event:token` / `data:{t}`, stops on done/error. web: EventSource with `?token=` (headers impossible). stub throws so callers fall back | services/sse.dart, sse_io.dart, sse_web.dart, sse_stub.dart | `streamScope` | B-109 |
| K4A-191 | Auth & security | Biometric abstraction | local_auth `canCheckBiometrics \|\| isDeviceSupported`; authenticate (biometricOnly false, stickyAuth); web stub returns false | services/biometric*.dart | Login | A-147 |
| K4A-192 | Scheduling & notifications | Local OS notifications | flutter_local_notifications channel `anchor_updates` (high importance) on Android/iOS; no-op on web | services/notifications*.dart | `_detect` | A-133 |
| K4A-193 | Voice | Web meeting iframe / report opener | `registerMonitor` registers an iframe platform view (allow microphone/autoplay) of `<brainBase>/meeting_monitor.html?pid`. `brainBase` = localStorage `odin.base` or `http://localhost:8000` (so deployed web points at the viewer's localhost). `openReport` opens a new tab. Mobile stub: `canOpenMonitor=false` | services/web_open.dart, web_open_stub.dart | meeting / export | B-200 |
| K4A-194 | Other | Recording path helper + `record` dependency (unused) | `tempRecordPath()` builds an `.m4a` temp path; no caller; the `record` package is unused | services/recpath*.dart; pubspec.yaml:28 | none | no |
| K4A-195 | Build, packaging, run & clients | pubspec | Flutter ≥3.27 / Dart ≥3.6. Deps: http, provider, shared_preferences, intl (unused), flutter_local_notifications, flutter_tts, speech_to_text, local_auth, image_picker, file_picker, record, audioplayers, cross_file. Launcher icons (android adaptive bg #0E1320, ios remove_alpha, web) | odin_app/pubspec.yaml:1-55 | `flutter pub get` / `dart run flutter_launcher_icons` | D-017 |
| K4A-196 | Build, packaging, run & clients | Web shell | `$FLUTTER_BASE_HREF` base, PWA meta (apple-mobile-web-app, theme colour), manifest, inline Ω splash removed on `flutter-first-frame`, `flutter_bootstrap.js` | odin_app/web/index.html:1-50 | web load | partial: A-141 |
| K4A-197 | Build, packaging, run & clients | iOS Info.plist | Display name Odin. Mic + speech-recognition usage strings ONLY. **No NSCameraUsageDescription / NSPhotoLibraryUsageDescription** although image_picker camera/gallery is used | odin_app/ios/Runner/Info.plist:9-10, 69-72 | iOS build | partial: A-170 (MFI claims camera/photo keys exist) |
| K4A-198 | Build, packaging, run & clients | Android manifest | Label Odin, singleTop. **No INTERNET, RECORD_AUDIO or CAMERA permission** declared (release builds would have no network) | odin_app/android/app/src/main/AndroidManifest.xml:1-45 | Android build | partial: D-016 |
| K4A-199 | Synchronization & Anchor | Anchor-mode coverage gaps (direct-only calls) | These call `_api` and throw in anchor mode, so on web/mobile production they fail silently or show errors: approvals, archived, project detail (`project`, rules, schedules, operations, plan, runStatus), team edits, add mapping, schedule editor save, run team / sync / deploy, operations provide/stop, company agents and connectors add/remove, validate agents, intake suggest, new-project create, scope summary/rename, monitor feed, capability dialog, uploads | anchor_api.dart:284-543, 610, 672-694 | anchor-mode UI | no |
| K4A-200 | Other | Unused API / state surface | `auditConfig`, `stats`, `agents(pid)`, `uiProject`, `uiTypes`, `uiConnectors`, `suggestIdentifier`, `archiveProject`, `updateRule`, `approvalsCount`, `scopeMessagesRich`, `companyChat`, `AppState.ask`/`companyChat`, `syncLabel`, `bellCount`, `Voice.cancel` / `ttsDiag` / `available` | various (see rows above) | none | no |

## 2. Not in MFI

Rows with no MFI match:

| ID | Capability |
|---|---|
| K4A-003 | Cursor-based DELTA sync (`since=`/`max_seq`, merge by id, sort by seq) |
| K4A-004 | Delta self-heal: full re-pull when the server `total` differs |
| K4A-008 | Logout (anchor `/manage/logout` or `/auth/logout`) |
| K4A-011 | 15 s HTTP timeout on all calls |
| K4A-016 | "offline · last synced X ago" label (computed, never rendered) |
| K4A-056 | Attachment URL resolution (`fileUrl`) |
| K4A-064 | Anchor COMMAND queue (`__command__` / sender `command`, 2 s poll, 3 min, silent timeout) |
| K4A-065 | Ten command kinds: mark_notif, delete_message, post_message, run_now, meeting_report, create_chat, rename_chat, create_project, delete_chat, clear_scope |
| K4A-082 | In-memory pool cache for instant reopen |
| K4A-090 | Unread pulse (bell shake trigger) |
| K4A-091 | Notification → open-project redirect |
| K4A-093 | 12 s fingerprint change detector (anchor counts + activity length) |
| K4A-096 | Crash-proof UI (`ErrorWidget.builder` + `runZonedGuarded`) |
| K4A-097 | TLS cert override for VM IP + anchor domain (mobile/desktop) |
| K4A-100 | Shell 12 s background loop |
| K4A-105 | Narrow ⋮ "Conversations" item does nothing (bug) |
| K4A-107 | Ports & Environment sheet with Dev↔Prod flip |
| K4A-109 | Environment chip |
| K4A-112 | Dead WhatsApp conversation-list code |
| K4A-117 | Forward messages to another conversation |
| K4A-119 | Sender tag "· via Conversations" |
| K4A-132 | Run-state banner WORKING / FINISHED |
| K4A-154 | Dashboard wide/narrow layouts |
| K4A-157 | Long-streaming project chunking confirmation dialog |
| K4A-159 | New-project sheet fails in anchor mode (bug) |
| K4A-162 | Searchable Help & Testing Guide (Docs screen) |
| K4A-170 | Shaking notifications bell |
| K4A-184 | Shared widget kit |
| K4A-194 | Unused recording helper / `record` dependency |
| K4A-199 | Anchor-mode coverage gaps (direct-only calls fail in production) |
| K4A-200 | Unused API / state surface |

Partial matches: MFI touches the area, but the specific behaviour is missing or contradicted.

| ID | Gap |
|---|---|
| K4A-002 | `X-Odin-Client` and `X-Manage-Token` headers (A-154 is listed as PLANNED) |
| K4A-005 | Manage request-code: built in the client, but MFI A-154 says PLANNED |
| K4A-006 | Same as K4A-005, for Manage login |
| K4A-018 | Mark-read through the anchor command |
| K4A-031 | HubSpot `/hubspot/overview` route |
| K4A-108 | HubSpot chip |
| K4A-072 | Anchor API key hard-coded in client source |
| K4A-073 | v3 profile-key bump |
| K4A-075 | `ODIN_ANCHOR` dart-define is listed by MFI as a selector but never read by the code |
| K4A-076 | Fail-closed auth policy |
| K4A-083 | Anchor-routed chat create/rename |
| K4A-084 | Anchor-routed project create |
| K4A-085 | Anchor-routed clear/delete; direct mode cannot clear non-chat scopes |
| K4A-104 | Responsive drawer / ⋮ layout |
| K4A-116 | Multi-select copy/forward/delete |
| K4A-121 | Client-side meeting heuristic vs. server gating |
| K4A-126 | Lazy load (MFI has it as PLAN) |
| K4A-134 | Client capability-gap 4-way dialog with `⟦resolve⟧` messages |
| K4A-147 | Recurring card with pulse |
| K4A-158 | Unknown-agent create/pick/remove gate |
| K4A-182 | Design tokens |
| K4A-188 | Speech normaliser: built, but MFI A-171 calls it a plan |
| K4A-189 | Web Speech synthesis bypass: built, but MFI A-171 calls it a plan |
| K4A-196 | Web splash/PWA shell |
| K4A-197 | iOS plist lacks camera/photo keys; contradicts A-170 |
| K4A-198 | Android manifest lacks INTERNET/RECORD_AUDIO/CAMERA |

## 3. Requested-category confirmations

**(a) Every screen and user action: FOUND**
- **Chat:**
  - Normal-mode ChatView: chat_screen.dart:19-696.
  - Conversations: whatsapp.dart:156-881.
  - Send, dictate, voice replies, run now, export, meeting, summary, rename, capability dialog.
- **Projects:**
  - dashboard.dart:494-606.
  - project_detail.dart:11-758: edit, mapping, team, rules, schedules, ops.
  - new_project.dart: create, suggest, unknown-agent gate.
  - ui_projects.dart; archived.dart.
- **Agents:**
  - agent_detail.dart.
  - ui_agents.dart.
  - Dashboard roster, company agents, live agents: dashboard.dart:192-367.
- **Approvals:** approvals.dart:8-114 (approve/reject); schedule Approve/Skip at project_detail.dart:309-325.
- **Notifications:** notifications_panel.dart:48-180; bell shake at :8-46; guide bell at bell.dart; banner at shell.dart:870.
- **Settings:** settings_screen.dart:10-194 (profiles, editor, test connection).
- **Auth:**
  - login.dart: password, desktop code, Face ID, 2FA, forgot.
  - account.dart: change password, security toggles, sign out.
  - Logout: shell.dart:578-608.
- **Voice:**
  - services/voice.dart, speech_text.dart, speech_web.dart.
  - meeting_sheet.dart.
  - Mic/speaker buttons in both chat views.
- **Anchor:** anchor_screen.dart (counts, lifecycle, requests, send request).
- **Environment profiles:**
  - config.dart:13-125.
  - settings_screen.dart.
  - Ports sheet at shell.dart:662-774; Docs "Switch" at docs.dart:142.
- **Others:** Audit (audit_screen.dart), Docs/Help (docs.dart), HubSpot chip (shell.dart:776).
- `home_screen.dart` and `projects_screen.dart` are empty stubs.

**(b) Live sync with desktop/web, and offline behaviour: FOUND**
- **How it syncs: polling only, plus cursor delta. There is no push.**
  - Open chats re-read every 5 s: whatsapp.dart:364; chat_screen.dart:132.
  - Reads use the cursor delta `/anchor/v1/pool/{scope}?since=<lastSeq>` with `max_seq`, merge by id and self-heal on a `total` mismatch: anchor_api.dart:49-81.
  - Shell runs a 12 s change detector (anchor counts + activity length) and notifications refresh: shell.dart:60-67; app_state.dart:580-596.
  - HubSpot chip polls every 60 s; Audit screen every 12 s.
- **Anchor path:**
  - Reads come from the anchor mirror (`/anchor/v1/mirror/{key}`, `/anchor/v1/projects`, `/pool`).
  - Writes go through the anchor request queue. Chat uses `sender:'chat'`, polled every 2 s for up to 8 min. Commands use `project:'__command__'`, polled every 2 s for up to 3 min.
  - The desktop's poller (not in these files) executes them on the brain and mirrors the results back.
- **Offline behaviour:**
  - If the anchor is unreachable, `offline=true` and every cache is wiped (no stale data), with an 800 ms visible retry spinner: app_state.dart:437-484.
  - Dashboard shows "You are offline / Try again": dashboard.dart:107-139.
  - Chat sends fail with "(offline — could not reach the anchor)".
  - Shown conversations are never wiped by an empty read.
  - `lastSync` staleness is captured, but the "offline · last synced X ago" label is never displayed (app_state.dart:230-242).
  - There is no offline write queue or durable local cache; `poolCache` is memory-only.

**(c) WhatsApp-clone mode and other clone features: FOUND**
- **Conversations mode** is toggled from the always-visible top-bar forum icon (shell.dart:545-554). It renders `Conversation` for the sidebar-selected scope (whatsapp.dart:78-88).
- **Features** (whatsapp.dart):
  - Cached instant open; 5 s live sync.
  - Reply (group post with `reply_to`).
  - Long-press multi-select with copy, forward and delete.
  - Copy all.
  - Camera, gallery and file attachments.
  - Image bubbles; voice-note playback with transcript.
  - "Load earlier" lazy list.
  - Sender tagging.
- **Gaps:**
  - The narrow ⋮ "Conversations" item is unhandled (shell.dart:594-604).
  - The old conversation-list code is dead.
  - Attachments fail in anchor mode because the upload is direct-only.
- **No other clone modes found.**

**(d) UDP / websocket / socket usage: NOT FOUND**
- No UDP, WebSocket, `RawDatagramSocket`, `Socket` or `web_socket` usage in any assigned file.
- Transport is plain HTTP(S) request/response (`package:http`) plus Server-Sent Events: `http.Client` stream on io, `EventSource` on web (sse_io.dart, sse_web.dart). SSE is used in direct mode only.

**(e) Mobile-specific (iOS) features, push/notifications, background: partly FOUND**
- **FOUND:**
  - Face ID / biometric unlock via local_auth (biometric_mobile.dart; app_state.dart:114-117; login.dart:37-41).
  - On-device STT (SFSpeechRecognizer via speech_to_text) and TTS (flutter_tts): voice.dart.
  - Native meeting sheet: meeting_sheet.dart.
  - Camera and photo picker: whatsapp.dart:499-507.
  - Local OS notifications via flutter_local_notifications on new terminal anchor requests (notifications_mobile.dart; app_state.dart:540).
  - Self-signed cert override: cert_override_io.dart.
  - Info.plist mic and speech usage strings.
- **NOT FOUND:**
  - Remote push (APNs/FCM), background fetch or background tasks. All polling uses in-app `Timer`s that run only while the app is in the foreground.
  - iOS camera/photo usage keys in Info.plist.
  - Android INTERNET, RECORD_AUDIO and CAMERA permissions.

**(f) Environment selection (dev/prod/anchor) and config: FOUND**
- **Profiles and persistence:** three default profiles (config.dart:60-86): Local direct, local anchor on :9100, and Deployed anchor at `https://anchor.odinmarkets.com/odin-anchor`. Persisted under the `odin.profiles.v3` / `odin.selected.v3` keys.
- **Build flag:** `--dart-define=ODIN_FORCE_ENV=production|phase2` selects a profile at launch (app_state.dart:32-44).
- **Runtime fallback:** if the local brain is unreachable, the app switches itself to the Deployed profile (app_state.dart:458-470).
- **Manual switching:**
  - Settings profile list and editor (URLs, token, two API keys, direct/anchor mode).
  - Ports sheet "Use Development / Use Production" (shell.dart:662-774).
  - Docs "Switch" button.
- **Hard guarantee:** anchor mode refuses to build any backend URL (anchor_api.dart:133-138).
- **Not used:** the `ODIN_ANCHOR` dart-define is documented but never read.
- **Secrets in source:** the ANCHOR_API_KEY literal is in config.dart:77, 84, and a VM IP is in cert_override_io.dart:9. Both are named here, not copied.


<!-- ==================== PART K4B ==================== -->

# K4B — Desktop (Electron + React) and static dashboard capability inventory

Scope read completely: `desktop/src/{App.jsx, views.jsx (2961 lines), ChatPanel.jsx, Conversations.jsx, api.js, ui.jsx, main.jsx, theme.css}`, `desktop/electron/{main.cjs, preload.cjs}`, `desktop/package.json`, `desktop/vite.config.js`, `desktop/index.html`, and every file in `dashboard/` (`index.html, console.html, mobile.html, audit.html, meeting_monitor.html, artifact.html, odin-md.js, README.md`).
`desktop/build/*.cjs`: **the folder does not exist in this snapshot** (so `afterpack-sign.cjs` and `icon.png`, both referenced by package.json, could not be read).
Secret values seen in source are named only (never copied).

## 1. Capabilities found

| ID | Category | Capability | What it does | Evidence | Triggered by | In MFI? |
|---|---|---|---|---|---|---|
| K4B-001 | Build, packaging, run & clients | ODIN_DEV dev mode | `ODIN_DEV=1` makes Electron load Vite `http://localhost:5173` and open docked DevTools; otherwise loads `dist/index.html` from file:// | electron/main.cjs:14,141-146 `createWindow` | `npm run dev` | A-206, D-001 |
| K4B-002 | Build, packaging, run & clients | ODIN_PORT / ODIN_ANCHOR env | Backend port (default 8000) and online anchor URL used by the poller (default production anchor) | main.cjs:15,17 | env | D-008 |
| K4B-003 | Build, packaging, run & clients | Backend root resolution | ODIN_ROOT → userData/root.txt (must contain server/run.sh) → repo dev root (../..) → ~/Desktop/AiAgentWorkSpace/Odin-Orchestrator | main.cjs:23-36 `backendRoot` | app start, poller, request page | A-238, D-008 |
| K4B-004 | Other | `isUp()` health probe (dead code) | GET 127.0.0.1:PORT/health 1.2s timeout — defined but never called; app ALWAYS spawns a fresh backend (comment l.213) | main.cjs:38-44 `isUp` | none (unused) | no (D-008 claims a health check happens) |
| K4B-005 | Build, packaging, run & clients | Spawn backend | `bash server/run.sh` detached own process group; env USE_VOICE default 1, PORT, Homebrew/~/.local PATH restored (macOS GUI PATH stripped) | main.cjs:46-68 `startBackend` | app.whenReady | A-011, D-008 |
| K4B-006 | Build, packaging, run & clients | Kill backend process group | SIGKILL to -pid and child, once | main.cjs:70-79 `killBackend` | exit paths | A-011 |
| K4B-007 | Synchronization & Anchor | Production poller spawn | Prod only (skipped when ODIN_DEV): runs `.venv/bin/python` (or python3) `-u local_poller_http.py --anchor <ONLINE_ANCHOR> --interval 4` in server/ | main.cjs:86-102 `startPoller` | app.whenReady | A-238, A-182, D-008 |
| K4B-008 | Synchronization & Anchor | Poller self-heal | On poller exit, restart after 3s unless `_pollerKilled` | main.cjs:106-111 | poller exit event | A-186 |
| K4B-009 | Build, packaging, run & clients | Kill poller | SIGKILL process group, sets `_pollerKilled` | main.cjs:117-125 `killPoller` | exit paths | A-186 |
| K4B-010 | Build, packaging, run & clients | Bullet-proof cleanup on every exit | `cleanupAll` (backend+poller+request page) on window-all-closed, before-quit, will-quit, process exit, SIGINT, SIGTERM, uncaughtException | main.cjs:127,222-229 | OS / app events | A-011 |
| K4B-011 | Auth & security | Window hardening | 1440×920 (min 1080×720), hiddenInset titlebar, contextIsolation true, nodeIntegration false, preload bridge | main.cjs:129-139 `createWindow` | app start | no |
| K4B-012 | Auth & security | External links to system browser | `setWindowOpenHandler` opens every new-window URL with shell.openExternal and denies in-app windows | main.cjs:140 | window.open / target=_blank (report export, attachments) | no |
| K4B-013 | Build, packaging, run & clients | Native folder picker (create location) | IPC `pick-folder` openDirectory+createDirectory | main.cjs:150-156 | window.odin.pickFolder | A-122 |
| K4B-014 | Build, packaging, run & clients | Native multi-folder / multi-file pickers | IPC `pick-folders`, `pick-files` | main.cjs:157-164 | window.odin.pickFolders/pickFiles | A-121 |
| K4B-015 | Synchronization & Anchor | One-click local Request page | IPC `start-request-page`: checks root has anchor_sim.html, probes :ODIN_REQ_PORT (default 9104), else spawns `python -m http.server 9104 --bind 127.0.0.1` detached, waits 800ms, opens `/anchor_sim.html?env=prod` in browser; idempotent | main.cjs:166-200 | RequestPageTab "Run it & open" | D-008 (preload name only); no row for the IPC behaviour (A-196 is sim_server.py) |
| K4B-016 | Build, packaging, run & clients | Kill request-page server | SIGKILL group | main.cjs:201 `killReqpage` | cleanupAll | no |
| K4B-017 | Build, packaging, run & clients | Single-instance lock | Second launch quits (no second backend / port fight) | main.cjs:204-206 | app launch | A-011 |
| K4B-018 | Auth & security | Permission auto-grant (all) | `setPermissionRequestHandler` returns true for EVERY permission (ternary yields true in both branches), not only mic | main.cjs:209-211 | any web permission request | no |
| K4B-019 | Build, packaging, run & clients | Re-create window on activate | macOS dock re-open | main.cjs:218 | app activate | no |
| K4B-020 | Build, packaging, run & clients | Preload bridge `window.odin` | pickFolder, pickFolders, pickFiles, startRequestPage, isDesktop | electron/preload.cjs:4-11 | renderer | D-008, A-121, A-122 |
| K4B-021 | Build, packaging, run & clients | npm dev script | concurrently vite + wait-on tcp:5173 then `ODIN_DEV=1 ELECTRON_ENABLE_LOGGING=1 electron .` | package.json:11 | `npm run dev` | D-001, A-206 |
| K4B-022 | Build, packaging, run & clients | npm build / dist / pack | build = vite build; dist = `VITE_ODIN_ENV=production vite build && electron-builder --mac dmg`; pack = build + `--dir` (no prod env) | package.json:12-14 | npm scripts | D-002, D-003, D-004 |
| K4B-023 | Testing | npm e2e / e2e:quick | `python3 ../tests/e2e.py [--quick]` | package.json:15-16 | npm scripts | D-007, T-38 |
| K4B-024 | Build, packaging, run & clients | electron-builder config | appId ai.odin.orchestrator, productName Odin, output release/, buildResources build/, files dist+electron+package.json, mac dmg, category developer-tools, icon build/icon.png, identity null (unsigned), dmg title, afterPack ./build/afterpack-sign.cjs (file absent in snapshot) | package.json:33-57 | `npm run dist/pack` | A-238, D-005 |
| K4B-025 | Build, packaging, run & clients | Vite config | base "./" (file:// loading), dev port 5173 strictPort, outDir dist, emptyOutDir | vite.config.js:5-10 | vite | D-002 |
| K4B-026 | Build, packaging, run & clients | React entry | index.html (#root, title "Odin — CTO Brain") → main.jsx renders `<App/>` + theme.css | index.html:1-12; main.jsx:1-6 | load | B-025 |
| K4B-027 | Build, packaging, run & clients | Backend base URL + token store | BASE from localStorage `odin.base` (default localhost:8000), `setBase/setToken/getBase`; token in `odin.token` | api.js:2-7 | Settings save | A-123 |
| K4B-028 | Auth & security | Token on every call | `X-Odin-Token` header on JSON calls/uploads; `?token=` appended for SSE, TTS audio, STT | api.js:9-17,124-125,176,193,218,231-233 `headers`,`qtoken` | every API call | A-150, D-010 |
| K4B-029 | Per-project features & integrations | Meeting capability + monitor URL | `GET /meeting/capable?pid`; monitor URL `/meeting_monitor.html?pid=` | api.js:32-33 | ChatPanel | B-199, C-042 |
| K4B-030 | Per-project features & integrations | Report URL | `/project/report?pid&fmt` (any project, generated on the fly) | api.js:37 | export menu | C-018, A-106 |
| K4B-031 | Scheduling & notifications | Notifications client | GET /notifications?unread&limit=100, /notifications/count, POST /notifications/read {id} or {all:true}; failures → empty | api.js:39-42 | bell / recurring card | C-032 |
| K4B-032 | Audit & consistency | Audit client | /audit/status, /audit/scan, POST /audit/run?force=true, /audit/violations?limit, POST /audit/config?enabled&silence_minutes | api.js:44-48 | AuditView | C-028, A-104 |
| K4B-033 | Middleware & DB registry | Generic UI contract client | /ui/projects, /ui/project/{pid}, /ui/agents, /ui/connectors, /ui/types | api.js:50-54 | grids, badges | C-031, B-043 |
| K4B-034 | Other | Duplicate object keys in `api` (bug) | `schedules` and `updateSchedule` defined twice; later ones win: `updateSchedule(tid,b)` posts `b` raw, so ScheduleEditor sends the schedule object as the body instead of `{schedule}` (first definition's shape) | api.js:56-57 vs 138-141 | ScheduleEditor save | no |
| K4B-035 | Orchestration core | Project/intake/capability client | /projects, /projects/{pid}, POST /projects, /projects/intake, /projects/intake/readiness, /agents/validate, /projects/{pid}/capability, POST /projects/{pid}/agents (force add), /projects/{pid}/run-now {prompt,cid}, /capabilities, /agents/all | api.js:59-69 | UI | C-002, C-004, C-005, C-003, C-013 |
| K4B-036 | Middleware & DB registry | Company agents + connectors client | /company/agents GET/POST/DELETE; /connectors GET/POST/DELETE | api.js:70-75 | dashboard panels | C-005, C-010 |
| K4B-037 | Per-project features & integrations | HubSpot client | /hubspot/status, POST /hubspot/run, POST /hubspot/ask | api.js:77-79 | HubSpotBadge | C-041 |
| K4B-038 | Orchestration core | Project ops client | update, delete, archived, archive/unarchive, mappings, plan, rules CRUD, sync/run, deploy/run | api.js:80-92 | ProjectView | C-002, C-007, C-008, C-012 |
| K4B-039 | Middleware & DB registry | Agents/stats/models client | project agents CRUD, suggest, update, rule, stats, /models, /models/set {scope,model} | api.js:94-104 | Member/Project views | C-006, C-009, C-015 |
| K4B-040 | Synchronization & Anchor | Standalone shared chats client | /chats list/create, /chats/rename?scope, DELETE /chats/{scope} — same list as web+mobile | api.js:108-111 | sidebar CHATS | C-017 |
| K4B-041 | Synchronization & Anchor | Scope pool client | scope chats CRUD, /scope/summary, /scope/message (post without AI turn), /scope/upload (multipart), fileUrl, /scope/messages (whole pool merged), message delete, /scope/children | api.js:112-134 | chat views | C-016 |
| K4B-042 | Orchestration core | Activity, schedules, anchor admin, types/roles, periodic gate, infra, approvals, run, operations clients | /activity, /schedules CRUD+pending/approve/skip, /anchor/v1/admin/{requests,counts,config}, /project-types, /roles, /infra/connect-test, /approvals(+count, approve, reject with note), orchestrate start/status/stop, /operations (list, latest, get, stop, provide), deploy/operation, deploy/request | api.js:136-171 | UI | C-019, C-020, C-026, C-003, A-042, C-011, C-013, C-014, C-012 |
| K4B-043 | Orchestration core | Scoped chat SSE stream | EventSource `/scope/stream?scope&text&lang&cid`; events status, token, delegate, approval, capability_gap, done, error; closes on done/error | api.js:175-189 `streamScope` | send in any chat | C-016 (capability_gap event: no) |
| K4B-044 | Orchestration core | Team-run SSE stream | EventSource `/projects/{pid}/orchestrate?goal`; events status, plan, delegate, token, step_done, approval, done, error | api.js:192-203 `streamOrchestrate` | TeamRun Go | A-066 |
| K4B-045 | Voice | Backend-only TTS, one voice at a time | `speak` → /voice/tts with per-language speed (localStorage odin.speed.en default 1.0, odin.speed.ar default 1.15); stops previous audio; never OS voice | api.js:206-224 | autospeak after reply | A-161, A-166, A-167 |
| K4B-046 | Voice | Mute | localStorage `odin.mute`; mute stops current speech | api.js:210-211 | topbar Voice on/off | A-166 |
| K4B-047 | Voice | STT upload | multipart `file` to /voice/stt?language[&fast=1]; surfaces server `detail` on error | api.js:226-242 `transcribe` | mic | A-164, C-043 |
| K4B-048 | Build, packaging, run & clients | Avatar + heartbeat kit | Role map cto/frontend/backend/devops/security/qa/database/generic with glyphs/colours; `active` = animated | ui.jsx:5-29 | everywhere | A-082, A-127 |
| K4B-049 | Build, packaging, run & clients | StatusDot / Modal / UsageBar | Shared UI primitives; Modal body scrolls so footer always reachable | ui.jsx:31-80 | everywhere | A-127 |
| K4B-050 | Build, packaging, run & clients | Markdown renderer (desktop) | code fences, tables, headers, lists, bold/italic/code, HTML-escaped | ui.jsx:83-121,135-137 | assistant messages, plan panel | A-117, A-120 |
| K4B-051 | Voice | toSpeech cleaner (desktop) | strips code blocks/markdown/pipes for TTS | ui.jsx:124-133 | autospeak | A-110 (dashboard twin) |
| K4B-052 | Build, packaging, run & clients | Sidebar navigation | Company, PROJECTS list, New project, CHATS section, Archived, Anchor Connect, Audit, Projects grid, Agents grid, Settings, status dots | App.jsx:84-133 | click | A-115, A-084 |
| K4B-053 | Build, packaging, run & clients | Collapsible sidebar persisted | 264px ↔ 62px, stored in localStorage `odin.nav` | App.jsx:19,27,83,92-93 | ‹ › button | no |
| K4B-054 | Synchronization & Anchor | Standalone chats in sidebar | New (window.prompt name), rename ✎, delete ✕ ("Delete this chat everywhere?"), open in Company chat area | App.jsx:43-47,104-119 | sidebar | C-017 |
| K4B-055 | Synchronization & Anchor | Health poll + self-heal reload | every 4s: /health → clear error, reload projects + chats; error pill "Connecting to the backend… (~20s voice models)" | App.jsx:39-61 | interval | no |
| K4B-056 | Orchestration core | Live activity poll | every 2.5s /activity → activeSet `pid:agent` + task/phase map driving heartbeats | App.jsx:63-76 | interval | A-068, C-019 |
| K4B-057 | Build, packaging, run & clients | Breadcrumbs | Company / project / member, clickable | App.jsx:137-141 | click | no |
| K4B-058 | Build, packaging, run & clients | Scrollable top bar with ‹ › arrows | toolbar never clips; arrows scroll 70% width | App.jsx:28-37,142-161; theme.css:86-108 | click | no |
| K4B-059 | Build, packaging, run & clients | Conversations mode toggle | swaps whole content to ConversationsView (same pool) | App.jsx:20,149-150,165 | topbar button | no |
| K4B-060 | Build, packaging, run & clients | Refresh button | bumps refreshSignal, reloads projects + health | App.jsx:156 | click | no |
| K4B-061 | Orchestration core | Create → auto kickoff | after creation open project and set kickoff for 6s so TeamRun autostarts with the brief | App.jsx:78,194-195; views.jsx:947-949 | project created | no |
| K4B-062 | Build, packaging, run & clients | Global watchers mounted | OutcomeToasts, OperationFinishWatcher, PeriodicApprovalWatcher always mounted | App.jsx:200-204 | app root | no |
| K4B-063 | Build, packaging, run & clients | Ports & Env map | constant PORT_MAP dev (8000/9100/9104/9300/8080 local) vs prod (anchor + web on anchor.odinmarkets.com via nginx 443, brain local) shown in a table | App.jsx:215-237,425-462 `PortsModal` | 🗺 Ports & Env / EnvBadge | no |
| K4B-064 | Build, packaging, run & clients | Environment flip | PortsModal Apply writes odin.env, odin.anchor (+odin.prod.anchor) and reloads; backend base stays localhost:8000 in BOTH branches | App.jsx:428-434 | Apply button | no |
| K4B-065 | Build, packaging, run & clients | Always-visible env badge | PRODUCTION (green) / DEVELOPMENT (blue) from localStorage odin.env else `import.meta.env.VITE_ODIN_ENV` else development | App.jsx:328-345 `EnvBadge` | render | no |
| K4B-066 | Per-project features & integrations | Generic connector badges | /ui/connectors every 15s; one badge per connector with icon map + green/grey dot | App.jsx:245-271 `ConnectorBadges` | interval | no (API B-043/C-031) |
| K4B-067 | Per-project features & integrations | HubSpot badge + overview popup | /hubspot/status every 60s (dot green/red/amber); click runs /hubspot/run, popup shows portal, contacts, companies, deals, contacts this month, scope count, "scope needed" | App.jsx:272-326 `HubSpotBadge` | interval / click | no (API C-041) |
| K4B-068 | Synchronization & Anchor | Connecting-with-Anchor code indicator | polls `<anchor>/anchor/v1/manage/pending-code` every 4s with X-API-Key (prod → online anchor, dev → odin.anchor or :9100); blinks; modal shows email, password and code (expires ~10 min) with Copy buttons | App.jsx:351-423 `AnchorCodeIndicator`, `CopyRow` | interval / click | A-124 (MFI says PLANNED — it is built) |
| K4B-069 | Auth & security | Hard-coded credentials in renderer (finding) | `ANCHOR_KEY` (anchor API key) and `MANAGE_PASSWORD` (anchor Manage password) plus `MANAGE_EMAIL` are literal constants in App.jsx and therefore shipped inside the DMG bundle | App.jsx:351-353 | build | no |
| K4B-070 | Build, packaging, run & clients | Settings modal | Environment select (dev/prod presets), Backend URL, Anchor URL, Access token; Save writes odin.env, odin.anchor, odin.prod.base/anchor, base, token; reload | App.jsx:464-498 `SettingsModal` | ⚙️ Settings | A-123 (env + anchor fields: no) |
| K4B-071 | Build, packaging, run & clients | Conversations view list | Company + every project as a conversation (scopes company / project:<pid>) | Conversations.jsx:7-26 `ConversationsView` | Conversations mode | no |
| K4B-072 | Synchronization & Anchor | Conversation pool sync | gets/creates first chat of scope; polls /scope/messages every 3s unless recording/busy | Conversations.jsx:67-82 | interval | no |
| K4B-073 | Orchestration core | Plain message vs reply | plain text → streamScope to CTO (shows tokens); a reply → POST /scope/message with reply_to (group post, no AI turn); sender "Owner · via Conversations" | Conversations.jsx:40,83-100 `sendText` | Send | no (A-135 is the Flutter equivalent) |
| K4B-074 | Synchronization & Anchor | Attach file / voice note to pool | upload /scope/upload then post message with attachment (+transcript); MediaRecorder webm voice notes | Conversations.jsx:101-118 | 📎 / 🎤 | no |
| K4B-075 | Synchronization & Anchor | Select, copy, forward, delete messages | multi-select; copy lines; forward to any scope chosen via prompt (creates chat if none, tagged "(forwarded)"); delete per message | Conversations.jsx:42-65,124-137,155-158 | buttons | no |
| K4B-076 | Build, packaging, run & clients | Attachment rendering | image inline, audio player + transcript, file/zip link, reply quote | Conversations.jsx:141-161 | render | no |
| K4B-077 | Voice | EN/AR language switch in chat | header EN / ع toggle drives stream, STT, TTS, RTL placeholder | ChatPanel.jsx:8,426-429,509-510 | click | A-165 |
| K4B-078 | Synchronization & Anchor | Live chat pool sync (desktop) | every 3s (skips while streaming/recording) re-reads whole scope pool; replaces only if message COUNT differs; also refreshes chat list | ChatPanel.jsx:58-80 | interval | no |
| K4B-079 | Orchestration core | Run-state + stuck detector | for project scopes polls orchestrate/status; if running and no new message >5 min → STUCK info flag; never auto-stops | ChatPanel.jsx:66-76 | interval | no |
| K4B-080 | Orchestration core | WORKING / STUCK / FINISHED banner | coloured banner above project chat | ChatPanel.jsx:432-450 | state | no |
| K4B-081 | Synchronization & Anchor | Manual refresh "syncing…" | reloads chat list + whole pool (seq-sorted server side) | ChatPanel.jsx:120-127,385-389 `doRefresh` | ↻ | no (A-142 is Flutter) |
| K4B-082 | Scheduling & notifications | Run now (autonomous) | ▶ in project chat → POST run-now (no approval prompt), refreshes at 3/8/15s | ChatPanel.jsx:130-143,390-396 `runProjectNow` | ▶ | C-013 |
| K4B-083 | Orchestration core | Chat list newest-first, auto-create | sorts by updated; creates first chat if none | ChatPanel.jsx:97-110 | scope change | A-117 |
| K4B-084 | Orchestration core | Attach paths in message | prefixes `[Attached for you to use/consider: a | b]` (paths only, no upload) | ChatPanel.jsx:154-164,490-499 | ＋ menu | A-121 |
| K4B-085 | Orchestration core | Queue while busy | messages typed while streaming are queued and sent one by one after done/error; "N queued" pill; button label Queue | ChatPanel.jsx:30,161,219-225,507,516 | Send while busy | no |
| K4B-086 | Safety & approvals | Capability-gap dialog | on SSE `capability_gap`: 4 choices — CTO does it / embed recommended existing agent / expand an existing member's role (edit rules → updateAgent) / create custom role (name, role, rules; overlap warning) → addAgentForce; sends `⟦resolve⟧ …` prompt | ChatPanel.jsx:31-38,173-179,188-217,312-374 `resolveCapability` | SSE event | no |
| K4B-087 | Orchestration core | `⟦resolve⟧` prompt texts | injected texts: "Delegate this to X (they have the full shared pool)", "(role expanded; full shared pool)", "Handle this yourself, CTO (you have the full shared context)" | ChatPanel.jsx:194,202,211,213 | dialog Proceed | no |
| K4B-088 | Orchestration core | Real stop | closes EventSource (server terminates engine), appends "⏹ Stopped by you." | ChatPanel.jsx:228-238,514-515 | ⏹ Stop | no |
| K4B-089 | Voice | Whisper near-real-time dictation | MediaRecorder 500ms chunks; fast-model partial every 1.8s; accurate final on stop ("refining…"); errors visible; Web Speech not used | ChatPanel.jsx:243-286 `startWhisper` | 🎤 | A-164 (MFI says 0.9s) |
| K4B-090 | Voice | Start beep | 880Hz 0.12s tone when listening starts | ChatPanel.jsx:288-298 `startBeep` | mic start | no |
| K4B-091 | Voice | Draft lock | late dictation results can't refill input after send; send while recording stops dictation first | ChatPanel.jsx:43,155,159,265,277 | send | no |
| K4B-092 | Voice | Autospeak reply | speak(toSpeech(reply)) after done when autospeak | ChatPanel.jsx:181 | done | A-117, A-167 |
| K4B-093 | Build, packaging, run & clients | Copy message / copy all | per-message ⧉ and whole conversation copy with clipboard fallback | ChatPanel.jsx:45-51,381-384,459-462 | click | no |
| K4B-094 | Per-project features & integrations | Report export menu | 📄 PDF / DOCX / MD / PPTX opens /project/report in browser | ChatPanel.jsx:397-416 | 📄 | C-018, A-106 |
| K4B-095 | Build, packaging, run & clients | RTL auto-direction | Arabic range → rtl + right align | ChatPanel.jsx:454-457 | render | A-119 |
| K4B-096 | Orchestration core | Status rail | last 5 status steps while streaming | ChatPanel.jsx:468-478 | SSE status | A-117 |
| K4B-097 | Voice | Live-meeting popup | 🗣️ only if project meeting-capable; iframe meeting_monitor.html with mic/autoplay; closes on postMessage `meeting-close` then refreshes chat | ChatPanel.jsx:83-95,419-424,521-530 | 🗣️ | B-199, B-200, A-173 |
| K4B-098 | Other | groupChatsByDate (dead code) | computes Today/Yesterday groups but result never rendered (middle chat-list column removed) | ChatPanel.jsx:309,542-553 | none | A-117 (MFI still lists date sidebar) |
| K4B-099 | Scheduling & notifications | OS notifications | Web Notifications API (macOS) with permission request | views.jsx:12-18 `osNotify` | approvals, outcomes, periodic due | no |
| K4B-100 | Scheduling & notifications | Outcome dialogs | `odin-outcome` CustomEvent → top-centre cards; success auto-dismiss 9s, problems stay; also OS notification | views.jsx:22-60 `emitOutcome`,`OutcomeToasts` | run/operation end | no |
| K4B-101 | Scheduling & notifications | Global operation finish watcher | polls /operations every 2.5s; announces each terminal op once (done/stopped/failed); seeds silently on first pass; remembers last 200 ids in localStorage `odin.ops.announced` | views.jsx:66-98 | interval | no |
| K4B-102 | Safety & approvals | Approvals popup (Approval Center) | polls /approvals every 2.5s; OS notification per new request; topbar button blinks with count; ONE tabbed dialog; shows member, title, summary, recommended, fix plan, files (action/path/why), commands (where local/vm) | views.jsx:106-262 `ApprovalCenter` | interval / click | no (API C-011) |
| K4B-103 | Safety & approvals | Severity ordering | security (red, rank -1) > critical > caution (default) > routine (qa-recommendation) | views.jsx:134-145 | render | no |
| K4B-104 | Safety & approvals | Approve-all-safe excludes security | bulk approve only non-security; security must be decided individually | views.jsx:156-166,211-212,247 | button | no |
| K4B-105 | Safety & approvals | Approve / Reject single | POST approve/reject; closing the dialog decides nothing | views.jsx:147-155,213,248-251 | buttons | C-011 |
| K4B-106 | Per-project features & integrations | Azure VM status chip | /infra/connect-test on mount + every 60s + click; flips to bad only after 2 consecutive failures; reasons az-not-found / not-logged-in | views.jsx:265-304 `VmStatus` | interval/click | A-048, A-042 |
| K4B-107 | Build, packaging, run & clients | System status panel | projects count, agents live, API, engine, voice EN Kokoro/AR Coqui, VM, main model | views.jsx:307-329 `StatusPanel` | render | A-115 |
| K4B-108 | Orchestration core | Live agents card | only working agents incl. Project CTO; phase + task; click → member | views.jsx:332-358 `LiveAgents` | activity | A-082, A-068 |
| K4B-109 | Middleware & DB registry | Agent roster (all agents) | /agents/all every 5s (keeps last good), dedupe by name, project list, grouped Operational/Technical | views.jsx:364-411 `AgentRoster` | interval | no (API C-005) |
| K4B-110 | Middleware & DB registry | Company agents panel | list/remove, create name+role+rule (auto-added to every new project) | views.jsx:414-443 `CompanyAgents` | Create | A-076 |
| K4B-111 | Per-project features & integrations | Connectors panel | add name/type/API key (password field), status dot, remove | views.jsx:445-471 `Connectors` | Connect | A-077 |
| K4B-112 | Scheduling & notifications | Recurring & scheduled card | periodic projects list; red pulse when unread notifications (poll 12s); inline schedule editor | views.jsx:475-519 `RecurringCard` | render / ✎ | no |
| K4B-113 | Build, packaging, run & clients | Company dashboard layout | chat (sidebar-chosen scope, keyed remount) + collapsible right panel (roster, live, company agents, connectors, monitor, projects grouped by type with id, periodic pill, live count, avatars incl CTO, live phase) | views.jsx:521-617 `Dashboard` | default view | A-115 |
| K4B-114 | Orchestration core | Project ⋯ menu | Archive; Delete with confirm (chats removed, disk files kept) | views.jsx:624-638 `ProjectMenu` | ⋯ | A-084, C-002 |
| K4B-115 | Orchestration core | Archived page | Restore / permanent delete | views.jsx:641-664 `ArchivedView` | nav Archived | A-084 |
| K4B-116 | Orchestration core | Project toolbar | ✦ Plan (markdown), ⏰ Schedule; DevOps-only: 🗂 Map folders, ⇅ Sync (confirm, .env excluded), 🚀 Deploy (confirm → deploy/request → approve in Approval Center) | views.jsx:682,694-702 `ProjectView` | buttons | A-116, A-052, C-012 |
| K4B-117 | Orchestration core | Team members grid | CTO card (not removable, animates when working) + members with status working/done/idle, usage bar (stats), ✎ edit, ✕ remove with confirm | views.jsx:707-765 | render/click | A-116, A-074 |
| K4B-118 | Orchestration core | Live operation panel | polls latest op every 1.5s (full log); state running/done/stopped/blocked/issues + elapsed; ⏹ Stop; ▶ Run again; step chips; outcome dialog once per terminal op | views.jsx:797-922 `LiveOperation` | interval | C-014 |
| K4B-119 | Safety & approvals | Blocked operation → owner input | shows question + `needs[]` inputs (folder picker for `local_*` keys); Continue posts answers to /operations/{id}/provide | views.jsx:850-863,879-896 | ▶ Continue | C-014 |
| K4B-120 | Orchestration core | Team run (Build with the team) | goal → streamOrchestrate; plan flow nodes go green per step_done; progress bar, timer, log, finish/fail banners + outcome dialogs; autostart on kickoff | views.jsx:924-1056 `TeamRun` | Go / kickoff | A-066 |
| K4B-121 | Orchestration core | Monitor feed | /scope/summary feed every 3s (company and project) | views.jsx:1059-1076 `MonitorFeed` | interval | A-081 |
| K4B-122 | Orchestration core | Member activity log | member scope chats + msg counts, poll 3s | views.jsx:1079-1097 | interval | A-080 |
| K4B-123 | Safety & approvals | Project rules editor | add / edit on blur / discard additive rules the CTO and team follow | views.jsx:1101-1126 `ProjectRules` | input | A-078, C-007 |
| K4B-124 | Scheduling & notifications | Timezone list (Egypt default) | TZS list with Africa/Cairo default; weekdays map | views.jsx:1129-1131 | editor | C-020 |
| K4B-125 | Scheduling & notifications | Calendar schedule editor | daily/weekly(weekdays)/monthly(days 1-31), multiple times, timezone; saves kind "calendar"; ▶ Test now | views.jsx:1133-1205 `schedText`,`ScheduleEditor` | ✎ | C-020 (calendar kind: no) |
| K4B-126 | Scheduling & notifications | Scheduled tasks panel | list (cadence, runs, assignee), edit, remove; poll 10s | views.jsx:1208-1237 `SchedulesPanel` | render | B-098 |
| K4B-127 | Orchestration core | Live flow rail | last 4 hand-offs from /activity?pid flow, poll 2.5s | views.jsx:1239-1259 `FlowRail` | interval | no |
| K4B-128 | Middleware & DB registry | Member page | avatar/live task; per-member model select (scope member:pid:name); skills, restrictions, custom rules + save permanent rule; activity log; "Interrupt chat" at member scope | views.jsx:1262-1328 `MemberView` | nav | A-074, A-012, C-015 |
| K4B-129 | Middleware & DB registry | Project type catalogue (client) | 19 types: tech (web, mobile, desktop, deployment, security, scripting, integration, embedded, gaming, xr, ai_ml, data) + operational (marketing, email, content, support, sales, social, fulfillment) with suggested roles | views.jsx:1339-1362 `TYPE_META` | creation/grouping | C-003, A-211 |
| K4B-130 | Middleware & DB registry | Role meta | role → nature (technical/operational) + avatar | views.jsx:1331-1334,1364-1374 | creation | no |
| K4B-131 | Orchestration core | Client type recommender | keyword mirror of server recommend_type (fulfillment, email, marketing … default web) | views.jsx:1376-1398 `clientRecommendType` | spec proposed | no |
| K4B-132 | Scheduling & notifications | Periodic schedule builder | interval min 60s or daily hh:mm; requireApproval default true | views.jsx:1400-1413 `periodicSchedule`,`scheduleLabel` | create | C-020, D-042 |
| K4B-133 | Orchestration core | Owner verbatim brief | brief = "OWNER'S INSTRUCTIONS — verbatim, follow EXACTLY (no omission)" + owner's typed text (excluding seed + confirm string) then "CTO's understanding (supporting)" | views.jsx:1418-1426,1485-1489 | spec proposed | no (A-089 planned only) |
| K4B-134 | Orchestration core | Team role notes | plain-language role notes; existing-project tail "reads it, edits only when you ask"; DevOps "deploy stays approval-gated" | views.jsx:1430-1442 `TEAM_ROLE_NOTE` | spec review | no |
| K4B-135 | Orchestration core | Project create dialog — kind & folders step | existing (multi-folder, read-only) vs new (pick parent or type path); type + cadence picker shown early | views.jsx:1446-1475,1529-1534,1738-1766 `ConversationalNewProject` | ＋ New project | A-073, C-004 |
| K4B-136 | Safety & approvals | Read-only seed context text | seeds history: "EXISTING project. Folders … (READ-ONLY unless I explicitly ask to modify)" / "NEW project to create at …"; intro shown without calling the model | views.jsx:1501-1511 `startChat` | Next | no |
| K4B-137 | Orchestration core | Intake chat with attachments | answers + "ATTACHED FILES (read these)" path list → /projects/intake; option buttons; backend-offline message | views.jsx:1477-1527,1768-1818 | Send | A-073, C-004 |
| K4B-138 | Orchestration core | Digest confirm step | "Here's my understanding" → ✓ Confirm or correction | views.jsx:1782-1790 | digest action | A-073 |
| K4B-139 | Voice | Long-streaming project confirm | keyword list (zoom, meeting, transcrib, stream, microphone, 2 hour, chunk …) → confirm dialog explaining chunked processing before create | views.jsx:1537-1553 | Create | no |
| K4B-140 | Orchestration core | Team composition rule | base team minus unticked + accepted recommended members + type-seeded roles (dedup, nature/avatar) | views.jsx:1556-1569 | Create | no |
| K4B-141 | Orchestration core | Recommendations approve/reject | each recommended member/feature has a checkbox with reason; accepted features appended as "APPROVED RECOMMENDED FEATURES" | views.jsx:1571-1574,1850-1872 | spec review | no (MFI status table mentions "recommendations" only) |
| K4B-142 | Safety & approvals | Unknown-agent confirm gate | POST /agents/validate; unknown names open dialog: Create (role + rules required) / Use existing (catalog) / Remove; creation waits | views.jsx:1575-1584,1605-1623,1935-1981 | Create | no (API C-005) |
| K4B-143 | Orchestration core | Create payload | name, identifier (unique, editable), description=brief, members, type, stack, mode existing/build, localPath, sources (existing), autoApprove, cadence, periodic | views.jsx:1588-1602 `_finalizeCreate` | Create & start | C-002 |
| K4B-144 | Orchestration core | Type / custom type / cadence picker | tech + operational type buttons, custom type input, once / recurring / periodical with animated clock, daily or every N hours, "ask me to approve before each run" | views.jsx:1628-1723 `typeSchedulePicker` | folders step | no |
| K4B-145 | Orchestration core | Spec review screen | name, identifier, type/cadence summary, platform, features, editable brief (edited marker), team ticks, readiness list + ↻ live re-check (engine/Azure/connectors), dependencies, create-at / working-on | views.jsx:1820-1918 | spec | C-004 (readiness), A-073 |
| K4B-146 | Safety & approvals | Pre-approve changes toggle | `autoApprove`: no approval popup for this project (warning: sandboxes only); default every change waits | views.jsx:1919-1931 | checkbox | no |
| K4B-147 | Other | DeployProjectModal (unmounted) | deploy-only project (DevOps+QA) with local↔VM folder rows, update/replace mode, playbook description — exported but never rendered | views.jsx:1987-2030 | none | no |
| K4B-148 | Other | NewProjectModal (unmounted) | simple name/description/path create — exported but never rendered | views.jsx:2032-2056 | none | A-072 (presets not present in this code) |
| K4B-149 | Middleware & DB registry | Add member with AI suggestion | describe role → /agents/suggest → editable name, role, nature, description, resources & dependencies, env vars → create | views.jsx:2058-2113 `AddMemberModal` | ＋ Add member | C-006, A-074 |
| K4B-150 | Middleware & DB registry | Edit member resources & env | description, Allowed Resources & Dependencies, env KEY/value rows | views.jsx:2116-2146 `EditMemberModal` | ✎ | no |
| K4B-151 | Scheduling & notifications | Schedule modal | prompt, run-as agent (default Project CTO), daily hh:mm / interval seconds / once in 1 min | views.jsx:2148-2175 `ScheduleModal` | ⏰ Schedule | B-098, C-020 |
| K4B-152 | Synchronization & Anchor | Map local ↔ cloud folder | local, VM destination, role → /projects/{pid}/mappings | views.jsx:2177-2190 `MapModal` | 🗂 Map folders | C-002 |
| K4B-153 | Scheduling & notifications | Notifications bell | /notifications every 12s; shakes when unread grows; list with severity dot; click marks read + opens project; Mark all read | views.jsx:2212-2286 `NotificationsBell` | interval/click | no (API C-032) |
| K4B-154 | Other | In-app docs bell ("New in Odin") | 📖 badge = BELL_TABS length (9); invite → tabs Story, Caching, Tests, Anchor, Links, Request, Live Meeting, Deploy, Security SOC | views.jsx:2197-2359 `BellNotification` | click | A-125 |
| K4B-155 | Other | Docs tab contents | Links (paper/docs/key code paths), Anchor flow SVG + test commands, Story (shared context), Caching (cached_modules flow), Live Meeting steps, Deploy steps, SOC 8 agents + API list, Tests (e2e_phase2_gate, e2e_cache_timing, ODIN_DISABLE_CACHE) | views.jsx:2361-2396,2447-2687 | tabs | A-125 |
| K4B-156 | Synchronization & Anchor | Request page tab one-click start | calls window.odin.startRequestPage; shows shell command + copy; error states | views.jsx:2398-2445 `RequestPageTab` | ▶ Run it & open | no |
| K4B-157 | Safety & approvals | Periodic approval watcher | polls /schedules/pending every 10s; OS notification per new; bottom-right cards "Approve & run" / "Skip this time" | views.jsx:2694-2744 | interval | C-020, D-042 |
| K4B-158 | Synchronization & Anchor | Anchor Connect page | counts by status, retry config (count, interval, poll limit), request rows (status, id, project, webhook attempts, ack, error); on-demand refresh only | views.jsx:2751-2811 `AnchorView` | nav | C-026, A-176, A-177 |
| K4B-159 | Audit & consistency | Audit page (desktop) | open issues, quiet minutes, silence gap, would-run; enable toggle + gap; Scan (read-only); Run now (heal) → healed/flagged or debounced; issues table; history table | views.jsx:2814-2881 `AuditView` | nav Audit | A-104, C-028 |
| K4B-160 | Middleware & DB registry | Generic projects grid | /ui/projects cards (chip, category, icons, counts agents/connectors/files); type-driven controls play/run-once/export/cadence/period/timeout (all open the project) | views.jsx:2885-2918 `ProjectsGrid` | nav Projects | B-049, C-031 |
| K4B-161 | Middleware & DB registry | Generic agents grid | /ui/agents grouped by type, group chip, role, used-by count, capability pills voice/export | views.jsx:2922-2961 `AgentsGrid` | nav Agents | B-049, C-031 |
| K4B-162 | Build, packaging, run & clients | Premium dark theme + layering | tokens, glass cards, idle avatars static / working animated (heartbeat, glow, conic halo), z-index ordering note | theme.css:1-250 (177-186) | CSS | A-082 |
| K4B-163 | Build, packaging, run & clients | Static dashboard (index) | reads ../state/project.json, tasks.json, approvals.json, ../history/log.jsonl; built-in fallback snapshot + warning; phases, features, tasks, approvals, agents, history | dashboard/index.html:137-216 | open file / http.server | A-112, A-218 |
| K4B-164 | Voice | Dashboard Voice Console | enabled only if /health ok; browser Web Speech (ar-EG/en-US) → POST /chat → /voice/tts; audio unlock on click; no OS TTS fallback; strips "[Routed to …]" before speaking | dashboard/index.html:219-316 | 🎤 | A-114, A-163 |
| K4B-165 | Build, packaging, run & clients | Cockpit console | chat list (/chats legacy, create, select, dblclick rename, delete), SSE /chats/{cid}/stream status/token/done with activity rail + caret, TTS, Web Speech mic, last chat in localStorage odin_cid | dashboard/console.html:93-175 | open /console.html | A-109, C-021 |
| K4B-166 | Build, packaging, run & clients | OdinMD renderer | render (code with copy, tables, headers, lists, links) + toSpeech | dashboard/odin-md.js:5-87 | console/mobile | A-110 |
| K4B-167 | Auth & security | Mobile HTML cockpit with token | drawer chats, token row appears on 401, X-Odin-Token header + ?token= on SSE/TTS, SSE stream, mic, TTS, odin_m_cid | dashboard/mobile.html:79-133 | /mobile.html | A-240, B-022 |
| K4B-168 | Audit & consistency | Audit HTML page | same audit status/scan/run/config/history as desktop, switch toggle saves config | dashboard/audit.html:69-110 | /audit.html | A-104, D-041 |
| K4B-169 | Voice | Live Meeting monitor page | Start (offers clean of previous chunks via /meeting/state + /meeting/clear), mic level meter + VAD (level>8), chunk every 15/30/60/120s → POST /meeting/chunk (lang, noise, confidence; LOW CONF if <0.35), pause/resume flushes chunk, Stop → /meeting/finish builds report, view EN/AR via /meeting/view, export md/docx × en/ar, All 4 zip /meeting/report_all, New, close via postMessage; API fallback localhost:8000 | dashboard/meeting_monitor.html:109-293 | 🗣️ iframe / direct | A-173, A-174, B-195, C-042 |
| K4B-170 | Build, packaging, run & clients | Artifact snapshot page | light-theme dashboard with hard-coded DATA snapshot (78%, phases 1-8, tasks, history) | dashboard/artifact.html:53-71 | open file | A-112 |
| K4B-171 | Build, packaging, run & clients | Dashboard README | two ways: static file (+ http.server for live state) and Cowork artifact | dashboard/README.md:1-27 | doc | A-112, A-113 |

## 2. Not in MFI

| ID | Capability | Evidence |
|---|---|---|
| K4B-004 | `isUp()` defined but never called; MFI D-008 wrongly says launch checks health first | main.cjs:38-44,213-215 |
| K4B-011 | Electron window hardening (contextIsolation, no nodeIntegration) | main.cjs:129-139 |
| K4B-012 | External links forced to system browser | main.cjs:140 |
| K4B-015 | `start-request-page` IPC (static http.server on 9104, opens anchor_sim.html?env=prod) | main.cjs:166-200 |
| K4B-016 | killReqpage on exit | main.cjs:201 |
| K4B-018 | Permission handler grants every permission | main.cjs:209-211 |
| K4B-019 | Re-create window on activate | main.cjs:218 |
| K4B-034 | Duplicate `schedules`/`updateSchedule` keys in api.js (body-shape bug) | api.js:56-57,138-141 |
| K4B-043 | `capability_gap` SSE event | api.js:180 |
| K4B-053 | Collapsible sidebar persisted (`odin.nav`) | App.jsx:19,27 |
| K4B-055 | 4s health poll self-heal | App.jsx:51-61 |
| K4B-057 | Breadcrumbs | App.jsx:137-141 |
| K4B-058 | Scrollable toolbar with arrows | App.jsx:28-37 |
| K4B-059 | Conversations mode toggle | App.jsx:149-150 |
| K4B-060 | Refresh button | App.jsx:156 |
| K4B-061 | Auto kickoff of team run after creation | App.jsx:194-195 |
| K4B-062 | Global watchers mounted at root | App.jsx:200-204 |
| K4B-063 | Ports & Env map | App.jsx:215-237 |
| K4B-064 | Env flip (backend base stays localhost either way) | App.jsx:428-434 |
| K4B-065 | PRODUCTION/DEVELOPMENT badge | App.jsx:328-345 |
| K4B-066 | Generic connector badges in top bar | App.jsx:245-271 |
| K4B-067 | HubSpot badge + overview popup (UI) | App.jsx:273-326 |
| K4B-069 | Hard-coded anchor API key + Manage password/email in renderer bundle | App.jsx:351-353 |
| K4B-070 (part) | Settings env selector + Anchor URL field | App.jsx:464-498 |
| K4B-071..076 | Desktop Conversations mode (list, 3s sync, reply-as-group-post, attachments/voice notes, select/copy/forward/delete, attachment rendering) | Conversations.jsx |
| K4B-078 | Desktop 3s pool sync (count-only change detection) | ChatPanel.jsx:58-80 |
| K4B-079 | Stuck detector (>5 min, never auto-stop) | ChatPanel.jsx:66-76 |
| K4B-080 | WORKING/STUCK/FINISHED banner | ChatPanel.jsx:432-450 |
| K4B-081 | Desktop manual refresh "syncing…" | ChatPanel.jsx:120-127 |
| K4B-085 | Message queue while busy | ChatPanel.jsx:161,219-225 |
| K4B-086 | Capability-gap dialog (self / existing / expand / create) | ChatPanel.jsx:188-217,312-374 |
| K4B-087 | `⟦resolve⟧` prompt texts | ChatPanel.jsx:194-213 |
| K4B-088 | Real stop closes stream | ChatPanel.jsx:228-238 |
| K4B-090 | Start beep | ChatPanel.jsx:288-298 |
| K4B-091 | Draft lock | ChatPanel.jsx:43 |
| K4B-093 | Copy message / copy all (desktop) | ChatPanel.jsx:45-51 |
| K4B-099 | OS notifications helper | views.jsx:12-18 |
| K4B-100 | Outcome dialogs | views.jsx:22-60 |
| K4B-101 | Global operation finish watcher (`odin.ops.announced`) | views.jsx:66-98 |
| K4B-102 | Approval Center popup (UI) | views.jsx:106-262 |
| K4B-103 | Approval severity ordering | views.jsx:134-145 |
| K4B-104 | Approve-all-safe excludes security | views.jsx:156-166 |
| K4B-109 | Agent roster card (UI) | views.jsx:364-411 |
| K4B-112 | Recurring & scheduled card | views.jsx:475-519 |
| K4B-127 | Live flow rail | views.jsx:1239-1259 |
| K4B-130 | Role meta map | views.jsx:1364-1374 |
| K4B-131 | Client type recommender | views.jsx:1376-1398 |
| K4B-133 | Owner-verbatim brief composition | views.jsx:1418-1426,1485-1489 |
| K4B-134 | Team role notes | views.jsx:1430-1442 |
| K4B-136 | Read-only seed context text | views.jsx:1501-1511 |
| K4B-139 | Long-streaming project confirm | views.jsx:1537-1553 |
| K4B-140 | Team composition rule | views.jsx:1556-1569 |
| K4B-141 | Recommendations approve/reject + "APPROVED RECOMMENDED FEATURES" | views.jsx:1571-1574,1850-1872 |
| K4B-142 | Unknown-agent confirm dialog (UI) | views.jsx:1935-1981 |
| K4B-144 | Type/custom type/cadence picker | views.jsx:1628-1723 |
| K4B-146 | Pre-approve changes (autoApprove) toggle | views.jsx:1919-1931 |
| K4B-147 | DeployProjectModal (unmounted) | views.jsx:1987-2030 |
| K4B-150 | Edit member resources & env | views.jsx:2116-2146 |
| K4B-153 | Notifications bell (UI) | views.jsx:2212-2286 |
| K4B-156 | Request page one-click start tab | views.jsx:2398-2445 |
| K4B-125 (part) | Calendar schedule kind (weekly/monthly, multiple times) | views.jsx:1133-1205 |

MFI corrections: A-124 is marked PLANNED but is built (App.jsx:355-410). A-164 says partials every 0.9s; code uses 1.8s (ChatPanel.jsx:269). A-117's date-grouped sidebar is no longer rendered (dead code, ChatPanel.jsx:309). A-072 project presets are not present in this desktop code. `desktop/build/` (afterpack-sign.cjs, icon.png; D-005, A-238) is missing from this snapshot.

## 3. Requested-category confirmations

**(a) Desktop screens, modals and user actions**
- Project create dialog with recommendations approve/reject: FOUND — views.jsx:1446-1984 (`ConversationalNewProject`). Steps kind → folders → intake chat → digest → spec. Recommendations as checkboxes with reasons (1850-1872), team tick/untick (1873-1886), readiness + live re-check (1888-1914), pre-approve toggle (1919-1931).
- Capability dialog: FOUND — ChatPanel.jsx:312-374 (4 choices), resolve at 188-217.
- Unknown-agent confirm: FOUND — views.jsx:1575-1584 and 1935-1981 (Create / Use existing / Remove).
- Approvals popup: FOUND — views.jsx:106-262 (`ApprovalCenter`). Also periodic approve/skip at 2694-2744 and the blocked-operation input at 850-896.
- Run/orchestrate view: FOUND — `TeamRun` views.jsx:924-1056, `LiveOperation` 797-922, chat ▶ Run now ChatPanel.jsx:130-143, Stop 228-238.
- Chats: FOUND — ChatPanel.jsx (all scopes), sidebar standalone chats App.jsx:43-47,104-119, Conversations.jsx.
- Agents: FOUND — AgentRoster 364-411, CompanyAgents 414-443, team grid 707-765, MemberView 1262-1328, Add/Edit member 2058-2146, AgentsGrid 2922-2961.
- Connectors: FOUND — Connectors panel views.jsx:445-471, ConnectorBadges App.jsx:245-271, HubSpotBadge 273-326.
- Settings: FOUND — App.jsx:464-498 (`SettingsModal`) and PortsModal 425-462.
- Audit page: FOUND — views.jsx:2814-2881 (`AuditView`). Also dashboard/audit.html.
- Notifications: FOUND — NotificationsBell views.jsx:2212-2286, OS notifications 12-18, OutcomeToasts 29-60, OperationFinishWatcher 66-98, docs bell 2290-2359.
- Export: FOUND — report export menu ChatPanel.jsx:397-416 (PDF/DOCX/MD/PPTX); meeting export md/docx × en/ar + All-4 zip at meeting_monitor.html:263-276. ProjectsGrid "Export" button only opens the project (views.jsx:2906).

**(b) Live sync with web/mobile; dev vs packaged DMG**
- Polling: FOUND. Pool every 3s (ChatPanel.jsx:58-80; Conversations.jsx:72-76), activity 2.5s (App.jsx:63-76), health 4s (App.jsx:51-61), approvals 2.5s, operations 2.5s, latest op 1.5s, notifications 12s, pending schedules 10s, anchor code 4s, connectors 15s, HubSpot 60s, VM 60s.
- Same-list sharing with web/mobile: FOUND. Standalone chats are the same `/chats` registry (api.js:106-111; App.jsx:22-23). The scope pool is the same `/scope/messages` (api.js:131-132).
- Sequence/delta: NOT FOUND in the client. "seq-sorted" appears only in comments (ChatPanel.jsx:118-119,385-387). The client always re-pulls the whole pool and replaces it only when the message count changes, with no since/seq/delta parameter. Sequencing is done server-side, if at all.
- Desktop to anchor: in production the desktop never calls the anchor for data. Only the Manage-code indicator talks to the anchor (App.jsx:362-368). Web/mobile reach the brain through the poller that Electron spawns (main.cjs:86-115).
- Dev vs build: FOUND.
  - `ODIN_DEV=1` (from `npm run dev`) loads Vite :5173 with DevTools and does NOT spawn the poller (main.cjs:14,87,141-143).
  - The packaged/dist build loads `dist/index.html` and spawns backend + poller against `ODIN_ANCHOR` (main.cjs:145,215-216).
  - `VITE_ODIN_ENV=production` is baked in only by `npm run dist` (package.json:13), not by `pack`.
  - At runtime VITE_ODIN_ENV is only the default for `odin.env`, which drives EnvBadge, the PortsModal/Settings presets and the anchor-code poll target (App.jsx:329,364-367,426,473). The backend base stays `localhost:8000` in both environments (App.jsx:432,468-470).

**(c) Electron main/preload features**
- Process spawning: FOUND. Backend run.sh (main.cjs:46-68), poller (86-115, self-heal), request-page http.server (166-200), process-group kill on every exit path (70-79,117-127,201,222-229).
- Server start: FOUND. It always starts a fresh backend; `isUp` is unused (main.cjs:38-44,213-215).
- Single instance: FOUND (main.cjs:204).
- Native pickers + preload bridge: FOUND (main.cjs:150-164; preload.cjs:4-11).
- Tray: NOT FOUND (no Tray/Menu code).
- Deep links: NOT FOUND (no setAsDefaultProtocolClient or open-url). The only URL handling is `setWindowOpenHandler` → openExternal (main.cjs:140).

**(d) UDP / websocket**
- UDP: NOT FOUND (no dgram or UDP in any assigned file).
- WebSocket: NOT FOUND. Transport is HTTP fetch polling plus Server-Sent Events: EventSource in api.js:179,194, console.html:149 and mobile.html:114.

**(e) Dashboard pages and what they show**
- `index.html`: FOUND (CTO Brain dashboard). Shows progress %, phase, delivery status, pending approvals, phases, features done vs planned, active tasks and owners, agent team and recent history. These come from `../state/*.json` and `../history/log.jsonl`, with a fallback snapshot and a warning. It also has the Voice Console (STT → /chat → TTS, EN/AR), active only when served by the backend.
- `console.html`: FOUND (Odin Cockpit). Persistent legacy chats with SSE streaming, an activity rail, markdown, mic and TTS.
- `mobile.html`: FOUND. Phone chat with a drawer, access-token field on 401, SSE, mic and TTS.
- `audit.html`: FOUND (Audit/Observer). Status, enable/silence config, scan, run-now heal, issues and history.
- `meeting_monitor.html`: FOUND (Live Meeting). Chunked capture with meter, VAD, language, noise and low-confidence flags. It builds a report and exports md/docx in EN/AR or all 4 as a zip.
- `artifact.html`: FOUND. Static light-theme snapshot with hard-coded data.
- `odin-md.js`: FOUND. Markdown renderer and speech cleaner.
- `README.md`: FOUND. Explains the two ways to view the dashboard.


<!-- ==================== PART K5A ==================== -->

# K5A — SOC, security sentinel, VM/Azure access, deploy SSH, test keys, e2e suites

Scope (all read in full): `server/soc_run.py` (1343 lines), `soc_api.py`, `soc_behavior.py`, `soc_blueprint.py`, `soc_enrich.py`, `soc_hunt.py`, `soc_intel.py`, `soc_intel_fusion.py`, `soc_inventory.py`, `soc_predict.py`, `soc_quota.py`, `soc_recovery.py`, `security_sentinel.py`, `infra_az.py`, `infra_rotate.py`, `infra_ssh.py`, `deploy_ssh.py`, `gen_test_keys.py`, and all 11 `e2e_*.py`.
Secrets are named, never copied. (The source hard-codes the VM public IP in `soc_run.py:145`, `soc_inventory.py:85,88` and `deploy_ssh.py:19`, and a throwaway DB role password in `e2e_phase2_gate.py:37`. Values are omitted here.)

## 1. Capabilities found

| ID | Category | Capability | What it does | Evidence | Triggered by | In MFI? |
|---|---|---|---|---|---|---|
| K5A-001 | Per-project features & integrations | SOC run engine (Observe→Correlate→Verify→Report→Approve) | Runs the whole multi-agent SOC cycle for any pid, posting each phase into a project chat | soc_run.py:1038 `run()` | CLI `soc_run.py --pid --mode --cid --test` (1338-1343); scheduler run_cmd (soc_blueprint:109); POST /soc/run | A-227, C-033 |
| K5A-002 | Per-project features & integrations | Project-agnostic SOC (CURRENT_PID) | Global `CURRENT_PID` is set per run so every check works for any security project, not just RedBerry | soc_run.py:28-31, 1039-1040 | run() | no |
| K5A-003 | Safety & approvals | SOC runtime settings with defaults | 22 `SOC_*` flags (enabled, schedule, 23:00 America/New_York, monitor-only, retention 90/30/365 d, max 4 parallel tasks, per-domain monitoring toggles) | soc_run.py:35-48 `DEFAULT_SETTINGS` | settings() | C-033 (partial; flags not listed) |
| K5A-004 | Safety & approvals | Auto-remediation forced false/boolean | `save_settings` keeps only known keys and coerces `SOC_AUTO_REMEDIATION_ENABLED` to bool, default False ("MANDATORY default") | soc_run.py:47, 53-56 `save_settings()` | POST /soc/settings | A-227 |
| K5A-005 | Middleware & DB registry | SOC settings persistence | Merges defaults with `soc_settings.json` from the store | soc_run.py:32, 50-51 `settings()` | /soc/status, /soc/settings, run() | C-033 |
| K5A-006 | Safety & approvals | SOC content always inside the workspace | `_socdir` returns `workspace/projects/<pid>/data/soc`, never an external localPath (HARD RULE) | soc_run.py:58-66 `_socdir()` | every SOC module | no |
| K5A-007 | Testing | Env flag SOC_DIR_OVERRIDE | Test/sandbox-only override of the SOC content dir | soc_run.py:61-63 | env | no |
| K5A-008 | Audit & consistency | Persistent findings registry | `soc_findings_registry.json` per project (items keyed by finding id) | soc_run.py:69-72 `_reg_path/_load_registry/_save_registry` | run(), set_finding_status | A-228 |
| K5A-009 | Safety & approvals | Owner finding status action | Owner marks a finding resolved/pending/accepted/open with note and timestamp; unknown status falls back to open | soc_run.py:74-86 `set_finding_status()` | POST /soc/finding | C-034 |
| K5A-010 | Audit & consistency | Registry reconcile (memorizing tracker) | Splits this run's issues into new/open/pending/accepted; re-opens resolved items that are seen again; auto-resolves open items no longer detected; shows owner-resolved items for 7 days | soc_run.py:88-123 `_reconcile()` | run() :1259 | A-228 |
| K5A-011 | Auth & security | VM password loader | Reads key `azvmcred` from `workspace/shared/oth/.cred` | soc_run.py:126-132 `_vm_pw()` | all SSH checks, behavior, recovery, sentinel | A-032 (partial) |
| K5A-012 | Safety & approvals | Read-only SSH guard (`_ssh_ro`) | Refuses commands that contain banned substrings (rm, reboot, systemctl restart/stop, ufw, iptables, prisma migrate, DROP/DELETE/UPDATE/INSERT, kill, chmod, chown, npm install, apt); then runs one command via sshpass as mostafa with StrictHostKeyChecking=no to a hard-coded VM IP | soc_run.py:134-149 `_ssh_ro()` | all SOC VM reads | A-28 agent row (guard mentioned) |
| K5A-013 | Per-project features & integrations | Read-only Node/Prisma runner on VM | Base64-encodes a JS script and pipes it to `node` in `/home/mostafa/bendcore`, so the script is not mangled by the shell | soc_run.py:151-157 `_node_ro()` | DB checks | no |
| K5A-014 | Audit & consistency | Finding schema + 7-class taxonomy | Classes Informational…Confirmed; finding fields include evidence, false-positive analysis, data-source state, remediation, risk, blast radius, unknowns | soc_run.py:159-167 `CLASS`, `_finding()` | every check | A-229 (partial) |
| K5A-015 | Per-project features & integrations | Check SOC-OPS-001 service health | `systemctl is-active` for bendcore, organics, nginx, odin-anchor-online, odin-web-online; inactive/failed services raise Suspicious/high | soc_run.py:170-186 `check_service_health()` | FUNNEL/QUICK "service" | A-229 |
| K5A-016 | Per-project features & integrations | Check SOC-NET-001 network listeners | `sudo -S ss -ltnp` (password piped via echo) lists external listeners | soc_run.py:188-204 `check_network_listeners()` | "network" | A-229 |
| K5A-017 | Per-project features & integrations | Finding SOC-DB-001 PostgreSQL externally bound | Emitted by the listeners check when :5432 is bound off localhost (critical) | soc_run.py:198-202 | "network" | no |
| K5A-018 | Per-project features & integrations | Check SOC-AUTH-002 SSH keys/users | Counts authorized_keys lines and UID≥1000 users; always Needs Review (compare with known-good baseline) | soc_run.py:206-217 `check_ssh_auth()` | "ssh" | A-229 |
| K5A-019 | Per-project features & integrations | Check SOC-HOST-003 persistence | Reads crontab and systemd timers | soc_run.py:219-230 `check_persistence()` | "persistence" | A-229 |
| K5A-020 | Per-project features & integrations | Check SOC-APP-001 newsletter/registration abuse | Test mode: synthetic 8-submission, 10-minute-cadence fixture. Live: greps nginx logs for POST /email-subscribe and /api/register per IP; 10 or more from one IP = Suspicious | soc_run.py:232-273 `check_redberry_app_abuse()` | "app_abuse" | A-229 |
| K5A-021 | Per-project features & integrations | Check SOC-DEP-002 dependency intel | Calls soc_intel.update on the local organics-backend/frontend; triages runtime vs dev; stashes runtime CVEs to `intel-cache/our_cves.json` | soc_run.py:275-317 `check_dependency_intel()` | "dependency" | A-229 |
| K5A-022 | Per-project features & integrations | Check SOC-NET-002 website/endpoint health | HTTP code for anchor health, odin-web, and organics-api :4013 (the last via SSH curl); 200/301/302/401 count as OK | soc_run.py:319-344 `check_website_health()` | "website" | A-229 |
| K5A-023 | Per-project features & integrations | Check SOC-DB-002 DB anomaly | Prisma read: user count and new users in 24 h; more than 100 new = Suspicious | soc_run.py:346-371 `check_db_anomaly()` | "db_anomaly" | A-229 |
| K5A-024 | Per-project features & integrations | Garbage-name scorer | 0..1 score from vowel ratio, long consonant runs, long single token, Shannon entropy | soc_run.py:376-393 `_garbage_name_score()` | subscriber forensics | no |
| K5A-025 | Per-project features & integrations | Disposable/suspicious email rule | Disposable-domain list (mailinator, yopmail, …), local parts ending in 4+ digits, or a garbage local part | soc_run.py:374-375 `_DISPOSABLE`, 394-398 `_email_suspicious()` | subscriber forensics | no |
| K5A-026 | Per-project features & integrations | Check SOC-APP-004 subscriber forensics | Reads 7 days of users (up to 800) via Prisma, including the twoFactorCode field; scores garbage names, disposable emails and verified+2FA "farming"; risk ratio decides Probable/Suspicious | soc_run.py:400-456 `check_subscriber_forensics()` | "subscriber_forensics" | A-229 |
| K5A-027 | Per-project features & integrations | Check SOC-HOST-002 crypto-miner hunt | Top CPU plus egress via `sudo ss -tnp`; miner keywords; excludes KNOWN processes (prevents self-measurement false positives) and owner IPs from egress | soc_run.py:458-505 `check_miner_hunt()` | "miner_hunt" | A-229 |
| K5A-028 | Per-project features & integrations | Check SOC-CLOUD-003 port/firewall hardening | Reads `ufw status` and 0.0.0.0 binds over SSH; reads NSG inbound Allow rules with `az network nsg rule list` (RG/NSG names hard-coded). The NSG is the source of truth: critical vs defense-in-depth | soc_run.py:507-560 `check_port_hardening()` | "port_hardening" | A-229 |
| K5A-029 | Per-project features & integrations | Check SOC-IDS-001 behavioral intrusion | Wraps soc_behavior.analyze; Probable when any IP scores as bad; adds the UFW example command to the recommendation | soc_run.py:562-595 `check_intrusion_behavior()` | "intrusion_behavior" | A-229 |
| K5A-030 | Per-project features & integrations | Check SOC-SENSOR-008 24/7 sensor ingest | Tails 400 lines of `/home/mostafa/soc-sensor/events.jsonl`. Flags ssh_fail ≥20, ext_ports ≥1, unknown CPU >90 %, top-auth IP ≥30. Says honestly when the sensor is not installed | soc_run.py:597-662 `check_sensor()` | "sensor" | A-229, A-232 |
| K5A-031 | Per-project features & integrations | Check SOC-INTEL-007 fused intel | Matches our CVEs against CISA KEV and observed IPs against abuse.ch Feodo; a KEV hit = critical | soc_run.py:664-714 `check_intel_fusion()` | "intel_fusion" | A-229 |
| K5A-032 | Per-project features & integrations | Check SOC-CLOUD-004 multi-cloud surface posture | Credential-free probe of up to 8 inventory URLs: TLS expiry (<14 d = issue), HSTS and X-Frame-Options/CSP headers | soc_run.py:716-768 `check_cloud_posture()` | "cloud_posture" | A-229 |
| K5A-033 | Per-project features & integrations | Check SOC-EXT-006 third-party quota | Calls soc_quota.check; abuse flag comes from earlier findings in this run | soc_run.py:770-795 `check_thirdparty_quota()` | "quota" | A-229 |
| K5A-034 | Per-project features & integrations | Check SOC-WEB-005 clickjacking | HEAD request to the anchor site; missing X-Frame-Options or CSP frame-ancestors = Suspicious | soc_run.py:797-826 `check_clickjacking()` | "clickjacking" | A-229 |
| K5A-035 | Per-project features & integrations | CHECKS registry + per-check gating flags | Maps 17 check keys to their `SOC_*_ENABLED` gate. Note: service health is gated by SOURCE_INTEGRITY; persistence and sensor by SSH | soc_run.py:828-846 `CHECKS` | run() | no |
| K5A-036 | Per-project features & integrations | Run modes: quick / single-check / full funnel | QUICK = service, website, app_abuse, intrusion_behavior; `--mode <key>` runs one check; otherwise the full FUNNEL in broad-to-narrow order | soc_run.py:847-851, 1104-1109 | run(mode) | no |
| K5A-037 | Per-project features & integrations | Quota abuse propagation | Before the quota check, sets `_abuse` when APP-001/APP-004/IDS-001 are Suspicious or worse | soc_run.py:1116-1119 | run() | no |
| K5A-038 | Per-project features & integrations | Team hand-off explainer post | Posts the 8 SOC lanes and the flow into the chat | soc_run.py:1053-1064 | run() | A-227 (partial) **[corrected: see §0.8 C-6]** |
| K5A-039 | Per-project features & integrations | Phase A intel refresh announcement + usage record | Full non-test runs post the OSV refresh note and record Architect usage | soc_run.py:1067-1074 | run(full) | C-039 |
| K5A-040 | Per-project features & integrations | Phase A2 inventory refresh in run | soc_inventory.scan plus scope recommendations, posted by the Asset agent | soc_run.py:1077-1092 | run() | C-035, A-233 |
| K5A-041 | Per-project features & integrations | Phase B white-scope discovery note | Posts the NIST SP 800-61 / SANS PICERL / threat-hunting-funnel / ATT&CK methodology | soc_run.py:1097-1102 | run(full) | no |
| K5A-042 | Audit & consistency | Mining root-cause correlation | Miner + vulnerable dependency + degraded service → chain T1190→T1496→T1499 | soc_run.py:1128-1142 | run() | no |
| K5A-043 | Audit & consistency | Abuse root-cause correlation | IDS + subscriber + cadence (+ DB velocity) → app-level abuse (T1583/T1586), not VM compromise; flags a possible client-side OTP leak | soc_run.py:1143-1156 | run() | no |
| K5A-044 | Per-project features & integrations | Phase D prediction in run | soc_predict.predict; posts the top 8 predictions | soc_run.py:1159-1172 | run() | A-230 |
| K5A-045 | Per-project features & integrations | Phase D2 hunt in run | Fuses cached CVEs (no IPs) and runs soc_hunt.generate | soc_run.py:1175-1189 | run() | A-230 |
| K5A-046 | Per-project features & integrations | Phase D3 auto-triage enrichment | Live runs enrich the worst behavioral IP that scores ≥0.4 and is not the owner | soc_run.py:1192-1201 | run() | C-039 |
| K5A-047 | Safety & approvals | Auto config backup on clean full runs | Live full runs with no Confirmed finding capture an encrypted config backup, without approval | soc_run.py:1209-1213 | run(full, live) | A-231 (partial) |
| K5A-048 | Safety & approvals | Auto DB backup when stale >1 day | Captures an encrypted pg_dump when the last DB backup is more than 86400 s old | soc_run.py:1214-1221 | run(full, live) | no |
| K5A-049 | Per-project features & integrations | Phase E resilience posture post | Key fingerprint, backup count, readiness, smart plan | soc_run.py:1222-1232 | run() | A-231 |
| K5A-050 | Per-project features & integrations | Phase F CTO scope recommendation post | Lists services/clouds to enrol | soc_run.py:1235-1237 | run() | A-233 |
| K5A-051 | Safety & approvals | Remediation → approval request | Each Suspicious+ finding with a remediation becomes an approval (approvals.create, kind change). The decision is DENIED in test/monitor mode, otherwise PENDING; "no agent approves its own action" | soc_run.py:1240-1255 | run() | A-227 |
| K5A-052 | Per-project features & integrations | Issue tracker text | Lists New / Still open / Pending / Accepted / Resolved | soc_run.py:859-873 `status_tracker()` | run() | A-228 |
| K5A-053 | Per-project features & integrations | Owner summary | Status Healthy/Attention/Critical, counts, "No production changes were made" | soc_run.py:875-891 `owner_summary()` | run() | A-227 |
| K5A-054 | Per-project features & integrations | Technical report (markdown) | Per-finding evidence, false-positive analysis, blast radius, remediation | soc_run.py:893-907 `technical_report()` | run() | no |
| K5A-055 | Per-project features & integrations | Plain-words narrative | Lead text, what stood out, likely story, next risk, disaster readiness, growth advice, "never changes anything on its own" | soc_run.py:911-943 `_humanized_narrative()` | report spec | A-234 |
| K5A-056 | Per-project features & integrations | Branded health report spec | Sections: plain words, executive summary with badge, tracker, methodology, open/deferred/resolved tables, hunt, prediction, resilience, scope, surface, all checks, per-issue detail; severity colour map | soc_run.py:909, 945-1036 `_health_report_spec()` | run() | A-234, A-25 |
| K5A-057 | Per-project features & integrations | Multi-format report render | report_engine.render_to_file to PDF, DOCX, MD and PPTX under `soc/reports/soc-health-<date>` | soc_run.py:1268-1290 | run() | C-033 (/soc/report) |
| K5A-058 | Audit & consistency | Run record persistence | Writes `history/findings/run-<ts>.json` (full record) and `soc_last_run.json` | soc_run.py:1293-1303 | run() | no |
| K5A-059 | Per-project features & integrations | Agent usage recording | `agents_registry.record_usage` for the CTO, Investigator, Architect, Asset, Predictor, Recovery and Reporting agents | soc_run.py:1072, 1089, 1169, 1229, 1287, 1305-1310 | run() | A-075 (generic) |
| K5A-060 | Synchronization & Anchor | Scope sync-up after SOC run | `scopes.sync_up` with the finding and approval counts | soc_run.py:1311-1314 | run() | no |
| K5A-061 | Scheduling & notifications | SOC notification to bell | Live runs send "N items need attention" (critical or attention severity, deep-link pid/cid) or "daily run complete — all healthy" | soc_run.py:1316-1334 | run() | no |
| K5A-062 | Orchestration core | Auto-create SOC chat | Creates "🛡️ SOC run <date>" when no cid is given | soc_run.py:1044-1047 | run() | no |
| K5A-063 | Per-project features & integrations | GET /soc/status | Settings summary, last run, next scheduled run | soc_api.py:14-24 | dashboard/web/mobile | C-033 |
| K5A-064 | Per-project features & integrations | GET/POST /soc/settings | Read or patch SOC settings | soc_api.py:26-34 | UI | C-033 |
| K5A-065 | Scheduling & notifications | POST /soc/run | Calls scheduler.run_now for the pid (default redberry-continuous-soc) | soc_api.py:36-40 | UI ▶ | C-033 |
| K5A-066 | Per-project features & integrations | GET /soc/report?fmt= | Streams the latest pdf/docx/md/pptx report; 404 if none | soc_api.py:42-55 | UI download | C-033 |
| K5A-067 | Per-project features & integrations | GET /soc/inventory | Inventory plus scope recommendations | soc_api.py:57-62 | UI | C-035 |
| K5A-068 | Per-project features & integrations | GET /soc/recovery | Posture plus smart plan (optional problem_date); plan only, never restores | soc_api.py:64-69 | UI | C-036 |
| K5A-069 | Safety & approvals | POST /soc/backup | Documented as "requires approved=true", but run_backup ignores `approved` (see Not-in-MFI note) | soc_api.py:71-76 | UI | C-036 |
| K5A-070 | Safety & approvals | POST /soc/escrow | Key escrow to VM, gated by approved=true | soc_api.py:78-83 | UI | C-036 |
| K5A-071 | Per-project features & integrations | GET /soc/quota | Quota posture (abuse_active=False) | soc_api.py:85-89 | UI | C-037 |
| K5A-072 | Per-project features & integrations | GET /soc/behavior | Live UEBA analysis | soc_api.py:91-95 | UI | C-038 |
| K5A-073 | Safety & approvals | POST /soc/finding | Owner sets a finding's status | soc_api.py:97-102 | UI | C-034 |
| K5A-074 | Per-project features & integrations | GET /sentinel/status | Read-only RED/GREEN VM health | soc_api.py:105-109 | UI | C-040 |
| K5A-075 | Per-project features & integrations | POST /sentinel/run | Full sentinel run (create_alarms default true, pid vm-sentinel) | soc_api.py:111-117 | ▶ button / daily task | C-040 |
| K5A-076 | Safety & approvals | POST /approvals/approve-all (SAFE) | `approvals.approve_all_safe` approves non-security items only; security alarms stay individual | soc_api.py:119-123 | UI "approve all" | C-011 (partial: "safe/non-security" not stated) |
| K5A-077 | Per-project features & integrations | UEBA analyze | Builds per-IP profiles, scores them, sorts, persists, and recommends a UFW block for bad IPs | soc_behavior.py:83-116 `analyze()` | check_intrusion_behavior, /soc/behavior, run D3 | C-038 |
| K5A-078 | Auth & security | Owner IP allow-list (dynamic) | `$SSH_CLIENT` source IP read from the VM, plus `knowledge/owner-ip-allowlist.txt` | soc_behavior.py:30-47 `_owner_allowlist()` | analyze, miner hunt, sentinel | A-18 (partial) |
| K5A-079 | Per-project features & integrations | Cadence regularity metric | 1 − coefficient of variation of the gaps (≈1 = bot) | soc_behavior.py:49-60 `_regularity()` | analyze | no |
| K5A-080 | Per-project features & integrations | IP behavior scoring rules | Fan-out ≥3 accounts +0.4; regularity ≥0.7 with ≥4 hits +0.35; ≥3 UAs with ≥2 accounts +0.15; ≥5 sensitive hits +0.1. Verdicts at 0.7 / 0.4 / 0.2; owner IP = 0 | soc_behavior.py:62-81 `_score_ip()` | analyze | no |
| K5A-081 | Testing | UEBA deterministic fixture | Bot, human and OWNER profiles prove detection and false-positive safety | soc_behavior.py:86-94 | analyze(test=True), `__main__` | no |
| K5A-082 | Per-project features & integrations | Live nginx log mining | `sudo grep` of 4000 lines on sensitive endpoints; account creation = POST to register/signup/auth (with a quote-anchored regex fix) | soc_behavior.py:118-149 `_collect_live()` | analyze | no |
| K5A-083 | Middleware & DB registry | Behavior profile persistence | `knowledge/visitor-behavior-profiles.json` (read by fusion and sentinel) | soc_behavior.py:22-28, 151-158 | analyze | no |
| K5A-084 | Safety & approvals | UFW block recommendation (never applied) | Example `ufw deny from <IP>`, false-positive guard: score ≥0.7 only, owner excluded | soc_behavior.py:107-112 | analyze | A-18 |
| K5A-085 | Per-project features & integrations | SOC blueprint provision | Registers the 8-agent team, syncs the members manifest, seeds the knowledge base, creates the schedule; idempotent | soc_blueprint.py:31-65 `provision()` | CLI `soc_blueprint.py <pid>`; intake | C-033 |
| K5A-086 | Per-project features & integrations | 8-agent SECURITY_TEAM catalog | SecCTO, SecArchitect, SecInvestigator, AssetSurface, BehaviorIDS, Predictor, Recovery, Reporter | soc_blueprint.py:18-19 | provision | T-25 (partial) |
| K5A-087 | Orchestration core | Security-intent detector | Keyword test ("security company", "soc", "threat hunt", "intrusion", "blue team", …) used by intake to offer the blueprint | soc_blueprint.py:22-28 `is_security_intent()` | intake | no |
| K5A-088 | Middleware & DB registry | Members manifest sync | Merges the registered agent names into `projects/<pid>/index.json` members | soc_blueprint.py:45-55 | provision | no |
| K5A-089 | Per-project features & integrations | KB seed (operating principle) | Writes `knowledge/00-OPERATING-PRINCIPLE.md` once | soc_blueprint.py:77-95 `_seed_kb()` | provision | no |
| K5A-090 | Scheduling & notifications | SOC schedule creation | Calendar schedule (default 23:00 Africa/Cairo) titled "SOC daily monitor", assignee CTO; run_cmd = soc_run.py full; catchup=True; skipped if a task exists | soc_blueprint.py:98-117 `_ensure_schedule()` | provision | C-020/P-08 (partial) |
| K5A-091 | Per-project features & integrations | IP enrichment (ip-api.com) | Country, ISP, ASN, hosting/proxy/mobile flags; 24 h cache; known-C2 check via Feodo | soc_enrich.py:28-61 `enrich_ip()` | run D3 | C-039 |
| K5A-092 | Per-project features & integrations | Analyst narrative | Combines enrichment and behavior; datacenter host + regularity ≥0.7 → "automation" | soc_enrich.py:64-84 `narrative()` | run D3 | C-039 |
| K5A-093 | Per-project features & integrations | ATT&CK hypothesis hunting | 7 hunts (T1190→T1496, KEV T1190, T1583/T1586, T1498/T1499, T1078, T1485/T1486, T1190/T1189) judged supported/refuted/inconclusive | soc_hunt.py:19-85 `generate()` | run D2 | A-230 |
| K5A-094 | Per-project features & integrations | Hunt summary text | Count of supported hunts, coloured marks | soc_hunt.py:88-94 `summary_text()` | run D2 | A-230 |
| K5A-095 | Per-project features & integrations | OSV.dev dependency intel | Parses package-lock v1/v2/v3, batches 100 packages per OSV query, enriches the top 12 with severity/CVE/fixed version, writes `live-dependency-intel.md` | soc_intel.py:16-133 `update()`, `_resolved_versions`, `_osv_query`, `_severity` | check_dependency_intel; CLI | C-039, A-27 |
| K5A-096 | Per-project features & integrations | Reachability triage rule (KB text) | "Presence of a CVE is NOT compromise"; priority order: exploitable > likely > installed-not-reachable | soc_intel.py:123-126 | update | A-27 |
| K5A-097 | Per-project features & integrations | CISA KEV fetch | Map of known-exploited CVEs (name, product, due date, ransomware use) | soc_intel_fusion.py:63-73 `fetch_kev()` | fuse | C-039 |
| K5A-098 | Per-project features & integrations | abuse.ch Feodo C2 IP fetch | Active botnet C2 IP map | soc_intel_fusion.py:76-86 `fetch_bad_ips()` | fuse, enrich | no |
| K5A-099 | Per-project features & integrations | Feed cache with 6 h TTL + stale fallback | Live, cache, stale-cache or unavailable state | soc_intel_fusion.py:26, 40-60 `_get_json()` | fetch_* | no |
| K5A-100 | Per-project features & integrations | Intel fusion | Our CVEs × KEV and observed IPs × Feodo; writes `fused-threat-intel.md` | soc_intel_fusion.py:89-133 `fuse()`, `_write_kb()` | check_intel_fusion, run D2 | C-039 |
| K5A-101 | Per-project features & integrations | Provider models catalog | azure-vm, aws-ec2, godaddy, hostinger, cloudflare, static-cdn (how each is monitored) | soc_inventory.py:19-38 `PROVIDERS` | scan | A-233 |
| K5A-102 | Per-project features & integrations | Stack fingerprints | 12 marker files → stack, ecosystem, typical risk | soc_inventory.py:41-81 `_FINGERPRINTS`, `_fingerprint_dir()` | scan | C-035 |
| K5A-103 | Per-project features & integrations | Declared infra seed | Two Azure VM services (organics+bendcore; Odin anchor+web) with public URLs | soc_inventory.py:84-91 `DECLARED_INFRA` | scan | no |
| K5A-104 | Per-project features & integrations | Owner extra-hosts (multi-cloud live) | `knowledge/extra-hosts.json` adds any-cloud hosts, optionally with an ssh cred env var | soc_inventory.py:93-106 `_extra_hosts()` | scan | no |
| K5A-105 | Per-project features & integrations | Inventory scan + reverse-search filter | Enumerates projects (localPath fingerprints) and extra paths; computes the ecosystems/frameworks/providers we run; writes json and `asset-inventory.md` | soc_inventory.py:109-181 `scan()`, `_write()` | run A2, /soc/inventory, cloud posture | C-035, A-01 |
| K5A-106 | Per-project features & integrations | Scope recommendations | Enrol out-of-scope projects with known stacks; suggest Cloudflare when there is azure-vm without an edge | soc_inventory.py:183-198 | run, /soc/inventory | A-233 |
| K5A-107 | Per-project features & integrations | Stack-driven predictive rules | Per-stack weakness rules (Next.js, NestJS, Laravel, Prisma/PG, Static) | soc_predict.py:16-47 `_STACK_RULES` | predict | A-230 |
| K5A-108 | Per-project features & integrations | Threat prediction | Stack rules + evidence-linked rules (DEP, abuse) + architecture rules (no edge WAF, no backup); de-duplicated, high likelihood first | soc_predict.py:49-103 `predict()` | run D | A-230, A-30 |
| K5A-109 | Per-project features & integrations | Provider quota templates | Klaviyo, HubSpot, Mailchimp, SendGrid, Mailgun, Postmark, Brevo, Twilio, ActiveCampaign, GENERIC (env key names, usage URLs) | soc_quota.py:21-36 | check | C-037 |
| K5A-110 | Per-project features & integrations | Provider config resolution | `knowledge/thirdparty-services.json`, else env-key presence, else default klaviyo+hubspot | soc_quota.py:38-59 `_services_config()` | check | no |
| K5A-111 | Per-project features & integrations | Live usage telemetry | GET to the provider usage endpoint with the env key (read-only) | soc_quota.py:61-78 `_live_usage()` | check | C-037 |
| K5A-112 | Per-project features & integrations | Quota check / at-risk | Modes: live, key-error, advisory. When abuse is active, advisory providers are marked at risk | soc_quota.py:80-103 `check()` | check_thirdparty_quota, /soc/quota | C-037 |
| K5A-113 | Auth & security | Backup key management | Fernet key (fallback: random material) in `redberry-continuous-soc/data/soc_secure/backup.key` (0600, dir 0700); fingerprint file | soc_recovery.py:23-30, 42-66 `ensure_key()` | posture, run_backup | A-231 |
| K5A-114 | Auth & security | Encryption with weak fallback | Fernet; without the cryptography lib, an XOR stream marked "weak-fallback" | soc_recovery.py:75-84 `_encrypt()` | run_backup | no |
| K5A-115 | Safety & approvals | Encrypted backup capture | Config: nginx sites, systemd units, dpkg list. DB: pg_dump of the DB name grepped from the VM `.env`, capped at 20 MB. sha256, encrypted, registered in `soc_backups.json` with a "clean" health tag | soc_recovery.py:86-113 `run_backup()` | run E auto, POST /soc/backup | A-231 |
| K5A-116 | Safety & approvals | Backup key escrow to VM | PBKDF2 (200k) + Fernet with a one-time recovery code; writes `~/soc-key-escrow/backup.key.escrow` on the VM; approval-gated | soc_recovery.py:115-148 `escrow_key_to_vm()` | POST /soc/escrow | C-036 |
| K5A-117 | Per-project features & integrations | Auto problem date | Earliest first_seen among open Suspicious+ registry items | soc_recovery.py:150-167 `_auto_problem_date()` | smart_recovery_plan | no |
| K5A-118 | Safety & approvals | Smart recovery plan | Newest clean backup before the problem; decisions no-backups / no-clean-point / recover-from-pre-problem / may-not-be-needed; sha256 verify; restore approval-gated; narrowing rule | soc_recovery.py:170-208 | run E, /soc/recovery | A-231 |
| K5A-119 | Per-project features & integrations | Resilience posture | Ready = last backup less than 7 days old | soc_recovery.py:210-220 `posture()` | run E, /soc/recovery | A-231 |
| K5A-120 | Per-project features & integrations | Sentinel sensor read | Tails 40 lines of the sensor log via `sudo -S` | security_sentinel.py:24-41 `_sensor_events()` | vm_health | C-040 |
| K5A-121 | Per-project features & integrations | Sentinel reuses UEBA profiles | Reads the persisted profiles with score ≥0.4. Uses a CWD-relative path, unlike `_socdir` | security_sentinel.py:52-60 `_top_suspicious()` | vm_health | no |
| K5A-122 | Per-project features & integrations | Sentinel RED/GREEN rules | disk ≥90 %; memory <200,000 KB; ssh_fail ≥20; ext_ports rising above its min; attacker IP score ≥0.45 that is not the owner. Each finding carries a recommended action and a "LOCAL then DEPLOY" fix plan | security_sentinel.py:63-106 `vm_health()` | /sentinel/status, run_sentinel | C-040 |
| K5A-123 | Safety & approvals | Security-alarm approvals (separate red channel) | On RED, one `approvals.create_security` per finding; never part of approve-all | security_sentinel.py:126-137 | run_sentinel | P-10 (partial) |
| K5A-124 | Scheduling & notifications | Sentinel red/green notification | 🟢 info or 🔴 critical notification | security_sentinel.py:115-124 | run_sentinel | no |
| K5A-125 | Per-project features & integrations | Sentinel status message in project | "▶ VM status" chat with facts, findings and the alarm note; sync_up | security_sentinel.py:139-152 | run_sentinel | C-040 |
| K5A-126 | Build, packaging, run & clients | az binary self-heal | Finds `az` even with a stripped PATH (Homebrew paths) | infra_az.py:36-50 `_az_bin()`, `az_available()` | all az calls | A-042 (partial) |
| K5A-127 | Middleware & DB registry | Connection profile resolution | Workspace path first, then repo-root fallback; never throws | infra_az.py:22-26, 53-62 `_profile()` | infra_az | A-042 |
| K5A-128 | Build, packaging, run & clients | Resource-group auto-discovery | Uses the profile RG, else `az vm list` by VM name | infra_az.py:69-80 `discover_rg()` | vm_run | A-043 |
| K5A-129 | Middleware & DB registry | Persist RG + connected status | Writes the RG and a "connected (Azure control-plane…)" status to the profile | infra_az.py:83-87 `_save_rg()` | connect_test | A-043 |
| K5A-130 | Auth & security | App-user resolution | `azure.appUser` or "mostafa"; commands run as this user to avoid root-owned files | infra_az.py:90-96 `app_user()` | vm_run | A-032 |
| K5A-131 | Auth & security | Control-plane VM exec (`vm_run`) | `az vm run-command invoke RunShellScript`, wrapped `sudo -u <user> -H bash -lc` unless as_user='root'; 200 s timeout. **STATE-CHANGING** (arbitrary; approval-gated by docstring only) | infra_az.py:99-121 `vm_run()` | connect_test; other callers | A-042 |
| K5A-132 | Auth & security | Connect test with retry | Runs whoami/uname/ls /home (read); one retry; classifies not-logged-in vs run-failed | infra_az.py:124-155 `_connect_test_raw()` | connect_test | A-042 |
| K5A-133 | Auth & security | Badge-stable connect test | Serializes az calls with a lock; trusts the last good result for 300 s through transient blips | infra_az.py:28-33, 175-193 `connect_test()` | GET /infra/connect-test | A-042 (partial; lock/TTL not listed) |
| K5A-134 | Auth & security | VM public IP lookup | `az vm show -d --query publicIps` | infra_az.py:158-172 `vm_public_ip()` | deploy_ssh.vm_ip | no |
| K5A-135 | Auth & security | Dynamic-IP rotation (NSG + ufw) | NSG SSH rule source → `<ip>/32`, then ufw script via run-command; ok = ufw step succeeded. **STATE-CHANGING**, approval-gated | infra_rotate.py:111-152 `rotate()` | deploy_ssh.refresh_firewall; e2e suites | A-045, A-033 |
| K5A-136 | Safety & approvals | Safe ufw rotation script (80/443 sacred) | Opens 80/443 first; deletes ALL 22/tcp ALLOW/DENY rules (descending numbers); allows the single new IP on 22; denies 22; re-asserts 80/443. **STATE-CHANGING** | infra_rotate.py:84-108 `_ufw_script()` | rotate | A-029, B-135 |
| K5A-137 | Auth & security | NSG + SSH-rule auto-discovery | NIC → NSG (or subnet NSG); first rule with destinationPortRange '22' | infra_rotate.py:43-63 | rotate | A-045 (partial) |
| K5A-138 | Middleware & DB registry | Persist discovered NSG/rule names | Writes nsgName/sshRuleName to the profile | infra_rotate.py:66-76 `_persist()` | rotate | no |
| K5A-139 | Auth & security | Rotation config validation | Requires resourceGroup + vmName (not TBD) | infra_rotate.py:28-35 `_cfg()` | rotate | no |
| K5A-140 | Auth & security | Current public IP detection | curl to ipify, ifconfig.me, icanhazip | infra_ssh.py:31-41 `current_public_ip()` | rotate, /infra/ip | A-044 |
| K5A-141 | Auth & security | Key-based SSH profile connector | BatchMode, accept-new, port/key from the profile | infra_ssh.py:22-28, 44-55 | reachable, run | A-044 |
| K5A-142 | Auth & security | SSH reachability (read) | `echo ODIN_OK; uname -a` | infra_ssh.py:58-68 `reachable()` | GET /infra/reachable | A-044 |
| K5A-143 | Auth & security | Arbitrary SSH run (gated) | Runs any command; timeout env `ODIN_SSH_TIMEOUT` (default 300). **STATE-CHANGING** | infra_ssh.py:71-77 `run()` | callers after approval | A-044 |
| K5A-144 | Auth & security | Deploy password loader | `azvmcred` from `.cred` | deploy_ssh.py:26-31 `vm_password()` | ssh_exec, rsync | A-032 |
| K5A-145 | Auth & security | VM IP with fallback | infra_az.vm_public_ip, else a hard-coded fallback IP | deploy_ssh.py:19, 34-39 `vm_ip()` | ssh_exec, rsync | no |
| K5A-146 | Auth & security | Firewall refresh (only root/control-plane use) | Delegates to infra_rotate.rotate. **STATE-CHANGING** | deploy_ssh.py:42-48 `refresh_firewall()` | e2e setup; deploy path | A-033 |
| K5A-147 | Auth & security | Forced password-auth SSH options | PreferredAuthentications=password, PubkeyAuthentication=no, StrictHostKeyChecking=no, ConnectTimeout 20 | deploy_ssh.py:55-57 `_opts()` | ssh_exec, rsync | A-032 |
| K5A-148 | Build, packaging, run & clients | SSH exec as mostafa with sudo rewrite | Rewrites `sudo` to `sudo -S -p ''` and pipes the password; optional cwd; 1200 s timeout; output tail. **STATE-CHANGING** (arbitrary) | deploy_ssh.py:60-81 `ssh_exec()` | e2e suites; deploy path | A-032 |
| K5A-149 | Build, packaging, run & clients | rsync push (checksum) | `rsync -az --checksum`, optional `--delete` and dry-run. **STATE-CHANGING** | deploy_ssh.py:84-110 `rsync_push()` | deploy path | B-176 (partial) |
| K5A-150 | Safety & approvals | Always-on secret excludes | .env*, .backup-env, *.pem, *.key, config/google-oauth-client.json, *.bak, *.tmp, *.copy, .DS_Store | deploy_ssh.py:22-23 `SECRET_EXCLUDES` | rsync_push, verify_sync | A-025 |
| K5A-151 | Audit & consistency | Content-level sync verification | checksum + dry-run + itemize; lists files still differing; ok only when none are pending (read-only) | deploy_ssh.py:113-150 `verify_sync()` | deploy verify | B-176 (partial) |
| K5A-152 | Auth & security | Test API key generator | Appends ANCHOR_API_KEY / ODIN_API_KEY (`od_<prefix>_<token>`) to `.cred` when missing; never overwrites; prints the keys | gen_test_keys.py:20-56 `_load/ensure/main` | CLI; development_full_checker.sh | A-150, C-047 |
| K5A-153 | Testing | AI capability E2E (frozen) | Mining / Propagation / Crystallization / Truthfulness / Adaptation scorecard in the VM sandbox; exit codes 0/1/3 | e2e_ai_capability.py:247-313 `main()` | CLI | A-094, T-10 |
| K5A-154 | Safety & approvals | Production-touch guard (e2e) | Blocks prod paths, `sudo reboot`/reboot, `prisma migrate deploy/dev/reset` | e2e_ai_capability.py:60-67 `touches_production()` | guarded_auto_approve | T-10 |
| K5A-155 | Safety & approvals | Guarded auto-approve | Approves pending items like the owner, but rejects prod-touching ones (recorded as a capability gap); dispatches deploy/apply in the background | e2e_ai_capability.py:123-146 | run_agent_flow | no |
| K5A-156 | Testing | Sandbox create/teardown on VM | Firewall refresh, then `rm -rf` + mkdir `/home/mostafa/_e2e_sandbox` | e2e_ai_capability.py:76-96 | main | A-031 |
| K5A-157 | Testing | Sandbox deploy config (ODIN_DEPLOY_CONFIG) | Writes `data/_e2e_sandbox_config.sh` (sandbox paths, migration none, reboot 0, echo builds) and sets the env var | e2e_ai_capability.py:99-106 | main | §0 file list |
| K5A-158 | Testing | Instruction-line filter | Lines that forbid a method are not counted as using it | e2e_ai_capability.py:200-205 `_actions_only()` | measures | no |
| K5A-159 | Testing | Measures: mining / propagation / crystallization / truthfulness | Regex needs; drift checks (az run-command, migrate dev, prod paths) + `audit.audit_deploy_proposal`; sandbox file counts via SSH; `audit.scan_hidden_faults` / `claims_success` | e2e_ai_capability.py:188-237 | main | A-094 |
| K5A-160 | Testing | Adaptation test (frontend-only) | Second project; frontend dir must be non-empty and backend empty | e2e_ai_capability.py:276-287 | main | A-094 (adaptation not listed) |
| K5A-161 | Testing | production_untouched stub | Runs a stat but always returns True ("informational") | e2e_ai_capability.py:240-243 | (unused) | no |
| K5A-162 | Testing | venv self re-exec | Re-execs under `.venv` when fastapi is missing (`ODIN_E2E_REEXEC`) | e2e_ai_capability.py:47-56 (also hard_deploy:59, shared_context:41, strong:32, gate:61) | CLI | no |
| K5A-163 | Testing | Anchor lifecycle E2E (in-process) | Happy path, no double-processing, idempotent re-submit, retry (3 attempts), FAILED after retries (record kept), config persistence, counts; cleans its own rows | e2e_anchor.py:61-145 | CLI | A-201, T-01 |
| K5A-164 | Testing | Flaky local webhook receiver | Returns 500 for the first N hits, then 200 | e2e_anchor.py:27-55 | e2e_anchor | T-01 |
| K5A-165 | Testing | Anchor suite runner | Runs the 3 anchor suites in subprocesses and prints a summary | e2e_anchor_all.py:20-46 | CLI | A-201, T-04 |
| K5A-166 | Testing | Anchor HTTP contract E2E | TestClient on the real app: 401 without X-API-Key, POST /requests, poll, result, status, no re-poll, admin counts/config; env `ODIN_ANCHOR_NO_POLLER=1` | e2e_anchor_http.py:16, 50-136 | CLI | A-201, T-02 |
| K5A-167 | Testing | Anchor live E2E (Klaviyo/Veeqo read-only) | Feature wiring checks (types/roles/clients), creation-time connection ping, CTO→team orchestration, timing >1 s, real counts, status feed | e2e_anchor_live.py:55-176 | CLI (Mac) | A-201, T-03 |
| K5A-168 | Testing | Cache timing E2E | Same DevOps task with `ODIN_DISABLE_CACHE` =1 then =0; run_timer.compare; prints the speedup | e2e_cache_timing.py:24-77 | CLI | C-045, T-11 |
| K5A-169 | Testing | Hard deploy Phase-1 E2E | DevOps+QA+Security on the hard brief; pool growth, propagation of 6 details, no drift, omission guard (`main_task.reconcile`), truthfulness, production safe | e2e_phase1_hard_deploy.py:200-345 | CLI | T-09 |
| K5A-170 | Safety & approvals | Production fingerprint before/after | File count + mtime of bendcore/organics over SSH; FAIL if changed | e2e_phase1_hard_deploy.py:108-113; e2e_phase2_gate.py:98-101 | hard_deploy, gate | T-06, T-09 |
| K5A-171 | Testing | Opt-in throwaway DB simulation (ODIN_E2E_DBSIM) | Default off. When on: builds a sandbox URL from the VM `.env` DATABASE_URL (db name swapped), creates the DB, guards via `migrate status`, final confinement guard, `migrate deploy` + `migrate reset --force`, drop | e2e_phase1_hard_deploy.py:116-175, 215-252 | env ODIN_E2E_DBSIM=1 | A-031 (partial) |
| K5A-172 | Testing | Shared-context token E2E | Backend invents ODIN-XXXXXX; Frontend must reuse it | e2e_phase1_shared_context.py:81-164 | CLI | T-07 |
| K5A-173 | Testing | Strong 2-hop + hand-off E2E | Tokens A/B across 3 members; BACKEND-TODO hand-off | e2e_phase1_strong.py:78-149 | CLI | T-08 |
| K5A-174 | Testing | Phase 2/3 topology E2E | Real remote-anchor stand-in (`anchor_remote.Handler` + `_retry_sweep`) over HTTP; `--smoke` echo processor; real orchestration by default | e2e_phase2.py:90-202 | CLI | A-202, T-05 |
| K5A-175 | Testing | Phase-2 gate Part A (labelled tokens) | Extracts TOKEN_A / USES_A / TOKEN_B by label; hop2 + hand-off | e2e_phase2_gate.py:218-258 | CLI | T-06 |
| K5A-176 | Testing | Phase-2 gate Part B (always-on DB sim) | Firewall refresh; fingerprint; `sudo -u postgres` creates a throwaway role + DB; guard; `migrate deploy` + `reset --force`; drop; fingerprint again | e2e_phase2_gate.py:104-123, 260-293 | CLI | T-06 |
| K5A-177 | Testing | Phase-2 gate Part C (Phase-3 features) | Project types catalog + recommend_type mapping, roles readiness, operational agent nature/mode, periodic project task with requireApproval, scheduler gate: due→pending_approval, skip→idle, grossly missed→silent roll-forward; self-cleaning | e2e_phase2_gate.py:125-208 `phase3_check()` | gate main | no (T-06 omits Part C) |
| K5A-178 | Testing | Gate verdict | READY only if A + B PASS + prod safe + C | e2e_phase2_gate.py:305-330 | CLI | T-06 |

## 2. Not in MFI

These rows have no MFI match, or only a partial one (marked).

| ID | Capability | Evidence |
|---|---|---|
| K5A-002 | Project-agnostic SOC via CURRENT_PID | soc_run.py:28-31,1039 |
| K5A-003 | Full SOC_* settings flag set (retention days, parallel tasks, per-domain toggles); partial in MFI | soc_run.py:35-48 |
| K5A-006 | SOC content always inside the workspace rule | soc_run.py:58-66 |
| K5A-007 | SOC_DIR_OVERRIDE env flag | soc_run.py:61 |
| K5A-013 | `_node_ro` base64 Prisma runner on VM | soc_run.py:151-157 |
| K5A-017 | SOC-DB-001 externally bound PostgreSQL finding | soc_run.py:198-202 |
| K5A-024/025 | Garbage-name scorer + disposable-email rule | soc_run.py:374-398 |
| K5A-035 | CHECKS→gate-flag mapping (service health gated by SOURCE_INTEGRITY) | soc_run.py:828-846 |
| K5A-036 | Quick / single-check / funnel run modes | soc_run.py:847-851,1104-1109 |
| K5A-037 | Quota abuse propagation | soc_run.py:1116-1119 |
| K5A-041 | White-scope discovery methodology post | soc_run.py:1097-1102 |
| K5A-042/043 | Mining and abuse root-cause correlation chains (ATT&CK) | soc_run.py:1128-1156 |
| K5A-048 | Auto encrypted DB backup when stale >1 day, no approval | soc_run.py:1214-1221 |
| K5A-054 | Markdown technical report | soc_run.py:893-907 |
| K5A-058 | Run record persistence (history/findings, soc_last_run.json) | soc_run.py:1293-1303 |
| K5A-060 | SOC scope sync_up | soc_run.py:1311 |
| K5A-061 | SOC notification to the bell | soc_run.py:1316-1334 |
| K5A-062 | Auto-create SOC chat | soc_run.py:1044 |
| K5A-076 | approve-all approves NON-security items only (MFI C-011 says "bulk approve-all" only) | soc_api.py:119-123 |
| K5A-079/080/081/082/083 | UEBA internals: regularity metric, scoring weights and thresholds, fixture, nginx mining, profile file | soc_behavior.py |
| K5A-087 | `is_security_intent` intake detector | soc_blueprint.py:22-28 |
| K5A-088/089 | Blueprint members-manifest sync + KB seed | soc_blueprint.py:45-95 |
| K5A-090 | Blueprint schedule ("SOC daily monitor", default 23:00 Africa/Cairo vs settings default America/New_York); partial | soc_blueprint.py:98-117 |
| K5A-098/099 | abuse.ch Feodo fetch; 6 h feed cache with stale fallback | soc_intel_fusion.py |
| K5A-103/104 | DECLARED_INFRA seed; owner `extra-hosts.json` | soc_inventory.py:84-106 |
| K5A-110 | `thirdparty-services.json` provider config | soc_quota.py:38-59 |
| K5A-114 | XOR "weak-fallback" encryption when cryptography is missing | soc_recovery.py:75-84 |
| K5A-117 | Auto problem-date from the registry | soc_recovery.py:150-167 |
| K5A-121 | Sentinel reads UEBA profiles (CWD-relative path) | security_sentinel.py:52-60 |
| K5A-123 | Security-alarm approvals (`create_security`, never in approve-all); MFI only P-10 text, partial | security_sentinel.py:126-137 |
| K5A-124 | Sentinel red/green notification | security_sentinel.py:115-124 |
| K5A-133 | Az lock + 300 s last-good TTL (badge stability); partial | infra_az.py:28-33,175-193 |
| K5A-134 | `vm_public_ip` via az | infra_az.py:158-172 |
| K5A-138/139 | Persist discovered NSG/rule names; rotation config validation | infra_rotate.py:28-76 |
| K5A-145 | Hard-coded fallback VM IP | deploy_ssh.py:19,34-39 |
| K5A-149/151 | `rsync_push` / `verify_sync` functions (MFI B-176 is the prompt rule only); partial | deploy_ssh.py:84-150 |
| K5A-155 | Guarded auto-approve harness | e2e_ai_capability.py:123-146 |
| K5A-158 | Instruction-line filter (`_actions_only` / `_INSTR`) | e2e_ai_capability.py:200; hard_deploy:52 |
| K5A-161 | `production_untouched()` always returns True (stub) | e2e_ai_capability.py:240-243 |
| K5A-162 | venv self re-exec (ODIN_E2E_REEXEC) | e2e_* files |
| K5A-171 | ODIN_E2E_DBSIM opt-in DB sim in hard_deploy (reads the VM `.env` DATABASE_URL); partial | e2e_phase1_hard_deploy.py:116-252 |
| K5A-177 | Phase-2 gate Part C: Phase-3 feature checks and scheduler due/skip/missed gate | e2e_phase2_gate.py:125-208 |

Defects and inconsistencies found while reading (not in MFI):
- **The key escrow can never succeed.** `escrow_key_to_vm` sends `mkdir … && chmod 600 …` through `_ssh_ro`, and `"chmod "` is on `_ssh_ro`'s banned list. The command is always REFUSED, so the endpoint returns "escrow-failed" (soc_recovery.py:140-144 vs soc_run.py:136-139).
- **POST /soc/backup is not gated.** It is documented as "Requires approved=true", but `run_backup(..., approved=True)` never reads `approved`, so the backup is not actually gated (soc_api.py:71-76, soc_recovery.py:86). The DB backup also reads the VM `.env` to get the DSN db name (soc_recovery.py:98-99).
- **Owner IP comes from `$SSH_CLIENT` on the VM.** That is whatever IP the SOC itself connects from, so it is excluded automatically (soc_behavior.py:36).
- **Two different default timezones.** Settings default to 23:00 America/New_York (soc_run.py:37). The blueprint defaults to 23:00 Africa/Cairo (soc_blueprint.py:31).
- **The cache-timing docstring is wrong.** It says it "points at the sandbox config", but the code never sets ODIN_DEPLOY_CONFIG. It creates the project with auto_approve=True and a goal of "connect to the sandbox VM" (e2e_cache_timing.py:11-12, 33-39).

## 3. Requested-category confirmations

### (a) Every SOC capability
- **Agents.** FOUND.
  - The 8-agent team: soc_blueprint.py:18-19 `SECURITY_TEAM`.
  - Lanes and hand-off: soc_run.py:1053-1064.
  - Posts sent as: CTO Orchestrator, Asset/Exposure/Attack-Surface, Security Intelligence & Threat-Hunting Architect, Security Operations Investigator, Intrusion Detection & Behavioral Analytics, Threat Prediction & Prevention, Recovery & Resilience, Reporting & Documentation.
  - Usage recorded at soc_run.py:1072-1310.
- **Checks and finding IDs.** FOUND. There are 17 checks (soc_run.py:828-846) and 18 finding IDs:
  - SOC-OPS-001 :170
  - SOC-NET-001 :188
  - SOC-DB-001 :200
  - SOC-AUTH-002 :206
  - SOC-HOST-003 :219
  - SOC-APP-001 :232
  - SOC-DEP-002 :275
  - SOC-NET-002 :319
  - SOC-DB-002 :346
  - SOC-APP-004 :400
  - SOC-HOST-002 :458
  - SOC-CLOUD-003 :507
  - SOC-IDS-001 :562
  - SOC-SENSOR-008 :597
  - SOC-INTEL-007 :664
  - SOC-CLOUD-004 :716
  - SOC-EXT-006 :770
  - SOC-WEB-005 :797
- **Predictions.** FOUND. soc_predict.py:16-103; used at soc_run.py:1159-1172.
- **Intel.** FOUND.
  - OSV: soc_intel.py:63-133.
  - KEV + abuse.ch fusion: soc_intel_fusion.py:63-133.
- **Hunting.** FOUND. soc_hunt.py:19-94 (7 ATT&CK hypotheses).
- **Behaviour (UEBA).** FOUND. soc_behavior.py:30-158.
- **Recovery.** FOUND.
  - Key: soc_recovery.py:44.
  - Backup: :86.
  - Escrow: :115 (broken by the `chmod` ban, see §2).
  - Smart plan: :170.
  - Posture: :210.
- **Inventory.** FOUND. soc_inventory.py:19-198.
- **Quota.** FOUND. soc_quota.py:21-103.
- **Enrich.** FOUND. soc_enrich.py:28-84 (ip-api.com + Feodo).
- **Blueprint.** FOUND. soc_blueprint.py:31-117.
- **Reports.** FOUND.
  - Tracker, summary, technical report, narrative, spec: soc_run.py:859-1036.
  - 4-format render: :1268-1290.
  - Download: soc_api.py:42-55.
- **Backups.** FOUND. soc_recovery.py:86-113. Auto-run at soc_run.py:1209-1221; POST /soc/backup at soc_api.py:71.
- **Schedules.** FOUND.
  - Blueprint creates a calendar task with run_cmd and catch-up: soc_blueprint.py:98-117.
  - Default run time 23:00: soc_run.py:37.
  - /soc/run → scheduler.run_now: soc_api.py:36-40.
  - Next run shown in /soc/status: soc_api.py:18-19.
- **Approvals / alarms.** FOUND.
  - SOC remediation approvals (auto-denied in monitor/test mode): soc_run.py:1240-1255.
  - Security-alarm approvals: security_sentinel.py:126-137.
  - Safe approve-all (non-security only): soc_api.py:119-123.
  - Red/green notifications: security_sentinel.py:115-124; soc_run.py:1316-1334.

### (b) VM/Azure access paths, and whether each one CHANGES state

| Path | Mechanism | State |
|---|---|---|
| soc_run.py:134 `_ssh_ro` | sshpass SSH as mostafa, password, banned-substring guard | READ (intended). It does pipe the sudo password to `sudo -S` |
| soc_run.py:151 `_node_ro` | via `_ssh_ro`, node + Prisma reads | READ |
| soc_run.py:524 `az network nsg rule list` | local az CLI | READ |
| soc_recovery.py:86 `run_backup` | via `_ssh_ro` (cat configs / pg_dump) | READ on the VM; WRITES local encrypted files |
| soc_recovery.py:115 `escrow_key_to_vm` | via `_ssh_ro` mkdir/write/chmod | Would WRITE to the VM (gated), but the guard refuses it |
| soc_behavior.py:36, 118 | via `_ssh_ro` | READ |
| security_sentinel.py:24 | via `_ssh_ro` tail of the sensor log | READ |
| infra_az.py:99 `vm_run` | `az vm run-command invoke` (Azure agent; `sudo -u mostafa` or root) | **CHANGES** (arbitrary) |
| infra_az.py:124/175 `connect_test` | vm_run(whoami/uname/ls) | READ on the VM; writes the local profile (RG/status) |
| infra_az.py:69, 158 `discover_rg`, `vm_public_ip` | az vm list/show | READ |
| infra_rotate.py:131-137 | `az network nsg rule update --source-address-prefixes <ip>/32` | **CHANGES: NSG** |
| infra_rotate.py:143-146 + :84 `_ufw_script` | `az vm run-command` running a ufw script | **CHANGES: ufw** (22 only; 80/443 kept open) |
| infra_rotate.py:43-63 discovery | az vm/nic/vnet/nsg show/list | READ; writes the local profile |
| infra_ssh.py:58 `reachable` | key SSH `uname` | READ |
| infra_ssh.py:71 `run` | key SSH arbitrary | **CHANGES** (gated by docstring only) |
| deploy_ssh.py:42 `refresh_firewall` | calls `infra_rotate.rotate` | **CHANGES: NSG + ufw** |
| deploy_ssh.py:60 `ssh_exec` | sshpass SSH as mostafa; `sudo` → `sudo -S` | **CHANGES** (arbitrary, e.g. rm/mkdir/psql/prisma in the e2e suites) |
| deploy_ssh.py:84 `rsync_push` | sshpass rsync, optional `--delete` | **CHANGES: files** |
| deploy_ssh.py:113 `verify_sync` | rsync dry-run itemize | READ |

- **sshd:** NOT FOUND. No sshd_config change exists anywhere in these files.
- **IP rotation:** FOUND. infra_rotate.py:111 `rotate`, called from deploy_ssh.refresh_firewall, e2e_ai_capability.py:82, e2e_phase1_hard_deploy.py:101 and e2e_phase2_gate.py:265.

### (c) Dynamic-IP rule (replace the single SSH allow rule, never stack)
FOUND, in infra_rotate.py.
- **NSG side** (infra_rotate.py:131-137): updates the ONE existing SSH rule's source to `<ip>/32` (`nsg rule update`). It replaces the rule, it does not add one. Caveat: `_discover_ssh_rule` (:59-63) takes only the first rule whose `destinationPortRange=='22'`, so any extra port-22 NSG rules are left as they are.
- **ufw side** (`_ufw_script`, :84-108):
  - Deletes EVERY existing `22/tcp` ALLOW IN / DENY IN rule, highest number first.
  - Adds one `allow from <ip> to any port 22`, then `deny 22/tcp`.
  - Opens 80/443 before and after.
  - Caveat: the awk match `/22\/tcp/` is a substring match, so it would also delete rules for ports such as 2222/tcp or 8022/tcp.

Related text in my files:
- The SOC recommendations repeat the rule ("22 to your single (dynamic) IP with a refresh protocol"): soc_run.py:501, 549-550; soc_predict.py:86.
- infra_ssh.py:10-11 still describes the strict dynamic-IP steps as MANUAL (older wording).

### (d) Every e2e test: what it proves, and whether it touches the VM

| File | Proves | Touches VM? |
|---|---|---|
| e2e_ai_capability.py | AI deploy capability across Mining, Propagation, Crystallization, Truthfulness and Adaptation (frontend-only); guard blocks prod/reboot/migrate | **YES.** Firewall rotate (NSG + ufw changes); creates, rsyncs into and deletes `/home/mostafa/_e2e_sandbox` over SSH; stats the prod dirs. Agent changes are auto-approved unless they touch prod |
| e2e_anchor.py | Anchor queue lifecycle, retry, FAILED, no double-processing, config/counts | NO (local queue + local receiver) |
| e2e_anchor_all.py | Runs the 3 anchor suites with one summary | NO directly (the live suite reaches Klaviyo/Veeqo SaaS) |
| e2e_anchor_http.py | Real /anchor/v1 HTTP contract + X-API-Key 401 + webhook + admin | NO |
| e2e_anchor_live.py | Real projects + read-only Klaviyo/Veeqo through CTO→team orchestration and the full lifecycle; real numbers; timing >1 s | NO (external SaaS GETs) |
| e2e_cache_timing.py | Wall-clock speedup of cached vs non-cached runs | INDIRECT. A DevOps agent with auto_approve=True is told to "connect to the sandbox VM" for a read-only health check. No sandbox config is set despite the docstring |
| e2e_phase1_hard_deploy.py | Multi-agent detail propagation (6 details), no drift, omission guard, truthfulness, production fingerprint unchanged; optional DB sim | **YES.** Firewall rotate; sandbox create/delete; fingerprint. With ODIN_E2E_DBSIM=1 it also reads the prod `.env` DATABASE_URL and creates, migrates, **resets** and drops `organics_e2e_sandbox`. Agents auto_approve=True against the sandbox |
| e2e_phase1_shared_context.py | Token from Backend reaches Frontend through the shared pool; pool growth; omission; truthfulness | NO (local `/tmp` dir, read-only reasoning) |
| e2e_phase1_strong.py | 2-hop token propagation (A, B) + BACKEND-TODO hand-off | NO |
| e2e_phase2.py | App ⇄ remote-anchor stand-in ⇄ local over real HTTP; `--smoke` transport only; real Klaviyo/Veeqo counts by default | NO (local stand-in) |
| e2e_phase2_gate.py | A: multi-hop context. B: throwaway DB `migrate deploy` + `reset`, prod fingerprint unchanged. C: Phase-3 types, operational agents, periodic task + scheduler due/skip/missed gate | **YES (Part B, always on).** Firewall rotate; `sudo -u postgres` creates and drops a throwaway role + DB; prisma migrate deploy/**reset --force** against it from `/home/mostafa/bendcore`; fingerprints prod. Parts A and C: no |


<!-- ==================== PART K5B ==================== -->

# K5B — Capability inventory: shared infra / testing / utils / shells / project code / data

Scope read in full (Read tool, every line): `workspace/shared/infra/{deploy.sh, deploy.config.sh, deploy_changes.py, deploy_run.sh, deploy_verify.py, ensure-connection.sh, phase3_gate.py, phase3_e2e.py, anchor/*, azure/*}`, the `deploy-lists/*` baselines (structure only), `workspace/shared/testing/*.py|*.sh` (25 files), `workspace/shared/utils/*.py|*.sh` (5 files), `workspace/shared/skills/odin-cto-brain/SKILL.md`, `workspace/shared/assets/global_voice_streaming_asset.md` (skills/ and assets/ contain no .py/.sh/.js), `shells/*` (7 files), `data/run_timings.json`, every source file under `workspace/projects/*/code/` and `*/deploy/`.

Path abbreviations used in Evidence: **INF** = `workspace/shared/infra/` · **TST** = `workspace/shared/testing/` · **UTL** = `workspace/shared/utils/` · **SH** = `shells/` · **SOC** = `workspace/projects/redberry-continuous-soc/code/` · **FS** = `workspace/projects/full-services-19jul/code/` · **ARM** = `workspace/projects/odin-external-arms/deploy/`.

Not read line-by-line (compiled / generated, noted only): `ARM/web/main.dart.js` (3.4 MB compiled Flutter web bundle), `ARM/web/flutter.js` + `flutter_bootstrap.js` (Flutter loader, minified), `ARM/web/assets/**` (NOTICES licence file, AssetManifest, FontManifest = MaterialIcons, `record_web` package JS worklets, ink_sparkle/stretch_effect shaders). These are the built release of `odin_app` with `<base href="/odin-web/">`, title "Odin — Remote Anchor (Web)", PWA manifest, and a self-unregistering `flutter_service_worker.js`. `ARM/web/.last_build_id` (32 B) and `.web_src_fingerprint` (64 B sha256) are phase3 change-detection state. All other project `code/` and `deploy/` folders contain only `.gitkeep` (daily-egypt-amazon-product-poster, email-klaviyo-…-18ca, fulfillment-vq-…-dc1e, hubspot-crm-operator, vm-sentinel, zoom-real-flow, odin-external-arms/code).

Secrets policy: VM IP, VM password key value, API keys, login password and password hash present in these files are NOT copied — named only.

---

## 1. Capabilities found

| ID | Category | Capability | What it does | Evidence | Triggered by | In MFI? |
|---|---|---|---|---|---|---|
| K5B-001 | Build, packaging, run & clients | deploy.sh repo/cred/log bootstrap | Locates repo from script dir, cred file `oth/.cred`, creates `workspace/logs/e2e-deploy-<ts>.log` | INF/deploy.sh:25-29 | CLI `bash deploy.sh`; deploy_run.sh STEP 1 | D-027 |
| K5B-002 | Build, packaging, run & clients | Hard-coded VM identity defaults | VM user, RG, VM name, VM-IP fallback (value not copied), backend verify port 4013 | INF/deploy.sh:32-36 | every deploy.sh run | D-027 |
| K5B-003 | Build, packaging, run & clients | Built-in RBO-Staging target defaults | Backend/frontend local + VM folders, mig `new`/`none`, build `rm -rf dist|.next && npm run build` | INF/deploy.sh:39-42 | every run (unless CFG_*) | B-137, B-140 |
| K5B-004 | Safety & approvals | Never-sync exclude list (defaults) | Excludes .git, .env*, .backup-env, *.pem, *.key, google-oauth json, *.bak/tmp/copy, media, node_modules, dist, .next, logs, prisma/migrations, lockfile, uploads | INF/deploy.sh:46-49 `DEF_EXCLUDES` | every rsync | B-138, A-025 (A-025 says `config/*.json`; code only excludes `config/google-oauth-client.json`) |
| K5B-005 | Build, packaging, run & clients | Default full-reboot flag | `DEF_REBOOT=1` (full VM reboot if no services configured) | INF/deploy.sh:50 | finalize stage | D-027 |
| K5B-006 | Build, packaging, run & clients | Isolated config override env | `ODIN_DEPLOY_CONFIG` points deploy.sh at a sandbox/project delta config instead of deploy.config.sh | INF/deploy.sh:55-57 | env flag (harness/project delta) | D-027 (env list §2) |
| K5B-007 | Safety & approvals | Per-run migration override | `ODIN_MIG_OVERRIDE` beats CFG/DEF migration mode (set by deploy_run DB gate) | INF/deploy.sh:61-63 | env from deploy_run.sh | B-133 |
| K5B-008 | Build, packaging, run & clients | Effective-config resolvers | `target_local/vm/mig/build` map backend/frontend to effective values | INF/deploy.sh:60-70 | internal | D-027 |
| K5B-009 | Build, packaging, run & clients | Exclude merge (defaults + extras − drops) | Builds EXCLUDES from DEF + CFG_EXTRA_EXCLUDES minus CFG_DROP_EXCLUDES | INF/deploy.sh:73-80 | every run | D-027 |
| K5B-010 | Build, packaging, run & clients | CLI argument parser | `--dry-run`, `--print-config`, `backend|frontend`, any other token = SUBPATH (a mistyped flag silently becomes a subfolder target) | INF/deploy.sh:82-90 | CLI | D-027 |
| K5B-011 | Build, packaging, run & clients | --print-config review mode | Prints effective reboot/targets/migration/commands/excludes/extra steps, then exits (changes nothing) | INF/deploy.sh:93-109 | CLI `--print-config` | D-027 |
| K5B-012 | Audit & consistency | Step recorder + tee'd log | `record/say/hr` collect name/state/note per step for the final table | INF/deploy.sh:112-115 | internal | D-027 |
| K5B-013 | Auth & security | Forced password-auth SSH options | `PreferredAuthentications=password, PubkeyAuthentication=no, StrictHostKeyChecking=no, ConnectTimeout=20` | INF/deploy.sh:117-118 | all SSH/rsync | B-134 |
| K5B-014 | Auth & security | VM password load (`azvmcred`) | Greps key from `oth/.cred`, records OK/FAIL | INF/deploy.sh:131-136 | Phase A step 1 | B-134 |
| K5B-015 | Build, packaging, run & clients | Tool pre-flight | Checks sshpass/rsync/ssh/az/curl; prints brew hint for sshpass | INF/deploy.sh:139-144 | Phase A step 2 | D-027 |
| K5B-016 | Build, packaging, run & clients | Local folder pre-flight | Verifies backend/frontend local dirs exist | INF/deploy.sh:147-151 | Phase A step 3 | D-027 |
| K5B-017 | Synchronization & Anchor | Public IP detection | `api.ipify.org` then `ifconfig.me` | INF/deploy.sh:154-155 | Phase A step 4 | A-046 |
| K5B-018 | Synchronization & Anchor | VM IP discovery via az | `az vm show -d … publicIps` with hard-coded fallback | INF/deploy.sh:156-161 | Phase A step 4 | A-043 |
| K5B-019 | Auth & security | NSG port-22 single-IP rule replace [AZURE] | Finds first NSG in RG + first rule with port 22, `az network nsg rule update` source=MYIP/32, Allow, Tcp, 22 (in-place update, never adds a rule) — runs also in `--dry-run` | INF/deploy.sh:163-181 | Phase A step 5 (always) | B-135, A-045 |
| K5B-020 | Auth & security | ufw single-IP SSH rotation via control plane [VM, root] | `az vm run-command`: allow 80/443, allow 22 from MYIP, delete every other 22/tcp ALLOW/DENY rule (reverse numbered), deny 22/tcp, re-allow 80/443, reload; NOT guarded by `--dry-run`; comment claims "insert at position 1" but code uses plain append | INF/deploy.sh:183-209 | Phase A step 5b (always when az + IP) | A-029, A-033, B-135 |
| K5B-021 | Build, packaging, run & clients | SSH reachability test with retries | 3 attempts (8 s apart) `echo SSH_OK; whoami; node -v; npm -v` | INF/deploy.sh:211-222 | Phase A step 6 | D-027 |
| K5B-022 | Safety & approvals | sshd self-heal via control plane [VM, root] | If SSH still fails: `systemctl enable` + `restart ssh/sshd` through run-command, re-test 3× — runs in `--dry-run` too | INF/deploy.sh:223-246 | SSH failure | D-027 |
| K5B-023 | Safety & approvals | Hard stop when VM unreachable | No Phase B if SSH_OK≠1; summary still printed | INF/deploy.sh:251-255 | SSH failure | D-027 |
| K5B-024 | Build, packaging, run & clients | rsync sync per target [VM] | `sshpass rsync -az` with excludes, no `--delete`, no `--checksum`, whole tree (not `--files-from`) | INF/deploy.sh:261-285 | Phase B | D-027 (MFI step 6 says `--checksum`, B-128 says `--files-from` — neither in code) |
| K5B-025 | Build, packaging, run & clients | /home user-path normalisation | Rewrites `/home/<other>/…` to `/home/mostafa/…` (fixes mustafa typo) | INF/deploy.sh:267-272 | Phase B | D-027 |
| K5B-026 | Build, packaging, run & clients | Subfolder-only sync | Appends SUBPATH to local+VM path for the chosen target | INF/deploy.sh:273-276 | CLI `frontend <subpath>` | D-027 |
| K5B-027 | Safety & approvals | Dry-run rsync preview | Adds `-n -v` to rsync; skips build/migrate | INF/deploy.sh:279, 287 | CLI `--dry-run` | D-027 |
| K5B-028 | Safety & approvals | Abort-on-sync/build failure guard | B_FAIL set by any rsync/build failure blocks restart/reboot | INF/deploy.sh:262, 284, 304, 342-343 | Phase B failures | D-027 |
| K5B-029 | Build, packaging, run & clients | Migration step `new` [VM DB] | `npx prisma generate && npx prisma migrate deploy` as mostafa | INF/deploy.sh:291-294 | Phase B (mig=new) | A-039, B-139 |
| K5B-030 | Safety & approvals | Destructive migration `reset` [VM DB] | `rm -rf prisma/migrations && prisma generate && migrate reset --force && migrate dev --name ini` (uses `migrate dev`, which MFI step 7 forbids) | INF/deploy.sh:295-296 | ODIN_MIG_OVERRIDE=reset (DB gate approve) | A-039, B-132 (no row records the `migrate dev` part) |
| K5B-031 | Build, packaging, run & clients | Remote build as mostafa [VM] | `export CI=1; bash -lc 'set -e; cd <vm> && <mig> && <build>'` | INF/deploy.sh:289-305 | Phase B | B-140 |
| K5B-032 | Build, packaging, run & clients | EXTRA_STEPS on VM [VM] | Runs each configured shell step as mostafa (skipped on dry-run / subpath) | INF/deploy.sh:308-321 | config `EXTRA_STEPS` | D-027 |
| K5B-033 | Build, packaging, run & clients | Service-list detection | Counts CFG_RESTART_SERVICES as array or string; empty = no services | INF/deploy.sh:330-339 | finalize stage | B-045 |
| K5B-034 | Build, packaging, run & clients | Verify port from project delta | `CFG_BACKEND_PORT` overrides 4013 | INF/deploy.sh:341 | finalize stage | B-045 |
| K5B-035 | Safety & approvals | `__ODIN_REBOOTED__` commit-point marker | Printed before restart so the agent never re-runs the deploy | INF/deploy.sh:346 | full run only | D-027 |
| K5B-036 | Build, packaging, run & clients | Restart only app services [VM] | `echo <pw> | sudo -S systemctl restart <svcs> && is-active` (VM password passed on the remote command line) | INF/deploy.sh:347-355 | full run, services configured | D-027, B-045 |
| K5B-037 | Build, packaging, run & clients | Skip restart for service-less projects | CFG_REBOOT=0 and no services → recorded OK "skipped by design" | INF/deploy.sh:356-358 | sandbox projects | B-045 |
| K5B-038 | Build, packaging, run & clients | Full VM reboot fallback [VM] | `sudo reboot` + 40 s wait when no services and CFG_REBOOT=1 | INF/deploy.sh:359-364 | full run | D-027 |
| K5B-039 | Testing | Basic backend reachability wait | On VM: curl 127.0.0.1:<port> 12×10 s for HTTP 200 | INF/deploy.sh:365-371 | full run | A-053 |
| K5B-040 | Middleware & DB registry | Baseline re-date after "verified" run | Calls `deploy_changes.py update` when no FAIL + SSH OK — also on `--dry-run`, partial (`backend` only/subpath) runs, and BEFORE deploy_verify.py runs; no `--project` passed (updates legacy lists) | INF/deploy.sh:376-394 | end of every run | B-131 (MFI says "only after PASS" — code contradicts) |
| K5B-041 | Audit & consistency | Final summary table + exit code | ✓/✗/! per step, pass/warn/fail counts, exit 1 on any FAIL | INF/deploy.sh:396-410 | end of run | D-027 |
| K5B-042 | Safety & approvals | Owner config: additive migrations only | `CFG_BACKEND_MIG="new"` (one-run reset reverted) | INF/deploy.config.sh:12-14 | sourced by deploy.sh | A-039 |
| K5B-043 | Build, packaging, run & clients | Owner config: extra/drop excludes | Adds media, *.copy, lockfile, uploads; drop list empty (public/ and package.json are synced) | INF/deploy.config.sh:22-29 | sourced | D-027 |
| K5B-044 | Safety & approvals | Owner config: service-restart "reboot solution" | `CFG_RESTART_SERVICES=(bendcore-staging organics-staging)`, `CFG_REBOOT=0`; no `CFG_BACKEND_PORT` so deploy.sh verifies :4013 while staging backend is :4014 | INF/deploy.config.sh:31-37 | sourced | B-045 (port mismatch not recorded) |
| K5B-045 | Build, packaging, run & clients | EXTRA_STEPS template (subdomain + nginx proxy example) | Commented example: mkdir, nginx site, symlink, `nginx -t && reload` | INF/deploy.config.sh:39-56 | owner edit | D-027 |
| K5B-046 | Middleware & DB registry | Change-detector project selection | `--project <pid>` or `ODIN_DEPLOY_PROJECT`, default `organics-prod-deploy` (no such project folder exists) | INF/deploy_changes.py:42-45 | CLI/env | B-044, D-029 |
| K5B-047 | Middleware & DB registry | Per-project baseline folder | Legacy flat `deploy-lists/*.json` for organics-prod-deploy, else `deploy-lists/<pid>/` (auto-mkdir) | INF/deploy_changes.py:48-51 | import | B-044 |
| K5B-048 | Middleware & DB registry | Targets from project delta (mapping file) | Reads `workspace/projects/<pid>/deploy/deploy-config.json` `targets[].name/local/excludes`; non-glob excludes → dirs (+defaults), glob excludes REPLACE default globs | INF/deploy_changes.py:59-78 `_targets_from_project` | scan/update | B-032, B-044 |
| K5B-049 | Middleware & DB registry | Legacy organics targets | Hard-coded `~/Desktop/VolatileWorkSpace/RBO-Staging/{b,f}` with per-target exclude sets | INF/deploy_changes.py:81-108 | default project | B-127 |
| K5B-050 | Middleware & DB registry | mtime tree scan with excludes | `os.walk` pruning excluded dirs, fnmatch globs on basename, `{relpath: int(mtime)}` | INF/deploy_changes.py:116-140 | scan/update | B-127 |
| K5B-051 | Middleware & DB registry | Baseline load/save | JSON `{saved_at, count, files}` per target | INF/deploy_changes.py:143-149 | scan/update | B-127 |
| K5B-052 | Middleware & DB registry | Diff added/modified/removed | Compares current vs saved; `changed` = added ∪ modified | INF/deploy_changes.py:152-163 `diff/scan_all` | scan | B-127 |
| K5B-053 | Safety & approvals | DB-sensitivity classifier | Path hints: schema (`prisma/schema.prisma`, `prisma/migrations`, `.prisma`), seed (`src/seed/`, `prisma/seed`, `seed-data`, `rbac.seed`, `seed-reference`, `seed.`) | INF/deploy_changes.py:169-184 `classify_db/db_scan_all` | scan/dbscan | B-132 |
| K5B-054 | Middleware & DB registry | Bootstrap baseline 2 years old | Every file dated now−2y so next scan = everything changed | INF/deploy_changes.py:113, 187-193 `seed_old` | CLI `seed-old`, deploy_run `--bootstrap` | B-129 |
| K5B-055 | Middleware & DB registry | Baseline update to real mtimes | Re-scans and saves real mtimes | INF/deploy_changes.py:196-202 `update_real` | CLI `update` | B-131 |
| K5B-056 | Middleware & DB registry | Changed-file list output | Prints changed paths for one target (for rsync `--files-from`; no script consumes it) | INF/deploy_changes.py:211-214 | CLI `changed <t>` | B-128 |
| K5B-057 | Middleware & DB registry | dbscan machine output | JSON + `DB_SENSITIVE: YES/NO` | INF/deploy_changes.py:215-219 | CLI `dbscan` (deploy_run 0b) | B-132 |
| K5B-058 | Middleware & DB registry | scan report + deploy decision | Per-target counts, first 10 changed, `DEPLOY_REQUIRED: YES/NO`, DB recommendation with ⚠ [schema]/[seed] lines | INF/deploy_changes.py:220-238 | CLI `scan` | B-127, B-132 |
| K5B-059 | Middleware & DB registry | Saved baseline lists (data) | Legacy backend 880 / frontend 668 files (2026-08-01); real-deployment-and-diagnosis-organics-07d7 395/679 (2026-08-22); revealer-6978 3/3 (2026-07-19) | INF/deploy-lists/** | written by update/seed-old | D-029 |
| K5B-060 | Orchestration core | deploy_run.sh bootstrap option | `--bootstrap` → seed-old before scan | INF/deploy_run.sh:36-40 | CLI | B-129, D-028 |
| K5B-061 | Orchestration core | STEP 0 change gate | Runs scan; `DEPLOY_REQUIRED: NO` → exit 0 "no deployment required" | INF/deploy_run.sh:42-47 | CLI | B-127, D-028 |
| K5B-062 | Safety & approvals | STEP 0b DB rebase approval gate | If DB_SENSITIVE: banner, `ODIN_DB_REBASE` or TTY prompt approve/deny; non-TTY without decision → exit 3; approve→reset, else new | INF/deploy_run.sh:49-78 | scan result | B-132, D-028 |
| K5B-063 | Orchestration core | STEP 1 deploy engine call | Records DEPLOY_START epoch, runs deploy.sh (never `--dry-run`), stops on non-zero | INF/deploy_run.sh:80-87 | deploy_run | D-028 |
| K5B-064 | Testing | STEP 2 strong verify gate | `deploy_verify.py --since-epoch <start>`; FAIL → stop | INF/deploy_run.sh:89-95 | deploy_run | B-130 |
| K5B-065 | Middleware & DB registry | STEP 3 baseline update | `deploy_changes.py update` (second update; deploy.sh already updated at its end) | INF/deploy_run.sh:97-98 | PASS | B-131 |
| K5B-066 | Testing | Build freshness check | `stat -c %Y` of VM `dist/` and `.next/BUILD_ID` ≥ deploy start | INF/deploy_verify.py:52-57, 98-106 | deploy_run STEP 2 | B-130 |
| K5B-067 | Testing | Endpoint poll to real 200 | curl on VM 127.0.0.1:4014 and :3001, 18×10 s | INF/deploy_verify.py:33-34, 60-71, 109-111 | STEP 2 | B-130 |
| K5B-068 | Testing | DB health via Prisma JS | base64-shipped node script counts users, rbacRoles, superadmins, appSettings (no `products` count although MFI B-130 lists it) | INF/deploy_verify.py:39-49, 74-90 | STEP 2 | B-130 |
| K5B-069 | Safety & approvals | Auto-remediate once [VM] | DB empty → `sudo systemctl restart bendcore-staging`, wait 30 s, re-check | INF/deploy_verify.py:118-125 | DB check fail (unless `--no-fix`) | B-130 |
| K5B-070 | Testing | Verdict + CLI | PASS only if fresh builds + 200s + DB ok; `--since-epoch`, `--no-fix`, default 45-min window | INF/deploy_verify.py:127-143 | CLI | D-030 |
| K5B-071 | Safety & approvals | Additive-only connection restore [VM] | `ufw allow 80/tcp`, `443/tcp` only | INF/ensure-connection.sh:11-13 | run on VM | A-030, D-031 |
| K5B-072 | Testing | VM health report | ufw status, running web services, `nginx -t`, curl 127.0.0.1:80/443/4013 | INF/ensure-connection.sh:15-32 | run on VM | D-031 |
| K5B-073 | Synchronization & Anchor | Phase-3 anchor/web shipping set | ANCHOR_FILES (6 server modules) + `.cred`; web = `odin_app/build/web`; web source globs lib/**/*.dart, web/**, pubspec.yaml | INF/phase3_gate.py:37-48 | import | D-019 |
| K5B-074 | Synchronization & Anchor | Deployment copies + first-run flag | `ARM/anchor`, `ARM/web`, `.web_src_fingerprint`, `workspace/logs/.phase3_firstrun_done`; `ODIN_SERVER_NAME` host | INF/phase3_gate.py:50-59 | import | D-019, A-057 |
| K5B-075 | Synchronization & Anchor | Anchor sha256 fingerprint | Per-file sha256 of the 6 files + `.cred` (original vs copy) | INF/phase3_gate.py:62-79 | compare | D-019 |
| K5B-076 | Synchronization & Anchor | Web source fingerprint | Single sha256 over sorted source paths+bytes | INF/phase3_gate.py:82-101 | compare/snapshot | A-056 |
| K5B-077 | Synchronization & Anchor | `init` subcommand | Creates deploy copies if missing (first-run signal), records web fingerprint | INF/phase3_gate.py:112-139 | production_full_checker | D-019 |
| K5B-078 | Synchronization & Anchor | `compare` decision | FIRST_RUN (exit 20) / CHANGED (10, lists files) / SAME (0) + `DECISION=` line | INF/phase3_gate.py:142-173 | production_full_checker | D-019, A-057 |
| K5B-079 | Testing | `validate` VM checks | Refreshes SSH firewall rule (writes), then SSH, nginx sites + `nginx -t`, SSL via curl to domain, anchor/web dirs, PostgreSQL + odin_anchor DB, `.cred` on VM, ufw snapshot | INF/phase3_gate.py:188-251 | production_full_checker | D-019 |
| K5B-080 | Middleware & DB registry | `ensure-db` create-if-missing | Creates `odin_anchor` PG DB only if absent; never fails deploy (no caller invokes it) | INF/phase3_gate.py:254-278 | CLI `ensure-db` only | no |
| K5B-081 | Auth & security | Postgres role link with rotated password [VM] | Creates/ALTERs role `odin_anchor` with a fresh 28-char password every deploy, OWNER + GRANT on DB, TCP test, returns DSN (password on psql command lines) | INF/phase3_gate.py:296-316 `_pg_link` | deploy-anchor | A-191 (partly: "odin_anchor DB linked") |
| K5B-082 | Build, packaging, run & clients | `deploy-anchor` [VM] | Firewall refresh, refresh copies, PG link, isolated venv + psycopg2, systemd drop-in (DSN + ExecStart venv python on 127.0.0.1:48619), `rsync --delete` (keeps .venv/log), daemon-reload/stop/pkill/reset-failed/start each in own SSH call, domain /health ×10, proof table exists in odin_anchor | INF/phase3_gate.py:319-383 | production_full_checker | D-019, A-191 |
| K5B-083 | Build, packaging, run & clients | `deploy-web` [VM] | Firewall refresh, copy freshest build, `rsync --delete` keeping `_serve_nocache.py`/`web.log`, restart `odin-web-online`, check /odin-web 200/301/302 | INF/phase3_gate.py:386-409 | production_full_checker | D-019 |
| K5B-084 | Synchronization & Anchor | `snapshot` + first-run stamp | Refresh copies from originals + fingerprint, write first-run flag | INF/phase3_gate.py:412-430 | after successful deploy+e2e | D-019 |
| K5B-085 | Orchestration core | phase3_gate CLI dispatcher | 7 subcommands init/compare/validate/ensure-db/deploy-anchor/deploy-web/snapshot | INF/phase3_gate.py:433-443 | CLI | D-019 |
| K5B-086 | Auth & security | Real-cert-only TLS context | `ssl.create_default_context()` (never self-signed) for production e2e | INF/phase3_e2e.py:26 | phase3_e2e | T-34 |
| K5B-087 | Testing | Anchor health + landing checks | /health = 200 + ok:true; landing 200 | INF/phase3_e2e.py:61-77 | production_full_checker step 7 | T-34 |
| K5B-088 | Testing | Web production page check | /odin-web 200/301/302, body looks like Flutter | INF/phase3_e2e.py:79-86 | step 7 | T-34 |
| K5B-089 | Testing | Production login simulation | anon read 401 → request-code → pending-code → login email+password+code → authed read 200 (pending-code GET sent without X-API-Key → 401 when key set; default login password hard-coded in source, value not copied) | INF/phase3_e2e.py:88-123 | step 7 | A-143 |
| K5B-090 | Testing | Production client-config assertion | `config.dart` has domain anchor + empty apiBaseUrl; `anchor_api.dart` contains "must go through the anchor" guard | INF/phase3_e2e.py:125-133 | step 7 | A-138 |
| K5B-091 | Build, packaging, run & clients | Anchor Docker image | python:3.12-slim, copies `server/`, CMD anchor_remote on 0.0.0.0:9100 (build context `../..` now resolves to `workspace/shared`, which has no `server/`) | INF/anchor/Dockerfile:4-15 | `docker compose up` | B-145, A-193 |
| K5B-092 | Build, packaging, run & clients | Anchor compose stack | restart unless-stopped, 9100:9100, `oth` mounted read-only, `anchor-data` volume, python healthcheck | INF/anchor/docker-compose.yml:3-23 | manual | B-145 |
| K5B-093 | Build, packaging, run & clients | Anchor systemd (docker) unit | `docker compose pull/up/down`, Restart=always | INF/anchor/odin-anchor.service:4-21 | manual install | B-145 |
| K5B-094 | Auth & security | Anchor nginx TLS proxy template | 80→301 https; 443 with certbot paths; `/anchor/` → 127.0.0.1:9100; optional web root | INF/anchor/nginx-anchor.conf:6-33 | manual | B-145 |
| K5B-095 | Build, packaging, run & clients | Anchor containerisation procedure | 5 steps (cred, compose, systemd, certbot+nginx, repoint clients); "prepared, not executed" | INF/anchor/DEPLOY.md:13-41 | manual | B-145 |
| K5B-096 | Structural | Azure connection profile | Non-secret host/user/port/os, RG/NSG/rule/VM names, procedure flags (dynamic IP, single IP, systemd not pm2, folder mapping), policy flags (approval-gated, autoReadOnlyAllowed, manualOnly) | INF/azure/connection.profile.json | read by server/infra_* | A-042, A-049 |
| K5B-097 | Safety & approvals | Azure framework doc | Key-based SSH + approval-gated plan (contradicts password SSH used by deploy.sh) | INF/azure/README.md:1-30 | doc | B-143 |
| K5B-098 | Structural | Azure inventory template | VM / TLS / ports tables, all TBD | INF/azure/inventory.md | doc | B-144 |
| K5B-099 | Orchestration core | odin-cto-brain skill | 10-step loop, agent routing, approval gate, hard rules, PENDING reminder | workspace/shared/skills/odin-cto-brain/SKILL.md:1-56 | Claude skill trigger | B-193, B-001 |
| K5B-100 | Voice | Global voice streaming asset definition | Ownership, endpoints, chunking, noise rules, bilingual, MD/DOCX export, activation | workspace/shared/assets/global_voice_streaming_asset.md:1-68 | doc / agent asset | B-194, B-199..B-203 |
| K5B-101 | Testing | Smart per-test time limits | quick 120 / single 300 / multi 900 / deploy 1200 / revealer 2400 s, +25 %/agent, `ODIN_TEST_MAX_SECONDS` cap | TST/harness.py:38-52 `smart_timeout` | tests | T-13 |
| K5B-102 | Testing | Post-test keep/clean decision | ODIN_TEST_KEEP / ODIN_TEST_CLEAN / ODIN_TEST_SEED_ON_PASS / interactive prompt; non-interactive default = keep | TST/harness.py:56-82 `SeedingPrompt._decide` | end of each test | B-182 |
| K5B-103 | Testing | Cleanup with diagnosis snapshot | Logs last 6 pool entries then `projects.delete_project` + extra cleanup | TST/harness.py:84-118 `SeedingPrompt.run` | end of each test | B-192 |
| K5B-104 | Testing | CTO capability-dialog auto-resolver | `capability_options` → existing agent or CTO-self; `⟦resolve⟧` message | TST/harness.py:121-143 | tests | B-182 |
| K5B-105 | Testing | CTO-present assertion | Returns True unless "project cto" is excluded (expression `True and (… or True)` is always True) | TST/harness.py:146-158 `assert_cto_present` | tests | T-13 |
| K5B-106 | Testing | Shared-pool readers | `pool/pool_text/voices` from `main_task` | TST/harness.py:167-186 | tests | B-182 |
| K5B-107 | Testing | Detail-propagation (leak) check | Needles that no member restated | TST/harness.py:189-196 `propagated` | tests | no |
| K5B-108 | Testing | Forbidden-method drift check | Regex matches in member actions, excluding "never/do not" instruction lines | TST/harness.py:199-202 `drift` | tests | no |
| K5B-109 | Audit & consistency | Test truthfulness gate | Fake success = claims_success AND hidden faults; skips QA verdicts and resolved/past-tense lines; OOM/"step reported FAIL" counted only if in last 12 lines | TST/harness.py:205-247 `truthfulness` | every test scorecard | no |
| K5B-110 | Testing | Hallucinated-agent detector | Voices not in allowed + system labels + company agents | TST/harness.py:250-272 `only_these_agents` | tests | no |
| K5B-111 | Per-project features & integrations | Provider ground truth | Klaviyo flows/metrics/lists; Veeqo orders (same 7-day window as anchor), carriers, user | TST/harness.py:275-294 | T2/T3 | T-13 |
| K5B-112 | Testing | Scoreline printer | ✅/❌ per row | TST/harness.py:297-299 | tests | no |
| K5B-113 | Testing | Deterministic redeploy-overwrite helper | v1 marker push → read → v2 → redeploy → must read v2 (sandbox path; not used by any test) | TST/harness.py:302-340 `verify_deploy_overwrite` | none (unused) | no |
| K5B-114 | Testing | CTO plan checkpoint | Mines "(plan)" pool entry; flags obsolete roles (frontend/backend/database/shipping), operator given build task, operator before build/deploy (key hand-off exempt), unknown roles, DevOps before build | TST/harness.py:343-405 `evaluate_plan` | run_flow_monitored(plan_check), preflight | no |
| K5B-115 | Testing | Per-role expected output + time | Expected seconds/outputs per role; warn at 1.5× | TST/harness.py:408-433 `_STEP_EXPECT/step_expectation` | run_flow_monitored | no |
| K5B-116 | Testing | Chunked self-recovering run monitor | Preflight GO/NO-GO, start run, plan checkpoint, quota stop, owner-block auto-answer via `operations.provide`, engine-inflight breadcrumb liveness, per-step stall bound, hard cap | TST/harness.py:437-595 `run_flow_monitored` | T4, T5 | B-181 (owner auto-answer only) |
| K5B-117 | Testing | Watchdog run helper + resource failure protocol | Stops on quota/limit text (no retry), on stall, on cap | TST/harness.py:599-659 `run_flow` | T2, T3 | no |
| K5B-118 | Testing | SOC E2E (sections 1-6) | 8-agent roster, monitor-only + auto-remediation off, read-only SSH guard refuses `systemctl restart`, findings registry, approvals DENIED, FP classification, resolve→reopen | TST/e2e_soc.py:16-65 | agent bridge shell | T-25 |
| K5B-119 | Testing | SOC E2E (sections 7-18) | PDF/DOCX/MD/PPTX reports, last-run persistence, 23:00 ET schedule + catch-up, deep checks (UEBA, clickjacking, miner, ports, forensics), same-IP-many-accounts with owner IP excluded, predictions, Fernet backup + date-aware recovery + escrow gate, multi-cloud inventory, white-scope + correlations, humanized report, generic quota monitor, intel fusion + ATT&CK hunts, SOC blueprint on a new project | TST/e2e_soc.py:67-180 | agent bridge shell | no (T-25 lists only the first sections) |
| K5B-120 | Testing | Zoom real-flow HTTP driver | /projects/intake (≤3 clarify hops), forbidden-role deviation check, POST /projects (daily 06:00), GET /agents/all (reads missing `workspace/shared/logs/zoom_spec.txt`; docstring step 5 run-now not implemented) | TST/e2e_real_flow.py:28-92 | CLI | T-24 |
| K5B-121 | Testing | Suite entry point | `python3 testing/` → run_all.main | TST/__main__.py:1-11 | CLI | T-12 |
| K5B-122 | Testing | Anchor node isolation probe | T1 health, T2 CORS preflight, T3 projects read, T4 404 root-cause (wrong base vs right vs unknown path), T5 async fast-ack + lifecycle follow ≤120 s; final verdict | TST/isolate_anchor.py:68-182 | phase_ctl `isolate` | T-22 |
| K5B-123 | Scheduling & notifications | File-driven test daemon | RUN_NOW mtime → (re)start with filter; STOP → kill run, children, stray `python3 testing/`, `claude -p You are`; STATUS/RUN_SEQ/latest.log; SEED_ON_PASS + haiku gates | TST/loop.sh:19-69 | `nohup bash loop.sh` | D-032 |
| K5B-124 | Testing | Permanent live log monitor | `tail -n 200 -F latest.log` in relaunch loop | TST/monitor.sh:8-18 | manual | D-033 |
| K5B-125 | Testing | Per-project child integrity test | Skeleton dirs, index.json, odin_core row, every tracked file indexed (au.is_tracked), zero audit violations, deps resolve to `shared/` | TST/phase7_lib.py:33-100 `run_project_test` | phase7_monitor, project tests | B-210, T-26 |
| K5B-126 | Testing | Create→monitor→clean lifecycle | 4 shapes via `create_owner`, deploy reuse via `request_capability`, link 3 agents, monitor (placement/heal/in_db), delete, exact count baseline, shared deploy files survive | TST/phase7_lifecycle.py:33-125 | CLI | B-209, T-28 |
| K5B-127 | Audit & consistency | Parent monitor over all projects | Child test + placement violations + `au.heal(force)` + post-heal issues; excludes PROTECTED_PROJECTS | TST/phase7_monitor.py:28-77 | CLI | B-207, T-27 |
| K5B-128 | Testing | 4 prompt-created projects with acceptance | Intake → create (autoApprove) → run-now → message growth → role-keyword team coverage via project_agents JOIN, shared-deploy reuse, no duplicate deploy_changes.py, 0 violations, 0 cross-owner refs, exact delete baseline; report `workspace/logs/prompt4_report.json` | TST/phase7_prompt4.py:77-244 | CLI | T-31, B-051 |
| K5B-129 | Testing | Prompt-driven loop (3 specs) | Same journey without acceptance roles; report `prompt_loop_report.json` | TST/phase7_prompt_loop.py:36-154 | CLI | T-30, B-051 |
| K5B-130 | Testing | Real first-time run of every project | SOC via `/soc/run`, others `/projects/<pid>/run-now`; quiescence timing; audit+placement+DB delta; report `realrun_report.json` | TST/phase7_realrun.py:74-155 | CLI | T-32, B-050 |
| K5B-131 | Audit & consistency | Adversarial injection test S1-S8 | Cross-owner + cross-type write redirect, misplaced file move, duplicate promote-to-shared, foreign-ref rewrite, resolve+load capability, override overlay executed, 0 violations, exact cleanup | TST/phase7_strong.py:68-175 | CLI | B-208, T-29 |
| K5B-132 | Testing | Preflight: engine + tool permissions | claude available; build agents have Write/Edit/Bash; read-only agents write-stripped | TST/preflight.py:40-68 | harness, CLI | T-14 |
| K5B-133 | Auth & security | Preflight: credential presence | `oth/.cred` contains required key names | TST/preflight.py:71-87 | CLI `--keys` | T-14 |
| K5B-134 | Testing | Preflight: role catalogue + resources | Each role resolves and has Resources & Dependencies block | TST/preflight.py:90-107 | harness, CLI | T-14 |
| K5B-135 | Testing | Preflight: cheap haiku plan dry-run | Throwaway project, plan_pipeline, evaluate_plan, no-op step detector, long-plan warning; inconclusive ≠ NO-GO | TST/preflight.py:110-169 | CLI `--plan` | T-14 |
| K5B-136 | Testing | Test 3 Klaviyo read-only | Email-only project; connected, real counts, total=live+draft, agent reports real numbers, metrics/lists, no devops, CTO, truthful | TST/readonly_email_klaviyo_workflows.py:22-77 | run_all | T-16, B-167 |
| K5B-137 | Testing | Test 2 Veeqo read-only | Fulfillment-only, no folder, connected, real count reported, carriers, CTO, truthful | TST/readonly_shipping_vq_status.py:24-77 | run_all | T-15, B-166 |
| K5B-138 | Testing | Auto-discovering suite runner | Re-exec under .venv, discovers EVERY *.py except run_all/harness/__init__/__main__ (not only files with main), known order first, filter word, PROGRESS.txt board, default SEED_ON_PASS + haiku gate | TST/run_all.py:35-161 | CLI / loop.sh | T-12 |
| K5B-139 | Testing | Test 5 agent redeploy overwrite | Unique token; DevOps agent deploys→edits→redeploys (`rsync --checksum`) to `/home/mostafa/sandbox-revealer`; harness re-reads via SSH; SKIP if VM unreachable | TST/sandbox_deploy_overwrite_check.py:45-126 | run_all filter `overwrite` | T-18, B-169 |
| K5B-140 | Testing | Test 4 Revealer multi-agent | Needs-only brief, team derived, plan checkpoint, Fullstack owns code, operators operational, QA reviewed, real build + UI files, CTO, truthful, finished | TST/sandbox_revealer_multiagent.py:96-215 | run_all filter `revealer` | T-17, B-168 |
| K5B-141 | Middleware & DB registry | Connector seeding (deadlock-safe) | Folders+index.json, `pg_terminate_backend` of idle-in-transaction/lock-waiting odin_core sessions, upsert 5 connector rows, then sync folders/files | TST/seed_connectors.py:30-70 | CLI (also auto-run by run_all) | T-33, B-048 (session-kill step not recorded) |
| K5B-142 | Build, packaging, run & clients | Test 6 anchor online deploy [VM] | Firewall rotate, reachability skip, :80 snapshot, ODIN_ANCHOR_SKIP, `rm -f *.py` then rsync 5 files (omits `anchor_manage.py` which anchor_remote imports) + full `.cred`, systemd unit with StartLimit 30/60 s, per-sudo SSH calls, LOCAL + PUBLIC route proof, crash diagnostics, round-trip, :80 + prod-folder safety, enable | TST/test_anchor_online.py:169-375 | CLI, phase_ctl `redeploy`, run_all | T-19 |
| K5B-143 | Auth & security | Guarded nginx `odin-proxy` site [VM] | LE cert for domain (certbot if missing), self-signed for bare IP, tar backup of /etc/nginx, branded landing, /odin-anchor + /odin-web locations, `nginx -t`, restore on failure or if existing site status changes — called unconditionally (docstring says off unless `ODIN_ANCHOR_NGINX=1`) | TST/test_anchor_online.py:71-166, 308 `_nginx_proxy` | Test 6 | A-191, A-061 |
| K5B-144 | Auth & security | Close extra ports (ufw + NSG) | Deletes ufw allow 48619/48620 and NSG rule `odin-<port>` (az run from the VM shell) | TST/test_anchor_online.py:58-68, 306-307; TST/test_web_online.py:162-163 | Tests 6/7 | no |
| K5B-145 | Build, packaging, run & clients | Test 7 web online deploy [VM] | Skip if serving (ODIN_FORCE_DEPLOY overrides), flutter build with `ODIN_ANCHOR=http://<vm-ip>:48619` and no base-href, `rsync --checksum --delete`, no-cache server on 127.0.0.1, ports cleaned, nginx untouched, persistent `odin-web-online` unit | TST/test_web_online.py:59-222 | CLI, run_all | T-20, A-205, A-061 |
| K5B-146 | Testing | Anchor chain trace | brain localhost → anchor local on VM → anchor public from VM → public from Mac + DNS → web → CORS preflight/headers → nginx odin-proxy, `nginx -t`, service state | TST/trace_chain.py:42-90 | phase_ctl `trace` | T-21, A-190 |
| K5B-147 | Auth & security | VM security audit (+ --fix) | ufw, NSG (az from VM), listeners, nginx sites, verdict for 48619/48620; `--fix` deletes those ufw/NSG rules only | TST/vm_security_audit.py:27-84 | phase_ctl `audit`/`auditfix` | T-23 |
| K5B-148 | Testing | Stale test-project cleanup | Dry-run default, `--apply`; skip while STATUS=RUNNING; keep T2, KEEP_PROJECTS ids, newest T3/revealer/overwrite; delete other test-pattern ids (reads `utils/results/*` and `data/projects.json` — both paths do not exist after the store remap, so the safety check is inert) | UTL/cleanup_projects.py:30-110 | CLI | no |
| K5B-149 | Build, packaging, run & clients | Wait-for-iPhone production install | Retries 180×5 s for a non-emulator iOS device, `flutter run --release` with production dart-defines, watches log for INSTALLED / SIGNING error | UTL/install_to_phone.sh:4-43 | CLI | A-239, D-015 |
| K5B-150 | Scheduling & notifications | Zoom pipeline scheduled run_cmd | Creates daily 06:00 task if absent; sets `run_cmd` → `server/zoom_pipeline_run.py --pid --cid`, cwd | UTL/set_runcmd.py:1-19 | CLI | no |
| K5B-151 | Testing | Endpoint smoke test | /health, /, /mobile.html, /state/project.json, /chat, /dispatch gated (required:true), /voice/stt + /voice/tts codes; X-Odin-Token support | UTL/smoke_test.sh:8-43 | CLI | A-204 |
| K5B-152 | Voice | Neural TTS self-test | EN + AR via `voice_service.synthesize`, wav >5 KB → /tmp | UTL/voice_selftest.py:16-52 | CLI | A-169 |
| K5B-153 | Synchronization & Anchor | Phase control bridge loop | CMD file mtime → run curated action → OUT.log/STATUS | SH/phase_ctl.sh:89-118 | agent writes CMD | D-025, A-189 |
| K5B-154 | Testing | Bridge `health` | curl brain/anchor/sim/webhook locals + online anchor/web | SH/phase_ctl.sh:30-43 | CMD `health|status` | D-025 |
| K5B-155 | Synchronization & Anchor | Bridge `send` | POST request with webhook, poll 40×3 s, emit RESULT as soon as filled | SH/phase_ctl.sh:45-68 | CMD `send <pid> <prompt>` | D-025 |
| K5B-156 | Testing | Bridge `tail` / `vm` | last 30 log lines; read-only VM anchor health, :80, anchor.log | SH/phase_ctl.sh:70-81 | CMD | D-025 |
| K5B-157 | Build, packaging, run & clients | Bridge `redeploy` / `trace` / `isolate` / `audit` / `auditfix` | Runs test_anchor_online (VM writes), trace_chain, isolate_anchor, vm_security_audit (`--fix` changes firewall) | SH/phase_ctl.sh:83-87 | CMD | D-025, A-105 |
| K5B-158 | Synchronization & Anchor | Standalone anchor + poller drill | Starts brain if absent, frees port, anchor (PG DSN, JSON fallback) + poller 4 s, opens landing; Ctrl-C stops only these | SH/anchor_up.sh:13-71 | CLI | D-021, A-188 |
| K5B-159 | Orchestration core | Two-phase loop controller | RUN file / typed: phase2, phase3, stop, done; stop kills checker/bridge/anchor/poller/webhook/sim + frees 9100/9104/9300/8080 | SH/anchor_loop.sh:23-87 | nohup / RUN file | D-020, A-189 |
| K5B-160 | Synchronization & Anchor | Poller supervisor | Relaunch `local_poller_http.py` within 5 s via `pgrep -f "[l]ocal_poller…"` | SH/poller_supervisor.sh:20-35 | phase checkers | D-022, A-185 |
| K5B-161 | Auth & security | Agent terminal bridge | Runs ANY command written to CMD in the owner shell (no allow-list), echoes it, file capture, stdin /dev/null, `ODIN_CMD_TIMEOUT` watchdog (900 s) | SH/agent_terminal_bridge.sh:51-96 | owner starts; agent writes CMD | D-026, A-223, B-028 |
| K5B-162 | Build, packaging, run & clients | Dev checker: env bootstrap | venv create/activate, pip requirements + faster-whisper, `gen_test_keys.py` | SH/development_full_checker.sh:7-18 | `bash development_full_checker.sh` | D-011, A-059 |
| K5B-163 | Safety & approvals | Dev checker: remove prod marker | `rm -f anchor_prod.js` so sim defaults to local | SH/development_full_checker.sh:26-29 | phase2 | D-011, D-039 |
| K5B-164 | Build, packaging, run & clients | Dev checker: port reset + cleanup trap | Kill 9100/8080 at start; Ctrl-C trap kills PIDs, frees all ports (8000 only if started), desktop/flutter scoped pkill | SH/development_full_checker.sh:36-77 | phase2 | A-224, D-011 |
| K5B-165 | Synchronization & Anchor | Dev checker: anchor on/off choice | `USE_ANCHOR` or TTY prompt (offline drill) | SH/development_full_checker.sh:79-88 | phase2 | D-011 |
| K5B-166 | Build, packaging, run & clients | Dev checker: brain + anchor + supervised poller + webhook | Reuse/start brain :8000; anchor :9100 (nohup, PG DSN); single supervisor; webhook :9300 | SH/development_full_checker.sh:90-125 | phase2 | D-011 |
| K5B-167 | Synchronization & Anchor | Dev checker: request-page seed + sim server | Writes `anchor_seed.js` (key + local webhook) to anchor-layer and root, starts `sim_server.py` :9104, opens page and landing | SH/development_full_checker.sh:127-159 | phase2 | D-011, D-040, A-199 |
| K5B-168 | Synchronization & Anchor | Dev checker: control bridge start | `bash phase_ctl.sh` from repo root (file lives in `shells/`) | SH/development_full_checker.sh:161-166 | phase2 | D-025 (§0.3 / §6 item 2 notes the path bug) |
| K5B-169 | Build, packaging, run & clients | Dev checker: desktop launch | npm install if needed, `npm run dev` tracked for Ctrl-C | SH/development_full_checker.sh:168-174 | phase2 | D-011 |
| K5B-170 | Auth & security | Dev checker prints app login | Banner prints owner email + default password (value not copied) | SH/development_full_checker.sh:187 | phase2 | D-011 (§6 item 19) |
| K5B-171 | Build, packaging, run & clients | Dev checker: Flutter setup | brew cask install if missing; guarded `flutter create` (backs up main.dart); pub get; launcher icons | SH/development_full_checker.sh:192-215 | phase2 | D-011, D-016 |
| K5B-172 | Testing | Dev checker: compile check | `flutter analyze` → counts errors, prints first 40 | SH/development_full_checker.sh:217-231 | phase2 | D-011 |
| K5B-173 | Build, packaging, run & clients | Dev checker: release web + no-cache server | `flutter build web --release ODIN_FORCE_ENV=phase2`, `_web_serve.py` on 0.0.0.0:8080 (LAN-visible), auto-open | SH/development_full_checker.sh:233-271 | phase2 | D-012, A-141 |
| K5B-174 | Build, packaging, run & clients | Dev checker: iOS simulator clean build + simctl | Reuse/boot iPhone sim, `flutter build ios --simulator`, simctl install/launch | SH/development_full_checker.sh:273-318 | phase2 | D-014 |
| K5B-175 | Build, packaging, run & clients | Dev checker: keep-alive | Infinite sleep until Ctrl-C | SH/development_full_checker.sh:320-325 | phase2 | A-224 |
| K5B-176 | Orchestration core | Prod checker: gate + decision | init, compare (tee log), FIRST_RUN deploy / CHANGED ask (or ODIN_PHASE3_YES) / SAME start-only / unknown = safe no-deploy | SH/production_full_checker.sh:51-78 | `bash production_full_checker.sh` | D-018, A-058 |
| K5B-177 | Build, packaging, run & clients | Prod checker: validate → deploy-anchor → web build → deploy-web → e2e → snapshot [VM] | Each step gated; failure exits 1 without stamping | SH/production_full_checker.sh:83-140 | prod checker | D-018 |
| K5B-178 | Synchronization & Anchor | Prod checker: production client config | Writes `anchor_prod.js` (brain "", anchor, wh, key) and production `anchor_seed.js` | SH/production_full_checker.sh:146-161 | prod checker | D-039, D-040 |
| K5B-179 | Build, packaging, run & clients | Prod checker: local players | brain, supervised poller → online anchor, webhook, request page via `http.server` :9104 `?env=prod`, open web + landing, desktop `VITE_ODIN_ENV=production`, flutter web-server :8080 | SH/production_full_checker.sh:166-208 | prod checker | D-018 |
| K5B-180 | Build, packaging, run & clients | Prod checker: real-iPhone-only mobile | `ODIN_SKIP_MOBILE`; physical device or wait 180×5 s, never simulator | SH/production_full_checker.sh:209-241 | prod checker | D-015 |
| K5B-181 | Testing | Run-timing records (data) | 27 runs {pid, task, cached, ok, seconds, ts}; 19 for real-deployment-and-diagnosis-organics-07d7; 9/27 ok; slowest 2099 s | data/run_timings.json | written by run_timer | C-045 |
| K5B-182 | Per-project features & integrations | SOC 24/7 evidence sensor | One JSON line: load, MemAvailable, disk %, failed ssh (last 200 auth lines), external non-80/443/22 listeners, top CPU, top auth/subscribe IP (last 300 nginx lines); rotate at 5 MB; renice/ionice (with `set -e`, `grep -c … || echo 0` yields "0\n0" → malformed JSON on zero matches) | SOC/sensor/soc_sensor.sh:11-39 | systemd timer | A-232, B-154 |
| K5B-183 | Safety & approvals | SOC sensor resource caps | oneshot, CPUQuota 4 %, MemoryMax 48M, Nice 19, idle IO | SOC/sensor/soc-sensor.service:5-12 | timer | B-154 |
| K5B-184 | Scheduling & notifications | SOC sensor timer | OnBoot 2 min, every 5 min | SOC/sensor/soc-sensor.timer:4-10 | systemd | B-154 |
| K5B-185 | Per-project features & integrations | SOC project creation with 3 controlled agents | CTO Orchestrator, Threat-Hunting Architect (theoretical mode), Operations Investigator; daily 23:00 America/New_York, requireApproval false | SOC/setup/create_soc.py:12-75 | CLI | A-227, P-08 |
| K5B-186 | Safety & approvals | SOC agent rules (prompt-injected) | Only CTO talks to owner; one investigator; prod-affecting → approval request; two report levels; Architect never touches prod, dedupe KB, presence≠compromise; Investigator read-only default, load playbooks first, early-stop, FP analysis, "10-min gap ≠ legitimate" | SOC/setup/create_soc.py:19-50 | agent prompts | no |
| K5B-187 | Per-project features & integrations | SOC expansion agents + roster sync | Removes short-key dupes, registers AssetSurface/Predictor/Recovery/BehaviorIDS by role name (force), syncs project members | SOC/setup/add_soc_agents.py:16-44 | CLI | no (C §5 item 6 notes drift) |
| K5B-188 | Per-project features & integrations | SOC knowledge base seeding | asset inventory (embeds VM IP — not copied), evidence standards + confidence ladder + redaction list, FP catalog, dependency security, 7 compact catalogs, detailed PB-APP-001, 18 template playbooks, 5 detection YAMLs, cadence YAML, incident history + known-good baseline + history dirs | SOC/setup/seed_soc_knowledge.py:14-347 | CLI | P-08 ("KB of 43 files") |
| K5B-189 | Scheduling & notifications | SOC daily scheduled run_cmd | Task "RedBerry SOC (daily 11PM ET)" → `server/soc_run.py --pid --mode full --cid`; prints next run ET + local | SOC/setup/set_soc_schedule.py:8-28 | CLI | P-08 |
| K5B-190 | Per-project features & integrations | Ops platform bootstrap (NestJS) | CORS on, `/api` prefix, PORT default 4000 | FS/backend/src/main.ts:5-13 | `npm run start` | P-04, D-038 |
| K5B-191 | Middleware & DB registry | TypeORM Postgres wiring | DATABASE_URL, 7 entities, `synchronize:false` (SQL owns schema), 5 feature modules + health | FS/backend/src/app.module.ts:18-43 | app boot | no |
| K5B-192 | Per-project features & integrations | Health route | GET /api/health → status ok, service, ts | FS/backend/src/health/health.controller.ts:3-9 | HTTP | no |
| K5B-193 | Per-project features & integrations | CRM routes (HubSpot) | GET deals (top 200 by amount), contacts, pipeline summary; POST sync upserts 100 deals | FS/backend/src/crm/crm.controller.ts:4-27; crm.service.ts:16-43 | HTTP | no |
| K5B-194 | Per-project features & integrations | HubSpot client | Bearer from env, CRM v3 deals/contacts mapping (`fetchContacts` unused) | FS/backend/src/crm/hubspot.client.ts:9-62 | CRM sync | A-209 (connector, not this code) |
| K5B-195 | Per-project features & integrations | Email routes (Klaviyo) | GET campaigns, engagement summary (open/click rates); POST sync flows (live/draft counts) | FS/backend/src/email/email.controller.ts:4-22; email.service.ts:16-50 | HTTP | no |
| K5B-196 | Per-project features & integrations | Klaviyo client | `Klaviyo-API-Key`, revision 2024-10-15, /flows, /campaigns (`fetchCampaigns` unused) | FS/backend/src/email/klaviyo.client.ts:9-57 | Email sync | A-207 (connector, not this code) |
| K5B-197 | Per-project features & integrations | Fulfillment routes (Veeqo) | GET orders, shipments, throughput by status; POST sync orders + allocations/shipments | FS/backend/src/fulfillment/fulfillment.controller.ts:4-27; fulfillment.service.ts:16-52 | HTTP | no |
| K5B-198 | Per-project features & integrations | Veeqo client | `x-api-key`, /orders page_size, maps allocations to shipments | FS/backend/src/fulfillment/veeqo.client.ts:9-48 | Fulfillment sync | A-208 (connector, not this code) |
| K5B-199 | Per-project features & integrations | Support ticket workflow | GET tickets, GET summary, POST create, PATCH tickets/:id/status (no auth, no status validation) | FS/backend/src/support/support.controller.ts:5-28; support.service.ts:12-32 | HTTP | no |
| K5B-200 | Per-project features & integrations | Analytics API | GET /analytics (unified), /crm, /email, /fulfillment from SQL views | FS/backend/src/analytics/*.ts | HTTP | no |
| K5B-201 | Middleware & DB registry | Ops schema migration 0001 | crm_contacts/deals, email_campaigns/engagement, fulfillment_orders/shipments, support_tickets + indexes, pgcrypto | FS/backend/prisma/migrations/0001_init.sql | `psql -f` / `npm run migration:run` | D-038 (env only) |
| K5B-202 | Middleware & DB registry | Analytics views 0002 | pipeline/win/close rates, by-stage, campaign + overview engagement, throughput + avg transit, fulfillment overview | FS/backend/prisma/migrations/0002_analytics_views.sql | `psql -f` (not in `migration:run`, which runs only 0001) | no |
| K5B-203 | Per-project features & integrations | Ops dashboard page | Server component; 6 guarded fetches; Deals/Engagement/Shipments panels; link to analytics | FS/frontend/app/page.tsx:18-40; components/*Panel.tsx | browser | no |
| K5B-204 | Per-project features & integrations | Analytics page + dependency-free bar chart | CRM/Email/Fulfillment analytics panels | FS/frontend/app/analytics/page.tsx:16-32; AnalyticsPanels.tsx; BarChart.tsx | browser | no |
| K5B-205 | Per-project features & integrations | Frontend API client + config | `NEXT_PUBLIC_API_BASE` default localhost:4000/api, 12 calls, no-store | FS/frontend/lib/api.ts:2-24; next.config.js | page render | D-037 |
| K5B-206 | Structural | Ops platform README | Layout, endpoint table (omits analytics, orders, contacts, support summary), run steps, env-keys rule | FS/README.md | doc | P-04 |
| K5B-207 | Synchronization & Anchor | In-process anchor router (FastAPI) | POST /requests (key + project check), GET /requests/{id}, POST ack, GET /poll, POST result, admin config/requests/counts (admin routes have no key check) | ARM/anchor/anchor.py:54-108 `build_router` | brain mounts router | A-178, C-025, C-026 |
| K5B-208 | Per-project features & integrations | Connector facts (read-only grounding) | Klaviyo flows_summary or Veeqo orders since 7 days by project type / prompt keywords | ARM/anchor/anchor.py:112-131 `_connector_facts` | process() | A-180 |
| K5B-209 | Synchronization & Anchor | Fast read-only answer formatter | Formats Veeqo count / Klaviyo live-draft-total without LLM | ARM/anchor/anchor.py:134-160 `_format_facts` | process() | no |
| K5B-210 | Synchronization & Anchor | Last-answer extractor with noise filter | Prefers latest member deliverable; skips plan/review/orchestrator and telemetry breadcrumbs | ARM/anchor/anchor.py:163-198 `_last_answer` | process() tier 3 | no |
| K5B-211 | Orchestration core | 3-tier external request processing | Tier 1 fast-readonly (`ODIN_ANCHOR_FAST`), tier 2 single grounded read-only engine call with 90 s cap (`ODIN_ANCHOR_SINGLE`), tier 3 full CTO→team run for heavy verbs / `payload.orchestrate` (timeout 300 s) | ARM/anchor/anchor.py:201-285 `process` | poller | A-180 (tiers not recorded) |
| K5B-212 | Safety & approvals | External scope/privacy guard injection | `workspace_mw.scope_answer_guard(name, external=True)` with inline fallback text | ARM/anchor/anchor.py:244-252 | process() | A-098, A-095 |
| K5B-213 | Synchronization & Anchor | In-process background poller | Thread: next_pending → processing → process → submit_result → retry_due; `ODIN_ANCHOR_NO_POLLER=1` disables | ARM/anchor/anchor.py:293-320 `start_local_poller` | brain start | A-182 |
| K5B-214 | Middleware & DB registry | Store path remap | Redirects projects/company_agents/connectors/keys → shared/core-registry, models → config, soc/hubspot settings → utils, chat files → workspace/chats, anchor files → anchor-layer, projects/* → workspace/projects | ARM/anchor/store.py:21-58 `_REMAP/_p` | every store read/write | C-044 (remap not recorded) |
| K5B-215 | Middleware & DB registry | Per-project sharded JSON stores | main_tasks, operations, run_timings, approvals, schedules, notifications split into `workspace/projects/<pid>/data/jsons/` (non-project → `_shared`), merged on read | ARM/anchor/store.py:70-150 | read_json/write_json | no |
| K5B-216 | Middleware & DB registry | Atomic write + odin_core lockstep | tmp+replace under RLock, then `workspace_mw.sync_row` best-effort | ARM/anchor/store.py:166-179 | write_json | C-044 |
| K5B-217 | Auth & security | Manage login (email + password hash + target code) | Unsalted SHA-256 hash default in source (overridable via cred), per-target random 6-digit code (TTL 600 s, single use), sessions 7 days, remembered devices 30 days | ARM/anchor/anchor_manage.py:25-31, 91-153 | /manage/login | A-154, A-143 |
| K5B-218 | Auth & security | Client allow/stop settings | `allow_mobile` / `allow_web` toggles | ARM/anchor/anchor_manage.py:59-80 | Manage page | A-154 |
| K5B-219 | Auth & security | Pending-code read for desktop | Single target or all live targets (+ back-compat single fields) | ARM/anchor/anchor_manage.py:106-122 | GET /manage/pending-code | no |
| K5B-220 | Auth & security | Device remember + session check + logout | check_device, valid_session, logout | ARM/anchor/anchor_manage.py:126-165 | manage routes | A-154 |
| K5B-221 | Synchronization & Anchor | Pluggable queue storage (Postgres / JSON) | `ANCHOR_PG_DSN` → table anchor_requests(jsonb) + indexes, else JSON (last 2000 rows); dispatching primitives | ARM/anchor/anchor_queue.py:72-233 | import (`_pg_init` at 449) | A-192 |
| K5B-222 | Synchronization & Anchor | Large-result file offload | >32 000 chars → `anchor-layer/active_requests/<rid>/<random>.json` pointer, rehydrate on read, cleanup on delete | ARM/anchor/anchor_queue.py:33-34, 236-286 | submit_result | A-192 |
| K5B-223 | Synchronization & Anchor | Request lifecycle + history | 13 statuses, history appended on every change; enqueue/next_pending (sent_to_local, poll_limit)/mark_processing/submit_result (idempotent on terminal) | ARM/anchor/anchor_queue.py:36-52, 292-351 | anchor routes | A-176, A-175 |
| K5B-224 | Synchronization & Anchor | Webhook delivery with retries | POST result to caller URL (server-side request to any URL); 2xx → acknowledged→finished; else ack_pending + next_retry_at; FAILED after retry_count | ARM/anchor/anchor_queue.py:354-408 | submit_result, retry sweep | A-179, A-177 |
| K5B-225 | Synchronization & Anchor | Queue admin ops | cfg/set_cfg (retry_count, retry_interval_sec, poll_limit), list, counts, cancel, remove, clear_all (+ files) | ARM/anchor/anchor_queue.py:54-69, 411-445 | admin/manage routes | A-177, A-197 |
| K5B-226 | Synchronization & Anchor | Durable WhatsApp-style mirror | SYNC {projects, agents, pools, mirror, updated} loaded at start, persisted on each push | ARM/anchor/anchor_remote.py:44-80 | POST /sync | A-183 |
| K5B-227 | Synchronization & Anchor | Anchor landing page | HTML with projects-synced count, last sync age, request counts, Manage link | ARM/anchor/anchor_remote.py:83-125, 326-328 | GET / (Accept html) | A-187 |
| K5B-228 | Auth & security | Anchor Manage page (UI) | Login card (email/password/code/remember), Resend code, requests table with delete, Clear all, mobile/web toggles, sign out; proxy-aware API base; token in localStorage | ARM/anchor/anchor_remote.py:128-224 | GET /manage | A-154 |
| K5B-229 | Safety & approvals | Crash-proof request handler | Every GET/POST/DELETE wrapped → JSON 500, service keeps serving | ARM/anchor/anchor_remote.py:272-299 | every request | no |
| K5B-230 | Auth & security | CORS + API-key check | `Access-Control-Allow-Origin: *`, allowed headers incl. X-Manage-Token, X-Odin-Client; `X-API-Key` must equal ANCHOR_API_KEY when set | ARM/anchor/anchor_remote.py:231-264 | every JSON response | A-178 |
| K5B-231 | Auth & security | Web/mobile client gate | `X-Odin-Client` web|mobile → 403 if stopped, 401 if no valid manage session | ARM/anchor/anchor_remote.py:308-320 `_client_blocked` | projects/mirror/pool/requests | A-143, A-154 |
| K5B-232 | Synchronization & Anchor | Health / _status routes | `/`, `/health`, `/healthz` JSON with endpoints list; `/anchor/v1/_status` | ARM/anchor/anchor_remote.py:331-345 | HTTP | A-178 |
| K5B-233 | Auth & security | Manage API routes | GET pending-code (key), me, requests, settings; POST request-code (public), check-device, login, logout, settings, requests/clear; DELETE manage/requests/{id} | ARM/anchor/anchor_remote.py:347-362, 454-477, 542-551 | Manage page / desktop badge | C-026, A-154 |
| K5B-234 | Synchronization & Anchor | Mirror read routes | GET /projects (stale >90 s, age_seconds), /mirror/{key}, /pool/{pid} paginated (offset/limit) and delta `?since=<seq>` | ARM/anchor/anchor_remote.py:364-415 | web/mobile | A-184, A-138 (delta cursor not recorded) |
| K5B-235 | Synchronization & Anchor | Poll / request status / admin routes | GET poll, requests/{id}, admin requests/counts/config (all key-checked) | ARM/anchor/anchor_remote.py:417-444 | poller, 3rd party | A-178 |
| K5B-236 | Synchronization & Anchor | Intake route with chat/command senders | POST /requests (key + client gate), project check skipped for sender chat/command | ARM/anchor/anchor_remote.py:479-501 | 3rd party, web/mobile | A-178 |
| K5B-237 | Synchronization & Anchor | Sync push route | POST /sync merges projects/agents/pools/mirror, stamps updated, persists | ARM/anchor/anchor_remote.py:503-525 | poller | A-183 |
| K5B-238 | Synchronization & Anchor | ack / result / admin config routes | POST ack (no key check), result (key), admin config (key) | ARM/anchor/anchor_remote.py:527-538 | 3rd party, poller | A-178 |
| K5B-239 | Synchronization & Anchor | Webhook retry sweep thread | `q.retry_due()` every 30 s | ARM/anchor/anchor_remote.py:554-568 | serve() | A-181 |
| K5B-240 | Synchronization & Anchor | Anchor HTTP server CLI | ThreadingHTTPServer `--host/--port` (default 0.0.0.0:9100) | ARM/anchor/anchor_remote.py:571-583 | systemd / scripts | D-024 |
| K5B-241 | Auth & security | Poller HTTP client | Adds X-API-Key; HTTPS with `CERT_NONE` (no TLS verification) | ARM/anchor/local_poller_http.py:26-51 | poller | D-023 |
| K5B-242 | Synchronization & Anchor | poll_once dispatch | command → `_run_command`, chat → brain stream, else `anchor.process`; posts result; immediate sync after chat/command | ARM/anchor/local_poller_http.py:54-97 | poller loop | A-182 |
| K5B-243 | Synchronization & Anchor | Remote write commands | create_project (autoApprove), create_chat, rename_chat, delete_chat, clear_scope, run_now, mark_notif, post_message (reply/attachment/client_msg_id), delete_message, meeting_report | ARM/anchor/local_poller_http.py:118-219 `_run_command` | anchor tasks sender=command | B-198 (meeting_report only) |
| K5B-244 | Synchronization & Anchor | Chat through brain /scope/stream | Ensures a scope chat, drains SSE ≤90 s, reads last assistant message back | ARM/anchor/local_poller_http.py:222-262 | sender=chat | A-136 |
| K5B-245 | Synchronization & Anchor | Mirror push (projects/pools/agents/mirror) | company + project + standalone chat scopes, each pool capped to last 60 (avoids HTTP 413), activity/health, mirror keys roles/company_agents/all_agents/connectors/activity/hubspot/notifications/ui_projects/ui_agents/ui_types/ui_connectors/chats | ARM/anchor/local_poller_http.py:276-347 `sync_push` | every poll cycle | A-182, A-184 |
| K5B-246 | Synchronization & Anchor | Poller main loop | poll + sync every interval; `--anchor`, `--interval` | ARM/anchor/local_poller_http.py:350-369 | supervisor | D-023 |
| K5B-247 | Build, packaging, run & clients | Deployed web build (compiled) | Flutter release with base /odin-web/, splash, manifest, self-unregistering SW, version 0.1.0 | ARM/web/index.html, manifest.json, version.json, flutter_service_worker.js | deploy-web | D-013, A-191 |
| K5B-248 | Build, packaging, run & clients | Project deploy delta: staging organics | host/user (values not copied), restart_services, domains, targets with service/port 4014/3001/migration/build/excludes (only name/local/excludes are read by code) | workspace/projects/real-deployment-and-diagnosis-organics-07d7/deploy/deploy-config.json | deploy_changes `--project` | P-07, B-032 |
| K5B-249 | Build, packaging, run & clients | Clone/sandbox delta: revealer-6978 | JSON delta (ports 4113/3112, own DB, no domain) + generated `CFG_*` shell delta for deploy.sh (`CFG_REBOOT=0`, seed in build) | workspace/projects/revealer-6978/deploy/{deploy-config.json, revealer-6978.config.sh} | ODIN_DEPLOY_CONFIG / --project | B-046, P-09 |

Row count: 249.

---

## 2. Not in MFI

| ID | Capability | Evidence |
|---|---|---|
| K5B-080 | `phase3_gate ensure-db` create-if-missing (never called) | INF/phase3_gate.py:254-278 |
| K5B-107 | Harness detail-propagation (leak) check | TST/harness.py:189-196 |
| K5B-108 | Harness forbidden-method drift check | TST/harness.py:199-202 |
| K5B-109 | Harness truthfulness gate (QA-excluded, tail-gated) | TST/harness.py:205-247 |
| K5B-110 | Hallucinated-agent voice detector | TST/harness.py:250-272 |
| K5B-112 | Scoreline printer | TST/harness.py:297-299 |
| K5B-113 | Deterministic redeploy-overwrite helper (unused) | TST/harness.py:302-340 |
| K5B-114 | CTO plan checkpoint (evaluate_plan) | TST/harness.py:343-405 |
| K5B-115 | Per-role expected output/time health warnings | TST/harness.py:408-433 |
| K5B-117 | run_flow watchdog + quota failure protocol | TST/harness.py:599-659 |
| K5B-119 | e2e_soc sections 7-18 (reports, schedule, deep checks, UEBA, prediction, recovery/escrow, inventory, white-scope, humanized report, quota, hunts, blueprint) | TST/e2e_soc.py:67-180 |
| K5B-144 | Extra-port close (ufw + NSG `odin-<port>`) inside Tests 6/7 | TST/test_anchor_online.py:58-68 |
| K5B-148 | Stale test-project cleanup utility | UTL/cleanup_projects.py |
| K5B-150 | Zoom pipeline scheduled `run_cmd` setter | UTL/set_runcmd.py |
| K5B-186 | SOC agent rule texts (3 controlled agents) | SOC/setup/create_soc.py:19-50 |
| K5B-187 | SOC expansion agents registration + roster sync | SOC/setup/add_soc_agents.py |
| K5B-191 | Ops platform TypeORM wiring (`synchronize:false`) | FS/backend/src/app.module.ts |
| K5B-192 | Ops platform /api/health | FS/backend/src/health/health.controller.ts |
| K5B-193 | Ops CRM routes + HubSpot sync | FS/backend/src/crm/* |
| K5B-195 | Ops Email routes + Klaviyo sync | FS/backend/src/email/* |
| K5B-197 | Ops Fulfillment routes + Veeqo sync | FS/backend/src/fulfillment/* |
| K5B-199 | Ops support-ticket workflow | FS/backend/src/support/* |
| K5B-200 | Ops analytics API | FS/backend/src/analytics/* |
| K5B-202 | Analytics SQL views migration 0002 | FS/backend/prisma/migrations/0002_analytics_views.sql |
| K5B-203 | Ops dashboard page + panels | FS/frontend/app/page.tsx |
| K5B-204 | Ops analytics page + bar chart | FS/frontend/app/analytics/page.tsx |
| K5B-209 | Fast read-only answer formatter | ARM/anchor/anchor.py:134-160 |
| K5B-210 | Last-answer extractor with telemetry-noise filter | ARM/anchor/anchor.py:163-198 |
| K5B-215 | Per-project sharded JSON stores | ARM/anchor/store.py:70-150 |
| K5B-219 | Per-target pending-code read for desktop badge | ARM/anchor/anchor_manage.py:106-122 |
| K5B-229 | Crash-proof request handler (500 instead of crash) | ARM/anchor/anchor_remote.py:272-299 |

Partly covered (MFI row exists but the specific behaviour is not recorded): K5B-020 (ufw step not dry-run-guarded; "insert at 1" comment wrong), K5B-024 (no `--checksum`, no `--files-from`), K5B-030 (`reset` uses `migrate dev`), K5B-040 (baseline re-dated on dry-run / partial / before verify), K5B-044 (verify port 4013 vs staging 4014), K5B-068 (no `products` check), K5B-081 (role password rotated every deploy), K5B-141 (kills odin_core sessions), K5B-143 (nginx proxy always applied), K5B-211 (3 processing tiers + env flags), K5B-214 (store remap), K5B-234 (delta `since` cursor), K5B-243 (9 of 10 remote command kinds).

---

## 3. Requested-category confirmations

### (a) Certified deploy pipeline, step by step — FOUND
Entry: `bash INF/deploy_run.sh` (D-028). **[VM]** = changes the VM, **[AZURE]** = changes Azure, **[LOCAL]** = changes only local files.
1. Optional bootstrap `--bootstrap` → `deploy_changes.py seed-old` — deploy_run.sh:37-40 → deploy_changes.py:187-193 **[LOCAL]** (baseline files).
2. STEP 0 change detection `scan` — deploy_run.sh:42-47 → deploy_changes.py:220-238; stops with exit 0 when `DEPLOY_REQUIRED: NO`. Read-only.
3. STEP 0b DB gate `dbscan` — deploy_run.sh:52-78 → deploy_changes.py:169-184, 215-219; approve→`ODIN_MIG_OVERRIDE=reset`, deny/none→`new`; non-TTY without `ODIN_DB_REBASE` → exit 3. Read-only. (MFI step 2 "show changed files and ask approval" is NOT implemented; only the DB gate asks.)
4. STEP 1 `deploy.sh` (no flags) — deploy_run.sh:80-87:
   - A1-A4 cred, tools, local dirs, public IP, VM IP via `az vm show` — deploy.sh:131-161 (reads only).
   - A5 NSG port-22 rule → MYIP/32 — deploy.sh:163-181 **[AZURE]**.
   - A5b ufw rotation via `az vm run-command` as root — deploy.sh:190-209 **[VM]**.
   - A6 SSH test — deploy.sh:213-222; A6b sshd enable+restart via control plane on failure — deploy.sh:226-241 **[VM]**.
   - B rsync per target (no --delete, no --checksum) — deploy.sh:278-285 **[VM]**.
   - B migration `new` (generate + migrate deploy) or `reset` (destructive incl. `migrate dev`) — deploy.sh:291-297 **[VM DB]**.
   - B build — deploy.sh:298-305 **[VM]**.
   - B EXTRA_STEPS — deploy.sh:309-321 **[VM]** (empty in current config).
   - Restart `bendcore-staging organics-staging` — deploy.sh:347-355 **[VM]** (or full reboot 359-364 **[VM]** if no services and CFG_REBOOT=1).
   - Reachability curl :4013 (config has no CFG_BACKEND_PORT; staging backend is :4014) — deploy.sh:366-371 read-only.
   - Baseline re-date `deploy_changes.py update` — deploy.sh:381-394 **[LOCAL]** — runs BEFORE STEP 2, so a later verify failure leaves the lists already updated (contradicts "only after PASS").
5. STEP 2 `deploy_verify.py --since-epoch` — deploy_run.sh:89-95: freshness, :4014/:3001 200, DB counts; auto-restart `bendcore-staging` once — deploy_verify.py:118-125 **[VM]**.
6. STEP 3 `deploy_changes.py update` — deploy_run.sh:97-98 **[LOCAL]**.
Phase-3 (anchor/web) pipeline: production_full_checker.sh:54-139 → phase3_gate.py init/compare (local) → validate (refresh_firewall **[AZURE/VM]**, rest read-only) → deploy-anchor (PG role password + drop-in + rsync --delete + service restart **[VM]**) → flutter build (local) → deploy-web (rsync --delete + restart **[VM]**) → phase3_e2e (read-only) → snapshot **[LOCAL]**.

### (b) `deploy.sh --dry-run` behaviour — FOUND; current code does NOT comply with the owner's rule
- NSG: rule update to MYIP/32 runs in dry-run — deploy.sh:163-181. It updates the existing first port-22 rule in place (replaced, never stacked) → **complies** (it also forces Allow/Tcp/22 on that rule; only the first NSG in the RG is touched).
- ufw: full rotation runs in dry-run, with no `DRY` check — deploy.sh:190-209: `ufw allow 80/tcp`, `allow 443/tcp`, `allow from MYIP to 22`, deletes every other 22/tcp ALLOW and DENY rule, `ufw deny 22/tcp`, allow 80/443 again, `ufw reload`. Replacing the SSH allow rule is allowed, but adding the deny-22 rule, adding 80/443 rules if missing, and reloading ufw are additional changes → **violates** "change NOTHING else".
- sshd: if SSH fails after the rotation, `systemctl enable` + `restart ssh/sshd` via control plane runs in dry-run — deploy.sh:223-241 → **violates**.
- Ports 80/443: only touched through the ufw `allow` commands above (never removed) — deploy.sh:193-194, 198-199 → **violates** the strict rule (they are changes when the rules were absent), safe in effect.
- File sync: `rsync -n -v` preview only — deploy.sh:279 → complies.
- Build: skipped (`[[ $DRY -eq 1 ]] && continue`) — deploy.sh:287 → complies.
- Migration: skipped (same `continue`, before the migration case) — deploy.sh:287-297 → complies.
- Extra steps / restart / reboot / verify: skipped (`$DRY -eq 0` guards) — deploy.sh:310, 344 → complies.
- Local baseline: `deploy_changes.py update` runs on a successful dry-run — deploy.sh:383-385 → **violates** (re-dates the lists, so the next real scan reports "nothing to deploy" for files never deployed).
- Local log file created — deploy.sh:28-29 (bookkeeping only).
Verdict: **non-compliant** — 3 violations (ufw extras, sshd restart, baseline re-date); NSG part complies.

### (c) Smart change detection — FOUND
- Folder change detection by mtime vs saved per-target lists: INF/deploy_changes.py:116-163; decision line 228.
- DB change detection by path hints (schema/seed), not by schema diff: INF/deploy_changes.py:169-184, 229-238; gate in INF/deploy_run.sh:52-78.
- Baselines: `seed-old` (2-year-old dates) INF/deploy_changes.py:187-193; `update` 196-202; stored in INF/deploy-lists/ (legacy 880/668 files, 2026-08-01; organics-07d7 395/679, 2026-08-22; revealer-6978 3/3, 2026-07-19). deploy.sh and deploy_run.sh never pass `--project`, so they read/update the legacy `organics-prod-deploy` lists, not the 07d7 per-project lists.
- Mapping files: `workspace/projects/<pid>/deploy/deploy-config.json` (read at INF/deploy_changes.py:59-78; only `name/local/excludes` used), shell delta `revealer-6978.config.sh` for deploy.sh via `ODIN_DEPLOY_CONFIG` (INF/deploy.sh:56), owner override `INF/deploy.config.sh`, folder mapping in `INF/azure/connection.profile.json`.
- Phase-3 detection: sha256 per anchor file + `.cred` and one web-source fingerprint, first-run flag, decision exit codes — INF/phase3_gate.py:62-173; state files `ARM/web/.web_src_fingerprint`, `.last_build_id`. The 6 deploy copies in `ARM/anchor/` are byte-identical to `server/` (checked), so `compare` would report SAME for the anchor.

### (d) Per-project features in project code — FOUND
- **redberry-continuous-soc**: sensor (K5B-182..184; JSON bug when grep counts 0), create_soc (K5B-185/186), add_soc_agents (K5B-187), seed_soc_knowledge (K5B-188), set_soc_schedule (K5B-189).
- **full-services-19jul**: NestJS backend — health, CRM/HubSpot, Email/Klaviyo, Fulfillment/Veeqo, Support tickets, Analytics views, SQL migrations 0001/0002 (K5B-190..202); Next.js dashboard + analytics page (K5B-203..205); README (K5B-206). No auth on any route; `migration:run` applies only 0001; `fetchContacts` and `fetchCampaigns` unused; `deploy/` empty.
- **odin-external-arms**: `deploy/anchor/` = the 6 anchor modules shipped by phase3 (K5B-207..246); `deploy/web/` = compiled Flutter release (K5B-247). `code/` empty.
- **real-deployment-and-diagnosis-organics-07d7**: deploy delta only (K5B-248).
- **Clone projects**: `revealer-6978` is the sandbox clone of the production deploy flow (K5B-249: own ports 4113/3112, own DB, generated `CFG_*` delta); `odin-external-arms/deploy/anchor` is a deployment clone of `server/` (identical bytes).
- NOT FOUND (only `.gitkeep`): code/deploy for daily-egypt-amazon-product-poster, email-klaviyo-workflows-read-only-18ca, fulfillment-vq-status-read-only-dc1e, hubspot-crm-operator, vm-sentinel, zoom-real-flow.

### (e) Environment / phase scripts — FOUND
- development_full_checker.sh: K5B-162..175 (bridge start path bug at SH/development_full_checker.sh:164; prints login at :187; web served on 0.0.0.0:8080 at :257).
- production_full_checker.sh: K5B-176..180 (never calls `phase3_gate ensure-db`; does not start phase_ctl; banner says "MOBILE sim" at :250 despite real-device policy).
- phase_ctl.sh: K5B-153..157 (help text at :112 omits trace/isolate; `vm` defaults to port 9100 when ANCHOR_PORT is unset, while the VM anchor listens on 48619).
- anchor_up.sh: K5B-158. anchor_loop.sh: K5B-159. poller_supervisor.sh: K5B-160. agent_terminal_bridge.sh: K5B-161 (unrestricted command execution).

### (f) Test harness scripts and what they prove — FOUND
- harness.py: shared helpers (K5B-101..117).
- e2e_soc.py: SOC roster, safety guards, registry memory, approvals denied, FPs, reports, schedule, deep checks, UEBA, prediction, recovery, inventory, hunts, blueprint (K5B-118/119). Runs at import time and calls `sys.exit`, so auto-discovery by run_all ends the runner (`SystemExit` is not caught by `except Exception`).
- e2e_real_flow.py: intake → no forbidden roles → create → org roster (K5B-120).
- __main__.py / run_all.py: run every discovered test (K5B-121/138). Discovery includes test_anchor_online, test_web_online, vm_security_audit, seed_connectors, isolate_anchor, trace_chain, phase7_*, preflight, so `python3 testing/` with filter `all` deploys to the VM and edits nginx.
- isolate_anchor.py: anchor reachable, CORS, data read, 404 cause, async fast-ack + round trip (K5B-122).
- loop.sh / monitor.sh: autonomous file-driven runner and live view (K5B-123/124).
- phase7_lib/monitor/lifecycle/strong/prompt4/prompt_loop/realrun: structural integrity, audit self-heal to 0, exact baseline after delete, shared-capability reuse, adversarial correction, timed real runs (K5B-125..131).
- preflight.py: engine/tool permissions, creds, roles, cheap plan grading (K5B-132..135).
- readonly_email_klaviyo_workflows.py / readonly_shipping_vq_status.py: real provider numbers reach the agent's answer, read-only, single-agent team (K5B-136/137).
- sandbox_deploy_overwrite_check.py: agent redeploy really overwrites on the VM (K5B-139).
- sandbox_revealer_multiagent.py: CTO derives team, correct plan, real build + UI, QA, truthful (K5B-140).
- seed_connectors.py: seeding, not a test (K5B-141).
- test_anchor_online.py: online anchor deploy + round trip + no collateral damage (K5B-142..144); ships 5 files and omits `anchor_manage.py` after deleting `*.py` on the VM.
- test_web_online.py: online web build/deploy/persistence (K5B-145).
- trace_chain.py: locate where a 404 is born (K5B-146).
- vm_security_audit.py: firewall/listener exposure; `--fix` removes 48619/48620 (K5B-147).
- infra/phase3_e2e.py: production endpoints, login flow, client config (K5B-86..90); its pending-code read omits the API key.
- utils/smoke_test.sh (K5B-151), utils/voice_selftest.py (K5B-152), deploy_verify.py (K5B-066..070).
- NOT FOUND in my files: `real_production_deploy_devops_only.py` (Test 1, referenced by loop.sh/run_all docs), `tests/e2e.py`.


<!-- ==================== PART CH0 ==================== -->

# CH0 — Chat gap-check, part 00 (`/home/claude/chats_part_00`)

Read in full (5,569 lines, about 500 KB, around 150 chat files). Every candidate was grepped against MFI.md and K1, K2A, K2B, K3, K4A, K4B, K5A and K5B. Secret values that appear in the transcript are not copied here. That includes cred-file contents echoed in tool output, VM IPs and keys.

Timestamps are the chat epoch, followed by the UTC date. Paths are shortened to `<scope>/<chat-id>`, and all of them sit under `workspace/chats/scopes/`.

## 1. Added from chats (not covered by MFI/K)

| ID | Category | Item | Source | Evidence quote | Status |
|---|---|---|---|---|---|
| CH0-001 | Safety & approvals | The rotation helper `_ufw_script` adds `deny 22/tcp`. That rule lands above the new single-IP allow, so ufw denies the owner's own IP and SSH times out. | chat__cd22e3846c74/8cbb96a66f41 @1787668217 (2026-08-25) assistant | "each run it re-issued `ufw allow 80/443` and added a `deny 22/tcp`" | reported broken in chat |
| CH0-002 | Owner rule | Dynamic-IP rotation must be a pure replace. Swap only the source IP of the existing NSG port-22 rule and of the ufw 22 allow. Add no rule, no extra deny and no re-added 80/443. Do not re-diagnose; go back to the agreed rules. | chat__cd22e3846c74/8cbb96a66f41 @1787667581 and @1787667917 (2026-08-25) user | "no add but replace as before ... and no new allow to new ports" | stated requirement |
| CH0-003 | Safety & approvals | The stray `DENY 22` came back between turns. A background or scheduled rotation re-runs the old `_ufw_script`. The permanent fix (a pure port-22 swap) was proposed but never applied. | chat__cd22e3846c74/8cbb96a66f41 @1789407246 (2026-09-14) assistant | "the stray `DENY 22` reappeared between turns" | reported broken in chat |
| CH0-004 | Safety & approvals | A delete proposal offers an "archive first" safety net: bundle the files into one .tgz, then `rm` the exact named files, with no globbing. The owner approved and the run verified 0 left. | chat__6b736bf1c7b9/d9a01fad4caf @1785217134 (2026-07-28) assistant; user "approved" @1785217152 | "Say "archive first" for that; say "just delete" for a straight removal" | confirmed working in chat |
| CH0-005 | Other | Text-chat replies match the language of the latest message (Arabic ↔ English) automatically. A fixed language can be saved as a preference. Code, paths and service names stay as they are. | company/2f30a30f409f @1783572089 (2026-07-09) assistant; company/d7a7b2bad54e Arabic turns | "I detect the language you write in and reply in that same language" | confirmed working in chat |
| CH0-006 | Owner rule | When asked who created the Odin app or agent, answer the owner, Mostafa Adawy. Anthropic only made the model. Some test chats answered "Anthropic" until the owner corrected them. | chat__b6496b3879e6/9ae3d9c6f4e2 @1783278226 (2026-07-05) user; chat__ea029bf09cd6/3185305d522c @1783277981 | "I am not asking on opus I am asking about this app Odin ai agent" | stated requirement (answers inconsistent) |
| CH0-007 | Owner rule | Owner's correction for the Egypt Amazon content project: no Fullstack or DevOps, only Content Creator plus Content Reviewer. The daily 09:00 run must go through Odin's operational schedule, not a hand-built launchd or cron job. | member__daily-egypt-amazon-product-poster__Content Creator/972574b0907f @1785532875 (2026-07-31) assistant quoting owner; …/65bc03ee0f48 @1784493344 CTO mandate | "no need to handle anything in DevOps... create this internally using the operational mode" | stated requirement |
| CH0-008 | Per-project features & integrations | The Egypt Amazon launchd 09:00 job crashed on every run (EX_CONFIG 78): macOS TCC blocks background jobs from `~/Desktop`. No content was produced after 2026-07-20. After the owner said twice to remove it, the job was reinstalled, and it still exited 78. | …Content Creator/972574b0907f @1785532443, @1785533336 (2026-07-31) assistant | "last exit code = 78: EX_CONFIG" | reported broken in chat |
| CH0-009 | Per-project features & integrations | The amazon.eg live scrape parses 0 products on every run and falls back to the seed list without saying so. WebSearch and WebFetch are not granted in member contexts, so "search the web daily" is never met. | …Content Creator/ece0ed2087d1 @1784498817 (2026-07-19); …/972574b0907f @1785532875 | "live fetch failed (parsed 0) -> seed fallback" | reported broken in chat |
| CH0-010 | Per-project features & integrations | Social posts must carry an accurate disclosure: sourced from amazon.eg public listings, not affiliated with Amazon. The unsupported "shared with consent / affiliate" lines were replaced. Side bug: the `posts.py` guard now adds the line twice. | …Content/d7d583ebbad2 @1783576888 (2026-07-09); …QA _ Reviewer (operational)/22fbcfd4e20b @1783576518 | "not affiliated with, sponsored by, or endorsed by Amazon" | stated requirement (applied; side bug reported) |
| CH0-011 | Per-project features & integrations | Content QA hard gate: each of 3 distinct products needs its own working /dp/ link, a verified price and a real description. The scraper paired titles and links by list index, so one product got another's link. Fixed by parsing per-item blocks and de-duplicating by title. | …QA _ Reviewer/22fbcfd4e20b @1783576518; …Project CTO/71018ee2c857 @1783600950 (2026-07-09) | "That index-zipping was the root cause" | reported broken, then fixed in chat |
| CH0-012 | Audit & consistency | The AUDIT EYE gate ("you wrote ZERO real files / folder empty") fires while the member runs propose-first, with Write disabled and Bash blocked by the hook. Result: repeated rejections. The CTO then called the "can't build" report false because the files existed. | …Content Creator/d71d2cebd906 @1783575343, @1783576327; CTO review @1783576355 (2026-07-09) | "The automated "is the folder empty?" gate rejects on a false premise" | reported broken in chat |
| CH0-013 | Audit & consistency | AUDIT EYE rejects honest reports that only quote errors from a diagnosis ("fatal/crash", "a step reported FAIL"). The CTO confirmed one of these reports. | …Content Creator/972574b0907f @1785532443; Fulfillment/fc8c8668bf2a @1785433992, CTO confirmed @1785434012 | "AUDIT EYE (try 1) rejected this step: hidden errors in your output" | reported broken (false positive) |
| CH0-014 | Safety & approvals | The read-only hook blocks harmless reads in member runs: a plain `ls`/`cd`, `launchctl list` and jq pipelines. | …Content Creator/d71d2cebd906 @1783576327; …/ece0ed2087d1 @1784493692 | "a plain `ls`/`cd` was blocked by the read-only hook" | reported broken in chat |
| CH0-015 | Orchestration core | Member reports get cut off mid-sentence or mid-JSON. The CTO rejects them as incomplete. Accepted fixes were compact reports of about 25 lines or fewer. | fulfillment…Fulfillment/1c49312673cb @1785420206; …/8efd5b62b37c @1785433685 (2026-07-30); …/7088dcded3da @1785533540 | "The report is truncated mid-JSON" | reported broken in chat |
| CH0-016 | Audit & consistency | The CTO review runs its own live read-only provider calls to check member figures. Examples: Veeqo X-Total-Count and per-status counts; Klaviyo profile pulls. | fulfillment…Fulfillment/256f1c2d5e88 @1782904271; …/bd7bfdee96f0 @1783152883; email…/9e9bfd605870 @1784583347 | "I independently verified every figure against the live Veeqo API" | confirmed working in chat |
| CH0-017 | Per-project features & integrations | Veeqo "total orders" means the all-time X-Total-Count. A count for a date window must be labelled as a window count. | fulfillment…Fulfillment/256f1c2d5e88 @1782904271 (2026-07-01) CTO review; …/35647f8c6c5c mandate @1783131037 | "it's a mislabeled window count, not the total" | stated requirement |
| CH0-018 | Audit & consistency | A value from an injected or shared-pool live pull is not evidence. A member must cite its own GET, with endpoint and HTTP status. | fulfillment…Fulfillment/7088dcded3da @1785533540 (2026-07-31) CTO review; email…/a24fe0218a8e @1783131585 | "per the truth rules an injected value isn't evidence" | stated requirement |
| CH0-019 | Orchestration core | The "Also cover (from YOUR request)" gap-check step added another project's daily task (the Amazon poster run) and team dialogue to the Veeqo-only fulfillment project. The members refused under the project guardrails, and the CTO still marked "Needs fix". | fulfillment…Fulfillment/7088dcded3da @1785533428; …EasyPost/75717e341f4b @1785533716 (2026-07-31) | "that is a **different project** ... not this one" | reported broken in chat |

## 2. Already covered

About 45 more candidates from this part are already in MFI or K. Ten examples:

| Chat item | Maps to |
|---|---|
| Per-chat Claude session resume and multi-turn memory (FALCON-77 test) | A-013, A-108, K2A-197 |
| `run.sh` reload off by default, `ODIN_RELOAD=1`; token gate `/chat` `/dispatch` `/voice`, `?token=` for SSE; mobile.html with Tailscale/Cloudflare/LAN runbook | MFI (ODIN_RELOAD, phone-access), A-240 |
| Dynamic-IP rotation (az only to replace the IP; SSH as `mostafa`; 80/443 sacred; single /32) | A-029, A-045, A-046, B-093, MFI §721/§776 |
| Anchor 3-factor login (email + hashed password + per-target desktop code, 10-min code, 7-day session, 30-day device, allow_web/allow_mobile, X-Odin-Client) | K3 (CODE_TTL, SESSION_TTL, DEVICE_TTL), K5B, A-143 |
| Hybrid DB (odin_core Postgres + sharded JSON + SQLite anchor), single creation door, 3-layer audit, approval severity and red security-alarm channel | K1-001, C-029, B-039, K2A/K2B approvals, MFI security-alarm |
| Role catalogue: 10 technical + 10 operational + CTO Brain; Fullstack merges front/back/db; company agents; removed agents remembered | K2B-001, K1-101, A-076 |
| Agents are real `claude -p` subprocesses (`--disallowedTools AskUserQuestion`, 600 s); read-only PreToolUse hook and safe-redirect rule | A-001, D-043, K2B-097, K1-086, K1-087 |
| Member mandate / upstream hand-off / CTO "Confirmed:"/"Needs fix:" review; proposal → approval popup or chat; scheduled run with approval already granted | K2A-109, K2A-164, B-178, K2A-066, K2A |
| Provider tutorials read first (golden rule); Veeqo status stops at "shipped"; scalar extraction; EasyPost read-only tracking after Veeqo; Veeqo→EasyPost generic chain proven live (2026-07-30) | B-157, B-158, B-160, B-161, A-11 |
| Engine auth or limit messages (OAuth expired, weekly limit) not counted as done; SOC daily monitor result line; per-scope seq counters, chat_registry, company feed | K2A-170, K5A (soc_run), K3-096, K2A-053 |

## 3. Contradictions

1. **Chat memory status.** MFI §814 says "Test persistent chat memory … PENDING". In chat 2e6a41cd6e97 (@1782161107, 2026-06-22) a live 2-turn recall test passed ("The codeword is FALCON-77"). The status should be raised to verified-run.
2. **Six specialist agents.** MFI A-063 lists six specialist agents (Frontend, Backend, Database, …) from `agents/*.agent.md`. The owner said on 2026-07-08 (company/d7a7b2bad54e @1783547762) that this front/back split belongs to the old version. Odin agreed the `.agent.md` files are stale and that Fullstack is a single merged role (K1-101).
3. **ufw rotation.** MFI A-029, A-045 and B-093 and the owner's protocol say "only replace the port-22 IP". The code does more: per K5A-136 and K5B-020, `_ufw_script` deletes every 22 rule, adds `deny 22/tcp` and re-adds 80/443. The owner said this breaks the agreed protocol. The chat shows the extra deny blocked SSH (CH0-001, CH0-003).
4. **EasyPost writes.** MFI B-159 says EasyPost is GET-only, and a member report (fulfillment…/1c49312673cb @1785420198) says "only GET /trackers calls were made". K3-145 shows `easypost.py` allows `POST /trackers`. The drill output 8efd5b62b37c reports `http_list_or_create: 200`, so a tracker create may have run.
5. **Injected live facts.** K2A-126 puts live connector facts into briefs as grounding ("GROUND your answer in these"). The CTO review rule (CH0-018) says such injected values are not evidence and must be re-pulled.
6. **Egypt Amazon scheduling.** MFI P-01 records Odin's own schedule (daily 09:00, requireApproval true). In the chats, members built a separate macOS launchd/cron job instead. The owner said twice to remove it. It was deleted, then reinstalled on 2026-07-31 and still crashing (CH0-007, CH0-008).
7. **Company agents.** MFI §0.1 says "Company agents auto-added to every project (EasyPost)". On 2026-07-05 the engine reported "Company-level agents: 0" (chat__b6496b3879e6 @1783280056). This may only reflect timing, but it should be checked.


<!-- ==================== PART CH1 ==================== -->

# CH1 — Chat gap-check, part 01

**Source read in full:** /home/claude/chats_part_01 (4016 lines, about 505 KB). It holds 47 chats: 45 member chats from the Organics project "Real Deployment & Diagnosis" (DevOps, Analytics, CloudDebug, Email, Fulfillment, HubSpot, Project CTO, Reporter) and 2 from "RedBerry Continuous SOC" (CTO Orchestrator).

**Path shorthand:** `ORG/<Member>/<id>` stands for `workspace/chats/scopes/member__real-deployment-and-diagnosis-organics-07d7__<Member>/chats/<id>.json`, and `SOC/<id>` stands for `workspace/chats/scopes/member__redberry-continuous-soc__CTO Orchestrator/chats/<id>.json`.

**Note on roles:** in these chats, role `user` is mostly the system-generated "[Project CTO → X] MANDATE", "[Project CTO review]" or "[Awaiting your approval]" text. The owner's own words appear inside mandate OBJECTIVE lines, for example "Do your part for: i have made many modifications…". Where the owner's words are quoted, the row says so.

## 1. Added from chats (not covered in MFI or K1–K5B)

| ID | Category | Item | Source (chat, ts, role) | Evidence quote (≤20 words) | Status |
|---|---|---|---|---|---|
| CH1-001 | Orchestration core | The DevOps deploy planner takes over non-deploy DevOps mandates (read-only diagnosis, SRE pass, governance/DB-reference task). It returns "could not derive a safe deploy plan", sometimes with "no JSON object in engine reply", and does no work. | ORG/DevOps/470fb76a5596, 1784844837, assistant; also 51fa282a00b1 1784848278, 82aef09f1810 1784845498, 46eeb7a6f94b 1784850671 | "⚠️ I could not derive a safe deploy plan from the brief." | reported broken in chat |
| CH1-002 | Orchestration core | The deploy-once guard ("deploy already ran once… not repeating") fires on steps that are not deploys: SRE diagnosis, the governance/DB-reference task, change-detection, and even non-DevOps helpers (HubSpot). The message replaces the deliverable. | ORG/DevOps/4e5bec487dc7, 1784893668, assistant; ORG/HubSpot/688f611e571c, 1784894627.66, assistant; ORG/DevOps/a2ccee1399cd 1784848291 | "Not repeating it — re-running would reboot/reset the VM again." | reported broken in chat |
| CH1-003 | Orchestration core | Bad upstream hand-off. Planner and deploy-once error text is passed to downstream helpers and the Reporter as "Upstream deliverables… from DevOps". | ORG/Fulfillment/2a43d9cb04d3, 1784850684, user (mandate) | "from DevOps: I could not derive a safe deploy plan from the brief." | reported broken in chat |
| CH1-004 | Owner rule | Owner: when I ask only for diagnosis, no deployment of any kind. Connect through the assigned SSH protocol and read the logs. The planner did recognise this (deploy:false, mode read-only-diagnosis). | ORG/DevOps/9b98f2871544, 1784842099, user (owner text in OBJECTIVE); 470fb76a5596 1784844837 | "I'm not asking about deployment I only ask for the [diagnosis]" | stated requirement |
| CH1-005 | Owner rule | Owner: after I deploy manually, update the deploy-trigger baselines (`deploy_changes.py update`) and nothing else. A later issue or diagnosis request must not trigger a deploy unless files really change again. CTO confirmed DEPLOY_REQUIRED=false afterwards. | ORG/DevOps/5d51c7532aed, 1784937597, user (owner text); CTO confirm 1784937738 | "next time if i asked for issue there is no deploy required unless i really changed files again" | stated requirement + confirmed working in chat |
| CH1-006 | Build, packaging, run & clients | Trigger-script rule (from CTO review): when asked to use the trigger script, list the modified files before running `update`. The update must target exactly the flagged paths. One run updated unrelated entries and was rejected. | ORG/DevOps/9be2c819b763, 1784940176, user (CTO review); ORG/DevOps/685ee950436b 1784974443 | "which should have been shown before running `update`" | stated requirement (CTO) |
| CH1-007 | Build, packaging, run & clients | Change-detection is read-only, so it must run and be reported even when deploying is forbidden this run. If the hook blocks rsync, fall back to `diff -rq`, checksums or a file-list compare. | ORG/DevOps/265f2a0b9b8f, 1785433878, user (CTO review); ORG/DevOps/c8038d310db7 1785414486 | "change-detection is a read-only local diff and should still have been run" | stated requirement (CTO) |
| CH1-008 | Build, packaging, run & clients | Deploy only the target that changed. Example: only the frontend changed, so deploy the frontend only and do not rebuild and rsync both targets. | ORG/DevOps/b34392811ef2, 1784893667, user (CTO review) | "the plan should deploy the frontend target only, not blanket rebuild+rsync both" | stated requirement (CTO) |
| CH1-009 | Build, packaging, run & clients | Re-timestamped init-migration landmine. Local `prisma/migrations/<new>_ini` and the VM's `<old>_ini` contain the same SQL. Syncing or applying the local one would act as a DB rebase, so migrations are excluded under the owner's "no db rebase". | ORG/DevOps/f7928b560cf6, 1784962792, assistant; CTO confirm 1784962824 | "two conflicting `_ini` migrations — pushing/applying it would be exactly a DB rebase" | confirmed working in chat |
| CH1-010 | Audit & consistency | The CTO reviewer re-checks claims itself before confirming: it re-runs provider calls, reads `data/jsons/approvals.json` and history, and diffs deploy lists. Claims without artifacts are rejected. | ORG/DevOps/372ace82f53e, 1785434717, user; ORG/Fulfillment/d836ddef74bc 1784848874, user | "I re-ran the EasyPost lookup live and it matches the report exactly" | confirmed working in chat |
| CH1-011 | Audit & consistency | The CTO reviewer receives member reports truncated mid-sentence. It then flags "Needs fix" or adds a caveat because of the cut, not because of the work. | ORG/Reporter/0c644f9c603d, 1784850336, user; ORG/DevOps/a006f9fe9b67 1785507239; ORG/Analytics/8fe13076055c 1784850209 | "The verdict is truncated mid-sentence at" | reported broken in chat |
| CH1-012 | Audit & consistency | Audit eye and CTO disagree. The audit eye rejects steps ("a step reported FAIL", "fatal/crash") that the CTO then confirms as correct. The rejection is posted after the proposal and approval notice. | ORG/Fulfillment/44b2cf31f83e, 1784894011.72 assistant then 1784894083 user; ORG/DevOps/372ace82f53e 1785434374 | "AUDIT EYE (try 1) rejected this step: hidden errors in your output: ['a step reported FAIL']" | reported broken in chat (false-positive pattern) |
| CH1-013 | Other | Engine and API failures are posted word for word as the "[Project CTO review]" text or as the deliverable / [Done] line. Seen: OAuth 401 expired, weekly limit, FailedToOpenSocket, and "Connection closed mid-response". | ORG/DevOps/8dd0f1ca2e07, 1784841862, user; ORG/DevOps/bf74fa7155fd 1784960141, user; ORG/Reporter/846ea0b76cda 1784895657, assistant | "[Project CTO review] API Error: Unable to connect to API (FailedToOpenSocket)" | reported broken in chat (K2A-170 catches only oauth/weekly-limit, at run end) |
| CH1-014 | Safety & approvals | Approved `where:"vm"` commands that already contain `sshpass … ssh` are run on the VM as well, a double wrap. Result: "sshpass: command not found". | ORG/DevOps/c8038d310db7, 1785414236, assistant; ORG/Fulfillment/4d9829d86e75 1784750173, assistant | "▶ ran on VM (ssh/mostafa): … bash: line 1: sshpass: command not found" | reported broken in chat |
| CH1-015 | Safety & approvals | An approved proposal whose "command" is prose ("existing deploy flow for the 14 changed backend files…") is run literally in bash on the VM, giving a syntax error. | ORG/Project CTO/4542848b1e3c, 1785525261, assistant | "bash: -c: line 1: syntax error near unexpected token `('" | reported broken in chat |
| CH1-016 | Safety & approvals | Read-only hook false positives. It blocks any command containing the string "migrat" (even a `_prisma_migrations` SELECT), rsync `--dry-run`, read-only HubSpot POST /search, and a plain `ls` in another workspace. | ORG/DevOps/a006f9fe9b67, 1785507224, assistant; ORG/DevOps/c8038d310db7 1785414466; ORG/HubSpot/a60d78376a50 1784849662; SOC/efbdaf00db56 1784584436 | "the read-only hook blocks any command containing the string \"migrat\"" | reported broken in chat |
| CH1-017 | Safety & approvals | Per-proposal chat notice "[Awaiting your approval] <Member> proposed N file change(s) + M command(s). Approve (popup or chat)". Applied results then post as "[Done] …" lines in the member chat or an "Applied" chat. | ORG/DevOps/685ee950436b, 1784974411, user; ORG/DevOps/685ee950436b 1784974483 assistant | "DevOps proposed 2 file change(s) + 2 command(s). Approve (popup or chat) to run them." | confirmed working in chat |
| CH1-018 | Per-project features & integrations | Veeqo→EasyPost chain confirmed live. The Veeqo operator pulls the scalars (`tracking_number.tracking_number`, `carrier.name`) and passes them to the EasyPost tracker, which resolves DELIVERED with time, place and scans. The chain works for any carrier. Caveat: it is GET-only, so it only sees trackers that already exist. | ORG/DevOps/55f61b99d233, 1785415484, user (CTO); ORG/DevOps/372ace82f53e 1785434717 | "the Veeqo→EasyPost path is genuinely generic" | confirmed working in chat |
| CH1-019 | Per-project features & integrations | CTO ruling on credential_source. A resolved agent_scope/DB binding is labelled `delta` even when its value is byte-identical to the default key. The identical value is reported as a non-blocking scope-hygiene note, with advice to seed distinct keys. | ORG/Email/6ed781694a34, 1784894627, user; ORG/HubSpot/688f611e571c 1784895011 | "labels any resolved DB binding `credential_source=delta`" | confirmed in chat (later ruling; see Contradictions) |
| CH1-020 | Per-project features & integrations | The delta getters `getHubspotConfig` and `getKlaviyoConfig`, and the Analytics `getGaConfig`, exist only in prose, with no runnable code. The Analytics helper has no GA delta and no default GA key, so it substitutes nginx logs. | ORG/HubSpot/a60d78376a50, 1784849807, user; ORG/Analytics/8fe13076055c 1784850209, user | "`getHubspotConfig` exists only in the index/instruction prose, not as runnable code" | reported broken in chat (gap) |
| CH1-021 | Per-project features & integrations | Look before overwriting. Before rewriting the single hand-off file, the Reporter compares the target's current sha1 and mtime with what the mandate describes. If it is already reconciled, it stops and surfaces that instead of rewriting. | ORG/Reporter/cc1fba21b09f, 1784893705, assistant | "look at the target before overwriting; if it contradicts how it was described, surface it" | confirmed working in chat |
| CH1-022 | Scheduling & notifications | "Run this project's recurring/daily task now" arrives as a direct-mode single-member mandate ("Do EXACTLY… no team"). DevOps then writes the whole "team conversation" (CTO, Fulfillment, Analytics, CloudDebug, Reporter) inside one turn. | ORG/DevOps/c8038d310db7, 1785413217 user + 1785413578 assistant; ORG/DevOps/265f2a0b9b8f 1785433500 | "OBJECTIVE: Do EXACTLY what the owner asked -- nothing else." | observed in chat (conflicts with K2B-154) |
| CH1-023 | Build, packaging, run & clients | The Organics backend path in the mapping and profile, `~/Bendcore`, does not exist on the VM; the running service uses `~/bendcore`. An approved dry-run rsync to `Bendcore/` showed it would create a stray full tree. | ORG/DevOps/f7928b560cf6, 1784962229, assistant | "`~/Bendcore` **does not exist** at that path (`ls`/`git` errored) even though `bendcore.service` runs" | reported broken in chat |

**Rows added: 23**

## 2. Already covered

About 40 candidate items from this part are already in MFI or the K files. Ten examples:

| Chat item | Maps to |
|---|---|
| Mandate format: OBJECTIVE / DELIVERABLE / ACCEPTANCE / upstream deliverables / "own EXACTLY this mandate" | K2A-141, A-091 |
| Direct mode: "Do EXACTLY what the owner asked — nothing else… no team" | K2A-117, K2A-175 |
| "PROJECT CONSTRAINTS (guardrails… NOT tasks)", "Also cover (from YOUR request…)" | K2A-118, K2A-119 |
| CTO review "Confirmed:" / "Needs fix:" after each member | K2A-164, B-178, §0.1 G1 |
| Audit eye "CLAIMED success while errors are present"; `az vm run-command` rejection | K2A-160, A-034, K2A-159 |
| "[Scheduled autonomous run — approval already granted…]" suffix | K2B-154 |
| Proposal JSON (summary/files/commands with where local or vm), propose-first | K2A-064, K2A-066 |
| Readiness check REQUIRES / HAVE / MISSING | K2A-144, B-171 |
| `deploy_changes.py` scan/update, DEPLOY_REQUIRED, DB_SENSITIVE; `deploy_run.sh` chain with strong verify; `ODIN_ALLOW_PROD_DEPLOY` | D-029, B-132, D-028, B-126, B-130 |
| agent_scope delta→default with credential_source; `set_external_report_ref`; EasyPost GET-only; SOC monitor-and-report-only and no-overlap; `infra_rotate` single-IP port 22; re-confirm excludes per run; "still working…" heartbeat | A-085, K1-039, K1 (external_report_ref), B-159, K3-146, A-227, A-08, K5A infra_rotate rows, B-142, K2B-110 |

## 3. Contradictions

1. **credential_source labelling changed between CTO reviews.**
   - Earlier reviews said a delta value byte-identical to the default must be reported as `default`: ORG/Email/7a9a53673bc3 1784849368 and ORG/Fulfillment/2a43d9cb04d3 1784851002. ORG/HubSpot/a60d78376a50 1784849807 also confirmed "no HubSpot delta → default".
   - Later reviews ruled that any resolved DB binding is `delta` with a hygiene note: ORG/Email/6a99f266ab8b 1784851286, ORG/Fulfillment/44b2cf31f83e 1784894083, ORG/HubSpot/688f611e571c 1784895011.
   - A-085 and K1-039 do not settle which rule holds.
2. **Reading the VM `.env`.**
   - CTO 1784849368 (Email) called reading `/home/mostafa/bendcore/.env` for DATABASE_URL a "hard violation" (this matches A-024).
   - Later runs that used the same `.env` path were confirmed without objection (Fulfillment 1784894083; DevOps c8038d310db7 1785414466).
3. **Veeqo carrier fallback.** The MFI open item (line 820, "Veeqo carrier-tracking fallback not built") conflicts with the chats. They show the organics code falling back to EasyPost (`tracking-status.service.ts` → `getEasyPostConfig`, at c8038d310db7 1785414074), and the Veeqo→EasyPost operator chain confirmed live (55f61b99d233 1785415484).
4. **VM backend path.**
   - A-047 maps the backend to `~/Bendcore`.
   - The chat at f7928b560cf6 1784962229 shows `~/Bendcore` does not exist; the real path is `~/bendcore`. B-027 notes the lowercase fix, but A-047 and the DevOps planner still use `Bendcore`.
5. **Read-only hook.**
   - K1-086 says rsync is blocked only *without* dry-run.
   - In the chats, an rsync `--dry-run` was blocked (c8038d310db7 1785414466), and any command containing "migrat" was blocked (a006f9fe9b67 1785507224).
6. **CFG_BACKEND_MIG.**
   - MFI line 809 says "reset" is still set and left untouched by design.
   - In chat it was reverted to "new" through an approved proposal, and the deploy then passed (d0127007bda4 / f7928b560cf6 1784962407). This matches K5B-042.
7. **Recurring-run routing.**
   - K2B-154 says a scheduled project-level run with no assignee becomes a team run (`orchestrate_blocking`).
   - In the chats, "Run this project's recurring task" turns arrive as direct-mode single-member DevOps mandates ("no team"), and that member writes the whole team conversation (CH1-022).


<!-- ==================== PART CH2 ==================== -->

# CH2 — Chat gap-check, part 02

Source read in full: /home/claude/chats_part_02 (3,646 lines). The chats covered are the RedBerry SOC lanes, Revealer (DevOps, Email, Fulfillment, Fullstack, QA), vm-sentinel, daily-egypt-amazon-product-poster, email-klaviyo-workflows, fulfillment-vq-status, full-services-19jul, hubspot-crm-operator, odin-external-arms and real-deployment-and-diagnosis-organics.
Paths below are shortened. `.../<scope>/<id>` means `workspace/chats/scopes/<scope>/chats/<id>.json`. Timestamps are the epoch seconds from the transcript.
No secret values are copied.

## 1. Added from chats (not in MFI or K1–K5B)

| ID | Category | Item | Source | Evidence quote | Status |
|---|---|---|---|---|---|
| CH2-001 | Orchestration core | Background-run acknowledgement in chat. When a main-chat owner message becomes a team run, Odin replies that it runs in the background, that the owner can switch freely between the CTO and members, that live commands show in the member's chat, and that a notification arrives when it finishes. | .../project__real-deployment-and-diagnosis-organics-07d7/d748d0460f0b 1784841815 assistant | "the team is now running this in the background. You can switch between the CTO and any member" | confirmed working in chat |
| CH2-002 | Safety & approvals | Pending-approval chat notice. After a member's proposal block, a user-role system line is posted: "[Awaiting your approval] <member> proposed N file change(s) + M command(s). Approve (popup or chat)". | .../member__redberry-continuous-soc__.../ef01bef626fe 1784584699 user(system); also 9789c0e39591 1784733523 | "proposed 2 file change(s) + 0 command(s). Approve (popup or chat) to run them." | confirmed working in chat |
| CH2-003 | Safety & approvals | Apply feedback messages. A chat "approved" gets "✅ Approved — running N change(s) now; results appear in the member chats". Each applied item posts "[Done] Applied." in the member chat. | .../d748d0460f0b 1784850445 assistant; SOC chat lines 58–108 | "✅ Approved — running 1 change(s) now; results appear in the member chats." | confirmed working in chat |
| CH2-004 | Orchestration core | The plan footer "(DevOps-only run — no QA, as you instructed.)" is added to every CTO plan, even when the owner gave no such instruction and QA or Reviewer steps are in the plan. | .../project__daily-egypt-amazon-product-poster/12926fbfbb6b 1784890263 assistant; .../project__full-services-19jul/255512bf2514 1784478076 | "10) QA → Final verification… Briefing the team now. (DevOps-only run — no QA, as you instructed.)" | reported broken in chat |
| CH2-005 | Orchestration core | The coverage or gap check turns the project description back into tasks on narrow requests. Examples: "confirm the AI report was updated" was re-planned into a full Capability-1 deploy plus every helper; a diagnosis-only request got deploy steps. | .../d748d0460f0b 1784850574, 1784848133, 1784893474 assistant | "Plan gap — not covered: CAPABILITY 1 DEPLOY: refresh the dynamic-IP firewall rule first…" | reported broken in chat |
| CH2-006 | Orchestration core | Cross-project leak in "Gap vs YOUR request". The Fulfillment-VQ project's daily-run re-plan demanded another project's recurring task (the Amazon product-poster run). | .../project__fulfillment-vq-status-read-only-dc1e/97a2be00d782 1785533265 assistant | "Actually execute the project's daily scheduled task itself (the recurring Amazon product-poster run)" | reported broken in chat |
| CH2-007 | Scheduling & notifications | Scheduled and manual "Run this project's recurring/daily task now" turns are caught by the gate classifier and never run. They are answered "That's a Backend task… needs your approval first ()" (empty category). The local content project was classed as "DevOps & Cloud (deployment, azure-vm-action)". | .../project__email-klaviyo-workflows-read-only-18ca/69bb02b755d9 1784479048; .../daily-egypt.../07bff04f2a53 1784467363; odin-external-arms ×4 | "That's a Backend task and it needs your approval first (). I'll prepare an approval request" | reported broken in chat |
| CH2-008 | Build, packaging, run & clients | DevOps member steps are always sent to the deploy-decision engine, even for read-only diagnosis or "confirm the report" tasks. They fail with "could not derive a safe deploy plan" (flagged) instead of doing the diagnosis. | .../d748d0460f0b 1784841862, 1784844850, 1784848291, 1784850684 assistant | "I could not derive a safe deploy plan from the brief." | reported broken in chat |
| CH2-009 | Build, packaging, run & clients | The deploy-once marker covers non-deploy steps and makes a false claim. HubSpot and DevOps-diagnosis steps were answered "deploy already ran once… synced, built, rebooted and verified", but no deploy ran in that run. | .../d748d0460f0b 1784848291, 1784849408, 1784851286 assistant | "[HubSpot] ✅ The deploy already ran once in this run (it synced, built, rebooted…" | reported broken in chat |
| CH2-010 | Audit & consistency | An engine weekly-limit message was accepted as a member deliverable labelled "✅ passed (QA + audit clean)". | .../fulfillment-vq-status-read-only-dc1e/d6b99adb9d1e 1782905605 assistant | "✅ passed (QA + audit clean). You've hit your weekly limit" | reported broken in chat |
| CH2-011 | Orchestration core | Duplicated Chief prefix: "[Chief Engineer → Project CTO] For X: [Chief Engineer → Project CTO] For X: … report back.. Plan it…" (a nested re-wrap). | .../d748d0460f0b 1784845316 user(system) | "For 'Real Deployment & Diagnosis — Organics': [Chief Engineer → Project CTO] For 'Real…" | reported broken in chat |
| CH2-012 | Audit & consistency | CTO review sees member reports truncated (cut mid-table or mid-JSON) and returns "Needs fix". The owner had to issue "compact, under ~25 lines" drills to get a confirmation. | .../revealer-6978__Fullstack/ab7c8b892146 1782882184; .../fulfillment-vq.../cd332fe9a59c 1785433582 user | "flagged 'Needs fix / truncated mid-JSON' because the report pasted the entire multi-KB tracker JSON" | reported broken in chat |
| CH2-013 | Owner rule | No drift into unrelated agents or topics. In the content project the owner rejected Fulfillment and shipping-status work: "do not drift… that is violation". | .../daily-egypt.../e4645036a83a 1783577065, 1783577129 user | "stop this kidding no need for fullfilment… remove fullfilment do not drift" | stated requirement |
| CH2-014 | Owner rule | A diagnosis request must not plan or perform a deploy. The owner says to use the assigned SSH and log protocol only. | .../d748d0460f0b 1784842069 user | "there is no need to make any deployment I'm not asking about deployment I only ask for the [diagnosis]" | stated requirement |
| CH2-015 | Owner rule | Disclosure wording for the Egypt Amazon posts. The owner approved replacing the consent/affiliate claim with "Sourced from public amazon.eg listings. Not affiliated with or endorsed by Amazon. Prices subject to change." This was applied to 5 templates and posters. | .../daily-egypt.../e4645036a83a 1783577129 assistant (applied, approved edits) | "replaced the 'shared with consent and may contain affiliate links' line with: Sourced from public amazon.eg listings" | confirmed working in chat |
| CH2-016 | Per-project features & integrations | The Egypt Amazon daily pipeline exists and runs outside the workspace, in Odin Testing/testing/daily-egypt-amazon-product-poster. It has research.py, poster.py (1080×1080 FB and 1080×1350 IG PNGs), posts.py, approval.py, meta_publish.py, run_daily.py, work/status.json and preview.html. A local launchd job fired at 08:50 and held 2 posts pending approval. | .../daily-egypt.../a4646ebc6df0 1783600315 assistant; e4645036a83a 1783577129 | "the local launchd job ran at 08:50 — work/status.json confirms… 2 posts, pending approval" | confirmed working in chat |
| CH2-017 | Per-project features & integrations | research.py zips independent title, price and link lists, so links shift onto the wrong product. It also scrapes one bestseller sub-category (garden), which gives duplicate products. | .../daily-egypt.../a4646ebc6df0 1783600315 assistant | "builds titles, prices, and links as independent lists and zips them by index" | reported broken in chat |
| CH2-018 | Per-project features & integrations | The posts.py consent guard (`if "consent" not in caption`) now always appends CONSENT_LINE after the disclosure change, which duplicates the disclosure. The posts in work/posts.json were not regenerated after the template edits. | .../daily-egypt.../e4645036a83a 1783577129, 1783577240 assistant | "this guard now always evaluates true and appends CONSENT_LINE… producing a duplicate disclosure" | reported broken in chat |
| CH2-019 | Per-project features & integrations | SOC investigation run charter. The CTO lane wrote run-<ts>-charter.md plus ACTIVE-RUN.lock (a no-overlap lock released at the last lane). Mode was MONITOR-AND-REPORT-ONLY, enforced by the read-only hook. There were 13 ordered lanes and an incident-ID reconciliation (SOC-APP-001 = INC-2026-001 = PB-APP-001). These were applied through approval. | .../member__redberry-continuous-soc__CTO.../ (lines 1–108) 1784584436, 1785583766 assistant | "ACTIVE-RUN.lock held by run-1784584358 — prevents a second overlapping investigation" | confirmed working in chat |
| CH2-020 | Safety & approvals | Old approvals stay pending and can be applied days later. The 2026-07-21 SOC proposals were applied on 2026-08-01, after the target soc/ tree had vanished. Apply created the missing parent directories without re-checking the context. | SOC CTO chat 1785583730–1785583766; Threat-Hunting chat 1785673485 assistant | "the soc/history/investigations/ path did not exist, so I created the parent directories" | confirmed working in chat (risk) |
| CH2-021 | Per-project features & integrations | Veeqo→EasyPost delivered-status loop. The Veeqo order status tops out at "shipped" (the ceiling). The scalars tracking_number.tracking_number and carrier.name are fed to EasyPost Trackers, which resolves delivered, status_detail and the newest tracking_detail. The flow is generic for any carrier or order. | .../fulfillment-vq.../3d8c4d8a3f68 1785419595 user; .../real-deployment.../01dc78d976e4 1785434717 assistant | "this Veeqo->EasyPost flow is GENERIC — works for ANY carrier (USPS/FedEx/DHL/UPS) and ANY order" | confirmed working in chat |
| CH2-022 | Per-project features & integrations | Veeqo `orders_summary()` reads only one page (≤100 orders), so monthly counts are undercounted. A paginated GET was needed and it returned 86 orders this month. | .../fulfillment-vq.../e81670c63165 1784499060, 1784583899 assistant | "The built-in orders_summary() only reads one page (≤100), which would undercount a full month." | reported broken in chat |
| CH2-023 | Safety & approvals | The read-only PreToolUse hook blocks harmless reads that contain `>` (for example `2>/dev/null`) and `rsync --dry-run`. Agents had to drop redirects, and change-detection was skipped in one daily run. | .../real-deployment.../451e738d6310 1784737115; d5e86dd00341 1785414486 assistant | "The 2>/dev/null redirect (contains >) is what the hook blocks." / "rsync dry-run was blocked by the read-only hook" | reported broken in chat |

## 2. Already covered

About 60 distinct chat features were already in MFI or K1–K5B. Ten examples:

1. Read-only PreToolUse hook ("READ-ONLY MODE — this command changes state") maps to K1-086 and A-020.
2. Propose-first fenced `proposal` JSON {summary, files, commands[where local/vm]} maps to K2A-064.
3. Audit Eye rejection of `az vm run-command` and "claimed success while errors present" maps to K2A (AUDIT EYE rows) and A-032.
4. "⛔ RESOURCE/QUOTA limit hit — pausing the run, not retried" maps to K2A-163.
5. "Scoped request — X handles it directly; no team expansion" plus the auto "Constraint: do NOT deploy… local edits allowed" maps to K2A-117.
6. "Requirements checklist: N item(s) tracked" and "⚠️ Incomplete — N requirement(s) NOT addressed" map to K2A-169.
7. "[Scheduled autonomous run — approval already granted…]" maps to K2B and K2A-180.
8. Change-detection, the re-baseline gate, "press play" and the [system] diagnosis prompt map to K2A-149, K2A-150, K2A-026, K2A-107 and K2A-101.
9. Delta-first `credential_source` and AI_DIAGNOSIS_REPORT.md single-file hand-off map to A-085, K1-039 and A-087.
10. "No current agent's rules fully cover this…" capability-gap dialog maps to K4A-134. The engine-offline structural meeting report maps to K2B-231.

## 3. Contradictions and status conflicts (chat versus MFI/K)

1. **Audit Eye versus CTO review versus A-032.** Audit Eye rejected QA and Fulfillment three times for using `az vm run-command` (a 52.x Revealer QA chat at 1782884400). The CTO review then "Confirmed: Azure control-plane execution is correct" (1782884412). This conflicts with A-032, which allows the control plane for the firewall only.
2. **K2A-118 ("brief as constraints, NOT tasks") is contradicted by the coverage gate.** The gate re-adds the description's Capability-1 deploy and helpers as tasks (CH2-005).
3. **K2A-170 (engine auth-failure guard) is inconsistent.** At 1784842113 the run ended "All requirements addressed ✅" with a 401 OAuth-expired member. At 1784851896 it correctly ended "Incomplete — engine could not authenticate".
4. **K2A-184 (deterministic status answer) misfired.** The owner's 87-character complaint about shipping status got "📋 Deploy status — straight from Odin's records" (daily-egypt/e4645036a83a 1783577129).
5. **A-095 (scope answer guard) failed.** In the Klaviyo project, "how many profiles" was answered with the Odin app's EnvProfiles (3; config.dart). It should have been Klaviyo profiles (69bb02b755d9 1784500173). Later turns answered correctly with a live read (16 new this month; 17 total).
6. **A-096 (read-execute guard, "never proposal for reads") was inconsistent.** Order and profile counts were first sent as approval proposals (1784499060, 1784502436) and later auto-executed (1784583899, 1784582795).
7. **K2A-147 (deploy once per run)** is shown applying to non-deploy members and claiming a reboot that did not happen (CH2-009).
8. **P-01 and the "NOT FOUND (only .gitkeep)" code note for daily-egypt-amazon-product-poster.** A working pipeline exists in the owner's Odin Testing/testing folder (CH2-016). The local launchd fired at 08:50, while the project schedule says daily 09:00.
9. **P-03 says "members lack EasyPost".** The fulfillment-vq chats show an EasyPost member running as step 2/2 (97a2be00d782 1785533736). The agent exists in practice, so this confirms the members-list drift.
10. **K5A-038 posts "8 SOC lanes".** The RedBerry Continuous SOC chat runs a 13-lane CTO plan (CH2-019).
11. **Truth gate G1 (PARTIAL) confirmed again.** Many runs end "All requirements addressed ✅" or "RUN FINISHED" while member reviews say "Needs fix" (for example 97a2be00d782 1785533736, 01dc78d976e4).
12. **K2A-087 (single-run concurrency guard) gap.** Six identical owner messages within about 12 minutes (d748d0460f0b 1784843427–1784844134) each got a new "running in the background" acknowledgement. The guard's "A team run is already in progress" reply only appears in later chats.


<!-- ==================== PART CH3 ==================== -->

# CH3 — Chat gap-check, part 03

Input: /home/claude/chats_part_03 (6,136 lines, read in full). It holds 31 chats: 2 from `project__real-deployment-and-diagnosis-organics-07d7` (the deploy/diagnosis owner chat and one diagnosis chat) and 29 from `project__redberry-continuous-soc` (periodic and manual SOC runs). Most SOC runs repeat the same template, so the SOC chats were also deduplicated line by line (547 distinct normalized lines), and every distinct line was reviewed. The file has 23 owner (`user`) messages, 3 of them `[system]` gate continuations.

Path abbreviations used below:
- RDD = `workspace/chats/scopes/project__real-deployment-and-diagnosis-organics-07d7/chats/`
- SOC = `workspace/chats/scopes/project__redberry-continuous-soc/chats/`

Timestamps are the epoch values from the chat lines.

## 1. Added from chats (not covered by MFI.md or K*.md)

| ID | Category | Item | Source | Evidence quote | Status |
|---|---|---|---|---|---|
| CH3-001 | Owner rule | After the owner deploys by hand, only re-baseline the deploy trigger lists (`deploy-lists/{backend,frontend}.json`); do not deploy. A later issue query must then say no deploy is required unless files really changed. | RDD/(first chat in part) 1784937209.156627 user; repeated 1784939895, 1784974290 | "update the trigger script for deploy lists to avoid unrequired deploymet next time just update nothing else" | stated requirement |
| CH3-002 | Build, packaging, run & clients | Confirmed re-baseline result: the live scan after the list refresh gave backend 875 files 0/0/0 and frontend 668 files 0/0/0, with `DEPLOY_REQUIRED: NO` and `DB_SENSITIVE: NO`. Only the two list files changed. | RDD 1784974510.393853 assistant (after owner "confirm that is done") | "Live change-detection against those baselines … DEPLOY_REQUIRED: NO (and DB_SENSITIVE: NO)" | confirmed working in chat |
| CH3-003 | Build, packaging, run & clients | Re-baselining without a verified deploy leaves a stale baseline. The detector then reports modified:0 and skips a real change (auth.service.ts). The workaround is `deploy_run.sh --bootstrap`, which seeds the lists to an old date so the real diff is detected. | RDD 1784962643.039741 assistant | "the 'no deploy needed' is a false negative … pipeline skipped because of a stale baseline" | reported broken in chat |
| CH3-004 | Orchestration core | A "Plan gap — not covered" check runs against the project brief's CAPABILITY list (deploy flow, read-only helpers, delta scope, single-file hand-off, governance). The plan is then re-issued with "MUST also cover (do not omit)". This is the brief-capability variant of the coverage re-plan; K2A-119 only covers gaps in the owner's request. | RDD 1784937486.800687 / 1784937583.789574 assistant | "[Project CTO] Plan gap — not covered: CAPABILITY 1 deploy flow steps … Re-planning to include them." | confirmed working in chat |
| CH3-005 | Build, packaging, run & clients | The DevOps step expects a JSON deploy plan from the engine. A free-text reply is flagged with "could not derive a safe deploy plan". This happened even when the reply said the requested list update was done. | RDD 1784937738.3787909 and 1784940176.325253 assistant | "I could not derive a safe deploy plan from the brief. [why: no JSON object in engine reply" | reported broken in chat |
| CH3-006 | Audit & consistency | The engine auth-failure guard (K2A-170) misfires. A step whose reviewer confirmed real work ("lists were correctly updated") was still declared unauthenticated with no real work produced. A weekly-limit message from a different reviewer also marked the whole run as not done. | RDD 1784940176.342227 assistant; also lines 9–10 (Reporter/DevOps weekly limit) | "a member's Claude engine could not authenticate … No real work was produced, so the run is NOT done" | reported broken in chat |
| CH3-007 | Orchestration core | The intent gate misread an explicit deploy request. The owner asked to "deploy as the instructions you have" and the plan still added "do NOT deploy, rsync, build on the VM…". The checklist then flagged deploy items as not addressed. | RDD 1784963035.082189 assistant (owner msg 1784963025.955503) | "no db rebase … then deploy as the instructiond ypu have" → "Constraint: do NOT deploy, rsync, build on the VM" | reported broken in chat |
| CH3-008 | Safety & approvals | The read-only harness blocks VM reads too: `az vm run-command`, some sshpass reads and the deployed-commit check are gated. Diagnosis answers therefore carry a caveat that the VM state is unverified, and they say this is "the harness, not a connectivity block". | RDD 1784960974.306763 and 1784962643 assistant; RDD/d7a8eed981dd.json 1784736952.065141 (hook errors on sshpass) | "this session's read-only harness blocks the VM read … it's the harness, not a connectivity block" | reported broken in chat |
| CH3-009 | Per-project features & integrations | Veeqo diagnosis of "admin shows Shipped, Veeqo shows Out for Delivery". Veeqo's order-status enum stops at `shipped`. "Other"/manual-carrier shipments have null tracking fields, so the resolver cannot advance to OUT_FOR_DELIVERY/DELIVERED. Three advisory fixes were given (none executed). | RDD 1784974881.874133 user → 1784975041.735926 assistant | "this is a data-source gap, not a code bug, and it's confirmed with live Veeqo reads" | confirmed working in chat |
| CH3-010 | Build, packaging, run & clients | The chat shows a "🔧 What I actually did:" tool-trace digest: one line per tool (🔎 search, 📖 read, ⚙️ command), with ↳ ✅/❌ result previews and heartbeat lines in between. | RDD/d7a8eed981dd.json 1784736952.065141 assistant | "🔧 What I actually did: • 🔎 getVeeqoConfig|RUNTIME_OPERATIONAL_SETTINGS … ↳ ✅ Found 4 files" | confirmed working in chat |
| CH3-011 | Per-project features & integrations | Every SOC finding carries a three-state data-source label: "Checked and healthy", "Checked and finding detected" or "Data unavailable". The rule is that missing data never counts as healthy (the finding becomes Needs Review). | SOC/108d6a980e74.json 1786877003+ assistant (and about 31 other occurrences) | "False-positive analysis: cannot conclude healthy from missing data" | confirmed working in chat |
| CH3-012 | Per-project features & integrations | SOC-HOST-002 was escalated to critical/high Suspicious ("Critical attention") on foreign egress alone. There were no miner keywords and no unknown high-CPU process, so this is a likely false positive. | SOC/108d6a980e74.json 1786877060.666126 assistant | "miner keywords=[]; unknown high-CPU=[]; foreign egress=[…]" → "critical/high" | reported broken in chat |
| CH3-013 | Per-project features & integrations | The SOC's own SSH probe was refused for too many authentication failures (and in another run got Permission denied on sudo). Most host checks then showed Data unavailable. P-30 records only timeouts. | SOC/108d6a980e74.json run (chat line 2157) assistant | "Received disconnect … port 22:2: Too many authentication failures" | reported broken in chat |
| CH3-014 | Per-project features & integrations | The SOC behaviour remediation recommends a UFW block only for IPs at or above a score threshold. It keeps the owner allow-list current through the dynamic-IP refresh protocol, and the owner runs or approves the block, which is never auto-applied. Other remediations offer monitor/skip/enforce modes with shared-IP false-positive protection. | SOC 0ab5d00da95f / 0d47442b4c1c runs (2026-07-15) assistant | "block confirmed-bad IPs at UFW/edge (score≥… only) … (owner runs / approves; never auto-applied)" | confirmed working in chat |

## 2. Already covered

About 42 distinct candidates from this part are already covered. Ten examples:

1. The SOC run engine (Observe→Correlate→Verify→Report→Approve, with mode, monitor_only and test flags) maps to K5A-001 and A-227.
2. SOC approvals DENIED in monitor/test mode, plus "No agent may approve its own action", map to K5A-051.
3. The SOC issue tracker across runs (new / open / pending / accepted / auto-resolved) maps to A-228 and K5A-010.
4. The 24/7 sensor, not installed and with an approval-gated INSTALL_SOC_SENSOR.md, maps to A-232 and K5A-030.
5. The CTO scope recommendation to enroll Revealer and the Egypt content agent, plus Cloudflare, maps to A-233.
6. Smart date-aware recovery (newest clean pre-problem point, no post-problem restore) maps to K5A-118.
7. The mining and abuse root-cause chains (ATT&CK) map to K5A-042 and K5A-043.
8. The `[system]` gate-approved auto-continue (DB gate / post-deploy test / full diagnosis with EasyPost compare) maps to K2A-082.
9. The direct-mode scoped request (DevOps only, no team expansion, forbid-deploy with local edits allowed) maps to K2A-117. The DevOps-only rule maps to B-125.
10. Delta-first credentials reporting `credential_source` map to A-085 and K1-039. The DB-sensitive rebase gate ("no db rebase") maps to B-132 and D-028.

Also covered: the requirements checklist (K2A-128); "approved" approving everything (K2A-183); the "still working…" heartbeat (K2B-110); the re-baseline (synclist) gate (K2A-104 and K2A-107); the md5/checksum content verify (B-176); post-deploy health polling and rollback (A-053); the dynamic-IP and systemd-not-pm2 procedure (A-046); the quota GENERIC template (K5A-109); clickjacking (K5A-034); the ▶ Running start line (K2B-153); the weekly-limit / quota stop (K2A-163); the reboot commit point / no re-deploy within a run (K2B-199 and A-055); and the AI_DIAGNOSIS_REPORT single external file (in MFI).

## 3. Contradictions

1. **K2A-185 says the background-run message is dead code.** In these chats, every owner request in the RDD project chat (2026-07-25) gets "On it — the team is now running this in the background. You can switch between the CTO and any member…". Either the code changed after these chats, or the path is still live.
2. **The SOC team size differs between sources.** Every SOC chat lists 8 agents (CTO Orchestrator plus 7 specialists, "each agent has ONE clear lane"). K-inventory notes refer to an "11-agent SOC team", and P-08 lists 13 names including aliases.
3. **K2A-170 assumes the auth-failure guard fires only when no real work was produced.** In the chat it fired on runs where the reviewer confirmed the work was done (CH3-006).
4. **The owner rule "update only the lists, then next time no deploy unless files really changed" (CH3-001) conflicts with "baseline update gated on verification" (B-045 and the PHASE7 deploy protocol).** The owner explicitly asked to re-baseline without any deploy, and that caused the stale-baseline false negative (CH3-003).


<!-- ==================== PART CH4 ==================== -->

# CH4 — Chat gap-check, part 04

Source: `/home/claude/chats_part_04` (25 chats, all in scope `project__redberry-continuous-soc`, 6,297 lines). The part was read completely, and its 812 unique lines were reviewed after repeated SOC-run boilerplate was removed.
Chat path prefix below: `workspace/chats/scopes/project__redberry-continuous-soc/chats/` (P/).
Almost all content is auto-generated SOC run output. There are only 4 real owner messages, all in P/a40902636ace.json, and 6 "[system] gate APPROVED" continuation messages in P/a0992a060de4.json.

## 1. Added from chats (not covered in MFI / K*)

| ID | Category | Item | Source | Evidence quote | Status |
|---|---|---|---|---|---|
| CH4-001 | Owner rule | The SOC health verdict must account for the owner's reported fake-user/app-abuse problem. The system must not declare "good health" while that concern is open. | P/a40902636ace.json 1784584042.30 user | "We still have a problem that there are some fake users make app abuse. So can you actually report…good health?" | stated requirement |
| CH4-002 | Owner rule | Owner decision: the fake users are in the Klaviyo account, not in the app DB. The 8 DB users are legitimate, so the fix must target Klaviyo itself. | P/a40902636ace.json 1784584532.20 user | "I see this in the Clavu account not in my our database… I need to solve this problem in Clavu" | stated requirement |
| CH4-003 | Per-project features & integrations | SOC subscriber forensics (SOC-APP-004/DB-002) covers only the app PostgreSQL DB. It cannot read HubSpot/Klaviyo contact lists, so marketing-list bot signups are invisible to it. | P/a40902636ace.json 1784584264.49 assistant | "those services aren't currently exposed as readable endpoints in this session" | reported broken in chat |
| CH4-004 | Orchestration core | The owner had to ask again before getting the CTO's answer. The answer arrived about 220 s after the question and only after the owner prompted. | P/a40902636ace.json 1784584164.34 user | "where is the answer for the previous question" | reported broken in chat |
| CH4-005 | Audit & consistency | Project CTO reported "All requirements addressed ✅" while its own lane review said the run was not registered ("Needs fix"). The completion claim contradicts the evidence. | P/a40902636ace.json 1784584699.79 assistant | "All requirements addressed ✅ • CTO Orchestrator: Needs fix: …the run is not actually registered" | reported broken in chat |
| CH4-006 | Orchestration core | The plan-gap check flagged that general threat hunting was missing. The re-plan then explicitly forbade broad hunting, so the gap was never closed. | P/a40902636ace.json 1784584173.63 / 1784584257.26 assistant | "explicitly forbid broad/general threat hunting for other or unknown threats" | reported broken in chat |
| CH4-007 | Orchestration core | After the owner's Klaviyo clarification, the reply was a "Lane 1 Complete" SOC deliverable marked "passed (QA + audit clean)". It did not address Klaviyo, and the same run was declared "DevOps-only — no QA". | P/a40902636ace.json 1784584533.99 assistant | "✅ passed (QA + audit clean)… Lane 1 Complete — RedBerry Continuous" | reported broken in chat |
| CH4-008 | Per-project features & integrations | SOC-APP-001 newsletter-abuse check: the evidence captured is a sudo password prompt, not log data. It is still classified Benign/Expected "Checked and healthy" (12 occurrences). | P/(first chat in part) ~1784479520 and others, assistant | "Evidence: [sudo] password for mostafa:" | reported broken in chat |
| CH4-009 | Audit & consistency | A quick-mode run (4 checks) auto-resolved 9 findings it never checked (CLOUD-004, DEP-002, AUTH-002, HOST-003, SENSOR-008…) and reported "Healthy". Those findings came back in later full runs. | P/638bb24d772c.json 1784751465.79 assistant | "Resolved (9): SOC-DEP-002 … auto (no longer detected) … Security status: Healthy" | reported broken in chat |
| CH4-010 | Per-project features & integrations | The OSV dependency scan returned 0 packages and was classified "Checked and healthy" instead of "Data unavailable". | P/8fafca9c4d7e.json ~1789546787 assistant | "OSV.dev: scanned 0 pkgs; 0 vulnerable … Benign/Expected" | reported broken in chat |
| CH4-011 | Per-project features & integrations | The crypto-miner hunt flagged its own `ps` probe as an unknown high-CPU process. | P/921f1f2aa01d.json 1784113810 assistant | "unknown high-CPU=['ps@100%']" | reported broken in chat |
| CH4-012 | Per-project features & integrations | The crypto-miner check raised a critical "Suspicious" finding on foreign egress alone, with no miner keywords and no high-CPU process. Status escalated to "Critical attention". | P/77b4e9681a75.json 1784471085 assistant | "miner keywords=[]; unknown high-CPU=[]; foreign egress=[…]" → critical/high | reported broken in chat |
| CH4-013 | Per-project features & integrations | The read-only DB anomaly check failed: the Prisma `node -e` eval error was dumped as evidence. | P/921f1f2aa01d.json 1784113810 assistant | "DB read-only query unavailable: [eval]:1 const{PrismaClient}=require('@prisma/client')" | reported broken in chat |
| CH4-014 | Per-project features & integrations | The 24/7 sensor ingest could not parse events.jsonl, which gave a SOC-SENSOR-008 Needs Review / Data unavailable result. | P/6fc025f21a3e.json ~1784542445 assistant | "Evidence: sensor log unparseable" | reported broken in chat |
| CH4-015 | Per-project features & integrations | The multi-cloud surface check (CLOUD-004) repeats the same host's finding 3 times in every run, because inventory URLs are not deduplicated. | P/(first chat), P/7de317f6a6b9.json and others, assistant | "anchor…: missing headers ['strict-transport-security']" ×3 | reported broken in chat |
| CH4-016 | Per-project features & integrations | Recovery posture is inconsistent between runs: the 07-22 quick run reported "backups retained: 0; ready: False" while full runs before and after reported 8–16 fresh backups. | P/638bb24d772c.json 1784751510.43 assistant | "backups retained: 0; ready: False. No fresh encrypted backup" | reported broken in chat |
| CH4-017 | Safety & approvals | Gate-approval auto-continue messages (deploy/diagnosis flow: Klaviyo, Veeqo, EasyPost, HubSpot) were posted into the SOC periodic chat. Six approvals landed within about 48 s, and "running 4 change(s)" appeared twice. | P/a0992a060de4.json 1785583719.71–1785583767.27 user/assistant | "✅ Approved — running 4 change(s) now; results appear in the member chats." | reported broken in chat |
| CH4-018 | Safety & approvals | The approve message wording is "✅ Approved — running N change(s) now; results appear in the member chats", with N counting down per remaining approval. | P/a0992a060de4.json 1785583719.76 assistant | "Approved — running 5 change(s) now; results appear in the member chats" | confirmed working in chat |
| CH4-019 | Safety & approvals | The auto-continue prompt includes a rule that a turn which only announces counts as a failure: the reads must run and real numbers must be posted in the same turn. | P/a0992a060de4.json 1785583719.71 user([system]) | "a turn that only announces is a FAILURE. Run every read to completion" | stated requirement |
| CH4-020 | Orchestration core | Background-run acknowledgement: the owner can switch between the CTO and any member while the run continues. Live commands appear in DevOps's chat, followed by a completion notification. | P/a40902636ace.json 1784584042.34 assistant | "You can switch between the CTO and any member (DevOps) freely; it keeps running" | confirmed working in chat |
| CH4-021 | Audit & consistency | Rule: missing or unavailable data is never "clean". A run where SSH timed out cannot support a healthy claim, and a sensor that is not installed is not "healthy". | P/a40902636ace.json 1784584264.49; P/7c9b3b6a9182.json, assistant | "'Data unavailable' — which is not the same as clean" | confirmed working in chat |

## 2. Already covered

About 45 distinct features or rules stated or confirmed in this part were already in MFI/K. Examples:

- SOC monitor-and-report flow, auto-remediation off, approvals auto-DENIED in monitor/test mode → MFI A-227, K5A-051
- Issue tracker across runs (new/open/pending/accepted/resolved, auto-resolve) → MFI A-228, K5A-010
- 17-check catalogue incl. clickjacking SOC-WEB-005 → MFI A-229, K5A-034
- ATT&CK 7-hypothesis threat hunt + predict & prevent → MFI A-230
- Encrypted backups, key on local desktop, smart date-aware recovery, sha256, restore approval-gated → MFI A-231, K5A-118
- 24/7 sensor (soc-sensor.timer, events.jsonl, install approval-gated) → MFI A-232, B-154
- Scope recommendations + provider models (AWS/GoDaddy/Hostinger/Cloudflare) → MFI A-233, K5A-050/106
- Quick / single-check / full funnel run modes and the NIST/PICERL white-scope note → K5A-036, K5A-041
- UEBA scoring, owner dynamic-IP exclusion, UFW block only at score ≥0.7 and never applied → K5A-080, K5A-084, MFI A-18
- Styled reports PDF/DOCX/MD/PPTX via GET /soc/report → MFI C-033, K5A-056
- (also) Chief Engineer → Project CTO brief K2A-116, requirements checklist K2A-128, propose-first K2A-064, auto-continue after gate K2A-082, background team run K2A-038, extra SOC agents MFI A-05/09/17/32, periodic daily 23:00 P-08

## 3. Contradictions

- **SOC-APP-001 "healthy" claim:** MFI A-229/K5A-020 describe a live nginx-log abuse check. The chats show it returning a sudo prompt every run while still reporting "Checked and healthy" (CH4-008). This contradicts the MFI rule that every claim must be backed by evidence and the "Data unavailable ≠ healthy" rule.
- **Requirements done-gate:** K2A-128 says nothing is "done" until every item is addressed. In the chat the CTO declared "All requirements addressed ✅" with an open "Needs fix" (CH4-005).
- **Plan-gap re-plan:** MFI/K2A treat plan-gap re-planning as closing the gaps. The re-plan here kept the exact gap it had flagged (CH4-006).
- **Auto-resolve:** MFI A-228/K5A-010 say findings auto-resolve when no longer detected. In practice a quick run resolved findings it never checked (CH4-009), so "resolved" is not trustworthy unless the same check actually ran.
- **QA:** the run was declared "DevOps-only — no QA, as you instructed", yet its deliverable was stamped "passed (QA + audit clean)" (CH4-007).
- **Fake-user location:** the owner moved the fake-user problem from the VM/app DB to Klaviyo (CH4-002). The SOC framing in MFI A-229 (abuse = app DB/nginx) does not cover a vendor-side problem, and SOC-EXT-006 tracks only quota drain, not fake contacts.
- **Gate approvals:** approvals for a deploy/diagnosis flow landed in the SOC periodic chat (CH4-017). This conflicts with SOC being monitor-only with `requireApproval: false`, and with per-project scope isolation.


<!-- ==================== PART CH5 ==================== -->

# CH5: chat gap-check for part 05

**Scope:** I read all of `/home/claude/chats_part_05` (6,990 lines).

**Projects it covers:**
- redberry-continuous-soc (30 chats: periodic and test SOC runs)
- revealer-6978 (6 chats)
- vm-sentinel (9 chats)
- zoom-real-flow (12 chats)
- rev-chat (1 chat, empty)
- shipping-veeqo (1 chat)

**What the chats contain:** few owner messages. Most of the content is automated runs. The repetitive SOC and Zoom runs were de-duplicated after normalising the numbers, and every distinct line was reviewed.

**Note on line references:** in the Source column, "L" means a line number in `chats_part_05`.

## 1. Added from chats (not already covered in MFI or the K files)

| ID | Category | Item | Source | Evidence quote | Status |
|---|---|---|---|---|---|
| CH5-001 | Owner rule | **False-fail rule.** A step "fail" with an exit code but empty captured stderr, contradicted by verified downstream results, is recorded as DONE and not as failed. The agent re-labels it with evidence and states the caveat that it did not re-run the step. | project__revealer-6978/chats/f02bc0d948d3.json, 1782884742.96, user | "it is actually afake fail ... no need to fail message i think you need to record as done" | stated requirement |
| CH5-002 | Owner rule | **Revealer is backend-only.** The owner decided Revealer needs no frontend and that the earlier empty deploy was wrong. The CTO re-planned it as a BACKEND-ONLY service (FastAPI) with a REAL non-empty deploy. | f02bc0d948d3.json, 1782884919.75, user (CTO re-plan at 1782885056.62) | "actually the frontend is not required and deploy empty was wrong from the beggining" | stated requirement; confirmed working in chat (Fullstack passed QA + audit) |
| CH5-003 | Orchestration core | **Background-run acknowledgement.** When the owner's reply is forwarded as a Chief brief, the ack says the team runs in the background. The owner can switch freely between the CTO and any member, live commands appear in that member's chat, and a notification arrives on finish. | f02bc0d948d3.json, 1782884919.75, assistant | "You can switch between the CTO and any member (DevOps) freely; it keeps running" | confirmed working in chat |
| CH5-004 | Scheduling & notifications | **Revealer scheduled runs never executed.** Five "▶ Manual run" scheduled-task runs each stopped with "Backend task … needs your approval first ()". The gate reason is empty and no run went ahead. | project__revealer-6978/chats/1b1c2eda63cd, 2a911a0c3921, 2c62986f9954, a56b55f5fcb8, e571c8a8eb51 (e.g. 1784479553.20, assistant) | "That's a Backend task and it needs your approval first ()." | reported broken in chat (observed) |
| CH5-005 | Per-project features & integrations | **shipping-veeqo question unanswered.** The owner's question in the shipping-veeqo App chat got no assistant reply, and the owner followed up with "??". | shipping-veeqo/chats/c3e2b509753b.json, 1782574992.13 and 1782575066.17, user | "need to know the total order this week" / "??" | reported broken in chat |
| CH5-006 | Other | **vm-sentinel question unanswered at first.** The owner's first question got no reply. It was answered only after the owner repeated it in another chat. | project__vm-sentinel/chats/08e1b76de951.json, 1785673341.86, user; 9e25f35ba677.json, 1785673687.52, user | "is there any new issues" … "please i need to know the answer" | reported broken in chat |
| CH5-007 | Safety & approvals | **Daily VM health result format.** The Daily VM health JSON carries `status` (green/red), `sensor_reachable`, `latest` facts, `findings`, `summary` and `approvals_made`. GREEN with `sensor_reachable:false` means "no new threat signal", not a confirmed live sensor read. | vm-sentinel 9e25f35ba677.json, 1784957842.69 and 1785673788.05, assistant | "green here means no new threat signal rather than a freshly confirmed live sensor read" | confirmed working in chat |
| CH5-008 | Orchestration core | **Repeated auto-continue after a bulk approval.** The auto-continue "[system] gate APPROVED…" prompt fired about 10 times in a row in a SOC periodic chat, once per bulk-approved item ("running 6…1 change(s) now"). It ended with "Nothing is pending approval right now." The diagnosis it requested names Klaviyo, Veeqo and EasyPost, which have no role in a SOC run. | project__redberry-continuous-soc/chats/a7caf927ee58.json, 1787667121.80–1787667122.80, user [system] | "Approved — running 6 change(s) now; results appear in the member chats." | reported broken in chat (observed) |
| CH5-009 | Audit & consistency | **SOC marks missing data as healthy.** Some checks classify absent data as "Benign/Expected / Checked and healthy". SOC-APP-001's evidence was a sudo password prompt. SOC-DEP-002 scanned 0 packages, while the asset filter listed ecosystem=pypi and the scan was over npm. | redberry-continuous-soc (first chat at L1–223, ts ≈1789136037; also f913af495931.json ≈1790095509), assistant | "Evidence: [sudo] password for mostafa:" / "OSV.dev: scanned 0 pkgs" | reported broken in chat (observed) |
| CH5-010 | Safety & approvals | **SOC 24/7 sensor log unreadable across runs.** SOC-SENSOR-008 reported "sensor log unparseable" in run after run (Aug–Sep), so the 24/7 sensor coverage never took effect. | a7caf927ee58.json 1787387975.69; L1–223 (≈1789136037); f913af495931.json ≈1790095509; assistant | "Evidence: sensor log unparseable" | reported broken in chat (observed) |
| CH5-011 | Audit & consistency | **SOC threat-hunt marks a good result as red.** A healthy result is labelled 🔴 "supported". In the same run, smart recovery said no clean backup predates the problem. | a7caf927ee58.json, 1787387979.05 and 1787388027.56, assistant | "🔴 [T1485/T1486] Recoverability … supported: encrypted dated backups … are in place" | reported broken in chat (observed) |
| CH5-012 | Synchronization & Anchor | **Anchor Connect question triggered a full build.** A read-only question (orders this week) came in via Anchor Connect with the live data already included. The CTO still produced a full build → deploy → operators → QA plan instead of answering directly. | f02bc0d948d3.json, 1783131593.50 (user/Chief) → 1783131689.11 (assistant) | "Plan: 1) Fullstack → Build the entire Revealer web app (UI + API + DB)" | reported broken in chat (observed) |
| CH5-013 | Voice | **Meeting-agent features the owner reported.** The owner said these were added to the meeting agent: auto-clear of previous content on each new Start, a Finish control distinct from Stop, and a configurable chunk length. A-173 covers the mic, pause and language, but not these three. | project__zoom-real-flow/chats/f2b977b11e9e.json, 1783630222.01, assistant (report of owner's own talk) | "auto-clear of previously created content on each new start … configurable chunk length" | stated requirement (owner-reported as done) |
| CH5-014 | Build, packaging, run & clients | **Continuous deploy watcher.** The owner reported a script that continuously watches version-control changes, syncs changed files, runs the needed commands, restarts and tests. He also reported a "run" button that redeploys or kills and restarts projects. The B-044 change detector is a manual scan, not a watcher. | zoom-real-flow f2b977b11e9e.json, 1783630222.01, assistant (owner's talk) | "A script now continuously monitors version-control changes and acts on modified files automatically" | stated requirement (owner-reported as done) |

## 2. Already covered

**Count:** about 40 distinct features or behaviours seen in these chats are already in MFI or K. Ten examples:

1. **SOC 8-agent roster with one lane each; monitor-only; approvals auto-DENIED.** Maps to A-18, T-25, K5B-118 and K5A-003.
2. **SOC issue tracker across runs** (new / open / pending / accepted risk / resolved). Maps to A-228.
3. **Smart date-aware recovery and encrypted dated backups** (newest clean point, sha256, approval-gated). Maps to K5A-118.
4. **OSV / KEV / abuse.ch intel, ATT&CK hunting, IP enrichment, prediction.** Maps to C-039 and C-038 (UEBA).
5. **CTO scope recommendation** (enrol Revealer and the Egypt content agent; Cloudflare). Maps to A-233.
6. **Owner summary, technical report and styled PDF/DOCX/MD/PPTX via /soc/report.** Maps to K5A-053, K5A-054 and K5A-056.
7. **Security-alarm approvals decided individually and excluded from approve-all.** Maps to K2B-120, K2B-121 and K4B-104.
8. **Auto-continue after an applied gate** (DB gate → post-deploy TEST → read-only diagnosis; an announce-only turn = FAILURE). Maps to K2A-082 and K2A-101.
9. **Chief → CTO brief, plan coverage gap re-plan, requirements checklist, CTO "Needs fix" review.** Maps to K2A-116, K2A-119, K2A-128 and B-178.
10. **Zoom 7-agent autonomous pipeline** (chunk analysis, 13-section final report, smart notifications that invent nothing). Maps to K2B-236 through K2B-243.

Also covered:
- DevOps deploy secret excludes: A-025 and K5A-150
- Owner instruction relayed to "↳ team updates": K2A-199
- Anchor live read-only data: A-180

## 3. Contradictions

1. **Zoom pipeline: chat claims vs code.** The chat says it "Captured authorized meeting audio in short serial segments" and that chunks of 2–5 min are processed "DURING the meeting".
   - The code reads a transcript file (K2B-237) and splits it into 14-line / 3-min chunks (K2B-238).
   - The chat narration claims a live-capture behaviour that the code does not have.
2. **vm-sentinel schedule.** MFI P-10 says vm-sentinel's periodic schedule is `{}` (empty), but the chats show "⏰ Daily VM health" cron runs on 2026-07-19, 07-24 and 07-25 at about 08:00.
3. **Revealer stack.** MFI T-17 describes Revealer as a NestJS + Next.js app. After the owner's decision (CH5-002), the delivered Revealer is a backend-only Python FastAPI service with no frontend.
4. **SOC approvals.** The SOC project is monitor-only with approvals auto-DENIED (T-25, K5A-003), yet its periodic chat received repeated "[system] The gate you proposed was APPROVED and applied" continuations with change execution (CH5-008).
5. **Requested gate vs no gate.** The scheduled-task prompt says "Execute it fully (do not just propose); stop only at any real publish/approval gate". Yet the Revealer manual runs stopped at a gate with an empty reason every time (CH5-004).


<!-- ==================== PART CAT_COMMS ==================== -->

# CAT_COMMS — Communication and connection mechanisms (Odin-Orchestrator v1)

**Scope.** Every way the parts of Odin talk to each other or to outside services, found by grep across all file types in `/home/claude/v1src` (py, js, cjs, jsx, ts, dart, sh, html, json, yaml, md, plist, xml, conf, service). The compiled Flutter bundle `deploy/web/main.dart.js` and its `NOTICES` file were excluded from hit lists (dart2js runtime noise). The byte-identical copies under `workspace/projects/odin-external-arms/deploy/anchor/` share the `server/` line numbers (K3 note) and are not listed again.

**Secrets.** Not copied. Hard-coded values are named only: the anchor API key literal (`desktop/src/App.jsx:351`, `odin_app/lib/config.dart:77,84`), the VM public IP (`server/soc_run.py:146`, `odin_app/lib/services/cert_override_io.dart:9`, `server/deploy_ssh.py:19`), and the `.cred` keys (`ANCHOR_API_KEY`, `ODIN_API_KEY`, `azvmcred`, Klaviyo / Veeqo / HubSpot / EasyPost keys). The online anchor host is called "the online anchor domain".

**Paths.** `INF` = `workspace/shared/infra/`, `TST` = `workspace/shared/testing/`, `SH` = `shells/`, `SRV` = `server/`, `DSK` = `desktop/`, `APP` = `odin_app/lib/`.

**Direction.** "push" means the initiator sends data. "pull" means the initiator fetches data. "both" means a request and reply that both carry payload, or a two-way stream.

---

## 1. Mechanism table

| ID | Mechanism | From -> To | Transport / protocol | Direction | Evidence (file:line) | Trigger / cadence | In MFI/K? |
|---|---|---|---|---|---|---|---|
| COM-001 | Electron launches the brain process | Electron main -> brain (`server/run.sh` -> uvicorn) | `child_process.spawn("bash", [run.sh])`, stdio inherit, detached process group; SIGKILL of the group on exit | push | DSK/electron/main.cjs:11, 46-68, 70-79, 127, 215, 222-229 | app launch; killed on every exit path | K4B-005, K4B-006, K4B-010, A-011 |
| COM-002 | Electron launches the production poller and restarts it | Electron main -> `local_poller_http.py` | `spawn(python -u local_poller_http.py --anchor <online anchor> --interval 4)`; on exit, `setTimeout` restarts it after 3 s | push | DSK/electron/main.cjs:16-17, 86-125, 216 | app launch (production only; skipped when `ODIN_DEV`) | K4B-007, K4B-008, A-186 |
| COM-003 | Electron IPC bridge | React renderer -> Electron main | `contextBridge.exposeInMainWorld("odin")` -> `ipcRenderer.invoke` -> `ipcMain.handle` (`pick-folder`, `pick-folders`, `pick-files`, `start-request-page`) | both | DSK/electron/preload.cjs:2-11; DSK/electron/main.cjs:7, 150-200 | user clicks | K4B-013, K4B-014, K4B-015, K4B-020 |
| COM-004 | One-click request page | renderer -> main -> local static server -> system browser | `http.get` probe of 127.0.0.1:9104, then `spawn(python -m http.server 9104 --bind 127.0.0.1)`, then `shell.openExternal(.../anchor_sim.html?env=prod)`; fallback shows a copyable command | push | DSK/electron/main.cjs:166-201; DSK/src/views.jsx:2398-2410 | button | K4B-015 |
| COM-005 | New-window URLs go to the system browser | renderer -> OS browser | `setWindowOpenHandler` -> `shell.openExternal`; used by `window.open` for report exports | push | DSK/electron/main.cjs:140; DSK/src/ChatPanel.jsx:410 | link or export click | K4B-012, K4B-094 |
| COM-006 | Renderer UI source | Electron window -> Vite dev server or file:// bundle | HTTP to `localhost:5173` (dev, strictPort) or `loadFile(dist/index.html)` | pull | DSK/electron/main.cjs:141-146; DSK/vite.config.js:15-20 | window creation | K4B-001 |
| COM-007 | `isUp()` brain health probe (dead code) | Electron main -> brain `/health` | Node `http.get`, 1.2 s timeout | pull | DSK/electron/main.cjs:38-44 | never called | K4B-004 |
| COM-008 | Desktop REST client | React renderer -> brain (`odin.base`, default `http://localhost:8000`) | `fetch` JSON; `X-Odin-Token` header when a token is stored; about 120 wrapped endpoints | both | DSK/src/api.js:1-172 | user actions and the polls in COM-013/014/015 | K4B-027, K4B-028 |
| COM-009 | Scoped chat stream | renderer -> brain `/scope/stream` | SSE (`EventSource`); events status, token, delegate, approval, capability_gap, done, error; token sent as `?token=` | both (GET opens, server pushes) | DSK/src/api.js:175-189; SRV/api_v2.py:599-600 | send in chat | K4B-043, A-006, A-007 |
| COM-010 | Team-run stream | renderer -> brain `/projects/{pid}/orchestrate` | SSE; events status, plan, delegate, token, step_done, approval, done, error | both | DSK/src/api.js:192-203; SRV/api_v2.py:386 | team run start | K4B-044 |
| COM-011 | File and audio uploads | renderer -> brain `/scope/upload`, `/voice/stt` | multipart `FormData` POST (field `file`) | push | DSK/src/api.js:120-129, 226-242 | attach file; dictation (interim every 1.8 s, final on stop) | K4B-089, K3-160 |
| COM-012 | Text-to-speech playback | renderer -> brain `/voice/tts` | HTTP GET of WAV through an `<audio>` element (`new Audio(url)`), `?token=` | pull | DSK/src/api.js:212-224 | each spoken reply | K4B-045 |
| COM-013a | Desktop global polls | renderer -> brain | `setInterval` + fetch: `/health` 4 s; `/activity` 2.5 s; `/ui/connectors` 15 s; `/hubspot/status` 60 s; `/operations` watcher 2.5 s; `/approvals` 2.5 s; `/infra/connect-test` 60 s; `/notifications/count` 12 s; bell 12 s; `/schedules/pending` 10 s | pull | DSK/src/App.jsx:50-60, 63-76, 245-252, 276-282; DSK/src/views.jsx:66-96, 110-131, 294, 478-481, 2224-2227, 2700-2710 | timers while the app is open | K4B-055, K4B-056, K4B-066, K4B-067, K4B-101, K4B-102, K4B-106, K4B-112 |
| COM-013b | Desktop view polls | renderer -> brain | `setInterval`: `/agents/all` 5 s; operation panel 1.5 s; `/scope/summary` feed 3 s; member chats 3 s; schedules 10 s; activity flow 2.5 s | pull | DSK/src/views.jsx:368-372, 820-828, 1060-1063, 1081-1084, 1209-1212, 1242 | while the view is mounted | K4B-109, K4B-118, K4B-121, K4B-122 |
| COM-013c | Desktop chat polls | renderer -> brain | `setInterval`: `/scope/messages` 3 s (ChatPanel and Conversations), run-status stuck check, run-now refresh at 3 s, 8 s and 15 s | pull | DSK/src/ChatPanel.jsx:55-66, 136-140; DSK/src/Conversations.jsx:72-75 | open chat | K4B-072, K4B-078, K4B-079, K4B-082 |
| COM-014 | Desktop reads the anchor login code | renderer -> anchor (production: the online anchor domain, hard-coded; dev: `odin.anchor` or `localhost:9100`) | `fetch` GET `/anchor/v1/manage/pending-code` with `X-API-Key` (literal key in source) | pull | DSK/src/App.jsx:351, 355-376 | every 4 s | K4B-068, K4B-069, K3-061, A-124 |
| COM-015 | Desktop Anchor Connect view | renderer -> brain's in-process anchor admin | `fetch` `/anchor/v1/admin/requests`, `/counts`, `/config` (GET/POST) on the brain base | pull | DSK/src/api.js:143-146; SRV/anchor.py:92-104 | Anchor Connect page | K4B-158, K3-010, K3-011 |
| COM-016 | Desktop OS notifications | renderer -> macOS Notification Center | Web Notifications API inside Electron (`new Notification`, permission request) | push | DSK/src/views.jsx:12-18, 120-125, 2706 | new approval, op outcome, periodic task due | K4B-099, K4B-100 |
| COM-017 | Live-meeting monitor page | renderer / Flutter web iframe / browser -> brain `/meeting_monitor.html` + `/meeting/*` | static page + `fetch`: `/meeting/state`, `/clear`, `/chunk` (audio multipart per chunk), `/finish`, `/view`, `/report`, `/report_all` | both | DSK/src/api.js:33; dashboard/meeting_monitor.html:113-273; SRV/meeting_api.py:395-548 | meeting start; one chunk per timer (`setTimeout`) | K4B-029, K4B-169, K2B-219, K4A-193 |
| COM-018 | Report and file downloads | clients -> brain | HTTP `StreamingResponse` / `FileResponse` (PDF, DOCX, MD, PPTX, ZIP, scope files) | pull | SRV/api_v2.py:650, 686, 773; SRV/soc_api.py:54; SRV/meeting_api.py:518-545; DSK/src/api.js:37 | export / attachment click | K4B-094, C-018 |
| COM-019 | Brain HTTP server | Electron / shell scripts -> uvicorn FastAPI | HTTP on `HOST` (default 127.0.0.1) : `PORT` (default 8000); `run.sh` frees the port first (`lsof` + `kill -9`) | serves | SRV/run.sh:22-52; SRV/app.py:35; SH/anchor_up.sh:42; SH/development_full_checker.sh:93; SH/production_full_checker.sh:170 | process start | K3-129, D-010 |
| COM-020 | Brain route mounts | brain -> its sub-routers | FastAPI `include_router`: voice, api_v2 (89 routes), soc, notifications, meeting, auth, `/api/v1`, `/anchor/v1`, hubspot, directions, audit, ui; static `/state`, `/history`, `/` (dashboard) | serves | SRV/app.py:66-188, 459-461 | startup | K3-132, K3-140, C-023 |
| COM-021 | Brain CORS | any web origin -> brain | `CORSMiddleware(allow_origins=["*"])` | serves | SRV/app.py:38-46 | every request | K3-130 |
| COM-022 | Brain access-token gate | client -> brain | `X-Odin-Token` header or `?token=` (for SSE), only when `ODIN_ACCESS_TOKEN` is set, only for paths starting `/chat`, `/dispatch`, `/voice` | inbound check | SRV/app.py:50-63 | every request | K3-131, A-151 (scope gap is new: see §2 N1) |
| COM-023 | Brain SSE endpoints | brain -> clients | `StreamingResponse(media_type="text/event-stream")`: `/scope/stream`, `/projects/{pid}/orchestrate`, `/activity/stream` (2 s loop), legacy `/chat/stream`, `/chats/{cid}/stream` | push | SRV/api_v2.py:386, 599-600, 781-790; SRV/app.py:259, 373 | client opens a stream | K3-135, K3-136, K2A-057 (no-consumer finding is new: §2 N2) |
| COM-024 | Claude CLI one-shot call | brain modules -> `claude` binary (which reaches Anthropic itself) | `subprocess.run(["claude","-p",…,"--output-format","json"])`, captured stdout, `ODIN_CLAUDE_TIMEOUT` 600 s; `--resume <session>` for memory | both | SRV/claude_cli.py:80-140; callers SRV/projects.py:992, 1388, 1478; SRV/main_task.py:53, 120; SRV/audit.py:185; SRV/deploy_runner.py:163, 328; SRV/deploy_agent.py:41; SRV/agents_registry.py:432; SRV/zoom_pipeline_run.py:25 | engine calls | K2B-101, K2B-104, K2B-105, A-001 |
| COM-025 | Claude CLI streaming session | brain -> `claude` binary | `subprocess.Popen` stdout/stderr PIPE, `--output-format stream-json --verbose`; background reader thread + stderr drain; heartbeat 15 s, idle kill 420 s, max-wall 900 s | both (stdout stream) | SRV/claude_cli.py:150-300; callers SRV/api_v2.py:911-913; SRV/app.py:331; orchestrator/dispatcher.py:273 | chat, team run, operations | K2B-106 – K2B-113, A-006 |
| COM-026 | Engine read-only hook | `claude` binary -> `readonly_hook.py` | Claude Code PreToolUse hook registered through `--settings`; JSON on stdin; exit 2 = deny | both | SRV/claude_cli.py:58-74; SRV/readonly_hook.py:56-77 | every Bash tool call in read-only runs | K2B-097, K1-086 – K1-088 |
| COM-027 | MCP isolation | brain -> `claude` binary | `--strict-mcp-config` (no MCP servers spawned) unless `ODIN_AGENT_MCP=1` | push (flag) | SRV/claude_cli.py:163-169 | every streamed agent call | K2B-107 |
| COM-028 | Ollama chat fallback | brain -> local Ollama | HTTP POST `ODIN_OLLAMA_URL` (default localhost:11434) `/api/chat`, 120 s | both | SRV/brain_handler.py:13-61; callers SRV/api_v2.py:920; SRV/projects.py:998, 1484 | Claude CLI unavailable, or engine = ollama | K2B-115, K2B-116, A-002 |
| COM-029 | Ollama semantic router | dispatcher -> local Ollama | HTTP POST `/api/chat` with JSON output, `ODIN_ROUTER_TIMEOUT` 12 s | both | orchestrator/semantic_router.py:18-72; orchestrator/dispatcher.py:187 | each routed request when `ODIN_SEMANTIC_ROUTER=1` | K2B-255, K2B-259, K2B-260 |
| COM-030 | Ollama model discovery | brain -> local Ollama | HTTP GET `/api/tags` (2–3 s timeout) | pull | SRV/models_config.py:69-70; SRV/capabilities.py:36-37 | model list / capabilities read | K2B-167 |
| COM-031 | Tool presence checks | brain -> local PATH | `shutil.which("claude")`, `which az` for connector "connected" badges | pull | SRV/claude_cli.py:24; SRV/ui_api.py:151; SRV/infra_az.py:36-49 | /ui/connectors, engine calls | K3-108, K2B-096, K5A-126 |
| COM-032 | Brain -> core database | brain modules -> local PostgreSQL `odin_core` | `psycopg2.connect(dbname="odin_core")` (local socket, no DSN) | both | SRV/workspace_mw.py:45-46; SRV/agents_registry.py:28-29, 85, 131, 224, 265; SRV/ui_api.py:21-22; SRV/directions.py:21-22; SRV/workspace_audit.py:70-71; SRV/capabilities.py:51-52; SRV/projects.py:609-610; tests TST/phase7_lib.py:29-30, TST/seed_connectors.py:46 | registry, UI contract, audit | K3-104, K1-006, B-060 |
| COM-033 | JSON store <-> DB lockstep | `store.py` writes -> `workspace_mw.sync_row` -> `odin_core` | in-process call after an atomic tmp+replace JSON write | push | SRV/store.py:153-166; SRV/workspace_mw.py:45 | every store write | K3-154, K1-011 |
| COM-034 | Anchor queue storage | anchor (in-process or remote) -> PostgreSQL `odin_anchor` or JSON file | `psycopg2.connect(ANCHOR_PG_DSN)`, table `anchor_requests`; else `workspace/anchor-layer/anchor_queue.json` (last 2000 rows); results over 32,000 chars offloaded to `active_requests/` | both | SRV/anchor_queue.py:29-34, 75-119, 237-275; SRV/store.py:36-39; SH/development_full_checker.sh:107; SH/anchor_up.sh:52; INF/phase3_gate.py:343-345 | every queue operation | K3-022 – K3-027, A-192 |
| COM-035 | In-process anchor router | callers -> brain `/anchor/v1` | FastAPI router: POST `/requests`, GET `/requests/{rid}`, POST `/ack`, GET `/poll`, POST `/result`, admin config/requests/counts; `X-API-Key` on /requests, /poll, /result only | serves | SRV/anchor.py:55-104; SRV/app.py:128-137 | inbound calls | K3-005 – K3-011 |
| COM-036 | In-process anchor poller | brain thread -> its own queue -> engine -> webhook | daemon thread every 5 s: next_pending, mark_processing, process, submit_result, retry_due; `ODIN_ANCHOR_NO_POLLER=1` disables | push | SRV/anchor.py:296-320; SRV/app.py:132 | every 5 s while the brain runs | K3-020, K3-021 |
| COM-037 | Anchor processing tiers | anchor.process -> Klaviyo/Veeqo, engine, or team run | Tier 1 connector facts over HTTPS; Tier 2 one read-only engine stream capped at 90 s; Tier 3 `api_v2.start_run`, then `run_status` polled every 2 s (300 s) | both | SRV/anchor.py:112-160, 224-290 | each processed request | K3-012, K3-015, K3-018, K3-019 |
| COM-038 | Standalone anchor server | web, mobile, third parties, poller, desktop -> `anchor_remote.py` | stdlib `ThreadingHTTPServer`; `/`, `/health(z)`, `/manage`, `/anchor/v1/*`; dev binds 0.0.0.0:9100, VM binds 127.0.0.1:48619 behind nginx | serves | SRV/anchor_remote.py:227-330, 571-583; SH/development_full_checker.sh:107; SH/anchor_up.sh:52; INF/phase3_gate.py:343-345 | process start (systemd on the VM) | K3-051, K3-060, K5B-240, D-024 |
| COM-039 | Anchor CORS | any origin -> anchor_remote | `Access-Control-Allow-Origin: *`; allowed headers Content-Type, X-API-Key, X-Manage-Token, X-Odin-Client | serves | SRV/anchor_remote.py:231 | every response | K3-056 |
| COM-040 | Anchor auth headers | clients -> anchor_remote | `X-API-Key` (= ANCHOR_API_KEY; open when unset); `X-Odin-Client: web/mobile` gate (403 when stopped, 401 without a manage session); `X-Manage-Token` session | inbound check | SRV/anchor_remote.py:31, 260, 305-308; APP/api/anchor_api.dart:91-97 | every gated route | K3-052, K3-058, A-150 |
| COM-041 | Anchor Manage owner UI | browser -> anchor_remote `/manage` + `manage/*` | HTML page with inline `fetch`; token and device id in browser `localStorage`; request-code shows a code on the desktop | both | SRV/anchor_remote.py:132-223, 350-360, 457-476, 547 | owner login / admin | K3-055, K3-069, K3-070, A-154 |
| COM-042 | Mirror endpoints | web/mobile -> anchor_remote | GET `/anchor/v1/projects` (with `stale` flag), `/mirror/{key}`, `/pool/{scope}` paged, `?since=<seq>` delta | pull | SRV/anchor_remote.py:365-415 | client polls (COM-055) | K3-064 – K3-067, A-183, A-184 |
| COM-043 | Webhook delivery to the caller | anchor -> third-party `webhook_url` | HTTP POST JSON, 20 s timeout, 2xx = ack; retry state machine (`retry_count` 4, `retry_interval_sec` 600) | push | SRV/anchor_queue.py:354-408 | result submit, then retry sweeps | K3-036, K3-037, A-179 |
| COM-044 | Webhook retry sweeps | anchor -> webhook_url | remote: daemon thread every 30 s; in-process: `retry_due` inside the 5 s poller loop | push | SRV/anchor_remote.py:554-568; SRV/anchor.py:309-318 | 30 s / 5 s | K3-074, K3-039 |
| COM-045 | Third-party acknowledgement callback | third party / webhook viewer -> anchor | HTTP POST `/anchor/v1/requests/{rid}/ack` (no auth) | push | SRV/anchor.py:76; SRV/anchor_remote.py:527; SRV/webhook_receiver.py:97 | caller choice | K3-007, K3-073, K3-114 |
| COM-046 | HTTP poller: pull tasks and return results | Mac poller -> anchor (local :9100 or online anchor) | urllib JSON, `X-API-Key`, 60 s timeout; HTTPS with `CERT_NONE` (no TLS verification); GET `/poll`, POST `/requests/{rid}/result` | both | SRV/local_poller_http.py:20-98 | every interval | K3-075, K3-076, K5B-241, D-023 |
| COM-047 | Poller -> brain commands | poller -> brain (`ODIN_BRAIN`, default localhost:8000) | urllib POST/DELETE/GET: `/projects`, `/chats` CRUD, `/scope/message`, `/projects/{pid}/run-now`, `/notifications/read`, `/meeting/finish_text` | push | SRV/local_poller_http.py:100-233, 265-268 | sender=command requests | K3-078 – K3-087, K5B-243 |
| COM-048 | Poller consumes the brain SSE | poller -> brain `/scope/stream` | urllib GET with `Accept: text/event-stream`, drained until done (90 s cap), then reads back the last assistant message | pull | SRV/local_poller_http.py:235-262 | sender=chat requests | K3-088 |
| COM-049 | Mirror sync push | poller -> anchor `POST /anchor/v1/sync` | JSON body: projects, pools (≤60 msgs each), agents, 13 mirror keys; persisted to `anchor_sync.json` | push | SRV/local_poller_http.py:276-347, 92-96; SRV/anchor_remote.py:504-525, 54-80 | every interval, plus immediately after chat/command | K3-089, K3-090, K3-077, K3-072, A-182, A-183 |
| COM-050 | Poller loop and cadence | poller process | `while True: poll_once; sync_push; sleep(interval)`; default 5 s, 4 s from Electron and the supervisor | both | SRV/local_poller_http.py:350-369; DSK/electron/main.cjs:96; SH/poller_supervisor.sh:132-133 | continuous | K3-091 |
| COM-051 | Poller supervisor | shell -> poller | `pgrep -f "[l]ocal_poller_http.py --anchor"` every 5 s; relaunch with `nohup` | push | SH/poller_supervisor.sh:145-153; SH/development_full_checker.sh:112-113; SH/production_full_checker.sh:177-179 | every 5 s | K5B-160, A-185, D-022 |
| COM-052 | Flutter HTTP client and profiles | Flutter app -> brain (direct) or anchor (anchor mode) | `package:http`; direct: `X-Odin-Token` + `/api/v1` with `X-API-Key` (ODIN_API_KEY); anchor: `X-API-Key`, `X-Odin-Client`, `X-Manage-Token`; 15 s timeout; anchor mode throws if a brain URL is built | both | APP/api/anchor_api.dart:18-165; APP/config.dart:16-86; APP/state/app_state.dart:25-32 | every call | K4A-001, K4A-002, K4A-011, K4A-072, A-150 |
| COM-053 | Flutter chat through the anchor | app -> anchor -> poller -> brain -> anchor -> app | POST `/anchor/v1/requests` (sender `chat`), then GET status every 2 s for up to 8 min | both | APP/api/anchor_api.dart:732-750 | send in chat (anchor mode) | K4A-063, A-137 |
| COM-054 | Flutter command queue through the anchor | app -> anchor -> poller -> brain | POST requests `{project:"__command__", sender:"command", prompt:kind}`; poll every 2 s for up to 3 min; meeting_report polls the pool 8×2 s | both | APP/api/anchor_api.dart:755-810 | write actions (anchor mode) | K4A-064, K4A-065, K4A-067 |
| COM-055 | Flutter mirror reads and delta sync | app -> anchor | GET `/mirror/{key}`, `/pool/{scope}?offset&limit`, `?since=<lastSeq>` with a self-heal full pull | pull | APP/api/anchor_api.dart:47-80, 170-185 | timer polls (COM-058) | K4A-003, K4A-012, K4A-013 |
| COM-056 | Flutter ask (sync and async) | app -> brain `/api/v1/p/{id}/ask` or anchor | direct POST; anchor: submit then poll every 3 s for up to 8 min | both | APP/api/anchor_api.dart:696-700, 813-837; SRV/external_api.py:57 | `AppState.ask` (no UI caller) | K4A-068, K3-112, A-131 |
| COM-057 | Flutter login through the anchor | app -> anchor `manage/*`; code shown on the desktop (COM-014) | POST request-code, login; GET me; POST logout | both | APP/api/anchor_api.dart:102-133 | login screen | K3-049, K3-062, A-154 |
| COM-058 | Flutter timers | app -> brain or anchor | `Timer.periodic`: shell 12 s (notifications + change detector), HubSpot chip 60 s, chat 5 s, WhatsApp view 5 s, audit 12 s | pull | APP/screens/shell.dart:60, 792; APP/screens/chat_screen.dart:132; APP/screens/whatsapp.dart:364; APP/screens/audit_screen.dart:27 | while the screen is open | K4A-100, K4A-108, K4A-113, K4A-130, K4A-165 |
| COM-059 | Flutter SSE (direct mode only) | app -> brain `/scope/stream` | io: `http.Client().send` + line parser on `event:token`; web: `EventSource` with `?token=`; refused in anchor mode | both | APP/services/sse_io.dart:4-27; APP/services/sse_web.dart:7-30; APP/api/anchor_api.dart:646-655 | chat send (direct) | K4A-057, K4A-190 |
| COM-060 | TLS certificate override | Flutter (iOS/Android/desktop) -> VM reverse proxy | `HttpOverrides.global`, `badCertificateCallback` true only for the VM IP and the anchor domain; no-op on web | both | APP/services/cert_override_io.dart:1-19; APP/services/cert_override.dart:1-4; APP/main.dart:34 | app start | K4A-097 |
| COM-061 | Mobile local notifications | Flutter -> iOS/Android notification center | `flutter_local_notifications` channel `anchor_updates`; web uses an in-app banner | push | APP/services/notifications_mobile.dart:1-40; APP/services/notifications.dart:1-5 | new terminal anchor request | K4A-089, K4A-192, A-133 |
| COM-062 | Flutter web opens URLs and embeds the meeting page | Flutter web -> browser tab / iframe of brain | `html.window.open(url,'_blank')`; iframe platform view of `<brainBase>/meeting_monitor.html?pid` | push | APP/services/web_open.dart:13-28 | report export / meeting | K4A-123, K4A-193 |
| COM-063 | Device speech services | Flutter -> OS speech recognition and TTS | `speech_to_text` (continuous, 30 s/4 s), `flutter_tts`; mic and speech permissions | both | APP/services/voice.dart:24-113; APP/screens/meeting_sheet.dart:57; odin_app/ios/Runner/Info.plist:69-71 | mic button / meeting | K4A-163, K4A-187, K4A-189 |
| COM-064 | Android network permission missing | Flutter Android release -> network | `android.permission.INTERNET` only in debug/profile manifests | n/a | odin_app/android/app/src/debug/AndroidManifest.xml:6; odin_app/android/app/src/profile/AndroidManifest.xml:6; main manifest has none | release build | K4A-198 |
| COM-065 | Password SSH to the VM | brain / scripts -> VM | `sshpass -p <azvmcred> ssh` (password auth, StrictHostKeyChecking=no, ConnectTimeout 20); `sudo` rewritten to `sudo -S` fed on stdin | both | SRV/deploy_ssh.py:26-82; callers SRV/api_v2.py:1203, 1298, 1339; SRV/deploy_runner.py:371, 415, 425; SRV/deploy_agent.py:97-113, 194-195; SH/phase_ctl.sh:72-81; INF/phase3_gate.py:178; INF/deploy_verify.py:31 | deploy, diagnose, gates | K5A-144 – K5A-148, A-032, D-027 |
| COM-066 | rsync over SSH | Mac -> VM folders | `sshpass rsync -az --checksum` (optional `--delete`), verify by `--dry-run --itemize-changes`; secret excludes | push | SRV/deploy_ssh.py:84-150; INF/deploy.sh:262-284; TST/test_web_online.py:130; TST/test_anchor_online.py:237; INF/phase3_gate.py:400 | deploy | K5A-149 – K5A-151, B-126 |
| COM-067 | Read-only SSH channel for SOC | SOC modules -> VM | `_ssh_ro` (sshpass, banned-verb guard, hard-coded host); `_node_ro` sends base64 Node/Prisma scripts | pull | SRV/soc_run.py:134-158, 352, 425, 606; SRV/security_sentinel.py:29-30; SRV/soc_behavior.py:36, 125; SRV/soc_recovery.py:100, 142 | SOC runs, sentinel | K5A-012, K5A-030 |
| COM-068 | Key-based SSH profile | brain -> VM | `ssh` BatchMode with host/user/port/key from `connection.profile.json`; reachability and gated run | both | SRV/infra_ssh.py:22-80; SRV/app.py:380-396 | `/infra/reachable`, `/infra/connect-test` | K5A-141 – K5A-143, K3-137 |
| COM-069 | Azure control plane | brain / deploy.sh -> Azure Resource Manager -> VM agent | `az vm list/show`, `az vm run-command invoke` (RunShellScript as root or `sudo -u`), `az network nsg rule list/update` | both | SRV/infra_az.py:69-175; SRV/infra_rotate.py:38-150; SRV/soc_run.py:524; SRV/api_v2.py:174, 1262-1268; INF/deploy.sh:157-236 | connect test, IP rotation, deploy preflight | K5A-128 – K5A-139, A-045, B-164 |
| COM-070 | Public IP discovery | Mac -> ipify / ifconfig.me / icanhazip | `curl -s --max-time 6` | pull | SRV/infra_ssh.py:31-41; INF/deploy.sh:154 | rotation / deploy / `/infra/ip` | K5A-140, K5B-017 |
| COM-071 | Deploy script stream | brain -> `bash deploy.sh` | `subprocess.Popen`, stdout+stderr PIPE line-buffered into the operation log and chat; stop watchdog every 1 s | both | SRV/deploy_runner.py:40-110 | deploy operation | K2B-201, K2B-202, K2B-203 |
| COM-072 | Local helper subprocesses | brain -> `deploy_changes.py`, scheduler pipelines | `subprocess.run` (scan/update); scheduler `run_cmd` with `shell=True`, 1800 s, output posted to the scope chat | push | SRV/api_v2.py:1726-1729, 1872-1875, 2590-2592; SRV/scheduler.py:255-275 | deploy flow; scheduled pipelines | K2B-152, K2B-153, K2A-090 |
| COM-073 | Remote DB and migration commands | Mac (over SSH) -> VM PostgreSQL / Prisma | `sudo -u postgres psql` (create db/role), `npx prisma migrate deploy/status`, read-only Prisma via Node | push | INF/phase3_gate.py:240-310; INF/deploy.sh:294-301; SRV/deploy_agent.py:100-101; SRV/soc_run.py:352, 425 | deploy, SOC | K5B-073 – K5B-078, K2B-197 |
| COM-074 | VM services via systemd | Mac (over SSH) -> VM systemd | `odin-anchor-online` (anchor_remote on 127.0.0.1:48619, PG drop-in), `odin-web-online` (no-cache static server on 48620) | push | TST/test_anchor_online.py:249-270; TST/test_web_online.py:193-215; INF/phase3_gate.py:341-365, 403 | deploy | K5A-015, K5B-142, K5B-145, K5B-083, A-191 |
| COM-075 | Reverse proxy on the VM | internet -> nginx 443 -> loopback services | nginx site `odin-proxy`: `/odin-anchor/` -> 127.0.0.1:48619, `/odin-web/` -> 127.0.0.1:48620, branded landing; Let's Encrypt cert for the domain, self-signed for a bare IP | both | TST/test_anchor_online.py:108-150 | always on | K5B-143, A-191 |
| COM-076 | Repo proxy and container template (not the live layout) | nginx `/anchor/` -> 127.0.0.1:9100; docker compose; systemd unit running docker | nginx template, Dockerfile, compose (port 9100, `oth` read-only), healthcheck by urllib | serves | INF/anchor/nginx-anchor.conf:1-33; INF/anchor/Dockerfile:2; INF/anchor/docker-compose.yml:3-23; INF/anchor/odin-anchor.service:1-21 | manual | K5B-091 – K5B-094, A-193 |
| COM-077 | SOC sensor on the VM | systemd timer -> `soc_sensor.sh` -> `events.jsonl`; brain reads it over SSH | file on the VM + `tail` over SSH | push (VM) / pull (brain) | workspace/projects/redberry-continuous-soc/code/sensor/soc-sensor.timer:4-10; …/soc-sensor.service:5-12; …/soc_sensor.sh:28-35; SRV/soc_run.py:606; SRV/security_sentinel.py:29 | every 5 min (sensor); SOC runs | K5B-182 – K5B-184, K5A-030 |
| COM-078 | SOC endpoint probes | brain -> public endpoints | urllib GET/HEAD (status, security headers), raw TLS socket to :443 for cert expiry, curl over SSH for 127.0.0.1 targets | pull | SRV/soc_run.py:325-340, 720-760, 800-812 | SOC run | K5A-022, K5A-032, K5A-034 |
| COM-079 | Threat-intel feeds | brain -> OSV.dev, CISA KEV, abuse.ch Feodo, ip-api.com | HTTPS POST/GET JSON; ip-api over plain HTTP | pull | SRV/soc_intel.py:13-46; SRV/soc_intel_fusion.py:17-51; SRV/soc_enrich.py:39-40 | SOC run (cached 6 h / 24 h) | K5A-031, K5A-039, K5A-091, K5A-095, K5A-097, K5A-098 |
| COM-080 | SaaS quota probes | brain -> Klaviyo, HubSpot, SendGrid, Brevo usage APIs | HTTPS GET with provider auth header (Twilio, Mailgun etc. templated without URL) | pull | SRV/soc_quota.py:17-75 | SOC quota check | K5A-033, K5A-109 – K5A-112 |
| COM-081 | HubSpot API | brain -> api.hubapi.com | HTTPS, `Authorization: Bearer`; routes `/hubspot/status|overview|scopes|run|ask` | both | SRV/integrations/hubspot.py:18-140; SRV/hubspot_api.py:26-134 | desktop badge, run, scheduler | K3-141 – K3-148, C-041 |
| COM-082 | Klaviyo API | brain -> a.klaviyo.com | HTTPS, `Klaviyo-API-Key` + revision header; GET only, one POST `/metric-aggregates` | pull | SRV/integrations/klaviyo.py:12-121 | anchor facts, callers | K3-149 – K3-151, A-207 |
| COM-083 | Veeqo API | brain -> api.veeqo.com | HTTPS, `x-api-key`; GET whitelist | pull | SRV/integrations/veeqo.py:17-99 | anchor facts | K3-152, K3-153, A-208 |
| COM-084 | EasyPost API | brain -> api.easypost.com | HTTPS Basic (key); GET + POST `/trackers` only | both | SRV/integrations/easypost.py:21-115 | callers | K3-145, K3-146, B-158, B-159 |
| COM-085 | Credentials file | integrations, scripts -> `workspace/shared/oth/.cred` | file read (`KEY=value` / `key: value`) | pull | SRV/integrations/cred.py:15-34; SH/phase_ctl.sh:25; SRV/app.py:139-152 | each call; startup auto-register | K3-144, K3-133, A-152 |
| COM-086 | Azure Speech TTS (not wired) | voice -> `<region>.tts.speech.microsoft.com` | HTTPS SSML POST | push | voice/backend/azure_tts.py:16-53 | none (nothing imports it) | K3-164 |
| COM-087 | macOS `say` / `afconvert` / Piper (dead code) | voice -> local binaries | `subprocess.run` | push | voice/backend/voice_service.py:136-150 | none | K3-159 |
| COM-088 | Voice router | clients -> brain `/voice/stt`, `/voice/tts` | multipart upload / WAV response; 503 unless `USE_VOICE=1` | both | voice/backend/voice_service.py:158-191; voice/frontend/useVoice.ts:41, 101 | dictation / speech | K3-160, K3-165 |
| COM-089 | External API | third parties / app -> brain `/api/v1` | HTTP + `X-API-Key` (ODIN_API_KEY, open when unset): `/health`, `/projects`, `/p/{id}/ask` | both | SRV/external_api.py:28-60 | caller | K3-110 – K3-112, C-024 |
| COM-090 | Scheduler loop | brain thread -> scheduled tasks -> engine / pipelines / notifications | daemon thread every 20 s (`_tick`), audit sentinel about every 15 min | push | SRV/scheduler.py:387, 455-473; SRV/app.py:429 | every 20 s | K2B-159, K2B-161, C-020 |
| COM-091 | Background worker threads | API handlers -> daemon threads (UI polls the result) | `threading.Thread(daemon=True)` for approvals apply, deploy, resume, orchestrate | push | SRV/api_v2.py:253-273, 467, 478, 1275, 1416, 1513, 1781, 3281; SRV/app.py:426 | API calls | K2A-036, K2B-154 |
| COM-092 | In-app notification feed | brain modules -> notifications store -> clients | JSON store; `/notifications` GET/count/read/clear/test; mirrored to the anchor under key `notifications` | pull | SRV/notifications_store.py:28-58; SRV/notifications_api.py:9-31 | polled by clients | C-032, K2B-151, K4B-031 |
| COM-093 | Webhook receiver | anchor -> local receiver; browser -> viewer | `ThreadingHTTPServer` on 0.0.0.0:`--port` (9300): POST `/cb[/pid]`, GET `/list[/pid]`, HTML viewer polling every 3 s | both | SRV/webhook_receiver.py:19-109; SH/development_full_checker.sh:124; SH/production_full_checker.sh:182 | webhook delivery | K3-113 – K3-115, A-198 |
| COM-094 | Request-log sim server | request page -> `sim_server.py` | `ThreadingHTTPServer` 127.0.0.1:9104: `/sim/requests` CRUD, `/sim/response`, static files; SQLite | both | SRV/sim_server.py:29-268 | request page | K3-116 – K3-120 |
| COM-095 | Third-party request page | browser -> anchor, webhook receiver, sim server | `fetch` POST `/anchor/v1/requests`, GET status every 2.5 s, GET webhook `/list/<pid>`, sim CRUD; Dev/Prod switch via `anchor_prod.js` / `anchor_seed.js` (embedded key) | both | workspace/anchor-layer/anchor_sim.html:150-337; anchor_prod.js:2-8; anchor_seed.js:1 | user send | K3-167 – K3-175 |
| COM-096 | Static request-page servers | shell / Electron -> `python -m http.server 9104` | stdlib static server on 127.0.0.1 | serves | SH/production_full_checker.sh:186; DSK/electron/main.cjs:188; workspace/anchor-layer/index.html:3 | phase start / button | K5B-179, K3-169 |
| COM-097 | Third-party CLI and legacy HTML sim | CLI / browser -> anchor | urllib or fetch POST, then GET every 3 s ×200 | both | SRV/third_party.py:27-53; workspace/anchor-layer/third_party_sim.html:57-92 | manual | K3-121, K3-177 |
| COM-098 | E2E in-process HTTP sinks | tests -> local TCP servers | `socketserver.TCPServer(("127.0.0.1",0))` webhook sinks; `ThreadingHTTPServer` anchor stand-in + hook server | both | SRV/e2e_anchor.py:53-54; SRV/e2e_anchor_http.py:45-46; SRV/e2e_anchor_live.py:50-51; SRV/e2e_phase2.py:51, 105-108 | test runs | K5A-163 – K5A-167 |
| COM-099 | Test / diagnostic clients with TLS checks off | test scripts -> anchor, web, brain | urllib with unverified SSL contexts; `curl -sk` | pull | TST/isolate_anchor.py:17-46; INF/phase3_e2e.py:19-97; TST/trace_chain.py:13-66; TST/test_anchor_online.py:32-52, 329-334; TST/test_web_online.py:33-53; INF/phase3_gate.py:227, 371, 406; SH/phase_ctl.sh:38-40 | gates, trace, isolate | K5B-122, K5B-146, K5B-157 |
| COM-100 | Brain/anchor readiness waits | shell scripts -> brain / anchor | `python -c urlopen(/health)` loop (30×1 s), `curl /anchor/v1/_status` loop | pull | SH/anchor_up.sh:40-44; SH/development_full_checker.sh:32, 97, 157; SH/production_full_checker.sh:169-171; INF/anchor/docker-compose.yml:17 | phase start | K5B-158 |
| COM-101 | Test runners against the brain | phase7 / e2e scripts -> brain REST | urllib GET/POST to `BRAIN + path` | both | TST/phase7_realrun.py:38-47; TST/phase7_prompt_loop.py:51-60; TST/phase7_prompt4.py:41-50; TST/e2e_real_flow.py:19-21 | test runs | K5B-120, K5B-125 – K5B-127 |
| COM-102 | Agent terminal bridge | outside agent -> owner's Mac shell | files `workspace/logs/agent_term/CMD` -> `OUT.log` + `STATUS`; mtime poll every 1 s; `bash -c` with stdin `/dev/null`, output to file, 900 s watchdog; any command | both | SH/agent_terminal_bridge.sh:13-96 | CMD file change | K5B-161, A-223, B-028, D-026 |
| COM-103 | Phase control bridge | outside agent -> Mac watcher | files `workspace/logs/phase_ctl/CMD` -> `OUT.log` + `STATUS`; poll every 2 s; commands health, send, tail, vm, redeploy, trace, isolate, audit, auditfix | both | SH/phase_ctl.sh:19-118; SH/development_full_checker.sh:162-166 | CMD file change | K5B-122, K5B-157, A-189, D-025 |
| COM-104 | Anchor loop RUN file | outside agent or typed input -> phase stack | file `workspace/logs/phase_ctl/RUN` (phase2, phase3, stop, done) + timed `read` on stdin; poll every 2 s | push | SH/anchor_loop.sh:1-86 | RUN file change | K5B-159, K4A-162 |
| COM-105 | Test loop trigger files | outside agent -> test daemon | files `testing/results/RUN_NOW`, `STOP` -> `STATUS`, `RUN_SEQ`, `latest.log`; `monitor.sh` follows the log with `tail -F` | both | TST/loop.sh:1-60; TST/monitor.sh:14-18 | file change | K5B-123, K5B-138, D-020, D-032 |
| COM-106 | Dev stack launcher | `development_full_checker.sh` -> all local players | background processes: brain, anchor_remote 0.0.0.0:9100, poller supervisor, webhook 9300, request page, phase_ctl, `npm run dev` (Vite + Electron), Flutter web no-cache server 0.0.0.0:8080, iOS simulator via `xcrun simctl` | push | SH/development_full_checker.sh:93-309 | phase 2 start | K5B-162 – K5B-175, D-011 |
| COM-107 | Production stack launcher | `production_full_checker.sh` -> deploy gates + local players | VM validation, deploy-anchor, Flutter web build, deploy-web over SSH; poller -> online anchor; webhook; request page; desktop with `VITE_ODIN_ENV=production`; Flutter web-server and physical iPhone | push | SH/production_full_checker.sh:36-247 | phase 3 start | K5B-176 – K5B-180 |
| COM-108 | Browser opening by scripts | shell scripts -> default browser | macOS `open <url>` (request page, anchor landing, online web, anchor) and `open -a Simulator` | push | SH/development_full_checker.sh:151-158, 267, 275, 288; SH/production_full_checker.sh:188-193 | phase start | K5B-179, K5B-174 |
| COM-109 | Legacy dashboard pages | browser -> brain | `index.html` reads `/state`, `/history`, POSTs `/chat`; `console.html` SSE `/chats/{cid}/stream`; `mobile.html` token on 401 + SSE; `audit.html` | both | dashboard/index.html:153-158, 224-277; dashboard/console.html:100-149; dashboard/mobile.html:98-114; dashboard/audit.html:70-71 | page use | K4B-163 – K4B-168 |
| COM-110 | Phone-access options (doc only) | phone -> Mac brain | Tailscale `serve` HTTPS, Cloudflare quick tunnel, or LAN `0.0.0.0:8000`, with `ODIN_ACCESS_TOKEN` | both | workspace/shared/runbooks/phone-access.md:1-41 | manual | A-155, B-150 |
| COM-111 | Project code: full-services backend and frontend | NestJS backend -> HubSpot / Klaviyo / Veeqo; backend -> PostgreSQL; Next.js -> backend | axios instances with env base URLs; TypeORM `DATABASE_URL`; HTTP listen | both | workspace/projects/full-services-19jul/code/backend/src/crm/hubspot.client.ts:2-15; …/fulfillment/veeqo.client.ts:2-15; …/email/klaviyo.client.ts:2-15; …/app.module.ts:23; …/main.ts:10 | project runtime | K5B-190 – K5B-203 |
| COM-112 | Project code: Egypt Amazon pipeline (generated, outside the workspace) | owner's Mac -> amazon.eg; -> Meta Graph API; launchd -> pipeline | `requests.get` HTML scrape with a browser User-Agent; `graph.facebook.com` publisher (only when approved and `META_*` creds exist); LaunchAgent at 09:00 | both | workspace/projects/daily-egypt-amazon-product-poster/data/jsons/approvals.json:91-97, 127, 242-272, 438-488 (file bodies inside the approval records) | daily 09:00 (launchd) | CH0-007, CH0-008, CH2-016 (launchd/posters); scrape and Meta channel are new (§2 N4) |

**Row count: 114** (COM-001 to COM-112, with COM-013 split into a, b, c).

---

## 2. New: not in MFI or K

| # | Finding | Evidence | Why it matters |
|---|---|---|---|
| N1 | **The brain token gate covers only `/chat*`, `/dispatch` and `/voice*`.** The desktop (COM-008) and Flutter direct mode (COM-052) send `X-Odin-Token` to every route, but `/scope/stream`, `/projects`, `/approvals`, `/operations`, `/anchor/v1/admin/*`, `/soc/*`, `/meeting/*` and `/infra/*` ignore it, even when `ODIN_ACCESS_TOKEN` is set. The main protection is that `run.sh` binds 127.0.0.1 by default; the phone runbook binds 0.0.0.0 (COM-110). K3-131 lists the prefixes but does not draw this conclusion. | SRV/app.py:56-61; SRV/run.sh:29; workspace/shared/runbooks/phone-access.md:9-10 | Exposure when the brain is reachable beyond localhost |
| N2 | **`/activity/stream` SSE has no consumer.** Every client polls `/activity` (desktop 2.5 s, Flutter 12 s) instead. | SRV/api_v2.py:781-790; no hit for `activity/stream` in any .js, .jsx, .dart or .html file | Dead push channel; polling load |
| N3 | **Desktop Anchor Connect shows the brain's in-process queue, not the online anchor.** In production, web/mobile/third-party traffic goes to the VM anchor, so the desktop view does not show it. | DSK/src/api.js:143-146; SRV/anchor.py:92-104; SRV/app.py:131-132 | Wrong source of truth for the owner |
| N4 | **Agent-generated Egypt pipeline talks to two outside services:** it scrapes amazon.eg with a browser User-Agent, and it has a Meta Graph publisher gated on approval and `META_*` credentials. CH0/CH2 record only the launchd job and the posters. | approvals.json:242-272 (bodies of `research.py`, `meta_publisher.py`) | Outside-service channels with no Odin connector or gate record |
| N5 | **Possible shared JSON queue file across two processes.** When `ANCHOR_PG_DSN` is not reachable, the brain's in-process anchor and a local `anchor_remote.py` both read and write `workspace/anchor-layer/anchor_queue.json`. Each uses only an in-process `RLock`, and two pollers (the brain thread every 5 s and the HTTP poller) can hand out the same rows. PLAUSIBLE: this only happens in dev, without Postgres. | SRV/anchor_queue.py:29-32, 113-119; SRV/store.py:36-39; SRV/anchor.py:296-320; SH/development_full_checker.sh:107 | Double processing or lost writes in dev |
| N6 | **`phase_ctl send` always registers `http://localhost:9300/cb` as the webhook, even against the online anchor.** The VM cannot reach the Mac's localhost, so requests stay `ack_pending` and retry. The script comments say this. | SH/phase_ctl.sh:47-49, 59-60 | Retry noise; webhook path untested online |
| N7 | **The desktop pending-code poll hard-codes the production anchor URL.** It ignores the editable `odin.prod.anchor` setting that other desktop code honours. | DSK/src/App.jsx:364-368 vs 470-481 | Settings change does not reach this channel |
| N8 | **IP enrichment sends observed client IPs to ip-api.com over plain HTTP.** No TLS. K5A-091 records the service, not the plaintext transport. | SRV/soc_enrich.py:39 | Data leaves unencrypted |

**New subset count: 8.**

---

## 3. Component connection map

- **Desktop app (Electron main) <-> brain:** spawns `run.sh` -> uvicorn on 127.0.0.1:8000 (COM-001). Renderer -> brain over REST, SSE, multipart and audio (COM-008 to COM-013, COM-015, COM-017, COM-018). Renderer -> main over IPC (COM-003). Main -> system browser (COM-004, COM-005).
- **Desktop app <-> anchor:** the renderer polls the anchor for login codes every 4 s (COM-014). Electron main spawns the poller that bridges the online anchor to the brain (COM-002).
- **Brain internal:** route mounts (COM-020); in-process anchor router and its 5 s poller (COM-035, COM-036); scheduler 20 s (COM-090); daemon worker threads (COM-091); notification store (COM-092); JSON store to `odin_core` lockstep (COM-032, COM-033).
- **Brain <-> LLM engines:** Claude CLI subprocess, one-shot and streaming (COM-024, COM-025), with the read-only hook (COM-026) and no MCP (COM-027). Ollama HTTP on localhost:11434 for fallback, routing and model listing (COM-028 to COM-030).
- **Poller bridge (Mac) <-> anchor (local :9100 or online):** pulls `/poll`, posts `/result`, pushes `/sync` (COM-046, COM-049, COM-050). Supervised by a shell loop or Electron (COM-051, COM-002).
- **Poller <-> brain:** command calls (COM-047) and SSE chat consumption (COM-048).
- **Anchor (remote) <-> web/mobile:** Flutter reads the mirror and pool deltas (COM-055) and writes chat and commands as queued requests (COM-053, COM-054). Login goes through `manage/*`, with the code shown on the desktop (COM-057, COM-014). Auth headers and the client gate apply (COM-040). CORS is open (COM-039).
- **Anchor <-> third parties:** POST requests and poll status (COM-095, COM-097). Webhook delivery and retries (COM-043, COM-044). The ack callback (COM-045). The local webhook receiver and sim server are test tools (COM-093, COM-094).
- **Flutter <-> brain (direct mode only):** REST with `X-Odin-Token`, `/api/v1` with `X-API-Key`, SSE (COM-052, COM-056, COM-059). Web build opens report URLs and the meeting iframe (COM-062).
- **Internet <-> VM:** nginx 443 `/odin-anchor/` -> anchor 127.0.0.1:48619; `/odin-web/` -> web 127.0.0.1:48620 (COM-075, COM-074). Mobile accepts a self-signed certificate for the VM host (COM-060).
- **Brain/Mac <-> VM:** password SSH, rsync, read-only SOC SSH and key-based SSH (COM-065 to COM-068). Azure control plane via `az`, including run-command and NSG updates (COM-069). Remote psql, Prisma and systemd over SSH (COM-073, COM-074). SOC sensor file read over SSH (COM-077). Deploy script stream (COM-071).
- **Brain <-> third-party business APIs:** HubSpot, Klaviyo, Veeqo, EasyPost (COM-081 to COM-084), with keys from `.cred` (COM-085). SOC calls OSV, CISA KEV, Feodo, ip-api and quota endpoints (COM-079, COM-080), and probes public endpoints and TLS (COM-078).
- **Voice:** clients -> `/voice/stt`, `/voice/tts`, `/meeting/*` (COM-088, COM-017). Device speech services on mobile (COM-063). Azure TTS and macOS `say` exist but are not wired (COM-086, COM-087).
- **Outside agent <-> Mac (file bridges):** `agent_term` CMD/OUT.log/STATUS, `phase_ctl` CMD/OUT.log/STATUS, the `RUN` file, `RUN_NOW`/`STOP` (COM-102 to COM-105).
- **Launch and orchestration:** dev and production checkers start every player and open browsers (COM-106 to COM-108). Readiness loops (COM-100).
- **OS notifications:** desktop Web Notifications (COM-016); mobile local notifications (COM-061). There is no remote push.
- **Project code:** full-services NestJS/Next.js clients (COM-111). Egypt pipeline with scrape, Meta and launchd (COM-112).

---

## 4. Transports that are NOT present

Grep was run across all of `/home/claude/v1src` with `main.dart.js` and `NOTICES` excluded, and across `/home/claude/chats_all.txt`.

| Transport | Result | Grep evidence |
|---|---|---|
| **UDP** (dgram, SOCK_DGRAM, udp) | **Not present** | `websocket\|ws://\|wss://\|dgram\|SOCK_DGRAM\|\budp\b…` -> 0 code hits; `UDP` in chats = 0. Every `socket` use is TCP: `socket.create_connection((host,443))` (SRV/soc_run.py:742), `socket.socket()` port probe (SRV/e2e_phase2.py:51), `socketserver.TCPServer` (e2e tests), `gethostbyname` (TST/trace_chain.py:66). |
| **WebSocket** (ws://, wss://, socket.io) | **Not present** | 0 hits in source; `websocket` in chats = 0. The only hit is the dart2js DOM type table inside the excluded `main.dart.js` (`WebSocket:A.as`), which is runtime boilerplate and not used. Live updates use SSE (COM-009, COM-010, COM-023, COM-059) and short polling. |
| **mDNS / Bonjour / zeroconf** | **Not present** | 0 hits for `bonjour\|mdns\|zeroconf\|NSBonjourServices\|NSLocalNetworkUsage`; Info.plist has only microphone and speech keys (odin_app/ios/Runner/Info.plist:69-71). |
| **Message brokers** (RabbitMQ, AMQP, Kafka, Redis, NATS, ZeroMQ, MQTT) | **Not present** | 0 hits for `rabbit\|amqp\|nats\|zmq\|mqtt`. `redis` and `kafka` appear only as glossary words (SRV/meeting_api.py:83). The queues are the anchor queue (Postgres or JSON) and JSON files. |
| **gRPC** | Not present in code | 0 code hits. |
| **WebRTC** | Not present | Only inside the excluded `main.dart.js`. |
| **Email / SMTP sending** | **Not present in Odin** | 0 hits for `smtplib\|SMTP\|sendmail\|nodemailer` in code. Email providers appear only as read-only quota probes (SRV/soc_quota.py:27-32). `smtp*` in chats (4 hits) are key names printed from the RBO app's env, not an Odin channel. `nodemailer` appears only in SOC reports about the RBO app. |
| **Remote push** (APNs, FCM, Firebase) | **Not present** | 0 hits. Notifications are local only (COM-016, COM-061). |
| **Deep links / custom URL schemes** | **Not present** | No `CFBundleURLTypes`; the Android intent-filter is only MAIN/LAUNCHER (odin_app/android/app/src/main/AndroidManifest.xml:23-26); no `setAsDefaultProtocolClient` in Electron. |
| **launchd / cron in Odin core** | **Not present** | `scheduler.py:6` "No external cron". launchd appears only in the agent-generated Egypt project (COM-112). systemd timers exist on the VM only (COM-074, COM-077). |
| **Long polling** | Not present | Every poll is a short request on a timer (COM-013, COM-044, COM-050, COM-058). |
| **Tunnels** (ngrok, cloudflared, Tailscale) | Not in code | Only in the phone-access runbook (COM-110); `ngrok` = 0 hits. |
| **Zoom API, Google Analytics API** | Not present | `zoom.us\|api.zoom` = 0; `ga4\|gtag` appears only as an intent keyword (SRV/projects.py:547). Zoom work uses transcripts only. |

**Present real-time transports:** HTTP/1.1 REST, SSE, stdout pipes (Claude CLI, deploy.sh), files (bridges, sensor, mirror), SSH/rsync, Azure ARM via `az`, and PostgreSQL wire (psycopg2 on the local socket or a DSN).


<!-- ==================== PART CAT_MODES ==================== -->

# CAT_MODES — App modes, clones and UI variants (all clients)

**Date:** 2026-10-11. Read-only pass over `/home/claude/v1src`, plus leads from MFI.md, K3, K4A, K4B (and K2A/K2B/K5A/K5B/CH* for cross-reference).
**Clients covered:** Desktop (Electron + React), Web (Flutter web, static dashboard pages, anchor-layer pages, HTML served by server routes), Mobile (Flutter iOS/Android), Anchor (landing / Manage / API).
**Secrets:** hard-coded keys and passwords are named only. No values are copied.

**Column "In MFI/K?":** the matching MFI or K ID, `partial: …` when the existing row misses the mode aspect, or `no`.

---

## 1. Full table

| ID | Mode / variant | Client(s) | How it is switched on | What changes | Evidence file:line | In MFI/K? |
|---|---|---|---|---|---|---|
| MOD-001 | Conversations (WhatsApp-clone) mode, Flutter | Web, Mobile | Top-bar toggle button (always visible), `_chat` bool | The whole content area becomes `WhatsAppMode`, showing the same scope pool as a chat app. The sidebar stays. The title becomes the active chat title | odin_app/lib/screens/shell.dart:45, :115, :545-551; whatsapp.dart:16-20 | A-126, A-135, K4A-101, K4A-111 |
| MOD-002 | Conversations mode, desktop | Desktop | Top-bar button "💬 Conversations" / "🗂 Dashboard" (`convMode`) | Replaces every view with `ConversationsView` (Company + projects + chats list, same pool). Messages are tagged "Owner · via Conversations" | desktop/src/App.jsx:20, :149-150, :165-188; Conversations.jsx:4-7, :40 | K4B-059, K4B-071 (MFI: no) |
| MOD-003 | Narrow ⋮ menu "Conversations" item (broken variant) | Web, Mobile (narrow) | ⋮ dropdown item `chat` | Shown on narrow screens, but the handler does nothing (bug) | odin_app/lib/screens/shell.dart:594-604 | K4A-105 |
| MOD-004 | Conversation-list split view inside WhatsApp mode (dead) | Web, Mobile | `_open(ctx, width>=820, …)`, never reached | Conversation list + detail at ≥820 px. The code is dead; the sidebar replaced it | odin_app/lib/screens/whatsapp.dart:48, :90, :119 | K4A-112 |
| MOD-005 | Message multi-select mode | Web, Mobile, Desktop | Long-press a bubble (Flutter) / select (desktop) | The toolbar switches to copy / forward / delete for the selected messages | whatsapp.dart:270-271, :734; desktop/src/Conversations.jsx:36, :124-148 | K4A-116, K4B-075 |
| MOD-006 | Reply-to (quoted) message state | Web, Mobile, Desktop | Tap or long-press the reply action | The composer shows a quoted message; the send carries the reply ref | whatsapp.dart:269; Conversations.jsx (reply) | A-135, K4B-073 |
| MOD-007 | Wide vs narrow shell (sidebar vs drawer) | Web, Mobile, Tablet | Platform width `MediaQuery ≥ 900` | Wide: a fixed 264 px sidebar plus inline top-bar items (ports, env chip, guide bell). Narrow: a drawer plus a ⋮ overflow menu | odin_app/lib/screens/shell.dart:150, :158, :165, :521-567, :632-633 | K4A-104 (partial: A-172) |
| MOD-008 | Dashboard wide/narrow layout | Web, Mobile, Tablet | Width `≥ 1000` | Wide: multi-column grid with the company monitor feed. Narrow: a single column; the monitor feed is hidden | odin_app/lib/screens/dashboard.dart:20, :51 | K4A-154, K4A-152 |
| MOD-009 | Project detail wide/narrow layout | Web, Mobile, Tablet | Width `≥ 1000` | Two-column vs stacked project page | odin_app/lib/screens/project_detail.dart:335, :536 | partial: K4A-135 (layout not listed) |
| MOD-010 | Bell / notifications panel width-adaptive | Web, Mobile | Screen width | Panel width and max height follow the viewport (a popover on wide screens, near full width on phones) | odin_app/lib/screens/bell.dart:56-62; notifications_panel.dart:82-90 | no |
| MOD-011 | Desktop collapsible sidebar (full / icon rail) | Desktop | Sidebar toggle, persisted `localStorage odin.nav` | Grid `264px` vs `62px` rail | desktop/src/App.jsx:19, :27, :83-84 | K4B-053 |
| MOD-012 | Desktop narrow top bar with ‹ › scroll arrows | Desktop | Automatic when the window is narrow | Top-bar actions scroll horizontally with explicit arrows | desktop/src/App.jsx:28, :142-160 | K4B-058 |
| MOD-013 | Desktop fixed window frame | Desktop | Electron BrowserWindow options | 1440×920 default, min 1080×720, macOS `hiddenInset` title bar. No responsive breakpoints in theme.css | desktop/electron/main.cjs:131-133; desktop/src/theme.css (no @media) | K4B-011 |
| MOD-014 | Static dashboard responsive grid (phone/desktop) | Web (dashboard) | CSS `@media(max-width:760px)` | Span-2 cards collapse to one column on phones | dashboard/index.html:48; dashboard/artifact.html:32 | A-112 |
| MOD-015 | Development vs Production environment flip (Flutter) | Web, Mobile | Ports & Environment sheet ("Use Development" / "Use Production"), the env chip, or the Docs "Switch" button | Selects the Local or Deployed profile: base URLs, mode, and the top-bar chip/badge colour | odin_app/lib/screens/shell.dart:557-567, :662-766; docs.dart:26, :127-142 | K4A-107, K4A-109 (MFI: no) |
| MOD-016 | Development vs Production environment flip (desktop) | Desktop | Ports & Env modal or Settings modal dropdown, persisted `localStorage odin.env`, then reload | Repoints the anchor URL (local :9100 vs online anchor domain). The EnvBadge shows DEVELOPMENT/PRODUCTION | desktop/src/App.jsx:328-345 (EnvBadge), :425-462 (PortsModal), :466-497 (SettingsModal) | K4B-063, K4B-064, K4B-065, K4B-070 (MFI: no) |
| MOD-017 | `VITE_ODIN_ENV` build-time default env | Desktop | Vite env var at build | Default for `odin.env` when localStorage is empty | desktop/src/App.jsx:329, :364, :426, :473 | no |
| MOD-018 | `ODIN_FORCE_ENV` dart-define auto-select (production / phase2) | Web, Mobile | `--dart-define=ODIN_FORCE_ENV=production\|phase2` at build/run | On launch, auto-selects the anchor profile whose URL is remote (production) or localhost (phase2) | odin_app/lib/state/app_state.dart:32-44; shells/production_full_checker.sh:112, :166; development_full_checker.sh:241, :304 | K4A-074, D-012, D-013 |
| MOD-019 | `ODIN_ANCHOR` dart-define (ignored) | Web, Mobile | `--dart-define=ODIN_ANCHOR=…` | Nothing; the Dart code never reads it (dead switch) | shells/production_full_checker.sh:112, :166; no `fromEnvironment('ODIN_ANCHOR')` in odin_app/lib | K4A-075 |
| MOD-020 | Access mode direct vs anchor | Web, Mobile | Settings → profile editor SegmentedButton `direct`/`anchor`; or picking a profile | Direct: sync `/api/v1` + SSE to the brain. Anchor: every call goes through `/anchor/v1` (async queue + mirror reads) | odin_app/lib/config.dart:11, :20; settings_screen.dart:164-176 | A-134, K4A-069 |
| MOD-021 | Connection profiles: Local (Phase 2) / Anchor local (Phase 2) / Deployed (Phase 3) | Web, Mobile | Settings → select a profile (v3 storage key) | Three preset environments. The anchor profiles have an empty `apiBase` (pure anchor) | odin_app/lib/config.dart:64-90, :103-104 | A-134, K4A-070, K4A-071, K4A-073 |
| MOD-022 | Pure-anchor mode (Phase 2 mimics Phase 3) | Web, Mobile | Pick a profile with empty apiBase + anchor mode | No backend shortcut. If the anchor is down, the app shows nothing (offline) | odin_app/lib/config.dart:70-77; app_state.dart:228 | A-138, K4A-009 |
| MOD-023 | Auto-switch to the Deployed profile when the local brain is unreachable | Web, Mobile | Automatic at boot/refresh | Flips to the remote anchor profile | odin_app/lib/state/app_state.dart (refresh path ~:440-480) | A-140, K4A-087 |
| MOD-024 | Offline mode ("You are offline / Try again") | Web, Mobile | Automatic when the anchor is unreachable in anchor mode | The dashboard is replaced by `_OfflineView`, data is cleared, no spinner | odin_app/lib/state/app_state.dart:357-361, :443; dashboard.dart:24, :115-125 | A-139, K4A-086, K4A-145 |
| MOD-025 | "offline · last synced X ago" stale indicator (computed, never shown) | Web, Mobile | `syncStale` getter | Meant to show when the desktop is closed and the mirror is stale; no screen renders it | odin_app/lib/state/app_state.dart:231-232 | K4A-016 |
| MOD-026 | Offline-drill launch (anchor OFF) | All local clients | `development_full_checker.sh` prompt "Run WITH the anchor point? [Y/n]" or `USE_ANCHOR=0/1` | n: no anchor or poller. Web/Flutter must show OFFLINE; the request page shows "anchor is offline — not received"; the landing page is not opened | shells/development_full_checker.sh:79-87, :147-155 | partial: D-011 (prompt/USE_ANCHOR not listed) |
| MOD-027 | Phase loop modes phase2 / phase3 / stop / done | All | `shells/anchor_loop.sh` typed command | Runs the dev checker (local) or the prod checker (online), or stops | shells/anchor_loop.sh:42-46, :64-70 | A-189, D-020 |
| MOD-028 | Production launch policy (no simulator; real iPhone only) | Mobile | `production_full_checker.sh` | Release build on a physical device, retried until connected. Never falls back to the simulator | shells/production_full_checker.sh:204-238 | D-015, D-018 |
| MOD-029 | `ODIN_SKIP_MOBILE` (defer mobile) | Mobile | env `ODIN_SKIP_MOBILE=1` | Phase 3 skips the iPhone install | shells/production_full_checker.sh:209-210 | no |
| MOD-030 | Release vs debug Flutter builds (web release served statically; iOS simulator debug; iPhone release) | Web, Mobile | Shell flags `--release` / `--debug` / `--simulator` | Release web avoids the debug dev-server splash hang. A debug iOS build cannot launch from the home screen (iOS 14+) | shells/development_full_checker.sh:235-241, :304; production_full_checker.sh:112, :220; docs.dart:104 | A-141, D-012-D-015 |
| MOD-031 | Production web under `/odin-web/` base-href | Web | `flutter build web --base-href /odin-web/` (phase 3) | The web app is served behind the VM reverse proxy at a sub-path | shells/production_full_checker.sh:112 | partial: A-191, K5B-088 |
| MOD-032 | Owner local web view in production run | Web | Phase 3 `flutter run -d web-server … $DART_DEFS` | A local web app on the production profile, beside the online web | shells/production_full_checker.sh:204-208 | no |
| MOD-033 | PWA standalone / portrait shell | Web (installed) | Install web app (manifest) | `display: standalone`, `orientation: portrait-primary`; title "Odin — Remote Anchor (Web)" | odin_app/web/manifest.json:4-9; odin_app/web/index.html (title) | K4A-196 (partial: A-141) |
| MOD-034 | Platform branding label web vs mobile | Web, Mobile | `kIsWeb` | Sidebar label "Remote Anchor · Web" vs "· Mobile"; login caption "Web sign in" vs "Mobile sign in" | odin_app/lib/screens/shell.dart:240; login.dart:136 | no |
| MOD-035 | Client identity header (web vs mobile) | Web, Mobile → Anchor | `kIsWeb` → `X-Odin-Client: web\|mobile` | The anchor applies per-client allow/stop and per-target login codes | odin_app/lib/api/anchor_api.dart:31, :95; server/anchor_remote.py:306-313 | K4A-002, K3-058 |
| MOD-036 | Login required per platform (web / mobile) | Web, Mobile | `/auth/config` `require_login_web` / `require_login_mobile` (direct mode) | The login gate shows or is skipped. Fail-closed if the config cannot be read | odin_app/lib/state/app_state.dart:95-104; server/auth.py:42-43 | A-149, K4A-076, K4A-077 |
| MOD-037 | Anchor-mode login (email + password + desktop code, 7-day session) | Web, Mobile | Automatic when the profile is anchor + empty apiBase | Shows the code field and "send code"; password-only login is blocked; resumes a valid 7-day token | odin_app/lib/state/app_state.dart:69-93; login.dart:57-58, :160-176; server/anchor_manage.py:30 | A-143, K4A-005, K4A-006, K4A-007, K4A-079 |
| MOD-038 | 2FA state (default OFF) + dev code | Web, Mobile (direct mode) | Account → "Two-factor authentication" switch (`twofa_enabled`) | Login returns `twofa_required`, then a code dialog. A fixed dev code is accepted (hint shown in UI) | odin_app/lib/screens/account.dart:78-84; login.dart:65-92; server/auth.py:52, :145-154 | A-144, K4A-167, K3-124, K3-125 (dev-code hint in UI: no) |
| MOD-039 | Verify-email required (default OFF) | Web, Mobile | Account switch `verify_email_enabled` | An email verification step; uses the same dev code | odin_app/lib/screens/account.dart:86-91; server/auth.py:19, :188-192 | A-145 |
| MOD-040 | Face ID first-access / resume lock | Mobile only | Account switch `faceid_first_access` (default true) + `!kIsWeb` | With a saved session the app opens in `pendingBiometric` state ("Unlock with Face ID"). Unavailable → password hint | odin_app/lib/state/app_state.dart:114-119; login.dart:33, :138-145, :193-194; account.dart:93-98 | A-147, K4A-078, K4A-191 |
| MOD-041 | Desktop open (no login) | Desktop | `desktop_open: true` in auth config | The desktop needs no login; the token setting is optional | server/auth.py:47; desktop/src/App.jsx:494 | A-148 |
| MOD-042 | Boot / splash state (auth unresolved) | Web, Mobile | Automatic until `authResolved` | A spinner, then Shell or LoginScreen (`gateOpen`) | odin_app/lib/main.dart:66-75 | K4A-098 |
| MOD-043 | Shared-secret token gate | Web (mobile.html), Desktop, any brain caller | env `ODIN_ACCESS_TOKEN` on the brain | Brain routes require `X-Odin-Token`/`?token=`. mobile.html reveals its token row on 401 | server/app.py:50-54; dashboard/mobile.html:62, :98, :132; desktop/src/App.jsx:494 | A-151, K4B-167 |
| MOD-044 | Anchor Manage (admin) vs public landing | Anchor (browser) | Route `/manage` vs `/` (Accept: text/html); "Manage" button | Landing: online status. Manage: login card → protected panel (requests CRUD + allow toggles) | server/anchor_remote.py:83-126, :128-230, :326-330 | A-154, A-187, K3-054, K3-055 |
| MOD-045 | Manage "remember this device & browser" (skip code) | Anchor (browser) | Checkbox at login, `device_id` | The next login hides the code row | server/anchor_remote.py:162-163, :192-194 (template), anchor_manage.py:6 | K3-048 |
| MOD-046 | Allow / stop the web app and the mobile app | Anchor → Web, Mobile | Manage panel switches `allow_mobile` / `allow_web` | The anchor rejects reads from the stopped client type; third-party intake is unaffected | server/anchor_remote.py:176-177, :220-221, :306-313, :473-474, :484; anchor_manage.py:12, :64-74 | A-154, K3-045 |
| MOD-047 | "Connecting with Anchor" blinking indicator | Desktop | Automatic: polls `/manage/pending-code` (dev → local anchor, prod → online) | Blinks while a code is pending; a dialog shows the email, password and code to copy (hard-coded values; see K4B-069) | desktop/src/App.jsx:347-385 | A-124, K4B-068, K4B-069 |
| MOD-048 | Owner-only admin surfaces (Account security toggles, Approval center, Audit) | Web, Mobile, Desktop | Signed-in owner; single-owner system (no role-based views) | Security flags, approvals and audit only appear inside the authenticated shell | odin_app/lib/screens/account.dart:76-98; shell.dart:97-102 | partial: A-149, K4A-169, K4A-176 (no multi-role variant exists) |
| MOD-049 | Voice replies (TTS) on/off, Flutter | Web, Mobile | Chat header 🔊/🔇 button (`_speak`) | Assistant replies are spoken after streaming | odin_app/lib/screens/chat_screen.dart:122, :288, :514-517; whatsapp.dart:267, :444-457, :666-671 | K4A-124, A-170 |
| MOD-050 | Voice on/off (mute), desktop | Desktop | Top-bar "🔊 Voice on / 🔇 Voice off", `localStorage odin.mute` | Mutes and stops all TTS | desktop/src/App.jsx:145-148; api.js:210-211 | K4B-046, A-166 |
| MOD-051 | Autospeak per chat panel (desktop) | Desktop | `autospeak` prop on ChatPanel | Speaks the final reply in the chosen language | desktop/src/ChatPanel.jsx:7, :181 | K4B-092 |
| MOD-052 | Dictation language EN / Arabic (Flutter) | Web, Mobile | Chat composer toggle "EN"/"ع" (`_sttLocale en_US / ar_SA`) | STT locale switches | odin_app/lib/screens/chat_screen.dart:32, :443, :634-638; whatsapp.dart:172, :541, :760-764 | K4A-125, A-170 |
| MOD-053 | Reply/voice language EN / AR (desktop chat) | Desktop | Chat header EN / ع segmented control (`lng`) | Stream `lang` param, TTS voice, RTL composer + Arabic placeholder | desktop/src/ChatPanel.jsx:8, :427-428, :509-510 | A-165, K4B-077 |
| MOD-054 | EN/AR toggle on HTML pages | Web (dashboard index, console, mobile) | EN / AR buttons | STT `ar-EG`/`en-US`, TTS `lang=ar` | dashboard/index.html:81, :247-249; console.html:101-102, :161; mobile.html:88-89, :123 | A-114, K4B-164, K4B-165, K4B-167 |
| MOD-055 | Arabic speed per language (desktop) | Desktop | `localStorage odin.speed.ar / odin.speed.en` (no UI control) | TTS speed; AR default 1.15 | desktop/src/api.js:217 | partial: A-161 (hidden localStorage knob: no) |
| MOD-056 | RTL/LTR auto-direction | Desktop, Flutter meeting sheet, meeting_monitor.html | Automatic per message (Arabic range) or per report language | Bubbles and reports are right-aligned RTL for Arabic | desktop/src/ChatPanel.jsx:454-457; odin_app/lib/screens/meeting_sheet.dart:179-180; dashboard/meeting_monitor.html:37 | A-119, K4B-095 |
| MOD-057 | Web vs native voice engine (Flutter) | Web vs Mobile | `kIsWeb` + conditional import `speech_web` | Web uses the browser Web Speech API; mobile uses flutter_tts with per-language rate | odin_app/lib/services/voice.dart:6, :45-58, :61, :145 | K4A-186, K4A-189 |
| MOD-058 | Dictation mic mode (toggle, not push-to-talk) | Desktop, Web, Mobile | Mic button toggles start/stop (desktop: Whisper fast partials + final pass) | No hold-to-talk anywhere. The dashboard labels it "Hold-free record" | desktop/src/ChatPanel.jsx (toggleMic ~:300); whatsapp.dart:524-535; dashboard/index.html:80 | A-164, K4B-089 (no PTT mode exists) |
| MOD-059 | Voice notes vs dictation (WhatsApp mode) | Web, Mobile | Record-voice-note vs mic-dictation actions | A voice note posts audio to the pool with a server transcript; dictation fills the text box | odin_app/lib/screens/whatsapp.dart:173, :416, :524 | A-135, K3-101 |
| MOD-060 | Backend voice on/off (`USE_VOICE`) | Desktop, Web (all voice) | env `USE_VOICE` (default 1) via run.sh / Electron | Loads or skips the STT/TTS stack | server/run.sh:23, :49; desktop/electron/main.cjs:59 | partial: A-156 (flag not listed) |
| MOD-061 | Live meeting mode (in-app sheet vs web iframe) | Mobile vs Web, Desktop | 🎙 button when the project owns the meeting asset; platform decides the surface | Mobile: native sheet with sensitivity + chunks. Web: served `meeting_monitor.html`. Desktop: popup | odin_app/lib/screens/chat_screen.dart:502-509; meeting_sheet.dart; desktop/src/ChatPanel.jsx:420-423 | A-173, K4A-123, K4A-163, K4B-097 |
| MOD-062 | Meeting report language view EN/AR | Web (meeting_monitor.html), Mobile | Export language select / auto-detected language | Report is RTL for Arabic; MD/Word export language | dashboard/meeting_monitor.html:64, :97, :193, :233-238 | A-174, K4B-169 |
| MOD-063 | Dark-only theme (no light theme anywhere) | Desktop, Web, Mobile, Anchor pages | Fixed | Flutter `Brightness.dark` only; desktop `:root` dark tokens only; dashboard/anchor pages dark CSS. No theme switch or `prefers-color-scheme` | odin_app/lib/theme.dart:6-7, :106; desktop/src/theme.css:2; anchor_remote.py:100 (inline dark CSS) | K4B-162, K4A-182 (MFI: no) |
| MOD-064 | Project kind: build (new) vs existing (read-only sources) | Desktop | New-project dialog first step (`kind` new/existing) | Existing: multi-folder picker, READ-ONLY seed context, `mode: existing`, `sources`. New: single create location | desktop/src/views.jsx:1448, :1502-1503, :1530, :1594-1595, :1762, :1917 | K4B-135, K4B-136, K2A-008 |
| MOD-065 | Project mode `deploy` (DevOps deploy of an existing app) via DeployProjectModal (unmounted) | Desktop (hidden) | `DeployProjectModal` exported but never rendered; server honours `mode == "deploy"` | Deploy-only project with update/replace choice; server sets `deploy_mode` | desktop/src/views.jsx:1987-2000; server/api_v2.py:1936; projects.py:689 | K4B-147, K2A-148 |
| MOD-066 | Simple NewProjectModal (unmounted legacy variant) | Desktop (hidden) | Exported, never rendered | Name/desc/path-only project create | desktop/src/views.jsx:2032-2040 | K4B-148 |
| MOD-067 | DevOps-only team / run | All (server-driven) | Brief or goal phrase ("only devops", "devops only", "no other agent"…) | The team becomes `[DevOps]` only; QA is disabled for the run; the status says "DevOps-only run — no QA" | server/projects.py:470-474; api_v2.py:1944-1950, :2080 | K2A-111, K2B-034, B-125 |
| MOD-068 | Direct (single-member) request mode vs orchestrate | All (server-driven) | `intent.classify_request` → `mode: direct` | One member (`_direct_member`) handles the scoped ask; no team fan-out; deploy can be forbidden | server/intent.py:70-77, :120; api_v2.py:2016-2025, :3035 | K2A-117, K2A-175, K2B-177 |
| MOD-069 | Read-only (propose-first) vs write-enabled agent runs | All (server-driven); shown in chat as proposals/approvals | Project `auto_approve` (desktop "Pre-approve changes" toggle) or pre-authorization phrases | Read-only: Write/Edit removed + PreToolUse hook; proposals become approvals. Authorized: "agents execute directly (write-enabled)" | server/claude_cli.py:59-74; api_v2.py:1956-1964, :3460-3467; readonly_hook.py:2; desktop/src/views.jsx:1454, :1919-1931 | K2A-064, K2A-071, K2A-112, K2A-194, K2B-097, K4B-146 |
| MOD-070 | Agent `mode` normal \| theoretical (+ nature technical \| operational) | Desktop, Web (agent roster grouping) | Agent registration field; operational agents default `normal` | Nature drives roster grouping and resources. `theoretical` is stored but never read by any code path (label only) | server/agents_registry.py:205-207; projects.py:53-58; desktop/src/views.jsx:387-391, :1567 | partial: K2B-051, K5A-177 (theoretical unused: no) |
| MOD-071 | Project cadence once / recurring / periodical (scheduled) | Desktop, Web, Mobile | New-project Cadence dropdown | Periodical builds a schedule (daily/interval/calendar) with requireApproval; recurring adds a ▶ Run-now | odin_app/lib/screens/new_project.dart:129-139; desktop/src/views.jsx:1469-1470, :1598-1599, :1713-1714 | K2B-048, K4B-144, K1-128 |
| MOD-072 | Autonomous scheduled / Run-now execution | Desktop, Web, Mobile | Scheduler fire or ▶ Run now | Run marked "Scheduled autonomous run — approval already granted"; executes local/read-only directly; VM changes still gated | server/scheduler.py:300-310, :375-388; chat_screen.dart:41; whatsapp.dart:181 | A-226, K4A-120, K4B-082 |
| MOD-073 | Periodic approval gate (requireApproval) | Desktop, Web, Mobile | Per-task requireApproval checkbox | A due task waits for approve/skip (desktop watcher popup, Flutter schedule card) | desktop/src/views.jsx:1405, :2694; project_detail.dart:309, :517-521 | K2A-059, K4B-157 |
| MOD-074 | Ollama offline fallback brain / engine selector | All | env `ODIN_ENGINE` (default claude); automatic when the Claude CLI is unavailable | System status shows "local LLM" vs "Claude CLI"; canned "Plan (offline)" | server/app.py:235, :332, :443; api_v2.py:912; projects.py:1487 | A-002, K2B-065, K2B-115 |
| MOD-075 | Dispatcher vs raw Ollama chat | Web (dashboard/console), Mobile HTML | env `ODIN_USE_DISPATCHER` (default 1) | Routes chat through the specialist dispatcher + approval gate, or raw model | server/app.py:199-200 | partial: B-005 (flag not listed) |
| MOD-076 | Electron dev mode (`ODIN_DEV`) | Desktop | env `ODIN_DEV=1` | Loads the Vite dev server :5173 with DevTools docked at the bottom; else the packaged `dist/index.html` | desktop/electron/main.cjs:14, :141-146 | K4B-001, A-206, D-001 |
| MOD-077 | Packaged .dmg production bridge (poller always on) | Desktop | Always at app ready (also in dev) | Starts the backend + online-anchor poller with self-heal; env `ODIN_ANCHOR`, `ODIN_PORT`, `ODIN_ROOT` override | desktop/electron/main.cjs:15-24, :207-217 | K4B-002, K4B-007, K4B-008, A-186 |
| MOD-078 | Desktop React served without Electron (browser variant) | Desktop UI in a browser | Opening the Vite/dist page outside Electron (`window.odin` absent) | Native file/folder pickers and the request-page button silently disappear | desktop/electron/preload.cjs:4-10 (`isDesktop`); desktop/src/views.jsx:888, :1514, :1530; ChatPanel.jsx:495-496 | no |
| MOD-079 | Single-instance desktop | Desktop | `requestSingleInstanceLock` | A second launch quits | desktop/electron/main.cjs:204 | K4B-017 |
| MOD-080 | Request page (third-party simulator) Dev / Prod env selector | Web (anchor_sim.html :9104) | `?env=dev\|prod`, `<select id=env>`, or presence of `window.ODIN_PROD` (anchor_prod.js) | Switches the brain/anchor/webhook URLs; prod is the forced default when ODIN_PROD exists; the dev checker deletes anchor_prod.js | workspace/anchor-layer/anchor_sim.html:53-56, :114-116, :147-154, :339-347; shells/development_full_checker.sh:27-28; production_full_checker.sh:149 | K3-167, K3-170, D-039 |
| MOD-081 | Request page "hide environment variables" | Web (anchor_sim.html) | ⚙ toggle button | Collapses the config block | workspace/anchor-layer/anchor_sim.html:50, :142 | K3-176 |
| MOD-082 | Desktop one-click Request page opened in prod mode | Desktop | Docs tab button → IPC `start-request-page` | Starts a static server :9104 and opens `anchor_sim.html?env=prod` | desktop/electron/main.cjs:169-171; preload.cjs:9; views.jsx:2398-2445 | K4B-015, K4B-156 |
| MOD-083 | Durable sim server (SQLite) vs static request page | Web (anchor_sim) | `sim_server.py` (phase 2) vs `python -m http.server` (phase 3) | Persistent request log + Clear all vs no persistence | server/sim_server.py:3-19, :239; shells/development_full_checker.sh:145; production_full_checker.sh:186 | A-196, A-197, D-035 |
| MOD-084 | Legacy third-party simulator page | Web | Open `third_party_sim.html` | Older single-form third-party sender | workspace/anchor-layer/third_party_sim.html:6 | A-195, K3-177 |
| MOD-085 | CLI third-party simulator | CLI | `python3 server/third_party.py --project … --prompt …` | Sends one external request to the anchor | server/third_party.py:3-8 | A-195 |
| MOD-086 | Anchor-layer index redirect (landing for :9104) | Web | Open `http://localhost:9104/` | Meta-refresh to anchor_sim.html | workspace/anchor-layer/index.html:1-7 | no |
| MOD-087 | Webhook receiver viewer page | Web | Open the webhook receiver root | HTML viewer listing callbacks per project | server/webhook_receiver.py:55, :78 | A-198, K3-114 |
| MOD-088 | Anchor fast/single-call answer tiers | Anchor → all clients | env `ODIN_ANCHOR_FAST` (default 1), `ODIN_ANCHOR_SINGLE` (default 1) | Tier-1 fast read-only answer / tier-2 single grounded call instead of a full CTO→team run | server/anchor.py:221-224, :253 | K3-015, K3-018 |
| MOD-089 | Anchor with or without in-process poller | Anchor | env `ODIN_ANCHOR_NO_POLLER=1` | Disables the embedded poller (external poller used) | server/anchor.py:302 | K3-021 |
| MOD-090 | Anchor storage PostgreSQL vs JSON | Anchor | env `ANCHOR_PG_DSN` set and reachable | Production PG store vs local JSON files | server/anchor_queue.py:5, :85 | A-192 |
| MOD-091 | Brain root serves the static dashboard | Web | `GET /` on :8000 | dashboard/ mounted with html=True | server/app.py:5, :461 | D-041, A-112 |
| MOD-092 | Static dashboard live vs built-in snapshot (offline) | Web (dashboard/index.html) | Automatic: state files unreachable | Shows "Showing built-in snapshot" with embedded fallback data | dashboard/index.html:139, :213, :227 | A-112, K4B-163 |
| MOD-093 | Artifact snapshot page (static, frozen data) | Web | Open `dashboard/artifact.html` | Fully hard-coded snapshot dashboard | dashboard/artifact.html:6, :56-60 | K4B-170, A-112 |
| MOD-094 | Cockpit console page | Web | Open `/console.html` | Streaming chat cockpit with EN/AR + browser STT | dashboard/console.html:6, :95-161 | A-109, K4B-165 |
| MOD-095 | Mobile HTML cockpit (legacy, token) | Web (phone browser) | Open `/mobile.html` | Phone-sized chat + voice; token row | dashboard/mobile.html:6, :62 | A-240, K4B-167 |
| MOD-096 | Audit/Observer HTML page watching vs stopped | Web | Audit config enabled/silence | Pill shows "watching · gap Nm" or "stopped" | dashboard/audit.html:33, :82 | A-104, K4B-168 |
| MOD-097 | Browser voice test page | Web (testing) | Open `workspace/shared/testing/voice_test.html` | Standalone browser voice self-test | workspace/shared/testing/voice_test.html (title) | partial: A-169 |
| MOD-098 | "How it connects" pipeline doc page | Web (docs) | Open `workspace/docs/odin_pipeline.html` | Static explainer page | workspace/docs/odin_pipeline.html (title) | no |
| MOD-099 | Deployed web copy (external-arms) | Web (VM) | Phase 3 deploy copy | Byte copy of the Flutter web shell served online | workspace/projects/odin-external-arms/deploy/web/index.html | K5B-073, A-191 |
| MOD-100 | Help & Testing Guide live env banner | Web, Mobile | Docs screen; reflects the active profile | Banner "Active now: PRODUCTION (online anchor) / DEVELOPMENT (local)" + Switch | odin_app/lib/screens/docs.dart:26, :45-50, :127-142 | K4A-162 |
| MOD-101 | TLS self-signed override (mobile/desktop only) | Mobile (not web) | Conditional import `dart.library.io` | Trusts the VM IP / anchor domain cert only on native | odin_app/lib/services/cert_override.dart:4; cert_override_io.dart:1-12; main.dart:~35 | K4A-097 |
| MOD-102 | Platform service stubs (web vs io) | Web vs Mobile | Conditional imports | Biometric, local notifications, SSE (web EventSource vs io), record path, web_open: real on one platform, stub on the other | odin_app/lib/services/biometric.dart:1; notifications.dart:5; sse.dart:1; recpath.dart:1; chat_screen.dart:8; whatsapp.dart:13 | K4A-190, K4A-191, K4A-192 (as a set: no) |
| MOD-103 | Local notifications vs in-app banner | Mobile vs Web | Platform (conditional import) | Mobile: OS notification. Web: banner bar | odin_app/lib/services/notifications.dart:5; shell.dart:189 | A-133, K4A-110 |
| MOD-104 | Debug banner hidden + crash-proof zone | Web, Mobile | Always | `debugShowCheckedModeBanner:false`; `runZonedGuarded` + error logging | odin_app/lib/main.dart:39, :53 | K4A-096 |
| MOD-105 | Run-state banner WORKING / STUCK / FINISHED | Desktop, Web, Mobile | Automatic from run status | Chat header banner state | desktop ChatPanel (run-state); odin_app chat_screen (run banner) | K4A-132, K4B-079, K4B-080 |
| MOD-106 | SOC monitor-only vs auto-remediation | Desktop, Web (SOC views/results) | `SOC_AUTO_REMEDIATION_ENABLED` (forced default False) + 22 `SOC_*` flags | Monitor-and-report only; remediation disabled | server/soc_run.py:42, :47; soc_blueprint.py:87 | A-227, K5A-003, K5A-004 |
| MOD-107 | Server reload dev mode | Server (affects all clients) | env `ODIN_RELOAD=1` | uvicorn reload on (opt-in; scoped watch) | server/run.sh:49 | A-010 |
| MOD-108 | Cache disabled baseline mode | Server (timing) | env `ODIN_DISABLE_CACHE=1` | Hides the cached-modules pool | server/cached_modules.py:20; run_timer.py:37 | K1-107 |
| MOD-109 | Test-only fast gate model | Server | env `ODIN_GATE_MODEL` | Cheaper model for QA gate / CTO review | server/api_v2.py (gate) | K2A-132 |
| MOD-110 | Hard-to-guess online ports (test) | Web, Anchor (online tests) | env `ODIN_WEB_PORT` (48620), `ODIN_ANCHOR_PORT` (48619), `ODIN_ANCHOR_NGINX=1`, `ODIN_TLS_CERT/KEY` | Alternative online exposure profile for testing | workspace/shared/testing/test_web_online.py:22, :40; test_anchor_online.py:10, :23, :82-83 | A-205 (partial) |

**Row count, section 1: 110.**

---

## 2. New: not in MFI or any K file

| ID | Mode / variant | Why it is new |
|---|---|---|
| MOD-010 | Width-adaptive bell / notifications panel | No MFI or K row describes its responsive sizing |
| MOD-017 | `VITE_ODIN_ENV` build-time env default (desktop) | K4B lists the env flip but not this build variable |
| MOD-034 | Platform branding labels ("Remote Anchor · Web/Mobile", "Web/Mobile sign in") | Not listed |
| MOD-055 | Hidden `odin.speed.ar/en` localStorage TTS-speed knob (desktop) | A-161 covers Arabic speed, but not this hidden per-language override |
| MOD-060 | `USE_VOICE` backend voice on/off | Voice rows exist; the switch itself is not listed |
| MOD-070 | Agent `mode: theoretical` stored but never consumed | K2B-051 / K5A-177 mention the mode; none notes that "theoretical" is dead |
| MOD-075 | `ODIN_USE_DISPATCHER` dispatcher vs raw-Ollama switch | B-005 covers the dispatcher, not the off-switch |
| MOD-078 | Desktop React UI running in a plain browser (no `window.odin`) | Not listed; pickers silently vanish |
| MOD-086 | anchor-layer `index.html` redirect landing for :9104 | Not listed |
| MOD-098 | `odin_pipeline.html` "How it connects" docs page | Not listed |
| MOD-102 | Web-vs-io conditional-import stub set, as one platform-variant mechanism | The parts exist in K4A; the variant set is not |
| MOD-032 | Owner local web view on the production profile during Phase 3 | Not listed |
| MOD-029 | `ODIN_SKIP_MOBILE` defer-mobile flag | Not listed |

Partly new (the existing row misses the mode aspect): MOD-009, MOD-026 (USE_ANCHOR prompt / offline drill), MOD-031 (`/odin-web/` base-href), MOD-038 (dev 2FA code hint shown in the UI), MOD-048 (no multi-role views; owner-only), MOD-058 (there is no push-to-talk mode in any client), MOD-063 (dark-only: MFI has no theme row), MOD-097, MOD-110.

Also new to MFI (they exist only in K files): MOD-002, MOD-015, MOD-016, MOD-063, MOD-064, MOD-069, MOD-076, MOD-080.

**Count: 13 fully new, 9 partly new, 8 in K files only.**

---

## 3. Per-client summary

**Desktop (Electron + React)**
- **Views:** Dashboard ⇄ Conversations (MOD-002).
- **Layout:** collapsible sidebar (MOD-011), scroll-arrow top bar (MOD-012), fixed min-size frame with no CSS breakpoints (MOD-013).
- **Environment:** Development/Production flip via Ports & Env / Settings / EnvBadge (MOD-016); `VITE_ODIN_ENV` default (MOD-017).
- **Launch:** `ODIN_DEV` dev server + DevTools vs packaged dist (MOD-076); the poller bridge always on (MOD-077); single instance (MOD-079); browser-without-Electron variant (MOD-078).
- **Login and anchor:** no login (MOD-041); "Connecting with Anchor" code indicator (MOD-047).
- **Voice:** on/off (MOD-050), autospeak (MOD-051), EN/ع reply language + RTL (MOD-053, MOD-056), hidden speed knob (MOD-055), toggle dictation with no PTT (MOD-058).
- **Projects:** new/existing project kinds (MOD-064); hidden Deploy and simple New-project modals (MOD-065, MOD-066); Pre-approve (write-enabled) toggle (MOD-069); cadence and periodic gate (MOD-071, MOD-073).
- **Request page:** one-click request page in prod mode (MOD-082).
- **Theme:** dark only (MOD-063).

**Web (Flutter web + HTML pages)**
- **Flutter web views and layout:** normal ⇄ WhatsApp-clone Conversations (MOD-001; MOD-003 broken narrow item, MOD-004 dead split view); wide/narrow shell, dashboard and project layouts (MOD-007 to MOD-010).
- **Flutter web environment:** Dev/Prod flip, profiles, direct/anchor, pure-anchor, auto-switch (MOD-015, MOD-018 to MOD-023); offline view (MOD-024).
- **Flutter web login:** web login policy, anchor 3-factor login, 2FA, verify email (MOD-036 to MOD-039).
- **Flutter web voice:** TTS on/off and EN/ع dictation through the Web Speech API (MOD-049, MOD-052, MOD-057).
- **Flutter web builds:** PWA standalone (MOD-033); release static build and `/odin-web/` base-href (MOD-030, MOD-031).
- **HTML pages:** the brain root dashboard, live vs snapshot (MOD-091, MOD-092); artifact snapshot (MOD-093); console (MOD-094); mobile.html with token gate (MOD-095, MOD-043); audit watching/stopped (MOD-096); meeting monitor EN/AR + RTL (MOD-062); voice test (MOD-097); pipeline doc (MOD-098).
- **Anchor-layer pages:** anchor_sim Dev/Prod (MOD-080, MOD-081); durable vs static sim (MOD-083); legacy third-party sim (MOD-084); :9104 redirect (MOD-086); webhook viewer (MOD-087).
- **Theme:** dark only (MOD-063).

**Mobile (Flutter iOS/Android)**
- **Shared with Flutter web:** the same views, environment and login modes, and the narrow drawer layout by default (MOD-007, MOD-008).
- **Mobile only:** Face ID first-access lock (MOD-040); native TTS/STT with per-language rate (MOD-057); native meeting sheet (MOD-061); OS local notifications (MOD-103); self-signed TLS override (MOD-101); conditional-import real services (MOD-102).
- **Builds:** debug simulator (phase 2) vs release iPhone, never the simulator in production (MOD-028, MOD-030); `ODIN_SKIP_MOBILE` (MOD-029); `ODIN_FORCE_ENV` auto-select (MOD-018); `ODIN_ANCHOR` define ignored (MOD-019).
- **Tablet:** no dedicated tablet layout. Tablets get the wide or narrow variants purely by width breakpoints (900 / 1000 / 820).

**Anchor (server + browser pages)**
- **Pages:** public landing vs protected Manage (MOD-044); remember-device (MOD-045); allow/stop web and mobile clients (MOD-046).
- **Client handling:** per-client `X-Odin-Client` gating and per-target codes (MOD-035).
- **Answer modes:** fast/single answer tiers (MOD-088); with or without the in-process poller (MOD-089).
- **Storage:** PostgreSQL vs JSON (MOD-090).
- **Online test profile:** hard-to-guess ports + nginx/TLS (MOD-110).

**Cross-client / server-driven behaviour modes**
- **Agent runs:** direct single-member vs orchestrate (MOD-068); DevOps-only (MOD-067); read-only propose-first vs write-enabled (MOD-069); agent normal/theoretical (theoretical dead) (MOD-070).
- **Scheduling:** autonomous scheduled / Run-now (MOD-072); periodic approval gate (MOD-073).
- **Engine:** Claude vs Ollama offline engine (MOD-074); dispatcher on/off (MOD-075); voice backend on/off (MOD-060).
- **SOC:** monitor-only (MOD-106).
- **Dev and test flags:** reload, cache-off and gate-model (MOD-107 to MOD-109); phase loop and offline drill (MOD-026, MOD-027).

**Explicitly absent (checked):**
- No light theme or theme toggle.
- No push-to-talk mode.
- No kiosk mode.
- No demo mode beyond the simulators.
- No tablet-specific layout.
- No multi-role admin/user split (single owner; the only admin area is the anchor Manage page).
