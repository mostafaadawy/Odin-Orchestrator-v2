#!/bin/bash
# F-06 live proof (plan login only, auth-checked by scenarios.py): restart the copy server with the fix, run S5 r4.
cd /Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated
export PATH="$PWD/_isolation/shims:/opt/homebrew/bin:/usr/bin:/bin" PGHOST=/tmp/odc_pg PGPORT=25432
export CLAUDE_CALL_LOG=$PWD/_consolidation/results/claude_calls.jsonl
L=_consolidation/results/f06_s.log; : > $L
echo "$(date '+%F %T') START S5 r4" >> $L
.venv/bin/python _consolidation/scenarios.py S5 4 >> $L 2>&1
echo "$(date '+%F %T') END rc=$?" >> $L; echo DONE >> $L
