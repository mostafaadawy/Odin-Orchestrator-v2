"""
workspace_mw.py — the SINGLE creation door for workspace content (Phase 3).

Every create / update / delete of workspace files should go through here. It:
  1. VALIDATES placement against the canonical schema (WORKSPACE-SCHEMA.md) and BLOCKS violations,
  2. WRITES / REMOVES the file in the correct slot,
  3. keeps odin_core_iso in LOCKSTEP (upserts / deletes the file + folder rows).

DB sync is best-effort: if odin_core_iso is unreachable the file op still succeeds (the audit
reconciles later), so the running app never breaks on a DB hiccup.
"""
from __future__ import annotations
import pathlib, datetime, json, shutil

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
        return psycopg2.connect(dbname="odin_core_iso")
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
    write it, sync odin_core_iso, and record any correction so the flow keeps moving smoothly.

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
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, (dict, list)):
        content = json.dumps(content, ensure_ascii=False, indent=2)
    p.write_text(content if isinstance(content, str) else str(content), encoding="utf-8")
    sync_row(p, owner_type, owner_id, sf, description)
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
        sync_row(f)  # keep the correction log itself indexed in odin_core_iso (no parity gap)
    except Exception:
        pass


def sync_row(path, owner_type=None, owner_id=None, subfolder=None, description=None) -> None:
    """Upsert the odin_core_iso folder+file rows for a file that already exists on disk. Best-effort;
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
        cu.execute("DELETE FROM files WHERE path=%s", (rel,))
        cu.execute("INSERT INTO files(folder_id,owner_type,owner_id,name,path,kind,description,size_bytes,created_at,modified_at) "
                   "VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                   (fid, owner_type, owner_id, p.name, rel, _kind(p.name),
                    description or f"{_kind(p.name)} '{p.name}' — {owner_type} {owner_id}/{subfolder or 'root'}",
                    s.st_size, datetime.datetime.fromtimestamp(s.st_ctime),
                    datetime.datetime.fromtimestamp(s.st_mtime)))
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
    """Delete a file and its odin_core_iso row together."""
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
    entry AND the odin_core_iso dependency + shared_capability rows. Idempotent."""
    man = WS / _area(owner_type) / owner_id / "dependencies" / "manifest.json"
    try:
        deps = json.loads(man.read_text()) if man.exists() else []
    except Exception:
        deps = []
    existing = next((d for d in deps if d.get("source") == shared_rel), None)
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
        for v in old_variants:
            if v:
                new = new.replace(v, new_rel)
        if new != txt:
            f.write_text(new, encoding="utf-8")
            sync_row(f)
            n += 1
    return n


def promote_to_shared(src_path, category=None, extra_consumers=None) -> dict:
    """MOVE a capability file out of a project/agent into shared/<category>/, then repoint the ORIGINAL
    owner + every extra consumer at it, and update odin_core_iso. The single sanctioned cross-owner move —
    a project cannot do this itself; the middleware does. Returns a summary dict."""
    p = pathlib.Path(src_path)
    ot, oid, _sub = _infer_owner(p)
    name = p.name
    low = name.lower()
    cat = category or ("infra" if "deploy" in low else
                       "testing" if ("test" in low or "e2e" in low or "spec" in low) else "utils")
    dest_rel = f"shared/{cat}/{name}"
    dest = WS / "shared" / cat / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    # capture every form the old path may be referenced by, BEFORE moving it
    old_ws = str(p.relative_to(WS))
    old_variants = {str(p.relative_to(ROOT)), old_ws, "workspace/" + old_ws}
    if not dest.exists():
        shutil.move(str(p), str(dest))          # move (binary-safe) — removes the in-owner copy
    elif p.exists():
        p.unlink()                               # shared already holds it — just drop the duplicate copy
    remove_file(p)                               # drop the old odin_core_iso file row
    sync_row(dest)                               # index the shared location
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
    return {"promoted": dest_rel, "from": f"{ot}/{oid}", "repointed": repointed,
            "category": cat, "source_rewrites": rewrites}


def repoint_reference(referrer_path, old_ref, new_rel) -> bool:
    """Rewrite a referrer's SOURCE so it reads the capability from its new shared location instead of the
    other owner's private path. Replaces the old path string (with or without a 'workspace/' prefix) with
    new_rel, writes back, and re-syncs odin_core_iso. Closes the loop after promote_to_shared so the foreign
    reference is actually gone, not just pointer-added."""
    p = pathlib.Path(referrer_path)
    if not p.is_file():
        return False
    try:
        txt = p.read_text(errors="replace")
    except Exception:
        return False
    variants = {old_ref, old_ref.replace("workspace/", "", 1),
                ("workspace/" + old_ref) if not old_ref.startswith("workspace/") else old_ref}
    new = txt
    for v in variants:
        if v:
            new = new.replace(v, new_rel)
    if new == txt:
        return False
    p.write_text(new, encoding="utf-8")
    sync_row(p)
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


def customize_shared(owner_type, owner_id, name, overlay_name, overlay_content, mode="override") -> dict:
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
    res = put_file(owner_type, owner_id, "code", overlay_name, overlay_content)  # overlay in the owner's own code/
    add_dependency(owner_type, owner_id, name, src, kind="code", mode=mode, overlay=overlay_name)
    return {"ok": True, "base": src, "overlay": overlay_name, "mode": mode, "overlay_path": res["path"]}


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
    overlay_path = (WS / _area(owner_type) / owner_id / "code" / overlay) if overlay else None
    base_ok = bool(base_path and base_path.exists())
    overlay_ok = bool(overlay_path and overlay_path.exists())
    return {"resolved": base_ok and (overlay is None or overlay_ok),
            "base": base_rel, "base_exists": base_ok,
            "mode": entry.get("mode", "as-is"), "overlay": overlay, "overlay_exists": overlay_ok,
            "base_path": str(base_path) if base_path else None,
            "overlay_path": str(overlay_path) if overlay_path else None}


# ---- THE DATABASE IS THE ONLY REGISTRY (parallel-source guard) ----------------------------------
# odin_core_iso is the single source of truth for projects / agents / connectors. A GLOBAL json registry
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
            reason = (f"{fname} is a parallel source of truth — odin_core_iso owns '{table}'. "
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
    """Ensure odin_core_iso has a folder row for EVERY subfolder that exists on disk for this owner,
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
    write index.json, and register it + all its folders in odin_core_iso. Never partial — always the full shape."""
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
    """Clean deletion: remove the owner's folder + all its odin_core_iso rows (its OWN content only —
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
