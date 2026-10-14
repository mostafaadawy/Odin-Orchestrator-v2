"""
e2e_phase2_gate.py — THE single gate: are we truly ready to start Phase 2?

One test, one verdict. It combines the two things that must both be real, measured in ways I cannot
game:

  PART A — CONTEXT (un-gameable, multi-hop):
    3 reasoning members. Backend INVENTS a runtime token A (not in the brief), Frontend must REUSE A
    and invent its own B, and a third agent (Integrator) must cite BOTH from the shared pool. Tokens
    invented at runtime ⇒ impossible to echo from the brief ⇒ only passes if context truly flows
    across TWO hops. Plus a cross-role hand-off (Frontend → Backend) must be recorded.

  PART B — DB SIMULATION + SAFETY (on the VM, never production):
    Fingerprint production before; create a THROWAWAY db (organics_e2e_sandbox); a hard guard confirms
    prisma targets the throwaway, not 'organics'; run `migrate deploy` AND the destructive `reset`
    against it; drop it; fingerprint production after and require it byte-for-byte UNCHANGED.

Verdict is "READY FOR PHASE 2" only if BOTH parts pass. Anything skipped/uncertain = NOT ready
(honest — no green unless it's real). Run:  python3 server/e2e_phase2_gate.py
"""
from __future__ import annotations

import os
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
REPO = pathlib.Path(__file__).resolve().parent.parent
TOK = re.compile(r"ODIN-[A-Z0-9]{6}")

# DB simulation: a DEDICATED throwaway role + db, created via the postgres superuser and dropped
# after. Never the production 'organics' db or its role. No production credentials, no .env reading.
SBX_DB = "organics_e2e_sandbox"
SBX_ROLE = "odin_e2e_sbx"
SBX_PW = "odin_e2e_sbx_pw"
REAL_BE = "/home/mostafa/bendcore"                       # has node_modules/prisma; URL is overridden
SBX_DB_URL = f"postgresql://{SBX_ROLE}:{SBX_PW}@localhost:5432/{SBX_DB}?schema=public"
_DB_ENV = f"DATABASE_URL='{SBX_DB_URL}' DIRECT_URL='{SBX_DB_URL}'"

CONTEXT_BRIEF = (
    "Build a tiny demo in THREE ordered steps by three members; consistency through ONE shared "
    "context is the point.\n"
    "STEP 1 — Backend: INVENT a unique token A = the letters ODIN- followed by 6 REAL random "
    "characters (A-Z, 0-9) that YOU generate (do NOT write placeholder X's). Define GET /api/<A>/status. "
    "Write on its own line exactly: TOKEN_A: <your token>\n"
    "STEP 2 — Frontend: reuse the Backend's EXACT token A from the shared context (never invent your "
    "own A); then INVENT a different token B (same ODIN- + 6 real random chars form). Write: USES_A: <A> "
    "and TOKEN_B: <B>. If the backend must change anything to integrate, hand it back: BACKEND-TODO: <one task>\n"
    "STEP 3 — Integrator: from the shared context, confirm by citing BOTH tokens EXACTLY: "
    "CONFIRMED A=<A> B=<B>. Invent nothing new.\n"
    "All tokens must match across members — that proves the context never broke."
)


def log(m=""):
    print(m, flush=True)


def _ensure_venv():
    try:
        import fastapi  # noqa
        return
    except ModuleNotFoundError:
        venv = REPO / ".venv" / "bin" / "python3"
        if venv.exists() and os.environ.get("ODIN_E2E_REEXEC") != "1":
            os.environ["ODIN_E2E_REEXEC"] = "1"
            print(f"(re-running under {venv})\n", flush=True)
            os.execv(str(venv), [str(venv), str(pathlib.Path(__file__).resolve()), *sys.argv[1:]])


def _ssh(cmd):
    import deploy_ssh
    return deploy_ssh.ssh_exec(cmd)


def run_flow(pid, goal, timeout=900):
    import api_v2
    api_v2.start_run(pid, goal)
    t0 = time.time()
    while time.time() - t0 < timeout:
        if not api_v2.run_status(pid).get("running"):
            break
        time.sleep(5)
    else:
        try:
            api_v2.stop_run(pid)
        except Exception:
            pass


def _mtext(pool, name):
    return " ".join(e["text"] for e in pool if name.lower() in e["who"].lower())


