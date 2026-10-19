# REQUIREMENTS_TRACKER: Odin v2 program

**Updated:** 2026-10-11 (order-of-work update). Fix #1 accepted. Fix #2 approved, starting once you confirm the order of work. This file is updated at every phase gate.

**Rule (yours):** no phase is approved while an item for that phase is still open, unless you say so.

**Statuses:**
- **open**
- **in progress**
- **done:** carried out, not tested by a run.
- **verified:** proven by a run.
- **⚠ needs owner:** waiting on your decision.

**Source abbreviations:**
- *V-prompt:* the verification prompt (2026-10-10).
- *Plan:* the v2 consolidation plan (2026-10-11).
- *Gate0:* your Phase 0 approval.
- *Tracker:* your tracker prompt.
- *Rpt:* my reports (`odin_scenario_verification.md` = SV; `MASTER_FEATURE_INVENTORY.md` = MFI).

## A. Program rules (apply in every phase)

| ID | Requirement | Source | Phase | Status | Evidence |
|---|---|---|---|---|---|
| R-01 | Stop at every phase gate: short summary plus a report file, then wait for written approval | Plan | all | in progress | Gates 0 and 1 held |
| R-02 | Never modify, move or delete Odin-Orchestrator (v1) | Plan, V-prompt | all | verified | Checksums and git status vs baseline (SV §6); re-checked at this gate (below) |
| R-03 | Never modify Odin-Isolated, Odin-Consolidated or research folders except where a phase says so; delete only in Phase 9 | Plan | all | verified | Isolated checksums identical |
| R-04 | Never touch production PostgreSQL; private throwaway databases from read-only dumps only | Plan | 0–7 | verified | Private clusters 25432/25433 (SV) |
| R-05 | No cloud, VM, SSH, rsync, Azure or git push before Phase 8; record VM steps as "would run" | Plan | 0–7 | in progress | Shims active in Consolidated |
| R-06 | **Permanent block on agent web requests to the VM's public address, for every process and agent** | Tracker | 3, 5 | open | Exists only in Consolidated (curl/nc/wget shims). Must be made permanent in v2 for all agents, not only via `PATH` shims. |
| R-07 | Dummy credentials only; never print secrets | Plan | all | verified | No values in any report (secret scan on MFI) |
| R-08 | Judge by what the system does when triggered; semantic decisions may live in prompts, middleware or the database; never call a feature missing without a failed run | V-prompt, Plan | all | in progress | Applied in SV and MFI (§0.3) |
| R-09 | Hidden or unlisted features are required unless you approve removing them | Plan | all | in progress | MFI §0.2 |
| R-10 | ~~Cost estimate before every LLM batch; never exceed the approved cap~~ **Superseded 2026-10-11 by R-ZC.** Dollar figures are kept only as "reported usage, not charged" | Plan, owner | 2–7 | superseded by R-ZC | Reported usage so far: see the latest status block (not charged) |
| R-ZC | **HARD RULE — ZERO EXTRA COST (owner, 2026-10-11).** (1) Not a single extra cent: every model call runs under the owner's existing Claude PLAN login, never a paid API key or any other paid service. (2) Before every run, confirm the Claude CLI auth method (no key printed); if anything uses an API key or a paid endpoint, STOP and tell the owner; nothing runs until he decides. (3) Dollar figures are MEASUREMENT ONLY (paper cost metrics), labelled "reported usage, not charged"; no "budget", no dollar cap logic; instead watch the plan's usage limits and tell the owner when they are near. (4) Phase 4: download Qwen free and train locally on the M4; examples come from Odin's real logs, the owner's reviewed labels and runs under the plan; no paid service of any kind. (5) If a step can only be done with a paid service, stop and ask first. **Allowed sources, ONLY:** (A) free and local — free models (e.g. Qwen 16-bit), local training on the M4, Ollama, scripts, tests, code work on the Mac; (B) the current Claude plan — agent runs and example generation through Claude Code on the existing plan login. **Not allowed:** per-use API keys, paid cloud services, paid models, new subscriptions — such a task STOPS for the owner. Status block shows "plan usage", not a budget. **Confirmed by the owner 2026-10-11 as implemented.** | Owner 2026-10-11 | all | **in force** — verified 2026-10-11: CLI 2.1.185 logged in with the Claude Max plan (oauth, billing = subscription), NO API key in env/config/settings, NO apiKeyHelper, paid extra usage DISABLED. Code guard + test Z1–Z4 | `g8b_test.py` |
| R-11 | Git tag at the start and end of each phase in the working folder; CHANGELOG entry with reason and approval date for every change | Plan | 3–9 | open | No working folder in Phases 0–1 |
| R-12 | Tracker updated at every gate, showing changed and still-open items | Tracker | all | in progress | This file |
| R-13 | Prefer extending existing mechanisms over new parallel ones | V-prompt, Plan | 3, 5 | open | — |

## B. Phases

