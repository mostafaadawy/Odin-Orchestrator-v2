"""
e2e_phase1_strong.py — the STRONG, un-gameable Phase-1 test (multi-hop + hand-off).

Why this is harder than the 2-agent token test and cannot be gamed by echoing the brief:
  • Backend INVENTS token A at runtime (ODIN-XXXXXX) — A is NOT in the brief, so no one can echo it.
  • Frontend must REUSE A (proves Backend→Frontend), and INVENT its own token B.
  • Integrator (a THIRD agent) must cite BOTH A and B from the shared pool — proving context survived
    TWO hops, not one. If the pool leaks at any step, a later agent simply cannot know the token.
  • Frontend must HAND a remaining task back for the Backend (your cross-role hand-off) — the test
    checks that hand-off was actually recorded in the shared pool.

No VM, no DB, no writes (read-only reasoning) — so it's safe and measures ONLY context fidelity.
This is the honest picture of Phase 1 before Phase 2. Run:  python3 server/e2e_phase1_strong.py
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
    "Build a tiny demo across THREE ordered steps by three members. Consistency through ONE shared "
    "context is the whole point — each member must use what the previous one produced.\n"
    "STEP 1 — Backend: INVENT a unique token A of the EXACT form ODIN-XXXXXX (6 caps/digits). Define "
    "GET /api/<A>/status. In your report write on its own line: TOKEN_A: <A>\n"
    "STEP 2 — Frontend: from the SHARED CONTEXT, reuse the Backend's EXACT token A (never invent your "
    "own A). Then INVENT your own different token B (ODIN-XXXXXX) for a cache key. Write: USES_A: <A> "
    "and TOKEN_B: <B>. ALSO, if the backend must change anything to integrate, HAND IT BACK on a line: "
    "BACKEND-TODO: <one concrete task for the Backend>\n"
    "STEP 3 — Integrator: from the SHARED CONTEXT, confirm end-to-end consistency by citing BOTH tokens "
    "EXACTLY as the others set them. Write: CONFIRMED A=<A> B=<B>. Do not invent new tokens.\n"
    "Every token must match across members — that proves the context never broke."
)


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


def _member_text(pool, name):
    return " ".join(e["text"] for e in pool if name.lower() in e["who"].lower())


def main() -> int:
    import projects, main_task, audit

    log("=" * 72)
    log("PHASE 1 — STRONG test (multi-hop, runtime markers, cross-role hand-off; un-gameable)")
    log("=" * 72)

    proj = projects.create_project(
        name="E2E Phase1 Strong", description=BRIEF, mode="build",
        members=[{"name": "Backend", "role": "Backend", "avatar": "backend"},
                 {"name": "Frontend", "role": "Frontend", "avatar": "frontend"},
                 {"name": "Integrator", "role": "Integration", "avatar": "generic"}],
        local_path="/tmp/odin_phase1_strong", sources=[], auto_approve=False)
    pid = proj["id"]
    log(f"      ✓ project: {pid}")

    try:
        log("\n[run] real 3-member flow (slow; the pool grows across all three)…")
        run_flow(pid, "Build the demo per the brief; keep every token identical across the three members.")

        pool = (main_task.get(pid) or {}).get("pool", [])
        whos = [e["who"] for e in pool]
        be, fe, integ = _member_text(pool, "Backend"), _member_text(pool, "Frontend"), _member_text(pool, "Integrator")
        full = "\n".join(f"[{e['who']}] {e['text']}" for e in pool)

        log("\n[measure]")
        log(f"      pool entries: {len(pool)} ({', '.join(whos)})")
        A = (TOK.search(be).group(0) if TOK.search(be) else None)              # Backend's invented token
        fe_tokens = TOK.findall(fe)
        reuse_A = bool(A and A in fe_tokens)                                   # Frontend reused A
        B = next((t for t in fe_tokens if t != A), None)                      # Frontend's own token
        A_to_integ = bool(A and A in integ)                                   # A survived hop 2
        B_to_integ = bool(B and B in integ)                                   # B survived hop 2
        handoff = bool(re.search(r"backend[- ]?todo", fe, re.I))             # cross-role hand-off recorded
        grew = len(pool) >= 5 and any("CTO" in w for w in whos)
        snakes = audit.scan_hidden_faults(full)
        fake = audit.claims_success(full) and bool(snakes)

        log(f"      Backend invented A: {A or '(none)'}")
        log(f"      Frontend reused A : {reuse_A}   | Frontend's own B: {B or '(none)'}")
        log(f"      A reached Integrator (hop 2): {A_to_integ}   | B reached Integrator: {B_to_integ}")
        log(f"      cross-role hand-off recorded (BACKEND-TODO): {handoff}")

        log("\n" + "=" * 72)
        log("PHASE 1 STRONG SCORECARD")
        log("=" * 72)
        log(f"  POOL GROWTH            {'PASS' if grew else 'FAIL'}")
        log(f"  PROPAGATION hop 1 (BE→FE)  {'PASS' if reuse_A else 'FAIL'}")
        log(f"  PROPAGATION hop 2 (→Integrator) {'PASS' if (A_to_integ and B_to_integ) else 'FAIL'}")
        log(f"  CROSS-ROLE HAND-OFF    {'PASS' if handoff else 'FAIL'}")
        log(f"  TRUTHFULNESS           {'PASS' if not snakes and not fake else 'FAIL'}")
        ok = grew and reuse_A and A_to_integ and B_to_integ and handoff and not snakes and not fake
        log("-" * 72)
        if ok:
            log("  ✅ PHASE 1 HOLDS (STRONG) — runtime tokens flowed across TWO hops + the hand-off was "
                "recorded, all un-gameable. Context is genuinely shared.")
            return 0
        gaps = []
        if not reuse_A: gaps.append("Frontend did NOT reuse Backend's token (hop-1 context loss)")
        if not (A_to_integ and B_to_integ): gaps.append("a token did NOT reach the Integrator (hop-2 context loss)")
        if not handoff: gaps.append("cross-role hand-off was not recorded")
        if snakes or fake: gaps.append("fakes/snakes in the pool")
        if not grew: gaps.append("pool didn't accumulate")
        log("  ❌ PHASE 1 GAP — " + "; ".join(gaps))
        log("     (real leak; fix the app, never the test.)")
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
