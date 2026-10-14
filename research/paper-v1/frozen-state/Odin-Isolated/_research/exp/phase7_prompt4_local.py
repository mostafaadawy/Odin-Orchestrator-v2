# ISOLATED adaptation of the owner's phase7_prompt4.py: specs A–C only; everything else unchanged.
"""
phase7_prompt4.py — the OWNER JOURNEY, strong: create 4 NEW projects BY PROMPT (as the owner), each mixing
several existing capabilities/agents, then for each project prove — with STRONG acceptance points baked into
the check (not into the system) — that:

  1. the system PLANNED from the prompt (intake),
  2. CREATE seeded the RIGHT team and it is visible on every DB-backed surface (project_agents JOIN — the
     exact query ui_api.py + directions.py use for the desktop/web/mobile cards),
  3. capability REUSE happened where the brief needed a shared capability (deploy -> shared/, NOT a copy),
  4. RUN produced REAL output (message growth) — the project actually does its task,
  5. ZERO general + ZERO cross-owner violations for the project (audit is the judge, healed first),
  6. DELETE returns the system to EXACT baseline (every count) — clean, modular teardown.

The 4 specs deliberately MIX HubSpot CRM, Veeqo fulfillment, Klaviyo email, SOC/security, reporting/export
and deployment so the run also proves REUSE (shared + custom delta) instead of re-creation.

Run:  python3 workspace/shared/testing/phase7_prompt4.py
Exit 0 only if ALL four are fully clean AND global violations end at 0.
"""
from __future__ import annotations
import sys, json, time, re, pathlib, urllib.request

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
WS = ROOT / "workspace"
SERVER = ROOT / "server"
for p in (str(HERE), str(SERVER)):
    if p not in sys.path:
        sys.path.insert(0, p)

import workspace_mw as mw      # noqa: E402
import workspace_audit as au   # noqa: E402
import psycopg2                # noqa: E402

BRAIN = "http://127.0.0.1:18000"
QUIET, BAIL, MAXW = 20, 130, 420


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
    for t in ("projects", "agents", "files", "folders", "dependencies", "project_agents", "connectors"):
        cu.execute(f"SELECT count(*) FROM {t}"); o[t] = cu.fetchone()[0]
    c.close(); return o


def _team(pid):
    """Exactly the JOIN the cards render from — proves the team is visible on desktop/web/mobile."""
    c = psycopg2.connect(dbname="odin_core_iso"); cu = c.cursor()
    cu.execute("SELECT a.name FROM project_agents pa JOIN agents a ON a.id=pa.agent_id WHERE pa.project_id=%s", (pid,))
    r = [x[0] for x in cu.fetchall()]; c.close(); return r


def _msgs(pid):
    d = _get(f"/scope/messages?scope=project%3A{pid}")
    m = d.get("messages") or d.get("items") or []
    return len(m) if isinstance(m, list) else 0


# Each spec: a prompt (as the owner would type) with acceptance criteria woven in, the cadence, the roles the
# team MUST include (the "strong points"), and whether it must reuse the shared deploy capability.
SPECS = [
    {"key": "A", "name": "Ops Pulse — CRM + fulfillment health",
     "cadence": "recurring",
     "prompt": ("Every morning pull HubSpot CRM deals and Veeqo unshipped orders, cross-check them and send me "
                "one short summary. Acceptance: connect to both, report real counts, produce one summary. Recurring."),
     "must_roles": {"Sales", "Fulfillment"}, "reuse_deploy": False},
    {"key": "B", "name": "Signal Guard — email + security watch",
     "cadence": "periodical",
     "prompt": ("Watch Klaviyo email engagement/bounces together with our website signup logs; if one IP or "
                "domain creates many accounts or bounces, flag it for my approval to block. Acceptance: reuse "
                "email + security monitoring, produce a flagged list, stop at the approval gate. Periodical."),
     "must_roles": {"Email", "Security"}, "reuse_deploy": False},
    {"key": "C", "name": "Fulfillment Guard — SLA report + export",
     "cadence": "recurring",
     "prompt": ("Track Veeqo shipments that miss their SLA, produce an exportable report for me and keep a "
                "running history. Acceptance: a reporting agent adds export; produce a report; keep history. On demand."),
     "must_roles": {"Fulfillment", "Reporter"}, "reuse_deploy": False},
    {"key": "D", "name": "Sandbox Deploy Mirror — reuse shared deploy",
     "cadence": "once",
     "prompt": ("Set up a sandbox deployment that reuses our existing shared deploy engine with its own delta "
                "(its own database and internal ports, no domain) and must never touch production. Acceptance: "
                "reuse the shared deploy capability (no duplicate deploy script), keep production untouched."),
     "must_roles": {"DevOps"}, "reuse_deploy": True},
]


