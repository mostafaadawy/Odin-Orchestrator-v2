#!/usr/bin/env python3
"""Step C test (no LLM): F-45 (who approved + channel) and F-24 (an owner removal is remembered; re-creation refused),
replaying the REAL v1 poster sequence (876bba23bdfb removal → c647148af20b reinstall). python stepC_test.py <root>"""
import sys, os, pathlib, json, time, threading
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
import api_v2, approvals, projects
api_v2._apply_approval_bg = lambda aid: None
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
R = {(r.path, list(r.methods)[0]): r.endpoint for r in api_v2.build_router().routes if hasattr(r, "endpoint")}
p = projects.create_project("StepC", "x", identifier="stepc"); P = p["id"]
mk = lambda: approvals.create(P, "Fullstack", "t", files=[{"path": f"workspace/projects/{P}/code/a.txt", "action": "create"}])["id"]
a1 = mk(); R[("/approvals/{aid}/approve", "POST")](a1, {"channel": "desktop"}); g = approvals.get(a1)
check("F45-1: a desktop approval records by=owner, channel=desktop", g.get("decided_by") == "owner" and g.get("decided_channel") == "desktop", g)
a2 = mk(); R[("/approvals/{aid}/approve", "POST")](a2, {"channel": "phone"})
a3 = mk(); R[("/approvals/{aid}/approve", "POST")](a3, {})
check("F45-2: phone → phone; a client that does not say → api", approvals.get(a2).get("decided_channel") == "phone" and approvals.get(a3).get("decided_channel") == "api")
a4 = mk(); R[("/approvals/{aid}/reject", "POST")](a4, {"channel": "desktop"})
check("F45-3: a rejection records who and the channel too", approvals.get(a4).get("decided_by") == "owner" and approvals.get(a4).get("status") == "rejected")
a5 = mk(); out = []
for ev in api_v2._scoped_gen(f"project:{P}", f"approve {a5}", "en", "", from_owner=True): out.append(ev)
check("F45-4: a chat approval records channel=chat", approvals.get(a5).get("decided_channel") == "chat", approvals.get(a5))
a6 = mk(); pv = approvals.approve_all_safe(P) if hasattr(approvals, "approve_all_safe") else {}
tok = pv.get("token") or pv.get("confirm")
if tok: approvals.approve_all_safe(P, confirm=tok)
check("F45-5: bulk approve-all records channel=bulk", approvals.get(a6).get("decided_channel") == "bulk", (pv.keys() if pv else None, approvals.get(a6)))
a7 = approvals.create(P, "Fullstack", "out", files=[{"path": "/etc/hosts", "action": "edit"}])["id"]
api_v2._refuse_outside(P, "Fullstack", {"files": [{"path": "/etc/hosts"}]}, ["file /etc/hosts"], aid=a7)
check("F45-6: Odin's own refusal records by=odin, channel=guard", approvals.get(a7).get("decided_by") == "odin" and approvals.get(a7).get("decided_channel") == "guard", approvals.get(a7))
check("F45-7: every decision is kept in the approval's history", len(approvals.get(a1).get("decisions") or []) == 1)
js = (root / "desktop/src/api.js").read_text() if (root / "desktop/src/api.js").exists() else ""
dart = (root / "odin_app/lib/api/anchor_api.dart").read_text() if (root / "odin_app/lib/api/anchor_api.dart").exists() else ""
check("F45-8: the desktop and phone apps say which channel they are", 'channel: "desktop"' in js and "'channel': 'phone'" in dart)
# ---------- F-24 with the REAL v1 records
PP = "daily-egypt-amazon-product-poster"
rem, rei = approvals.get("876bba23bdfb"), approvals.get("c647148af20b")
check("F24-0: the real v1 removal and reinstall approvals are present in the test data", bool(rem) and bool(rei))
if rem and rei and hasattr(api_v2, "_remember_removals"):
    rem = dict(rem); rem["decided_by"] = "owner"
    gone = api_v2._remember_removals(PP, rem)
    check("F24-1: the owner-approved removal is remembered (the launchd plist + the scheduler folder)",
          any("LaunchAgents/com.odin.egypt-amazon-poster.plist" in g for g in gone) and any(g.endswith("scheduler") for g in gone), gone)
    bad = api_v2._outside_paths(PP, {"files": rei.get("files") or [], "commands": rei.get("commands") or []}, rei.get("cwd") or "")
    check("F24-2: the REAL reinstall proposal (c647148af20b) is now refused", any("you REMOVED this" in b for b in bad), bad[:3])
    ok = api_v2._outside_paths(PP, {"files": [{"path": "posts.py", "action": "edit"}], "commands": []}, rei.get("cwd") or "")
    check("F24-3: unrelated work in the same project is still allowed", not any("REMOVED" in b for b in ok), ok)
    p2 = projects.create_project("StepC2", "y", identifier="stepc2")
    rem2 = dict(rem); rem2["decided_by"] = "odin"
    check("F24-4: a removal NOT decided by the owner is not remembered", api_v2._remember_removals(p2["id"], rem2) == [])
else:
    for n in ("F24-1", "F24-2", "F24-3", "F24-4"):
        check(n + ": (feature missing)", False)
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
