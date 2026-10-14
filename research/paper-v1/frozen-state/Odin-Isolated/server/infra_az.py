"""
Azure control-plane connector for Odin — runs ON the owner's Mac (where `az` is logged in).

Uses `az vm run-command invoke` to execute commands on the VM through Azure's agent (as root),
with NO SSH, NO key, NO IP allow-listing required. This is how Odin "connects" and manages the
VM safely. Read-only helpers here; arbitrary command execution (`vm_run`) is APPROVAL-GATED and
not exposed as an open endpoint.

Resource group is auto-discovered from the VM name, so the owner only provides the VM name.
"""
import os
import json
import shutil
import subprocess
import pathlib
import threading
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
# The connection profile lives under the workspace (canonical) after the restructure; keep the old
# repo-root path as a fallback. Whichever exists is used.
_PROFILE_CANDIDATES = [
    ROOT / "workspace" / "shared" / "infra" / "azure" / "connection.profile.json",
    ROOT / "infra" / "azure" / "connection.profile.json",
]
PROFILE = next((p for p in _PROFILE_CANDIDATES if p.exists()), _PROFILE_CANDIDATES[0])

# Azure CLI shares a token cache under ~/.azure; concurrent `az` calls (the badge poll + an agent
# running its own `az`) can contend and one transiently fails. We serialize the backend's az calls
# and remember the last good connection so a busy run can't flip the badge to a false "disconnected".
_AZ_LOCK = threading.Lock()
_LAST_GOOD = {"ts": 0.0, "res": None}
_GOOD_TTL = 300  # seconds: trust a recent success through transient blips


def _az_bin() -> str | None:
    """SELF-HEAL: find the `az` binary even when PATH is stripped (macOS GUI apps) — check the
    normal PATH first, then the common Homebrew / install locations."""
    p = shutil.which("az")
    if p:
        return p
    for c in ("/opt/homebrew/bin/az", "/usr/local/bin/az", "/opt/homebrew/sbin/az",
              os.path.expanduser("~/.local/bin/az"), "/usr/bin/az"):
        if os.path.exists(c):
            return c
    return None


def az_available() -> bool:
    return _az_bin() is not None


def _profile() -> dict:
    # RESILIENT: re-resolve each call (the file may be created after start) and NEVER throw — a missing
    # profile must yield a clean {"ok":false} status, not a 500 that freezes the badge on red.
    for p in _PROFILE_CANDIDATES:
        try:
            if p.exists():
                return json.loads(p.read_text())
        except Exception:
            pass
    return {}


def vm_name() -> str:
    return _profile().get("azure", {}).get("vmName", "")


def discover_rg() -> str | None:
    vm = vm_name()
    if not vm:
        return None
    az = _profile().get("azure", {})
    if az.get("resourceGroup") and az["resourceGroup"] != "TBD":
        return az["resourceGroup"]
    r = subprocess.run(
        [_az_bin() or "az", "vm", "list", "--query", f"[?name=='{vm}'].resourceGroup | [0]", "-o", "tsv"],
        capture_output=True, text=True, timeout=60)
    rg = (r.stdout or "").strip()
    return rg or None


def _save_rg(rg: str) -> None:
    p = _profile()
    p.setdefault("azure", {})["resourceGroup"] = rg
    p["status"] = "connected (Azure control-plane via az vm run-command)"
    PROFILE.write_text(json.dumps(p, indent=2, ensure_ascii=False))


def app_user() -> str:
    """The VM user that OWNS the app dirs. Commands run as this user so they never create
    root-owned files (the cause of the 'permission denied' lockout). Configurable in the profile."""
    try:
        return (_profile().get("azure", {}).get("appUser") or "mostafa")
    except Exception:
        return "mostafa"


