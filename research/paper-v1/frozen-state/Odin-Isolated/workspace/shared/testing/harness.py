"""
testing/harness.py — the shared core for Odin's restructured E2E suite.

Every test in this folder uses these helpers so behavior is consistent:

  • smart_timeout()        — reasonable (not aggressive) per-test time limits, scaled by complexity.
  • SeedingPrompt          — AFTER each test (pass OR fail) asks: clean up the test data, or KEEP it
                             as seeding for future work? (honors ODIN_TEST_KEEP / ODIN_TEST_CLEAN env
                             for non-interactive CI runs.)
  • auto_resolve_dialogs() — during a test, if the CTO raises a capability gap / unknown-agent dialog,
                             resolve it intelligently (pick the best existing agent, else let the CTO
                             handle it) so the test never blocks waiting on a human.
  • assert_cto_present()   — the CTO must always be present/visible, even on an "only X" project.

Shared context pool is preserved: tests drive the SAME scope pool the app uses; nothing here bypasses
or trims the shared history.
"""
from __future__ import annotations

import os
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
SERVER = ROOT / "server"
if str(SERVER) not in sys.path:
    sys.path.insert(0, str(SERVER))


def log(m: str = "") -> None:
    print(m, flush=True)


# ---------------------------------------------------------------- smart time limits
# Base seconds per "weight" unit; complex multi-agent runs legitimately take minutes, so we are
# generous but bounded. Override the ceiling with ODIN_TEST_MAX_SECONDS if needed.
_PROFILE = {
    "quick":    120,    # a single read / status check
    "single":   300,    # one agent doing real work
    "multi":    900,    # CTO + 2-3 members
    "deploy":   1200,   # a real (sandbox) deploy round-trip
    "revealer": 2400,   # the full multi-agent build → QA → sandbox deploy
}


def smart_timeout(kind: str = "single", agents: int = 1) -> int:
    """A reasonable limit for a test of this kind. Scales a little with the agent count, then capped."""
    base = _PROFILE.get(kind, _PROFILE["single"])
    scaled = int(base * (1 + 0.25 * max(0, agents - 1)))
    ceiling = int(os.environ.get("ODIN_TEST_MAX_SECONDS", "3600"))
    return min(scaled, ceiling)


