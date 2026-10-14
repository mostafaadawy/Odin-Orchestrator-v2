#!/bin/bash
# Driver: N in 1 2 5 10, door vs bypass, 5 seeds; fresh throwaway root + fresh private DB per trial.
ISO=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Isolated; cd $ISO
export PATH="$ISO/_isolation/shims:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin" PGHOST=$ISO/_research/tmp/pg/sock PGPORT=15433 ANCHOR_PG_DSN="dbname=odin_anchor_iso"
OUT=$ISO/_research/results/consistency_trials.jsonl; : > $OUT
.venv/bin/python -c "import sys;sys.path.insert(0,'_research/exp');import common,json;print(json.dumps(common.env_snapshot('consistency start')))" > $ISO/_research/results/consistency_env_start.json
for seed in 1 2 3 4 5; do for N in 1 2 5 10; do for cond in door bypass; do
  _isolation/pg_up.sh 15433 --reset >/dev/null 2>&1
  T=$(_research/exp/mkroot.sh cx 2>/dev/null | tail -1)
  .venv/bin/python _research/exp/consistency_trial.py "$T" $N $cond $seed 2>>$ISO/_research/results/consistency_err.log | tail -1 >> $OUT
  echo "$(date -u +%T) seed=$seed N=$N $cond" >> $ISO/_research/results/consistency_progress.log
done; done; done
.venv/bin/python -c "import sys;sys.path.insert(0,'_research/exp');import common,json;print(json.dumps(common.env_snapshot('consistency end')))" > $ISO/_research/results/consistency_env_end.json
echo DONE >> $ISO/_research/results/consistency_progress.log
