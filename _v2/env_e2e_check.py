"""Environment e2e (no LLM, no cost): a client that can reach ONLY the Anchor (like web/mobile) creates an internal
project; the poller carries it to the brain; the brain has it; the Anchor mirror shows it back to every client.
Also checks the external-user page is served with its webhook pre-wired. Never prints a key.
usage: python _v2/env_e2e_check.py <root> <brain_port> <anchor_port> <sim_port> <webhook_port>"""
import sys, json, time, pathlib, urllib.request
root, bp, ap, sp, wp = sys.argv[1], *sys.argv[2:6]
cred = (pathlib.Path(root) / "workspace/shared/oth/.cred").read_text().splitlines()
key = next((l.split("=", 1)[1].strip().strip('"') for l in cred if l.startswith("ANCHOR_API_KEY=")), "")
def req(method, url, body=None, hdr=None):
    r = urllib.request.Request(url, method=method, data=json.dumps(body).encode() if body is not None else None,
                               headers={"Content-Type": "application/json", **(hdr or {})})
    with urllib.request.urlopen(r, timeout=20) as f:
        raw = f.read().decode(); return json.loads(raw) if raw.strip().startswith(("{", "[")) else raw
A = {"X-API-Key": key}
ok = lambda n, c, i="": print(("PASS " if c else "FAIL ") + n + ("" if c else f"  [{str(i)[:200]}]")) or c
res = []
name = f"Env proof {int(time.time())}"
t0 = time.time()
c = req("POST", f"http://localhost:{ap}/anchor/v1/requests", {"project": "__command__", "sender": "command", "prompt": "create_project",
        "payload": {"kind": "create_project", "name": name}}, A)
rid = c.get("request_id", "")
res.append(ok("1: the Anchor accepts the client's create-project command", bool(rid), c))
st = {}
for _ in range(60):
    time.sleep(1)
    st = req("GET", f"http://localhost:{ap}/anchor/v1/requests/{rid}", None, A)
    if st.get("status") in ("finished", "failed", "cancelled"): break
res.append(ok("2: the poller carried it to the brain and posted the result", st.get("status") == "finished", st))
pj = req("GET", f"http://localhost:{bp}/projects")
lst = pj.get("projects", pj) if isinstance(pj, dict) else pj
mine = [p for p in lst if p.get("name") == name]
res.append(ok("3: the brain (desktop's backend) has the new project", len(mine) == 1, [p.get("name") for p in lst][-5:]))
seen = False
for _ in range(30):
    try:
        m = req("GET", f"http://localhost:{ap}/anchor/v1/mirror/ui_projects", None, A)
        seen = name in json.dumps(m)
    except Exception: pass
    if seen: break
    time.sleep(2)
res.append(ok("4: the Anchor mirror (what web + mobile read) shows it", seen))
print(f"   create → visible to web/mobile: {time.time() - t0:.1f}s")
page = req("GET", f"http://localhost:{sp}/anchor_sim.html")
seed = req("GET", f"http://localhost:{sp}/anchor_seed.js")
res.append(ok("5: external-user page served", "<html" in str(page).lower()))
res.append(ok("6: its webhook/return URL is pre-wired to the local receiver", f"http://localhost:{wp}" in str(seed) and "key" in str(seed)))
res.append(ok("7: webhook receiver answers", isinstance(req("GET", f"http://localhost:{wp}/list"), (dict, list))))
print("RESULT:", "ALL PASS" if all(res) else f"{res.count(False)} FAIL")