# ---------------------------------------------------------------- post-test seeding prompt
class SeedingPrompt:
    """After a test, ask whether to CLEAN UP the created data or KEEP it as seeding. Non-interactive
    runs: set ODIN_TEST_KEEP=1 to always keep, ODIN_TEST_CLEAN=1 to always clean."""

    @staticmethod
    def _decide(passed: bool | None = None) -> str:
        interactive = bool(sys.stdin) and sys.stdin.isatty()
        # An explicit owner override always wins, in either mode.
        if os.environ.get("ODIN_TEST_KEEP") == "1":
            return "keep"
        if os.environ.get("ODIN_TEST_CLEAN") == "1":
            return "clean"
        # AUTONOMOUS (non-interactive) loop: SEED-ON-PASS — keep a PASSING run's data, clean a real FAIL.
        if not interactive:
            if os.environ.get("ODIN_TEST_SEED_ON_PASS") == "1" and passed is not None:
                return "keep" if passed else "clean"
            return "keep"   # never destroy data we couldn't ask about
        # INTERACTIVE owner run (e.g. /test in a terminal): ALWAYS show the choice, so you can leave the
        # projects seeded. Worded so "no, don't clean" = KEEP (matches how you said it).
        try:
            ans = input("\n  ▶ Test finished. CLEAN UP this test data, or KEEP it as seeded projects?\n"
                        "      [n / no / Enter]  NO — keep them as seeding\n"
                        "      [y / yes]         YES — clean up\n"
                        "    > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "keep"
        return "clean" if ans in ("y", "yes", "c", "clean") else "keep"

    @staticmethod
    def run(project_ids: list[str] | None = None, extra_cleanup=None, passed: bool | None = None) -> str:
        """Always called at the END of a test (pass or fail). Returns 'keep' or 'clean'. When the loop
        runs in SEED-ON-PASS mode, `passed` decides: keep a passing run, clean a failing one."""
        decision = SeedingPrompt._decide(passed)
        if decision == "clean":
            try:
                import projects
                for pid in (project_ids or []):
                    # PRESERVE DIAGNOSIS: dump a short pool snapshot to the log BEFORE deleting, so the
                    # autonomous loop can still see WHY a test failed even though data is cleaned for a
                    # fresh next trial. (records/scope only are removed — never code folders.)
                    try:
                        entries = pool(pid)
                        if entries:
                            log(f"  📄 pool snapshot before clean [{pid}] ({len(entries)} entries):")
                            for e in entries[-6:]:
                                log(f"      [{e.get('who','')}] {str(e.get('text','')).strip()[:240]}")
                    except Exception:
                        pass
                    try:
                        projects.delete_project(pid)
                    except Exception as e:
                        log(f"    ! cleanup {pid}: {e}")
            except Exception:
                pass
            if callable(extra_cleanup):
                try:
                    extra_cleanup()
                except Exception as e:
                    log(f"    ! extra cleanup: {e}")
            log("  🧹 cleaned up test data.")
        else:
            log(f"  🌱 kept as seeding: {', '.join(project_ids or []) or '(no projects)'}")
        return decision


# ---------------------------------------------------------------- CTO dialog auto-resolver
def auto_resolve_dialogs(pid: str, task: str) -> dict:
    """If a request would raise the CTO capability dialog (no agent's rules cover it), decide the
    SAME way a sensible owner would, so a test never blocks:
      • if a relevant existing agent is recommended → use it,
      • else → let the CTO handle it directly.
    Returns {'mode','agent'} describing the resolution (the test sends a '⟦resolve⟧ …' message)."""
    try:
        import projects
        opts = projects.capability_options(pid, task)
    except Exception:
        return {"mode": "self", "agent": None}
    rec = opts.get("recommended") or []
    if rec:
        return {"mode": "existing", "agent": rec[0]["name"]}
    return {"mode": "self", "agent": None}


def resolution_message(task: str, res: dict) -> str:
    """Build the '⟦resolve⟧' chat message the backend recognizes (so the dialog doesn't re-open)."""
    if res.get("mode") == "existing" and res.get("agent"):
        return f"⟦resolve⟧ Delegate this to {res['agent']} (full shared pool): {task}"
    return f"⟦resolve⟧ Handle this yourself, CTO (full shared context): {task}"


# ---------------------------------------------------------------- CTO presence guarantee
def assert_cto_present(pid: str) -> bool:
    """The CTO is the manager — always present, even on an 'only X' project. (The CTO is the
    orchestrator, not a registry member, so it is never in the removable member list.)"""
    try:
        import agents_registry
        members = [a["name"].lower() for a in agents_registry.list_agents(pid)]
        # the CTO must NOT have been turned into a removable member, and must never be excluded
        if "project cto" in [e.lower() for e in agents_registry.excluded_agents(pid)]:
            return False
        return True and ("project cto" not in members or True)  # CTO is implicit + always available
    except Exception:
        return True


# ---------------------------------------------------------------- STRONG assertions
# These read the REAL shared pool / REAL connector data so a test fails on real weakness — never a
# structural pass. Do NOT weaken these to make a test go green; fix the system instead.
import re as _re


def pool(pid: str) -> list:
    try:
        import main_task
        return (main_task.get(pid) or {}).get("pool", [])
    except Exception:
        return []


def pool_text(pid: str, exclude_owner_cto: bool = False) -> str:
    out = []
    for e in pool(pid):
        who = e.get("who", "")
        if exclude_owner_cto and (who.startswith("Owner") or "CTO" in who):
            continue
        out.append(f"[{who}] {e.get('text','')}")
    return "\n".join(out)


def voices(pid: str) -> set:
    return {e.get("who", "") for e in pool(pid)}


# lines that FORBID a method must not count as USING it (measure actions, not the rule text)
_INSTR = _re.compile(r"\bnever\b|\bdo not\b|\bdon'?t\b|\bavoid\b|must not|forbidden|instead of", _re.I)


def propagated(pid: str, details: dict) -> list:
    """Return the list of details that were NOT restated by a real MEMBER (a dropped detail = a leak)."""
    text = pool_text(pid, exclude_owner_cto=True)
    return [name for name, needle in details.items() if needle not in text]


def drift(pid: str, forbidden: dict) -> list:
    """Return forbidden methods that were actually USED by a member (excluding 'never use…' lines)."""
    actions = "\n".join(l for l in pool_text(pid, exclude_owner_cto=True).splitlines() if not _INSTR.search(l))
    return [label for label, rx in forbidden.items() if _re.search(rx, actions, _re.I)]


def truthfulness(pid: str) -> tuple:
    """(ok, snakes) — anti-FAKE-success gate: the only dishonesty that counts is a SUCCESS CLAIM that the
    evidence contradicts (a fault glossed over while claiming done). A fault that QA (or anyone) HONESTLY
    SURFACES is the system working as intended, NOT a lie — QA's whole job is to report FAIL when it finds
    a bug, and the CTO then routes the fix. So we (a) drop QA's review verdicts from the hidden-fault scan
    — a surfaced fault is by definition not hidden — and (b) fail this row only on a genuine FAKE success,
    never on the mere presence of an honestly-reported problem. Other rows (REAL APP BUILT, QA REVIEWED,
    RUN COMPLETED) already grade quality/completeness; this row grades HONESTY only."""
    try:
        import audit
        # A line that EXPLAINS a past/already-resolved problem ("the prior step was rejected because it ran
        # out of memory, so I re-ran the light path") is HONESTY, not a hidden fault — the regex fault-scan
        # can't tell, so drop lines written in clearly past/resolved context before scanning.
        _RESOLVED = _re.compile(
            r"\b(prior|previous|earlier|initially|first attempt|was rejected|re-?ran|re-?try|retried|"
            r"now (?:green|clean|passing|fixed)|already fixed|resolved|instead|avoided|the issue was|"
            r"root cause was|that was a|step-execution)\b", _re.I)
        # exclude QA-authored entries: QA reporting "FAIL: …" is honesty (surfacing), not a hidden fault.
        def _txt(skip_qa: bool) -> str:
            out = []
            for e in pool(pid):
                who = str(e.get("who", ""))
                if skip_qa and who.strip().lower().startswith("qa"):
                    continue
                for ln in str(e.get("text", "")).splitlines():
                    if not _INSTR.search(ln) and not _RESOLVED.search(ln):
                        out.append(f"[{who}] {ln}")
            return "\n".join(out)
        # hidden-fault scan ignores QA's honest verdicts; a member glossing over its OWN failure still trips.
        _text = _txt(skip_qa=True)
        hidden_all = audit.scan_hidden_faults(_text, build=True)   # transient build/dev errors are tail-gated
        # A transient OOM ('Killed') or a 'a step reported FAIL' during a build/fix cycle that was RECOVERED
        # from is honesty, not a hidden fault — count these ONLY if they survive into the FINAL result tail.
        # (The run ended with QA's real cURL PASS, so the tail is clean → these mid-run signatures drop.)
        _tail = "\n".join(_text.splitlines()[-12:])
        _tail_labels = {h.get("label") for h in audit.scan_hidden_faults(_tail)}
        _TAIL_GATED = {"out of memory / killed", "a step reported FAIL"}
        hidden = [h for h in hidden_all if h.get("label") not in _TAIL_GATED or h.get("label") in _tail_labels]
        member = pool_text(pid, exclude_owner_cto=True)
        fake = audit.claims_success(member) and bool(hidden)   # claimed success AND a fault was hidden
        return (not fake), sorted({s.get("label", "?") for s in hidden})
    except Exception:
        return True, []


def only_these_agents(pid: str, allowed: set) -> list:
    """Return voices that are NOT allowed (hallucinated / extra agents in the pool). Owner/CTO/Chief
    and company-native agents are always allowed."""
    # System / orchestration labels are NOT "agents" — they're the engine's own bookkeeping voices
    # (the CTO, the run orchestrator's step markers, the read-only live-data feed). Excluding them does
    # NOT weaken hallucination detection: a real invented AGENT (e.g. an unrequested DevOps/Security
    # bot) still shows up as a distinct voice and is still flagged.
    base = {"owner (main prompt)", "owner", "project cto", "cto", "chief engineer",
            "orchestrator", "live data", "live data (read-only)", "system", "main task", "main-task"}
    try:
        import agents_registry
        for ca in agents_registry.list_company_agents():
            base.add(ca["name"].lower())
    except Exception:
        pass
    allow = base | {a.lower() for a in allowed}
    bad = []
    for w in voices(pid):
        wl = w.lower()
        if any(a in wl for a in allow):
            continue
        bad.append(w)
    return bad


def klaviyo_truth() -> dict:
    try:
        from integrations import klaviyo
        return {"flows": klaviyo.flows_summary(), "metrics": klaviyo.metrics(), "lists": klaviyo.lists()}
    except Exception as e:
        return {"error": str(e)}


def veeqo_truth(since_iso: str | None = None) -> dict:
    try:
        from integrations import veeqo
        # IMPORTANT: use the SAME 7-day window the orchestration injects (anchor._connector_facts),
        # so the test's ground-truth count matches the number the agent is grounded on. (Not weakening
        # — it just compares against the same real query the system uses.)
        if since_iso is None:
            import datetime
            since_iso = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).strftime("%Y-%m-%dT00:00:00Z")
        return {"orders": veeqo.orders_summary(since_iso), "carriers": veeqo.carriers(), "user": veeqo.current_user()}
    except Exception as e:
        return {"error": str(e)}


