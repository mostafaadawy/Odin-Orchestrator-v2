#!/usr/bin/env python3
"""F-38 test (no LLM): every project gets a folder; proposals writing outside are refused and shown. python f38_test.py <root>"""
import sys, os, pathlib, json, time
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
import projects, approvals, api_v2
WS = root / "workspace"; fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
# ---- A: the project folder is always set ----
p1 = projects.create_project("F38 NoPath", "test project without a declared folder", identifier="f38-nopath")
std = WS / "projects" / p1["id"] / "code"
check("A1: no declared path -> localPath = workspace/projects/<id>/code", pathlib.Path(p1.get("localPath") or "/x").resolve() == std.resolve() and std.is_dir(), p1.get("localPath"))
decl = root / "_f38_declared"; decl.mkdir(exist_ok=True)
p2 = projects.create_project("F38 Declared", "test project with a declared folder", local_path=str(decl), identifier="f38-declared")
check("A2: a declared path is used", str(p2.get("localPath") or "").startswith(str(decl)), p2.get("localPath"))
# ---- B: the outside-path guard ----
P = p1["id"]; F = str(std)
def out(files=(), cmds=()):
    return api_v2._outside_paths(P, {"files": [{"path": f} for f in files], "commands": [{"cmd": c, "where": w} for c, w in cmds]}, F)
check("B1: ~/Desktop file is outside", out(files=["~/Desktop/leads-landing/server.js"]))
check("B2: S4 r8 command `cd ~/Desktop/... && npm init -y > package.json` is outside", out(cmds=[("cd ~/Desktop/leads-landing && npm init -y > package.json", "local")]))
check("B2b: a write after `cd` to a home folder is outside", out(cmds=[("cd ~/Desktop && mkdir leads-landing", "local")]))
check("B2c: reading elsewhere is not writing (cd to repo root + ls)", not out(cmds=[(f"cd {root} && ls server", "local")]))
check("B2d: commands sent over ssh are left to the VM rules", not out(cmds=[('sshpass -p "$PW" ssh u@h "du -sh ~/organics/public > ~/x.txt"', "local")]))
check("B2e: a launchd plist written into ~/Library is outside", out(files=["~/Library/LaunchAgents/com.odin.x.plist"]))
check("B3: /tmp write is outside", out(cmds=[("echo hi > /tmp/f38.txt", "local")]))
check("B4: absolute path in another folder is outside", out(files=["/Users/someone/Documents/x.py"]))
check("B5: project-relative files are inside", not out(files=["code/calc.py", "calc.py", f"workspace/projects/{P}/code/x.py"]), out(files=["code/calc.py", "calc.py"]))
check("B6: heredoc write inside the folder is inside", not out(cmds=[("cat > calc.py <<'EOF'\nx=1\nEOF", "local")]))
check("B7: reading system paths / running tests is fine", not out(cmds=[("python3 -m unittest -v", "local"), ("ls /usr/bin > /dev/null", "local")]))
check("B8: shared/ in the workspace is inside", not out(files=["workspace/shared/utils/x.py"]))
check("B9: VM commands are left to the VM rules", not out(cmds=[("cd /home/mostafa/app && ls", "vm")]))
check("B10: `cd ..` out of the workspace then writing is caught", out(cmds=[("cd ../../../../.. && touch f38.txt", "local")]))
P2 = p2["id"]
check("B11: the DECLARED folder of another project is inside for it", not api_v2._outside_paths(P2, {"files": [{"path": str(decl / 'f38-declared' / 'a.py')}], "commands": []}, p2["localPath"]))
# ---- B12-B15 (F-39): exact extra files only — never the folder ----
pp = projects.get_project(P); pp["allowedExtraFiles"] = ["~/Library/LaunchAgents/com.odin.f38-test.plist"]; projects._update(pp)
check("B12: the exact allowed file is allowed", not out(files=["~/Library/LaunchAgents/com.odin.f38-test.plist"]))
check("B13: another file in the same folder is refused", out(files=["~/Library/LaunchAgents/com.other.plist"]))
check("B14: writing into the folder itself is refused", out(cmds=[("mkdir ~/Library/LaunchAgents/x", "local")]))
check("B15: cp of the exact file into that folder is allowed; another name is refused",
      not out(cmds=[("cp scheduler/com.odin.f38-test.plist ~/Library/LaunchAgents/", "local")]) and
      out(cmds=[("cp scheduler/evil.plist ~/Library/LaunchAgents/", "local")]))
# ---- C: refused at proposal time and shown to the owner ----
prop = {"files": [{"path": "~/Desktop/leads-landing/server.js", "action": "create"}], "commands": [{"cmd": "cd ~/Desktop/leads-landing && npm install", "where": "local"}], "summary": "test"}
bad = api_v2._outside_paths(P, prop, F)
r = api_v2._refuse_outside(P, "Fullstack", prop, bad, F, "F38 test")
a = approvals.get(r["id"])
check("C1: recorded as a REJECTED approval with the reason (visible to the owner)", a and a["status"] == "rejected" and "outside" in a.get("note", ""), a and (a.get("status"), a.get("note")))
import notifications_store as ns
check("C2: a notification is raised for the owner", any("Refused" in (n.get("title") or "") for n in ns.list(limit=50)))
# ---- D: refused at APPLY time even if approved ----
called = []
api_v2._engine_stream = lambda *a, **k: (called.append(1), iter(()))[1]
ap = approvals.create(P, "Fullstack", title="old outside proposal", files=prop["files"], commands=prop["commands"], cwd=F, kind="change")
approvals.decide(ap["id"], True, "owner approved")
api_v2._apply_approval_bg(ap["id"])
a2 = approvals.get(ap["id"])
check("D1: an approved outside proposal is NOT applied (engine never called)", not called and not a2.get("applied"), (called, a2.get("applied")))
check("D2: it is marked refused with the reason", a2["status"] == "rejected" and "outside" in a2.get("note", ""), (a2.get("status"), a2.get("note")))
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
