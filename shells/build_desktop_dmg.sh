#!/usr/bin/env bash
# v2 DESKTOP BUILD — produces the Odin v2 DMG and proves it installs and starts from a CLEAN path.
#   bash shells/build_desktop_dmg.sh            build + clean-path install test
#   SKIP_TEST=1 bash shells/build_desktop_dmg.sh  build only
# The test never touches /Applications, your real app data, or your real database: the app is copied to a temp
# folder, started with a temp user-data dir, a spare port, the ISOLATED v2 clone as its backend (if present) and an
# unreachable anchor; then it is quit and every port it opened is checked free.
set -uo pipefail
cd "$(dirname "$0")/.."; ROOT="$(pwd)"
export PATH="/opt/homebrew/bin:/usr/local/bin:$HOME/.nvm/versions/node/v20.20.2/bin:$PATH"
LOG="$ROOT/workspace/logs/desktop_dist.log"; mkdir -p "$ROOT/workspace/logs"
echo "==== Odin v2 desktop build ===="
cd desktop
[ -d node_modules ] || npm install >"$LOG" 2>&1
rm -rf release
if ! npm run dist >>"$LOG" 2>&1; then echo "❌ build failed — tail of $LOG:"; tail -25 "$LOG"; exit 1; fi
DMG="$(ls -t "$ROOT"/desktop/release/*.dmg 2>/dev/null | head -1)"
[ -f "$DMG" ] || { echo "❌ no DMG produced"; exit 1; }
echo "  ✓ DMG: $DMG"
echo "    size: $(du -h "$DMG" | cut -f1)   sha256: $(shasum -a 256 "$DMG" | cut -d' ' -f1)"
# the bundle must carry NO owner secret (F-14) and must not point at v1
APPDIR="$(ls -d "$ROOT"/desktop/release/mac*/Odin.app 2>/dev/null | head -1)"
if [ -n "$APPDIR" ]; then
  HITS="$(grep -rlE 'od_anchor_[A-Za-z0-9_-]{20,}' "$APPDIR/Contents/Resources" 2>/dev/null | wc -l | tr -d ' ')"
  V1="$(grep -rl 'AiAgentWorkSpace/Odin-Orchestrator"' "$APPDIR/Contents/Resources" 2>/dev/null | wc -l | tr -d ' ')"
  [ "$HITS" = "0" ] && echo "  ✓ no anchor-key literal in the bundle" || echo "  ❌ $HITS bundle file(s) carry an anchor-key literal"
  [ "$V1" = "0" ] && echo "  ✓ no v1 path in the bundle" || echo "  ❌ $V1 bundle file(s) point at the v1 folder"
fi
[ "${SKIP_TEST:-0}" = "1" ] && exit 0

echo "---- clean-path install test ----"
T="$(mktemp -d /tmp/odin_dmg_test.XXXX)"; MNT="$T/mnt"; mkdir -p "$MNT" "$T/ud"
hdiutil attach -nobrowse -readonly -mountpoint "$MNT" "$DMG" >/dev/null || { echo "❌ DMG does not mount"; exit 1; }
cp -R "$MNT/Odin.app" "$T/" ; hdiutil detach "$MNT" >/dev/null 2>&1
echo "  ✓ DMG mounts; app copied to a clean temp path"
echo "    bundle id: $(/usr/libexec/PlistBuddy -c 'Print CFBundleIdentifier' "$T/Odin.app/Contents/Info.plist")  version: $(/usr/libexec/PlistBuddy -c 'Print CFBundleShortVersionString' "$T/Odin.app/Contents/Info.plist")"
BK="${TEST_ROOT:-$ROOT/_v2/iso_root}"; [ -f "$BK/server/run.sh" ] || BK="$ROOT"
PORT=48517
ODIN_ROOT="$BK" ODIN_PORT=$PORT ODIN_ANCHOR="http://127.0.0.1:9" USE_VOICE=0 \
  "$T/Odin.app/Contents/MacOS/Odin" --user-data-dir="$T/ud" >"$T/app.log" 2>&1 &
APP=$!
OK=0
for i in $(seq 1 60); do
  H="$(curl -s -m 2 http://127.0.0.1:$PORT/health 2>/dev/null)"
  if echo "$H" | grep -q '"ok"'; then OK=1; break; fi; sleep 1
done
if [ $OK = 1 ]; then echo "  ✓ packaged app started its backend from a clean path: $(echo "$H" | python3 -c 'import sys,json;d=json.load(sys.stdin);print("root_name=%s version=%s decider=%s" % (d.get("root_name"),d.get("odin_version"),d.get("decider_mode")))')"
else echo "  ❌ backend did not answer on :$PORT within 60s — see $T/app.log"; fi
kill $APP 2>/dev/null; sleep 3; pkill -f "$T/Odin.app" 2>/dev/null; sleep 1
if lsof -ti tcp:$PORT >/dev/null 2>&1; then echo "  ❌ port $PORT still held after quit"; lsof -ti tcp:$PORT | xargs kill -9 2>/dev/null; else echo "  ✓ app quit cleanly — port $PORT freed"; fi
[ -f "$T/ud/root.txt" ] && echo "  note: root.txt written in the TEMP user-data dir only" || true
echo "  test folder: $T  (safe to delete)"
[ $OK = 1 ] && echo "RESULT: DMG OK" || { echo "RESULT: DMG TEST FAILED"; exit 1; }
