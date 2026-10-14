#!/usr/bin/env python3
"""odin_secrets.py — v2 owner-secret provisioning (F-14 Keychain) + Anchor key/password rotation.

  python3 server/odin_secrets.py keychain          # copy the Anchor key (+ manage email/password) into the macOS Keychain
  python3 server/odin_secrets.py rotate            # NEW random Anchor API key + NEW random Manage password (no prompt),
                                           # .cred backed up first, then the Keychain is refreshed
  python3 server/odin_secrets.py rotate-vm         # NEW VM login password via Azure, proven by SSH before .cred changes
  python3 server/odin_secrets.py status            # present / missing only — never a value

Rules: no secret is ever printed or logged; Keychain writes pass the value to `security add-generic-password -w`
(its documented interface, visible only to the owner's own user for the instant it runs); .cred keeps mode 600;
a timestamped backup is written before any change.
The Keychain service/accounts match desktop/electron/secrets.cjs: service "odin-anchor", accounts
"anchor-key", "manage-email", "manage-password".
"""
from __future__ import annotations

import hashlib
import os
import pathlib
import secrets
import shutil
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
CRED = ROOT / "workspace" / "shared" / "oth" / ".cred"
SERVICE = "odin-anchor"
DEF_EMAIL = "tech@odinmarkets.com"


def _read() -> list[str]:
    return CRED.read_text(encoding="utf-8").splitlines() if CRED.exists() else []


def _get(lines: list[str], key: str) -> str:
    for raw in lines:
        s = raw.strip()
        if s.startswith(key + "="):
            return s.split("=", 1)[1].strip().strip('"')
    return ""


def _set(lines: list[str], key: str, val: str) -> list[str]:
    out, done = [], False
    for raw in lines:
        if raw.strip().startswith(key + "=") and not done:
            out.append(f"{key}={val}"); done = True
        else:
            out.append(raw)
    if not done:
        out.append(f"{key}={val}")
    return out


def _write(lines: list[str]) -> None:
    if CRED.exists():
        bak = CRED.with_name(f".cred.bak_rotate_{time.strftime('%Y%m%d_%H%M%S')}_{time.time_ns() % 1000000:06d}")
        shutil.copy2(CRED, bak); os.chmod(bak, 0o600)
    CRED.parent.mkdir(parents=True, exist_ok=True)
    CRED.write_text("\n".join(lines) + "\n", encoding="utf-8"); os.chmod(CRED, 0o600)


