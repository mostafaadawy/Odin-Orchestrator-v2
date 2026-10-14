# Phase 3 — G5 + F-36 (duplicate rules)

**Git:** `g5-start` (acf1536) → **`g5-done` (11a4a47)**. CHANGELOG updated. No model calls (cost 0). v1 untouched. Paper v1 fingerprint unchanged.

**Pre-flight:**
- Copy server health: 200.
- Auth: plan login only, no paid route.

## G5: a project's own delta is never called a duplicate
A file counts as the project's own delta when it is any of these:
- a registered overlay in the project's dependency manifest;
- a file that declares "delta over shared capability: shared/…" (and the base exists);
- a per-project input that a shared capability reads from every project. For example, `deploy/deploy-config.json` is read by `shared/infra/deploy_changes.py`. This is detected from shared code, not from tests.

**Live copy:**
- Before the fix, `deploy-config.json` was flagged in 6 projects.
- Now it is not flagged.
- The remaining flagged duplicates are real: the S7/S12 `calc` files and the S10 `status.md`.

## F-36: duplicate cleanup
- **Which copy is kept:** the OLDEST *registered* copy, under its **original name**. It is no longer the alphabetically first copy.
- **Category:** decided by location and content.
  - A file in `tests/`, or real test code → `testing`.
  - A file in `deploy/`, or a name with the word "deploy" → `infra`.
  - Everything else → `utils`.
  - A helper named `dup_test_…` or `latest_prices.py` is no longer filed under testing.
- **Safety fix found by the test:** if `shared/<category>/<name>` already held DIFFERENT content, the old code **deleted the project's copy** (data loss). It is now FLAGGED, and nothing is lost.

## Tests
| Check | Before | After |
|---|---|---|
| `g5_test.py` (11 checks) | 6 FAIL, including the data loss on a name clash | **ALL PASS** |
| G6 / G6b / G8 / G8b tests | — | all still PASS |
| Regression | — | 32/32, with and without the migration |
| phase7 lifecycle / strong | — | ALL GREEN (3/3 with the migration; 1/1 without) |
