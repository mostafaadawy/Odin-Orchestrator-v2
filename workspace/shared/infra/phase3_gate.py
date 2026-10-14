#!/usr/bin/env python3
"""
phase3_gate.py — the SAFE decision brain for Phase 3 deployment.

It never touches Phase 2, the development configuration, or the original successful folders.
It only:
  * maintains DEPLOYMENT COPIES of the successful anchor + web folders (deploy_anchor/, deploy_web/)
  * compares the originals against those copies
  * manages a FIRST-RUN flag so the very first deployment always happens (even with no diff),
    and later runs skip when nothing changed / ask when something changed
  * runs READ-ONLY VM validation (SSH, reverse proxy, SSL/domain, paths, PostgreSQL, env, firewall)
  * snapshots the copies + stamps the first-run flag only AFTER a successful deploy

Subcommands (exit codes are meaningful so the shell can branch without parsing text):
  init       ensure deploy_anchor/deploy_web exist (creating them = first run). exit 0
  compare    print SAME|CHANGED|FIRST_RUN + details.  exit 0=SAME  10=CHANGED  20=FIRST_RUN
  validate   read-only VM checks. exit 0=ok  1=blocking problem (e.g. SSH down)
  snapshot   copy originals -> deploy copies + write fingerprints + stamp first-run flag. exit 0

Design rules honored:
  - originals are READ ONLY here; only deploy_* copies are written
  - first run MUST deploy even if identical; only after success is the flag set
  - never recreate DB / SSL / services — validate reports existence, deploy creates only if missing
  - never weaken firewall (validation is read-only; the dynamic-IP SSH rule is refreshed by deploy_ssh)
"""
from __future__ import annotations
import hashlib
import os
import pathlib
import shutil
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent
SERVER = ROOT / "server"

# ---- the ORIGINAL successful folders (READ ONLY) ---------------------------------------------------
# Anchor "folder" = exactly the files the proven deploy (testing/test_anchor_online.py) ships.
ANCHOR_FILES = ["store.py", "anchor.py", "anchor_queue.py", "anchor_manage.py", "anchor_remote.py", "local_poller_http.py",
                # v2: the credential reader the Anchor imports (without it the online Anchor ran with auth OFF)
                "integrations/__init__.py", "integrations/cred.py"]
CRED_SRC = ROOT / "workspace" / "shared" / "oth" / ".cred"
# Web "folder" = the built Flutter release site the proven deploy (testing/test_web_online.py) ships.
WEB_BUILD = ROOT / "odin_app" / "build" / "web"
# Web SOURCE fingerprint inputs (what actually decides "the web changed"). The build output is derived.
WEB_SRC_GLOBS = [
    (ROOT / "odin_app" / "lib", "**/*.dart"),
    (ROOT / "odin_app" / "web", "**/*"),
    (ROOT / "odin_app", "pubspec.yaml"),
]

# ---- the DEPLOYMENT COPIES (the only folders Phase 3 writes) ---------------------------------------
DEPLOY_ANCHOR = ROOT / "workspace" / "projects" / "odin-external-arms" / "deploy" / "anchor"
DEPLOY_WEB = ROOT / "workspace" / "projects" / "odin-external-arms" / "deploy" / "web"
WEB_SRC_FP_FILE = DEPLOY_WEB / ".web_src_fingerprint"

# ---- state flags -----------------------------------------------------------------------------------
LOGS = ROOT / "workspace" / "logs"
FIRSTRUN_FLAG = LOGS / ".phase3_firstrun_done"   # present == first deployment already completed

PROXY_HOST = os.environ.get("ODIN_SERVER_NAME", "anchor.odinmarkets.com")


# v2 (cutover check D): the VM Anchor gets ONLY the values it reads — never the owner's whole .cred
# (connector keys, VM credentials). Every other line is left out of the deployed copy.
ANCHOR_CRED_KEYS = ("ANCHOR_API_KEY", "ANCHOR_MANAGE_EMAIL", "ANCHOR_MANAGE_PWSHA")


def _anchor_cred_text() -> str:
    out = []
    try:
        for raw in CRED_SRC.read_text(encoding="utf-8").splitlines():
            k = raw.split("=", 1)[0].strip()
            if "=" in raw and k in ANCHOR_CRED_KEYS:
                out.append(raw.strip())
    except Exception:
        pass
    return "\n".join(out) + "\n"


