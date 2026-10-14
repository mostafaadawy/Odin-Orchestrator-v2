#!/usr/bin/env python3
"""G10 data repair (copy only, owner-approved): restore the 5 shortened shared agent titles from the
baseline 0462cc0, in the capability files, as ONE logged batch; the DB role is re-synced from each agent's index.json. Undo: python server/rewrite_log.py revert <batch>"""
import sys, os, pathlib, subprocess
root = pathlib.Path(__file__).resolve().parent.parent; os.chdir(root); sys.path.insert(0, str(root / "server"))
import workspace_mw as mw
AG = ["devops", "email", "fullstack", "qa", "security"]
with mw.rewrite_batch("G10 data repair: restore shared agent titles shortened by the reuse bug (owner approved 2026-10-11)") as bid:
    for a in AG:
        f = root / f"workspace/agents/{a}/capability.md"
        base = subprocess.run(["git", "show", f"0462cc0:workspace/agents/{a}/capability.md"], capture_output=True, text=True).stdout
        old_t, new_t = f.read_text().splitlines()[0], base.splitlines()[0]
        if old_t == new_t:
            print(a, "already ok"); continue
        before = f.read_text(); after = before.replace(old_t, new_t, 1)
        mw._apply_rewrite(f, before, after, old_t, new_t)
        print(a, ":", old_t, "->", new_t)
    # the DB role is NOT edited here: sync_row re-derives it from each agent's own index.json (never damaged)
    for a in AG:
        mw.sync_row(root / f"workspace/agents/{a}/index.json")
print("BATCH", bid)
