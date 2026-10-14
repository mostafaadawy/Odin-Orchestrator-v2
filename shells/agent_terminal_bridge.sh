#!/usr/bin/env bash
# ==============================================================================================
# agent_terminal_bridge.sh
#   Grants the Odin agent controlled command access to THIS Mac terminal — so it can run tools that
#   only exist in your environment (az CLI, psql / createdb / Postgres setup, brew, ssh, etc.) on your
#   behalf while you watch.
#
#   YOU stay in control:
#     • every command is PRINTED here before it runs,
#     • it runs in THIS shell (your logins, your PATH, your venv),
#     • press Ctrl-C at any time to STOP the bridge and revoke access immediately.
#
#   How it works: the agent writes a command into workspace/logs/agent_term/CMD; this loop detects the change,
#   runs it, and writes the combined output to workspace/logs/agent_term/OUT.log (which the agent reads back).
# ==============================================================================================
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
DIR="$ROOT/workspace/logs/agent_term"
mkdir -p "$DIR"
CMD="$DIR/CMD"; OUT="$DIR/OUT.log"; ST="$DIR/STATUS"
: > "$CMD"; : > "$OUT"
echo "READY $(date)" > "$ST"

# make your project tools available (venv → python/psql wrappers, etc.)
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/local/sbin:$HOME/.local/bin:$PATH"
for V in "${ODIN_VENV:-}" ".venv" "venv" "../.venv"; do
  if [ -n "$V" ] && [ -f "$V/bin/activate" ]; then source "$V/bin/activate"; break; fi
done

cleanup() {
  trap - EXIT INT TERM
  echo ""
  echo "agent-terminal bridge STOPPED — access revoked. $(date)"
  echo "STOPPED $(date)" > "$ST"
  exit 0
}
trap cleanup EXIT INT TERM

# portable mtime (BSD/macOS: stat -f %m ; GNU/Linux: stat -c %Y)
mt() { stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null; }

echo "=================================================================="
echo "  AGENT TERMINAL BRIDGE — the agent can now run commands in THIS shell."
echo "    • every command is printed below BEFORE it runs"
echo "    • output → workspace/logs/agent_term/OUT.log (the agent reads it)"
echo "    • press Ctrl-C to STOP and revoke access"
echo "=================================================================="
echo "agent-terminal bridge started $(date)" >> "$OUT"

LAST=""
while true; do
  NOW="$(mt "$CMD")"
  if [ -n "$NOW" ] && [ "$NOW" != "$LAST" ]; then
    LAST="$NOW"
    sleep 0.2                       # let the write finish
    C="$(cat "$CMD" 2>/dev/null)"
    if [ -n "$C" ]; then
      echo ""
      echo ">>> [$(date '+%H:%M:%S')] running:"
      printf '%s\n' "$C" | sed 's/^/      /'
      {
        echo ""
        echo "=== CMD @ $(date '+%H:%M:%S') ==="
        printf '%s\n' "$C"
        echo "--- OUTPUT ---"
      } >> "$OUT"
      echo "RUNNING $(date)" > "$ST"
      # ---- HANG-PROOF EXECUTION -------------------------------------------------------------------
      # Past hangs were caused by capturing output with $(bash -c ...), which reads a PIPE and waits
      # for EVERY writer to close it. Any command that backgrounds a long-lived process (uvicorn, the
      # poller, headless chrome, the flutter web-server) keeps that pipe open, so $() never returns even
      # though the command already finished. Fix, so the bridge can NEVER hang again:
      #   • capture to a FILE, not a $() pipe  → backgrounded children can't block the loop,
      #   • stdin from /dev/null               → a command can never sit waiting for input,
      #   • a hard TIMEOUT watchdog            → a runaway FOREGROUND command is killed, never infinite.
      TMP="$DIR/.run_out"; : > "$TMP"
      TIMEOUT="${ODIN_CMD_TIMEOUT:-900}"      # 15 min default (long builds finish; true hangs get killed)
      bash -c "$C" </dev/null >"$TMP" 2>&1 &
      CPID=$!
      ( sleep "$TIMEOUT"
        kill -TERM "$CPID" 2>/dev/null; pkill -TERM -P "$CPID" 2>/dev/null; sleep 3
        kill -KILL "$CPID" 2>/dev/null; pkill -KILL -P "$CPID" 2>/dev/null
        printf '\n[bridge] command exceeded %ss — terminated. The bridge stays alive.\n' "$TIMEOUT" >> "$TMP"
      ) & WPID=$!
      wait "$CPID" 2>/dev/null; RC=$?
      kill "$WPID" 2>/dev/null; wait "$WPID" 2>/dev/null   # cancel the watchdog if the command finished in time
      OUTPUT="$(cat "$TMP" 2>/dev/null)"
      printf '%s\n' "$OUTPUT"                 # echo to your terminal (you see it)
      { printf '%s\n' "$OUTPUT"; echo "--- EXIT $RC ---"; } >> "$OUT"
      echo "IDLE (last exit $RC) $(date)" > "$ST"
      echo "<<< done (exit $RC)"
    fi
  fi
  sleep 1
done
