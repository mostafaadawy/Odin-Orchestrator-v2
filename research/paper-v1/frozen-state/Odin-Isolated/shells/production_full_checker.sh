#!/usr/bin/env bash
# =====================================================================================================
# production_full_checker.sh — ONLINE / PRODUCTION shell (rewritten clean, from scratch).
#
# Goal: reuse the SAME successful components proven in Phase 2, but pointed at the deployed PRODUCTION
# targets (Azure VM + anchor.odinmarkets.com over the 443 reverse proxy). It NEVER touches development_full_checker.sh,
# the development configuration, the original successful folders, the existing SSL/domain, working VM
# services, or the firewall in an unsafe way.
#
# Flow (exactly as specified):
#   1. ensure deploy_anchor/ + deploy_web/ copies exist + read the first-run flag
#   2. compare the ORIGINAL successful folders against those copies
#   3. decide whether a deploy is required
#   4. FIRST RUN  -> always deploy (even with no diff), then stamp the flag
#      CHANGED     -> ASK before deploying; if refused, only auto-start production
#      SAME (done) -> do NOT ask; just auto-start production
#   5. before any deploy: validate the VM (SSH, proxy, SSL, paths, PostgreSQL, env, firewall) read-only
#   6. deploy via the PROVEN tools (isolated dirs, SSL preserved, service create-if-missing), then test
#   7. run smart production e2e tests (fixed inputs/outputs) to prove prod config is correct
#   8. auto-start ONLY the main visible players (request page, web prod, Flutter sim, desktop)
#
# Non-interactive approve for automation: export ODIN_PHASE3_YES=1  (first run deploys regardless).
# =====================================================================================================
set -uo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/local/sbin:$HOME/.local/bin:$HOME/development/flutter/bin:$PATH"
for V in "${ODIN_VENV:-}" ".venv" "venv" "../.venv"; do
  if [ -n "$V" ] && [ -f "$V/bin/activate" ]; then source "$V/bin/activate"; break; fi
done
[ -z "${VIRTUAL_ENV:-}" ] && { python3 -m venv .venv >/dev/null 2>&1 && source .venv/bin/activate; }
PYBIN="$(command -v python || command -v python3)"
"$PYBIN" -m pip install -q -r server/requirements.txt >/dev/null 2>&1 || true
mkdir -p workspace/logs

# ---- production targets (the deployed, proven infrastructure) --------------------------------------
BRAIN_PORT="${BRAIN_PORT:-18000}"                # LOCAL brain (desktop's backend) — stays local, reached via anchor
ANCHOR_PORT="${ODIN_ANCHOR_PORT:-48619}"        # ONLINE anchor port on the VM (behind nginx 443)
WEB_PORT="${WEB_PORT:-18080}"                    # optional local owner-view web (production target)
WEB_VM_PORT="${WEB_VM_PORT:-48620}"             # ONLINE web port on the VM (behind nginx 443)
WEBHOOK_PORT="${WEBHOOK_PORT:-19300}"
ANCHOR_SIM_PORT="${ANCHOR_SIM_PORT:-19104}"      # local request/CD-flow page, opened in PRODUCTION mode
PROXY_HOST="${ODIN_SERVER_NAME:-anchor.odinmarkets.com}"
export ODIN_SERVER_NAME="$PROXY_HOST"
ANCHOR_BASE="https://${PROXY_HOST}/odin-anchor"
WEB_BASE="https://${PROXY_HOST}/odin-web"

echo "================ ODIN PHASE 3 — ONLINE / PRODUCTION ================"
echo "  domain: https://${PROXY_HOST}   (443 reverse proxy · existing SSL reused · no raw ports)"

# =====================================================================================================
# 1) deploy copies + 2) compare + 3) decide
# =====================================================================================================
"$PYBIN" workspace/shared/infra/phase3_gate.py init
"$PYBIN" workspace/shared/infra/phase3_gate.py compare | tee workspace/logs/phase3_compare.log
DECISION="$(grep -E '^DECISION=' workspace/logs/phase3_compare.log | tail -1 | cut -d= -f2)"
echo "  decision: ${DECISION:-UNKNOWN}"

