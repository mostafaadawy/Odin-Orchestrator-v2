"""
phase7_lifecycle.py — the create → monitor → clean cycle (Phase 7).

Creates 4 NEW projects via the NEW methodology (workspace_mw.create_owner — the single door), each a
different shape, MONITORS the system after each create (middleware placement + odin_core_iso lockstep + audit
== 0 violations), then DELETES them via delete_owner and proves the system returns to EXACT baseline while
any promoted SHARED capability survives.

Shapes:
  1. schedule   — recurring/periodical scheduled project
  2. reader     — read-only connector reader
  3. deploy     — REUSES the shared deploy capability via request_capability (proves NO deploy_2 duplicate)
  4. revealer   — multi-agent project (links several existing agents)

Production (organics/bendcore) is never touched. Run:
  python3 workspace/shared/testing/phase7_lifecycle.py
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

import workspace_mw as mw
import workspace_audit as au
import psycopg2

NEW = [
    ("t7-schedule-poster", {"type": "recurring", "category": "marketing", "cadence": "recurring",
                            "config": {"cadence": "recurring", "schedule": {"kind": "daily", "at": "09:00"}}}),
    ("t7-reader-connector", {"type": "normal", "category": "read-only",
                             "config": {"mode": "read-only"}}),
    ("t7-deploy-reuse", {"type": "normal", "category": "devops", "config": {}}),
    ("t7-revealer-multi", {"type": "normal", "category": "build", "config": {}}),
]


def _db():
    return psycopg2.connect(dbname="odin_core_iso")


def _counts():
    c = _db(); cu = c.cursor(); o = {}
    for t in ("projects", "agents", "files", "folders", "dependencies", "project_agents"):
        cu.execute(f"SELECT count(*) FROM {t}"); o[t] = cu.fetchone()[0]
    c.close(); return o


def _monitor(pid) -> dict:
    placement = [x for x in mw.scan_violations() if f"projects/{pid}/" in x[0]]
    au.heal(force=True)  # 'run now' after each create — self-heal any drift
    post = [i for i in au.scan()
            if i.get("owner") == pid or str(i.get("path", "")).startswith(f"workspace/projects/{pid}/")]
    c = _db(); cu = c.cursor()
    cu.execute("SELECT count(*) FROM projects WHERE id=%s", (pid,)); in_db = cu.fetchone()[0] == 1
    c.close()
    return {"placement": len(placement), "violations": len(post), "in_db": in_db,
            "ok": (not placement and not post and in_db)}


def run() -> bool:
    print("=" * 74)
    print("PHASE 7 — CREATE → MONITOR → CLEAN  (4 new projects, new methodology)")
    print("=" * 74)
    base = _counts(); base_iss = len(au.scan())
    print(f"baseline: {base} | violations={base_iss}")
    print("-" * 74)

    # snapshot the shared deploy capability so we can prove it SURVIVES project deletion
    shared_deploy = sorted(str(p.relative_to(WS)) for p in (WS / "shared").rglob("*")
                           if p.is_file() and "deploy" in p.name.lower())
    ok_all = True

    for pid, idx in NEW:
        mw.delete_owner("project", pid)  # clean slate
        mw.create_owner("project", pid, {"id": pid, "name": pid, **idx})

        extra = ""
        if pid == "t7-deploy-reuse":
            # REUSE the shared deploy capability instead of creating a copy (anti-duplication)
            res = mw.request_capability("project", pid, "deploy")
            man = WS / "projects" / pid / "dependencies" / "manifest.json"
            pts_shared = man.is_file() and any(d.get("source", "").startswith("shared/")
                                               for d in json.loads(man.read_text()))
            extra = f"| reuse={res.get('action')} found={res.get('found')} points_to_shared={pts_shared}"
            if not pts_shared:
                ok_all = False
        if pid == "t7-revealer-multi":
            # link 3 existing agents (multi-agent) via the DB relation
            c = _db(); cu = c.cursor()
            cu.execute("SELECT id FROM agents ORDER BY id LIMIT 3"); ags = [r[0] for r in cu.fetchall()]
            for a in ags:
                cu.execute("INSERT INTO project_agents(project_id,agent_id) VALUES(%s,%s) ON CONFLICT DO NOTHING", (pid, a))
            c.commit(); c.close()
            extra = f"| linked_agents={len(ags)}"

        m = _monitor(pid)
        status = "PASS" if m["ok"] else "FAIL"
        if not m["ok"]:
            ok_all = False
        print(f"  CREATE [{status}] {pid:22s} type={idx['type']:10s} monitor(placement={m['placement']},"
              f"violations={m['violations']},in_db={m['in_db']}) {extra}")

    print("-" * 74)
    # ---- clean deletion: remove all 4, prove baseline restored + shared survives ----
    for pid, _ in NEW:
        mw.delete_owner("project", pid)
    after = _counts(); after_iss = len(au.scan())
    delta = {k: after[k] - base[k] for k in base}
    shared_after = sorted(str(p.relative_to(WS)) for p in (WS / "shared").rglob("*")
                          if p.is_file() and "deploy" in p.name.lower())
    shared_survived = shared_deploy == shared_after
    print(f"after clean: {after} | violations={after_iss}")
    print(f"delta vs baseline: {delta}")
    print(f"shared deploy capability survived deletion: {shared_survived} ({len(shared_after)} files)")
    clean = all(v == 0 for v in delta.values()) and after_iss == base_iss and shared_survived
    ok = ok_all and clean
    print("-" * 74)
    print("PHASE7_LIFECYCLE:", "ALL GREEN ✅" if ok else "HAS FAILURES ❌")
    return ok


if __name__ == "__main__":
    sys.exit(0 if run() else 1)
