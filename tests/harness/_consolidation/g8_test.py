#!/usr/bin/env python3
"""G8 test (no LLM): files.created_by migration (add-only, reversible, backup first) + creator recording +
every audit finding names the creator. Run inside a throwaway root: python g8_test.py <root>"""
import sys, os, pathlib, json, subprocess, re
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
import workspace_mw as mw, workspace_audit as au
WS = root / "workspace"; fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
def sh(*a, inp=None, env=None):
    r = subprocess.run(list(a), capture_output=True, text=True, input=inp, env={**os.environ, **(env or {})}); return r.returncode, r.stdout, r.stderr
def schema():
    rc, out, _ = sh("pg_dump", "-s", "-d", "odin_core_con"); return [l for l in out.splitlines() if not l.startswith("--") and l.strip()]
def q(sql, a=()):
    c = mw._db(); cu = c.cursor(); cu.execute(sql, a); r = cu.fetchall(); c.close(); return r
def views():
    return q("SELECT viewname, definition FROM pg_views WHERE schemaname='public' ORDER BY 1")
def probes():   # the code's existing queries on files + every view
    return {"files": q("SELECT owner_type,owner_id,name,path,kind,description FROM files ORDER BY path"),
            "count": q("SELECT count(*) FROM files"),
            **{v: q(f"SELECT * FROM public.{v} ORDER BY 1") for v, _ in views()}}
def reset_cache(): mw._CB_CACHE.update(v=None, t=0.0)
MIG = str(root / "server" / "migrations" / "migrate_g8.sh"); BK = str(root / "_g8_backups")
P = "zoom-real-flow"
for _ in range(3): au.heal(force=True)
# ---- A: un-migrated database behaves as before ----
reset_cache()
check("A: column absent before migration", not mw.has_created_by())
r = mw.put_file("project", P, "code", "g8_pre.py", "x = 1\n", actor=("project", P))
check("A: door write works without the column", pathlib.Path(r["path"]).is_file())
iss = au.scan()
check("A: findings carry created_by = unknown when not migrated", all(i.get("created_by") in ("unknown", None) or isinstance(i.get("created_by"), dict) for i in iss))
s0, v0, p0 = schema(), views(), probes()
# ---- B: migration up (backup first, add-only) ----
rc, out, err = sh(MIG, "up", "odin_core_con", BK); print(out.strip())
bk = [p for p in pathlib.Path(BK).glob("*before_g8_up*.dump")]
check("B: backup taken before the change (non-empty)", rc == 0 and bk and bk[0].stat().st_size > 0, err)
s1 = schema(); reset_cache()
added = [l for l in s1 if l not in s0]; removed = [l for l in s0 if l not in s1]
check("B: schema diff = only the created_by column (+ its comment)", not removed and added and all("created_by" in l or l.strip() in (");",) for l in added), (added, removed))
check("B: views unchanged", views() == v0)
check("B: existing queries and views return identical results", probes() == p0)
check("B: every existing row is NULL (= unknown)", q("SELECT count(*) FROM files WHERE created_by IS NOT NULL")[0][0] == 0)
check("B: label for an existing row is 'unknown'", mw.creators_for([f"workspace/projects/{P}/code/g8_pre.py"])[f"workspace/projects/{P}/code/g8_pre.py"] == "unknown")
# ---- C: reversible ----
rc, out, err = sh(MIG, "down", "odin_core_con", BK)
check("C: down takes a backup too", rc == 0 and list(pathlib.Path(BK).glob("*before_g8_down*.dump")), err)
check("C: after down the schema is exactly as before", schema() == s0)
check("C: after down the data is identical", probes() == p0)
rc, out, err = sh(MIG, "up", "odin_core_con", BK); reset_cache()
check("C: up again works", rc == 0 and mw.has_created_by(), err)
# ---- D: the creator hook records a NEW file's agent; an edit never changes it ----
f = WS / "projects" / P / "code" / "g8_new.py"; f.write_text("def g8():\n    return 8\n")
hook = str(root / "server" / "creator_hook.py")
rc, out, err = sh(sys.executable, hook, inp=json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(f)}, "cwd": str(root)}),
                  env={"ODIN_MEMBER": "Fullstack", "ODIN_ACTOR_PID": P, "ODIN_ROOT": str(root)})
