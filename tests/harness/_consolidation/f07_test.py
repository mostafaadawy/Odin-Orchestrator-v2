#!/usr/bin/env python3
"""F-07 test (no LLM): files written by an approved apply are indexed at once. python f07_test.py <root>"""
import sys, os, pathlib, json, time, subprocess
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
import workspace_mw as mw, workspace_audit as au
WS = root / "workspace"; fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
def unindexed(tag): return [i["path"] for i in au.scan() if i["type"] == "unindexed" and tag in i["path"]]
P = "zoom-real-flow"; code = WS/"projects"/P/"code"
for _ in range(3): au.heal(force=True)
mw._CB_CACHE.update(v=None, t=0.0)
# 1) un-migrated DB: an agent's Write of a NEW file is indexed by the hook immediately
f1 = code/"f07_write.py"; f1.write_text("a = 1\n")
subprocess.run([sys.executable, str(root/"server"/"creator_hook.py")], input=json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(f1)}}),
               text=True, env={**os.environ, "ODIN_ROOT": str(root), "ODIN_MEMBER": "Fullstack", "ODIN_ACTOR_PID": P})
check("F07-1: (no migration) a file written by the agent's Write tool is indexed at once", mw.get_creator(f1)[0])
# 2) the apply's LOCAL COMMANDS create/modify files that are not in the proposal's file list
import api_v2
ok = hasattr(api_v2, "_index_changed_since")
old = code/"f07_old.py"; old.write_text("o = 0\n"); mw.sync_row(old); os.utime(old, (time.time()-3600, time.time()-3600)); mw.sync_row(old)
time.sleep(2.5); t0 = time.time(); time.sleep(0.2)
f2 = code/"f07_by_command.py"; f2.write_text("b = 2\n")                        # e.g. made by `npm init` / a script
f3 = WS/"projects"/P/"deploy"/"f07_generated.json"; f3.parent.mkdir(exist_ok=True); f3.write_text("{}\n")
rep = api_v2._index_changed_since(P, str(code), t0, creator_agent="DevOps", approval_id="abc123") if ok else {}
check("F07-2: files created by the apply's commands are indexed right after the apply", ok and mw.get_creator(f2)[0] and mw.get_creator(f3)[0], rep)
check("F07-3: nothing from these appears as 'unindexed' in the audit", ok and not unindexed("f07_"), unindexed("f07_"))
check("F07-4: files older than the apply are not touched", ok and rep.get("indexed") == 2, rep)
# 3) with the G8 column: a new file from an approved apply records its agent
subprocess.run([str(root/"server/migrations/migrate_g8.sh"), "up", "odin_core_con", str(root/"_bk")], capture_output=True); mw._CB_CACHE.update(v=None, t=0.0)
t1 = time.time(); time.sleep(0.2); f4 = code/"f07_after_mig.py"; f4.write_text("c = 3\n")
if ok: api_v2._index_changed_since(P, str(code), t1, creator_agent="DevOps", approval_id="abc123")
lab = mw.creators_for([str(f4.relative_to(root))]).popitem()[1]
check("F07-5: (migrated) the new file records the approved proposal's agent", ok and lab.startswith("DevOps") and "abc123" in lab, lab)
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
