#!/bin/bash
# P4f: wait for rep 1, then reps 2 and 3 on the held-out TEST ids only (plan login, limit-guarded), then rename partials.
cd /Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2/research/phase4
PY=../../.venv/bin/python
while pgrep -f "baseline.py 1" >/dev/null; do sleep 20; done
for r in 2 3; do P4_PAR=3 caffeinate -i $PY baseline.py $r data/test_ids.json > baseline$r.log 2>&1 || { echo "rep $r stopped rc=$?"; exit 1; }; done
echo REPS-DONE
