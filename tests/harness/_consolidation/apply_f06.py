import pathlib
def patch(path, a, b):
    p = pathlib.Path(path); s = p.read_text(); assert s.count(a) == 1, (path, a[:70]); p.write_text(s.replace(a, b))
patch("server/directions.py", """# ---- HTTP router (so chats/agents/UI can query directions) ----""", '''_STOP = set("""how what which who whom whose when where why is are was were be been the a an of for to in on at by
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
                scored.append({**r, "hits": hits})
        scored.sort(key=lambda r: -len(r["hits"]))
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
        return (f"[EXISTING CAPABILITY — looked up in odin_core (directions) for: {kw}: nothing matching found. Say so, then answer.]\\n\\n", [])
    note = (f"[EXISTING CAPABILITY — looked up in odin_core (directions) BEFORE you answer; keywords: {kw}. Start from "
            "these: if a project, report, agent or shared script below already covers the question, answer from it "
            "(its latest outputs/reports) or route the owner to it — do not probe infrastructure directly when an "
            "existing one covers it. Name what you used.]\\n" + "\\n".join(lines) + "\\n\\n")
    return note, ids


# ---- HTTP router (so chats/agents/UI can query directions) ----''')
patch("server/api_v2.py", """        folder_note = ""
        proj_cwd = None
""", """        folder_note = ""
        proj_cwd = None
        # F-06: in the MAIN (company) chat, look up EXISTING capability in odin_core (directions) first
        if not pid and not member:
            try:
                import directions as _dir
                _lk_note, _lk_ids = _dir.lookup_note(text)
                folder_note += _lk_note
                yield sse("status", {"icon": "🔎", "text": "Looked up existing capability: " +
                                     (", ".join(_lk_ids[:6]) if _lk_ids else "nothing matching found")})
            except Exception:
                pass
""")
print("ok")
