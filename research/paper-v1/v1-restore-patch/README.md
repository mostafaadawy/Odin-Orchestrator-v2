# v1 restore patch (F-42) — for the owner to decide

Folder: `odin-v2-staging/research/v1-restore-patch/` (outside v1). Nothing here has been run on v1.

| Step | Command (run in this folder) |
|---|---|
| See exactly what would change (writes nothing in v1) | `python3 v1_restore.py` → summary + `dry_run_diff.txt` |
| Apply (backs up each file first) | `python3 v1_restore.py --apply` |
| Undo the last apply (only files not edited since) | `python3 v1_restore.py --undo` |

- Source: v1's own git commit `06a6ddb` (2026-07-18). Touches only `workspace/agents/*/capability.md`. Merge only: no existing line is changed or deleted. No git commit.
- **Caution 1:** v1's code still has the G10 bug. The triggers listed in the G10 report (a new project with an existing agent, adding an agent to a project, a self-hiring run, accepting "add QA", editing an agent or saving a rule in a project, setting up a SOC project) will wipe the restored content again.
- **Caution 2 (F-43):** v1's agents read only the first 900 characters of `capability.md` at run time, so most rules and the restored sections are on file but do not reach the agent's prompt.
