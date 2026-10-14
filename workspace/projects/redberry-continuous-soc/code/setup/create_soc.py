#!/usr/bin/env python3
"""Create the RedBerry Continuous SOC project inside the platform, with EXACTLY the 3 required agents
(reusing the platform's project + agent conventions). Periodic daily run at 11:00 PM America/New_York."""
import sys, pathlib
R = pathlib.Path("/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2")
sys.path.insert(0, str(R / "server"))
import projects, agents_registry, scheduler  # type: ignore

PID = "redberry-continuous-soc"

# ---- the 3 controlled agents (no overlapping investigators) --------------------------------------
MEMBERS = [
    {"name": "CTO Orchestrator", "role": "CTO Orchestrator", "nature": "operational", "mode": "normal",
     "asset": "soc_engine",
     "description": "Project owner + the ONLY agent that presents final decisions to the human owner. "
                    "Initiates SOC runs, assigns work, prevents overlapping investigations, validates the "
                    "investigator followed the playbook, produces the humanized owner summary + technical "
                    "report, and raises approval requests. Never approves its own action.",
     "rules": [
        "Only the CTO presents decisions to the owner; no other agent talks to the owner directly.",
        "Prevent overlapping/duplicate live investigations — one authoritative investigator only.",
        "Every action with any reasonable chance of affecting production MUST become an approval request first.",
        "Produce two report levels: a brief Owner Summary and an expandable Technical Report.",
        "Record the owner's decision, verify remediation results, preserve audit history."]},
    {"name": "Security Intelligence & Threat-Hunting Architect", "role": "Security Intelligence & Threat-Hunting Architect",
     "nature": "operational", "mode": "theoretical",
     "description": "Owns security knowledge, playbooks, detection logic, threat updates and the shared SOC "
                    "knowledge base. Does NOT touch production. Defines indicators, required evidence, "
                    "false-positive criteria, early-stop rules, data sources, safe commands, remediation "
                    "options + operational impact, and recheck cadences.",
     "rules": [
        "Never modify production systems — knowledge/playbooks/detections only.",
        "Before adding a threat/playbook: search the knowledge base + incident history; update existing "
        "entries when appropriate; create new only when materially different; cross-reference, don't duplicate.",
        "Distinguish vulnerability PRESENCE from actual compromise; define exploitability-in-our-environment.",
        "Every knowledge item carries: id, indicators, required + disconfirming evidence, false-positive "
        "cases, early-stop conditions, data sources, safe commands, operational impact, review cadence."]},
    {"name": "Security Operations Investigator", "role": "Security Operations Investigator",
     "nature": "operational", "mode": "normal", "asset": "soc_engine",
     "description": "The ONE primary operational investigator. Executes APPROVED read-only, non-disruptive, "
                    "evidence-driven hunts; correlates logs (app, nginx, systemd, auth, DB, cloud, deps, "
                    "integrations); classifies findings (informational→confirmed) with confidence/severity, "
                    "false-positive analysis, blast radius; recommends safe next steps + operational effect. "
                    "Owns the SOC run engine asset.",
     "rules": [
        "DEFAULT: read-only, non-disruptive, evidence-driven. Never modify prod (services, DB, firewall, "
        "users, secrets, code, packages, schedules, config) without explicit CTO-workflow approval.",
        "Load playbooks/baseline/history/known-good BEFORE each run; record checked/changed/skipped+why/reused.",
        "Apply early-stop conditions to cut load, noise, cost — without hiding uncertainty.",
        "Every finding includes a false-positive analysis; a ten-minute gap does NOT make activity legitimate."]},
]

def main():
    if projects.get_project(PID):
        print("SOC project already exists:", PID)
    else:
        proj = projects.create_project(
            name="RedBerry Continuous SOC",
            description=("Production-grade continuous multi-agent SOC. Observe -> Correlate -> Verify -> "
                         "Report -> Request approval -> Act only if approved. Monitors cloud infra, VMs, "
                         "apps, DBs, APIs, dependencies and security telemetry; general + incident-specific "
                         "threat hunting; read-only and approval-gated; starts in Monitor-and-report-only mode."),
            members=MEMBERS,
            ptype="operational", stack="operational — SOC (read-only, approval-gated)",
            cadence="periodical",
            periodic={"enabled": True,
                      "schedule": {"kind": "daily", "hhmm": "23:00", "tz": "America/New_York"},
                      "requireApproval": False},
            identifier=PID)
        print("created:", proj["id"], "| members:", proj["members"])

    # tag the SOC engine asset owners + confirm agents
    for a in agents_registry.list_agents(PID):
        print("  agent:", a["name"], "| role:", a.get("role"), "| asset:", a.get("asset") or "-")

if __name__ == "__main__":
    main()