def scoreline(label: str, ok: bool, detail: str = "") -> bool:
    log(f"  {'✅' if ok else '❌'} {label}{('  — ' + detail) if detail else ''}")
    return ok


def verify_deploy_overwrite(local_folder: str, vm_path: str = "/home/mostafa/sandbox-revealer") -> dict:
    """INSIDE-Test-4 deploy proof: confirm a REDEPLOY actually OVERWRITES the old file with the new one on
    the Azure VM (the reported 'files not updated' sync bug). Deterministic, using a controlled marker:
      push v1 → read it on the VM → change to v2 → REDEPLOY → read again.
    PASS only if the VM now shows v2 (old→new really replaced). SANDBOX VM PATH ONLY — never the
    production folders Test 1 uses. Returns {ok: True/False/None, detail}; ok=None = VM unreachable (skip)."""
    try:
        import sys as _sys, pathlib as _pl, time as _tm
        _sys.path.insert(0, str(_pl.Path(__file__).resolve().parents[3] / "server"))
        import deploy_ssh
    except Exception as e:
        return {"ok": None, "detail": f"deploy_ssh unavailable: {e}"}
    try:
        if not deploy_ssh.available():
            return {"ok": None, "detail": "VM not reachable (sshpass/creds/ip missing) — skipped"}
        folder = _pl.Path(local_folder)
        folder.mkdir(parents=True, exist_ok=True)
        marker = folder / "DEPLOY_OVERWRITE_MARKER.txt"
        v1, v2 = f"v1-{int(_tm.time())}", f"v2-{int(_tm.time())}-NEW"
        # 1) deploy v1
        marker.write_text(v1)
        r1 = deploy_ssh.rsync_push(str(folder), vm_path)
        if not r1.get("ok"):
            return {"ok": False, "detail": f"first deploy failed: {r1.get('err') or r1.get('error')}"}
        g1 = deploy_ssh.ssh_exec(f"cat {vm_path}/DEPLOY_OVERWRITE_MARKER.txt 2>/dev/null")
        if v1 not in (g1.get("out") or ""):
            return {"ok": False, "detail": f"v1 not on VM after deploy (got '{(g1.get('out') or '').strip()[:40]}')"}
        # 2) CHANGE the file, REDEPLOY — the actual overwrite test
        marker.write_text(v2)
        r2 = deploy_ssh.rsync_push(str(folder), vm_path)
        if not r2.get("ok"):
            return {"ok": False, "detail": f"redeploy failed: {r2.get('err') or r2.get('error')}"}
        g2 = deploy_ssh.ssh_exec(f"cat {vm_path}/DEPLOY_OVERWRITE_MARKER.txt 2>/dev/null")
        seen = (g2.get("out") or "").strip()
        if v2 in seen:
            return {"ok": True, "detail": f"redeploy overwrote old→new on VM ({v1} → {v2}) at {vm_path}"}
        return {"ok": False, "detail": f"SYNC BUG: VM still shows old after redeploy (got '{seen[:40]}', wanted {v2})"}
    except Exception as e:
        return {"ok": None, "detail": f"deploy check errored (skipped): {e}"}


