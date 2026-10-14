#!/usr/bin/env bash
# Phase-3 mobile: wait for a REAL iPhone (retry until connected) then install the PRODUCTION app.
# No simulator fallback. Production profile = online anchor.
cd /Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Isolated
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/local/sbin:$HOME/.local/bin:$HOME/development/flutter/bin:$PATH"
ANCHOR_BASE="https://anchor.odinmarkets.com/odin-anchor"
DART_DEFS="--dart-define=ODIN_FORCE_ENV=production --dart-define=ODIN_ANCHOR=${ANCHOR_BASE}"
LOG="logs/app_ios.log"; : > "$LOG"

detect() {
  cd odin_app && flutter devices --machine 2>/dev/null | python3 -c "import sys,json
try:
 d=json.load(sys.stdin); print(next((x['id'] for x in d if str(x.get('targetPlatform','')).startswith('ios') and not x.get('emulator',False)),''))
except Exception: print('')" 2>/dev/null; cd ..
}

echo "[$(date '+%H:%M:%S')] Waiting for a REAL iPhone — connect it via USB and tap 'Trust'. Retrying every 5s…" | tee -a "$LOG"
PHYS=""
for i in $(seq 1 180); do          # up to ~15 min of retrying
  PHYS="$(detect)"
  if [ -n "$PHYS" ]; then echo "[$(date '+%H:%M:%S')] iPhone connected: $PHYS" | tee -a "$LOG"; break; fi
  sleep 5
done
if [ -z "$PHYS" ]; then
  echo "RESULT=NO_PHONE — no iPhone detected after waiting. Connect + trust it, then I'll retry." | tee -a "$LOG"
  exit 2
fi
echo "[$(date '+%H:%M:%S')] Installing the PRODUCTION app to $PHYS (needs a signing team set in Xcode for odin_app/ios)…" | tee -a "$LOG"
cd odin_app
# --release build, install to the device, run. Detach after it reports installed/launched or errors.
flutter run --release -d "$PHYS" $DART_DEFS >>"../$LOG" 2>&1 &
RUN_PID=$!
# watch the log for a terminal signal (installed / launched / signing error)
for i in $(seq 1 180); do
  if grep -qiE "Installing and launching|Syncing files to device|flutter run key commands|Application launched|is available at" "../$LOG"; then
    echo "RESULT=INSTALLED — production app is on the phone." | tee -a "../$LOG"; break
  fi
  if grep -qiE "requires a development team|code sign|No profiles|Provisioning|Xcode build done.*error|Error launching application|Could not build" "../$LOG"; then
    echo "RESULT=SIGNING_OR_BUILD_ERROR — see the lines above (usually: set a Development Team in Xcode ▸ Runner ▸ Signing)." | tee -a "../$LOG"; break
  fi
  sleep 5
done
echo "[$(date '+%H:%M:%S')] (flutter run pid=$RUN_PID stays attached; the app is on the phone if RESULT=INSTALLED)"