def _kc_has(acct: str) -> bool:
    return subprocess.run(["security", "find-generic-password", "-s", SERVICE, "-a", acct],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0


def _kc_put(acct: str, val: str) -> bool:
    if not val:
        return False
    r = subprocess.run(["security", "add-generic-password", "-U", "-s", SERVICE, "-a", acct, "-w", val],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return r.returncode == 0


def _in_test_clone() -> bool:
    # the isolated test clone must never write the owner's real macOS Keychain
    return "_v2/iso_root" in str(ROOT) or os.environ.get("ODIN_NO_KEYCHAIN") == "1"


def _new_manage_password() -> str:
    return secrets.token_urlsafe(18)          # 24 random characters; never shown, never typed


def ensure_manage_password(lines: list[str]) -> tuple[list[str], bool]:
    """v1 parity without a plaintext in the app bundle: the Manage password lives in the owner's LOCAL .cred
    (ANCHOR_MANAGE_PASSWORD — never deployed; only its hash ANCHOR_MANAGE_PWSHA goes to the VM). If it is not
    there yet, one is generated automatically. Returns (lines, changed)."""
    pw = _get(lines, "ANCHOR_MANAGE_PASSWORD")
    sha = _get(lines, "ANCHOR_MANAGE_PWSHA")
    if pw and sha == hashlib.sha256(pw.encode()).hexdigest():
        return lines, False
    if not pw:
        pw = _new_manage_password()
        lines = _set(lines, "ANCHOR_MANAGE_PASSWORD", pw)
    lines = _set(lines, "ANCHOR_MANAGE_PWSHA", hashlib.sha256(pw.encode()).hexdigest())
    return lines, True


def keychain() -> int:
    """Copy the local values into the Keychain for the desktop app. NEVER prompts."""
    lines = _read()
    lines, changed = ensure_manage_password(lines)
    if changed:
        _write(lines)
        print("  ✓ Manage password generated and saved in the local .cred (backup kept; only its hash is ever deployed)")
    if _in_test_clone():
        print("  (test clone — Keychain not touched)"); return 0
    key = _get(lines, "ANCHOR_API_KEY")
    email = (_get(lines, "ANCHOR_MANAGE_EMAIL") or DEF_EMAIL).lower()
    ok_key = _kc_put("anchor-key", key)
    ok_mail = _kc_put("manage-email", email)
    ok_pw = _kc_put("manage-password", _get(lines, "ANCHOR_MANAGE_PASSWORD"))
    print(f"  Keychain [{SERVICE}]  anchor-key: {'stored' if ok_key else 'MISSING (no ANCHOR_API_KEY in .cred)'}"
          f" · manage-email: {'stored' if ok_mail else 'MISSING'} · manage-password: {'stored' if ok_pw else 'MISSING'}")
    return 0 if (ok_key and ok_pw) else 1


def rotate() -> int:
    """Cutover: NEW random Anchor API key + NEW random Manage password, both generated here and saved in the
    local .cred (timestamped backup first), then the Keychain. No prompt; no value is shown."""
    lines = _read()
    lines = _set(lines, "ANCHOR_API_KEY", secrets.token_urlsafe(32))
    lines = _set(lines, "ANCHOR_MANAGE_PASSWORD", _new_manage_password())
    lines, _ = ensure_manage_password(lines)
    _write(lines)
    print("  ✓ Anchor API key + Manage password rotated and saved locally (.cred backed up) — "
          "the VM receives the key and the password HASH on this deploy.")
    return keychain()


def rotate_odin() -> int:
    """NEW random ODIN_API_KEY (X-API-Key of the local /api/v1 external API), generated here and saved in the
    local .cred (timestamped backup first). No prompt; no value is shown. Read per request, so no restart."""
    lines = _read()
    old = _get(lines, "ODIN_API_KEY")
    new = secrets.token_urlsafe(30)
    _write(_set(lines, "ODIN_API_KEY", new))
    ok = _get(_read(), "ODIN_API_KEY") == new and new != old
    print("  " + ("✓ Odin API key rotated and saved locally (.cred backed up)" if ok else "✗ Odin API key NOT rotated"))
    return 0 if ok else 1


def _vm_line_set(lines: list[str], pw: str) -> list[str]:
    out, done = [], False
    for raw in lines:
        if raw.strip().startswith("azvmcred") and not done:
            sep = ":" if ":" in raw.split("azvmcred", 1)[1][:3] else "="
            out.append(f"azvmcred{sep} {pw}" if sep == ":" else f"azvmcred={pw}"); done = True
        else:
            out.append(raw)
    if not done:
        out.append(f"azvmcred: {pw}")
    return out


def rotate_vm() -> int:
    """Cutover (owner condition E): NEW password for the VM login user, set out-of-band by Azure
    (`az vm user update`, which also works if SSH fails), then PROVEN by a fresh SSH login with the new value; only then
    is .cred updated. If the proof fails, the OLD password is put back the same way. Values are never printed."""
    import string
    sys.path.insert(0, str(ROOT / "server"))
    import deploy_ssh, infra_az
    old = deploy_ssh.vm_password()
    if not old:
        print("  ✗ no VM credential line in .cred — nothing to rotate"); return 1
    rg, vm = infra_az.discover_rg(), infra_az.vm_name()
    if not rg or not vm:
        print("  ✗ Azure VM / resource group not found (is `az login` done?)"); return 1
    az = infra_az._az_bin() or "az"
    new = "".join(secrets.choice(string.ascii_letters + string.digits) for _ in range(28))
    def az_set(pw: str) -> bool:
        r = subprocess.run([az, "vm", "user", "update", "-g", rg, "-n", vm, "-u", deploy_ssh.VM_USER, "-p", pw, "-o", "none"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
        return r.returncode == 0
    def login_ok(pw: str) -> bool:
        real = deploy_ssh.vm_password
        deploy_ssh.vm_password = lambda: pw
        try:
            return "ok" in (deploy_ssh.ssh_exec("echo ok", timeout=60).get("out") or "")
        finally:
            deploy_ssh.vm_password = real
    try:
        deploy_ssh.refresh_firewall()
    except Exception:
        pass
    if not az_set(new):
        print("  ✗ Azure refused the password update — NOTHING changed (old password still valid)"); return 1
    if login_ok(new):
        _write(_vm_line_set(_read(), new))
        print("  ✓ VM password rotated (Azure) and proven by a fresh SSH login; .cred updated (backup kept)")
        return 0
    print("  ✗ new VM password did not log in — restoring the old one")
    ok = az_set(old) and login_ok(old)
    print("  " + ("✓ old password restored and proven" if ok else "✗ RESTORE FAILED — use the Azure portal: VM > Reset password"))
    return 1


def status() -> int:
    lines = _read()
    for k in ("ANCHOR_API_KEY", "ANCHOR_MANAGE_PASSWORD", "ANCHOR_MANAGE_PWSHA", "ODIN_API_KEY"):
        print(f"  .cred {k}: {'present' if _get(lines, k) else 'missing'}")
    for a in ("anchor-key", "manage-email", "manage-password"):
        print(f"  Keychain {a}: {'present' if _kc_has(a) else 'missing'}")
    return 0


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    sys.exit({"keychain": keychain, "rotate": rotate, "rotate-vm": rotate_vm, "rotate-odin": rotate_odin, "status": status}.get(cmd, status)())
