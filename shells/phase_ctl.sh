#!/usr/bin/env bash
# phase_ctl.sh — CONTROL BRIDGE for the Anchor phases (same idea as workspace/shared/testing/loop.sh).
#
# WHY: the agent (Claude) cannot reach your Azure VM from its sandbox. This watcher runs on YOUR Mac (which
# DOES have VM access) as part of development_full_checker.sh / production_full_checker.sh. The agent writes a command into
#   workspace/logs/phase_ctl/CMD   (a mounted file it can edit)
# and this watcher executes a curated, SAFE action and appends the result to
#   workspace/logs/phase_ctl/OUT.log   +   workspace/logs/phase_ctl/STATUS
# so the agent can drive the flow, read real logs, confirm behaviour, and find issues — without you.
#
# Commands the agent may write into CMD (one per line, latest wins):
#   health                         → curl every component (brain/anchor/sim/webhook + online anchor)
#   send <project_id> <prompt…>    → POST a request to the anchor, poll to done, record the full flow+result
#   tail <brain|anchor_remote|local_poller|webhook|anchor_sim|phase3_deploy>  → last 30 log lines
#   vm                             → READ-ONLY VM diagnostics (anchor health on VM, existing :80 site health)
#   redeploy                       → re-run the safe online anchor deploy (phase 3 only)
set -uo pipefail
cd "$(dirname "$0")/.."
CTL="workspace/logs/phase_ctl"; mkdir -p "$CTL"
CMD="$CTL/CMD"; OUT="$CTL/OUT.log"; ST="$CTL/STATUS"
[ -f "$CMD" ] || : > "$CMD"
BRAIN_PORT="${BRAIN_PORT:-8000}"; ANCHOR_PORT="${ODIN_ANCHOR_PORT:-${ANCHOR_PORT:-9100}}"
SIM_PORT="${ANCHOR_SIM_PORT:-9104}"; WH_PORT="${WEBHOOK_PORT:-9300}"; VM_IP="${VM_IP:-}"; PROXY_HOST="${PROXY_HOST:-$VM_IP}"
PYBIN="$(command -v python || command -v python3)"
KEY="$(grep -E 'ANCHOR_API_KEY' workspace/shared/oth/.cred 2>/dev/null | head -1 | cut -d= -f2- | tr -d '"[:space:]')"
KH=(); [ -n "$KEY" ] && KH=(-H "X-API-Key: $KEY")
emit(){ echo "[$(date '+%H:%M:%S')] $*" >> "$OUT"; }
mt(){ stat -f %m "$1" 2>/dev/null || stat -c %Y "$1" 2>/dev/null || echo 0; }

do_health(){
  emit "HEALTH"
  for pr in "brain:$BRAIN_PORT" "anchor-local:$ANCHOR_PORT" "sim:$SIM_PORT" "webhook:$WH_PORT"; do
    n="${pr%%:*}"; p="${pr##*:}"
    c=$(curl -s -m 5 -o /dev/null -w '%{http_code}' "http://localhost:$p/" 2>/dev/null || echo ERR)
    emit "  $n (:$p) → $c"
  done
  if [ -n "$VM_IP" ]; then
    c=$(curl -sk -m 8 -o /dev/null -w '%{http_code}' "https://$PROXY_HOST/odin-anchor/health" 2>/dev/null || echo ERR)
    emit "  ONLINE anchor (https://$PROXY_HOST/odin-anchor) → $c"
    w=$(curl -sk -m 8 -o /dev/null -w '%{http_code}' "https://$PROXY_HOST/odin-web" 2>/dev/null || echo ERR)
    emit "  ONLINE web (https://$PROXY_HOST/odin-web) → $w"
  fi
}

do_send(){
  local proj="$1"; shift; local prompt="$*"
  local base; [ -n "$VM_IP" ] && base="https://$PROXY_HOST/odin-anchor" || base="http://localhost:$ANCHOR_PORT"
  emit "SEND base=$base project=$proj prompt=\"$prompt\""
  # F-22 / N6: a localhost webhook only works with the LOCAL anchor; the online anchor (VM) cannot reach this Mac,
  # so against it we register NO webhook and simply poll for the result below (no ack_pending retry noise).
  local body
  if [ -n "$VM_IP" ]; then
    body=$(printf '{"project":"%s","prompt":"%s"}' "$proj" "$prompt")
  else
    body=$(printf '{"project":"%s","prompt":"%s","webhook_url":"http://localhost:%s/cb"}' "$proj" "$prompt" "$WH_PORT")
  fi
  local resp; resp=$(curl -sk -m 15 "${KH[@]}" -H 'Content-Type: application/json' -d "$body" "$base/anchor/v1/requests" 2>/dev/null)
  emit "  queued: $resp"
  local rid; rid=$(printf '%s' "$resp" | "$PYBIN" -c 'import sys,json;print(json.load(sys.stdin).get("request_id",""))' 2>/dev/null || echo "")
  [ -z "$rid" ] && { emit "  no request_id — abort"; return; }
  for i in $(seq 1 40); do
    sleep 3
    local s; s=$(curl -sk -m 8 "${KH[@]}" "$base/anchor/v1/requests/$rid" 2>/dev/null)
    local st; st=$(printf '%s' "$s" | "$PYBIN" -c 'import sys,json;print(json.load(sys.stdin).get("status",""))' 2>/dev/null || echo "?")
    emit "  [$rid] status=$st (${i}0s)"
    # the RESULT is available as soon as it's posted (status may stay ack_pending because the VM anchor
    # can't reach your Mac's localhost webhook) — show it the moment the result field is populated.
    local res; res=$(printf '%s' "$s" | "$PYBIN" -c 'import sys,json;r=json.load(sys.stdin).get("result");print(str(r) if r not in (None,"") else "")' 2>/dev/null)
    if [ -n "$res" ]; then
      emit "  RESULT: ${res:0:800}"
      return
    fi
  done
  emit "  (not done after ~120s — check workspace/logs/local_poller.log)"
}

