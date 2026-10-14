#!/usr/bin/env python3
"""door_cli.py — the agents' SANCTIONED door (P2). The only way an agent writes outside its own project:
  promote <path-inside-your-project>      → workspace_mw.promote_to_shared (the same route the audit uses)
  put <subfolder> <name> <source-file>    → workspace_mw.put_file into YOUR project (slot routed + DB synced)
The actor is taken from ODIN_ACTOR_PID (set by the engine), never from the arguments."""
import sys, os, json, pathlib
ROOT = pathlib.Path(os.environ.get("ODIN_ROOT") or pathlib.Path(__file__).resolve().parent.parent)
sys.path.insert(0, str(ROOT / "server"))
import workspace_mw as mw


def main(a):
    actor = os.environ.get("ODIN_ACTOR_PID", "").strip()
    if not actor or len(a) < 2:
        print(__doc__); return 2
    if a[0] == "promote":
        p = pathlib.Path(a[1]).resolve()
        own = (ROOT / "workspace" / "projects" / actor).resolve()
        if own not in p.parents:
            print(json.dumps({"ok": False, "error": "you can only promote a file from your own project"})); return 1
        r = mw.promote_to_shared(str(p))
        print(json.dumps({"ok": True, **r}, default=str)); return 0
    if a[0] == "put" and len(a) >= 4:
        content = pathlib.Path(a[3]).read_text()
        r = mw.put_file("project", actor, a[1], a[2], content, actor=("project", actor))
        print(json.dumps({"ok": True, **r}, default=str)); return 0
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
