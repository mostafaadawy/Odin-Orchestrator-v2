import pathlib
p = pathlib.Path("server/api_v2.py"); s = p.read_text()
a = """    if cap:
        out.append("### What YOU can do (your capability.md):\\n" + cap)
"""
b = """    if cap:
        out.append("### What YOU can do (your capability.md):\\n" + cap)
        # F-43: the agent's FULL 'Must honor' + 'Custom rules' (capped; '' in legacy900 mode = paper v1 behaviour)
        try:
            import agent_rules
            _rb = agent_rules.block(member, _read(f"workspace/agents/{d}/capability.md", 10 ** 7))
            if _rb:
                out.append(_rb)
        except Exception:
            pass
"""
assert s.count(a) == 1; p.write_text(s.replace(a, b)); print("ok")
