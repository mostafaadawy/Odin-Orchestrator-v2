# Odin v2 — what changed from v1, and why

This document is the record of the v2 program. The short operational guide is `README.md`; the line-by-line
change log is `CHANGELOG.md`; the full requirement history is `docs/program/REQUIREMENTS_TRACKER.md`.
Numbers marked **provisional** are waiting for the owner's human labels (see section 4.5).

## 1. What v2 is

v2 (`~/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2`, branch `v2`) is v1 (`Odin-Orchestrator`, commit af2cbd8 plus
its 8 uncommitted runtime files) with every fix proven in the Phase 3 program, the new local decider "Jev", the
pre-cutover items, and all research material in one place. v1 itself is untouched and stays the live system until
cutover.

| | v1 | v2 |
|---|---|---|
| Code | af2cbd8 + 8 modified files | the same, plus 46 replayed fix commits (Consolidated 7305356..7e3afb4), PC-4, v2 launch/build work |
| Defects | the Phase 3 list below is open | every item fixed and proven by a before→after test |
| Agent prompt | first 900 characters of each agent's capability file | full rules (F-43) from the agent's own file (F-44); `ODIN_AGENT_RULES_MODE=legacy900` reproduces v1 byte-identically |
| Owner secrets | Anchor key and Manage password compiled into the desktop bundle | macOS Keychain at run time (F-14); rotation tool `server/odin_secrets.py` |
| Brain | open routes, CORS `*` | local-only + token on every changing route (F-20), origin lock (PC-5) |
| Phone | approvals desktop-only; keys only on the desktop | keys through the encrypted relay (F-41); approvals signed by a paired phone and sealed to the Mac (PC-4) |
| Decisions | always the LLM | Normal (LLM, exactly v1) or Jev (local model + per-decision heads, LLM fallback) |
| Research | spread over Odin-Isolated, Odin-Consolidated, staging, "Resulted Papers" | `research/` (paper-v1 frozen state with fingerprint, paper-v1 submission, paper-v2, phase4, consolidation) and `docs/program/` |

## 2. How v2 was built (Phases 0–5)

1. **Copy and repath.** v2 was created with `tar` from v1 (no `.venv`, build outputs or caches). `_v2/repath_v1_to_v2.py`
   repointed 4,832 references in 384 files from `Odin-Orchestrator` to `Odin-Orchestrator-v2`; records (chats, history,
   logs) were not touched. Tags `v2-start`, `v2-repath`.
2. **Research import** (`_v2/import_research.sh`, tag `v2-set-a`). The paper-v1 frozen state was copied file by file and its
   fingerprint re-verified inside v2 (2,217 files, OK).
3. **Fix replay** (`_v2/port_from_consolidated.py`, tags `v2-set-b`, `v2-set-c`). Each Consolidated commit was replayed as one
   v2 commit with a three-way merge (ours = v2, base/theirs = the Consolidated file with the isolation dialect reversed).
   6 conflicts, all resolved by rule (docs keep the concrete v2 path; `.gitignore` union). Three files lost their
   executable bit in the replay and were restored (`server/door_cli.py`, `server/scope_hook.py`,
   `server/migrations/migrate_g8.sh`).
4. **Isolated re-proof** (`_v2/iso/build_iso.py`, `_v2/iso/run_suite.sh`). v2 code stays production-true; tests run on a
   throwaway clone (`_v2/iso_root`) with its own paths, databases (`odin_core_v2i`, `odin_anchor_v2i`, private Postgres on
   26432/26433), ports (38000/39100/39104/39300/38080), blank secrets, disabled schedules and shims for `az/ssh/rsync`.
   The "before" trees the tests compare against are the exact Consolidated evidence trees, rebuilt in the clone's dialect.
5. **Result (suite `after_fix1`, tag `phase5-done`)**: regression 32/32; Phase-7 lifecycle and strong tests ALL GREEN in 3 of 3
   repetitions; all 35 item tests in the suite ALL PASS (f33 is run separately, see CHANGELOG), including F-43 legacy900 byte-identical (paper v1), Step E 12/12 and the Jev
   toggle (p4e). v1 baseline on the same harness failed the fix tests as expected (`_v2/results/baseline_v1`).

