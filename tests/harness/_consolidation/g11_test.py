#!/usr/bin/env python3
"""G11 test (no LLM): who gets a scoped request. python g11_test.py <root>"""
import sys, os, pathlib
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
import api_v2, agents_registry
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{info}]" if info and not c else ""))
    if not c: fails.append(n)
TEAM = [{"name": "Fullstack"}, {"name": "DevOps"}]
agents_registry.list_agents = lambda pid: TEAM
S4 = "Plan the work and build the first version of the contact form. Do not deploy."
cases = [
 (S4, "Fullstack"),
 (S4 + " Constraint: do NOT deploy, rsync, build on the VM, migrate, or reboot -- no VM/production state change.", "Fullstack"),
 ("Fix the login page", "Fullstack"),
 ("Update the product catalog description", "Fullstack"),
 ("Add a feedback form to the blog", "Fullstack"),
 ("Don't touch the server, just fix the CSS", "Fullstack"),
 ("Check the VM uptime over SSH", "DevOps"),
 ("Deploy the site to the VM", "DevOps"),
 ("Show me the server logs from today", "DevOps"),
 ("Run the cleanup script on the server", "DevOps"),
 ("Don't forget to deploy after the fix", "DevOps"),
]
for goal, want in cases:
    got = api_v2._direct_member("x", goal)
    check(f"{goal[:60]!r} -> {want}", got == want, got)
TEAM[:] = [{"name": "DevOps"}, {"name": "QA"}]
check("team without a builder: the non-QA member still gets it", api_v2._direct_member("x", S4) == "DevOps")
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