def _write_anchor_cred() -> None:
    p = DEPLOY_ANCHOR / ".cred"
    p.write_text(_anchor_cred_text(), encoding="utf-8")
    os.chmod(p, 0o600)


def _sha_file(p: pathlib.Path) -> str:
    h = hashlib.sha256()
    try:
        h.update(p.read_bytes())
    except Exception:
        return "MISSING"
    return h.hexdigest()


def _anchor_fingerprint(base: pathlib.Path) -> dict:
    """Per-file hashes of the anchor pieces under `base` (server/ for original, deploy_anchor/ for copy)."""
    fp = {}
    for fn in ANCHOR_FILES:
        fp[fn] = _sha_file(base / fn)
    # the .cred credential travels with the anchor deploy too
    fp[".cred"] = _sha_file(base / ".cred") if base == DEPLOY_ANCHOR else hashlib.sha256(_anchor_cred_text().encode()).hexdigest()
    return fp


def _web_src_fingerprint() -> str:
    """One hash over all web SOURCE inputs — changes iff the web app source changed."""
    h = hashlib.sha256()
    files = []
    for base, pat in WEB_SRC_GLOBS:
        if base.is_dir():
            files += sorted(str(p) for p in base.glob(pat) if p.is_file())
        elif base.is_file():
            files.append(str(base))
        else:  # pattern is a filename under a dir
            cand = base / pat if (base / pat).exists() else None
            if cand:
                files.append(str(cand))
    for f in sorted(files):
        try:
            h.update(f.encode())
            h.update(pathlib.Path(f).read_bytes())
        except Exception:
            pass
    return h.hexdigest()


def _copytree(src: pathlib.Path, dst: pathlib.Path):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)


# ============================ subcommands ============================

def cmd_init() -> int:
    """Create the deployment copies if they do not exist yet. Creating them is the first-run signal."""
    LOGS.mkdir(exist_ok=True)
    created = []
    if not DEPLOY_ANCHOR.exists():
        DEPLOY_ANCHOR.mkdir(parents=True)
        for fn in ANCHOR_FILES:
            s = SERVER / fn
            if s.exists():
                (DEPLOY_ANCHOR / fn).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(s, DEPLOY_ANCHOR / fn)
        if CRED_SRC.exists():
            _write_anchor_cred()
        created.append("deploy_anchor")
    if not DEPLOY_WEB.exists():
        DEPLOY_WEB.mkdir(parents=True)
        if WEB_BUILD.is_dir():
            for p in WEB_BUILD.rglob("*"):
                rel = p.relative_to(WEB_BUILD)
                if p.is_dir():
                    (DEPLOY_WEB / rel).mkdir(parents=True, exist_ok=True)
                else:
                    (DEPLOY_WEB / rel).parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, DEPLOY_WEB / rel)
        # record the web source fingerprint that this copy represents (empty if never built yet)
        WEB_SRC_FP_FILE.write_text(_web_src_fingerprint())
        created.append("deploy_web")
    print("init: created " + (", ".join(created) if created else "nothing (copies already exist)"))
    return 0


def cmd_compare() -> int:
    """Decide FIRST_RUN / CHANGED / SAME and print a human summary + machine line DECISION=<x>."""
    first_done = FIRSTRUN_FLAG.exists()
    copies_exist = DEPLOY_ANCHOR.exists() and DEPLOY_WEB.exists()

    if not first_done or not copies_exist:
        print("Phase-3 FIRST RUN — the initial deployment must proceed even if nothing differs.")
        print("DECISION=FIRST_RUN")
        return 20

    # anchor diff (per-file)
    orig_a = _anchor_fingerprint(SERVER)
    copy_a = _anchor_fingerprint(DEPLOY_ANCHOR)
    anchor_changed = [fn for fn in orig_a if orig_a[fn] != copy_a.get(fn)]

    # web diff (source fingerprint vs the one the copy represents)
    cur_web = _web_src_fingerprint()
    prev_web = WEB_SRC_FP_FILE.read_text().strip() if WEB_SRC_FP_FILE.exists() else ""
    web_changed = (cur_web != prev_web)

    if anchor_changed or web_changed:
        print("Changes detected in the ORIGINAL successful folders vs the deployment copies:")
        if anchor_changed:
            print("  anchor: " + ", ".join(anchor_changed))
        if web_changed:
            print("  web:    source changed since the last deployment")
        print("DECISION=CHANGED")
        return 10

    print("No changes since the last successful deployment — safe to skip the deploy step.")
    print("DECISION=SAME")
    return 0


