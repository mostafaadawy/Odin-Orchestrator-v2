import pathlib, re
p = pathlib.Path("server/api_v2.py"); s = p.read_text()
def patch(a, b):
    global s
    assert s.count(a) == 1, a[:80]; s = s.replace(a, b)
# 1) identity in every orchestration prompt that names the project
lines = s.split("\n"); start = next(i for i, l in enumerate(lines) if l.startswith("def _orchestrate_gen("))
end = next(i for i in range(start + 1, len(lines)) if lines[i].startswith("def "))
n = 0
for i in range(start, end):
    if "'{name}'" in lines[i] and lines[i].lstrip().startswith(("f\"", "brief = (f\"", "work_prompt = (f\"")):
        lines[i] = lines[i].replace("'{name}'", "'{name}' (project id: {pid} — folders and paths use this ID, never the name)", 1); n += 1
s = "\n".join(lines)
assert n >= 7, n
# 2) identity in the chat brain orientation
patch("""    lines = []
    try:
        import agents_registry as _ar
        ags = _ar.list_agents(pid) or []""", """    lines = []
    try:   # F-08: the project's ID and folder — agents must never derive a folder from the project NAME
        import projects as _pjid
        _lp = (_pjid.get_project(pid) or {}).get("localPath") or f"workspace/projects/{pid}/code"
        lines.append(f"[PROJECT ID: {pid} — folder names and paths use this ID, never the project name. "
                     f"Project folder: {_lp}]")
    except Exception:
        pass
    try:
        import agents_registry as _ar
        ags = _ar.list_agents(pid) or []""")
# 3) guard: a write into ANOTHER project's folder (or a folder named after the project NAME) is refused
patch("""    bad = []
    for f in prop.get("files") or []:
        q = _res((f or {}).get("path", ""), base)
        if q is not None and not _inside(q):
            bad.append(f"file {f.get('path')}")""", """    _pname_slug = re.sub(r"[^a-z0-9]+", "-", str(_proj.get("name") or "").lower()).strip("-")
    def _wrong_project(q):
        # F-08: workspace/projects/<x>/... with x != this project's id -> another project's folder, or a folder
        # named after the project NAME instead of its ID. Returns the explanation, or "".
        try:
            x = q.relative_to(ws / "projects").parts[0]
        except Exception:
            return ""
        if x == pid or x.startswith("_"):
            return ""
        why = "a folder named after the project NAME" if x == _pname_slug else "another project's folder"
        return f" — {why} '{x}'; this project's id is '{pid}' (folder: {lp or base})"
    bad = []
    for f in prop.get("files") or []:
        q = _res((f or {}).get("path", ""), base)
        if q is not None and not _inside(q):
            bad.append(f"file {f.get('path')}")
        elif q is not None and _wrong_project(q):
            bad.append(f"file {f.get('path')}{_wrong_project(q)}")""")
p.write_text(s); print("ok, prompts patched:", n)