## 3. Every defect found and fixed

"before → after" is the item test run on the pre-fix tree and on v2. All tests are in `tests/harness/_consolidation/`.

### 3.1 Gaps from the Phase 2 scenarios

| ID | Defect | Fix | Proof |
|---|---|---|---|
| G1 | False success: runs reported "passed" without QA or with a "Needs fix" review | the review ends with a FIXED verdict field; success needs evidence; F-18's 42 chat mismatches are acceptance checks | fix2_unit, fix2c_unit, live S7 |
| G2 | "Do not deploy" blocked local file work (`_touches_vm`) | negation-aware `_vm_intent()` (with F-32) | f32g2_unit |
| G3/G4 | Delta written but not saved or registered; proposals not registered as approvals | parser + registration of manifest, dependencies and approvals | fix1 tests |
| G5 | A project's own delta flagged as a duplicate | own-delta recognised | g5 6 FAIL → pass |
| G6 | Duplicate + foreign reference left a dangling reference; audit reported 0 | heal resolves references; audit counts them | g6, g6b |
| G7 | Audit did not scan `tests/` | scanned | g7 4 FAIL → pass |
| G8 | No record of which agent created a file | creator recorded (DB migration `migrate_g8.sh`) | g8 27/27, g8b 9/9 |
| G9 | Per-project credential choice not recorded | recorded in `agent_scope` + delta; one storage place | g9 13/13, g9b 16/16 |
| G10 | Reusing an agent overwrote its shared role/title | per-project role; lost rules restored | g10 12/12, g10r |
| G11 | Build step assigned to DevOps instead of Fullstack | correct owner | g11 6 FAIL → pass |
| G12 | EasyPost auto-added | recommended per project, never auto-added | g12 3 FAIL → pass |
| G13 | Agent strengthening (add a skill, delete nothing) missing | additive, logged, reversible strengthen | g13 3 FAIL → pass |

### 3.2 Findings

| ID | Defect | Fix | Proof |
|---|---|---|---|
| F-04 / F-14 | Live Anchor key and Manage password compiled into the desktop/DMG | Keychain via Electron main (`secret-get`), `--dart-define` for Flutter, generated anchor js untracked; v2 adds Keychain provisioning + rotation | stepE 7 FAIL → 12/12 |
| F-06 | Main-chat questions ignored the database/directions | capability lookup first | f06 5 FAIL → pass |
| F-07 | Approval apply wrote files without indexing them | indexed at apply | f07 5 FAIL → pass |
| F-08 | Agents looked for project folders by name slug | id-based lookup | f08 |
| F-10 | No rule update after an audit violation | audit PROPOSES a rule; owner approves; revert in one command | f10 |
| F-11 | 50% shared-vs-separate threshold missing | implemented + true deltas | f11 |
| F-16 → PC-2 | No generic-reply detector | detector + format guard | pc2 |
| F-18 | 42 chat mismatches | acceptance checks (PROVEN / DOC / 0 PENDING) | f18_acceptance |
| F-20 | Brain token covered only chat/dispatch/voice | local-only + token on every changing route | f20 |
| F-21 | IP enrichment sent client IPs to ip-api.com over HTTP | local GeoLite2 | f21 |
| F-22 | Desktop pending-code poll hard-coded the production URL; unreachable callback; shared queue | editable anchor, reachable callback, separate queues | stepD 120/240 lost → 0 |
| F-23 | Approval bypass (chat approvals by anyone) | only the owner, only by id/reply_to | fix3 |
| F-24 | Poster launchd job reinstalled after removal, still crashing | agents cannot install launchd/cron jobs | stepC 13/13 |
| F-25, F-27…F-31 | `~/Bendcore` path, recurring runs to one member, coverage gate re-adds excluded tasks, status shortcut misfire, concurrency guard miss, empty gate reason | each fixed | stepA 15 FAIL → pass |
| F-26 | Inconsistent "do not read the VM .env" | secret-file rule | f26 |
| F-32 | Pre-authorised runs refreshed the PRODUCTION firewall on any VM-ish word | intent detection | f32 |
| F-33 | "Approve all" bulk-approved | confirmation listing every proposal; security items never in bulk | f33 |
| F-36…F-40 | Duplicate heal kept the wrong copy; audit switch ignored by the sentinel; projects without a folder wrote to `~/Desktop`; old approvals now refused; isolation gap | each fixed | f37, f38, g6 |
| F-41 | Phone could not send a key safely | end-to-end encrypted key relay (X25519 + HKDF + AES-GCM), fingerprint pinning | f41i, flutter |
| F-42 | v1 lost charter sections and rules on 2026-07-19 | restored (`research/v1-restore-patch`) | g10r |
| F-43 | Agents read only the first 900 characters of their rules | full rules; `legacy900` mode for paper v1 | f43 14/14 (byte-identical) |
| F-44 | Agent file lookup picked the first folder whose name was contained in the agent name | exact match | f43 4b, 12, 13 |
| F-45 | Approvals did not record who decided and through which channel | who + channel + history | stepC 13/13 |
| P8-2 | deploy.sh dry-run ignored the owner's rule | dry-run obeys | stepG |

