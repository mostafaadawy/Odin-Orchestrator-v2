#!/usr/bin/env python3
"""G6: a promotion must leave NO dangling reference, and the audit must REPORT one if it exists."""
import pathlib, sys
R = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
def sub(path, old, new, count=1):
    p = R / path; s = p.read_text()
    assert s.count(old) == count, (path, old[:60], s.count(old)); p.write_text(s.replace(old, new))
MW, AU = "server/workspace_mw.py", "server/workspace_audit.py"
# ---------------- workspace_mw.py ----------------
sub(MW, "import pathlib, datetime, json, shutil\n", "import pathlib, datetime, json, shutil, re\n")
sub(MW, "def _rewrite_owner_refs(owner_type, owner_id, old_variants, new_rel) -> int:",
'''# ── G6: moves are RECORDED and references FOLLOW them, so a promotion never leaves a dangling reference ──
MOVES_LOG = WS / "history" / "moves.jsonl"
REF_EXT = {".py", ".sh", ".js", ".ts", ".dart", ".json", ".md"}
RECORD_DIRS = {"data", "history", "logs", "chat", "chats"}   # historical records: never rewritten, never audited


def _ws_rel(ref) -> str:
    s = str(ref).replace("\\\\", "/")
    return s[len("workspace/"):] if s.startswith("workspace/") else s


def _swap_ref(txt: str, old_ws: str, new_rel: str) -> str:
    """Replace a reference to old_ws (workspace-relative) with new_rel and KEEP its form: a reference
    written with the 'workspace/' prefix stays prefixed, so it still resolves from the repo root."""
    if not old_ws:
        return txt
    txt = txt.replace("workspace/" + old_ws, "workspace/" + new_rel)
    return re.sub(r"(?<![\\w/\\-])" + re.escape(old_ws), new_rel, txt)


def record_move(old_ref, new_rel) -> None:
    try:
        MOVES_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(MOVES_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": datetime.datetime.now().isoformat(),
                                 "from": _ws_rel(old_ref), "to": _ws_rel(new_rel)}) + "\\n")
    except Exception:
        pass


def moved_to(ref):
    """Where a file that used to be at `ref` lives NOW (following chains of moves), or None."""
    s = _ws_rel(ref)
    try:
        lines = MOVES_LOG.read_text(errors="replace").splitlines()
    except Exception:
        return None
    m = {}
    for ln in lines:
        try:
            d = json.loads(ln); m[d["from"]] = d["to"]
        except Exception:
            pass
    cur, seen = s, set()
    while cur in m and cur not in seen:
        seen.add(cur); cur = m[cur]
    return cur if cur != s and (WS / cur).is_file() else None


def capability_files(exts=None):
    """Every non-record text file of every project/agent: (owner_type, owner_id, path)."""
    for ot in ("project", "agent"):
        base = WS / _area(ot)
        if not base.exists():
            continue
        for f in base.glob("*/**/*"):
            rel = f.relative_to(base).parts
            if len(rel) < 2 or rel[1] in RECORD_DIRS or not f.is_file():
                continue
            if f.suffix.lower() in (exts or REF_EXT):
                yield ot, rel[0], f


def repoint_everywhere(old_ref, new_rel) -> list:
    """Rewrite EVERY owner's file that references old_ref (not only the consumers the caller knew about)
    so it reads new_rel. Each rewritten owner gets a dependency on the shared file. Returns [owner]."""
    old_ws, new_ws = _ws_rel(old_ref), _ws_rel(new_rel)
    owners = []
    for ot, oid, f in capability_files():
        try:
            txt = f.read_text(errors="replace")
        except Exception:
            continue
        new = _swap_ref(txt, old_ws, new_ws)
        if new != txt:
            f.write_text(new, encoding="utf-8")
            sync_row(f)
            if (ot, oid) not in owners:
                owners.append((ot, oid))
                if new_ws.startswith("shared/"):
                    add_dependency(ot, oid, pathlib.PurePath(new_ws).name, new_ws)
    return [f"{a}/{b}" for a, b in owners]


def _rewrite_owner_refs(owner_type, owner_id, old_variants, new_rel) -> int:''')
sub(MW, '''        new = txt
        for v in old_variants:
            if v:
                new = new.replace(v, new_rel)
        if new != txt:
            f.write_text(new, encoding="utf-8")
            sync_row(f)
            n += 1
    return n''', '''        new = txt
        for v in {_ws_rel(v) for v in old_variants if v}:
            new = _swap_ref(new, v, new_rel)          # G6: keep the reference's form so it still resolves
        if new != txt:
            f.write_text(new, encoding="utf-8")
            sync_row(f)
            n += 1
    return n''')
sub(MW, '''    remove_file(p)                               # drop the old odin_core_con file row
    sync_row(dest)                               # index the shared location
''', '''    remove_file(p)                               # drop the old odin_core_con file row
    sync_row(dest)                               # index the shared location
    record_move(old_ws, dest_rel)                # G6: so a reference written later can still be repointed
''')
sub(MW, '''        repointed.append(f"{cot}/{cid}")
    return {"promoted": dest_rel,''', '''        repointed.append(f"{cot}/{cid}")
    # G6: ANY other owner that referenced the old path follows it too (otherwise it dangles)
    for o in repoint_everywhere(old_ws, dest_rel):
        if o not in repointed:
            repointed.append(o)
    return {"promoted": dest_rel,''')