do_tail(){ local f="workspace/logs/$1.log"; emit "TAIL $f"; tail -30 "$f" 2>/dev/null >> "$OUT" || emit "  (no such log)"; }

do_vm(){
  emit "VM read-only diagnostics"
  ( cd server && "$PYBIN" -c "
import deploy_ssh as d
for lbl,c in [('anchor@VM','curl -s -o /dev/null -w %{http_code} http://127.0.0.1:${ANCHOR_PORT}/health'),
              ('existing :80','curl -s -o /dev/null -w %{http_code} http://127.0.0.1:80'),
              ('anchor.log','tail -6 /home/mostafa/anchor-online/anchor.log 2>/dev/null')]:
    r=d.ssh_exec(c); print('  '+lbl+' -> '+((r.get('out') or r.get('error') or '')[:200]).replace(chr(10),' | '))
" ) >> "$OUT" 2>&1 || emit "  (vm check errored)"
}

do_redeploy(){ emit "REDEPLOY (safe online anchor)"; ODIN_ANCHOR_PORT="$ANCHOR_PORT" "$PYBIN" workspace/shared/testing/test_anchor_online.py >> "$OUT" 2>&1 || emit "  (redeploy returned non-zero)"; }
do_trace(){ emit "TRACE CHAIN (desktop → anchor local → anchor public → web → nginx)"; ODIN_SERVER_NAME="${PROXY_HOST}" ODIN_ANCHOR_PORT="${ANCHOR_PORT}" "$PYBIN" workspace/shared/testing/trace_chain.py >> "$OUT" 2>&1 || emit "  (trace errored)"; }
do_isolate(){ emit "ISOLATE ANCHOR NODE (mimic every transmission as an outside caller; 100%-or-name-the-failure)"; "$PYBIN" workspace/shared/testing/isolate_anchor.py >> "$OUT" 2>&1 || emit "  (isolate errored)"; }
do_audit(){ emit "SECURITY AUDIT (read-only: ufw+NSG+listeners+nginx)"; "$PYBIN" workspace/shared/testing/vm_security_audit.py >> "$OUT" 2>&1 || emit "  (audit errored)"; }
do_auditfix(){ emit "SECURITY FIX: remove 48619/48620 from ufw+NSG; 80/443/22 left untouched"; "$PYBIN" workspace/shared/testing/vm_security_audit.py --fix >> "$OUT" 2>&1 || emit "  (fix errored)"; }

emit "phase-ctl bridge started (anchor=$ANCHOR_PORT sim=$SIM_PORT vm=${VM_IP:-none})"
echo "READY $(date)" > "$ST"
LAST="$(mt "$CMD")"
while true; do
  NOW="$(mt "$CMD")"
  if [ "$NOW" != "$LAST" ]; then
    LAST="$NOW"
    C="$(tail -1 "$CMD" 2>/dev/null)"
    if [ -n "$C" ]; then
      echo "RUNNING: $C  $(date)" > "$ST"; emit "=== CMD: $C ==="
      # shellcheck disable=SC2086
      set -- $C
      case "${1:-}" in
        health|status) do_health ;;
        send) shift; p="${1:-}"; shift || true; do_send "$p" "$*" ;;
        tail) do_tail "${2:-}" ;;
        vm) do_vm ;;
        redeploy) do_redeploy ;;
        trace) do_trace ;;
        isolate) do_isolate ;;
        audit) do_audit ;;
        auditfix) do_auditfix ;;
        "") : ;;
        *) emit "unknown: $C (health|send <proj> <prompt>|tail <comp>|vm|redeploy|audit|auditfix)" ;;
      esac
      emit "=== done ==="; echo "IDLE $(date)" > "$ST"
    fi
  fi
  sleep 2
done
