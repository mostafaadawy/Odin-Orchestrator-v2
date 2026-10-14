#!/bin/bash
# Rep 3 of the real-scenario head-to-head (rep 3 stopped at a plan limit on 2026-10-13). Waits for the plan reset (22:12
# local), re-runs Normal r3 and Jev r3 in full on the isolated copy server with the experiment switch, then restores shadow.
cd /Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2
while [ "$(date +%H%M)" -lt 2212 ]; do sleep 60; done
.venv/bin/python -c "import sys;sys.path.insert(0,'server');import claude_cli;sys.exit(1 if claude_cli.paid_auth_problem() else 0)" || { echo "R-ZC STOP"; exit 3; }
ODIN_JEV_EXPERIMENT=1 bash _isolation/up.sh; sleep 12
for m in normal jev; do .venv/bin/python research/phase4/scenario_h2h.py $m 3 || { echo "stopped at $m 3 rc=$?"; break; }; done
bash _isolation/up.sh; sleep 8
curl -s -m5 -H "X-Odin-Token: $(cat data/brain_token)" http://127.0.0.1:28000/settings/decider-mode; echo
echo SCEN3-DONE
