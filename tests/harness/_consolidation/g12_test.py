#!/usr/bin/env python3
"""G12 test (no LLM): EasyPost is recommended per project, added only when chosen; other company agents unchanged."""
import sys, os, pathlib
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
import projects, agents_registry
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
names = lambda p: [a["name"] for a in agents_registry.list_agents(p["id"])]
check("0: EasyPost is a company agent in this copy (the G12 cause)", any(c["name"] == "EasyPost" for c in agents_registry.list_company_agents()))
p1 = projects.create_project("G12 Blog", "a small personal blog", members=[{"name": "Fullstack", "role": "Fullstack"}], identifier="g12-blog")
check("1: a project that did not choose EasyPost does NOT get it", "EasyPost" not in names(p1), names(p1))
p2 = projects.create_project("G12 Shop", "track shipments for our store", members=[{"name": "Fullstack", "role": "Fullstack"}, {"name": "EasyPost", "role": "EasyPost Shipping & Tracking Operator"}], identifier="g12-shop")
check("2: a project whose owner chose EasyPost gets it", "EasyPost" in names(p2), names(p2))
opts = projects.capability_options(p1["id"], "track a parcel with the carrier tracking number via EasyPost")
check("3: EasyPost is RECOMMENDED for a shipping task (not added)", any(o["name"] == "EasyPost" for o in opts["recommended"]) and "EasyPost" not in names(p1), [o["name"] for o in opts["recommended"]])
agents_registry.add_company_agent("Concierge G12", role="Company concierge")
p3 = projects.create_project("G12 Other", "another project", members=[{"name": "Fullstack", "role": "Fullstack"}], identifier="g12-other")
check("4: a company agent that is NOT a catalogue role is still native to every project", "Concierge G12" in names(p3), names(p3))
check("4b: ...and EasyPost still is not", "EasyPost" not in names(p3))
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
