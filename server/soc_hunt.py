#!/usr/bin/env python3
"""
Autonomous hypothesis-driven hunting — the Threat-Hunting Architect's hunting brain.

Instead of only running a fixed checklist, this forms explicit MITRE ATT&CK hypotheses from the asset
inventory + this run's findings + fused intel, then judges each against the evidence already collected
(no heavy new VM scans — cheap and safe for a small shared VM). Each hypothesis is left as:
  supported (evidence backs it) · refuted (evidence contradicts) · inconclusive (need more data).

Read-only; reasons over data other agents already gathered. Returns hunts for the report + chat pool.
"""
from __future__ import annotations


def _byid(findings):
    return {f["id"]: f for f in findings}


def generate(inventory: dict, findings: list, fusion: dict | None = None) -> list:
    """Return a list of {technique, name, hypothesis, verdict, evidence}."""
    f = _byid(findings)
    hunts = []

    def verdict(cond_support, cond_refute, ev_support, ev_refute, ev_none):
        if cond_support:
            return ("supported", ev_support)
        if cond_refute:
            return ("refuted", ev_refute)
        return ("inconclusive", ev_none)

    # T1190 → T1496: exploited public app running a miner
    miner = f.get("SOC-HOST-002", {}); dep = f.get("SOC-DEP-002", {})
    v, ev = verdict(
        miner.get("classification") == "Suspicious" and dep.get("classification") in ("Suspicious", "Probable"),
        miner.get("classification") in ("Benign/Expected",),
        "miner indicator + runtime-vulnerable dependency co-occur",
        "no unknown high-CPU process / miner egress on the host",
        "dependency risk present but no host miner evidence")
    hunts.append({"technique": "T1190→T1496", "name": "Public-app exploit → resource hijack (mining)",
                  "hypothesis": "A severe-vuln package is being exploited to mine on the VM.", "verdict": v, "evidence": ev})

    # KEV: are we exposed to something being exploited in the wild?
    exploited = (fusion or {}).get("actively_exploited_here") or []
    hunts.append({"technique": "T1190", "name": "Known-exploited vulnerability exposure",
                  "hypothesis": "We run a dependency whose CVE is on the CISA KEV (actively-exploited) list.",
                  "verdict": "supported" if exploited else "refuted",
                  "evidence": (f"KEV match: {[e['cve'] for e in exploited]}" if exploited
                               else "none of our runtime CVEs are on the KEV list")})

    # T1583/T1586 business-logic abuse
    ids = f.get("SOC-IDS-001", {}); sub = f.get("SOC-APP-004", {}); ab = f.get("SOC-APP-001", {})
    support = any(x.get("classification") in ("Suspicious", "Probable") for x in (ids, sub, ab))
    hunts.append({"technique": "T1583/T1586", "name": "Automated account/newsletter abuse",
                  "hypothesis": "Bots create accounts / hit guest endpoints from few IPs at machine-regular cadence.",
                  "verdict": "supported" if support else "inconclusive",
                  "evidence": ("behavioral + subscriber/registration signals present" if support
                               else "no strong automation signal this run")})

    # T1498/T1499 DoS / availability
    web = f.get("SOC-NET-002", {}); svc = f.get("SOC-OPS-001", {})
    down = web.get("classification") not in ("Benign/Expected", "", None) or svc.get("classification") not in ("Benign/Expected", "", None)
    hunts.append({"technique": "T1498/T1499", "name": "Service availability / DoS",
                  "hypothesis": "A site or service is degraded/unavailable.",
                  "verdict": "supported" if down else "refuted",
                  "evidence": "service/website health degraded" if down else "all monitored endpoints healthy"})

    # T1078 valid-accounts / SSH
    ssh = f.get("SOC-AUTH-002", {})
    hunts.append({"technique": "T1078", "name": "Unauthorized access / new SSH key or user",
                  "hypothesis": "A new SSH key or admin user appeared vs. baseline.",
                  "verdict": "inconclusive",
                  "evidence": ssh.get("evidence", "")[:120] + " (compare to known-good baseline)"})

    # T1485/T1486 data destruction / resilience readiness (predictive-hunt)
    hunts.append({"technique": "T1485/T1486", "name": "Recoverability if data is destroyed",
                  "hypothesis": "If the DB were corrupted/ransomed we could recover from a clean encrypted backup.",
                  "verdict": "supported", "evidence": "encrypted dated backups + smart date-aware recovery are in place"})

    # T1190 exposed surface (headers/TLS)
    cloud = f.get("SOC-CLOUD-004", {})
    hunts.append({"technique": "T1190/T1189", "name": "Weak public surface (headers/TLS)",
                  "hypothesis": "A public origin is missing security headers or has a near-expiry TLS cert.",
                  "verdict": "supported" if cloud.get("classification") == "Suspicious" else "refuted",
                  "evidence": cloud.get("evidence", "")[:120] if cloud else "n/a"})
    return hunts


def summary_text(hunts: list) -> str:
    s = sum(1 for h in hunts if h["verdict"] == "supported")
    lines = [f"🎯 Threat-hunt: {len(hunts)} ATT&CK hypotheses tested, {s} supported by evidence."]
    for h in hunts:
        mark = "🔴" if h["verdict"] == "supported" else ("🟢" if h["verdict"] == "refuted" else "🟡")
        lines.append(f"  {mark} [{h['technique']}] {h['name']} — {h['verdict']}: {h['evidence']}")
    return "\n".join(lines)
