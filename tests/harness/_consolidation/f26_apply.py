"""F-26 edits — idempotent."""
import pathlib
def edit(p, old, new, marker):
    s = pathlib.Path(p).read_text()
    if marker in s: print('skip', marker); return
    assert s.count(old) == 1, (p, old[:70], s.count(old))
    pathlib.Path(p).write_text(s.replace(old, new)); print('ok', p, marker)
C = 'server/claude_cli.py'
edit(C, '''_CREATOR_HOOK = _HERE / "creator_hook.py"   # G8: PostToolUse — records which agent created a new file
''', '''_CREATOR_HOOK = _HERE / "creator_hook.py"   # G8: PostToolUse — records which agent created a new file

_SECRET_HOOK = _HERE / "secret_hook.py"     # F-26: never open/print a .env/.cred file — EVERY run, every mode


def _secret_entry(py: str) -> dict:
    return {"matcher": "Read|Bash|Grep", "hooks": [{"type": "command", "command": f"{py} {str(_SECRET_HOOK)}"}]}


def _secret_only_settings_file() -> str:
    """F-26: settings with only the secret-file guard (runs that have no other hook)."""
    py = shutil.which("python3") or "python3"
    f = _HERE / ".secret-settings.json"
    try:
        f.write_text(json.dumps({"hooks": {"PreToolUse": [_secret_entry(py)]}}))
        return str(f)
    except Exception:
        return ""
''', '_SECRET_HOOK = _HERE')
edit(C, '''        cfg = {
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Bash",''', '''        cfg = {
            "hooks": {
                "PreToolUse": [
                    _secret_entry(shutil.which('python3') or 'python3'),   # F-26
                    {"matcher": "Bash",''', '# F-26\n                    {"matcher": "Bash",')
edit(C, '''        if not no_vm:
            return _readonly_settings_file() if readonly else ""''', '''        if not no_vm:
            return _readonly_settings_file() if readonly else _secret_only_settings_file()   # F-26 stays on''',
     '_secret_only_settings_file()   # F-26 stays on')
edit(C, '''    f = _HERE / ((".scope-settings-ro" if readonly else ".scope-settings") + ("-novm" if no_vm else "") + ".json")''',
'''    pre.insert(0, _secret_entry(py))   # F-26: the secret-file rule is first in every run
    f = _HERE / ((".scope-settings-ro" if readonly else ".scope-settings") + ("-novm" if no_vm else "") + ".json")''',
     'pre.insert(0, _secret_entry(py))')
edit(C, '''            if _sf and (_actor or no_vm):
                cmd += ["--settings", _sf]''', '''            if _sf and (_actor or no_vm):
                cmd += ["--settings", _sf]
            else:   # F-26: runs with no other hook still get the secret-file guard
                _ss = _secret_only_settings_file()
                if _ss:
                    cmd += ["--settings", _ss]''', 'runs with no other hook still get')
edit(C, '''            "--disallowedTools", "AskUserQuestion",  # headless: never block on a question
        ] + _model_flags(model)''', '''            "--disallowedTools", "AskUserQuestion",  # headless: never block on a question
        ] + _model_flags(model)
        _ss = _secret_only_settings_file()   # F-26
        if _ss:
            cmd += ["--settings", _ss]''', '] + _model_flags(model)\n        _ss = _secret_only_settings_file()')
edit(C, '''        cmd = ["claude", "-p", prompt, "--output-format", "json", "--allowedTools", tools,
               "--disallowedTools", "AskUserQuestion"]
        if session_id:''', '''        cmd = ["claude", "-p", prompt, "--output-format", "json", "--allowedTools", tools,
               "--disallowedTools", "AskUserQuestion"]
        _ss = _secret_only_settings_file()   # F-26
        if _ss:
            cmd += ["--settings", _ss]
        if session_id:''', '"AskUserQuestion"]\n        _ss = _secret_only_settings_file()')
A = 'server/api_v2.py'
edit(A, '''    "KEYS: never write or edit .cred or .env files, and never put a key value in a file or command. If you need a "''',
'''    "SECRET FILES (owner rule F-26): Never open or print any .env or .cred file, local or on the VM. To check a "
    "setting, only check that its name exists (e.g. grep -c '^NAME=' .env).\\n"
    "KEYS: never write or edit .cred or .env files, and never put a key value in a file or command. If you need a "''',
     'SECRET FILES (owner rule F-26)')
edit(A, '''    for c in prop.get("commands") or []:
        if (c or {}).get("where") == "vm":
            continue
        cmd = str(c.get("cmd", "")).split("<<")[0].split("\\n")[0]''', '''    for c in prop.get("commands") or []:
        try:   # F-26: local AND VM commands — never open or print a .env/.cred file
            import secret_files as _sfl
            _sv = _sfl.command_violation(str((c or {}).get("cmd", "")))
        except Exception:
            _sv = ""
        if _sv:
            bad.append(f"command `{str(c.get('cmd', '')).strip()[:80]}` — {_sv}")
            continue
        if (c or {}).get("where") == "vm":
            continue
        cmd = str(c.get("cmd", "")).split("<<")[0].split("\\n")[0]''', 'F-26: local AND VM commands')
edit(A, '''                "Then END with exactly ONE line: VERDICT: {\\"verdict\\": \\"PASSED\\" | \\"NOT_DONE\\" | "''',
'''                "SECRET FILES (owner rule F-26): Never open or print any .env or .cred file, local or on the VM; to "
                "check a setting, only check that its name exists. Apply it the SAME way every time: work that only "
                "checked a setting's NAME followed the rule (never 'Needs fix:' for not reading the file); work that "
                "opened or printed a .env/.cred is 'Needs fix:'; never ask an agent to read one.\\n"
                "Then END with exactly ONE line: VERDICT: {\\"verdict\\": \\"PASSED\\" | \\"NOT_DONE\\" | "''',
     'Apply it the SAME way every time')
