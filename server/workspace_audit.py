"""
workspace_audit.py — the Audit / Observer (Phase 5): the debounced, self-healing SAFETY NET.

It watches the workspace + the repo root (EXCLUDING the core-app folders and their files) for issues
the Phase-3 middleware didn't prevent, and HEALS them at the SOURCE — it does not paper over problems:
  • un-indexed file (on disk, not in odin_core)   -> index it (real DB sync)
  • misplaced file (wrong schema slot)             -> move it to the canonical slot via the middleware
  • duplicate function in >=2 projects (identical) -> PROMOTE to shared/ + repoint both (custom delta stays)
  • duplicate but different                        -> FLAG (needs a content decision, never guessed)
  • stray file/folder created OUTSIDE workspace    -> FLAG (owner review; may be legit core work)

DEBOUNCED: it acts only after a configurable SILENCE GAP (default 30 min) of no new writes, so it never
reacts to every single file. The owner can enable/disable and set the interval, or stop it entirely.
Every violation + how it was solved is logged to workspace/history/audit-log.jsonl for the audit page.

Design rule: the audit must NOT become a crutch. Its fixes are real (move/index/promote), so if the audit
were removed the corrected state remains. The middleware is the primary defense; the audit is the net.
"""
from __future__ import annotations
import pathlib, json, datetime, hashlib, shutil, re

ROOT = pathlib.Path(__file__).resolve().parent.parent
WS = ROOT / "workspace"
CORE_APPS = {"server", "orchestrator", "voice", "desktop", "odin_app", "dashboard", "shells", "data",
             ".git", ".venv", "workspace"}
CORE_ROOT_FILES = {"CLAUDE.md", "README.md", ".gitignore", ".DS_Store",
                   # generated dev/prod launcher artifacts written at repo root by the shells (phase2/phase3)
                   "anchor_seed.js", "anchor_prod.js", "anchor_sim.html"}
INTERESTING = {".json", ".md", ".sh", ".py", ".ts", ".js", ".jsx", ".tsx", ".dart", ".html", ".jsonl"}
# PRODUCTION projects the audit must NEVER auto-touch (owner handles them in a dedicated phase). Any issue
# that references one of these is dropped from scan() and skipped in heal() — belt-and-suspenders.
PROTECTED_PROJECTS = {"real-deployment-and-diagnosis-organics-07d7"}


def _is_protected(*texts) -> bool:
    for t in texts:
        if not t:
            continue
        s = str(t).replace("\\", "/")
        for pp in PROTECTED_PROJECTS:
            if f"projects/{pp}/" in s or f"projects/{pp}" == s or s == pp:
                return True
    return False
CONFIG = WS / "shared" / "config" / "audit-config.json"
LOG = WS / "history" / "audit-log.jsonl"

_DEFAULT_CFG = {"enabled": True, "silence_minutes": 30, "watch_root": True}


def config() -> dict:
    try:
        return {**_DEFAULT_CFG, **json.loads(CONFIG.read_text())}
    except Exception:
        return dict(_DEFAULT_CFG)


def set_config(**kw) -> dict:
    c = config(); c.update({k: v for k, v in kw.items() if v is not None})
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(json.dumps(c, indent=2))
    try:
        import workspace_mw as mw; mw.sync_row(CONFIG)
    except Exception:
        pass
    return c


def _db():
    try:
        import psycopg2
        return psycopg2.connect(dbname="odin_core")
    except Exception:
        return None


def _interesting(p: pathlib.Path) -> bool:
    return (p.is_file() and p.suffix.lower() in INTERESTING and p.name not in (".gitkeep", ".DS_Store")
            and "__pycache__" not in p.parts)


def quiet_for() -> float:
    """Minutes since the most recent interesting write in the workspace (the silence gap)."""
    newest = 0.0
    for p in WS.rglob("*"):
        if _interesting(p) and p.relative_to(WS).parts[:1] != ("logs",):
            try:
                newest = max(newest, p.stat().st_mtime)
            except Exception:
                pass
    if not newest:
        return 1e9
    return (datetime.datetime.now().timestamp() - newest) / 60.0


def should_run() -> dict:
    """Debounce decision: run only if enabled AND the workspace has been silent long enough."""
    c = config()
    q = quiet_for()
    ok = bool(c["enabled"]) and q >= c["silence_minutes"]
    return {"should_run": ok, "enabled": c["enabled"], "quiet_minutes": round(q, 1),
            "silence_gap": c["silence_minutes"]}


