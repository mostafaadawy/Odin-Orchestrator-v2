#!/usr/bin/env python3
"""
SOC Blueprint — the REUSABLE capability that turns ANY project into a full, strong security company.

This is what makes the SOC a first-class AGENT capability rather than a one-off: given a project id, it
provisions the entire team + knowledge base + schedule, so the exact same strong SOC can be created from the
app (by the agent) for a brand-new project — not just the original RedBerry one.

    provision(pid, name=None, tz="Africa/Cairo", run_times=("23:00",))

Idempotent. Registers the 8 non-overlapping security agents from the CORE role catalog, seeds a starter
knowledge base (methodology + playbooks pointers), and creates the recurring monitor-and-report schedule.
"""
from __future__ import annotations
import pathlib, datetime

# The 8-agent security team, by CORE catalog key (all live in projects.OPERATIONAL_MEMBERS).
SECURITY_TEAM = ["SecCTO", "SecArchitect", "SecInvestigator", "AssetSurface", "BehaviorIDS",
                 "Predictor", "Recovery", "Reporter"]


def is_security_intent(text: str) -> bool:
    """Does a project request describe a security company / SOC? (used by intake to offer the blueprint)."""
    t = (text or "").lower()
    kws = ("security company", "soc ", " soc", "security operations", "threat hunt", "threat-hunt",
           "cyber security", "cybersecurity", "penetration", "vulnerability monitoring", "intrusion",
           "security monitoring", "blue team", "incident response", "protect my", "monitor my server security")
    return any(k in t for k in kws)


def provision(pid: str, name: str | None = None, tz: str = "Africa/Cairo", run_times=("23:00",)) -> dict:
    """Make `pid` a full SOC: register the team, seed KB, create the schedule. Returns a summary."""
    import projects, agents_registry, store  # type: ignore
    cat = {**projects.ALL_MEMBERS, **projects.OPERATIONAL_MEMBERS}
    registered = []
    for key in SECURITY_TEAM:
        m = cat.get(key)
        if not m:
            continue
        agents_registry.register_agent(pid, m["role"], role=m.get("role", ""), avatar=m.get("avatar", "generic"),
            description=m.get("description", ""), nature=m.get("nature", "operational"),
            mode=m.get("mode", "normal"), asset=m.get("asset", ""), force=True)
        registered.append(m["role"])

    # sync project.members to the real roster
    try:
        names = [a["name"] for a in agents_registry.list_agents(pid)]
        # the project's OWN canonical manifest (index.json), middleware-indexed — NOT a global registry
        p = store.read_json(f"projects/{pid}/index.json", {}) or {}
        p["id"] = pid
        ex = [x.get("name") if isinstance(x, dict) else x for x in p.get("members", [])]
        p["members"] = list(dict.fromkeys([*ex, *names]))
        store.write_json(f"projects/{pid}/index.json", p)
    except Exception:
        pass

    # seed a starter knowledge base if the project has none yet (methodology + operating principle)
    kb_written = _seed_kb(pid)

    # create the recurring monitor-and-report schedule (calendar kind: multi-time + timezone; catch-up on)
    sched = _ensure_schedule(pid, tz, list(run_times))

    return {"pid": pid, "name": name or pid, "agents": registered, "kb_seeded": kb_written,
            "schedule": sched, "mode": "monitor-and-report-only",
            "note": "Full SOC provisioned. Same capability for any project — created from the app by the agent."}


def _socdir(pid):
    try:
        import soc_run  # type: ignore
        return soc_run._socdir(pid)
    except Exception:
        import store  # type: ignore
        return store.WS / "projects" / pid / "data" / "soc"


def _seed_kb(pid) -> bool:
    try:
        kb = _socdir(pid) / "knowledge"
        kb.mkdir(parents=True, exist_ok=True)
        readme = kb / "00-OPERATING-PRINCIPLE.md"
        if readme.exists():
            return False
        readme.write_text(
            "# SOC Operating Principle\n\n"
            "Observe → Correlate → Verify → Report → Request approval → Act only if approved.\n\n"
            "- Read-only & monitor-and-report-only by default; autonomous remediation DISABLED.\n"
            "- Methodology: NIST SP 800-61 · SANS PICERL · threat-hunting funnel · MITRE ATT&CK.\n"
            "- White-scope wide sweep first, then narrow to evidence — never a fake/surface cause.\n"
            "- False-positive discipline; never turn missing evidence into a healthy verdict.\n"
            "- Intel is filtered to what we actually run (reverse-search) and fused with CISA KEV + abuse.ch.\n"
            f"\n_Provisioned {datetime.date.today().isoformat()} by the SOC blueprint._\n", encoding="utf-8")
        return True
    except Exception:
        return False


def _ensure_schedule(pid, tz, times) -> dict:
    try:
        import scheduler  # type: ignore
        existing = scheduler.list_tasks(pid)
        if existing:
            return {"existing": True, "id": existing[0].get("id")}
        schedule = {"kind": "calendar", "times": times, "tz": tz}
        # a run_cmd pipeline so the recurring run EXECUTES the SOC engine autonomously in monitor mode
        import sys
        py = sys.executable
        root = pathlib.Path(__file__).resolve().parent.parent
        run_cmd = f'"{py}" "{root}/server/soc_run.py" --pid {pid} --mode full --cid {{cid}}'
        t = scheduler.create_task(pid, prompt="Run the SOC monitor-and-report cycle",
                                  schedule=schedule, title="SOC daily monitor", assignee="CTO Orchestrator")
        tid = t.get("id") if isinstance(t, dict) else None
        if tid:
            scheduler.update_task(tid, run_cmd=run_cmd, cwd=str(root), catchup=True)
        return {"created": True, "id": tid, "times": times, "tz": tz}
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import sys
    pid = sys.argv[1] if len(sys.argv) > 1 else "test-soc-blueprint"
    import json
    print(json.dumps(provision(pid), indent=2, ensure_ascii=False))
