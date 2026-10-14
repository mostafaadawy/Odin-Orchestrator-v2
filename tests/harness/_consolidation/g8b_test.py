#!/usr/bin/env python3
"""G8 follow-up + ZERO-COST guard test (no LLM). Run inside a throwaway root (column migrated):
python g8b_test.py <root>"""
import sys, os, pathlib, json, time, tempfile, subprocess
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
subprocess.run([str(root / "server/migrations/migrate_g8.sh"), "up", "odin_core_con", str(root / "_g8_backups")], capture_output=True)
import claude_cli as cc, workspace_mw as mw
mw._CB_CACHE.update(v=None, t=0.0)
# ---- ZERO-COST guard ----
cc._PAID_CACHE.update(t=0.0)
check("Z1: the real login is the plan login (no paid route)", cc.paid_auth_problem() == "", cc.paid_auth_problem())
for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL", "CLAUDE_CODE_USE_BEDROCK"):
    os.environ[var] = "x-test-not-a-real-value"; cc._PAID_CACHE.update(t=0.0)
    msg = cc.paid_auth_problem(); os.environ.pop(var)
    check(f"Z2: {var} set -> refused, value never shown", var in msg and "x-test" not in msg, msg)
fh = pathlib.Path(tempfile.mkdtemp()); (fh / ".claude.json").write_text(json.dumps({"primaryApiKey": "sk-test", "oauthAccount": {"hasExtraUsageEnabled": True}}))
old = os.environ["HOME"]; os.environ["HOME"] = str(fh); cc._PAID_CACHE.update(t=0.0)
msg = cc.paid_auth_problem(); os.environ["HOME"] = old
check("Z3: API key in config or paid extra usage -> refused", "API key" in msg and "extra usage" in msg and "sk-test" not in msg, msg)
os.environ["ANTHROPIC_API_KEY"] = "x"; cc._PAID_CACHE.update(t=0.0)
ev = list(cc.ClaudeCLIBrain().stream_session("hello"))
os.environ.pop("ANTHROPIC_API_KEY"); cc._PAID_CACHE.update(t=0.0)
check("Z4: the engine does NOT run when a paid route is configured", len(ev) == 1 and "ZERO-COST RULE" in ev[0].get("text", ""), ev)
# ---- step attribution only for files the member really created ----
import api_v2
P = "zoom-real-flow"; WS = root / "workspace" / "projects" / P
t0 = time.time() - 1
agents = WS / "agents.json"
if agents.exists():
    mw.sync_row(agents); agents.write_text(agents.read_text())       # pre-existing file rewritten during the step
newf = WS / "code" / "g8b_bash_made.py"; newf.write_text("z = 3\n")  # created during the step (e.g. by Bash)
pyc = WS / "code" / "__pycache__" / "x.cpython-312.pyc"; pyc.parent.mkdir(exist_ok=True); pyc.write_bytes(b"\0")
api_v2._attribute_step_files(P, "Fullstack", t0, str(WS / "code"))
cr = mw.creators_for([f"workspace/projects/{P}/code/g8b_bash_made.py", f"workspace/projects/{P}/agents.json"])
check("S1: a file created during the step gets the member (inferred)", cr[f"workspace/projects/{P}/code/g8b_bash_made.py"].startswith("Fullstack") and "inferred" in cr[f"workspace/projects/{P}/code/g8b_bash_made.py"], cr)
check("S2: a pre-existing file rewritten in the step stays unknown", not agents.exists() or cr[f"workspace/projects/{P}/agents.json"] == "unknown", cr)
check("S3: __pycache__/.pyc ignored", mw.get_creator(pyc)[0] is False)
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
