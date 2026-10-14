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
BRAIN_PORT="${BRAIN_PORT:-8000}"                # LOCAL brain (desktop's backend) — stays local, reached via anchor
ANCHOR_PORT="${ODIN_ANCHOR_PORT:-48619}"        # ONLINE anchor port on the VM (behind nginx 443)
WEB_PORT="${WEB_PORT:-8080}"                    # optional local owner-view web (production target)
WEB_VM_PORT="${WEB_VM_PORT:-48620}"             # ONLINE web port on the VM (behind nginx 443)
WEBHOOK_PORT="${WEBHOOK_PORT:-9300}"
ANCHOR_SIM_PORT="${ANCHOR_SIM_PORT:-9104}"      # local request/CD-flow page, opened in PRODUCTION mode
PROXY_HOST="${ODIN_SERVER_NAME:-anchor.odinmarkets.com}"
export ODIN_SERVER_NAME="$PROXY_HOST"
ANCHOR_BASE="https://${PROXY_HOST}/odin-anchor"
WEB_BASE="https://${PROXY_HOST}/odin-web"

bash "$(dirname "$0")/pg_heal.sh" || exit 1
echo "================ ODIN v2 — PRODUCTION (Anchor deploy + production links + mobile) ================"
# v2: key/password rotation (cutover). `--rotate-keys` (or ODIN_ROTATE_KEYS=1) makes a NEW Anchor API key and a NEW
# Manage password (both generated, saved locally, no prompt) BEFORE deploying, so the deploy ships the new values and the old ones stop working.
for _a in "$@"; do [ "$_a" = "--rotate-keys" ] && ODIN_ROTATE_KEYS=1; done
if [ "${ODIN_ROTATE_KEYS:-0}" = "1" ]; then
  echo "---- rotating the Anchor API key + Manage password (values are never shown) ----"
  "$PYBIN" server/odin_secrets.py rotate || { echo "❌ rotation failed — NOT deploying."; exit 1; }
  "$PYBIN" server/odin_secrets.py rotate-vm || { echo "❌ VM password rotation failed (old password kept/restored) — NOT deploying."; exit 1; }
  ODIN_FORCE_DEPLOY=1
fi
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
    echo "  → first production run from v2: an initial deployment is needed."
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
    if [ "${ODIN_FORCE_DEPLOY:-0}" = "1" ]; then echo "  → no code changes, but the keys were rotated → deploying."; DO_DEPLOY=1
    else echo "  → no changes since the last successful deployment → NOT deploying; starting production."; fi ;;
  *)
    echo "  ⚠ could not determine a decision; defaulting to SAFE no-deploy (start production only)." ;;
esac

# =====================================================================================================
# 5) validate VM  +  6) deploy (proven tools)  +  7) production e2e — only when deploying
# =====================================================================================================
# v2: the Anchor VM is the owner's own machine — ALWAYS confirm before touching it (ODIN_PHASE3_YES=1 skips).
if [ "$DO_DEPLOY" = "1" ] && [ "${ODIN_PHASE3_YES:-0}" != "1" ] && [ "$DECISION" != "CHANGED" ]; then
  printf "  Deploy the v2 Anchor + web to https://%s now? [y/N] " "$PROXY_HOST"
  read -r ANS </dev/tty 2>/dev/null || ANS="n"
  case "$ANS" in y|Y|yes|YES) ;; *) DO_DEPLOY=0; echo "  → deployment declined — starting the CURRENT production setup only." ;; esac
fi