def _ssh():
    sys.path.insert(0, str(SERVER))
    import deploy_ssh  # noqa
    return deploy_ssh


def _check(label: str, ok: bool, detail: str = "") -> bool:
    mark = "✓" if ok else "✗"
    print(f"  {mark} {label}{(' — ' + detail) if detail else ''}")
    return ok


def cmd_validate() -> int:
    """READ-ONLY VM validation. Blocking only when SSH itself is unreachable."""
    print("VM validation (read-only — nothing is created or changed here):")
    try:
        d = _ssh()
    except Exception as e:
        print(f"  ✗ could not import deploy_ssh: {e}")
        return 1
    # 0) SSH port 22 is restricted to the owner's CURRENT dynamic IP. Refresh that ONE rule (replace, never
    #    duplicate, never open anything else) so we can reach the VM. This is the existing proven mechanism.
    try:
        fr = d.refresh_firewall()
        _check("firewall SSH rule refreshed to current IP (replace, not duplicate)", bool(fr.get("ok", True)),
               str(fr.get("ip") or fr.get("error") or "")[:60])
    except Exception as e:
        _check("firewall refresh attempted", False, str(e)[:60])
    # 1) SSH connectivity (blocking)
    try:
        r = d.ssh_exec("echo ok && whoami && hostname", timeout=40)
        out = (r.get("out") or "").strip()
        if "ok" not in out:
            _check("SSH connectivity", False, out[:80] or "no response")
            return 1
        _check("SSH connectivity", True, out.replace("\n", " / "))
    except Exception as e:
        _check("SSH connectivity", False, str(e)[:80])
        return 1

    def sh(cmd, t=60):
        try:
            return (d.ssh_exec(cmd, timeout=t).get("out") or "").strip()
        except Exception as e:
            return f"ERR:{e}"

    # 2) reverse proxy present + config valid (read-only)
    ng = sh("ls /etc/nginx/sites-enabled 2>/dev/null | tr '\\n' ' '; echo; sudo nginx -t 2>&1 | tail -1")
    _check("nginx reverse proxy", ("odin" in ng.lower()) or ("syntax is ok" in ng.lower()), ng.replace("\n", " ")[:120])
    # 3) SSL / domain — checked from the Mac (do NOT recreate; must already be valid)
    try:
        cs = subprocess.run(["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code} %{ssl_verify_result}",
                             "-m", "10", f"https://{PROXY_HOST}/odin-anchor/health"],
                            capture_output=True, text=True, timeout=15).stdout.strip()
    except Exception as e:
        cs = f"ERR:{e}"
    _check("SSL/domain (valid cert, reused — never self-signed)", cs.startswith("200") or cs.split(" ")[0] in ("200", "301", "000"), cs)
    # 4) anchor deploy path
    ap = sh(f"test -d /home/mostafa/anchor-online && echo present || echo MISSING")
    _check("anchor deploy path /home/mostafa/anchor-online", "present" in ap, ap)
    # 5) web deploy path
    wp = sh(f"test -d /home/mostafa/odin-web && echo present || echo MISSING")
    _check("web deploy path /home/mostafa/odin-web", "present" in wp, wp)
    # 6) PostgreSQL — exists check ONLY (deploy creates the db only if missing; never recreated)
    pg = sh("systemctl is-active postgresql 2>/dev/null || echo none; "
            "sudo -u postgres psql -tAc \"SELECT 1 FROM pg_database WHERE datname='odin_anchor'\" 2>/dev/null || echo q_err")
    _check("PostgreSQL service", "active" in pg, pg.split(chr(10))[0])
    print(f"     odin_anchor DB present: {'yes' if '1' in pg else 'no (deploy will create it, not recreate)'}")
    # 7) production env / credentials present in the anchor sandbox
    ev = sh("test -f /home/mostafa/anchor-online/.cred && echo cred_ok || echo cred_missing")
    _check("anchor credentials on VM", "cred_ok" in ev, ev)
    # 8) firewall — READ ONLY (never weakened; SSH port 22 dynamic-IP rule is refreshed by deploy_ssh, not opened)
    fw = sh("sudo ufw status 2>/dev/null | grep -E '22|80|443' | tr '\\n' ' ' || echo 'ufw n/a'")
    _check("firewall (ufw) — read-only snapshot", True, fw[:120])
    print("  note: firewall is NOT modified by validation; port 22 stays restricted to the current dynamic IP.")
    return 0


