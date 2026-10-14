"""
Azure VM connector — runs from the owner's Mac, over SSH, using the Mac's existing SSH key.

SAFETY (per core-rules §5.1 and workspace/shared/runbooks/azure-secure-connection.md):
- Read-only helpers (`current_public_ip`, `reachable`) are safe and need no approval.
- `run(cmd)` executes an ARBITRARY command on the VM and is APPROVAL-GATED — it must only be
  called after an approval is recorded. It is NOT exposed as an open HTTP endpoint.
- Connection profile (host/user/port/keyPath) is non-secret and lives in
  workspace/shared/infra/azure/connection.profile.json. The private key stays in the Mac's ~/.ssh — never here.
- The strict dynamic-IP firewall steps (Serial Console + NSG) are MANUAL; this module only
  detects the current IP and guides; it never widens exposure.
"""
import os
import json
import subprocess
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROFILE = ROOT / "workspace" / "shared" / "infra" / "azure" / "connection.profile.json"


def load_profile() -> dict:
    return json.loads(PROFILE.read_text())


def configured() -> bool:
    p = load_profile().get("profile", {})
    return bool(p.get("host") and p.get("host") != "TBD" and p.get("sshUser") and p.get("sshUser") != "TBD")


def current_public_ip() -> str | None:
    """The Mac's public IP — the source address Azure NSG must allow for SSH."""
    for url in ("https://api.ipify.org", "https://ifconfig.me/ip", "https://icanhazip.com"):
        try:
            out = subprocess.run(["curl", "-s", "--max-time", "6", url],
                                 capture_output=True, text=True, timeout=8).stdout.strip()
            if out and len(out) <= 45:
                return out
        except Exception:
            pass
    return None


def _ssh_base() -> list[str]:
    p = load_profile()["profile"]
    cmd = ["ssh",
           "-o", "ConnectTimeout=10",
           "-o", "BatchMode=yes",
           "-o", "StrictHostKeyChecking=accept-new",
           "-p", str(p.get("sshPort", 22))]
    key = p.get("keyPath")
    if key:
        cmd += ["-i", os.path.expanduser(key)]
    cmd += [f'{p["sshUser"]}@{p["host"]}']
    return cmd


def reachable() -> dict:
    """Read-only reachability test (runs `uname -a`). Safe."""
    if not configured():
        return {"configured": False, "hint": "Fill workspace/shared/infra/azure/connection.profile.json (host, sshUser)."}
    try:
        r = subprocess.run(_ssh_base() + ["echo ODIN_OK; uname -a"],
                           capture_output=True, text=True, timeout=25)
        return {"configured": True, "ok": r.returncode == 0,
                "stdout": r.stdout.strip(), "stderr": r.stderr.strip()}
    except Exception as e:
        return {"configured": True, "ok": False, "error": str(e)}


def run(cmd: str) -> dict:
    """APPROVAL-GATED. Execute an arbitrary command on the VM. Caller must have approval."""
    if not configured():
        raise RuntimeError("VM not configured (workspace/shared/infra/azure/connection.profile.json).")
    r = subprocess.run(_ssh_base() + [cmd], capture_output=True, text=True,
                       timeout=int(os.environ.get("ODIN_SSH_TIMEOUT", "300")))
    return {"returncode": r.returncode, "stdout": r.stdout, "stderr": r.stderr}
