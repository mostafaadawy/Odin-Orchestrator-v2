#!/usr/bin/env python3
"""Strong E2E for RedBerry Continuous SOC — approves NOTHING, makes NO production change.
Runs from the agent bridge shell. Asserts agent coordination, safety, detection, false-positives,
memorizing tracker, multi-format reporting, and the mandatory auto-remediation guard."""
import sys, glob, pathlib, json, time
R = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(R / "server"))
import soc_run, store, scopes, agents_registry, scheduler  # type: ignore
PID = "redberry-continuous-soc"
P = F = 0
def ok(name, cond, detail=""):
    global P, F
    print(("  PASS " if cond else "  FAIL ") + name + ((" — " + detail) if detail else ""))
    P += 1 if cond else 0; F += 0 if cond else 1

print("== 1. Agent coordination (8 non-overlapping agents) ==")
agents = [a["name"] for a in agents_registry.list_agents(PID)]
ok("3 core agents + reporting agent present", all(x in agents for x in
   ["CTO Orchestrator", "Security Intelligence & Threat-Hunting Architect", "Security Operations Investigator", "Reporting & Documentation Agent"]), str(agents))
ok("exactly ONE operational investigator", agents.count("Security Operations Investigator") == 1)
ok("4 new distinct-lane agents present", all(x in agents for x in
   ["Asset, Exposure & Attack-Surface Agent", "Threat Prediction & Prevention Agent",
    "Recovery & Resilience Agent", "Intrusion Detection & Behavioral Analytics Agent"]), str(agents))
ok("no duplicate agents (clean roster)", len(agents) == len(set(agents)) and len(agents) == 8, f"{len(agents)} agents")
# educational: each agent carries a role + description you can inspect/learn from
full = agents_registry.list_agents(PID)
ok("every agent is self-describing (role + description for learning)",
   all(a.get("role") and a.get("description") for a in full))

print("== 2. Mandatory safety guards ==")
s = soc_run.settings()
ok("SOC_AUTO_REMEDIATION_ENABLED == false", s["SOC_AUTO_REMEDIATION_ENABLED"] is False)
ok("SOC starts in monitor-and-report-only mode", s["SOC_MONITOR_ONLY"] is True)
ok("read-only guard refuses a mutating command", soc_run._ssh_ro("systemctl restart nginx")[0] is False and
   "REFUSED" in soc_run._ssh_ro("systemctl restart nginx")[1])

print("== 3. Reset registry, then run (memorizing tracker) ==")
store.write_json(f"projects/{PID}/soc_findings_registry.json", {"items": {}})
r1 = soc_run.run(PID, mode="full", test=True)
reg = store.read_json(f"projects/{PID}/soc_findings_registry.json", {"items": {}})["items"]
ok("run produced findings", len(r1["findings"]) >= 5, f"{len(r1['findings'])} findings")
ok("RedBerry abuse detected (SOC-APP-001, Probable)",
   any(f["id"] == "SOC-APP-001" and f["classification"] == "Probable" for f in r1["findings"]))
ok("RedBerry NOT called VM compromise", all("compromise" not in f["title"].lower() for f in r1["findings"]))
ok("issue entered the registry as tracked", "SOC-APP-001" in reg)

print("== 4. Approval discipline (nothing approved / executed) ==")
ok(">=1 approval request raised", r1["approvals_made"] >= 1)
ok("approvals auto-denied in test/monitor (no execution)", r1["monitor_only"] is True and r1["test"] is True)
msgs = scopes.all_messages(f"project:{PID}")
denied = [m for m in msgs if "Decision: DENIED" in (m.get("content") or "")]
ok("approval message shows DENIED — no production change", len(denied) >= 1)
selfapprove = [m for m in msgs if "approve its own" in (m.get("content") or "").lower()]
ok("states no agent approves its own action", len(selfapprove) >= 1)

print("== 5. False-positive handling ==")
benign = [f for f in r1["findings"] if f["classification"] in ("Benign/Expected", "Informational")]
ok("benign checks classified Benign/Expected (not confirmed)", len(benign) >= 3, f"{len(benign)} benign")

print("== 6. Owner resolves a finding -> tracker remembers it ==")
soc_run.set_finding_status(PID, "SOC-APP-001", "resolved", "mitigations approved+deployed")
r2 = soc_run.run(PID, mode="full", test=True)
# after resolve, SOC-APP-001 is re-detected in run2 -> registry marks it reopened (owner_status open)
reg2 = store.read_json(f"projects/{PID}/soc_findings_registry.json", {"items": {}})["items"]
ok("resolved-then-redetected is reopened (memory works)", reg2["SOC-APP-001"].get("owner_status") == "open" and reg2["SOC-APP-001"].get("reopened_ts"))

