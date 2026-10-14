#!/usr/bin/env python3
"""F-37: when the audit switch is OFF the audit only detects and reports; it never moves, deletes or rewrites.
Only when it is ON may it heal (the timer sentinel and the 'Run now' button included)."""
import pathlib, sys
R = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
def sub(path, old, new, count=1):
    p = R / path; s = p.read_text()
    assert s.count(old) == count, (path, old[:70], s.count(old)); p.write_text(s.replace(old, new))
AU = "server/workspace_audit.py"
sub(AU, '''    try:
        heal(force=True)
    except Exception:
        pass
    iss = scan()''', '''    # F-37: heal ONLY when the owner's audit switch is ON; when OFF the sentinel detects and reports only
    if config().get("enabled"):
        try:
            heal(force=True)
        except Exception:
            pass
    iss = scan()''')
sub(AU, '''    import workspace_mw as mw
    dec = should_run()
    if not force and not dec["should_run"]:
        return {"ran": False, "reason": "debounced", **dec}''', '''    import workspace_mw as mw
    dec = should_run()
    if not config().get("enabled"):
        # F-37: switch OFF = report only. force (the 'Run now' button / sentinel) never overrides the switch.
        iss = scan()
        return {"ran": False, "reason": "audit switched OFF — report only, nothing changed",
                "healed": 0, "flagged": len(iss), "issues": iss, "actions": [], **dec}
    if not force and not dec["should_run"]:
        return {"ran": False, "reason": "debounced", **dec}''')
print("F-37 applied")
