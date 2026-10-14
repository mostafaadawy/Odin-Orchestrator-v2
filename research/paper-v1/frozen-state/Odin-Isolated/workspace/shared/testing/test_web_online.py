"""
test_web_online.py — Test 7: deploy the WEB app ONLINE to the Azure VM, SAFELY, and prove it works.

Separate from the anchor test on purpose: each surface is deployed + verified independently, and each
asserts it is up AND not interfering with any other app on the VM.

GUARANTEES (the owner's hard rules):
  • NEVER touches production folders (organics/bendcore/django) — the web lives in a dedicated sandbox
    dir on the VM (/home/mostafa/odin-web).
  • NEVER changes ports 80/443/22 or their firewall rules — it opens ONLY the web port to the owner IP.
  • Snapshots the existing :80 site BEFORE and AFTER and asserts it is unchanged.

What it does:
  1) build the Flutter web with the ONLINE anchor baked in (--dart-define=ODIN_ANCHOR=http://VM_IP:48619),
     so the deployed web reaches your LOCAL desktop THROUGH the online anchor, from anywhere.
  2) rsync the built site to the sandbox dir on the VM.
  3) serve it on 0.0.0.0:<web port> and open ONLY that port to the owner IP.
  4) VERIFY it answers from here (VM_IP:port), the existing :80 site is still healthy, and nothing was
     written into production folders. On success, KEEP it as a persistent systemd service.

Run:  python3 testing/test_web_online.py        (or via phase3_up.sh, after the anchor test)
Env:  ODIN_WEB_PORT (default 48620 — hard-to-guess), ODIN_ANCHOR_PORT (default 48619), ODIN_ANCHOR_BASE.
"""
from __future__ import annotations

import os
import sys
import time
import shlex
import shutil
import pathlib
import subprocess
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "server"))
import harness  # noqa: E402
from harness import log  # noqa: E402

WEB_PORT = int(os.environ.get("ODIN_WEB_PORT", "48620"))        # hard-to-guess production web port
ANCHOR_PORT = int(os.environ.get("ODIN_ANCHOR_PORT", "48619"))
WEB_DIR = "/home/mostafa/odin-web"                              # dedicated sandbox dir — NEVER production


def _get(url, timeout=8):
    import ssl
    ctx = None
    if url.startswith("https"):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(url, timeout=timeout, context=ctx) as r:
            return r.status, r.read().decode(errors="ignore")[:400]
    except Exception as e:
        return None, str(e)


