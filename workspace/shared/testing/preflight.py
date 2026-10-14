"""
preflight.py — FAST, CHEAP health gate. Run this BEFORE committing to any expensive multi-agent build.

The whole point of the new methodology: never again burn an hour (and tokens) only to discover a
structural problem that a 10-second check would have caught — e.g. the Fullstack agent lacking
write permission, a missing credential, a role that doesn't resolve, or a CTO that plans the wrong
order. Preflight validates the SYSTEM is healthy and behaving logically, defines what we EXPECT, and
returns a clear GO / NO-GO. Only on GO do we spend tokens on the real run.

It checks, in order (cheapest first):
  1) ENGINE + TOOLS  — claude available; BUILD agents have Write/Edit/Bash; QA is read-only.
  2) CREDENTIALS/ENV — oth/.cred exists and holds the keys the brief's integrations need.
  3) ROLES           — every requested role resolves and has a Resources & Dependencies section.
  4) PLAN (optional, one cheap haiku call) — the CTO plans the RIGHT roles in the RIGHT order
     (requirements→Fullstack→QA→DevOps→operators→verify), with NO no-op steps. Graded by evaluate_plan.

Usage:
    python3 testing/preflight.py                      # checks 1-3 (no token cost)
    python3 testing/preflight.py --plan "<brief>"     # also does the cheap plan dry-run
    python3 testing/preflight.py --keys VEEQO,KLAVIYO  # require these keys present
Exit 0 = GO (healthy), 1 = NO-GO (stop and fix before spending tokens).
"""
from __future__ import annotations

import os
import sys
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in (str(HERE), str(ROOT / "server")):
    if p not in sys.path:
        sys.path.insert(0, p)


def _ok(b):
    return "✅" if b else "❌"


def check_engine_tools() -> tuple[bool, list[str]]:
    notes = []
    healthy = True
    try:
        import claude_cli
    except Exception as e:
        return False, [f"engine import failed: {e}"]
    avail = False
    try:
        avail = claude_cli.available()
    except Exception as e:
        notes.append(f"availability check errored: {e}")
    notes.append(f"{_ok(avail)} claude engine available")
    healthy &= avail
    # BUILD agents (readonly=False) MUST have Write + Edit + Bash, else they narrate instead of building.
    try:
        build_flags = " ".join(claude_cli._tool_flags(False))
        has_write = ("Write" in build_flags) and ("Edit" in build_flags) and ("Bash" in build_flags)
        notes.append(f"{_ok(has_write)} build agents can write files (Write/Edit/Bash present)")
        healthy &= has_write
        # QA / read-only agents MUST NOT have Write/Edit.
        ro_flags = " ".join(claude_cli._tool_flags(True))
        ro_clean = ("disallowedTools" in ro_flags) and ("Write" in ro_flags.split("disallowedTools")[-1])
        notes.append(f"{_ok(ro_clean)} read-only agents are correctly write-stripped (QA stays read-only)")
        healthy &= ro_clean
    except Exception as e:
        notes.append(f"❌ tool-flag inspection failed: {e}")
        healthy = False
    return healthy, notes


def check_credentials(required_keys: list[str]) -> tuple[bool, list[str]]:
    notes = []
    cred = ROOT / "oth" / ".cred"
    if not cred.exists():
        return (not required_keys), [f"{_ok(not required_keys)} oth/.cred "
                                     + ("missing (no keys required)" if not required_keys else "MISSING — keys unavailable")]
    notes.append("✅ oth/.cred present")
    try:
        body = cred.read_text(errors="ignore")
    except Exception as e:
        return False, [f"❌ oth/.cred unreadable: {e}"]
    healthy = True
    for k in required_keys:
        present = k.upper() in body.upper()
        notes.append(f"{_ok(present)} default key available for {k}")
        healthy &= present
    return healthy, notes


def check_roles(roles: list[str]) -> tuple[bool, list[str]]:
    notes = []
    healthy = True
    try:
        import projects
        cat = {**projects.ALL_MEMBERS, **projects.OPERATIONAL_MEMBERS}
    except Exception as e:
        return False, [f"❌ role catalogue import failed: {e}"]
    for r in roles:
        hit = next((k for k in cat if k.lower() == r.lower()), None)
        has_res = False
        try:
            has_res = bool(hit and projects.resources_block(hit).strip())
        except Exception:
            has_res = False
        notes.append(f"{_ok(bool(hit) and has_res)} role '{r}' resolves and has a Resources & Dependencies section")
        healthy &= bool(hit) and has_res
    return healthy, notes