### 3.3 Found during v2 (Phases 5–6)

| ID | Defect | Fix | Proof |
|---|---|---|---|
| D-v2-1 | Desktop "Open request page" always failed (looked for `anchor_sim.html` in the repo root; it lives in `workspace/anchor-layer`) — present in v1 | serve it with `server/sim_server.py` from the right folder | manual + DMG test |
| D-v2-2 | A saved `root.txt` from the v1 app could make the v2 desktop start the v1 backend | a saved root is used only if it is a v2 checkout | DMG clean-path test |
| D-v2-3 | Launch scripts reused ANY brain on :8000 (the v1 app's) | `/health` reports `root_name`; scripts stop a brain from another checkout | env script |
| D-v2-4 | Anchor-key literals in docs/logs/chat records (v1 copies) | redacted (as Step E did in Consolidated) | stepE check 1 |
| D-v2-5 | Replay lost the executable bit on 3 files | restored | g8, g8b, f07 |
| F-02 | `development_full_checker.sh` ran `bash phase_ctl.sh` from the repo root (the file is in `shells/`) — the control bridge never started (confirmed: "No such file or directory") | absolute path | env run |
| D-v2-6 | Ctrl-C left the supervised poller, its poller and the control bridge running (no port, so "all ports freed" was printed while they kept polling) — present in v1 | cleanup stops the ones this run started (scoped to this folder / anchor port) | env run: 0 processes, 0 ports after stop |
| D-v2-7 | Without Flutter on PATH the environment script ran `brew install --cask flutter` silently | installing Flutter now asks first (never in headless runs); it uses the Flutter already on your PATH | env run |
| D-v2-8 | The Anchor deploy shipped the owner's WHOLE `.cred` to the VM (connector keys and the VM credential), although the Anchor reads only 3 values — present in v1 | the deployed copy carries only `ANCHOR_API_KEY`, `ANCHOR_MANAGE_EMAIL`, `ANCHOR_MANAGE_PWSHA` (mode 600); the next deploy replaces the VM copy | deploy copy checked (key names only) |
| D-v2-9 | Jev in shadow ran the decider on the request path (~40 ms per decision, unused) and paid a ~1.5 s cold start on the first decision | shadow decisions run on a background worker (0.3 ms on the request path); the model is pre-warmed at start and when Jev is switched on | p4e 16, 17; `research/phase4/TIMING_DIAGNOSIS.md` |

### 3.4 Pre-cutover list

| ID | Item | Status |
|---|---|---|
| PC-1 | Poster launchd job fails at every 09:00 run (macOS blocks launchd from the Desktop) | v2 runs the poster from Odin's own scheduler (project task, daily 09:00, owner approval kept). Removing the old launchd job is an owner step at cutover (Phase 8 list) |
| PC-2 | Generic-reply detector | done (pc2) |
| PC-3 | Relay-key fingerprint on the desktop | done (Settings) |
| PC-4 | Secure phone approvals through the Anchor | **done in v2** (section 6) — pc4 25/25, flutter 15/15 |
| PC-5 | Brain CORS `*` | done (origin lock `app://odin-desktop`) |
| PC-6 | Read the live Anchor logs for Android clients | needs a read-only look at the VM — asked at the Anchor step (Phase 8) |

## 4. Jev — the local decider

### 4.1 Design

Jev answers five closed decisions that already exist in Odin: **mode** (direct / orchestrate), **specialist**,
**read/change**, **QA gate**, **agent nature**. A frozen Qwen2.5 model (0.5B active, 1.5B kept) runs in MLX on the Mac;
Odin's standing context (specialists, rules, agents, projects; about 925 tokens) is processed once and kept as a
key/value cache (170 ms to prepare with 0.5B). Each decision feeds only its short suffix; the hidden state of a chosen
layer goes to a small per-decision MLP head (256 units). Probabilities are temperature-scaled; below the fallback
threshold, for a disabled class, or when the request has an owner exclusion ("do not", "only", "read-only"), the case
goes to the normal LLM path. Every Jev decision is logged.

**Normal / Jev toggle:** desktop Settings (or `ODIN_DECIDER=jev|normal` for the environment script, or
`POST /settings/decider-mode`). Normal is exactly v1 behaviour (the decider is never called; test p4e).
**Authority:** `shadow` until the owner's labels are applied — Jev runs and is logged, the LLM decides.

### 4.2 Training

836 synthetic training examples generated per decision schema; heads trained with class weights; layer chosen on the
synthetic validation split (0.5B: mean of layers 16–24; 1.5B: layer 24); thresholds and calibration fitted on generated
data are **never used live**. Independent ground truth from the logs: 42 strict and 67 extended read/change cases (the
logs hold only 176 unique owner messages, so this is the maximum without labels), 39 mode cases, 7 QA cases.

### 4.3 Measurements (provisional)

| Decision | Model | n | Production path | Jev | McNemar p | Verdict |
|---|---|---|---|---|---|---|
| Mode | 0.5B / 1.5B | 39 | 100.0% [91.0, 100.0] | 100.0% [91.0, 100.0] | 1.000 | non-inferior |
| Read/change (strict) | 0.5B | 42 | 83.3% [69.4, 91.7] | 83.3% [69.4, 91.7] | 1.000 | non-inferior |
| Read/change (strict) | 1.5B | 42 | 83.3% | 88.1% [75.0, 94.8] | 0.625 | non-inferior (not significant) |
| Read/change (extended) | 0.5B / 1.5B | 67 | 74.6% (router and Claude) | 80.6% / 83.6% | 1.5B p=0.07 | non-inferior |
| QA gate | both | 7 | 71.4% | 71.4% | 1.000 | head off (too few labels) |

Latency per decision: mode 28 ms (Jev) vs 10.7 s (LLM); read/change 24 ms (Jev) vs 906 ms (router) vs 10.9 s (Claude).
Real scenarios on the isolated copy (2 paired repetitions, paused by the owner): chat turn median 20.4 s (Jev, all 12
decisions fell back in shadow) vs 35.3 s (Normal); project run median 171 s (Jev) vs 124 s (Normal) with the same mode
accuracy (100%). End-to-end time is dominated by the agents' own work, so faster decisions do not yet show as faster
runs — this is reported as measured.

### 4.4 Statistics

Every accuracy comparison carries a 95% Wilson interval and an exact paired McNemar test; "best" is used only when
p < 0.05, otherwise "non-inferior" (or "inconclusive" when lower but not significant). Calibration: ECE before/after
temperature scaling per decision (target < 0.05), reported on the synthetic validation split and the real test split.

### 4.5 After the owner's labels

`research/phase4/after_labels.sh` runs, in this order: layer choice on the real validation set → temperature scaling →
thresholds → head-to-head; then the real-scenario head-to-head runs once (it uses the Claude plan, so it is asked
first). Only that run may give Jev live authority.

## 5. Paper v1 targets and what was done for them

| ID | Rule | How v2 keeps it |
|---|---|---|
| PP-1 | Paper v1 frozen | `research/paper-v1/frozen-state` is a file-exact copy; fingerprint re-verified in v2 (2,217 files OK); never edited |
| PP-2 | v2 in Normal mode reproduces paper v1 | regression 32/32 + f43 legacy900 byte-identical; the reproduction check before cutover runs with `ODIN_AGENT_RULES_MODE=legacy900` |
| PP-3 / PP-4 | Jev results go to paper v2 only | `research/paper-v2` (draft, every number marked provisional) |
| PP-5 | Paper v2 never changes paper v1 | separate folders |
| PP-6 | Both papers kept as separate folders, never deleted | `research/paper-v1*`, `research/paper-v2` |
| PP-7 / PP-8 / PP-9 | Submission copy with approved description corrections and layout fixes | `research/paper-v1-submission` (numbers unchanged; 9 pages each) |
| PP-10 | Paper-v1 runs use `legacy900` | documented in README and enforced by f43 |

## 6. PC-4 — secure phone approvals (new in v2)

The phone reaches the Mac only through the Anchor (VM), which is treated as untrusted. A phone decision is applied only if:
the phone is **paired** (its Ed25519 public key registered with a proof of possession) and the owner **trusted** it on the
desktop after comparing the fingerprint on both screens; the decision is **signed** by that key; the signature covers a
**digest of the exact request the phone showed** (id, project, kind, title, summary, folder, every file action/path/content
and every command — the Mac recomputes it from its own record, so a changed or different request is refused); it is
**sealed** to the Mac's relay key (the Anchor sees only ciphertext); it is **fresh** (15-minute window) and **used once**
(nonce + envelope replay guard); it is for a pending request (never a key request, never "approve all"). Decisions are
recorded as owner / phone with the device id (F-45). Trust and revoke exist only on the desktop (Settings ▸ Paired phones).

**Anchor sign-in for web and mobile.** The web app and the phone never carry the Anchor API key (it would be readable
inside the web bundle). They sign in with a Manage session (owner email + password + a one-time code shown on the
desktop) and each client type must be allowed by the owner; the Anchor accepts a request with either the secret API key
(poller, desktop, third parties) or a valid session from an allowed web/mobile client. Proven by
`_v2/cutover/anchor_flat_test.sh` (no key → 401; web without a session → 401; real session → 200; forged → 401).

**Sign-in exactly as in v1, with nothing to type.** v1 kept the Manage password and the Anchor key as plain text inside
the desktop app's source; v2 keeps them out of the source and the DMG. The Manage password now lives in the owner's
local `.cred` (`ANCHOR_MANAGE_PASSWORD`, never deployed; only its hash `ANCHOR_MANAGE_PWSHA` goes to the VM) and in the
macOS Keychain, from where the desktop's "🔗 Anchor" window shows email, password and the one-time code with Copy
buttons — the same window as v1. `odin_secrets.py keychain` generates the password if it is missing and never prompts;
`rotate` generates a new key and a new password itself (timestamped backup first). The flow is unchanged: Get code on
web/phone → the desktop button blinks → copy → sign in → 1-week session, 30-day remembered device
(`_v2/cutover/signin_flow_test.py`).

## 7. Build, run and deploy (summary — details in README.md)

* Environment (local, no deploy): `bash ~/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2/shells/development_full_checker.sh`
* Production (Anchor deploy, production links, mobile): `bash ~/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2/shells/production_full_checker.sh`
* Desktop DMG: `bash ~/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2/shells/build_desktop_dmg.sh`
* Re-proof suite (isolated): `bash _v2/iso/run_suite.sh <label>`
