#!/usr/bin/env python3
"""Sign in as web/mobile with the code read off the desktop's Anchor window; email/password = the desktop's copy rows
(Keychain). Prints only ok/status, never a value.  python3 signin_with_code.py <web|mobile> <code>"""
import json, subprocess, sys, urllib.request, urllib.error
cl, code = sys.argv[1], sys.argv[2]; A = "http://localhost:9100"
kc = lambda a: subprocess.run(["security","find-generic-password","-s","odin-anchor","-a",a,"-w"],capture_output=True,text=True).stdout.strip()
def req(m, p, b=None, h=None):
    r = urllib.request.Request(A+p, method=m, data=json.dumps(b).encode() if b is not None else None, headers={"Content-Type":"application/json", **(h or {})})
    try:
        with urllib.request.urlopen(r, timeout=10) as x: return x.status, json.loads(x.read() or b"{}")
    except urllib.error.HTTPError as e: return e.code, {}
H = {"X-Odin-Client": cl}
st, d = req("POST", "/anchor/v1/manage/login", {"email": kc("manage-email"), "password": kc("manage-password"), "code": code, "target": cl, "remember": True, "device_id": cl+"-proof"}, H)
print("login:", st, "ok=", d.get("ok"), "token=", "present" if d.get("token") else "none", "err=", d.get("error"))
st2, _ = req("GET", "/anchor/v1/projects", h={**H, "X-Manage-Token": d.get("token","")})
print("data with session (no key):", st2)
st3, _ = req("GET", "/manage/pending-code".join(["/anchor/v1",""]), h={"X-API-Key": kc("anchor-key")})
