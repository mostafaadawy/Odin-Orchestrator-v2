#!/bin/bash
# Owner's Revealer E2E (isolated local adaptation) in a throwaway root, with a hard budget watchdog.
ISO=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated; cd $ISO; CAPUSD=${CAPUSD:-19.0}
spent(){ cat _research/results/claude_calls*.jsonl 2>/dev/null | /usr/bin/python3 -c "import sys,json;print(sum((json.loads(l).get('cost_usd') or 0) for l in sys.stdin if l.strip()))"; }
_isolation/pg_up.sh 25435 --reset >/dev/null 2>&1
T=$(_research/exp/mkroot.sh rev fullall | tail -1)
cp _research/exp/sandbox_revealer_local.py "$T/workspace/shared/testing/"
export PATH="$ISO/.venv/bin:/opt/homebrew/bin:/usr/bin:/bin" PGHOST=/tmp/odc_pg PGPORT=25435 ANCHOR_PG_DSN="dbname=odin_anchor_con"
export CLAUDE_CALL_LOG=$ISO/_research/results/claude_calls_revealer.jsonl CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 ODIN_TEST_KEEP=1 USE_VOICE=0
cd "$T"; .venv/bin/python -c 1 2>/dev/null
$ISO/.venv/bin/python -c "import sys;sys.path.insert(0,'$ISO/_research/exp');import common,json;print(json.dumps(common.env_snapshot('revealer start')))" > $ISO/_research/results/revealer_env_start${SUF}.json
START=$(date +%s)
$ISO/.venv/bin/python workspace/shared/testing/sandbox_revealer_local.py > $ISO/_research/results/owner_revealer_local${SUF}.log 2>&1 &
RP=$!
while kill -0 $RP 2>/dev/null; do
  sleep 20
  S=$(cd $ISO && spent); if /usr/bin/python3 -c "import sys;sys.exit(0 if $S >= $CAPUSD else 1)"; then echo "BUDGET KILL at $S" >> $ISO/_research/results/owner_revealer_local${SUF}.log; pkill -TERM -P $RP; kill -TERM $RP; break; fi
done
wait $RP; echo "RC=$? wall_s=$(( $(date +%s)-START )) spent_total=$(cd $ISO && spent)" >> $ISO/_research/results/owner_revealer_local${SUF}.log
