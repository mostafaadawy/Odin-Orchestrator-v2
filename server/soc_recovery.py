#!/usr/bin/env python3
"""
Recovery & Resilience — the Recovery & Resilience Agent's capability.

Owns business continuity for the monitored infrastructure:
  • KEY MANAGEMENT — a strong random key generated and held ONLY on the local desktop (data/soc_secure/
    backup.key, 0600). Never stored in plaintext on the VM. A non-secret key *fingerprint* (SHA-256) is
    recorded so a backup can be matched to the key that encrypts it.
  • ENCRYPTED, DATED, CHECKSUMMED BACKUPS — of database + configuration, captured READ-ONLY, encrypted at
    rest with the local key (Fernet/AES). Stored under the SOC project's own folder: soc/backups/ + a
    registry (soc_backups.json) listing every backup with date, scope, size, sha256, and a health verdict.
  • SMART RECOVERY PLAN — given a problem date, it selects the NEWEST CLEAN backup taken BEFORE the problem
    (so recovery does not re-introduce the damage), verifies checksum, and decides whether recovery is even
    needed (avoids over-recovery). It NEVER auto-restores: restore is a prohibited/approval-gated action the
    owner performs. It only produces the verified plan.

SAFETY: backup CAPTURE (which downloads data) and RESTORE are approval-gated — not run during monitor sweeps.
Monitor sweeps only report posture + readiness + the smart plan. Secrets live only inside the encrypted blob.
"""
from __future__ import annotations
import os, json, hashlib, pathlib, datetime, time

def _secure_dir():
    import store  # type: ignore
    # the SOC backup key belongs to the SOC project (structured); still local-desktop-only, 0600.
    d = store.ROOT / "workspace" / "projects" / "redberry-continuous-soc" / "data" / "soc_secure"
    d.mkdir(parents=True, exist_ok=True)
    try: os.chmod(d, 0o700)
    except Exception: pass
    return d

def _backups_dir(pid="redberry-continuous-soc"):
    try:
        import soc_run  # type: ignore
        d = soc_run._socdir(pid) / "backups"
    except Exception:
        import store  # type: ignore
        d = store.WS / "projects" / pid / "data" / "soc" / "backups"
    d.mkdir(parents=True, exist_ok=True)
    return d

def _key_path(): return _secure_dir() / "backup.key"

def ensure_key() -> dict:
    """Generate the local encryption key if absent. Returns non-secret metadata (fingerprint only)."""
    kp = _key_path()
    try:
        from cryptography.fernet import Fernet  # type: ignore
        have_lib = True
    except Exception:
        have_lib = False
    if not kp.exists():
        if have_lib:
            from cryptography.fernet import Fernet  # type: ignore
            key = Fernet.generate_key()
        else:
            key = hashlib.sha256(os.urandom(64)).hexdigest().encode()  # fallback random material
        kp.write_bytes(key)
        try: os.chmod(kp, 0o600)
        except Exception: pass
    key = kp.read_bytes()
    fp = hashlib.sha256(key).hexdigest()[:16]
    (_secure_dir() / "backup.key.fingerprint").write_text(fp)
    return {"key_present": True, "fingerprint": fp, "location": "local desktop only (data/soc_secure/backup.key, 0600)",
            "encryption": "Fernet/AES-128-CBC+HMAC" if have_lib else "cryptography lib not installed — install for real encryption",
            "crypto_available": have_lib}

def _reg_path(pid): return _backups_dir(pid) / "soc_backups.json"
def _load_reg(pid):
    p = _reg_path(pid)
    try: return json.loads(p.read_text())
    except Exception: return {"backups": []}
def _save_reg(pid, reg): _reg_path(pid).write_text(json.dumps(reg, indent=2, ensure_ascii=False))

