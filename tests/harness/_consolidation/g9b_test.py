#!/usr/bin/env python3
"""G9b test (no LLM): agent ASKS -> owner enters the key in the app's secure field -> the APP stores it -> the delta
records only the NAME; agents still never write .cred. python g9b_test.py <root>"""
import sys, os, pathlib, json
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
import projects, approvals, secret_store, workspace_mw as mw, api_v2
WS = root / "workspace"; fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
_routes = {(r.path, list(r.methods)[0]): r.endpoint for r in api_v2.build_router().routes if hasattr(r, "endpoint")}
class _Cli:   # calls the REAL route functions (no HTTP client package needed)
    def post(self, path, json=None):
        class _R:
            def __init__(s, v): s.v = v
            def json(s): return s.v
        if path.startswith("/approvals/") and path.endswith("/approve"):
            return _R(_routes[("/approvals/{aid}/approve", "POST")](path.split("/")[2], json))
        return _R(_routes[(path, "POST")](json))
cli = _Cli()
SECRET = "kv_TEST_9f3b7c1e_not_real"
p = projects.create_project("G9b Brand Three", "email reporting for brand three", members=[{"name": "Email", "role": "Email Specialist"}], identifier="g9b-brand-three")
P = p["id"]
reply = 'I need a different key. KEY_REQUEST: {"service": "klaviyo", "name": "KLAVIYO_KEY_BRAND3", "why": "brand three uses its own account"}'
reqs = secret_store.requests_from_reply(P, "Email", reply)
a = reqs[0] if reqs else {}
check("1: the agent's KEY_REQUEST line creates a key request for the owner", a.get("kind") == "key_request" and a.get("key_name") == "KLAVIYO_KEY_BRAND3" and a.get("status") == "pending", a)
check("2: the request carries NO value field", "value" not in a and SECRET not in json.dumps(a))
r = cli.post(f"/approvals/{a['id']}/approve", json={"note": "x"}).json()
check("3: plain 'Approve' cannot fulfil a key request (needs the secure field)", "error" in r and approvals.get(a["id"])["status"] == "pending", r)
pv = approvals.approve_all_preview(None)
check("4: a key request is never in 'Approve all'", a["id"] not in [x["id"] for x in pv["items"]])
_cf = WS / "shared" / "oth" / ".cred"; _cf.parent.mkdir(parents=True, exist_ok=True)
_cf.write_text("# dummy test credentials\nDUMMY_EXISTING_KEY=abc123\nazvmcred: dummy-colon-format\n")
r = cli.post("/secrets/project-key", json={"aid": a["id"], "value": SECRET}).json()
check("5: the secure field stores it (app, not agent) and returns no value", r.get("ok") and SECRET not in json.dumps(r), r)
import importlib, integrations.cred as cred; importlib.reload(cred)
check("6: the stored key is readable by the runtime under its NAME", cred.get("KLAVIYO_KEY_BRAND3") == SECRET)
check("7: the .cred file is private (mode 600)", oct(cred.CRED.stat().st_mode & 0o777) == "0o600", oct(cred.CRED.stat().st_mode & 0o777))
rows = mw.list_agent_scope(P)
check("8: the project's delta records only the NAME (agent_scope)", any(x["credential_ref"] == "KLAVIYO_KEY_BRAND3" for x in rows) and SECRET not in json.dumps(rows), rows)
refp = WS / "projects" / P / "connectors" / "klaviyo.credential-ref.json"
check("9: the connectors/ reference holds the name, never the value", refp.exists() and "KLAVIYO_KEY_BRAND3" in refp.read_text() and SECRET not in refp.read_text())
hits = [str(f) for f in WS.rglob("*") if f.is_file() and f.name != ".cred" and f.stat().st_size < 5_000_000 and SECRET in f.read_text(errors="ignore")]
check("10: the value appears in NO other workspace file (logs, approvals, chats, DB mirror)", not hits, hits[:3])
check("11: the request is closed (approved + applied), note shows no value", approvals.get(a["id"])["status"] == "approved" and SECRET not in json.dumps(approvals.get(a["id"])))
other = cred.load(); check("12: other keys in .cred are kept unchanged (both formats, comment kept)",
      other.get("DUMMY_EXISTING_KEY") == "abc123" and other.get("azvmcred") == "dummy-colon-format" and _cf.read_text().startswith("# dummy test credentials"), other.keys())
r2 = cli.post("/secrets/project-key", json={"aid": a["id"], "value": "again"}).json()
check("13: a closed request cannot be reused", not r2.get("ok"))
check("14: agents still never write .cred (proposal refused)", api_v2._outside_paths(P, {"files": [{"path": "workspace/shared/oth/.cred"}], "commands": []}, p.get("localPath") or ""))
before = len([x for x in approvals.list_pending(P) if x.get("kind") == "key_request"])
api_v2._refuse_outside  # refusal of a secret write turns into a key request inside _run_gated; check the helper directly:
r3 = secret_store.request_key(P, "Email", "klaviyo", "KLAVIYO_KEY_BRAND4", "test")
check("15: a refused secret write can be turned into a key request", r3.get("kind") == "key_request")
check("16: bad key names are rejected", not cli.post("/secrets/project-key", json={"aid": r3["id"], "name": "bad name", "value": "x"}).json().get("ok"))
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
