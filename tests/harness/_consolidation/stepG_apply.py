"""Step G (P8-2 + R-DP) deploy.sh edits — idempotent. Run from the copy root."""
import pathlib
P = pathlib.Path('workspace/shared/infra/deploy.sh')
s = P.read_text()
def rep(old, new):
    global s
    if new in s: print('skip', old[:50].strip()); return
    assert s.count(old) == 1, (old[:80], s.count(old)); s = s.replace(old, new); print('ok', old[:50].strip())

# 1) guards + would-run helper, after the report bookkeeping
rep('''hr(){ say "------------------------------------------------------------------"; }
''', '''hr(){ say "------------------------------------------------------------------"; }
# P8-2 / R-DP: in a dry run, anything that would change the VM is LOGGED, never executed.
would(){ say "    WOULD RUN ($1): $2"; record "would-run:$1" DRY "$2"; }

# ---- R-DP guards (owner rule): RBO Staging / Production are READ-ONLY; shared services are never restarted.
# Checked BEFORE anything touches the network. There is deliberately no override switch.
_is_protected_path(){ [[ "$1" =~ ^(/home/[^/]+/|~/|\\$HOME/)?(bendcore|organics|RBO-Staging|RBO-Production)(/|$|[-_]) ]]; }
_is_protected_svc(){ [[ "$1" =~ ^(nginx|ssh|sshd|ufw|bendcore.*|organics.*)(\\.service)?$ ]]; }
_is_protected_step(){ [[ "$1" =~ (nginx|ufw|sshd|systemctl[[:space:]]+(restart|reload|stop|disable)|reboot|bendcore|organics|RBO-Staging) ]]; }
GUARD=""
for k in backend frontend; do
  [[ -n "$ONLY" && "$ONLY" != "$k" ]] && continue
  _is_protected_path "$(target_vm "$k")" && GUARD+="$k target $(target_vm "$k") is RBO Staging/Production (read-only); "
done
set +u
for s_ in "${CFG_RESTART_SERVICES[@]}"; do [[ -n "$s_" ]] && _is_protected_svc "$s_" && GUARD+="service '$s_' is shared or RBO; "; done
for s_ in "${EXTRA_STEPS[@]}"; do _is_protected_step "$s_" && GUARD+="extra step touches a shared/RBO resource: ${s_%%$'\\n'*}; "; done
set -u
if [[ -n "$GUARD" ]]; then
  say "⛔ STOP (R-DP): $GUARD"
  say "   Nothing was run: no firewall change, no SSH, no sync."
  exit 2
fi

# R-DP: read-only fingerprint of RBO Staging (folders, its services, the web ports). Taken before and after.
rbo_fp(){
  sshpass -p "$PW" ssh "${SSH_OPTS[@]}" "$VM_USER@$VM_IP" \\
    'for d in ~/bendcore ~/organics; do [ -e "$d" ] && find "$d" -maxdepth 2 -not -path "*/node_modules*" -printf "%p %s %T@\\n" 2>/dev/null | sort; done; systemctl is-active nginx bendcore-staging organics-staging 2>/dev/null; ss -tln 2>/dev/null | grep -E ":(80|443) " | sort' \\
    2>/dev/null | shasum -a 256 | cut -c1-16
}
''')

