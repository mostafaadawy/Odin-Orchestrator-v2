#!/bin/bash
# Step F / F-41 relay: BEFORE (server+phone at tag stepF-start) and AFTER (current), each in a throwaway root. No LLM.
# AFTER also runs the phone tests (flutter) and a cross-language vector: Dart seals -> Python opens.
ISO=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated; cd $ISO
FL=/Users/mostafaadawy/Desktop/VolatileWorkSpace/flutter/bin/flutter
export PATH="$ISO/_isolation/shims:$ISO/.venv/bin:/opt/homebrew/bin:/usr/bin:/bin" PGHOST=/tmp/odc_pg PGPORT=25433 ANCHOR_PG_DSN="dbname=odin_anchor_con" ODIN_SCOPE_HOOK=enforce
L=_consolidation/results/stepF_test.log; : > $L
for ver in ${STEPF_VERS:-before after}; do
  _isolation/pg_up.sh 25433 --reset >/dev/null 2>&1
  T=$(_research/exp/mkroot.sh stepF_$ver fullall | tail -1); chmod -R u+w $T
  rm -rf $T/workspace && mkdir -p $T/workspace && git archive 4945000 workspace | tar -x -C $T && mkdir -p $T/workspace/chats $T/workspace/logs
  if [ $ver = before ]; then rm -rf $T/server && mkdir -p $T/server && git archive ${STEPF_BEFORE:-stepF-start} server | tar -x -C $T; fi
  echo "== $ver ($T)" >> $L
  DENV=""
  if [ $ver = after ]; then
    (cd $T && python -c "import sys,json; sys.path.insert(0,'server'); import key_relay; json.dump(key_relay.public_info(), open('f41_pub.json','w'))") >> $L 2>&1
    (cd odin_app && F41_PUB_FILE=$T/f41_pub.json F41_OUT=$T/dart_env.json $FL test test/f41_relay_test.dart test/f41_key_request_test.dart test/widget_test.dart 2>&1 | tail -3) >> $L
    DENV=$T/dart_env.json
  fi
  (cd $T && python $ISO/_consolidation/stepF_test.py $T $DENV) >> $L 2>&1; echo "rc=$?" >> $L
done; echo DONE >> $L
