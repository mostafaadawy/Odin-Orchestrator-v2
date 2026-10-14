#!/usr/bin/env python3
"""F-07: files written by an approved apply (inline or background) are indexed IMMEDIATELY, not at the next audit."""
import pathlib, sys
R = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
def sub(path, old, new, count=1):
    p = R / path; s = p.read_text()
    assert s.count(old) == count, (path, old[:70], s.count(old)); p.write_text(s.replace(old, new))
API, HOOK = "server/api_v2.py", "server/creator_hook.py"
sub(API, '''def _register_applied_files(''', '''def _index_changed_since(pid: str, folder: str, t0: float, creator_agent: str = "", approval_id: str = "") -> dict:
    """F-07: after an approved apply, index EVERY workspace file the apply created or changed (also files made by
    its local commands, not only the files listed in the proposal), so odin_core matches the disk at once
    instead of at the next audit. A NEW file also records its creator (G8)."""
    import workspace_mw as _mw
    ws = (ROOT / "workspace").resolve()
    roots = {(ws / "projects" / pid).resolve()}
    if folder:
        fp = pathlib.Path(os.path.expanduser(folder)).resolve()
        if fp == ws or ws in fp.parents:
            roots.add(fp)
    rep = {"indexed": 0, "new": 0}
    for r in roots:
        if not r.is_dir():
            continue
        for p in r.rglob("*"):
            if not p.is_file() or ({"logs", "node_modules", ".git", "__pycache__"} & set(p.relative_to(ws).parts)):
                continue
            if p.stat().st_mtime < t0 - 2:
                continue
            existed = _mw.get_creator(p)[0]
            _mw.sync_row(p)
            rep["indexed"] += 1
            if not existed:
                rep["new"] += 1
                if creator_agent:
                    _mw.set_creator(p, _mw.make_creator(agent=creator_agent, project=pid,
                                                        via=f"approved proposal {approval_id}".strip()))
    return rep


def _register_applied_files(''')
# inline (pre-authorized) apply
sub(API, '''    applied, applied_prog = "", []
    if prop["files"] or local_cmds:
        apply_prompt = (f"You are the {member} agent. The owner APPROVED these changes — apply them EXACTLY, "
                        "nothing more, nothing less.''', '''    applied, applied_prog = "", []
    _f07_t0 = time.time()   # F-07: everything the apply writes from now on is indexed right after it
    if prop["files"] or local_cmds:
        apply_prompt = (f"You are the {member} agent. The owner APPROVED these changes — apply them EXACTLY, "
                        "nothing more, nothing less.''')
sub(API, '''    try:   # FIX #1 (G3): register inline-applied (pre-authorized) files too
        _register_applied_files(pid, prop.get("files", []))
    except Exception:
        pass''', '''    try:   # FIX #1 (G3): register inline-applied (pre-authorized) files too
        _register_applied_files(pid, prop.get("files", []))
    except Exception:
        pass
    try:   # F-07: and every other file the apply created or changed (e.g. by its local commands)
        _index_changed_since(pid, folder, _f07_t0, creator_agent=member, approval_id=str(apply_id or ""))
    except Exception:
        pass''')
# background (chat-approved) apply
sub(API, '''    local_cmds = [{**c, "cmd": _fix_rsync_auth(_vm_subst(c.get('cmd', ''), vm_ip))} for c in local_cmds]
    if a.get("files") or local_cmds:''', '''    local_cmds = [{**c, "cmd": _fix_rsync_auth(_vm_subst(c.get('cmd', ''), vm_ip))} for c in local_cmds]
    _f07_t0 = time.time()   # F-07
    if a.get("files") or local_cmds:''')
sub(API, '''        _reg = _register_applied_files(pid, a.get("files", []), creator_agent=member, approval_id=aid)''',
         '''        _reg = _register_applied_files(pid, a.get("files", []), creator_agent=member, approval_id=aid)
        _idx = _index_changed_since(pid, folder, _f07_t0, creator_agent=member, approval_id=aid)   # F-07
        _reg["indexed_after_apply"] = _idx''')
# the creator hook indexes a NEW file even when the created_by column is not migrated
sub(HOOK, '''        if mw.has_created_by():
            mw.record_creator_if_new(p, mw.make_creator(via=f"{data.get('tool_name') or 'write'} tool"))''',
          '''        # F-07: index a NEW file at once (set_creator is a no-op until the G8 column is migrated)
        mw.record_creator_if_new(p, mw.make_creator(via=f"{data.get('tool_name') or 'write'} tool"))''')
print("F-07 applied")

# ---- F-07 part 2: no double indexing when the work folder is inside the project folder; report the indexed paths (applied in-tree)
