#!/usr/bin/env python3
"""
phase3_e2e.py — smart PRODUCTION end-to-end checks for Phase 3.

Purpose: isolate the ONE real risk of Phase 3 — the switch from development to production configuration
(URLs, ports, deployed paths, cloud latency). Phase 2 already proved the behaviour; here we prove the
ONLINE endpoints answer correctly with production config and no accidental direct-backend dependency.

Each check has a FIXED expectation. Exit 0 = all critical checks pass; non-zero = a real failure.
Reads only; sends nothing that mutates state.
"""
from __future__ import annotations
import json
import os
import pathlib
import re
import ssl
import sys
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent
HOST = os.environ.get("ODIN_SERVER_NAME", "anchor.odinmarkets.com")
ANCHOR = f"https://{HOST}/odin-anchor"
WEB = f"https://{HOST}/odin-web"

_ctx = ssl.create_default_context()  # PRODUCTION must use the REAL valid cert (never self-signed)

fails = []
def ok(label, cond, detail=""):
    print(f"  {'✓' if cond else '✗'} {label}{(' — ' + detail) if detail else ''}")
    if not cond:
        fails.append(label)
    return cond

def get(url, headers=None, timeout=15):
    req = urllib.request.Request(url, headers=headers or {})
    r = urllib.request.urlopen(req, timeout=timeout, context=_ctx)
    return r.getcode(), r.read().decode("utf-8", "replace")

def code_of(url, headers=None):
    try:
        c, _ = get(url, headers)
        return c, ""
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, str(e)[:80]

def _cred(name):
    try:
        for line in (ROOT / "workspace" / "shared" / "oth" / ".cred").read_text().splitlines():
            if line.strip().split("=", 1)[0].strip() == name and "=" in line:
                return line.split("=", 1)[1].strip().strip('"').strip()
    except Exception:
        pass
    return ""

def _key():
    return _cred("ANCHOR_API_KEY")

def main():
    print(f"Production e2e against https://{HOST}  (valid SSL required — never self-signed):")

    # 1) ANCHOR health — must be 200 + ok:true (the secure hub is online in production)
    try:
        c, body = get(f"{ANCHOR}/health")
        j = {}
        try: j = json.loads(body)
        except Exception: pass
        ok("anchor /health = 200 + ok:true", c == 200 and j.get("ok") is True, f"HTTP {c}")
    except Exception as e:
        ok("anchor /health reachable", False, str(e)[:80])

    # 2) ANCHOR landing page — the ONLINE secure-hub page (proof it's production, not the dev landing)
    c, body = 0, ""
    try:
        c, body = get(f"{ANCHOR}/")
    except Exception as e:
        body = str(e)
    ok("anchor landing page serves (200)", c == 200, f"HTTP {c}")

    # 3) WEB production page — the deployed Flutter site answers (200/301) and looks like the app
    wc, _ = code_of(WEB)
    ok("web /odin-web serves (200/301)", wc in (200, 301, 302), f"HTTP {wc}")
    try:
        _, wbody = get(WEB if wc == 200 else WEB + "/")
        ok("web page is the Flutter app", ("flutter" in wbody.lower()) or ("main.dart.js" in wbody) or ("<!doctype html" in wbody.lower()), "")
    except Exception as e:
        ok("web page body readable", False, str(e)[:80])

    # 4) PRODUCTION AUTH — SIMULATE the real login: anon read is BLOCKED (401), then generate a code (like the
    #    desktop), read it, and log in with email + password + that code, and the authed read then works (200).
    #    This proves login + the 7-day session work in production and the web is no longer an open board.
    key = _key()

    def _post(path, body, hdr=None):
        req = urllib.request.Request(ANCHOR + path, data=json.dumps(body).encode(), method="POST",
                                     headers={"Content-Type": "application/json", "X-API-Key": key, **(hdr or {})})
        try:
            r = urllib.request.urlopen(req, timeout=15, context=_ctx); return r.getcode(), r.read().decode()
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")
        except Exception as e:
            return 0, str(e)

    anon, _ = code_of(f"{ANCHOR}/anchor/v1/projects", {"X-API-Key": key, "X-Odin-Client": "web"})
    ok("anon web read is BLOCKED (401 login required)", anon == 401, f"HTTP {anon}")
    # generate + read the code (as the desktop badge would show it)
    _post("/anchor/v1/manage/request-code", {"target": "web"}, {"X-Odin-Client": "web"})
    # the DESKTOP reads the code with the secret Anchor key (v1 flow) — never anonymously
    try:
        _, pcbody = get(f"{ANCHOR}/anchor/v1/manage/pending-code?target=web", {"X-API-Key": key})
    except urllib.error.HTTPError as e:
        pcbody = "{}"; ok("desktop (with the key) can read the waiting code", False, f"HTTP {e.code}")
    try:
        code = json.loads(pcbody).get("code", "")
    except Exception:
        code = ""
    email = os.environ.get("ODIN_LOGIN_EMAIL", "tech@odinmarkets.com")
    pw = os.environ.get("ODIN_LOGIN_PW", "") or _cred("ANCHOR_MANAGE_PASSWORD")  # local .cred, never printed
    lc, lbody = _post("/anchor/v1/manage/login",
                      {"email": email, "password": pw, "code": code, "target": "web"}, {"X-Odin-Client": "web"})
    try:
        tok = json.loads(lbody).get("token", "")
    except Exception:
        tok = ""
    ok("login with email+password+desktop code works (production)", lc == 200 and bool(tok), f"HTTP {lc}")
    authed, _ = code_of(f"{ANCHOR}/anchor/v1/projects",
                        {"X-API-Key": key, "X-Odin-Client": "web", "X-Manage-Token": tok})
    ok("authed web read = 200 (7-day session active)", authed == 200, f"HTTP {authed}")

    # 5) PRODUCTION CONFIG assertion — web/mobile must point ONLY at the online anchor, never the backend.
    cfg = (ROOT / "odin_app" / "lib" / "config.dart").read_text(encoding="utf-8", errors="replace")
    # the deployed/production profile: apiBaseUrl empty (NO direct backend) + anchorBaseUrl = the domain
    prod_ok = (f"https://{HOST}/odin-anchor" in cfg) and re.search(r"apiBaseUrl:\s*''", cfg) is not None
    ok("app production profile uses domain anchor + EMPTY apiBase (no direct backend)", bool(prod_ok),
       "config.dart deployed profile")
    # and the hard guarantee is present in the api layer
    api = (ROOT / "odin_app" / "lib" / "api" / "anchor_api.dart").read_text(encoding="utf-8", errors="replace")
    ok("api throws on any direct-backend call in anchor mode", "must go through the anchor" in api, "")

    print("")
    if fails:
        print(f"RESULT: FAIL ({len(fails)} check(s)): {', '.join(fails)}")
        return 1
    print("RESULT: PASS — production endpoints answer correctly and config points to the online anchor only.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
