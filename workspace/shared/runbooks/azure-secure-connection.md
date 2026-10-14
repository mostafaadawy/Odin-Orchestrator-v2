# Runbook: Azure VM Secure Connection & Deploy (Dynamic IP / Egypt)

**Owner agent:** DevOps & Cloud · **Reviewer:** Security & Compliance
**Gate:** EVERY firewall/NSG/VM/deploy step is APPROVAL-GATED. The Brain guides you
step-by-step and may automate only the safe, read-only parts (see §Automation).

> Why this is strict: the operator's home IP in Egypt is **dynamic** (changes often), and
> the VM exposes SSH only to a single allow-listed IP at a time. This is an intentional,
> good security posture. We **respect it** — we never widen exposure (e.g. 0.0.0.0/0) to make
> life easier.

---

## Key facts the system must always remember
- **Access is IP-pinned:** only the current public IP is allowed to SSH; the old one is removed.
- **Two places must agree** on the allowed IP: (1) the VM's **OS firewall** (via Serial
  Console) and (2) **Azure NSG** (VM → Networking → SSH inbound rule).
- **Services run under `systemd`** — NOT PM2. Restarts/rebuilds use `systemctl`.
- **Folder mapping (local ↔ Azure):**
  | Local | Azure |
  |-------|-------|
  | `frontend/organics` | `organics` |
  | `backend/organics-backend` | `bendcore` |
- **Sync is via `scp`** from local → Azure (respect existing method; do not replace it).
- **Web proxies** front the sites and must be handled on rebuild.

---

## Procedure (ordered)

### 1. Detect current public IP  *(safe / automatable)*
```bash
curl -s https://api.ipify.org ; echo
```
Record OLD_IP (previous) and NEW_IP (current).

### 2. Update the VM OS firewall via Azure Serial Console  *(APPROVAL REQUIRED — manual)*
Azure Portal → the VM → **Serial console** → log in → run the firewall update
(example shape — confirm exact tooling: `ufw` / `firewalld` / `iptables`):
```bash
# remove the stale IP, add the new one (example for ufw)
sudo ufw delete allow from <OLD_IP> to any port 22
sudo ufw allow from <NEW_IP> to any port 22
sudo ufw status numbered
```
> Serial Console is used precisely because SSH is blocked until the IP is allowed.

### 3. Update Azure NSG SSH rule  *(APPROVAL REQUIRED — manual in Portal)*
Azure Portal → VM → **Networking** → inbound SSH rule → set **Source IP** = `NEW_IP` → Save.

### 4. Verify SSH reachability  *(safe)*
```bash
ssh -o ConnectTimeout=8 <user>@<vm-host> "echo connected; uname -a"
```

### 5. Sync folders with scp  *(APPROVAL REQUIRED — writes to VM)*
```bash
# frontend
scp -r ./frontend/organics            <user>@<vm-host>:~/organics
# backend
scp -r ./backend/organics-backend     <user>@<vm-host>:~/bendcore
```

### 6. Rebuild + restart services under systemd  *(APPROVAL REQUIRED)*
```bash
ssh <user>@<vm-host> '
  sudo systemctl daemon-reload
  sudo systemctl restart organics.service        # frontend unit
  sudo systemctl restart bendcore.service        # backend unit
  systemctl --no-pager status organics.service bendcore.service
'
```

### 7. Handle proxies  *(APPROVAL REQUIRED if config changes)*
Reload/verify the reverse proxy fronting the sites (nginx/caddy/etc.):
```bash
ssh <user>@<vm-host> 'sudo nginx -t && sudo systemctl reload nginx'
```

### 8. Post-deploy verification  *(safe)*
Health-check the public endpoints; confirm TLS valid; check service logs are clean.
```bash
ssh <user>@<vm-host> 'journalctl -u bendcore.service -n 50 --no-pager'
```

### 9. Log it
Write a CHANGE entry to `history/` (IP rotation + deploy), update `state/` + dashboard.

---

## Rollback
- Re-point services to the previous artifact / restore prior config from the pre-change copy.
- `sudo systemctl restart <unit>`; verify health.
- NSG/firewall: the prior allowed IP is recorded in the history entry if a revert is needed.

## Automation policy (what the Brain may do automatically vs. ask)
- **Auto (read-only, no approval):** detect public IP, check SSH reachability, run health
  checks, read service logs, draft the exact commands for each step.
- **Always ask (approval-gated):** any firewall/NSG change, any `scp` write, any
  `systemctl restart`/rebuild, any proxy/config change. The Brain presents the filled-in
  approval request (`runbooks/approval-template.md`) and waits for explicit YES.
- **Manual-only (Brain guides, cannot perform):** Azure Portal Serial Console login and NSG
  edits in the Portal UI — the Brain provides exact step-by-step instructions and the precise
  commands to paste.

## Placeholders to confirm with owner
`<vm-host>` / IP, `<user>`, OS firewall tool (ufw/firewalld/iptables), exact systemd unit
names, reverse-proxy software. These get recorded (non-secret) in
`infra/azure/connection.profile.json` and `infra/azure/inventory.md`.
