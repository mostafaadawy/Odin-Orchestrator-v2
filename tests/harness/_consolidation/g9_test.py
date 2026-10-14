#!/usr/bin/env python3
"""G9 test (no LLM): the per-project credential choice is recorded (agent_scope + connectors/ ref), never in
shared/oth/.cred; secret stores are never a write target. python g9_test.py <root>"""
import sys, os, pathlib, json, hashlib
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
import projects, workspace_mw as mw
WS = root / "workspace"; fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
cred = WS / "shared" / "oth" / ".cred"
h0 = hashlib.sha256(cred.read_bytes()).hexdigest() if cred.exists() else None
S3 = ("Email reporting for our second brand: read-only Klaviyo reporting, but this brand uses a DIFFERENT Klaviyo "
      "account than our existing email project. Its key will be stored as KLAVIYO_KEY_BRAND2 (dummy value for now). "
      "Never use the default Klaviyo key for this project.")
check("1: the choice is read from the brief", ("klaviyo", "KLAVIYO_KEY_BRAND2") in mw.credential_choice_from_text(S3))
p = projects.create_project("G9 Brand Two", S3, members=[{"name": "Email", "role": "Email Specialist"}, {"name": "Analytics", "role": "Analytics"}], identifier="g9-brand-two")
rows = mw.list_agent_scope(p["id"])
check("2: agent_scope row for the agent that uses Klaviyo (Email)", any(r["agent"] == "Email" and r["service"] == "klaviyo" and r["credential_ref"] == "KLAVIYO_KEY_BRAND2" for r in rows), rows)
check("3: no row for an agent that does not use Klaviyo (Analytics)", not any(r["agent"] == "Analytics" for r in rows), rows)
ref = WS / "projects" / p["id"] / "connectors" / "klaviyo.credential-ref.json"
d = json.loads(ref.read_text()) if ref.exists() else {}
check("4: reference stored in the project's OWN connectors/ folder", d.get("credential_ref") == "KLAVIYO_KEY_BRAND2", d)
check("5: the reference file holds no secret value", set(d) <= {"service", "credential_ref", "agents", "source", "recorded", "note"})
check("6: shared/oth/.cred untouched", (hashlib.sha256(cred.read_bytes()).hexdigest() if cred.exists() else None) == h0)
g = mw.agent_scope_guard(p["id"], "Email")
check("7: at run time the agent is told to use the scoped credential (credential_source=delta)", "KLAVIYO_KEY_BRAND2" in g and "credential_source=delta" in g)
p2 = projects.create_project("G9 Plain", "a normal email reporting project using our usual Klaviyo account", members=[{"name": "Email", "role": "Email Specialist"}], identifier="g9-plain")
check("8: no different key named -> nothing recorded (default stays)", not mw.list_agent_scope(p2["id"]))
import api_v2
P = p["id"]; F = p.get("localPath") or ""
out = lambda files: api_v2._outside_paths(P, {"files": [{"path": x} for x in files], "commands": []}, F)
check("9: a proposal writing shared/oth/.cred is refused", out(["workspace/shared/oth/.cred"]))
check("10: a proposal writing a .env file in the project is refused", out([f"workspace/projects/{P}/code/.env"]))
check("10b: a .env.example template (no secrets) is allowed", not out([f"workspace/projects/{P}/code/.env.example"]))
check("11: the project's connectors/ reference file is allowed", not out([f"workspace/projects/{P}/connectors/klaviyo.credential-ref.json"]))
mw.record_credential_choice(P, "klaviyo", "KLAVIYO_KEY_BRAND3", source="run")
check("12: a choice stated in a RUN updates the record", any(r["credential_ref"] == "KLAVIYO_KEY_BRAND3" for r in mw.list_agent_scope(P)))
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
