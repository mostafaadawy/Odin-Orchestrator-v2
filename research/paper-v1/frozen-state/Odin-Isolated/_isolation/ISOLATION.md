# Odin-Isolated: isolation record (2026-10-06)

This folder is a copy of Odin-Orchestrator at HEAD af2cbd8, taken on 2026-10-06. It is isolated from the real folder and from the real databases.

## Left out of the copy
- `.git`: a fresh local repo was created here, with no remote and no hooks.
- `.venv`, `desktop/node_modules`, `desktop/release`, and the Flutter build, Pods, `.symlinks`, ephemeral and `.dart_tool` folders. These are rebuildable, and they contain absolute paths.
- `__pycache__` and `.DS_Store`.
- `workspace/logs/agent_term`, the real folder's bridge. The copy keeps an empty one.
- All symlinks (copied with `--no-links`).

## Credentials
- These were excluded: `.cred`, `.auth`, `connector_keys.json`, `backup.key` and every `.env` file.
- Placeholders were put in their place:
  - `connector_keys.json` keeps its structure with every value blank.
  - The `.cred` and `.auth` files contain one comment line.
  - The `.env*.example` templates were restored.
- In chats, logs and data, 54 values were redacted to `<REDACTED>`. Code files had none.
- The `.enc` files are untouched. They are encrypted SOC backups, and their key was not copied.

## Neutralised references (reverse these maps when promoting)
- `repath_changed_files.json`: 252 files and 7,042 references were redirected:
  - `.../AiAgentWorkSpace/Odin-Orchestrator` → `.../AiAgentWorkSpace/Odin-Isolated`
  - `~/Desktop/Odin`, `~/Desktop/OdinTesting` and `~/Desktop/VolatileWorkSpace` → `Odin-Isolated/_external/...` (empty sandboxes)
  - References to the deleted old copy: none found.
- The same redirect was applied to dynamic home paths in 4 code files:
  - `deploy_changes.py` (RBO-Staging source)
  - the 2 `sandbox_*` testing scripts ("Odin Testing")
  - `desktop/electron/main.cjs`
- `pkill -f "Odin-Orchestrator/desktop"` → `Odin-Isolated/desktop` in `shells/development_full_checker.sh` (and its `.bak` copy).
- `db_port_remap_files.json` lists the 56 code files changed for databases and ports:
  - Databases: `odin_core` → `odin_core_iso` and `odin_anchor` → `odin_anchor_iso`. These databases do NOT exist yet, so the copy fails safe. Creating them is a database action and needs the owner's approval.
  - Ports: 8000→18000, 9100→19100, 9104→19104, 9300→19300 and 8080→18080. The copy therefore never collides with the real server's ports, and its kill-by-port steps never touch the real processes.
- `schedules_original_enabled.json`: all 5 scheduled tasks are disabled in the copy, so the SOC agents never run twice.

## Not neutralised (intentional)
- Remote hosts and VM targets in the deploy configs are unchanged, because the Sandbox project needs them. Rules for the copy:
  - Never run real-deployment-and-diagnosis-organics.
  - Every remote action needs the owner's approval.
- Display labels saying "Odin-Orchestrator" (product name, UI and docs) and relative `__file__` paths are unchanged.

## Rescued research items
These are in `_research/rescued/` and are verified by `MANIFEST.sha256`.
- isolation: blank placeholder workspace/projects/redberry-continuous-soc/data/soc_secure/backup.key added (the DB indexes it; without it the audit reports a db-orphan).
