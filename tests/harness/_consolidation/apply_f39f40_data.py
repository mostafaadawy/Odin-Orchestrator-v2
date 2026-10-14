#!/usr/bin/env python3
"""F-39 (1)+(3 marking) and F-40 — DATA changes in the COPY only (owner approved 2026-10-11). v2 keeps the real paths:
  real-deployment-and-diagnosis-organics-07d7 -> ~/Desktop/VolatileWorkSpace/RBO-Staging
  redberry-continuous-soc                    -> ~/Desktop/AiAgentWorkSpace/RedBerry-Continuous-SOC
In the copy every one of these points into the copy's own _external/ folder."""
import sys, os, json, pathlib
R = pathlib.Path(__file__).resolve().parents[1]; sys.path.insert(0, str(R / "server"))
import projects, approvals, workspace_mw as mw
X = R / "_external"
RD, SOC, LA = X / "VolatileWorkSpace" / "RBO-Staging", X / "RedBerry-Continuous-SOC", X / "LaunchAgents"
for d in (RD, SOC, LA):
    d.mkdir(parents=True, exist_ok=True)
log = {}
for pid, path in (("real-deployment-and-diagnosis-organics-07d7", RD), ("redberry-continuous-soc", SOC)):
    p = projects.get_project(pid); log[pid] = {"localPath_before": p.get("localPath"), "localPath_after": str(path)}
    p["localPath"] = str(path); projects._update(p)
p = projects.get_project("daily-egypt-amazon-product-poster")
log["poster_allowedExtraFiles"] = {"before": p.get("allowedExtraFiles"), "after": [str(LA / "com.odin.egypt-amazon-poster.plist")]}
p["allowedExtraFiles"] = [str(LA / "com.odin.egypt-amazon-poster.plist")]; projects._update(p)
er_before = mw.external_report_ref("real-deployment-and-diagnosis-organics-07d7")
mw.set_external_report_ref("real-deployment-and-diagnosis-organics-07d7", str(RD / "AI_DIAGNOSIS_REPORT.md"))
log["external_report"] = {"before": er_before, "after": str(RD / "AI_DIAGNOSIS_REPORT.md")}
for aid in ("d946bb03be7c", "211282322806"):
    a = approvals.get(aid); log[f"approval {aid} cwd"] = {"before": a.get("cwd"), "after": str(SOC)}
    approvals.set_fields(aid, cwd=str(SOC))
HIST = ["6b89443f6616", "f74209cd7cb8", "ae8e79831af3", "99441fb4eed2", "245fef2de291", "d59839b8dce7",
        "3f13f19084bc", "0878e058188d", "e2318b3f5a4c", "f0612f5ef369", "71d9635f8639"]
for aid in HIST:
    approvals.set_fields(aid, historical="old folder layout, historical, not re-runnable")
log["marked_historical"] = HIST
(R / "_consolidation" / "results" / "f39f40_data_log.json").write_text(json.dumps(log, indent=1))
print(json.dumps(log, indent=1))