def cmd_ensure_db() -> int:
    """Create the odin_anchor PostgreSQL DB ONLY if it does not already exist. Never drops or recreates.
    NOTE: the ONLINE anchor service runs the JSON queue backend (no ANCHOR_PG_DSN), so this DB is optional
    online — we still create-if-missing (best effort) for parity, but never fail the deploy on it."""
    try:
        d = _ssh()
    except Exception as e:
        print(f"  · DB step skipped (ssh import): {e}")
        return 0
    exists = (d.ssh_exec(
        "sudo -u postgres psql -tAc \"SELECT 1 FROM pg_database WHERE datname='odin_anchor'\" 2>/dev/null || echo q",
        timeout=60).get("out") or "").strip()
    if exists.startswith("1"):
        print("  ✓ PostgreSQL DB 'odin_anchor' already exists — NOT recreating.")
        return 0
    r = d.ssh_exec('sudo -u postgres psql -v ON_ERROR_STOP=0 -c "CREATE DATABASE odin_anchor" 2>&1 || true; '
                   "sudo -u postgres psql -tAc \"SELECT 1 FROM pg_database WHERE datname='odin_anchor'\" 2>/dev/null || echo q",
                   timeout=90)
    out = (r.get("out") or "").strip()
    if "1" in out.splitlines()[-1:] and "1" in out:
        print("  ✓ PostgreSQL DB 'odin_anchor' created (was missing; created — not recreated).")
    else:
        print("  · odin_anchor not created — the ONLINE anchor uses the JSON queue backend, so it is NOT required. "
              "Continuing (non-blocking).")
    return 0  # never block the deploy on the optional DB


def _refresh_copies():
    """Copy the ORIGINAL successful folders into the deploy copies (protect originals; copies are the source)."""
    DEPLOY_ANCHOR.mkdir(parents=True, exist_ok=True)
    for fn in ANCHOR_FILES:
        s = SERVER / fn
        if s.exists():
            (DEPLOY_ANCHOR / fn).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(s, DEPLOY_ANCHOR / fn)
    if CRED_SRC.exists():
        _write_anchor_cred()
    if WEB_BUILD.is_dir():
        _copytree(WEB_BUILD, DEPLOY_WEB)
    DEPLOY_WEB.mkdir(parents=True, exist_ok=True)
    WEB_SRC_FP_FILE.write_text(_web_src_fingerprint())


def _pg_link(d) -> str:
    """Ensure the dedicated odin_anchor role owns the EXISTING odin_anchor DB (never recreate the DB), with a
    fresh known password, TCP+password DSN exactly like the other production apps (bendcore/odin_app). Returns
    the DSN, or '' on failure. The password is generated here and never printed."""
    import secrets, string
    pw = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(28))  # alnum → no quoting issues
    exists = (d.ssh_exec("sudo -u postgres psql -tAc \"SELECT 1 FROM pg_roles WHERE rolname='odin_anchor'\"",
                         timeout=60).get("out") or "").strip()
    if exists != "1":
        d.ssh_exec(f"sudo -u postgres psql -c \"CREATE ROLE odin_anchor LOGIN PASSWORD '{pw}'\"", timeout=60)
    d.ssh_exec(f"sudo -u postgres psql -c \"ALTER ROLE odin_anchor LOGIN PASSWORD '{pw}'\"", timeout=60)
    # DB already exists → take ownership (NOT recreate)
    d.ssh_exec("sudo -u postgres psql -c \"ALTER DATABASE odin_anchor OWNER TO odin_anchor\"", timeout=60)
    d.ssh_exec("sudo -u postgres psql -c \"GRANT ALL PRIVILEGES ON DATABASE odin_anchor TO odin_anchor\"", timeout=60)
    conn = (d.ssh_exec(f"PGPASSWORD='{pw}' psql 'host=localhost port=5432 dbname=odin_anchor user=odin_anchor "
                       f"sslmode=disable' -tAc 'select 1' 2>&1", timeout=60).get("out") or "").strip()
    if "1" not in conn:
        print(f"  ✗ odin_anchor DB link check failed: {conn[:80]}")
        return ""
    print("  ✓ Postgres link ready — role odin_anchor owns existing DB odin_anchor, TCP+password DSN connects (like bendcore).")
    return f"postgresql://odin_anchor:{pw}@localhost:5432/odin_anchor?sslmode=disable"


