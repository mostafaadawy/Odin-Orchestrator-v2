#!/bin/bash
# Owner 2026-10-13 item 7: run ONLY after the owner's labels are in data/gt_owner.jsonl, in this order:
#   layer choice on the real validation set -> temperature scaling -> thresholds (train_decider.py --after-labels)
#   -> head-to-head for BOTH model sizes (h2h.py) -> statistics. Plan login only.
set -e
cd /Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2/research/phase4
PY=../../.venv/bin/python
test -s data/gt_owner.jsonl || { echo "no owner labels yet - nothing run"; exit 2; }
caffeinate -i $PY outcome_labels.py
caffeinate -i $PY train_decider.py --after-labels
for m in Qwen2.5-0.5B-Instruct Qwen2.5-1.5B-Instruct; do
  ODIN_JEV_DIR=$PWD/../../data/jev_models/$m H2H_TAG=after_labels_$m caffeinate -i $PY h2h.py > h2h_after_labels_$m.log 2>&1
done
echo AFTER-LABELS-DONE
