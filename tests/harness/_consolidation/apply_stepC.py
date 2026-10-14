"""Step C code: F-45 (who approved, through which channel) + F-24 (an owner removal is remembered; re-creation refused)."""
import pathlib
def patch(path, a, b, n=1):
    p = pathlib.Path(path); s = p.read_text(); assert s.count(a) == n, (path, s.count(a), a[:80]); p.write_text(s.replace(a, b))
AP, A = "server/approvals.py", "server/api_v2.py"
# ---------------- F-45
patch(AP, '''def decide(aid: str, approved: bool, note: str = "") -> dict | None:
    items = _all()
    for a in items:
        if a["id"] == aid:
            a["status"] = "approved" if approved else "rejected"
            a["decided"] = store.now()
            a["note"] = note or ""''', '''CHANNELS = ("desktop", "phone", "web", "api", "chat", "bulk", "secure-field", "guard", "system", "unknown")


def decide(aid: str, approved: bool, note: str = "", by: str = "unknown", channel: str = "unknown") -> dict | None:
    """F-45: every decision records WHO decided (owner | odin) and through WHICH channel, and keeps a history."""
    items = _all()
    for a in items:
        if a["id"] == aid:
            a["status"] = "approved" if approved else "rejected"
            a["decided"] = store.now()
            a["note"] = note or ""
            a["decided_by"] = by or "unknown"
            a["decided_channel"] = channel if channel in CHANNELS else "unknown"
            a.setdefault("decisions", []).append({"ts": a["decided"], "approved": bool(approved), "by": a["decided_by"],
                                                  "channel": a["decided_channel"], "note": (note or "")[:200]})''')
patch(AP, '''        decide(x["id"], True, note="approved via approve-all after the owner confirmed the full list")''',
      '''        decide(x["id"], True, note="approved via approve-all after the owner confirmed the full list", by="owner", channel="bulk")''')
patch(A, '''        a = approvals.decide(aid, True, (body or {}).get("note", ""))''',
      '''        a = approvals.decide(aid, True, (body or {}).get("note", ""), by="owner", channel=_client_channel(body))''')
patch(A, '''        a = approvals.decide(aid, False, (body or {}).get("note", ""))''',
      '''        a = approvals.decide(aid, False, (body or {}).get("note", ""), by="owner", channel=_client_channel(body))''')
patch(A, '''    a = approvals.decide(aid, False, why) or {}''', '''    a = approvals.decide(aid, False, why, by="odin", channel="guard") or {}''')
patch(A, '''        _apx.decide(aid, False, f"not re-runnable: {a['historical']}")''',
      '''        _apx.decide(aid, False, f"not re-runnable: {a['historical']}", by="odin", channel="guard")''')
patch(A, '''approvals.decide(_old["id"], False, note="superseded — a new run started")''',
      '''approvals.decide(_old["id"], False, note="superseded — a new run started", by="odin", channel="system")''')
patch(A, '''                    approvals.decide(ap["id"], True, "owner chat approval (by id)")''',
      '''                    approvals.decide(ap["id"], True, "owner chat approval (by id)", by="owner", channel="chat")''')
patch("server/secret_store.py", '''    approvals.decide(aid, True, f"key {name} provided by the owner in the app (value stored by the app, not shown)")''',
      '''    approvals.decide(aid, True, f"key {name} provided by the owner in the app (value stored by the app, not shown)",
                     by="owner", channel="secure-field")''')
patch("desktop/src/api.js", '''  approveChange: (aid, note = "") => jpost(`/approvals/${aid}/approve`, { note }),''',
      '''  approveChange: (aid, note = "") => jpost(`/approvals/${aid}/approve`, { note, channel: "desktop" }),   // F-45''')
s = pathlib.Path("desktop/src/api.js").read_text()
if "/reject`, { note })" in s:
    patch("desktop/src/api.js", "/reject`, { note })", "/reject`, { note, channel: \"desktop\" })")
patch("odin_app/lib/api/anchor_api.dart", """      _post(_api('/approvals/$aid/approve'), _native(), {'note': note});""",
      """      _post(_api('/approvals/$aid/approve'), _native(), {'note': note, 'channel': 'phone'});   // F-45""")
patch("odin_app/lib/api/anchor_api.dart", """      _post(_api('/approvals/$aid/reject'), _native(), {'note': note});""",
      """      _post(_api('/approvals/$aid/reject'), _native(), {'note': note, 'channel': 'phone'});   // F-45""")