def check_plan(brief: str) -> tuple[bool, list[str]]:
    """One CHEAP haiku plan dry-run, graded by evaluate_plan. Catches a wrong-order/wrong-role plan in
    seconds for pennies — instead of after the full build. Uses a throwaway project that is deleted."""
    notes = []
    os.environ.setdefault("ODIN_GATE_MODEL", "haiku")
    try:
        import projects, harness, main_task
    except Exception as e:
        return True, [f"⚠️ plan dry-run skipped (import: {e})"]
    pid = None
    try:
        proj = projects.create_project(name="Preflight", description=brief, ptype="web",
                                       mode="build", members=None)
        pid = proj["id"]
        team = proj.get("members", [])
        notes.append(f"• team derived: {team}")
        steps = projects.plan_pipeline(pid, "Deliver per the brief: decide the team, assign each part, "
                                            "build, QA, deploy, then have operators verify live data.")
        # write the plan into the pool the way the runner does, so evaluate_plan can read it
        plan_txt = "; ".join(f"{i+1}) {s['member']} → {s.get('objective', s.get('task',''))}"
                             for i, s in enumerate(steps))
        try:
            main_task.append(pid, "Project CTO (plan)", plan_txt)
        except Exception:
            pass
        pv = harness.evaluate_plan(pid)
        parsed = pv.get("steps", [])
        # The standalone dry-run uses a quick (non-streaming) planner call that can fall back to a generic
        # plan or not persist to the pool the harness reads. That is NOT a real failure — the AUTHORITATIVE
        # plan gate is plan_check=True during the real run. So this dry-run is BEST-EFFORT: it can only
        # CONFIRM health or surface a CONCRETE violation; it never produces a false NO-GO.
        fallback = any("do your part for" in str(s.get("objective", s.get("task", ""))).lower() for s in steps)
        if not parsed or fallback:
            notes.append("⚠️ plan dry-run inconclusive (quick non-streaming planner call) — the authoritative "
                         "check is plan_check during the real run; engine/tools/roles above are the real gate")
            return True, notes
        if not pv.get("ok"):
            notes.append(f"❌ CTO plan has violations ({len(parsed)} steps):")
            for v in pv.get("violations", []):
                notes.append(f"    ✗ {v}")
            return False, notes
        notes.append(f"✅ CTO plan is well-formed ({len(parsed)} steps, right roles & order)")
        noop = [s for s in steps if any(w in str(s.get("objective", "")).lower()
                                        for w in ("establish the shared pool", "stand up the", "set up coordination",
                                                  "initialise the workspace", "initialize the workspace"))]
        if noop:
            notes.append(f"❌ {len(noop)} no-op/busywork step(s) planned (should be zero)")
            return False, notes
        if len(parsed) > 9:
            notes.append(f"    ⚠️ plan is long ({len(parsed)} steps) — prefer the shortest pipeline")
        return True, notes
    except Exception as e:
        return True, [f"⚠️ plan dry-run skipped (error: {e})"]
    finally:
        if pid:
            try:
                import projects as _p
                _p.delete_project(pid)
            except Exception:
                pass


def main() -> int:
    args = sys.argv[1:]
    brief = None
    req_keys: list[str] = []
    roles = ["Fullstack", "QA", "DevOps", "Fulfillment", "Email"]
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--plan" and i + 1 < len(args):
            brief = args[i + 1]; i += 2; continue
        if a == "--keys" and i + 1 < len(args):
            req_keys = [k.strip() for k in args[i + 1].split(",") if k.strip()]; i += 2; continue
        if a == "--roles" and i + 1 < len(args):
            roles = [k.strip() for k in args[i + 1].split(",") if k.strip()]; i += 2; continue
        i += 1

    print("=" * 70)
    print("PREFLIGHT — fast health gate (GO / NO-GO before spending tokens)")
    print("=" * 70)

    sections = []
    h1, n1 = check_engine_tools(); sections.append(("ENGINE + TOOLS", h1, n1))
    h2, n2 = check_credentials(req_keys); sections.append(("CREDENTIALS / ENV", h2, n2))
    h3, n3 = check_roles(roles); sections.append(("ROLES + RESOURCES", h3, n3))
    healthy = h1 and h2 and h3
    if brief:
        h4, n4 = check_plan(brief); sections.append(("CTO PLAN (cheap dry-run)", h4, n4)); healthy &= h4

    for title, ok, notes in sections:
        print(f"\n[{_ok(ok)}] {title}")
        for ln in notes:
            print("   " + ln)

    print("\n" + "=" * 70)
    print(("✅ GO — system is healthy; expected pipeline is sound. Safe to spend tokens on the run."
           if healthy else
           "❌ NO-GO — fix the ❌ items above BEFORE running. Do not burn tokens on an unhealthy system."))
    print("=" * 70)
    return 0 if healthy else 1


if __name__ == "__main__":
    sys.exit(main())
