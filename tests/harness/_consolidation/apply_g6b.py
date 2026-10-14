#!/usr/bin/env python3
"""G6b (owner condition on G6): every automatic reference rewrite is LOGGED (file, old path, new path, time,
reason) and REVERSIBLE with one command (`python server/rewrite_log.py revert <batch>`)."""
import pathlib, sys
R = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
def sub(path, old, new, count=1):
    p = R / path; s = p.read_text()
    assert s.count(old) == count, (path, old[:70], s.count(old)); p.write_text(s.replace(old, new))
MW, AU = "server/workspace_mw.py", "server/workspace_audit.py"
# 1) batch context, change log, rewrite helper, revert — inserted right after the G6 header constants
sub(MW, '''RECORD_DIRS = {"data", "history", "logs", "chat", "chats"}   # historical records: never rewritten, never audited
''', '''RECORD_DIRS = {"data", "history", "logs", "chat", "chats"}   # historical records: never rewritten, never audited

# ── G6b (owner condition): every automatic change is LOGGED and REVERSIBLE with one command ──────────────
# One action (one promotion / one audit heal) = one BATCH id. Logged per change, in the existing middleware
# log: kind "ref-rewrite" (file, old path, new path, time, reason, the file's previous content), "move",
# "copy-removed", and on undo "revert" + "hold". Undo: `python server/rewrite_log.py revert <batch>`.
import contextlib as _ctx, hashlib as _hl, uuid as _uuid
_BATCH = {"id": None, "reason": None}
_KEEP_BEFORE = 512 * 1024          # previous content is stored for files up to 512 KB (larger: not revertible)


@_ctx.contextmanager
def rewrite_batch(reason):
    if _BATCH["id"]:                   # nested call joins the outer action
        yield _BATCH["id"]
        return
    _BATCH.update(id=_uuid.uuid4().hex[:12], reason=str(reason)[:300])
    try:
        yield _BATCH["id"]
    finally:
        _BATCH.update(id=None, reason=None)


def _sha(t: str) -> str:
    return _hl.sha256(t.encode("utf-8", "replace")).hexdigest()


def _log_change(rec: dict) -> None:
    try:
        rec = {"ts": datetime.datetime.now().isoformat(), "batch": _BATCH["id"] or "unbatched",
               "reason": _BATCH["reason"] or "automatic change", **rec}
        MOVES_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(MOVES_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\\n")
        sync_row(MOVES_LOG)
    except Exception:
        pass


def _apply_rewrite(f, before: str, after: str, old_ref: str, new_ref: str) -> None:
    f.write_text(after, encoding="utf-8")
    sync_row(f)
    _log_change({"kind": "ref-rewrite", "file": str(pathlib.Path(f).relative_to(ROOT)), "old": old_ref,
                 "new": new_ref, "before": before if len(before) <= _KEEP_BEFORE else None,
                 "after_sha": _sha(after)})


def change_log(batch=None) -> list:
    try:
        lines = MOVES_LOG.read_text(errors="replace").splitlines()
    except Exception:
        return []
    out = []
    for ln in lines:
        try:
            d = json.loads(ln)
        except Exception:
            continue
        if d.get("kind") in ("ref-rewrite", "move", "copy-removed", "revert", "hold") and \\
                (batch is None or d.get("batch") == batch or d.get("reverts") == batch):
            out.append(d)
    return out


def _reverted_batches() -> set:
    return {d.get("reverts") for d in change_log() if d.get("kind") == "revert"}


def held_paths() -> set:
    s = set()
    for d in change_log():
        if d.get("kind") == "hold":
            s.update(d.get("paths") or [])
    return s


def record_removed_copy(path, kept_rel) -> None:
    p = ROOT / path if not pathlib.Path(path).is_absolute() else pathlib.Path(path)
    try:
        txt = (WS / _ws_rel(kept_rel)).read_text(errors="replace")
    except Exception:
        txt = None
    _log_change({"kind": "copy-removed", "path": _ws_rel(pathlib.Path(p).relative_to(ROOT)),
                 "kept": _ws_rel(kept_rel), "content": txt if (txt is not None and len(txt) <= _KEEP_BEFORE) else None})


def revert_batch(batch: str, hold: bool = True) -> dict:
    """Undo ONE logged action exactly: restore every rewritten file's previous content (only if it was not
    edited since), move the file back from shared, recreate removed copies, drop the dependency rows the
    action created, and (hold=True) tell the audit not to redo it. Returns what was done and skipped."""
    recs = [d for d in change_log(batch) if d.get("batch") == batch]
    if not recs:
        return {"ok": False, "error": f"no logged changes for batch {batch}"}
    if batch in _reverted_batches():
        return {"ok": False, "error": f"batch {batch} was already reverted"}
    done, skipped, touched = [], [], set()
    for d in reversed([r for r in recs if r["kind"] == "ref-rewrite"]):
        f = ROOT / d["file"]; touched.add(_ws_rel(d["file"]))
        if d.get("before") is None:
            skipped.append(f"{d['file']}: previous content not stored (file too large)"); continue
        if not f.is_file():
            skipped.append(f"{d['file']}: file no longer exists"); continue
        if _sha(f.read_text(errors="replace")) != d["after_sha"]:
            skipped.append(f"{d['file']}: edited after the rewrite — left as is"); continue
        f.write_text(d["before"], encoding="utf-8"); sync_row(f)
        done.append(f"restored {d['file']} ({d['new']} -> {d['old']})")
    for d in reversed([r for r in recs if r["kind"] == "move"]):
        src, dst = WS / d["to"], WS / d["from"]; touched.update({d["to"], d["from"]})
        if dst.exists():
            skipped.append(f"{d['from']}: already exists — not overwritten"); continue
        if not src.is_file():
            skipped.append(f"{d['to']}: not found — cannot move back"); continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        if d.get("created_shared", True):
            shutil.move(str(src), str(dst)); remove_file(src)
            conn = _db()
            if conn:
                try:
                    conn.cursor().execute("DELETE FROM dependencies WHERE shared_capability_id=%s", (d["to"],))
                    conn.commit()
                finally:
                    conn.close()
            done.append(f"moved back {d['to']} -> {d['from']} (its dependency rows removed)")
        else:
            shutil.copy2(str(src), str(dst))
            done.append(f"restored {d['from']} (copy of {d['to']}, which existed before this action)")
        sync_row(dst)
    for d in [r for r in recs if r["kind"] == "copy-removed"]:
        p = WS / d["path"]; touched.add(d["path"])
        if p.exists():
            skipped.append(f"{d['path']}: already exists"); continue
        if d.get("content") is None:
            skipped.append(f"{d['path']}: content not stored"); continue
        p.parent.mkdir(parents=True, exist_ok=True); p.write_text(d["content"], encoding="utf-8"); sync_row(p)
        done.append(f"recreated removed copy {d['path']}")
    rec = {"ts": datetime.datetime.now().isoformat(), "kind": "revert", "reverts": batch,
           "done": done, "skipped": skipped}
    _append_raw(rec)
    if hold:
        _append_raw({"ts": rec["ts"], "kind": "hold", "batch": batch,
                     "paths": sorted("workspace/" + t for t in touched),
                     "reason": "owner reverted this action — the audit FLAGS these paths instead of redoing it"})
    return {"ok": True, "batch": batch, "done": done, "skipped": skipped, "held": hold}


def _append_raw(rec: dict) -> None:
    MOVES_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(MOVES_LOG, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False) + "\\n")
    sync_row(MOVES_LOG)
''')
# 2) record_move goes through the batch log (and says whether the shared file was created by this move)
sub(MW, '''def record_move(old_ref, new_rel) -> None:
    try:
        MOVES_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(MOVES_LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"ts": datetime.datetime.now().isoformat(), "kind": "move",
                                 "from": _ws_rel(old_ref), "to": _ws_rel(new_rel)}) + "\\n")
        sync_row(MOVES_LOG)
    except Exception:
        pass''', '''def record_move(old_ref, new_rel, created_shared=True) -> None:
    _log_change({"kind": "move", "from": _ws_rel(old_ref), "to": _ws_rel(new_rel),
                 "created_shared": bool(created_shared)})''')
