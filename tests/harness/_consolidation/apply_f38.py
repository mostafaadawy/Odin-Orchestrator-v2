#!/usr/bin/env python3
"""F-38: every project always has a folder (declared local path, else workspace/projects/<id>/code); a proposal that
writes outside the workspace or that folder is REFUSED and shown to the owner (at proposal time and at apply time)."""
import pathlib, sys
R = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
def sub(path, old, new, count=1):
    p = R / path; s = p.read_text()
    assert s.count(old) == count, (path, old[:70], s.count(old)); p.write_text(s.replace(old, new))
PJ, API = "server/projects.py", "server/api_v2.py"
# ---- 1) the intake/create path ALWAYS sets the project folder ----
sub(PJ, '''        except Exception:
            created_path = local_path
    proj = {''', '''        except Exception:
            created_path = local_path
    if not (created_path or local_path):
        # F-38: no declared folder → the standard one, workspace/projects/<id>/code (never left empty)
        _std = store.WS / "projects" / pid / "code"
        try:
            _std.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        created_path = str(_std)
    proj = {''')
# ---- 2) the guard ----
sub(API, '''def _parse_proposal(text: str):''', '''_SAFE_DEV = ("/dev/null", "/dev/stdout", "/dev/stderr")


def _outside_paths(pid: str, prop: dict, folder: str = "") -> list:
    """F-38: every target of a proposal (file paths and the write targets of LOCAL commands) that lies OUTSIDE
    the workspace and the project's declared folder. VM commands are governed by the VM rules, not here."""
    import shlex
    ws = (ROOT / "workspace").resolve()
    roots = [ws]
    try:
        import projects as _pj
        lp = ((_pj.get_project(pid) or {}).get("localPath") or "").strip()
    except Exception:
        lp = ""
    if lp:
        roots.append(pathlib.Path(os.path.expanduser(lp)).resolve())
    base = pathlib.Path(os.path.expanduser(folder or lp or str(ws / "projects" / pid / "code")))
    def _res(raw, cwd):
        raw = str(raw).strip().strip("'\\"")
        if not raw or raw in _SAFE_DEV:
            return None
        raw = raw.replace("<project localPath>", lp or str(base)).replace("$HOME", "~").replace("${HOME}", "~")
        q = pathlib.Path(os.path.expanduser(raw))
        if not q.is_absolute():
            if raw.startswith("workspace/"):
                q = ROOT / raw
            else:
                q = cwd / q
        return q.resolve()
    def _inside(q):
        return any(q == r or r in q.parents for r in roots)
    bad = []
    for f in prop.get("files") or []:
        q = _res((f or {}).get("path", ""), base)
        if q is not None and not _inside(q):
            bad.append(f"file {f.get('path')}")
    for c in prop.get("commands") or []:
        if (c or {}).get("where") == "vm":
            continue
        cmd = str(c.get("cmd", "")).split("<<")[0].split("\\n")[0]
        cwd = base
        for seg in re.split(r"&&|\\|\\||;|\\|", cmd):
            try:
                tok = shlex.split(seg)
            except Exception:
                tok = seg.split()
            if not tok:
                continue
            targets = []
            for i, t in enumerate(tok):
                if t in (">", ">>", "1>", "2>") and i + 1 < len(tok):
                    targets.append(tok[i + 1])
                elif re.match(r"^\\d?>>?[^>&]", t):
                    targets.append(re.sub(r"^\\d?>>?", "", t))
                elif t.startswith("~") or t.startswith("$HOME"):
                    targets.append(t)
            prog = tok[0]
            args = [t for t in tok[1:] if not t.startswith("-")]
            if prog == "cd" and args:
                q = _res(args[0], cwd)
                if q is not None and not _inside(q):
                    bad.append(f"command `{seg.strip()[:80]}`")
                elif q is not None:
                    cwd = q
                continue
            if prog in ("mkdir", "touch", "tee", "rm", "rmdir") and args:
                targets += args
            if prog in ("cp", "mv", "ln", "install") and len(args) >= 2:
                targets.append(args[-1])
            if prog == "rsync" and len(args) >= 2 and "@" not in args[-1] and ":" not in args[-1]:
                targets.append(args[-1])
            for t in targets:
                q = _res(t, cwd)
                if q is not None and not _inside(q):
                    bad.append(f"command `{seg.strip()[:80]}`")
                    break
    return list(dict.fromkeys(bad))


def _refuse_outside(pid: str, member: str, prop: dict, bad: list, folder: str = "", title: str = "", aid: str = "") -> dict:
    """F-38: refuse a proposal that writes outside the workspace / declared folder, and SHOW it to the owner:
    it is recorded as a rejected approval with the reason, and a notification is raised."""
    import approvals
    why = "refused automatically: writes outside the workspace and the project folder — " + "; ".join(bad[:6])
    if not aid:
        ap = approvals.create(pid, member, title=(title or "Proposed changes")[:80], summary=prop.get("summary", ""),
                              files=prop.get("files") or [], commands=prop.get("commands") or [], cwd=folder, inline=False,
                              kind="change")
        aid = ap["id"]
    a = approvals.decide(aid, False, why) or {}
    try:
        import notifications_store as _ns
        _ns.add(kind="finding", title=f"Refused: {member} proposed writing outside the project folder",
                body=why[:600], pid=pid, severity="attention", icon="\\u26d4")
    except Exception:
        pass
    return {"id": aid, "status": a.get("status", "rejected"), "note": why}


def _parse_proposal(text: str):''')
# ---- 3) refuse at proposal time (member runs) ----
sub(API, '''    nf, nc = len(prop["files"]), len(prop["commands"])
    # F-32: a pre-authorized run WITHOUT VM intent never applies VM-touching commands inline.''', '''    nf, nc = len(prop["files"]), len(prop["commands"])
    _bad = _outside_paths(pid, prop, folder)
    if _bad:   # F-38: never create or apply a proposal that writes outside the workspace / project folder
        _r = _refuse_outside(pid, member, prop, _bad, folder, task_label)
        yield sse("status", {"icon": "\\u26d4", "text": f"{member}: proposal REFUSED — it writes outside the project folder ({'; '.join(_bad[:3])}). Shown to you as {_r['id']}."})
        if cid:
            scopes.add_message(scope, cid, "assistant", f"\\u26d4 [Refused {_r['id']}] {_r['note']}")
        yield ("__return__", {"reply": reply, "approved": False, "applied": False, "refused": _r}); return
    # F-32: a pre-authorized run WITHOUT VM intent never applies VM-touching commands inline.''')
