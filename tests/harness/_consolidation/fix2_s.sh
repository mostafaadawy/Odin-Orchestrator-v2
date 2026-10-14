#!/bin/bash
# Fix #2 scenario batch B (LLM cost ~$5-7): S2 r7 (QA on), S4 r4 + r5 (QA off). Pass condition per run:
# the run ends ok=True ONLY if every step's review is "Confirmed"; any Needs-fix/unclear review -> ok=False.
cd /Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated
export PATH="$PWD/_isolation/shims:/opt/homebrew/bin:/usr/bin:/bin" PGHOST=/tmp/odc_pg PGPORT=25432 COST_CAP=40
export CLAUDE_CALL_LOG=$PWD/_consolidation/results/claude_calls.jsonl
L=_consolidation/results/fix2_s.log
bash _isolation/up.sh; sleep 25
for sr in ${FIX2_RUNS:-S2:7 S4:4 S4:5}; do
  set -- ${sr/:/ }
  echo "$(date '+%F %T') START $1 r$2" >> $L
  .venv/bin/python _consolidation/scenarios.py $1 $2 >> $L 2>&1
  echo "$(date '+%F %T') END $1 r$2 rc=$?" >> $L
  .venv/bin/python _consolidation/fix2c_consist.py _consolidation/results/$1_r$2.json . >> $L 2>&1
done; echo DONE >> $L
