#!/usr/bin/env bash
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/local/sbin:$HOME/.local/bin:$HOME/development/flutter/bin:$PATH"

for V in "${ODIN_VENV:-}" ".venv" "venv" "../.venv" "$HOME/.venvs/odin"; do
  if [ -n "$V" ] && [ -f "$V/bin/activate" ]; then source "$V/bin/activate"; break; fi
done
if [ -z "${VIRTUAL_ENV:-}" ]; then python3 -m venv .venv && source .venv/bin/activate; fi
PYBIN="$(command -v python || command -v python3)"

"$PYBIN" -m pip install -q --upgrade pip >/dev/null 2>&1 || true
"$PYBIN" -m pip install -q -r server/requirements.txt >/dev/null 2>&1 || true
# voice-note transcription (speech -> text). Best-effort; first transcription downloads the model.
"$PYBIN" -m pip install -q faster-whisper >/dev/null 2>&1 || true

( cd server && "$PYBIN" gen_test_keys.py ) || true

BRAIN_PORT="${BRAIN_PORT:-18000}"
ANCHOR_PORT="${ANCHOR_PORT:-19100}"
WEB_PORT="${WEB_PORT:-18080}"
ANCHOR_SIM_PORT="${ANCHOR_SIM_PORT:-19104}"    # the CD-flow simulator page (served, not file://)
mkdir -p workspace/logs

# PHASE 2 IS DEVELOPMENT — remove any anchor_prod.js left by a previous Phase 3 run. Its presence defines
# window.ODIN_PROD, which makes the sim default to PRODUCTION. Deleting it guarantees the sim (and anything
# keyed off ODIN_PROD) defaults to the LOCAL dev anchor here. Phase 3 re-creates it when you actually deploy.
rm -f anchor_prod.js 2>/dev/null || true

BRAIN_UP=0
if "$PYBIN" -c "import urllib.request;urllib.request.urlopen('http://localhost:$BRAIN_PORT/health',timeout=2)" >/dev/null 2>&1; then
  BRAIN_UP=1
fi

if command -v lsof >/dev/null 2>&1; then
  for P in "$ANCHOR_PORT" "$WEB_PORT"; do
    KP="$(lsof -ti tcp:"$P" 2>/dev/null || true)"
    [ -n "$KP" ] && kill -9 $KP 2>/dev/null || true
  done
  sleep 1
fi

PIDS=()
STARTED_BRAIN=0
_CLEANED=0
cleanup() {
  [ "$_CLEANED" = "1" ] && return
  _CLEANED=1
  trap - EXIT INT TERM    # don't re-enter
  echo ""
  echo "stopping Odin — terminating processes and freeing ports…"
  # 1) terminate the processes we started (and a moment later, force any stragglers)
  for pid in "${PIDS[@]:-}"; do kill "$pid" 2>/dev/null || true; done
  sleep 1
  for pid in "${PIDS[@]:-}"; do kill -9 "$pid" 2>/dev/null || true; done
  # 2) free EVERY port this app opened, regardless of how the child was spawned (subshell children,
  #    uvicorn workers, the flutter web server, electron/vite). Only free the brain port if WE started
  #    it — if we reused a brain that was already running, we leave it alone.
  if command -v lsof >/dev/null 2>&1; then
    # EVERY port this run opens — incl. 5173 (desktop Vite) and the debug/devtools ports flutter opens.
    local PORTS=("${ANCHOR_PORT:-19100}" "${WEB_PORT:-18080}" "${WEBHOOK_PORT:-19300}" "${ANCHOR_SIM_PORT:-19104}" 5173)
    [ "$STARTED_BRAIN" = "1" ] && PORTS+=("${BRAIN_PORT:-18000}")
    for P in "${PORTS[@]}"; do
      KP="$(lsof -ti tcp:"$P" 2>/dev/null || true)"
      [ -n "$KP" ] && kill -9 $KP 2>/dev/null || true
    done
  fi
  # 3) kill the DESKTOP (Electron + Vite) and any flutter/dart web-server this run spawned — scoped to THIS
  #    project path so we never touch other Electron/VSCode apps. This is why the desktop used to stay open.
  pkill -f "Odin-Isolated/desktop" 2>/dev/null || true
  pkill -f "$ROOT/desktop" 2>/dev/null || true
  pkill -f "flutter run -d web-server --web-port ${WEB_PORT:-18080}" 2>/dev/null || true
  echo "stopped — all ports freed (brain, anchor, web, sim, webhook, desktop:5173)."
  exit 0   # actually terminate after Ctrl-C (the main loop is an infinite wait; traps were cleared above)
}
trap cleanup EXIT INT TERM

