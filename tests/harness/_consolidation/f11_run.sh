#!/bin/bash
# F-11 test (50% rule): BEFORE (server at f11-start) and AFTER (current), throwaway roots. No LLM.
ISO=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated; cd $ISO
export PATH="$HOME/.nvm/versions/node/v20.20.2/bin:$ISO/_isolation/shims:$ISO/.venv/bin:/opt/homebrew/bin:/usr/bin:/bin" PGHOST=/tmp/odc_pg PGPORT=25433 ANCHOR_PG_DSN="dbname=odin_anchor_con" ODIN_SCOPE_HOOK=enforce
L=_consolidation/results/f11_test.log; : > $L
for ver in ${F11_VERS:-before after}; do
  _isolation/pg_up.sh 25433 --reset >/dev/null 2>&1
  T=$(_research/exp/mkroot.sh f11_$ver fullall | tail -1); chmod -R u+w $T
  rm -rf $T/workspace && mkdir -p $T/workspace && git archive 4945000 workspace | tar -x -C $T && mkdir -p $T/workspace/chats $T/workspace/logs
  if [ $ver = before ]; then rm -rf $T/server && mkdir -p $T/server && git archive ${F11_BEFORE:-f11b-start} server | tar -x -C $T; fi
  echo "== $ver ($T)" >> $L
  (cd $T && python $ISO/_consolidation/f11_test.py $T) >> $L 2>&1; echo "rc=$?" >> $L
done; echo DONE >> $L