# ---- 4) refuse at proposal time (chat) ----
sub(API, '''            if prop:
                who = member or "Project CTO"
                ap = approvals.create(pid, who, title=(text[:60] or "Proposed changes"),''', '''            _bad = _outside_paths(pid, prop, proj_cwd or "") if prop else []
            if prop and _bad:   # F-38
                who = member or "Project CTO"
                _r = _refuse_outside(pid, who, prop, _bad, proj_cwd or "", text[:60])
                scopes.add_message(scope, cid, "assistant", f"\\u26d4 [Refused {_r['id']}] {_r['note']}")
                yield sse("status", {"icon": "\\u26d4", "text": f"Proposal refused — writes outside the project folder. Shown as {_r['id']}."})
                prop = None
            if prop:
                who = member or "Project CTO"
                ap = approvals.create(pid, who, title=(text[:60] or "Proposed changes"),''')
# ---- 5) refuse at apply time (an older or edited proposal approved later) ----
sub(API, '''    pid, member, folder = a["pid"], a["member"], (a.get("cwd") or "")
    out, log_lines = [], []   # log_lines = clear, in-points record for the member chat''', '''    pid, member, folder = a["pid"], a["member"], (a.get("cwd") or "")
    _bad = _outside_paths(pid, {"files": a.get("files") or [], "commands": a.get("commands") or []}, folder)
    if _bad:   # F-38: even an approved proposal never writes outside the workspace / project folder
        _refuse_outside(pid, member, a, _bad, folder, aid=aid)
        with _APPLY_LOCK:
            _APPLYING.discard(aid)
        return
    out, log_lines = [], []   # log_lines = clear, in-points record for the member chat''')
print("F-38 applied")

# ---- F-38 part 2: `cd` is not a write; segments run over ssh/sshpass/az are remote; "~" counts only as a write target (applied in-tree)
