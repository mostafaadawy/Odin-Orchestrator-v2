#!/usr/bin/env python3
"""Fix #2c unit checks (no model cost): fixed verdict field + evidence agreement. Usage: fix2c_unit.py <server_dir>"""
import sys, ast, re, json, os, pathlib, tempfile, time, types
srv = pathlib.Path(sys.argv[1]); src = (srv / "api_v2.py").read_text()
tree = ast.parse(src)
want = {"_review_verdict", "_parse_verdict", "_step_outcome"}
body = [n for n in tree.body if (isinstance(n, ast.FunctionDef) and n.name in want) or
        (isinstance(n, ast.Assign) and any(getattr(t, "id", "") == "_BUILDISH" for t in n.targets))]
fails = []
def check(n, c):
    print(("PASS " if c else "FAIL ") + n)
    if not c: fails.append(n)
check("helpers present", len(body) == 4)
tmp = pathlib.Path(tempfile.mkdtemp()).resolve(); ROOT = tmp   # resolved: on macOS /var is a link to /private/var (the product resolves paths)
(tmp / "workspace/projects/p1/code").mkdir(parents=True)
registered = set(); pending = []
mw = types.ModuleType("workspace_mw")
class Cur:
    def execute(self, q, a): self.r = (1,) if a[0] in registered else None
    def fetchone(self): return self.r
class Conn:
    def cursor(self): return Cur()
    def close(self): pass
mw._db = lambda: Conn()
mw.sync_row = lambda p: registered.add(str(pathlib.Path(p).relative_to(ROOT))) if REGISTER_OK[0] else None
REGISTER_OK = [True]
ap = types.ModuleType("approvals"); ap.list_pending = lambda pid: [x for x in pending if x["pid"] == pid]
sys.modules["workspace_mw"] = mw; sys.modules["approvals"] = ap
ns = {"re": re, "json": json, "os": os, "pathlib": pathlib, "ROOT": ROOT}
exec(compile(ast.Module(body=body, type_ignores=[]), "h", "exec"), ns)
pv, so = ns["_parse_verdict"], ns["_step_outcome"]
V = lambda v, files=(), reason="r": 'Confirmed: ok\nVERDICT: ' + json.dumps({"verdict": v, "evidence_files": list(files), "reason": reason})

# parse
check("parse PASSED", pv(V("PASSED", ["a"]))["verdict"] == "PASSED")
check("parse missing → NOT_DONE", pv("Confirmed: all good")["verdict"] == "NOT_DONE" and not pv("Confirmed: all good")["parsed"])
check("parse invalid json → NOT_DONE", pv('VERDICT: {"verdict": PASSED}')["verdict"] == "NOT_DONE")
check("parse unknown value → NOT_DONE", pv(V("DONE"))["verdict"] == "NOT_DONE")
check("parse last verdict wins", pv(V("NOT_DONE") + "\n" + V("WAITING_FOR_APPROVAL").split("\n")[1])["verdict"] == "WAITING_FOR_APPROVAL")

