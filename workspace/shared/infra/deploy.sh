#!/usr/bin/env bash
# =============================================================================
# deploy.sh — ONE comprehensive, self-diagnosing deploy you run on YOUR Mac.
#
# It does exactly what your working terminal does, but bundled, safe, and with a
# full report at the end. Two clearly separated phases:
#   PHASE A  (read-only)  — gather system facts: creds, tools, network, VM reach.
#   PHASE B  (real update) — rsync local -> VM as `mostafa`, then build on the VM.
#
# It NEVER touches secrets / node_modules / .env / prisma migrations / public /
# uploads / build output. It does NOT use `rsync --delete` by default (no data
# loss). Every step records its exit code + output; a summary table prints last.
#
# USAGE:
#   bash infra/deploy.sh                 # full deploy (backend + frontend)
#   bash infra/deploy.sh --dry-run       # rsync dry-run (shows what WOULD sync), no build
#   bash infra/deploy.sh backend         # only the backend target
#   bash infra/deploy.sh frontend src/components   # sync only a SUBFOLDER of frontend
#
# Run it once, paste me the report it prints, and I fix whatever it surfaces.
# =============================================================================
set -uo pipefail

# ---- locate the repo + credentials (script lives in <repo>/infra) -----------
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
CRED="$REPO/workspace/shared/oth/.cred"
LOG="$REPO/workspace/logs/e2e-deploy-$(date +%Y%m%d-%H%M%S).log"
mkdir -p "$REPO/workspace/logs"

# ---- config (edit these if your paths/host differ) --------------------------
VM_USER="mostafa"
RG="DJANGO-PROJECT"
VM_NAME="django-vm"
VM_IP_FALLBACK="52.180.154.225"
BACKEND_PORT="4013"

# ---- DEFAULTS (the deploy that works today). Override any of them in deploy.config.sh. -------
DEF_BACKEND_LOCAL="/Users/mostafaadawy/Desktop/VolatileWorkSpace/RBO-Staging/b"
DEF_BACKEND_VM="/home/mostafa/RBO-Staging/b"; DEF_BACKEND_MIG="new"; DEF_BACKEND_BUILD="rm -rf dist && npm run build"
DEF_FRONTEND_LOCAL="/Users/mostafaadawy/Desktop/VolatileWorkSpace/RBO-Staging/f"
DEF_FRONTEND_VM="/home/mostafa/RBO-Staging/f"; DEF_FRONTEND_MIG="none"; DEF_FRONTEND_BUILD="rm -rf .next && npm run build"
# Sync excludes = owner spec (env*, package LOCK, node_modules, dist, .next) + machine-generated / protected:
# .git, prisma/migrations (regenerated on the VM), uploads (PRODUCTION user data — never overwrite), logs,
# secrets/keys, next-env.d.ts / *.tsbuildinfo. public/ and package.json ARE synced (site assets + manifest).
DEF_EXCLUDES=( ".git" ".env" ".env.*" ".backup-env" "*.pem" "*.key"
  "config/google-oauth-client.json" "*.copy" "*.bak" "*.tmp" "*.DS_Store"
  "*.mp4" "*.mp5" "node_modules" "dist" ".next" "logs" "prisma/migrations"
  "next-env.d.ts" "*.tsbuildinfo" "package-lock.json" "uploads" "organics-local-vm-deploy-sync" )
DEF_REBOOT=1

# ---- load the owner/app config (optional). Absent = pure defaults above. ---------------------
# ODIN_DEPLOY_CONFIG (env) lets a harness point at an ISOLATED config (e.g. a sandbox) without
# touching the real deploy.config.sh. If unset, the normal deploy.config.sh is used.
CFG_EXTRA_EXCLUDES=(); CFG_DROP_EXCLUDES=(); EXTRA_STEPS=()
_CFG_FILE="${ODIN_DEPLOY_CONFIG:-$HERE/deploy.config.sh}"
[[ -f "$_CFG_FILE" ]] && source "$_CFG_FILE" && say_cfg=1 || say_cfg=0

