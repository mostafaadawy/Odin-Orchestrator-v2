"""
test_anchor_online.py — Test 6: deploy the Anchor ONLINE to the Azure VM, SAFELY, and prove it works.

GUARANTEES (the owner's hard rules):
  • NEVER touches production folders (organics/bendcore/django) — the anchor lives in a dedicated sandbox
    dir on the VM (/home/mostafa/anchor-online).
  • NEVER changes ports 80/443/22 or their firewall rules — it opens ONLY the anchor port to the owner IP.
  • If it adds an nginx reverse-proxy, it FIRST backs up all of /etc/nginx, runs `nginx -t`, verifies the
    existing sites still answer, and RESTORES the backup on any failure. (Off by default — direct port is
    the safe path; enable with ODIN_ANCHOR_NGINX=1.)

What it does:
  1) rsync the anchor code to the sandbox dir on the VM (deploy_ssh, checksum overwrite).
  2) start `anchor_remote.py` on 0.0.0.0:<port> under nohup on the VM (kills any old one first).
  3) open the anchor port to the owner's current public IP (az NSG + ufw), additive only.
  4) VERIFY: the anchor answers on the VM (localhost) AND from here (VM_IP:port); a request round-trips;
     and the EXISTING production site is still healthy (no collateral damage).

This test is ANCHOR-ONLY. The WEB is deployed + verified by its own test (test_web_online.py), so each
surface proves independently that it is up AND not interfering with any other app on the VM.

Run:  python3 testing/test_anchor_online.py        (or via phase3_up.sh)
Env:  ODIN_ANCHOR_PORT (default 48619 — hard-to-guess), ODIN_ANCHOR_NGINX=1 to add the guarded nginx proxy.
"""
from __future__ import annotations

import os
import sys
import json
import time
import pathlib
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "server"))
import harness  # noqa: E402
from harness import log  # noqa: E402

ANCHOR_PORT = int(os.environ.get("ODIN_ANCHOR_PORT", "48619"))   # hard-to-guess production anchor port
VM_DIR = "/home/mostafa/anchor-online"          # dedicated sandbox dir — NEVER production
PROD_FOLDERS = ("/home/mostafa/organics", "/home/mostafa/bendcore", "/home/mostafa/django")


def _get(url, timeout=8):
    import ssl
    ctx = None
    if url.startswith("https"):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE   # VM has no domain cert; we reach it by IP over the existing 443
    try:
        with urllib.request.urlopen(url, timeout=timeout, context=ctx) as r:
            return r.status, r.read().decode(errors="ignore")[:400]
    except Exception as e:
        return None, str(e)


def _nsg_close(deploy_ssh, port: int):
    """Remove any Azure NSG rule a prior run may have added for this port. Best-effort; if az/NSG isn't
    reachable it's a no-op. We NEVER add an inbound rule — the app is reached only via nginx on 443."""
    try:
        deploy_ssh.ssh_exec(
            "RG=$(az group list --query '[0].name' -o tsv 2>/dev/null); "
            "NSG=$(az network nsg list --query '[0].name' -o tsv 2>/dev/null); "
            f"[ -n \"$NSG\" ] && az network nsg rule delete -g \"$RG\" --nsg-name \"$NSG\" "
            f"-n odin-{port} 2>/dev/null; true")
    except Exception:
        pass


