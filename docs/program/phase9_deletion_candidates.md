# Phase 9 — deletion list (for the owner's YES)

Nothing is deleted without the owner's yes. Approved folders are MOVED to `~/Desktop/AiAgentWorkSpace/_to_delete/`
(the owner empties it himself). **Never touched:** `Odin-Orchestrator` (v1), `~/Desktop/misc/Odin`, `~/Desktop/misc/Odin Testing`,
the owner's local credentials files, and any folder outside these three.

## Proof that everything is in v2 (`_v2/results/phase9_coverage.txt`, re-run any time: `python3 _v2/cutover/coverage_proof.py`)

Every file is hashed (SHA-256) and searched by content in `Odin-Orchestrator-v2` (including `_archive/`).

| Folder | Size | Files | In v2 by content | Full git history kept as |
|---|---|---|---|---|
| `Odin-Consolidated` | 10 G | 4231 | **4231 / 4231 (100 %)** | `_archive/Odin-Consolidated.git.bundle` (verified) |
| `Odin-Isolated` | 452 M | 2173 | **2173 / 2173 (100 %)** | `_archive/Odin-Isolated.git.bundle` (verified) |
| `odin-v2-staging` | 15 M | 113 | **113 / 113 (100 %)** | (not a git repo) |

How 100 % was reached: v2 already held the code (replayed commits), the research (`research/consolidation`,
`research/isolated-research`, `research/paper-v1/frozen-state/Odin-Isolated`, `research/phase4`, `research/paper-v2`),
Jev models and heads. The 1003 files that were not yet in v2 (older versions of chats/logs/project files, Jev feature
cache `.npy`, test-project files, hook logs, the accident quarantine) were COPIED into `v2/_archive/<folder>/…`
(382 MB, git-ignored), so nothing is lost.

Not counted (rebuildable or scratch, not copied): `.venv` (394 M), `node_modules`, Flutter `build`/`.dart_tool`, and
`Odin-Consolidated/_research/tmp/*_before|*_after|pg` (5 G of test-run scratch copies that the suite recreates in
`v2/_v2/iso_root` every run). The `.git` internals are covered by the verified bundles.

## Kept (not on the list)
* `workspace/projects/odin-external-arms/deploy/` inside v2 — the live production deploy staging (correction 2026-10-14).
* `odin-bridge/` — the tool channel used for this work; remove only after the final handover if you want.
