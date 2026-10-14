#!/usr/bin/env python3
"""
Threat-Intelligence Updater — the Security Intelligence & Threat-Hunting Architect's real capability.

Pulls CURRENT vulnerability intelligence for OUR ACTUAL stack from a professional vulnerability database
(OSV.dev — Google's Open Source Vulnerabilities, aggregating GHSA/NVD/npm advisories), triages each by
REACHABILITY (runtime vs dev), prioritizes, and writes/updates protocols in the shared SOC knowledge base.
Read-only; never touches production. Falls back gracefully offline (reports "Data unavailable").
"""
from __future__ import annotations
import json, urllib.request, pathlib, datetime, re

OSV = "https://api.osv.dev/v1/querybatch"
OSV_VULN = "https://api.osv.dev/v1/vulns/"

def _resolved_versions(lock_path: pathlib.Path, runtime_names: set) -> dict:
    """Parse package-lock.json → {name: (version, is_runtime)} for installed packages."""
    out = {}
    try:
        d = json.loads(lock_path.read_text())
    except Exception:
        return out
    pkgs = d.get("packages") or {}
    if pkgs:  # lockfile v2/v3
        for path, meta in pkgs.items():
            if not path.startswith("node_modules/"):
                continue
            name = path.split("node_modules/")[-1]
            v = meta.get("version")
            if name and v:
                out[name] = (v, name in runtime_names or not meta.get("dev", False))
    else:      # lockfile v1
        for name, meta in (d.get("dependencies") or {}).items():
            if meta.get("version"):
                out[name] = (meta["version"], not meta.get("dev", False))
    return out

def _osv_query(items):
    queries = [{"package": {"ecosystem": "npm", "name": n}, "version": v} for (n, v, _) in items]
    req = urllib.request.Request(OSV, data=json.dumps({"queries": queries}).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=25).read()).get("results", [])

def _severity(vuln_id):
    try:
        d = json.loads(urllib.request.urlopen(OSV_VULN + vuln_id, timeout=15).read())
        sev = d.get("database_specific", {}).get("severity")
        if not sev:
            for s in d.get("severity", []) or []:
                sev = s.get("type"); break
        cve = next((a for a in d.get("aliases", []) if a.startswith("CVE-")), vuln_id)
        fixed = ""
        for aff in d.get("affected", []) or []:
            for rng in aff.get("ranges", []) or []:
                for ev in rng.get("events", []) or []:
                    if ev.get("fixed"):
                        fixed = ev["fixed"]
        return {"id": vuln_id, "cve": cve, "severity": (sev or "UNKNOWN"), "fixed": fixed,
                "summary": (d.get("summary") or "")[:140]}
    except Exception:
        return {"id": vuln_id, "cve": vuln_id, "severity": "UNKNOWN", "fixed": "", "summary": ""}

def update(project_dirs, knowledge_dir: pathlib.Path, max_detail=12):
    """Fetch advisories for the actual installed deps, triage, write intel. Returns a summary dict."""
    today = datetime.date.today().isoformat()
    vuln_pkgs = []   # {name, version, runtime, vuln_ids:[...]}
    total_scanned = 0
    source_state = "Checked and healthy"
    for d in project_dirs:
        d = pathlib.Path(d)
        pkgjson = d / "package.json"
        lock = d / "package-lock.json"
        if not lock.exists():
            source_state = "Partially checked"
            continue
        runtime = set()
        try:
            pj = json.loads(pkgjson.read_text()); runtime = set((pj.get("dependencies") or {}).keys())
        except Exception:
            pass
        resolved = _resolved_versions(lock, runtime)
        items = [(n, v, rt) for n, (v, rt) in resolved.items()]
        total_scanned += len(items)
        try:
            for i in range(0, len(items), 100):
                chunk = items[i:i+100]
                res = _osv_query(chunk)
                for (n, v, rt), r in zip(chunk, res):
                    vulns = r.get("vulns") or []
                    if vulns:
                        vuln_pkgs.append({"name": n, "version": v, "runtime": rt,
                                          "vuln_ids": [x.get("id") for x in vulns]})
        except Exception as e:
            source_state = "Data unavailable"
            break

    # prioritize: runtime-reachable first, then by vuln count
    vuln_pkgs.sort(key=lambda p: (not p["runtime"], -len(p["vuln_ids"])))
    # enrich the top few with severity/CVE/fixed
    details = []
    for p in vuln_pkgs[:max_detail]:
        sev = [_severity(vid) for vid in p["vuln_ids"][:3]]
        worst = max((s["severity"] for s in sev), default="UNKNOWN")
        details.append({**p, "worst_severity": worst, "advisories": sev})

    runtime_vulnerable = [p for p in vuln_pkgs if p["runtime"]]
    summary = {"date": today, "packages_scanned": total_scanned,
               "vulnerable_packages": len(vuln_pkgs), "runtime_vulnerable": len(runtime_vulnerable),
               "source": "OSV.dev (GHSA/NVD/npm)", "source_state": source_state,
               "top": details}

    # write the live intel into the knowledge base (Architect updates the shared KB)
    lines = [f"# Live Dependency Threat Intelligence  (source: OSV.dev · {today})", "",
             f"- Packages scanned: {total_scanned}", f"- Vulnerable packages: {len(vuln_pkgs)} "
             f"(runtime-reachable: {len(runtime_vulnerable)})", f"- Data-source state: {source_state}", "",
             "## Prioritized (runtime-reachable first)", "",
             "| Package | Version | Reachability | Vulns | Worst | Example CVE | Fixed in |",
             "|---|---|---|---|---|---|---|"]
    for p in details:
        adv = p["advisories"][0] if p["advisories"] else {"cve": "", "fixed": ""}
        lines.append(f"| {p['name']} | {p['version']} | {'runtime' if p['runtime'] else 'dev'} "
                     f"| {len(p['vuln_ids'])} | {p['worst_severity']} | {adv.get('cve','')} | {adv.get('fixed','') or '—'} |")
    lines += ["", "## Triage rule (do NOT report presence as compromise)",
              "For each: is it runtime? externally reachable? vulnerable path used? fixed version available? "
              "upgrade breakage? Prioritize Exploitable-in-env > Likely > Installed-not-reachable. "
              "Presence of a CVE is NOT compromise — reachability + evidence required to escalate.",
              "", f"_Last updated by the Security Intelligence & Threat-Hunting Architect: {today}_"]
    try:
        (knowledge_dir).mkdir(parents=True, exist_ok=True)
        (knowledge_dir / "live-dependency-intel.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass
    return summary

if __name__ == "__main__":
    import pathlib as _p
    home = _p.Path.home()
    dirs = [home / "Desktop/VolatileWorkSpace/organics-backend", home / "Desktop/VolatileWorkSpace/organics-frontend"]
    kb = _p.Path(__file__).resolve().parent.parent / "data/projects/redberry-continuous-soc/soc/knowledge"
    s = update(dirs, kb)
    print(json.dumps({k: v for k, v in s.items() if k != "top"}, indent=2))
    for p in s["top"][:6]:
        print(" ", p["name"], p["version"], "runtime" if p["runtime"] else "dev",
              "vulns=", len(p["vuln_ids"]), "worst=", p["worst_severity"])
