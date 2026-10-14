#!/usr/bin/env python3
"""G7 test (no LLM): duplicates in tests/ are found; per-project thin pointers are not. python g7_test.py <root>"""
import sys, os, pathlib, json, time
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root); sys.path.insert(0, str(root / "server"))
import workspace_mw as mw, workspace_audit as au
WS = root / "workspace"; fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
def dups(tag): return [i for i in au.scan() if i["type"] == "duplicate" and any(tag in x for x in i["paths"])]
A, C = "hubspot-crm-operator", "zoom-real-flow"
R = "revealer-6978"   # its tests/ is a REGISTERED overlay folder (delta over shared/testing/run_all.py)
for _ in range(3): au.heal(force=True)
ptr = list(WS.glob("projects/*/tests/project_test.py"))
check("G7-0: the copy has per-project test pointers in >=2 projects", len(ptr) >= 2, len(ptr))
check("G7-1: per-project thin pointers (tests/project_test.py) are NOT flagged", not dups("project_test.py"), dups("project_test.py"))
body = "def helper_g7():\n    return 7\n"
for pid in (A, C):
    d = WS/"projects"/pid/"tests"; d.mkdir(parents=True, exist_ok=True); (d/"helper_g7.py").write_text(body); mw.sync_row(d/"helper_g7.py"); time.sleep(1.1)
check("G7-2: identical copies in tests/ ARE found", len(dups("helper_g7")) == 1 and dups("helper_g7")[0]["identical"])
au.heal(force=True)
check("G7-3: heal promotes them to shared/testing under the original name", (WS/"shared"/"testing"/"helper_g7.py").is_file()
      and not any((WS/"projects"/p/"tests"/"helper_g7.py").exists() for p in (A, C)))
for pid, v in ((A, 1), (C, 2)):
    (WS/"projects"/pid/"tests"/"test_g7.py").write_text(f"import unittest\nclass T(unittest.TestCase):\n    def test_v(self):\n        self.assertEqual({v}, {v})\n")
d = dups("test_g7")
check("G7-4: same-name different tests in tests/ are flagged (not promoted)", len(d) == 1 and not d[0]["identical"])
# G7-5: an IDENTICAL copy inside a registered overlay folder is still a duplicate; a different one is not
(WS/"projects"/R/"tests").mkdir(parents=True, exist_ok=True)
(WS/"projects"/R/"tests"/"same_g7.py").write_text("S = 1\n"); (WS/"projects"/C/"tests"/"same_g7.py").write_text("S = 1\n")
(WS/"projects"/R/"tests"/"diff_g7.py").write_text("D = 1\n"); (WS/"projects"/C/"tests"/"diff_g7.py").write_text("D = 2\n")
check("G7-5: identical copy inside an overlay folder is still found", len(dups("same_g7")) == 1)
check("G7-6: a different same-name file inside an overlay folder is not flagged", not dups("diff_g7"), dups("diff_g7"))
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