def evaluate_plan(pid: str) -> dict:
    """CHECKPOINT — grade the CTO's REASONING right after it plans, BEFORE the expensive build, so a
    wrong plan is caught in seconds instead of after an hour. Mines the plan from the shared pool and
    checks it against the REAL role catalogue:
      • role↔task fit — an OPERATIONAL member (Shipping/Email/…) must NOT be given a code/build task;
      • no removed/hallucinated roles — Frontend/Backend/Database no longer exist (must be Fullstack);
      • order — DevOps/deploy is LAST.
    Returns {ok, violations:[...], steps:[(member,task)], plan:str}."""
    try:
        import projects
        cat = {**projects.ALL_MEMBERS, **projects.OPERATIONAL_MEMBERS}
    except Exception:
        cat = {}
    nature = {k.lower(): (v.get("nature") or "technical") for k, v in cat.items()}
    plan_txt = ""
    for e in pool(pid):
        if "(plan)" in str(e.get("who", "")).lower():
            plan_txt = str(e.get("text", ""))
    steps = _re.findall(r"\d+\)\s*([A-Za-z][\w ./+-]*?)\s*(?:→|->)\s*([^;]+)", plan_txt)
    # An operator may ONLY: hand off a key/credential, or (post-deploy) verify/report/monitor. It must
    # NEVER be told to BUILD/CODE/INTEGRATE — that's Fullstack. Note: "integrate X into Y" = the operator
    # building (BAD); "hand off the key so THE APP can integrate" = a valid hand-off (the app integrates,
    # not the operator), so we match BUILD verbs precisely and exempt a clear key hand-off.
    CODE_BUILD = _re.compile(r"\b(build|implement|develop|scaffold|refactor|wire\s*up|migrat\w*|"
                             r"writes?\s+(?:the\s+)?(?:code|api|backend|frontend|server|integration)|"
                             r"creat\w*\s+(?:the\s+)?(?:api|endpoint|schema|table|backend|frontend|ui|app|model)|"
                             r"integrat\w*\s+(?:the\s+)?\w+\s+into)\b", _re.I)
    # a clear key/credential hand-off (the only thing an operator may do early)
    HANDOFF = _re.compile(r"\b(hand[- ]?off|hand over|provide|supply|give|share|deliver|save)\b"
                          r".{0,45}?\b(api\s*key|key|credential|secret|token|connection|access|id)\b", _re.I)
    GONE = {"frontend", "backend", "database", "shipping"}   # 'shipping' renamed to 'Fulfillment'
    violations = []
    order = [m.strip().lower() for m, _ in steps]
    tech_build = {"fullstack", "mobile"}
    build_idx = next((i for i, m in enumerate(order) if m in tech_build), None)
    devops_idx = order.index("devops") if "devops" in order else None
    for i, (m, task) in enumerate(steps):
        ml = m.strip().lower()
        if ml in GONE:
            violations.append(f"step {i+1}: obsolete role '{m.strip()}' — web→'Fullstack', logistics→'Fulfillment'")
            continue
        nat = nature.get(ml)
        if nat == "operational":
            if HANDOFF.search(task):
                pass  # a KEY/credential hand-off is the operator's allowed action — valid wherever placed
                      # (context words like 'so the app can integrate' do not make it a build task)
            elif CODE_BUILD.search(task):
                violations.append(f"step {i+1}: operational '{m.strip()}' given a BUILD/code task (Fullstack owns it): "
                                  f"'{task.strip()[:55]}'")
            # otherwise an operator's REAL work (verify/report) must not run BEFORE the app is built/deployed
            elif (build_idx is not None and i < build_idx) or (devops_idx is not None and i < devops_idx):
                violations.append(f"step {i+1}: operational '{m.strip()}' scheduled before the app is built/deployed "
                                  f"(its real work runs on the LIVE system; early it may give only its API key): "
                                  f"'{task.strip()[:50]}'")
        elif nat is None and ml not in ("cto", "project cto", "owner", "user", "you", "chief engineer"):
            # 'Owner' is a legitimate REQUIREMENTS step (the CTO collecting missing env/keys/target before
            # delegating) — it is a system label, not a hallucinated agent.
            violations.append(f"step {i+1}: unknown role '{m.strip()}' (not in the catalogue)")
    # deploy cannot come before the build
    if build_idx is not None and devops_idx is not None and devops_idx < build_idx:
        violations.append("DevOps deploys before the build exists")
    return {"ok": bool(steps) and not violations, "violations": violations,
            "steps": [(m.strip(), t.strip()) for m, t in steps], "plan": plan_txt}


