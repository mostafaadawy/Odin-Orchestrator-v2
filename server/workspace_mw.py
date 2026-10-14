"""
workspace_mw.py — the SINGLE creation door for workspace content (Phase 3).

Every create / update / delete of workspace files should go through here. It:
  1. VALIDATES placement against the canonical schema (WORKSPACE-SCHEMA.md) and BLOCKS violations,
  2. WRITES / REMOVES the file in the correct slot,
  3. keeps odin_core in LOCKSTEP (upserts / deletes the file + folder rows).

DB sync is best-effort: if odin_core is unreachable the file op still succeeds (the audit
reconciles later), so the running app never breaks on a DB hiccup.
"""
from __future__ import annotations
import pathlib, datetime, json, shutil, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
WS = ROOT / "workspace"

# ---- canonical schema (mirrors workspace/shared/directions/WORKSPACE-SCHEMA.md) ----
PROJECT_SUBFOLDERS = {"instructions", "restrictions", "plan", "connectors", "schedule",
                      "dependencies", "code", "features", "chat", "tests", "data", "docs",
                      "files", "deploy",
                      # per-project operational data written as FILES the DB points to (schedules,
                      # approvals, notifications, run timings…). Canonical so JSON-as-files never trips
                      # a schema violation — files inside the skeleton, never a parallel registry.
                      "jsons"}
AGENT_SUBFOLDERS = {"instructions", "restrictions", "dependencies", "code", "outputs"}
PROJECT_ROOT_FILES = {"index.json", "agents.json"}
AGENT_ROOT_FILES = {"index.json", "capability.md", "handoff.json"}


class Violation(Exception):
    pass


def _kind(name: str) -> str:
    e = pathlib.Path(name).suffix.lower()
    return {".json": "json", ".md": "md", ".sh": "shell", ".py": "py", ".html": "html",
            ".txt": "txt", ".pdf": "pdf", ".service": "unit", ".timer": "unit",
            ".key": "secret", ".cred": "secret", ".jsonl": "jsonl"}.get(
        e, "code" if e in (".ts", ".js", ".jsx", ".tsx", ".dart", ".css") else "other")


def _db():
    try:
        import psycopg2
        return psycopg2.connect(dbname="odin_core")
    except Exception:
        return None


def _area(owner_type: str) -> str:
    return owner_type + "s" if owner_type in ("project", "agent", "connector", "chat") else owner_type


def validate(owner_type: str, owner_id: str, subfolder: str, name=None):
    """Return (ok, reason). subfolder='' = an owner-root file. When `name` is given, an owner-root
    file that isn't one of the allowed root files is a violation (it belongs in a subfolder)."""
    if owner_type == "project":
        if not subfolder:
            if name is None or name in PROJECT_ROOT_FILES:
                return True, ""
            return False, f"'{name}' is not an allowed project-root file (belongs in a subfolder)"
        top = subfolder.split("/")[0]
        return (top in PROJECT_SUBFOLDERS), ("" if top in PROJECT_SUBFOLDERS
                                             else f"'{top}' is not a canonical project subfolder")
    if owner_type == "agent":
        if not subfolder:
            if name is None or name in AGENT_ROOT_FILES:
                return True, ""
            return False, f"'{name}' is not an allowed agent-root file (belongs in a subfolder)"
        top = subfolder.split("/")[0]
        return (top in AGENT_SUBFOLDERS), ("" if top in AGENT_SUBFOLDERS
                                           else f"'{top}' is not a canonical agent subfolder")
    if owner_type in ("connector", "chat", "shared", "workspace"):
        return True, ""
    return False, f"unknown owner_type '{owner_type}'"


def resolve_path(owner_type: str, owner_id: str, subfolder: str, name: str) -> pathlib.Path:
    base = WS / _area(owner_type) / owner_id if owner_type in ("project", "agent", "connector", "chat") \
        else (WS / "shared" / owner_id if owner_type == "shared" else WS / owner_id)
    return (base / subfolder / name) if subfolder else (base / name)


def _infer_owner(p: pathlib.Path):
    rel = p.relative_to(WS); parts = rel.parts; a = parts[0]
    # NOTE: >=3 means the 2nd part is an actual owner FOLDER (agents/<slug>/file), not a file that
    # sits directly under the area (agents/README.md) — the latter is an area-level file, not an owner.
    if a == "projects" and len(parts) >= 3 and parts[1] != "_shared":
        return ("project", parts[1], parts[2] if len(parts) >= 4 else "")
    if a == "agents" and len(parts) >= 3:
        return ("agent", parts[1], parts[2] if len(parts) >= 4 else "")
    if a == "connectors" and len(parts) >= 3:
        return ("connector", parts[1], parts[2] if len(parts) >= 4 else "")
    if a == "shared" and len(parts) >= 2:
        return ("shared", parts[1], parts[2] if len(parts) >= 4 else "")
    if a == "chats":
        stem = parts[1][:-5] if len(parts) == 2 and parts[1].endswith(".json") else "_pool"
        return ("chat", stem, "" if len(parts) == 2 else parts[1])
    return ("workspace", a, parts[1] if len(parts) >= 3 else "")


def route(owner_type, owner_id, requested_subfolder, name):
    """Decide the CANONICAL slot for a file. A valid requested subfolder is respected; an invalid
    one is REDIRECTED to the right slot inferred from the file (kind/name). Never blocks.
    Returns (subfolder, corrected:bool, note)."""
    root_files = PROJECT_ROOT_FILES if owner_type == "project" else (AGENT_ROOT_FILES if owner_type == "agent" else set())
    if name in root_files:
        return "", (bool(requested_subfolder)), ("moved to owner root" if requested_subfolder else "")
    allowed = PROJECT_SUBFOLDERS if owner_type == "project" else (AGENT_SUBFOLDERS if owner_type == "agent" else None)
    if allowed is None:  # connector/chat/shared/workspace: keep as requested
        return requested_subfolder, False, ""
    top = (requested_subfolder or "").split("/")[0]
    if top in allowed:
        return requested_subfolder, False, ""  # valid intent — respect it
    # --- redirect to the canonical slot ---
    k = _kind(name); low = name.lower()
    if owner_type == "agent":
        if "handoff" in low or "capability" in low or name == "index.json":
            sf = ""
        elif k in ("shell", "py", "code"):
            sf = "code"
        elif k == "md":
            sf = "instructions"
        else:
            sf = "outputs"
    else:  # project
        if any(t in low for t in ("test", "e2e", "spec")):
            sf = "tests"
        elif "deploy" in low:
            sf = "deploy"
        elif k in ("shell", "py", "code"):
            sf = "code"
        elif k in ("md", "pdf", "html"):
            sf = "docs"
        elif k in ("json", "jsonl"):
            sf = "data/approvals" if "approval" in low else "data/jsons"
        else:
            sf = "files"
    return sf, True, f"redirected '{top or 'root'}' -> '{sf}' (kind={k})"


def put_file(owner_type, owner_id, subfolder, name, content, description=None, actor=None) -> dict:
    """The door: ROUTE the file to its canonical slot (redirect if misplaced — never blocks),
    write it, sync odin_core, and record any correction so the flow keeps moving smoothly.

    OWNER-SCOPE GUARD (Phase-7 hardening): `actor` is who is performing the write. No project/agent may
    write into a DIFFERENT project/agent's folder — even into a structurally-valid subfolder. That looks
    legal on disk but is a real cross-owner violation. We PREVENT-and-CORRECT (never block): the write is
    redirected into the actor's OWN folder. If the actor genuinely needs a capability that lives in the
    target owner, that goes through request_capability()/promote_to_shared() — the only sanctioned
    cross-owner path — not a direct write."""
    scope_note = ""
    if actor and owner_type in ("project", "agent"):
        a_type, a_id = actor if isinstance(actor, (tuple, list)) else (owner_type, actor)
        if a_id and a_id != owner_id:
            scope_note = (f"cross-owner write prevented: {a_type}/{a_id} may not write into "
                          f"{owner_type}/{owner_id} — redirected to its own folder "
                          f"(use request_capability to reuse the other owner's work)")
            owner_type, owner_id = a_type, a_id
    sf, corrected, note = route(owner_type, owner_id, subfolder, name)
    if scope_note:
        corrected = True
        note = (note + "; " if note else "") + scope_note
    p = resolve_path(owner_type, owner_id, sf, name)
    _g8_new = not get_creator(p)[0]          # G8: no odin_core row yet = this write creates the file
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, (dict, list)):
        content = json.dumps(content, ensure_ascii=False, indent=2)
    p.write_text(content if isinstance(content, str) else str(content), encoding="utf-8")
    sync_row(p, owner_type, owner_id, sf, description)
    if _g8_new:
        _act = actor if isinstance(actor, (tuple, list)) else ((owner_type, actor) if actor else (owner_type, owner_id))
        set_creator(p, make_creator(project=_act[1] if _act[0] == "project" else None, via="middleware door",
                                    **({"owner_agent": _act[1]} if _act[0] == "agent" else {})))
    result = {"path": str(p), "corrected": corrected, "note": note, "owner_id": owner_id,
              "requested_subfolder": subfolder, "final_subfolder": sf, "scope_redirected": bool(scope_note)}
    if corrected:
        _log_correction(owner_type, owner_id, name, subfolder, sf, note)
    return result