# ---- resolve effective values (CFG_* override DEF_*) -----------------------------------------
BACKEND_LOCAL="${CFG_BACKEND_LOCAL:-$DEF_BACKEND_LOCAL}";  BACKEND_VM="${CFG_BACKEND_VM:-$DEF_BACKEND_VM}"
# ODIN_MIG_OVERRIDE (env, set by deploy_run.sh after the owner approves/denies a DB rebase for schema/seed
# changes) wins over the config so the DB decision is made per-run, on the recommendation — never silently.
BACKEND_MIG="${ODIN_MIG_OVERRIDE:-${CFG_BACKEND_MIG:-$DEF_BACKEND_MIG}}"; BACKEND_BUILD="${CFG_BACKEND_BUILD:-$DEF_BACKEND_BUILD}"
FRONTEND_LOCAL="${CFG_FRONTEND_LOCAL:-$DEF_FRONTEND_LOCAL}"; FRONTEND_VM="${CFG_FRONTEND_VM:-$DEF_FRONTEND_VM}"
FRONTEND_MIG="${CFG_FRONTEND_MIG:-$DEF_FRONTEND_MIG}";       FRONTEND_BUILD="${CFG_FRONTEND_BUILD:-$DEF_FRONTEND_BUILD}"
REBOOT_FLAG="${CFG_REBOOT:-$DEF_REBOOT}"
target_local(){ case "$1" in backend) echo "$BACKEND_LOCAL";; frontend) echo "$FRONTEND_LOCAL";; esac; }
target_vm(){    case "$1" in backend) echo "$BACKEND_VM";;    frontend) echo "$FRONTEND_VM";; esac; }
target_mig(){   case "$1" in backend) echo "$BACKEND_MIG";;   frontend) echo "$FRONTEND_MIG";; esac; }
target_build(){ case "$1" in backend) echo "$BACKEND_BUILD";; frontend) echo "$FRONTEND_BUILD";; esac; }

# effective EXCLUDES = defaults + extras − drops
EXCLUDES=()
set +u
for e in "${DEF_EXCLUDES[@]}" "${CFG_EXTRA_EXCLUDES[@]}"; do
  [[ -z "$e" ]] && continue
  drop=0; for d in "${CFG_DROP_EXCLUDES[@]}"; do [[ "$e" == "$d" ]] && drop=1; done
  [[ $drop -eq 0 ]] && EXCLUDES+=( "$e" )
done
set -u

DRY=0; ONLY=""; SUBPATH=""; PRINTCFG=0
for a in "$@"; do
  case "$a" in
    --dry-run) DRY=1 ;;
    --print-config) PRINTCFG=1 ;;     # print the EFFECTIVE config the run will use, then exit
    backend|frontend) ONLY="$a" ;;
    *) SUBPATH="$a" ;;            # optional subfolder of the chosen target
  esac
done

