#!/usr/bin/env python3
"""G9: when the intake or a run names a different credential for a service, record the CHOICE (a reference name,
never the value) in agent_scope and in the project's own connectors/ folder; never in shared/oth/.cred.
Proposals that write a secret store (shared/oth/, *.cred, .env*) are refused like outside writes."""
import pathlib, sys
R = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
def sub(path, old, new, count=1):
    p = R / path; s = p.read_text()
    assert s.count(old) == count, (path, old[:70], s.count(old)); p.write_text(s.replace(old, new))
MW, PJ, API = "server/workspace_mw.py", "server/projects.py", "server/api_v2.py"
sub(MW, '''def agent_scope_guard(project_id, agent):''', '''# ── G9: the per-project CREDENTIAL CHOICE is recorded (reference name only — never the secret value) ──
_CRED_SERVICES = {"klaviyo": "klaviyo", "veeqo": "veeqo", "hubspot": "hubspot", "easypost": "easypost",
                  "stripe": "stripe", "shopify": "shopify", "google analytics": "analytics", "ga4": "analytics"}
_CRED_REF = re.compile(r"\\b([A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*_(?:KEY|TOKEN|SECRET)(?:_[A-Z0-9]+)*)\\b")


def credential_choice_from_text(text) -> list:
    """[(service, credential_ref)] named in an owner text, e.g. 'its key will be stored as KLAVIYO_KEY_BRAND2'.
    A reference is paired with the service named inside it, else with the only service the text mentions."""
    t = text or ""
    refs = list(dict.fromkeys(_CRED_REF.findall(t)))
    if not refs:
        return []
    low = t.lower()
    svcs = list(dict.fromkeys(v for k, v in _CRED_SERVICES.items() if re.search(r"\\b" + re.escape(k) + r"\\b", low)))
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


def agent_scope_guard(project_id, agent):''')
sub(PJ, '''    proj["members"] = [a["name"] for a in agents_registry.list_agents(pid)]
    _update(proj)

''', '''    proj["members"] = [a["name"] for a in agents_registry.list_agents(pid)]
    _update(proj)
    # G9: a different credential named in the owner's brief is RECORDED (agent_scope + connectors/ reference)
    try:
        import workspace_mw as _mw_g9
        for _svc, _ref in _mw_g9.credential_choice_from_text(f"{name}. {description}"):
            _mw_g9.record_credential_choice(pid, _svc, _ref, source="intake")
    except Exception:
        pass

''')
sub(API, '''        _cls = _intent.classify_request(goal, engine=getattr(projects, "_engine", None))''', '''        try:   # G9: a credential choice stated in a RUN is recorded too (reference name only)
            import workspace_mw as _mw_g9
            for _svc, _ref in _mw_g9.credential_choice_from_text(goal):
                _mw_g9.record_credential_choice(pid, _svc, _ref, source="run")
        except Exception:
            pass
        _cls = _intent.classify_request(goal, engine=getattr(projects, "_engine", None))''')
# secret stores are never a write target
sub(API, '''    def _inside(q):
        return q in exact or any(q == r or r in q.parents for r in roots)''', '''    def _inside(q):
        if _secret(q):
            return False   # G9: a secret store is never a write target, even inside the workspace
        return q in exact or any(q == r or r in q.parents for r in roots)
    def _secret(q):
        return ((ws / "shared" / "oth") == q or (ws / "shared" / "oth") in q.parents or q.suffix == ".cred"
                or q.name == ".cred" or q.name == ".env" or q.name.startswith(".env."))''')
print("G9 applied")

# ---- G9 part 2: .env.example / .env.sample / .env.template are templates, not secret stores (applied in-tree)
