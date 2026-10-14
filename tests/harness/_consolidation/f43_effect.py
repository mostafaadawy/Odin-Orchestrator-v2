#!/usr/bin/env python3
"""F-43 effect table (no LLM): how many of each agent's rule lines reach its prompt, legacy900 vs full. Run in a root."""
import os, sys, re, json
sys.path.insert(0, "server")
import api_v2, agent_rules
rows = []
for a in ["CTO Orchestrator", "HubSpot", "Security Operations Investigator", "Security Intelligence & Threat-Hunting Architect", "Fullstack", "QA", "DevOps"]:
    os.environ["ODIN_AGENT_RULES_MODE"] = "legacy900"; o = api_v2._orientation_block(a)
    os.environ["ODIN_AGENT_RULES_MODE"] = "full"; n = api_v2._orientation_block(a)
    d = [x for x in sorted(os.listdir("workspace/agents")) if re.sub("[^a-z0-9]", "", x) == re.sub("[^a-z0-9]", "", a.lower())][0]
    r = agent_rules.extract(open(f"workspace/agents/{d}/capability.md").read()); tot = r["must_honor"] + r["custom_rules"]
    k = lambda l: re.sub(r"^\s*-\s*", "", l)[:50]
    rows.append({"agent": a, "must_honor": len(r["must_honor"]), "custom": len(r["custom_rules"]),
                 "reach_legacy900": sum(k(l) in o for l in tot), "reach_full": sum(k(l) in n for l in tot), "block_chars": len(n) - len(o)})
for x in rows:
    print(f"{x['agent']}: {x['must_honor']} Must honor + {x['custom']} Custom | reach prompt: legacy900 {x['reach_legacy900']}, full {x['reach_full']} | +{x['block_chars']} chars")
json.dump(rows, open(sys.argv[1], "w"), indent=1)
