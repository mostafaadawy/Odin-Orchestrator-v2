#!/usr/bin/env python3
"""Check one scenario result: run 'ok' must equal 'every step review Confirmed (and not flagged)'."""
import sys, json, re
r = json.load(open(sys.argv[1])); ev = (r.get("record") or {}).get("run", {}).get("events") or []
steps, done = [], None
for e, d in ev:
    if e == "step_done" and isinstance(d, dict):
        res = str(d.get("result", ""))
        body = re.sub(r"^(✅ QA passed\. |⚠️ QA issues remain\. |QA skipped\. )", "", res)
        t = re.sub(r"^[\s>*_`#\"'✅⚠️❌🔎:-]+", "", body).lower()
        v = "needs_fix" if re.search(r"\bneeds[\s-]+(a\s+)?fix", t) else "confirmed" if re.match(r"confirmed[*_`\s]*:", t) else "unclear"
        steps.append({"member": d.get("member"), "label": res[:20], "review": v})
    if e == "done" and isinstance(d, dict):
        done = str(d.get("ok")) == "True"
statuses = [str(d.get("text", "")) for e, d in ev if e == "status" and isinstance(d, dict)]
all_conf = bool(steps) and all(s["review"] == "confirmed" for s in steps)
flagged = any("still has issues" in s for s in statuses)
consistent = (done is not True) or (all_conf and not flagged)
out = {"file": sys.argv[1], "steps": steps, "done_ok": done, "all_reviews_confirmed": all_conf,
       "any_step_flagged": flagged, "CONSISTENT": consistent,
       "qa_skipped_label_ok": all(not s["label"].startswith("✅ QA passed") for s in steps) if "S4" in sys.argv[1] else None}
print("CONSIST " + json.dumps(out, ensure_ascii=False))
