"""
e2e_phase1_shared_context.py  —  REAL test of Phase 1 (the one growing shared context pool).

It does NOT replace the other E2Es. It measures the thing Phase 1 is supposed to fix: is context
truly MAINTAINED and SHARED across agents, with nothing lost between them?

The non-deceptive trick is MARKER PROPAGATION (a real, deterministic probe):
  • The Backend is told to INVENT a unique token `ODIN-XXXXXX` and define `/api/<token>/status`.
  • The Frontend is told to call the EXACT endpoint the Backend defined — reuse the SAME token,
    never invent its own.
If the shared pool works, the token flows Backend → Frontend (and the Frontend echoes it). If
context is lost (the old per-chat fragmentation), the Frontend can't know the token and invents a
different one → the test FAILS honestly. No VM, no writes (members work read-only), so it's safe.

It measures, from project creation to results:
  POOL GROWTH    — did the pool accumulate prompt + CTO plan + each member's work?
  PROPAGATION    — did the Backend's token reach the Frontend unchanged? (the core of Phase 1)
  OMISSION GUARD — were all requirements addressed (reconcile)?
  TRUTHFULNESS   — any fake "done"/snakes in the shared pool?

Run on your Mac (needs the Claude engine; no VM):  python3 server/e2e_phase1_shared_context.py
"""
from __future__ import annotations

import os
import pathlib
import re
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
REPO = pathlib.Path(__file__).resolve().parent.parent
TOKEN_RE = re.compile(r"ODIN-[A-Z0-9]{6}")
SANDBOX_DIR = "/tmp/odin_phase1_sandbox"


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


BRIEF = (
    "Build a tiny demo service, in TWO ordered steps by two members — and they MUST stay consistent "
    "through one shared context.\n"
    "STEP 1 — Backend: INVENT one unique token of the EXACT form ODIN-XXXXXX (6 uppercase letters/"
    "digits). Define an endpoint `GET /api/<token>/status` returning {\"ok\":true}. In your report, "
    "state the token on its own line exactly as: TOKEN: ODIN-XXXXXX\n"
    "STEP 2 — Frontend: call the EXACT endpoint the Backend defined. Reuse the SAME token from the "
    "shared context — do NOT invent your own. In your report, state exactly: CALLING: /api/<token>/status\n"
    "Both steps must use the IDENTICAL token. Consistency across the team is the whole point."
)


def run_flow(pid: str, goal: str, timeout: int = 600):
    """Drive the REAL orchestration (read-only; members reason + report, nothing is executed)."""
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

    log("=" * 72)
    log("PHASE 1 E2E — does the SHARED CONTEXT POOL keep context consistent across agents?")
    log("=" * 72)

    # from the very start: create the project (two members so context must cross between them)
    log("\n[1] Create the project (Backend + Frontend; build task, sandbox folder, no VM)…")
    try:
        os.makedirs(SANDBOX_DIR, exist_ok=True)
    except Exception:
        pass
    proj = projects.create_project(
        name="E2E Phase1 Shared Context", description=BRIEF, mode="build",
        members=[{"name": "Backend", "role": "Backend", "avatar": "backend"},
                 {"name": "Frontend", "role": "Frontend", "avatar": "frontend"}],
        local_path=SANDBOX_DIR, sources=[], auto_approve=False)
    pid = proj["id"]
    log(f"      ✓ project: {pid}")

    try:
        log("\n[2] Run the REAL multi-agent flow (this is slower — context grows each step)…")
        run_flow(pid, "Build the tiny demo per the brief; keep the token identical across members.")

        # ---- gather the shared pool ----
        mt = main_task.get(pid) or {}
        pool = mt.get("pool", [])
        whos = [e["who"] for e in pool]
        backend_text = " ".join(e["text"] for e in pool if "backend" in e["who"].lower())
        frontend_text = " ".join(e["text"] for e in pool if "frontend" in e["who"].lower())
        full_text = "\n".join(f"[{e['who']}] {e['text']}" for e in pool)

        log("\n[3] MEASURE Phase 1 from the shared pool…")
        # POOL GROWTH
        grew = (len(pool) >= 3 and any("Owner" in w for w in whos)
                and any("CTO" in w for w in whos))
        log(f"      pool entries: {len(pool)}  ({', '.join(whos)})")

        # PROPAGATION (the core): Backend's token must appear in the Frontend's work, identical
        be_tok = TOKEN_RE.search(backend_text)
        fe_tok = TOKEN_RE.search(frontend_text)
        be_tok, fe_tok = (be_tok.group(0) if be_tok else None), (fe_tok.group(0) if fe_tok else None)
        propagated = bool(be_tok and fe_tok and be_tok == fe_tok)
        log(f"      Backend token: {be_tok or '(none)'} | Frontend token: {fe_tok or '(none)'} | "
            f"identical: {propagated}")

        # OMISSION GUARD
        open_reqs = main_task.reconcile(pid, full_text)
        log(f"      requirements still open: {[r['text'][:40] for r in open_reqs] or 'none'}")

        # TRUTHFULNESS
        snakes = audit.scan_hidden_faults(full_text)
        fake = audit.claims_success(full_text) and bool(snakes)
        log(f"      snakes in pool: {sorted({h['label'] for h in snakes}) or 'none'} | fake success: {fake}")

        # ---- SCORECARD ----
        log("\n" + "=" * 72)
        log("PHASE 1 SCORECARD")
        log("=" * 72)
        log(f"  POOL GROWTH      {'PASS' if grew else 'FAIL'}   (prompt + CTO plan + members accumulate)")
        log(f"  CONTEXT PROPAGATION {'PASS' if propagated else 'FAIL'}   (Backend's token reached Frontend unchanged)")
        log(f"  OMISSION GUARD   {'PASS' if not open_reqs else 'FAIL'}   (all requirements addressed)")
        log(f"  TRUTHFULNESS     {'PASS' if not snakes and not fake else 'FAIL'}   (no fakes/snakes)")
        ok = grew and propagated and not open_reqs and not snakes and not fake
        log("-" * 72)
        if ok:
            log("  ✅ PHASE 1 VERIFIED — context is shared and consistent: the token flowed Backend→Frontend, "
                "the pool grew, all requirements met, no fakes.")
            return 0
        reasons = []
        if not grew: reasons.append("pool did not accumulate the full history")
        if not propagated: reasons.append("CONTEXT LOST — Frontend did not reuse the Backend's token (the core Phase-1 failure)")
        if open_reqs: reasons.append(f"{len(open_reqs)} requirement(s) unaddressed")
        if snakes or fake: reasons.append("fakes/snakes in the shared pool")
        log("  ❌ PHASE 1 GAP — " + "; ".join(reasons))
        log("     (this is the real gap to fix in the app — never in the test.)")
        return 1
    finally:
        log("\n[cleanup] removing the test project…")
        try:
            projects.delete_project(pid)
        except Exception:
            pass


if __name__ == "__main__":
    _ensure_venv()
    sys.exit(main())
