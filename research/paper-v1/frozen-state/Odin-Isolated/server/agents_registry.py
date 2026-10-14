"""
Agent (team-member) registry + skills/rules engine (Phase 4) + usage stats (Phase 3/5).

Each project owns a set of agents. An agent has: name, role, avatar style, description,
skills/responsibilities/restrictions, an assigned model, and usage stats. Custom rules are saved
per project under data/projects/<pid>/skills/<agent>.md so the core brain understands each
member's purpose and can assign work intelligently. New agents can be proposed from a free-text
description, with a suggested name.
"""
from __future__ import annotations

import re
import store  # type: ignore

AVATARS = ["frontend", "backend", "devops", "security", "qa", "database", "generic"]


def _reg_path(pid: str) -> str:
    return f"projects/{pid}/agents.json"


# ---- COMPANY-level agents (defined once, auto-added to every new project) -------
# The DATABASE is the source of truth for WHICH agents exist. A COMPANY agent is one whose own on-disk
# manifest (workspace/agents/<slug>/index.json, which the DB points to) is marked company:true. There is
# NO global company_agents.json registry.
def _db_agent_ids():
    try:
        import psycopg2  # type: ignore
        c = psycopg2.connect(dbname="odin_core_iso"); cu = c.cursor()
        cu.execute("SELECT id FROM agents"); ids = [r[0] for r in cu.fetchall()]; c.close()
        return ids
    except Exception:
        return None


def _agent_cfg(slug: str) -> dict:
    import json as _j
    import workspace_mw as mw  # type: ignore
    p = mw.resolve_path("agent", slug, "", "index.json")
    try:
        return _j.loads(p.read_text()) if p.exists() else {}
    except Exception:
        return {}


def list_company_agents() -> list:
    ids = _db_agent_ids()
    if ids is None:
        return []
    out = []
    for slug in ids:
        cfg = _agent_cfg(slug)
        if cfg.get("company"):
            cfg.setdefault("name", slug)
            out.append(cfg)
    return out


def add_company_agent(name: str, role: str = "", avatar: str = "generic",
                      description: str = "", rules: list | None = None) -> dict:
    agents = list_company_agents()
    if any(a["name"].lower() == name.lower() for a in agents):
        return next(a for a in agents if a["name"].lower() == name.lower())
    slug = _slug(name)
    a = {"id": slug, "name": name, "role": role or name, "avatar": avatar if avatar in AVATARS else "generic",
         "description": description, "rules": rules or [], "created": store.now(),
         "type": "operational", "company": True}
    # THE single door: write the agent's OWN manifest (marked company) → its folder + odin_core_iso row +
    # indexed. No global registry file.
    try:
        import workspace_mw
        workspace_mw.put_file("agent", slug, "", "index.json", a)
    except Exception:
        pass
    return a


def remove_company_agent(name: str) -> bool:
    # No global registry to rewrite — just update the DB/manifest via the single door.
    try:
        import workspace_mw, psycopg2
        slug = _slug(name)
        refd = 1  # if we can't verify, err on the safe side and KEEP the agent
        try:
            c = psycopg2.connect(dbname="odin_core_iso"); cu = c.cursor()
            cu.execute("SELECT count(*) FROM project_agents WHERE agent_id=%s", (slug,))
            refd = cu.fetchone()[0]; c.close()
        except Exception:
            refd = 1
        if refd == 0:
            workspace_mw.delete_owner("agent", slug)   # not referenced → flush DB row + folder
        else:
            cfg = _agent_cfg(slug); cfg["company"] = False   # referenced → keep, just unmark as company
            workspace_mw.put_file("agent", slug, "", "index.json", cfg)
    except Exception:
        pass
    return True


def _doc(pid: str) -> dict:
    return store.read_json(_reg_path(pid), {"agents": [], "excluded": []})


def list_agents(pid: str) -> list:
    return _doc(pid).get("agents", [])


