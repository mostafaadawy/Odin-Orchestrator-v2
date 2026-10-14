#!/bin/bash
# F-43 test: BEFORE (server f43-start) records the old orientation; AFTER (current) compares legacy900 byte-for-byte. No LLM.
ISO=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated; cd $ISO
export PATH="$ISO/_isolation/shims:$ISO/.venv/bin:/opt/homebrew/bin:/usr/bin:/bin" PGHOST=/tmp/odc_pg PGPORT=25433 ANCHOR_PG_DSN="dbname=odin_anchor_con" ODIN_SCOPE_HOOK=enforce
L=_consolidation/results/f43_test.log; : > $L; S=_consolidation/results/f43_old_orientation.json
for ver in before after; do
  _isolation/pg_up.sh 25433 --reset >/dev/null 2>&1
  T=$(_research/exp/mkroot.sh f43_$ver fullall | tail -1); chmod -R u+w $T
  rm -rf $T/workspace && mkdir -p $T/workspace && git archive 4945000 workspace | tar -x -C $T && mkdir -p $T/workspace/chats $T/workspace/logs $T/data
  rm -rf $T/workspace/agents && git archive HEAD workspace/agents | tar -x -C $T     # the CURRENT agent files (restored rules)
  if [ $ver = before ]; then rm -rf $T/server && mkdir -p $T/server && git archive f43-start server | tar -x -C $T; fi
  echo "== $ver ($T)" >> $L
  (cd $T && python $ISO/_consolidation/f43_test.py $T $ver $ISO/$S) >> $L 2>&1; echo "rc=$?" >> $L
done; echo DONE >> $L