# 2) ufw: replace ONLY the owner's single-IP SSH allow; nothing else (no deny, no 80/443, no reload/reset)
rep('''  say "  · rotating VM ufw: allow 22 from ${MYIP}/32 (80/443 kept open, never reset)"
  if az vm run-command invoke -g "$RG" -n "$VM_NAME" --command-id RunShellScript --scripts \\
       "sudo ufw allow 80/tcp" \\
       "sudo ufw allow 443/tcp" \\
       "sudo ufw allow from ${MYIP} to any port 22 proto tcp" \\
       "sudo ufw status numbered | grep '22/tcp' | grep -E 'ALLOW IN|DENY IN' | grep -v '${MYIP}' | tr -d '[]' | awk '{print \\$1}' | sort -rn | while read n; do sudo ufw --force delete \\"\\$n\\"; done" \\
       "sudo ufw deny 22/tcp" \\
       "sudo ufw allow 80/tcp" \\
       "sudo ufw allow 443/tcp" \\
       "sudo ufw reload || true" \\
       "sudo ufw status numbered" >>"$LOG" 2>&1; then
    record "firewall ufw 22<-${MYIP}/32" OK "80/443 preserved; allow inserted at 1"
    say "    ✓ ufw rotated (80/443 preserved)"''',
'''  # P8-2 / R-DP: REPLACE the owner's single dynamic-IP SSH allow (add the current IP, remove older
  # single-IP 22 ALLOWs). Never stacked. Nothing else: no deny, no 80/443, no reload, no reset, and
  # "Anywhere" / v6 rules are left exactly as they are.
  say "  · replacing the owner's single-IP SSH allow on the VM ufw -> ${MYIP} (nothing else changes)"
  if az vm run-command invoke -g "$RG" -n "$VM_NAME" --command-id RunShellScript --scripts \\
       "sudo ufw allow from ${MYIP} to any port 22 proto tcp" \\
       "sudo ufw status numbered | grep '22/tcp' | grep 'ALLOW IN' | grep -v 'Anywhere' | grep -v '(v6)' | grep -v -w '${MYIP}' | tr -d '[]' | awk '{print \\$1}' | sort -rn | while read n; do sudo ufw --force delete \\"\\$n\\"; done" \\
       "sudo ufw status numbered" >>"$LOG" 2>&1; then
    record "firewall ufw 22<-${MYIP}/32" OK "single-IP SSH allow replaced; nothing else changed"
    say "    ✓ ufw single-IP SSH allow replaced"''')

# 3) never restart sshd (shared service)
rep('''    say "  · SSH still down — sshd may be stopped; restarting it via control plane (no SSH needed)…"
    az vm run-command invoke -g "$RG" -n "$VM_NAME" --command-id RunShellScript --scripts \\
        "sudo systemctl enable ssh 2>/dev/null || sudo systemctl enable sshd 2>/dev/null || true" \\
        "sudo systemctl restart ssh 2>/dev/null || sudo systemctl restart sshd 2>/dev/null || sudo service ssh restart 2>/dev/null || true" \\
        "sleep 2; (sudo ss -tlnp | grep ':22 ') || echo NO_LISTEN_22" >>"$LOG" 2>&1 \\
      && say "    ✓ sshd restart issued via control plane" \\
      || say "    ! sshd restart run-command failed (see log)"
    sleep 6''', '''    # R-DP: sshd is a SHARED service — never enabled/restarted from here. Report it for the owner.
    say "  · SSH still down. Restarting sshd is NOT allowed from a deploy (R-DP: shared service) — owner action."
    record "sshd restart" WARN "not done (R-DP: shared service) — owner action"
    if false; then''')
rep('''      [[ $attempt -lt 3 ]] && { say "    · retry after sshd restart $attempt…"; sleep 8; }
    done
  fi''', '''      [[ $attempt -lt 3 ]] && { say "    · retry after sshd restart $attempt…"; sleep 8; }
    done
    fi
  fi''')

# 4) fingerprint before phase B
rep('''  say "PHASE B · real update $([[ $DRY -eq 1 ]] && echo '(DRY-RUN: rsync preview only, no build)')"''',
'''  say "PHASE B · real update $([[ $DRY -eq 1 ]] && echo '(DRY-RUN: rsync preview only, no build)')"
  FP_BEFORE="$(rbo_fp)"; say "  · RBO Staging fingerprint before: ${FP_BEFORE}"''')

