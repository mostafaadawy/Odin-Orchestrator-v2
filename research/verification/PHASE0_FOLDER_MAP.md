# Phase 0 — Odin folder map (read-only)

**Date:** 2026-10-11.

**Method:** run through your terminal bridge (`odin-bridge/phase0_map.sh` and `phase0_unique.sh`), using `du`, `find`, `git log` / `git status --no-optional-locks`, `diff -rq`, `cmp` and `unzip -l`. Nothing was modified. No git tags were created, because Phase 0 has no working folder.

## 1. Folders that belong to Odin

| # | Folder (under ~/Desktop) | Purpose | Last commit / newest file | Size | Holds that no other folder holds | Differs from the original how |
|---|---|---|---|---|---|---|
| 1 | `AiAgentWorkSpace/Odin-Orchestrator` (**v1, the original**) | Production system: server, orchestrator, desktop (Electron), `odin_app` (Flutter web and mobile), dashboard, voice, shells, live workspace | `af2cbd8` 2026-08-22 "done"; 73 commits; remote `github.com/mostafaadawy/Odin-Orchestrator`. Newest file 2026-10-10. 8 runtime data files modified, no code. | 4.9 GB, 75,523 files | **Real credentials** (`oth/.cred` 12 lines, `.auth`, `connector_keys.json`). Full git history and GitHub remote. **Live workspace data** after 2026-10-06 (newer than every copy). `.venv` (1.5 GB), `desktop/node_modules` (523 MB), **Flutter build outputs** `odin_app/build` (1.1 GB), **DMG** `desktop/release/Odin-1.0.0-arm64.dmg` (96 MB, built 2026-08-01). | — (reference) |
| 2 | `AiAgentWorkSpace/Odin-Isolated` (paper copy) | Isolated copy used for the paper study (2026-10-06) | `86cf630` 2026-10-06; 2 commits, no remote. 26 uncommitted changes (the P2 work). | 452 MB, 5,575 files | **Original, un-repathed paper record**, with paths pointing at Odin-Isolated as cited in the paper. `_research/`: 01–05 analysis docs, `DECISIONS.md`, `deliverables/` (the final3 LaTeX source, named and anonymous PDFs, replication .tgz files), `results/` (raw logs and cost ledgers), `exp/`, `regression/`, `promotion/`, `rescued/`. `_isolation/` (isolation record and shims). **P2 code** (`scope_hook.py`, `door_cli.py` and 4 edited files), uncommitted. Exactly one file exists only here: `workspace/projects/revealer-6978/tests/project_test.py` (moved to shared by scenario S6 in Consolidated). | Copy of v1 at `af2cbd8` with no credentials; paths, databases and ports remapped; 5 schedules disabled; plus P2. |
| 3 | `AiAgentWorkSpace/Odin-Consolidated` (verification copy) | Phase-2 scenario verification | `a4de1ec` 2026-10-10; 5 commits, no remote. | 589 MB, 10,854 files | `_consolidation/` (scenario harness, 18 run results, cost ledger, remap log). The 3-commit history of the consolidation. The workspace state after 18 runs (about 12 test projects plus promoted test files). Private PostgreSQL data under `_research/tmp/pg` (git-ignored). The curl/nc/wget VM-guard shims. | Copy of Isolated, with every path, database and port repathed (304 files), plus the run results. |
| 4 | `AiAgentWorkSpace/odin-bridge` | Copy of your `agent_terminal_bridge.sh`, so v1's folder is never written | No git; newest 2026-10-11 | 52 KB | The **log of every command I ran on your Mac** (`workspace/logs/agent_term/OUT.log`), plus the Phase 0 scripts. | The bridge script is identical to v1's; only the location differs. |
| 5 | `AiAgentWorkSpace/Resulted Papers and Documents` | Earlier paper material (July) | No git; newest 2026-07-23 | 1.9 MB, 22 files | **Everything in it exists nowhere else:** `odin_paper.tex`/.pdf/.docx (the earlier paper), `engineering_journey.*`, `venue_submission_guide.*`, and `Social Media/` (LinkedIn and Instagram posts, images, `make_images.py`). | Not in any Odin folder. |
| 6 | `AiAgentWorkSpace/RedBerry-Continuous-SOC` | Earlier SOC working files | No git; newest 2026-08-02 | 24 KB, 4 files | `soc/playbooks/fake-user-app-abuse-hunt.md`, `soc/knowledge/incident-history.md`, an investigation charter and `ACTIVE-RUN.lock`. **None was found by name in v1.** | — |
| 7 | `AiAgentWorkSpace/AiAgentWorkSpace.zip` | Archive snapshot of #1, #5 and #6 | 2026-08-01 | 1.7 GB | A point-in-time v1 from 2026-08-01, including the then `.venv`. | Older than v1 HEAD (v1 committed through 2026-08-22). |
| 8 | `AiAgentWorkSpace/odin-cto-brain.skill` and `zi8SAsI7` | CTO-brain skill package (`SKILL.md`) | 2026-06-21 | about 2 KB each | The packaged skill. The two files are different zip encodings (deflate vs store) of the same single `SKILL.md`. | — |
| 9 | `/Applications/Odin.app` | **Installed desktop app** (from the DMG) | Version 1.0.0, installed 2026-08-01 | — | The running executable. | Built from v1 at that date. |
| 10 | `~/Library/Application Support/odin-desktop` | Desktop app data (cache, cookies, local storage) | — | 240 MB | **App state and local storage for the installed Odin.app.** | — |