sub(MW, '''    variants = {old_ref, old_ref.replace("workspace/", "", 1),
                ("workspace/" + old_ref) if not old_ref.startswith("workspace/") else old_ref}
    new = txt
    for v in variants:
        if v:
            new = new.replace(v, new_rel)
    if new == txt:''', '''    new = _swap_ref(txt, _ws_rel(old_ref), _ws_rel(new_rel))   # G6: keeps the reference's form
    if new == txt:''')
# ---------------- workspace_audit.py ----------------
sub(AU, '''    issues += _external_writes()
    # PROTECTED projects''', '''    # (d) DANGLING REFERENCE (G6) — a capability file that references a file inside a real project or in
    # shared/ that does NOT exist. Before G6 a reference whose target was gone was silently skipped, so a
    # promotion that left one behind made the audit report 0. Records (data/, history/, logs/) and .md
    # notes (which may name planned files) are not checked.
    dang_re = re.compile(r'(?<![\\w/\\-])((?:workspace/)?(?:projects/([A-Za-z0-9_\\-]+)|shared)/[A-Za-z0-9_\\-/\\.]+)')
    for _ot, _oid, p in mw.capability_files(exts={".py", ".sh", ".js", ".ts", ".dart", ".json"}):
        if not _interesting(p):
            continue
        try:
            txt = p.read_text(errors="replace")
        except Exception:
            continue
        for m in dang_re.finditer(txt):
            ref = m.group(1).rstrip("\\"').,)")
            pid = m.group(2)
            if pid is not None and pid != "_shared" and pid not in real_projects:
                continue                      # not a real project id: a path-like mention, not a dependency
            if "." not in pathlib.PurePath(ref).name or ".." in ref:
                continue                      # a folder or a relative mention, not a file reference
            if (WS / mw._ws_rel(ref)).is_file():
                continue
            issues.append({"type": "dangling-ref", "path": str(p.relative_to(ROOT)), "ref": ref,
                           "moved_to": mw.moved_to(ref),
                           "reason": f"references {ref}, which does not exist"})
    issues += _external_writes()
    # PROTECTED projects''')
sub(AU, '''    HARD = ("external-write", "foreign-ref", "parallel-registry", "misplaced", "duplicate")''',
        '''    HARD = ("external-write", "foreign-ref", "dangling-ref", "parallel-registry", "misplaced", "duplicate")''')
sub(AU, '''                for x in others:
                    op = ROOT / x
                    if op.exists():
                        op.unlink()
                    mw.remove_file(op)
                fix = f"promoted identical duplicate -> {res['promoted']}; repointed {res['repointed']}"''',
'''                for x in others:
                    op = ROOT / x
                    if op.exists():
                        op.unlink()
                    mw.remove_file(op)
                    # G6: the removed copy's references follow it to shared (any owner), and the move is recorded
                    mw.record_move(x, res["promoted"])
                    for o in mw.repoint_everywhere(x, res["promoted"]):
                        if o not in res["repointed"]:
                            res["repointed"].append(o)
                fix = f"promoted identical duplicate -> {res['promoted']}; repointed {res['repointed']}"''')
sub(AU, '''            elif t == "foreign-ref":
                if iss.get("target_exists") and iss.get("target"):''', '''            elif t == "foreign-ref" and iss.get("target") and not (ROOT / iss["target"]).is_file():
                # G6: an earlier action in this heal already moved the target — follow the recorded move
                nt = mw.moved_to(iss["target"])
                if nt:
                    rewrote = mw.repoint_reference(ROOT / iss["path"], iss.get("ref_match") or iss["target"], nt)
                    fix = f"target already moved -> {nt}; referrer source rewritten: {rewrote}"
                else:
                    fix = (f"FLAGGED: {iss['owner']} references {iss['target']}, which no longer exists "
                           f"and has no recorded move — needs owner review")
            elif t == "dangling-ref":
                nt = iss.get("moved_to") or mw.moved_to(iss["ref"])
                if nt:
                    rewrote = mw.repoint_reference(ROOT / iss["path"], iss["ref"], nt)
                    fix = f"repointed dangling reference {iss['ref']} -> {nt} (recorded move); rewritten: {rewrote}"
                else:
                    fix = (f"FLAGGED: {iss['path']} references {iss['ref']}, which does not exist and has no "
                           f"recorded move — needs owner review")
            elif t == "foreign-ref":
                if iss.get("target_exists") and iss.get("target"):''')
if "--part2" not in sys.argv:
    pass
print("G6 applied (part 1 already in tree)" if "--part2" in sys.argv else "G6 applied")
# ---- G6 part 2 (found by the baseline check in a fresh copy): secret dotfiles + one issue per reference ----
if "--part2" in sys.argv:
    sub(AU, '''            if "." not in pathlib.PurePath(ref).name or ".." in ref:
                continue                      # a folder or a relative mention, not a file reference''',
'''            _nm = pathlib.PurePath(ref).name
            if "." not in _nm or ".." in ref:
                continue                      # a folder or a relative mention, not a file reference
            if _nm.startswith("."):
                continue                      # secret dotfile (.cred/.auth/.env): never in git, supplied per install
            if (str(p), ref) in _dang_seen:
                continue
            _dang_seen.add((str(p), ref))''')
    sub(AU, '''    for _ot, _oid, p in mw.capability_files(exts={".py", ".sh", ".js", ".ts", ".dart", ".json"}):''',
'''    _dang_seen = set()
    for _ot, _oid, p in mw.capability_files(exts={".py", ".sh", ".js", ".ts", ".dart", ".json"}):''')
    print("G6 part 2 applied")
# ---- G6 part 3 (found by phase7_strong: a new moves.jsonl broke the exact-baseline check): moves go into the
# existing mw-corrections.jsonl as kind="move" (applied in-tree by an inline script; recorded here for review) ----
