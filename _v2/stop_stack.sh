#!/bin/bash
# stop every v2 stack process (dev or production run) — scoped to the v2 folder / its ports only
pkill -INT -f 'shells/development_full_checker.sh' 2>/dev/null; pkill -INT -f 'shells/production_full_checker.sh' 2>/dev/null; sleep 4
pkill -f 'Odin-Orchestrator-v2/desktop/node_modules' 2>/dev/null
pkill -f 'Odin-Orchestrator-v2/shells/poller_supervisor.sh' 2>/dev/null; pkill -f 'Odin-Orchestrator-v2/shells/phase_ctl.sh' 2>/dev/null
pkill -f 'Odin-Orchestrator-v2.*local_poller' 2>/dev/null
for p in 8000 9100 9104 9300 8080 5173; do for pid in $(lsof -ti tcp:$p -sTCP:LISTEN); do
  ps -o command= -p $pid | grep -q -E 'Odin-Orchestrator-v2|anchor_remote|sim_server|webhook_receiver|_web_serve|uvicorn|flutter|dart' && kill $pid; done; done
pkill -f 'shells/development_full_checker.sh' 2>/dev/null; sleep 2
for p in 8000 9100 9104 9300 8080 5173; do printf "$p:$(lsof -ti tcp:$p -sTCP:LISTEN | wc -l | tr -d ' ') "; done; echo
