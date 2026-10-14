#!/usr/bin/env python3
"""G12 (owner decision): EasyPost — and any company-level agent that is also a catalogue ROLE — is RECOMMENDED per
project like any role and added only when the owner approves it; it is never auto-added to every project.
Company agents that are not catalogue roles keep the existing 'native to every project' behaviour."""
import pathlib, sys
R = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
def sub(path, old, new, count=1):
    p = R / path; s = p.read_text()
    assert s.count(old) == count, (path, old[:70], s.count(old)); p.write_text(s.replace(old, new))
sub("server/projects.py", '''    # company-level agents are "native" to every project — auto-add them too
    for ca in agents_registry.list_company_agents():
        agents_registry.register_agent(''', '''    # company-level agents are "native" to every project — auto-add them too.
    # G12 (owner decision): an agent that is also a catalogue ROLE (e.g. EasyPost) is NOT native — it is
    # recommended per project like any role and added only when the owner approves it (it is in `members`).
    _chosen = {str(m.get("name", "") if isinstance(m, dict) else m).lower() for m in (members or [])}
    for ca in agents_registry.list_company_agents():
        if member_def(ca["name"]) and ca["name"].lower() not in _chosen:
            continue
        agents_registry.register_agent(''')
print("G12 applied")
