#!/usr/bin/env python3
"""G10 rule recovery (copy only, owner-approved 2026-10-11): add back the custom rules the G10 bug wiped from
shared agent files (found in v1 git 06a6ddb, see results/v1_lost_custom_rules.json). Additive only, ONE logged
batch. Undo: python server/rewrite_log.py revert <batch>"""
import sys, os, json, pathlib
root = pathlib.Path(__file__).resolve().parent.parent; os.chdir(root); sys.path.insert(0, str(root / "server"))
import workspace_mw as mw, agents_registry as ar
lost = json.loads((root / "_consolidation/results/v1_lost_custom_rules.json").read_text())
with mw.rewrite_batch("G10 rule recovery: custom rules wiped by the reuse bug, restored from v1 git 06a6ddb (owner approved 2026-10-11)") as bid:
    for agent, rules in lost.items():
        p = mw.WS / "agents" / agent / "capability.md"
        rules = list(dict.fromkeys(rules))
        before = p.read_text(encoding="utf-8")
        ar._merge_skill_file(p, {"rules": rules})
        after = p.read_text(encoding="utf-8")
        p.write_text(before, encoding="utf-8")
        if after != before:
            mw._apply_rewrite(p, before, after, "", f"{len(rules)} custom rule(s) restored")
        print(agent, len(rules), "restored" if after != before else "already present")
print("BATCH", bid)