def vm_run(script: str, rg: str | None = None, as_user: str | None = None) -> dict:
    """Run a shell script on the VM via the Azure agent. By DEFAULT it runs as the app user
    (so builds/syncs produce user-owned files, never root-owned). Pass as_user='root' only for
    genuine root ops (reboot, ufw/firewall, apt). APPROVAL-GATED for changes."""
    if not az_available():
        raise RuntimeError("Azure CLI not found on PATH (this must run on the Mac, not the sandbox).")
    vm = vm_name()
    rg = rg or discover_rg()
    if not rg:
        raise RuntimeError(f"Could not find resource group for VM '{vm}'. Is `az login` done?")
    user = app_user() if as_user is None else as_user
    if user and user != "root":
        import shlex
        wrapped = f"sudo -u {user} -H bash -lc {shlex.quote(script)}"   # run AS the app user → no root-owned files
    else:
        wrapped = script
    r = subprocess.run(
        [_az_bin() or "az", "vm", "run-command", "invoke", "-g", rg, "-n", vm,
         "--command-id", "RunShellScript", "--scripts", wrapped,
         "--query", "value[0].message", "-o", "tsv"],
        capture_output=True, text=True, timeout=200)
    return {"rg": rg, "vm": vm, "ok": r.returncode == 0, "ran_as": user or "root",
            "output": (r.stdout or "").strip(), "error": (r.stderr or "").strip()[:800]}


def _connect_test_raw() -> dict:
    if not az_available():
        return {"ok": False, "vm": vm_name(), "reason": "az-not-found",
                "hint": "Azure CLI not found. Install it (`brew install azure-cli`)."}
    last = None
    # one retry on a transient failure (token-cache contention shows up as an intermittent error)
    for attempt in (1, 2):
        try:
            res = vm_run("echo '=== whoami ==='; whoami; uname -a; ls -la /home")
        except Exception as e:
            msg = str(e)
            reason = "not-logged-in" if "login" in msg.lower() else "run-failed"
            last = {"ok": False, "vm": vm_name(), "reason": reason, "hint": msg[:200]}
            if reason == "not-logged-in":
                return last           # not transient — don't retry
            time.sleep(1.5); continue
        if res.get("ok"):
            if res.get("rg"):
                try:
                    _save_rg(res["rg"])
                except Exception:
                    pass
            res["reason"] = "connected"
            return res
        err = (res.get("error") or "").lower()
        res["reason"] = "not-logged-in" if "az login" in err or "credential" in err else "run-failed"
        res["hint"] = (res.get("error") or "VM command failed")[:200]
        last = res
        if res["reason"] == "not-logged-in":
            return last
        time.sleep(1.5)
    return last or {"ok": False, "vm": vm_name(), "reason": "run-failed", "hint": "unknown"}


def vm_public_ip() -> str | None:
    """The VM's current public IP (for rsync/ssh once the firewall is opened to our IP)."""
    if not az_available():
        return None
    vm = vm_name()
    rg = discover_rg()
    if not (vm and rg):
        return None
    try:
        r = subprocess.run([_az_bin() or "az", "vm", "show", "-d", "-g", rg, "-n", vm,
                            "--query", "publicIps", "-o", "tsv"],
                           capture_output=True, text=True, timeout=60)
        return (r.stdout or "").strip() or None
    except Exception:
        return None


def connect_test() -> dict:
    """Read-only proof of connection — RESILIENT so the badge stays solid during busy runs.
    Serializes az calls, retries transient blips, and falls back to the last good result if it
    happened recently (a concurrent-az hiccup must NOT flip the badge to 'disconnected')."""
    with _AZ_LOCK:
        res = _connect_test_raw()
    now = time.time()
    if res.get("ok"):
        _LAST_GOOD["ts"] = now
        _LAST_GOOD["res"] = res
        return res
    # failed now — but if we were connected very recently, treat it as a transient blip, stay green
    if _LAST_GOOD["res"] and (now - _LAST_GOOD["ts"] < _GOOD_TTL):
        out = dict(_LAST_GOOD["res"])
        out["reason"] = "connected"
        out["transient"] = True
        out["hint"] = "rechecking — a transient Azure CLI blip during a busy run (still connected)"
        return out
    return res