def _log_correction(owner_type, owner_id, name, requested, final, note):
    """Append an audit trail of every redirect the middleware made (for the Phase-5 audit page)."""
    try:
        rec = {"ts": datetime.datetime.now().isoformat(), "owner": f"{owner_type}/{owner_id}",
               "file": name, "requested": requested, "corrected_to": final, "note": note}
        f = WS / "history" / "mw-corrections.jsonl"
        f.parent.mkdir(parents=True, exist_ok=True)
        with open(f, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        sync_row(f)  # keep the correction log itself indexed in odin_core (no parity gap)
    except Exception:
        pass


# ── G8: who CREATED a file (files.created_by — optional column, added by server/migrations/migrate_g8.sh) ──
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


def sync_row(path, owner_type=None, owner_id=None, subfolder=None, description=None) -> None:
    """Upsert the odin_core folder+file rows for a file that already exists on disk. Best-effort;
    only acts on paths under workspace/. Safe to call from store writes."""
    p = pathlib.Path(path)
    try:
        p.relative_to(WS)
    except Exception:
        return  # not a workspace path — nothing to sync
    conn = _db()
    if not conn:
        return
    try:
        if owner_type is None:
            owner_type, owner_id, subfolder = _infer_owner(p)
        rel = str(p.relative_to(ROOT))
        cu = conn.cursor()
        # ROBUST SINGLE-DOOR LOCKSTEP: ensure the owner row exists (enriched from its index.json) so a file
        # written for a brand-new project/agent by ANY path (app, middleware, audit) never dangles.
        if owner_type in ("project", "agent", "connector", "chat"):
            base = WS / _area(owner_type) / owner_id
            meta = {}
            ixp = base / "index.json"
            if ixp.exists():
                try:
                    meta = json.loads(ixp.read_text())
                except Exception:
                    meta = {}
            opath = str(base.relative_to(ROOT))
            if owner_type == "project":
                feats = json.dumps(meta.get("features")) if meta.get("features") is not None else None
                cu.execute("INSERT INTO projects(id,name,type,category,path,features) VALUES(%s,%s,%s,%s,%s,%s) "
                           "ON CONFLICT (id) DO UPDATE SET name=COALESCE(EXCLUDED.name,projects.name),"
                           "type=COALESCE(EXCLUDED.type,projects.type),category=COALESCE(EXCLUDED.category,projects.category),"
                           "features=COALESCE(EXCLUDED.features,projects.features)",
                           (owner_id, meta.get("name", owner_id), meta.get("type"), meta.get("category"), opath, feats))
            elif owner_type == "agent":
                cu.execute('INSERT INTO agents(id,name,role,type,"group",nature,description,path) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) '
                           'ON CONFLICT (id) DO UPDATE SET name=COALESCE(EXCLUDED.name,agents.name),'
                           'role=COALESCE(EXCLUDED.role,agents.role),type=COALESCE(EXCLUDED.type,agents.type),'
                           '"group"=COALESCE(EXCLUDED."group",agents."group"),'
                           'nature=COALESCE(EXCLUDED.nature,agents.nature),'
                           'description=COALESCE(EXCLUDED.description,agents.description)',
                           (owner_id, meta.get("name", owner_id), meta.get("role"), meta.get("type"), meta.get("group"), (meta.get("nature") or meta.get("type")), meta.get("description"), opath))
            elif owner_type == "connector":
                cu.execute("INSERT INTO connectors(id,name,path) VALUES(%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                           (owner_id, meta.get("name", owner_id), opath))
            elif owner_type == "chat":
                cu.execute("INSERT INTO chats(id,title,path) VALUES(%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                           (owner_id, meta.get("title", owner_id), opath))
        fid = None
        if subfolder:
            top = subfolder.split("/")[0]
            fpath = str((WS / _area(owner_type) / owner_id / top).relative_to(ROOT))
            cu.execute("INSERT INTO folders(owner_type,owner_id,name,path,description) VALUES(%s,%s,%s,%s,%s) "
                       "ON CONFLICT (owner_type,owner_id,name) DO UPDATE SET path=EXCLUDED.path RETURNING id",
                       (owner_type, owner_id, top, fpath, f"{top} of {owner_type} {owner_id}"))
            fid = cu.fetchone()[0]
        s = p.stat()
        _cb = None
        if has_created_by():   # G8: a re-sync must not lose who created the file
            cu.execute("SELECT created_by FROM files WHERE path=%s", (rel,))
            _r = cu.fetchone(); _cb = _r[0] if _r else None
        cu.execute("DELETE FROM files WHERE path=%s", (rel,))
        cu.execute("INSERT INTO files(folder_id,owner_type,owner_id,name,path,kind,description,size_bytes,created_at,modified_at) "
                   "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                   (fid, owner_type, owner_id, p.name, rel, _kind(p.name),
                    description or f"{_kind(p.name)} '{p.name}' — {owner_type} {owner_id}/{subfolder or 'root'}",
                    s.st_size, datetime.datetime.fromtimestamp(s.st_ctime),
                    datetime.datetime.fromtimestamp(s.st_mtime)))
        if _cb is not None:
            cu.execute("UPDATE files SET created_by=%s WHERE path=%s", (_cb, rel))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def remove_file(path) -> None:
    """Delete a file and its odin_core row together."""
    p = pathlib.Path(path)
    if p.exists():
        p.unlink()
    conn = _db()
    if not conn:
        return
    try:
        rel = str(p.relative_to(ROOT))
        cu = conn.cursor()
        cu.execute("DELETE FROM files WHERE path=%s", (rel,))
        conn.commit()
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


# ============================================================================================
# SANCTIONED CROSS-OWNER PROTOCOL (Phase-7): the ONLY legal way one owner's work reaches another.
# A project/agent can never write into another's folder. When a capability that lives inside one owner
# is needed by another, the MIDDLEWARE (not the project) promotes it to shared/ and repoints EVERY
# consumer (including the original owner) to read it from shared. So deleting any one owner can never
# break another — the shared capability lives in shared/ and survives deletion.
# ============================================================================================

def add_dependency(owner_type, owner_id, name, shared_rel, kind="code", mode="as-is", overlay=None) -> None:
    """Repoint an owner (project OR agent) at a shared capability: write its dependencies/manifest.json
    entry AND the odin_core dependency + shared_capability rows. Idempotent."""
    man = WS / _area(owner_type) / owner_id / "dependencies" / "manifest.json"
    try:
        deps = json.loads(man.read_text()) if man.exists() else []
    except Exception:
        deps = []
    existing = next((d for d in deps if d.get("source") == shared_rel), None)
    _prev = man.read_text(errors="replace") if man.exists() else None      # G6b: for the change log
    changed = False
    if existing is None:
        deps.append({"name": name, "source": shared_rel, "kind": kind, "mode": mode, "overlay": overlay})
        changed = True
    else:  # a later customize() may upgrade an as-is pointer to a custom overlay — reflect that
        if mode and mode != "as-is" and existing.get("mode") != mode:
            existing["mode"] = mode; changed = True
        if overlay and existing.get("overlay") != overlay:
            existing["overlay"] = overlay; changed = True
    if changed:
        man.parent.mkdir(parents=True, exist_ok=True)
        man.write_text(json.dumps(deps, ensure_ascii=False, indent=2))
        sync_row(man)  # keep the manifest itself indexed
        if _BATCH["id"]:   # G6b: an automatic action changed this manifest — log it so it can be reverted
            _log_change({"kind": "ref-rewrite", "file": str(man.relative_to(ROOT)),
                         "old": "(dependency manifest)", "new": f"+ dependency on {shared_rel}",
                         "before": _prev or "", "created": _prev is None,
                         "after_sha": _sha(man.read_text(errors="replace"))})
    conn = _db()
    if conn:
        try:
            cu = conn.cursor()
            cat = shared_rel.split("/")[1] if shared_rel.count("/") >= 2 else "utils"
            cu.execute("INSERT INTO shared_capabilities(id,category,name,path,description) VALUES(%s,%s,%s,%s,%s) "
                       "ON CONFLICT (id) DO NOTHING",
                       (shared_rel, cat, name, shared_rel, f"promoted shared capability: {name}"))
            # idempotent: only add the dependency row if this owner isn't already pointed at this capability
            cu.execute("INSERT INTO dependencies(owner_type,owner_id,name,source_path,shared_capability_id,kind,mode) "
                       "SELECT %s,%s,%s,%s,%s,%s,%s WHERE NOT EXISTS ("
                       "  SELECT 1 FROM dependencies WHERE owner_type=%s AND owner_id=%s AND shared_capability_id=%s)",
                       (owner_type, owner_id, name, shared_rel, shared_rel, kind, mode,
                        owner_type, owner_id, shared_rel))
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            conn.close()


# ── G6: moves are RECORDED and references FOLLOW them, so a promotion never leaves a dangling reference ──
MOVES_LOG = WS / "history" / "mw-corrections.jsonl"   # moves live in the existing middleware log (kind="move")
REF_EXT = {".py", ".sh", ".js", ".ts", ".dart", ".json", ".md"}
RECORD_DIRS = {"data", "history", "logs", "chat", "chats"}   # historical records: never rewritten, never audited

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
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
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
        if d.get("kind") in ("ref-rewrite", "move", "copy-removed", "revert", "hold", "release") and \
                (batch is None or d.get("batch") == batch or d.get("reverts") == batch):
            out.append(d)
    return out


def _reverted_batches() -> set:
    return {d.get("reverts") for d in change_log() if d.get("kind") == "revert"}


def held_paths() -> set:
    log = change_log()
    released = {d.get("batch") for d in log if d.get("kind") == "release"}
    s = set()
    for d in log:
        if d.get("kind") == "hold" and d.get("batch") not in released:
            s.update(d.get("paths") or [])
    return s


def release_hold(batch: str) -> dict:
    """Owner lifts the hold of a reverted action: the audit may fix those paths again."""
    if not any(d.get("kind") == "hold" and d.get("batch") == batch for d in change_log()):
        return {"ok": False, "error": f"no hold for batch {batch}"}
    _append_raw({"ts": datetime.datetime.now().isoformat(), "kind": "release", "batch": batch})
    return {"ok": True, "released": batch}


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
        if d.get("created"):
            f.unlink(); remove_file(f)
            done.append(f"removed {d['file']} (created by this action)"); continue
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
                    _cu = conn.cursor()
                    _cu.execute("DELETE FROM dependencies WHERE shared_capability_id=%s", (d["to"],))
                    _cu.execute("DELETE FROM shared_capabilities WHERE id=%s", (d["to"],))
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
            if not any(x.startswith(f"restored {d['path']} ") for x in done):
                skipped.append(f"{d['path']}: already exists")
            continue
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
        fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    sync_row(MOVES_LOG)


def _ws_rel(ref) -> str:
    s = str(ref).replace("\\", "/")
    return s[len("workspace/"):] if s.startswith("workspace/") else s


def _swap_ref(txt: str, old_ws: str, new_rel: str) -> str:
    """Replace a reference to old_ws (workspace-relative) with new_rel and KEEP its form: a reference
    written with the 'workspace/' prefix stays prefixed, so it still resolves from the repo root."""
    if not old_ws:
        return txt
    txt = txt.replace("workspace/" + old_ws, "workspace/" + new_rel)
    return re.sub(r"(?<![\w/\-])" + re.escape(old_ws), new_rel, txt)


def record_move(old_ref, new_rel, created_shared=True) -> None:
    _log_change({"kind": "move", "from": _ws_rel(old_ref), "to": _ws_rel(new_rel),
                 "created_shared": bool(created_shared)})


def moved_to(ref):
    """Where a file that used to be at `ref` lives NOW (following chains of moves), or None."""
    s = _ws_rel(ref)
    try:
        lines = MOVES_LOG.read_text(errors="replace").splitlines()
    except Exception:
        return None
    m = {}
    rev = _reverted_batches()
    for ln in lines:
        try:
            d = json.loads(ln)
            if d.get("kind") == "move" and d.get("batch") not in rev:
                m[d["from"]] = d["to"]
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
            _apply_rewrite(f, txt, new, old_ws, new_ws)          # G6b: logged + reversible
            if (ot, oid) not in owners:
                owners.append((ot, oid))
                if new_ws.startswith("shared/"):
                    add_dependency(ot, oid, pathlib.PurePath(new_ws).name, new_ws)
    return [f"{a}/{b}" for a, b in owners]


def _rewrite_owner_refs(owner_type, owner_id, old_variants, new_rel) -> int:
    """Rewrite an owner's OWN files that referenced a now-moved file by its old in-project path, so they
    read it from its new shared location. Returns how many files were rewritten."""
    base = WS / _area(owner_type) / owner_id
    if not base.exists():
        return 0
    n = 0
    for f in base.rglob("*"):
        if not (f.is_file() and f.suffix.lower() in {".py", ".sh", ".js", ".ts", ".dart", ".json", ".md"}):
            continue
        try:
            txt = f.read_text(errors="replace")
        except Exception:
            continue
        new = txt
        olds = sorted({_ws_rel(v) for v in old_variants if v})
        for v in olds:
            new = _swap_ref(new, v, new_rel)          # G6: keep the reference's form so it still resolves
        if new != txt:
            _apply_rewrite(f, txt, new, ", ".join(olds), _ws_rel(new_rel))   # G6b: logged + reversible
            n += 1
    return n


def promote_to_shared(src_path, category=None, extra_consumers=None) -> dict:
    """One promotion = one logged, revertible batch (G6b). See _promote_to_shared."""
    with rewrite_batch(f"promote {str(src_path).replace(str(ROOT) + '/', '')} to shared"):
        r = _promote_to_shared(src_path, category, extra_consumers)
        r["batch"] = _BATCH["id"]
        return r


class SharedNameConflict(ValueError):
    """F-36: shared/<category>/<name> already holds DIFFERENT content — never overwrite or drop a copy."""


# ── F-11 (owner's design, 2026-10-12): the 50% rule for SHARED vs SEPARATE ──
#   more than 50% common    -> one SHARED base + a per-project DELTA
#   more than 50% different -> SEPARATE scripts (not a duplicate; nothing is merged)
#   exactly 50%             -> owner review (never guessed)
# "Common" = matching meaningful lines (blank and comment-only lines ignored), Dice-style over both files.
SHARE_THRESHOLD = 0.5
_F11_COMMENT = re.compile(r"^\s*(#|//|--|;|/\*|\*/|\*\s)")


def _f11_lines(text) -> list:
    return [l.strip() for l in (text or "").splitlines() if l.strip() and not _F11_COMMENT.match(l)]


def common_ratio(a: str, b: str) -> float:
    import difflib
    la, lb = _f11_lines(a), _f11_lines(b)
    if not la and not lb:
        return 1.0
    sm = difflib.SequenceMatcher(None, la, lb, autojunk=False)
    m = sum(bl.size for bl in sm.get_matching_blocks())
    return 2.0 * m / (len(la) + len(lb))


def share_decision(a: str, b: str) -> dict:
    r = round(common_ratio(a, b), 4)
    d = "shared+delta" if r > SHARE_THRESHOLD else ("separate" if r < SHARE_THRESHOLD else "review")
    return {"common": r, "decision": d}


_TEST_NAME = re.compile(r"(^test_|_test\.|\.test\.|\.spec\.|(^|[_\-.])e2e([_\-.]|$)|^conftest\.py$)", re.I)
_TEST_BODY = re.compile(r"^\s*(import unittest|from unittest|import pytest|from pytest)|^\s*def test_\w+\(|\bdescribe\(|\bit\(['\"]", re.M)


def shared_category(p) -> str:
    """F-36: the CORRECT shared category for a file — decided by where it lives and what it is, never by a
    substring of its name ('latest_prices.py' or 'dup_test_r4.py' holding a helper is NOT a test)."""
    p = pathlib.Path(p)
    try:
        parts = p.resolve().relative_to(WS.resolve()).parts
    except Exception:
        parts = p.parts
    sub = parts[2] if len(parts) > 3 and parts[0] in ("projects", "agents") else ""
    try:
        body = p.read_text(errors="replace")[:20000]
    except Exception:
        body = ""
    if sub == "tests" or (_TEST_NAME.search(p.name) and (_TEST_BODY.search(body) or not body)) or _TEST_BODY.search(body):
        return "testing"
    if sub == "deploy" or re.search(r"(^|[_\-.])deploy([_\-.]|$)", p.name.lower()):
        return "infra"
    return "utils"


def oldest_registered(paths) -> str:
    """F-36: of several identical copies, the ORIGINAL = the oldest copy that odin_core has a row for (oldest
    file birth time; then the DB row's created_at; then path). If none is registered, the oldest on disk."""
    rows = {}
    conn = _db()
    if conn:
        try:
            cu = conn.cursor()
            cu.execute("SELECT path, created_at FROM files WHERE path = ANY(%s)", ([_relp(x) for x in paths],))
            rows = {a: b for a, b in cu.fetchall()}
        except Exception:
            rows = {}
        finally:
            conn.close()
    def key(x):
        q = ROOT / _relp(x)
        try:
            st = q.stat(); born = getattr(st, "st_birthtime", st.st_ctime)
        except Exception:
            born = float("inf")
        ca = rows.get(_relp(x))
        return (0 if _relp(x) in rows else 1, born, ca.timestamp() if ca else float("inf"), _relp(x))
    return sorted(paths, key=key)[0]


def _promote_to_shared(src_path, category=None, extra_consumers=None) -> dict:
    """MOVE a capability file out of a project/agent into shared/<category>/, then repoint the ORIGINAL
    owner + every extra consumer at it, and update odin_core. The single sanctioned cross-owner move —
    a project cannot do this itself; the middleware does. Returns a summary dict."""
    p = pathlib.Path(src_path)
    ot, oid, _sub = _infer_owner(p)
    name = p.name
    low = name.lower()
    cat = category or shared_category(p)          # F-36: by location + content, not a name substring
    dest_rel = f"shared/{cat}/{name}"
    dest = WS / "shared" / cat / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    # capture every form the old path may be referenced by, BEFORE moving it
    old_ws = str(p.relative_to(WS))
    old_variants = {str(p.relative_to(ROOT)), old_ws, "workspace/" + old_ws}
    created_shared = not dest.exists()
    if dest.exists() and p.exists() and dest.read_bytes() != p.read_bytes():
        raise SharedNameConflict(f"{dest_rel} already exists with DIFFERENT content — not promoted; owner review")
    _g8_cb = get_creator(p)[1]               # G8: keep the creator across the move
    if not dest.exists():
        shutil.move(str(p), str(dest))          # move (binary-safe) — removes the in-owner copy
    elif p.exists():
        p.unlink()                               # shared already holds it — just drop the duplicate copy
    remove_file(p)                               # drop the old odin_core file row
    sync_row(dest)                               # index the shared location
    if _g8_cb:
        set_creator(dest, _g8_cb)
    record_move(old_ws, dest_rel, created_shared)  # G6: so a reference written later can still be repointed
    consumers = [(ot, oid)] + [tuple(c) for c in (extra_consumers or [])]
    seen = set()
    repointed = []
    rewrites = 0
    for cot, cid in consumers:
        if not cid or (cot, cid) in seen:
            continue
        seen.add((cot, cid))
        add_dependency(cot, cid, name, dest_rel)
        # rewrite that owner's OWN internal references to the moved file (so nothing dangles)
        rewrites += _rewrite_owner_refs(cot, cid, old_variants, dest_rel)
        repointed.append(f"{cot}/{cid}")
    # G6: ANY other owner that referenced the old path follows it too (otherwise it dangles)
    for o in repoint_everywhere(old_ws, dest_rel):
        if o not in repointed:
            repointed.append(o)
    return {"promoted": dest_rel, "from": f"{ot}/{oid}", "repointed": repointed,
            "category": cat, "source_rewrites": rewrites}


def repoint_reference(referrer_path, old_ref, new_rel) -> bool:
    """Rewrite a referrer's SOURCE so it reads the capability from its new shared location instead of the
    other owner's private path. Replaces the old path string (with or without a 'workspace/' prefix) with
    new_rel, writes back, and re-syncs odin_core. Closes the loop after promote_to_shared so the foreign
    reference is actually gone, not just pointer-added."""
    p = pathlib.Path(referrer_path)
    if not p.is_file():
        return False
    try:
        txt = p.read_text(errors="replace")
    except Exception:
        return False
    new = _swap_ref(txt, _ws_rel(old_ref), _ws_rel(new_rel))   # G6: keeps the reference's form
    if new == txt:
        return False
    _apply_rewrite(p, txt, new, _ws_rel(old_ref), _ws_rel(new_rel))   # G6b: logged + reversible
    return True


def request_capability(actor_type, actor_id, need) -> dict:
    """'I need <need>.' The anti-duplication entrypoint the middleware/directions expose so an owner
    NEVER re-implements or copies another owner's file. Resolution order:
      1) already in shared/  -> add a pointer for the actor, done.
      2) inside ANOTHER owner -> promote it to shared/ + repoint the original AND the actor.
      3) nowhere             -> the actor should create it fresh in its OWN folder.
    Returns what happened so the caller (and the test) can assert no duplicate was created."""
    need_l = need.lower()
    shared_root = WS / "shared"
    if shared_root.exists():
        for sp in shared_root.rglob("*"):
            if sp.is_file() and sp.name not in (".gitkeep",) and need_l in sp.name.lower():
                rel = "shared/" + str(sp.relative_to(shared_root))
                add_dependency(actor_type, actor_id, sp.name, rel)
                return {"found": "shared", "source": rel, "action": "pointer-added", "duplicated": False}
    # search the capability-bearing folders of every OTHER owner (not just code/ — deploy/tests/files too)
    CAP_SUBS = ("code", "deploy", "tests", "files", "connectors", "schedule")
    for area, otype in (("projects", "project"), ("agents", "agent")):
        base = WS / area
        if not base.exists():
            continue
        for cp in base.glob("*/*/**/*"):
            if not (cp.is_file() and cp.name not in (".gitkeep",) and need_l in cp.name.lower()):
                continue
            rel_parts = cp.relative_to(base).parts  # (<owner>, <subfolder>, ...)
            if len(rel_parts) < 2 or rel_parts[1] not in CAP_SUBS:
                continue
            _ot, oid, _s = _infer_owner(cp)
            if oid == actor_id:
                continue  # it's the actor's own file — nothing to share
            res = promote_to_shared(cp, extra_consumers=[(actor_type, actor_id)])
            return {"found": f"{otype}/{oid}", **res, "action": "promoted+repointed", "duplicated": False}
    return {"found": None, "action": "create-new-in-own-folder", "duplicated": False}


def customize_shared(owner_type, owner_id, name, overlay_name, overlay_content, mode="override",
                     full_version: str = None) -> dict:
    """Reuse a shared capability but add a CUSTOM delta on top (the base+overlay model). The shared BASE is
    left untouched; the owner keeps only its small delta in its OWN code/, recorded in the manifest with
    mode=extend|subset|override + overlay=<file>. This is how a project customizes ~10% without forking."""
    src = None
    sroot = WS / "shared"
    if sroot.exists():
        for sp in sroot.rglob("*"):
            if sp.is_file() and sp.name != ".gitkeep" and (sp.name == name or name.lower() in sp.name.lower()):
                src = "shared/" + str(sp.relative_to(sroot))
                break
    if not src:
        return {"ok": False, "reason": f"shared base for '{name}' not found"}
    if full_version is not None:   # F-11: the owner's whole version decides delta vs separate script
        dec = share_decision((WS / src).read_text(errors="replace"), full_version)
        if dec["decision"] == "review":
            return {"ok": False, **dec, "reason": "exactly 50% common — owner review (F-11)"}
        if dec["decision"] == "separate":
            res = put_file(owner_type, owner_id, "code", overlay_name, full_version)   # its own script, no base
            return {"ok": True, **dec, "base": None, "separate": res["path"]}
        import delta as _dl   # F-11: a TRUE delta — only the differences + a pointer, proven to rebuild exactly
        _why = _dl.supported(overlay_name, full_version)
        if _why:
            return {"ok": False, **dec, "reason": f"{_why} — owner review (F-11); nothing written"}
        _base_text = (WS / src).read_text(encoding="utf-8")
        _d = _dl.make(_base_text, full_version, src)
        if _dl.apply(_base_text, _d) != full_version:
            return {"ok": False, **dec, "reason": "delta could not reproduce the version exactly — nothing written"}
        overlay_content = _dl.launcher(pathlib.Path(overlay_name).suffix.lower(), _d)
        mode = "delta"
    res = put_file(owner_type, owner_id, "code", overlay_name, overlay_content)  # overlay in the owner's own code/
    add_dependency(owner_type, owner_id, name, src, kind="code", mode=mode, overlay=overlay_name)
    out = {"ok": True, "base": src, "overlay": overlay_name, "mode": mode, "overlay_path": res["path"]}
    if full_version is not None:
        out.update(dec)
    return out


def provision_capability(owner_type, owner_id, need, overrides=None) -> dict:
    """THE SYSTEM does what a human otherwise does by hand: find the shared capability for <need>, then
    GENERATE this owner's own custom delta for it and register the dependency pointer.

    This is the anti-duplication protocol completing itself: directions says "it EXISTS in shared", and
    instead of a person hand-writing a config, the owner gets a delta generated from the shared
    capability's template + only the values that are genuinely project-specific (overrides).
    Returns what was found, what was generated, and where."""
    overrides = dict(overrides or {})
    found = request_capability(owner_type, owner_id, need)          # shared-first, promote if needed
    base = found.get("source") or found.get("promoted")
    if not base:
        return {"ok": False, "reason": f"no shared capability for '{need}'", **found}

    # a deploy-style capability needs a per-project delta file; generate it INTO the owner's own folder
    if "deploy" in need.lower():
        pid_dir = WS / _area(owner_type) / owner_id / "deploy"
        pid_dir.mkdir(parents=True, exist_ok=True)
        d = {"CFG_BACKEND_LOCAL": overrides.get("backend_local", ""),
             "CFG_BACKEND_VM": overrides.get("backend_vm", ""),
             "CFG_BACKEND_MIG": overrides.get("backend_mig", "none"),
             "CFG_BACKEND_BUILD": overrides.get("backend_build", "rm -rf dist && npm run build"),
             "CFG_BACKEND_PORT": str(overrides.get("backend_port", "")),
             "CFG_FRONTEND_LOCAL": overrides.get("frontend_local", ""),
             "CFG_FRONTEND_VM": overrides.get("frontend_vm", ""),
             "CFG_FRONTEND_MIG": overrides.get("frontend_mig", "none"),
             "CFG_FRONTEND_BUILD": overrides.get("frontend_build", "rm -rf .next && npm run build"),
             "CFG_FRONTEND_PORT": str(overrides.get("frontend_port", "")),
             "CFG_RESTART_SERVICES": overrides.get("restart_services", ""),
             "CFG_REBOOT": str(overrides.get("reboot", 0))}
        lines = [f"# GENERATED BY THE SYSTEM for {owner_type}/{owner_id} — delta over shared capability: {base}",
                 f"# Only project-specific values live here; the engine itself stays shared and generic."]
        lines += [f'{k}="{v}"' for k, v in d.items() if v != ""]
        name = f"{owner_id}.config.sh"
        res = put_file(owner_type, owner_id, "deploy", name, "\n".join(lines) + "\n",
                       description=f"generated deploy delta over {base}")
        add_dependency(owner_type, owner_id, "deploy-engine", base, kind="code",
                       mode="extend", overlay=f"deploy/{name}")
        return {"ok": True, "need": need, "shared_base": base, "delta": res["path"],
                "generated_by": "system", **{k: found.get(k) for k in ("found", "action")}}

    add_dependency(owner_type, owner_id, need, base, kind="code", mode="as-is")
    return {"ok": True, "need": need, "shared_base": base, "delta": None, "generated_by": "system",
            **{k: found.get(k) for k in ("found", "action")}}


def resolve_capability(owner_type, owner_id, name) -> dict:
    """Resolve the EFFECTIVE capability a consumer sees: the shared BASE plus this owner's custom OVERLAY.
    Reads the owner's dependencies/manifest.json. Proves the pointer works and any custom-over-shared is
    wired correctly. Returns base/overlay paths + existence so callers can load and combine them."""
    man = WS / _area(owner_type) / owner_id / "dependencies" / "manifest.json"
    entry = None
    if man.is_file():
        try:
            for d in json.loads(man.read_text()):
                if d.get("name") == name or pathlib.Path(d.get("source", "")).name == name \
                        or (d.get("overlay") and pathlib.Path(d["overlay"]).name == name):
                    entry = d
                    break
        except Exception:
            entry = None
    if not entry:
        return {"resolved": False, "reason": "no manifest entry"}
    base_rel = entry.get("source", "")
    base_path = WS / base_rel if base_rel.startswith("shared/") else None
    overlay = entry.get("overlay")
    overlay_path = None
    if overlay:   # FIX #1 (2026-10-11): manifests store overlays relative to the owner folder (deploy/x.config.sh,
        _own = WS / _area(owner_type) / owner_id          # tests/); keep the legacy code/<overlay> form as fallback.
        overlay_path = _own / overlay if (_own / overlay).exists() else _own / "code" / overlay
    base_ok = bool(base_path and base_path.exists())
    overlay_ok = bool(overlay_path and overlay_path.exists())
    return {"resolved": base_ok and (overlay is None or overlay_ok),
            "base": base_rel, "base_exists": base_ok,
            "mode": entry.get("mode", "as-is"), "overlay": overlay, "overlay_exists": overlay_ok,
            "base_path": str(base_path) if base_path else None,
            "overlay_path": str(overlay_path) if overlay_path else None}


# ---- THE DATABASE IS THE ONLY REGISTRY (parallel-source guard) ----------------------------------
# odin_core is the single source of truth for projects / agents / connectors. A GLOBAL json registry
# that still lists those entities is a PARALLEL source of truth — the exact drift that let ghost
# projects hide behind a clean DB while the UI read the file. The MIDDLEWARE owns this rule; the audit
# calls scan_registry_violations() so both layers consider it a violation.
_CORE_REGISTRY = WS / "shared" / "core-registry"
REGISTRY_GUARD = (("projects.json", "projects", "projects"),
                  ("connectors.json", "connectors", "connectors"),
                  ("company_agents.json", "agents", "agents"))


def scan_registry_violations():
    """[(path, reason, {orphans,table,key})] for any global json registry that duplicates a DB table.
    The DB is authoritative; any such file is a violation (the audit heals the migrated ones by deleting
    them, and flags the rest as pending until their reader is moved to the DB)."""
    out = []
    conn = _db()
    if not conn:
        return out
    try:
        cu = conn.cursor()
        for fname, table, key in REGISTRY_GUARD:
            f = _CORE_REGISTRY / fname
            if not f.exists():
                continue
            try:
                doc = json.loads(f.read_text())
                rows = doc.get(key, []) if isinstance(doc, dict) else doc
                file_ids = {r.get("id") for r in rows if isinstance(r, dict) and r.get("id")}
            except Exception:
                file_ids = set()
            cu.execute("SELECT id FROM " + table)
            db_ids = {r[0] for r in cu.fetchall()}
            orphans = sorted(x for x in (file_ids - db_ids) if x)
            reason = (f"{fname} is a parallel source of truth — odin_core owns '{table}'. "
                      + (f"{len(orphans)} id(s) not in the DB." if orphans else "duplicates the DB registry."))
            out.append((str(f.relative_to(ROOT)), reason, {"orphans": orphans, "table": table, "key": key}))
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return out


def scan_violations():
    """Return [(path, reason)] for any workspace file whose placement violates the schema.
    Used by the Phase-5 audit; also a good self-check for the middleware."""
    bad = []
    for p in WS.rglob("*"):
        if not p.is_file() or p.name in (".gitkeep", ".DS_Store") or "__pycache__" in p.parts:
            continue
        if p.relative_to(WS).parts[:1] == ("logs",):
            continue
        ot, oid, sub = _infer_owner(p)
        ok, reason = validate(ot, oid, sub, p.name)
        if not ok:
            bad.append((str(p.relative_to(ROOT)), reason))
    return bad


# ---- full canonical skeletons (used to stamp new owners AND to sync empty folders) ----
PROJECT_SKELETON = ["instructions", "restrictions", "plan", "connectors", "schedule", "dependencies",
                    "code", "features", "features/voice", "chat", "tests", "data", "data/jsons",
                    "data/approvals", "docs", "files", "deploy"]
AGENT_SKELETON = ["instructions", "restrictions", "dependencies", "code", "outputs"]


def sync_folders(owner_type, owner_id) -> None:
    """Ensure odin_core has a folder row for EVERY subfolder that exists on disk for this owner,
    INCLUDING empty canonical ones (so the DB reflects the full skeleton, not just folders with files)."""
    base = WS / _area(owner_type) / owner_id
    if not base.exists():
        return
    conn = _db()
    if not conn:
        return
    try:
        cu = conn.cursor()
        for sub in base.iterdir():
            if sub.is_dir() and sub.name != "__pycache__":
                cu.execute("INSERT INTO folders(owner_type,owner_id,name,path,description) VALUES(%s,%s,%s,%s,%s) "
                           "ON CONFLICT (owner_type,owner_id,name) DO NOTHING",
                           (owner_type, owner_id, sub.name, str(sub.relative_to(ROOT)),
                            f"{sub.name} of {owner_type} {owner_id}"))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def create_owner(owner_type, owner_id, index=None) -> str:
    """The single door for a NEW project/agent: stamp its full canonical skeleton (folders + .gitkeep),
    write index.json, and register it + all its folders in odin_core. Never partial — always the full shape."""
    import json as _json
    skel = PROJECT_SKELETON if owner_type == "project" else (AGENT_SKELETON if owner_type == "agent" else [])
    base = WS / _area(owner_type) / owner_id
    base.mkdir(parents=True, exist_ok=True)
    for sub in skel:
        d = base / sub
        d.mkdir(parents=True, exist_ok=True)
        if not any(d.iterdir()):
            (d / ".gitkeep").write_text("")
    idx = index or {"id": owner_id, "name": owner_id}
    (base / "index.json").write_text(_json.dumps(idx, ensure_ascii=False, indent=2))
    # the OTHER mandatory root files, so a new owner is FULLY conformant (not just index.json)
    if owner_type == "project":
        aj = base / "agents.json"
        if not aj.exists():
            aj.write_text(_json.dumps({"agents": []}, ensure_ascii=False, indent=2))
    elif owner_type == "agent":
        cap = base / "capability.md"
        if not cap.exists():
            cap.write_text(f"# {idx.get('name', owner_id)}\n\n{idx.get('description') or 'capability — to define'}\n")
        hf = base / "handoff.json"
        if not hf.exists():
            hf.write_text(_json.dumps({"runs_after": [], "runs_before": [], "collaborates_with": []},
                                      ensure_ascii=False, indent=2))
    conn = _db()
    if conn:
        try:
            cu = conn.cursor()
            if owner_type == "project":
                cu.execute("INSERT INTO projects(id,name,type,category,path,description) VALUES(%s,%s,%s,%s,%s,%s) "
                           "ON CONFLICT (id) DO NOTHING",
                           (owner_id, idx.get("name", owner_id), idx.get("type"), idx.get("category"),
                            str(base.relative_to(ROOT)), idx.get("description")))
            elif owner_type == "agent":
                cu.execute('INSERT INTO agents(id,name,role,type,"group",nature,path,description) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) '
                           'ON CONFLICT (id) DO UPDATE SET name=COALESCE(EXCLUDED.name,agents.name),'
                           'role=COALESCE(EXCLUDED.role,agents.role),type=COALESCE(EXCLUDED.type,agents.type),'
                           '"group"=COALESCE(EXCLUDED."group",agents."group"),'
                           'nature=COALESCE(EXCLUDED.nature,agents.nature),'
                           'description=COALESCE(EXCLUDED.description,agents.description)',
                           (owner_id, idx.get("name", owner_id), idx.get("role"), idx.get("type"),
                            idx.get("group"), (idx.get("nature") or idx.get("type")), str(base.relative_to(ROOT)), idx.get("description")))
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
        finally:
            try:
                conn.close()
            except Exception:
                pass
    sync_folders(owner_type, owner_id)
    for f in base.iterdir():
        if f.is_file():
            sync_row(f)   # index ALL root files (index.json, agents.json / capability.md, handoff.json)
    return str(base)


def delete_owner(owner_type, owner_id) -> None:
    """Clean deletion: remove the owner's folder + all its odin_core rows (its OWN content only —
    shared capabilities it promoted are left intact). Used by Phase-7 create/delete tests."""
    import shutil
    base = WS / _area(owner_type) / owner_id
    if base.exists():
        shutil.rmtree(base, ignore_errors=True)
    # FIX (owner's prompt-journey test): a project's RUNS create conversation scopes
    # (chats/scopes/project__<pid>/… and member__<pid>__*/…) whose files are indexed as owner_type 'chat'.
    # Deleting only the owner's rows left those registry rows (and folders) behind. The project's scopes are
    # part of the project, so the single door removes them too — folders AND their rows.
    scope_like = []
    if owner_type == "project":
        import glob as _glob
        sroot = WS / "chats" / "scopes"
        for d in [sroot / f"project__{owner_id}"] + [pathlib.Path(x) for x in _glob.glob(str(sroot / f"member__{owner_id}__*"))]:
            shutil.rmtree(d, ignore_errors=True)
        _esc = owner_id.replace("\\", "\\\\").replace("_", "\\_").replace("%", "\\%")
        scope_like = [f"workspace/chats/scopes/project\\_\\_{_esc}/%", f"workspace/chats/scopes/member\\_\\_{_esc}\\_\\_%"]
    conn = _db()
    if not conn:
        return
    try:
        cu = conn.cursor()
        cu.execute("DELETE FROM files WHERE owner_type=%s AND owner_id=%s", (owner_type, owner_id))
        cu.execute("DELETE FROM folders WHERE owner_type=%s AND owner_id=%s", (owner_type, owner_id))
        cu.execute("DELETE FROM dependencies WHERE owner_type=%s AND owner_id=%s", (owner_type, owner_id))
        for _lk in scope_like:
            cu.execute("DELETE FROM files WHERE path LIKE %s ESCAPE '\\'", (_lk,))
            cu.execute("DELETE FROM folders WHERE path LIKE %s ESCAPE '\\'", (_lk,))
        # link/relation rows MUST go before the owner row (FK-safe) so deletion is clean and leaves no orphans
        if owner_type == "project":
            cu.execute("DELETE FROM project_agents WHERE project_id=%s", (owner_id,))
            cu.execute("DELETE FROM project_connectors WHERE project_id=%s", (owner_id,))
            cu.execute("DELETE FROM project_chats WHERE project_id=%s", (owner_id,))
            cu.execute("DELETE FROM projects WHERE id=%s", (owner_id,))
        elif owner_type == "agent":
            cu.execute("DELETE FROM project_agents WHERE agent_id=%s", (owner_id,))
            cu.execute("DELETE FROM agents WHERE id=%s", (owner_id,))
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


# =============================================================================================
# SCOPE-AWARE ANSWERING — a SYSTEM (middleware) capability, used by BOTH the owner path
# (server/api_v2._scoped_gen, internal /scope/stream) AND the external path (server/anchor.process).
# It NEVER cuts knowledge or consistency: every agent still SEES all data (shared pool, directions).
# It only SHAPES the answer so a question is interpreted within the current project's scope first, asks
# to clarify on ambiguity, and — only for EXTERNAL third-party callers — gates genuinely out-of-scope
# information behind the owner's approval. For the OWNER (desktop/web/mobile) nothing is ever blocked.
# Keeping it here (not inline in a project) makes it project-INDEPENDENT: every project inherits it.
# =============================================================================================
def scope_answer_guard(project_name: str, external: bool) -> str:
    """Return the scope-shaping instruction to prepend to an answer prompt for a project/agent scope.
    external=False -> OWNER (never blocked); external=True -> third-party request (approval to go out of scope)."""
    pn = project_name or "this project"
    if external:
        return (
            f"SCOPE (external request to '{pn}') — reason, do not pattern-match. 1) Search THIS project's own "
            f"scope FIRST and answer the closest correct in-scope value (a request is one-shot — do not block). "
            f"2) Never reveal another project's / the company's / the system's data (leak). 3) Ask a narrow "
            f"'X or Y?' (both in scope) only if they say that was not what they meant. 4) Only if they INSIST on "
            f"something confirmed OUTSIDE this project: do not reveal it — say it needs the owner's approval and "
            f"raise it (request-level). Be concise; real data only; never invent; never leak.")
    return (
        f"SCOPE (owner of '{pn}') — reason about meaning, do not pattern-match. You keep ALL knowledge and "
        f"access; scope only shapes the answer. 1) Search THIS project's own scope FIRST and dig — the answer "
        f"is usually yours. 2) Answer from your OWN data; never substitute another project's / the company's / "
        f"the system's value (that is a leak and a hallucination). 3) Never falsely block, refuse, or say 'I "
        f"need more info' when the answer is reachable in scope — that is the main failure. 4) Ask one narrow "
        f"'do you mean X or Y?' only on genuine in-scope ambiguity. 5) If truly outside '{pn}': you are the "
        f"owner, so NEVER refuse or gate on scope — actually GO FIND it from the global / other-projects / system "
        f"data you can access and give it; only if it is genuinely not tracked anywhere do you say so plainly. "
        f"'Outside this project' is never a reason to withhold from the owner.")


# =============================================================================================
# read_execute_guard — SYSTEM-WIDE "a read is not a change" capability (project-INDEPENDENT).
#   THE bug this fixes: an informational question ("how many profiles?", "what's the VM status?")
#   was being answered with a PROPOSAL to run the read, instead of the agent just RUNNING the read
#   and stating the live value. A GET/list/show/status is never a state change — it must EXECUTE.
#   This instruction is appended (instead of PROPOSE_RULES) whenever the message is a READ, for
#   BOTH the owner path and the external path. It is generic: it names no connector and no project;
#   the agent picks whatever read-only source the question needs (files, the project's connected
#   service via its API GET/list, a status command) and answers from the real value it fetched.
# =============================================================================================
def read_execute_guard(connectors: list | None = None) -> str:
    """Instruction that makes the agent EXECUTE read-only queries and answer with the live value,
    never propose a read. `connectors` (optional) = names of this project's connected services so the
    agent knows what it may read live; it stays generic (no hardcoded per-connector logic)."""
    hint = ""
    if connectors:
        names = ", ".join(sorted({str(c) for c in connectors if c}))
        if names:
            hint = (f" This project is connected to: {names}. To answer a data question you MAY read "
                    f"live from these services (their API GET/list/show endpoints, read-only) and from "
                    f"the project's files.")
    return (
        "\n\nREAD (informational): a read is NOT a change — EXECUTE it (read files, call the connected "
        "service's GET/list/show, run a status/list command) and state the REAL live value." + hint +
        " Never propose a read, ask the owner to approve one, or say you are blocked; use read-only command "
        "forms, and if one is blocked as state-changing, silently switch to its read-only equivalent. Find the "
        "value in THIS project's own scope — never answer with another scope's similar value. Offer any "
        "follow-up as a plain offer, not an approval request. Only a real WRITE is proposed. "
        "If a read is blocked by a permission / read-only error, NEVER say you 'can\'t', NEVER propose a change, "
        "NEVER ask approval — use the read-only form, ACTUALLY attempt the connected service's live read-only query for the asked metric BEFORE concluding the data isn't there — don't infer 'not pulled' from local files alone. If the data is genuinely not connected, answer plainly what IS available (what the scope does cover) and STOP — do NOT end with a 'want me to...?' question or a next-read proposal; a plain answer never needs an approval question appended. An ambiguous question is answered OR one narrow clarify — never proposed, never approval-gated. Be decisive: after a reasonable read give the concrete answer or the best available figure with a one-line caveat — never investigate open-endedly, never stop at 'I'll look into it' without landing an answer.")


# ============================ AGENT SCOPE (delta) ============================
# A borrowed helper agent runs under a per-(project,agent) DELTA: a SCOPED credential
# REFERENCE (pointer into the seeded runtime_settings) so this project never uses/mutates
# the agent's default key. Delta-first -> else default; the agent reports credential_source.
# Non-blocking for reads; a write must be proposed, never executed.
def _ensure_agent_scope():
    c = _db()
    if not c:
        return
    try:
        cu = c.cursor()
        cu.execute('CREATE TABLE IF NOT EXISTS agent_scope('
                   'project_id TEXT NOT NULL, agent TEXT NOT NULL, service TEXT, '
                   'credential_ref TEXT, read_only BOOLEAN DEFAULT TRUE, '
                   'PRIMARY KEY(project_id, agent))')
        c.commit()
    finally:
        c.close()

def set_agent_scope(project_id, agent, service, credential_ref, read_only=True):
    _ensure_agent_scope()
    c = _db()
    if not c:
        return False
    try:
        cu = c.cursor()
        cu.execute('INSERT INTO agent_scope(project_id,agent,service,credential_ref,read_only) '
                   'VALUES(%s,%s,%s,%s,%s) ON CONFLICT (project_id,agent) DO UPDATE SET '
                   'service=EXCLUDED.service, credential_ref=EXCLUDED.credential_ref, '
                   'read_only=EXCLUDED.read_only',
                   (project_id, agent, service, credential_ref, bool(read_only)))
        c.commit()
        return True
    finally:
        c.close()

def agent_credential_ref(project_id, agent):
    _ensure_agent_scope()
    c = _db()
    if not c:
        return None
    try:
        cu = c.cursor()
        cu.execute('SELECT service,credential_ref,read_only FROM agent_scope '
                   'WHERE project_id=%s AND agent=%s', (project_id, agent))
        r = cu.fetchone()
        if not r:
            return None
        return {"service": r[0], "credential_ref": r[1], "read_only": bool(r[2])}
    finally:
        c.close()

def list_agent_scope(project_id):
    _ensure_agent_scope()
    c = _db()
    if not c:
        return []
    try:
        cu = c.cursor()
        cu.execute('SELECT agent,service,credential_ref,read_only FROM agent_scope WHERE project_id=%s', (project_id,))
        return [{"agent": a, "service": s, "credential_ref": cr, "read_only": bool(ro)} for (a, s, cr, ro) in cu.fetchall()]
    finally:
        c.close()

# ── G9: the per-project CREDENTIAL CHOICE is recorded (reference name only — never the secret value) ──
_CRED_SERVICES = {"klaviyo": "klaviyo", "veeqo": "veeqo", "hubspot": "hubspot", "easypost": "easypost",
                  "stripe": "stripe", "shopify": "shopify", "google analytics": "analytics", "ga4": "analytics"}
_CRED_REF = re.compile(r"\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*_(?:KEY|TOKEN|SECRET)(?:_[A-Z0-9]+)*)\b")


def credential_choice_from_text(text) -> list:
    """[(service, credential_ref)] named in an owner text, e.g. 'its key will be stored as KLAVIYO_KEY_BRAND2'.
    A reference is paired with the service named inside it, else with the only service the text mentions."""
    t = text or ""
    refs = list(dict.fromkeys(_CRED_REF.findall(t)))
    if not refs:
        return []
    low = t.lower()
    svcs = list(dict.fromkeys(v for k, v in _CRED_SERVICES.items() if re.search(r"\b" + re.escape(k) + r"\b", low)))
    out = []
    for ref in refs:
        own = [v for k, v in _CRED_SERVICES.items() if k.replace(" ", "_").upper() in ref or v.upper() in ref]
        svc = own[0] if own else (svcs[0] if len(svcs) == 1 else None)
        if svc:
            out.append((svc, ref))
    return out


def record_credential_choice(project_id, service, credential_ref, source="intake") -> dict:
    """Record WHICH credential this project uses for <service>: an agent_scope row for every member whose role
    uses that service, plus connectors/<service>.credential-ref.json in the project's OWN folder (reference
    name only). Nothing is ever written to shared/oth/.cred."""
    agents = []
    try:
        import agents_registry as _ar, projects as _pj
        for a in _ar.list_agents(project_id):
            d = _pj.member_def(a.get("name", "")) or {}
            if service in (d.get("deps") or []):
                agents.append(a["name"])
    except Exception:
        pass
    for ag in agents:
        set_agent_scope(project_id, ag, service, credential_ref, read_only=True)
    ref_doc = {"service": service, "credential_ref": credential_ref, "agents": agents, "source": source,
               "recorded": datetime.datetime.now().isoformat(timespec="seconds"),
               "note": "Reference NAME only. The secret value lives in the runtime settings - never in this file, "
                       "never in shared/oth/.cred. The project's agents must use this credential, not the default."}
    r = put_file("project", project_id, "connectors", f"{service}.credential-ref.json", ref_doc,
                 actor=("project", project_id))
    return {"service": service, "credential_ref": credential_ref, "agents": agents, "file": r.get("path")}


def agent_scope_guard(project_id, agent):
    """Prepend to a BORROWED-agent (helper) call. Delta-first -> else default; report credential_source;
    read-only in helper context; never blocks."""
    b = agent_credential_ref(project_id, agent)
    if b and b.get("credential_ref"):
        return ("\n\nAGENT SCOPE (you are a HELPER borrowed by project '" + str(project_id) + "'): this project sets a "
                "scoped DELTA for you. Use the SCOPED credential referenced by '" + str(b.get("credential_ref")) +
                "' (service " + str(b.get("service")) + "), resolved at runtime from the seeded runtime_settings — do NOT use "
                "your default key. State credential_source=delta. You are READ-ONLY here (GET/list/show, read logs); a write "
                "must be PROPOSED, never executed. This never blocks: if the scoped credential cannot be resolved, say so "
                "plainly and report what IS available (credential_source=unresolved).")
    return ("\n\nAGENT SCOPE: no delta is set for you in project '" + str(project_id) + "' — use your DEFAULT credential "
            "(as in your own project) and state credential_source=default. Read-only in a helper context; a write must be "
            "PROPOSED, never executed.")


# ==================== EXTERNAL SINGLE-FILE REPORT RULE ======================
# A project working on EXTERNAL read-only folders may write EXACTLY ONE file: its diagnosis report
# at the registered external path. Any other external write is a violation. The DB stores the ref.
def set_external_report_ref(project_id, path):
    _ensure_external_report()
    c = _db()
    if not c:
        return False
    try:
        cu = c.cursor()
        cu.execute('INSERT INTO external_report(project_id,path) VALUES(%s,%s) '
                   'ON CONFLICT (project_id) DO UPDATE SET path=EXCLUDED.path', (project_id, path))
        c.commit()
        return True
    finally:
        c.close()

def _ensure_external_report():
    c = _db()
    if not c:
        return
    try:
        cu = c.cursor()
        cu.execute('CREATE TABLE IF NOT EXISTS external_report('
                   'project_id TEXT PRIMARY KEY, path TEXT NOT NULL)')
        c.commit()
    finally:
        c.close()

def external_report_ref(project_id):
    _ensure_external_report()
    c = _db()
    if not c:
        return None
    try:
        cu = c.cursor()
        cu.execute('SELECT path FROM external_report WHERE project_id=%s', (project_id,))
        r = cu.fetchone()
        return r[0] if r else None
    finally:
        c.close()

def write_external_report(project_id, path, content):
    """Enforce the single-file rule: the ONLY external path this project may write is its registered
    report path. Any other path is refused as a violation. Returns (ok, msg)."""
    import os
    allowed = external_report_ref(project_id)
    if not allowed:
        return (False, "no external_report registered for this project")
    if os.path.abspath(path) != os.path.abspath(allowed):
        return (False, "VIOLATION: external write to %s not allowed; only %s" % (path, allowed))
    os.makedirs(os.path.dirname(allowed), exist_ok=True)
    with open(allowed, "w", encoding="utf-8") as fh:
        fh.write(content)
    return (True, allowed)


# ============= READ-ONLY VM DIAGNOSIS CAPABILITY (make agents self-sufficient) =============
# Injected for members of a DIAGNOSIS project (one that has a registered external report). Tells the
# agent HOW to execute read-only VM checks itself within the read-only hook — no hook weakening.
def vm_diagnosis_guard():
    return (
        "\n\nREAD-ONLY VM DIAGNOSIS (execute yourself — do NOT merely propose reads): you MAY run read-only "
        "checks on the production VM directly. Form: sshpass -p \"$(grep azvmcred workspace/shared/oth/.cred | "
        "sed -E 's/.*azvmcred[[:space:]]*[:=][[:space:]]*//' | tr -d '\\r')\" ssh -o StrictHostKeyChecking=no -o "
        "ConnectTimeout=15 mostafa@52.180.154.225 '<READ-ONLY remote command>'. Allowed remote: psql SELECT, tail, "
        "grep, ls, cat, head, wc, pgrep, 'systemctl status', curl -s (GET only), awk, date. "
        "CRITICAL: NEVER use '>' or '>>' file redirects (the read-only hook blocks ALL file writes, even to /tmp) — "
        "PIPE output directly instead (| head, | python3 -c ...). The STAGING (RBO-Staging/b) DB url is in "
        "/home/mostafa/RBO-Staging/b/.env (DATABASE_URL). Your scoped service key (delta) is the field named by your "
        "credential_ref inside AppSetting row key='RUNTIME_OPERATIONAL_SETTINGS'. These reads EXECUTE now; only a real "
        "WRITE (INSERT/UPDATE/DELETE/rm/mv/restart/rsync-without-dry-run) is proposed for owner approval.")


# ================= TUTORIAL-FIRST GUARD (learn from provider API mistakes) =================
# For a diagnosis project's agents: read the shared provider tutorial BEFORE reasoning, so shipped/
# status decisions come from the DOCUMENTED request/response, never a guessed field. Generic: it maps
# the project's agent-scope services to shared/tutorials/<service>_*.md.
_TUTORIAL_MAP = {"veeqo": "workspace/shared/tutorials/veeqo_fulfillment_api.md"}
def tutorial_guard(project_id):
    svcs = set((b.get("service") or "").lower() for b in list_agent_scope(project_id))
    try:
        import projects as _pj
        _memmap = {"fulfillment": "veeqo", "email": "klaviyo", "hubspot": "hubspot"}
        for m in ((_pj.get_project(project_id) or {}).get("members") or []):
            mn = (m.get("name") if isinstance(m, dict) else m) or ""
            if mn.lower() in _memmap:
                svcs.add(_memmap[mn.lower()])
    except Exception:
        pass
    svcs = sorted(x for x in svcs if x)
    tuts = [ _TUTORIAL_MAP[s] for s in svcs if s in _TUTORIAL_MAP ]
    if not tuts:
        return ""
    lst = "; ".join(tuts)
    return ("\n\nTUTORIAL FIRST (mandatory): BEFORE deciding any provider state, READ the shared tutorial(s) for "
            "this project's services and follow their DOCUMENTED request/response — do NOT guess field names from "
            "intuition/logic. Tutorials: " + lst + " (and workspace/shared/tutorials/INDEX.md). Specifically for "
            "Veeqo 'shipped': decide from allocation.dispatch_date OR shipment.shipped_by_id OR a created tracking "
            "label — NEVER from shipped_at / status enums alone (Veeqo leaves those null in the manual-ship flow). "
            "If a documented field is null, check the alternate documented signals before concluding. If the live "
            "response no longer matches the tutorial, update the tutorial from the live response first.")
