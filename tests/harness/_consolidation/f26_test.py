#!/usr/bin/env python3
"""F-26 test (owner's secret-file rule, no LLM): "Never open or print any .env or .cred file, local or on the VM.
To check a setting, only check that its name exists." python f26_test.py <root>"""
import sys, os, pathlib, json, subprocess
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
hook = root / "server" / "secret_hook.py"
def run_hook(tool, ti):
    if not hook.exists(): return None
    r = subprocess.run([sys.executable, str(hook)], input=json.dumps({"tool_name": tool, "tool_input": ti}),
                       capture_output=True, text=True, env={**os.environ, "ODIN_ROOT": str(root)})
    return r.returncode
blocked = [("Read", {"file_path": "/x/proj/.env"}), ("Bash", {"command": "cat .env"}),
           ("Bash", {"command": "ssh mostafa@vm 'cat ~/bendcore/.env'"}), ("Bash", {"command": "grep STRIPE .env"}),
           ("Bash", {"command": "az vm run-command invoke --scripts 'cat ~/organics/.env.production'"}),
           ("Read", {"file_path": "workspace/shared/oth/.cred"}), ("Grep", {"pattern": "KEY", "path": "/p/.env"})]
allowed = [("Bash", {"command": "grep -c '^STRIPE_KEY=' .env"}), ("Bash", {"command": "test -f .env && echo present"}),
           ("Bash", {"command": "ssh mostafa@vm \"grep -q '^DB_URL=' ~/bendcore/.env && echo set\""}),
           ("Read", {"file_path": "/x/proj/.env.example"}), ("Grep", {"pattern": "^KEY=", "path": "/p/.env", "output_mode": "count"}),
           ("Bash", {"command": "node -e 'console.log(process.env.PORT)'"})]
rb = [run_hook(t, ti) for t, ti in blocked]; ra = [run_hook(t, ti) for t, ti in allowed]
check("1: the hook BLOCKS opening/printing .env/.cred (local, ssh, az run-command, Read, Grep)", rb == [2] * len(blocked), rb)
check("2: the hook ALLOWS name-only checks, existence checks, templates and process.env", ra == [0] * len(allowed), ra)
import claude_cli as cc
os.environ["ODIN_SCOPE_HOOK"] = "off"
def has_secret(path): return bool(path) and "secret_hook.py" in pathlib.Path(path).read_text()
check("3: secret guard is in EVERY settings variant (scope hook off/on, read-only, no-VM)",
      has_secret(cc._scope_settings_file(False)) and has_secret(cc._scope_settings_file(True))
      and has_secret(cc._scope_settings_file(False, True)) and (os.environ.update(ODIN_SCOPE_HOOK="enforce") or True)
      and has_secret(cc._scope_settings_file(False)) and has_secret(cc._scope_settings_file(True)))
cap = []
class _R: stdout = '{"result": "ok", "session_id": "s"}'; stderr = ""; returncode = 0
cc.available = lambda: True; cc.paid_auth_problem = lambda: ""
_orig = cc.subprocess.run
cc.subprocess.run = lambda cmd, **k: (cap.append(cmd), _R())[1]
try:
    cc.ClaudeCLIBrain().respond("hi"); cc.ClaudeCLIBrain().respond_with_session("hi")
finally:
    cc.subprocess.run = _orig
check("4: plain respond() and respond_with_session() runs carry the secret guard", len(cap) == 2 and all(
      "--settings" in c and has_secret(c[c.index("--settings") + 1]) for c in cap), [c[-4:] for c in cap])
src = (root / "server" / "claude_cli.py").read_text()
check("5: stream runs without an actor still get the guard", "runs with no other hook still get the secret-file guard" in src)
import api_v2
bad1 = api_v2._outside_paths("revealer-6978", {"commands": [{"cmd": "cat ~/bendcore/.env", "where": "vm"}]})
bad2 = api_v2._outside_paths("revealer-6978", {"commands": [{"cmd": "grep -c '^STRIPE_KEY=' ~/bendcore/.env", "where": "vm"}]})
bad3 = api_v2._outside_paths("revealer-6978", {"commands": [{"cmd": "head -2 workspace/shared/oth/.cred", "where": "local"}]})
check("6: a proposal that reads a .env on the VM is refused; a name-only check is not",
      any("F-26" in b for b in bad1) and not any("F-26" in b for b in bad2), (bad1, bad2))
check("7: a proposal that prints the local .cred is refused", any("F-26" in b for b in bad3), bad3)
api = (root / "server" / "api_v2.py").read_text()
rule = "Never open or print any .env or .cred file, local or on the VM"
check("8: agents get the rule in their proposal rules", rule in getattr(api_v2, "PROPOSE_RULES", ""))
check("9 (CH1-2): CTO reviews apply the rule the SAME way (name-only check is correct, reading is Needs fix)",
      "Apply it the SAME way every time" in api and "never 'Needs fix:' for not reading the file" in api)
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