# ASK FIRST — run WITH the anchor, or WITHOUT it (the offline drill)? The web/flutter ALWAYS talk ONLY to
# the anchor; with no anchor they must show "You are offline" and NO data — proof they never touch the
# backend directly. Set USE_ANCHOR=0/1 in the env to skip the prompt.
USE_ANCHOR="${USE_ANCHOR:-}"
if [ -z "$USE_ANCHOR" ] && [ -t 0 ]; then
  printf "\n>>> Run WITH the anchor point? [Y/n]\n>>>   Y = anchor + poller ON  (web/flutter show synced data)\n>>>   n = anchor OFF (offline drill — web/flutter must show OFFLINE; later run: bash shells/anchor_up.sh)\n>>> choice: "
  read -r _ans </dev/tty 2>/dev/null || _ans=""
  case "$_ans" in [nN]*) USE_ANCHOR=0 ;; *) USE_ANCHOR=1 ;; esac
fi
USE_ANCHOR="${USE_ANCHOR:-1}"

if [ "$BRAIN_UP" = "1" ]; then
  echo "brain already running on :$BRAIN_PORT — reusing it (desktop/web/mobile share the same data)"
else
  USE_VOICE="${USE_VOICE:-0}" "$PYBIN" -m uvicorn server.app:app --host 127.0.0.1 --port "$BRAIN_PORT" >workspace/logs/brain.log 2>&1 &
  PIDS+=($!)
  STARTED_BRAIN=1
  for i in $(seq 1 30); do
    "$PYBIN" -c "import urllib.request;urllib.request.urlopen('http://localhost:$BRAIN_PORT/health',timeout=2)" >/dev/null 2>&1 && break
    sleep 1
  done
fi
# ANCHOR + POLLER — only when USE_ANCHOR=1. -u (unbuffered) so their logs show activity live.
if [ "$USE_ANCHOR" = "1" ]; then
  # anchor uses PostgreSQL (robust) — falls back to JSON automatically if Postgres is unreachable.
  # nohup + </dev/null so these SURVIVE the launching session detaching. The poller especially: without
  # nohup it was getting SIGHUP-killed when the terminal/bridge detached, which silently stopped the whole
  # request queue from draining (sim requests stuck "queued", web/mobile messages never reaching the brain).
  ( cd server && ANCHOR_PG_DSN="${ANCHOR_PG_DSN:-dbname=odin_anchor_iso}" nohup "$PYBIN" -u anchor_remote.py --host 0.0.0.0 --port "$ANCHOR_PORT" >"$ROOT/workspace/logs/anchor_remote.log" 2>&1 </dev/null ) &
  PIDS+=($!)
  sleep 2
  # SUPERVISED poller — the supervisor relaunches it within ~5s if it ever dies, so the request queue /
  # sync can NEVER silently stop (the crash the owner kept hitting). One supervisor only.
  pkill -f "poller_supervisor.sh" 2>/dev/null || true
  ( nohup bash "$ROOT/shells/poller_supervisor.sh" "http://localhost:$ANCHOR_PORT" 4 >"$ROOT/workspace/logs/poller_supervisor.log" 2>&1 </dev/null ) &
  PIDS+=($!)
  echo "  ✓ anchor + SUPERVISED poller ON → http://localhost:$ANCHOR_PORT   (web/flutter will show synced data)"
else
  echo "  ✗ anchor OFF (offline drill) → web/flutter MUST show 'You are offline'. Bring it up in another terminal:  bash shells/anchor_up.sh"
fi

WEBHOOK_PORT="${WEBHOOK_PORT:-19300}"
if command -v lsof >/dev/null 2>&1; then
  KP="$(lsof -ti tcp:"$WEBHOOK_PORT" 2>/dev/null || true)"; [ -n "$KP" ] && kill -9 $KP 2>/dev/null || true
fi
( cd server && "$PYBIN" webhook_receiver.py --port "$WEBHOOK_PORT" >"$ROOT/workspace/logs/webhook.log" 2>&1 ) &
PIDS+=($!)

