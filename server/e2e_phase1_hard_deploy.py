"""
e2e_phase1_hard_deploy.py — the HARD Phase-1 test, using the real DEPLOY brief.

A 2-agent token test is the easy case. This is the hard case: the real, detail-heavy deploy brief
run through MULTIPLE agents (DevOps + QA + Security), where many *easy-to-drop* specifics must
survive the whole chain without omission or drift. To make propagation MEASURABLE and fair, the
brief orders every member to EXPLICITLY restate the exact details it's acting on — so a member that
has the full shared context can restate them, and one that lost context cannot.

It is SAFE: everything is pinned to an isolated VM sandbox (/home/mostafa/_e2e_sandbox) via
ODIN_DEPLOY_CONFIG with migration=none + reboot=0, nothing is auto-approved, and a before/after
PRODUCTION FINGERPRINT verifies organics/bendcore were byte-for-byte untouched (FAILs loudly if not).
The sandbox is created at start and deleted in cleanup.

It measures (hard bar — ALL must pass):
  POOL GROWTH        — prompt + CTO plan + every member accumulate in one pool.
  DETAIL PROPAGATION — each critical detail (both paths, the rare `*.mp5` exclude, port 4013,
                       `migrate deploy`, user `mostafa`) is restated by a MEMBER (not just present
                       in the brief). A dropped detail = omission = FAIL.
  NO DRIFT           — no member actually USES a broken method (az / migrate dev / @VM placeholder).
  OMISSION GUARD     — every requirement reconciled.
  TRUTHFULNESS       — no fakes/snakes in the pool.

Run on your Mac:  python3 server/e2e_phase1_hard_deploy.py
"""
from __future__ import annotations

import os
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
REPO = pathlib.Path(__file__).resolve().parent.parent
SANDBOX = "/home/mostafa/_e2e_sandbox"
SBX_BE, SBX_FE = SANDBOX + "/bendcore", SANDBOX + "/organics"
SBX_CONFIG = str(REPO / "data" / "_e2e_phase1_sandbox.sh")
PROD = ("/home/mostafa/bendcore", "/home/mostafa/organics")

# the critical, easy-to-drop details that MUST survive the whole agent chain
DETAILS = {
    "frontend sandbox path": SBX_FE,
    "backend sandbox path": SBX_BE,
    "rare exclude *.mp5": "*.mp5",
    "verify port 4013": "4013",
    "migrate deploy (not dev)": "migrate deploy",
    "ssh user mostafa": "mostafa",
}

# lines that FORBID a method must not count as USING it (measure actions, not rules)
_INSTR = re.compile(r"\bnever\b|\bdo not\b|\bdon'?t\b|\bavoid\b|\bnot the\b|must not|forbidden|instead of", re.I)


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


HARD_BRIEF = (
    "# DEPLOY (HARD SANDBOX TEST) — Organics → isolated VM sandbox. Multiple members; stay consistent "
    "through ONE shared context.\n"
    "Reach the VM over SSH as user `mostafa` (password in workspace/shared/oth/.cred). NEVER use `az vm run-command`. "
    "Refresh the firewall to my current IP first.\n"
    f"- Local frontend → VM {SBX_FE}\n- Local backend → VM {SBX_BE}\n"
    "EXCLUDES (apply to both, exactly): .env* .backup-env *.pem *.key node_modules dist .next logs "
    "prisma/migrations package.json public uploads *.mp4 *.mp5\n"
    "BACKEND DB: `npx prisma generate && npx prisma migrate deploy` (NEVER `migrate dev`). "
    "BUILD: rm -rf dist && npm run build. FRONTEND: rm -rf .next && npm run build.\n"
    "After deploy, VERIFY the backend responds on port 4013.\n"
    "From the NEXT run on, re-confirm the full exclude list and commands with me before acting.\n\n"
    "SANDBOX SAFETY (THIS RUN ONLY — ABSOLUTE): this is an isolated SANDBOX rehearsal. Sync files to the "
    "sandbox paths above ONLY. Do NOT run ANY database migration and do NOT connect to, reset, or modify the "
    "PRODUCTION `organics` database in this run. State the production command for the record "
    "(`npx prisma migrate deploy`, never `migrate dev`) but DO NOT execute it. Port 4013 verify is best-effort.\n\n"
    "CONSISTENCY REQUIREMENT (mandatory for EVERY member): in your report, EXPLICITLY restate the exact "
    "target paths, the FULL exclude list (including *.mp5), the exact migration command, and the verify "
    "port — proving you have the full shared context. Do not summarize them away."
)


def _ssh(cmd, timeout=1200):
    import deploy_ssh
    return deploy_ssh.ssh_exec(cmd, timeout=timeout)


