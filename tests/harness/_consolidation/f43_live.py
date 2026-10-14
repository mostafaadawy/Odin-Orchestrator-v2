#!/usr/bin/env python3
"""F-43/F-44 live A/B (plan login; auth checked by the server's R-ZC guard): the same member-chat question in
legacy900 and in full mode. Writes results/f43_live.json."""
import sys, os, json, pathlib, time
R = pathlib.Path(__file__).resolve().parent.parent; sys.path.insert(0, str(R / "server")); sys.path.insert(0, str(R / "_consolidation"))
import scenarios, agent_rules
LEDGER = R / "_consolidation/results/claude_calls.jsonl"
def spent():
    return sum(json.loads(l).get("cost_usd") or 0 for l in LEDGER.read_text().splitlines() if l.strip())
Q = ("Before you start any work: list, word for word, every rule you must follow as this agent, and say which "
     "agent's file they come from. Do NOT run any command, do not read any project data — answer only.")
SCOPE = "member:redberry-continuous-soc:Security Operations Investigator"
out = {}
for m in ("legacy900", "full"):
    agent_rules.set_mode(m); s0 = spent(); t0 = time.time()
    rec = scenarios.chat(SCOPE, Q)
    out[m] = {"chat": rec, "sec": round(time.time() - t0, 1), "reported_usage_usd_not_charged": round(spent() - s0, 4)}
agent_rules.set_mode("full")
(R / "_consolidation/results/f43_live.json").write_text(json.dumps(out, indent=1, ensure_ascii=False))
print(json.dumps({m: {k: v for k, v in out[m].items() if k != "chat"} for m in out}))
