#!/bin/bash
# G6 test: BEFORE (server from tag fix3-start) and AFTER (current), each in its own throwaway root. No LLM.
ISO=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated; cd $ISO
export PATH="$ISO/_isolation/shims:$ISO/.venv/bin:/opt/homebrew/bin:/usr/bin:/bin" PGHOST=/tmp/odc_pg PGPORT=25433 ANCHOR_PG_DSN="dbname=odin_anchor_con" ODIN_SCOPE_HOOK=enforce
L=_consolidation/results/f08_test.log; : > $L
for ver in ${F08_VERS:-before after}; do
  _isolation/pg_up.sh 25433 --reset >/dev/null 2>&1
  T=$(_research/exp/mkroot.sh f08_$ver fullall | tail -1); chmod -R u+w $T
  rm -rf $T/workspace && mkdir -p $T/workspace && git archive 4945000 workspace | tar -x -C $T && mkdir -p $T/workspace/chats $T/workspace/logs
  if [ $ver = before ]; then rm -rf $T/server && mkdir -p $T/server && git archive ${F08_BEFORE:-f08-start} server | tar -x -C $T; fi
  echo "== $ver ($T)" >> $L
  (cd $T && python $ISO/_consolidation/f08_test.py $T $ISO) >> $L 2>&1; echo "rc=$?" >> $L
done; echo DONE >> $L
