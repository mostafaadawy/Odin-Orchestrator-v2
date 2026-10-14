#!/bin/bash
# F-32 + G2 live batch. Records the isolation-shim blocked-call count before/after each run.
cd /Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated
export PATH="$PWD/_isolation/shims:/opt/homebrew/bin:/usr/bin:/bin" PGHOST=/tmp/odc_pg PGPORT=25432 COST_CAP=100
export CLAUDE_CALL_LOG=$PWD/_consolidation/results/claude_calls.jsonl
L=_consolidation/results/f32_s.log
bash _isolation/up.sh; sleep 25
for sr in ${F32_RUNS:-S7:3 S4:7 S9:1}; do
  set -- ${sr/:/ }
  b0=$(wc -l < _isolation/blocked_calls.log)
  echo "$(date '+%F %T') START $1 r$2 blocked_before=$b0" >> $L
  .venv/bin/python _consolidation/scenarios.py $1 $2 >> $L 2>&1
  b1=$(wc -l < _isolation/blocked_calls.log)
  echo "$(date '+%F %T') END $1 r$2 blocked_after=$b1 new_blocked=$((b1-b0))" >> $L
  tail -n $((b1-b0)) _isolation/blocked_calls.log | grep -E "^20" | cut -c1-140 >> $L
done; echo DONE >> $L
