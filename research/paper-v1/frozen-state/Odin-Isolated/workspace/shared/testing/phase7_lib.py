"""
phase7_lib.py — the SHARED per-project test logic (Phase 7).

One home for the test body; every project's tests/project_test.py is a thin pointer that calls
run_project_test(<its id>). That is the anti-duplication model applied to the tests themselves: the
capability lives in shared/, each consumer reuses it with its own id — no copy per project.

A child test confirms a project is CORRECT and CONSISTENT with the new architecture, fast:
  1. canonical skeleton present (folders + index.json valid),
  2. present + seeded in odin_core_iso,
  3. every on-disk file is indexed (DB lockstep),
  4. no schema/cross-owner violations for this project (uses the audit's own detectors),
  5. capability integrity — every dependency resolves to a real shared/ capability (not a bundled copy,
     not a foreign project path).
Live external execution is a later layer (after the anchor); this proves structural + capability health
with a performance number, which is what must be green BEFORE anything heavier runs.
"""
from __future__ import annotations
import sys, json, time, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]
WS = ROOT / "workspace"
SERVER = ROOT / "server"
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))


def _db():
    import psycopg2
    return psycopg2.connect(dbname="odin_core_iso")


def run_project_test(pid: str) -> dict:
    """Return {pid, passed, ms, checks:[{check,ok,detail}]}. Pure read-only integrity test."""
    t0 = time.time()
    import workspace_audit as au
    base = WS / "projects" / pid
    checks = []

    def chk(name, ok, detail=""):
        checks.append({"check": name, "ok": bool(ok), "detail": str(detail)})

    # 1) skeleton conformance
    chk("folder exists", base.exists(), base)
    ok_idx = False
    try:
        idx = json.loads((base / "index.json").read_text())
        ok_idx = bool(idx.get("id"))
    except Exception as e:
        idx = {}
        ok_idx = f"error: {e}"
    chk("index.json valid", ok_idx is True, "" if ok_idx is True else ok_idx)
    missing = [s for s in ("code", "tests", "data", "deploy", "dependencies", "docs", "files")
               if not (base / s).exists()]
    chk("core subfolders present", not missing, f"missing={missing}")

    # 2) present in odin_core_iso + 3) every file indexed (DB lockstep)
    in_db = False
    unindexed = []
    try:
        c = _db(); cu = c.cursor()
        cu.execute("SELECT count(*) FROM projects WHERE id=%s", (pid,))
        in_db = cu.fetchone()[0] == 1
        cu.execute("SELECT path FROM files WHERE owner_type='project' AND owner_id=%s", (pid,))
        dbfiles = {r[0] for r in cu.fetchall()}
        c.close()
        # count only files the DB is expected to track — use the AUDIT'S OWN classifier (au.is_tracked) as
        # the SINGLE source of truth, so this test can NEVER diverge from what the audit actually indexes.
        # (A private, weaker filter here — skip only dotfiles + __pycache__ — was what made a clean project
        # read as dirty: it counted node_modules/build/output files the audit rightly never tracks, and it
        # relied on the audit's old allow-list dropping .sql. One definition now governs both.)
        disk = [p for p in base.rglob("*") if au.is_tracked(p)]
        unindexed = [str(p.relative_to(ROOT)) for p in disk if str(p.relative_to(ROOT)) not in dbfiles]
    except Exception as e:
        chk("odin_core_iso reachable", False, e)
    chk("seeded in odin_core_iso", in_db)
    chk("all files indexed (DB lockstep)", not unindexed, f"unindexed={len(unindexed)}: {unindexed[:3]}")

    # 4) no schema / cross-owner violations for THIS project
    iss = [i for i in au.scan()
           if i.get("owner") == pid or str(i.get("path", "")).startswith(f"workspace/projects/{pid}/")]
    chk("zero violations", not iss, f"types={[i.get('type') for i in iss]}")

    # 5) capability integrity — deps resolve to a real shared/ capability
    man = base / "dependencies" / "manifest.json"
    bad = []
    if man.is_file():
        try:
            for d in json.loads(man.read_text()):
                src = d.get("source", "")
                if src and not src.startswith("shared/"):
                    bad.append(f"{src} (not shared/)")
                elif src and not (WS / src).exists():
                    bad.append(f"{src} (missing)")
        except Exception as e:
            bad.append(f"manifest error: {e}")
    chk("deps resolve via shared/", not bad, f"bad={bad}")

    ms = round((time.time() - t0) * 1000)
    return {"pid": pid, "passed": all(c["ok"] for c in checks), "ms": ms, "checks": checks}