# 3) moved_to ignores reverted actions
sub(MW, '''    m = {}
    for ln in lines:
        try:
            d = json.loads(ln)
            if d.get("kind") == "move":
                m[d["from"]] = d["to"]''', '''    m = {}
    rev = _reverted_batches()
    for ln in lines:
        try:
            d = json.loads(ln)
            if d.get("kind") == "move" and d.get("batch") not in rev:
                m[d["from"]] = d["to"]''')
# 4) every rewrite path logs through _apply_rewrite
sub(MW, '''        new = _swap_ref(txt, old_ws, new_ws)
        if new != txt:
            f.write_text(new, encoding="utf-8")
            sync_row(f)
            if (ot, oid) not in owners:''', '''        new = _swap_ref(txt, old_ws, new_ws)
        if new != txt:
            _apply_rewrite(f, txt, new, old_ws, new_ws)          # G6b: logged + reversible
            if (ot, oid) not in owners:''')
sub(MW, '''        new = txt
        for v in {_ws_rel(v) for v in old_variants if v}:
            new = _swap_ref(new, v, new_rel)          # G6: keep the reference's form so it still resolves
        if new != txt:
            f.write_text(new, encoding="utf-8")
            sync_row(f)
            n += 1''', '''        new = txt
        olds = sorted({_ws_rel(v) for v in old_variants if v})
        for v in olds:
            new = _swap_ref(new, v, new_rel)          # G6: keep the reference's form so it still resolves
        if new != txt:
            _apply_rewrite(f, txt, new, ", ".join(olds), _ws_rel(new_rel))   # G6b: logged + reversible
            n += 1''')
