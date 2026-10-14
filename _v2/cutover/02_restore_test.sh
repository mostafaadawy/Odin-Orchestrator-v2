#!/bin/bash
# CUTOVER STEP 1b (owner condition B) — PROVE the dumps restore: into scratch databases, compare every table's row count
# with the counts taken at backup time, then drop ONLY the scratch databases this script created.
set -uo pipefail
export PATH=/opt/homebrew/bin:/opt/homebrew/opt/postgresql@14/bin:/usr/bin:/bin
V2=$HOME/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2; B=$(cat $V2/_v2/cutover/LAST_BACKUP)
ok=1
for db in odin_core odin_anchor; do
  S=${db}_restoretest_$$
  createdb "$S" || { echo "❌ createdb $S"; exit 1; }
  pg_restore --no-owner -d "$S" "$B/$db.dump" 2> "$B/${db}_restore.err" || true
  bad=0; n=0
  while read t c; do n=$((n+1)); r=$(psql -d "$S" -Atc "select count(*) from public.\"$t\"" 2>/dev/null); [ "$r" = "$c" ] || { bad=$((bad+1)); echo "   ✗ $db.$t backup=$c restored=${r:-missing}"; }; done < "$B/$db.rowcounts"
  [ $bad = 0 ] && echo "  ✓ $db: $n tables restored, every row count matches" || { echo "  ❌ $db: $bad of $n tables differ"; ok=0; }
  dropdb "$S"
done
[ $ok = 1 ] && echo "RESTORE TEST OK" || { echo "RESTORE TEST FAILED"; exit 1; }
