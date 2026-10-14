#!/usr/bin/env python3
"""F-43 test (no LLM). BEFORE root (server f43-start): records each agent's orientation block.
AFTER root: legacy900 must reproduce it BYTE-IDENTICAL (paper v1); full mode adds every Must honor + Custom rule,
capped (Must honor first), truncation noted + logged. python f43_test.py <root> <before|after> <shared_json>"""
import sys, os, json, pathlib
root = pathlib.Path(sys.argv[1]).resolve(); ver = sys.argv[2]; shared = pathlib.Path(sys.argv[3])
os.chdir(root); sys.path.insert(0, str(root / "server"))
os.environ.pop("ODIN_AGENT_RULES_MODE", None)
import api_v2
AGENTS = ["CTO Orchestrator", "Fullstack", "QA", "DevOps", "HubSpot", "Security Operations Investigator",
          "Security Intelligence & Threat-Hunting Architect", "Email", "Sales"]
if ver == "before":
    shared.write_text(json.dumps({a: api_v2._orientation_block(a) for a in AGENTS}, ensure_ascii=False))
    print("recorded the old orientation for", len(AGENTS), "agents"); sys.exit(0)
import agent_rules
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
old = json.loads(shared.read_text())
check("0: default mode is full", agent_rules.mode() == "full")
os.environ["ODIN_AGENT_RULES_MODE"] = "legacy900"
same = [a for a in AGENTS if api_v2._orientation_block(a) == old[a]]
check("1: legacy900 reproduces the old prompt BYTE-IDENTICAL for every agent (paper v1)", len(same) == len(AGENTS), set(AGENTS) - set(same))
os.environ["ODIN_AGENT_RULES_MODE"] = "full"
full = {a: api_v2._orientation_block(a) for a in AGENTS}
cto = full["CTO Orchestrator"]
check("2: full mode — CTO Orchestrator's 5 custom rules all reach the prompt",
      all(k in cto for k in ("Only the CTO presents decisions", "Prevent overlapping", "MUST become an approval request",
                               "two report levels", "Record the owner's decision")), cto[-600:])
fs = full["Fullstack"]
check("3: full mode — Fullstack's restored charter 'Must honor' rules reach the prompt", "Must honor:" in fs and fs.count("\n- ") > old["Fullstack"].count("\n- "))
F44 = {"Security Operations Investigator", "Security Intelligence & Threat-Hunting Architect"}
exc = lambda t: t.split("### YOUR RULES")[0].split("### Shared tools")[0].rstrip()
check("4: full mode keeps the old 900-char excerpt unchanged for every agent except the 2 fixed by F-44 (only ADDS the rules block)",
      all(exc(full[a]) == exc(old[a]) for a in AGENTS if a not in F44), [a for a in AGENTS if a not in F44 and exc(full[a]) != exc(old[a])])
check("4b: ...and for those 2 the excerpt is now their OWN file (was the plain Security agent's)",
      all(a.split()[0] in exc(full[a]) and exc(full[a]) != exc(old[a]) and "# Security — Security & Threat Hunting" in exc(old[a]) for a in F44))
check("5: an agent with no rules gets no rules block", "### YOUR RULES" not in full["Sales"] or "Custom rules:" in full["Sales"])
# cap: a synthetic agent with far more rules than the cap
d = root / "workspace/agents/zz-cap-test"; d.mkdir(parents=True, exist_ok=True)
must = [f"- MUST-{i:03d} " + "x" * 80 for i in range(40)]; cust = [f"- CUST-{i:03d} " + "y" * 80 for i in range(80)]
(d / "capability.md").write_text("# ZZ Cap Test — tester\n\nd\n\n## Must honor\n" + "\n".join(must) + "\n\n## Custom rules\n" + "\n".join(cust) + "\n")
logp = root / "workspace/history/audit-log.jsonl"; n0 = logp.read_text().count("rules-truncated") if logp.exists() else 0
z = api_v2._orientation_block("ZZ Cap Test")
blk = z[z.index("### YOUR RULES"):].split("\n### ")[0] if "### YOUR RULES" in z else ""
check(f"6: the rules block respects the cap ({agent_rules.CAP} chars + header/note)", 0 < len(blk) <= agent_rules.CAP + 300, len(blk))
check("7: every Must honor line is kept before any Custom rule", all(f"MUST-{i:03d}" in blk for i in range(40)) and "CUST-079" not in blk)
check("8: the truncation is stated in the prompt", "more rule line(s) not shown" in blk)
check("9: the truncation is logged (audit-log 'rules-truncated')", logp.exists() and logp.read_text().count("rules-truncated") == n0 + 1)
soi = full["Security Operations Investigator"]
check("12: F-44 full mode — Security Operations Investigator gets ITS OWN file and rules (not the plain Security agent's)",
      "Security Operations Investigator" in soi.split("### Shared tools")[0] and "false-positive analysis" in soi)
sit = full["Security Intelligence & Threat-Hunting Architect"]
check("13: F-44 full mode — Threat-Hunting Architect gets its own rules", "PRESENCE from actual compromise" in sit)
os.environ.pop("ODIN_AGENT_RULES_MODE"); agent_rules.set_mode("legacy900")
check("10: the setting file switches the mode", agent_rules.mode() == "legacy900")
os.environ["ODIN_AGENT_RULES_MODE"] = "full"
check("11: the environment overrides the setting file (reproduction runs cannot pick the wrong mode)", agent_rules.mode() == "full")
(root / "data/agent_rules.json").unlink()
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
