"""Aggregate every raw result into results/summary.json (ratios + variance) for the paper."""
import json, glob, statistics as st, collections, pathlib, re
R = pathlib.Path("/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Isolated/_research/results")
S = {}
rows = [json.loads(l) for l in open(R / "consistency_trials.jsonl") if l.strip()]
g = collections.defaultdict(list)
for r in rows: g[(r["N"], r["cond"])].append(r)
def ms(v): return {"mean": st.mean(v), "sd": st.pstdev(v), "n": len(v)}
S["rq1"] = {f"N{N}_{c}": {"violation_rate": ms([x["violation_rate"] for x in v]), "residual_after_heal": ms([x["residual_rate_after_heal"] for x in v]),
            "cross_project_per_write": ms([x["cross_project_landed"] / x["writes"] for x in v]), "wrong_folder_per_write": ms([x["wrong_folder_landed"] / x["writes"] for x in v]),
            "audit_issues_per_write": ms([x["audit_issues"] / x["writes"] for x in v]), "residual_audit_issues": ms([x["after_heal"]["audit_issues"] for x in v]),
            "lockstep_before_heal": ms([x["db_lockstep_before_heal"] or 0 for x in v]), "lockstep_after_heal": ms([x["db_lockstep_after_heal"] or 0 for x in v]),
            "lat_p50_ms": ms([x["lat_p50_ms"] for x in v]), "writes": v[0]["writes"], "agents": v[0]["agents"],
            "work_cpu_share_of_wall": ms([x["work"]["cpu_share_of_wall"] for x in v])} for (N, c), v in sorted(g.items())}
b1 = S["rq1"]["N1_door"]["lat_p50_ms"]["mean"]
S["rq1_latency_ratio_to_N1"] = {N: S["rq1"][f"N{N}_door"]["lat_p50_ms"]["mean"] / b1 for N in (1, 2, 5, 10)}
S["rq1_door_vs_bypass_latency_ratio"] = {N: S["rq1"][f"N{N}_door"]["lat_p50_ms"]["mean"] / S["rq1"][f"N{N}_bypass"]["lat_p50_ms"]["mean"] for N in (1, 2, 5, 10)}
L = json.load(open(R / "llm_summary.json"))
def phase(rep): return "before" if rep < 10 else ("watch" if rep < 20 else ("after" if rep < 30 else ("adv_hook_off" if rep == 30 else ("adv_hook_on_v1" if rep == 31 else "adv_hook_on"))))
S["rq2"] = {}; S["rq2_cost_per_task_ratio_to_N1"] = {}
for ph in ("before", "watch", "after", "adv_hook_off", "adv_hook_on_v1", "adv_hook_on"):
    byN = collections.defaultdict(list)
    for o in L:
        if phase(o["rep"]) == ph: byN[o["N"]].append(o)
    S["rq2"][ph] = {}
    for N, v in sorted(byN.items()):
        t = sum(o["tasks"] for o in v)
        S["rq2"][ph][N] = {"reps": len(v), "tasks": t, "success_ratio": sum(o["test_passes"] for o in v) / t, "built_ratio": sum(o["built"] for o in v) / t,
                   "in_code_slot_ratio": sum(o["in_code_slot"] for o in v) / t, "runs_with_outside_writes": sum(1 for o in v if o["files_outside_any_project"]) / len(v),
                   "outside_files_per_task": sum(o["files_outside_any_project"] for o in v) / t, "cross_project_files": sum(o["cross_project_files"] for o in v), "cross_project_module_writes": sum(o.get("cross_project_module_writes", 0) for o in v),
                   "audit_flag_ratio": [o["audit_flag_ratio"] for o in v], "escaped_to_main_copy": sum(len(o.get("escaped_to_main_copy", [])) for o in v),
                   "shared_files_changed": sum(len(o.get("shared_files_changed", [])) for o in v),
                   "hook": {k: sum(o.get("hook", {}).get(k, 0) for o in v) for k in set().union(*[o.get("hook", {}).keys() for o in v])},
                   "cost_per_task_usd": ms([o["cost_per_task"] for o in v]), "llm_busy_share": ms([o["llm_busy_share"] for o in v if o["llm_busy_share"] is not None]),
                   "wall_ratio_to_cap": ms([o["wall_ratio_to_cap"] for o in v])}
    if 1 in S["rq2"][ph]:
        c1 = S["rq2"][ph][1]["cost_per_task_usd"]["mean"]
        S["rq2_cost_per_task_ratio_to_N1"][ph] = {N: S["rq2"][ph][N]["cost_per_task_usd"]["mean"] / c1 for N in S["rq2"][ph]}
def owner(pattern):
    out = []
    for f in sorted(glob.glob(str(R / pattern))):
        t = open(f).read()
        out.append({"file": pathlib.Path(f).name, "pass": t.count("[PASS]") + len(re.findall(r"CREATE \[PASS\]", t)), "fail": t.count("[FAIL]"),
                    "all_green": "ALL GREEN" in t, "real_s": (re.findall(r"^real ([\d.]+)", t, re.M) or [None])[0]})
    return out
S["rq3"] = {"phase7_lifecycle": owner("owner_phase7_lifecycle_rep*.log"), "phase7_strong": owner("owner_phase7_strong_rep*.log"),
            "phase7_lifecycle_after": owner("owner_phase7_lifecycle_after_rep*.log"), "phase7_strong_after": owner("owner_phase7_strong_after_rep*.log")}
a = json.load(open(R / "anchor_exp.json"))
S["rq4"] = {"queue": a["queue"], "sync": a["sync"], "env": a["env"]}
regs = sorted(glob.glob(str(R / "regression_*.json")))
S["regression"] = [{"file": pathlib.Path(f).name, "pass": sum(1 for v in json.load(open(f))["metrics"].values() if v is True),
                    "failures": json.load(open(f))["failures"], "regressions": json.load(open(f)).get("regressions_vs_baseline")} for f in regs]
cost = 0.0
for f in glob.glob(str(R / "claude_calls*.jsonl")):
    for l in open(f):
        if l.strip(): cost += json.loads(l).get("cost_usd") or 0
extra = sum(json.loads(l)["usd"] for l in open(R / "cost_ledger.jsonl") if l.strip() and ("unlogged" in l or "verification (" in l))
S["cost_total_usd"] = cost + extra
(R / "summary.json").write_text(json.dumps(S, indent=1, default=str))
print(json.dumps({"cost": S["cost_total_usd"], "rq2": {ph: {N: (round(v["success_ratio"],3), round(v["in_code_slot_ratio"],3), v["outside_files_per_task"], v["cross_project_files"], v["escaped_to_main_copy"], v["hook"]) for N, v in d.items()} for ph, d in S["rq2"].items()}}, default=str))
