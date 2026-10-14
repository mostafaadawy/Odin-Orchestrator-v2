# v1 check: did the shared-name data-loss bug delete any project file? (read-only, 2026-10-11)

**Method:** read only. I used no v1 imports and no database access; I read logs, git history and file hashes.

**Does the bug exist in v1?** **Yes.** In `server/workspace_mw.py` l.389–390 (`elif p.exists(): p.unlink()`), if `shared/<category>/<name>` already exists, the project's copy is deleted without comparing the contents.

**Did it delete anything? No.**
- **The audit log has 31 promotions.**
  - 26 are the regression-test fixtures `_s_c/dupz.py` and `_s_f/flib.py`, which the tests re-create and clean up each run.
  - 3 are the July 17 audit demo projects (`audit-demo-a`, `audx-a`, `catp-a`).
  - 2 are `redberry-continuous-soc/code/sensor/INSTALL_SOC_SENSOR.md` (2026-07-20, both in the same second).
- **INSTALL_SOC_SENSOR.md:**
  - before the move, `shared/utils/INSTALL_SOC_SENSOR.md` did not exist in git (commit 06a6ddb);
  - the shared file is byte-identical to the project's original (blob c35ba49, in commit 8790899 and still today);
  - the second record found the file already moved, so nothing was deleted. **No loss.**
- **Agent-side promotions** (door / request_capability): there are none in the chats or logs.
- **The only project files deleted in v1's git history** are `organics-prod-deploy/*` (2026-07-22). That was a whole-project deletion: the project's chats were removed too, and the project continues as `real-deployment-and-diagnosis-organics-07d7`. **Not this bug.** It is recoverable from commit `6e131b4^` if ever needed.
- **Exposure today:** a filesystem-only dry calculation of what v1's next audit heal would delete returns **0 files**.

**One fact for keeping v1 safe:** v1's audit sentinel runs about every 15 minutes and calls `heal(force=True)`, which **ignores the "enabled" switch** on the Audit page. Turning the audit off in the app does NOT stop automatic healing. (New item F-37.)

**How to stay safe until cutover** (you do these; I change nothing in v1):
1. **Make a recovery point now and keep it current.** v1's last git commit is 2026-08-22. Commit v1 (or copy its `workspace/` folder, or let Time Machine run) now, then daily until cutover. Any file can then be recovered.
2. **Do not create a file in a project with the same name as a file already in `workspace/shared/`.** This only matters when the file is identical in two projects, or when another project references it.
3. **For zero risk,** stop the v1 server when you are not using it. The sentinel runs only while the server runs.
4. **If you want it,** I can prepare (not apply) a one-line v1 guard for your decision. v1 stays untouched unless you explicitly allow it.

**Disclosure:** my earlier read-only `git status` checks on v1 refreshed git's own index cache (`.git/index`, last at 13:12 UTC). No tracked file, commit or working file changed. From now on I use `git --no-optional-locks`, which does not touch the index.