## 2. Folders Odin depends on (outside the Odin folders)

| Folder | Role | Note |
|---|---|---|
| `~/Desktop/Odin` (872 MB, 3,243 files, newest 2026-09-02) | Working copy and `.git` baseline of the organics deploy targets. v1's UI and deploy scripts point here. | **Must stay** while v1 or v2 deploy organics. It is an external reference, not Odin code. |
| `~/Desktop/Odin Testing` (92 MB, 5,291 files, newest 2026-10-06) | Sandbox sources (`backend-sandbox`, `frontend-sandbox`, `noteTaker`, `testing`), used by `sandbox_revealer_multiagent.py` and recorded in `e2e-report.json` | **Must stay.** Referenced by v1 test scripts. |
| `~/Desktop/VolatileWorkSpace/RBO-Staging/*` (not sized here) | Staging source that the deploy engine reads | Read-only for us. Never touched. |

## 3. Similar names, but not Odin-Orchestrator (out of scope)

| Folder | What it is |
|---|---|
| `VolatileWorkSpace/odinmarkets` (1.0 GB, git remote `odinmarkets`) | The Odin Markets website (Next.js) |
| `VolatileWorkSpace/OM` (1.5 GB) | Odin Medical Supplies sites and zip |
| `VolatileWorkSpace/mostafa-app` (1.2 GB) | The older app that the voice module was extracted from. `core-rules.md §6.3` says v1 must not depend on it. |
| `Mostafa-Career-System/output/_trash/odin-20260927T175707Z` | One `events.log.bak` from the career app |

**Odin-Keel-Research:** no longer exists. It was deleted on 2026-10-06, by your decision recorded in that session, and its rescued files are in `Odin-Isolated/_research/rescued/`.

## 4. Points that matter for later phases

- **Paper material is spread over 3 places:**
  1. `Odin-Isolated/_research` (the current paper, final3);
  2. `Resulted Papers and Documents` (the earlier paper, journey and social posts);
  3. my reports in this chat (`odin_code_verification.md`, `odin_inventory_part1.md`, `odin_scenario_verification.md`), **which are not yet in any folder on your Mac**.

  All three must go into `v2/research/` before Phase 9.
- **The live workspace of v1 is newer than every copy.** Phase 5 must copy v1 fresh, not reuse Isolated or Consolidated.
- The **installed Odin.app and its 240 MB app data** belong to v1. Phase 8 installs the v2 DMG; your app data should be backed up first.
- `RedBerry-Continuous-SOC` holds 4 SOC knowledge files that exist nowhere else. **Should they go into v2?** That is your decision.

**Phase 0 is done and waiting for your approval.** Phase 1 (the master feature inventory, read-only) is next.