def all_agents() -> list:
    """The TRUE org-wide roster of ACTUAL agents: every project's real agents (tagged with their project)
    plus the company-level agents. This is what the main page shows so a newly-created agent appears
    globally — not only inside its project. It is NOT the role CATALOG (the 20 template roles); it is the
    agents that actually exist right now."""
    out: list = []
    try:
        import projects as _p
        for pr in _p.list_projects():
            pid = pr.get("id")
            pname = pr.get("name", pid)
            for a in list_agents(pid):
                out.append({**a, "project": pname, "pid": pid, "level": "project"})
    except Exception:
        pass
    for c in list_company_agents():
        out.append({**c, "project": "Company", "pid": "", "level": "company"})
    # DB IS THE SOURCE OF TRUTH: surface EVERY agent registered in odin_core_iso, even one with no JSON
    # roster entry and not company-flagged (e.g. an operator created via create_owner). Without this a
    # DB-registered agent is invisible on the roster screen. Tag it with its DB-linked project(s) else Company.
    try:
        import psycopg2  # type: ignore
        _seen = {str(a.get("name", "")).lower() for a in out}
        _c = psycopg2.connect(dbname="odin_core_iso"); _cu = _c.cursor()
        _cu.execute('SELECT id,name,role,type,"group",nature,description FROM agents ORDER BY name')
        for aid, name, role, typ, grp, nature, desc in _cu.fetchall():
            if str(name or "").lower() in _seen:
                continue
            _c2 = _c.cursor()
            _c2.execute("SELECT p.name FROM project_agents pa JOIN projects p ON p.id=pa.project_id WHERE pa.agent_id=%s", (aid,))
            _projs = [r[0] for r in _c2.fetchall()]
            out.append({"id": aid, "name": name, "role": role or "", "type": typ or "technical",
                        "group": grp, "nature": nature or ("operational" if typ == "operational" else "technical"),
                        "description": desc or "", "skills": [], "restrictions": [], "rules": [],
                        "project": (_projs[0] if _projs else "Company"), "pid": "", "level": "db"})
            _seen.add(str(name or "").lower())
        _c.close()
    except Exception:
        pass
    return out


def excluded_agents(pid: str) -> list:
    """Agents the owner explicitly REMOVED — they must never be auto-re-added by the team seeding,
    company-agent auto-add, or the CTO's on-the-fly hiring, unless the owner adds them back."""
    return _doc(pid).get("excluded", [])


def is_excluded(pid: str, name: str) -> bool:
    return any(e.lower() == (name or "").lower() for e in excluded_agents(pid))


def get_agent(pid: str, name: str):
    for a in list_agents(pid):
        if a["name"].lower() == name.lower():
            return a
    return None


def _save(pid: str, agents: list, excluded: list | None = None) -> None:
    doc = _doc(pid)
    doc["agents"] = agents
    if excluded is not None:
        doc["excluded"] = excluded
    store.write_json(_reg_path(pid), doc)


def register_agent(pid: str, name: str, role: str = "", avatar: str = "generic",
                   description: str = "", skills: list | None = None,
                   restrictions: list | None = None, model: str = "",
                   nature: str = "technical", mode: str = "", force: bool = False,
                   resources: str = "", env: list | None = None, asset: str = "") -> dict | None:
    # an owner-removed agent is never silently brought back — only an EXPLICIT add (force=True) re-allows it
    if is_excluded(pid, name):
        if not force:
            return None
        _save(pid, list_agents(pid), excluded=[e for e in excluded_agents(pid) if e.lower() != name.lower()])
    agents = list_agents(pid)
    if get_agent(pid, name):
        return get_agent(pid, name)
    # If no explicit resources section was given, derive the standard one from the role catalogue so EVERY
    # agent (including a dynamically-created one) starts with an editable Allowed-Resources & Dependencies
    # section. The owner can edit it later from the dashboard.
    if not resources:
        try:
            import projects as _p
            resources = _p.resources_block(name)
        except Exception:
            resources = ""
    a = {
        "name": name,
        "role": role or name,
        "avatar": avatar if avatar in AVATARS else "generic",
        "description": description,
        "skills": skills or [],
        "responsibilities": [],
        "restrictions": restrictions or [],
        "model": model or "",                 # "" => inherits project/main model
        "nature": nature or "technical",      # technical | operational
        "mode": mode or ("normal" if nature == "operational" else ""),  # normal | theoretical
        "resources": resources,                # editable "Allowed Resources & Dependencies" section
        "env": env or [],                      # editable per-agent env vars: [{"key":..,"value":..}, …]
        "asset": asset or "",                  # a reusable asset this agent owns (e.g. "meeting_monitor")
        "rules": [],
        "stats": {"invocations": 0, "lastActive": None},
        "created": store.now(),
    }
    agents.append(a)
    _save(pid, agents)
    _write_skill_file(pid, a)
    # register the role into the project rules so the brain understands the new member
    _append_project_rule(pid, f"- **{name}** ({role}): {description}")
    # DB IS THE SINGLE SOURCE OF TRUTH: every project member becomes a COMPLETE odin_core_iso agents row
    # (name/role/type/nature/description) AND a project_agents link — no roster-only ghost members.
    try:
        import psycopg2  # type: ignore
        _c = psycopg2.connect(dbname="odin_core_iso"); _cu = _c.cursor()
        _cu.execute("SELECT id FROM agents WHERE lower(name)=lower(%s)", (name,))
        _row = _cu.fetchone()
        _sid = _row[0] if _row else _slug(name)
        _nat = a.get("nature") or "operational"
        _cu.execute('INSERT INTO agents(id,name,role,type,nature,description) VALUES(%s,%s,%s,%s,%s,%s) '
                    'ON CONFLICT (id) DO UPDATE SET name=COALESCE(EXCLUDED.name,agents.name),'
                    'role=COALESCE(EXCLUDED.role,agents.role),type=COALESCE(EXCLUDED.type,agents.type),'
                    'nature=COALESCE(EXCLUDED.nature,agents.nature),'
                    'description=COALESCE(EXCLUDED.description,agents.description)',
                    (_sid, name, role or name, _nat, _nat, description))
        _cu.execute("INSERT INTO project_agents(project_id,agent_id) VALUES(%s,%s) ON CONFLICT DO NOTHING", (pid, _sid))
        _c.commit(); _c.close()
    except Exception:
        pass
    return a


