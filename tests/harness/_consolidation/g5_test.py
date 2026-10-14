#!/usr/bin/env python3
"""G5 + F-36 test (no LLM). Run inside a throwaway root: python g5_test.py <root>"""
import sys, os, pathlib, json, time
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
import workspace_mw as mw, workspace_audit as au
WS = root / "workspace"; fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
def dups(tag): return [i for i in au.scan() if i["type"] == "duplicate" and any(tag in x for x in i["paths"])]
A, B, C = "revealer-6978", "hubspot-crm-operator", "zoom-real-flow"
for _ in range(3): au.heal(force=True)
# G5-1: the per-project deploy config read by shared/infra/deploy_changes.py
check("G5-1: deploy/deploy-config.json (per-project input) not flagged", not dups("deploy-config.json"), dups("deploy-config.json"))
# G5-2: registered overlays (base + custom delta) in two projects, same name, different content
base = next((WS / "shared").rglob("*.py"))
for pid, v in ((A, 1), (B, 2)):
    mw.customize_shared("project", pid, base.name, "overlay_g5.py", f"# delta over shared capability: shared/{base.relative_to(WS/'shared')}\nV = {v}\n", mode="extend")
check("G5-2: registered deltas (same name, different content) not flagged", not dups("overlay_g5"), dups("overlay_g5"))
# G5-3: declared delta header only
for pid, v in ((A, 1), (C, 2)):
    (WS/"projects"/pid/"code"/"decl_g5.py").write_text(f"# delta over shared capability: shared/{base.relative_to(WS/'shared')}\nW = {v}\n")
check("G5-3: declared delta not flagged", not dups("decl_g5"))
# G5-4 control: a real same-name / different-content pair is STILL flagged
for pid, v in ((A, 1), (C, 2)):
    (WS/"projects"/pid/"code"/"util_g5.py").write_text(f"def util():\n    return {v}\n")
check("G5-4: a real non-delta duplicate is still flagged", len(dups("util_g5")) == 1)
# G5-5: an identical per-project input is never promoted
for pid in (A, C):
    d = WS/"projects"/pid/"deploy"; d.mkdir(parents=True, exist_ok=True); (d/"deploy-config.json").write_text('{"targets": []}\n')
au.heal(force=True)
check("G5-5: identical per-project configs stay in their projects", all((WS/"projects"/p/"deploy"/"deploy-config.json").is_file() for p in (A, C)))
# F-36-1: keep the OLDEST registered copy, its ORIGINAL name, correct category
body = "def helper_g5():\n    return 'g5'\n"
mw.put_file("project", A, "code", "helper_g5.py", body, actor=("project", A)); time.sleep(1.2)
cp = WS/"projects"/B/"code"/"dup_test_g5.py"; cp.write_text(body); mw.sync_row(cp)      # newer copy, sorts FIRST
ref = WS/"projects"/C/"code"/"use_g5.py"; ref.write_text(f"# C\nexec(open('workspace/projects/{B}/code/dup_test_g5.py').read())\n")
h = au.heal(force=True)
fx = [a["fix"] for a in h["actions"] if a["type"] == "duplicate" and "helper_g5" in json.dumps(a)]
check("F36-1: kept the original name and correct category (shared/utils/helper_g5.py)", (WS/"shared"/"utils"/"helper_g5.py").is_file() and not list((WS/"shared").rglob("dup_test_g5.py")), fx)
check("F36-1: not filed under testing", not (WS/"shared"/"testing"/"helper_g5.py").exists())
check("F36-1: the reference to the removed copy resolves to the kept file", "shared/utils/helper_g5.py" in ref.read_text(), ref.read_text())
# F-36-2: a real test file goes to testing
tb = "import unittest\nclass T(unittest.TestCase):\n    def test_x(self):\n        self.assertTrue(True)\n"
mw.put_file("project", A, "code", "test_g5x.py", tb, actor=("project", A)); time.sleep(1.1)
(WS/"projects"/C/"code"/"test_g5x.py").write_text(tb); mw.sync_row(WS/"projects"/C/"code"/"test_g5x.py")
au.heal(force=True)
check("F36-2: a real test file is filed under shared/testing", (WS/"shared"/"testing"/"test_g5x.py").is_file())
# F-36-3: name clash in shared with DIFFERENT content -> flagged, nothing lost
(WS/"shared"/"utils").mkdir(parents=True, exist_ok=True); (WS/"shared"/"utils"/"clash_g5.py").write_text("OTHER = 1\n"); mw.sync_row(WS/"shared"/"utils"/"clash_g5.py")
for pid in (A, C):
    (WS/"projects"/pid/"code"/"clash_g5.py").write_text("MINE = 2\n"); mw.sync_row(WS/"projects"/pid/"code"/"clash_g5.py")
h = au.heal(force=True)
fx = [a["fix"] for a in h["actions"] if a["type"] == "duplicate" and "clash_g5" in json.dumps(a)]
check("F36-3: clash flagged, both copies kept, shared file untouched",
      fx and fx[0].startswith("FLAGGED") and all((WS/"projects"/p/"code"/"clash_g5.py").is_file() for p in (A, C))
      and (WS/"shared"/"utils"/"clash_g5.py").read_text() == "OTHER = 1\n", fx)
check("F36-4: shared_category never files a helper named *test* under testing",
      mw.shared_category(WS/"projects"/A/"code"/"latest_prices.py") == "utils")
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
