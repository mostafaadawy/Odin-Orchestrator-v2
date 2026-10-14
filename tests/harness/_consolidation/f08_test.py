#!/usr/bin/env python3
"""F-08 test (no LLM): a project is addressed by its ID, never by its name. Writes into a folder named after the
project NAME (the S1 bug) or into another project's folder are refused and explained; prompts carry the ID.
python f08_test.py <root> <iso_root>"""
import sys, os, re, json, pathlib
root = pathlib.Path(sys.argv[1]).resolve(); iso = pathlib.Path(sys.argv[2]); os.chdir(root); sys.path.insert(0, str(root / "server"))
import projects, api_v2
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
p = projects.create_project("Supabase Customers r4", "customers + orders", identifier="customer-orders-internal-app-rep-4")
P = p["id"]; F = p.get("localPath") or ""
def out(files=(), cmds=()):
    return api_v2._outside_paths(P, {"files": [{"path": f} for f in files], "commands": [{"cmd": c, "where": "local"} for c in cmds]}, F)
# the REAL S1 r4 proposal paths
s1 = (iso / "_consolidation/results/S1_r4.json").read_text()
real = sorted(set(re.findall(r"workspace/projects/supabase-customers-r4/[A-Za-z0-9_./-]+", s1)))[:12]
r = out(files=real)
check(f"1: the real S1 r4 proposal ({len(real)} paths into the NAME folder) is refused", len(real) > 0 and len(r) == len(real), (real[:3], r[:3]))
check("2: ...and the refusal says it is the project NAME and gives the right id", bool(r) and "project NAME" in r[0] and P in r[0], r[:1])
r = out(files=["workspace/projects/revealer-6978/code/x.py"])
check("3: a write into ANOTHER project's folder is refused", len(r) == 1 and "another project's folder" in r[0], r)
check("4: a write into this project's own folder is allowed", not out(files=[f"workspace/projects/{P}/code/app.ts", f"{F}/web/page.tsx"]))
check("5: a write into workspace/shared is allowed", not out(files=["workspace/shared/utils/x.py"]))
r = out(cmds=["mkdir -p workspace/projects/supabase-customers-r4/frontend && cp a.txt workspace/projects/supabase-customers-r4/"])
check("6: a command that creates the NAME folder is refused (each segment)", len(r) == 2 and all("project NAME" in x for x in r) and "project NAME" in r[0], r)
check("7: a command inside the own folder is allowed", not out(cmds=[f"mkdir -p workspace/projects/{P}/code/frontend"]))
o = api_v2._brain_orientation(P, "Fullstack")
check("8: the chat brain is told the project ID and folder", f"PROJECT ID: {P}" in o and "never the project name" in o, o[:300])
src = (root / "server/api_v2.py").read_text()
check("9: every orchestration prompt that names the project also gives its ID", src.count("(project id: {pid} — folders and paths use this ID, never the name)") >= 8)
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
