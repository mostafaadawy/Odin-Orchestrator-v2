#!/usr/bin/env python3
"""Apply fix #1 (G4 parser + G3 registration + resolve_capability overlay path). Exact-anchor edits; aborts if any anchor is missing."""
import pathlib, sys
R = pathlib.Path(__file__).resolve().parent.parent
api = R / "server/api_v2.py"; mwp = R / "server/workspace_mw.py"
a = api.read_text(); m = mwp.read_text()

# --- 1) parser: prefer ```proposal, else LAST fenced json block with files/commands, else brace scan ---
old_p = '''    blob = None
    m = _re.search(r"```(?:proposal|json)?\\s*(\\{.*?\\})\\s*```", text, _re.DOTALL)
    if m:
        blob = m.group(1)
    elif '"files"' in text or '"commands"' in text:'''
new_p = '''    blob = None
    # FIX #1 (G4, 2026-10-11): an agent often SHOWS file contents in ```json blocks before its ```proposal
    # block; taking the first block lost the proposal (S1/S2/S4 replay: 4 of 6). Prefer an explicit
    # ```proposal block; else the LAST fenced json block that carries files/commands; else the brace scan.
    _fences = _re.findall(r"```(\\w*)\\s*(\\{.*?\\})\\s*```", text, _re.DOTALL)
    _cands = [b for (lang, b) in _fences if lang.lower() == "proposal"]
    if not _cands:
        _cands = [b for (lang, b) in _fences if lang.lower() in ("", "json") and ('"files"' in b or '"commands"' in b)]
    m = None
    if _cands:
        blob = _cands[-1]
    elif '"files"' in text or '"commands"' in text:'''
assert a.count(old_p) == 1, "parser anchor"
a = a.replace(old_p, new_p)

# --- 2) registration helper + calls ---
helper = '''

def _register_applied_files(pid: str, files: list) -> dict:
    """FIX #1 (G3, 2026-10-11): after APPROVED files are written, keep odin_core in lockstep through the
    existing middleware functions. Each approved file under workspace/ is indexed (sync_row infers the owner
    from its real location). A file under THIS project whose header says it is a delta over a shared
    capability is registered as that project's dependency (manifest + dependencies row, mode=extend,
    overlay relative to the project). Files outside this project are NEVER registered under it - they are
    indexed under their true owner and reported as out-of-scope for the audit."""
    import workspace_mw as _mw
    ws = (ROOT / "workspace").resolve()
    proj = (ws / "projects" / pid).resolve()
    rep = {"indexed": [], "deltas": [], "out_of_scope": [], "skipped": []}
    for f in files or []:
        raw = str((f or {}).get("path", "")).strip()
        if not raw or "<" in raw:
            rep["skipped"].append(raw); continue
        p = pathlib.Path(os.path.expanduser(raw))
        p = (p if p.is_absolute() else ROOT / p).resolve()
        if not p.is_file() or ws not in p.parents:
            rep["skipped"].append(raw); continue
        _mw.sync_row(p)
        rep["indexed"].append(str(p.relative_to(ROOT)))
        if proj not in p.parents:
            rep["out_of_scope"].append(str(p.relative_to(ROOT))); continue
        try:
            head = p.read_text(errors="replace")[:600]
        except Exception:
            head = ""
        mm = re.search(r"delta over shared capability:\\s*(shared/[\\w./-]+)", head)
        if mm and (ws / mm.group(1)).is_file():
            base = mm.group(1)
            _mw.add_dependency("project", pid, pathlib.Path(base).name, base, kind="code", mode="extend",
                               overlay=str(p.relative_to(proj)))
            rep["deltas"].append({"overlay": str(p.relative_to(proj)), "base": base})
    return rep
'''
anchor_def = "\ndef _apply_approval_bg(aid: str):"
assert a.count(anchor_def) == 1, "apply_bg anchor"
a = a.replace(anchor_def, helper + anchor_def)

old_bg = '''    result = "\\n".join(out)
    approvals.mark_applied(aid, result)'''
new_bg = '''    try:   # FIX #1 (G3): register what was actually written, under its true owner
        _reg = _register_applied_files(pid, a.get("files", []))
        if _reg.get("deltas") or _reg.get("out_of_scope"):
            out.append(f"[registry] indexed={len(_reg['indexed'])} deltas={_reg['deltas']} out_of_scope={_reg['out_of_scope']}")
    except Exception as _e:
        out.append(f"[registry] registration error: {_e}")
    result = "\\n".join(out)
    approvals.mark_applied(aid, result)'''
assert a.count(old_bg) == 1, "bg mark_applied anchor"
a = a.replace(old_bg, new_bg)

old_in = '''    if apply_id:
        approvals.mark_applied(apply_id, full)
    yield ("__return__", {"reply": reply + "\\n\\n[Applied after approval] " + full,'''
new_in = '''    try:   # FIX #1 (G3): register inline-applied (pre-authorized) files too
        _register_applied_files(pid, prop.get("files", []))
    except Exception:
        pass
    if apply_id:
        approvals.mark_applied(apply_id, full)
    yield ("__return__", {"reply": reply + "\\n\\n[Applied after approval] " + full,'''
assert a.count(old_in) == 1, "inline anchor"
a = a.replace(old_in, new_in)

# --- 3) resolve_capability: overlay relative to the project first, then code/<overlay> (legacy) ---
old_r = '''    overlay_path = (WS / _area(owner_type) / owner_id / "code" / overlay) if overlay else None'''
new_r = '''    overlay_path = None
    if overlay:   # FIX #1 (2026-10-11): manifests store overlays relative to the owner folder (deploy/x.config.sh,
        _own = WS / _area(owner_type) / owner_id          # tests/); keep the legacy code/<overlay> form as fallback.
        overlay_path = _own / overlay if (_own / overlay).exists() else _own / "code" / overlay'''
assert m.count(old_r) == 1, "resolve anchor"
m = m.replace(old_r, new_r)

api.write_text(a); mwp.write_text(m); print("fix1 applied")
