"""
phase7_strong.py — the STRONG, adversarial Phase-7 test. Not twisted to pass: it INJECTS every violation
type and proves the system CORRECTS it for real (files actually move, DB rows change, source is rewritten),
proves promote-to-shared + the pointer resolves to a LOADABLE capability, and proves custom-over-shared by
EXECUTING the overlay. Ends by asserting 0 cross-owner AND 0 general violations, then restores baseline.

Every check asserts the REAL outcome on disk / in the DB / in behavior — if the system fails to correct,
the test raises and fails. Run:  python3 workspace/shared/testing/phase7_strong.py
"""
from __future__ import annotations
import sys, json, pathlib, importlib.util

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WS = ROOT / "workspace"
SERVER = ROOT / "server"
for p in (str(HERE), str(SERVER)):
    if p not in sys.path:
        sys.path.insert(0, p)

import workspace_mw as mw
import workspace_audit as au
import psycopg2

OWNERS_P = ["_s_a", "_s_b", "_s_c", "_s_d", "_s_e", "_s_f", "_s_g"]
OWNERS_A = ["_s_agent"]
SHARED_TEST_FILES = ["dupz.py", "flib.py", "calc_base.py", "calc_override.py", "tool.py"]
_fails = []


def _load(path, modname):
    spec = importlib.util.spec_from_file_location(modname, str(path))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def check(label, cond, detail=""):
    ok = bool(cond)
    print(f"   [{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if (detail and not ok) else ""))
    if not ok:
        _fails.append(label)
    return ok


def _clean():
    for p in OWNERS_P + ["B"]:
        mw.delete_owner("project", p)
    for a in OWNERS_A:
        mw.delete_owner("agent", a)
    for nm in SHARED_TEST_FILES:
        for f in (WS / "shared").rglob(nm):
            try:
                mw.remove_file(f)
                if f.exists():
                    f.unlink()
            except Exception:
                pass


def _counts():
    c = psycopg2.connect(dbname="odin_core"); cu = c.cursor(); o = {}
    for t in ("projects", "agents", "files", "folders", "dependencies", "project_agents"):
        cu.execute(f"SELECT count(*) FROM {t}"); o[t] = cu.fetchone()[0]
    c.close(); return o


def run() -> bool:
    print("=" * 74)
    print("PHASE 7 — STRONG ADVERSARIAL TEST (inject → prove real correction → 0 violations)")
    print("=" * 74)
    _clean()
    base_counts = _counts(); base_iss = len(au.scan())
    print(f"baseline: {base_counts} | violations={base_iss}")
    for p in OWNERS_P:
        mw.create_owner("project", p, {"id": p, "name": p, "type": "normal"})
    for a in OWNERS_A:
        mw.create_owner("agent", a, {"id": a, "name": a, "type": "technical"})
    A, B, C, D, E, F, G = OWNERS_P
    AG = OWNERS_A[0]

    print("\nS1 — cross-owner write (project B → project A) is PREVENTED + redirected, NOT blocked")
    r = mw.put_file("project", A, "code", "tool.py", "x=1\n", actor=B)
    check("flow not blocked (returned a path)", bool(r.get("path")))
    check("scope_redirected flag set", r.get("scope_redirected") is True)
    check("redirected to B's own folder", r.get("owner_id") == B, r.get("owner_id"))
    check("file landed in B, code/", (WS / "projects" / B / "code" / "tool.py").is_file())
    check("file did NOT leak into A", not (WS / "projects" / A / "code" / "tool.py").exists())

    print("\nS2 — cross-TYPE write (project A → agent) is PREVENTED + redirected")
    r2 = mw.put_file("agent", AG, "code", "x.py", "y=1\n", actor=("project", A))
    check("redirected to project A", r2.get("scope_redirected") and r2.get("owner_id") == A, r2.get("owner_id"))
    check("landed in project A", (WS / "projects" / A / "code" / "x.py").is_file())
    check("did NOT leak into the agent", not (WS / "agents" / AG / "code" / "x.py").exists())

    print("\nS3 — misplaced file (direct write, bypassing the door) is DETECTED + moved to code/")
    bad = WS / "projects" / A / "randomsub" / "stray.py"
    bad.parent.mkdir(parents=True, exist_ok=True); bad.write_text("z=2\n")
    check("audit detects misplaced", any(i.get("type") == "misplaced" and "stray.py" in i.get("path", "")
                                         for i in au.scan()))
    au.heal(force=True)
    check("moved OUT of the wrong slot", not bad.exists())
    check("moved INTO code/", (WS / "projects" / A / "code" / "stray.py").is_file())
    check("0 misplaced remain for stray.py", not any("stray.py" in i.get("path", "") for i in au.scan()))

    print("\nS4 — identical duplicate across 2 projects → PROMOTED to shared + both repointed + copies removed")
    same = "def z():\n    return 7\n"
    mw.put_file("project", C, "code", "dupz.py", same)
    mw.put_file("project", D, "code", "dupz.py", same)
    check("audit detects identical duplicate",
          any(i.get("type") == "duplicate" and i.get("name") == "dupz.py" and i.get("identical") for i in au.scan()))
    au.heal(force=True)
    shared_dupz = list((WS / "shared").rglob("dupz.py"))
    check("promoted to shared once", len(shared_dupz) == 1, f"{len(shared_dupz)} copies")
    check("removed from BOTH projects",
          not (WS / "projects" / C / "code" / "dupz.py").exists() and not (WS / "projects" / D / "code" / "dupz.py").exists())
    mc = json.loads((WS / "projects" / C / "dependencies" / "manifest.json").read_text())
    md = json.loads((WS / "projects" / D / "dependencies" / "manifest.json").read_text())
    check("both repointed to shared", any("shared/" in x.get("source", "") for x in mc) and any("shared/" in x.get("source", "") for x in md))
    check("0 duplicate remains", not any(i.get("type") == "duplicate" and i.get("name") == "dupz.py" for i in au.scan()))

    print("\nS5 — foreign reference (E reads F's private file) → PROMOTED + E's SOURCE rewritten")
    mw.put_file("project", F, "code", "flib.py", "def g():\n    return 3\n")
    mw.put_file("project", E, "code", "usef.py", "P='workspace/projects/_s_f/code/flib.py'\n")
    check("audit detects foreign-ref", any(i.get("type") == "foreign-ref" and i.get("owner") == E for i in au.scan()))
    au.heal(force=True)
    check("F's file promoted to shared", bool(list((WS / "shared").rglob("flib.py"))))
    etxt = (WS / "projects" / E / "code" / "usef.py").read_text()
    check("E's source rewritten to shared", "shared/" in etxt and "projects/_s_f/code" not in etxt, etxt.strip())
    check("0 foreign-ref remains for E", not any(i.get("type") == "foreign-ref" and i.get("owner") == E for i in au.scan()))

    print("\nS6 — pointer RESOLVES to a loadable shared capability (promote + pointer works)")
    res = mw.resolve_capability("project", E, "flib.py")
    check("resolve_capability resolved", res.get("resolved") and res.get("base_exists"), json.dumps(res))
    if res.get("base_path"):
        mod = _load(res["base_path"], "flib_shared_load")
        check("loaded shared capability executes (g()==3)", getattr(mod, "g", lambda: None)() == 3)

    print("\nS7 — custom-over-shared: overlay OVERRIDES the shared base (EXECUTED, not just declared)")
    (WS / "shared" / "utils").mkdir(parents=True, exist_ok=True)
    base_f = WS / "shared" / "utils" / "calc_base.py"
    base_f.write_text("def value():\n    return 1\n"); mw.sync_row(base_f)
    cust = mw.customize_shared("project", G, "calc_base.py", "calc_override.py",
                               "def value():\n    return 2\n", mode="override")
    check("customize_shared ok", cust.get("ok"), json.dumps(cust))
    rc = mw.resolve_capability("project", G, "calc_base.py")
    check("resolves base+overlay, mode=override", rc.get("resolved") and rc.get("mode") == "override"
          and rc.get("base_exists") and rc.get("overlay_exists"), json.dumps(rc))
    if rc.get("base_path") and rc.get("overlay_path"):
        bmod = _load(rc["base_path"], "cb_load"); omod = _load(rc["overlay_path"], "co_load")
        check("base value()==1 (shared untouched)", bmod.value() == 1)
        check("overlay value()==2 (custom delta actually overrides)", omod.value() == 2)
    check("shared base file left UNCHANGED", base_f.read_text().strip() == "def value():\n    return 1".strip())

    print("\nS8 — FINAL: drive audit to convergence, assert 0 cross + 0 general violations")
    for _ in range(3):
        au.heal(force=True)
    remaining = au.scan()
    # scope to our test owners for the cross/general split
    ours = [i for i in remaining if any(o in json.dumps(i) for o in OWNERS_P + OWNERS_A)]
    check("0 violations touching the test owners", not ours, f"{[i.get('type') for i in ours]}")
    check("0 GENERAL workspace violations", len(remaining) == 0, f"{len(remaining)} remain: {[i.get('type') for i in remaining][:6]}")

    print("\nCLEANUP — remove all injected artifacts, assert baseline restored")
    _clean()
    after = _counts(); after_iss = len(au.scan())
    delta = {k: after[k] - base_counts[k] for k in base_counts}
    check("system back to EXACT baseline", all(v == 0 for v in delta.values()), json.dumps(delta))
    check("0 violations after cleanup", after_iss == base_iss)

    print("-" * 74)
    ok = not _fails
    print(f"STRONG TEST: {'ALL GREEN ✅' if ok else 'FAILURES: ' + ', '.join(_fails)}")
    print("PHASE7_STRONG:", "ALL GREEN ✅" if ok else "HAS FAILURES ❌")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
