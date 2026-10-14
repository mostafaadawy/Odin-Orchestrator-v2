#!/bin/bash
# Sequential LLM consistency series. Fresh throwaway root + fresh private DB per trial. Budget guard: stop when spend >= $LIMIT.
ISO=/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Isolated; cd $ISO; LIMIT=${LIMIT:-13}; REP=${REP:-0}; MODEL=${MODEL:-haiku}
spent(){ cat _research/results/claude_calls*.jsonl 2>/dev/null | /usr/bin/python3 -c "import sys,json;print(sum((json.loads(l).get('cost_usd') or 0) for l in sys.stdin if l.strip()))"; }
for N in ${NS:-1 2 5 10}; do
  S=$(spent); if /usr/bin/python3 -c "import sys;sys.exit(0 if $S < $LIMIT else 1)"; then :; else echo "BUDGET STOP at $S before N=$N rep=$REP" >> _research/results/llm_series.log; break; fi
  name="llm_r${REP}_n$N"; port=$((18110+N)); 
  _research/exp/llm_root_up.sh $name $port 15434 >> _research/results/llm_series.log 2>&1
  _research/exp/llm_trial.sh $name $port 15434 $N $REP $MODEL $((600+120*N))
  kill $(cat _research/tmp/$name/server.pid) 2>/dev/null
  echo "$(date -u +%T) done N=$N rep=$REP spent=$(spent)" >> _research/results/llm_series.log
done
echo SERIES_DONE >> _research/results/llm_series.log