sub(MW, '''    new = _swap_ref(txt, _ws_rel(old_ref), _ws_rel(new_rel))   # G6: keeps the reference's form
    if new == txt:
        return False
    p.write_text(new, encoding="utf-8")
    sync_row(p)
    return True''', '''    new = _swap_ref(txt, _ws_rel(old_ref), _ws_rel(new_rel))   # G6: keeps the reference's form
    if new == txt:
        return False
    _apply_rewrite(p, txt, new, _ws_rel(old_ref), _ws_rel(new_rel))   # G6b: logged + reversible
    return True''')
# 5) promote_to_shared runs as ONE batch and records whether it created the shared file
sub(MW, '''def promote_to_shared(src_path, category=None, extra_consumers=None) -> dict:
    """MOVE''', '''def promote_to_shared(src_path, category=None, extra_consumers=None) -> dict:
    """One promotion = one logged, revertible batch (G6b). See _promote_to_shared."""
    with rewrite_batch(f"promote {_ws_rel(pathlib.Path(src_path).resolve().relative_to(ROOT)) if str(src_path).startswith(str(ROOT)) else src_path} to shared"):
        r = _promote_to_shared(src_path, category, extra_consumers)
        r["batch"] = _BATCH["id"]
        return r


def _promote_to_shared(src_path, category=None, extra_consumers=None) -> dict:
    """MOVE''')
sub(MW, '''    old_variants = {str(p.relative_to(ROOT)), old_ws, "workspace/" + old_ws}
    if not dest.exists():''', '''    old_variants = {str(p.relative_to(ROOT)), old_ws, "workspace/" + old_ws}
    created_shared = not dest.exists()
    if not dest.exists():''')
sub(MW, '''    record_move(old_ws, dest_rel)                # G6: so a reference written later can still be repointed''',
        '''    record_move(old_ws, dest_rel, created_shared)  # G6: so a reference written later can still be repointed''')
