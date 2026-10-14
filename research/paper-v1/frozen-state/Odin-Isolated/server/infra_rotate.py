"""
Automated dynamic-IP SSH rotation via Azure CLI — keeps the NSG to a SINGLE IP.

Solves the owner's lockout problem WITHOUT Serial Console or Portal clicking, by using two
Azure control-plane operations (these go through Azure's agent, not the network, so they work
even while SSH is blocked):

  1. az network nsg rule update   -> set the NSG SSH inbound source to <new_ip>/32 (one IP)
  2. az vm run-command invoke      -> run `reset_ssh_ip <new_ip>` on the VM (updates ufw)

APPROVAL-GATED: this changes firewall + NSG rules. Never call without the owner's approval.
Requires Azure CLI installed and logged in:  brew install azure-cli ; az login
Azure resource names live (non-secret) in workspace/shared/infra/azure/connection.profile.json -> "azure".
"""
import json
import shutil
import subprocess
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROFILE = ROOT / "workspace" / "shared" / "infra" / "azure" / "connection.profile.json"


def az_available() -> bool:
    return shutil.which("az") is not None


def _cfg() -> dict:
    # Only the resource group + VM name are required; the NSG name and SSH rule name are
    # AUTO-DISCOVERED from Azure if they're missing/TBD (Odin is logged in — it figures it out).
    a = json.loads(PROFILE.read_text()).get("azure", {})
    missing = [k for k in ("resourceGroup", "vmName") if not a.get(k) or a.get(k) == "TBD"]
    if missing:
        raise RuntimeError(f"Azure config missing in connection.profile.json -> azure: {missing}")
    return a


def _az(args, timeout=120):
    r = subprocess.run([shutil.which("az") or "az", *args], capture_output=True, text=True, timeout=timeout)
    return (r.stdout or "").strip(), (r.stderr or "").strip(), r.returncode


def _discover_nsg(rg: str, vm: str) -> str | None:
    """Find the VM's NSG via its NIC (direct, or on the subnet)."""
    nic, _, _ = _az(["vm", "show", "-g", rg, "-n", vm, "--query",
                     "networkProfile.networkInterfaces[0].id", "-o", "tsv"])
    if not nic:
        return None
    nsg, _, _ = _az(["network", "nic", "show", "--ids", nic, "--query", "networkSecurityGroup.id", "-o", "tsv"])
    if not nsg:
        sub, _, _ = _az(["network", "nic", "show", "--ids", nic, "--query",
                         "ipConfigurations[0].subnet.id", "-o", "tsv"])
        if sub:
            nsg, _, _ = _az(["network", "vnet", "subnet", "show", "--ids", sub, "--query",
                             "networkSecurityGroup.id", "-o", "tsv"])
    return nsg.split("/")[-1] if nsg else None


def _discover_ssh_rule(rg: str, nsg: str) -> str | None:
    """Find the inbound rule that opens port 22 in the NSG."""
    name, _, _ = _az(["network", "nsg", "rule", "list", "-g", rg, "--nsg-name", nsg, "--query",
                      "[?destinationPortRange=='22'] | [0].name", "-o", "tsv"])
    return name or None


def _persist(nsg: str | None, rule: str | None) -> None:
    try:
        p = json.loads(PROFILE.read_text())
        az = p.setdefault("azure", {})
        if nsg:
            az["nsgName"] = nsg
        if rule:
            az["sshRuleName"] = rule
        PROFILE.write_text(json.dumps(p, indent=2, ensure_ascii=False))
    except Exception:
        pass


def current_public_ip() -> str | None:
    from infra_ssh import current_public_ip as _ip
    return _ip()


