#!/usr/bin/env python3
"""F-25 (copy only): the real VM backend folder is ~/bendcore (lowercase); fix the two guidance files that still say
~/Bendcore. ONE logged batch (undo: python server/rewrite_log.py revert <batch>). Records/history/backups untouched."""
import sys, os, pathlib
root = pathlib.Path(__file__).resolve().parent.parent; os.chdir(root); sys.path.insert(0, str(root / "server"))
import workspace_mw as mw
FILES = ["workspace/shared/directions/core-rules.md", "workspace/shared/runbooks/azure-secure-connection.md"]
with mw.rewrite_batch("F-25: VM backend folder is ~/bendcore (lowercase), not ~/Bendcore") as bid:
    for f in FILES:
        p = root / f; cur = p.read_text(encoding="utf-8"); new = cur.replace("Bendcore", "bendcore")
        if new != cur:
            mw._apply_rewrite(p, cur, new, "Bendcore", "bendcore"); print(f, cur.count("Bendcore"), "fixed")
print("BATCH", bid)
