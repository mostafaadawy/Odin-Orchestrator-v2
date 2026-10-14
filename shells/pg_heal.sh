#!/bin/bash
# v2: make sure the main Postgres (odin_core / odin_anchor) is up before anything starts.
# After a Mac restart Postgres can refuse to start because of a stale postmaster.pid whose PID now belongs to
# another process (seen 2026-10-14: projects/agents vanished from the desktop). Heal that one case only.
PGDATA_DIR="${PGDATA_DIR:-/opt/homebrew/var/postgresql@14}"
command -v pg_isready >/dev/null 2>&1 || exit 0
pg_isready -q -h /tmp -p 5432 && { echo "  ✓ Postgres up"; exit 0; }
PIDF="$PGDATA_DIR/postmaster.pid"
if [ -f "$PIDF" ]; then
  P="$(head -1 "$PIDF")"
  if ! ps -o command= -p "$P" 2>/dev/null | grep -q postgres; then
    mv -n "$PIDF" "$PIDF.stale_$(date +%Y%m%d_%H%M%S)" && echo "  ↻ stale Postgres lock moved aside (PID $P is not Postgres)"
  fi
fi
brew services restart postgresql@14 >/dev/null 2>&1 || true
for i in $(seq 1 15); do pg_isready -q -h /tmp -p 5432 && { echo "  ✓ Postgres started"; exit 0; }; sleep 1; done
echo "  ❌ Postgres is not running — projects and agents would not load. Check /opt/homebrew/var/log/postgresql@14.log"; exit 1