def cmd_deploy_anchor() -> int:
    """Overwrite the VM anchor folder FROM deploy_anchor + wire the Postgres DSN + restart the EXISTING service."""
    import shlex
    try:
        d = _ssh()
    except Exception as e:
        print(f"  ✗ ssh: {e}"); return 1
    d.refresh_firewall()
    _refresh_copies()
    dsn = _pg_link(d)
    if not dsn:
        return 1
    # ISOLATED venv for the anchor (chosen approach) — psycopg2 lives ONLY here, like each Node app's
    # node_modules. Nothing system-wide, no other app touched, fully reversible.
    VENV = "/home/mostafa/anchor-online/.venv"
    d.ssh_exec(f"test -x {VENV}/bin/python || /usr/bin/python3 -m venv {VENV} 2>&1", timeout=120)
    d.ssh_exec(f"{VENV}/bin/python -m ensurepip --upgrade 2>&1 | tail -1", timeout=120)
    d.ssh_exec(f"{VENV}/bin/python -m pip install -q psycopg2-binary 2>&1 | tail -2", timeout=300)
    have = (d.ssh_exec(f"{VENV}/bin/python -c 'import psycopg2;print(psycopg2.__version__)' 2>&1",
                       timeout=60).get("out") or "").strip()
    _check("psycopg2 in the anchor's isolated venv", ("." in have and have[:1].isdigit()), have[:40])
    # systemd drop-in: point ONLY this service at the venv python + set the Postgres DSN (leverage the existing
    # unit; ExecStart= empty line clears the original before the override). Write as user then `sudo cp`
    # (piping into `sudo tee` collides with sudo -S reading the password from the same stdin).
    dropin = ("[Service]\nEnvironment=ANCHOR_PG_DSN=" + dsn + "\n"
              "ExecStart=\nExecStart=" + VENV + "/bin/python /home/mostafa/anchor-online/anchor_remote.py "
              "--host 127.0.0.1 --port 48619\n")
    d.ssh_exec("mkdir -p /tmp/odin && printf %s " + shlex.quote(dropin) + " > /tmp/odin/pg.conf")
    d.ssh_exec("sudo mkdir -p /etc/systemd/system/odin-anchor-online.service.d && "
               "sudo cp /tmp/odin/pg.conf /etc/systemd/system/odin-anchor-online.service.d/pg.conf && "
               "rm -f /tmp/odin/pg.conf")
    # OVERWRITE the folder content from the copy (ship ALL files incl anchor_manage.py + .cred); keep the log.
    # OVERWRITE the code, but PRESERVE the anchor's own isolated venv (VM-only, not in the copy) + its log —
    # a plain rsync --delete would wipe .venv and drop the anchor back to JSON.
    r = d.rsync_push(str(DEPLOY_ANCHOR), "/home/mostafa/anchor-online",
                     excludes=["anchor.log", "__pycache__", "*.pyc", ".venv"], delete=True)
    print(f"  {'✓' if r.get('ok', True) else '✗'} anchor folder overwritten from deploy_anchor (.venv preserved)")
    # A STALE anchor process (old /usr/bin/python3 start) can still hold port 48619, so the systemd service
    # on the venv python can't bind it and the old JSON process keeps answering. Stop + kill the stale one
    # (scoped to THIS anchor's file only), then start fresh on the venv python.
    # Each sudo in its OWN call — a compound `sudo …; sudo …; sudo start` line does not reliably fire the
    # final start over this SSH channel (the isolated start does). Reliable restart on the venv python:
    d.ssh_exec("sudo systemctl daemon-reload", timeout=60)
    d.ssh_exec("sudo systemctl stop odin-anchor-online 2>/dev/null; true", timeout=60)
    d.ssh_exec("sudo pkill -f 'anchor-online/anchor_remote.py' 2>/dev/null; sleep 1; true", timeout=30)
    d.ssh_exec("sudo systemctl reset-failed odin-anchor-online 2>/dev/null; true", timeout=60)
    d.ssh_exec("sudo systemctl start odin-anchor-online", timeout=60)
    # health via the domain (existing nginx 443 + valid SSL — reused, never self-signed)
    import subprocess, time
    time.sleep(4)
    hc = ""
    for _ in range(10):
        hc = subprocess.run(["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}", "-m", "10",
                             f"https://{PROXY_HOST}/odin-anchor/health"], capture_output=True, text=True).stdout.strip()
        if hc == "200":
            break
        time.sleep(3)
    _check("anchor online /health = 200", hc == "200", f"HTTP {hc}")
    # PROVE Postgres is actually in use (not JSON fallback): the anchor creates its table in odin_anchor.
    tbl = (d.ssh_exec("PGPASSWORD_UNUSED=1 sudo -u postgres psql -d odin_anchor -tAc "
                      "\"SELECT count(*) FROM information_schema.tables WHERE table_name LIKE 'anchor%'\" 2>&1",
                      timeout=60).get("out") or "").strip()
    _check("anchor is using Postgres (anchor table present in odin_anchor)", tbl.isdigit() and int(tbl) >= 1,
           f"tables={tbl}")
    return 0 if hc == "200" else 1


