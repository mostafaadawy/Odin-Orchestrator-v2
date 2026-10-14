"""
directions.py — the schema-backed knowledge layer (Phase 4).

The entrypoint the CTO brain, agents, and every chat read FIRST. It is a LIVE VIEW over odin_core
(kept in lockstep by the Phase-3 middleware), so it always reflects what the system currently has —
no manual refresh. It answers:
  • overview()            — the full system picture (what we have)
  • find(q)               — where does X live (files/projects/agents/shared) by keyword
  • capability(need)      — THE anti-duplication advisory: does a shared capability already exist,
                            who already customized it, and the reuse recipe (reuse shared + custom delta)
  • resources(otype,oid)  — an owner's files, dependencies, connectors (what it can already reach)
  • similar(text)         — similar prior work

If odin_core is unreachable, functions return an explanatory stub instead of raising, so callers
never break.
"""
from __future__ import annotations


def _db():
    import psycopg2
    return psycopg2.connect(dbname="odin_core")


def _rows(sql, params=()):
    try:
        c = _db(); cu = c.cursor()
        cu.execute(sql, params)
        cols = [d[0] for d in cu.description]
        out = [dict(zip(cols, r)) for r in cu.fetchall()]
        c.close()
        return out
    except Exception as e:
        return [{"_error": str(e)}]


def overview() -> dict:
    """The full picture — what the system currently has."""
    def n(t):
        r = _rows(f"SELECT count(*) c FROM {t}")
        return r[0].get("c") if r and "c" in r[0] else None
    return {
        "projects": n("projects"), "agents": n("agents"), "connectors": n("connectors"),
        "chats": n("chats"), "shared_capabilities": n("shared_capabilities"),
        "files": n("files"), "dependencies": n("dependencies"),
        "project_agent_links": n("project_agents"), "project_connector_links": n("project_connectors"),
        "agent_types": _rows("SELECT type, count(*) c FROM agents GROUP BY type ORDER BY c DESC"),
        "project_types": _rows("SELECT type, count(*) c FROM projects GROUP BY type ORDER BY c DESC"),
        "note": "live view over odin_core; current as of the last middleware write",
    }


def find(q: str, limit: int = 25) -> dict:
    """Where does X live — search files, projects, agents, shared capabilities by keyword."""
    like = f"%{q}%"
    return {
        "query": q,
        "projects": _rows("SELECT id,name,type,category,description FROM projects WHERE name ILIKE %s OR id ILIKE %s OR description ILIKE %s LIMIT %s", (like, like, like, limit)),
        "agents": _rows('SELECT id,role,type,"group",description FROM agents WHERE name ILIKE %s OR role ILIKE %s OR description ILIKE %s LIMIT %s', (like, like, like, limit)),
        "connectors": _rows("SELECT id,name,description FROM connectors WHERE name ILIKE %s OR id ILIKE %s OR description ILIKE %s LIMIT %s", (like, like, like, limit)),
        "chats": _rows("SELECT id,title,path,description FROM chats WHERE id ILIKE %s OR title ILIKE %s OR description ILIKE %s LIMIT %s", (like, like, like, limit)),
        "shared_capabilities": _rows("SELECT id,category,name,path,description FROM shared_capabilities WHERE name ILIKE %s OR path ILIKE %s OR category ILIKE %s LIMIT %s", (like, like, like, limit)),
        "files": _rows("SELECT owner_type,owner_id,name,path,kind,description FROM files WHERE name ILIKE %s OR path ILIKE %s OR description ILIKE %s ORDER BY owner_type LIMIT %s", (like, like, like, limit)),
    }