def update_agent(pid: str, name: str, **fields) -> dict | None:
    agents = list_agents(pid)
    found = None
    for a in agents:
        if a["name"].lower() == name.lower():
            a.update({k: v for k, v in fields.items() if v is not None})
            found = a
    if found:
        _save(pid, agents)
        _write_skill_file(pid, found)
    return found


def remove_agent(pid: str, name: str) -> bool:
    agents = [a for a in list_agents(pid) if a["name"].lower() != name.lower()]
    exc = list(excluded_agents(pid))
    if not any(e.lower() == name.lower() for e in exc):
        exc.append(name)   # remember the removal so it's never auto-re-added
    _save(pid, agents, excluded=exc)
    # DB lockstep: drop this project's link; if the agent has no folder AND no remaining project links it
    # was a pure roster member -> remove its odin_core_iso row too (no orphan).
    try:
        import psycopg2, workspace_mw as _mw  # type: ignore
        _c = psycopg2.connect(dbname="odin_core_iso"); _cu = _c.cursor()
        _cu.execute("SELECT id FROM agents WHERE lower(name)=lower(%s)", (name,))
        _r = _cu.fetchone(); _sid = _r[0] if _r else _slug(name)
        _cu.execute("DELETE FROM project_agents WHERE project_id=%s AND agent_id=%s", (pid, _sid))
        _cu.execute("SELECT count(*) FROM project_agents WHERE agent_id=%s", (_sid,))
        _links = _cu.fetchone()[0]
        _folder = _mw.resolve_path("agent", _sid, "", "index.json")
        if _links == 0 and not _folder.exists():
            _cu.execute("DELETE FROM agents WHERE id=%s", (_sid,))
        _c.commit(); _c.close()
    except Exception:
        pass
    return True


def record_usage(pid: str, name: str) -> None:
    agents = list_agents(pid)
    for a in agents:
        if a["name"].lower() == name.lower():
            a["stats"]["invocations"] = a["stats"].get("invocations", 0) + 1
            a["stats"]["lastActive"] = store.now()
            _save(pid, agents)
            return


def stats(pid: str) -> dict:
    agents = list_agents(pid)
    total = sum(a["stats"].get("invocations", 0) for a in agents) or 1
    return {
        "total": total,
        "perAgent": [
            {"name": a["name"], "role": a["role"], "avatar": a["avatar"],
             "invocations": a["stats"].get("invocations", 0),
             "percent": round(100 * a["stats"].get("invocations", 0) / total, 1),
             "lastActive": a["stats"].get("lastActive")}
            for a in agents
        ],
    }


# ---- rules / skills -------------------------------------------------------------
def save_rule(pid: str, name: str, rule: str) -> dict | None:
    """Save a reusable, customized rule for an agent (Phase 4 'save as permanent rule')."""
    a = get_agent(pid, name)
    if not a:
        return None
    a.setdefault("rules", []).append({"rule": rule, "ts": store.now()})
    update_agent(pid, name, rules=a["rules"])
    _append_skill(pid, name, f"- RULE: {rule}")
    return a


