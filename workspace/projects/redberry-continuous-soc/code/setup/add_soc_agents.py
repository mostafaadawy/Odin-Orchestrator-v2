#!/usr/bin/env python3
"""Add the new non-overlapping SOC agents to the RedBerry Continuous SOC project and sync project.members.
Agents are named by their human-readable ROLE (consistent with 'CTO Orchestrator' etc.). Idempotent; cleans
any short-key duplicates from earlier runs. Each agent carries its distinct asset + educational description."""
import sys, pathlib
R = pathlib.Path(__file__).resolve().parents[5]
sys.path.insert(0, str(R / "server"))
import projects, agents_registry, store  # type: ignore

PID = "redberry-continuous-soc"
CAT = {**projects.ALL_MEMBERS, **projects.OPERATIONAL_MEMBERS}
# catalog keys for the NEW distinct-lane agents (Reporter already exists as 'Reporting & Documentation Agent')
NEW_KEYS = ["AssetSurface", "Predictor", "Recovery", "BehaviorIDS"]
SHORT_DUPES = {"AssetSurface", "Predictor", "Recovery", "BehaviorIDS", "Reporter"}  # remove if present as names

# 1) remove any short-key-named duplicates from earlier runs
doc = store.read_json(f"projects/{PID}/agents.json", {"agents": []})
before = [a["name"] for a in doc.get("agents", [])]
doc["agents"] = [a for a in doc.get("agents", []) if a.get("name") not in SHORT_DUPES]
store.write_json(f"projects/{PID}/agents.json", doc)

# 2) register each new agent under its ROLE name
for key in NEW_KEYS:
    m = CAT.get(key)
    if not m:
        print("MISSING catalog role:", key); continue
    agents_registry.register_agent(PID, m["role"], role=m.get("role", ""), avatar=m.get("avatar", "generic"),
        description=m.get("description", ""), nature=m.get("nature", "operational"),
        mode=m.get("mode", "normal"), asset=m.get("asset", ""), force=True)

# 3) sync project.members to the real roster
agents = agents_registry.list_agents(PID)
names = [a["name"] for a in agents]
projs = store.read_json("projects.json", {"projects": []})
for i, p in enumerate(projs.get("projects", [])):
    if p.get("id") == PID:
        ex = p.get("members", [])
        ex_names = [x.get("name") if isinstance(x, dict) else x for x in ex]
        projs["projects"][i]["members"] = list(dict.fromkeys([*ex_names, *names]))
store.write_json("projects.json", projs)

print("removed dupes:", sorted(set(before) & SHORT_DUPES))
print("SOC agents now:", names)
print("count:", len(names))