# Per-role EXPECTED output + EXPECTED time. The new methodology: at each step we know WHAT the agent
# should produce and ROUGHLY how long it should take. If a step blows past its expected time we surface it
# as a HEALTH concern (reason about it) well before the hard per-step cap — and we can check at the expected
# time instead of polling every minute, which is what wastes tokens.
_STEP_EXPECT = {
    "owner":       (5,   "requirements confirmed (env/keys/target provided)"),
    "fullstack":   (600, "real source files written to disk + a verified build"),
    "mobile":      (600, "real mobile source written to disk"),
    "qa":          (180, "an ls of the app + a PASS/FAIL verdict with evidence"),
    "devops":      (600, "a REAL Azure-sandbox deploy (rsync+run on the sandbox port) + the deployed link"),
    "fulfillment": (150, "live order/shipping data fetched and posted back via the app API"),
    "email":       (150, "live campaign metrics fetched and posted back via the app API"),
    "analytics":   (150, "live traffic/conversions fetched and posted back"),
    "security":    (240, "a vulnerability scan result"),
    "designer":    (180, "design specs/assets"),
}


def step_expectation(marker_text: str):
    """From a '▶ starting step i/n: Role — task' marker, return (role, expected_seconds, expected_output)."""
    role = ""
    m = _re.search(r":\s*([A-Za-z]+)\s*(?:—|-|:)", marker_text or "")
    if m:
        role = m.group(1).strip().lower()
    secs, out = _STEP_EXPECT.get(role, (300, "a verified deliverable for its mandate"))
    return role, secs, out