lab = mw.creators_for([f"workspace/projects/{P}/code/g8_new.py"])[f"workspace/projects/{P}/code/g8_new.py"]
check("D: hook recorded the creating agent", rc == 0 and not out and lab.startswith("Fullstack") and P in lab and "Write tool" in lab, (rc, out, err, lab))
f.write_text(f.read_text() + "# edit\n")
sh(sys.executable, hook, inp=json.dumps({"tool_name": "Edit", "tool_input": {"file_path": str(f)}}), env={"ODIN_MEMBER": "QA", "ODIN_ACTOR_PID": P, "ODIN_ROOT": str(root)})
mw.sync_row(f)
lab2 = mw.creators_for([f"workspace/projects/{P}/code/g8_new.py"])[f"workspace/projects/{P}/code/g8_new.py"]
check("D: a later edit (QA) and a re-sync keep the creator", lab2 == lab, lab2)
rc, out, err = sh(sys.executable, hook, inp="not json", env={"ODIN_ROOT": str(root)})
check("D: the hook never blocks and prints nothing on bad input", rc == 0 and not out and not err, (rc, out, err))
# ---- E: the door records its creator ----
os.environ["ODIN_MEMBER"] = "DevOps"
r = mw.put_file("project", P, "deploy", "g8_door.sh", "echo hi\n", actor=("project", P)); os.environ.pop("ODIN_MEMBER")
lab = mw.creators_for([str(pathlib.Path(r["path"]).relative_to(root))]).popitem()[1]
check("E: middleware door records the agent", lab.startswith("DevOps") and "middleware door" in lab, lab)
# ---- F: audit findings name the creator; moves keep it ----
loose = WS / "projects" / P / "loose_g8.py"; loose.write_text("y = 2\n")
sh(sys.executable, hook, inp=json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(loose)}}), env={"ODIN_MEMBER": "Backend", "ODIN_ACTOR_PID": P, "ODIN_ROOT": str(root)})
mis = [i for i in au.scan() if i["type"] == "misplaced" and "loose_g8" in i["path"]]
check("F: misplaced finding names the creating agent", mis and str(mis[0].get("created_by", "")).startswith("Backend"), mis)
h = au.heal(force=True)
moved = [a for a in h["actions"] if a["type"] == "misplaced" and "loose_g8" in a["path"]]
check("F: the audit log record names the creator", moved and str(moved[0].get("created_by", "")).startswith("Backend"), moved)
newp = [str(p.relative_to(root)) for p in (WS / "projects" / P).rglob("loose_g8.py")]
check("F: after the heal move the file keeps its creator", newp and mw.creators_for(newp)[newp[0]].startswith("Backend"), newp)
A, B = "revealer-6978", "hubspot-crm-operator"
body = "def g8dup():\n    return 'g8'\n"
fa = WS / "projects" / A / "code" / "g8dup_a.py"; fa.write_text(body)
sh(sys.executable, hook, inp=json.dumps({"tool_name": "Write", "tool_input": {"file_path": str(fa)}}), env={"ODIN_MEMBER": "Fullstack", "ODIN_ACTOR_PID": A, "ODIN_ROOT": str(root)})
fb = WS / "projects" / B / "code" / "g8dup_b.py"; fb.write_text(body)
dup = [i for i in au.scan() if i["type"] == "duplicate" and any("g8dup" in x for x in i["paths"])]
cb = dup[0].get("created_by") if dup else None
check("F: duplicate finding names the creator of each copy (known / unknown)", isinstance(cb, dict) and
      cb.get(f"workspace/projects/{A}/code/g8dup_a.py", "").startswith("Fullstack") and cb.get(f"workspace/projects/{B}/code/g8dup_b.py") == "unknown", cb)
every = au.scan()
check("F: EVERY finding has a created_by field", every and all("created_by" in i for i in every), [i["type"] for i in every if "created_by" not in i][:5])
# ---- G: hook registration ----
import claude_cli as cc
w = json.loads(pathlib.Path(cc._scope_settings_file(False)).read_text())
ro = json.loads(pathlib.Path(cc._scope_settings_file(True)).read_text())
check("G: write-enabled runs register the creator hook (PostToolUse)", "creator_hook.py" in json.dumps(w.get("hooks", {}).get("PostToolUse")))
check("G: read-only runs do not", "PostToolUse" not in ro.get("hooks", {}))
check("G: PreToolUse hooks unchanged in shape", "scope_hook.py" in json.dumps(w["hooks"]["PreToolUse"]))
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
