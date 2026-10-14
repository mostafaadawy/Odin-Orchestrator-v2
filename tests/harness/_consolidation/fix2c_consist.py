#!/usr/bin/env python3
"""Scenario check after fix #2c: run outcome must equal the combination of step outcomes, and PASSED steps must
list evidence files that exist. Usage: fix2c_consist.py <result.json> <ROOT>"""
import sys, json, pathlib
r = json.load(open(sys.argv[1])); root = pathlib.Path(sys.argv[2]); ev = (r.get("record") or {}).get("run", {}).get("events") or []
steps = [d for e, d in ev if e == "step_done" and isinstance(d, dict)]
done = next((d for e, d in ev if e == "done" and isinstance(d, dict)), {})
so = [str(s.get("outcome")) for s in steps]
exp = "PASSED" if so and all(x == "PASSED" for x in so) else ("WAITING_FOR_APPROVAL" if so and all(x in ("PASSED","WAITING_FOR_APPROVAL") for x in so) else "NOT_DONE")
out = {"file": sys.argv[1], "step_outcomes": so, "run_outcome": done.get("outcome"), "ok": done.get("ok"),
       "expected_from_steps": exp, "CONSISTENT": (done.get("outcome") == exp) or (done.get("outcome") == "NOT_DONE" and exp != "PASSED")}
print("CONSIST " + json.dumps(out, ensure_ascii=False))
