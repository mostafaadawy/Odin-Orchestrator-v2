#!/usr/bin/env python3
"""G10 test (no LLM): reusing an existing agent in another project must not overwrite its SHARED role, title,
description, skills or rules; the project's own role is kept in that project's roster."""
import sys, os, pathlib
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
import projects, agents_registry, psycopg2
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
cap = root / "workspace/agents/security/capability.md"
before = cap.read_text()
title0 = before.splitlines()[0]
def db_role(aid):
    c = psycopg2.connect(dbname="odin_core_con"); cu = c.cursor()
    cu.execute("SELECT role, description FROM agents WHERE id=%s", (aid,)); r = cu.fetchone(); c.close(); return r
role0 = db_role("security")
check("0: baseline shared title is 'Security — Security & Threat Hunting'", title0 == "# Security — Security & Threat Hunting", title0)
pA = projects.create_project("G10 A", "security review of a small app", members=[{"name": "Security", "role": "Security & Threat Hunting"}], identifier="g10-a")
agents_registry.save_rule(pA["id"], "Security", "RULE-FROM-A: never print secrets")
afterA = cap.read_text()
check("1: a rule saved in project A is in the shared file", "RULE-FROM-A" in afterA)
pB = projects.create_project("G10 B", "another project reusing Security", members=[{"name": "Security", "role": "Security", "description": "B-only description"}], identifier="g10-b")
txt = cap.read_text()
check("2: reuse in B keeps the shared title", txt.splitlines()[0] == title0, txt.splitlines()[0])
check("3: reuse in B keeps the shared description (B's text not written)", "B-only description" not in txt)
check("4: reuse in B keeps A's rule", "RULE-FROM-A" in txt)
check("5: reuse in B keeps the shared DB role/description", db_role("security") == role0, (db_role("security"), role0))
rb = agents_registry.get_agent(pB["id"], "Security") or {}
check("6: B's own role is kept in B's roster", rb.get("role") == "Security", rb.get("role"))
ra = agents_registry.get_agent(pA["id"], "Security") or {}
check("7: A's roster role is unchanged", ra.get("role") == "Security & Threat Hunting", ra.get("role"))
agents_registry.save_rule(pB["id"], "Security", "RULE-FROM-B: log every scan")
agents_registry.update_agent(pB["id"], "Security", skills=["skill-from-B"])
txt = cap.read_text()
check("8: an edit in B adds B's rule and skill", "RULE-FROM-B" in txt and "skill-from-B" in txt)
check("9: ...without removing A's rule or the shared title", "RULE-FROM-A" in txt and txt.splitlines()[0] == title0)
pC = projects.create_project("G10 C", "brand-new agent", members=[{"name": "Zeta Auditor G10", "role": "Zeta Role", "description": "zeta desc"}], identifier="g10-c")
zc = root / "workspace/agents/zeta-auditor-g10/capability.md"
check("10: a NEW agent still gets its own full capability file", zc.exists() and zc.read_text().splitlines()[0] == "# Zeta Auditor G10 — Zeta Role")
check("11: ...and its DB row carries its role", (db_role("zeta-auditor-g10") or [None])[0] == "Zeta Role", db_role("zeta-auditor-g10"))
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
