#!/bin/bash
# Sequential scenario batch (background). Stops automatically at the cost cap (scenarios.py exits 3).
cd /Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated
export PATH="$PWD/_isolation/shims:/opt/homebrew/bin:/usr/bin:/bin" PGHOST=/tmp/odc_pg PGPORT=25432 COST_CAP=40
for rep in 1 2 3; do for sc in S5 S4 S1 S3 S2; do
  echo "$(date '+%F %T') START $sc r$rep" >> _consolidation/results/batch.log
  .venv/bin/python _consolidation/scenarios.py $sc $rep >> _consolidation/results/batch.log 2>&1; rc=$?
  echo "$(date '+%F %T') END $sc r$rep rc=$rc" >> _consolidation/results/batch.log
  [ $rc -eq 3 ] && { echo "COST CAP REACHED" >> _consolidation/results/batch.log; exit 0; }
done; done
echo "$(date '+%F %T') BATCH DONE" >> _consolidation/results/batch.log
