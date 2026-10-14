# Phase 3, fix #2 (G1 false success): before and after report, revision 2

**Applied in:** Odin-Consolidated only.
- **Git:** `fix2-start` (dc51706) → fix #2 `e801cfe` → #2b `67deac5` → **#2c `6bc4ec3`** (fixed verdict field) → **#2d `5429603`** (waiting path) → **#2e `f902e74`** (text net guards PASS only). Tag **`fix2-done` = f902e74**. A CHANGELOG entry for each.
- **Code:** `server/api_v2.py` and `server/soc_run.py`. No database, folder or file-format change. The `done` and `step_done` events gain an `outcome` field (additive).
- **Model cost:** $11.01 for fix #2. **Total $36.92 of $40.** Paid runs are stopped until you set the new cap.
- **Paper v1 fingerprint (2,217 files):** re-checked after all tests. **Unchanged.**

## How pass/fail is decided now (your two changes)

1. **The review must end with a FIXED field:**
   `VERDICT: {"verdict": PASSED | NOT_DONE | WAITING_FOR_APPROVAL, "evidence_files": [...], "reason": "..."}`
   A missing or invalid field counts as NOT_DONE.
2. **PASSED is accepted only when the evidence agrees:**
   - every listed file exists;
   - each file was created or changed **during this step**;
   - each file is **registered in odin_core** (workspace files), or lies in the project's own folder;
   - a build or write task needs at least one such file;
   - the audit eye is clean;
   - QA passed, if it ran.

   Otherwise the outcome is NOT_DONE, with the reason recorded.
3. **WAITING_FOR_APPROVAL** is accepted only when an approval for this project was created during the step and is still pending. The run then ends **"⏳ Waiting for your approval — <member> (<approval id>)"**.
4. **Text check:** kept only as a safety net. "Needs fix" anywhere in the review blocks a PASSED claim.

## Results

| Check | Result | Verdict |
|---|---|---|
| **Clean pass, live** (S7: Fullstack + QA, owner pre-authorized, small local Python task) | **r1 and r2 both PASSED.** QA really ran `python -m unittest` (8 tests, OK). The files exist, were written in the step and are registered; I re-ran the tests myself: OK. | ✅ |
| **Waiting path, live** (S8: same task, NOT pre-authorized) | **r3: "Waiting for your approval — Fullstack (2b841d68b150)"**, one proposal and no duplicates. r1 and r2 found two more defects, fixed as #2d and #2e (below). | ✅ after #2e |
| **Not-done path, live** | S2 r7, S4 r5, S4 r6, S1 r4: all ended not done, consistent with their reviews | ✅ |
| Regression suite | **32/32** before and after | ✅ |
| Your end-to-end tests | `phase7_lifecycle` and `phase7_strong`: **ALL GREEN, 3/3 each** after; 1/1 before | ✅ |
| Unit checks (no cost) | Fixed-field and evidence checks: 28/28. Earlier checks: ALL PASS (77 real reviews, SOC, engine guard). | ✅ |
| History re-read | Phase 2: 14/15 runs falsely "passed" before. v1: 7 of 11 "✅" claims. None could pass now (no valid verdict field plus evidence). | ✅ |

## Defects found and fixed during these tests

| Fix | Found by | Problem | Fix |
|---|---|---|---|
| #2b | S4 r4 | A review that opened "Confirmed via filesystem…" and then said "Needs fix" was read as passed | Superseded by #2c (fixed field) |
| #2d | S8 r1 | A proposal waiting for approval was treated as "zero files". It was re-proposed on every retry (**3 duplicate approvals**) and the run ended "Incomplete". | A pending approval created in the step stops the retries, skips the build halt and the QA run, and is named to the reviewer |
| #2e | S8 r2 | The reviewer wrote "Needs fix:" (the prompt offered no other opener) while its field correctly said WAITING; the text net overrode it | The text net now guards PASSED only; the prompt offers a "Waiting:" opener |

## ⚠ New safety finding (not caused by fix #2): F-32, high priority

**In a pre-authorized run, the words "no VM" or "no deploy" in the goal trigger the Azure firewall refresh.** This includes the NSG update and the **ufw rotation** (`deny 22`, re-adding 80/443), which breaks your dry-run rule.
- **Cause:** `api_v2.py` l.1077 does a keyword match on "vm" and "deploy". It is the same family as G2.
- **In the copy:** the shims blocked every `az` call (logged in `_isolation/blocked_calls.log`). **Nothing reached Azure.**
- **In v1 with real credentials:** a local-only pre-authorized task that says "no VM" would run these commands against production.
- **Recommendation:** fix it together with G2 (step 3.4), before any other G-item. **Your decision.**

## Still open and flagged

- The SOC changes (CH4-1, CH4-4) are proven by unit tests only. They need the VM, so they are not run live.
- **Deploy override:** not exercised live (no VM).
- **S4 r4's false pass** from before #2c could not happen now (no valid field plus evidence). It was not re-run, to save budget.
- Pending approvals left by the tests (S4 r6 ×2, S1 r4, S8 r1 ×3, S8 r2, S8 r3) are untouched. They will serve fix #3's test.
- **Read-only tasks:** a task with no build or write verb can pass with no files, if the review says PASSED and the audit is clean. Tell me if you want a stricter rule there.

**Next, after your approval:** fix #3 (approval bypass). Then the inventory corrections, one at a time.
