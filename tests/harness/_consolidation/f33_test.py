#!/usr/bin/env python3
"""F-33 server test (no LLM). Run inside a throwaway root: python f33_test.py <root>"""
import sys, os, pathlib, time
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
import approvals
fails = []
def check(n, c):
    print(("PASS " if c else "FAIL ") + n)
    if not c: fails.append(n)
pid = f"f33-{int(time.time())}"
A = approvals.create(pid, "Fullstack", "change A", files=[{"path": f"workspace/projects/{pid}/code/a.py", "action": "create"}])["id"]
B = approvals.create(pid, "DevOps", "change B", commands=[{"cmd": "echo hi", "where": "local"}])["id"]
S = approvals.create_security(pid, "SecCTO", "security alarm S")["id"] if hasattr(approvals, "create_security") else None
st = lambda i: (approvals.get(i) or {}).get("status")
r1 = approvals.approve_all_safe(pid)
check("no token: nothing approved", st(A) == "pending" and st(B) == "pending")
ids = {x["id"] for x in r1["items"]}
check("no token: list shows every non-security proposal", ids == {A, B} and r1["needs_confirmation"])
check("list shows project and what it changes", all(x["pid"] == pid for x in r1["items"]) and
      any(x["files"] for x in r1["items"]) and any(x["commands"] for x in r1["items"]))
check("security alarm is not in the list", S is None or S not in ids)
C = approvals.create(pid, "QA", "change C (arrived after the list was shown)")["id"]
r2 = approvals.approve_all_safe(pid, r1["confirm"])
check("list changed after it was shown: nothing approved", "error" in r2 and st(A) == "pending" and st(C) == "pending")
r3 = approvals.approve_all_safe(pid, r2["confirm"])
check("with the fresh token: exactly the listed ones approved", st(A) == "approved" and st(B) == "approved" and st(C) == "approved")
check("security alarm still pending (individual only)", S is None or st(S) == "pending")
for x in approvals.list_for(pid, limit=50):
    if x.get("status") == "pending": approvals.decide(x["id"], False, "f33 test cleanup")
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
