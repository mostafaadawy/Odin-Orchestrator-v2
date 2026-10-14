#!/bin/bash
# llm_trial.sh <rootname> <port> <pgport> <N> <rep> <model> <cap>
ISO=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Isolated; cd $ISO
export PATH="$ISO/_isolation/shims:/opt/homebrew/bin:/usr/bin:/bin" PGHOST=$ISO/_research/tmp/pg/sock PGPORT=$3 ANCHOR_PG_DSN="dbname=odin_anchor_iso"
export CLAUDE_CALL_LOG="$ISO/_research/results/claude_calls_$1.jsonl"
.venv/bin/python _research/exp/llm_exp.py "$ISO/_research/tmp/$1" $2 $4 $5 $6 $7 >> _research/results/llm_$1.log 2>&1
echo "DONE N=$4 rep=$5" >> _research/results/llm_$1.log