# CD-FLOW SIMULATOR — serve anchor_sim.html on :9104 (two sections: left = seeded data + your request +
# live Command/Data flow; right = webhook response). Static file server over the repo root.
# Seed the sim with the anchor API key + webhook (from workspace/shared/oth/.cred) so the seeded 3rd-party data is complete.
SEED_KEY="$(grep -E 'ANCHOR_API_KEY' workspace/shared/oth/.cred 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"[:space:]')"
# Write the seed INTO the directory the sim server actually serves (workspace/anchor-layer/), next to
# anchor_sim.html — writing it to the repo root 404'd it, leaving the X-API-Key empty so the anchor
# returned no projects. Also keep a repo-root copy for any other loader (the sim server self-heals from
# either location).
mkdir -p workspace/anchor-layer
cat > workspace/anchor-layer/anchor_seed.js <<JS
window.ODIN_SEED = { key: "${SEED_KEY}", webhook: "http://localhost:${WEBHOOK_PORT}" };
JS
cp -f workspace/anchor-layer/anchor_seed.js anchor_seed.js 2>/dev/null || true
if command -v lsof >/dev/null 2>&1; then
  KP="$(lsof -ti tcp:"$ANCHOR_SIM_PORT" 2>/dev/null || true)"; [ -n "$KP" ] && kill -9 $KP 2>/dev/null || true
fi
# Serve the request page via sim_server.py — it also gives the page a DURABLE SQLite log of the requests it
# fires (responses saved to files). So a refresh or a full browser close never loses the requests/statuses.
( cd server && "$PYBIN" -u sim_server.py --host 127.0.0.1 --port "$ANCHOR_SIM_PORT" >"$ROOT/workspace/logs/anchor_sim.log" 2>&1 ) &
PIDS+=($!)
sleep 1
# Open the anchor's REQUEST PAGE (third-party page: project links + prompt + return webhook) ALWAYS — even
# with the anchor OFF, so you can press Send and SEE the "anchor is offline — not received" feedback. When
# the anchor is ON, Send is acknowledged immediately and the result returns later to the webhook panel.
if [ "${OPEN_SIM:-1}" = "1" ] && command -v open >/dev/null 2>&1; then
  open "http://localhost:$ANCHOR_SIM_PORT/anchor_sim.html" >/dev/null 2>&1 || true
fi
# Open the ANCHOR LANDING PAGE in the browser ONLY when the anchor is ON (proof the secure hub is up). With
# no anchor there is no landing page — so we don't open it (matches: "if anchor works, I see its landing").
if [ "$USE_ANCHOR" = "1" ] && command -v open >/dev/null 2>&1; then
  ( for i in $(seq 1 10); do curl -sf -o /dev/null -m 2 "http://localhost:$ANCHOR_PORT/anchor/v1/_status" && break; sleep 1; done
    open "http://localhost:$ANCHOR_PORT/" >/dev/null 2>&1 || true ) &
fi

# CONTROL BRIDGE (loop.sh-style) — lets the agent drive/monitor this run without you: it writes commands
# into workspace/logs/phase_ctl/CMD and reads workspace/logs/phase_ctl/OUT.log. Runs on YOUR Mac (which has the VM access).
BRAIN_PORT="$BRAIN_PORT" ANCHOR_PORT="$ANCHOR_PORT" ANCHOR_SIM_PORT="$ANCHOR_SIM_PORT" WEBHOOK_PORT="$WEBHOOK_PORT" \
  bash phase_ctl.sh >"$ROOT/workspace/logs/phase_ctl.log" 2>&1 &
PIDS+=($!)
echo "  control bridge → agent drives via workspace/logs/phase_ctl/CMD, reads workspace/logs/phase_ctl/OUT.log"

if [ "${OPEN_DESKTOP:-1}" = "1" ] && [ -f desktop/package.json ]; then
  if [ ! -d desktop/node_modules ]; then ( cd desktop && npm install >"$ROOT/workspace/logs/desktop.log" 2>&1 ) || true; fi
  # capture the PID (NOT nohup-detached) so Ctrl-C tears the desktop down with everything else.
  ( cd desktop && npm run dev >>"$ROOT/workspace/logs/desktop.log" 2>&1 ) &
  PIDS+=($!)
  echo "desktop → Electron app launching (workspace/logs/desktop.log)"
fi

echo ""
echo "================ ODIN PHASE 2 ================"
echo "  opening for you:  web app (browser) · request page (browser) · desktop app · mobile (simulator)"
if [ "$USE_ANCHOR" = "1" ]; then
  echo "  anchor: ON  → web + mobile show live synced data; the request page gets an instant ACK, result via webhook"
else
  echo "  anchor: OFF → web + mobile show 'You are offline'; the request page's Send says 'anchor offline — not received'"
  echo "  bring the anchor online later:  bash shells/anchor_up.sh   (then refresh the web/mobile)"