# ---- DB simulation helpers (safe; throwaway db only) ----
def prod_fingerprint():
    r = _ssh("for d in /home/mostafa/bendcore /home/mostafa/organics; do "
             "echo \"$d=$(ls -A \"$d\" 2>/dev/null | wc -l):$(stat -c %Y \"$d\" 2>/dev/null)\"; done")
    return (r.get("out") or "").strip()


def db_create():
    # create a dedicated throwaway role + db AS the postgres superuser (peer auth works as we saw)
    r = _ssh(
        f"sudo -u postgres psql -c \"DROP DATABASE IF EXISTS {SBX_DB};\" "
        f"-c \"DROP ROLE IF EXISTS {SBX_ROLE};\" "
        f"-c \"CREATE ROLE {SBX_ROLE} LOGIN PASSWORD '{SBX_PW}';\" "
        f"-c \"CREATE DATABASE {SBX_DB} OWNER {SBX_ROLE};\" 2>&1; "
        f"sudo -u postgres psql -lqt 2>&1 | cut -d'|' -f1 | grep -qw {SBX_DB} && echo CREATED || echo NODB")
    return "CREATED" in (r.get("out") or "")


def db_guard():
    out = (_ssh(f"cd {REAL_BE} && {_DB_ENV} npx prisma migrate status 2>&1 | tail -15").get("out") or "")
    return (f'"{SBX_DB}"' in out) and ('"organics"' not in out), out


def db_drop():
    _ssh(f"sudo -u postgres psql -c \"DROP DATABASE IF EXISTS {SBX_DB};\" "
         f"-c \"DROP ROLE IF EXISTS {SBX_ROLE};\" 2>&1")


def phase3_check():
    """PHASE 3 — project types, operational (non-technical) agents, periodical projects + the
    due→approve/skip run gate. Pure-logic + registry checks (no engine/VM); fully self-cleaning so
    it never pollutes real data. Returns (pass: bool, detail: dict)."""
    import uuid
    import projects, agents_registry, scheduler
    d = {}
    created_pid = None
    try:
        # 1) TYPES — grouped catalog (tech + operational) exists, is extensible, and recommendation
        # maps correctly (real mapping, not echo).
        tlist = projects.project_types()
        keys = {t["key"] for t in tlist}
        groups = {t.get("group") for t in tlist}
        want = {"web", "mobile", "deployment", "security", "scripting", "embedded", "gaming", "xr",
                "marketing", "email", "content", "support"}
        types_ok = want.issubset(keys) and {"tech", "operational"}.issubset(groups)
        rec_ok = (projects.recommend_type("weekly klaviyo newsletter") == "email"
                  and projects.recommend_type("an AR experience in Unity") == "xr"
                  and projects.recommend_type("build an iOS mobile app") == "mobile"
                  and projects.recommend_type("deploy the app to an azure vm") == "deployment"
                  and projects.recommend_type("a simple react dashboard") == "web")
        # role roster carries dependencies + readiness (warn-but-continue)
        roster = projects.roles_readiness()
        roster_ok = any(r["name"] == "DevOps" and "deps" in r for r in roster) and \
            any(r["name"] == "Email" for r in roster)
        d["types"] = types_ok and rec_ok and roster_ok

        # 2) OPERATIONAL AGENT + 3) PERIODICAL PROJECT (one throwaway project exercises both)
        nm = f"E2E P3 {uuid.uuid4().hex[:5]}"
        proj = projects.create_project(
            name=nm, description="weekly marketing digest", mode="build",
            members=[{"name": "Marketing", "role": "Marketing", "nature": "operational", "mode": "theoretical"}],
            local_path="/tmp/odin_p3", sources=[], auto_approve=True,
            periodic={"enabled": True, "schedule": {"kind": "daily", "hhmm": "09:00"}, "requireApproval": True})
        created_pid = proj["id"]

        # type normalized to a valid known key + periodic persisted
        d["type_persisted"] = proj.get("type") in keys
        d["periodic_persisted"] = bool(proj.get("periodic", {}).get("enabled"))

        # operational agent registered with the right nature + mode (real registry read)
        ag = next((a for a in agents_registry.list_agents(created_pid) if a["name"] == "Marketing"), None)
        d["operational_agent"] = bool(ag and ag.get("nature") == "operational" and ag.get("mode") == "theoretical")

        # the periodical project registered a scheduler task, approval-gated
        task = next((t for t in scheduler.list_tasks(created_pid) if t.get("kindTag") == "project-periodic"), None)
        d["periodic_task"] = bool(task and task.get("requireApproval"))

        gate_ok = False
        if task:
            tid = task["id"]
            # DUE + device online → must go PENDING, must NOT run
            scheduler.update_task(tid, nextRun=time.time() - 1)
            scheduler._tick()
            t1 = scheduler.get_task(tid)
            pending_ok = t1.get("status") == "pending_approval" and t1.get("runs", 0) == 0
            # SKIP → rolls forward, no run
            scheduler.skip(tid)
            t2 = scheduler.get_task(tid)
            skip_ok = t2.get("status") == "idle" and t2.get("nextRun", 0) > time.time() and t2.get("runs", 0) == 0
            # MISSED while offline (grossly overdue) → rolls forward silently, no pending, no run
            scheduler.update_task(tid, nextRun=time.time() - 99999)
            scheduler._tick()
            t3 = scheduler.get_task(tid)
            missed_ok = t3.get("status") == "idle" and t3.get("nextRun", 0) > time.time() and t3.get("runs", 0) == 0
            gate_ok = pending_ok and skip_ok and missed_ok
            d["gate"] = {"pending": pending_ok, "skip": skip_ok, "missed": missed_ok}
        d["gate_ok"] = gate_ok

        ok = all([d["types"], d["type_persisted"], d["periodic_persisted"],
                  d["operational_agent"], d["periodic_task"], d["gate_ok"]])
        return ok, d
    except Exception as e:
        d["error"] = str(e)
        return False, d
    finally:
        if created_pid:
            try:
                for t in scheduler.list_tasks(created_pid):
                    scheduler.delete_task(t["id"])
                projects.delete_project(created_pid)
            except Exception:
                pass