DEPLOY_OK=1
# v2: one STATUS line per part, printed at the end of the run
ST_ANCHOR="unchanged — already live (not redeployed)"; ST_WEB="unchanged — already live (not redeployed)"
ST_E2E="not run"; ST_DMG="not built"; ST_PHONE="not started"; ST_RBO="not checked (no deploy this run)"
mkdir -p workspace/logs; : > workspace/logs/phone_status.txt
if [ "$DO_DEPLOY" = "1" ]; then
  echo ""
  echo "---- pre-deploy VM validation (read-only) ----------------------------------------"
  if ! "$PYBIN" workspace/shared/infra/phase3_gate.py validate | tee workspace/logs/phase3_validate.log; then
    echo "❌ VM validation reported a blocking problem (see workspace/logs/phase3_validate.log). STOPPING — nothing deployed."
    exit 1
  fi

  # v2: RBO "before" fingerprint (read-only) — compared again right after the deploy
  if [ "$DEPLOY_OK" = "1" ]; then
    echo ""; echo "---- RBO fingerprint BEFORE (read-only) ----"
    RBO_B="$("$PYBIN" "$ROOT/_v2/cutover/04a_vm_guard.py" before --no-backup 2>&1)"; RBO_RC=$?
    echo "$RBO_B" | head -1
    if [ "$RBO_RC" != "0" ]; then echo "❌ RBO before-check failed — STOPPING. Nothing deployed."; exit 1; fi
  fi

  # ANCHOR: overwrite the VM folder FROM deploy_anchor (ships ALL files incl anchor_manage.py), create the
  # Postgres DB link (dedicated role owns the EXISTING odin_anchor db — never recreated), restart the EXISTING
  # service (leverage it; existing nginx/domain/SSL reused, never self-signed). DB is created if missing inside.
  if [ "$DEPLOY_OK" = "1" ]; then
    echo ""
    echo "---- pre-deploy proof: the Anchor exactly as deployed reads ONLY its 3 values and enforces the API key ----"
    # HARD GATE: the proof must finish (120 s limit), exit 0 AND print "FLAT ANCHOR OK" — otherwise the run STOPS here.
    ( set -o pipefail; perl -e 'alarm shift; exec @ARGV' 120 bash "$ROOT/_v2/cutover/anchor_flat_test.sh" 2>&1 \
        | tee workspace/logs/anchor_flat_test.log ); PROOF_RC=$?
    if [ "$PROOF_RC" != "0" ] || ! tail -3 workspace/logs/anchor_flat_test.log | grep -q "FLAT ANCHOR OK"; then
      echo "❌ pre-deploy proof failed or timed out (rc=$PROOF_RC) — STOPPING. Nothing was deployed."; exit 1
    fi
  fi

  if [ "$DEPLOY_OK" = "1" ]; then
    echo ""
    echo "---- deploy ANCHOR: overwrite /home/mostafa/anchor-online FROM deploy_anchor + Postgres link + restart ----"
    "$PYBIN" workspace/shared/infra/phase3_gate.py deploy-anchor | tee workspace/logs/phase3_deploy.log
    A_RC="${PIPESTATUS[0]}"
    [ "$A_RC" = "0" ] && ST_ANCHOR="✓ deployed → ${ANCHOR_BASE}"
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
        && echo "  ✓ production web built" || { echo "❌ production web build failed (workspace/logs/web_build.log) — STOPPING before the web deploy."; exit 1; }
    fi
    "$PYBIN" workspace/shared/infra/phase3_gate.py deploy-web | tee -a workspace/logs/phase3_deploy.log
    W_RC="${PIPESTATUS[0]}"
    [ "$W_RC" = "0" ] && ST_WEB="✓ deployed → ${WEB_BASE}"
    if [ "$W_RC" != "0" ]; then echo "❌ web deploy failed — see workspace/logs/phase3_deploy.log. STOPPING."; exit 1; fi
  fi

  # v2: RBO "after" fingerprint — must be identical to "before"
  if [ "$DEPLOY_OK" = "1" ]; then
    echo ""; echo "---- RBO fingerprint AFTER (read-only) ----"
    RBO_OUT="$("$PYBIN" "$ROOT/_v2/cutover/04a_vm_guard.py" after 2>&1 | tail -3)"; echo "$RBO_OUT"
    if echo "$RBO_OUT" | grep -q "RBO UNTOUCHED"; then ST_RBO="✓ identical before/after (51 items)"; else
      ST_RBO="❌ DIFFERENCE — see above"; echo "❌ RBO fingerprint changed — STOPPING and reporting (nothing on the RBO side is touched)."; exit 1; fi
  fi

  # 7) production e2e — prove the ONLINE endpoints answer with production behaviour
  if [ "$DEPLOY_OK" = "1" ]; then
    echo ""
    echo "---- production e2e tests (fixed checks against the ONLINE endpoints) -------------"
    ODIN_SERVER_NAME="$PROXY_HOST" "$PYBIN" workspace/shared/infra/phase3_e2e.py | tee workspace/logs/phase3_e2e.log
    E_RC="${PIPESTATUS[0]}"
    [ "$E_RC" = "0" ] && ST_E2E="✓ PASS (live sign-in, auth enforced, production links)" || ST_E2E="❌ FAILED — workspace/logs/phase3_e2e.log"
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

# v2: when nothing was redeployed, still PROVE the live production answers correctly (read-only checks)
if [ "$ST_E2E" = "not run" ]; then
  echo ""; echo "---- live production check (read-only) ----"
  if ODIN_SERVER_NAME="$PROXY_HOST" "$PYBIN" workspace/shared/infra/phase3_e2e.py | tee workspace/logs/phase3_e2e.log | tail -2; then
    tail -1 workspace/logs/phase3_e2e.log | grep -q PASS && ST_E2E="✓ PASS (live sign-in, auth enforced, production links)" || ST_E2E="❌ FAILED — workspace/logs/phase3_e2e.log"
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
# v2 / F-14: the desktop app reads the Anchor key + Manage login from the macOS Keychain (never from its bundle).
"$PYBIN" server/odin_secrets.py keychain || echo "  ⚠ Keychain not provisioned — the desktop 'Anchor' code button stays idle until it is."

