# Phase 3, fix #1 (G4 + G3): before and after report

**Applied in:** Odin-Consolidated only.
- Git: tag `phase3-start` → commit `dc51706`, tag `fix1-done`. CHANGELOG entry added.
- Code changed: 2 files, +60/−4 lines (`server/api_v2.py`, `server/workspace_mw.py`).
- **Model cost so far:** $25.91 of the $40 cap (+$7.62 for this fix).

## Results against your 5 conditions

| # | Condition | Before | After | Verdict |
|---|---|---|---|---|
| 1a | Regression suite | 31/32 (2026-10-10 runs) | **32/32**, no regressions | ✅ |
| 1b | Your end-to-end tests: `phase7_lifecycle` and `phase7_strong` | ALL GREEN (1 run each, on the pre-fix code) | **ALL GREEN, 3/3 each** | ✅ |
| 1c | Affected scenario S2 (3 new runs, r4–r6) | Delta written 1/3, registered 0/3 | **Written 3/3, registered 3/3** (manifest entry plus `dependencies` row), **resolves 3/3** | ✅ |
| 1d | Parser replay on the 6 recorded Phase 2 transcripts | 2/6 proposals found | **6/6** | ✅ |
| 2 | Existing deltas still work, including Revealer's system-generated delta | Revealer `deploy_changes.py` overlay **did not resolve**, nor did the `testing` overlay (the old code looked under `code/`) | **Both resolve** | ✅ (this was already broken in v1; now fixed) |
| 3 | New files registered under the correct owner only | No registration at all | Unit test plus 3 runs: every new file is owned by its own project; 0 rows under another owner. A file deliberately written into **another** project was indexed under that project, its real place, **and never under the approving project**; it is reported as out of scope. | ✅ |
| 4 | A project's own delta not reported as a duplicate | Flagged | **Still flagged**: `deploy/deploy-config.json` in Revealer and the sandbox projects is reported as "same filename, different content" | ❌ remains open under the audit fix (G5) |

## Inventory items touching proposals, approvals, file registration and manifests

| Item | Evidence after the fix |
|---|---|
| Proposal parser (team runs) | Replay 6/6; S2 r4–r6 created approvals 3/3 (r5 created 2) |
| Proposal → approval → background applier | Approved items applied; result now ends with `[registry] indexed=2 deltas=[…]` |
| Inline (pre-authorized) apply path | Same registration call added. **Not exercised by a run** in this fix (no pre-authorized project); it will run in Phase 7. |
| Chat proposal → real approval (`api_v2` ~l.3538) | Uses the same parser, so it inherits the fix. **Not exercised by a run** yet. |
| Middleware door, owner-scope redirect, promotion, foreign-ref repoint, `resolve_capability` | `phase7_strong` 3/3 green |
| Create/delete lockstep, exact-baseline restore | `phase7_lifecycle` 3/3 green |
| Placement and owner-scope rules, live endpoints | Regression 32/32 |

## New findings from these runs (not caused by the fix)

1. **An approval I did not give was executed.**
   - In S2 r5 I approved one proposal (`8206a5ef`). An older pending proposal for the same project (`dc13fbd7`) was approved 34 seconds later, with no note, and then applied.
   - **Most likely cause:** the auto-continue step after an apply posts a message, and the chat rule "saying approve approves ALL pending" (`api_v2.py` l.3322–3327) matched it.
   - Both proposals contained the same two files, so nothing harmful happened.
   - This is a **gate-bypass risk**, added as F-23 for your decision.
2. **Agents add a local read-only command to their proposals** (`deploy_changes.py scan`). My test harness only auto-approves file-only proposals, so I approved r5 and r6 by hand: the command is local and read-only, no VM, shims active. This is a harness note, not a system defect.
3. **Files written by the approvals store are still unindexed** until the audit heals them: `data/jsons/approvals.json` in r6 (F-07).
4. **The "Needs fix" review was still marked passed** in all three S2 runs. That is fix #2 (G1), next.
5. **Name vs id (F-08):** one replayed proposal (S1 r1) targets `supabase-customers-r1`, a folder named after the project name, not the project id.

## Test notes (for honesty)

- **The first runs of your end-to-end tests failed both before and after the fix,** identically. The throwaway roots did not match their database: the workspace had the 12 Phase 2 test projects, while chats and logs were missing.
- With a consistent starting point (the workspace as of the database dump, and the audit converged first, identically for before and after), both tests are green. The fix did not change any result.
- Raw logs are in `_consolidation/results/`:
  - `fix1_tests*.log`, `fix1c_*` and `fix1v_*`;
  - `fix1_before.json`, `fix1_after.json` and `fix1_post.json`;
  - `S2_r4–r6.json`.