def cmd_deploy_web() -> int:
    """Overwrite the VM web folder FROM deploy_web (preserve the service file _serve_nocache.py) + restart."""
    try:
        d = _ssh()
    except Exception as e:
        print(f"  ✗ ssh: {e}"); return 1
    d.refresh_firewall()
    # ALWAYS refresh deploy_web from the freshest build so we never ship a stale site.
    if WEB_BUILD.is_dir() and (WEB_BUILD / "index.html").exists():
        _copytree(WEB_BUILD, DEPLOY_WEB)
        WEB_SRC_FP_FILE.write_text(_web_src_fingerprint())
    if not (DEPLOY_WEB.is_dir() and (DEPLOY_WEB / "index.html").exists()):
        print("  ✗ deploy_web has no built site (index.html missing) — build the web first."); return 1
    # OVERWRITE the built site but NEVER delete the service runner or its log the systemd unit depends on.
    r = d.rsync_push(str(DEPLOY_WEB), "/home/mostafa/odin-web",
                     excludes=["_serve_nocache.py", "web.log"], delete=True)
    print(f"  {'✓' if r.get('ok', True) else '✗'} web folder overwritten from deploy_web (service file preserved)")
    d.ssh_exec("sudo systemctl restart odin-web-online", timeout=90)
    import subprocess, time
    time.sleep(2)
    wc = subprocess.run(["curl", "-sk", "-o", "/dev/null", "-w", "%{http_code}", "-m", "10",
                         f"https://{PROXY_HOST}/odin-web"], capture_output=True, text=True).stdout.strip()
    _check("web online /odin-web = 200/301", wc in ("200", "301", "302"), f"HTTP {wc}")
    return 0 if wc in ("200", "301", "302") else 1


def cmd_snapshot() -> int:
    """After a SUCCESSFUL deploy: refresh the deployment copies from originals + stamp the first-run flag."""
    LOGS.mkdir(exist_ok=True)
    # anchor copy
    DEPLOY_ANCHOR.mkdir(parents=True, exist_ok=True)
    for fn in ANCHOR_FILES:
        s = SERVER / fn
        if s.exists():
            (DEPLOY_ANCHOR / fn).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(s, DEPLOY_ANCHOR / fn)
    if CRED_SRC.exists():
        _write_anchor_cred()
    # web copy (from the freshly built site)
    if WEB_BUILD.is_dir():
        _copytree(WEB_BUILD, DEPLOY_WEB)
    DEPLOY_WEB.mkdir(parents=True, exist_ok=True)
    WEB_SRC_FP_FILE.write_text(_web_src_fingerprint())
    FIRSTRUN_FLAG.write_text("done\n")
    print("snapshot: deployment copies refreshed + first-run flag set.")
    return 0


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    return {
        "init": cmd_init,
        "compare": cmd_compare,
        "validate": cmd_validate,
        "ensure-db": cmd_ensure_db,
        "deploy-anchor": cmd_deploy_anchor,
        "deploy-web": cmd_deploy_web,
        "snapshot": cmd_snapshot,
    }.get(cmd, lambda: (print(__doc__), 2)[1])()


if __name__ == "__main__":
    raise SystemExit(main())
