#!/usr/bin/env python3
"""F-24 data (copy only): the owner's removal of the poster's launchd job (v1 approval 876bba23bdfb, applied
2026-08-01 00:22 at the owner's request) is remembered in the copy, so the copy never proposes reinstalling it.
Logged in results/stepC_data.json; undo: projects.set_flags(pid, ownerRemoved=<previous>)."""
import sys, os, json, pathlib
root = pathlib.Path(__file__).resolve().parent.parent; os.chdir(root); sys.path.insert(0, str(root / "server"))
import api_v2, approvals, projects
PP = "daily-egypt-amazon-product-poster"
prev = (projects.get_project(PP) or {}).get("ownerRemoved")
a = dict(approvals.get("876bba23bdfb") or {}); a["decided_by"] = "owner"
gone = api_v2._remember_removals(PP, a)
log = {"project": PP, "from_approval": "876bba23bdfb", "previous": prev, "remembered": gone}
(root / "_consolidation/results/stepC_data.json").write_text(json.dumps(log, indent=1)); print(json.dumps(log))
