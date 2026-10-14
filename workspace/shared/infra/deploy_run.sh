#!/usr/bin/env bash
# =============================================================================
# deploy_run.sh — the ONE command the organics-prod-deploy PROJECT/agent runs.
# It chains the full, correct flow with strong gates. The agent runs THIS, not a
# pile of manual commands. Order is fixed and each stage gates the next:
#
#   STEP 0  CHANGE DETECTION  → python infra/deploy_changes.py scan
#           • no changes (baseline exists) → STOP, "no deployment required".
#           • changes → continue (deploy only what changed).
#   STEP 1  DEPLOY            → bash "$HERE"/deploy.sh   (rsync as mostafa → migrate(reset|new) → build →
#                              restart bendcore-staging+organics-staging [the reboot solution, no full VM reboot]).
#   STEP 2  STRONG VERIFY     → python infra/deploy_verify.py --since-epoch <deploy start>
#           • REAL file change on VM (fresh dist + .next/BUILD_ID), :4014 & :3001 == 200,
#             DB users>0/roles>0/superadmin>0/appSettings>0. Auto-restart-once if DB empty.
#           • FAIL → STOP, do NOT update lists, report ❌ (never fake success).
#   STEP 3  UPDATE LISTS      → python infra/deploy_changes.py update   (REAL current mtimes, to the minute)
#           • only on a PASS, so a re-run says "no deployment required".
#   STEP 4  CONFIRM DONE.
#
# Rules honored: SSH as mostafa; az ONLY for the SSH firewall; never root for app work; never touch
# nginx/ports/other sites; never `npm run start`.
#
#   bash infra/deploy_run.sh              # normal run
#   bash infra/deploy_run.sh --bootstrap  # seed change-lists to 2-years-ago first (=> everything changed)
# =============================================================================
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
PY="$( [ -x "$REPO/.venv/bin/python" ] && echo "$REPO/.venv/bin/python" || echo python3 )"
cd "$REPO"

echo "════════════════════════════════════════════════════════════════"
echo " ORGANICS PROD DEPLOY · $(date)"
echo "════════════════════════════════════════════════════════════════"

# Optional one-time bootstrap: mark every file changed so this run redeploys everything cleanly.
if [[ "${1:-}" == "--bootstrap" ]]; then
  echo "· STEP 0a  bootstrap: seeding change-lists to 2 years ago (everything will show as changed)"
  "$PY" "$HERE"/deploy_changes.py seed-old
fi

echo; echo "· STEP 0  change detection"
SCAN="$("$PY" "$HERE"/deploy_changes.py scan)"; echo "$SCAN"
if echo "$SCAN" | grep -q 'DEPLOY_REQUIRED: NO'; then
  echo; echo "✅ No changes since the last successful deploy — no deployment required. Done."
  exit 0
fi

# STEP 0b — SMART DB-change gate. If any CHANGED file is a schema or seed file, a plain code deploy is not
# enough: RECOMMEND (serious, but required) a DB rebase/reseed and ASK the owner to approve or deny. The
# decision sets the migration mode for THIS run (reset = destructive rebase+reseed, new = keep data).
DBSENS="$("$PY" "$HERE"/deploy_changes.py dbscan)"
export ODIN_MIG_OVERRIDE=""
if echo "$DBSENS" | grep -q 'DB_SENSITIVE: YES'; then
  echo
  echo "  ┌──────────────────────────────────────────────────────────────────────┐"
  echo "  │ ⚠  RECOMMENDATION (serious, but required): schema/seed files changed. │"
  echo "  │    A DATABASE rebase/reseed is recommended for this deploy.           │"
  echo "  └──────────────────────────────────────────────────────────────────────┘"
  echo "$DBSENS" | grep -E '^\s+⚠ \[' || true
  DECISION="${ODIN_DB_REBASE:-}"
  if [[ -z "$DECISION" ]]; then
    if [[ -t 0 ]]; then
      read -r -p "  Approve DESTRUCTIVE DB rebase+reseed (migrate reset --force)? [approve/deny]: " DECISION
    else
      echo "  ⛔ DB-sensitive changes need YOUR decision. Re-run with ODIN_DB_REBASE=approve (rebase+reseed)"
      echo "     or ODIN_DB_REBASE=deny (deploy code only, keep data). STOP."
      exit 3
    fi
  fi
  case "$DECISION" in
    approve|APPROVE|yes|y) export ODIN_MIG_OVERRIDE="reset"; echo "  ✓ approved → DB will be rebased+reseeded (reset).";;
    *)                     export ODIN_MIG_OVERRIDE="new";   echo "  ✓ denied → code-only deploy, data kept (new).";;
  esac
else
  echo "  ✓ no schema/seed changes → non-destructive deploy (data kept)."
  export ODIN_MIG_OVERRIDE="new"
fi

DEPLOY_START=$(date +%s)
echo; echo "· STEP 1  deploy (rsync → migrate → build → restart services)   [start epoch $DEPLOY_START]"
bash "$HERE"/deploy.sh
DRC=$?
if [[ $DRC -ne 0 ]]; then
  echo; echo "❌ STEP 1 deploy reported failures (exit $DRC) — STOP. Change-lists NOT updated."
  exit 1
fi

echo; echo "· STEP 2  STRONG verify (fresh builds + :4014/:3001 + DB seeded)"
"$PY" "$HERE"/deploy_verify.py --since-epoch "$DEPLOY_START"
VRC=$?
if [[ $VRC -ne 0 ]]; then
  echo; echo "❌ STEP 2 verification FAILED — STOP. Change-lists NOT updated. Production may be broken; investigate."
  exit 1
fi

echo; echo "· STEP 3  verification PASSED → updating change-lists to REAL current mtimes"
"$PY" "$HERE"/deploy_changes.py update

echo; echo "════════════════════════════════════════════════════════════════"
echo "✅ DEPLOY DONE & VERIFIED. Change-lists updated — a re-run will report 'no deployment required'."
echo "════════════════════════════════════════════════════════════════"
