#!/bin/bash
# v2 baseline / re-proof suite on the ISOLATED clone (no LLM, no network, no real DB, no real credentials).
# usage: _v2/iso/run_suite.sh <label>   -> _v2/results/<label>/summary.txt (+ logs). Same items as the Consolidated gate suite.
set -u
V2=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2; L=${1:?label}; OUT=$V2/_v2/results/$L; mkdir -p $OUT
# teardown of any previous run (stale postmasters survive an iso rebuild and serve EMPTY databases)
ISO0=$V2/_v2/iso_root; [ -f $ISO0/_research/runs/server.pid ] && kill "$(cat $ISO0/_research/runs/server.pid)" 2>/dev/null
for pt in 38000 39100 39104 39300 38080; do for pid in $(lsof -ti tcp:$pt -sTCP:LISTEN 2>/dev/null); do kill $pid 2>/dev/null; done; done
for lk in /tmp/odv2_pg/.s.PGSQL.2643[23].lock; do [ -f "$lk" ] && kill -INT "$(head -1 "$lk")" 2>/dev/null; done
for i in 1 2 3 4 5 6 7 8 9 10; do ls /tmp/odv2_pg/.s.PGSQL.2643[23].lock >/dev/null 2>&1 || break; sleep 1; done
cd $V2 && .venv/bin/python _v2/iso/build_iso.py > $OUT/build_iso.log 2>&1 || { echo "ISO BUILD FAILED" > $OUT/summary.txt; exit 2; }
cd $V2 && .venv/bin/python _v2/iso/scrub_iso.py >> $OUT/build_iso.log 2>&1 || { echo "ISO SCRUB FAILED" > $OUT/summary.txt; exit 2; }
ISO=$V2/_v2/iso_root; cd $ISO
bash _isolation/pg_up.sh 26432 --reset >/dev/null 2>&1; bash _isolation/pg_up.sh 26433 --reset >/dev/null 2>&1
for pt in 26432 26433; do echo "pg$pt: $(PGHOST=/tmp/odv2_pg PGPORT=$pt /opt/homebrew/bin/psql -d odin_core_v2i -Atc 'select count(*) from projects' 2>&1 | head -1)" >> $OUT/pg_check.txt; done
bash _isolation/up.sh >/dev/null 2>&1; sleep 10
echo "server: $(curl -s -m5 -o /dev/null -w %{http_code} http://127.0.0.1:38000/health)" > $OUT/summary.txt
G8_MIG=1 FIX2_LOG=v2_tests_mig.log FIX2_VERS=after FIX2_N=3 _consolidation/g8_tests.sh >/dev/null 2>&1
grep -h "regression\|phase7" _consolidation/results/v2_tests_mig.log >> $OUT/summary.txt 2>/dev/null
for x in g6 g6b g8 g8b g5 g7 f07 f37 g11 f38 g12 g9 g9b g10 g10r g13 f41i f06 f43 f08 stepA stepC stepD stepE stepF stepG f10 f11 f20 f21 f26 pc5 pc2 p4e pc4 f33; do
  [ -f _consolidation/${x}_run.sh ] || { echo "$x: (no runner)" >> $OUT/summary.txt; continue; }
  perl -e 'alarm shift; exec @ARGV' 900 bash _consolidation/${x}_run.sh >/dev/null 2>&1; printf "%s: " $x >> $OUT/summary.txt
  grep -h RESULT _consolidation/results/${x}_test.log 2>/dev/null | tail -1 >> $OUT/summary.txt || echo "(no result)" >> $OUT/summary.txt
done
FIX3_VERS=after perl -e 'alarm shift; exec @ARGV' 900 bash _consolidation/fix3_run.sh >/dev/null 2>&1; printf "fix3: " >> $OUT/summary.txt; grep -h RESULT _consolidation/results/fix3_test.log 2>/dev/null | tail -1 >> $OUT/summary.txt
for u in f32g2_unit f32c_unit fix2c_unit; do printf "%s: " $u >> $OUT/summary.txt; .venv/bin/python _consolidation/$u.py server 2>&1 | tail -1 >> $OUT/summary.txt; done
printf "f18: " >> $OUT/summary.txt; .venv/bin/python _consolidation/f18_acceptance.py >/dev/null 2>&1
.venv/bin/python -c "
import json,collections;d=json.load(open('_consolidation/results/f18_acceptance.json'))
rows=[r for v in d.values() if isinstance(v,list) for r in v if isinstance(r,dict)]
print(dict(collections.Counter(r.get('status') for r in rows)), 'of', len(rows))" >> $OUT/summary.txt 2>&1
cp -r _consolidation/results $OUT/logs 2>/dev/null
[ -f _research/runs/server.pid ] && kill "$(cat _research/runs/server.pid)" 2>/dev/null
echo SUITE-DONE >> $OUT/summary.txt
