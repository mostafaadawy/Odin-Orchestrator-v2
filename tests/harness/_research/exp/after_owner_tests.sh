#!/bin/bash
# AFTER the P2 + bug-fix changes: re-run the owner's tests (same scripts as BEFORE), logs suffixed _after.
ISO=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated; cd $ISO
export PATH="$ISO/.venv/bin:/opt/homebrew/bin:/usr/bin:/bin" PGHOST=/tmp/odc_pg PGPORT=25433 ANCHOR_PG_DSN="dbname=odin_anchor_con" ODIN_SCOPE_HOOK=enforce
for t in lifecycle strong; do for rep in 1 2 3; do
  _isolation/pg_up.sh 25433 --reset >/dev/null 2>&1; T=$(_research/exp/mkroot.sh p7a fullall | tail -1); chmod -R u+w $T
  (cd $T && /usr/bin/time -p python workspace/shared/testing/phase7_$t.py > $ISO/_research/results/owner_phase7_${t}_after_rep$rep.log 2>&1)
done; done
SUF=_after CAPUSD=17.5 _research/exp/revealer_run.sh
SUF=_after CAPUSD=19 _research/exp/prompt4_run.sh
echo AFTER_OWNER_DONE >> _research/results/llm_series.log
