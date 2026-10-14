#!/usr/bin/env bash
# anchor_loop.sh — ONE command to run + control BOTH Anchor phases, agent-driven (like workspace/shared/testing/loop.sh).
#
# Start it once (leave it running; the Claude agent drives it through mounted files):
#     nohup bash anchor_loop.sh > workspace/logs/anchor_loop.log 2>&1 &
#
# The agent controls everything via files under workspace/logs/phase_ctl/ :
#   RUN   → write "phase2" (local) | "phase3" (online) | "stop"     (which stack to bring up)
#   CMD   → bridge commands once a phase is up: health | send <project_id> <prompt…> | tail <comp> | vm | redeploy
#   STATUS, OUT.log → what the agent reads back to confirm + find issues
#
# Each phase POPS UP the anchor page (:9104), the desktop app, and Flutter (web + iOS sim) so YOU watch
# while the agent drives — the hybrid test. Ctrl-C stops the loop and the current phase (the ONLINE anchor
# on the VM stays up as its own service — Test 6 keeps it).
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"; CTL="workspace/logs/phase_ctl"; mkdir -p "$CTL"
RUN="$CTL/RUN"; ST="$CTL/STATUS"
[ -f "$RUN" ] || : > "$RUN"
mt(){ stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null || echo 0; }
CHILD=""

free_ports(){
  command -v lsof >/dev/null 2>&1 || return 0
  for P in 19100 19104 19300 18080 ; do KP="$(lsof -ti tcp:"$P" 2>/dev/null || true)"; [ -n "$KP" ] && kill -9 $KP 2>/dev/null || true; done
}
stop_phase(){
  [ -n "$CHILD" ] && kill "$CHILD" 2>/dev/null || true
  # stop the stack children this app spawns (never touches anything else)
  pkill -f "development_full_checker.sh" 2>/dev/null || true
  pkill -f "production_full_checker.sh" 2>/dev/null || true
  pkill -f "phase_ctl.sh" 2>/dev/null || true
  pkill -f "anchor_remote.py" 2>/dev/null || true
  pkill -f "local_poller_http.py" 2>/dev/null || true
  pkill -f "webhook_receiver.py" 2>/dev/null || true
  pkill -f "http.server 9104" 2>/dev/null || true
  sleep 1; free_ports; CHILD=""
}
start_phase(){
  local ph="$1"
  stop_phase
  case "$ph" in
    phase2) echo "PHASE2 (local) up $(date)"  > "$ST"; bash shells/development_full_checker.sh >"$ROOT/workspace/logs/phase2_run.log" 2>&1 & CHILD=$! ;;
    phase3) echo "PHASE3 (online) up $(date)" > "$ST"; bash shells/production_full_checker.sh >"$ROOT/workspace/logs/phase3_run.log" 2>&1 & CHILD=$! ;;
    stop)   echo "STOPPED $(date)"            > "$ST"; return ;;
    *)      echo "unknown RUN '$ph' (use phase2|phase3|stop)"; return ;;
  esac
  echo "  → $ph launched (pid $CHILD). run log: workspace/logs/${ph}_run.log · bridge: $CTL/OUT.log"
}
trap 'echo "anchor-loop stopping"; stop_phase; exit 0' INT TERM

echo "anchor-loop ready. $(date)" | tee "$ST"
echo ""
echo ">>> Type a command here (or the agent writes it to $RUN):"
echo ">>>   phase2   bring up LOCAL phase 2 (apps pop up; agent drives via the bridge)"
echo ">>>   phase3   HYBRID GATE — only when you AND the agent agree phase 2 is good: deploy & move to ONLINE phase 3"
echo ">>>   done     phase 3 confirmed done → CLOSE everything and exit   (alias: close)"
echo ">>>   stop     tear down the current phase but keep the loop running"
echo ""
LAST="$(mt "$RUN")"
C0="$(tail -1 "$RUN" 2>/dev/null)"; [ -n "$C0" ] && start_phase "$C0"
handle(){
  local cmd="$1"
  case "$cmd" in
    done|close|exit|quit)
      echo "closing — phase confirmed done. tearing down the local stack (the ONLINE anchor stays up as its VM service)."
      stop_phase; echo "CLOSED $(date)" > "$ST"; exit 0 ;;
    phase2|phase3|stop) start_phase "$cmd" ;;
    "") : ;;
    *) echo "unknown '$cmd' (phase2|phase3|stop|done)" ;;
  esac
}
while true; do
  # (a) the AGENT drives by writing the RUN file
  NOW="$(mt "$RUN")"
  if [ "$NOW" != "$LAST" ]; then LAST="$NOW"; C="$(tail -1 "$RUN" 2>/dev/null)"; [ -n "$C" ] && { echo "[from agent] $C"; handle "$C"; }; fi
  if [ -n "$CHILD" ] && ! kill -0 "$CHILD" 2>/dev/null; then echo "phase exited $(date) — see run log" > "$ST"; CHILD=""; fi
  # (b) YOU drive by typing (foreground only). The timed read also serves as the ~2s poll delay.
  if [ -t 0 ]; then
    if IFS= read -t 2 -r line; then
      line="$(echo "$line" | tr -d '[:space:]')"
      [ -n "$line" ] && { echo "$line" > "$RUN"; LAST="$(mt "$RUN")"; echo "[you] $line"; handle "$line"; }
    fi
  else
    sleep 2
  fi
done
