#!/bin/bash
cd /Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated
export PATH="$PWD/_isolation/shims:/opt/homebrew/bin:/usr/bin:/bin" PGHOST=/tmp/odc_pg PGPORT=25432 COST_CAP=40
export CLAUDE_CALL_LOG=$PWD/_consolidation/results/claude_calls.jsonl
bash _isolation/up.sh; sleep 25
for rep in 4 5 6; do
  echo "$(date '+%F %T') START S2 r$rep" >> _consolidation/results/fix1_s2.log
  .venv/bin/python _consolidation/scenarios.py S2 $rep >> _consolidation/results/fix1_s2.log 2>&1
  echo "$(date '+%F %T') END S2 r$rep rc=$?" >> _consolidation/results/fix1_s2.log
done; echo DONE >> _consolidation/results/fix1_s2.log
