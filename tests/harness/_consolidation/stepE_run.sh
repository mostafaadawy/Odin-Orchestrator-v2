#!/bin/bash
# Step E / F-14: BEFORE = tree at tag stepE-start, AFTER = what this step ships (tracked + new, minus ignored).
ISO=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated; cd $ISO
export PATH="$HOME/.nvm/versions/node/v20.20.2/bin:$ISO/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"
L=_consolidation/results/stepE_test.log; : > $L
for ver in ${STEPE_VERS:-before after}; do
  if [ $ver = before ]; then T=$(mktemp -d)/b; mkdir -p $T; git archive stepE-start | tar -x -C $T
    (cd $T && find . -type f | sed 's|^\./||') > $T.list
  else T=$ISO; git --no-optional-locks ls-files -co --exclude-standard | grep -v '^_research/tmp/' > /tmp/stepE_after.list; cp /tmp/stepE_after.list $T/_consolidation/results/.stepE_after.list 2>/dev/null; fi
  echo "== $ver" >> $L
  if [ $ver = before ]; then python3 _consolidation/stepE_test.py $T $T.list $ISO >> $L 2>&1; else python3 _consolidation/stepE_test.py $ISO /tmp/stepE_after.list $ISO >> $L 2>&1; fi
  echo "rc=$?" >> $L
done; echo DONE >> $L
