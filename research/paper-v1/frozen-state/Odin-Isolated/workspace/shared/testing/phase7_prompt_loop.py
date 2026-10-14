"""
phase7_prompt_loop.py — the USER journey, automated: send a PROMPT, let the system plan, approve, watch
it build, audit, then delete — measuring the time from prompt → output.

For each spec:
  1. POST /projects/intake  with the prompt   (the system derives the plan / asks for enhancement)
  2. approve the proposal   (we act as the owner and accept)
  3. POST /projects         to actually create it (full stack: CTO + inferred team + connectors)
  4. WATCH until it produces output           <-- TIMED WINDOW (prompt -> expected output)
  5. AUDIT (manual run) + middleware placement + DB lockstep + cross/general violations
  6. DELETE it and prove other agents/projects are untouched (exact baseline restore)

The specs deliberately MIX existing capabilities (HubSpot CRM, Veeqo fulfillment, Klaviyo email,
SOC/security, scheduling) so the run also proves capability REUSE instead of re-creation.

Run: python3 workspace/shared/testing/phase7_prompt_loop.py
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

BRAIN = "http://127.0.0.1:18000"
QUIET, BAIL, MAXW = 20, 120, 600

SPECS = [
    {"name": "Ops Pulse — CRM + fulfillment health",
     "prompt": ("Every morning check HubSpot CRM for new deals and Veeqo for unshipped orders, "
                "cross-check them, and send me one short summary. Recurring daily.")},
    {"name": "Customer Signal — email + security watch",
     "prompt": ("Watch Klaviyo email engagement and our website signup logs together; if one IP or "
                "domain creates many accounts or bounces, flag it for my approval to block. Periodical.")},
    {"name": "Fulfillment Guard — shipping SLA + report",
     "prompt": ("Track Veeqo shipments that miss their SLA, produce an exportable report for me, "
                "and keep a running history. Run on demand.")},
]


def _get(p, t=20):
    try:
        return json.load(urllib.request.urlopen(BRAIN + p, timeout=t))
    except Exception:
        return {}


def _post(p, b=None, t=120):
    r = urllib.request.Request(BRAIN + p, data=json.dumps(b or {}).encode(),
                               headers={"Content-Type": "application/json"})
    try:
        return json.load(urllib.request.urlopen(r, timeout=t))
    except Exception as e:
        return {"error": str(e)}


def _counts():
    c = psycopg2.connect(dbname="odin_core_iso"); cu = c.cursor(); o = {}
    for t in ("projects", "agents", "files", "folders", "dependencies", "project_agents"):
        cu.execute(f"SELECT count(*) FROM {t}"); o[t] = cu.fetchone()[0]
    c.close(); return o


def _msgs(pid):
    d = _get(f"/scope/messages?scope=project%3A{pid}")
    m = d.get("messages") or d.get("items") or []
    return len(m) if isinstance(m, list) else 0


def run_spec(spec) -> dict:
    base_counts, base_iss = _counts(), len(au.scan())
    t0 = time.time()

    # 1) the system PLANS from the prompt (this is the owner's intake conversation)
    plan = _post("/projects/intake", {"history": [{"role": "user", "content": spec["prompt"]}]})
    planned = bool(plan) and not plan.get("error")

    # 2+3) approve + create (we act as the owner accepting the proposal)
    created = _post("/projects", {"name": spec["name"], "description": spec["prompt"],
                                  "autoApprove": True, "cadence": "recurring"})
    pid = created.get("id") or (created.get("project") or {}).get("id")
    if not pid:
        return {"spec": spec["name"], "ok": False, "stage": "create", "detail": str(created)[:200],
                "planned": planned, "duration_sec": round(time.time() - t0, 1)}

    # 4) watch until it produces output (TIMED)
    last, chg, grew = _msgs(pid), time.time(), False
    while time.time() - t0 < MAXW:
        time.sleep(5)
        n = _msgs(pid)
        if n != last:
            last, chg, grew = n, time.time(), True
        if grew and time.time() - chg >= QUIET:
            break
        if not grew and time.time() - t0 >= BAIL:
            break
    duration = round(time.time() - t0, 1)

    # 5) AUDIT + middleware + DB
    placement = [x for x in mw.scan_violations() if f"projects/{pid}/" in x[0]]
    au.heal(force=True)
    after = au.scan()
    mine = [i for i in after if i.get("owner") == pid or str(i.get("path", "")).startswith(f"workspace/projects/{pid}/")]
    c = psycopg2.connect(dbname="odin_core_iso"); cu = c.cursor()
    cu.execute("SELECT count(*) FROM project_agents WHERE project_id=%s", (pid,)); nag = cu.fetchone()[0]
    cu.execute("SELECT count(*) FROM files WHERE owner_type='project' AND owner_id=%s", (pid,)); nfiles = cu.fetchone()[0]
    c.close()

    # 6) DELETE + prove exact baseline restore (other agents/projects untouched)
    mw.delete_owner("project", pid)
    end_counts, end_iss = _counts(), len(au.scan())
    delta = {k: end_counts[k] - base_counts[k] for k in base_counts}

    return {"spec": spec["name"], "pid": pid, "planned": planned, "produced_output": grew,
            "duration_sec": duration, "agents_linked": nag, "files_created": nfiles,
            "violations_project": len(mine), "placement_violations": len(placement),
            "violations_global_after": len(after), "delete_delta": delta,
            "clean_delete": all(v == 0 for v in delta.values()) and end_iss == base_iss,
            "ok": (not mine and not placement and all(v == 0 for v in delta.values()))}


def main():
    print("=" * 78)
    print("PHASE 7 — PROMPT-DRIVEN LOOP (create as the owner → watch → audit → delete)")
    print("=" * 78)
    print(f"start violations: {len(au.scan())}")
    out = []
    for s in SPECS:
        print("-" * 78)
        print(f"▶ PROMPT: {s['prompt'][:90]}…")
        r = run_spec(s)
        out.append(r)
        print(f"  project      : {r.get('pid')}")
        print(f"  planned      : {r.get('planned')} | produced output: {r.get('produced_output')}")
        print(f"  DURATION     : {r.get('duration_sec')}s   <-- prompt → output")
        print(f"  agents linked: {r.get('agents_linked')} | files: {r.get('files_created')}")
        print(f"  violations   : project={r.get('violations_project')} placement={r.get('placement_violations')} "
              f"global={r.get('violations_global_after')}")
        print(f"  delete delta : {r.get('delete_delta')} | clean delete: {r.get('clean_delete')}")
        print(f"  RESULT       : {'CLEAN ✅' if r.get('ok') else 'NEEDS ATTENTION ❌'}")
    print("=" * 78)
    ok = sum(1 for r in out if r.get("ok"))
    print(f"SUMMARY: {ok}/{len(out)} clean | final violations: {len(au.scan())}")
    (WS / "logs" / "prompt_loop_report.json").write_text(json.dumps(out, indent=2))
    print("report: workspace/logs/prompt_loop_report.json")
    return ok == len(out) and len(au.scan()) == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