def capability(need: str) -> dict:
    """THE capability-reuse advisory. Before creating anything for <need>, ask this. Returns the
    existing shared capability, who already uses/customized it, and the reuse recipe — so no
    duplicate (`deploy_2`, `deploy_othername`, …) is ever created."""
    like = f"%{need}%"
    shared = _rows("SELECT id,category,name,path,description FROM shared_capabilities WHERE name ILIKE %s OR path ILIKE %s OR category ILIKE %s ORDER BY category LIMIT 25", (like, like, like))
    used_by = _rows("SELECT owner_type,owner_id,name,source_path,mode,overlay_path FROM dependencies WHERE name ILIKE %s OR source_path ILIKE %s ORDER BY owner_type", (like, like))
    # ALSO surface the same capability built CUSTOM inside a project/agent (not yet promoted to shared) —
    # so "we already did it in another project" is answerable and can be reused/promoted instead of re-built.
    also_built_in = _rows(
        "SELECT owner_type,owner_id,name,path,description FROM files "
        "WHERE owner_type IN ('project','agent') AND (name ILIKE %s OR path ILIKE %s OR description ILIKE %s) "
        "AND (path LIKE '%%/code/%%' OR path LIKE '%%/deploy/%%' OR path LIKE '%%/tests/%%') "
        "ORDER BY owner_type LIMIT 15", (like, like, like))
    have_shared = bool([s for s in shared if "_error" not in s])
    have_custom = bool([x for x in also_built_in if "owner_id" in x])
    if have_shared:
        verdict = "EXISTS in shared — reuse it"
        recipe = (f"REUSE the existing shared capability (do NOT create a new '{need}_2' or duplicate). "
                  f"Point your dependencies/manifest.json at the shared path. If you need a difference, reuse the "
                  f"shared part UP TO A POINT and add ONLY your custom delta as an overlay in your own code/ "
                  f"(mode: extend | subset | override). See 'used_by' for how others already customized it.")
    elif have_custom:
        verdict = "EXISTS as custom in another owner — reuse or promote it"
        recipe = (f"'{need}' is already implemented custom inside another project/agent (see 'also_built_in'). "
                  f"Do NOT rebuild it. Either reuse it directly, or (if it will serve >1 owner) PROMOTE it to "
                  f"shared/<category>/ and point both owners at it with your own custom delta as an overlay.")
    else:
        verdict = "NOT FOUND — build in shared if reusable"
        recipe = (f"No shared or custom implementation found for '{need}'. If you build it and it could serve more "
                  f"than one owner, create it in shared/<category>/ and point to it — don't bury it inside one project.")
    return {"need": need, "verdict": verdict, "shared": shared, "used_by": used_by,
            "also_built_in": also_built_in, "reuse_recipe": recipe}


def resources(owner_type: str, owner_id: str) -> dict:
    """What an owner can already reach — its files, shared dependencies, connectors."""
    return {
        "owner": f"{owner_type}/{owner_id}",
        "files": _rows("SELECT name,path,kind,description FROM files WHERE owner_type=%s AND owner_id=%s ORDER BY name", (owner_type, owner_id)),
        "dependencies": _rows("SELECT name,source_path,mode,overlay_path FROM dependencies WHERE owner_type=%s AND owner_id=%s", (owner_type, owner_id)),
        "connectors": (_rows("SELECT c.name,c.description FROM project_connectors pc JOIN connectors c ON c.id=pc.connector_id WHERE pc.project_id=%s", (owner_id,)) if owner_type == "project" else []),
        "agents": (_rows("SELECT a.name,a.role,a.type FROM project_agents pa JOIN agents a ON a.id=pa.agent_id WHERE pa.project_id=%s", (owner_id,)) if owner_type == "project" else []),
    }


def similar(text: str, limit: int = 15) -> dict:
    """Similar prior work — files/projects whose description overlaps the request (keyword scan)."""
    words = [w for w in "".join(ch if ch.isalnum() else " " for ch in text.lower()).split() if len(w) > 3][:6]
    if not words:
        return {"text": text, "matches": []}
    conds = " OR ".join(["description ILIKE %s" for _ in words])
    params = tuple(f"%{w}%" for w in words) + (limit,)
    return {"text": text, "keywords": words,
            "matches": _rows(f"SELECT owner_type,owner_id,name,path,description FROM files WHERE {conds} LIMIT %s", params)}


_STOP = set("""how what which who whom whose when where why is are was were be been the a an of for to in on at by
with and or our your my their its this that these those does do did can could would should will please tell me us
show give get about any some all there here have has had from into it as status current currently""".split())
_SHORT = {"vm", "db", "ui", "qa", "ci", "ip", "ai", "crm", "soc", "api"}


def _tokens(text: str) -> list:
    words = "".join(ch if ch.isalnum() else " " for ch in str(text).lower()).split()
    out = []
    for w in words:
        if w in _STOP or (len(w) < 4 and w not in _SHORT):
            continue
        w = w[:-1] if len(w) > 4 and w.endswith("s") else w
        if w not in out:
            out.append(w)
    return out[:10]


