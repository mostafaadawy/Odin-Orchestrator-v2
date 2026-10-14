#!/usr/bin/env python3
"""G8: record which agent created each file (files.created_by, nullable, option A) and name it in every audit finding."""
import pathlib, sys
R = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
def sub(path, old, new, count=1):
    p = R / path; s = p.read_text()
    assert s.count(old) == count, (path, old[:70], s.count(old)); p.write_text(s.replace(old, new))
MW, AU, CC, API = "server/workspace_mw.py", "server/workspace_audit.py", "server/claude_cli.py", "server/api_v2.py"
# ---------------- workspace_mw.py ----------------
sub(MW, "def sync_row(path, owner_type=None, owner_id=None, subfolder=None, description=None) -> None:",
'''# ── G8: who CREATED a file (files.created_by — optional column, added by server/migrations/migrate_g8.sh) ──
# Every function below is a no-op when the column is absent (an un-migrated database behaves exactly as before).
import os as _os, time as _time
_CB_CACHE = {"v": None, "t": 0.0}


def has_created_by() -> bool:
    if _CB_CACHE["v"] is not None and _time.time() - _CB_CACHE["t"] < 30:
        return _CB_CACHE["v"]
    v = False
    conn = _db()
    if conn:
        try:
            cu = conn.cursor()
            cu.execute("SELECT 1 FROM information_schema.columns WHERE table_schema='public' "
                       "AND table_name='files' AND column_name='created_by'")
            v = cu.fetchone() is not None
        except Exception:
            v = False
        finally:
            conn.close()
    _CB_CACHE.update(v=v, t=_time.time())
    return v


def make_creator(agent=None, project=None, via="", **extra) -> str:
    agent = agent or _os.environ.get("ODIN_MEMBER") or None
    project = project or _os.environ.get("ODIN_ACTOR_PID") or None
    return json.dumps({"agent": agent, "project": project, "via": via,
                       "ts": datetime.datetime.now().isoformat(timespec="seconds"), **extra}, ensure_ascii=False)


def creator_label(raw) -> str:
    """Human label for a created_by value; NULL/absent = 'unknown'."""
    if not raw:
        return "unknown"
    try:
        d = json.loads(raw)
    except Exception:
        return str(raw)
    who = d.get("agent") or (f"project {d['project']}" if d.get("project") else "unknown")
    bits = [x for x in ((f"project {d['project']}" if d.get("agent") and d.get("project") else ""),
                        (f"via {d['via']}" if d.get("via") else "")) if x]
    return who + (f" ({', '.join(bits)})" if bits else "")


def _relp(path) -> str:
    p = pathlib.Path(path)
    p = p if p.is_absolute() else ROOT / p
    try:
        return str(p.resolve().relative_to(ROOT.resolve()))
    except Exception:
        return str(p)


def get_creator(path):
    """(row_exists, raw created_by or None)."""
    conn = _db()
    if not conn:
        return False, None
    try:
        cu = conn.cursor()
        if has_created_by():
            cu.execute("SELECT created_by FROM files WHERE path=%s", (_relp(path),))
            r = cu.fetchone()
            return (r is not None), (r[0] if r else None)
        cu.execute("SELECT 1 FROM files WHERE path=%s", (_relp(path),))
        return cu.fetchone() is not None, None
    except Exception:
        return False, None
    finally:
        conn.close()


def set_creator(path, creator: str, only_if_null: bool = True) -> bool:
    if not creator or not has_created_by():
        return False
    conn = _db()
    if not conn:
        return False
    try:
        cu = conn.cursor()
        q = "UPDATE files SET created_by=%s WHERE path=%s" + (" AND created_by IS NULL" if only_if_null else "")
        cu.execute(q, (creator, _relp(path)))
        n = cu.rowcount
        conn.commit()
        return n > 0
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False
    finally:
        conn.close()


def record_creator_if_new(path, creator: str) -> bool:
    """A file an agent just wrote: if odin_core had NO row for it, it is NEW — index it and record its
    creator. An existing file keeps its creator (an editor is not the creator)."""
    p = pathlib.Path(path)
    try:
        p.resolve().relative_to(WS.resolve())
    except Exception:
        return False
    if not p.is_file():
        return False
    existed, _raw = get_creator(p)
    if existed:
        return False
    sync_row(p)
    return set_creator(p, creator)


def carry_creator(old_path, new_path) -> None:
    """A move keeps the file's creator."""
    _e, raw = get_creator(old_path)
    if raw:
        set_creator(new_path, raw)


def creators_for(paths) -> dict:
    """{path: label} for many paths in one query ('unknown' when NULL, absent, or column not migrated)."""
    paths = [p for p in {str(x) for x in paths if x}]
    out = {p: "unknown" for p in paths}
    if not paths or not has_created_by():
        return out
    conn = _db()
    if not conn:
        return out
    try:
        cu = conn.cursor()
        cu.execute("SELECT path, created_by FROM files WHERE path = ANY(%s)", (paths,))
        for pth, raw in cu.fetchall():
            out[pth] = creator_label(raw)
    except Exception:
        pass
    finally:
        conn.close()
    return out


def sync_row(path, owner_type=None, owner_id=None, subfolder=None, description=None) -> None:''')
# sync_row re-inserts the row: keep created_by across the DELETE/INSERT
sub(MW, '''        s = p.stat()
        cu.execute("DELETE FROM files WHERE path=%s", (rel,))''', '''        s = p.stat()
        _cb = None
        if has_created_by():   # G8: a re-sync must not lose who created the file
            cu.execute("SELECT created_by FROM files WHERE path=%s", (rel,))
            _r = cu.fetchone(); _cb = _r[0] if _r else None
        cu.execute("DELETE FROM files WHERE path=%s", (rel,))''')
