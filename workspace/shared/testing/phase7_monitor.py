"""
phase7_monitor.py — the PARENT test (Phase 7): the monitor that runs each project's child test and, AFTER
each one, exercises the SYSTEM and asserts it stayed correct:
  • middleware placement    — no file of this project sits in the wrong schema slot,
  • odin_core lockstep       — every on-disk file is indexed,
  • audit                    — running the audit ('run now') finds + heals, converging to ZERO violations,
  • structure               — nothing leaked outside the project / into another owner.

The role here is MONITOR, not player: the middleware + audit are what keep things correct; this harness
proves they do, from several angles, and reports it. Production (organics/bendcore) is EXCLUDED — never
touched. Run:  python3 workspace/shared/testing/phase7_monitor.py
"""
from __future__ import annotations
import sys, json, pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WS = ROOT / "workspace"
SERVER = ROOT / "server"
for p in (str(HERE), str(SERVER)):
    if p not in sys.path:
        sys.path.insert(0, p)

import phase7_lib                      # shared child-test logic
import workspace_audit as au
import workspace_mw as mw

PROTECTED = set(getattr(au, "PROTECTED_PROJECTS", {"organics-prod-deploy"}))


def _projects():
    return sorted(d.name for d in (WS / "projects").iterdir()
                  if d.is_dir() and d.name != "_shared" and d.name not in PROTECTED)


def run(auto_heal: bool = True) -> bool:
    print("=" * 74)
    print("PHASE 7 — MONITORED TEST HARNESS  (parent monitor + per-project child tests)")
    print("=" * 74)
    print(f"excluded (protected/production): {sorted(PROTECTED)}")
    print(f"workspace violations at start: {len(au.scan())}")
    print("-" * 74)

    results = []
    for pid in _projects():
        # ---- child test: is the project itself correct + consistent? ----
        r = phase7_lib.run_project_test(pid)

        # ---- parent monitor: after the test, exercise the SYSTEM and assert it stayed clean ----
        placement = [x for x in mw.scan_violations() if f"projects/{pid}/" in x[0]]
        if auto_heal:
            au.heal(force=True)  # the 'run now' button — system self-heals any drift this test surfaced
        post = [i for i in au.scan()
                if i.get("owner") == pid or str(i.get("path", "")).startswith(f"workspace/projects/{pid}/")]
        monitor_ok = not placement and not post
        r["monitor"] = {"placement_violations": len(placement), "audit_issues_after_heal": len(post),
                        "ok": monitor_ok}
        results.append(r)

        status = "PASS" if (r["passed"] and monitor_ok) else "FAIL"
        nok = sum(c["ok"] for c in r["checks"])
        print(f"  [{status}] {pid:40s} {r['ms']:5d}ms  checks {nok}/{len(r['checks'])}  monitor_ok={monitor_ok}")
        for c in r["checks"]:
            if not c["ok"]:
                print(f"         ✗ {c['check']}: {c['detail']}")
        if not monitor_ok:
            print(f"         ✗ monitor: placement={placement[:2]} audit_after_heal={[i.get('type') for i in post]}")

    print("-" * 74)
    passed = sum(1 for r in results if r["passed"] and r["monitor"]["ok"])
    end_iss = len(au.scan())
    avg = round(sum(r["ms"] for r in results) / max(1, len(results)))
    print(f"RESULT: {passed}/{len(results)} projects PASS + monitor-clean | avg {avg}ms | "
          f"workspace violations after: {end_iss}")
    ok = passed == len(results) and end_iss == 0
    print("PHASE7_MONITOR:", "ALL GREEN ✅" if ok else "HAS FAILURES ❌")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
