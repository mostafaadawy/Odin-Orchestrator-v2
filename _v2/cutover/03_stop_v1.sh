#!/bin/bash
# CUTOVER STEP 2 — stop v1 everywhere (so no scheduled agent runs twice) and bring over records v1 wrote after the copy.
# v1's files are only READ. Stops on the first failure.
set -uo pipefail
V1=$HOME/Desktop/AiAgentWorkSpace/Odin-Orchestrator; V2=$HOME/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2
fail(){ echo "❌ STEP 2 FAILED: $*"; exit 1; }
osascript -e 'tell application "Odin" to quit' >/dev/null 2>&1; sleep 3
# v1 processes = anything running from the v1 folder (never the -v2 one)
for pid in $(pgrep -f "AiAgentWorkSpace/Odin-Orchestrator/" ) $(pgrep -f "/Applications/Odin.app"); do kill "$pid" 2>/dev/null; done
for p in 8000 9100 9104 9300 8080; do for pid in $(lsof -ti tcp:$p -sTCP:LISTEN 2>/dev/null); do
  c=$(lsof -a -p $pid -d cwd -Fn 2>/dev/null | sed -n 's/^n//p'); case "$c" in *Odin-Orchestrator-v2*) ;; *) kill $pid 2>/dev/null;; esac; done; done
sleep 2
left=$(pgrep -fl "AiAgentWorkSpace/Odin-Orchestrator/|/Applications/Odin.app" | wc -l | tr -d ' ')
[ "$left" = 0 ] || fail "$left v1 process(es) still running"
echo "  ✓ v1 stopped (app, brain, anchor, poller): 0 processes"
# records written by v1 after v2 was created (tag v2-start time)
T0=$(git -C "$V2" --no-optional-locks log -1 --format=%ct v2-start)
cd "$V1" && find workspace data -type f -newermt "@$T0" ! -path '*/__pycache__/*' 2>/dev/null > /tmp/v1_newer.txt
n=$(wc -l < /tmp/v1_newer.txt | tr -d ' '); echo "  v1 files newer than the v2 copy: $n"
if [ "$n" != 0 ]; then
  while read f; do
    if [ -e "$V2/$f" ] && [ "$V2/$f" -nt "$V1/$f" ]; then echo "   CONFLICT (changed in both, v2 kept, v1 copy saved as .from_v1): $f"; cp -p "$V1/$f" "$V2/$f.from_v1"
    else mkdir -p "$(dirname "$V2/$f")"; cp -p "$V1/$f" "$V2/$f" || fail "copy $f"; fi
  done < /tmp/v1_newer.txt
  echo "  ✓ records copied v1 → v2"
fi
echo "STEP 2 OK"
