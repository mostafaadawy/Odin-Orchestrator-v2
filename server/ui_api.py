"""
ui_api.py — the GENERIC UI contract (Phase 6).

One endpoint the desktop (primary), web, and mobile all consume so the clients are pure MAPPERS:
  • content defines the COUNT  -> the client renders array.map over whatever the DB returns (8 or 20,000)
  • type defines the UI        -> each item carries a resolved `ui` spec (chip + controls + icons) derived
                                  from shared/config/project-types/<type>.json and shared/config/features/*

Nothing in the clients is hardcoded: a project's buttons come from its type, its icons from its features,
its agent/connector counts from the DB relations. Add a project type or feature definition and every client
picks it up automatically. The anchor mirrors this same payload so web/mobile stay in sync cheaply.
"""
from __future__ import annotations
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
WS = ROOT / "workspace"


def _db():
    import psycopg2
    return psycopg2.connect(dbname="odin_core")


def _typedef(t: str) -> dict:
    try:
        return json.loads((WS / "shared" / "config" / "project-types" / f"{t}.json").read_text())
    except Exception:
        return {}


def _agent_typedef(t: str) -> dict:
    try:
        return json.loads((WS / "shared" / "config" / "agent-types" / f"{t}.json").read_text())
    except Exception:
        return {}


def _featuredef(f: str) -> dict:
    try:
        return json.loads((WS / "shared" / "config" / "features" / f"{f}.json").read_text())
    except Exception:
        return {}


def _features_of(pid: str) -> list:
    try:
        ix = json.loads((WS / "projects" / pid / "index.json").read_text())
        return ix.get("features") or []
    except Exception:
        return []


def project_cards() -> list:
    """The generic, DB-driven list. Each card = data (from odin_core) + a resolved `ui` spec (from the
    type + feature definitions). The client just maps this — no per-type branching in the UI code."""
    c = _db(); cu = c.cursor()
    cu.execute("SELECT id,name,type,category,cadence,config,status,description,features FROM projects ORDER BY name")
    rows = cu.fetchall()
    cards = []
    for pid, name, typ, cat, cadence, config, status, desc, features in rows:
        cu.execute("SELECT count(*) FROM project_agents WHERE project_id=%s", (pid,)); nag = cu.fetchone()[0]
        cu.execute("SELECT c.name FROM project_connectors pc JOIN connectors c ON c.id=pc.connector_id WHERE pc.project_id=%s", (pid,))
        conns = [r[0] for r in cu.fetchall()]
        cu.execute("SELECT count(*) FROM files WHERE owner_type='project' AND owner_id=%s", (pid,)); nfiles = cu.fetchone()[0]
        # the project's AGENTS also shape the UI (owner's rule: type AND the used agent define the buttons)
        cu.execute("SELECT a.name, a.role FROM project_agents pa JOIN agents a ON a.id=pa.agent_id WHERE pa.project_id=%s", (pid,))
        agent_blurbs = [f"{(r[0] or '')} {(r[1] or '')}".lower() for r in cu.fetchall()]
        td = _typedef(typ or "normal").get("ui", {})
        feats = features or []
        icons = [ic for f in feats for ic in [(_featuredef(f).get("icon"))] if ic]
        controls = list(td.get("controls", []))
        # CADENCE also drives the run button when the type didn't specify one (content defines behavior too):
        # a runnable project with a cadence gets its run control even if its type is plain 'normal'.
        if not any(x in controls for x in ("play", "run-once")):
            if cadence == "recurring":
                controls = ["play", "cadence"] + controls
            elif cadence == "periodical":
                controls = ["play", "period"] + controls
            elif cadence == "once":
                controls = ["run-once"] + controls
        # a Reporting/Exporter agent -> an EXPORT button; a Voice agent -> the voice icon (agent-driven UI)
        if any(("report" in b or "export" in b) for b in agent_blurbs) and "export" not in controls:
            controls.append("export")
        if any("voice" in b for b in agent_blurbs) and "streaming-voice" not in icons:
            icons.append("streaming-voice")
        cards.append({
            "id": pid, "name": name, "type": typ, "category": cat, "cadence": cadence,
            "config": config or {}, "status": status, "description": desc,
            "counts": {"agents": nag, "connectors": len(conns), "files": nfiles},
            "connectors": conns, "features": feats,
            "ui": {"chip": td.get("chip", (typ or "normal").title()),
                   "controls": controls,                  # type controls + agent-driven (e.g. export)
                   "icons": icons},                       # feature/agent icons (e.g. voice-streaming)
        })
    c.close()
    return cards


