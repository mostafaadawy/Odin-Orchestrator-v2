import pathlib, sys
p = pathlib.Path("server/agents_registry.py"); s = p.read_text()
def rep(a, b):
    global s
    assert s.count(a) == 1, a[:80]; s = s.replace(a, b)
# 1) reuse never rewrites the shared capability file
rep("""    agents.append(a)
    _save(pid, agents)
    _write_skill_file(pid, a)
""", """    agents.append(a)
    _save(pid, agents)
    # G10: an agent that already exists elsewhere keeps its SHARED identity (title, description, skills, rules);
    # this project's own role lives in this project's roster (agents.json) and instructions only.
    if not _skill_path(pid, name).exists():
        _write_skill_file(pid, a)
""")
# 2) DB: fill the shared row only where it is empty; never overwrite another project's role/description
rep("""                    'ON CONFLICT (id) DO UPDATE SET name=COALESCE(EXCLUDED.name,agents.name),'
                    'role=COALESCE(EXCLUDED.role,agents.role),type=COALESCE(EXCLUDED.type,agents.type),'
                    'nature=COALESCE(EXCLUDED.nature,agents.nature),'
                    'description=COALESCE(EXCLUDED.description,agents.description)',
                    (_sid, name, role or name, _nat, _nat, description))""",
"""                    'ON CONFLICT (id) DO UPDATE SET name=COALESCE(NULLIF(agents.name,\\'\\'),EXCLUDED.name),'
                    'role=COALESCE(NULLIF(agents.role,\\'\\'),EXCLUDED.role),type=COALESCE(agents.type,EXCLUDED.type),'
                    'nature=COALESCE(agents.nature,EXCLUDED.nature),'
                    'description=COALESCE(NULLIF(agents.description,\\'\\'),EXCLUDED.description)',
                    (_sid, name, role or name, _nat, _nat, description))  # G10: keep the shared values""")
# 3) edits MERGE into an existing shared file (add bullets, never remove; header kept)
rep("""def _write_skill_file(pid: str, a: dict) -> None:
    p = _skill_path(pid, a["name"])
""", """def _merge_skill_file(p, a: dict) -> None:
    \"\"\"G10: add this project's skills/restrictions/rules to an EXISTING shared capability file. The title and
    description (shared identity) are kept, existing bullets are never removed, nothing is duplicated.\"\"\"
    text = p.read_text(encoding="utf-8")
    want = {"Skills": [str(x) for x in a.get("skills", [])],
            "Restrictions": [str(x) for x in a.get("restrictions", [])],
            "Custom rules": [r["rule"] if isinstance(r, dict) else str(r) for r in a.get("rules", [])]}
    lines = text.rstrip("\\n").split("\\n")
    for sec, items in want.items():
        items = [i for i in items if i]
        if not items:
            continue
        hdr = f"## {sec}"
        if hdr not in lines:
            lines += ["", hdr]
        i = lines.index(hdr); j = i + 1
        while j < len(lines) and not lines[j].startswith("## "):
            j += 1
        body = lines[i + 1:j]
        have = {l.strip() for l in body}
        new = [f"- {x}" for x in items if f"- {x}" not in have]
        if not new:
            continue
        body = [l for l in body if l.strip() not in ("- (none yet)", "- (none)")]
        while body and not body[-1].strip():
            body.pop()
        lines = lines[:i + 1] + body + new + ([""] if j < len(lines) else []) + lines[j:]
    out = "\\n".join(lines) + "\\n"
    if out != text:
        p.write_text(out, encoding="utf-8")
        _index(p)


def _write_skill_file(pid: str, a: dict) -> None:
    p = _skill_path(pid, a["name"])
    if p.exists():
        _merge_skill_file(p, a)   # G10: never overwrite a shared agent's file
        return
""")
# 4) appending a rule line is idempotent (no duplicate when the same company rule is re-saved per project)
rep("""    prev = p.read_text(encoding="utf-8") if p.exists() else f"# {name}\\n"
    p.write_text(prev.rstrip() + "\\n" + line + "\\n", encoding="utf-8")
    _index(p)


def _append_project_rule""", """    prev = p.read_text(encoding="utf-8") if p.exists() else f"# {name}\\n"
    if line.strip() in {l.strip() for l in prev.splitlines()}:
        return   # G10: already there
    p.write_text(prev.rstrip() + "\\n" + line + "\\n", encoding="utf-8")
    _index(p)


def _append_project_rule""")
p.write_text(s); print("patched")
