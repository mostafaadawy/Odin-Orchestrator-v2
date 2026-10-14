#!/usr/bin/env bash
# phone_install.sh — install the PRODUCTION Odin app on the REAL iPhone and LAUNCH it.
# Success is reported ONLY when the app was installed AND launched on the phone (the old,
# proven `flutter run --release` method; --no-resident makes it exit after launch).
# Usage: shells/phone_install.sh            (waits up to 15 min for the iPhone)
#        ODIN_PHONE_WAIT_MIN=2 shells/phone_install.sh
set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; cd "$ROOT"
LOG="$ROOT/workspace/logs/app_ios_install.log"; ST="$ROOT/workspace/logs/phone_status.txt"
mkdir -p workspace/logs
PROXY_HOST="${ODIN_SERVER_NAME:-anchor.odinmarkets.com}"
ANCHOR_BASE="${ANCHOR_BASE:-https://${PROXY_HOST}/odin-anchor}"
DART_DEFS="${DART_DEFS:---dart-define=ODIN_FORCE_ENV=production --dart-define=ODIN_ANCHOR=${ANCHOR_BASE}}"
find_phone() { (cd odin_app && flutter devices --machine 2>/dev/null) | python3 -c "import sys,json
try:
 d=json.load(sys.stdin); print(next((x['id'] for x in d if str(x.get('targetPlatform','')).startswith('ios') and not x.get('emulator',False)),''))
except Exception: print('')" 2>/dev/null; }
WAIT=$(( ${ODIN_PHONE_WAIT_MIN:-15} * 12 )); PHYS=""
echo "waiting for your iPhone — connect it by USB, UNLOCK it and tap Trust" > "$ST"
for i in $(seq 1 "$WAIT"); do PHYS="$(find_phone)"; [ -n "$PHYS" ] && break; sleep 5; done
if [ -z "$PHYS" ]; then
  echo "no iPhone connected — connect + unlock + trust it, then run shells/phone_install.sh" > "$ST"
  echo "  📱 PHONE: no iPhone found — connect, unlock, Trust, then run: bash shells/phone_install.sh"; exit 2; fi
echo "installing + launching on the iPhone ($PHYS)… keep it UNLOCKED and connected" > "$ST"
echo "  📱 PHONE: iPhone $PHYS found — installing + launching the production app (keep it unlocked)…"
# hard cap 10 min so a stuck transfer can never be reported as success
( cd odin_app && perl -e 'alarm 600; exec @ARGV' flutter run --release --no-resident -d "$PHYS" $DART_DEFS ) >"$LOG" 2>&1
RC=$?
if [ $RC -eq 0 ] && ! grep -qi 'error\|failed\|could not' "$LOG"; then
  echo "✓ installed AND launched on your iPhone ($PHYS)" > "$ST"
  echo "  📱 PHONE: ✓ installed and launched on your iPhone — Odin is open on the phone."; exit 0
fi
echo "❌ install/launch failed (rc=$RC) — workspace/logs/app_ios_install.log" > "$ST"
echo "  📱 PHONE: ❌ install/launch failed (rc=$RC) — last lines:"; tail -8 "$LOG" | sed 's/^/     /'; exit 1