def project_card(pid: str) -> dict:
    for c in project_cards():
        if c["id"] == pid:
            return c
    return {"error": "not found", "id": pid}


def agent_cards() -> list:
    """Generic agent roster — data-driven, carries type/group so the client groups without hardcoding."""
    c = _db(); cu = c.cursor()
    cu.execute('SELECT id,name,role,type,"group",nature,description FROM agents ORDER BY type,"group",name')
    rows = cu.fetchall()
    out = []
    for aid, name, role, typ, grp, nature, desc in rows:
        cu.execute("SELECT count(*) FROM project_agents WHERE agent_id=%s", (aid,))
        npro = cu.fetchone()[0]
        atd = _agent_typedef(typ or "technical").get("ui", {})
        # agent-driven buttons: the agent's own role/nature adds controls (voice / export / run) so the UI
        # respects the USED AGENT, not just static text (owner's rule).
        blurb = f"{name} {role or ''} {desc or ''}".lower()
        actrls = []
        if "voice" in blurb:
            actrls.append("voice")
        if "report" in blurb or "export" in blurb or "document" in blurb:
            actrls.append("export")
        out.append({"id": aid, "name": name, "role": role, "type": typ, "group": grp,
                    "nature": nature, "description": desc, "projects": npro,
                    # same generic contract as projects: TYPE defines the chip/group label the client renders
                    "ui": {"chip": atd.get("chip", (typ or "technical").title()), "group": grp,
                           "controls": actrls}})
    c.close()
    return out


def type_catalog() -> dict:
    """Every project type + agent type + feature definition — so a client can render controls/icons
    for types it has never seen before (fully generic)."""
    def _load(dirn):
        d = WS / "shared" / "config" / dirn
        out = {}
        if d.exists():
            for f in d.glob("*.json"):
                try:
                    out[f.stem] = json.loads(f.read_text())
                except Exception:
                    pass
        return out
    return {"project_types": _load("project-types"), "agent_types": _load("agent-types"),
            "features": _load("features")}


def _connector_connected(cid: str) -> bool:
    """Best-effort live status for a connector badge (never throws)."""
    import shutil
    cl = (cid or "").lower()
    if cl in ("claude-cli", "claude"):
        return shutil.which("claude") is not None
    if cl in ("az-cli", "az", "azure"):
        return shutil.which("az") is not None
    try:
        import capabilities
        for c in capabilities.list_connectors():
            if (c.get("id", "") == cid) or (c.get("name", "").lower() == cl):
                return bool(c.get("connected", True))
    except Exception:
        pass
    return True  # configured connector folder exists → treat as available unless proven otherwise


def connector_cards() -> list:
    """Generic connector list straight from odin_core — the UI array.maps THIS for the connection badges
    (not a hardcoded HubSpot-only badge). Add a connector folder + row and its badge appears automatically."""
    c = _db(); cu = c.cursor()
    cu.execute("SELECT id,name,path FROM connectors ORDER BY name")
    rows = cu.fetchall(); c.close()
    out = []
    for cid, name, path in rows:
        kind = ""
        try:
            if path:
                kind = json.loads((ROOT / path / "index.json").read_text()).get("kind", "")
        except Exception:
            kind = ""
        out.append({"id": cid, "name": name, "kind": kind, "connected": _connector_connected(cid)})
    return out


def build_router():
    from fastapi import APIRouter
    r = APIRouter(prefix="/ui", tags=["ui"])

    @r.get("/projects")
    def _projects(offset: int = 0, limit: int = 0):
        cards = project_cards()
        page = cards[offset:offset + limit] if limit else cards[offset:]
        return {"cards": page, "total": len(cards), "offset": offset, "limit": limit}

    @r.get("/project/{pid}")
    def _project(pid: str):
        return project_card(pid)

    @r.get("/agents")
    def _agents(offset: int = 0, limit: int = 0):
        ags = agent_cards()
        page = ags[offset:offset + limit] if limit else ags[offset:]
        return {"agents": page, "total": len(ags), "offset": offset, "limit": limit}

    @r.get("/types")
    def _types():
        return type_catalog()

    @r.get("/connectors")
    def _connectors():
        return {"connectors": connector_cards()}

    return r
