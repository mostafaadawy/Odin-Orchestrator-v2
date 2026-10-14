#!/usr/bin/env python3
"""G6b test (no LLM): every automatic rewrite is logged (file, old, new, time, reason) and one command reverts it.
Run inside a throwaway root: python g6b_test.py <root>"""
import sys, os, pathlib, json, hashlib, subprocess
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
import workspace_mw as mw, workspace_audit as au
WS = root / "workspace"; fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{info}]" if info and not c else ""))
    if not c: fails.append(n)
def snap():
    out = {}
    for base in (WS / "projects", WS / "shared"):
        for p in base.rglob("*"):
            if p.is_file() and not ({"data", "history", "logs"} & set(p.relative_to(WS).parts[2:3])):
                out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out
def db(q, a=()):
    c = mw._db(); cu = c.cursor(); cu.execute(q, a); r = cu.fetchall(); c.close(); return r
def cli(*a):
    r = subprocess.run([sys.executable, "server/rewrite_log.py", *a], capture_output=True, text=True); return r.returncode, r.stdout + r.stderr
A, B = "revealer-6978", "hubspot-crm-operator"
def setup(tag):
    body = f"def helper_{tag}():\n    return '{tag}'\n"
    mw.put_file("project", A, "code", f"helper_{tag}.py", body, actor=("project", A))
    (WS/"projects"/B/"code"/f"dup_test_{tag}.py").write_text(body)
    (WS/"projects"/B/"code"/f"use_{tag}.py").write_text(f"# B uses it\nexec(open('workspace/projects/{A}/code/helper_{tag}.py').read())\n")
    (WS/"projects"/A/"code"/f"main_{tag}.py").write_text(f"# A main\nexec(open('workspace/projects/{A}/code/helper_{tag}.py').read())\n")
    for p in (WS/"projects"/B/"code").glob(f"*_{tag}.py"): mw.sync_row(p)
    for p in (WS/"projects"/A/"code").glob(f"*_{tag}.py"): mw.sync_row(p)
def dup_batch(h, tag):
    return [a.get("batch") for a in h["actions"] if a["type"] == "duplicate" and tag in json.dumps(a)]
for _ in range(4): au.heal(force=True)          # settle the baseline copy first
# ---- 1: log content ----
setup("g6b"); before = snap()
h = au.heal(force=True); b = dup_batch(h, "g6b")
check("heal ran one duplicate action with a batch id", len(b) == 1 and b[0], b)
b = b[0] if b else ""
rw = [d for d in mw.change_log(b) if d["kind"] == "ref-rewrite"]
files = {d["file"] for d in rw}
check("both referrers' rewrites are logged", {f"workspace/projects/{B}/code/use_g6b.py", f"workspace/projects/{A}/code/main_g6b.py"} <= files, files)
check("each entry has file, old path, new path, time, reason",
      rw and all(d.get("file") and d.get("old") and d.get("new") and d.get("ts") and d.get("reason") for d in rw))
check("old/new paths are the real ones", all(d["old"].startswith("(") or d["old"].endswith("helper_g6b.py") and d["new"].startswith("shared/") for d in rw), [(d['old'], d['new']) for d in rw])
rc, out = cli("list", "--batch", b)
check("CLI list shows the batch", rc == 0 and "use_g6b.py" in out and "MOVED" in out and "REMOVED identical copy" in out, out[-400:])
print(out)
# ---- 2: one-command revert restores the exact pre-heal state ----
rc, out = cli("revert", b); print(out)
after = snap()
diff = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
check("revert: every file byte-identical to before the heal", not diff, diff[:6])
check("revert: shared copy gone", not any("g6b" in p.name for p in (WS / "shared").rglob("*")))
check("revert: no dependency rows left for it", db("SELECT count(*) FROM dependencies WHERE shared_capability_id LIKE %s", ("%g6b%",))[0][0] == 0)
rows = {r[0] for r in db("SELECT path FROM files WHERE path LIKE %s", ("%g6b%",))}
check("revert: DB rows mirror disk (originals in, shared out)",
      f"workspace/projects/{A}/code/helper_g6b.py" in rows and f"workspace/projects/{B}/code/dup_test_g6b.py" in rows and not any("shared/" in r for r in rows), rows)
check("revert: references resolve again (old paths exist)", (WS/"projects"/A/"code"/"helper_g6b.py").is_file())
h2 = au.heal(force=True)
fx = [a["fix"] for a in h2["actions"] if "g6b" in json.dumps(a) and a["type"] in ("duplicate", "foreign-ref")]
check("audit does not redo a reverted action (held, flagged)", fx and all("held" in f for f in fx) and snap() == after, fx)
rc, out = cli("revert", b)
check("revert twice is refused", rc != 0 and "already reverted" in out)
rc, out = cli("revert", "nosuchbatch0")
check("unknown batch is refused", rc != 0)
rc, out = cli("release", b); h3 = au.heal(force=True)
check("release: the audit may fix it again", rc == 0 and any(a["type"] == "duplicate" and "g6b" in json.dumps(a) and "held" not in a["fix"] for a in h3["actions"]))
# ---- 3: a file edited after the rewrite is NOT overwritten ----
setup("g6e"); h = au.heal(force=True); b3 = (dup_batch(h, "g6e") or [""])[0]
ed = WS/"projects"/B/"code"/"use_g6e.py"; ed.write_text(ed.read_text() + "# owner edit\n")
rc, out = cli("revert", b3); r = json.loads(out)
check("edited file skipped and reported, owner edit kept", any("use_g6e.py" in s for s in r["skipped"]) and ed.read_text().endswith("# owner edit\n"), r["skipped"])
check("the other rewritten file was restored", any("main_g6e.py" in s for s in r["done"]), r["done"])
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
