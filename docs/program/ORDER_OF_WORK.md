# ORDER OF WORK: Odin v2 program

**CONFIRMED by the owner 2026-10-11.** Decisions at confirmation:
1. The dry-run fix stays in step 3.11, tested in the copy with "would run" logging and proven at cutover. It follows the exact rule: a dry run may ONLY replace the single SSH allow rule for the current IP; nothing else changes.
2. The audit fixes (step 3.5) are done ONE AT A TIME, each tested and approved separately.
3. Step 3.12: the decision items are presented ONE AT A TIME, in plain words: what it is, the risk, and a recommendation.

**Date:** 2026-10-11. **Budget:** $25.91 of $40 spent.
**Source of truth:** `REQUIREMENTS_TRACKER.md`. Every item below has a tracker ID. Nothing was dropped. The only removals are the old P4-1…P4-4 (cloud Jev), which your decision replaced.

Each step stops for your approval. Each fix runs under the same conditions as fix #1:
- the regression suite;
- your end-to-end tests (`phase7_lifecycle`, `phase7_strong`);
- the affected scenarios;
- the inventory rows it touches;
- a before/after report, with the tracker updated.

## Done

| Step | Items |
|---|---|
| Phase 0 | P0-1, P9-4 |
| Phase 1 | P1-1…P1-8, F-12, F-13 |
| Phase 2 | P2-1 |
| Phase 3, fix #1 | G3/G4: verified (`fix1-done`). F-07 is partly covered and stays open. |

## Phase 3: remaining work, one at a time, in this order

| # | Item(s) | What | Notes |
|---|---|---|---|
| **3.2** | **G1 + F-18** | **Fix #2: false success.** A run ends as passed ONLY when the review confirms the work, with evidence. | **Approved.** All 42 chat mismatches are its acceptance checks. |
| **3.3** | **F-23** | **Fix #3: approval bypass.** "Approve" applies only to the proposal named or replied to. Only your messages can approve, never Odin's own messages, follow-ups or agents. Older pending proposals stay pending. | Includes a test that reproduces the 34-second case and proves it cannot happen again. |
| 3.4 | G2 | "Do not deploy" wrongly blocks local file work (`_touches_vm`) | |
| 3.5 | G6, G8, G5, G7, F-07 | **Audit fixes:**<br>• G6: duplicate plus foreign reference leaves a dangling reference.<br>• G8: no record of the creating agent.<br>• G5: a project's own delta is flagged as a duplicate.<br>• G7: `tests/` is not scanned.<br>• F-07: approval writes are left unindexed. | **One at a time**, each tested and approved separately (confirmed) |
| 3.6 | G11 | Build step goes to DevOps instead of Fullstack | |
| 3.7 | G12 | EasyPost is recommended per project, never auto-added | Already decided |
| 3.8 | G9, G10, G13 | **Agents and credentials:**<br>• G9: the credential choice is not recorded.<br>• G10: reuse overwrites a shared role.<br>• G13: strengthening an agent is not done. | |
| 3.9 | F-06, F-08 | **Lookup:**<br>• F-06: main chat does not look up existing capability.<br>• F-08: name vs id mix-up. | |
| 3.10 | F-14 | **Security:** move the Anchor password and key out of the desktop code and DMG into the Keychain | Decided |
| 3.11 | P8-2 (code part) | Make `deploy.sh` dry runs obey your rule: ufw l.183–209, sshd l.223–246, baseline re-date l.376–394. Tested only with "would run" logging. | **Confirmed:** fixed here and proven at cutover (P8-2). Only the single SSH allow rule for the current IP may be replaced; nothing else changes. |
| 3.12 | **Your decisions needed** | F-20 (token covers only some routes), F-21 (IPs sent over plain HTTP), F-04 (Anchor key in plain text), F-03 (Android?), F-05 (missing defects doc), F-10 (automatic rule update?), F-11 (50% threshold), F-16 (generic-reply detector?) | Kept open. Presented to you **one at a time** (what it is, the risk, a recommendation). Each one approved for fixing gets its own step. |
| 3.13 | Phase 3 gate | Full regression and end-to-end tests; tag `phase3-done` | Your approval starts Phase 4 |

## Phase 4: local decider (replaces cloud Jev, P4-0). Stop after each sub-phase (P4-S)

| Sub-phase | Items |
|---|---|
| 4a: decision points, LLM baseline, closed vs open | P4a-1…3 |
| 4b: RAM, MLX/MPS, one full-precision 0.5–3B model, no quantized training | P4b-1…3 |
| 4c: frozen base, decision head, calibration, prepared context, LLM fallback | P4c-1…5 (early exit P4c-6 parked) |
| 4d: data from real context, your label review, split plus leakage check, cost first | P4d-1…4 |
| 4e: Normal / Jev toggle in the React desktop app (default Normal), logging | P4e-1…4 |
| 4f: head-to-head, 3 repetitions, plus real scenarios; acceptance rule | P4f-1…3 |
| 4g: paper tables and charts into research (paper text not edited) | P4g-1…2 |
| Into v2 | P4-5 |