# v2: build the DESKTOP DMG from this exact code (clean-install tested inside the build script).
if [ "${ODIN_SKIP_DMG:-0}" != "1" ]; then
  echo ""; echo "---- building the desktop DMG (workspace/logs/dmg_build.log) ----"
  if bash "$ROOT/shells/build_desktop_dmg.sh" >"$ROOT/workspace/logs/dmg_build.log" 2>&1 && grep -q "RESULT: DMG OK" "$ROOT/workspace/logs/dmg_build.log"; then
    DMG_PATH="$(ls -t "$ROOT"/desktop/release/*.dmg 2>/dev/null | head -1)"
    ST_DMG="✓ built + clean-install tested → ${DMG_PATH}"
  else
    ST_DMG="❌ DMG build failed — workspace/logs/dmg_build.log"
  fi
  echo "  $ST_DMG"
fi

# =====================================================================================================
# 8) AUTO-START only the MAIN players (production). Supporting services run in the background (no windows).
# =====================================================================================================
DART_DEFS="--dart-define=ODIN_FORCE_ENV=production --dart-define=ODIN_ANCHOR=${ANCHOR_BASE}"

# --- background: local brain (the desktop's backend; stays local, reached through the anchor) ---
_BR_NAME="$("$PYBIN" -c "import json,urllib.request;print(json.load(urllib.request.urlopen('http://localhost:$BRAIN_PORT/health',timeout=2)).get('root_name',''))" 2>/dev/null)"
if [ -n "$(lsof -ti tcp:"$BRAIN_PORT" 2>/dev/null)" ] && [ "$_BR_NAME" != "$(basename "$ROOT")" ]; then
  echo "  ! a brain from ANOTHER checkout (${_BR_NAME:-v1 / unknown}) holds :$BRAIN_PORT — stopping it, starting the v2 brain"
  KP="$(lsof -ti tcp:"$BRAIN_PORT" 2>/dev/null || true)"; [ -n "$KP" ] && kill $KP 2>/dev/null; sleep 2
  KP="$(lsof -ti tcp:"$BRAIN_PORT" 2>/dev/null || true)"; [ -n "$KP" ] && kill -9 $KP 2>/dev/null; sleep 1
fi
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
( cd "$ROOT/server" && "$PYBIN" -u sim_server.py --host 127.0.0.1 --port "$ANCHOR_SIM_PORT" >"$ROOT/workspace/logs/anchor_sim.log" 2>&1 ) &
# v2 fix (14 Oct): WAIT until the request page really answers (up to 20s) before opening it — opening after a
# fixed 1s sleep raced the server start, so Safari got "can't connect" and the page never appeared.
SIM_URL="http://127.0.0.1:$ANCHOR_SIM_PORT/anchor_sim.html?env=prod"
for i in $(seq 1 40); do curl -s -o /dev/null --max-time 1 "$SIM_URL" && break; sleep 0.5; done
if curl -s -o /dev/null --max-time 2 "$SIM_URL"; then
  command -v open >/dev/null 2>&1 && open -a Safari "$SIM_URL" >/dev/null 2>&1 || true
  echo "  ✓ request page opened in Safari: $SIM_URL"
else
  echo "  ⚠ request page did not start — see workspace/logs/anchor_sim.log"
fi

