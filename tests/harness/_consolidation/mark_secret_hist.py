#!/usr/bin/env python3
"""Owner 2026-10-11: the 3 past proposals that write a secret file are historical, replaced by the G9b secure key field."""
import sys, os, json, pathlib
R = pathlib.Path(__file__).resolve().parent.parent; os.chdir(R); sys.path.insert(0, str(R / "server"))
import approvals
IDS = ["6bd7b2ebf3ef", "bc12b7443bfa", "1915cc48a862"]
out = {}
for aid in IDS:
    a = approvals.get(aid) if hasattr(approvals, "get") else None
    approvals.set_fields(aid, historical="historical, replaced by the secure key field")
    out[aid] = {"status_before": (a or {}).get("status"), "marked": True}
(R / "_consolidation/results/secret_hist_log.json").write_text(json.dumps(out, indent=1)); print(json.dumps(out))