# --print-config: emit exactly what THIS run would do (for the re-ask / review step), then exit.
if [[ $PRINTCFG -eq 1 ]]; then
  echo "EFFECTIVE DEPLOY CONFIG (defaults unless infra/deploy.config.sh overrides):"
  echo "  config file present : $([[ -f "$HERE/deploy.config.sh" ]] && echo yes || echo no)"
  echo "  reboot              : ${REBOOT_FLAG:-1}"
  for k in backend frontend; do
    echo "  $k local            : $(target_local "$k")"
    echo "  $k → VM             : $(target_vm "$k")"
    echo "  $k migration        : $(target_mig "$k")"
    echo "  $k commands         : $(target_build "$k")"
  done
  echo "  excludes (${#EXCLUDES[@]}):"
  for e in "${EXCLUDES[@]}"; do echo "      - $e"; done
  set +u; ne=${#EXTRA_STEPS[@]}; set -u
  echo "  extra steps (${ne:-0}):"
  if [[ "${ne:-0}" -gt 0 ]]; then for s in "${EXTRA_STEPS[@]}"; do echo "      - ${s%%$'\n'*}"; done; fi
  exit 0
fi

# ---- report bookkeeping -----------------------------------------------------
declare -a STEP_NAME STEP_STATE STEP_NOTE
record(){ STEP_NAME+=("$1"); STEP_STATE+=("$2"); STEP_NOTE+=("$3"); }
say(){ echo -e "$*" | tee -a "$LOG"; }
hr(){ say "------------------------------------------------------------------"; }
# P8-2 / R-DP: in a dry run, anything that would change the VM is LOGGED, never executed.
would(){ say "    WOULD RUN ($1): $2"; record "would-run:$1" DRY "$2"; }

# ---- R-DP guards (owner rule): RBO Staging / Production are READ-ONLY; shared services are never restarted.
# Checked BEFORE anything touches the network. There is deliberately no override switch.
_is_protected_path(){ [[ "$1" =~ ^(/home/[^/]+/|~/|\$HOME/)?(bendcore|organics|RBO-Staging|RBO-Production)(/|$|[-_]) ]]; }
_is_protected_svc(){ [[ "$1" =~ ^(nginx|ssh|sshd|ufw|bendcore.*|organics.*)(\.service)?$ ]]; }
_is_protected_step(){ [[ "$1" =~ (nginx|ufw|sshd|systemctl[[:space:]]+(restart|reload|stop|disable)|reboot|bendcore|organics|RBO-Staging) ]]; }
GUARD=""
for k in backend frontend; do
  [[ -n "$ONLY" && "$ONLY" != "$k" ]] && continue
  _is_protected_path "$(target_vm "$k")" && GUARD+="$k target $(target_vm "$k") is RBO Staging/Production (read-only); "
done
set +u
for s_ in "${CFG_RESTART_SERVICES[@]}"; do [[ -n "$s_" ]] && _is_protected_svc "$s_" && GUARD+="service '$s_' is shared or RBO; "; done
for s_ in "${EXTRA_STEPS[@]}"; do _is_protected_step "$s_" && GUARD+="extra step touches a shared/RBO resource: ${s_%%$'\n'*}; "; done
set -u
if [[ -n "$GUARD" ]]; then
  say "⛔ STOP (R-DP): $GUARD"
  say "   Nothing was run: no firewall change, no SSH, no sync."
  exit 2
fi

# R-DP: read-only fingerprint of RBO Staging (folders, its services, the web ports). Taken before and after.
rbo_fp(){
  sshpass -p "$PW" ssh "${SSH_OPTS[@]}" "$VM_USER@$VM_IP" \
    'for d in ~/bendcore ~/organics; do [ -e "$d" ] && find "$d" -maxdepth 2 -not -path "*/node_modules*" -printf "%p %s %T@\n" 2>/dev/null | sort; done; systemctl is-active nginx bendcore-staging organics-staging 2>/dev/null; ss -tln 2>/dev/null | grep -E ":(80|443) " | sort' \
    2>/dev/null | shasum -a 256 | cut -c1-16
}

SSH_OPTS=(-o PreferredAuthentications=password -o PubkeyAuthentication=no
          -o StrictHostKeyChecking=no -o ConnectTimeout=20)

say "E2E DEPLOY  ·  $(date)"
say "repo: $REPO"
say "log : $LOG"
hr

# =============================================================================
# PHASE A — READ-ONLY system facts (changes nothing)
# =============================================================================
say "PHASE A · read-only pre-flight"

# 1) credential
PW=""
if [[ -f "$CRED" ]]; then
  PW="$(grep -E 'azvmcred' "$CRED" | sed -E 's/.*azvmcred[[:space:]]*[:=][[:space:]]*//' | tr -d '\r')"
fi
if [[ -n "$PW" ]]; then record "credential (workspace/shared/oth/.cred azvmcred)" OK "found"; say "  ✓ credential found";
else record "credential (workspace/shared/oth/.cred azvmcred)" FAIL "missing"; say "  ✗ NO azvmcred in $CRED"; fi

# 2) tools
for tool in sshpass rsync ssh az curl; do
  if command -v "$tool" >/dev/null 2>&1; then record "tool:$tool" OK "$(command -v $tool)"; say "  ✓ $tool";
  else record "tool:$tool" FAIL "not installed"; say "  ✗ $tool MISSING";
    [[ "$tool" == sshpass ]] && say "      → brew install hudochenkov/sshpass/sshpass";
  fi
done

# 3) local folders
for k in backend frontend; do
  LD="$(target_local "$k")"
  if [[ -d "$LD" ]]; then record "local:$k" OK "$LD"; say "  ✓ local $k present";
  else record "local:$k" FAIL "$LD missing"; say "  ✗ local $k MISSING"; fi
done

# 4) public IP + VM IP (read-only)
MYIP="$(curl -fsS -4 https://api.ipify.org 2>/dev/null || curl -fsS -4 https://ifconfig.me 2>/dev/null || echo '')"
say "  · my public IP: ${MYIP:-unknown}"
VM_IP=""
if command -v az >/dev/null 2>&1; then
  VM_IP="$(az vm show -d -g "$RG" -n "$VM_NAME" --query publicIps -o tsv 2>>"$LOG" | tr -d '\r')"
fi
VM_IP="${VM_IP:-$VM_IP_FALLBACK}"
say "  · VM IP: $VM_IP"

# 5) firewall refresh (control plane) so SSH from THIS IP is allowed on 22
if command -v az >/dev/null 2>&1 && [[ -n "$MYIP" ]]; then
  say "  · refreshing NSG port-22 rule -> ${MYIP}/32 (single-IP allow)"
  RULE="$(az network nsg list -g "$RG" --query "[0].name" -o tsv 2>>"$LOG")"
  if [[ -n "$RULE" ]]; then
    SSHRULE="$(az network nsg rule list -g "$RG" --nsg-name "$RULE" \
      --query "[?destinationPortRange=='22'||contains(destinationPortRanges,'22')].name | [0]" -o tsv 2>>"$LOG")"
    if [[ -n "$SSHRULE" ]]; then
      az network nsg rule update -g "$RG" --nsg-name "$RULE" -n "$SSHRULE" \
        --source-address-prefixes "${MYIP}/32" --access Allow --protocol Tcp \
        --destination-port-ranges 22 >>"$LOG" 2>&1 \
        && { record "firewall NSG->${MYIP}/32" OK "$RULE/$SSHRULE"; say "    ✓ NSG updated"; } \
        || { record "firewall NSG->${MYIP}/32" FAIL "az rule update failed (see log)"; say "    ✗ NSG update failed"; }
    else record "firewall NSG" WARN "no port-22 rule found"; say "    ! no port-22 rule found";
    fi
  else record "firewall NSG" WARN "no NSG in RG"; say "    ! no NSG found in $RG";
  fi
else record "firewall NSG" WARN "az or public IP unavailable"; say "  ! skipped firewall refresh";
fi

# 5b) VM ufw single-IP (control plane run-command) — the OTHER half of our access protocol. The NSG
#     above only governs Azure's edge; the VM's own ufw can still drop port 22. SAFE BY CONSTRUCTION:
#       - 80/443 are explicitly ALLOWED (the websites can never be taken down by this step),
#       - the current-IP SSH allow is INSERTED AT POSITION 1 so it is evaluated BEFORE any deny,
#       - then 22 is denied for everyone else (single-IP SSH),
#     and it NEVER runs `ufw reset`, `ufw disable`, or flushes rules. This is exactly the safe
#     rotation we hardened after the outage — no default-deny that could black-hole web traffic.
if command -v az >/dev/null 2>&1 && [[ -n "$MYIP" && -n "$VM_NAME" ]]; then
  # P8-2 / R-DP: REPLACE the owner's single dynamic-IP SSH allow (add the current IP, remove older
  # single-IP 22 ALLOWs). Never stacked. Nothing else: no deny, no 80/443, no reload, no reset, and
  # "Anywhere" / v6 rules are left exactly as they are.
  say "  · replacing the owner's single-IP SSH allow on the VM ufw -> ${MYIP} (nothing else changes)"
  if az vm run-command invoke -g "$RG" -n "$VM_NAME" --command-id RunShellScript --scripts \
       "sudo ufw allow from ${MYIP} to any port 22 proto tcp" \
       "sudo ufw status numbered | grep '22/tcp' | grep 'ALLOW IN' | grep -v 'Anywhere' | grep -v '(v6)' | grep -v -w '${MYIP}' | tr -d '[]' | awk '{print \$1}' | sort -rn | while read n; do sudo ufw --force delete \"\$n\"; done" \
       "sudo ufw status numbered" >>"$LOG" 2>&1; then
    record "firewall ufw 22<-${MYIP}/32" OK "single-IP SSH allow replaced; nothing else changed"
    say "    ✓ ufw single-IP SSH allow replaced"
  else
    record "firewall ufw" WARN "run-command failed (see log)"
    say "    ! ufw rotate via run-command failed (continuing to SSH test)"
  fi
  sleep 6   # let the NSG + ufw changes settle before the connection test
fi

# 6) THE decisive read-only test: can we SSH to the VM as mostafa? Retry a couple times to absorb
#    NSG/ufw propagation lag right after the rotation above.
SSH_OK=0
if [[ -n "$PW" ]] && command -v sshpass >/dev/null 2>&1; then
  say "  · testing SSH: mostafa@$VM_IP …"
  for attempt in 1 2 3; do
    if OUT=$(sshpass -p "$PW" ssh "${SSH_OPTS[@]}" "$VM_USER@$VM_IP" 'echo SSH_OK; whoami; node -v 2>/dev/null; npm -v 2>/dev/null' 2>>"$LOG"); then
      SSH_OK=1; record "ssh reach VM" OK "$(echo "$OUT" | tr '\n' ' ')"; say "    ✓ SSH connected: $(echo "$OUT" | tr '\n' ' ')";
      break
    fi
    [[ $attempt -lt 3 ]] && { say "    · SSH attempt $attempt failed — waiting for firewall to settle, retrying…"; sleep 8; }
  done
  # 6b) SELF-HEAL: if SSH still won't connect, the VM may simply have sshd stopped (not firewall,
  #     not power — the probe shows other ports listening). Restart sshd via the CONTROL PLANE
  #     (works without SSH). Safe: only (re)starts + enables the ssh service, touches nothing else.
  if [[ $SSH_OK -ne 1 ]] && command -v az >/dev/null 2>&1 && [[ -n "$VM_NAME" ]]; then
    # R-DP: sshd is a SHARED service — never enabled/restarted from here. Report it for the owner.
    say "  · SSH still down. Restarting sshd is NOT allowed from a deploy (R-DP: shared service) — owner action."
    record "sshd restart" WARN "not done (R-DP: shared service) — owner action"
    if false; then
    for attempt in 1 2 3; do
      if OUT=$(sshpass -p "$PW" ssh "${SSH_OPTS[@]}" "$VM_USER@$VM_IP" 'echo SSH_OK; whoami; node -v 2>/dev/null; npm -v 2>/dev/null' 2>>"$LOG"); then
        SSH_OK=1; record "ssh reach VM (after sshd restart)" OK "$(echo "$OUT" | tr '\n' ' ')"; say "    ✓ SSH connected after sshd restart"; break
      fi
      [[ $attempt -lt 3 ]] && { say "    · retry after sshd restart $attempt…"; sleep 8; }
    done
    fi
  fi
  if [[ $SSH_OK -ne 1 ]]; then
    record "ssh reach VM" FAIL "sshd not accepting on 22 even after a control-plane restart (see log)"
    say "    ✗ SSH still down after NSG+ufw+sshd-restart. The VM is up (other ports listen) but sshd"
    say "      won't come back via the Azure agent — likely a broken sshd config on the VM that needs a look."
  fi
else
  record "ssh reach VM" FAIL "no password or sshpass"; say "    ✗ cannot test SSH (missing password or sshpass)";
fi

hr
if [[ $SSH_OK -ne 1 ]]; then
  say "STOP: the VM is not reachable over SSH, so no update can run. Fix the ✗ items above first."
  say "      (Most common: install sshpass, or the firewall/IP didn't open port 22 to ${MYIP:-your IP}.)"
  # still print the summary so you have the full picture
else
  # ===========================================================================
  # PHASE B — REAL UPDATE (rsync + build as mostafa). Only runs if SSH works.
  # ===========================================================================
  say "PHASE B · real update $([[ $DRY -eq 1 ]] && echo '(DRY-RUN: rsync preview only, no build)')"
  FP_BEFORE="$(rbo_fp)"; say "  · RBO Staging fingerprint before: ${FP_BEFORE}"
  EX_ARGS=(); for e in "${EXCLUDES[@]}"; do EX_ARGS+=( --exclude="$e" ); done
  B_FAIL=0   # ANY rsync/build failure → abort: never run build/reset, never reboot on a broken sync

  for k in backend frontend; do
    [[ -n "$ONLY" && "$ONLY" != "$k" ]] && continue
    LOCAL="$(target_local "$k")"; VM="$(target_vm "$k")"
    # Normalize the destination home to the ACTUAL ssh user — fixes the /home/mustafa vs /home/mostafa
    # typo automatically (mostafa can't write under another user's /home → rsync exit 11).
    case "$VM" in
      /home/*/*) NEWVM="/home/$VM_USER/${VM#/home/*/}";
                 [[ "$NEWVM" != "$VM" ]] && say "    · normalized dest home -> $NEWVM (was $VM)"; VM="$NEWVM" ;;
    esac
    # optional subfolder targeting (e.g. only sync src/components)
    if [[ -n "$SUBPATH" && ( -z "$ONLY" || "$ONLY" == "$k" ) ]]; then
      LOCAL="$LOCAL/$SUBPATH"; VM="$VM/$SUBPATH"
    fi
    say ""; say ">>> $k : ${LOCAL}  →  ${VM_USER}@VM:${VM}"
    RSYNC=( sshpass -p "$PW" rsync -az -e "ssh ${SSH_OPTS[*]}" "${EX_ARGS[@]}" )
    [[ $DRY -eq 1 ]] && RSYNC+=( -n -v )
    RSYNC+=( "${LOCAL%/}/" "${VM_USER}@${VM_IP}:${VM%/}/" )
    if "${RSYNC[@]}" >>"$LOG" 2>&1; then
      record "rsync:$k" OK "$([[ $DRY -eq 1 ]] && echo dry-run || echo synced)"; say "    ✓ rsync $k ok";
    else
      rc=$?; record "rsync:$k" FAIL "exit $rc (see log)"; say "    ✗ rsync $k FAILED (exit $rc)"; B_FAIL=1; continue;
    fi

    # build the ordered VM command list (migration first, then build) — run as mostafa
    CMDS=""; BUILDCMD="$(target_build "$k")"
    case "$(target_mig "$k")" in
      # non-destructive: regenerate the client + apply committed migrations. NEVER resets, never
      # prompts (the correct production command). If there are no pending migrations it's a no-op.
      new)   CMDS="npx prisma generate && npx prisma migrate deploy" ;;
      # destructive wipe+reseed — ONLY when explicitly chosen. Forced non-interactive.
      reset) CMDS="rm -rf prisma/migrations && npx prisma generate && npx prisma migrate reset --force && npx prisma migrate dev --name ini" ;;
    esac
    [[ -n "$BUILDCMD" ]] && CMDS="${CMDS:+$CMDS && }$BUILDCMD"
    [[ -z "$CMDS" ]] && continue
    if [[ $DRY -eq 1 ]]; then would "vm, as mostafa" "cd $VM && $CMDS"; continue; fi   # dry-run never builds
    say "    · (vm, as mostafa) cd $VM && $CMDS"
    if sshpass -p "$PW" ssh "${SSH_OPTS[@]}" "$VM_USER@$VM_IP" "export CI=1; bash -lc 'set -e; cd $(printf %q "$VM") && $CMDS'" </dev/null >>"$LOG" 2>&1; then
      record "build:$k" OK "ok"; say "    ✓ build $k ok";
    else
      rc=$?; record "build:$k" FAIL "exit $rc (see log)"; say "    ✗ build $k FAILED (exit $rc) — check the log for the compiler error"; B_FAIL=1;
    fi
  done

  # EXTRA steps (services / subdomain folder / nginx proxy / etc.) — config-driven, as mostafa.
  set +u; N_EXTRA=${#EXTRA_STEPS[@]}; set -u
  if [[ $DRY -eq 1 && "${N_EXTRA:-0}" -gt 0 ]]; then set +u; for step in "${EXTRA_STEPS[@]}"; do would "vm" "${step%%$'\n'*}"; done; set -u; fi
  if [[ $DRY -eq 0 && -z "$SUBPATH" && "${N_EXTRA:-0}" -gt 0 ]]; then
    say ""; say "· extra steps (${N_EXTRA}) from deploy.config.sh"
    eidx=0
    for step in "${EXTRA_STEPS[@]}"; do
      eidx=$((eidx+1)); say "    · (vm) ${step%%$'\n'*}"
      if sshpass -p "$PW" ssh "${SSH_OPTS[@]}" "$VM_USER@$VM_IP" "export CI=1; bash -lc 'set -e; $step'" </dev/null >>"$LOG" 2>&1; then
        record "extra:$eidx" OK "${step%%$'\n'*}"; say "      ✓ ok";
      else
        rc=$?; record "extra:$eidx" FAIL "exit $rc — ${step%%$'\n'*}"; say "      ✗ failed (exit $rc, see log)";
      fi
    done
  fi

  # restart/reboot + verify (full run only) — but NEVER proceed if a sync/build failed.
  # CFG_RESTART_SERVICES (preferred): restart ONLY the app services (e.g. bendcore organics). This is the
  #   "reboot solution" that re-runs the boot self-seed after a DB reset, WITHOUT dropping the other 5
  #   production sites on this shared VM (never damage). Full `sudo reboot` is only used if no services
  #   are configured AND CFG_REBOOT=1.
  # count real services: an empty string / unset means "this project has no systemd units" (e.g. a sandbox),
  # which must SKIP the restart cleanly instead of failing on an empty systemctl command.
  set +u
  N_SVC=0
  if [[ -n "${CFG_RESTART_SERVICES+x}" ]]; then
    if [[ "$(declare -p CFG_RESTART_SERVICES 2>/dev/null)" == "declare -a"* ]]; then
      N_SVC=${#CFG_RESTART_SERVICES[@]}
    else
      [[ -n "${CFG_RESTART_SERVICES// /}" ]] && N_SVC=1 || N_SVC=0
    fi
  fi
  set -u
  # the VERIFY port belongs to the PROJECT (delta), not to whichever project this engine was born for
  VERIFY_BACKEND_PORT="${CFG_BACKEND_PORT:-$BACKEND_PORT}"
  FP_MID="$(rbo_fp)"
  if [[ "$FP_MID" != "$FP_BEFORE" ]]; then
    say "⛔ STOP (R-DP): the RBO Staging fingerprint CHANGED (${FP_BEFORE} -> ${FP_MID}). Not continuing."
    record "RBO Staging unchanged" FAIL "fingerprint changed ${FP_BEFORE} -> ${FP_MID}"; B_FAIL=1
  else
    record "RBO Staging unchanged" OK "fingerprint ${FP_BEFORE}"
  fi
  if [[ $DRY -eq 1 && -z "$ONLY" && -z "$SUBPATH" ]]; then
    set +u
    if [[ "${N_SVC:-0}" -gt 0 ]]; then would "vm" "sudo systemctl restart ${CFG_RESTART_SERVICES[*]}"; fi
    set -u
    would "vm" "verify backend :$VERIFY_BACKEND_PORT"
  fi
  if [[ "${B_FAIL:-0}" -ne 0 ]]; then
    say ""; say "⛔ a sync/build step FAILED — NOT restarting and NOT proceeding. Nothing was reset. Fix the ✗ items above."
  elif [[ $DRY -eq 0 && -z "$ONLY" && -z "$SUBPATH" ]]; then
    say ""; say "· restart services + verify"
    say "__ODIN_REBOOTED__"   # COMMIT POINT marker — the agent must NOT re-run the deploy after this
    if [[ "${N_SVC:-0}" -gt 0 ]]; then
      SVC_LIST="${CFG_RESTART_SERVICES[*]}"
      say "    · restarting app services (never touches other sites/nginx/ports): $SVC_LIST"
      if sshpass -p "$PW" ssh "${SSH_OPTS[@]}" "$VM_USER@$VM_IP" \
           "echo '$PW' | sudo -S -p '' systemctl restart $SVC_LIST && systemctl is-active $SVC_LIST" </dev/null >>"$LOG" 2>&1; then
        record "restart services" OK "$SVC_LIST"; say "    ✓ services restarted (boot self-seed re-runs on bendcore)";
      else
        record "restart services" FAIL "systemctl restart failed (see log)"; say "    ✗ service restart FAILED"; B_FAIL=1;
      fi
    elif [[ "${REBOOT_FLAG:-1}" -eq 0 ]]; then
      record "restart services" OK "none configured for this project (sandbox) — skipped by design"
      say "    · no services configured for this project — skipping restart (by design)"
    else
      # R-DP: the VM is SHARED (RBO Staging and other sites) — a full reboot is never done from a deploy.
      record "reboot" WARN "refused (R-DP: shared VM) — no services configured, nothing restarted"
      say "    · full VM reboot REFUSED (R-DP: shared VM). Configure the project's own services instead."
    fi
    # basic reachability wait; the STRONG gate (fresh builds + DB seeded + :4014/:3001 200) is deploy_verify.py
    if sshpass -p "$PW" ssh "${SSH_OPTS[@]}" "$VM_USER@$VM_IP" \
        "for i in \$(seq 1 12); do curl -fsS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:$VERIFY_BACKEND_PORT && exit 0; sleep 10; done; exit 7" >>"$LOG" 2>&1; then
      record "verify backend :$VERIFY_BACKEND_PORT" OK "HTTP 200"; say "    ✓ backend responded on :$VERIFY_BACKEND_PORT";
    else
      record "verify backend :$VERIFY_BACKEND_PORT" FAIL "no 200 within ~2min (see journalctl in log)"; say "    ✗ backend did not respond — see log";
    fi
  fi
fi

# =============================================================================
# BASELINE LIST UPDATE — ONLY after a verified-good deploy
# =============================================================================
# The saved front/back lists must be re-dated to the REAL file mtimes ONLY once the DB + live-endpoint
# checks passed. Doing it earlier would mark files as "deployed" that were never actually verified, and
# the next scan would wrongly report "nothing to deploy". So: count failures first, then update.
if [[ $SSH_OK -eq 1 && -n "${FP_BEFORE:-}" ]]; then
  FP_AFTER="$(rbo_fp)"; say "  · RBO Staging fingerprint after: ${FP_AFTER}"
  [[ "$FP_AFTER" != "$FP_BEFORE" ]] && { say "⛔ STOP (R-DP): RBO Staging CHANGED during this run"; record "RBO Staging unchanged (end)" FAIL "${FP_BEFORE} -> ${FP_AFTER}"; }
fi
_pre_fail=0
for i in "${!STEP_NAME[@]}"; do [[ "${STEP_STATE[$i]}" == "FAIL" ]] && ((_pre_fail++)); done
if [[ $DRY -eq 1 ]]; then
  would "local" "deploy_changes.py update (re-date the baseline lists)"
elif [[ $_pre_fail -eq 0 && $SSH_OK -eq 1 ]]; then
  _PY="$REPO/.venv/bin/python"; [[ -x "$_PY" ]] || _PY="$(command -v python3 || command -v python)"
  if "$_PY" "$REPO/workspace/shared/infra/deploy_changes.py" update >>"$LOG" 2>&1; then
    record "baseline lists updated" OK "real mtimes saved (verified deploy only)"
    say "  ✓ baseline front/back lists re-dated to the real file mtimes"
  else
    record "baseline lists updated" WARN "deploy_changes.py update failed (see log)"
  fi
else
  record "baseline lists updated" WARN "SKIPPED — deploy not fully verified (lists left untouched)"
  say "  ! baseline lists NOT updated (deploy not verified) — next run will still see the changes"
fi

# =============================================================================
# FINAL REPORT
# =============================================================================
hr; say "SUMMARY"; hr
pass=0; fail=0; warn=0
for i in "${!STEP_NAME[@]}"; do
  s="${STEP_STATE[$i]}"; icon="•"
  case "$s" in OK) icon="✓"; ((pass++));; FAIL) icon="✗"; ((fail++));; WARN) icon="!"; ((warn++));; esac
  printf "  %s  %-34s %-5s %s\n" "$icon" "${STEP_NAME[$i]}" "$s" "${STEP_NOTE[$i]}" | tee -a "$LOG"
done
hr
say "RESULT:  $pass ok · $warn warn · $fail fail"
say "Full raw log (every command's output): $LOG"
[[ $fail -eq 0 && $SSH_OK -eq 1 ]] && say "✅ Deploy completed." || say "⚠️  Not fully done — fix the ✗ items, or paste this report back to me."
exit $(( fail > 0 ? 1 : 0 ))