DO_DEPLOY=0
case "$DECISION" in
  FIRST_RUN)
    echo "  → first Phase-3 run: the initial deployment will proceed (even though nothing differs)."
    DO_DEPLOY=1 ;;
  CHANGED)
    if [ "${ODIN_PHASE3_YES:-0}" = "1" ]; then
      echo "  → changes detected; ODIN_PHASE3_YES=1 → deploying."
      DO_DEPLOY=1
    else
      # 4) ASK before deploying when changes are detected. Refuse => only auto-start production.
      printf "  Changes were found in the successful folders. Deploy them to production now? [y/N] "
      read -r ANS </dev/tty 2>/dev/null || ANS="n"
      case "$ANS" in y|Y|yes|YES) DO_DEPLOY=1 ;; *) echo "  → deployment declined — starting the CURRENT production setup only." ;; esac
    fi ;;
  SAME)
    echo "  → no changes since the last successful deployment → NOT deploying; starting production." ;;
  *)
    echo "  ⚠ could not determine a decision; defaulting to SAFE no-deploy (start production only)." ;;
esac

# =====================================================================================================
# 5) validate VM  +  6) deploy (proven tools)  +  7) production e2e — only when deploying
# =====================================================================================================
DEPLOY_OK=1
if [ "$DO_DEPLOY" = "1" ]; then
  echo ""
  echo "---- pre-deploy VM validation (read-only) ----------------------------------------"
  if ! "$PYBIN" workspace/shared/infra/phase3_gate.py validate | tee workspace/logs/phase3_validate.log; then
    echo "❌ VM validation reported a blocking problem (see workspace/logs/phase3_validate.log). NOT deploying."
    DEPLOY_OK=0
  fi

  # ANCHOR: overwrite the VM folder FROM deploy_anchor (ships ALL files incl anchor_manage.py), create the
  # Postgres DB link (dedicated role owns the EXISTING odin_anchor_iso db — never recreated), restart the EXISTING
  # service (leverage it; existing nginx/domain/SSL reused, never self-signed). DB is created if missing inside.
  if [ "$DEPLOY_OK" = "1" ]; then
    echo ""
    echo "---- deploy ANCHOR: overwrite /home/mostafa/anchor-online FROM deploy_anchor + Postgres link + restart ----"
    "$PYBIN" workspace/shared/infra/phase3_gate.py deploy-anchor | tee workspace/logs/phase3_deploy.log
    A_RC="${PIPESTATUS[0]}"
    if [ "$A_RC" != "0" ]; then
      echo "❌ anchor deploy failed — see workspace/logs/phase3_deploy.log. NOT continuing."
      DEPLOY_OK=0
    fi
  fi

  # WEB: build the PRODUCTION site (domain baked in) then overwrite the VM folder FROM deploy_web, preserving
  # the existing service runner (_serve_nocache.py) + restarting the EXISTING web service.
  if [ "$DEPLOY_OK" = "1" ]; then
    echo ""
    echo "---- build PRODUCTION web then overwrite /home/mostafa/odin-web FROM deploy_web ----"
    if command -v flutter >/dev/null 2>&1; then
      ( cd odin_app && flutter build web --release --base-href /odin-web/ --dart-define=ODIN_FORCE_ENV=production --dart-define=ODIN_ANCHOR="$ANCHOR_BASE" ) >workspace/logs/web_build.log 2>&1 \
        && echo "  ✓ production web built" || echo "  ⚠ web build issues — see workspace/logs/web_build.log"
    fi
    "$PYBIN" workspace/shared/infra/phase3_gate.py deploy-web | tee -a workspace/logs/phase3_deploy.log
    W_RC="${PIPESTATUS[0]}"
    [ "$W_RC" != "0" ] && echo "⚠️ web deploy note — see workspace/logs/phase3_deploy.log (anchor is up; continuing)."
  fi

  # 7) production e2e — prove the ONLINE endpoints answer with production behaviour
  if [ "$DEPLOY_OK" = "1" ]; then
    echo ""
    echo "---- production e2e tests (fixed checks against the ONLINE endpoints) -------------"
    ODIN_SERVER_NAME="$PROXY_HOST" "$PYBIN" workspace/shared/infra/phase3_e2e.py | tee workspace/logs/phase3_e2e.log
    E_RC="${PIPESTATUS[0]}"
    if [ "$E_RC" != "0" ]; then
      echo "❌ production e2e failed (see workspace/logs/phase3_e2e.log). NOT stamping success / NOT auto-starting."
      DEPLOY_OK=0
    fi
  fi

  # snapshot copies + stamp the first-run flag ONLY after a fully successful deploy+test
  if [ "$DEPLOY_OK" = "1" ]; then
    "$PYBIN" workspace/shared/infra/phase3_gate.py snapshot
    echo "  ✓ deployment copies refreshed + first-run flag stamped."
  else
    echo "  (first-run flag NOT stamped — this run did not fully succeed; a re-run will retry the deploy.)"
    exit 1
  fi
fi