fi
echo "  the WEB is a SEPARATE app — it opens whether or not the anchor is on (it just shows offline)."
echo "  note: localhost:18000 is the desktop's own backend — internal, never opened as a page."
echo "  app login: tech@odinmarkets.com / 12345678"
echo "  logs: ./workspace/logs/"
echo "=============================================="
echo ""

if ! command -v flutter >/dev/null 2>&1; then
  if command -v brew >/dev/null 2>&1; then brew install --cask flutter || true; fi
fi
if ! command -v flutter >/dev/null 2>&1; then
  echo "flutter not found — backends are up; install Flutter then: cd odin_app && flutter run -d chrome"
  wait
fi

cd odin_app
# Scaffold the platform folders ONCE, guarded — so later runs never clobber lib/ (that previously
# wiped in-progress UI changes via `git checkout -- odin_app/lib`). Safe to call every time: a no-op
# once platforms exist. We back up/restore lib/main.dart only when create actually runs.
if [ ! -d web ] || [ ! -d android ] || [ ! -d ios ]; then
  cp lib/main.dart /tmp/odin_main.dart.bak 2>/dev/null || true
  flutter create . --platforms web,android,ios --project-name odin_app --org com.odin >/dev/null 2>&1 || true
  cp /tmp/odin_main.dart.bak lib/main.dart 2>/dev/null || true
fi
flutter pub get   # idempotent; resolves deps for the new code

# PROFESSIONAL APP ICON + NAME — stamp the Odin Ω launcher icon onto iOS/Android/web so the app on the
# simulator/phone looks like a real product (not the default Flutter icon). Best-effort + idempotent.
if [ -f assets/icon/odin_icon.png ]; then
  dart run flutter_launcher_icons >/dev/null 2>&1 && echo "  ✓ launcher icons stamped (Odin)" || echo "  (icon step skipped — will retry next run)"
fi

echo ""
echo "================ COMPILE CHECK (flutter analyze) ================"
flutter analyze > "$ROOT/workspace/logs/analyze.log" 2>&1 || true
ERRORS="$(grep -cE 'error •|^error|Error:' "$ROOT/workspace/logs/analyze.log" 2>/dev/null | head -1 | tr -cd '0-9')"
ERRORS="${ERRORS:-0}"
if [ "$ERRORS" -gt 0 ] 2>/dev/null; then
  echo "  ❌ $ERRORS compile error(s) — the app will keep the OLD build until these are fixed."
  echo "  ↓ paste these to me:"
  grep -E 'error •|^error|Error:' "$ROOT/workspace/logs/analyze.log" | head -40
  echo "  (full report: workspace/logs/analyze.log)"
else
  echo "  ✅ No compile errors — the new UI will build."
fi
echo "================================================================"
echo ""

flutter config --no-enable-swift-package-manager >/dev/null 2>&1 || true
# PHASE 2 MIMICS PHASE 3 — BUILD the web (release) and SERVE it statically, exactly like Phase 3. The debug
# `flutter run -d web-server` build hangs on the loading splash in a plain browser (it needs the Dart debug
# service); a RELEASE build boots reliably anywhere. ODIN_FORCE_ENV=phase2 bakes in ANCHOR mode against the
# local anchor (apiBase empty → the app can ONLY reach data through the anchor). Phase 3 = same, URL flips.
echo "  building the web app (release)… first build ~1-2 min"
# ABSOLUTE path — by this point the script is already inside odin_app, so a relative `cd odin_app` fails
# ("No such file or directory") and the build never runs. That was the real reason the web didn't work.
if ( cd "$ROOT/odin_app" && flutter build web --release --dart-define=ODIN_FORCE_ENV=phase2 >"$ROOT/workspace/logs/web_build.log" 2>&1 ); then
  echo "  ✓ web app built"
else
  echo "  ⚠️ web build FAILED — last lines of workspace/logs/web_build.log:"; tail -15 "$ROOT/workspace/logs/web_build.log" 2>/dev/null
fi
# no-cache static server so a rebuild is always picked up (kills stale service-worker caching)
cat > "$ROOT/workspace/logs/_web_serve.py" <<'PY'
import sys, os, http.server, socketserver
port = int(sys.argv[1]); os.chdir(sys.argv[2])
class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache'); self.send_header('Expires', '0')
        super().end_headers()
    def log_message(self, *a): pass