t0 = time.time()
f = tmp / "workspace/projects/p1/code/form.html"; f.write_text("<form></form>")
rel = "workspace/projects/p1/code/form.html"
o, d = so("p1", "Build the contact form", V("PASSED", [rel]), True, True, False, t0)
check("PASSED: file exists, new, registered → PASSED", o == "PASSED")
o, d = so("p1", "Build the contact form", V("PASSED", ["code/form.html"]), True, True, False, t0)
check("PASSED: project-relative path accepted", o == "PASSED")
o, d = so("p1", "Build the contact form", V("PASSED", ["workspace/projects/p1/code/missing.py"]), True, True, False, t0)
check("PASSED claimed, file missing → NOT_DONE", o == "NOT_DONE" and "missing" in d["checks"][0])
o, d = so("p1", "Build the contact form", V("PASSED", []), True, True, False, t0)
check("PASSED claimed, build task, no files → NOT_DONE", o == "NOT_DONE")
old = tmp / "workspace/projects/p1/code/old.py"; old.write_text("x"); os.utime(old, (t0 - 3600, t0 - 3600))
o, d = so("p1", "Build the contact form", V("PASSED", ["workspace/projects/p1/code/old.py"]), True, True, False, t0)
check("PASSED claimed, only an OLD file (not this step) → NOT_DONE", o == "NOT_DONE")
REGISTER_OK[0] = False; registered.clear()
f2 = tmp / "workspace/projects/p1/code/b.py"; f2.write_text("y")
o, d = so("p1", "Build b", V("PASSED", ["workspace/projects/p1/code/b.py"]), True, True, False, t0)
check("PASSED claimed, file not registered → NOT_DONE", o == "NOT_DONE" and "registered" in d["checks"][0])
REGISTER_OK[0] = True
o, d = so("p1", "Build b", V("PASSED", [rel]), False, True, False, t0)
check("audit flagged → NOT_DONE", o == "NOT_DONE")
o, d = so("p1", "Build b", V("PASSED", [rel]), True, False, True, t0)
check("QA ran and failed → NOT_DONE", o == "NOT_DONE")
o, d = so("p1", "Build b", V("PASSED", [rel]), True, True, True, t0)
check("QA ran and passed → PASSED", o == "PASSED")
o, d = so("p1", "Build b", "Confirmed: x. Needs fix: y\nVERDICT: " + json.dumps({"verdict": "PASSED", "evidence_files": [rel]}), True, True, False, t0)
check("safety net: 'Needs fix' in text + PASSED field → NOT_DONE", o == "NOT_DONE")
o, d = so("p1", "Diagnose the read-only status", V("PASSED", []), True, True, False, t0)
check("read-only task, PASSED, no files → PASSED (no file expected)", o == "PASSED")
o, d = so("p1", "Build b", V("WAITING_FOR_APPROVAL"), True, True, False, t0)
check("WAITING claimed, no approval exists → NOT_DONE", o == "NOT_DONE")
pending.append({"id": "old1", "pid": "p1", "created": t0 - 600})
o, d = so("p1", "Build b", V("WAITING_FOR_APPROVAL"), True, True, False, t0)
check("WAITING claimed, only an OLDER approval → NOT_DONE", o == "NOT_DONE")
pending.append({"id": "new1", "pid": "p1", "created": t0 + 1})
o, d = so("p1", "Build b", V("WAITING_FOR_APPROVAL"), True, True, False, t0)
check("WAITING claimed, approval created in this step → WAITING_FOR_APPROVAL", o == "WAITING_FOR_APPROVAL" and d["approvals"] == ["new1"])
o, d = so("p1", "Build b", "Needs fix: not on disk yet, proposal pending\nVERDICT: " + json.dumps({"verdict": "WAITING_FOR_APPROVAL", "evidence_files": [], "reason": "pending"}), True, True, False, t0)
check("fix #2e: 'Needs fix' text + WAITING field + approval exists → WAITING_FOR_APPROVAL", o == "WAITING_FOR_APPROVAL")
o, d = so("p1", "Build b", "Waiting: correct proposal\nVERDICT: " + json.dumps({"verdict": "WAITING_FOR_APPROVAL", "evidence_files": [], "reason": "pending"}), True, True, False, t0)
check("fix #2e: 'Waiting:' opener → WAITING_FOR_APPROVAL", o == "WAITING_FOR_APPROVAL")
o, d = so("p1", "Build b", V("PASSED", [rel]), True, True, False, t0)
o, d = so("p1", "Build b", "Confirmed: done (no verdict line)", True, True, False, t0)
check("no verdict field → NOT_DONE", o == "NOT_DONE")
o, d = so("p1", "Build b", V("PASSED", ["/etc/hosts"]), True, True, False, t0)
check("file outside workspace and project folder → NOT_DONE", o == "NOT_DONE")
own = tmp / "ownfolder"; own.mkdir(); (own / "app.py").write_text("z")
o, d = so("p1", "Build app", V("PASSED", [str(own / "app.py")]), True, True, False, t0, str(own))
check("file in the project's own localPath folder → PASSED", o == "PASSED")
# source wiring
check("run outcome WAITING wired", 'verdict = ("⏳ Waiting for your approval' in src)
check("done event carries outcome", '"outcome": _run_outcome' in src)
check("old word-match acceptance removed", 'ok_step = (_rv == "confirmed")' not in src)
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}")
sys.exit(1 if fails else 0)
