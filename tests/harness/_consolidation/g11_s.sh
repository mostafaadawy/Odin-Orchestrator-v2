#!/bin/bash
# G11 live proof (plan login only, auth-checked by scenarios.py): restart the copy server with the fix, run S4 r8.
cd /Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated
export PATH="$PWD/_isolation/shims:/opt/homebrew/bin:/usr/bin:/bin" PGHOST=/tmp/odc_pg PGPORT=25432
export CLAUDE_CALL_LOG=$PWD/_consolidation/results/claude_calls.jsonl
L=_consolidation/results/g11_s.log; : > $L
echo "$(date '+%F %T') START S4 r8" >> $L
.venv/bin/python _consolidation/scenarios.py S4 8 >> $L 2>&1
echo "$(date '+%F %T') END rc=$?" >> $L; echo DONE >> $L