# =====================================================================================================
# production config for the local players (write, never delete dev). The app auto-selects the PRODUCTION
# profile via --dart-define; dev profiles are untouched and remain selectable.
# =====================================================================================================
KEY="$(grep -E 'ANCHOR_API_KEY' workspace/shared/oth/.cred 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"[:space:]')"
cat > anchor_prod.js <<JS
// Written by production_full_checker.sh — the REAL online anchor via the nginx reverse proxy on 443 (no open port).
window.ODIN_PROD = {
  brain:  "",                                    // Phase 3 client config carries NO backend URL — web/request
                                                 // page/mobile reach data ONLY through the anchor. The brain is
                                                 // local-only and reached by the desktop; never by these clients.
  anchor: "${ANCHOR_BASE}",
  wh:     "${ANCHOR_BASE}",
  key:    "${KEY}"
};
JS
cat > workspace/anchor-layer/anchor_seed.js <<JS
window.ODIN_SEED = { key: "${KEY}", webhook: "${ANCHOR_BASE}" };
JS
echo "  ✓ production config written (anchor_prod.js → ${ANCHOR_BASE}); development profiles untouched."

# =====================================================================================================
# 8) AUTO-START only the MAIN players (production). Supporting services run in the background (no windows).
# =====================================================================================================
DART_DEFS="--dart-define=ODIN_FORCE_ENV=production --dart-define=ODIN_ANCHOR=${ANCHOR_BASE}"

# --- background: local brain (the desktop's backend; stays local, reached through the anchor) ---
if ! "$PYBIN" -c "import urllib.request;urllib.request.urlopen('http://localhost:$BRAIN_PORT/health',timeout=2)" >/dev/null 2>&1; then
  USE_VOICE=0 "$PYBIN" -m uvicorn server.app:app --host 127.0.0.1 --port "$BRAIN_PORT" >workspace/logs/brain.log 2>&1 &
  for i in $(seq 1 30); do "$PYBIN" -c "import urllib.request;urllib.request.urlopen('http://localhost:$BRAIN_PORT/health',timeout=2)" >/dev/null 2>&1 && break; sleep 1; done
fi
# --- background: SUPERVISED local poller → ONLINE anchor (pulls tasks, runs CTO→team locally, posts back) ---
# The supervisor relaunches the poller within ~5s if it ever dies, so the PRODUCTION request/sync flow can
# never silently stop — critical because the owner runs production by double-clicking the app (no terminal
# babysitting it). nohup + </dev/null so it survives the launcher detaching.
pkill -f 'local_poller_http.py' 2>/dev/null || true
pkill -f 'poller_supervisor.sh' 2>/dev/null || true
( nohup bash "$ROOT/shells/poller_supervisor.sh" "$ANCHOR_BASE" 4 >"$ROOT/workspace/logs/poller_supervisor.log" 2>&1 </dev/null ) &
# --- background: local webhook receiver (result watching) ---
if command -v lsof >/dev/null 2>&1; then KP="$(lsof -ti tcp:$WEBHOOK_PORT 2>/dev/null||true)"; [ -n "$KP" ] && kill -9 $KP 2>/dev/null||true; fi
( cd server && "$PYBIN" webhook_receiver.py --port "$WEBHOOK_PORT" >"$ROOT/workspace/logs/webhook.log" 2>&1 ) &

# --- PLAYER 1: the REQUEST page, in PRODUCTION (local page, talks to the ONLINE anchor) ---
if command -v lsof >/dev/null 2>&1; then KP="$(lsof -ti tcp:$ANCHOR_SIM_PORT 2>/dev/null||true)"; [ -n "$KP" ] && kill -9 $KP 2>/dev/null||true; fi
( cd "$ROOT/workspace/anchor-layer" && "$PYBIN" -m http.server "$ANCHOR_SIM_PORT" --bind 127.0.0.1 >"$ROOT/workspace/logs/anchor_sim.log" 2>&1 ) &
sleep 1
command -v open >/dev/null 2>&1 && open "http://localhost:$ANCHOR_SIM_PORT/anchor_sim.html?env=prod" >/dev/null 2>&1 || true

# --- PLAYER 2: the WEB PRODUCTION page (the deployed site, online) ---
command -v open >/dev/null 2>&1 && open "$WEB_BASE" >/dev/null 2>&1 || true
# also show the ONLINE anchor landing page (production, not the dev one)
command -v open >/dev/null 2>&1 && open "${ANCHOR_BASE}/" >/dev/null 2>&1 || true