# --- PLAYER 2: the WEB PRODUCTION page (the deployed site, online) ---
command -v open >/dev/null 2>&1 && open -a Safari "$WEB_BASE" >/dev/null 2>&1 || true
# also show the ONLINE anchor landing page (production, not the dev one)
command -v open >/dev/null 2>&1 && open -a Safari "${ANCHOR_BASE}/" >/dev/null 2>&1 || true

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
  # v2 (14 Oct): ASK before the phone step and WAIT for the answer — skip it when the app is already on the phone.
  if [ "${ODIN_SKIP_MOBILE:-0}" != "1" ] && [ -t 0 ]; then
    echo ""
    echo "  📱 PHONE STEP — install/refresh the Odin app on your iPhone?"
    echo "     [i] install now (connect + unlock the phone)     [s] skip — the app is already on the phone"
    _ans=""
    while [ "$_ans" != "i" ] && [ "$_ans" != "s" ]; do
      read -r -p "     your choice (i/s): " _ans; _ans="$(printf '%s' "$_ans" | tr 'A-Z' 'a-z' | cut -c1)"
    done
    if [ "$_ans" = "s" ]; then
      ODIN_SKIP_MOBILE=1; echo "skipped by you — the app already on the phone is used" > "$ROOT/workspace/logs/phone_status.txt"
    fi
  fi
  if [ "${ODIN_SKIP_MOBILE:-0}" = "1" ]; then
    echo "  mobile → skipped (the app already on your iPhone keeps working; re-run and pick [i] to refresh it)"
  elif command -v xcrun >/dev/null 2>&1 && [ -d odin_app/ios ]; then
    # v2: BUILD the production iOS app first (so the install is quick once the phone is connected).
    echo "  mobile → building the PRODUCTION iOS app (release)… (workspace/logs/app_ios_build.log)"
    ( cd odin_app && flutter build ios --release $DART_DEFS >"$ROOT/workspace/logs/app_ios_build.log" 2>&1 ) \
      && echo "  ✓ production iOS app built" || echo "  ⚠ iOS build issue — see workspace/logs/app_ios_build.log (signing team set in Xcode ▸ Runner ▸ Signing?)"
    echo ""
    echo "  ┌─ PHONE STEP (you) ───────────────────────────────────────────────────────────────┐"
    echo "  │ 1. Connect your iPhone by USB and tap 'Trust This Computer'.                      │"
    echo "  │ 2. After install: iPhone Settings ▸ General ▸ VPN & Device Management ▸ trust the  │"
    echo "  │    Apple Development profile, then open Odin. (A personal-team install stays valid │"
    echo "  │    about 7 days, a paid developer team about a year — re-run this to refresh.)     │"
    echo "  └───────────────────────────────────────────────────────────────────────────────────┘"
    # PHASE 3 = production → the REAL iPhone only (never a simulator).
    # v2 fix (14 Oct): one dedicated installer — install AND launch (proven `flutter run --release`
    # method), success only when the app actually opened; separate log; 10-min hard cap.
    echo "waiting for your iPhone — connect it by USB, UNLOCK it and tap Trust" > "$ROOT/workspace/logs/phone_status.txt"
    ( ANCHOR_BASE="$ANCHOR_BASE" DART_DEFS="$DART_DEFS" bash "$ROOT/shells/phone_install.sh" ) &
  fi
fi

echo ""
echo "================ ODIN PHASE 3 — PRODUCTION, WHAT IS RUNNING ================"
echo "  ANCHOR (online)   ${ANCHOR_BASE}        via nginx 443 · existing SSL · VM service odin-anchor-online"
echo "  WEB (online)      ${WEB_BASE}            deployed Flutter web — open from any browser"
echo "  REQUEST page      http://127.0.0.1:${ANCHOR_SIM_PORT}/anchor_sim.html?env=prod   (talks to the ONLINE anchor)"
echo "  DESKTOP           local Electron + local brain (backend stays local, reached via the anchor)"
echo "  MOBILE            your REAL iPhone (production build) — no simulator in production"
echo "  brain/poller      background on your Mac (no windows) — poller pulls from the ONLINE anchor"
echo "  Phase 2 is untouched — run ./shells/development_full_checker.sh anytime for the development stack."
echo "==========================================================================="
ST_PHONE="$(cat "$ROOT/workspace/logs/phone_status.txt" 2>/dev/null)"; [ -z "$ST_PHONE" ] && ST_PHONE="skipped (ODIN_SKIP_MOBILE=1)"
echo ""
echo "======================= PRODUCTION STATUS ======================="
printf "  %-16s %s\n" "Anchor"      "$ST_ANCHOR"
printf "  %-16s %s\n" "Web"         "$ST_WEB"
printf "  %-16s %s\n" "Live checks" "$ST_E2E"
printf "  %-16s %s\n" "RBO"         "$ST_RBO"
printf "  %-16s %s\n" "Desktop DMG" "$ST_DMG"
printf "  %-16s %s\n" "Phone"       "$ST_PHONE"
ST_CONN="$("$PYBIN" "$ROOT/_v2/cutover/connectors_live.py" 2>/dev/null | awk '{printf "%s %s · ", $1, $2}')"
printf "  %-16s %s\n" "Connectors"  "${ST_CONN:-could not check}"
echo "  Links:"
echo "    Anchor (online)   ${ANCHOR_BASE}/"
echo "    Web (online)      ${WEB_BASE}/"
echo "    Request page      http://127.0.0.1:${ANCHOR_SIM_PORT}/anchor_sim.html?env=prod   (customer requests → ONLINE anchor)"
echo "  (Phone result appears here as a 📱 PHONE line when the install finishes.)  Ctrl-C stops the local side."
echo "================================================================="
wait
