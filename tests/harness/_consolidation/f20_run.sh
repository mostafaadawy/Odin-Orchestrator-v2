#!/bin/bash
# F-20 test (local only + brain token): BEFORE (server+desktop at f20-start) and AFTER (current). No LLM.
ISO=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated; cd $ISO
export PATH="$ISO/_isolation/shims:$ISO/.venv/bin:/opt/homebrew/bin:/usr/bin:/bin" PGHOST=/tmp/odc_pg PGPORT=25433 ANCHOR_PG_DSN="dbname=odin_anchor_con" ODIN_SCOPE_HOOK=enforce
L=_consolidation/results/f20_test.log; : > $L
for ver in ${F20_VERS:-before after}; do
  _isolation/pg_up.sh 25433 --reset >/dev/null 2>&1
  T=$(_research/exp/mkroot.sh f20_$ver fullall | tail -1); chmod -R u+w $T
  rm -rf $T/workspace && mkdir -p $T/workspace && git archive 4945000 workspace | tar -x -C $T && mkdir -p $T/workspace/chats $T/workspace/logs
  if [ $ver = before ]; then rm -rf $T/server && mkdir -p $T/server && git archive ${F20_BEFORE:-f20-start} server | tar -x -C $T; fi
  mkdir -p $T/desktop/src $T/desktop/electron; if [ $ver = before ]; then git archive ${F20_BEFORE:-f20-start} desktop/src/api.js desktop/electron/main.cjs | tar -x -C $T; else cp desktop/src/api.js $T/desktop/src/; cp desktop/electron/main.cjs $T/desktop/electron/; fi
  echo "== $ver ($T)" >> $L
  (cd $T && python $ISO/_consolidation/f20_test.py $T) >> $L 2>&1; echo "rc=$?" >> $L
done; echo DONE >> $L
