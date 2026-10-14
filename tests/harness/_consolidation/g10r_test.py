#!/usr/bin/env python3
"""G10 rules test (no LLM): creating a project, setting up a SOC project, or saving a rule in one project must
NEVER remove a rule saved by another project (the 2026-07-19 v1 incident: a new SOC project wiped 8 agents)."""
import sys, os, pathlib
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
import projects, agents_registry as ar, soc_blueprint
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
cap = lambda a: (root / "workspace/agents" / ar._slug(a) / "capability.md").read_text()
A = projects.create_project("G10R A", "app", members=[{"name": "Fullstack", "role": "Full-Stack Engineer"}, {"name": "QA", "role": "QA & Testing"}], identifier="g10r-a")
ar.save_rule(A["id"], "Fullstack", "RULE-A1: keep money handling idempotent")
ar.save_rule(A["id"], "QA", "RULE-A2: never use real PII in tests")
B = projects.create_project("G10R B", "another app", members=[{"name": "Fullstack", "role": "Fullstack"}, {"name": "QA", "role": "QA"}], identifier="g10r-b")
check("1: creating project B keeps A's Fullstack rule", "RULE-A1" in cap("Fullstack"))
check("2: creating project B keeps A's QA rule", "RULE-A2" in cap("QA"))
ar.save_rule(B["id"], "Fullstack", "RULE-B1: prefer server components")
check("3: saving a rule in B adds B's rule", "RULE-B1" in cap("Fullstack"))
check("4: ...and keeps A's rule", "RULE-A1" in cap("Fullstack"))
ar.update_agent(B["id"], "QA", rules=[{"rule": "RULE-B2: run the smoke suite"}])
check("5: editing QA's rules in B keeps A's QA rule", "RULE-A2" in cap("QA") and "RULE-B2" in cap("QA"))
# the real incident: rules saved on SOC agents in one SOC project, then a SECOND SOC project is set up
S1 = projects.create_project("G10R SOC1", "soc", members=[], identifier="g10r-soc1"); soc_blueprint.provision(S1["id"])
names = [a["name"] for a in ar.list_agents(S1["id"])]
sec = [n for n in names if n not in ("Fullstack", "QA")][:3]
for i, n in enumerate(sec):
    ar.save_rule(S1["id"], n, f"RULE-SOC-{i}: evidence before action")
S2 = projects.create_project("G10R SOC2", "soc 2", members=[], identifier="g10r-soc2"); soc_blueprint.provision(S2["id"])
kept = [n for i, n in enumerate(sec) if f"RULE-SOC-{i}" in cap(n)]
check("6: setting up a second SOC project keeps every SOC agent's saved rule", len(sec) >= 1 and kept == sec, (sec, kept))
before_n = cap("Fullstack").count("RULE-A1")
projects.create_project("G10R C", "third", members=[{"name": "Fullstack", "role": "Fullstack"}], identifier="g10r-c")
check("7: another project creation does not duplicate or drop rules", cap("Fullstack").count("RULE-A1") == before_n and "RULE-B1" in cap("Fullstack"))
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
