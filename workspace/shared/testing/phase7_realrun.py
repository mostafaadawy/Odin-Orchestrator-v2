"""
phase7_realrun.py — REAL first-time run of every project, timed, with audit+middleware monitoring.

For each project (production organics/bendcore EXCLUDED):
  1. snapshot DB + violations BEFORE
  2. trigger the project's REAL run through the brain (SOC -> /soc/run, others -> /projects/<pid>/run-now)
  3. wait until it actually produces output (scope-message quiescence) — this is the TIMED window
  4. run the AUDIT ('run now') + middleware placement + DB-lockstep checks
  5. report: description, what it does, result, DURATION, gaps found/solved

Usage:
  python3 workspace/shared/testing/phase7_realrun.py            # all projects
  python3 workspace/shared/testing/phase7_realrun.py <pid> ...  # only these
"""
from __future__ import annotations
import sys, json, time, pathlib, urllib.request

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

def _odin_token():   # F-20: the brain token (same machine)
    import os as _o, pathlib as _p
    if _o.environ.get("ODIN_ACCESS_TOKEN"): return _o.environ["ODIN_ACCESS_TOKEN"]
    for _d in _p.Path(__file__).resolve().parents:
        _f = _d / "data" / "brain_token"
        if _f.is_file(): return _f.read_text().strip()
    return ""


BRAIN = "http://127.0.0.1:8000"
PROTECTED = set(getattr(au, "PROTECTED_PROJECTS", {"organics-prod-deploy"}))
QUIET_SECS = 25          # no new messages for this long => the run produced its output
MAX_WAIT = 900           # hard ceiling per project


def _get(path, timeout=20):
    try:
        return json.load(urllib.request.urlopen(BRAIN + path, timeout=timeout))
    except Exception:
        return {}


def _post(path, body=None, timeout=60):
    data = json.dumps(body or {}).encode()
    req = urllib.request.Request(BRAIN + path, data=data, headers={"Content-Type": "application/json", "X-Odin-Token": _odin_token()})
    try:
        return json.load(urllib.request.urlopen(req, timeout=timeout))
    except Exception as e:
        return {"error": str(e)}


def _msg_count(pid):
    d = _get(f"/scope/messages?scope=project%3A{pid}")
    m = d.get("messages") or d.get("items") or []
    return len(m) if isinstance(m, list) else 0


def _counts():
    c = psycopg2.connect(dbname="odin_core"); cu = c.cursor(); o = {}
    for t in ("projects", "agents", "files", "folders", "dependencies", "project_agents"):
        cu.execute(f"SELECT count(*) FROM {t}"); o[t] = cu.fetchone()[0]
    c.close(); return o


def _proj_meta(pid):
    try:
        ix = json.loads((WS / "projects" / pid / "index.json").read_text())
    except Exception:
        ix = {}
    return {"name": ix.get("name", pid), "type": ix.get("type"), "cadence": ix.get("cadence"),
            "description": (ix.get("description") or "").strip()}


def run_one(pid: str) -> dict:
    meta = _proj_meta(pid)
    before_counts = _counts()
    before_iss = len(au.scan())
    before_msgs = _msg_count(pid)

    t0 = time.time()
    if pid == "redberry-continuous-soc":
        started = _post("/soc/run", {})
    else:
        started = _post(f"/projects/{pid}/run-now", {})
    trigger_ok = bool(started.get("started") or started.get("ran") or started.get("operation"))

    # wait for real output: messages grow then go quiet for QUIET_SECS
    last_n, last_change = before_msgs, time.time()
    grew = False
    NO_OUTPUT_BAIL = 150   # if nothing was ever produced within this long, stop waiting (don't burn MAX_WAIT)
    while time.time() - t0 < MAX_WAIT:
        time.sleep(5)
        n = _msg_count(pid)
        if n != last_n:
            last_n = n; last_change = time.time(); grew = True
        if grew and (time.time() - last_change) >= QUIET_SECS:
            break
        if not grew and (time.time() - t0) >= NO_OUTPUT_BAIL:
            break   # never produced output — report it instead of hanging
    duration = round(time.time() - t0, 1)

    # AUDIT + middleware + DB checks (the monitor half)
    placement = [x for x in mw.scan_violations() if f"projects/{pid}/" in x[0]]
    au.heal(force=True)
    after_iss_list = au.scan()
    mine = [i for i in after_iss_list
            if i.get("owner") == pid or str(i.get("path", "")).startswith(f"workspace/projects/{pid}/")]
    after_counts = _counts()
    delta = {k: after_counts[k] - before_counts[k] for k in before_counts}

    return {
        "pid": pid, **meta,
        "trigger_ok": trigger_ok, "produced_output": grew,
        "messages_before": before_msgs, "messages_after": last_n,
        "duration_sec": duration,
        "violations_before": before_iss, "violations_after_global": len(after_iss_list),
        "violations_for_project": len(mine), "placement_violations": len(placement),
        "db_delta": delta,
        "clean": (not mine and not placement and len(after_iss_list) == 0),
    }


def main(pids=None):
    all_p = sorted(d.name for d in (WS / "projects").iterdir()
                   if d.is_dir() and d.name != "_shared" and d.name not in PROTECTED)
    targets = [p for p in (pids or all_p) if p in all_p]
    print("=" * 78)
    print("PHASE 7 — REAL FIRST-TIME RUN OF EVERY PROJECT (timed + audit-monitored)")
    print("=" * 78)
    print(f"excluded (production): {sorted(PROTECTED)}")
    print(f"projects to run: {len(targets)}")
    results = []
    for pid in targets:
        print("-" * 78)
        print(f"▶ RUNNING {pid} …")
        r = run_one(pid)
        results.append(r)
        print(f"  name        : {r['name']}")
        print(f"  type/cadence: {r['type']} / {r['cadence']}")
        if r["description"]:
            print(f"  description : {r['description'][:120]}")
        print(f"  triggered   : {r['trigger_ok']} | produced output: {r['produced_output']} "
              f"(messages {r['messages_before']}→{r['messages_after']})")
        print(f"  DURATION    : {r['duration_sec']}s   <-- prompt/trigger → output")
        print(f"  violations  : project={r['violations_for_project']} placement={r['placement_violations']} "
              f"global_after={r['violations_after_global']}")
        print(f"  db delta    : {r['db_delta']}")
        print(f"  RESULT      : {'CLEAN ✅' if r['clean'] else 'NEEDS ATTENTION ❌'}")
    print("=" * 78)
    ok = sum(1 for r in results if r["clean"])
    print(f"SUMMARY: {ok}/{len(results)} clean | total time "
          f"{round(sum(r['duration_sec'] for r in results),1)}s")
    (WS / "logs" / "realrun_report.json").write_text(json.dumps(results, indent=2))
    print("report saved: workspace/logs/realrun_report.json")
    return all(r["clean"] for r in results)


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1:] or None) else 1)
