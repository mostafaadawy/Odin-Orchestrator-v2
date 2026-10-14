# PHASE 7 — HANDOFF (read this FIRST in a new session)

> Owner: Mostafa. Bridge: `bash shells/agent_terminal_bridge.sh` (already running — do NOT ask to restart).
> Services already up: brain `:8000`, anchor `:9100`, poller. Host python: `.venv/bin/python`.

## 0) MY ROLE (non-negotiable)
I am **not** the owner's smart AI. My job is to make **his AI agent app** smart and strong.
The SYSTEM must solve things itself (middleware, audit, directions, promote-to-shared). When it fails,
I fix the **origin in his code** so the capability survives without me. Proof must come from **his audit
reporting clean**, never from my assertion.

## 1) STANDING RULES (never violate)
- **NEVER touch real production** `organics-prod-deploy` / bendcore / organics: not its DB, config, nginx,
  external ports, or its deploy behaviour. It is `PROTECTED_PROJECTS` in `workspace_audit.py`.
- **Deploy protocol**: change-detection first (no changes ⇒ do NOT deploy). `az` is used ONLY to **replace**
  the dynamic IP in NSG/UFW — never open new ports, never close 22/80/443. Then **SSH as `mostafa`** (never
  root; password key in `.cred` is **`azvmcred`**). DB rebase is **asked with a recommendation** and the owner
  may refuse. Reload services, don't reboot. Verify DB seed (users>0) + live endpoints + mtime evidence.
  Update baseline lists **only after** full verification.
- **Generic engine + per-project delta**: shared scripts know NOTHING about a specific project. Each project's
  personal paths/VM/DB/ports live in **its own** `workspace/projects/<pid>/deploy/…`. The SYSTEM generates the
  delta (`workspace_mw.provision_capability`) — a human must not hand-write it.
- **Do not stop / do not report "done"** until: 0 violations, 0 cross-violations, nothing partial or pending.
  Repeat the loop again and again. Fix every violation at its ORIGIN so it cannot recur.

## 2) CURRENT VERIFIED STATE (as of this handoff)
```
open_issues = 0
PHASE7_MONITOR   ALL GREEN   (8/8 projects, ~222ms each)
PHASE7_STRONG    ALL GREEN   (adversarial: injected → really corrected)
PHASE7_LIFECYCLE ALL GREEN   (create→clean, exact baseline restore)
DB: 9 projects · 28 agents · 5 connectors · 0 orphans
```
- Revealer sandbox mirrors production: own DB, ports **4113/3112** (both 200), no domain, frontend created,
  **systemd user units** `revealer-be` / `revealer-fe`, deploy = **18 ok · 0 warn · 0 fail ✅**.
- Production untouched & healthy: organics `:3012 → 200`, bendcore `:4013 → 200`.
- `provision_capability` proven: hand-written delta deleted → **system regenerated it** → deploy green.

## 3) WHAT IS BUILT (all on disk)
- `server/workspace_mw.py` — owner-scoping guard (`put_file(actor=)`), `promote_to_shared`,
  `repoint_reference`, `add_dependency`, `customize_shared`, `resolve_capability`, **`provision_capability`**,
  `create_owner`/`delete_owner` (FK-safe, link rows cleaned).
- `server/workspace_audit.py` — misplaced / unindexed / duplicate / **foreign-ref** detection + heal at source;
  `PROTECTED_PROJECTS`.
- `server/ui_api.py` — `/ui/projects|agents|types|connectors`, type **and agent** driven controls, pagination.
- `workspace/shared/infra/deploy_changes.py` — **generic**, `--project <pid>`, per-project baselines.
- `workspace/shared/infra/deploy.sh` — verify port from delta, empty-services skip, logs → `workspace/logs/`,
  baseline update gated on verification.
- Harnesses: `phase7_monitor.py`, `phase7_strong.py`, `phase7_lifecycle.py`, `phase7_lib.py`,
  **`phase7_realrun.py`**, **`phase7_prompt_loop.py`**, `seed_connectors.py`.

## 4) WHAT REMAINS — DO THIS FIRST
```bash
cd <odin-repo-root>
.venv/bin/python workspace/shared/testing/phase7_realrun.py       # 8 projects, REAL runs, timed
.venv/bin/python workspace/shared/testing/phase7_prompt_loop.py   # prompt→plan→watch→audit→delete
```
Then: fix every violation **at its origin**, re-run all suites, drive back to `open_issues = 0`. Repeat.
Report per project: description, what it does, result, **duration (prompt → output)**, violations, gaps fixed.

## 5) TRAPS THAT ALREADY BIT ME (don't repeat)
- **Bridge exit codes lie about SSH.** A build reported `exit 255` while it actually succeeded on the VM.
  Always verify the REAL state on the VM (`ls`, run the command manually) before believing a failure.
- **macOS has no `timeout`** — `timeout N cmd` silently no-ops the whole line. Never use it.
- **Postgres deadlock**: never hold an open transaction while calling `sync_row`/`sync_folders` (they open their
  own connections). It hung the bridge ~30 min twice. Commit + close first.
- Long real runs exceed the bridge's 900s timeout — launch them with `nohup … & disown` and poll the log.
- `deploy.config.sh` still has `CFG_BACKEND_MIG="reset"` from a one-time 2026-07-16 authorization whose own
  comment says to revert it. **Production deploy would wipe the DB.** Owner was told; left untouched by design.

## 6) UI REQUIREMENTS (verify on the real surfaces)
Desktop (**Electron — the main one**), web, mobile must all render from the same `/ui` payload:
agents actually appear; buttons/badges come from **type + the agents used + existing connectors** (never
static); connectors array-mapped from the DB (5: hubspot, klaviyo, veeqo, claude-cli, az-cli);
recurring/periodical show run/play; a Reporting agent adds **export**. Dashboard is landing-only (optional).