def _ufw_script(ip: str) -> str:
    """Rotate ONLY the SSH (port 22) rule to a single IP, while GUARANTEEING the public web ports
    (80/443) stay open — so tightening SSH can never take the websites down.

    Order matters: open 80/443 FIRST (idempotent), so there is never a window where the sites are
    blocked. Then touch ONLY port-22 rules (never flush other rules, never change default policy in a
    way that drops web traffic). This is the safe reset the owner asked for: function + security kept.
    """
    return (
        'set -e\n'
        f'new_ip="{ip}"\n'
        '# 1) PUBLIC WEB PORTS — always allowed (the websites must stay reachable). Idempotent.\n'
        'sudo ufw allow 80/tcp\n'
        'sudo ufw allow 443/tcp\n'
        '# 2) SSH (22) — restrict to the single current IP, deny the rest. Only port-22 rules touched.\n'
        "sudo ufw status numbered | awk '/22\\/tcp/ && (/ALLOW IN/ || /DENY IN/) "
        '{gsub(/\\[|\\]/,"",$2); print $2}\' | sort -rn | '
        'while read -r n; do sudo ufw --force delete "$n"; done\n'
        'sudo ufw allow from "$new_ip" to any port 22 proto tcp\n'
        'sudo ufw deny 22/tcp\n'
        '# 3) safety net: confirm 80/443 are present; if ufw is active they MUST be ALLOW.\n'
        'sudo ufw allow 80/tcp >/dev/null 2>&1 || true\n'
        'sudo ufw allow 443/tcp >/dev/null 2>&1 || true\n'
        'sudo ufw status numbered\n'
    )


def rotate(new_ip: str | None = None) -> dict:
    """APPROVAL-GATED. Point NSG + VM ufw at the current (or given) public IP. NSG name and SSH
    rule are auto-discovered from Azure if not in the profile. The ufw step (via the control plane)
    always runs and is what actually opens SSH at the VM."""
    if not az_available():
        raise RuntimeError("Azure CLI not found. Install: brew install azure-cli ; then: az login")
    cfg = _cfg()
    rg, vm = cfg["resourceGroup"], cfg["vmName"]
    ip = new_ip or current_public_ip()
    if not ip:
        raise RuntimeError("Could not detect current public IP.")

    nsg = cfg.get("nsgName") if cfg.get("nsgName") not in (None, "", "TBD") else _discover_nsg(rg, vm)
    rule = cfg.get("sshRuleName") if cfg.get("sshRuleName") not in (None, "", "TBD") else (_discover_ssh_rule(rg, nsg) if nsg else None)
    if nsg or rule:
        _persist(nsg, rule)   # remember what we found for next time

    out = {"ip": ip, "nsg": nsg, "rule": rule, "steps": []}

    # 1) NSG rule → single IP (best-effort; the ufw step below is the critical one).
    if nsg and rule:
        r1 = subprocess.run(
            ["az", "network", "nsg", "rule", "update", "--resource-group", rg,
             "--nsg-name", nsg, "--name", rule, "--source-address-prefixes", f"{ip}/32", "-o", "json"],
            capture_output=True, text=True, timeout=150)
        out["steps"].append({"step": "nsg-rule-update", "ok": r1.returncode == 0,
                             "stderr": (r1.stderr or "").strip()[:600]})
    else:
        out["steps"].append({"step": "nsg-rule-update", "ok": False, "skipped": True,
                             "stderr": "No NSG/SSH rule found to update — refreshing VM ufw only."})

    # 2) VM ufw → single IP, via the control plane (works even while SSH is blocked).
    r2 = subprocess.run(
        ["az", "vm", "run-command", "invoke", "--resource-group", rg, "--name", vm,
         "--command-id", "RunShellScript", "--scripts", _ufw_script(ip), "-o", "json"],
        capture_output=True, text=True, timeout=200)
    out["steps"].append({"step": "vm-ufw-update", "ok": r2.returncode == 0,
                         "stderr": (r2.stderr or "").strip()[:600]})

    # Connection is usable if the VM ufw step succeeded (that's what gates SSH at the host).
    out["ok"] = any(s["step"] == "vm-ufw-update" and s["ok"] for s in out["steps"])
    return out