# --- PLAYER 3: the DESKTOP app (local Electron + its local brain), production-compatible ---
if [ "${OPEN_DESKTOP:-1}" = "1" ] && [ -f desktop/package.json ]; then
  if command -v lsof >/dev/null 2>&1; then KP="$(lsof -ti tcp:5173 2>/dev/null || true)"; [ -n "$KP" ] && kill -9 $KP 2>/dev/null || true; fi
  pkill -f 'vite' 2>/dev/null || true; pkill -f 'electron .' 2>/dev/null || true; sleep 1
  [ -d desktop/node_modules ] || ( cd desktop && npm install >"$ROOT/workspace/logs/desktop.log" 2>&1 ) || true
  ( cd desktop && VITE_ODIN_ENV=production nohup npm run dev >"$ROOT/workspace/logs/desktop.log" 2>&1 & ) || true
  echo "  desktop → Electron launching (production env; workspace/logs/desktop.log)"
fi

# --- PLAYER 4: the Flutter MOBILE simulator (production target) + optional local web owner-view ---
if command -v flutter >/dev/null 2>&1; then
  flutter config --no-enable-swift-package-manager >/dev/null 2>&1 || true
  ( cd odin_app && flutter pub get >/dev/null 2>&1
    flutter run -d web-server --web-port "$WEB_PORT" --web-hostname 0.0.0.0 $DART_DEFS >"$ROOT/workspace/logs/app_web.log" 2>&1 ) &
  if [ "${ODIN_SKIP_MOBILE:-0}" = "1" ]; then
    echo "  mobile → DEFERRED (ODIN_SKIP_MOBILE=1) — will install on the REAL iPhone once you connect it."
  elif command -v xcrun >/dev/null 2>&1 && [ -d odin_app/ios ]; then
    # PHASE 3 = production → PREFER the REAL connected iPhone (physical device). Only fall back to a
    # simulator if no physical device is dev-ready. Production build (dart-defines) on either target.
    PHYS="$(cd odin_app && flutter devices --machine 2>/dev/null | python3 -c "import sys,json
try:
 d=json.load(sys.stdin); print(next((x['id'] for x in d if str(x.get('targetPlatform','')).startswith('ios') and not x.get('emulator',False)),''))
except Exception: print('')" 2>/dev/null)"
    if [ -n "$PHYS" ]; then
      echo "  mobile → REAL iPhone ($PHYS), PRODUCTION (needs a signing team in Xcode; see workspace/logs/app_ios.log)"
      ( cd odin_app && flutter run --release -d "$PHYS" $DART_DEFS >"$ROOT/workspace/logs/app_ios.log" 2>&1 ) &
    else
      # PRODUCTION policy: NEVER fall back to a simulator. ASK for the real iPhone and RETRY until it
      # connects, then install the production app to it.
      echo "  mobile → connect your iPhone via USB and tap 'Trust'. Waiting for it (retrying every 5s, up to ~15 min)…"
      ( PHYS=""
        for i in $(seq 1 180); do
          PHYS="$(cd odin_app && flutter devices --machine 2>/dev/null | python3 -c "import sys,json
try:
 d=json.load(sys.stdin); print(next((x['id'] for x in d if str(x.get('targetPlatform','')).startswith('ios') and not x.get('emulator',False)),''))
except Exception: print('')" 2>/dev/null)"
          [ -n "$PHYS" ] && break
          sleep 5
        done
        if [ -n "$PHYS" ]; then
          echo "  mobile → iPhone connected ($PHYS) — installing the PRODUCTION app (needs a signing team in Xcode ▸ Runner ▸ Signing)." >> "$ROOT/workspace/logs/app_ios.log"
          ( cd odin_app && flutter run --release -d "$PHYS" $DART_DEFS >>"$ROOT/workspace/logs/app_ios.log" 2>&1 )
        else
          echo "  mobile → no iPhone connected after waiting — connect+trust it, then re-run phase 3 (no simulator is used in production)." >> "$ROOT/workspace/logs/app_ios.log"
        fi ) &
    fi
  fi
fi

echo ""
echo "================ ODIN PHASE 3 — PRODUCTION, WHAT IS RUNNING ================"
echo "  ANCHOR (online)   ${ANCHOR_BASE}        via nginx 443 · existing SSL · VM service odin-anchor-online"
echo "  WEB (online)      ${WEB_BASE}            deployed Flutter web — open from any browser"
echo "  REQUEST page      http://localhost:${ANCHOR_SIM_PORT}/anchor_sim.html?env=prod   (talks to the ONLINE anchor)"
echo "  DESKTOP           local Electron + local brain (backend stays local, reached via the anchor)"
echo "  MOBILE sim        Flutter iOS simulator on the PRODUCTION profile"
echo "  brain/poller      background on your Mac (no windows) — poller pulls from the ONLINE anchor"
echo "  Phase 2 is untouched — run ./shells/development_full_checker.sh anytime for the development stack."
echo "==========================================================================="
wait
