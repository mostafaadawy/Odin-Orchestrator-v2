#!/bin/bash
# Fix #2 test batch A (no LLM cost): unit checks + regression + owner's phase7 lifecycle/strong,
# BEFORE (server from tag fix1-done) and AFTER (current). Same procedure as fix #1.
ISO=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated; cd $ISO
export PATH="$ISO/_isolation/shims:$ISO/.venv/bin:/opt/homebrew/bin:/usr/bin:/bin" PGHOST=/tmp/odc_pg PGPORT=25433 ANCHOR_PG_DSN="dbname=odin_anchor_con" ODIN_SCOPE_HOOK=enforce
L=_consolidation/results/${FIX2_LOG:-fix2_tests.log}; : > $L
python _consolidation/fix2_unit.py server ../Odin-Orchestrator/workspace > _consolidation/results/fix2_unit.log 2>&1; echo "== unit: $(tail -1 _consolidation/results/fix2_unit.log)" >> $L
mk(){ T=$(_research/exp/mkroot.sh $1 fullall | tail -1); chmod -R u+w $T
      rm -rf $T/workspace && mkdir -p $T/workspace && git archive 4945000 workspace | tar -x -C $T && mkdir -p $T/workspace/chats $T/workspace/logs
      if [ "$2" = before ]; then rm -rf $T/server && mkdir -p $T/server && git archive ${FIX2_BEFORE:-fix1-done} server | tar -x -C $T && git archive ${FIX2_BEFORE:-fix1-done} workspace/shared | tar -x -C $T; fi; echo $T; }
for ver in ${FIX2_VERS:-before after}; do
  _isolation/pg_up.sh 25433 --reset >/dev/null 2>&1; [ "$G8_MIG" = 1 ] && server/migrations/migrate_g8.sh up odin_core_con $ISO/_research/tmp/pg/backups >/dev/null 2>&1; T=$(mk f2rg_$ver $ver)
  echo "== regression $ver: $(python _research/regression/regress.py $T 2>&1 | tail -1)" >> $L
  for t in lifecycle strong; do
    n=1; [ $ver = after ] && n=${FIX2_N:-3}
    for rep in $(seq 1 $n); do
      _isolation/pg_up.sh 25433 --reset >/dev/null 2>&1; [ "$G8_MIG" = 1 ] && server/migrations/migrate_g8.sh up odin_core_con $ISO/_research/tmp/pg/backups >/dev/null 2>&1; T=$(mk f2p7_${ver}_${t}_$rep $ver)
      pre=$(cd $T && python -c "import sys;sys.path.insert(0,'server');import workspace_audit as a;[a.heal(force=True) for _ in range(4)];print(len(a.scan()))" 2>/dev/null | tail -1)
      (cd $T && python workspace/shared/testing/phase7_$t.py > $ISO/_consolidation/results/fix2_p7_${t}_${ver}_$rep.log 2>&1); rc=$?
      echo "== phase7_$t $ver rep$rep start_violations=$pre rc=$rc :: $(grep -E 'ALL GREEN|FAIL|PASS|baseline' $ISO/_consolidation/results/fix2_p7_${t}_${ver}_$rep.log | tail -3 | tr '\n' ' ')" >> $L
    done
  done
done
echo DONE >> $L
