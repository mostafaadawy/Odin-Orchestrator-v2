# Phase 3 — G6b (your condition on G6) and the G8 plan

**Git:** `g6b-start` (b272c99) → **`g6b-done` (9b8c541)**. CHANGELOG entry added. Model cost $0. v1 untouched. Paper v1 fingerprint unchanged.

## G6b: every automatic rewrite is logged and reversible

- **One action is one batch.** A promotion, or one audit heal action, gets one batch id.
- **What is logged, for every change:** file, old path, new path, time, batch and reason. The file's previous content is kept, so the change can be undone. Logged changes are:
  - reference rewrites, including the dependency manifest entries;
  - moves;
  - removed duplicate copies.
- **Where:** the existing `workspace/history/mw-corrections.jsonl`. No new file is added.

**Commands (one command each):**
```
python server/rewrite_log.py list [--batch ID] [--last N]
python server/rewrite_log.py revert <batch>     # undo exactly that action
python server/rewrite_log.py release <batch>    # allow the audit to fix those paths again
```

**What a revert does:**
- restores every rewritten file, but only if nobody edited it since (an edited file is skipped and reported);
- moves the file back from shared and recreates removed copies;
- deletes the database rows that the action created;
- places a **hold**, so the audit flags those paths instead of redoing the fix.

### The log (live copy, S6 run 5)
```
2026-10-11T16:23:49  8ced7321f959  move          MOVED projects/hubspot-crm-operator/code/dup_test_r5.py -> shared/testing/dup_test_r5.py
2026-10-11T16:23:49  8ced7321f959  ref-rewrite   workspace/projects/hubspot-crm-operator/dependencies/manifest.json: (dependency manifest) -> + dependency on shared/testing/dup_test_r5.py
2026-10-11T16:23:49  8ced7321f959  ref-rewrite   workspace/projects/revealer-6978/dependencies/manifest.json: (dependency manifest) -> + dependency on shared/testing/dup_test_r5.py
2026-10-11T16:23:49  8ced7321f959  copy-removed  REMOVED identical copy projects/revealer-6978/code/helper_s6_r5.py (kept shared/testing/dup_test_r5.py)
2026-10-11T16:23:49  8ced7321f959  move          MOVED projects/revealer-6978/code/helper_s6_r5.py -> shared/testing/dup_test_r5.py
2026-10-11T16:23:49  8ced7321f959  ref-rewrite   workspace/projects/hubspot-crm-operator/code/from_revealer-6978_r5.py: projects/revealer-6978/code/helper_s6_r5.py -> shared/testing/dup_test_r5.py
reason (all rows): audit heal: duplicate — identical content in >=2 projects — promote to shared
```

### Revert in the live copy: `python server/rewrite_log.py revert 8ced7321f959`
- **5 changes restored, 0 skipped.** The referrer reads the original path again, the shared file was moved back, and the removed copy was recreated.
- **The next audit run** flagged both issues as "held" and changed nothing.

### Tests
| Check | Before | After |
|---|---|---|
| `g6b_test.py` (16 checks) | no log exists | **ALL PASS** |
| Revert is byte-identical to the state before the heal; the database matches the disk | — | ✅ |
| A file edited after the rewrite is not overwritten (reported) | — | ✅ |
| Revert twice, or an unknown batch, is refused; release works | — | ✅ |
| `g6_test.py` (G6 still holds) | — | ALL PASS |
| Regression; phase7 lifecycle and strong | — | 32/32; ALL GREEN 3/3 each |

**Limit:** the S6 run 4 rewrite happened before G6b, so it has no logged previous content and cannot be reverted by the command.

## G8 plan (no code yet): record which agent created each file

**Today:** the database `files` row has no creator. The audit can say what is wrong, but not who caused it (0/3).

**Plan:**
1. **Exact record at write time.** The engine already runs a hook before every Write/Edit an agent makes. The engine will pass the member name (with project and run), and the hook will record (file, member, project, run, time).
2. **Approval path.** When an approved proposal is applied, the proposal's member is recorded.
3. **Middleware writes.** `put_file` records its actor.
4. **The audit** adds "created by <member> (project, run)" to every violation it reports or flags.
5. **Test:** a scripted test with no model cost, then one small live run. The live run costs about $1–2, and I will ask before it.

**Your choice: where the creator is stored.**
- **(A, recommended)** A new nullable `created_by` column in the database `files` table. The database is the single registry. This is a schema change, so it is added to P8-4 (cutover migration: one additive `ALTER TABLE`).
- **(B)** No schema change: keep creator records in the existing middleware log only. The audit reads the log.
