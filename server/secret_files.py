"""F-26 — the owner's secret-file rule (2026-10-12), in one place:

    "Never open or print any .env or .cred file, local or on the VM.
     To check a setting, only check that its name exists."

Used by the agent PreToolUse hook (secret_hook.py, on for every model run) and by the proposal check in
api_v2._outside_paths (local AND VM commands). Template files (.env.example / .sample / .template) hold no
values and are not secret (same list as the G9 write rule)."""
from __future__ import annotations
import os, re

RULE = ("Never open or print any .env or .cred file, local or on the VM. "
        "To check a setting, only check that its name exists.")
_TEMPLATES = (".env.example", ".env.sample", ".env.template")
_SECRET_TOKEN = re.compile(r"(?<![\w.-])(?:[\w./~$-]*/)?(\.env(?:\.[\w-]+)*|[\w-]*\.cred|\.backup-env)(?![\w.-])")
# allowed: count/quiet grep for ONE setting NAME (never prints a value)
_NAME_CHECK = re.compile(r"grep\s+(?:-[A-Za-z]*[cq][A-Za-z]*\s+)+(?:-[A-Za-z]+\s+)*['\"]?\^?[A-Za-z_][A-Za-z0-9_]*=?['\"]?\s+"
                         r"[\w./~$-]*(?:\.env(?:\.[\w-]+)*|[\w-]*\.cred|\.backup-env)(?![\w.-])")
# allowed: existence only
_EXISTS = re.compile(r"(?:test\s+-[ef]|\[\s+-[ef])\s+[\w./~$-]*(?:\.env(?:\.[\w-]+)*|[\w-]*\.cred|\.backup-env)(?![\w.-])")


def is_secret_name(name: str) -> bool:
    n = os.path.basename(str(name).strip().strip("'\""))
    if n in _TEMPLATES:
        return False
    return n == ".env" or n.startswith(".env.") or n == ".cred" or n.endswith(".cred") or n == ".backup-env"


def path_violation(path: str) -> str:
    return f"F-26: {RULE}" if path and is_secret_name(path) else ""


def command_violation(cmd: str) -> str:
    """'' when the command never opens/prints a secret file; otherwise the reason. Wrappers (ssh, az
    run-command, bash -c) are covered because the whole text is scanned, quotes included."""
    text = _NAME_CHECK.sub(" ", cmd or "")
    text = _EXISTS.sub(" ", text)
    for m in _SECRET_TOKEN.finditer(text):
        if is_secret_name(m.group(1)):
            return f"F-26: {RULE} (command touches {m.group(1)})"
    return ""