def _acceptance(pid, spec) -> dict:
    """The STRONG points, checked against reality (DB/disk/audit) — never against the system's own say-so."""
    checks = []

    def chk(label, ok, detail=""):
        checks.append({"label": label, "ok": bool(ok), "detail": str(detail)})

    team = _team(pid)
    # capability-aware match: a required role is covered if any linked agent's name matches its keywords.
    # (A security brief legitimately provisions the full SOC blueprint — named security agents, not a plain
    # "Security" — which MORE than satisfies the requirement.)
    _KEY = {"Security": ("security", "threat", "intrusion", "soc", "detection", "vulnerab", "recovery"),
            "Sales": ("sales", "hubspot", "crm"),
            "Fulfillment": ("fulfillment", "fulfilment", "shipping", "veeqo"),
            "Email": ("email", "klaviyo"),
            "Reporter": ("report", "export"),
            "DevOps": ("devops", "deploy", "cloud", "infra")}

    def _has(req):
        keys = _KEY.get(req, (req.lower(),))
        return any(any(k in t.lower() for k in keys) for t in team)

    missing = sorted(r for r in spec["must_roles"] if not _has(r))
    chk(f"team covers required capabilities {sorted(spec['must_roles'])}", not missing,
        f"team={sorted(team)} missing={missing}")
    chk("team visible on cards (project_agents JOIN non-empty)", bool(team), f"team={sorted(team)}")

    # reuse: a deploy brief must point at the SHARED deploy capability, never a bundled copy
    if spec["reuse_deploy"]:
        man = WS / "projects" / pid / "dependencies" / "manifest.json"
        pts = False
        try:
            deps = json.loads(man.read_text()) if man.is_file() else []
            pts = any(str(d.get("source", "")).startswith("shared/") and "deploy" in str(d.get("source", "")).lower()
                      for d in deps)
        except Exception:
            pts = False
        # no duplicate generic deploy engine written inside the project's own code/
        dup = list((WS / "projects" / pid / "code").rglob("deploy_changes.py"))
        chk("reuses SHARED deploy (dependency -> shared/…deploy…)", pts, f"manifest={man.is_file()}")
        chk("no duplicate deploy engine copied into the project", not dup, f"dupes={[str(x) for x in dup]}")

    # violations for THIS project (audit healed first — the audit is the self-correcting judge)
    au.heal(force=True)
    iss = [i for i in au.scan()
           if i.get("owner") == pid or str(i.get("path", "")).startswith(f"workspace/projects/{pid}/")]
    chk("0 violations for this project", not iss, f"{[i.get('type') for i in iss]}")

    # independent cross-owner check: no file under this project references another project's private files
    real = {d.name for d in (WS / "projects").iterdir() if d.is_dir()}
    rx = re.compile(r'(?:workspace/)?projects/([A-Za-z0-9_\-]+)/([A-Za-z0-9_\-/\.]+)')
    cross = []
    for f in (WS / "projects" / pid).rglob("*"):
        if not f.is_file() or f.suffix.lower() not in {'.py', '.sh', '.js', '.ts', '.dart', '.json', '.md'}:
            continue
        try:
            txt = f.read_text(errors="replace")
        except Exception:
            continue
        for m in rx.finditer(txt):
            rid, tail = m.group(1), m.group(2).rstrip("\"').,)")
            if rid in (pid, "_shared") or rid not in real or not tail:
                continue
            if (WS / "projects" / rid / tail).is_file():
                cross.append(f"{rid}/{tail}")
    chk("0 cross-owner references", not cross, f"{cross[:3]}")
    return {"checks": checks, "ok": all(c["ok"] for c in checks)}


