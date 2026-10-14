#!/usr/bin/env python3
"""F-39 (2): a project may name EXACT extra files (never folders) it may write outside its folder; for the Egypt
Amazon poster only ~/Library/LaunchAgents/com.odin.egypt-amazon-poster.plist. cp/mv/install into a folder count as
writing <folder>/<source file name>."""
import pathlib, sys
R = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
def sub(path, old, new, count=1):
    p = R / path; s = p.read_text()
    assert s.count(old) == count, (path, old[:70], s.count(old)); p.write_text(s.replace(old, new))
API = "server/api_v2.py"
sub(API, '''    try:
        import projects as _pj
        lp = ((_pj.get_project(pid) or {}).get("localPath") or "").strip()
    except Exception:
        lp = ""
    if lp:
        roots.append(pathlib.Path(os.path.expanduser(lp)).resolve())''', '''    try:
        import projects as _pj
        _proj = _pj.get_project(pid) or {}
    except Exception:
        _proj = {}
    lp = (_proj.get("localPath") or "").strip()
    if lp:
        roots.append(pathlib.Path(os.path.expanduser(lp)).resolve())
    # F-39: EXACT extra files the owner allowed for this project (files only — never a folder)
    exact = {pathlib.Path(os.path.expanduser(str(x))).resolve() for x in (_proj.get("allowedExtraFiles") or [])}''')
sub(API, '''    def _inside(q):
        return any(q == r or r in q.parents for r in roots)''', '''    def _inside(q):
        return q in exact or any(q == r or r in q.parents for r in roots)''')
sub(API, '''            if prog in ("cp", "mv", "ln", "install") and len(args) >= 2:
                targets.append(args[-1])''', '''            if prog in ("cp", "mv", "ln", "install") and len(args) >= 2:
                _d = args[-1]
                _dq = _res(_d, cwd)
                if _d.endswith("/") or (_dq is not None and _dq.is_dir()):   # into a folder = <folder>/<name>
                    _d = str(pathlib.Path(_d) / pathlib.Path(args[-2].rstrip("/")).name)
                targets.append(_d)''')
print("F-39 (2) applied")

# ---- F-39 part 2: the registered external report file (workspace_mw.external_report_ref) counts as an exact allowed file (applied in-tree)
