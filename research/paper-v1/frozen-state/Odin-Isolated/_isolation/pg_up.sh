#!/bin/bash
# PRIVATE throwaway PostgreSQL cluster(s) for the isolated copy ONLY. Never touches the owner's server (5432).
# usage: pg_up.sh [PORT=15432] [--restore|--reset]   data in _research/tmp/pg/data_<port>, socket _research/tmp/pg/sock
P=${1:-15432}; T=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Isolated/_research/tmp/pg
export PATH=/opt/homebrew/bin:$PATH LC_ALL=en_US.UTF-8
D="$T/data_$P"; [ "$P" = 15432 ] && [ -d "$T/data" ] && D="$T/data"
if [ ! -f "$D/PG_VERSION" ]; then initdb -D "$D" -A trust -U mostafaadawy >/dev/null 2>&1; fi
pg_ctl -D "$D" -o "-p $P -k $T/sock -c listen_addresses=''" -l "$T/pg_$P.log" -w start >/dev/null 2>&1 || true
export PGHOST="$T/sock" PGPORT=$P
if [ "$2" = "--reset" ]; then dropdb --if-exists odin_core_iso; dropdb --if-exists odin_anchor_iso; fi
for db in odin_core_iso odin_anchor_iso; do psql -d postgres -Atc "select 1 from pg_database where datname='$db'" | grep -q 1 || createdb "$db"; done
if [ "$2" = "--restore" ] || [ "$2" = "--reset" ]; then
  psql -q -d odin_core_iso -f "$T/odin_core.sql" >/dev/null 2>"$T/restore_err_$P.log"
  psql -q -d odin_anchor_iso -f "$T/odin_anchor_schema.sql" >/dev/null 2>>"$T/restore_err_$P.log"
fi
echo "pg:$P projects=$(psql -d odin_core_iso -Atc 'select count(*) from projects') files=$(psql -d odin_core_iso -Atc 'select count(*) from files')"
