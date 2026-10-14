#!/bin/bash
# G6 test: BEFORE (server from tag fix3-start) and AFTER (current), each in its own throwaway root. No LLM.
ISO=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated; cd $ISO
export PATH="$ISO/_isolation/shims:$ISO/.venv/bin:/opt/homebrew/bin:/usr/bin:/bin" PGHOST=/tmp/odc_pg PGPORT=25433 ANCHOR_PG_DSN="dbname=odin_anchor_con" ODIN_SCOPE_HOOK=enforce
L=_consolidation/results/f41i_test.log; : > $L
for ver in ${F41I_VERS:-before after}; do
  _isolation/pg_up.sh 25433 --reset >/dev/null 2>&1
  T=$(_research/exp/mkroot.sh f41i_$ver fullall | tail -1); chmod -R u+w $T
  rm -rf $T/workspace && mkdir -p $T/workspace && git archive 4945000 workspace | tar -x -C $T && mkdir -p $T/workspace/chats $T/workspace/logs
  mkdir -p $T/odin_app && cp -R odin_app/lib $T/odin_app/
  if [ $ver = before ]; then rm -rf $T/server $T/odin_app/lib && mkdir -p $T/server && git archive ${F41I_BEFORE:-f41i-start} server odin_app/lib | tar -x -C $T; fi
  echo "== $ver ($T)" >> $L
  (cd $T && python $ISO/_consolidation/f41i_test.py $T) >> $L 2>&1; echo "rc=$?" >> $L
done; echo DONE >> $L