## Phase 5: build v2

| Item | What |
|---|---|
| P5-1 | Blind copy of the original v1 |
| P5-2 | Behaviour baseline |
| P5-3 | Integrate in order: paper code, approved fixes, decider |
| P5-4 | Every change reaches every client |
| P5-5 | SOC playbook, history and charter (no `ACTIVE-RUN.lock`) |
| P5-6 | Feature preservation proven by run |
| P9-3 | Paper material into `v2/research` |
| F-15 | Desktop sync `since` |
| F-17 | Schema doc fix |
| F-22 | Hard-coded Anchor URL and callback |
| F-04 | If approved in 3.12 |

## Phase 6: build and run parity

P6-1, plus F-01 (missing e2e target), F-02 (`phase_ctl` path), F-09 (`/sim` log) and F-19 (DMG signing).

## Phase 7: end-to-end tests and a real project

P7-1…P7-4. This also re-runs the paths fix #1 could not exercise: inline apply and chat-proposal approval.

## Phase 8: cutover (your approval at each step)

| Item | What |
|---|---|
| P8-1 | Your certified VM deployment process |
| P8-2 | Dry-run proof |
| P8-3 | Fingerprint, backups and rollback |
| P8-4 | Schema changes |
| P8-5 | Real `.cred` |
| P8-6 | Anchor runs from v2 |
| P8-7 | Back up Odin.app and its 240 MB of app data |
| P8-8 | Post-cutover test, with rollback on failure |
| P8-9 | You change the Anchor password and rotate the key |

## Phase 9: cleanup

P9-1 (never-delete list), P9-2 (checklist per folder), P9-3 (paper material checked first) and P9-5 (README).

## Standing rules (apply to every step)

- No production database, cloud, VM, SSH or push before Phase 8. Shims stay on for every process.
- Never modify v1.
- **R-ZC, ZERO EXTRA COST (2026-10-11, supersedes every dollar cap):** every model call runs under the owner's Claude plan login only; auth checked before each run; dollar figures are "reported usage, not charged"; watch the plan's usage limits; Phase 4 uses Qwen trained locally on the M4; anything that needs a paid service stops for the owner first.
- Git tags and a CHANGELOG entry for every change.
- Never mark a feature missing from a code search alone.
- Hidden features are required.
- The paper is due 30 October.

## PAPER PROTECTION RULE (owner, 2026-10-11): applies to every phase above

- **Paper v1** is frozen as `paper-v1` (PP-1, PP-5).
- **Before cutover,** v2 in Normal mode must reproduce paper v1's measurements (PP-2). The check runs in Phase 7 and is a gate for Phase 8.
- **Phase 4 results** go to a separate `paper-v2` folder (PP-3, PP-4).
- **Phase 9:** both papers go into `v2/research` as separate folders and are never deleted (PP-6).

## Update 2026-10-11 (owner)

- **Fix #2:** approved.
- **NEXT:** step 3.2a, **F-32 + G2 together** (VM-keyword false triggers), before any other item.
- **Then:** step 3.3, fix #3 (approval bypass).
- **Cost cap:** $100 total for Phase 3. Phase 4 is capped separately later and planned small: about 1,500 training examples and fewer scenarios (updates P4d-1 and P4f-2 sizing).

## Update 2026-10-11 (owner): after fix #3

- **Fix #3:** approved.
- **Next steps, in order:**
  1. **3.3a** — The 11 inventory corrections, presented ONE at a time (no cost).
  2. **3.3b** — F-33: confirmation step for "Approve all".
  3. Then 3.5 onward (audit fixes one at a time, …) as above. Step 3.4 (G2) was done together with F-32.

## R-DP DEPLOYMENT PERMISSION RULE (owner, 2026-10-12) — global, in force
1. Real deployments ARE allowed for the TEST / SANDBOX projects (e.g. Revealer and the other test/sandbox projects) so their end-to-end tests run fully.
2. NEVER deploy, sync, build, migrate, restart or change anything for the real deployment projects targeting **RBO Staging** or **RBO Production**: no files, services, database, ports, nginx config or folders that belong to them. Read-only checks only. RBO Staging on the VM = `~/bendcore` (backend) and `~/organics` (frontend), their services and databases — protected: never write, sync, build, migrate, restart or delete anything in them.
3. Every allowed sandbox deploy (same VM as RBO Staging) must: change the firewall ONLY by the owner's single dynamic-IP rule (no ufw reset, no change to ports 80/443); never restart shared services (nginx, sshd, the staging services) or touch the staging folders and database; deploy only into the sandbox project's own folder and port; take an RBO Staging PRODUCTION FINGERPRINT before and after, and STOP immediately if anything in it changed.
4. The copy has NO real VM credentials, by design. Before the FIRST sandbox deploy: state exactly which credentials and which targets are needed, how they stay out of git and logs, and WAIT for the owner's approval.
- F-25 (guidance text `~/Bendcore` → `~/bendcore`) changes only two text files in the copy; it touches nothing on the VM.
