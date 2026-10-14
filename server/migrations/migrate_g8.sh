#!/bin/bash
# G8 migration: up | down | status.  ALWAYS takes a full backup of the database first (pg_dump -Fc).
# usage: migrate_g8.sh up|down|status [dbname=odin_core] [backup_dir]
# Uses the libpq environment (PGHOST/PGPORT/PGUSER). In the copy: PGHOST=/tmp/odc_pg PGPORT=25432|25433.
# Restore a backup if ever needed:  pg_restore --clean --if-exists -d <db> <backup file>
set -euo pipefail
ACT=${1:-status}; DB=${2:-odin_core}
HERE=$(cd "$(dirname "$0")" && pwd)
BK=${3:-$HERE/../../_research/tmp/pg/backups}
has() { psql -d "$DB" -Atc "SELECT count(*) FROM information_schema.columns WHERE table_schema='public' AND table_name='files' AND column_name='created_by'"; }
if [ "$ACT" = status ]; then echo "created_by column present: $( [ "$(has)" = 1 ] && echo yes || echo no )"; exit 0; fi
[ "$ACT" = up ] || [ "$ACT" = down ] || { echo "usage: $0 up|down|status [db] [backup_dir]"; exit 2; }
mkdir -p "$BK"; F="$BK/${DB}_before_g8_${ACT}_$(date +%Y%m%d_%H%M%S).dump"
pg_dump -Fc -d "$DB" -f "$F"
[ -s "$F" ] || { echo "BACKUP FAILED — nothing changed"; exit 1; }
echo "backup: $F"
psql -v ON_ERROR_STOP=1 -q -d "$DB" -f "$HERE/g8_files_created_by.$ACT.sql"
echo "done: $ACT; created_by column present: $( [ "$(has)" = 1 ] && echo yes || echo no )"
