#!/usr/bin/env python3
"""F-18: the 42 chat mismatches (Phase 2 chat gap-check, MFI CH0–CH5) as ACCEPTANCE CHECKS for G1 and the related
items. Each mismatch is tied to the test that proves it; this runner reads the latest test results (and runs the two
fix #2 unit tests) and reports each mismatch as PROVEN / PENDING (with the step that will prove it) / DOC (an
inventory correction, not a system fault). Writes results/f18_acceptance.json. python f18_acceptance.py"""
import json, pathlib, subprocess, sys
R = pathlib.Path(__file__).resolve().parent.parent; RES = R / "_consolidation/results"
def last_result(log):
    p = RES / log
    if not p.exists():
        return None
    lines = [l for l in p.read_text(errors="replace").splitlines() if l.startswith("RESULT")]
    return lines[-1] if lines else None
def run_unit(script):
    r = subprocess.run([sys.executable, str(R / "_consolidation" / script), str(R / "server")], capture_output=True, text=True)
    lines = [l for l in r.stdout.splitlines() if l.startswith("RESULT")]
    return lines[-1] if lines else f"RESULT: rc={r.returncode}"
UNIT = {"fix2c_unit.py": run_unit("fix2c_unit.py"), "fix2_unit.py": last_result("fix2_unit.log")}   # fix2_unit runs in the full suite (needs a workspace)
A = {"CH2-11": "fix #2 parts 1–3", "CH4-2": "fix #2 parts 1–3", "CH4-5": "fix #2 part 4", "CH2-1": "fix #2 part 2",
     "CH2-3": "fix #2 part 5", "CH3-3": "fix #2 part 5", "CH0-5": "fix #2 part 2", "CH4-1": "fix #2 part 6",
     "CH4-4": "fix #2 part 6", "CH0-4": "fix #2 part 2", "CH2-7": "fix #2 part 2", "CH4-3": "fix #2 parts 2–3",
     "CH5-1": "fix #2 part 2"}
B = {"CH0-3": ("P8-2", "stepG_test.log"), "CH3-4": ("P8-2", "stepG_test.log"), "CH1-5": ("P8-2", "stepG_test.log"),
     "CH0-7": ("G12", "g12_test.log"), "CH2-9": ("G12", "g12_test.log"), "CH1-1": ("G9", "g9_test.log"),
     "CH5-4": ("F-23 fix #3", "fix3_test.log"), "CH4-7": ("F-23 fix #3", "fix3_test.log"),
     "CH2-5": ("F-06", "f06_test.log"), "CH2-6": ("F-06", "f06_test.log")}
C = ["CH0-1", "CH0-2", "CH1-3", "CH1-6", "CH2-8", "CH2-10", "CH3-1", "CH3-2", "CH5-2", "CH5-3", "CH4-6"]
D = {"CH1-4": ("F-25", "stepA_test.log"), "CH1-7": ("F-27", "stepA_test.log"), "CH2-2": ("F-28", "stepA_test.log"),
     "CH2-4": ("F-29", "stepA_test.log"), "CH2-12": ("F-30", "stepA_test.log"), "CH5-5": ("F-31", "stepA_test.log"),
     "CH2-16": ("F-24", "stepC_test.log"), "CH1-2": ("F-26 secret-file rule", "f26_test.log")}
rows = []
ok = lambda r: bool(r) and "ALL PASS" in r
for k, part in A.items():
    good = ok(UNIT["fix2c_unit.py"]) and ok(UNIT["fix2_unit.py"])
    rows.append({"id": k, "group": "A (G1 false success)", "by": part, "evidence": "fix2_unit + fix2c_unit", "status": "PROVEN" if good else "FAIL"})
for k, (item, log) in B.items():
    if log is None:
        rows.append({"id": k, "group": "B", "by": item, "evidence": "step G (P8-2 dry-run code)", "status": "PENDING"})
    else:
        r = last_result(log); rows.append({"id": k, "group": "B", "by": item, "evidence": log, "status": "PROVEN" if ok(r) else "FAIL"})
for k in C:
    rows.append({"id": k, "group": "C (inventory was wrong)", "by": "MFI correction", "evidence": "PHASE3_FIX2_PLAN group C", "status": "DOC"})
for k, (item, log) in D.items():
    if log is None:
        rows.append({"id": k, "group": "D", "by": item, "evidence": "owner decision", "status": "PENDING"})
    else:
        r = last_result(log); rows.append({"id": k, "group": "D", "by": item, "evidence": log, "status": "PROVEN" if ok(r) else "FAIL"})
assert len(rows) == 42, len(rows)
summ = {s: sum(1 for x in rows if x["status"] == s) for s in ("PROVEN", "PENDING", "DOC", "FAIL")}
(RES / "f18_acceptance.json").write_text(json.dumps({"summary": summ, "rows": rows}, indent=1))
print("F-18 acceptance (42):", summ)
for x in rows:
    if x["status"] != "PROVEN": print(" ", x["status"], x["id"], "-", x["by"], "-", x["evidence"])
print("RESULT:", "ALL PASS" if summ["FAIL"] == 0 else f"{summ['FAIL']} FAIL")