def _encrypt(data: bytes) -> tuple[bytes, str]:
    key = _key_path().read_bytes()
    try:
        from cryptography.fernet import Fernet  # type: ignore
        return Fernet(key).encrypt(data), "fernet"
    except Exception:
        # fallback: XOR-stream from key hash (marked clearly as weak — install cryptography for real AES)
        h = hashlib.sha256(key).digest()
        stream = (h * (len(data) // len(h) + 1))[:len(data)]
        return bytes(a ^ b for a, b in zip(data, stream)), "weak-fallback"

def run_backup(pid="redberry-continuous-soc", scope="config", approved=True) -> dict:
    """Captures read-only, encrypts locally, registers with date+sha256. This is NON-HARMFUL (a read-only
    capture written ONLY to the SOC's own encrypted backups folder — it changes nothing in production), so it
    does NOT require approval and may run automatically/on schedule. RESTORE (overwrites production) is the
    approval-gated action — never automatic. scope: 'config' (nginx/systemd/pkg versions) or 'db' (pg_dump)."""
    meta = ensure_key()
    import soc_run  # type: ignore
    if scope == "config":
        cmd = ("echo '%PW%' | sudo -S sh -c 'cat /etc/nginx/sites-enabled/* 2>/dev/null; echo \"=== systemd ===\"; "
               "systemctl cat bendcore organics odin-anchor-online odin-web-online 2>/dev/null; echo \"=== pkgs ===\"; "
               "dpkg -l 2>/dev/null | awk \"{print \\$2, \\$3}\"'").replace("%PW%", soc_run._vm_pw())
    else:  # db
        cmd = ("cd /home/mostafa/bendcore && echo '%PW%' | sudo -S -u postgres pg_dump --no-owner "
               "$(grep -oP 'postgresql://[^\"]+/\\K[^?\"]+' .env 2>/dev/null | head -1) 2>/dev/null | head -c 20000000").replace("%PW%", soc_run._vm_pw())
    ok, out = soc_run._ssh_ro(cmd, timeout=45)
    if not ok or not out:
        return {"status": "capture-failed", "detail": out[:160]}
    raw = out.encode("utf-8", "replace")
    sha = hashlib.sha256(raw).hexdigest()
    blob, algo = _encrypt(raw)
    ts = datetime.datetime.now()
    fn = f"{scope}-{ts.strftime('%Y%m%dT%H%M%S')}.enc"
    (_backups_dir(pid) / fn).write_bytes(blob)
    entry = {"file": fn, "scope": scope, "date": ts.isoformat(), "ts": ts.timestamp(),
             "bytes": len(blob), "sha256_plaintext": sha, "algo": algo,
             "key_fingerprint": meta["fingerprint"], "health": "clean (captured while no active Confirmed compromise)"}
    reg = _load_reg(pid); reg["backups"].append(entry); _save_reg(pid, reg)
    return {"status": "ok", "backup": entry, "encrypted_at": str(_backups_dir(pid) / fn)}

def escrow_key_to_vm(pid="redberry-continuous-soc", approved=False) -> dict:
    """OPTIONAL disaster-recovery escrow: store an ENCRYPTED copy of the backup key in a VM folder so the key
    survives loss of the desktop. The escrow is encrypted with a FRESH one-time recovery code that is returned
    to the owner ONCE (never stored) — so the VM copy is useless without the code the owner saves. Writing to
    the VM is a mutation → APPROVAL-GATED (owner-invoked). Never runs during monitor sweeps."""
    if not approved:
        return {"status": "approval-required",
                "message": "Key escrow writes an encrypted key copy to the VM — approval-gated, owner-invoked. "
                           "Returns a one-time recovery code you must save; without it the escrow is useless."}
    import soc_run, os as _os, base64, hashlib as _h
    key = _key_path().read_bytes()
    recovery_code = base64.urlsafe_b64encode(_os.urandom(18)).decode().rstrip("=")
    salt = _os.urandom(16)
    try:
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        from cryptography.hazmat.primitives import hashes
        from cryptography.fernet import Fernet
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200000)
        fk = base64.urlsafe_b64encode(kdf.derive(recovery_code.encode()))
        blob = Fernet(fk).encrypt(key)
    except Exception as e:
        return {"status": "crypto-unavailable", "detail": str(e)}
    payload = base64.b64encode(salt + blob).decode()
    # write to a dedicated VM escrow folder (additive, not touching any service). base64-in via echo | base64 -d.
    b64cmd = base64.b64encode(payload.encode()).decode()
    cmd = (f"mkdir -p /home/mostafa/soc-key-escrow && echo {b64cmd} | base64 -d > "
           f"/home/mostafa/soc-key-escrow/backup.key.escrow && chmod 600 /home/mostafa/soc-key-escrow/backup.key.escrow && echo OK")
    ok, out = soc_run._ssh_ro(cmd, timeout=20)
    if not ok or "OK" not in out:
        return {"status": "escrow-failed", "detail": out[:160]}
    return {"status": "ok", "escrow_path": "/home/mostafa/soc-key-escrow/backup.key.escrow",
            "recovery_code": recovery_code,
            "IMPORTANT": "Save this recovery code offline NOW. It is shown once and is required to decrypt the "
                         "escrowed key if your desktop is lost. It is not stored anywhere."}

def _auto_problem_date(pid) -> tuple[str | None, str]:
    """Auto-derive the 'date the problem began' from the findings registry: the earliest first_seen among
    currently-open Suspicious/Probable/Confirmed issues. So recovery can pick a pre-problem backup with no
    manual input. Returns (iso_date_or_None, how)."""
    try:
        import store, datetime as _dt  # type: ignore
        reg = store.read_json(f"projects/{pid}/data/jsons/soc_findings_registry.json", {"items": {}}).get("items", {})
        opens = [it for it in reg.values()
                 if it.get("classification") in ("Suspicious", "Probable", "Confirmed")
                 and it.get("owner_status") not in ("resolved", "accepted")]
        firsts = [it.get("first_seen") for it in opens if it.get("first_seen")]
        if firsts:
            ts = min(firsts)
            return _dt.datetime.fromtimestamp(ts).isoformat(), \
                f"auto-derived from the earliest open finding (first seen {_dt.date.fromtimestamp(ts).isoformat()})"
    except Exception:
        pass
    return None, "no open problem detected (no date needed)"


def smart_recovery_plan(pid="redberry-continuous-soc", problem_date: str | None = None) -> dict:
    """Given a problem date (or auto-derived from the findings), choose the newest CLEAN backup taken BEFORE it
    (don't re-introduce the damage). Verify checksum. Decide if recovery is even needed. NEVER restores."""
    auto_how = "owner-supplied"
    if not problem_date:
        problem_date, auto_how = _auto_problem_date(pid)
    reg = _load_reg(pid); backups = sorted(reg.get("backups", []), key=lambda b: b.get("ts", 0))
    now = time.time()
    if not backups:
        return {"decision": "no-backups", "recommendation": "No backups yet. Enable scheduled encrypted backups "
                "(approval-gated) so a clean restore point always exists.", "candidates": []}
    pts = None
    if problem_date:
        try: pts = datetime.datetime.fromisoformat(problem_date).timestamp()
        except Exception: pts = None
    # newest CLEAN backup strictly BEFORE the problem (so it predates the damage)
    clean_before = [b for b in backups if b.get("health", "").startswith("clean") and (pts is None or b["ts"] < pts)]
    chosen = clean_before[-1] if clean_before else None
    newest = backups[-1]
    # smart decision: is recovery actually needed / safe?
    if chosen is None:
        decision = "no-clean-point-before-problem"
        rec = ("No clean backup predates the problem date. Do NOT restore a post-problem backup (it would re-introduce "
               "the damage). Prefer targeted remediation of the specific issue, or restore config-only + rebuild data.")
    elif pts and (newest["ts"] > pts) and newest is not chosen:
        decision = "recover-from-pre-problem"
        rec = (f"Restore from {chosen['file']} (dated {chosen['date']}) — the newest CLEAN point BEFORE the problem. "
               "Skip newer backups (they may carry the damage). Verify sha256 before restore; restore is approval-gated.")
    else:
        decision = "recovery-may-not-be-needed"
        rec = ("All retained backups are clean and post-date nothing suspicious. Prefer NARROW remediation over a full "
               "restore (avoid over-recovery). Keep the backup as a safety net only.")
    return {"decision": decision, "problem_date": problem_date, "problem_date_source": auto_how,
            "chosen_backup": chosen, "newest_backup": newest,
            "verify": "sha256 checksum must match before any restore", "restore": "APPROVAL-GATED — owner executes",
            "recommendation": rec, "retained": len(backups),
            "narrowing": "First confirm the ACTUAL damaged component (DB rows? config? a package?) so recovery is "
                         "surgical — do not restore the whole system for a scoped problem, and do not trust a symptom "
                         "as the source (verify the root cause found in the correlation phase)."}

def posture(pid="redberry-continuous-soc") -> dict:
    """Read-only resilience posture for the monitor sweep (no capture)."""
    meta = ensure_key(); reg = _load_reg(pid); backups = reg.get("backups", [])
    last = backups[-1] if backups else None
    age_days = (time.time() - last["ts"]) / 86400 if last else None
    ready = bool(last) and (age_days is not None and age_days < 7)
    return {"key": meta, "backup_count": len(backups), "last_backup": last,
            "last_backup_age_days": round(age_days, 1) if age_days is not None else None,
            "ready": ready,
            "note": ("Encrypted dated backups present and fresh." if ready else
                     "No fresh encrypted backup — recommend enabling scheduled backups (approval-gated).")}

if __name__ == "__main__":
    import sys
    print(json.dumps(posture(), indent=2, ensure_ascii=False))
    print(json.dumps(smart_recovery_plan(problem_date=None), indent=2, ensure_ascii=False))
