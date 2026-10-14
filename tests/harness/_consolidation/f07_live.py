#!/usr/bin/env python3
"""F-07 live proof (plan login only): approve the pending S8 r3 proposal in the COPY and check that the files it
writes are indexed the moment the apply finishes, without the audit."""
import sys, os, json, time, pathlib, urllib.request
R = pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0, str(R / "server"))
import claude_cli, workspace_mw as mw, workspace_audit as au

def _odin_token():   # F-20: the brain token (same machine)
    import os as _o, pathlib as _p
    if _o.environ.get("ODIN_ACCESS_TOKEN"): return _o.environ["ODIN_ACCESS_TOKEN"]
    for _d in _p.Path(__file__).resolve().parents:
        _f = _d / "data" / "brain_token"
        if _f.is_file(): return _f.read_text().strip()
    return ""

B = "http://127.0.0.1:28000"; AID = "2b841d68b150"; PID = "s8-calc-r3"
p = claude_cli.paid_auth_problem()
if p: print(json.dumps({"stopped": p})); sys.exit(3)
def get(u): return json.loads(urllib.request.urlopen(B + u, timeout=30).read())
def post(u, d): return json.loads(urllib.request.urlopen(urllib.request.Request(B + u, json.dumps(d).encode(), {"Content-Type": "application/json", "X-Odin-Token": _odin_token()}), timeout=30).read())
L = R / "_consolidation/results/claude_calls.jsonl"
usage = lambda: sum((json.loads(l).get("cost_usd") or 0) for l in L.read_text().splitlines() if l.strip())
code = R / "workspace/projects" / PID / "code"
rec = {"before": {f: [(code / f).exists(), mw.get_creator(code / f)[0]] for f in ("calc.py", "test_calc.py")}}
a0 = len((R / "workspace/history/audit-log.jsonl").read_text().splitlines()); u0 = usage(); t0 = time.time()
rec["approve"] = post(f"/approvals/{AID}/approve", {"note": "owner approves (F-07 live proof in the copy)"})
while time.time() - t0 < 420:
    a = next((x for x in (get(f"/approvals?pid={PID}&all=1").get("approvals") or []) if x["id"] == AID), {})
    if a.get("applied"): break
    time.sleep(5)
rec["applied_after_s"] = round(time.time() - t0); rec["applied"] = bool(a.get("applied"))
mw._CB_CACHE.update(v=None, t=0.0)
rec["after"] = {f: {"on_disk": (code / f).exists(), "indexed": mw.get_creator(code / f)[0],
                    "created_by": mw.creators_for([str((code / f).relative_to(R))]).popitem()[1]} for f in ("calc.py", "test_calc.py")}
new_audit = (R / "workspace/history/audit-log.jsonl").read_text().splitlines()[a0:]
rec["audit_touched_these_files"] = [l[:160] for l in new_audit if PID in l and "calc" in l]
rec["unindexed_in_project_now"] = [i["path"] for i in au.scan() if i["type"] == "unindexed" and PID in i["path"]]
rec["reported_usage_usd_not_charged"] = round(usage() - u0, 4)
print(json.dumps(rec, indent=1, default=str))
(R / "_consolidation/results/F07_live.json").write_text(json.dumps(rec, indent=1, default=str))
