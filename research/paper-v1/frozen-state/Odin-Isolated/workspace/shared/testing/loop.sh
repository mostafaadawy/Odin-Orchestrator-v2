#!/usr/bin/env bash
# Odin autonomous test LOOP — execution host on YOUR machine that the agent fully controls via files.
#
# Start ONCE (you can close the terminal if you use nohup):
#   nohup bash testing/loop.sh > testing/results/daemon.log 2>&1 &
#
# The AGENT controls everything through the shared workspace folder — no babysitting:
#   • touch/echo into  testing/results/RUN_NOW   → (re)START a run. Content = filter word
#                                                   ("all", "shipping", "email", "revealer", "real", …).
#                                                   If a run is in progress it is STOPPED first, then a
#                                                   fresh one starts (so new code is always picked up).
#   • touch            testing/results/STOP       → STOP the current run immediately.
#   • results land in  testing/results/latest.log  + STATUS + RUN_SEQ (the agent reads these).
#
# AUTONOMOUS loop CLEANS data after each test (ODIN_TEST_CLEAN=1) for correct fresh behavior every
# trial. (When YOU run `python3 testing/` yourself, you instead get the keep/clean prompt.)
# Test 1 stays propose-only unless ODIN_TEST_PROD_DEPLOY=1 is exported before starting.
set -uo pipefail
cd "$(dirname "$0")/../../.."
source .venv/bin/activate 2>/dev/null || true
mkdir -p testing/results
R="testing/results"
TRIG="$R/RUN_NOW"; STOP="$R/STOP"; STATUS="$R/STATUS"; LOG="$R/latest.log"; SEQ="$R/RUN_SEQ"
[ -f "$SEQ" ]  || echo 0   > "$SEQ"
[ -f "$TRIG" ] || echo all > "$TRIG"
: > "$STOP" 2>/dev/null || true
mt(){ stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null || echo 0; }

RUNPID=""
start_run(){
  local f; f="$(tr -d '[:space:]' < "$TRIG" 2>/dev/null)"; [ -z "$f" ] && f="all"
  echo "RUNNING filter=$f $(date)" > "$STATUS"
  echo ">>> starting run (filter=$f)"
  # tee → both the log file (for the agent) AND this terminal (so a FOREGROUND run is fully visible)
  #  • ODIN_TEST_SEED_ON_PASS=1 → keep a PASSING run's data, clean only a real FAIL (owner's rule).
  #  • ODIN_GATE_MODEL=haiku → the evaluative QA/CTO-review gates run on a FAST model in TESTING so we
  #    don't wait ~10 min/step. It does NOT skip any rule and does NOT touch production (which sets no
  #    model → full model, full rigor). `unset ODIN_GATE_MODEL` before launch to run gates full-model.
  ( ODIN_TEST_SEED_ON_PASS=1 ODIN_GATE_MODEL="${ODIN_GATE_MODEL:-haiku}" python3 testing/ "$f" < /dev/null 2>&1 | tee "$LOG" ) &
  RUNPID=$!
}
stop_run(){
  [ -z "$RUNPID" ] && return 0
  if kill -0 "$RUNPID" 2>/dev/null; then
    pkill -P "$RUNPID" 2>/dev/null || true        # python child of the subshell
    kill "$RUNPID" 2>/dev/null || true
    sleep 1
    kill -9 "$RUNPID" 2>/dev/null || true
    pkill -f "python3 testing/" 2>/dev/null || true   # stray runner
    pkill -f "claude -p You are" 2>/dev/null || true  # agents spawned by this run
    echo "STOPPED $(date)" > "$STATUS"; echo "<<< run stopped by agent"
  fi
  RUNPID=""
}

echo "Odin loop ready (autonomous). Agent drives via RUN_NOW / STOP. Ctrl-C to quit."
LASTT="$(mt "$TRIG")"; LASTS="$(mt "$STOP")"
start_run    # initial run on launch
while true; do
  NT="$(mt "$TRIG")"; NS="$(mt "$STOP")"
  if [ "$NS" != "$LASTS" ]; then LASTS="$NS"; stop_run; fi          # agent asked to STOP
  if [ "$NT" != "$LASTT" ]; then LASTT="$NT"; stop_run; start_run; fi  # agent asked to (re)start
  if [ -n "$RUNPID" ] && ! kill -0 "$RUNPID" 2>/dev/null; then       # run finished on its own
    N="$(( $(cat "$SEQ" 2>/dev/null || echo 0) + 1 ))"; echo "$N" > "$SEQ"
    echo "DONE seq=$N $(date)" > "$STATUS"; echo "<<< run #$N finished (results: $LOG)"
    RUNPID=""
  fi
  sleep 2
done
