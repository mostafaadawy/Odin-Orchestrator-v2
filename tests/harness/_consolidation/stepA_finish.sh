#!/bin/bash
# Step A: test (before/after), full suite, then report. No LLM. Commit is done separately after review.
cd /Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated
bash _isolation/pg_up.sh 25432 >/dev/null 2>&1; bash _isolation/pg_up.sh 25433 >/dev/null 2>&1
bash _consolidation/stepA_run.sh >/dev/null 2>&1
G8_MIG=1 FIX2_LOG=stepA_tests_mig.log FIX2_VERS=after FIX2_N=3 _consolidation/g8_tests.sh >/dev/null 2>&1
for x in g6 g6b g8 g8b g5 g7 f07 f37 g11 f38 g12 g9 g9b g10 g10r g13 f41i f06 f43 f08; do bash _consolidation/${x}_run.sh >/dev/null 2>&1; printf "%s: " $x; grep -h RESULT _consolidation/results/${x}_test.log | tail -1; done
FIX3_VERS=after bash _consolidation/fix3_run.sh >/dev/null 2>&1; printf "fix3: "; grep -h RESULT _consolidation/results/fix3_test.log | tail -1
.venv/bin/python _consolidation/f32g2_unit.py server 2>&1 | tail -1; .venv/bin/python _consolidation/f32c_unit.py server 2>&1 | tail -1
echo ALLDONE