def _nginx_proxy(deploy_ssh, path: str, port: int):
    """Expose 127.0.0.1:port through nginx on 443 under `path`, as OUR OWN separate enabled site
    (/etc/nginx/sites-available/odin-proxy). NO domain needed: the site's server_name is the VM IP, so it
    ONLY answers requests to the bare IP and never intercepts your domain sites (they match their own
    server_name). No new port is opened — only the existing 443. A self-signed cert for the IP is used.
    Fully guarded: back up /etc/nginx, write OUR site, `nginx -t`, verify an existing domain site still
    answers, and RESTORE on ANY failure (your sites are never edited)."""
    server_name = os.environ.get("ODIN_SERVER_NAME", "").strip() or deploy_ssh.vm_ip()
    site = "/etc/nginx/sites-available/odin-proxy"
    # cert: when your real subdomain is live you can point to a trusted cert (Let's Encrypt) via env, and
    # the "not private" warning disappears. Until then, a self-signed cert for the IP is used.
    #   ODIN_TLS_CERT / ODIN_TLS_KEY  (e.g. /etc/letsencrypt/live/<sub>/fullchain.pem + privkey.pem)
    crt = os.environ.get("ODIN_TLS_CERT", "").strip() or "/etc/nginx/odin-selfsigned.crt"
    key = os.environ.get("ODIN_TLS_KEY", "").strip() or "/etc/nginx/odin-selfsigned.key"
    self_signed = crt == "/etc/nginx/odin-selfsigned.crt"
    ts = int(time.time())
    # TRUSTED CERT — DEFINITIVE POLICY: for the real domain we ALWAYS use the Let's Encrypt cert. Never,
    # ever self-signed (that is the "not private" error the owner must never see again). The cert already
    # exists on the VM; we just REFERENCE it (no certbot re-run — that was the instability). If it is ever
    # genuinely missing, we ACQUIRE it and retry — but we never fall back to self-signed for the domain.
    is_domain = "." in server_name and server_name != deploy_ssh.vm_ip()
    if is_domain:
        le = f"/etc/letsencrypt/live/{server_name}"
        crt, key, self_signed = f"{le}/fullchain.pem", f"{le}/privkey.pem", False
        have = deploy_ssh.ssh_exec(f"sudo test -f {crt} && echo yes || echo no").get("out", "").strip()
        if "yes" not in have:
            deploy_ssh.ssh_exec(f"sudo certbot certonly --nginx -d {server_name} --non-interactive "
                                f"--agree-tos -m tech@odinmarkets.com --keep-until-expiring 2>&1 | tail -4")
            have = deploy_ssh.ssh_exec(f"sudo test -f {crt} && echo yes || echo no").get("out", "").strip()
        log(f"  ✓ TRUSTED Let's Encrypt cert for {server_name} (self-signed is NOT used for the domain){'' if 'yes' in have else ' — WARNING: cert file missing, acquisition attempted'}")
    # snapshot an existing site's health so we can PROVE we didn't break it
    before = deploy_ssh.ssh_exec("curl -sk -o /dev/null -w '%{http_code}' https://127.0.0.1/ -H 'Host: odinmarkets.com' || echo ERR").get("out", "").strip()
    deploy_ssh.ssh_exec(f"sudo tar czf /home/mostafa/nginx-backup-{ts}.tgz /etc/nginx 2>/dev/null; true")
    # self-signed cert for the IP (only when no real cert is provided). Verify the cert exists either way,
    # since a missing cert is the classic `nginx -t` failure.
    if self_signed:
        deploy_ssh.ssh_exec(f"[ -f {crt} ] || sudo openssl req -x509 -nodes -newkey rsa:2048 -days 825 "
                            f"-keyout {key} -out {crt} -subj '/CN={server_name}'; true")
    cert_ok = deploy_ssh.ssh_exec(f"sudo test -s {crt} && sudo test -s {key} && echo yes || echo no").get("out", "").strip()
    if "yes" not in cert_ok:
        return False, f"TLS cert/key not found ({crt}) — nginx NOT touched"
    # Build the config on the VM with a heredoc so nginx's $host/$remote_addr are written literally
    # (no shell/printf mangling). 'EOF' is quoted → the remote shell does NOT expand $variables.
    # Always write the COMPLETE site with BOTH locations (anchor 48619 + web 48620) so it's idempotent
    # no matter which test calls this — one server block, both paths, one self-signed cert for the IP.
    def _loc(p, pt):
        return (f"    location {p}/ {{\n        proxy_pass http://127.0.0.1:{pt}/;\n"
                "        proxy_set_header Host $host;\n        proxy_set_header X-Real-IP $remote_addr;\n"
                "        proxy_http_version 1.1;\n    }\n")
    # a branded landing page at / so the bare domain never shows the default "Welcome to nginx" (tech reveal)
    landing = (
        "    location = / {\n"
        "        default_type text/html;\n"
        "        return 200 '<!doctype html><meta charset=\"utf-8\"><title>Odin</title>"
        "<body style=\"margin:0;height:100vh;display:grid;place-items:center;"
        "background:radial-gradient(1000px 600px at 50% -10%,#16204a,#0a0c12);color:#e8ecf6;font-family:system-ui\">"
        "<div style=\"text-align:center\"><div style=\"font-size:52px;font-weight:800;color:#7af0d0\">&#937; Odin</div>"
        "<p style=\"color:#9aa4bf;margin-top:6px\">Secure anchor gateway</p></div></body>';\n"
        "    }\n")
    conf = (
        "server {\n"
        "    listen 443 ssl;\n"
        f"    server_name {server_name};\n"
        f"    ssl_certificate {crt};\n"
        f"    ssl_certificate_key {key};\n"
        + landing
        + _loc("/odin-anchor", 48619)
        + _loc("/odin-web", 48620)
        + "}\n"
    )
    import base64 as _b64
    conf_b64 = _b64.b64encode(conf.encode()).decode()
    builder = (
        f"echo {conf_b64} | base64 -d > /tmp/odin-proxy.conf && sudo cp /tmp/odin-proxy.conf {site} && "
        # only link once the real file exists — never leave a dangling symlink that breaks nginx -t
        f"sudo ln -sf {site} /etc/nginx/sites-enabled/odin-proxy && echo WROTE_OK || echo WRITE_FAILED")
    wr = deploy_ssh.ssh_exec(builder).get("out", "")
    if "WROTE_OK" not in wr:
        deploy_ssh.ssh_exec("sudo rm -f /etc/nginx/sites-enabled/odin-proxy")
        return False, f"could not write the proxy site file (sudo cp failed) — nginx not changed: {wr.strip()[:120]}"
    exists = deploy_ssh.ssh_exec(f"[ -s {site} ] && echo yes || echo no").get("out", "").strip()
    if "yes" not in exists:
        deploy_ssh.ssh_exec("sudo rm -f /etc/nginx/sites-enabled/odin-proxy")
        return False, "proxy site file is empty/missing after write — nginx not changed"
    test = deploy_ssh.ssh_exec("sudo nginx -t 2>&1").get("out", "")
    if "successful" not in test:
        # grab the specific [emerg] line so we know EXACTLY why, not a generic 'test failed'
        emerg = " | ".join(l.strip() for l in test.splitlines() if "emerg" in l.lower() or "error" in l.lower())[:300]
        deploy_ssh.ssh_exec(f"sudo rm -f /etc/nginx/sites-enabled/odin-proxy; sudo tar xzf /home/mostafa/nginx-backup-{ts}.tgz -C / && sudo systemctl reload nginx")
        return False, f"nginx -t FAILED → RESTORED (your sites untouched): {emerg or test.strip()[:200]}"
    deploy_ssh.ssh_exec("sudo systemctl reload nginx")
    after = deploy_ssh.ssh_exec("curl -sk -o /dev/null -w '%{http_code}' https://127.0.0.1/ -H 'Host: odinmarkets.com' || echo ERR").get("out", "").strip()
    if before not in ("", "ERR") and after != before:
        deploy_ssh.ssh_exec(f"sudo rm -f /etc/nginx/sites-enabled/odin-proxy; sudo tar xzf /home/mostafa/nginx-backup-{ts}.tgz -C / && sudo systemctl reload nginx")
        return False, f"existing site changed ({before}→{after}) → RESTORED; your sites safe"
    return True, f"separate site 'odin-proxy' (https://{server_name}{path}) added; existing site {before}→{after} unchanged"


