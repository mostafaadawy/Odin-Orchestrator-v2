#!/usr/bin/env python3
"""F-26 PreToolUse hook (Read | Bash | Grep), registered for EVERY model run: blocks opening or printing a
.env/.cred file. Checking that a setting's NAME exists (grep -c / grep -q '^NAME=' .env) is allowed."""
import json, sys, os, pathlib, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import secret_files as sf


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        sys.exit(0)
    tool = data.get("tool_name", ""); ti = data.get("tool_input", {}) or {}
    why = ""
    if tool == "Read":
        why = sf.path_violation(ti.get("file_path", ""))
    elif tool == "Grep":
        if ti.get("output_mode") != "count":
            why = sf.path_violation(ti.get("path", "")) or sf.path_violation(ti.get("glob", "") or "")
    elif tool == "Bash":
        why = sf.command_violation(ti.get("command", "") or "")
    if not why:
        sys.exit(0)
    try:
        root = pathlib.Path(os.environ.get("ODIN_ROOT") or pathlib.Path(__file__).resolve().parent.parent)
        (root / "workspace" / "history").mkdir(parents=True, exist_ok=True)
        with open(root / "workspace" / "history" / "secret-hook.jsonl", "a") as f:
            f.write(json.dumps({"ts": time.time(), "actor": os.environ.get("ODIN_ACTOR_PID", ""),
                                "member": os.environ.get("ODIN_MEMBER", ""), "tool": tool, "blocked": why}) + "\n")
    except Exception:
        pass
    print(f"[Odin secret-file rule] BLOCK: {why}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