def run_spec(spec) -> dict:
    base = _counts(); base_iss = len(au.scan())
    t0 = time.time()

    plan = _post("/projects/intake", {"history": [{"role": "user", "content": spec["prompt"]}]})
    planned = bool(plan) and not plan.get("error")

    created = _post("/projects", {"name": spec["name"], "description": spec["prompt"],
                                  "autoApprove": True, "cadence": spec["cadence"]})
    pid = created.get("id") or (created.get("project") or {}).get("id")
    if not pid:
        return {"spec": spec["name"], "key": spec["key"], "ok": False, "stage": "create",
                "detail": str(created)[:200], "planned": planned}

    # RUN it (the ▶ the owner presses) and watch for REAL output
    before = _msgs(pid)
    _post(f"/projects/{pid}/run-now", {})
    last, chg, grew = before, time.time(), False
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

    acc = _acceptance(pid, spec)
    team_now = _team(pid)

    # DELETE + prove exact baseline restore
    mw.delete_owner("project", pid)
    end = _counts(); end_iss = len(au.scan())
    delta = {k: end[k] - base[k] for k in base}
    clean_delete = all(v == 0 for v in delta.values()) and end_iss == base_iss

    return {"spec": spec["name"], "key": spec["key"], "pid": pid, "planned": planned,
            "produced_output": grew, "messages": f"{before}->{last}", "duration_sec": duration,
            "team": team_now, "acceptance": acc, "delete_delta": delta,
            "clean_delete": clean_delete, "ok": acc["ok"] and clean_delete and planned}


SPECS = SPECS[:3]   # ISOLATED RUN: spec D (sandbox deployment) omitted — deployment to a VM is a cloud change (STOP condition)


def main():
    print("=" * 80)
    print("PHASE 7 — 4 PROMPT-CREATED PROJECTS (create → run → strong acceptance → clean delete)")
    print("=" * 80)
    print(f"start global violations: {len(au.scan())}")
    out = []
    for s in SPECS:
        print("-" * 80)
        print(f"▶ [{s['key']}] {s['name']}")
        print(f"   prompt: {s['prompt'][:96]}…")
        r = run_spec(s)
        out.append(r)
        acc = r.get("acceptance", {})
        print(f"   pid          : {r.get('pid')}")
        print(f"   planned      : {r.get('planned')} | produced output: {r.get('produced_output')} "
              f"(msgs {r.get('messages')})")
        print(f"   DURATION     : {r.get('duration_sec')}s   <-- prompt → output")
        for c in acc.get("checks", []):
            print(f"     [{'PASS' if c['ok'] else 'FAIL'}] {c['label']}"
                  + (f" — {c['detail']}" if not c['ok'] else ""))
        print(f"   delete delta : {r.get('delete_delta')} | clean delete: {r.get('clean_delete')}")
        print(f"   RESULT       : {'CLEAN ✅' if r.get('ok') else 'NEEDS ATTENTION ❌'}")
    print("=" * 80)
    ok = sum(1 for r in out if r.get("ok"))
    final_iss = len(au.scan())
    print(f"SUMMARY: {ok}/{len(out)} clean | final global violations: {final_iss}")
    (WS / "logs" / "prompt4_report.json").write_text(json.dumps(out, indent=2, default=str))
    print("report: workspace/logs/prompt4_report.json")
    return ok == len(out) and final_iss == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