def lookup(question: str, limit: int = 5) -> dict:
    """F-06: deterministic, read-only lookup of EXISTING capability for a main-chat question (no LLM):
    projects, agents, shared capabilities and report files in odin_core whose id/name/description/path
    match the question's keywords, ranked by how many distinct keywords they hit."""
    toks = _tokens(question)
    empty = {"question": question, "keywords": toks, "projects": [], "agents": [], "shared": [], "files": []}
    if not toks:
        return empty
    def rank(rows, fields, need=1):
        scored = []
        for r in rows:
            if "_error" in r:
                continue
            hay = " ".join(str(r.get(f) or "") for f in fields).lower()
            hits = [t for t in toks if t in hay]
            if len(hits) >= need:
                ident = " ".join(str(r.get(f) or "") for f in fields[:2]).lower()   # id / name hits weigh more
                scored.append({**r, "hits": hits, "_w": len(hits) + 0.5 * sum(t in ident for t in hits)})
        scored.sort(key=lambda r: -r["_w"])
        return scored[:limit]
    return {"question": question, "keywords": toks,
            "projects": rank(_rows("SELECT id,name,type,category,path,description FROM projects"),
                             ("id", "name", "description", "category"), need=2 if len(toks) > 2 else 1),
            "agents": rank(_rows("SELECT id,name,role,description FROM agents"), ("id", "name", "role", "description"),
                           need=2 if len(toks) > 2 else 1),
            "shared": rank(_rows("SELECT id,category,name,path,description FROM shared_capabilities"),
                           ("name", "path", "category", "description"), need=2 if len(toks) > 2 else 1),
            "files": rank(_rows("SELECT owner_type,owner_id,name,path,description FROM files WHERE owner_type='project' "
                                "AND (name ILIKE '%%report%%' OR name ILIKE '%%diagnos%%' OR name ILIKE '%%health%%' OR name ILIKE '%%status%%')"),
                          ("owner_id", "name", "path", "description"), need=2)}


def lookup_note(question: str) -> tuple:
    """The block the main-chat CTO reads BEFORE answering, plus the ids found (for the visible status line)."""
    r = lookup(question)
    ids, lines = [], []
    for p in r["projects"]:
        ids.append(f"project {p['id']}"); lines.append(f"- project {p['id']} ({p.get('name')}): {str(p.get('description') or '')[:200]}")
    for f in r["files"]:
        ids.append(f"report {f['path']}"); lines.append(f"- report/file {f['path']} (project {f['owner_id']})")
    for s in r["shared"]:
        ids.append(f"shared {s['path']}"); lines.append(f"- shared capability {s['path']}: {str(s.get('description') or '')[:120]}")
    for a in r["agents"]:
        ids.append(f"agent {a['name']}"); lines.append(f"- agent {a['name']} ({a.get('role')})")
    kw = ", ".join(r["keywords"])
    if not lines:
        return (f"[EXISTING CAPABILITY — looked up in odin_core (directions) for: {kw}: nothing matching found. Say so, then answer.]\n\n", [])
    note = (f"[EXISTING CAPABILITY — looked up in odin_core (directions) BEFORE you answer; keywords: {kw}. Start from "
            "these: if a project, report, agent or shared script below already covers the question, answer from it "
            "(its latest outputs/reports) or route the owner to it — do not probe infrastructure directly when an "
            "existing one covers it. Name what you used.]\n" + "\n".join(lines) + "\n\n")
    return note, ids


# ---- HTTP router (so chats/agents/UI can query directions) ----
def build_router():
    from fastapi import APIRouter
    r = APIRouter(prefix="/directions", tags=["directions"])

    @r.get("/overview")
    def _overview():
        return overview()

    @r.get("/find")
    def _find(q: str, limit: int = 25):
        return find(q, limit)

    @r.get("/capability")
    def _capability(need: str):
        return capability(need)

    @r.get("/resources")
    def _resources(owner_type: str, owner_id: str):
        return resources(owner_type, owner_id)

    @r.get("/similar")
    def _similar(text: str):
        return similar(text)

    return r
