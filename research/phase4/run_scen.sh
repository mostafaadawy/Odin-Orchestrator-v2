#!/bin/bash
# Real-scenario head-to-head: restart the ISOLATED copy server with the measurement-only experiment switch, interleave
# Normal / Jev x 3 reps, then restart the copy server WITHOUT the switch (back to shadow).
cd /Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2
while pgrep -f "baseline_claude.py" >/dev/null; do sleep 20; done
ODIN_JEV_EXPERIMENT=1 bash _isolation/up.sh; sleep 12
for r in 1 2 3; do for m in normal jev; do
  .venv/bin/python research/phase4/scenario_h2h.py $m $r || { echo "stopped at $m $r rc=$?"; break 2; }
done; done
bash _isolation/up.sh; sleep 8
curl -s -m5 -H "X-Odin-Token: $(cat data/brain_token)" http://127.0.0.1:28000/settings/decider-mode; echo
echo SCEN-DONE