| ID | Requirement | Source | Phase | Status | Evidence |
|---|---|---|---|---|---|
| P0-1 | Folder map: purpose, last commit, size, unique contents, difference from the original | Plan | 0 | verified | `PHASE0_FOLDER_MAP.md`, approved 2026-10-11 |
| P1-1 | Read all docs, history, agents, middleware, audit, Anchor, live sync, SOC, test harness and chats | Plan | 1 | done | MFI, from 8 bundles. **Chats** were covered through the decision log and history, not each chat JSON one by one (see P1-5). |
| P1-2 | Read all build, run and release machinery (desktop dev/build/DMG, Flutter web, mobile/iPhone, Anchor, React client, env and phase scripts, third-party test, certified deployment) | Plan | 1 | done | MFI part D §1–4; part B §2 |
| P1-3 | Read the paper additions and the verification findings, including retractions | Plan | 1 | done | MFI part D §5; §0.1 |
| P1-4 | Produce `MASTER_FEATURE_INVENTORY.md`: location, how run, status per item | Plan | 1 | done | About 2,650 rows: 575 from docs, about 1,380 from code with file:line, 114 from chats |
| P1-6 | Build the inventory from the ACTUAL files read in full: structuring rules, database schema, middleware, audit and all consistency rules, sync features, UDP, live web/mobile/desktop sync, clone projects, each confirmed by file and line | Gate1 | 1 | done | MFI §0.5. **UDP: NOT FOUND anywhere in v1. Clone projects: only the WhatsApp-clone mode found.** See F-12 and F-13. |
| P1-8 | Treat UDP and clone as examples: list the full categories (all communication and connection mechanisms; all app modes, clones and UI variants) | Gate1b | 1 | done | MFI §0.7: 114 mechanisms (no UDP, no WebSocket); 110 modes, 13 new |
| P1-7 | "Features" means every category at every level; examples are only instances; enumerate the full set | Gate1 | 1, 5, 7 | done (Phase 1) | MFI §0.4 lists all 12 categories |
| P5-6 | **v2 preserves ALL features. Compare v1 and v2 behaviour per feature. "Preserved" only when a run proves it. Flag anything added, changed, stopped or removed.** | Gate1 | 5, 6, 7 | open | Rule recorded; a v1-vs-v2 column will be added in Phase 5 |
| P1-5 | Read ALL chat files, read-only, as the final gap check; add what is found | Plan, Gate1 | 1 | done | All 357 chat files (4,049 messages) read in full. 114 rows added (MFI parts CH0–CH5) and 42 contradictions listed. |
| P2-1 | Scenario verification (S1–S6 ×3) | V-prompt | 2 | verified | SV |
| P3-1 | Apply only approved G-items, one at a time, in your priority order, with your approval for each; after each, run regression, end-to-end tests, the affected scenario and the full MFI check | Plan, Gate1b | 3 | in progress | Phase 3 started 2026-10-11. Fix #1 (G4 + G3) designed; root cause proven by replay. **Awaiting your approval to apply.** |
| P4-0 | **Cloud Jev (TypeSafe AI) REJECTED** (2026-10-11). Reasons: (1) paid; (2) cloud-only, so decision data leaves the Mac and it needs internet, which conflicts with the offline Anchor path; (3) the Cairo network round-trip eats its speed advantage; (4) a stateless API, so context is resent on every call; (5) it decides only from what it is given, while Odin's LLM can search and gather context before deciding | Gate-P3/4 | 4 | done (decision recorded) | Owner decision |
| P4-S | Phase 4 starts ONLY after Phase 3 is complete and approved. Work in Odin-Consolidated; moves into v2 in Phase 5. **Stop for approval after each sub-phase 4a–4g.** It is an experiment with a measured yes/no outcome, not a commitment. | Gate-P3/4 | 4 | open | — |
| P4a-1 | List EVERY fixed-option decision point (which agent; reuse/strengthen/create; which shared script; which role; request priority; and all others found), with file:line | Gate-P3/4 | 4a | open | — |
| P4a-2 | Measure today's LLM decision for each point: accuracy against known correct answers, end-to-end time, cost | Gate-P3/4 | 4a | open | — |
| P4a-3 | Split into CLOSED (all context in Odin, local decider allowed) and OPEN (needs search or research, always the LLM) | Gate-P3/4 | 4a | open | — |
| P4b-1 | Report the M4's RAM; confirm training works via MLX or PyTorch MPS | Gate-P3/4 | 4b | open | — |
| P4b-2 | Use **Qwen** (free download, full precision FP16/BF16, 0.5B–3B), trained locally on the M4 (R-ZC); justify the size | Gate-P3/4 | 4b | open | — |
| P4b-3 | Rules: Ollama only for serving the LLM baseline (it cannot train); train from Hugging Face full-precision weights; NEVER train a quantized model; quantize only afterwards if needed, and re-check accuracy | Gate-P3/4 | 4b | open | — |
| P4c-1 | Base model layers intact and frozen; no internal layers cut | Gate-P3/4 | 4c | open | — |
| P4c-2 | Replace the text head with a decision head: one pass gives one choice from the allowed list plus a confidence | Gate-P3/4 | 4c | open | — |
| P4c-3 | Calibrate confidence on validation (e.g. temperature scaling) | Gate-P3/4 | 4c | open | — |
| P4c-4 | Your context design: standing context (agents, titles, descriptions, shared scripts, deltas, standards) PREPARED on Odin's side; per decision add only the new part as an offset | Gate-P3/4 | 4c | open | — |
| P4c-5 | Low confidence falls back automatically to the LLM | Gate-P3/4 | 4c | open | — |
| P4c-6 | Early exit: optional later experiment, NOT now | Gate-P3/4 | later | parked | — |
| P4d-1 | Training data generated with Claude Code from Odin's REAL context (log decisions, your reviewed labels, scenario runs); each example = input (situation + allowed options with real context) and the expected output ; **R-ZC: only Odin's real logs, the owner's reviewed labels and runs under the plan login — no paid service** | Gate-P3/4 | 4d | open | — |
| P4d-2 | You review a sample of the labels before training | Gate-P3/4 | 4d | open | — |
| P4d-3 | Train / validation / held-out test split; the test set is never used in training or tuning; leakage check (no near-duplicates) | Gate-P3/4 | 4d | open | — |
| P4d-4 | Cost estimate before generating | Gate-P3/4 | 4d | open | — |
| P4e-1 | Big, clear toggle in the React desktop client: "Normal (LLM)" / "Jev mode (local decider)"; default Normal | Gate-P3/4 | 4e | open | — |
| P4e-2 | Normal mode behaves EXACTLY as before; proven by regression and your end-to-end tests with the toggle off | Gate-P3/4 | 4e | open | — |
| P4e-3 | Every decision log records the mode, the confidence and the timing | Gate-P3/4 | 4e | open | — |
| P4e-4 | After it is proven on desktop, the mode setting reaches web, mobile and the Anchor | Gate-P3/4 | 4e, 5 | open | — |
| P4f-1 | Held-out test: every case in BOTH modes, same inputs and conditions, 3 repetitions; measure accuracy, end-to-end time incl. context preparation, cost, calibration and fallback rate | Gate-P3/4 | 4f | open | — |
| P4f-2 | Real Odin scenarios in both modes; fair baseline (your REAL LLM decision); state what context each method had | Gate-P3/4 | 4f | open | — |
| P4f-3 | Acceptance: faster AND more accurate = best; same or slower but MORE accurate = achievement; same or worse accuracy with no speed gain = failure. Report honestly. **Owner 2026-10-13: same accuracy AND faster = PASS, labelled "non-inferior" (the LLM still handles every low-confidence case).** | Gate-P3/4 | 4f | open | — |
| P4g-1 | Tables and charts for the paper: accuracy, time, cost and calibration per decision type, the Jev-rejection reasons, and the free local alternative | Gate-P3/4 | 4g | open | — |
| P4g-2 | Save data, model metadata, scripts and results with the paper research material (moves to v2/research); do NOT edit the paper text | Gate-P3/4 | 4g | open | — |
| JEV-DoD-1 | **Jev definition of done (owner, 2026-10-11): Phase 4 is not complete until ALL of JEV-DoD-1…7 are true.** (1) The local decider is built, trained and calibrated on the owner's M4, as specified in 4a–4g. | 4 | open |
| JEV-DoD-2 | The Normal / Jev mode button works in the React desktop client, and the mode reaches web, mobile and the Anchor (supersedes the timing in P4e-4). | 4 (5 for the other clients) | open |
| JEV-DoD-3 | Normal mode behaves exactly as before, proven by the regression suite and the owner's end-to-end tests. | 4 | open |
| JEV-DoD-4 | Head-to-head complete: accuracy, end-to-end time, cost, calibration and fallback rate, on the held-out set AND on real scenarios, 3 repetitions each. | 4 | open |
| JEV-DoD-5 | Verdict stated honestly: faster and more accurate / more accurate only / failure. | 4 | open |
| JEV-DoD-6 | The feature is carried into Odin-Orchestrator-v2 in Phase 5 and proven again in Phase 7. | 5, 7 | open |
| JEV-DoD-7 | PAPER v2 written and finished in `v2/research/paper-v2`: the feature, how it was built, why cloud Jev was rejected, all measurements, metrics, results, tables and charts, the reproduction scripts, and its own related sections. Paper v1 is not changed by it (extends P4g-1/2 and PP-3/PP-4 from "material" to a finished paper). | 4, 5, 7 | open |
| P4-5 | The decider, if kept, goes into the same v2; no new folders | Gate1 | 4, 5 | open | — |
| P5-1 | v2 is a blind full copy of the **original** v1 (fresh, because v1's workspace is newer than every copy) | Plan, P0 finding | 5 | open | — |
| P5-2 | Behaviour baseline before any change (all end-to-end tests, regression, read-only replay of project tasks, every client and build target) | Plan | 5 | open | — |
| P5-3 | Integrate one change set at a time: (a) paper code plus documents; (b) approved fixes; (c) the Jev decision. Rerun the baseline after each; any difference blocks | Plan | 5 | open | — |
| P5-4 | Every change reaches every client (desktop dev and build, Flutter web, mobile, Anchor, React client) | Plan | 5 | open | — |
| P6-1 | Build and run parity: dev mode, build, DMG installs and runs, Flutter web, mobile build, Anchor, React client, env and phase scripts, the third-party test | Plan, Tracker | 6 | open | — |
| P7-1 | Full local end-to-end test of every area listed in Plan §7.1 | Plan | 7 | open | — |
| P7-2 | Real new project: propose 2–3; you choose; create, verify, delete, recreate until clean (deltas saved and registered, shared files correct, 0 wrong-folder, right script, no duplicates, delete leaves nothing) | Plan | 7 | open | — |
| P7-3 | Answers inside a project must be specific and use the project's delta; generic, stuck or wrong-format replies count as failures | Plan | 7 | open | — |
| P7-4 | Repeat the key runs 3 times; report honestly | Plan | 7 | open | — |
| P8-1 | Cutover only with your approval at each step, using **your certified VM deployment process** | Plan, Tracker | 8 | open | Process documented in MFI part B §2 |
| P8-2 | **Dry-run rule (your exact wording):** a dry run MAY replace the single SSH allow rule for my current IP (my dynamic-IP feature, replaced, never stacked). It must change NOTHING else: no ufw reset or other ufw rules, no change to ports 80/443, no sshd restart, no file sync, no build, no migration. | Gate1 | 3, 5, 8 | **code done (step G, `stepG-done`)**, proven with stub tools (no VM): stepG_test before 9 FAIL → after 12/12; F-18 CH0-3/CH3-4/CH1-5 PROVEN. Real proof at cutover (Phase 7) | v1 `deploy.sh` checked against the rule. **Complies:** NSG replace l.163–181; rsync `-n`; build, migrate and extra steps skipped. **Violates:** ufw rotation not dry-run-guarded (adds `deny 22`, re-adds 80/443, reloads) l.183–209; sshd enable/restart l.223–246; baseline re-dated l.376–394. Must be fixed in v2 and proven by a dry-run that shows zero other remote changes. |
| P8-3 | Production fingerprint plus backups of the VM and database before the switch; rollback plan (v1 stays deployable, git tag, exact commands) | Plan, Tracker | 8 | open | — |
| P8-4 | Any database schema change is listed and backed up first, applied only after approval | Plan | 8 | open | **Migration list:** (1) G8 `server/migrations/migrate_g8.sh up` — adds nullable `files.created_by` only; full `pg_dump -Fc` backup first (built in); reversible with `migrate_g8.sh down` (backup first too). Proven in the copy: add-only, views/queries/data identical, down = exact original schema. |
| P8-5 | Real `.cred` used only at cutover, handled or approved by you; values never printed | Plan | 8 | open | — |
| P8-6 | Anchor switched to run from v2 | Plan | 8 | open | — |
| P8-7 | **Back up the installed Odin.app and its 240 MB of app data before installing the v2 DMG** | Tracker, P0 finding | 8 | open | Paths: `/Applications/Odin.app`, `~/Library/Application Support/odin-desktop` |
| P8-8 | Post-cutover end-to-end test; roll back to v1 on any failure | Plan | 8 | open | — |
| P9-1 | **Never-delete list: Odin-Orchestrator (v1), Odin-Orchestrator-v2, ~/Desktop/misc/Odin, ~/Desktop/misc/Odin Testing** | Plan, Gate0 | 9 | open (recorded) | `PROGRAM_DECISIONS.md` |
| P9-2 | Delete a folder only with its checklist: unique content in v2 or waived; paper in v2/research; nothing depends on it; a verified archive exists; your written approval, one folder at a time | Plan | 9 | open | — |
| P9-3 | **All paper material in `v2/research/` before any cleanup** (Isolated `_research`, `Resulted Papers and Documents`, verification reports, replication packages). Paper due 30 October. | Plan, Tracker | 5, 9 | in progress | Verification reports saved (P9-4) |
| P9-4 | **The three verification reports saved as files** | Gate0 | 1 | done | `odin-v2-staging/research/verification/` (also the Phase 0 map and the decisions log) |
| P9-5 | Full v2 README (what v2 adds, the progression, inventory, dev/build/DMG/web/mobile/Anchor, tests, deployment, paper location, rollback) | Plan | 9 | open | — |
| P5-5 | **Move the SOC playbook, incident history and investigation charter into v2; do NOT copy `ACTIVE-RUN.lock`** | Gate0, Tracker | 5 | open (staged) | Source: `AiAgentWorkSpace/RedBerry-Continuous-SOC/soc/` |

Old P4-1 to P4-4 (Jev shadow test and memo) were **replaced** by the new Phase 4 on 2026-10-11, at your instruction. Their intent (measure decisions, local alternative, shadow-style comparison, decision memo) is carried by P4a–P4g.

## C. Gaps from Phase 2 (`odin_scenario_verification.md`)

All are open and await your approval of which to apply (Phase 3). The Plan's priority order is shown.

| ID | Gap | Priority | Status | Evidence |
|---|---|---|---|---|
| G3/G4 | Delta written but not saved or registered (manifest and `dependencies`); proposals not registered as approvals | 1 | **verified by a run** | Fix #1 (`fix1-done`): parser 2/6 → 6/6; S2 r4–r6 written 3/3, registered 3/3, resolve 3/3, correct owner 3/3; Revealer overlays now resolve; regression 32/32; phase7 lifecycle and strong green 3/3. The inline-apply and chat-proposal paths are not yet run (Phase 7). |
| G1 | False success. **Fix #2 revised per your review** (`fix2-done` = f902e74): the review ends with a FIXED field (PASSED / NOT_DONE / WAITING_FOR_APPROVAL). PASSED is accepted only when the files exist, were changed in the step and are registered, the audit is clean and QA passed if it ran. Waiting work ends "Waiting for your approval". The text check is only a safety net. | 2 | **APPROVED 2026-10-11** | Live: S7 PASSED ×2 (QA ran), S8 WAITING ×1, 4 runs NOT_DONE. Regression 32/32; phase7 3/3 green. See `PHASE3_FIX2_REPORT.md` rev 2. |
| G2 | "Do not deploy" wrongly blocked local file work (`_touches_vm`). **Fixed with F-32**: negation-aware `_vm_intent()`. | 3 | **APPROVED 2026-10-11 (with F-32 fail-safe condition, met)** | Before 8/8 runs showed the VM lock; S4 r7 after: none; unit 0/13 false triggers |
| G6 | Duplicate plus foreign reference leaves a dangling reference; the audit then reports 0 | 4 | **APPROVED 2026-10-11** (`g6-done` b272c99) with condition G6b — **G6b APPROVED 2026-10-11** (`g6b-done` 9b8c541) | S6 2/2. `g6_test.py`: before 6 FAIL → after ALL PASS (11 checks). S6 r4: reference repointed and resolves. Old r2/r3 leftovers now reported (were 0). Regression 32/32; phase7 3/3 each |
| G8 | No record of which agent created a file | 4 | **APPROVED 2026-10-11**, verified by tests and a live run (`g8-done` = acf1536) | g8_test 27/27, g8b_test 9/9; live S12: Write-tool files → "Fullstack (via Write tool)", misplaced finding names Fullstack; regression 32/32 and phase7 3/3 with AND without the migration |
| G5 | A project's own delta is flagged as a duplicate | 4 | **APPROVED 2026-10-11** (with F-36) (`g5-done` = 11a4a47) | g5_test: before 6 FAIL → after ALL PASS (11). Live copy: deploy-config.json in 6 projects no longer flagged |
| G11 | Build step assigned to DevOps instead of Fullstack | 5 | **APPROVED 2026-10-11** (`g11-done` = 1cbcc03) | g11_test before 6 FAIL → after ALL PASS (12); live S4 r8: step delegated to Fullstack (was DevOps 7/7) |
| G12 | **Decided:** EasyPost recommended per project, never auto-added | 6 | **APPROVED 2026-10-11** (`g12-done` = 8348695) | g12_test before 3 FAIL → after ALL PASS (6) |
| G7 | Audit does not scan `tests/` for duplicates | 7 | **APPROVED 2026-10-11** (`g7-done` = 39f2c93) | g7_test before 4 FAIL → after ALL PASS (7); regression 32/32, phase7 3/3 |
| G9 | Per-project credential choice not recorded in `agent_scope` or a delta; storage location inconsistent | 7 | **CLOSED — approved by owner 2026-10-11** (with G9b, `g9b-done`) | g9_test 13/13; g9b_test 16/16; desktop UI 8/8 |
| G10 | Reusing an agent overwrites its shared role and title | 7 | **CLOSED — approved by owner 2026-10-11** (`g10-done`). Data repair (owner-approved): 5 shortened titles restored in the copy as ONE logged batch `28385e6bb293` (undo: `python server/rewrite_log.py revert 28385e6bb293`); DB roles re-synced from each agent's index.json (never damaged). Correction: 5 titles, not 6 — EasyPost kept its title; only its description was replaced by a longer one (left as is, owner may decide) | g10_test 12/12; trial revert restored 5/5 files |
| G13 | Agent strengthening (add a skill, delete nothing) not done | 7 | **CLOSED — approved by owner 2026-10-11** (`g13-done`): a NEEDED new platform → one approval per platform to ADD the skill to the builder agent; additive, logged, one-command revert | g13_test before 3 FAIL → after 13/13; recorded S1 intakes 4/4 would propose Supabase for Fullstack |

## D. Other findings to carry (from MFI and SV)

| ID | Finding | Phase | Status |
|---|---|---|---|
| F-01 | `npm run e2e` points at `../tests/e2e.py`, which does not exist | 6 | open |
| F-02 | `development_full_checker.sh` l.164 runs `bash phase_ctl.sh` from the repository root (the file is in `shells/`). UNDETERMINED until run. | 6 | open |
| F-03 | No Android build command exists. Is Android a target? | 6 | **checked 2026-10-12:** no Android build (no APK/AAB, no signing key), no Android device or user agent in any v1/copy log on the Mac; only an iPhone. Not checked: the live Anchor's own logs on the VM (no VM access from the copy). Android stays out of v2 unless that check finds Android use (owner rule: if yes, keep Android) |
| F-04 | **Live Anchor API key committed in plain text** in `anchor_prod.js` and `anchor_seed.js` (value not copied) | 5 | **superseded by F-14 (step E, done):** the key is out of every shipped file in the copy. Rotation of the live key stays with you (real credential). |
| F-05 | `ODIN_DEFECTS_AND_FIXES.md` was not found anywhere on your Mac | 1 | **decided (step H, low-risk, applied):** the file does not exist; nothing is traced to it. Requirements stay traced to the MFI and this tracker. If you find it, send it and I re-check. |
| F-06 | Main-chat questions did not use the database or directions to find existing capability (S5 0/3) | 3/7 | **CLOSED — approved by owner 2026-10-11** (`f06-done`) | f06_test before 5 FAIL → after 6/6; live S5 r4: lookup observed 1/1, CTO started from vm-sentinel + organics diagnosis project |
| F-07 | Approval apply writes files without indexing them (unindexed until the audit timer) | 3 | **APPROVED 2026-10-11**, verified by tests and a live run (`f07-done` = 3474302) | f07_test before 5 FAIL → after ALL PASS; live: approved S8 r3 proposal → calc.py/test_calc.py indexed 20 s after approval, created_by recorded, audit did not touch them |
| F-08 | Name vs id mix-up: agents looked for a project folder by name slug | 3 | **CLOSED — approved by owner 2026-10-11** (`f08-done`) | f08_test before 6 FAIL → after 9/9; real S1 r4 proposal refused with the right id |
| F-09 | Phase 3 request page (plain `http.server`) loses the durable `/sim` log | 6 | open |
| F-10 | Automatic update of rules after an audit violation: no mechanism found (UNDETERMINED) | 3/7 | **done 2026-10-12** (owner: the audit PROPOSES, owner approves, never automatic): rule_proposals.py; f10_test before 6 FAIL → after 8/8 |
| F-11 | 50% shared-vs-separate threshold not found in code or docs (UNDETERMINED) | 3/7 | **owner 2026-10-12: NOT closed — it is the owner's design.** >50% common → shared base + delta; >50% different → separate scripts; exactly 50% → owner review. Built in the audit (scan + heal) and in customize_shared; f11_test before 9 FAIL → after 10/10 |
| F-12 | UDP was an example; the full category of communication mechanisms is listed (MFI CAT_COMMS). No UDP or WebSocket exists. | 1 | done |
| F-13 | Clone was an example; the full category of app modes and UI variants is listed (MFI CAT_MODES, 110 modes) | 1 | done |
| F-14 | **FIX (owner decision 2026-10-11):** the Anchor password and key must not be in the desktop app's code or shipped in the DMG; read them from a secure local store (macOS Keychain). The same applies to `anchor_prod.js`, `anchor_seed.js` and the Flutter client (F-04). | 3/5 | **done (step E, `stepE-done`)** in the copy: desktop reads the key/email/password from the macOS Keychain (service `odin-anchor`) via the Electron main process; Flutter uses `--dart-define=ODIN_ANCHOR_KEY`; anchor_prod.js / anchor_seed.js are run-time generated and gitignored; key removed from 9 files. **Owner items:** rotate the Anchor key + Manage password (still in v1, git baseline 0462cc0 and old test roots); create the Keychain entries; decide on scrubbing git history | stepE_test before 7 FAIL → after 12/12 |
| P8-9 | After cutover, you change the Anchor Manage password (and rotate the Anchor key) | 8 | open (owner action) |
| F-15 | Desktop sync never sends `since` (count-only change detection); the mobile app uses a delta cursor | 5/7 | open |
| F-16 | Generic-reply detector not found; wrong-format handling only partial (verdict and JSON parsing) | 3/7 | **REQUIRED on the pre-cutover list (PC-2)** (owner 2026-10-12: not optional) |
| F-17 | WORKSPACE-SCHEMA.md (9 project entries) disagrees with code and disk (14 subfolders) | 5 | open (doc fix) |
| F-18 | **The 42 chat mismatches belong to the false-success fix and it must cover ALL of them** (owner decision 2026-10-11). Note: false success is **G1** in the report numbering (you wrote G2; G2 is "do not deploy"). I'm treating it as G1. Each of the 42 becomes an acceptance check for G1 (list in MFI CH0–CH5 §3). | 3 | **done (step C, `stepC-done`)**: 42 → 27 PROVEN by tests, 11 DOC, 4 PENDING (P8-2 ×3 → step G; F-26 → step H) | results/f18_acceptance.json |
| F-20 | Brain token gate covers only `/chat*`, `/dispatch`, `/voice*`; other routes are open on the brain (CAT_COMMS N1) | 3/5 | **done 2026-10-12**: local only + brain token on every changing route and on GET routes that run work; f20_test (real HTTP) before 7 FAIL → after 10/10. PC-5 (CORS) on the pre-cutover list |
| F-21 | IP enrichment sends client IPs to ip-api.com over plain HTTP (CAT_COMMS N8) | 3/5 | **done 2026-10-12** in code: local GeoLite2 (no third party, no network fallback); f21_test 7/7. **Owner item:** the GeoLite2 download needs your free MaxMind account licence key (a credential) — until the two .mmdb files are in data/geoip the SOC enrichment shows "geo database not installed" |
| F-23 | **Approval bypass, fix #3.** Chat approval only by id or reply_to and only from the owner; Odin's follow-ups and agents can never approve; others stay pending. | 3 | **APPROVED 2026-10-11** (`fix3-done`; 34-s case reproduced before and gone after; live S11: older stayed pending 91 s) |
| F-22 | Desktop pending-code poll hard-codes the production Anchor URL; `phase_ctl send` registers an unreachable localhost callback; possible shared JSON queue file across two processes (CAT_COMMS N5–N7) | 3/7 | **done (step D, `stepD-done`)**: N5 cross-process lock on the JSON queue; N6 localhost webhook only for the local anchor; N7 poll honours the editable production anchor | stepD_test before 120/240 lost → after 5/5 |
| F-19 | Build signing: `afterpack-sign.cjs` ad-hoc codesign plus `xattr -cr` is required for the DMG | 6 | open |
| F-32 | **⚠ HIGH, CONFIRMED IN LIVE v1:** pre-authorized runs triggered the production firewall refresh on any VM-ish substring. **Fixed in copy:** F-32 (intent), F-32b (fail safe: only a CLEAR request opens VM access), F-32c (engine guard blocks the agent's own VM/Azure commands when not clearly asked). Owner turns auto-approve OFF in v1 himself until cutover. | 3 | **APPROVED 2026-10-11; fail-safe condition met and verified by runs** (S10 r2: 0 Azure calls; S9 r2: clear still works) |
| F-33 | "Approve all" (`/approvals/approve-all`) bulk-approves. **Owner decision 2026-10-11:** keep it, but add a confirmation that lists EVERY pending proposal (id, project, what it changes) BEFORE anything is approved. | 3 (step 3.3b) | **APPROVED 2026-10-11** (`f33-done` 470913b; server tests 7/7, UI tests 7/7) |
| F-34 | **Find what actually triggers the Egypt-Amazon poster run at 08:50** (the project schedule says 09:00; a local launchd job was seen). Carry that trigger into v2 and prove it in Phase 7. Related: F-24. | 3 (find), 5 (carry), 7 (prove) | **CLOSED — approved by owner 2026-10-12** (answered read-only, step B): NOT a schedule. 08:50 on 2026-07-09 was the Content Creator BUILD step (approved proposal) running the pipeline once as a test at 08:50:08 and loading the launchd job at 08:50:17. The real recurring triggers are launchd `com.odin.egypt-amazon-poster` at 09:00 and Odin's own scheduler task `856cf92fdf` at 09:00 (requireApproval) | step B report |
| F-35 | **Find what actually triggers the daily vm-sentinel run** (about 08:00) although its project schedule is empty. Carry that trigger into v2 and prove it in Phase 7. | 3 (find), 5 (carry), 7 (prove) | **CLOSED — approved by owner 2026-10-12** (answered read-only, step B): Odin's own scheduler task `8225146481` 'Daily VM health', daily 08:00 Africa/Cairo, requireApproval false, in `vm-sentinel/data/jsons/schedules.json` (the project index `schedule` field is `{}`, which hid it). No launchd/cron job for it | step B report |
| F-36 | Duplicate heal keeps the alphabetically FIRST copy and promotes it under THAT copy's name; the category comes from the name. In S6 the original `helper_s6_r4.py` became `shared/testing/dup_test_r4.py` (a helper filed as a test, under the copy's name). Found during G6; not changed by G6. | 3 (with G5) | **APPROVED 2026-10-11:** keep the OLDEST registered copy with its original name, file it in the correct shared category (never "testing" by accident). Scheduled together with G5. **APPROVED 2026-10-11 (done with G5).** | S6 r4, `g6_test.py` case 1 |
| F-37 | The audit sentinel (scheduler, ~every 15 min) calls `heal(force=True)`, which IGNORES the Audit page "enabled" switch: turning the audit off does not stop automatic healing. Same in v1 and the copy. Found during the v1 data-loss check. | 3 | **APPROVED 2026-10-11** (`f37-done` = aaa1f80). Owner rule: OFF = detect/report only, ON = may heal | f37_test before 6 FAIL → after ALL PASS (both states tested) |
| F-38 | Observed in S4 r8: a project created by the intake has NO localPath; the builder then proposes files under `~/Desktop/<name>` (outside the workspace) and the step ends "waiting". The harness never approves outside paths, so nothing was written. Should the intake always set a localPath (e.g. inside the project folder)? | 3 | **APPROVED 2026-10-11** (`f38-done` = baf53f1). Owner rule: folder always set (declared, else workspace/projects/<id>/code); writes outside are refused + shown | f38_test before FAIL → after ALL PASS (24) |
| F-39 | Under the F-38 rule, 15 of the 62 past approvals in the copy would now be refused. (a) real-deployment-and-diagnosis-organics-07d7: 10 proposals writing in the production code mirror (`_external/VolatileWorkSpace`, no declared folder); (b) redberry-continuous-soc: 2 proposals writing in the SOC repo folder (`RedBerry-Continuous-SOC`, no declared folder); (c) daily-egypt-amazon-product-poster: 2 proposals writing a launchd job into `~/Library/LaunchAgents` (its 08:50 schedule, see F-34); (d) the S4 r8 `~/Desktop` proposal (correctly refused). | 3 | **CLOSED — approved by owner 2026-10-11** (`f39-done`). Also: 6bd7b2ebf3ef, bc12b7443bfa, 1915cc48a862 marked "historical, replaced by the secure key field" | final replay: v2 paths → 62 checked, 14 historical, **1 refused (S4 only)**; copy → also the 2 poster launchd proposals (isolation only) |
| F-40 | Isolation gap in the copy: the copy database's `external_report` row for real-deployment-and-diagnosis-organics-07d7 points to the REAL file `~/Desktop/VolatileWorkSpace/RBO-Staging/AI_DIAGNOSIS_REPORT.md` (not re-pathed into `_external/`), and two SOC approvals carry the REAL SOC folder as their working folder. A write through these in the copy would touch real folders. | 3 | **CLOSED — approved by owner 2026-10-11** (`f39-done`) | results/f39f40_data_log.json |
| F-41 | Phone part of the G9b secure key field: the phone reaches the Mac only through the Anchor (VM); a key must never transit or rest there in plain form | 3 | **approved by owner 2026-10-11**; interim DONE (`f41i-done`): key requests are desktop-only (`desktop_only` flag + "Enter this key on the desktop"); the phone shows that text with NO field and NO Approve (Reject only); no phone path reaches /secrets. Open: build the E2E encrypted relay (Mac public key → phone encrypts → Anchor relays ciphertext → Mac decrypts and stores) | **done (step F, `stepF-done`)**: relay built in the copy — the Mac publishes an X25519 public key (mirrored to the Anchor with ONLY key requests), the phone pins its fingerprint and seals the key (AES-256-GCM, bound to the request), the Anchor carries ciphertext only, the Mac opens it and stores it like the desktop field. stepF_test before 1 FAIL → after 14/14 (Dart-sealed envelope opened by Python); phone tests 8/8. **Open for you:** D-1 (should other approvals be possible from the phone through the Anchor?) |
| F-42 | v1 lost more than rules on 2026-07-19: the G10 rewrite also removed the 'Integrated foundational charter' sections (incl. 'Must honor' rules) and archived merged-duplicate sections from 13 shared agent files (e.g. Fullstack −62 lines, Security Operations Investigator −37, QA −33, DevOps −23). All recoverable from v1 git 06a6ddb. | 3 | **CLOSED in the copy (approved)**. v1 restore patch KEPT FOR REFERENCE ONLY — owner decided NOT to apply it to v1 (v1 agents read only 900 chars; the G10 bug would wipe it again) | research/v1-restore-patch/ |
| F-43 | Agents read only the FIRST 900 characters of their capability.md at run time, so most rules never reached the prompt | 3 | **CLOSED — approved by owner 2026-10-11** (`f43-done`): setting `agent_rules_mode` — `full` (v2 DEFAULT): the 900-char excerpt AS BEFORE + a rules block with every 'Must honor' and 'Custom rules' line, cap 6000 chars, Must honor first, cut at whole lines, truncation stated in the prompt and logged ('rules-truncated' in audit-log); `legacy900`: exactly the old prompt (paper v1 reproduction, PP-10). Env `ODIN_AGENT_RULES_MODE` overrides `data/agent_rules.json` | f43_test 14/14 (legacy900 byte-identical for 9 agents); effect table results/f43_effect.json |
| F-44 | The agent-file lookup picked the FIRST folder whose name is contained in the agent's name: 'Security Operations Investigator' and 'Security Intelligence & Threat-Hunting Architect' were given the plain 'Security' agent's capability (and rules) | 3 | **CLOSED — approved by owner 2026-10-11** (`f43-done`): in `full` mode exact folder first, else longest partial match; `legacy900` keeps the old rule (paper v1) | f43_test 12, 13, 4b |
| F-24 | Egypt-Amazon launchd/cron job reinstalled after you asked for its removal, and still crashing (chat CH0-6) | 3 | **done (step C)**: owner-approved removals are remembered; re-creation/reinstall refused and shown; the real v1 reinstall c647148af20b is refused in the test; the poster removal is remembered in the copy | stepC_test 13/13 |
| F-25 | `~/Bendcore` vs the real `~/bendcore` in the DevOps planner and A-047 (CH1-4) | 3 | **CLOSED — approved by owner 2026-10-12** (step A, `stepA-done`) | stepA_test before 15 FAIL → after 18/18 |
| F-26 | CTO reviews applied the "do not read the VM `.env`" rule inconsistently (CH1-2). Your rule is needed. | 3 | **done 2026-10-12** (owner wording): hook in every model run + proposal check + review rule; f26_test before 9 FAIL → after 9/9; F-18 CH1-2 PROVEN |
| F-27 | Recurring project runs are routed to a single member instead of a team run (CH1-7) | 3 | **CLOSED — approved by owner 2026-10-12** (step A, `stepA-done`) | stepA_test before 15 FAIL → after 18/18 |
| F-28 | The coverage gate re-adds tasks the brief excluded (CH2-2) | 3 | **CLOSED — approved by owner 2026-10-12** (step A, `stepA-done`) | stepA_test before 15 FAIL → after 18/18 |
| F-29 | The deterministic status-answer shortcut misfired on a complaint (CH2-4) | 3 | **CLOSED — approved by owner 2026-10-12** (step A, `stepA-done`) | stepA_test before 15 FAIL → after 18/18 |
| F-30 | The single-run concurrency guard missed repeated identical requests (CH2-12) | 3 | **CLOSED — approved by owner 2026-10-12** (step A, `stepA-done`) | stepA_test before 15 FAIL → after 18/18 |
| F-31 | Revealer runs stopped at a gate with an empty reason (CH5-5) | 3 | **CLOSED — approved by owner 2026-10-12** (step A, `stepA-done`) | stepA_test before 15 FAIL → after 18/18 |

---

## Changed status at the fix #1 gate

- **G3/G4:** verified by a run.
- **G5:** still open (confirmed by a run).
- **New item:** F-23.
- **F-20 and F-21:** kept open as you asked.
- **Cost:** $25.91 of $40.

## Changed status after your Phase 1 decisions

- **P1-5, done:** all chats read.
- **P1-6 and P1-7, done:** the source code was read in full and every category is confirmed by file and line.
- **P8-2:** the rule is set; v1 is non-compliant in 3 places, to fix in v2.
- **New items:** P5-6, P4-5, F-12 to F-19.

## Changed status at this gate (Phase 1, first pass)

- **P1-1 to P1-4, done:** the master inventory is written.
- **P9-4, done:** the reports are saved on your Mac.
- **R-02, verified again:** v1 is unchanged.
- **New items:** P8-2 conflict, F-01 to F-11, P1-5.

## Open items

- **Nothing blocks Phase 1.** You approved it subject to the decisions above, which are now carried out.
- **Your answers are needed before Phase 3:** F-10, F-11, F-12, F-13 and F-16.
- **Your answers are needed before Phases 5, 6 and 8:** F-03, F-04, F-05 and F-14.


## Gate change log: order of work confirmed (2026-10-11)

- `ORDER_OF_WORK.md` confirmed by the owner.
- **P8-2:** the code fix is done in Phase 3 step 3.11, tested with "would run" logging and proven at cutover. Exact rule: only the single SSH allow rule for the current IP may be replaced.
- **G6, G8, G5, G7, F-07:** one at a time, each tested and approved separately.
- **F-20, F-21, F-04, F-03, F-05, F-10, F-11, F-16:** presented one at a time (what it is, the risk, a recommendation).
- **G1 (fix #2):** started.

## Gate change log: fix #2 scope approved (2026-10-11)

- **Fix #2 covers the 13 false-success mismatches** (group A in `PHASE3_FIX2_PLAN.md`).
- **10 already tracked:** P8-2, G12, G9, F-23, F-06.
- **8 new items:** F-24 to F-31, fixed one at a time after fix #2.
- **All 42 stay acceptance checks.**
- **11 inventory corrections:** each correction is shown to the owner (before and after) BEFORE the inventory is changed. Never remove a feature from the inventory without owner approval.

## PAPER PROTECTION RULE (owner, 2026-10-11): applies to EVERY phase

| ID | Requirement | Phase(s) | Status |
|---|---|---|---|
| PP-1 | **Paper v1 is FROZEN as "paper-v1".** Never delete, edit or affect anything in it: the paper text and sources, PDFs, ALL measurements, metrics and results (tables, charts, raw data, statistical tests, cost and timing records), raw logs, scripts, replication packages, DECISIONS.md and the proposals. | ALL (0–9) | in force |
| PP-2 | With the toggle on **Normal**, v2 must reproduce paper v1's measurements and metrics. A reproduction check must prove this BEFORE any cutover. **The reproduction check runs with `ODIN_AGENT_RULES_MODE=legacy900`** (PP-10). | 5, 6, 7, gate before 8 | open |
| PP-3 | The local decider (Normal / Jev mode button) is NEW work. ALL of its measurements, metrics and results go into a SEPARATE **"paper-v2"** folder, never into paper v1:<br>• raw data and logs from every run;<br>• accuracy, end-to-end timing, cost, confidence calibration and fallback rate, per decision type;<br>• the Normal vs Jev comparison tables and charts, with statistical tests;<br>• the training data description, the splits, the model choice and its settings;<br>• the scripts to reproduce every number. | 4a–4g, 5 | open |
| PP-4 | Paper v2 covers the new feature and how it was built, why cloud Jev was rejected, the head-to-head comparisons, any other new features added after paper v1, and its own related sections. | 4g, later | open |
| PP-5 | Paper v2 may reference paper v1, but nothing in paper v1 (text, measurements, metrics or results) may change because of it. | ALL | in force |
| PP-6 | In Phase 9, paper v1 and paper v2 move into `v2/research` as **two separate folders**. Neither may be deleted. Added to the never-delete list. | 9 | open |

| PP-7 | **paper-v1-submission** (owner, 2026-10-11): `final3` stays frozen as paper-v1. Approved description corrections 1–11 (+5/7 in threats, embedding citations moved to P4) are applied in `research/paper-v1-submission/` with `CHANGE_LIST.md`. Numbers and results are unchanged. | 3 | **done** (both PDFs rebuilt, 9 pages each, within the 10+2 limit) |
| PP-8 | Layout: "P2a:"/"P2b:" labels overprinted their text (§3.1, p.3), plus a missing space after the vendor list (p.2). | 3 | **done 2026-10-11** (fixed in the submission copy; same words; still 9 pages) |

| PP-9 | Pre-existing in paper-v1 and still in the submission copy, found by the page-by-page check: (1) Fig. 2 right panel, the y-axis label is clipped; (2) Fig. 2 left panel, "dashed: after heal" touches the curve; (3) Fig. 5, the legend "publish+callback" is clipped; (4) named PDF p.1, the author affiliation and e-mail are placeholders. | 3 | **closed (owner 2026-10-11):** items 1–3 done; the affiliation stays a placeholder and does not block the anonymous submission. No paper change in step H. |
| PP-10 | **Agent prompt mode for paper v1** (owner, 2026-10-11): v2's default gives agents their full rules (F-43) and their own capability file (F-44). Every paper-v1 reproduction run MUST set `ODIN_AGENT_RULES_MODE=legacy900` (environment, which overrides the setting file), which restores the old 900-character prompt BYTE-IDENTICAL (proven for 9 agents by f43_test). New measurements with full rules go to paper-v2, never paper-v1. | 3, 5–7 | in force |

**Changes this rule makes to existing items:**
- **P4g-1 / P4g-2:** the outputs go to **paper-v2**, not to the paper v1 research material.
- **P9-3:** paper-v1 and paper-v2 are separate folders.
- **P9-1:** paper-v1 and paper-v2 are added to the never-delete list.
- **Phase 3 fix tests:** they never write into the paper v1 folders. Results stay in `Odin-Consolidated/_consolidation/results`.

## Gate change log: fix #2 done, waiting for approval (2026-10-11)

**Changed status:**
- **G1:** verified by runs (`fix2-done`).
- **Group A (13 mismatches):** covered, with proof per item in the report.
- **F-18:** group A covered. Groups B, C and D stay tracked.

**New this gate:**
- Fix #2b: the review reader is stricter (found by S4 r4).
- The test harness `pg_up.sh` recreates the socket folder after a reboot.
- Open question: should a run waiting for your approval say "waiting for approval" rather than "Not done"?

**Still open:**
- F-23 (fix #3, next).
- G2, G5–G13, F-24…F-31.
- Inventory corrections: 11 proposed in `INVENTORY_CORRECTIONS_PROPOSED.md`, not applied.

**Not yet proven by a live run:**
- the QA-failed path;
- the deploy override (no VM);
- a clean live run ending "passed".

**Paper v1 fingerprint:** unchanged (2,217 files).
**Cost:** $32.62 of $40.

## Gate change log: fix #2 revision 2, waiting for approval (2026-10-11)

**Owner review:**
- Word matching was rejected. It is replaced by a fixed verdict field checked against evidence (#2c).
- A clean live pass was required: S7 ×2.
- "Waiting for your approval" wording is in force (#2d, #2e).

**Defects found and fixed during the tests:**
- #2d: duplicate proposals on retries; waiting work reported as "zero files".
- #2e: the text net overrode a correct WAITING verdict.

**New finding:** F-32 (HIGH): "no VM" in a pre-authorized goal triggers the firewall refresh and the ufw rotation. Recommended to fix with G2.

**Cost and budget:**
- $36.92 of $40. Paid runs are stopped until the owner sets a new cap.
- Estimate given: rest of Phase 3 about $45–75; Phase 4 about $120–330.

**Paper v1 fingerprint:** unchanged.

**Order confirmed by the owner:**
1. Fix #2 approval.
2. Fix #3.
3. Inventory corrections, one at a time.

## Gate change log: fix #2 approved; new budget (2026-10-11)

- **Fix #2:** APPROVED by the owner (`fix2-done` = f902e74).
- **F-32:** confirmed in live v1 by a read-only check. Owner told: avoid pre-authorized runs in v1 until the cutover; two v1 projects have auto-approve ON. **F-32 + G2 are next, before any other item.**
- **Cost cap:** $100 total for Phase 3 (spent $36.92). Phase 4 gets its own cap later and is planned small (about 1,500 training examples, fewer scenarios).
- **Order:**
  1. F-32 + G2.
  2. Fix #3 (approval bypass).
  3. The rest of Phase 3 as in `ORDER_OF_WORK.md`.
  4. The inventory corrections, presented one at a time.

## Gate change log: F-32 + G2 done, waiting for approval (2026-10-11)

**Changed:**
- **F-32 and G2:** verified by runs (`f32g2-done` = f63ea15). Report: `PHASE3_F32_G2_REPORT.md`.

**Still open:**
- **P8-2 (step 3.11):** when VM work IS asked, the rotate function still runs the ufw rotation.
- **G11:** S4 r7 build step still went to DevOps.

**Cost:** $40.34 of the $100 Phase 3 cap.
**Paper v1:** unchanged.

## Gate change log: fail-safe + fix #3 done (2026-10-11)

**Status changes:**
- F-32 (+ G2): approved with the fail-safe condition; fail safe built (F-32b, F-32c) and verified.
- F-23 (fix #3): verified, waiting for approval.

**New:** F-33 (bulk "Approve all" endpoint; owner decision).

**Owner standing rules added:**
- the STATUS block ends every report;
- no item leaves the tracker unless done, verified by a run, or closed by the owner.

**Owner action:** auto-approve OFF in v1 for `full-services-19jul` and `revealer-6978` (done by the owner).

**Cost:** $45.99 of the $100 Phase 3 cap.
**Paper v1:** unchanged. **v1:** unchanged.

## Gate change log: fix #3 approved (2026-10-11)

- **F-23:** APPROVED. It is closed and no longer waits for a decision. (The previous status block listed it in both places; it was waiting for approval at that moment.)
- **F-33:** decided. Keep "Approve all", with a confirmation listing every pending proposal (id, project, what it changes) before anything is approved. Scheduled as step 3.3b.
- **STATUS block now also shows:**
  - open items per phase (3 to 9);
  - the cost projection to finish Phase 3 against the $100 cap. If the projection passes $100, the owner is told before continuing.

## Gate change log: inventory correction 1 applied (2026-10-11)

- **Correction 1 (CH0-1):** "Test persistent chat memory" changed from PENDING to VERIFIED-RUN (2026-06-22, chat). Applied in the MFI; the old wording is kept.
- **Owner rule added to the MFI header:** a past run counts for the inventory only. Every feature must still be re-proven in v2 in Phase 7.
- **Owner rule for corrections 2–11:**
  - corrections that are status-only, with evidence, keep the old wording and remove nothing: can be approved together;
  - corrections that change or remove a feature: one at a time.

## Gate change log: paper v1 accuracy check (2026-10-11)

- **`research/PAPER_V1_ACCURACY_CHECK.md`:**
  - 10 description mismatches with proposed wording;
  - 1 undetermined item (queue "prioritises");
  - consistent items listed.
  - Nothing has been applied, and the paper folder was not changed.
- **Correction:** chat mismatch **CH5-1** (Zoom "live capture") is NOT a false claim. `meeting_api.py` captures serial audio chunks and transcribes them live (`zoom_pipeline_run.py` is the separate transcript-file path). It moves from fix #2 group A to "no defect". Fix #2 itself is unaffected.
- **PP-1 question for the owner:** apply approved corrections to a separate "paper-v1 submission copy", keeping `final3` frozen as paper-v1.

## Gate change log: paper-v1-submission and inventory group A (2026-10-11)

- **PP-7 done:** `research/paper-v1-submission/` contains the LaTeX source, the anonymous and named PDFs, and `CHANGE_LIST.md` (14 edits).
  - 9 pages each; references start on p.8; limit 10+2.
  - Results text, tables, figures and data are byte-identical.
  - Citation indices were renumbered.
- **PP-8 new:** the P2a/P2b label overprint, which already exists in paper-v1. Owner decision.
- **Inventory group A** (C-3…C-9, C-11) applied in MFI §0.8, with inline markers; the old wording is kept.
- **F-34 and F-35 new:** find the real triggers of the 08:50 poster run and the daily vm-sentinel run; carry them into v2; prove them in Phase 7.
- **Next:** inventory correction #2, on its own.

## Gate change log: Jev definition of done (2026-10-11)

- **JEV-DoD-1…7 added** to Phase 4 (owner).
- **Every status block during Phase 4** reports progress on all 7.
- **Timing note for the owner:**
  - JEV-DoD-6 (into v2 in Phase 5, proven in Phase 7) and parts of DoD-2 and DoD-7 can only finish after Phase 4.
  - Proposed reading: the Phase 4 gate closes DoD-1, 3, 4, 5, the desktop part of DoD-2, and a complete paper-v2 draft.
  - The Jev feature is fully DONE only when DoD-6, the client part of DoD-2, and the final paper-v2 (with the Phase 7 re-proof) are complete.
  - **Owner to confirm.**

## Gate change log: DoD split, correction #2, PP-8 (2026-10-11)

- **JEV-DoD timing split (owner, agreed):**
  - **Phase 4 gate** = DoD-1, 3, 4, 5, the desktop toggle (DoD-2 desktop) and a complete paper-v2 draft.
  - **Jev FULLY done** = DoD-6 (Phases 5 and 7), the mode in web, mobile and the Anchor (DoD-2 rest), and paper v2 final with the Phase 7 numbers.
  - The status block tracks both levels.
- **Inventory correction #2 (C-2, A-063)** applied in MFI §0.8; the row is kept.
- **PP-8 done:**
  - the P2a/P2b overprint fixed, plus the missing space after the vendor list;
  - all 18 pages checked as images;
  - still 9 pages.
- **PP-9 new:** two clipped figure labels, one overlapping figure note, and author placeholders. Owner decision.
- **Correction #10 revised before presenting:**
  - T-17 correctly describes the TEST script (`sandbox_revealer_multiagent.py` asks for NestJS + Next.js), so it must not be rewritten.
  - The proposal becomes a note: the delivered Revealer is backend-only FastAPI, per the owner decision CH5-002.

## Gate change log: F-33 approved, PP-9, step 3.5 starts (2026-10-11)

- **F-33 APPROVED** by the owner (`f33-done` = 470913b).
- **PP-9 stays OPEN: waiting for owner decision** (affiliation only). Figures and e-mail are done. The placeholder does not block the anonymous submission.
- **Next:** step 3.5, audit fixes one at a time, starting with **G6**.

## Gate change log: G6 done (2026-10-11)

- **G6:** fixed and verified (`g6-start` 470913b → `g6-done` b272c99). Waiting for owner approval before G8.
- **New F-36:** duplicate heal keeps the alphabetically first copy and its name (found during G6).
- **Note:** the two dangling references left by S6 r2/r3 in the copy (made before the fix, no recorded move) are now reported and FLAGGED by heal; they are test leftovers and are kept as evidence.

## Gate change log: G6 approved with condition; G6b done; F-36 approved (2026-10-11)

- **G6 APPROVED** with the condition that every automatic reference rewrite is logged (file, old path, new path, time, reason) and reversible with one command. Implemented as **G6b** (`g6b-done` 9b8c541): `python server/rewrite_log.py list | revert <batch> | release <batch>`. Waiting for owner approval.
- **F-36 APPROVED:** keep the oldest registered copy and its original name, in the correct shared category. Done together with **G5**.
- **G8 started** (`g8-start`): plan in `PHASE3_G6B_REPORT.md`; one owner choice needed (where the creator is stored).

## Gate change log: G6b approved; G8 done; ZERO-COST rule (2026-10-11)

- **G6b APPROVED.**
- **G8 done** (option A with the owner's 4 conditions), waiting for approval. Migration added to the **P8-4 cutover list** (backup first, reversible).
- **R-ZC (HARD RULE — ZERO EXTRA COST) added** to the program rules; supersedes R-10 and every dollar cap. Auth verified: plan login only, no API key, paid extra usage disabled. Code guard refuses any paid route. Dollar figures are now "reported usage, not charged".
- **Phase 4:** Qwen, downloaded free, trained locally on the M4 (P4b-2, P4d-1 updated).

## Gate change log: G8 approved; R-ZC confirmed; G5 + F-36 done (2026-10-11)

- **G8 APPROVED.** **R-ZC confirmed by the owner** as implemented, with the allowed-sources wording; in force for every remaining phase.
- **Pre-flight before this step:** copy server health 200; auth check = plan login only, no paid route.
- **G5 + F-36** done and verified; waiting for approval. New safety fix found by the test: a shared-name clash used to DELETE the project copy (data loss) — now flagged, nothing lost.

## Gate change log: G5 + F-36 approved; v1 data-loss check; usage correction; G7 + F-07 done (2026-10-11)

- **G5 + F-36 APPROVED.**
- **v1 read-only check** (`V1_DATALOSS_CHECK.md`): the shared-name bug exists in v1 code, but NO project file was lost (31 promotions checked against git history; INSTALL_SOC_SENSOR.md moved byte-identical). Today's exposure: 0 files. New **F-37** (sentinel ignores the audit's "enabled" switch).
- **Usage correction:** S11 (fix #3 test) ended at 11:58:23 UTC, but the background apply of the approved proposal it triggered finished at 11:58:39 and logged **$0.4985** after the scenario had recorded its total. Fix #3's real usage was $1.93, not $1.44. The ledger (`claude_calls.jsonl`, 186 calls) is the authority: **$47.63 before this step** (not charged).
- **G7** and **F-07** done and verified; waiting for approval.

## Gate change log: G7, F-07 approved; F-37 + G11 done; harness fixes (2026-10-11)

- **G7 and F-07 APPROVED.** **F-37** built to the owner's rule and tested in both states; waiting for approval.
- **G11** done; live S4 r8 gave the build step to Fullstack. Waiting for approval.
- **Harness:** one usage ledger for the paper (S4 r8's $1.01 reported usage was logged to the shim's default file because the server had been restarted without the variable; merged); the plan-limit detector no longer reacts to project text such as "rate limiting".
- **New F-38** (owner decision): intake leaves localPath empty → builder proposes paths outside the workspace.
- **v1 recovery copy:** the owner will copy the v1 folder (or use Time Machine), not commit, so the af2cbd8 baseline stays valid.

## Gate change log: F-37, G11 approved; F-38 + G12 done (2026-10-11)

- **F-37 and G11 APPROVED.**
- **F-38** built to the owner's rule; **G12** built. Both waiting for approval.
- **New F-39** (owner decision): past approvals that the F-38 rule would now refuse (production code mirror, SOC repo, launchd schedule).
- **G12:** existing projects are not changed. In v1, only `fulfillment-vq-status-read-only-dc1e` (a shipping project) has EasyPost.

## Gate change log: F-38, G12 approved; F-39 (2) done; G9 done (2026-10-11)

- **F-38 and G12 APPROVED.**
- **F-39:** (2) done — only `~/Library/LaunchAgents/com.odin.egypt-amazon-poster.plist` is allowed for the poster (exact file). The poster is ONLY the scheduled poster job (launchd → `Odin Testing/testing/daily-egypt-amazon-product-poster/scheduler/run_daily.sh`); its folder has no Veeqo reference; nothing in Veeqo or US fulfillment was touched. (1) folders proposed; (3) waits for confirmation.
- **G9** done (live S3 r4); waiting for approval. A secret store is never a write target.
- **New F-40** (isolation gap in the copy). **F-34 note:** the launchd file says 09:00.

- **New F-41** (owner decision, P3): phone part of the G9b secure key field. The phone talks only through the Anchor (VM), so a key must not pass or rest there in plain form. Proposal: end-to-end encrypted relay — the Mac publishes a public key, the phone encrypts, the Anchor relays ciphertext only, the Mac decrypts and stores (can align with F-14 Keychain). Not built until approved.

## Gate change log: G9 (+G9b), F-39, F-40 (2026-10-11)
- **G9** approved by owner; **G9b** added and done on desktop (`g9b-done`).
- **F-39** done; **F-40** done (`f39-done`).
- **Phase 5 carry-over (v2 real values):** real-deployment → `~/Desktop/VolatileWorkSpace/RBO-Staging` (report `.../AI_DIAGNOSIS_REPORT.md`); SOC → `~/Desktop/AiAgentWorkSpace/RedBerry-Continuous-SOC`; poster file → `~/Library/LaunchAgents/com.odin.egypt-amazon-poster.plist`.


## Gate change log: G10 done (2026-10-11)
- **G10** done (`g10-done`); waiting for approval. Proposed data repair (copy only): restore the 6 degraded shared titles from the baseline.

## Gate change log: owner approvals + G10 repair + F-41 interim (2026-10-11)
- Closed by owner: G9 (+G9b), G10, F-39, F-40.
- G10 data repair done (batch `28385e6bb293`, reversible).
- 3 secret-file proposals marked historical (replaced by the secure key field).
- F-41 approved; interim done; the relay itself stays open.

## Gate change log: G13 done (2026-10-11)
- **G13** done (`g13-done`); waiting for approval. Step 3.8 (G9, G10, G13) complete.

## Gate change log: G13 approved; G10 rules recovered; F-42 found (2026-10-11)
- G13 closed by owner.
- v1 read-only check: 20 custom rules lost (5 agents), all recoverable (git 06a6ddb; 17 also in current v1 rosters). Recovered in the copy (batch `94593f5b7964`); test g10r 7/7.
- G10 leftovers done (batch `fce0302472dc`).
- New F-42 (charter sections lost in v1).

## Gate change log: F-42 done in the copy; v1 patch prepared; F-43 found (2026-10-11)

## Gate change log: F-06 done (2026-10-11)
- F-06 done (`f06-done`); waiting for approval. Live S5 r4 reported usage $0.62 (not charged).

## Gate change log: F-06 approved; F-42 v1 patch kept for reference; F-43 + F-44 done; PP-10 added (2026-10-11)

## CONVERGENCE RULE (owner, 2026-10-11)
1. Phase 3 closes when the FIXED Phase 3 exit list below is done — not when findings stop.
2. New findings from now on are NOT added to Phase 3 automatically: **critical** (safety, security, data or rule loss, core design: deltas, shared files, approvals, agent reuse, audit) → told to the owner immediately, owner decides; **everything else** → the PRE-CUTOVER FIX LIST (fixed in Phase 5, proven in Phase 7, done before cutover).
3. Small, low-risk, related items are grouped into one step / one report / one approval. One-at-a-time only for risky items (approvals, credentials, the VM, the database schema, deletion).
4. Every status block shows: exit list remaining, pre-cutover fix list count, estimated steps to close Phase 3.

## PHASE 3 EXIT LIST (fixed 2026-10-11) — 28 items
| # | Item | Step |
|---|---|---|
| 1–3 | F-08, F-43, F-44 — done, waiting for owner approval | approval |
| 4–9 | F-25, F-27, F-28, F-29, F-30, F-31 — run-flow and path fixes (low risk) | Step A (grouped) |
| 10–12 | F-34, F-35 (find what triggers the 08:50 poster and the ~08:00 sentinel), F-24 (poster job reinstalled after removal and still crashing; investigation and fix in the copy only) | Step B (grouped; any deletion done separately) |
| 13 | F-18 — the 42 chat mismatches as acceptance checks for G1 | Step C |
| 14 | F-22 — desktop pending-code poll hard-codes the production Anchor URL; unreachable callback; shared queue file | Step D |
| 15 | F-14 — Anchor password and key out of the desktop code into the Keychain | Step E (alone: credentials) |
| 16 | F-41 — phone key relay, end-to-end encrypted | Step F (alone: credentials) |
| 17 | P8-2 — deploy.sh dry-run obeys the owner's rule (code part) | Step G (alone: VM) |
| 18–27 | Decisions: F-03, F-04, F-05, F-10, F-11, F-16, F-20, F-21, F-26, PP-9 (affiliation) — one report, owner decides each | Step H (+ step I for any approved security fix) |
| 28 | Phase 3 gate: full regression + end-to-end, tag `phase3-done` | Step J |

## PRE-CUTOVER FIX LIST (fixed in Phase 5, proven in Phase 7, before cutover)
| # | Item | Found |
|---|---|---|
| PC-1 | The poster's launchd job has failed at every 09:00 run since 2026-08-01 ('can't open input file … run_daily.sh'): macOS privacy blocks a launchd job from reading the Desktop. Fix while carrying the poster into v2 (move the job's files out of ~/Desktop or run it from Odin's scheduler), prove in Phase 7. Nothing changed now. | step B, 2026-10-12 |


## Gate change log: F-08, F-43, F-44 approved; exit list confirmed (28 items / 10 steps); 8efef7bd4f08 marked historical (name-folder layout) (2026-10-11)
- Owner caution for step B: investigate the real launchd triggers READ-ONLY; change nothing in ~/Library/LaunchAgents or any real scheduler without explicit approval.
## R-DP DEPLOYMENT PERMISSION RULE (owner, 2026-10-12) — global, in force
1. Real deployments ARE allowed for the TEST / SANDBOX projects (e.g. Revealer and the other test/sandbox projects) so their end-to-end tests run fully.
2. NEVER deploy, sync, build, migrate, restart or change anything for the real deployment projects targeting **RBO Staging** or **RBO Production**: no files, services, database, ports, nginx config or folders that belong to them. Read-only checks only. RBO Staging on the VM = `~/bendcore` (backend) and `~/organics` (frontend), their services and databases — protected: never write, sync, build, migrate, restart or delete anything in them.
3. Every allowed sandbox deploy (same VM as RBO Staging) must: change the firewall ONLY by the owner's single dynamic-IP rule (no ufw reset, no change to ports 80/443); never restart shared services (nginx, sshd, the staging services) or touch the staging folders and database; deploy only into the sandbox project's own folder and port; take an RBO Staging PRODUCTION FINGERPRINT before and after, and STOP immediately if anything in it changed.
4. The copy has NO real VM credentials, by design. Before the FIRST sandbox deploy: state exactly which credentials and which targets are needed, how they stay out of git and logs, and WAIT for the owner's approval.
- F-25 (guidance text `~/Bendcore` → `~/bendcore`) changes only two text files in the copy; it touches nothing on the VM.


## Gate change log: step A done (2026-10-12) — F-25, F-27, F-28, F-29, F-30, F-31; waiting for approval. R-DP deployment permission rule recorded.

## Gate change log: step A approved (2026-10-12); step B started (READ-ONLY on the real Mac; nothing changed in ~/Library/LaunchAgents or any real scheduler)

## New finding — CRITICAL candidate (owner decides if it enters Phase 3)
| F-45 | Approval records do not store WHO approved or through WHICH channel (popup, chat, phone, bulk, automatic) | 3 | **done (step C)**: every decision records who (owner/odin) + channel (desktop/phone/web/api/chat/bulk/secure-field/guard/system) + history | stepC_test 13/13 |

## Gate change log: step B done (read-only) — F-34, F-35, F-24 answered; PC-1 added to the pre-cutover list; F-45 raised as critical candidate (2026-10-12)

## WORKING MODE (owner, 2026-10-12) — standing approval for steps C–J
1. Steps C to J run one after another without waiting, provided each change is tested (old fails, new passes), full suite + phase7 green, v1 and paper v1 unchanged, everything logged and reversible.
2. STOP and ask only for: anything touching v1, the real VM or RBO Staging/Production, real files or schedulers on the owner's Mac, real credentials, deletion of real data, database schema changes, paper v1, anything that could cost money; or a test that cannot be made green.
3. Step H: recommendation per decision; low-risk ones applied; risky ones collected in ONE list.
4. One report at the end of Phase 3.
## Gate change log: step B approved; F-24 fix folded into step C; F-45 added to Phase 3; PC-1 stays pre-cutover (2026-10-12)

## Progress (working mode): step C done 2026-10-12 (`stepC-done` 6982a7f). Test-harness fix: fix2c_unit resolves its temp root on macOS; added to the regular suite.

## Progress (working mode): step D done 2026-10-12.

## Step H decisions (2026-10-12)
Applied (low-risk, documentation only): F-03, F-04 (via F-14), F-05, F-11, F-16 (→ PC-2, required), PP-9 (closed by your 10-11 decision).
For your decision (risky — nothing applied): F-10, F-20, F-21, F-26, plus D-1 (phone approvals through the Anchor, found in step F) and D-2 (no override for the deploy RBO guard, step G). Recommendations are in the Phase 3 final report.
- **PC-2 (pre-cutover, REQUIRED):** generic-reply detector (F-16).
- **PC-3 (pre-cutover, from step F):** show the Mac relay-key fingerprint on the desktop (Settings) so you can compare it with the phone at first pairing; today the phone pins it on first use.

## STANDING DECISION RULE (owner, 2026-10-12) — global, applies to every future decision
1. Never weaken the owner's design to converge. A decision may not remove, disable, downgrade, make "optional", or replace with something simpler any feature, rule or behaviour of the design. If the only way to finish faster is to weaken something, choose the strong option and do the work.
2. Converge through method, not by cutting: group related work, run long sequences without stopping, decide low-risk items yourself, and put non-critical work on the pre-cutover list (REQUIRED, never optional).
3. Every self-made decision states in one line why it does NOT weaken the design. If that cannot be said, ask the owner.
- **PC-4 (pre-cutover, REQUIRED, owner 2026-10-12, D-1):** secure phone approvals through the Anchor — signed and encrypted like the F-41 relay, tied to one request, never replayable. Approvals stay desktop-only for the cutover; phone control is part of the design and is not dropped.
- **PC-5 (pre-cutover, REQUIRED, found in F-20):** the brain allows any web origin (CORS "*"), so a web page the owner opens could READ brain data from localhost:28000. Fix: allow only the desktop and local origins (needs a check of the packaged desktop's origin first).
- **PC-6 (pre-cutover, REQUIRED, F-03):** read the live Anchor's own logs on the VM (read-only) for Android clients; if any, Android becomes a v2 target.

- **Decisions 2026-10-12 (owner):** F-10, F-20, F-21, F-26 approved as recommended; D-1 desktop-only for cutover + PC-4; D-2 no override; rotation at Phase 8; no git scrub; old test folders deleted.

## Gate change log: Phase 3 closed (2026-10-12)
All 28 exit-list items done. Final gate: 33 item tests pass, regression 32/32, phase7 lifecycle/strong 3/3 each, flutter 8/8, desktop UI tests pass, F-18 = 31 PROVEN + 11 DOC + 0 PENDING. Tag `phase3-done`. Phase 4 started (owner: continuous mode; stop only for rule-2 items).

## Gate change log: Phase 4 gate3 owner rules (2026-10-13)

- **Statistical honesty (owner):** every accuracy comparison carries 95% Wilson intervals and an exact paired McNemar test; "best" only when the difference is significant (p < 0.05), otherwise "non-inferior" (lower but not significant = "inconclusive"). Applies to reports and paper v2.
- **No live authority before human labels (owner):** Jev runs in SHADOW (decider logged, the LLM decides every case) until the owner's labels arrive; thresholds and calibration fitted on generated data are never used for live decisions. Only the post-label re-run may grant live authority.
- **Post-label order (owner):** layer choice on the real validation set, then temperature scaling, then thresholds, then the head-to-head (`_research/phase4/after_labels.sh`).
- **Models (owner):** 0.5B active, 1.5B kept available; final choice after the re-measure on the owner's labels.
- **Read/change test set (owner target >= 100 from logs):** logs exhausted at 55 strict + 37 extended cases (extended reported separately; its rules make known errors); the rest needs the owner's labels.
- **Paper v2:** draft started in `research/paper-v2/`, every figure marked provisional; paper v1 untouched.
