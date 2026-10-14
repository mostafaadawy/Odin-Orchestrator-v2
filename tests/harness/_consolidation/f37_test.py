#!/usr/bin/env python3
"""F-37 test (no LLM): audit switch OFF = detect + report only, nothing changes; ON = heals. python f37_test.py <root>"""
import sys, os, pathlib, json, hashlib, time
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
import workspace_mw as mw, workspace_audit as au
WS = root / "workspace"; fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
def snap():
    out = {}
    for p in WS.rglob("*"):
        if p.is_file() and not ({"logs", "history"} & set(p.relative_to(WS).parts[:1])) and "notifications" not in str(p):
            out[str(p.relative_to(WS))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out
def rows():
    c = mw._db(); cu = c.cursor(); cu.execute("SELECT path, size_bytes FROM files ORDER BY path"); r = cu.fetchall()
    cu.execute("SELECT count(*) FROM dependencies"); d = cu.fetchone()[0]; c.close(); return r, d
A, C = "revealer-6978", "zoom-real-flow"
for _ in range(3): au.heal(force=True)
# make one of each fixable violation
(WS/"projects"/A/"loose_f37.py").write_text("x = 1\n")                                   # misplaced + unindexed
body = "def f37():\n    return 37\n"
mw.put_file("project", A, "code", "dup_f37.py", body, actor=("project", A)); time.sleep(1.1)
(WS/"projects"/C/"code"/"dup_f37.py").write_text(body)                                   # identical duplicate
(WS/"projects"/C/"code"/"ref_f37.py").write_text(f"exec(open('workspace/projects/{A}/code/dup_f37.py').read())\n")  # foreign ref
au.set_config(enabled=False)
s0, r0 = snap(), rows(); n0 = len(mw.change_log())
h = au.heal(force=True)                       # the 'Run now' button
sen = au.sentinel(notify=False)               # the 15-minute timer
types = {i["type"] for i in sen["issues"] if "f37" in json.dumps(i)}
check("OFF: issues are detected and reported", {"misplaced", "duplicate", "foreign-ref"} <= types and h.get("flagged", 0) > 0, types)
check("OFF: 'Run now' (force) heals nothing", not h["ran"] and h["healed"] == 0 and "OFF" in h["reason"], h.get("reason"))
check("OFF: no file moved, deleted or rewritten", snap() == s0, sorted(set(snap()) ^ set(s0))[:5])
check("OFF: no database row changed", rows() == r0)
check("OFF: no automatic change logged", len(mw.change_log()) == n0)
au.set_config(enabled=True)
h2 = au.heal(force=True)
check("ON: the audit heals again", h2["ran"] and h2["healed"] > 0)
check("ON: misplaced file moved, duplicate promoted", not (WS/"projects"/A/"loose_f37.py").exists() and (WS/"shared"/"utils"/"dup_f37.py").is_file())
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
