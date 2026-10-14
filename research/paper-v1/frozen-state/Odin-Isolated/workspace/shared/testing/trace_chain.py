"""
trace_chain.py — trace EVERY integration point of the anchor chain and show the exact response, so we
know precisely where a 404 is born. Runs on the Mac (has VM access) via the bridge `trace` command.

Points, in order of the data flow web/mobile → anchor → desktop:
  1. DESKTOP brain (localhost:18000/projects)         — the source of truth the poller mirrors
  2. ANCHOR local on the VM (127.0.0.1:48619/...)    — the process itself
  3. ANCHOR public via nginx (https://<domain>/odin-anchor/...) — EXACTLY what the app calls
  4. WEB public (https://<domain>/odin-web)          — the deployed app
  5. nginx: which site actually owns the domain (is odin-proxy enabled?)
"""
from __future__ import annotations
import os, sys, pathlib, urllib.request, ssl, json
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[3] / "server"))

DOMAIN = os.environ.get("ODIN_SERVER_NAME", "anchor.odinmarkets.com")
APORT = os.environ.get("ODIN_ANCHOR_PORT", "48619")


def _key():
    try:
        for ln in (pathlib.Path(__file__).resolve().parent.parent / "oth" / ".cred").read_text().splitlines():
            if "ANCHOR_API_KEY" in ln and "=" in ln:
                return ln.split("=", 1)[1].strip().strip('"')
    except Exception:
        return ""
    return ""


def _local_get(url, key=""):
    ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
    r = urllib.request.Request(url, headers={"X-API-Key": key} if key else {})
    try:
        with urllib.request.urlopen(r, timeout=15, context=ctx) as resp:
            return resp.status, resp.read().decode(errors="ignore")[:180]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="ignore")[:180]
    except Exception as e:
        return "ERR", str(e)[:180]


def main():
    import deploy_ssh
    key = _key()
    print("=" * 70); print("TRACE CHAIN  domain=%s  anchor_port=%s" % (DOMAIN, APORT)); print("=" * 70)

    # 1) DESKTOP brain — run on THIS Mac (localhost)
    st, body = _local_get("http://localhost:18000/projects")
    print("1) DESKTOP brain  localhost:18000/projects        -> %s  %s" % (st, body[:120]))

    # 2/3/4/5 run on the VM (it can reach localhost:anchor AND the public domain)
    def vm(cmd):
        return deploy_ssh.ssh_exec(cmd).get("out", "").strip()

    print("2) ANCHOR local   127.0.0.1:%s/anchor/v1/projects -> %s" % (
        APORT, vm(f"curl -s -m 10 -w ' [HTTP %{{http_code}}]' -H 'X-API-Key: {key}' http://127.0.0.1:{APORT}/anchor/v1/projects | head -c 200")))
    print("3) ANCHOR public (from VM loopback) https://%s/odin-anchor/anchor/v1/projects -> %s" % (
        DOMAIN, vm(f"curl -sk -m 10 -w ' [HTTP %{{http_code}}]' -H 'X-API-Key: {key}' https://{DOMAIN}/odin-anchor/anchor/v1/projects | head -c 160")))
    # 3b) THE DECISIVE ONE — from THIS MAC (external, exactly like the app/mobile does). If this is 404 but
    # #3 is 200, the domain resolves/routes differently from outside (the real root cause).
    st_ext, body_ext = _local_get(f"https://{DOMAIN}/odin-anchor/anchor/v1/projects", key)
    print("3b) ANCHOR public (FROM THIS MAC, like the app) -> %s  %s" % (st_ext, str(body_ext)[:150]))
    # 3c) what public IP does the domain resolve to, from the Mac vs the VM's own IP?
    import socket
    try:
        print("    domain resolves (from Mac) -> %s" % socket.gethostbyname(DOMAIN))
    except Exception as e:
        print("    domain resolve error: %s" % e)
    print("    VM public IP -> %s" % vm("curl -s -m 6 ifconfig.me 2>/dev/null || echo ?"))
    print("   ANCHOR public  /odin-anchor/health            -> %s" % (
        vm(f"curl -sk -m 10 -w ' [HTTP %{{http_code}}]' https://{DOMAIN}/odin-anchor/health | head -c 120")))
    print("4) WEB public     https://%s/odin-web/            -> %s" % (
        DOMAIN, vm(f"curl -sk -m 10 -o /dev/null -w 'HTTP %{{http_code}}' https://{DOMAIN}/odin-web/")))
    # 4b) WEB-AS-BROWSER: mimic exactly what the Flutter WEB does — a CORS preflight (OPTIONS) then the GET
    # with an Origin header — and show the CORS response headers. A missing Access-Control-Allow-Origin or a
    # failed preflight is invisible to a plain curl but BLOCKS the browser (spinner/empty), a web-only cause.
    origin = "https://%s" % DOMAIN
    print("4b) WEB browser sim (CORS):")
    print("    OPTIONS preflight -> " + vm(
        f"curl -sk -o /dev/null -w 'HTTP %{{http_code}}' -X OPTIONS "
        f"-H 'Origin: {origin}' -H 'Access-Control-Request-Method: GET' "
        f"-H 'Access-Control-Request-Headers: x-api-key' https://{DOMAIN}/odin-anchor/anchor/v1/projects"))
    print("    GET response headers (Access-Control-Allow-Origin?):")
    print(vm(f"curl -sk -D - -o /dev/null -H 'Origin: {origin}' -H 'X-API-Key: {key}' "
             f"https://{DOMAIN}/odin-anchor/anchor/v1/projects | grep -iE 'HTTP/|access-control|content-type' | head -6"))
    print("5) nginx site owning the domain:")
    print(vm("ls -l /etc/nginx/sites-enabled/ | grep -E 'odin-proxy' || echo '   odin-proxy NOT enabled (domain falls through to another site → 404 HTML)'"))
    print("   nginx -t: " + vm("sudo nginx -t 2>&1 | tail -1"))
    print("   anchor service: " + vm("systemctl is-active odin-anchor-online 2>/dev/null; sudo ss -ltn 2>/dev/null | grep -c ':%s ' || echo 0" % APORT))
    print("=" * 70)


if __name__ == "__main__":
    main()