# ---------------- audit: one batch per heal action, removed copies logged, owner holds respected ----------------
sub(AU, '''    actions = []
    for iss in scan():
        t = iss["type"]''', '''    actions = []
    held = mw.held_paths()
    for iss in scan():
        t = iss["type"]
        _paths = [iss.get("path"), iss.get("target"), *(iss.get("paths") or [])]
        if t in ("duplicate", "foreign-ref", "dangling-ref") and any(x and x in held for x in _paths):
            rec = {**iss, "fix": "FLAGGED: held — the owner reverted the earlier automatic fix for these paths"}
            actions.append(rec); _log(rec)
            continue''')
sub(AU, '''        try:
            if t == "unindexed":''', '''        _bctx = mw.rewrite_batch(f"audit heal: {t} — {str(iss.get('reason') or iss.get('path') or '')[:160]}")
        _bctx.__enter__()
        try:
            if t == "unindexed":''')
sub(AU, '''        except Exception as e:
            fix = f"error: {e}"
        rec = {**iss, "fix": fix}''', '''        except Exception as e:
            fix = f"error: {e}"
        finally:
            _bid = mw._BATCH["id"]
            _bctx.__exit__(None, None, None)
        rec = {**iss, "fix": fix, "batch": _bid}''')
sub(AU, '''                    # G6: the removed copy's references follow it to shared (any owner), and the move is recorded
                    mw.record_move(x, res["promoted"])''', '''                    # G6: the removed copy's references follow it to shared (any owner), and the move is recorded
                    mw.record_removed_copy(x, res["promoted"])
                    mw.record_move(x, res["promoted"], created_shared=False)''')
print("G6b applied")
# ---- G6b part 2 (found by g6b_test): add_dependency's manifest.json write is also logged + revertible;
#      revert of a created shared file also removes its shared_capabilities row ----
if "--part2" in sys.argv:
    sub(MW, '''    existing = next((d for d in deps if d.get("source") == shared_rel), None)
    changed = False''', '''    existing = next((d for d in deps if d.get("source") == shared_rel), None)
    _prev = man.read_text(errors="replace") if man.exists() else None      # G6b: for the change log
    changed = False''')
    sub(MW, '''        man.write_text(json.dumps(deps, ensure_ascii=False, indent=2))
        sync_row(man)  # keep the manifest itself indexed''', '''        man.write_text(json.dumps(deps, ensure_ascii=False, indent=2))
        sync_row(man)  # keep the manifest itself indexed
        if _BATCH["id"]:   # G6b: an automatic action changed this manifest — log it so it can be reverted
            _log_change({"kind": "ref-rewrite", "file": str(man.relative_to(ROOT)),
                         "old": "(dependency manifest)", "new": f"+ dependency on {shared_rel}",
                         "before": _prev or "", "created": _prev is None,
                         "after_sha": _sha(man.read_text(errors="replace"))})''')
    sub(MW, '''        if _sha(f.read_text(errors="replace")) != d["after_sha"]:
            skipped.append(f"{d['file']}: edited after the rewrite — left as is"); continue
        f.write_text(d["before"], encoding="utf-8"); sync_row(f)''', '''        if _sha(f.read_text(errors="replace")) != d["after_sha"]:
            skipped.append(f"{d['file']}: edited after the rewrite — left as is"); continue
        if d.get("created"):
            f.unlink(); remove_file(f)
            done.append(f"removed {d['file']} (created by this action)"); continue
        f.write_text(d["before"], encoding="utf-8"); sync_row(f)''')
    sub(MW, '''                    conn.cursor().execute("DELETE FROM dependencies WHERE shared_capability_id=%s", (d["to"],))
                    conn.commit()''', '''                    _cu = conn.cursor()
                    _cu.execute("DELETE FROM dependencies WHERE shared_capability_id=%s", (d["to"],))
                    _cu.execute("DELETE FROM shared_capabilities WHERE id=%s", (d["to"],))
                    conn.commit()''')
    print("G6b part 2 applied")
# ---- G6b part 3: `release <batch>` lifts a hold (applied in-tree by an inline script; see git diff g6b-start..g6b-done) ----
