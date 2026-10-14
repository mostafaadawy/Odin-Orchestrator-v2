#!/bin/bash
# Start the ISOLATED Odin server (port 28000), remote tools blocked, voice off, Claude auto-memory off.
cd /Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated
export PATH="$PWD/_isolation/shims:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PORT=28000 ODIN_HOST=127.0.0.1 USE_VOICE=0 CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 ODIN_VENV="$PWD/.venv"
export ANCHOR_PG_DSN="dbname=odin_anchor_con" PGDATABASE=odin_core_con
# one usage ledger for the paper (reported usage, not charged): the claude shim writes every call here
export CLAUDE_CALL_LOG="${CLAUDE_CALL_LOG:-$PWD/_consolidation/results/claude_calls.jsonl}"
# private throwaway Postgres (port 25432) — never the owner's server
_isolation/pg_up.sh 25432 >/dev/null
export PGHOST=/tmp/odc_pg PGPORT=25432
[ -f _research/runs/server.pid ] && kill "$(cat _research/runs/server.pid)" 2>/dev/null; sleep 1
nohup bash server/run.sh > _research/runs/server.log 2>&1 &
echo $! > _research/runs/server.pid
