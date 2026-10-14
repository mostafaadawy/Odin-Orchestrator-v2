#!/usr/bin/env python3
"""F-39: replay EVERY past proposal in the copy through the F-38 guard (read-only; nothing is changed).
Usage: f39_replay.py [--declare pid=/path ...]   (--declare = a PROPOSED folder, applied in memory only)"""
import sys, os, json, pathlib
R = pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0, str(R / "server"))
import approvals, projects, api_v2
virt = dict(a.split("=", 1) for a in sys.argv[sys.argv.index("--declare") + 1:] if "=" in a) if "--declare" in sys.argv else {}
V2 = "--v2" in sys.argv   # judge with the paths v2 will have (real folders), in memory only
V2_LOCAL = {"real-deployment-and-diagnosis-organics-07d7": "~/Desktop/VolatileWorkSpace/RBO-Staging",
            "redberry-continuous-soc": "~/Desktop/AiAgentWorkSpace/RedBerry-Continuous-SOC"}
V2_EXTRA = {"daily-egypt-amazon-product-poster": ["~/Library/LaunchAgents/com.odin.egypt-amazon-poster.plist"]}
V2_REPORT = {"real-deployment-and-diagnosis-organics-07d7": "~/Desktop/VolatileWorkSpace/RBO-Staging/AI_DIAGNOSIS_REPORT.md"}
_orig = projects.get_project
def _gp(pid):
    p = dict(_orig(pid) or {})
    if pid in virt: p["localPath"] = virt[pid]
    if V2 and pid in V2_LOCAL: p["localPath"] = V2_LOCAL[pid]
    if V2 and pid in V2_EXTRA: p["allowedExtraFiles"] = V2_EXTRA[pid]
    return p
projects.get_project = _gp
if V2:
    import workspace_mw as _mw
    _er = _mw.external_report_ref
    _mw.external_report_ref = lambda pid: V2_REPORT.get(pid) or _er(pid)
allp = [a for a in approvals._all() if a.get("files") or a.get("commands")]
def _cwd(a):
    c = a.get("cwd") or ""
    if V2 and "/_external/RedBerry-Continuous-SOC" in c:
        c = os.path.expanduser("~/Desktop/AiAgentWorkSpace/RedBerry-Continuous-SOC")
    return c
hist = [a["id"] for a in allp if a.get("historical")]
ref = [(a["id"], a["pid"], a.get("status"), api_v2._outside_paths(a["pid"], a, _cwd(a))) for a in allp if not a.get("historical")]
ref = [r for r in ref if r[3]]
print(json.dumps({"mode": "v2 real paths (in memory)" if V2 else "copy as stored", "declared_in_memory": virt,
                  "proposals_checked": len(allp), "historical_not_rerunnable": len(hist), "refused": len(ref),
                  "refused_list": [{"id": i, "project": p, "status": s, "why": [x[:110] for x in b[:2]]} for i, p, s, b in ref]}, indent=1))