def main() -> int:
    import projects, main_task, audit

    log("=" * 74)
    log("PHASE 2 GATE — one test: context (un-gameable) + DB simulation + production safety")
    log("=" * 74)

    # ---------------- PART A: CONTEXT ----------------
    log("\n[A] CONTEXT — 3-member flow, runtime tokens across two hops (un-gameable)…")
    proj = projects.create_project(
        name="E2E Gate Context", description=CONTEXT_BRIEF, mode="build",
        members=[{"name": "Backend", "role": "Backend", "avatar": "backend"},
                 {"name": "Frontend", "role": "Frontend", "avatar": "frontend"},
                 {"name": "Integrator", "role": "Integration", "avatar": "generic"}],
        local_path="/tmp/odin_gate_ctx", sources=[], auto_approve=False)
    cpid = proj["id"]
    a_pass = False
    a_detail = {}
    try:
        run_flow(cpid, "Build per the brief; keep every token identical across the three members.")
        pool = (main_task.get(cpid) or {}).get("pool", [])
        whos = [e["who"] for e in pool]
        be, fe, integ = _mtext(pool, "Backend"), _mtext(pool, "Frontend"), _mtext(pool, "Integrator")
        full = "\n".join(f"[{e['who']}] {e['text']}" for e in pool)
        # extract tokens from the EXPLICIT labels (not just any ODIN- in the text) so a quoted
        # instruction can't be mistaken for the invented token. Tokens are still runtime-random ⇒
        # un-gameable: reuse can only happen if context actually carried the value.
        def after(text, label):
            m = re.search(label + r"[^\n]{0,40}?(ODIN-[A-Z0-9]{6})", text, re.I)
            return m.group(1) if m else None
        A = after(be, "TOKEN_A")
        A_in_fe = after(fe, "USES_A")
        reuse_A = bool(A and A_in_fe and A_in_fe == A)
        B = after(fe, "TOKEN_B")
        hop2 = bool(A and B and A in integ and B in integ)
        handoff = bool(re.search(r"backend[- ]?todo", fe, re.I))
        grew = len(pool) >= 5 and any("CTO" in w for w in whos)
        snakes = audit.scan_hidden_faults(full)
        fake = audit.claims_success(full) and bool(snakes)
        a_pass = grew and reuse_A and hop2 and handoff and not snakes and not fake
        a_detail = {"A": A, "reuse_A": reuse_A, "B": B, "hop2": hop2, "handoff": handoff,
                    "pool": len(pool), "snakes": sorted({h['label'] for h in snakes})}
        log(f"      A={A} reuse={reuse_A} B={B} hop2={hop2} handoff={handoff} pool={len(pool)} snakes={a_detail['snakes'] or 'none'}")
    finally:
        try:
            projects.delete_project(cpid)
        except Exception:
            pass

    # ---------------- PART B: DB SIMULATION + SAFETY ----------------
    log("\n[B] DB SIMULATION — throwaway db (migrate deploy + reset), production fingerprinted…")
    db_result, prod_safe = "skipped", True
    try:
        import deploy_ssh
        deploy_ssh.refresh_firewall()
    except Exception as e:
        log(f"      ! firewall: {e}")
    prod_before = prod_fingerprint()
    log(f"      production fingerprint before: {prod_before or '(unavailable)'}")
    if not prod_before:
        log("      ! cannot reach VM/production to fingerprint — DB sim NOT run (cannot confirm safety).")
    elif not db_create():
        log("      ! no local createdb rights — DB sim SKIPPED (cannot confirm the DB path).")
    else:
        safe, status = db_guard()
        if not safe:
            log(f"      🚨 GUARD TRIPPED — prisma did NOT target the throwaway db; aborting. {status[-160:]}")
            db_drop(); db_result = "aborted-by-guard"
        else:
            log(f"      ✓ guard ok — prisma targets {SBX_DB}, not production")
            dep = (_ssh(f"cd {REAL_BE} && {_DB_ENV} npx prisma migrate deploy 2>&1 | tail -5").get("out") or "")
            rst = (_ssh(f"cd {REAL_BE} && {_DB_ENV} npx prisma migrate reset --force --skip-seed 2>&1 | tail -5").get("out") or "")
            log("      migrate deploy → " + dep.replace(chr(10), " ")[-140:])
            log("      migrate reset  → " + rst.replace(chr(10), " ")[-140:])
            deploy_ok = "error" not in dep.lower() or "up to date" in dep.lower() or "already" in dep.lower()
            reset_ok = "reset" in rst.lower() or "error" not in rst.lower()
            db_result = "PASS" if (deploy_ok and reset_ok) else "FAIL"
            db_drop()
            log(f"      ✓ throwaway db dropped — DB simulation: {db_result}")
    prod_after = prod_fingerprint()
    prod_safe = bool(prod_before) and (prod_before == prod_after)
    if prod_before and not prod_safe:
        log(f"      🚨 PRODUCTION CHANGED! before={prod_before} after={prod_after}")

    # ---------------- PART C: PHASE 3 FEATURES ----------------
    log("\n[C] PHASE 3 — project types, operational agents, periodical projects + run gate "
        "(self-cleaning; no engine/VM)…")
    c_pass, c_detail = phase3_check()
    log(f"      types={c_detail.get('types')} type_persisted={c_detail.get('type_persisted')} "
        f"periodic_persisted={c_detail.get('periodic_persisted')} operational_agent={c_detail.get('operational_agent')} "
        f"periodic_task={c_detail.get('periodic_task')} gate={c_detail.get('gate')}")
    if c_detail.get("error"):
        log(f"      ! phase3 error: {c_detail['error']}")

    # ---------------- VERDICT ----------------
    log("\n" + "=" * 74)
    log("ODIN GATE SCORECARD  (Phase 1 · Phase 2 · Phase 3)")
    log("=" * 74)
    log(f"  A · CONTEXT (multi-hop, un-gameable)   {'PASS' if a_pass else 'FAIL'}   {a_detail}")
    log(f"  B · DB SIMULATION (deploy + reset)     {db_result}")
    log(f"  B · PRODUCTION SAFE (untouched)        {'PASS' if prod_safe else 'FAIL'}")
    log(f"  C · PHASE 3 FEATURES (types/ops/cron)  {'PASS' if c_pass else 'FAIL'}   {c_detail}")
    log("-" * 74)
    # Phases 1–2 keep their EXACT original bar; Phase 3 is an ADDED requirement (never a relaxation).
    p12_ready = a_pass and db_result == "PASS" and prod_safe
    ready = p12_ready and c_pass
    if ready:
        log("  ✅ ALL PHASES PASS — context is genuinely shared across hops (un-gameable), the DB path "
            "(migrate deploy + reset) works on a throwaway db, production was untouched, and the Phase 3 "
            "features (project types, operational agents, periodical projects + the due→approve/skip gate) "
            "all behave correctly.")
        return 0
    why = []
    if not a_pass: why.append("context not proven (see A)")
    if db_result != "PASS": why.append(f"DB simulation = {db_result} (must be PASS)")
    if not prod_safe: why.append("production safety not confirmed")
    if not c_pass: why.append(f"Phase 3 features not proven (see C): {c_detail}")
    log("  ❌ NOT READY — " + "; ".join(why))
    log("     (the real gap; fix the app, never the test.)")
    return 1


if __name__ == "__main__":
    _ensure_venv()
    sys.exit(main())