socketserver.ThreadingTCPServer.allow_reuse_address = True
socketserver.ThreadingTCPServer(('0.0.0.0', port), H).serve_forever()
PY
if [ -f "$ROOT/odin_app/build/web/index.html" ]; then
  ( "$PYBIN" "$ROOT/workspace/logs/_web_serve.py" "$WEB_PORT" "$ROOT/odin_app/build/web" >"$ROOT/workspace/logs/app_web.log" 2>&1 ) &
  PIDS+=($!)
  # AUTO-OPEN the web app in the browser as soon as the server actually returns the page (200). No port
  # printed — it just opens. The web is served regardless of the anchor choice (it is a SEPARATE app).
  ( for i in $(seq 1 25); do
      curl -sf -o /dev/null -m 2 "http://localhost:$WEB_PORT/index.html" 2>/dev/null && break; sleep 1; done
    sleep 1
    if command -v open >/dev/null 2>&1; then open "http://localhost:$WEB_PORT" >/dev/null 2>&1 || true; fi ) &
  echo "  ✓ opening the web app in your browser…"
else
  echo "  ⚠️ web build not found — see workspace/logs/web_build.log"
fi

UDID=""
if command -v xcrun >/dev/null 2>&1; then
  open -a Simulator >/dev/null 2>&1 || true
  # (a) reuse a device that's ALREADY booted, if any
  for i in $(seq 1 8); do
    UDID="$(xcrun simctl list devices booted 2>/dev/null | grep -Eo '[0-9A-Fa-f-]{36}' | head -1)"
    [ -n "$UDID" ] && break
    sleep 2
  done
  # (b) none booted → explicitly BOOT the first available iPhone, then open the Simulator on it
  if [ -z "$UDID" ]; then
    DEV="$(xcrun simctl list devices available 2>/dev/null | grep -E 'iPhone' | grep -Eo '[0-9A-Fa-f-]{36}' | head -1)"
    if [ -n "$DEV" ]; then
      echo "no device booted — booting iOS simulator $DEV …"
      xcrun simctl boot "$DEV" >/dev/null 2>&1 || true
      open -a Simulator >/dev/null 2>&1 || true
      for i in $(seq 1 20); do
        UDID="$(xcrun simctl list devices booted 2>/dev/null | grep -Eo '[0-9A-Fa-f-]{36}' | head -1)"
        [ -n "$UDID" ] && break
        sleep 2
      done
    fi
  fi
fi

if [ -n "$UDID" ]; then
  echo "  ✓ building + launching the mobile app on the iOS simulator (anchor mode)…"
  # ROBUST LAUNCH: `flutter run` does an INCREMENTAL build that can fast-fail with Xcode error 74 (stale
  # build state) — that left the phone without the app. Instead do a CLEAN simulator build, then install +
  # launch via simctl. Deterministic; the app always lands. Backgrounded so quitting the phone never ends
  # this script. (Full build log: workspace/logs/app_ios.log.)
  ( cd "$ROOT/odin_app" && flutter build ios --simulator --debug --dart-define=ODIN_FORCE_ENV=phase2 >"$ROOT/workspace/logs/app_ios.log" 2>&1
    APP="$ROOT/odin_app/build/ios/iphonesimulator/Runner.app"
    if [ -d "$APP" ]; then
      BID="$(/usr/libexec/PlistBuddy -c 'Print CFBundleIdentifier' "$APP/Info.plist" 2>/dev/null || echo com.mostafaadawy.mobileapp)"
      xcrun simctl install "$UDID" "$APP" >>"$ROOT/workspace/logs/app_ios.log" 2>&1 && \
      xcrun simctl launch "$UDID" "$BID" >>"$ROOT/workspace/logs/app_ios.log" 2>&1 && \
      echo "  ✓ mobile app installed + launched on the simulator ($BID)" || \
      echo "  ⚠️ install/launch issue — see workspace/logs/app_ios.log"
    else
      echo "  ⚠️ mobile iOS build failed — see workspace/logs/app_ios.log"
    fi ) &
  PIDS+=($!)
else
  echo "  (no iOS simulator available — the web app is still running)"
fi

echo ""
echo "  Everything is up. Quit the phone or close the browser tab freely — the session stays alive."
echo "  ▶ Press Ctrl-C HERE (in this terminal) to stop everything and free all ports."
# Keep the session alive until YOU press Ctrl-C. The apps run as background jobs; if you quit the phone or
# the web tab, the rest keep running. Only Ctrl-C (the INT trap) runs cleanup and frees every port.
while true; do sleep 2; done
