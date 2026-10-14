# Phase 3, step 3.5 — G6 (dangling reference after an audit heal): before and after report

**Applied in:** Odin-Consolidated only. v1 untouched.
- **Git:** `g6-start` (470913b) → **`g6-done` (b272c99)**. CHANGELOG entry added.
- **Code:** `server/workspace_mw.py`, `server/workspace_audit.py`.
- **Model cost:** $0 (no LLM). Paper v1 fingerprint: unchanged.

## What was wrong (S6, 2 of 2 runs)

1. **Heal deleted the file a reference pointed to.** The duplicate heal kept one copy (the first in alphabetical order, hubspot's `dup_test_rN.py`), moved it to shared, and deleted revealer's original `helper_s6_rN.py`. A foreign reference to that original was not rewritten.
2. **The audit then reported 0.** The foreign-reference heal failed because the file was gone. The scan skipped any reference whose target did not exist, so the broken reference was invisible.

## The fix

- **Every move is recorded,** in the existing `workspace/history/mw-corrections.jsonl` with kind "move". No new file is added.
- **References follow every move.** When a file moves to shared, every project or agent file that referenced it is rewritten, not only the owners the caller named. Those owners get a dependency row.
- **The form of each reference is kept.** A `workspace/...` reference stays a `workspace/...` reference, so it still resolves.
- **Records are never rewritten.** This covers `data/`, `history/`, `logs/` and chats.
- **A new audit check, "dangling-ref", is a hard issue.** It fires when a code or config file references a file in a real project or in shared/ that does not exist.
  - If a recorded move exists, heal repoints the reference.
  - Otherwise heal **FLAGS it for you** and does not guess.
  - Not checked: `.md` notes (they may name planned files), records, secret dotfiles (`.cred`, `.auth`), and absolute paths.

## Results

| Check | Before | After |
|---|---|---|
| `g6_test.py` (11 checks, throwaway copy) | **6 FAIL**: both referrers dangling after heal; dangling reference not reported; late reference not repaired | **ALL PASS** |
| False alarms on the clean baseline copy | — | **0** |
| S6 r4 (no LLM) | — | The reference is rewritten to `workspace/shared/testing/dup_test_r4.py` and resolves |
| Old S6 r2/r3 leftovers in the copy | Audit reported **0** | **Reported as 2 dangling-ref**; flagged (no recorded move) |
| Regression | 32/32 | **32/32** |
| phase7_lifecycle / phase7_strong | green | **ALL GREEN 3/3 each** |

One problem was found and fixed during testing. The first version wrote a new `moves.jsonl`, which broke phase7_strong's exact-baseline check (+1 file). Moves now go into the existing middleware log.

## Flagged for you

- **New item F-36:** the duplicate heal keeps the alphabetically first copy *and its name*. In S6 the original helper ended up as `shared/testing/dup_test_r4.py`: it is a helper, but it is filed under "testing" because of the copy's name. I propose to keep the original (the oldest, registered copy) and its name. I suggest handling it with G5.
- The two S6 r2/r3 leftovers are test debris. I left them in place as evidence.
