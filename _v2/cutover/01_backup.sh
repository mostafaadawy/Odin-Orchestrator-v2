#!/bin/bash
# CUTOVER STEP 1 — full backup BEFORE anything changes. Nothing is modified here; v1's folder is not touched.
# Writes: _v2/cutover/backup_<ts>/ (gitignored) + MANIFEST.sha256. Never prints a secret.
set -uo pipefail
export PATH=/opt/homebrew/bin:/opt/homebrew/opt/postgresql@14/bin:/usr/bin:/bin:/usr/sbin:/sbin
V2=$HOME/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2; V1=$HOME/Desktop/AiAgentWorkSpace/Odin-Orchestrator
TS=$(date +%Y%m%d_%H%M%S); B=$V2/_v2/cutover/backup_$TS; mkdir -p "$B"; echo "$B" > $V2/_v2/cutover/LAST_BACKUP
fail(){ echo "❌ STEP 1 FAILED: $*"; exit 1; }
# a) the installed desktop app + its profile
[ -d /Applications/Odin.app ] && { ditto /Applications/Odin.app "$B/Odin.app" || fail "copy Odin.app"; echo "  ✓ Odin.app"; }
[ -d "$HOME/Library/Application Support/odin-desktop" ] && { ditto "$HOME/Library/Application Support/odin-desktop" "$B/app-support-odin-desktop" || fail "copy app data"; echo "  ✓ app data (odin-desktop profile)"; }
# b) databases (custom format, restorable)
for db in odin_core odin_anchor; do
  pg_dump -Fc -d $db -f "$B/$db.dump" || fail "pg_dump $db"; [ -s "$B/$db.dump" ] || fail "empty dump $db"; echo "  ✓ $db dump ($(du -h "$B/$db.dump" | cut -f1))"
  psql -d $db -Atc "select table_name from information_schema.tables where table_schema='public' and table_type='BASE TABLE' order by 1" \
    | while read t; do echo "$t $(psql -d $db -Atc "select count(*) from public.\"$t\"")"; done > "$B/$db.rowcounts" || fail "row counts $db"
done
# c) launchd plist (PC-1, removed in step 6)
P=$HOME/Library/LaunchAgents/com.odin.egypt-amazon-poster.plist
[ -f "$P" ] && { cp -p "$P" "$B/" || fail "plist"; echo "  ✓ launchd plist"; }
# d) v1 state stamp (v1 is left in place untouched — it is its own backup)
git -C "$V1" --no-optional-locks rev-parse HEAD > "$B/v1_HEAD" 2>/dev/null; git -C "$V1" --no-optional-locks status --porcelain > "$B/v1_status" 2>/dev/null
# e) absolute v1 paths stored in the database (decides whether step 3 needs a DB repath)
psql -d odin_core -Atc "select 'projects', count(*) from projects where path like '%AiAgentWorkSpace/Odin-Orchestrator/%' or config::text like '%AiAgentWorkSpace/Odin-Orchestrator/%'" > "$B/db_v1_paths" 2>&1
( cd "$B" && find . -type f ! -name MANIFEST.sha256 -print0 | xargs -0 shasum -a 256 > MANIFEST.sha256 )
echo "  ✓ manifest: $(wc -l < "$B/MANIFEST.sha256") files"; echo "BACKUP OK: $B"
