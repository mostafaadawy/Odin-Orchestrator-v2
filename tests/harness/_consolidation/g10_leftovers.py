#!/usr/bin/env python3
"""G10 leftovers (copy only, owner-approved 2026-10-11), ONE logged batch:
  - EasyPost: restore the original one-line description from baseline 0462cc0;
  - Email: align the title role to its index.json role ("Email & Lifecycle").
Undo: python server/rewrite_log.py revert <batch>"""
import sys, os, json, pathlib, subprocess
root = pathlib.Path(__file__).resolve().parent.parent; os.chdir(root); sys.path.insert(0, str(root / "server"))
import workspace_mw as mw
with mw.rewrite_batch("G10 leftovers: EasyPost description from baseline; Email title aligned to index.json (owner approved 2026-10-11)") as bid:
    p = mw.WS / "agents/easypost/capability.md"
    base = subprocess.run(["git", "show", "0462cc0:workspace/agents/easypost/capability.md"], capture_output=True, text=True).stdout
    cur = p.read_text(encoding="utf-8")
    old_d, new_d = cur.split("\n")[2], base.split("\n")[2]
    assert cur.split("\n")[0] == base.split("\n")[0], "unexpected EasyPost layout"
    if old_d != new_d:
        mw._apply_rewrite(p, cur, cur.replace(old_d, new_d, 1), old_d[:80] + "…", new_d)
        print("easypost description:", new_d)
    e = mw.WS / "agents/email/capability.md"
    role = json.loads((mw.WS / "agents/email/index.json").read_text()).get("role")
    cur = e.read_text(encoding="utf-8"); t_old = cur.split("\n")[0]; t_new = f"# Email — {role}"
    if t_old != t_new:
        mw._apply_rewrite(e, cur, cur.replace(t_old, t_new, 1), t_old, t_new)
        print("email title:", t_old, "->", t_new)
print("BATCH", bid)