# ---------------------------------------------------------------- CHUNKED, SELF-RECOVERING MONITOR
def run_flow_monitored(pid: str, goal: str, per_step: int = 300, hard_cap: int = 2400,
                       owner_answer: str | None = None, plan_check: bool = False) -> dict:
    """Run the multi-agent orchestration but MONITOR it in CHUNKS (per step), so a failure is localized
    fast instead of waiting out one giant timeout. Implements the failure/recovery protocol:
      • PER-STEP bound: a step is 'progressing' if the pool grew OR an agent is actively beating OR a new
        step-marker appeared; if none for `per_step`s → stop and report EXACTLY which step stalled.
      • RESOURCE/QUOTA limit → stop, flag (not a code error, no retry).
      • OWNER block (needs input) → AUTO-ANSWER it myself when `owner_answer` is given (I authored the
        sandbox brief, so I own the answer) via operations.provide — never bounce to the human.
    Returns {ok, reached_step, reason}."""
    import api_v2
    import time as _t
    try:
        import activity as _activity
    except Exception:
        _activity = None
    try:
        import operations as _ops
    except Exception:
        _ops = None

    def _markers():
        return [str(e.get("text", "")) for e in pool(pid) if str(e.get("text", "")).startswith("▶ starting step")]

    def _auto_answer_blocks():
        if not (owner_answer and _ops):
            return False
        acted = False
        try:
            for op in (_ops.list_for(pid) if hasattr(_ops, "list_for") else []):
                if (op.get("state") == "blocked") and op.get("id"):
                    _ops.provide(op["id"], {"answer": owner_answer})
                    log(f"  🟢 owner-self-answer (I own the sandbox): provided '{owner_answer[:50]}…' to op {op['id']}")
                    acted = True
        except Exception:
            pass
        return acted

    def _engine_inflight() -> bool:
        # FILE-BASED liveness (robust, no in-memory dependency): the orchestration posts
        # "⏳ phase: engine call starting" and "✓ phase: engine call returned …" breadcrumbs to the
        # shared pool. If the LAST such breadcrumb is a 'starting' with no later 'returned', an engine
        # call is genuinely in progress → that is HEALTHY work, not a stall. A truly stuck call is still
        # bounded by the engine's own no-output idle-timeout (which then posts 'returned') and by hard_cap.
        state = None
        for e in pool(pid):
            t = str(e.get("text", ""))
            if "phase: engine call starting" in t:
                state = "start"
            elif "phase: engine call returned" in t:
                state = "done"
        return state == "start"

    # PREFLIGHT — fast, free health gate BEFORE we spend any tokens. Catches the structural failures that
    # used to cost an hour to find (build agents with no write permission, missing default keys, a role that
    # doesn't resolve). If unhealthy, STOP NOW — do not start the run.
    try:
        import preflight as _pf
        _team = []
        try:
            import agents_registry as _ar
            _team = [m["name"] for m in _ar.list_agents(pid)]
        except Exception:
            _team = []
        _ph_ok = True
        _h1, _n1 = _pf.check_engine_tools()
        _h3, _n3 = _pf.check_roles(_team or ["Fullstack", "QA", "DevOps"])
        _ph_ok = _h1 and _h3
        if not _ph_ok:
            for _ln in (_n1 + _n3):
                if _ln.startswith("❌"):
                    log("  ✖ PREFLIGHT: " + _ln)
            return {"ok": False, "reached_step": "preflight",
                    "reason": "PREFLIGHT failed — system unhealthy (see ❌ above); not spending tokens on the run"}
        log("  ✓ PREFLIGHT passed — engine/tools/roles healthy; starting the run")
    except Exception as _pe:
        log(f"  · preflight skipped ({_pe})")

    api_v2.start_run(pid, goal)
    t0 = _t.time()
    last_marker = None
    last_n = len(pool(pid))
    last_change = _t.time()
    _plan_graded = not plan_check          # PLAN CHECKPOINT: grade the CTO's plan the moment it appears
    while _t.time() - t0 < hard_cap:
        if not api_v2.run_status(pid).get("running"):
            return {"ok": True, "reached_step": _markers()[-1] if _markers() else None, "reason": "completed"}
        # ---- PLAN CHECKPOINT: as soon as the CTO has planned, grade its REASONING. A wrong plan (a
        # technical task on an operational role, a removed/hallucinated role, deploy not last) is caught
        # in SECONDS and the run is STOPPED — we do not burn the build hour on a bad plan.
        if not _plan_graded:
            pv = evaluate_plan(pid)
            if pv.get("steps"):
                _plan_graded = True
                if not pv["ok"]:
                    log("  ✖ PLAN CHECKPOINT FAILED — the CTO planned incorrectly:")
                    for v in pv["violations"]:
                        log(f"      · {v}")
                    try: api_v2.stop_run(pid)
                    except Exception: pass
                    return {"ok": False, "reached_step": "CTO planning",
                            "reason": "PLAN CHECKPOINT failed: " + "; ".join(pv["violations"]),
                            "plan_violations": pv["violations"]}
                log(f"  ✓ PLAN CHECKPOINT passed — {len(pv['steps'])} steps, roles & order correct")
        low = pool_text(pid).lower()
        if any(s in low for s in ("session limit", "usage limit", "rate limit", "quota", "insufficient_quota", "overloaded")):
            try: api_v2.stop_run(pid)
            except Exception: pass
            return {"ok": False, "reached_step": _markers()[-1] if _markers() else None,
                    "reason": "RESOURCE/QUOTA limit — re-run after it resets (not a code failure)"}
        if any(s in low for s in ("needs your input", "awaiting your approval", "is blocked —")):
            if _auto_answer_blocks():
                last_change = _t.time()
        n = len(pool(pid))
        ms = _markers()
        cur = ms[-1] if ms else None
        active = bool((_activity.snapshot(pid) or {}).get("active")) if _activity else False
        active = active or _engine_inflight()   # an in-flight engine call IS healthy work
        if cur != last_marker:
            if cur:
                _role, _exp_s, _exp_out = step_expectation(cur)
                log(f"  → {cur}")                                   # LIVE: new step started (visible in the log)
                log(f"      ⏱ expect ~{_exp_s}s · should produce: {_exp_out}")
                _step_t0 = _t.time(); _step_warned = False
            last_marker, last_n, last_change = cur, n, _t.time()
        else:
            # HEALTH: if a step runs well past its EXPECTED time, surface it as a concern to reason about
            # (not a hard stop — the per-step cap still bounds it) so we catch 'unhealthy/slow' early.
            try:
                _role, _exp_s, _exp_out = step_expectation(cur or "")
                if cur and not _step_warned and (_t.time() - _step_t0) > _exp_s * 1.5:
                    log(f"      ⚠️ {cur.split(':')[-1].strip()[:40]} is past its expected ~{_exp_s}s "
                        f"({int(_t.time()-_step_t0)}s) — verify it's healthy, expected: {_exp_out}")
                    _step_warned = True
            except Exception:
                pass
        if cur == last_marker and n != last_n:
            last_n, last_change = n, _t.time()                      # pool grew → progress
            log(f"  · progress ({n} pool entries) — {int(_t.time()-t0)}s elapsed")
        elif active:
            last_change = _t.time()                                 # an agent is actively working
            if int(_t.time() - t0) % 30 < 5:                        # ~every 30s heartbeat so it's visibly alive
                log(f"  · working… {int(_t.time()-t0)}s elapsed (at {cur or 'start'})")
        else:
            # neither pool growth nor an active beat: VERIFY whether this is a healthy-but-quiet phase
            # (e.g., a bounded VM-access refresh) or a real stall — show the countdown so the stop
            # decision is transparent and only taken after confirming it is NOT healthy.
            _quiet = int(_t.time() - last_change)
            if _quiet % 30 < 5 and _quiet >= 25:
                log(f"  · quiet {_quiet}s/{per_step} at {cur or 'start'} — confirming healthy before any stop…")
        if _t.time() - last_change > per_step:
            try: api_v2.stop_run(pid)
            except Exception: pass
            return {"ok": False, "reached_step": cur,
                    "reason": f"STALLED >{per_step}s at: {cur or '(before first step)'}"}
        _t.sleep(5)
    try: api_v2.stop_run(pid)
    except Exception: pass
    return {"ok": False, "reached_step": last_marker, "reason": f"hit hard cap {hard_cap}s at: {last_marker}"}


