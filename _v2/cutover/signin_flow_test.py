#!/usr/bin/env python3
"""Local proof of the v1 sign-in flow on v2 (no value is ever printed).
web/mobile press 'Get code' -> the DESKTOP button's poll (Keychain key, exactly as desktop/electron/secrets.cjs reads it)
sees the code -> the desktop's copy rows (email + password from the Keychain) + code -> login -> session -> data.
Also: remembered device signs in again without a code; reused code / wrong password / no session are refused."""
import json, subprocess, sys, urllib.request, urllib.error, uuid
A = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:9100"
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + ("" if c else f"  [{info}]")); c or fails.append(n)
def kc(acct):   # same call the desktop app makes (secrets.cjs: security find-generic-password -s odin-anchor -a <acct> -w)
    return subprocess.run(["security", "find-generic-password", "-s", "odin-anchor", "-a", acct, "-w"],
                          capture_output=True, text=True).stdout.strip()
def req(method, path, body=None, h=None):
    r = urllib.request.Request(A + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                               headers={"Content-Type": "application/json", **(h or {})})
    try:
        with urllib.request.urlopen(r, timeout=10) as x: return x.status, json.loads(x.read() or b"{}")
    except urllib.error.HTTPError as e:
        try: return e.code, json.loads(e.read() or b"{}")
        except Exception: return e.code, {}
KEY, EMAIL, PW = kc("anchor-key"), kc("manage-email"), kc("manage-password")
check("0: Keychain holds anchor-key, manage-email, manage-password (desktop reads these)", bool(KEY and EMAIL and PW))
for client in ("web", "mobile"):
    H = {"X-Odin-Client": client}                       # web/mobile carry NO API key
    st, _ = req("GET", "/anchor/v1/projects", h=H)
    check(f"{client} 1: before sign-in, data is refused", st == 401, st)
    st, d = req("POST", "/anchor/v1/manage/request-code", {"target": client}, H)
    check(f"{client} 2: 'Get code' accepted (no key needed)", st == 200 and d.get("ok"), (st, d.get("error")))
    st, d = req("GET", "/anchor/v1/manage/pending-code", h={"X-API-Key": KEY})
    code = (d or {}).get("code", "")
    check(f"{client} 3: the desktop button sees a waiting code (it blinks)", st == 200 and d.get("pending") and bool(code), st)
    st, d = req("GET", "/anchor/v1/manage/pending-code")
    check(f"{client} 4: nobody without the key can read the code", st == 401, st)
    st, d = req("POST", "/anchor/v1/manage/login", {"email": EMAIL, "password": PW + "x", "code": code, "target": client}, H)
    check(f"{client} 5: wrong password refused", not d.get("ok"), st)
    dev = f"{client}-{uuid.uuid4().hex[:8]}"
    st, d = req("POST", "/anchor/v1/manage/login", {"email": EMAIL, "password": PW, "code": code, "target": client,
                                                   "remember": True, "device_id": dev}, H)
    tok = d.get("token", "")
    check(f"{client} 6: sign-in with the desktop's email + password + code succeeds", d.get("ok") and bool(tok), d.get("error"))
    st, d2 = req("POST", "/anchor/v1/manage/login", {"email": EMAIL, "password": PW, "code": code, "target": client}, H)
    check(f"{client} 7: the same code cannot be used again", not d2.get("ok"), st)
    HT = {**H, "X-Manage-Token": tok}
    st, _ = req("GET", "/anchor/v1/projects", h=HT)
    check(f"{client} 8: signed in -> data loads (no key in the app)", st == 200, st)
    st, d = req("GET", "/anchor/v1/manage/me", h=HT)
    check(f"{client} 9: session is valid (kept for 1 week)", st == 200 and d.get("ok"), st)
    st, d = req("POST", "/anchor/v1/manage/login", {"email": EMAIL, "password": PW, "code": "", "target": client,
                                                   "device_id": dev}, H)
    check(f"{client} 10: remembered device signs in again without a code (30 days)", d.get("ok"), d.get("error"))
    st, _ = req("GET", "/anchor/v1/projects", h={**H, "X-Manage-Token": "f" * 32})
    check(f"{client} 11: a forged session is refused", st == 401, st)
    req("POST", "/anchor/v1/manage/logout", {}, HT)
import pathlib, re
src = (pathlib.Path(__file__).resolve().parents[2] / "server/anchor_manage.py").read_text()
ttl = {k: eval(re.search(rf"^{k}\s*=\s*([^#\n]+)", src, re.M).group(1)) for k in ("CODE_TTL", "SESSION_TTL", "DEVICE_TTL")}
check("12: timings unchanged from v1 (code 10 min, session 7 days, device 30 days)",
      (ttl["CODE_TTL"], ttl["SESSION_TTL"], ttl["DEVICE_TTL"]) == (600, 7 * 86400, 30 * 86400), ttl)
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}")
