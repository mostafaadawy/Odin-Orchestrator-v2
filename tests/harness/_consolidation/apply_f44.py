import pathlib
p = pathlib.Path("server/api_v2.py"); s = p.read_text()
a = """    cap = ""
    try:
        for d in sorted(os.listdir(os.path.join(root, "workspace/agents"))):
            ds = re.sub(r"[^a-z0-9]", "", d.lower())
            if ds and (ds == slug or (len(slug) >= 4 and (slug in ds or ds in slug))):
                cap = _read(f"workspace/agents/{d}/capability.md", 900)
                if cap:
                    break
    except Exception:
        pass
"""
b = """    cap = ""
    try:
        _dirs = sorted(os.listdir(os.path.join(root, "workspace/agents")))
        try:
            import agent_rules as _ar
            _full = _ar.mode() == "full"
        except Exception:
            _full = False
        if _full:
            # F-44: EXACT folder first, else the closest partial match (longest overlap) — the old first-substring
            # rule gave 'Security Operations Investigator' the plain 'security' agent's file. legacy900 keeps the old rule.
            _ex = [d for d in _dirs if re.sub(r"[^a-z0-9]", "", d.lower()) == slug]
            _pa = sorted([d for d in _dirs if len(slug) >= 4 and (slug in re.sub(r"[^a-z0-9]", "", d.lower())
                          or re.sub(r"[^a-z0-9]", "", d.lower()) in slug)],
                         key=lambda d: -len(re.sub(r"[^a-z0-9]", "", d.lower())))
            _dirs = _ex + [d for d in _pa if d not in _ex]
        for d in _dirs:
            ds = re.sub(r"[^a-z0-9]", "", d.lower())
            if ds and (ds == slug or (len(slug) >= 4 and (slug in ds or ds in slug))):
                cap = _read(f"workspace/agents/{d}/capability.md", 900)
                if cap:
                    break
    except Exception:
        pass
"""
assert s.count(a) == 1; p.write_text(s.replace(a, b)); print("ok")
