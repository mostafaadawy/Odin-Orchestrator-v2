#!/bin/bash
# PC-4 test (secure phone approvals through the Anchor): BEFORE (post3-done: no such path) and AFTER (current). No LLM.
ISO=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated; cd $ISO
export PATH="$ISO/_isolation/shims:$ISO/.venv/bin:/opt/homebrew/bin:/usr/bin:/bin" PGHOST=/tmp/odc_pg PGPORT=25433 ANCHOR_PG_DSN="dbname=odin_anchor_con" ODIN_SCOPE_HOOK=enforce
L=_consolidation/results/pc4_test.log; : > $L
for ver in ${PC4_VERS:-before after}; do
  _isolation/pg_up.sh 25433 --reset >/dev/null 2>&1
  T=$(_research/exp/mkroot.sh pc4_$ver fullall | tail -1); chmod -R u+w $T
  rm -rf $T/workspace && mkdir -p $T/workspace && git archive 4945000 workspace | tar -x -C $T && mkdir -p $T/workspace/chats $T/workspace/logs
  rm -f $T/data/phone_devices.json $T/data/phone_nonces.json $T/data/relay_seen.json $T/data/relay_x25519.json
  if [ $ver = before ]; then rm -rf $T/server $T/orchestrator && mkdir -p $T/server && git archive ${PC4_BEFORE:-post3-done} server orchestrator | tar -x -C $T; fi
  echo "== $ver ($T)" >> $L
  (cd $T && python $ISO/_consolidation/pc4_test.py $T) >> $L 2>&1; echo "rc=$?" >> $L
done; echo DONE >> $L