print("== 7. Multi-format branded reporting (agent capability) ==")
rdir = soc_run._socdir(PID) / "reports"
for ext in ("pdf", "docx", "md", "pptx"):
    files = list(rdir.glob(f"*.{ext}"))
    ok(f"{ext.upper()} report generated", len(files) >= 1)
pdf = sorted(rdir.glob("*.pdf"))[-1].read_bytes()
ok("PDF is a valid document (with brand)", pdf[:5] == b"%PDF-")

print("== 8. Persistence & schedule ==")
ok("last-run state persisted", bool(store.read_json(f"projects/{PID}/soc_last_run.json", {})))
t = scheduler.list_tasks(PID)[0]
ok("daily schedule = 23:00 America/New_York", t["schedule"].get("hhmm") == "23:00" and t["schedule"].get("tz") == "America/New_York")
ok("catch-up enabled (survives desktop being off)", t.get("catchup") is True)

print("== 9. Deep checks present (behavior, clickjacking, miner, ports, forensics) ==")
ids = [f["id"] for f in r1["findings"]]
for cid, label in [("SOC-IDS-001", "behavioral intrusion (UEBA)"), ("SOC-WEB-005", "clickjacking/iframe"),
                   ("SOC-HOST-002", "crypto-miner hunt"), ("SOC-CLOUD-003", "port/firewall hardening"),
                   ("SOC-APP-004", "subscriber forensics")]:
    ok(f"{label} check ran ({cid})", cid in ids)

print("== 10. Behavioral detection: same-IP-many-accounts + owner FP-safety ==")
import soc_behavior  # type: ignore
bres = soc_behavior.analyze(PID, test=True)
ok("behaviorally-bad IP detected (203.0.113.7)", "203.0.113.7" in bres["bad_ips"])
ok("owner dynamic IP excluded from flagging (no false positive)", "OWNER" in bres["owner_excluded"] and "OWNER" not in bres["bad_ips"])
ok("UFW block recommendation is present but approval-gated (never auto)",
   bres["ufw_recommendation"] is not None and "approval-gated" in bres["ufw_recommendation"]["action"])

print("== 11. Prediction & prevention (forward-looking, evidence-linked) ==")
ok("predictions produced", len(r1.get("predictions", [])) >= 3, f"{len(r1.get('predictions', []))}")
ok("each prediction has likelihood + prevention + attack vector",
   all(p.get("likelihood") and p.get("prevention") and p.get("attack_vector") for p in r1["predictions"]))

print("== 12. Recovery: encrypted backup + SMART date-aware recovery + non-harmful capture ==")
import soc_recovery, time as _t, datetime as _dt  # type: ignore
meta = soc_recovery.ensure_key()
ok("encryption key held on LOCAL desktop only", "local desktop only" in meta["location"] and meta["crypto_available"])
blob, algo = soc_recovery._encrypt(b"db-dump")
from cryptography.fernet import Fernet  # type: ignore
ok("backup encryption round-trips (Fernet/AES)", Fernet(soc_recovery._key_path().read_bytes()).decrypt(blob) == b"db-dump")
ok("backup CAPTURE is non-harmful → no approval required", soc_recovery.run_backup.__defaults__[-1] is True)
# smart date-aware selection: pick newest CLEAN backup BEFORE the problem, not after
now = _t.time()
soc_recovery._save_reg(PID, {"backups": [
    {"file": "A.enc", "ts": now-4*86400, "date": _dt.datetime.fromtimestamp(now-4*86400).isoformat(), "health": "clean"},
    {"file": "B.enc", "ts": now-3*86400, "date": _dt.datetime.fromtimestamp(now-3*86400).isoformat(), "health": "clean"},
    {"file": "C.enc", "ts": now-1*86400, "date": _dt.datetime.fromtimestamp(now-1*86400).isoformat(), "health": "clean"}]})
plan = soc_recovery.smart_recovery_plan(PID, problem_date=_dt.datetime.fromtimestamp(now-2*86400).isoformat())
ok("smart recovery picks pre-problem clean backup (B, not post-problem C)",
   plan["chosen_backup"] and plan["chosen_backup"]["file"] == "B.enc")
ok("restore is APPROVAL-GATED (owner executes)", "APPROVAL-GATED" in plan["restore"])
soc_recovery._save_reg(PID, {"backups": []})

print("== 13. Multi-cloud/stack inventory + reverse-search targeting + CTO scope recs ==")
rs = r1.get("inventory_reverse_search", {})
ok("reverse-search targets our real stacks", any("Next.js" in f for f in rs.get("frameworks", [])))
import soc_inventory  # type: ignore
ok("provider models cover multiple clouds (extensible)",
   all(p in soc_inventory.PROVIDERS for p in ["azure-vm", "aws-ec2", "godaddy", "hostinger", "cloudflare"]))
