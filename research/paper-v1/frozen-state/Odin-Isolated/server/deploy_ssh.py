"""SSH deploy channel — log in as the app user `mostafa` with the PASSWORD from workspace/shared/oth/.cred and run
EVERYTHING there (rsync, build, migrate, reboot). The Azure control plane is used ONLY to open the
firewall (ufw + NSG port-22 to the current IP); no app command ever runs as root via the control
plane. This mirrors the owner's own working deploy tool.

Password auth is FORCED (PubkeyAuthentication=no) so SSH doesn't fail with 'too many authentication
failures' by offering keys first.
"""
import os
import re
import shlex
import shutil
import subprocess
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CRED = ROOT / "workspace" / "shared" / "oth" / ".cred"
VM_USER = "mostafa"
VM_FALLBACK_IP = "52.180.154.225"

# Always-excluded secrets/junk (on top of the owner's list) — never synced.
SECRET_EXCLUDES = [".env*", ".backup-env", "*.pem", "*.key", "config/google-oauth-client.json",
                   "*.bak", "*.tmp", "*.copy", ".DS_Store"]


def vm_password() -> str | None:
    try:
        m = re.search(r"azvmcred\s*[:=]\s*(.+)", CRED.read_text())
        return m.group(1).strip() if m else None
    except Exception:
        return None


def vm_ip() -> str:
    try:
        import infra_az
        return infra_az.vm_public_ip() or VM_FALLBACK_IP
    except Exception:
        return VM_FALLBACK_IP


def refresh_firewall() -> dict:
    """The ONLY control-plane (root) use: open ufw + NSG to the owner's CURRENT public IP."""
    try:
        import infra_rotate
        return infra_rotate.rotate()
    except Exception as e:
        return {"ok": False, "error": str(e)}


def available() -> bool:
    return bool(vm_password()) and shutil.which("sshpass") is not None


def _opts() -> list:
    return ["-o", "PreferredAuthentications=password", "-o", "PubkeyAuthentication=no",
            "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=20"]


def ssh_exec(command: str, cwd: str | None = None, timeout: int = 1200) -> dict:
    """Run a command on the VM over SSH AS mostafa (password auth). Any `sudo` is converted to
    `sudo -S` and fed the password on stdin, so reboot/root steps work without a key."""
    pw = vm_password()
    if not pw:
        return {"ok": False, "error": "azvmcred not found in workspace/shared/oth/.cred"}
    if not shutil.which("sshpass"):
        return {"ok": False, "error": "sshpass not installed — run: brew install hudochenkov/sshpass/sshpass"}
    ip = vm_ip()
    body = (f"cd {shlex.quote(cwd)} && " if cwd else "") + command
    if re.search(r"\bsudo\b", body):
        body = re.sub(r"\bsudo\b", "sudo -S -p ''", body)
        remote = f"printf '%s\\n' {shlex.quote(pw)} | bash -lc {shlex.quote(body)}"
    else:
        remote = f"bash -lc {shlex.quote(body)}"
    cmd = ["sshpass", "-p", pw, "ssh"] + _opts() + [f"{VM_USER}@{ip}", remote]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {"ok": r.returncode == 0, "ip": ip, "ran_as": VM_USER,
                "out": (r.stdout or "")[-4000:], "err": (r.stderr or "")[-1500:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "ssh command timed out"}


def rsync_push(local_dir: str, vm_dest: str, excludes=None, delete: bool = False,
               dry_run: bool = False, timeout: int = 1800) -> dict:
    """rsync local → VM over SSH AS mostafa (password). Secret excludes always applied."""
    pw = vm_password()
    if not pw:
        return {"ok": False, "error": "azvmcred not found in workspace/shared/oth/.cred"}
    if not shutil.which("sshpass"):
        return {"ok": False, "error": "sshpass not installed — brew install hudochenkov/sshpass/sshpass"}
    ip = vm_ip()
    ssh = "ssh " + " ".join(_opts())
    # --checksum: decide what to transfer by CONTENT HASH, not mtime+size. Without it, rsync's quick
    # time/size check can wrongly SKIP a locally-changed file (the "files not updated on the VM" bug) —
    # checksum guarantees a changed file ALWAYS overwrites the old one on the VM.
    args = ["sshpass", "-p", pw, "rsync", "-az", "--checksum", "-e", ssh]
    if dry_run:
        args += ["-n", "--itemize-changes"]
    if delete:
        args += ["--delete"]
    for e in list(excludes or []) + SECRET_EXCLUDES:
        args += ["--exclude", e]
    args += [f"{os.path.expanduser(local_dir).rstrip('/')}/", f"{VM_USER}@{ip}:{vm_dest.rstrip('/')}/"]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
        return {"ok": r.returncode == 0, "ip": ip, "ran_as": VM_USER,
                "out": (r.stdout or "")[-6000:], "err": (r.stderr or "")[-1500:]}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "rsync timed out"}


def verify_sync(local_dir: str, vm_dest: str, excludes=None, timeout: int = 600) -> dict:
    """PROVE the VM content matches local at CONTENT level (line-level), not just 'missing files added'.
    Runs rsync in CHECKSUM + DRY-RUN + ITEMIZE mode: it lists every file whose CONTENT still differs
    between local and the VM. If that list is EMPTY, the previous push genuinely overwrote everything and
    the VM is byte-for-byte identical to local. If it is NON-empty, the update did NOT fully take (those
    files are still stale on the VM) — which is exactly the 'files not updated / only missing uploaded'
    failure. Returns {ok, pending:[paths], detail}."""
    pw = vm_password()
    if not pw:
        return {"ok": False, "error": "azvmcred not found in workspace/shared/oth/.cred"}
    if not shutil.which("sshpass"):
        return {"ok": False, "error": "sshpass not installed"}
    ip = vm_ip()
    ssh = "ssh " + " ".join(_opts())
    args = ["sshpass", "-p", pw, "rsync", "-az", "--checksum", "--dry-run", "--itemize-changes", "-e", ssh]
    for e in list(excludes or []) + SECRET_EXCLUDES:
        args += ["--exclude", e]
    args += [f"{os.path.expanduser(local_dir).rstrip('/')}/", f"{VM_USER}@{ip}:{vm_dest.rstrip('/')}/"]
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "verify rsync timed out"}
    pending = []
    for ln in (r.stdout or "").splitlines():
        ln = ln.rstrip()
        # itemize lines look like ">f.st...... path/to/file"; the leading token's 2nd char 'f' = a file
        # being (re)transferred. A trailing-only dir entry ('cd+++++++++ dir/') without file transfers is
        # fine. We count any FILE transfer as a still-pending content mismatch.
        if not ln or ln.startswith(("sending", "total", "sent ", "cannot", "rsync ", "created ", "delta", "speedup")):
            continue
        parts = ln.split(None, 1)
        if len(parts) == 2 and len(parts[0]) >= 2 and parts[0][1] == "f":
            pending.append(parts[1])
    ok = (r.returncode == 0) and not pending
    return {"ok": ok, "pending": pending[:50], "count": len(pending),
            "detail": ("VM content matches local exactly (no pending file transfers)" if ok
                       else f"{len(pending)} file(s) still differ on the VM — update did NOT fully overwrite"),
            "raw": (r.stdout or "")[-2000:]}


def _q(s: str) -> str:
    import shlex
    return shlex.quote(s)
