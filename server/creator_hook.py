#!/usr/bin/env python3
"""creator_hook.py — G8 PostToolUse hook (Write/Edit/MultiEdit/NotebookEdit). After an agent writes a file,
record WHO created it (files.created_by) if the file is NEW to odin_core. It never blocks and prints nothing:
any error is swallowed so the agent's work is never affected."""
import sys, os, json, pathlib
try:
    ROOT = pathlib.Path(os.environ.get("ODIN_ROOT") or pathlib.Path(__file__).resolve().parent.parent)
    data = json.load(sys.stdin)
    inp = data.get("tool_input") or {}
    fp = inp.get("file_path") or inp.get("notebook_path") or ""
    if fp:
        p = pathlib.Path(os.path.expanduser(fp))
        p = p if p.is_absolute() else pathlib.Path(data.get("cwd") or os.getcwd()) / p
        sys.path.insert(0, str(ROOT / "server"))
        import workspace_mw as mw
        # F-07: index a NEW file at once (set_creator is a no-op until the G8 column is migrated)
        mw.record_creator_if_new(p, mw.make_creator(via=f"{data.get('tool_name') or 'write'} tool"))
except Exception:
    pass
sys.exit(0)