def _skill_path(pid: str, name: str):
    # Phase-1 structure: an agent's skill/rule doc lives in ITS OWN folder (workspace/agents/<id>/files),
    # not scattered as per-project copies. One home per agent. (Falls back to the old per-project path if the
    # workspace root doesn't exist yet, so nothing breaks before the structure is created.)
    import pathlib
    root = pathlib.Path("workspace")
    if root.exists():
        d = root / "agents" / _slug(name)
        d.mkdir(parents=True, exist_ok=True)
        return d / "capability.md"
    return store.ensure_dir("projects", pid, "plan") / f"{_slug(name)}.md"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "agent"


def _index(p) -> None:
    """Keep odin_core_iso in lockstep for content authored via direct writes (the middleware door's sync),
    so authored agent/project files never dangle as 'unindexed' until the audit runs."""
    try:
        import workspace_mw
        workspace_mw.sync_row(str(p))
    except Exception:
        pass


def _write_skill_file(pid: str, a: dict) -> None:
    p = _skill_path(pid, a["name"])
    skills = [f"- {s}" for s in a.get("skills", [])] or ["- (none yet)"]
    restr = [f"- {r}" for r in a.get("restrictions", [])] or ["- (none)"]
    rules = [f"- {r['rule']}" for r in a.get("rules", [])] or ["- (none yet)"]
    lines = ([f"# {a['name']} — {a['role']}", "", a.get("description", ""), "", "## Skills"]
             + skills + ["", "## Restrictions"] + restr + ["", "## Custom rules"] + rules)
    p.write_text("\n".join(lines), encoding="utf-8")
    _index(p)


def _append_skill(pid: str, name: str, line: str) -> None:
    p = _skill_path(pid, name)
    prev = p.read_text(encoding="utf-8") if p.exists() else f"# {name}\n"
    p.write_text(prev.rstrip() + "\n" + line + "\n", encoding="utf-8")
    _index(p)


def _append_project_rule(pid: str, line: str) -> None:
    import pathlib
    root = pathlib.Path("workspace")
    if root.exists():
        d = root / "projects" / pid / "instructions"
        d.mkdir(parents=True, exist_ok=True)
    else:
        d = store.ensure_dir("projects", pid, "instructions")
    p = d / "instructions.md"
    prev = p.read_text(encoding="utf-8") if p.exists() else f"# Project {pid} — team & rules\n"
    p.write_text(prev.rstrip() + "\n" + line + "\n", encoding="utf-8")
    _index(p)


# ---- propose a new agent from a description (Phase 4) ----------------------------
ROLE_HINTS = {
    # web UI + server/API + database are ONE role now (Fullstack) — no front/back/db split
    "front": ("Full-Stack Engineer", "backend"), "ui": ("Full-Stack Engineer", "backend"),
    "back": ("Full-Stack Engineer", "backend"), "api": ("Full-Stack Engineer", "backend"),
    "full": ("Full-Stack Engineer", "backend"), "web": ("Full-Stack Engineer", "backend"),
    "sql": ("Full-Stack Engineer", "backend"), "db": ("Full-Stack Engineer", "backend"),
    "mobile": ("Mobile Engineer", "frontend"), "flutter": ("Mobile Engineer", "frontend"),
    "android": ("Mobile Engineer", "frontend"), "ios": ("Mobile Engineer", "frontend"),
    "devops": ("DevOps & Cloud", "devops"), "deploy": ("DevOps & Cloud", "devops"),
    "infra": ("DevOps & Cloud", "devops"), "cloud": ("DevOps & Cloud", "devops"),
    "secur": ("Security & Compliance", "security"), "auth": ("Security & Compliance", "security"),
    "test": ("QA & Testing", "qa"), "qa": ("QA & Testing", "qa"),
    "data": ("Data / ML", "database"), "ml": ("Data / ML", "database"),
}


