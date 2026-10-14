#!/usr/bin/env python3
"""G6 test (no LLM). Run inside a throwaway root: python g6_test.py <root>
S6 shape: an identical duplicate across two projects PLUS a foreign reference to one copy, then heal.
Checks that NO reference is left dangling and that the audit REPORTS a dangling reference if one exists."""
import sys, os, pathlib, re, json
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
import workspace_mw as mw, workspace_audit as au
WS = root / "workspace"
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{info}]" if info and not c else ""))
    if not c: fails.append(n)
REF = re.compile(r'(?<![\w/\-])((?:workspace/)?(?:projects|shared)/[A-Za-z0-9_\-/\.]+)')
def refs_resolve(p):
    bad = []
    for m in REF.finditer(p.read_text(errors="replace")):
        r = m.group(1).rstrip("\"').,)")
        if "." not in pathlib.PurePath(r).name: continue
        q = (root / r) if r.startswith("workspace/") else (WS / r)
        if not q.is_file(): bad.append(r)
    return bad
A, B, C = "revealer-6978", "hubspot-crm-operator", "zoom-real-flow"
for x in (A, B, C): check(f"project {x} exists in the copy", (WS / "projects" / x).is_dir())
base_dang = [i for i in au.scan() if i.get("type") == "dangling-ref"]
check("baseline workspace: no dangling-ref noise", len(base_dang) == 0, json.dumps(base_dang)[:300])
# --- case 1: S6 exact (duplicate + foreign ref to the copy that heal deletes) ---
body = "def helper_g6():\n    return 'shared logic g6'\n"
mw.put_file("project", A, "code", "helper_g6.py", body, actor=("project", A))
dup = WS / "projects" / B / "code" / "dup_test_g6.py"; dup.write_text(body)
use = WS / "projects" / B / "code" / "use_g6.py"
use.write_text(f"exec(open('workspace/projects/{A}/code/helper_g6.py').read())\n")
own = WS / "projects" / A / "code" / "main_g6.py"
own.write_text(f"exec(open('workspace/projects/{A}/code/helper_g6.py').read())\nprint(helper_g6())\n")
au.heal(force=True)
check("case 1: B's foreign referrer resolves after heal", use.exists() and not refs_resolve(use), refs_resolve(use) if use.exists() else "gone")
check("case 1: A's own referrer resolves after heal", own.exists() and not refs_resolve(own), refs_resolve(own) if own.exists() else "gone")
check("case 1: the shared copy exists and holds the code", any(body == p.read_text() for p in (WS / "shared").rglob("*g6*.py")))
check("case 1: no private copy left in A or B", not (WS/"projects"/A/"code"/"helper_g6.py").exists() and not dup.exists())
post = [i for i in au.scan() if "g6" in json.dumps(i)]
check("case 1: scan after heal is clean for g6", not post, json.dumps(post)[:300])
# --- case 2: a dangling reference the heal cannot repair must be REPORTED (not 0) ---
dang = WS / "projects" / C / "code" / "dangling_g6.py"
dang.parent.mkdir(parents=True, exist_ok=True)
dang.write_text(f"exec(open('workspace/projects/{A}/code/never_existed_g6.py').read())\n")
s = [i for i in au.scan() if i.get("type") == "dangling-ref" and "dangling_g6" in i.get("path", "")]
check("case 2: scan reports the dangling reference", len(s) == 1)
sen = au.sentinel(notify=False)
check("case 2: sentinel counts it as a hard violation", any(i.get("type") == "dangling-ref" for i in sen["issues"]) and sen["hard"] >= 1)
h = au.heal(force=True)
fx = [a["fix"] for a in h["actions"] if "dangling_g6" in a.get("path", "")]
check("case 2: heal flags it for the owner (does not guess)", fx and all(f.startswith("FLAGGED") for f in fx), fx)
dang.unlink(); mw.remove_file(dang)
# --- case 3: a reference written AFTER a promotion, to the old path, is repaired from the move record ---
late = WS / "projects" / C / "code" / "late_g6.py"
late.write_text(f"exec(open('workspace/projects/{B}/code/dup_test_g6.py').read())\n")
au.heal(force=True)
check("case 3: late reference to a moved file is repointed", not refs_resolve(late), refs_resolve(late))
# --- case 4: plain foreign reference (no duplicate) still promotes and resolves (regression) ---
mw.put_file("project", A, "code", "solo_g6.py", "X_G6 = 4\n", actor=("project", A))
ref4 = WS / "projects" / C / "code" / "uses_solo_g6.py"
ref4.write_text(f"exec(open('workspace/projects/{A}/code/solo_g6.py').read())\n")
au.heal(force=True)
check("case 4: plain foreign ref promoted and resolves", not refs_resolve(ref4), refs_resolve(ref4))
check("final: no dangling-ref anywhere", not [i for i in au.scan() if i.get("type") == "dangling-ref"])
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
