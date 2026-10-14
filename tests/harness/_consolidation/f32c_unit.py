#!/usr/bin/env python3
"""F-32c unit checks (no model cost). Usage: f32c_unit.py <server_dir>"""
import sys, os, json, subprocess, pathlib, importlib
srv = pathlib.Path(sys.argv[1]).resolve(); hook = srv / "novm_hook.py"; fails = []
def check(n, c):
    print(("PASS " if c else "FAIL ") + n)
    if not c: fails.append(n)
def run(cmd, on=True):
    env = dict(os.environ, ODIN_NO_VM="1" if on else "0", ODIN_ROOT=str(srv.parent))
    p = subprocess.run([sys.executable, str(hook)], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": cmd}}),
                       text=True, capture_output=True, env=env)
    return p.returncode
BLOCK = ["ssh mostafa@52.180.154.225 uptime", "az vm run-command invoke -g DJANGO-PROJECT -n django-vm --scripts uptime",
         "sshpass -p x ssh host", "scp a host:/tmp", "rsync -avn dist/ mostafa@vm:/home/mostafa/app",
         "cd x && az network nsg rule update --name y", "python3 -c 'import deploy_ssh; deploy_ssh.ssh_exec(\"ls\")'",
         "curl -s https://52.180.154.225/"]
ALLOW = ["python3 -m unittest -v test_calc", "ls -R", "rsync -a dist/ build/", "echo 'deploy notes' > notes.md",
         "grep -rn azure_config docs/", "npm run build"]
for c in BLOCK: check(f"blocked when no VM access: {c[:60]}", run(c) == 2)
for c in ALLOW: check(f"allowed (local): {c[:60]}", run(c) == 0)
check("hook inactive when the run IS clearly about the VM (ODIN_NO_VM unset)", run(BLOCK[0], on=False) == 0)
sys.path.insert(0, str(srv)); cc = importlib.import_module("claude_cli")
for ro in (False, True):
    f = cc._scope_settings_file(ro, True); d = json.loads(pathlib.Path(f).read_text())
    cmds = [h["command"] for e in d["hooks"]["PreToolUse"] for h in e["hooks"]]
    check(f"settings (readonly={ro}) register the no-VM hook first", "novm_hook.py" in cmds[0])
os.environ["ODIN_SCOPE_HOOK"] = "off"
f = cc._scope_settings_file(False, True)
check("no-VM hook stays ON even when the scope hook is off", bool(f) and "novm_hook.py" in pathlib.Path(f).read_text())
check("readonly flags pass no_vm through", "novm" in " ".join(cc._tool_flags(True, True)))
src = (srv / "api_v2.py").read_text()
check("api: gated engine call passes no_vm=not vm_intent", "readonly=ro, no_vm=not vm_intent)" in src or "readonly=ro, no_vm=not vm_intent," in src)  # G8 added member= after it
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
