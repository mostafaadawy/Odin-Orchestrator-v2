#!/usr/bin/env python3
"""F-11 test (owner's 50% rule + TRUE deltas, no LLM). >50% common -> shared base + a delta that holds ONLY the
differences and reproduces the project's behaviour exactly (proven by running it before/after); >50% different ->
separate scripts; exactly 50% -> owner review. python f11_test.py <root>"""
import sys, os, pathlib, json, time, subprocess, shutil
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
import workspace_mw as mw, workspace_audit as au
WS = root / "workspace"; fails = []
NODE = shutil.which("node") or str(pathlib.Path.home() / ".nvm/versions/node/v20.20.2/bin/node")
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
def dups(tag): return [i for i in au.scan() if i["type"] == "duplicate" and any(tag in x for x in i["paths"])]
def manifest(pid):
    try: return json.loads((WS / "projects" / pid / "dependencies" / "manifest.json").read_text())
    except Exception: return []
A, B, C = "revealer-6978", "hubspot-crm-operator", "zoom-real-flow"
for _ in range(3): au.heal(force=True)
def pybody(common, own, tag, n=10):
    # `common` of `n` meaningful lines are shared; the two trailer lines count as common too
    L = [f"line_{tag}_common_{i} = {i}" for i in range(common)] + [f"line_{tag}_own_{own}_{i} = {i * 7}" for i in range(n - common)]
    return "\n".join(L + ["import sys", "print(sorted((k, v) for k, v in dict(globals()).items() if k.startswith('line_')), sys.argv[1:])"]) + "\n"
def half(own, tag):   # exactly 50%: 6 common (4 + trailer 2) of 12
    return pybody(4, own, tag, n=10)
def put(pid, name, text):
    p = WS / "projects" / pid / "code" / name; p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text); mw.sync_row(p); time.sleep(1.1); return p
def run(cmd, cwd):
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=60)
    return (r.returncode, r.stdout, r.stderr[-300:] if r.returncode else "")
sd = getattr(mw, "share_decision", lambda a, b: {"decision": None, "common": None})
check("1: 80% common -> shared+delta; 20% -> separate; 50% -> review; comments/blank lines ignored",
      sd(pybody(8, "a", "x"), pybody(8, "b", "x"))["decision"] == "shared+delta" and sd(pybody(2, "a", "x"), pybody(2, "b", "x"))["decision"] == "separate"
      and sd(half("a", "x"), half("b", "x"))["decision"] == "review" and sd("a = 1\n# n\n\nb = 2\n", "a = 1\n\n// o\nb = 2\n")["common"] == 1.0)
# (a) Python, >50% common
pa = put(A, "sync_f11.py", pybody(8, "a", "s")); pc = put(C, "sync_f11.py", pybody(8, "c", "s"))
orig_c = pc.read_text(); before = run([sys.executable, str(pc), "arg1"], pc.parent)
d = dups("sync_f11")
check("2: scan: the pair is a duplicate with plan shared+delta", len(d) == 1 and [v["decision"] for v in d[0].get("plan", {}).values()] == ["shared+delta"], d)
h = au.heal(force=True); fx = [a["fix"] for a in h["actions"] if "sync_f11" in json.dumps(a)]
sh = WS / "shared" / "utils" / "sync_f11.py"
check("3: the ORIGINAL copy (A) became the shared base", sh.is_file() and sh.read_text() == pybody(8, "a", "s") and not pa.exists(), fx)
txt = pc.read_text() if pc.exists() else ""
common_lines = [l for l in orig_c.splitlines() if "_common_" in l]
check("4: C's copy is now a TRUE delta: pointer to the base, NO common line, only the differences",
      "delta over shared capability: shared/utils/sync_f11.py" in txt and "_ODIN_DELTA" in txt
      and not any(l in txt for l in common_lines) and all(l in txt for l in orig_c.splitlines() if "_own_" in l), txt[:300])
after = run([sys.executable, str(pc), "arg1"], pc.parent)
check("5: C behaves EXACTLY as before (same output, same exit code)", before == after and before[0] == 0, (before, after))
reg = [e for e in manifest(C) if e.get("source") == "shared/utils/sync_f11.py"]
check("6: the delta is registered in C's manifest (mode delta) and the pair is no longer a violation",
      reg and reg[0].get("mode") == "delta" and reg[0].get("overlay") == "code/sync_f11.py" and not dups("sync_f11"), reg)
# (b) the shared base changes elsewhere -> C still identical; changes where C's delta applies -> C refuses
sh.write_text("# base note added later\n" + sh.read_text())
check("7: base changed elsewhere: C still behaves exactly as before", run([sys.executable, str(pc), "arg1"], pc.parent) == before)
t = sh.read_text(); sh.write_text(t.replace("line_s_own_a_0 = 0", "line_s_own_a_0 = 999"))
r = run([sys.executable, str(pc), "arg1"], pc.parent)
check("8: base changed where the delta applies: C REFUSES to run (never silently different)", r[0] != 0 and "DeltaConflict" in r[2], r)
sh.write_text(t.replace("# base note added later\n", ""))
# (c) bash and JavaScript
def shbody(common, own):
    return "#!/usr/bin/env bash\n" + "".join(f"echo common_{i}\n" for i in range(common)) + "".join(f"echo own_{own}_{i} \"$1\"\n" for i in range(10 - common)) + "exit 3\n"