def _default_resources(role: str, nature: str, description: str) -> str:
    """A sensible Allowed-Resources & Dependencies template when the engine can't draft one — so a new
    agent NEVER starts without an editable section."""
    head = ("=== ALLOWED RESOURCES & DEPENDENCIES (read FIRST; REASON before you ask — never ask for "
            "anything already here or already in the brief/shared pool) ===\n")
    if nature == "operational":
        return head + (
            f"• ROLE: NON-technical operator for: {description or role}. You write NO app code.\n"
            "• DEFAULT KEY: if a platform key for you is saved in workspace/shared/oth/.cred it is already available — do not "
            "search for it. KEY CHOICE: when asked to operate, confirm whether to use your DEFAULT key or an "
            "APP-SPECIFIC key provided in the brief/env for this project (ask ONCE if the brief doesn't say).\n"
            "• WHEN YOU WORK: your real work runs AFTER the app is deployed — you receive the link/endpoint, "
            "fetch the required data and post it back via the app API.\n"
            "• ASK-IF-MISSING: if you have no real key and none is provided, ask the CTO ONCE. Never fabricate.\n")
    return head + (
        f"• ROLE: technical specialist for: {description or role}.\n"
        "• PERMISSIONS: read/write within your discipline (Write/Edit/Bash as needed).\n"
        "• ENV/KEYS: read any credentials from the env/brief/shared pool/.env/workspace/shared/oth/.cred; ask the CTO ONCE "
        "only if a needed item is absent everywhere. Do not begin by testing keys unless the task requires it.\n"
        "• NEEDS: the upstream deliverables named in your mandate. Reason before asking; never ask for what "
        "you already have.\n")


def suggest_agent(description: str) -> dict:
    """Recommend a NEW member from a free-text description: name + role + avatar + nature + a drafted
    DESCRIPTION and an editable 'Allowed Resources & Dependencies' section + suggested env keys. The caller
    presents this for the owner to ACCEPT or EDIT before the agent is actually created."""
    d = description.lower()
    role, avatar = "Specialist", "generic"
    for k, (r, av) in ROLE_HINTS.items():
        if k in d:
            role, avatar = r, av
            break
    nature = "operational" if any(w in d for w in (
        "market", "email", "klaviyo", "mailchimp", "content", "support", "helpdesk", "sales", "crm",
        "fulfil", "shipping", "veeqo", "3pl", "analytics", "seo", "finance", "accounting", "operator")) else "technical"
    drafted_desc, resources, env = description.strip(), "", []
    # ENGINE-DRAFTED recommendation (role + description + resources + env), with a robust template fallback.
    try:
        import claude_cli  # type: ignore
        if claude_cli.available():
            prompt = (
                "You are designing a NEW AI team member for a software company. From this need, output ONLY a "
                "JSON object (no prose) with keys: name (one short proper noun), role (a job title), nature "
                "('technical' if it writes/edits code, else 'operational'), description (1-2 sentences), "
                "resources (a clear 'Allowed Resources & Dependencies' section as plain text with bullet lines "
                "covering: its permissions/allowed tools; where its credentials/env live and the default-vs-"
                "provided-key choice if it operates an external platform; what it must have before starting; "
                "what to ASK the CTO for if missing — and a REASON-BEFORE-ASK rule), and env (a JSON array of "
                "objects {key,value} for environment variables it will likely need, value empty if unknown).\n"
                f"NEED: {description}")
            raw = claude_cli.ClaudeCLIBrain().respond(prompt, lang="en")
            obj = _safe_json_obj(raw)
            if obj:
                role = obj.get("role") or role
                nature = obj.get("nature") or nature
                drafted_desc = obj.get("description") or drafted_desc
                resources = obj.get("resources") or ""
                if isinstance(obj.get("env"), list):
                    env = [e for e in obj["env"] if isinstance(e, dict) and e.get("key")]
                _nm = re.sub(r"[^A-Za-z]", "", str(obj.get("name") or "").split()[0]) if obj.get("name") else ""
                _suggested = _nm.capitalize() if 2 <= len(_nm) <= 18 else None
            else:
                _suggested = None
        else:
            _suggested = None
    except Exception:
        _suggested = None
    if not resources:
        resources = _default_resources(role, nature, drafted_desc)
    name = _suggested or (re.sub(r"[^a-z]", "", role.split(" ")[0].lower()) or "agent").capitalize() + "Bot"
    return {"suggestedName": name, "role": role, "avatar": avatar, "nature": nature,
            "description": drafted_desc, "resources": resources, "env": env}


def _safe_json_obj(raw: str):
    import json as _json
    if not raw:
        return None
    s = raw[raw.find("{"): raw.rfind("}") + 1] if "{" in raw and "}" in raw else raw
    try:
        return _json.loads(s)
    except Exception:
        return None