ok("CTO produced scope recommendation(s)", len(r1.get("scope_recommendations", [])) >= 1)

print("== 14. White-scope methodology + evidence-based correlation ==")
ok("correlation/narrow-down produced (root cause, not fake reason)", len(r1.get("correlations", [])) >= 1)
msgs2 = scopes.all_messages(f"project:{PID}")
ok("white-scope discovery announced (NIST/PICERL/funnel)",
   any("WHITE-SCOPE" in (m.get("content") or "") for m in msgs2))
ok("educational team charter posted (roles + handoffs)",
   any("SOC team & hand-offs" in (m.get("content") or "") for m in msgs2))

print("== 15. Humanized report section (read-this-first) ==")
mds = sorted((soc_run._socdir(PID) / "reports").glob("*.md"))
mdtext = mds[-1].read_text() if mds else ""
ok("report has a plain-language humanized section", "In Plain Words" in mdtext)
ok("report includes prediction & prevention section", "Prediction & Prevention" in mdtext)
ok("report includes resilience & recovery section", "Resilience & Recovery" in mdtext)

print("== 16. Generic third-party quota + multi-cloud surface + escrow ==")
import soc_quota, soc_recovery  # type: ignore
q = soc_quota.check(PID, abuse_active=True)
ok("quota monitor is generic (any provider, extensible)", "GENERIC" in soc_quota.PROVIDER_TEMPLATES and len(soc_quota.PROVIDER_TEMPLATES) >= 6)
ok("quota flags providers at risk when abuse is active", len(q["at_risk"]) >= 1)
ids16 = [f["id"] for f in r1["findings"]]
ok("multi-cloud surface check ran (SOC-CLOUD-004)", "SOC-CLOUD-004" in ids16)
ok("third-party quota check ran (SOC-EXT-006)", "SOC-EXT-006" in ids16)
ok("key escrow is approval-gated (not automatic)", soc_recovery.escrow_key_to_vm(PID, approved=False)["status"] == "approval-required")

print("== 17. Detection brain: intel fusion + autonomous hunting ==")
ids17 = [f["id"] for f in r1["findings"]]
ok("fused-intel check ran (SOC-INTEL-007)", "SOC-INTEL-007" in ids17)
ok("threat hunt produced ATT&CK hypotheses", len(r1.get("hunts", [])) >= 5)
ok("each hunt has technique + verdict + evidence",
   all(h.get("technique") and h.get("verdict") and "evidence" in h for h in r1["hunts"]))
import soc_hunt, soc_intel_fusion  # type: ignore
ok("hunt verdicts are evidence-based (supported/refuted/inconclusive)",
   all(h["verdict"] in ("supported", "refuted", "inconclusive") for h in r1["hunts"]))
ok("intel fusion module exposes KEV + abuse.ch fusion", hasattr(soc_intel_fusion, "fuse") and hasattr(soc_intel_fusion, "fetch_kev"))

print("== 18. Reproducible capability: blueprint provisions a full SOC on ANY project ==")
import soc_blueprint, agents_registry as _ar, store as _st, scheduler as _sch, shutil, pathlib as _pl
ok("security intent is recognized", soc_blueprint.is_security_intent("create a very advanced security company"))
_tpid = "e2e-blueprint-check"
_prov = soc_blueprint.provision(_tpid, name="E2E Blueprint Check")
_roster = [a["name"] for a in _ar.list_agents(_tpid)]
ok("blueprint registers all 8 non-overlapping agents", len(_prov["agents"]) == 8 and len(set(_roster)) == 8)
ok("blueprint creates a recurring schedule (Egypt default tz)",
   isinstance(_prov["schedule"], dict) and (_prov["schedule"].get("tz") in (None, "Africa/Cairo") or _prov["schedule"].get("existing")))
_rb = soc_run.run(_tpid, mode="full", test=True)
ok("SOC runs identically on a brand-new project (findings + reports)",
   len(_rb["findings"]) >= 10 and all(not str(v).startswith("error") for v in _rb["reports"].values()))
# cleanup
_p = _st.read_json("projects.json", {"projects": []}); _p["projects"] = [x for x in _p["projects"] if x.get("id") != _tpid]; _st.write_json("projects.json", _p)
for _t in _sch.list_tasks(_tpid): _sch.delete_task(_t["id"])
shutil.rmtree(_st.DATA / "projects" / _tpid, ignore_errors=True)

print(f"\n==== E2E RESULT: {P} passed, {F} failed ====")
sys.exit(0 if F == 0 else 1)