sub(MW, '''                    s.st_size, datetime.datetime.fromtimestamp(s.st_ctime),
                    datetime.datetime.fromtimestamp(s.st_mtime)))
        conn.commit()''', '''                    s.st_size, datetime.datetime.fromtimestamp(s.st_ctime),
                    datetime.datetime.fromtimestamp(s.st_mtime)))
        if _cb is not None:
            cu.execute("UPDATE files SET created_by=%s WHERE path=%s", (_cb, rel))
        conn.commit()''')
# put_file (the door): a NEW file records its creator
sub(MW, '''    p = resolve_path(owner_type, owner_id, sf, name)
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, (dict, list)):''', '''    p = resolve_path(owner_type, owner_id, sf, name)
    _g8_new = not get_creator(p)[0]          # G8: no odin_core row yet = this write creates the file
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, (dict, list)):''')
sub(MW, '''    sync_row(p, owner_type, owner_id, sf, description)
    result = {"path": str(p), "corrected": corrected,''', '''    sync_row(p, owner_type, owner_id, sf, description)
    if _g8_new:
        _act = actor if isinstance(actor, (tuple, list)) else ((owner_type, actor) if actor else (owner_type, owner_id))
        set_creator(p, make_creator(project=_act[1] if _act[0] == "project" else None, via="middleware door",
                                    **({"owner_agent": _act[1]} if _act[0] == "agent" else {})))
    result = {"path": str(p), "corrected": corrected,''')
# promote_to_shared: the shared file keeps the creator of the moved file
sub(MW, '''    created_shared = not dest.exists()
    if not dest.exists():''', '''    created_shared = not dest.exists()
    _g8_cb = get_creator(p)[1]               # G8: keep the creator across the move
    if not dest.exists():''')
sub(MW, '''    sync_row(dest)                               # index the shared location
    record_move(old_ws, dest_rel, created_shared)''', '''    sync_row(dest)                               # index the shared location
    if _g8_cb:
        set_creator(dest, _g8_cb)
    record_move(old_ws, dest_rel, created_shared)''')