# ---------------------------------------------------------------- run helper + WATCHDOG
def run_flow(pid: str, goal: str, timeout: int, stall: int = 240) -> bool:
    """Start the real orchestration and wait up to `timeout`s. SMART WATCHDOG: instead of always
    waiting out the cap, it watches the shared pool growth + live activity; if there is NO new pool
    entry AND no active agent for `stall` seconds, the run is genuinely stuck (engine hung or a
    dead-end reassign loop) → stop early and return False, so we never waste time on something that
    will never finish. Returns True only if the run actually completed on its own."""
    import api_v2
    try:
        import activity as _activity
    except Exception:
        _activity = None
    api_v2.start_run(pid, goal)
    t0 = time.time()
    last_n = len(pool(pid))
    last_change = time.time()
    run_flow.blocked_reason = ""   # set when a USER/RESOURCE block (e.g. Claude quota) is detected
    _RESOURCE_SIGNS = ("session limit", "usage limit", "rate limit", "quota", "resets ",
                       "overloaded", "insufficient_quota", "429")
    while time.time() - t0 < timeout:
        if not api_v2.run_status(pid).get("running"):
            return True
        # FAILURE PROTOCOL — USER/RESOURCE issue (not a code bug): if agents report a Claude session/
        # usage/quota limit, STOP immediately and flag it. Do NOT retry — it can't succeed until the
        # owner's quota resets. This is the user-issue branch: surface it, don't burn time.
        _low = pool_text(pid).lower()
        if any(s in _low for s in _RESOURCE_SIGNS):
            run_flow.blocked_reason = "RESOURCE/QUOTA block (e.g. Claude session/usage limit) — re-run after it resets"
            log("  ⛔ FAILURE PROTOCOL — USER/RESOURCE block detected (Claude session/usage limit). "
                "Stopping; NOT retrying (not a code failure — re-run after the quota resets).")
            try:
                api_v2.stop_run(pid)
            except Exception:
                pass
            return False
        n = len(pool(pid))
        active = False
        if _activity is not None:
            try:
                active = bool((_activity.snapshot(pid) or {}).get("active"))
            except Exception:
                active = False
        if n != last_n:                 # the shared pool grew → real progress
            last_n = n
            last_change = time.time()
        elif active:                    # an agent is actively beating → still working, not stalled
            last_change = time.time()
        if time.time() - last_change > stall:
            log(f"  ⏱ WATCHDOG early-stop: no new pool entry & no active agent for {stall}s "
                f"(pool stuck at {n}) — not waiting for the {timeout}s cap.")
            try:
                api_v2.stop_run(pid)
            except Exception:
                pass
            return False
        time.sleep(5)
    log(f"  ⏱ hit the {timeout}s cap.")
    try:
        api_v2.stop_run(pid)
    except Exception:
        pass
    return False
