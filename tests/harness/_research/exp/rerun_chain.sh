#!/bin/bash
ISO=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated; cd $ISO
export ODIN_SCOPE_HOOK=enforce
SUF=_after CAPUSD=19 _research/exp/revealer_run.sh
echo REVEALER_AFTER_DONE >> _research/results/llm_series.log
REP=32 NS=5 ADV=1 ODIN_SCOPE_HOOK=enforce ODIN_SCOPE_HOOK_TRACE=1 LIMIT=19.5 _research/exp/llm_series.sh
echo ADV2_DONE >> _research/results/llm_series.log
