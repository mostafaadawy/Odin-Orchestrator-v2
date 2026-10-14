# Phase 3, fix #2 (G1): false success. Plan and coverage of the 42 chat mismatches

**Status:** fix #2 is approved. This plan shows exactly what it will change, and how each of the 42 mismatches is covered.
**Working folder:** Odin-Consolidated only. Tag `fix2-start` is placed once the Mac bridge is back.

## The root cause, from the code (`server/api_v2.py` l.2916–3035)

1. **The CTO review is written but never read.**
   - The review starts with "Confirmed:" or "Needs fix:".
   - A step "passes" on `qa_ok and step_clean` alone (l.2955, l.2962). The review text plays no part.
2. **When QA is off, the run always passes.**
   - `all_ok = … if qa_enabled else True` (l.2971).
   - The verdict then reads "All requirements addressed ✅", whatever the reviews said.
3. **The messages claim more than was checked.**
   - The step result always begins "✅ QA passed." when QA was skipped (l.2967).
   - The member line says "passed (QA + audit clean)" with QA off (CH4-5).
4. **A verified deploy overrides everything** (l.3002). Other members' "Needs fix" reviews are ignored.
5. **The engine-failure guard scans the reviews as well as the work** (l.2988).
   - This means a review that merely mentions an expired login can fail a good run (CH3-3).
   - It also misses a plain "401" or "authentication_error" (CH2-3).
6. **SOC findings.**
   - Findings auto-resolve when they are not seen, even when the check that finds them did not run (`soc_run.py` l.112–118; CH4-4).
   - SOC-APP-001 reads a sudo password prompt as "0 submissions" and reports "Checked and healthy" (l.260–274; CH4-1).

## The fix

1. **New `_review_verdict(review)`.** It returns `confirmed`, `needs_fix` or `unclear`.
   - Only a review that starts "Confirmed:" counts as confirmed.
   - An unclear or empty review is NOT a pass.
2. **Evidence rule.** A step passes ONLY when all of these hold:
   - the review is confirmed;
   - the audit eye found the step clean (`step_clean`);
   - QA passed, when QA is on.

   The review prompt adds one line: cite the evidence (a file path, a command output or a test result) and do **not** accept values injected into the brief as evidence (CH0-5).
3. **Run result.** `all_ok` is true ONLY when every step passed under that rule, **including when QA is off**.
   - A verified deploy still counts as evidence for the deploy step, but it no longer hides another member's "Needs fix".
   - The final verdict lists every step that is not confirmed.
4. **Honest messages.**
   - "QA passed" only when QA actually ran and passed; "QA skipped (your choice)" when it is off.
   - "passed" only under the evidence rule.
   - `write_deliverable(done=…)` uses the same rule.
5. **Engine-failure guard.**
   - It scans the members' work only, not the reviews.
   - It adds the "401" and "authentication_error" markers.
6. **SOC.**
   - A finding auto-resolves only when the check that produces it ran and reported "Checked" this run. Otherwise it stays open as "not re-checked".
   - SOC-APP-001 treats output with no parsable counts (for example a sudo prompt) as "Data unavailable", never "healthy".

**What stays the same:**
- the approval gate;
- the QA gate itself;
- the audit eye;
- the deploy verification;
- the database, the folders and the file formats.

**Behaviour change, flagged:** some runs that used to end "✅ RUN FINISHED" will now end "RUN FINISHED (open items remain)". That is the purpose of the fix. No automatic retry is added; adding one would be a new feature, and it is only done if you approve it.

## Coverage of all 42 chat mismatches

**Group A: fixed by fix #2 and tested by it (13).**

| Mismatch | Covered by fix part |
|---|---|
| CH2-11 | 1–3 |
| CH4-2 | 1–3 |
| CH4-5 | 4 |
| CH2-1 (audit flagged, review confirmed anyway) | 2 |
| CH2-3 | 5 |
| CH3-3 | 5 |
| CH0-5 | 2 |
| CH4-1 | 6 |
| CH4-4 | 6 |
| CH0-4 (member said "only GET" with no evidence) | 2 |
| CH2-7 (reboot claimed, not done) | 2 |
| CH4-3 (re-plan said the gap was closed) | 2–3 |
| CH5-1 (Zoom "live capture" claim) | 2 |

**Group B: already in your order of work.**

| Mismatch | Tracker item |
|---|---|
| CH0-3 | P8-2, step 3.11 |
| CH3-4 | P8-2, step 3.11 |
| CH1-5 (dry-run rsync and "migrat" blocked) | P8-2, step 3.11 |
| CH0-7 | G12 |
| CH2-9 | G12 |
| CH1-1 | G9 |
| CH5-4 | F-23, fix #3 |
| CH4-7 | F-23, fix #3 |
| CH2-5 | F-06 |
| CH2-6 | F-06 |

**Group C: the inventory or docs were wrong, not the system. Corrected in the inventory (11).**
- CH0-1, CH0-2;
- CH1-3, CH1-6;
- CH2-8, CH2-10;
- CH3-1, CH3-2;
- CH5-2, CH5-3;
- CH4-6.

**Group D: real defects that are not false success. Added as new tracker items (8).**
- F-24: the launchd job reinstalled after you asked for its removal (CH0-6).
- F-25: `~/Bendcore` vs `~/bendcore` in the planner (CH1-4).
- F-26: reviews applied the VM `.env` rule inconsistently (CH1-2). Your rule is needed.
- F-27: recurring runs are routed to a single member (CH1-7).
- F-28: the coverage gate re-adds tasks the brief excluded (CH2-2).
- F-29: the status-answer shortcut misfired on a complaint (CH2-4).
- F-30: the concurrency guard missed repeated requests (CH2-12).
- F-31: Revealer runs stopped at a gate with an empty reason (CH5-5).

Total: 13 + 10 + 11 + 8 = **42**.

## Tests (same conditions as fix #1)

1. **Unit checks, no model cost:**
   - `_review_verdict` on every recorded review in the chats (for example 97a2be00d782, 01dc78d976e4);
   - the run-result rule;
   - the SOC auto-resolve and SOC-APP-001 cases;
   - the auth-guard cases.
2. **Regression suite:** 32/32 must hold.
3. **Your end-to-end tests:** `phase7_lifecycle` and `phase7_strong`, 3/3 each.
4. **Affected scenarios:** a team run where the review says "Needs fix" must end NOT passed, with QA on and with QA off; a clean run must still pass. **Cost estimate: about $5–7** (about $14 left of the $40 cap).
5. **Inventory rows** touching run status, reviews, QA, the truth gate, `audit.gate_success`, the omission guard, the engine-failure guard and SOC findings.

Then the before/after report and the tracker, and I wait for your approval before fix #3.
