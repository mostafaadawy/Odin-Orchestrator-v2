# Promotion package — for your review only (NOT applied to your real folder)

This package was built in Odin-Isolated from `git diff pre-p2`. The copy's isolation names (DB names, folder name, paths) were mapped back to the real ones. Every patch was checked with `git apply --check` against a TEMP copy of the real files (`_research/tmp/promo_verify`): all 5 apply, and the patched files compile. Nothing was written to Odin-Orchestrator.

| # | Patch | Files | What it fixes |
|---|---|---|---|
| 01 | p2a-agents-start-in-own-project-folder | server/api_v2.py, server/projects.py (`agent_workdir`) | Agents started at the repo root, so their own-tool writes landed outside the project (only 17% in the right slot at 10 projects). They now start in the project's localPath, or else its `workspace/projects/<pid>/code`. |
| 02 | p2b-owner-scope-hook | server/scope_hook.py (new), server/door_cli.py (new), server/claude_cli.py | A PreToolUse hook (the same mechanism as readonly_hook.py) applies your existing rule to the agent's own tools: read anywhere; write only in your own project; shared only through the door. It reuses `workspace_mw.route`. The door for agents is `door_cli.py promote` (= `promote_to_shared`, the audit's route). Modes: `ODIN_SCOPE_HOOK=watch` (log only), `enforce` (default), `off`. |
| 03 | p2a-relative-repo-path-in-instructions | 4 docs | Removes the absolute repo path from instructions agents read. Two agents followed that path and wrote outside their root. |
| 04 | fix-delete-leaves-scope-rows | server/workspace_mw.py (`delete_owner`) | Your prompt-journey test: deleting a project left 1–2 registry rows (its chat-scope files). The single door now removes those folders and rows too. |
| 05 | fix-easypost-role-catalogue | server/projects.py | Your Revealer pre-flight: EasyPost had no resources section in the role catalogue. |

## Evidence (all in the isolated copy)
- Regression suite: 32/32 pass, 0 regressions against the 18-check baseline. New checks: R9 (12 hook unit checks, including the door's actor check and the quoted-`>` and heredoc false positives), R10 (delete leaves 0 rows), R11 (every role has resources).
- RQ2, real agents, 3 reps × N=1/2/5/10. Before: own-code-slot 0.67/0.50/0.40/0.17, success 52/54. After (hook enforcing): 1.00 at every N, success 54/54, 0 files outside projects, 0 cross-project. In normal work the hook blocked nothing; P2a alone fixed placement.
- Adversarial (the agent is told to copy into shared and into another project): hook off → 5/5 raw writes into shared and 5/5 into another project. Hook on → blocked; 0 cross-project files; all 5 shared modules arrived through the door.
- Your tests after the changes: phase7 lifecycle 3/3 green; phase7 strong 32/32 ×3; prompt journey, clean delete 2/3 (before 0/3; the remaining "+1" is the system audit-log row registered for the first time, not a project row); Revealer passes pre-flight (before: blocked at pre-flight).

## Suggested way to apply (your decision; you run it yourself)
```bash
cd ~/Desktop/AiAgentWorkSpace/Odin-Orchestrator
git apply --check <pkg>/patches/0*.patch && git apply <pkg>/patches/0*.patch
export ODIN_SCOPE_HOOK=watch      # first days: log only → workspace/history/scope-hook.jsonl
# restart the server; review the log; then switch to enforce (the default) by unsetting the variable
```
Rollback: `git apply -R <pkg>/patches/0X-….patch` (in reverse order).

## Notes and risks
- 04 deletes the project's chat-scope folders when the project is deleted. Before, they were left behind.
- 02: the hook parses Bash commands best-effort (redirects, tee, mkdir, touch, cp/mv/install). A write done from inside a script (e.g. python open()) is not seen; the audit remains the at-rest check for that.
- Not included (proposals only): stop a deleted project's still-running agents (D30); the team-coverage gap in the prompt journey (1/3 before and after); some modules write relative to the CWD (D25).