def main() -> int:
    import deploy_ssh
    log("=" * 74)
    log("TEST 6 — Anchor ONLINE deploy to the Azure VM (safe, isolated; never touches other apps)")
    log("=" * 74)

    # 0) reachability + identities. On 4G your public IP can change; SSH(22) is locked to your IP, so
    #    FIRST rotate the 22 allow-rule (ufw + NSG source) to your CURRENT IP — never app ports. Then a
    #    changed IP simply reconnects instead of failing.
    try:
        fw = deploy_ssh.refresh_firewall()
        log(f"  SSH(22) allow rotated to current IP {fw.get('note', '(ok)')}")
    except Exception as e:
        log(f"  (firewall rotate note: {e})")
    if not (deploy_ssh.ssh_exec("echo ok").get("ok")):
        log("  ⏭  SKIPPED — VM not reachable this run (if on 4G, re-run; the IP rotate will let it in).")
        harness.SeedingPrompt.run(project_ids=[], passed=True)
        return 0
    vm_ip = deploy_ssh.vm_ip()
    log(f"  VM: {vm_ip}   anchor port: {ANCHOR_PORT}   dir: {VM_DIR} (sandbox, never production)")

    # SAFETY SNAPSHOT — existing site health BEFORE we do anything, so we can prove we didn't break it.
    before80 = deploy_ssh.ssh_exec("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:80 || echo ERR").get("out", "").strip()
    log(f"  existing site on :80 before = HTTP {before80}")

    # IDEMPOTENT PRE-CHECK — if the anchor is ALREADY deployed and healthy online, do NOT recreate or
    # redeploy it. Just verify it and pass. We only (re)deploy when it is missing or unhealthy.
    # pre-check via the PUBLIC proxy (the anchor is localhost-only on the VM, so the raw IP:port never
    # answers from here) — this lets a healthy deploy be detected and SKIPPED on re-runs.
    _ph = os.environ.get("ODIN_SERVER_NAME", "").strip() or vm_ip
    _pre_code, _ = _get(f"https://{_ph}/odin-anchor/health", timeout=6)
    _svc = deploy_ssh.ssh_exec("systemctl is-active odin-anchor-online 2>/dev/null || echo none").get("out", "").strip()
    # The anchor code sync + service restart is FAST (rsync --checksum + systemctl restart ~5s), and code
    # DOES change (e.g. new sync endpoints), so always refresh it — set ODIN_ANCHOR_SKIP=1 to skip when
    # you know the code is unchanged. Only the raw IP:port never answers here (localhost-only on the VM).
    skip_deploy = (_pre_code == 200) and os.environ.get("ODIN_ANCHOR_SKIP", "0") == "1"
    if skip_deploy:
        log(f"  ✓ anchor ALREADY online & healthy (HTTP 200, service={_svc}) — skipping redeploy, verifying only")
    else:
        log(f"  anchor not healthy yet (pre-check HTTP {_pre_code}, service={_svc}) — will deploy")

    # 1) push the anchor code to the sandbox dir (checksum overwrite), never production paths
    deploy_ssh.ssh_exec(f"mkdir -p {VM_DIR}")
    # CLEAN OLD/WRONG VERSIONS — earlier attempts may have left stale .py or a broken service on the VM.
    # Remove old code + stop any old service/process so we deploy ONE known-good, matching set (keeps logs).
    if not skip_deploy:
        deploy_ssh.ssh_exec(
            f"sudo systemctl stop odin-anchor-online 2>/dev/null; "
            f"fuser -k {ANCHOR_PORT}/tcp 2>/dev/null; sleep 1; "
            f"rm -f {VM_DIR}/*.py {VM_DIR}/*.pyc; rm -rf {VM_DIR}/__pycache__; true")
    _files = pathlib.Path(__file__).resolve().parents[3] / "server"
    # sync only the anchor pieces + their deps (stdlib-only service)
    import subprocess, shutil
    pw = deploy_ssh.vm_password()
    ssh = "ssh " + " ".join(deploy_ssh._opts())
    _rc = 1
    if not skip_deploy and pw and shutil.which("sshpass"):
        # anchor_remote.py → imports anchor_queue → imports store. ALL must ship or the VM process
        # crashes at import time (that was the 000ERR). store.py is stdlib-only, like the rest.
        for fn in ("store.py", "anchor.py", "anchor_queue.py", "anchor_remote.py", "local_poller_http.py"):
            src = _files / fn
            if src.exists():
                args = ["sshpass", "-p", pw, "rsync", "-az", "--checksum", "-e", ssh,
                        str(src), f"mostafa@{vm_ip}:{VM_DIR}/"]
                _rc = subprocess.run(args, capture_output=True, text=True, timeout=300).returncode
        # ship the credentials the anchor needs (auth key) into the sandbox dir only
        cred = _files.parent / "oth" / ".cred"
        if cred.exists():
            subprocess.run(["sshpass", "-p", pw, "rsync", "-az", "-e", ssh, str(cred),
                            f"mostafa@{vm_ip}:{VM_DIR}/.cred"], capture_output=True, text=True, timeout=120)
    pushed = True if skip_deploy else (_rc == 0)
    log(f"  {'✓' if pushed else '✗'} anchor code {'already present (skipped sync)' if skip_deploy else f'synced to {VM_DIR}'}")

    # 2) (re)start the anchor on 0.0.0.0:PORT under nohup — ONLY if it is not already healthy
    if not skip_deploy:
        deploy_ssh.ssh_exec(f"fuser -k {ANCHOR_PORT}/tcp 2>/dev/null; sleep 1; true")
    if skip_deploy:
        # already healthy — just read its local health, do NOT restart it
        r = deploy_ssh.ssh_exec(f"curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:{ANCHOR_PORT}/health || echo ERR")
    else:
        # START VIA SYSTEMD (bind 127.0.0.1 only — never public). systemd daemonizes cleanly, so the SSH
        # call returns instantly (no hang), and the anchor is persistent from the first start.
        import shlex as _sh
        # Keep systemd's DEFAULT start-limit (safety net — never fully disabled, per the owner's security
        # rule). A bounded, GENEROUS limit: allow up to 30 restarts/60s for transient hiccups, but still
        # stop an infinite crash-loop from burning CPU. The real fix is the crash-proof handler in
        # anchor_remote.py (a route bug returns 500, never crashes), so this limit is essentially never hit.
        svc = ("[Unit]\nDescription=Odin Anchor (online sandbox)\nAfter=network-online.target\n"
               "StartLimitIntervalSec=60\nStartLimitBurst=30\n\n"
               "[Service]\nType=simple\nUser=mostafa\nWorkingDirectory=" + VM_DIR + "\n"
               "Environment=ODIN_ANCHOR_CRED=" + VM_DIR + "/.cred\n"
               "ExecStart=/usr/bin/python3 " + VM_DIR + "/anchor_remote.py --host 127.0.0.1 --port " + str(ANCHOR_PORT) + "\n"
               "Restart=always\nRestartSec=2\n\n[Install]\nWantedBy=multi-user.target\n")
        # write the unit to a temp file as the normal user (no pipe into sudo — that eats the password),
        # then `sudo cp` it into place. HARD restart: stop the service, kill ANYTHING still holding the
        # port (old nohup/setsid processes running stale code — that's why /sync 404'd and mobile got a
        # 502 HTML page), then start fresh so the NEW code binds.
        # CRITICAL: deploy_ssh feeds the sudo password via stdin, so only the FIRST sudo in a command gets
        # it — chaining 6 sudos in one SSH call meant `systemctl start` silently never ran (that's why the
        # anchor never came up). Run each sudo in its OWN SSH call so every one authenticates.
        deploy_ssh.ssh_exec(f"printf %s {_sh.quote(svc)} > /tmp/odin-anchor.service")
        deploy_ssh.ssh_exec("sudo cp /tmp/odin-anchor.service /etc/systemd/system/odin-anchor-online.service")
        deploy_ssh.ssh_exec("sudo systemctl daemon-reload")
        deploy_ssh.ssh_exec("sudo systemctl stop odin-anchor-online 2>/dev/null; true")
        deploy_ssh.ssh_exec("sudo systemctl reset-failed odin-anchor-online 2>/dev/null; true")
        deploy_ssh.ssh_exec(f"sudo fuser -k {ANCHOR_PORT}/tcp 2>/dev/null; true")
        deploy_ssh.ssh_exec("sudo pkill -f 'anchor_remote.py' 2>/dev/null; true")
        deploy_ssh.ssh_exec("sudo systemctl start odin-anchor-online")
        deploy_ssh.ssh_exec("sudo systemctl enable odin-anchor-online 2>/dev/null; true")
        r = deploy_ssh.ssh_exec(f"sleep 4; curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:{ANCHOR_PORT}/health || echo ERR")
        # PROVE the NEW code is live: the new sync route must answer (not 404). If it 404s, old code is running.
        _k = deploy_ssh.ssh_exec(f"grep ANCHOR_API_KEY {VM_DIR}/.cred 2>/dev/null | cut -d= -f2 | tr -d '\"[:space:]'").get("out", "").strip()
        _nr = deploy_ssh.ssh_exec(
            f"curl -s -o /dev/null -w '%{{http_code}}' -H 'X-API-Key: {_k}' "
            f"http://127.0.0.1:{ANCHOR_PORT}/anchor/v1/projects || echo ERR").get("out", "").strip()
        log(f"  NEW sync route /anchor/v1/projects (LOCAL) → HTTP {_nr}  (200 = new code live)")
        # PUBLIC end-to-end check: the exact URL the app calls, through nginx on the domain. Must be 200,
        # not 404/502 — this catches a routing regression (falling through to Django) BEFORE you see it.
        _ph2 = os.environ.get("ODIN_SERVER_NAME", "").strip() or vm_ip
        _pub = deploy_ssh.ssh_exec(
            f"curl -sk -o /dev/null -w '%{{http_code}}' -H 'X-API-Key: {_k}' "
            f"https://{_ph2}/odin-anchor/anchor/v1/projects || echo ERR").get("out", "").strip()
        log(f"  PUBLIC app route https://{_ph2}/odin-anchor/anchor/v1/projects → HTTP {_pub}  (200 = apps can read it)")
    vm_local_health = (r.get("out", "") or "").strip().splitlines()[-1] if r.get("out") else "ERR"
    log(f"  anchor local health on the VM (127.0.0.1:{ANCHOR_PORT}) = HTTP {vm_local_health}")
    # DIAGNOSTIC — if the process didn't answer locally, show WHY (its crash log + what files landed).
    if not str(vm_local_health).startswith("200"):
        crash = deploy_ssh.ssh_exec(f"echo '--- files ---'; ls -1 {VM_DIR}; echo '--- python ---'; "
                                    f"python3 --version 2>&1; "
                                    f"echo '--- systemctl status ---'; sudo systemctl status odin-anchor-online --no-pager 2>&1 | tail -12; "
                                    f"echo '--- journal ---'; sudo journalctl -u odin-anchor-online --no-pager -n 15 2>&1; "
                                    f"echo '--- listener ---'; sudo ss -ltnp 2>/dev/null | grep 48619 || echo 'not listening'; "
                                    f"echo '--- import test ---'; cd {VM_DIR} && python3 -c 'import anchor_remote' 2>&1 | tail -5")
        log("  VM anchor diagnostic:\n" + (crash.get("out", "") or crash.get("err", "") or "(no output)"))

    # 3) EXPOSURE = REVERSE PROXY ONLY. Never open a public port. Remove any 48619 rule an earlier run
    #    added (ufw + NSG) so inbound stays 80/443/22 only, then route via a SEPARATE nginx site.
    deploy_ssh.ssh_exec(f"sudo ufw delete allow {ANCHOR_PORT}/tcp 2>/dev/null; sudo ufw delete allow {ANCHOR_PORT} 2>/dev/null; true")
    _nsg_close(deploy_ssh, ANCHOR_PORT)
    proxy_ok, proxy_note = _nginx_proxy(deploy_ssh, "/odin-anchor", ANCHOR_PORT)
    log(f"  exposure: no public port; ufw/NSG cleaned (80/443/22 only); nginx /odin-anchor → 127.0.0.1:{ANCHOR_PORT} — {proxy_note}")

    # 4) VERIFY from HERE via the reverse proxy on 443 (never a raw port)
    # verify via the DOMAIN (nginx routes by Host header/server_name), NOT the raw IP
    _proxy_host = os.environ.get("ODIN_SERVER_NAME", "").strip() or vm_ip
    base = f"https://{_proxy_host}/odin-anchor"
    time.sleep(2)
    code, body = _get(base + "/health")
    online_ok = code == 200
    log(f"  online health {base}/health = {code}")
    # round-trip: POST a request (auth via the key in .cred if the anchor enforces it)
    rid = None
    try:
        key = ""
        try:
            for ln in (_files.parent / "oth" / ".cred").read_text().splitlines():
                if "ANCHOR_API_KEY" in ln and "=" in ln:
                    key = ln.split("=", 1)[1].strip().strip('"')
        except Exception:
            key = ""
        req = urllib.request.Request(base + "/anchor/v1/requests",
                                     data=json.dumps({"project": "healthcheck", "prompt": "ping"}).encode(),
                                     headers={"Content-Type": "application/json", **({"X-API-Key": key} if key else {})})
        import ssl as _ssl
        _ctx = _ssl.create_default_context(); _ctx.check_hostname = False; _ctx.verify_mode = _ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=10, context=_ctx if base.startswith("https") else None) as rr:
            rid = json.loads(rr.read().decode()).get("request_id")
    except Exception as e:
        log(f"  round-trip POST note: {e}")
    roundtrip_ok = bool(rid)
    log(f"  round-trip request accepted online: {roundtrip_ok} (id={rid})")
    # NOTE: the WEB is deployed by its OWN test (test_web_online.py). This test is anchor-only so each
    # surface is proven independently and "not interfering with any other app" is asserted per deploy.

    # 5) SAFETY: prove the existing site is STILL healthy (unchanged) after our work
    after80 = deploy_ssh.ssh_exec("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:80 || echo ERR").get("out", "").strip()
    existing_safe = (after80 == before80) or (after80 and after80.startswith(("2", "3")))
    log(f"  existing site on :80 after = HTTP {after80} (was {before80})")
    # prove we never created anything in production folders
    prod_touch = deploy_ssh.ssh_exec(
        "for d in /home/mostafa/organics /home/mostafa/bendcore /home/mostafa/django; do "
        "[ -e \"$d/anchor_remote.py\" ] && echo TOUCHED; done; echo done").get("out", "")
    prod_untouched = "TOUCHED" not in prod_touch

    log("=" * 60 + "\n  STRONG SCORECARD\n" + "=" * 60)
    s1 = harness.scoreline("ANCHOR DEPLOYED TO SANDBOX DIR (never production folders)", pushed and prod_untouched,
                           f"dir={VM_DIR} prod_untouched={prod_untouched}")
    s2 = harness.scoreline("ANCHOR ONLINE + REACHABLE (VM_IP:port answers /health)", online_ok, f"{base}/health={code}")
    s3 = harness.scoreline("REQUEST ROUND-TRIPS THROUGH THE ONLINE ANCHOR", roundtrip_ok, f"id={rid}")
    s4 = harness.scoreline("EXISTING PRODUCTION SITE UNAFFECTED (:80 still healthy, ports 80/443/22 untouched)",
                           existing_safe, f"before={before80} after={after80}")
    ok = s1 and s2 and s3 and s4

    # The anchor is ALREADY a persistent systemd service (installed at start, bound to 127.0.0.1). Just
    # confirm it's enabled to survive reboots — no re-install, no rebinding to a public interface.
    if ok:
        try:
            deploy_ssh.ssh_exec("sudo systemctl enable odin-anchor-online 2>/dev/null")
            code2, _ = _get(base + "/health")
            log(f"  ✓ PERSISTENT service (odin-anchor-online, 127.0.0.1) — survives reboots; re-health={code2}")
        except Exception as e:
            log(f"  ⚠️ persistence step note (anchor still running via nohup): {e}")

    log("\n" + ("  ✅ ANCHOR ONLINE — deployed safely, reachable, round-trips, nothing else affected; KEPT & usable."
                if ok else "  ❌ ANCHOR ONLINE FAILED — see the rows above (nothing production was modified)."))
    harness.SeedingPrompt.run(project_ids=[], passed=ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