pa2 = put(A, "run_f11.sh", shbody(8, "a")); pc2 = put(C, "run_f11.sh", shbody(8, "c"))
b2 = run(["bash", str(pc2), "X Y"], pc2.parent)
def jsbody(common, own):
    return "".join(f"const c{i} = {i};\n" for i in range(common)) + "".join(f"const o{own}{i} = {i * 3};\n" for i in range(10 - common)) + \
        f"module.exports = {{ sum: {'+'.join([f'c{i}' for i in range(common)] + [f'o{own}{i}' for i in range(10 - common)])} }};\nconsole.log('js', module.exports.sum);\n"
pa3 = put(A, "calc_f11.js", jsbody(8, "a")); pc3 = put(C, "calc_f11.js", jsbody(8, "c"))
b3 = run([NODE, str(pc3)], pc3.parent)
b3m = run([NODE, "-e", f"console.log(JSON.stringify(require('{pc3}')))"], pc3.parent)
au.heal(force=True)
a2 = run(["bash", str(pc2), "X Y"], pc2.parent); a3 = run([NODE, str(pc3)], pc3.parent)
a3m = run([NODE, "-e", f"console.log(JSON.stringify(require('{pc3}')))"], pc3.parent)
check("9: bash delta: same output, arguments and exit code", "_ODIN_DELTA" in pc2.read_text() and a2 == b2 and b2[0] == 3, (b2, a2))
check("10: JavaScript delta: same output and same module exports", "_ODIN_DELTA" in pc3.read_text() and a3 == b3 and a3m == b3m and b3[0] == 0, (b3, a3, b3m, a3m))
# (d) a file type that cannot run as a delta -> owner review, nothing changed
j1 = put(A, "conf_f11.json", "\n".join(f'"k{i}": {i},' for i in range(8)) + '\n"x": 1\n'); j2 = put(C, "conf_f11.json", "\n".join(f'"k{i}": {i},' for i in range(8)) + '\n"x": 2\n')
jb = (j1.read_bytes(), j2.read_bytes())
h = au.heal(force=True); fx = [a["fix"] for a in h["actions"] if "conf_f11" in json.dumps(a)]
check("11: no executable delta possible (.json): flagged for the owner, both files unchanged",
      fx and fx[0].startswith("FLAGGED") and (j1.read_bytes(), j2.read_bytes()) == jb and not list((WS / "shared").rglob("conf_f11.json")), fx)
# (e) >50% different and exactly 50%
pa4 = put(A, "report_f11.py", pybody(2, "a", "r")); pc4 = put(C, "report_f11.py", pybody(2, "c", "r"))
au.heal(force=True)
check("12: 80% different: separate scripts, untouched, nothing in shared", not dups("report_f11") and pa4.is_file() and pc4.read_text() == pybody(2, "c", "r")
      and not list((WS / "shared").rglob("report_f11.py")))
put(A, "half_f11.py", half("a", "h")); put(C, "half_f11.py", half("c", "h"))
h = au.heal(force=True); fx = [a["fix"] for a in h["actions"] if "half_f11" in json.dumps(a)]
check("13: exactly 50%: flagged for owner review, nothing moved", fx and fx[0].startswith("FLAGGED") and "50%" in fx[0], fx)
# (f) the customize path writes a true delta too
(WS / "shared" / "utils").mkdir(parents=True, exist_ok=True)
(WS / "shared" / "utils" / "base_f11.py").write_text(pybody(8, "a", "k")); mw.sync_row(WS / "shared" / "utils" / "base_f11.py")
ownb = pybody(8, "b", "k")
try:
    r1 = mw.customize_shared("project", B, "base_f11.py", "base_f11_b.py", "", full_version=ownb)
    r2 = mw.customize_shared("project", C, "base_f11.py", "base_f11_c.py", "", full_version=pybody(2, "c", "k"))
except TypeError as e:
    r1 = r2 = {"error": repr(e)}
fb = WS / "projects" / B / "code" / "base_f11_b.py"
tmp = root / "tmp_f11_full.py"; tmp.write_text(ownb)
check("14: customize: >50% common -> a true delta that runs exactly like the full version; >50% different -> separate script",
      r1.get("mode") == "delta" and fb.is_file() and "line_k_common_0" not in fb.read_text()
      and run([sys.executable, str(fb), "z"], fb.parent)[1] == run([sys.executable, str(tmp), "z"], root)[1] and r2.get("decision") == "separate", (r1, r2))
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
