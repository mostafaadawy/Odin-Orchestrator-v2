#!/usr/bin/env bash
# anchor_up.sh — run ONLY the anchor (+ its poller) in a SEPARATE terminal.
#
# THE DRILL:
#   1) Start Phase 2 and answer "no" to the anchor question → web/flutter/desktop come up WITHOUT the anchor.
#      The apps must show "You are offline" and NO data (proof they depend on the anchor, not the backend).
#   2) In another terminal run:  bash anchor_up.sh   → the anchor comes online and the poller syncs the
#      brain's data into it. Refresh the web/flutter → the offline message clears and the data appears.
#
# Ctrl-C here stops ONLY the anchor + poller (so you can watch the apps go offline again). The brain, web,
# flutter and desktop keep running under Phase 2.
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/local/sbin:$HOME/.local/bin:$PATH"
for V in "${ODIN_VENV:-}" ".venv" "venv" "../.venv" "$HOME/.venvs/odin"; do
  if [ -n "$V" ] && [ -f "$V/bin/activate" ]; then source "$V/bin/activate"; break; fi
done
PYBIN="$(command -v python || command -v python3)"

BRAIN_PORT="${BRAIN_PORT:-8000}"
ANCHOR_PORT="${ANCHOR_PORT:-9100}"
mkdir -p workspace/logs

PIDS=()
cleanup() {
  trap - EXIT INT TERM
  echo ""; echo "stopping the anchor + poller (apps stay up; they will go offline again)…"
  for pid in "${PIDS[@]:-}"; do kill "$pid" 2>/dev/null || true; done
  sleep 1
  for pid in "${PIDS[@]:-}"; do kill -9 "$pid" 2>/dev/null || true; done
  if command -v lsof >/dev/null 2>&1; then
    KP="$(lsof -ti tcp:"$ANCHOR_PORT" 2>/dev/null || true)"; [ -n "$KP" ] && kill -9 $KP 2>/dev/null || true
  fi
  echo "anchor stopped — port $ANCHOR_PORT freed."
}
trap cleanup EXIT INT TERM

# the poller needs the brain (data source). If Phase 2 isn't running it, start it here.
if ! "$PYBIN" -c "import urllib.request;urllib.request.urlopen('http://localhost:$BRAIN_PORT/health',timeout=2)" >/dev/null 2>&1; then
  echo "brain not up on :$BRAIN_PORT — starting it (data source for the mirror)…"
  USE_VOICE=0 "$PYBIN" -m uvicorn server.app:app --host 127.0.0.1 --port "$BRAIN_PORT" >workspace/logs/brain.log 2>&1 &
  PIDS+=($!)
  for i in $(seq 1 30); do "$PYBIN" -c "import urllib.request;urllib.request.urlopen('http://localhost:$BRAIN_PORT/health',timeout=2)" >/dev/null 2>&1 && break; sleep 1; done
else
  echo "brain already running on :$BRAIN_PORT — reusing it."
fi

# free the anchor port if a stale one is bound, then start the anchor + poller (unbuffered logs)
if command -v lsof >/dev/null 2>&1; then KP="$(lsof -ti tcp:"$ANCHOR_PORT" 2>/dev/null || true)"; [ -n "$KP" ] && kill -9 $KP 2>/dev/null || true; fi
# anchor uses PostgreSQL (robust) — falls back to JSON automatically if Postgres is unreachable.
( cd server && ANCHOR_PG_DSN="${ANCHOR_PG_DSN:-dbname=odin_anchor}" "$PYBIN" -u anchor_remote.py --host 0.0.0.0 --port "$ANCHOR_PORT" >"$ROOT/workspace/logs/anchor_remote.log" 2>&1 ) &
PIDS+=($!)
sleep 2
( cd server && "$PYBIN" -u local_poller_http.py --anchor "http://localhost:$ANCHOR_PORT" --interval 4 >"$ROOT/workspace/logs/local_poller.log" 2>&1 ) &
PIDS+=($!)

echo ""
echo "================ ANCHOR IS UP (standalone) ================"
echo "  anchor        http://localhost:$ANCHOR_PORT/anchor/v1/_status   (the ONLY door for web/flutter)"
echo "  projects read http://localhost:$ANCHOR_PORT/anchor/v1/projects"
echo "  poller        syncing the brain → anchor every 4s (projects, pools, roles, agents, connectors)"
echo "  → now REFRESH the web/flutter: the offline message clears and the synced data appears."
echo "  Ctrl-C stops the anchor again (watch the apps go back offline)."
echo "=========================================================="
# open the anchor's LANDING PAGE in the browser once it answers (so you SEE it is online + reach Manage)
if command -v open >/dev/null 2>&1; then
  ( for i in $(seq 1 12); do curl -sf -o /dev/null -m 2 "http://localhost:$ANCHOR_PORT/anchor/v1/_status" && break; sleep 1; done
    open "http://localhost:$ANCHOR_PORT/" >/dev/null 2>&1 || true ) &
fi
wait
