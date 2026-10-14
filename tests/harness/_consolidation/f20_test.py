#!/usr/bin/env python3
"""F-20 test (no LLM): the brain is LOCAL ONLY and every changing route needs the brain token. Starts the root's
own brain on a spare port and calls it over real HTTP. python f20_test.py <root>"""
import sys, os, pathlib, json, subprocess, time, urllib.request, urllib.error, stat
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
PORT = 28917
env = {**os.environ, "USE_VOICE": "0"}; env.pop("ODIN_ACCESS_TOKEN", None)
srv = subprocess.Popen([sys.executable, "-m", "uvicorn", "server.app:app", "--host", "127.0.0.1", "--port", str(PORT)],
                       cwd=str(root), env=env, stdout=subprocess.DEVNULL, stderr=open(root / "f20_server.log", "w"))
def call(method, path, token=None, host=None, body=None):
    h = {"Content-Type": "application/json"}
    if token: h["X-Odin-Token"] = token
    if host: h["Host"] = host
    r = urllib.request.Request(f"http://127.0.0.1:{PORT}{path}", data=(json.dumps(body or {}).encode() if method != "GET" else None), method=method, headers=h)
    try:
        with urllib.request.urlopen(r, timeout=20) as x: return x.status
    except urllib.error.HTTPError as e: return e.code
    except Exception as e: return str(e)
try:
    for _ in range(60):
        if call("GET", "/health") == 200: break
        time.sleep(1)
    check("0: the brain starts", call("GET", "/health") == 200)
    tf = root / "data" / "brain_token"
    tok = tf.read_text().strip() if tf.is_file() else ""
    check("1: a local brain token exists in data/brain_token, mode 600", bool(tok) and stat.S_IMODE(tf.stat().st_mode) == 0o600)
    check("2: reads stay open locally (GET /projects)", call("GET", "/projects") == 200)
    c1 = call("POST", "/chats", body={"title": "f20"}); c2 = call("DELETE", "/chats/none-f20"); c3 = call("POST", "/approvals/x/approve")
    check("3: changing routes WITHOUT the token are refused (POST, DELETE, approve)", c1 == 401 and c2 == 401 and c3 == 401, (c1, c2, c3))
    c4 = call("POST", "/chats", token="wrong-token")
    check("4: a wrong token is refused", c4 == 401, c4)
    c5 = call("POST", "/chats", token=tok, body={"title": "f20"})
    check("5: the right token passes", c5 == 200, c5)
    c6 = call("GET", "/scope/stream?scope=company&text=hi&cid=x")
    c7 = call("GET", "/chat/stream?text=hi")
    check("6: GET routes that RUN work (scope/chat stream) need the token too", c6 == 401 and c7 == 401, (c6, c7))
    c8 = call("GET", "/projects", host="evil.example:28917"); c9 = call("POST", "/chats", token=tok, host="attacker.test", body={"title": "x"})
    check("7: a non-localhost Host (DNS rebinding) is refused, even with the token", c8 == 403 and c9 == 403, (c8, c9))
finally:
    srv.terminate(); srv.wait(10)
import local_poller_http as lp
seen = []
class _R:
    def __enter__(s): return s
    def __exit__(s, *a): return False
    def read(s): return b"{}"
    def __iter__(s): return iter([])
lp.urllib.request.urlopen = lambda req, timeout=0: (seen.append(dict(req.header_items())), _R())[1]
lp._brain_post("/chats", {}); lp._brain_delete("/chats/x")
try: lp._brain_chat_stream("company", "hi")
except Exception: pass
check("8: the Anchor poller sends the token on every changing call", len(seen) >= 3 and all(h.get("X-odin-token") == tok for h in seen[:3]), seen[:3])
src = (root / "desktop/src/api.js").read_text() if (root / "desktop/src/api.js").exists() else ""
mc = (root / "desktop/electron/main.cjs").read_text() if (root / "desktop/electron/main.cjs").exists() else ""
check("9: the desktop gets the brain token from the Electron main process at start-up", "initBrainToken" in src and '"brain-token"' in mc)
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
