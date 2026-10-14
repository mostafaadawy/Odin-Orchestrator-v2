#!/bin/bash
# F-43 live A/B (plan login only, auth-checked by scenarios.py): restart the copy server with the fix, legacy900 vs full.
cd /Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated
export PATH="$PWD/_isolation/shims:/opt/homebrew/bin:/usr/bin:/bin" PGHOST=/tmp/odc_pg PGPORT=25432
export CLAUDE_CALL_LOG=$PWD/_consolidation/results/claude_calls.jsonl
L=_consolidation/results/f43_s.log; : > $L
echo "$(date '+%F %T') START f43 A/B" >> $L
.venv/bin/python _consolidation/f43_live.py >> $L 2>&1
echo "$(date '+%F %T') END rc=$?" >> $L; echo DONE >> $L
