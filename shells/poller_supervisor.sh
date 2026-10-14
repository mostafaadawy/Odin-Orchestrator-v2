#!/usr/bin/env bash
# =============================================================================================
# poller_supervisor.sh — keeps the LOCAL POLLER alive, forever.
#   The poller (server/local_poller_http.py) is what drains the anchor request queue and mirrors
#   the pools to web/mobile. If it ever dies (SIGHUP on detach, a transient crash, OOM on a heavy
#   request), the whole request/sync flow silently stops. This supervisor guarantees it comes back:
#   it checks every few seconds and relaunches the poller if it is not running.
#   Launched (nohup'd) by development_full_checker.sh (dev) and production_full_checker.sh (production) so the poller is
#   self-healing in BOTH modes — including the production "run destination" the owner double-clicks.
# =============================================================================================
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
ANCHOR="${1:-http://localhost:9100}"
INTERVAL="${2:-4}"
LOG="$ROOT/workspace/logs/local_poller.log"
SUP="$ROOT/workspace/logs/poller_supervisor.log"
mkdir -p "$ROOT/workspace/logs"

# activate the project venv so the poller has its deps
for V in "${ODIN_VENV:-}" ".venv" "venv" "../.venv" "$HOME/.venvs/odin"; do
  if [ -n "$V" ] && [ -f "$V/bin/activate" ]; then source "$V/bin/activate"; break; fi
done
PYBIN="$(command -v python || command -v python3)"

echo "[poller-supervisor] up $(date) — anchor=$ANCHOR interval=${INTERVAL}s" >> "$SUP"
while true; do
  # NB: the [l] bracket makes this pattern not match the pgrep/supervisor command line itself (which would
  # otherwise make the supervisor think the poller is always running and never relaunch it).
  if ! pgrep -f "[l]ocal_poller_http.py --anchor" >/dev/null 2>&1; then
    echo "[poller-supervisor] poller not running — starting $(date)" >> "$SUP"
    ( cd server && nohup "$PYBIN" -u local_poller_http.py --anchor "$ANCHOR" --interval "$INTERVAL" >>"$LOG" 2>&1 </dev/null & )
  fi
  sleep 5
done