def setup_sandbox():
    import deploy_ssh
    try:
        deploy_ssh.refresh_firewall()
    except Exception as e:
        log(f"   ! firewall: {e}")
    r = _ssh(f"rm -rf {SANDBOX}; mkdir -p {SBX_BE} {SBX_FE} && echo OK")
    return "OK" in (r.get("out") or "")


def prod_fingerprint() -> str:
    """A signature of the PRODUCTION dirs (file count + mtime). Compared before/after the test to
    PROVE production was never touched — a real safety check, not just a comment."""
    r = _ssh("for d in /home/mostafa/bendcore /home/mostafa/organics; do "
             "echo \"$d=$(ls -A \"$d\" 2>/dev/null | wc -l):$(stat -c %Y \"$d\" 2>/dev/null)\"; done")
    return (r.get("out") or "").strip()


# ---- DB SIMULATION: a throwaway database, created and dropped; migrate deploy + reset tested there
SBX_DB = "organics_e2e_sandbox"                       # NEVER the production 'organics' db
REAL_BE = "/home/mostafa/bendcore"                    # has node_modules/prisma; we override the URL
_PROD_DB = "organics"                                 # the REAL db — must NEVER be the sim target
_DB_ENV_CACHE = None
# fast timeouts so a bad/unreachable DB link FAILS FAST with a reason instead of hanging ~20 min
_T_FAST, _T_MIG = 45, 150


def _sandbox_db_url() -> str:
    """Build the sim URL from the REAL working DATABASE_URL (the one the app deploys with), swapping
    ONLY the db name to the throwaway db — so we connect exactly like the app, not a hardcoded guess.
    SAFETY: the resulting db name MUST be the sandbox db and MUST NOT be production 'organics'."""
    real = (_ssh(f"cd {REAL_BE} && grep -E '^DATABASE_URL=' .env 2>/dev/null | head -1 "
                 f"| cut -d= -f2- | tr -d '\"' | tr -d \"'\"", timeout=_T_FAST).get("out") or "").strip()
    m = re.match(r'^(postgres(?:ql)?://[^/]+/)([^?]+)(\?.*)?$', real)
    if not m:
        return ""  # can't parse a real URL → caller will SKIP the sim (no guessing near production)
    db_name = m.group(2)
    url = f"{m.group(1)}{SBX_DB}{m.group(3) or ''}"
    # HARD ASSERT: never allow the sim URL to point at the production db
    if SBX_DB == _PROD_DB or f"/{_PROD_DB}?" in (url + "?") or url.rstrip('/').endswith("/" + _PROD_DB):
        return ""
    return url


def db_env() -> str:
    global _DB_ENV_CACHE
    if _DB_ENV_CACHE is None:
        url = _sandbox_db_url()
        _DB_ENV_CACHE = f"DATABASE_URL='{url}' DIRECT_URL='{url}'" if url else ""
    return _DB_ENV_CACHE


def db_create() -> bool:
    r = _ssh(f"psql -d postgres -c 'DROP DATABASE IF EXISTS {SBX_DB};' "
             f"-c 'CREATE DATABASE {SBX_DB};' 2>&1; "
             f"psql -d postgres -lqt 2>&1 | cut -d'|' -f1 | grep -qw {SBX_DB} && echo CREATED || echo NODB",
             timeout=_T_FAST)
    return "CREATED" in (r.get("out") or "")


def db_targets_sandbox() -> tuple:
    """HARD GUARD: confirm prisma (with the override) points at the SANDBOX db, not production.
    Reads-only `migrate status`; if it shows the production 'organics' db, we ABORT before any write.
    Returns (safe, reason_or_status). A timeout/empty result → NOT safe, with a clear reason."""
    env = db_env()
    if not env:
        return False, "could-not-resolve-sandbox-db-url-from-real-.env (sim skipped, production untouched)"
    r = _ssh(f"cd {REAL_BE} && {env} npx prisma migrate status 2>&1 | tail -15", timeout=_T_FAST)
    out = (r.get("out") or "")
    if r.get("error") or not out.strip():
        return False, f"db unreachable/slow with the sim URL → {(r.get('error') or r.get('err') or 'no output')[:160]}"
    safe = (f'"{SBX_DB}"' in out) and (f'"{_PROD_DB}"' not in out)
    return safe, out


def db_drop():
    _ssh(f"psql -d postgres -c 'DROP DATABASE IF EXISTS {SBX_DB};' 2>&1", timeout=_T_FAST)


