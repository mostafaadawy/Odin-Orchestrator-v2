#!/usr/bin/env bash
# Odin-Orchestrator smoke test — pings every endpoint and reports PASS/FAIL.
# Usage:
#   bash scripts/smoke_test.sh                  # tests http://localhost:18000
#   BASE=http://localhost:18000 TOKEN=xyz bash scripts/smoke_test.sh
set -uo pipefail

BASE="${BASE:-http://localhost:18000}"
TOKEN="${TOKEN:-}"
HDR=(); [ -n "$TOKEN" ] && HDR=(-H "X-Odin-Token: $TOKEN")
pass=0; fail=0
chk(){ # chk "name" expected_code actual_code
  if [ "$2" = "$3" ]; then echo "  ✅ $1 ($3)"; pass=$((pass+1));
  else echo "  ❌ $1 (got $3, want $2)"; fail=$((fail+1)); fi; }

echo "Testing $BASE  (token: $([ -n "$TOKEN" ] && echo set || echo none))"
echo

echo "1) Health & dashboard"
chk "/health is up" 200 "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health")"
chk "/ dashboard serves" 200 "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/")"
chk "/mobile.html serves" 200 "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/mobile.html")"
chk "/state/project.json serves" 200 "$(curl -s -o /dev/null -w '%{http_code}' "$BASE/state/project.json")"

echo "2) Brain / dispatcher (chat)"
code=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/chat" "${HDR[@]}" -H 'Content-Type: application/json' -d '{"text":"explain the approval gate","lang":"en"}')
chk "/chat answers (200)" 200 "$code"
echo "     reply: $(curl -s -X POST "$BASE/chat" "${HDR[@]}" -H 'Content-Type: application/json' -d '{"text":"explain the approval gate","lang":"en"}')"

echo "3) Approval gate is enforced (gated request must NOT execute)"
g=$(curl -s -X POST "$BASE/dispatch" "${HDR[@]}" -H 'Content-Type: application/json' -d '{"text":"deploy the backend to the azure vm","lang":"en"}')
echo "     dispatch: $g"
echo "$g" | grep -q '"required": *true' && { echo "  ✅ gated request flagged for approval"; pass=$((pass+1)); } || { echo "  ❌ gated request NOT flagged"; fail=$((fail+1)); }

echo "4) Voice endpoints (need USE_VOICE=1 + voice deps installed)"
sc=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/voice/stt" "${HDR[@]}")
echo "     /voice/stt (no file) → $sc  (422 = route OK; 503 = USE_VOICE off; 401 = token needed)"
tc=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/voice/tts?text=hello&lang=en" "${HDR[@]}")
echo "     /voice/tts en → $tc  (200 = Kokoro working; 503 = USE_VOICE off; 500 = deps missing)"

echo
echo "RESULT: $pass passed, $fail failed"
[ "$fail" -eq 0 ] && echo "✅ Core smoke test passed." || echo "⚠️  Some checks failed — see notes above."