# ---------------- workspace_audit.py ----------------
sub(AU, '''    issues = [i for i in issues
              if not _is_protected(i.get("path"), i.get("owner"), i.get("references"), i.get("target"),
                                   *(i.get("paths") or []))]
    return issues''', '''    issues = [i for i in issues
              if not _is_protected(i.get("path"), i.get("owner"), i.get("references"), i.get("target"),
                                   *(i.get("paths") or []))]
    # G8: every finding names the agent that CREATED the file(s) involved ('unknown' when not recorded)
    try:
        _cr = mw.creators_for([x for i in issues for x in ([i.get("path")] + list(i.get("paths") or []))
                               if x and str(x).startswith("workspace/")])
        for i in issues:
            if i.get("paths"):
                i["created_by"] = {x: _cr.get(x, "unknown") for x in i["paths"]}
            else:
                i["created_by"] = _cr.get(i.get("path"), "unknown")
    except Exception:
        pass
    return issues''')
sub(AU, '''            body = "; ".join("%s: %s" % (i.get("type"), i.get("path") or i.get("owner") or "?") for i in hard[:6])''',
'''            def _by(i):   # G8: name the creating agent in the notification
                c = i.get("created_by")
                c = ", ".join(sorted(set(c.values()))) if isinstance(c, dict) else (c or "unknown")
                return " (created by %s)" % c
            body = "; ".join("%s: %s%s" % (i.get("type"), i.get("path") or i.get("owner") or "?", _by(i)) for i in hard[:6])''')
sub(AU, '''                    if str(dest) != str(p):
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(p), str(dest))   # binary-safe (no read_text)
                        mw.remove_file(p)                 # drop old odin_core_con row
                        mw.sync_row(dest)                 # index the new location''', '''                    if str(dest) != str(p):
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        _g8_cb = mw.get_creator(p)[1]     # G8: a move keeps the creator
                        shutil.move(str(p), str(dest))   # binary-safe (no read_text)
                        mw.remove_file(p)                 # drop old odin_core_con row
                        mw.sync_row(dest)                 # index the new location
                        if _g8_cb:
                            mw.set_creator(dest, _g8_cb)''')
# ---------------- claude_cli.py: PostToolUse creator hook + member env ----------------
sub(CC, '''_NOVM_HOOK = _HERE / "novm_hook.py"
''', '''_NOVM_HOOK = _HERE / "novm_hook.py"

_CREATOR_HOOK = _HERE / "creator_hook.py"   # G8: PostToolUse — records which agent created a new file
''')
sub(CC, '''    f = _HERE / ((".scope-settings-ro" if readonly else ".scope-settings") + ("-novm" if no_vm else "") + ".json")
    try:
        f.write_text(json.dumps({"hooks": {"PreToolUse": pre}}))''', '''    f = _HERE / ((".scope-settings-ro" if readonly else ".scope-settings") + ("-novm" if no_vm else "") + ".json")
    hooks = {"PreToolUse": pre}
    if not readonly:   # G8: after every agent write, record the creator of a NEW file (never blocks)
        hooks["PostToolUse"] = [{"matcher": "Write|Edit|MultiEdit|NotebookEdit",
                                 "hooks": [{"type": "command", "command": f"{py} {str(_CREATOR_HOOK)}"}]}]
    try:
        f.write_text(json.dumps({"hooks": hooks}))''')
sub(CC, '''                       cwd: str | None = None, readonly: bool = False, model: str | None = None,
                       no_vm: bool = False):''', '''                       cwd: str | None = None, readonly: bool = False, model: str | None = None,
                       no_vm: bool = False, member: str = ""):''')
sub(CC, '''        if no_vm:   # F-32c: the no-VM hook reads this flag
            _env["ODIN_NO_VM"] = "1"''', '''        if no_vm:   # F-32c: the no-VM hook reads this flag
            _env["ODIN_NO_VM"] = "1"
        _env["ODIN_MEMBER"] = member or ""   # G8: the creator hook records which agent wrote a new file''')
# ---------------- api_v2.py: pass the member; approval + step attribution ----------------
sub(API, '''def _engine_stream(text: str, lang: str, session_id: str, model: str, cwd: str | None = None,
                   readonly: bool = False, no_vm: bool = False):''', '''def _engine_stream(text: str, lang: str, session_id: str, model: str, cwd: str | None = None,
                   readonly: bool = False, no_vm: bool = False, member: str = ""):''')