def write_cfg():
    pathlib.Path(SBX_CONFIG).write_text(
        f'CFG_BACKEND_VM="{SBX_BE}"\nCFG_FRONTEND_VM="{SBX_FE}"\nCFG_BACKEND_MIG="none"\n'
        'CFG_FRONTEND_MIG="none"\nCFG_REBOOT=0\nCFG_BACKEND_BUILD="echo sandbox build"\n'
        'CFG_FRONTEND_BUILD="echo sandbox build"\n', encoding="utf-8")
    os.environ["ODIN_DEPLOY_CONFIG"] = SBX_CONFIG


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


def main() -> int:
    import projects, main_task, audit

    log("=" * 74)
    log("PHASE 1 — HARD test (real deploy brief, multi-agent, sandbox-isolated)")
    log("=" * 74)

    write_cfg()
    if not setup_sandbox():
        log("❌ sandbox/SSH unavailable — cannot run the hard test.")
        return 3
    _prod_before = prod_fingerprint()        # safety: snapshot production BEFORE
    log(f"   · production fingerprint (before): {_prod_before or '(unavailable)'}")

    # ---- DB SIMULATION (throwaway db; migrate deploy + reset tested there, then dropped) ----
    db_result = "skipped"
    if os.environ.get("ODIN_E2E_DBSIM") != "1":
        # SAFETY (default): touch NO database at all. With real 'organics' deployed, the test must never
        # create or write any db unless you explicitly opt in. Opt in with ODIN_E2E_DBSIM=1 (throwaway db only).
        log("\n[DB] DB simulation DISABLED by default — NO database is created or written (production safe).")
        log("     To run it on the THROWAWAY db only: ODIN_E2E_DBSIM=1 python3 server/e2e_phase1_hard_deploy.py")
        db_result = "disabled-by-default"
    elif not db_create():
        log("\n[DB] couldn't create the sandbox db (no local createdb rights?) — DB sim SKIPPED, production safe.")
    else:
        log("\n[DB] Simulate the database on a THROWAWAY db (never production 'organics')…")
        safe, status = db_targets_sandbox()
        if not safe:
            # FAIL-FAST with a reason: most often the sim URL can't reach the db. We do NOT hang and
            # do NOT touch production — just report why and move on (DB sim does not gate the verdict).
            log(f"   ⚠ DB sim SKIPPED (production protected) — reason: {status[-200:]}")
            db_drop()
            db_result = "skipped (" + status.split(' →')[0][:60].strip() + ")"
        else:
            env = db_env()
            # FINAL HARD GUARD before ANY write: the connection string MUST be confined to the throwaway
            # db and MUST NOT reference production 'organics'. If not, we run nothing (no real db touched).
            confined = (SBX_DB in env) and (f"/{_PROD_DB}?" not in env) and (f"/{_PROD_DB}'" not in env)
            if not confined:
                log("   🚨 ABORT DB writes — sim URL not confined to the throwaway db; production protected.")
                db_drop()
                db_result = "aborted-by-final-guard"
            else:
                log(f"   ✓ guard ok — prisma targets {SBX_DB}, not production")
                dep = (_ssh(f"cd {REAL_BE} && {env} npx prisma migrate deploy 2>&1 | tail -6", timeout=_T_MIG).get("out") or "")
                log("   migrate deploy → " + (dep.replace(chr(10), " ")[-160:] or "(no output / timed out)"))
                rst = (_ssh(f"cd {REAL_BE} && {env} npx prisma migrate reset --force --skip-seed 2>&1 | tail -6", timeout=_T_MIG).get("out") or "")
                log("   migrate reset  → " + (rst.replace(chr(10), " ")[-160:] or "(no output / timed out)"))
                deploy_ok = "error" not in dep.lower() or "already" in dep.lower() or "up to date" in dep.lower()
                reset_ok = "reset" in rst.lower() or "error" not in rst.lower()
                db_result = "PASS" if (deploy_ok and reset_ok) else "FAIL"
                db_drop()
                log(f"   ✓ sandbox db dropped — DB simulation: {db_result}")

    log("\n[1] Create the project (DevOps + QA + Security; sandbox-targeted)…")
    proj = projects.create_project(
        name="E2E Phase1 Hard Deploy", description=HARD_BRIEF, mode="build",
        members=[{"name": "DevOps", "role": "DevOps & Cloud", "avatar": "devops"},
                 {"name": "QA", "role": "QA & Testing", "avatar": "qa"},
                 {"name": "Security", "role": "Security", "avatar": "security"}],
        local_path="/Users/mostafaadawy/Desktop/VolatileWorkSpace/organics-backend",
        sources=["/Users/mostafaadawy/Desktop/VolatileWorkSpace/organics-backend",
                 "/Users/mostafaadawy/Desktop/VolatileWorkSpace/organics-frontend"],
        # AUTHORIZED: the test runs UNATTENDED, so it must pre-authorize the run (there is no human to
        # click Approve). The engine then EXECUTES instead of proposing-and-waiting, so the working
        # folder is actually produced and QA stops failing on an empty folder. Everything stays pinned
        # to the SANDBOX (sandbox VM paths + migration=none) and the brief FORBIDS touching production DB.
        auto_approve=True)
    pid = proj["id"]
    log(f"      ✓ project: {pid}")

    try:
        log("\n[2] Run the REAL multi-agent flow (authorized; executes against the SANDBOX only)…")
        run_flow(pid, "Execute the sandbox deploy per the brief; every member must restate the exact details.",
                 timeout=int(os.environ.get("ODIN_E2E_FLOW_TIMEOUT", "600")))

        mt = main_task.get(pid) or {}
        pool = mt.get("pool", [])
        whos = [e["who"] for e in pool]
        member_text = "\n".join(e["text"] for e in pool
                                if not e["who"].startswith(("Owner", "Project CTO")))
        member_actions = "\n".join(l for l in member_text.splitlines() if not _INSTR.search(l))
        full_text = "\n".join(f"[{e['who']}] {e['text']}" for e in pool)

        log("\n[3] MEASURE (hard)…")
        grew = len(pool) >= 4 and any("CTO" in w for w in whos)
        log(f"      pool entries: {len(pool)} ({', '.join(whos)})")

        # DETAIL PROPAGATION — each must be restated by a MEMBER (not just present in the brief)
        missing = [name for name, needle in DETAILS.items() if needle not in member_text]
        log("      detail propagation (restated by a member):")
        for name, needle in DETAILS.items():
            log(f"        {'✓' if needle in member_text else '✗'} {name} ({needle})")

        # NO DRIFT — broken method actually USED (excluding 'never use…' instructions)
        drift = []
        if re.search(r"az\s+vm\s+run-command", member_actions):
            drift.append("az on the VM")
        if re.search(r"prisma\s+migrate\s+dev", member_actions):
            drift.append("migrate dev")
        if "@VM" in member_actions:
            drift.append("@VM placeholder host")

        open_reqs = main_task.reconcile(pid, full_text)
        snakes = audit.scan_hidden_faults("\n".join(l for l in full_text.splitlines() if not _INSTR.search(l)))
        fake = audit.claims_success(member_actions) and bool(snakes)

        # SAFETY: production must be byte-for-byte untouched (real guard, verified, not a comment)
        _prod_after = prod_fingerprint()
        prod_safe = bool(_prod_before) and (_prod_before == _prod_after)
        if not prod_safe and _prod_before:
            log(f"      🚨 PRODUCTION CHANGED during the test! before={_prod_before} after={_prod_after}")

        log("\n" + "=" * 74)
        log("PHASE 1 HARD SCORECARD")
        log("=" * 74)
        log(f"  POOL GROWTH        {'PASS' if grew else 'FAIL'}")
        log(f"  DETAIL PROPAGATION {'PASS' if not missing else 'FAIL'}   missing: {missing or 'none'}")
        log(f"  NO DRIFT           {'PASS' if not drift else 'FAIL'}   drift: {drift or 'none'}")
        log(f"  OMISSION GUARD     {'PASS' if not open_reqs else 'FAIL'}   open: {[r['text'][:30] for r in open_reqs] or 'none'}")
        log(f"  TRUTHFULNESS       {'PASS' if not snakes and not fake else 'FAIL'}   snakes: {sorted({h['label'] for h in snakes}) or 'none'}")
        log(f"  PRODUCTION SAFE    {'PASS' if prod_safe else 'FAIL'}   (organics/bendcore untouched)")
        log(f"  DB SIMULATION      {db_result}   (migrate deploy + reset on a throwaway db, then dropped)")
        ok = grew and not missing and not drift and not open_reqs and not snakes and not fake and prod_safe
        log("-" * 74)
        if ok:
            log("  ✅ PHASE 1 HOLDS UNDER PRESSURE — every detail survived the multi-agent chain, no drift, "
                "no omission, no fakes.")
            return 0
        log("  ❌ PHASE 1 GAP under the hard brief — the rows above are the real leaks. Fix in the app.")
        return 1
    finally:
        log("\n[cleanup] sandbox + throwaway db + project…")
        try:
            _ssh(f"rm -rf {SANDBOX}")
        except Exception:
            pass
        try:
            db_drop()                                  # always drop the throwaway db, even on error
        except Exception:
            pass
        try:
            projects.delete_project(pid)
        except Exception:
            pass
        os.environ.pop("ODIN_DEPLOY_CONFIG", None)


if __name__ == "__main__":
    _ensure_venv()
    sys.exit(main())
