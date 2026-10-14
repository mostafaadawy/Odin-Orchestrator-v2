#!/bin/bash
# Step G / P8-2 + R-DP: deploy.sh BEFORE (tag stepG-start) and AFTER (current), against stub tools. No VM, no network.
ISO=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated; cd $ISO
L=_consolidation/results/stepG_test.log; : > $L
for ver in ${STEPG_VERS:-before after}; do
  if [ $ver = before ]; then D=$(mktemp -d)/deploy.sh; git show ${STEPG_BEFORE:-stepG-start}:workspace/shared/infra/deploy.sh > $D; else D=$ISO/workspace/shared/infra/deploy.sh; fi
  echo "== $ver" >> $L
  .venv/bin/python _consolidation/stepG_test.py $D $ISO >> $L 2>&1; echo "rc=$?" >> $L
done; echo DONE >> $L