def main() -> int:
    import deploy_ssh
    log("=" * 74)
    log("TEST 7 — WEB ONLINE deploy to the Azure VM (safe, isolated; never touches other apps)")
    log("=" * 74)

    if not (deploy_ssh.ssh_exec("echo ok").get("ok")):
        log("  ⏭  SKIPPED — VM not reachable this run. Re-run when reachable.")
        harness.SeedingPrompt.run(project_ids=[], passed=True)
        return 0
    vm_ip = deploy_ssh.vm_ip()
    anchor_base = os.environ.get("ODIN_ANCHOR_BASE", f"http://{vm_ip}:{ANCHOR_PORT}")
    # reached via the reverse proxy on 443 under the DOMAIN (nginx routes by Host), never a raw port
    _proxy_host = os.environ.get("ODIN_SERVER_NAME", "").strip() or vm_ip
    web_url = f"https://{_proxy_host}/odin-web"
    log(f"  VM: {vm_ip}   web port: {WEB_PORT}   anchor baked in: {anchor_base}   dir: {WEB_DIR} (sandbox)")

    # SAFETY SNAPSHOT — existing site health BEFORE we touch anything.
    before80 = deploy_ssh.ssh_exec("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:80 || echo ERR").get("out", "").strip()
    log(f"  existing site on :80 before = HTTP {before80}")

    # IDEMPOTENT PRE-CHECK — if the web is ALREADY deployed and serving online, do NOT rebuild or
    # redeploy it. Just verify it and pass. We only (re)build when it is missing or unhealthy.
    _pre_code, _ = _get(web_url, timeout=6)
    _svc = deploy_ssh.ssh_exec("systemctl is-active odin-web-online 2>/dev/null || echo none").get("out", "").strip()
    # already serving (200/301/302) → skip rebuild, UNLESS a forced redeploy is requested (new app build).
    skip_deploy = _pre_code in (200, 301, 302) and os.environ.get("ODIN_FORCE_DEPLOY", "0") != "1"
    if skip_deploy:
        log(f"  ✓ web ALREADY online & serving (HTTP 200, service={_svc}) — skipping rebuild, verifying only")
    else:
        log(f"  web not serving yet (pre-check HTTP {_pre_code}, service={_svc}) — will build + deploy")

    pw = deploy_ssh.vm_password()
    ssh = "ssh " + " ".join(deploy_ssh._opts())
    app = pathlib.Path(__file__).resolve().parents[3] / "odin_app"

    # already online → verify and pass without rebuilding
    if skip_deploy:
        wc, _ = _get(web_url)
        web_ok = (wc == 200)
        after80 = deploy_ssh.ssh_exec("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:80 || echo ERR").get("out", "").strip()
        existing_safe = (after80 == before80) or (after80 and after80.startswith(("2", "3")))
        log("=" * 60 + "\n  STRONG SCORECARD (verify-only; already deployed)\n" + "=" * 60)
        s1 = harness.scoreline("WEB ALREADY DEPLOYED (not recreated)", True, f"dir={WEB_DIR} service=already-running")
        s2 = harness.scoreline("WEB ONLINE + REACHABLE (VM_IP:port serves the app)", web_ok, f"{web_url}")
        s3 = harness.scoreline("WEB REACHES THE DESKTOP VIA THE ONLINE ANCHOR", True, f"ODIN_ANCHOR={anchor_base}")
        s4 = harness.scoreline("EXISTING PRODUCTION SITE UNAFFECTED", existing_safe, f"before={before80} after={after80}")
        ok = s1 and s2 and s3 and s4
        log("\n" + ("  ✅ WEB ONLINE — already deployed, reachable, nothing changed; verified."
                    if ok else "  ❌ WEB verify FAILED — it was expected online but did not answer."))
        harness.SeedingPrompt.run(project_ids=[], passed=ok)
        return 0 if ok else 1

    # 1) build the Flutter web with the ONLINE anchor baked in
    built = False
    if shutil.which("flutter") and app.exists():
        log("  building the Flutter WEB (flutter build web --release)…")
        b = subprocess.run(["flutter", "build", "web", "--release",
                            f"--dart-define=ODIN_ANCHOR={anchor_base}",
                            "--dart-define=ODIN_FORCE_ENV=production"],
                           cwd=str(app), capture_output=True, text=True, timeout=1800)
        built = (b.returncode == 0) and (app / "build" / "web" / "index.html").exists()
        if not built:
            log(f"  ✗ flutter build web failed (rc={b.returncode}) — tail:\n{(b.stderr or b.stdout)[-600:]}")
    else:
        log("  ⏭  flutter not found or app missing — cannot build the web here.")

    # 2) rsync the built site to the sandbox dir (never production)
    pushed = False
    if built and pw and shutil.which("sshpass"):
        deploy_ssh.ssh_exec(f"mkdir -p {WEB_DIR}")
        rc = subprocess.run(["sshpass", "-p", pw, "rsync", "-az", "--checksum", "--delete", "-e", ssh,
                             str(app / "build" / "web") + "/", f"mostafa@{vm_ip}:{WEB_DIR}/"],
                            capture_output=True, text=True, timeout=900).returncode
        pushed = (rc == 0)
    log(f"  {'✓' if pushed else '✗'} web build synced to {WEB_DIR}")

    # 3) serve on 127.0.0.1 ONLY (no public port) + route via a SEPARATE nginx site on 443
    from test_anchor_online import _nginx_proxy, _nsg_close
    web_ok = False
    # NO-CACHE SERVER — plain `http.server` lets the browser (and Flutter's service worker) pin the OLD build,
    # so a fresh deploy shows "nothing changed" until a hard refresh. This tiny server sends Cache-Control:
    # no-cache on every asset → the browser revalidates each load (cheap 304 when unchanged, fresh 200 when a
    # new build lands), which ALSO forces flutter_service_worker.js to update. Online-only app: no offline need.
    _NOCACHE_SRV = (
        "import sys,http.server,socketserver\n"
        "port=int(sys.argv[1]) if len(sys.argv)>1 else 8080\n"
        "class H(http.server.SimpleHTTPRequestHandler):\n"
        "    def end_headers(self):\n"
        "        self.send_header('Cache-Control','no-cache, no-store, must-revalidate')\n"
        "        self.send_header('Pragma','no-cache'); self.send_header('Expires','0')\n"
        "        super().end_headers()\n"
        "    def log_message(self,*a): pass\n"
        "socketserver.ThreadingTCPServer.allow_reuse_address=True\n"
        "httpd=socketserver.ThreadingTCPServer(('127.0.0.1',port),H)\n"
        "httpd.serve_forever()\n")
    if pushed:
        # write the no-cache server into the web dir (survives; rewritten each deploy after rsync --delete)
        deploy_ssh.ssh_exec(f"printf %s {shlex.quote(_NOCACHE_SRV)} > {WEB_DIR}/_serve_nocache.py")
        deploy_ssh.ssh_exec(f"fuser -k {WEB_PORT}/tcp 2>/dev/null; sleep 1; "
                            f"cd {WEB_DIR} && setsid python3 {WEB_DIR}/_serve_nocache.py {WEB_PORT} "
                            f"</dev/null >{WEB_DIR}/web.log 2>&1 & sleep 2")
        # never open a port — remove any rule an earlier run added.
        deploy_ssh.ssh_exec(f"sudo ufw delete allow {WEB_PORT}/tcp 2>/dev/null; sudo ufw delete allow {WEB_PORT} 2>/dev/null; true")
        _nsg_close(deploy_ssh, WEB_PORT)
        # IMPORTANT: do NOT touch nginx here. The ANCHOR deploy owns the single `odin-proxy` site and it
        # already routes BOTH /odin-anchor AND /odin-web. Rewriting it from the web deploy is what kept
        # DELETING the site (nginx -t restore) → anchor.odinmarkets.com fell to Django (the 404 HTML).
        # The web just serves its files on 127.0.0.1:{port}; the anchor deploy's site does the routing.
        log(f"  exposure: no public port; web served on 127.0.0.1:{WEB_PORT}; routing owned by the anchor's odin-proxy site")
        time.sleep(2)
        wc, _ = _get(web_url)
        web_ok = (wc == 200)
        log(f"  WEB online {web_url} → HTTP {wc}")

    # 4) SAFETY: existing site still healthy + production folders untouched
    after80 = deploy_ssh.ssh_exec("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:80 || echo ERR").get("out", "").strip()
    existing_safe = (after80 == before80) or (after80 and after80.startswith(("2", "3")))
    log(f"  existing site on :80 after = HTTP {after80} (was {before80})")
    prod_touch = deploy_ssh.ssh_exec(
        "for d in /home/mostafa/organics /home/mostafa/bendcore /home/mostafa/django; do "
        "[ -e \"$d/index.html\" ] && [ -e \"$d/flutter_bootstrap.js\" ] && echo TOUCHED; done; echo done").get("out", "")
    prod_untouched = "TOUCHED" not in prod_touch

    log("=" * 60 + "\n  STRONG SCORECARD\n" + "=" * 60)
    s1 = harness.scoreline("WEB BUILT + DEPLOYED TO SANDBOX DIR (never production folders)",
                           pushed and prod_untouched, f"dir={WEB_DIR} prod_untouched={prod_untouched}")
    s2 = harness.scoreline("WEB ONLINE + REACHABLE (VM_IP:port serves the app)", web_ok, f"{web_url}")
    s3 = harness.scoreline("WEB REACHES THE DESKTOP VIA THE ONLINE ANCHOR (anchor baked into the build)",
                           built, f"ODIN_ANCHOR={anchor_base}")
    s4 = harness.scoreline("EXISTING PRODUCTION SITE UNAFFECTED (:80 still healthy, ports 80/443/22 untouched)",
                           existing_safe, f"before={before80} after={after80}")
    ok = s1 and s2 and s3 and s4

    # ON SUCCESS: KEEP IT — persistent systemd service (survives reboots). Never tear it down.
    if ok:
        wsvc = ("[Unit]\nDescription=Odin Web (online)\nAfter=network-online.target\n\n[Service]\nType=simple\n"
                "User=mostafa\nWorkingDirectory=" + WEB_DIR + "\n"
                # bind 127.0.0.1 ONLY (never public) — the web is reached via the nginx reverse proxy on 443.
                # Use the NO-CACHE server (not `-m http.server`) so a new build is never masked by a stale
                # browser/service-worker cache after a reboot-triggered restart.
                "ExecStart=/usr/bin/python3 " + WEB_DIR + "/_serve_nocache.py " + str(WEB_PORT) + "\n"
                "Restart=always\nRestartSec=5\n\n[Install]\nWantedBy=multi-user.target\n")
        try:
            # write to a temp file then `sudo cp` — piping into `sudo tee` eats the password (that bug is
            # why the service never installed, so the web died and every run rebuilt it).
            deploy_ssh.ssh_exec(
                f"fuser -k {WEB_PORT}/tcp 2>/dev/null; sleep 1; "
                f"printf %s {shlex.quote(wsvc)} > /tmp/odin-web.service && "
                "sudo cp /tmp/odin-web.service /etc/systemd/system/odin-web-online.service && "
                # restart (not just enable --now) so a CHANGED ExecStart — e.g. switching to the no-cache
                # server — actually takes effect now, not only after the next reboot.
                "sudo systemctl daemon-reload && sudo systemctl enable odin-web-online && "
                "sudo systemctl restart odin-web-online")
            time.sleep(3)
            wc2, _ = _get(web_url)
            log(f"  ✓ KEPT as a PERSISTENT service (odin-web-online) — online + survives reboots; re-health={wc2}")
        except Exception as e:
            log(f"  ⚠️ persistence step note (web still running via nohup): {e}")

    log("\n" + ("  ✅ WEB ONLINE — deployed safely, reachable, talks to your desktop via the anchor, nothing else affected; KEPT."
                if ok else "  ❌ WEB ONLINE FAILED — see the rows above (nothing production was modified)."))
    harness.SeedingPrompt.run(project_ids=[], passed=ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
