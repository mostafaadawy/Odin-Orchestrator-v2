#!/usr/bin/env python3
"""F-32c (found by S10 r1): with no firewall refresh, a pre-authorized agent still ran `az vm run-command` with its
own tools (blocked by the shims here; in v1 it would reach the VM through Azure). Fail safe: when the run is not
CLEARLY asked for VM work, the agent's engine gets a PreToolUse hook (server/novm_hook.py) that blocks every
VM/Azure command, in read-only and write-enabled runs alike."""
import pathlib, sys, shutil
R = pathlib.Path(__file__).resolve().parent.parent
cli = R / "server/claude_cli.py"; api = R / "server/api_v2.py"
c = cli.read_text(); a = api.read_text()
if "F-32c" in c: sys.exit("already applied")
def rep(txt, old, new, name):
    assert txt.count(old) == 1, f"anchor {name}: {txt.count(old)}"
    return txt.replace(old, new)
shutil.copy(R / "_consolidation/novm_hook.py", R / "server/novm_hook.py")
c = rep(c, '''def _scope_settings_file(readonly: bool) -> str:''', '''_NOVM_HOOK = _HERE / "novm_hook.py"


def _scope_settings_file(readonly: bool, no_vm: bool = False) -> str:''', "sfsig")
c = rep(c, '''    if os.environ.get("ODIN_SCOPE_HOOK", "enforce").lower() == "off":
        return _readonly_settings_file() if readonly else ""
    py = shutil.which("python3") or "python3"
    pre = [{"matcher": "Write|Edit|MultiEdit|NotebookEdit|Bash",
            "hooks": [{"type": "command", "command": f"{py} {str(_SCOPE_HOOK)}"}]}]
    if readonly:
        pre.insert(0, {"matcher": "Bash", "hooks": [{"type": "command", "command": f"{py} {str(_RO_HOOK)}"}]})
    f = _HERE / (".scope-settings-ro.json" if readonly else ".scope-settings.json")''',
'''    py = shutil.which("python3") or "python3"
    if os.environ.get("ODIN_SCOPE_HOOK", "enforce").lower() == "off":
        if not no_vm:
            return _readonly_settings_file() if readonly else ""
        pre = []   # F-32c: the no-VM guard is a SAFETY rule and stays on even when the scope hook is off
    else:
        pre = [{"matcher": "Write|Edit|MultiEdit|NotebookEdit|Bash",
                "hooks": [{"type": "command", "command": f"{py} {str(_SCOPE_HOOK)}"}]}]
    if readonly:
        pre.insert(0, {"matcher": "Bash", "hooks": [{"type": "command", "command": f"{py} {str(_RO_HOOK)}"}]})
    if no_vm:   # F-32c (fail safe): block every VM/Azure command when the run was not clearly asked for VM work
        pre.insert(0, {"matcher": "Bash", "hooks": [{"type": "command", "command": f"{py} {str(_NOVM_HOOK)}"}]})
    f = _HERE / ((".scope-settings-ro" if readonly else ".scope-settings") + ("-novm" if no_vm else "") + ".json")''', "sfbody")
c = rep(c, '''def _tool_flags(readonly: bool) -> list:''', '''def _tool_flags(readonly: bool, no_vm: bool = False) -> list:''', "tfsig")
c = rep(c, '''        sf = _scope_settings_file(True)''', '''        sf = _scope_settings_file(True, no_vm)''', "tfro")
c = rep(c, '''                       cwd: str | None = None, readonly: bool = False, model: str | None = None):''',
           '''                       cwd: str | None = None, readonly: bool = False, model: str | None = None,
                       no_vm: bool = False):''', "sssig")
c = rep(c, '''+ _tool_flags(readonly) + _model_flags(model)''', '''+ _tool_flags(readonly, no_vm) + _model_flags(model)''', "ssflags")
c = rep(c, '''        if not readonly:
            _sf = _scope_settings_file(False)
            if _sf and _actor:
                cmd += ["--settings", _sf]''', '''        if no_vm:   # F-32c: the no-VM hook reads this flag
            _env["ODIN_NO_VM"] = "1"
        if not readonly:
            _sf = _scope_settings_file(False, no_vm)
            if _sf and (_actor or no_vm):
                cmd += ["--settings", _sf]''', "ssenv")
a = rep(a, '''def _engine_stream(text: str, lang: str, session_id: str, model: str, cwd: str | None = None,
                   readonly: bool = False):''', '''def _engine_stream(text: str, lang: str, session_id: str, model: str, cwd: str | None = None,
                   readonly: bool = False, no_vm: bool = False):''', "essig")
a = rep(a, '''                    text, lang, session_id or None, cwd=cwd, readonly=readonly, model=model)''',
           '''                    text, lang, session_id or None, cwd=cwd, readonly=readonly, model=model, no_vm=no_vm)''', "escall")
a = rep(a, '''            for evd in _engine_stream(p, "en", None, model, cwd=folder or None, readonly=ro):''',
           '''            # F-32c: no VM/Azure commands at all unless this run was CLEARLY asked for VM work
            for evd in _engine_stream(p, "en", None, model, cwd=folder or None, readonly=ro, no_vm=not vm_intent):''', "gated")
cli.write_text(c); api.write_text(a); print("F-32c applied")
