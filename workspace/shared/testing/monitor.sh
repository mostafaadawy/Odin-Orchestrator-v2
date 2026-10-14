#!/usr/bin/env bash
# Odin LIVE MONITOR — open this ONCE in its own terminal and LEAVE IT. It NEVER closes on its own:
#   • `tail -F` (capital F) follows the log BY NAME, so it survives the log being truncated/replaced
#     every time the agent (re)starts a run — plain `tail -f` dies on that; this does not.
#   • the `while true` wrapper RELAUNCHES tail if it ever exits for any reason, so the view is permanent.
# You just watch here, live, alongside the agent (step markers → starting step N/M, the heartbeat
# working… Ns, per-step results, scorecards, final verdict). Close it only when YOU want to (Cmd-W).
cd "$(dirname "$0")/../../.."
R="testing/results"; mkdir -p "$R"; touch "$R/latest.log"
echo "============================================================"
echo " ODIN LIVE MONITOR — leave open. Self-reconnecting; survives every re-run."
echo " The agent drives the tests; you watch here. (Close with Cmd-W when done.)"
echo "============================================================"
while true; do
  tail -n 200 -F "$R/latest.log" 2>/dev/null
  echo "  …(monitor reconnecting — a new run is starting)…"
  sleep 1
done
