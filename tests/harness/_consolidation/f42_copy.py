#!/usr/bin/env python3
"""F-42 in the COPY (owner-approved 2026-10-11): merge back the charter and merged-duplicate sections (and any
missing base rules) from v1 git 06a6ddb (read with git --no-optional-locks; v1 is not modified). ONE logged batch.
  python f42_copy.py            -> dry run: per-agent report, nothing written
  python f42_copy.py --apply    -> apply as one batch; undo: python server/rewrite_log.py revert <batch>"""
import sys, os, json, pathlib, subprocess
root = pathlib.Path(__file__).resolve().parent.parent; os.chdir(root)
sys.path.insert(0, str(root / "server")); sys.path.insert(0, str(root / "_consolidation"))
import f42_merge
V1 = root.parent / "Odin-Orchestrator"; SRC = "06a6ddb"
def old(agent):
    r = subprocess.run(["git", "--no-optional-locks", "-C", str(V1), "show", f"{SRC}:workspace/agents/{agent}/capability.md"],
                       capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None
apply = "--apply" in sys.argv
plan = {}
for p in sorted((root / "workspace/agents").glob("*/capability.md")):
    o = old(p.parent.name)
    if o is None:
        continue
    cur = p.read_text(encoding="utf-8")
    new, rep = f42_merge.merge(o, cur)
    if new != cur:
        plan[p.parent.name] = (p, cur, new, rep)
report = {a: v[3] for a, v in plan.items()}
if apply:
    import workspace_mw as mw
    with mw.rewrite_batch(f"F-42: merge back charter + merged-duplicate sections from v1 git {SRC} (owner approved 2026-10-11)") as bid:
        for a, (p, cur, new, rep) in plan.items():
            mw._apply_rewrite(p, cur, new, "", f"F-42 restore: {len(rep['sections_added'])} section(s), {len(rep['rules_added'])} rule(s)")
    report["_batch"] = bid
print(json.dumps(report, indent=1, ensure_ascii=False))
