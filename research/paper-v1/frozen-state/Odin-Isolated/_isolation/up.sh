#!/bin/bash
# Start the ISOLATED Odin server (port 18000), remote tools blocked, voice off, Claude auto-memory off.
cd /Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Isolated
export PATH="$PWD/_isolation/shims:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PORT=18000 ODIN_HOST=127.0.0.1 USE_VOICE=0 CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 ODIN_VENV="$PWD/.venv"
export ANCHOR_PG_DSN="dbname=odin_anchor_iso" PGDATABASE=odin_core_iso
# private throwaway Postgres (port 15432) — never the owner's server
_isolation/pg_up.sh 15432 >/dev/null
export PGHOST="$PWD/_research/tmp/pg/sock" PGPORT=15432
[ -f _research/runs/server.pid ] && kill "$(cat _research/runs/server.pid)" 2>/dev/null; sleep 1
nohup bash server/run.sh > _research/runs/server.log 2>&1 &
echo $! > _research/runs/server.pid
