#!/bin/bash
# CUTOVER STEP 3 — the database changes v2 needs on the REAL odin_core: G8 migration (adds files.created_by; takes its own
# backup) + re-sync of the agent/file rows from v2's files. Stops on the first failure.
set -uo pipefail
export PATH=/opt/homebrew/bin:/opt/homebrew/opt/postgresql@14/bin:/usr/bin:/bin
V2=$HOME/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2; cd "$V2"
fail(){ echo "❌ STEP 3 FAILED: $*"; exit 1; }
bash server/migrations/migrate_g8.sh up odin_core "$V2/_v2/cutover/db_backups" || fail "G8 migration (database unchanged if its backup failed)"
.venv/bin/python - <<'PY' || exit 1
import sys, pathlib; sys.path.insert(0, "server")
import workspace_mw as mw
n = 0
for f in sorted(pathlib.Path("workspace/agents").glob("*/index.json")):
    mw.sync_row(f); n += 1
print(f"  ✓ {n} agent rows re-synced from their own index.json (G10)")
PY
echo "STEP 3 OK — status: $(bash server/migrations/migrate_g8.sh status odin_core)"
