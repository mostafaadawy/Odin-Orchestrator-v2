#!/bin/bash
# G8 live run (approved by the owner, ~$1-2): migrate the copy DB (backup first), restart the copy server, run S12.
cd /Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated
export PATH="$PWD/_isolation/shims:/opt/homebrew/bin:/usr/bin:/bin" PGHOST=/tmp/odc_pg PGPORT=25432
export CLAUDE_CALL_LOG=$PWD/_consolidation/results/claude_calls.jsonl
L=_consolidation/results/g8_s.log; : > $L
server/migrations/migrate_g8.sh up odin_core_con >> $L 2>&1
bash _isolation/up.sh; sleep 25
echo "$(date '+%F %T') START S12 r1" >> $L
.venv/bin/python _consolidation/scenarios.py S12 1 >> $L 2>&1
echo "$(date '+%F %T') END rc=$?" >> $L; echo DONE >> $L
