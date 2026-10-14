#!/bin/bash
# llm_root_up.sh <name> <port> <pgport>  — full throwaway root + private DB + Odin server (remote tools blocked)
ISO=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Isolated; cd $ISO
T=$(_research/exp/mkroot.sh "$1" full | tail -1); chmod -R u+w "$T"
[ -d "$T/server" ] || { echo "ROOT FAILED for $1"; exit 1; }
_isolation/pg_up.sh "$3" --reset >/dev/null 2>&1
cd "$T"
export PATH="$ISO/_isolation/shims:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
export PORT=$2 ODIN_HOST=127.0.0.1 USE_VOICE=0 CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 ODIN_VENV="$ISO/.venv"
export PGHOST="$ISO/_research/tmp/pg/sock" PGPORT=$3 ANCHOR_PG_DSN="dbname=odin_anchor_iso"
export CLAUDE_CALL_LOG="$ISO/_research/results/claude_calls_$1.jsonl"
export ODIN_SCOPE_HOOK=${ODIN_SCOPE_HOOK:-off}
export ODIN_SCOPE_HOOK_TRACE=${ODIN_SCOPE_HOOK_TRACE:-0}
nohup bash server/run.sh > "$T/server.log" 2>&1 &
echo $! > "$T/server.pid"
for i in $(seq 1 60); do curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$2/health 2>/dev/null | grep -q 200 && break; sleep 1; done
echo "$T $(cat $T/server.pid) health=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:$2/health)"
