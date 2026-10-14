#!/usr/bin/env python3
"""PC-5 test (no LLM): the brain answers browsers ONLY from the desktop app's origin (app://odin-desktop) and
localhost pages; every other web origin is refused for reads AND writes. Real HTTP. python pc5_test.py <root>"""
import sys, os, pathlib, subprocess, time, urllib.request, urllib.error
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root)
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
PORT = 28918
env = {**os.environ, "USE_VOICE": "0"}; env.pop("ODIN_ACCESS_TOKEN", None)
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "server.app:app", "--host", "127.0.0.1", "--port", str(PORT)],
                       cwd=str(root), env=env, stdout=subprocess.DEVNULL, stderr=open(root / "pc5_server.log", "w"))
def call(method, path, origin=None, token=None, extra=None):
    h = {"Content-Type": "application/json"}
    if origin is not None: h["Origin"] = origin
    if token: h["X-Odin-Token"] = token
    h.update(extra or {})
    r = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=(b"{}" if method in ("POST",) else None), method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=20) as x: return x.status, x.headers.get("access-control-allow-origin")
    except urllib.error.HTTPError as e: return e.code, e.headers.get("access-control-allow-origin")
    except Exception as e: return str(e), None
try:
    for _ in range(60):
        if call("GET", "/health")[0] == 200: break
        time.sleep(1)
    tf = root / "data" / "brain_token"; tok = tf.read_text().strip() if tf.is_file() else ""
    evil = ["https://evil.example", "null", "file://", "http://localhost.evil.example", "http://192.168.1.5:28000", "app://other"]
    rg = {o: call("GET", "/projects", o) for o in evil}
    check("1: reads from any other web origin are refused (incl. null / file:// / look-alikes)", all(v[0] == 403 and not v[1] for v in rg.values()), rg)
    rp = {o: call("POST", "/chats", o, tok) for o in evil}
    check("2: writes from any other web origin are refused, even with the token", all(v[0] == 403 for v in rp.values()), rp)
    pf = call("OPTIONS", "/chats", "https://evil.example", extra={"Access-Control-Request-Method": "POST"})
    check("3: a CORS preflight from another origin gets no allow header", pf[1] is None and pf[0] != 200, pf)
    ok = {o: call("GET", "/projects", o) for o in ("app://odin-desktop", "http://localhost:5173", "http://127.0.0.1:28000")}
    check("4: the desktop app's origin and localhost pages can read, with a matching allow header",
          all(v[0] == 200 and v[1] == o for o, v in ok.items()), ok)
    w = call("POST", "/chats", "app://odin-desktop", tok)
    check("5: the desktop app's origin can write with the token", w[0] == 200 and w[1] == "app://odin-desktop", w)
    check("6: local programs without an Origin (poller, CLI) still work (token rules unchanged)",
          call("GET", "/projects")[0] == 200 and call("POST", "/chats", None, tok)[0] == 200 and call("POST", "/chats")[0] == 401)
finally:
    srv.terminate(); srv.wait(10)
mc = (root / "desktop" / "electron" / "main.cjs").read_text() if (root / "desktop/electron/main.cjs").exists() else ""
check("7: the desktop app loads its UI from app://odin-desktop (not file://)", 'loadURL(DESKTOP_ORIGIN' in mc and "loadFile(" not in mc)
ev = root.parent.parent.parent / "_consolidation" / "results" / "pc5_electron_RESULT.txt"
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
