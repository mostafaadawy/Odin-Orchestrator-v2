#!/bin/bash
ISO=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated; cd $ISO; CAPUSD=${CAPUSD:-18.5}
spent(){ cat _research/results/claude_calls*.jsonl 2>/dev/null | /usr/bin/python3 -c "import sys,json;print(sum((json.loads(l).get('cost_usd') or 0) for l in sys.stdin if l.strip()))"; }
chmod -R a-w "$ISO/workspace"     # escape guard: the main copy's workspace is read-only during the run
_isolation/pg_up.sh 25435 --reset >/dev/null 2>&1
T=$(_research/exp/mkroot.sh p4 fullall | tail -1); chmod -R u+w "$T"
cp _research/exp/phase7_prompt4_local.py "$T/workspace/shared/testing/"
export PATH="$ISO/.venv/bin:/opt/homebrew/bin:/usr/bin:/bin" PGHOST=/tmp/odc_pg PGPORT=25435 ANCHOR_PG_DSN="dbname=odin_anchor_con"
export CLAUDE_CALL_LOG=$ISO/_research/results/claude_calls_prompt4.jsonl CLAUDE_CODE_DISABLE_AUTO_MEMORY=1 USE_VOICE=0 PORT=28000 ODIN_HOST=127.0.0.1 ODIN_VENV=$ISO/.venv
cd "$T"; nohup bash server/run.sh > "$T/server.log" 2>&1 & SP=$!
for i in $(seq 1 60); do curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:28000/health | grep -q 200 && break; sleep 1; done
START=$(date +%s)
$ISO/.venv/bin/python workspace/shared/testing/phase7_prompt4_local.py > $ISO/_research/results/owner_phase7_prompt4_local${SUF}.log 2>&1 & RP=$!
while kill -0 $RP 2>/dev/null; do sleep 20; S=$(cd $ISO && spent); if /usr/bin/python3 -c "import sys;sys.exit(0 if $S >= $CAPUSD else 1)"; then echo "BUDGET KILL at $S" >> $ISO/_research/results/owner_phase7_prompt4_local${SUF}.log; kill -TERM $RP; break; fi; done
wait $RP; echo "RC=$? wall_s=$(( $(date +%s)-START )) spent_total=$(cd $ISO && spent)" >> $ISO/_research/results/owner_phase7_prompt4_local${SUF}.log
kill $SP 2>/dev/null; chmod -R u+w "$ISO/workspace"