# 5) dry run: compute the VM commands and LOG them instead of skipping silently
_old5 = '    [[ $DRY -eq 1 ]] && continue   # dry-run never builds\n\n'
if _old5 in s: s = s.replace(_old5, ''); print('ok removed early dry-run skip')
if False: rep('''    [[ $DRY -eq 1 ]] && continue   # dry-run never builds

    # build the ordered VM command list (migration first, then build) — run as mostafa
    CMDS=""; BUILDCMD="$(target_build "$k")"''', '''    # build the ordered VM command list (migration first, then build) — run as mostafa
    CMDS=""; BUILDCMD="$(target_build "$k")"''')
rep('''    [[ -n "$BUILDCMD" ]] && CMDS="${CMDS:+$CMDS && }$BUILDCMD"
    [[ -z "$CMDS" ]] && continue''', '''    [[ -n "$BUILDCMD" ]] && CMDS="${CMDS:+$CMDS && }$BUILDCMD"
    [[ -z "$CMDS" ]] && continue
    if [[ $DRY -eq 1 ]]; then would "vm, as mostafa" "cd $VM && $CMDS"; continue; fi   # dry-run never builds''')
rep('''  set +u; N_EXTRA=${#EXTRA_STEPS[@]}; set -u
''', '''  set +u; N_EXTRA=${#EXTRA_STEPS[@]}; set -u
  if [[ $DRY -eq 1 && "${N_EXTRA:-0}" -gt 0 ]]; then set +u; for step in "${EXTRA_STEPS[@]}"; do would "vm" "${step%%$'\\n'*}"; done; set -u; fi
''')
# 6) fingerprint check before restart (stop if RBO changed), dry-run logs the restart
rep('''  if [[ "${B_FAIL:-0}" -ne 0 ]]; then
    say ""; say "⛔ a sync/build step FAILED''', '''  FP_MID="$(rbo_fp)"
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
    say ""; say "⛔ a sync/build step FAILED''')
# 7) never reboot the shared VM
rep('''    elif [[ "${REBOOT_FLAG:-1}" -eq 1 ]]; then
      say "    · full VM reboot (no services configured)"
      sshpass -p "$PW" ssh "${SSH_OPTS[@]}" "$VM_USER@$VM_IP" "echo '$PW' | sudo -S -p '' reboot" >>"$LOG" 2>&1 \\
        && { record "reboot" OK ""; say "    ✓ reboot issued"; } || { record "reboot" WARN "reboot returned nonzero (often normal)"; }
      say "    · waiting ~40s for the VM to come back…"; sleep 40
    fi''', '''    else
      # R-DP: the VM is SHARED (RBO Staging and other sites) — a full reboot is never done from a deploy.
      record "reboot" WARN "refused (R-DP: shared VM) — no services configured, nothing restarted"
      say "    · full VM reboot REFUSED (R-DP: shared VM). Configure the project's own services instead."
    fi''')
# 8) final fingerprint after restart/verify, and the baseline is never re-dated by a dry run
rep('''_pre_fail=0
for i in "${!STEP_NAME[@]}"; do''', '''if [[ $SSH_OK -eq 1 && -n "${FP_BEFORE:-}" ]]; then
  FP_AFTER="$(rbo_fp)"; say "  · RBO Staging fingerprint after: ${FP_AFTER}"
  [[ "$FP_AFTER" != "$FP_BEFORE" ]] && { say "⛔ STOP (R-DP): RBO Staging CHANGED during this run"; record "RBO Staging unchanged (end)" FAIL "${FP_BEFORE} -> ${FP_AFTER}"; }
fi
_pre_fail=0
for i in "${!STEP_NAME[@]}"; do''')
rep('''if [[ $_pre_fail -eq 0 && $SSH_OK -eq 1 ]]; then''', '''if [[ $DRY -eq 1 ]]; then
  would "local" "deploy_changes.py update (re-date the baseline lists)"
elif [[ $_pre_fail -eq 0 && $SSH_OK -eq 1 ]]; then''')
P.write_text(s); print('written')