sub(API, '''                    text, lang, session_id or None, cwd=cwd, readonly=readonly, model=model, no_vm=no_vm)''',
         '''                    text, lang, session_id or None, cwd=cwd, readonly=readonly, model=model, no_vm=no_vm,
                    member=member)''')
sub(API, '''            for evd in _engine_stream(p, "en", None, model, cwd=folder or None, readonly=ro, no_vm=not vm_intent):''',
         '''            for evd in _engine_stream(p, "en", None, model, cwd=folder or None, readonly=ro, no_vm=not vm_intent,
                                      member=member):''')
sub(API, '''        for evd in _engine_stream(apply_prompt, "en", None, model, cwd=folder or None, readonly=False):''',
         '''        for evd in _engine_stream(apply_prompt, "en", None, model, cwd=folder or None, readonly=False,
                                  member=member):''')
sub(API, '''            for evd in _engine_stream(prompt, "en", None, scope_model, cwd=folder or None):''',
         '''            for evd in _engine_stream(prompt, "en", None, scope_model, cwd=folder or None, member=who):''')
sub(API, '''        _reg = _register_applied_files(pid, a.get("files", []))''',
         '''        _reg = _register_applied_files(pid, a.get("files", []), creator_agent=member, approval_id=aid)''')
sub(API, '''def _register_applied_files(pid: str, files: list) -> dict:''',
         '''def _register_applied_files(pid: str, files: list, creator_agent: str = "", approval_id: str = "") -> dict:''')
sub(API, '''        _mw.sync_row(p)
        rep["indexed"].append(str(p.relative_to(ROOT)))''', '''        _g8_new = not _mw.get_creator(p)[0]
        _mw.sync_row(p)
        if _g8_new:   # G8: a file CREATED by an approved proposal records its agent (edits never change it)
            _mw.set_creator(p, _mw.make_creator(agent=creator_agent or None, project=pid,
                                                via=f"approved proposal {approval_id}".strip()))
        rep["indexed"].append(str(p.relative_to(ROOT)))''')
sub(API, '''            _outc, _odet = _step_outcome(pid, task, review, bool(step_clean), bool(qa_ok), _qa_ran,
                                         _step_t0, folder)''', '''            _outc, _odet = _step_outcome(pid, task, review, bool(step_clean), bool(qa_ok), _qa_ran,
                                         _step_t0, folder)
            try:   # G8: files CREATED during this member's step (any tool, e.g. Bash) record the member
                _attribute_step_files(pid, member, _step_t0, folder)
            except Exception:
                pass''')
sub(API, '''def _register_applied_files(''', '''def _attribute_step_files(pid: str, member: str, step_t0: float, folder: str = "") -> int:
    """G8: a file under workspace/ that was CREATED during this member's step and has no recorded creator
    gets this member, marked 'inferred from step' (the exact Write/Edit hook record always wins)."""
    import workspace_mw as _mw
    if not _mw.has_created_by():
        return 0
    ws = (ROOT / "workspace").resolve()
    roots = {(ws / "projects" / pid).resolve()}
    if folder:
        fp = pathlib.Path(os.path.expanduser(folder)).resolve()
        if ws in fp.parents or fp == ws:
            roots.add(fp)
    n = 0
    for r in roots:
        if not r.is_dir():
            continue
        for p in r.rglob("*"):
            if not p.is_file() or ({"data", "history", "logs", "chat", "chats", "node_modules", ".git"}
                                   & set(p.relative_to(ws).parts)):
                continue
            st = p.stat()
            born = getattr(st, "st_birthtime", st.st_ctime)
            if born < step_t0 - 5:
                continue
            existed, raw = _mw.get_creator(p)
            if raw:
                continue
            if not existed:
                _mw.sync_row(p)
            if _mw.set_creator(p, _mw.make_creator(agent=member, project=pid, via="inferred from step")):
                n += 1
    return n


def _register_applied_files(''')
print("G8 applied")