# ---------------- F-24 helpers (module level, before _outside_paths)
patch(A, '''def _outside_paths(pid: str, prop: dict, folder: str = "") -> list:''', '''def _client_channel(body) -> str:
    """F-45: which client approved (the desktop and phone apps say so); anything else is 'api'."""
    c = str((body or {}).get("channel", "")).strip().lower()
    return c if c in ("desktop", "phone", "web") else "api"


_NO_PATH_PROGS = ("rm", "rmdir", "ls", "cat", "stat", "test", "[", "echo", "head", "tail", "grep", "wc", "file")


def _resolve_raw(raw: str, base) -> "pathlib.Path | None":
    raw = str(raw or "").strip().strip("'\\"")
    if not raw or raw.startswith("-") or ("/" not in raw and not raw.endswith((".sh", ".plist", ".py", ".json"))):
        return None
    raw = raw.replace("$HOME", "~").replace("${HOME}", "~")
    q = pathlib.Path(os.path.expanduser(raw))
    if not q.is_absolute():
        q = (ROOT / raw) if raw.startswith("workspace/") else (pathlib.Path(base) / q)
    try:
        return q.resolve()
    except Exception:
        return None


def _removed_targets(prop: dict, base) -> list:
    """F-24: the paths an (owner-approved) proposal deletes — file actions 'delete' and rm/rmdir targets."""
    import shlex
    out = []
    for f in prop.get("files") or []:
        if str((f or {}).get("action", "")).lower() in ("delete", "remove"):
            q = _resolve_raw(f.get("path", ""), base)
            if q: out.append(q)
    for c in prop.get("commands") or []:
        if (c or {}).get("where") == "vm":
            continue
        for seg in re.split(r"&&|\\|\\||;|\\|", str(c.get("cmd", ""))):
            try:
                tok = shlex.split(seg)
            except Exception:
                tok = seg.split()
            if tok and os.path.basename(tok[0]) in ("rm", "rmdir", "trash"):
                for t in tok[1:]:
                    q = _resolve_raw(t, base) if not t.startswith("-") else None
                    if q: out.append(q)
    return out


def _remember_removals(pid: str, a: dict) -> list:
    """F-24: after an OWNER-approved removal is applied, remember it so Odin never silently puts it back."""
    if a.get("decided_by") != "owner":
        return []
    base = pathlib.Path(os.path.expanduser(a.get("cwd") or str(ROOT / "workspace" / "projects" / pid / "code")))
    gone = [str(q) for q in _removed_targets({"files": a.get("files"), "commands": a.get("commands")}, base)]
    if not gone:
        return []
    import projects as _pj
    cur = list((_pj.get_project(pid) or {}).get("ownerRemoved") or [])
    have = {x.get("path") for x in cur}
    for g in gone:
        if g not in have:
            cur.append({"path": g, "approval": a.get("id"), "ts": time.time()})
    _pj.set_flags(pid, ownerRemoved=cur)
    return gone


def _outside_paths(pid: str, prop: dict, folder: str = "") -> list:''')
patch(A, '''    bad = []
    for f in prop.get("files") or []:
        q = _res((f or {}).get("path", ""), base)
        if q is not None and not _inside(q):
            bad.append(f"file {f.get('path')}")''', '''    _removed = [(pathlib.Path(x["path"]), x) for x in (_proj.get("ownerRemoved") or []) if x.get("path")]
    def _was_removed(q):
        # F-24: the owner removed this path (or a folder containing it) — never re-create / reinstall it silently
        for rp, rec in _removed:
            if q == rp or rp in q.parents:
                _d = time.strftime("%Y-%m-%d", time.localtime(rec.get("ts") or 0))
                return f" — you REMOVED this on {_d} (approval {rec.get('approval')}); not re-creating it unless you say so"
        return ""
    bad = []
    for f in prop.get("files") or []:
        q = _res((f or {}).get("path", ""), base)
        if q is not None and _was_removed(q) and str((f or {}).get("action", "")).lower() not in ("delete", "remove"):
            bad.append(f"file {f.get('path')}{_was_removed(q)}"); continue
        if q is not None and not _inside(q):
            bad.append(f"file {f.get('path')}")''')
patch(A, '''            if prog in ("ssh", "sshpass", "az"):
                break            # the rest runs REMOTELY (VM rules apply); its paths are not local writes''',
'''            if prog in ("ssh", "sshpass", "az"):
                break            # the rest runs REMOTELY (VM rules apply); its paths are not local writes
            if _removed and prog not in _NO_PATH_PROGS:   # F-24: any use of a removed path (copy, load, run its installer)
                _hit = next((w for w in (_was_removed(q) for q in (_resolve_raw(t, cwd) for t in tok) if q) if w), "")
                if _hit:
                    bad.append(f"command `{seg.strip()[:80]}`{_hit}")
                    break''')
patch(A, '''    result = "\\n".join(out)
    approvals.mark_applied(aid, result)''', '''    try:   # F-24: remember what the OWNER had removed, so it is never silently put back
        _gone = _remember_removals(pid, approvals.get(aid) or a)
        if _gone:
            out.append(f"[removed — remembered, will not be re-created without your say-so] {len(_gone)} path(s)")
    except Exception:
        pass
    result = "\\n".join(out)
    approvals.mark_applied(aid, result)''')
print("ok")