def scan() -> list:
    """Find issues (read-only; changes nothing)."""
    import workspace_mw as mw
    issues = []
    for path, reason in mw.scan_violations():
        issues.append({"type": "misplaced", "path": path, "reason": reason})
    conn = _db()
    if conn:
        try:
            cu = conn.cursor(); cu.execute("SELECT path FROM files"); dbset = {r[0] for r in cu.fetchall()}
        finally:
            conn.close()
        for p in WS.rglob("*"):
            if _interesting(p) and p.relative_to(WS).parts[:1] != ("logs",):
                rel = str(p.relative_to(ROOT))
                if rel not in dbset:
                    issues.append({"type": "unindexed", "path": rel})
        # DB → disk lockstep (reverse direction): a files row whose file is GONE from disk = stale index.
        for dbpath in dbset:
            s = str(dbpath).replace("\\", "/")
            if not s.startswith("workspace/") or s.startswith("workspace/logs/"):
                continue
            if not (ROOT / dbpath).exists():
                issues.append({"type": "db-orphan", "path": dbpath,
                               "reason": "odin_core has a files row but the file is gone from disk — stale index"})
    # ── THE DATABASE IS THE ONLY REGISTRY ─────────────────────────────────────────────────────────────
    # odin_core is the single source of truth for projects / agents / connectors. Any GLOBAL json registry
    # that still holds an entity is a PARALLEL source of truth — exactly the drift that let 37 ghost
    # projects hide behind a clean DB while the UI read the file. Flag every such file loudly; heal the ones
    # whose readers are migrated (projects.json) by deleting them, and flag the rest as pending-migration.
    # THE DATABASE IS THE ONLY REGISTRY — the rule lives in the MIDDLEWARE (the single door); the audit
    # reports it so BOTH layers consider a parallel json registry a violation.
    try:
        for rel, reason, meta in mw.scan_registry_violations():
            issues.append({"type": "parallel-registry", "path": rel, "reason": reason,
                           "orphans": meta.get("orphans", []), "table": meta.get("table"),
                           "key": meta.get("key")})
    except Exception:
        pass
    # ── AGENT REGISTRATION COMPLETENESS + VISIBILITY (the create->DB->visible contract) ───────────────
    # An agent must have a COMPLETE odin_core row (nature + group) AND be surfaced on the roster the app
    # actually reads (/agents/all). This is the guard that would have caught the EasyPost class of bug:
    # a create path that left the row partial, or a DB agent invisible on the roster.
    try:
        _conn2 = _db()
        if _conn2:
            _cu2 = _conn2.cursor()
            _cu2.execute('SELECT id,name,nature,"group" FROM agents')
            _dbrows = _cu2.fetchall(); _conn2.close()
            for _aid, _name, _nature, _grp in _dbrows:
                if not _nature:
                    issues.append({"type": "agent-incomplete", "path": f"agents/{_aid}",
                                   "reason": f"agent '{_name}' has NULL nature in odin_core — the roster groups by nature, so it is mis-grouped/hidden"})
            try:
                import agents_registry as _ar
                _shown = {str(a.get("name", "")).lower() for a in _ar.all_agents()}
                for _aid, _name, _nature, _grp in _dbrows:
                    if str(_name or "").lower() not in _shown:
                        issues.append({"type": "agent-invisible", "path": f"agents/{_aid}",
                                       "reason": f"agent '{_name}' exists in odin_core but is NOT on the roster the app reads (/agents/all) — invisible to the user"})
            except Exception:
                pass
    except Exception:
        pass
    # ROSTER<->DB CONSISTENCY: a project-roster member with NO odin_core representation means the create
    # path did not DB-register it (the DB is the single source of truth for members too).
    try:
        import agents_registry as _ar2, projects as _pj2, re as _re2
        _c3 = _db()
        if _c3:
            _cu3 = _c3.cursor()
            _cu3.execute("SELECT lower(id) FROM agents"); _ids = {r[0] for r in _cu3.fetchall()}
            _cu3.execute("SELECT lower(name) FROM agents"); _nms = {r[0] for r in _cu3.fetchall()}
            _c3.close()
            def _slg(n): return _re2.sub(r"[^a-z0-9]+", "-", n.lower()).strip("-") or "agent"
            for _pr in _pj2.list_projects():
                for _a in _ar2.list_agents(_pr["id"]):
                    _n = str(_a.get("name", ""))
                    if _n and _n.lower() not in _nms and _slg(_n) not in _ids:
                        issues.append({"type": "agent-unregistered", "path": f"projects/{_pr['id']}/agents.json",
                                       "reason": f"roster member '{_n}' in project '{_pr['id']}' has NO odin_core agents row — create path did not DB-register it"})
    except Exception:
        pass
    if config().get("watch_root"):
        for p in ROOT.iterdir():
            if p.name in CORE_APPS or p.name in CORE_ROOT_FILES or p.name.startswith("."):
                continue
            issues.append({"type": "root-stray", "path": p.name,
                           "reason": "created OUTSIDE workspace and the core apps"})
    def _proj(x):
        pp = x.parts
        return pp[pp.index("projects") + 1] if "projects" in pp else None
    # capability-bearing files across ALL owners (code + deploy — the folders that hold reusable logic)
    def _cap_files():
        for sub in ("code", "deploy", "tests"):      # G7: tests/ copies are capabilities too
            for p in WS.glob(f"projects/*/{sub}/**/*"):
                if _interesting(p) and not _is_protected(str(p.relative_to(ROOT))):
                    yield p
    # G5: a project's OWN delta is not a duplicate — (1) a registered overlay in its dependency manifest,
    # (2) a file whose header declares "delta over shared capability: shared/…" (base exists), or (3) a
    # per-project input that a shared capability / core code reads from EVERY project at the same place
    # (e.g. deploy/deploy-config.json read by shared/infra/deploy_changes.py).
    _exempt = _delta_exemptions()
    by_hash, seen = {}, set()
    # (a) IDENTICAL content across >=2 projects — catches the same function under DIFFERENT names
    for p in _cap_files():
        # an IDENTICAL copy is never "custom": only single-file deltas skip this check (G7: not whole folders)
        if str(p.relative_to(ROOT)) in _exempt and not _exempt[str(p.relative_to(ROOT))].startswith("in registered delta folder"):
            continue
        try:
            by_hash.setdefault(hashlib.sha256(p.read_bytes()).hexdigest(), []).append(p)
        except Exception:
            pass
    for h, paths in by_hash.items():
        if len({_proj(x) for x in paths}) >= 2:
            key = tuple(sorted(str(x.relative_to(ROOT)) for x in paths))
            seen.add(key)
            issues.append({"type": "duplicate", "name": paths[0].name, "paths": list(key),
                           "identical": True,
                           "reason": "identical content in >=2 projects (same function, maybe different names) — promote to shared"})
    # (b) same FILENAME but DIFFERENT content across >=2 projects — flag: shared base + custom deltas
    by_name = {}
    for p in _cap_files():
        if str(p.relative_to(ROOT)) in _exempt:
            continue
        by_name.setdefault(p.name, []).append(p)
    for name, paths in by_name.items():
        if len({_proj(x) for x in paths}) >= 2:
            key = tuple(sorted(str(x.relative_to(ROOT)) for x in paths))
            if key not in seen:
                # F-11 (owner's 50% rule): compare every copy with the ORIGINAL (oldest registered) copy
                try:
                    base = mw.oldest_registered(list(key))
                    bt = (ROOT / base).read_text(errors="replace")
                    plan = {x: mw.share_decision(bt, (ROOT / x).read_text(errors="replace")) for x in key if x != base}
                except Exception:
                    base, plan = None, {}
                if plan and all(v["decision"] == "separate" for v in plan.values()):
                    continue   # >50% different everywhere: separate scripts by design — not a duplicate
                issues.append({"type": "duplicate", "name": name, "paths": list(key), "identical": False,
                               "base": base, "plan": plan,
                               "reason": "same filename, different content in >=2 projects — F-11: " + (", ".join(
                                   f"{x.split('/')[2]} {int(v['common'] * 100)}% common -> {v['decision']}"
                                   for x, v in plan.items()) or "promote shared base + custom deltas")})
    # (c) FOREIGN REFERENCE — a file under project X that reads a path INSIDE a different project Y.
    # Structurally X's file is legal, but depending on Y's private files is a cross-owner violation:
    # the referenced capability must live in shared/ and BOTH read it from there. (This is the at-rest
    # complement to the middleware's write-time owner-scope guard.)
    real_projects = {d.name for d in (WS / "projects").iterdir() if d.is_dir()} if (WS / "projects").exists() else set()
    ref_re = re.compile(r'(?:workspace/)?projects/([A-Za-z0-9_\-]+)/([A-Za-z0-9_\-/\.]+)')
    for p in WS.glob("projects/*/**/*"):
        if not _interesting(p) or p.suffix.lower() not in {".py", ".sh", ".js", ".ts", ".dart", ".json", ".md"}:
            continue
        owner = _proj(p)
        try:
            txt = p.read_text(errors="replace")
        except Exception:
            continue
        for m in ref_re.finditer(txt):
            ref_id, ref_tail = m.group(1), m.group(2).rstrip("\"').,)")
            # PRECISE: only a real, resolvable dependency on ANOTHER real project's file is a violation.
            # (A path-like mention of a non-existent id or an area, or an unresolvable tail, is not.)
            if ref_id in (owner, "_shared") or ref_id not in real_projects or not ref_tail:
                continue
            target = WS / "projects" / ref_id / ref_tail
            if not target.is_file():
                continue
            ref_match = m.group(0).rstrip("\"').,)")
            issues.append({"type": "foreign-ref", "path": str(p.relative_to(ROOT)),
                           "owner": owner, "references": ref_id, "ref_match": ref_match,
                           "target": str(target.relative_to(ROOT)), "target_exists": True,
                           "reason": f"project {owner} references files inside project {ref_id} — must go through shared/"})
            break
    # (d) DANGLING REFERENCE (G6) — a capability file that references a file inside a real project or in
    # shared/ that does NOT exist. Before G6 a reference whose target was gone was silently skipped, so a
    # promotion that left one behind made the audit report 0. Records (data/, history/, logs/) and .md
    # notes (which may name planned files) are not checked.
    dang_re = re.compile(r'(?<![\w/\-])((?:workspace/)?(?:projects/([A-Za-z0-9_\-]+)|shared)/[A-Za-z0-9_\-/\.]+)')
    _dang_seen = set()
    for _ot, _oid, p in mw.capability_files(exts={".py", ".sh", ".js", ".ts", ".dart", ".json"}):
        if not _interesting(p):
            continue
        try:
            txt = p.read_text(errors="replace")
        except Exception:
            continue
        for m in dang_re.finditer(txt):
            ref = m.group(1).rstrip("\"').,)")
            pid = m.group(2)
            if pid is not None and pid != "_shared" and pid not in real_projects:
                continue                      # not a real project id: a path-like mention, not a dependency
            _nm = pathlib.PurePath(ref).name
            if "." not in _nm or ".." in ref:
                continue                      # a folder or a relative mention, not a file reference
            if _nm.startswith("."):
                continue                      # secret dotfile (.cred/.auth/.env): never in git, supplied per install
            if (str(p), ref) in _dang_seen:
                continue
            _dang_seen.add((str(p), ref))
            if (WS / mw._ws_rel(ref)).is_file():
                continue
            issues.append({"type": "dangling-ref", "path": str(p.relative_to(ROOT)), "ref": ref,
                           "moved_to": mw.moved_to(ref),
                           "reason": f"references {ref}, which does not exist"})
    issues += _external_writes()
    # PROTECTED projects (production) are never auto-touched — drop any issue that references one.
    issues = [i for i in issues
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
    return issues


_CONV_STR = re.compile(r"projects/(?:<[^>/]+>|\{[^}/]+\}|\$\{?[A-Za-z_]+\}?)/([A-Za-z0-9_\-]+)/([A-Za-z0-9_\-.]+\.[A-Za-z0-9]+)")
_CONV_JOIN = re.compile(r"[\"']([A-Za-z0-9_\-]+)[\"']\s*/\s*[\"']([A-Za-z0-9_\-.]+\.[A-Za-z0-9]+)[\"']")


def _per_project_inputs() -> set:
    """(subfolder, filename) pairs that a SHARED capability reads from every project at the same place
    (e.g. shared/infra/deploy_changes.py reads projects/<pid>/deploy/deploy-config.json)."""
    out = set()
    srcs = [p for p in (WS / "shared").rglob("*") if p.is_file() and p.suffix in (".py", ".sh", ".js", ".ts")
            and ".bak" not in p.name and "testing" not in p.relative_to(WS / "shared").parts[:1]] \
        if (WS / "shared").exists() else []          # test scripts build fixture paths; they are not inputs
    for s in srcs:
        try:
            t = s.read_text(errors="replace")
        except Exception:
            continue
        out.update(_CONV_STR.findall(t))
        for ln in t.splitlines():   # a path join counts only when it is built from a project id
            if re.search(r"projects|\bpid\b|PROJECT", ln):
                out.update(_CONV_JOIN.findall(ln))
    return out


def _delta_exemptions() -> dict:
    """{ROOT-relative path: reason} for every project file that is that project's own delta (G5)."""
    ex = {}
    conv = _per_project_inputs()
    for proj in (WS / "projects").glob("*") if (WS / "projects").exists() else []:
        if not proj.is_dir():
            continue
        man = proj / "dependencies" / "manifest.json"
        try:
            entries = json.loads(man.read_text()) if man.is_file() else []
        except Exception:
            entries = []
        for d in entries if isinstance(entries, list) else []:
            ov = d.get("overlay")
            if ov and str(d.get("source", "")).startswith("shared/"):
                for q in ((proj / ov), (proj / "code" / ov)):
                    if q.is_file():
                        ex[str(q.relative_to(ROOT))] = f"registered delta over {d['source']}"
                    elif q.is_dir():
                        for f in q.rglob("*"):
                            if f.is_file():   # a whole overlay FOLDER: its files differ per project by design
                                ex[str(f.relative_to(ROOT))] = f"in registered delta folder over {d['source']}"
        for sub in ("code", "deploy", "tests"):
            for f in proj.glob(f"{sub}/**/*"):
                if not f.is_file():
                    continue
                rel = str(f.relative_to(ROOT))
                if rel in ex:
                    continue
                if (sub, f.name) in conv and f.parent == proj / sub:
                    ex[rel] = f"per-project input {sub}/{f.name} read by a shared capability"
                    continue
                try:
                    head = f.read_text(errors="replace")[:600]
                except Exception:
                    continue
                m = re.search(r"(?:delta over shared capability:|thin pointer to the shared[^\n(]*\()\s*(?:workspace/)?(shared/[\w./-]+)",
                              head, re.I)
                if m and (WS / m.group(1)).is_file():   # G7: also a declared thin pointer to shared logic
                    ex[rel] = f"declared delta / pointer over {m.group(1)}"
    return ex


def _external_writes() -> list:
    """HARD RULE: a project's GENERATED content must live INSIDE the workspace. This is the check that was
    missing when the SOC wrote to an external localPath. Flags any project whose localPath is OUTSIDE the
    workspace AND contains project-generated content dirs (soc/knowledge/reports/history/intel/enrich caches)."""
    out = []
    try:
        import projects  # type: ignore
        plist = projects.list_projects()
    except Exception:
        return out
    ws_abs = str(WS.resolve())
    GEN = ("soc", "knowledge", "reports", "history", "intel-cache", "enrich-cache", "findings")
    for pr in plist:
        lp = (pr.get("localPath") or "").strip()
        if not lp:
            continue
        try:
            lpp = pathlib.Path(lp).expanduser().resolve()
        except Exception:
            continue
        if str(lpp).startswith(ws_abs) or not lpp.exists():
            continue
        gen = [m for m in GEN if (lpp / m).is_dir()]
        genf = _gen_files(lpp)
        if gen or genf:
            marks = (gen + genf)[:8]
            out.append({"type": "external-write", "path": lp, "owner": pr.get("id"),
                        "reason": "project '%s' has agent-generated content OUTSIDE the workspace (%s)" % (pr.get("id"), ", ".join(marks))})
    return out


def _gen_files(root, cap=3):
    """Bounded (top 2 levels) scan for agent-GENERATED output files under an external dir. Pure code
    folders (no such files) are NOT flagged; anything the agents write out IS."""
    import fnmatch
    pats = ("soc_inventory.json", "run-*.json", "*-report-*.md", "*-report-*.pdf",
            "*-health-*.md", "*-health-*.pdf", "*-health-*.docx", "findings*.json", "asset-inventory.md")
    hits = []
    try:
        dirs = [root] + [d for d in list(root.iterdir())[:30] if d.is_dir()]
        for d in dirs:
            for f in list(d.iterdir())[:200]:
                if f.is_file() and any(fnmatch.fnmatch(f.name, p) for p in pats):
                    hits.append(f.name)
                    if len(hits) >= cap:
                        return hits
    except Exception:
        pass
    return hits


def sentinel(notify=True) -> dict:
    """PROACTIVE audit: heal what is auto-fixable (indexing new files, removing stale rows), then if any HARD
    violation remains (external-write / cross-violations), raise a USER NOTIFICATION so a breach can't sit
    unseen. Called on a debounced timer by the scheduler loop. Safe: heal + read + notify only."""
    # F-37: heal ONLY when the owner's audit switch is ON; when OFF the sentinel detects and reports only
    if config().get("enabled"):
        try:
            heal(force=True)
        except Exception:
            pass
    iss = scan()
    HARD = ("external-write", "foreign-ref", "dangling-ref", "parallel-registry", "misplaced", "duplicate")
    hard = [i for i in iss if i.get("type") in HARD]
    try:   # F-10: PROPOSE a rule for the agent that caused each violation — owner approves; never automatic
        import rule_proposals
        rule_proposals.propose_from_issues(hard)
    except Exception:
        pass
    if notify and hard:
        try:
            import notifications_store as _ns
            ext = [i for i in hard if i.get("type") == "external-write"]
            title = "Workspace audit: %d violation(s)%s" % (len(hard), " — EXTERNAL WRITE" if ext else "")
            def _by(i):   # G8: name the creating agent in the notification
                c = i.get("created_by")
                c = ", ".join(sorted(set(c.values()))) if isinstance(c, dict) else (c or "unknown")
                return " (created by %s)" % c
            body = "; ".join("%s: %s%s" % (i.get("type"), i.get("path") or i.get("owner") or "?", _by(i)) for i in hard[:6])
            _ns.add(kind="finding", title=title, body=body,
                    severity=("critical" if ext else "attention"), icon="\U0001f6e1")
        except Exception:
            pass
    return {"total": len(iss), "hard": len(hard), "issues": iss}


def _log(rec: dict) -> None:
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        rec = {"ts": datetime.datetime.now().isoformat(), **rec}
        with open(LOG, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        import workspace_mw as mw
        mw.sync_row(LOG)
    except Exception:
        pass


def heal(force: bool = False) -> dict:
    """Fix issues at the source. Respects the debounce unless force=True (the page 'Run now' button)."""
    import workspace_mw as mw
    dec = should_run()
    if not config().get("enabled"):
        # F-37: switch OFF = report only. force (the 'Run now' button / sentinel) never overrides the switch.
        iss = scan()
        return {"ran": False, "reason": "audit switched OFF — report only, nothing changed",
                "healed": 0, "flagged": len(iss), "issues": iss, "actions": [], **dec}
    if not force and not dec["should_run"]:
        return {"ran": False, "reason": "debounced", **dec}
    actions = []
    held = mw.held_paths()
    for iss in scan():
        t = iss["type"]
        _paths = [iss.get("path"), iss.get("target"), *(iss.get("paths") or [])]
        if t in ("duplicate", "foreign-ref", "dangling-ref") and any(x and x in held for x in _paths):
            rec = {**iss, "fix": "FLAGGED: held — the owner reverted the earlier automatic fix for these paths"}
            actions.append(rec); _log(rec)
            continue
        # never heal anything that touches a protected production project
        if _is_protected(iss.get("path"), iss.get("owner"), iss.get("references"), iss.get("target"),
                         *(iss.get("paths") or [])):
            actions.append({**iss, "fix": "SKIPPED: protected production project — owner handles it"})
            continue
        _bctx = mw.rewrite_batch(f"audit heal: {t} — {str(iss.get('reason') or iss.get('path') or '')[:160]}")
        _bctx.__enter__()
        try:
            if t == "unindexed":
                mw.sync_row(ROOT / iss["path"])
                fix = "indexed into odin_core"
            elif t == "misplaced":
                p = ROOT / iss["path"]
                if p.exists() and WS in p.parents:
                    ot, oid, sub = mw._infer_owner(p)
                    finalsub, _, _ = mw.route(ot, oid, sub, p.name)
                    dest = mw.resolve_path(ot, oid, finalsub, p.name)
                    if str(dest) != str(p):
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        _g8_cb = mw.get_creator(p)[1]     # G8: a move keeps the creator
                        shutil.move(str(p), str(dest))   # binary-safe (no read_text)
                        mw.remove_file(p)                 # drop old odin_core row
                        mw.sync_row(dest)                 # index the new location
                        if _g8_cb:
                            mw.set_creator(dest, _g8_cb)
                    fix = f"moved to correct slot: {finalsub}"
                else:
                    fix = "skipped (not resolvable)"
            elif t == "duplicate" and iss.get("identical"):
                # promote the FIRST copy to shared via the sanctioned middleware path (moves it + repoints
                # every owner + updates the DB), then drop the remaining identical copies.
                # F-36: keep the OLDEST registered copy, under its ORIGINAL name, in the correct category
                keep = mw.oldest_registered(iss["paths"])
                others = [x for x in iss["paths"] if x != keep]
                res = mw.promote_to_shared(
                    str(ROOT / keep),
                    extra_consumers=[("project", pathlib.Path(x).parts[2]) for x in others])
                for x in others:
                    op = ROOT / x
                    if op.exists():
                        op.unlink()
                    mw.remove_file(op)
                    # G6: the removed copy's references follow it to shared (any owner), and the move is recorded
                    mw.record_removed_copy(x, res["promoted"])
                    mw.record_move(x, res["promoted"], created_shared=False)
                    for o in mw.repoint_everywhere(x, res["promoted"]):
                        if o not in res["repointed"]:
                            res["repointed"].append(o)
                fix = f"promoted identical duplicate -> {res['promoted']}; repointed {res['repointed']}"
            elif t == "foreign-ref" and iss.get("target") and not (ROOT / iss["target"]).is_file():
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
                if iss.get("target_exists") and iss.get("target"):
                    res = mw.promote_to_shared(str(ROOT / iss["target"]),
                                               extra_consumers=[("project", iss["owner"])])
                    # rewrite the referrer's SOURCE so it reads from shared (not the other owner's path)
                    rewrote = False
                    if iss.get("ref_match"):
                        rewrote = mw.repoint_reference(ROOT / iss["path"], iss["ref_match"], res["promoted"])
                    fix = (f"promoted {iss['references']}'s referenced file -> {res['promoted']}; "
                           f"repointed {res['repointed']}; referrer source rewritten: {rewrote}")
                else:
                    fix = (f"FLAGGED: {iss['owner']} references project {iss['references']} but the target "
                           f"file isn't resolvable — needs owner review")
            elif t == "duplicate" and iss.get("base") and iss.get("plan") and \
                    not any(v["decision"] == "review" for v in iss["plan"].values()):
                # F-11 (owner): >50% common -> the ORIGINAL copy becomes the shared base and every >50%-common
                # copy is REPLACED by a true delta (only the differences + a pointer to the base) that rebuilds
                # that project's file byte-for-byte; <50% copies stay separate scripts.
                import delta as _dl
                deltas = [x for x, v in iss["plan"].items() if v["decision"] == "shared+delta"]
                sep = [x for x, v in iss["plan"].items() if v["decision"] == "separate"]
                own = {x: (ROOT / x).read_text(encoding="utf-8") for x in deltas}
                bad = [f"{x}: {_dl.supported(x, own[x])}" for x in deltas if _dl.supported(x, own[x])]
                if bad:
                    fix = "FLAGGED: >50% common but no executable delta is possible (" + "; ".join(bad) + ") — owner review; nothing changed"
                else:
                    base_text = (ROOT / iss["base"]).read_text(encoding="utf-8")
                    res = mw.promote_to_shared(str(ROOT / iss["base"]))
                    done, kept = [], []
                    for x in deltas:
                        d = _dl.make(base_text, own[x], res["promoted"])
                        try:
                            proof = _dl.apply(base_text, d) == own[x]
                        except _dl.DeltaConflict:
                            proof = False
                        if not proof:      # never replace a copy we cannot rebuild exactly
                            kept.append(x); continue
                        xp = ROOT / x
                        mw._apply_rewrite(xp, own[x], _dl.launcher(xp.suffix.lower(), d), "", f"F-11 delta over {res['promoted']}")
                        pp = pathlib.Path(x).parts
                        mw.add_dependency("project", pp[2], pp[-1], res["promoted"], kind="code", mode="delta",
                                          overlay=str(pathlib.Path(*pp[3:])))
                        done.append(f"{x} ({_dl.size_of_changes(d)} changed lines)")
                    fix = (f"F-11 shared base {res['promoted']} + true deltas {done}"
                           + (f"; NOT converted (could not prove an exact rebuild): {kept}" if kept else "")
                           + (f"; kept separate (>50% different): {sep}" if sep else ""))
            elif t == "duplicate":
                fix = ("FLAGGED: duplicate differs across projects — exactly 50% common, owner review (F-11)"
                       if iss.get("plan") else
                       "FLAGGED: duplicate differs across projects — promote shared base + custom deltas (review)")
            elif t == "root-stray":
                fix = "FLAGGED: stray outside workspace — owner review (may be legit core work)"
            elif t == "db-orphan":
                mw.remove_file(ROOT / iss["path"])
                fix = "removed stale odin_core row (file gone from disk) — DB re-mirrors disk"
            elif t == "parallel-registry":
                # The DB is the only registry. projects.json's readers are migrated, so the file is pure
                # violation → delete it (with its DB files-row). The others are still read by their module,
                # so flag them (loud + honest) until their reader is migrated to the DB.
                if str(iss.get("path", "")).endswith("projects.json"):
                    try:
                        mw.remove_file(ROOT / iss["path"])
                    except Exception:
                        p = ROOT / iss["path"]
                        if p.exists():
                            p.unlink()
                    fix = "removed projects.json — the database is the only project registry now"
                else:
                    fix = (f"FLAGGED: {iss['path']} still read by its module — migrate its reader to the DB, "
                           f"then it is removed (pending)")
            else:
                fix = "no-op"
        except mw.SharedNameConflict as e:      # F-36: never overwrite / drop a different shared file
            fix = f"FLAGGED: {e}"
        except Exception as e:
            fix = f"error: {e}"
        finally:
            _bid = mw._BATCH["id"]
            _bctx.__exit__(None, None, None)
        rec = {**iss, "fix": fix, "batch": _bid}
        actions.append(rec)
        _log(rec)
    return {"ran": True,
            "healed": len([a for a in actions if not a["fix"].startswith("FLAGGED")]),
            "flagged": len([a for a in actions if a["fix"].startswith("FLAGGED")]),
            "actions": actions, **dec}


def _add_dependency(owner_id, name, shared_rel):
    man = WS / "projects" / owner_id / "dependencies" / "manifest.json"
    try:
        deps = json.loads(man.read_text()) if man.exists() else []
    except Exception:
        deps = []
    if not any(d.get("source") == shared_rel for d in deps):
        deps.append({"name": name, "source": shared_rel, "kind": "code", "mode": "as-is", "overlay": None})
        man.parent.mkdir(parents=True, exist_ok=True)
        man.write_text(json.dumps(deps, ensure_ascii=False, indent=2))
    conn = _db()
    if conn:
        try:
            cu = conn.cursor()
            cat = shared_rel.split("/")[1] if shared_rel.count("/") >= 2 else "utils"
            cu.execute("INSERT INTO shared_capabilities(id,category,name,path,description) VALUES(%s,%s,%s,%s,%s) ON CONFLICT (id) DO NOTHING",
                       (shared_rel, cat, name, shared_rel, f"promoted shared capability: {name}"))
            cu.execute("INSERT INTO dependencies(owner_type,owner_id,name,source_path,shared_capability_id,kind,mode) VALUES('project',%s,%s,%s,%s,'code','as-is')",
                       (owner_id, name, shared_rel, shared_rel))
            conn.commit()
        except Exception:
            pass
        finally:
            conn.close()


def violations(limit: int = 100) -> list:
    if not LOG.exists():
        return []
    out = []
    for ln in LOG.read_text(errors="replace").splitlines()[-limit:]:
        try:
            out.append(json.loads(ln))
        except Exception:
            pass
    return out


def status() -> dict:
    return {"config": config(), "debounce": should_run(), "open_issues": len(scan())}


def build_router():
    from fastapi import APIRouter
    r = APIRouter(prefix="/audit", tags=["audit"])

    @r.get("/status")
    def _status():
        return status()

    @r.get("/scan")
    def _scan():
        return {"issues": scan()}

    @r.post("/run")
    def _run(force: bool = True):
        return heal(force=force)

    @r.get("/violations")
    def _violations(limit: int = 100):
        return {"log": violations(limit)}

    @r.get("/config")
    def _get_config():
        return config()

    @r.post("/config")
    def _set_config(enabled: bool = None, silence_minutes: int = None, watch_root: bool = None):
        return set_config(enabled=enabled, silence_minutes=silence_minutes, watch_root=watch_root)

    @r.get("/mirror")
    def _mirror():
        # ONE bundle mirrored to the anchor by the poller so the audit "silence page" renders on EVERY
        # surface. COMPACT (cap issues + last violations, truncate big 'detail') so the anchor sync body
        # NEVER exceeds its size limit (was causing 413 -> the whole project sync failed -> request page empty).
        try:
            iss = scan()
        except Exception:
            iss = []
        vio = violations(20) or []
        for v in vio:
            if isinstance(v, dict) and v.get("detail"):
                v["detail"] = str(v["detail"])[:120]
        return {"status": status(), "config": config(), "issues": iss[:25], "violations": vio}

    return r
