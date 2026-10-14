"""Post-hoc: for every LLM trial root, does Odin's own audit FLAG the files agents wrote outside their project?
usage: analyze_llm.py  (reads results/llm_N*_rep*.json, roots under _research/tmp/llm_r<rep>_n<N>)"""
import json, os, sys, glob, pathlib, subprocess
ISO = pathlib.Path("/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Consolidated"); RES = ISO / "_research/results"
out = []
OLD = {}
if (RES / "llm_summary.json").exists():
    for o in json.loads((RES / "llm_summary.json").read_text()): OLD[(o["N"], o["rep"])] = o
for f in sorted(RES.glob("llm_N*_rep*.json")):
    d = json.loads(f.read_text()); N, rep = d["N"], d["rep"]
    root = ISO / f"_research/tmp/llm_r{rep}_n{N}"
    if not root.is_dir():
        if (N, rep) in OLD:   # root already cleaned: keep the earlier analysis; cross writes from recorded artifact locations
            o = OLD[(N, rep)]
            o.setdefault("cross_project_module_writes", 0 if rep == 0 else sum(1 for pr in d["projects"] for l in pr["artifact_locations"] if "OTHER" in l))
            o.setdefault("hook", {}); o.setdefault("shared_files_changed", []); out.append(o)
        continue
    code = ("import sys,json;sys.path.insert(0,'server');import workspace_audit as au;"
            "print(json.dumps([i for i in au.scan() if i['type'] in ('root-stray','misplaced','foreign-ref','external-write')]))")
    env = dict(os.environ, PGPORT="15499")  # no DB: structural checks only
    r = subprocess.run([str(ISO / ".venv/bin/python"), "-c", code], cwd=root, capture_output=True, text=True, env=env, timeout=120)
    try: iss = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception: iss = []
    flagged = {i.get("path") for i in iss if i["type"] == "root-stray"}
    stray_top = {pathlib.Path(s).parts[0] for s in d.get("stray_outside_projects", [])}
    esc = []
    for pr in d["projects"]:
        q = ISO / "_research/tmp/accident_quarantine/escaped_llm" / pr["pid"]
        if q.is_dir():
            t = list(q.rglob("test_*.py"))
            okt = bool(t) and subprocess.run([str(ISO / ".venv/bin/python"), t[0].name], cwd=t[0].parent, capture_output=True).returncode == 0
            esc.append(pr["pid"]); pr["fullstack_built"] = True; pr["test_passes"] = okt; pr["artifact_locations"] = ["ESCAPED-to-main-copy/own-project/code"]
    BASES = ["csv2json", "slugify", "wordcount", "roman", "isbn"]
    def own_mod(i): return BASES[i % 5] + ("" if (rep == 0 or i < 5) else str(i))
    cross_w = 0; xr = []
    for pr in d["projects"]:
        i = int(pr["pid"].rsplit("-p", 1)[1]); pdir = root / "workspace/projects" / pr["pid"]
        mods = {f.stem for f in pdir.rglob("*.py") if not f.name.startswith("test_") and "__pycache__" not in f.parts}
        for m in mods:
            if m in [own_mod(j) for j in range(N) if j != i] and m != own_mod(i):
                cross_w += 1; xr.append(f'{pr["pid"]}:{m}')
    hk = {}
    hf = root / "workspace/history/scope-hook.jsonl"
    if hf.is_file():
        for l in open(hf):
            try:
                h = json.loads(l); k = f'{h.get("mode")}:{h.get("tool")}:{h.get("decision")}' + (":door" if h.get("target") == "door" else ""); hk[k] = hk.get(k, 0) + 1
            except Exception: pass
    out.append({"cross_project_module_writes": cross_w, "cross_examples": xr[:6], "shared_files_changed": d.get("shared_files_changed", []), "adv": d.get("adv", False), "hook": hk, "escaped_to_main_copy": esc, "N": N, "rep": rep, "tasks": len(d["projects"]),
                "built": sum(p["fullstack_built"] for p in d["projects"]), "test_passes": sum(p["test_passes"] for p in d["projects"]),
                "qa_reported_pass": sum(p["qa_reported_pass"] for p in d["projects"]),
                "in_code_slot": sum(p["artifacts_in_code_slot"] for p in d["projects"]),
                "locations": [p.get("artifact_locations") for p in d["projects"]],
                "files_outside_any_project": d["n_stray"], "cross_project_files": d["cross_project_files"],
                "stray_top_level": sorted(stray_top), "audit_flagged_root_stray": sorted(flagged & stray_top),
                "audit_flag_ratio": (len(flagged & stray_top) / len(stray_top)) if stray_top else None,
                "cost_usd": d["cost_usd"], "cost_per_task": d["cost_per_task_usd"], "calls": d["claude_calls"],
                "llm_busy_share": d["llm_busy_share_of_wall"], "server_cpu_share_machine": d["server_tree"]["cpu_share_of_machine"],
                "wall_ratio_to_cap": max(p["secs_ratio_to_cap"] for p in d["projects"]),
                "real_odin_cpu_pct_start": d["env_start"]["real_odin_cpu_pct"], "soc_last_hour": d["env_start"]["soc_reports_last_hour"]})
(RES / "llm_summary.json").write_text(json.dumps(out, indent=1))
for o in out: print({k: o[k] for k in ("N", "rep", "tasks", "built", "test_passes", "in_code_slot", "files_outside_any_project", "cross_project_files", "audit_flag_ratio", "cost_per_task")})
