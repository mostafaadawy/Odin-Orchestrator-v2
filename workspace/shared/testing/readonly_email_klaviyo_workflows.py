"""
test_3_email_klaviyo_readonly.py — Test 3: Email marketing via Klaviyo. READ-ONLY.

Real user flow: create an Email project that asks ONLY for the Email agent (Klaviyo); CTO is the manager
(always present). No DevOps or any other agent. The project READS: number of live workflows, draft
workflows, total workflows, plus metrics and lists. Nothing is sent or changed.
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import harness  # noqa: E402
from harness import log  # noqa: E402

PROMPT = ("Email marketing via Klaviyo — READ ONLY. Do NOT send or change anything. Report: number of "
          "LIVE workflows, DRAFT workflows, and TOTAL workflows; plus key metrics and the lists. Use ONLY "
          "the Email agent. Do not involve DevOps or any other agent.")


def main() -> int:
    import projects
    log("=" * 74)
    log("READ-ONLY — Email / Klaviyo (read-only)")
    log("=" * 74)

    proj = projects.create_project(
        name="Email — Klaviyo workflows (read-only)",
        description=PROMPT, ptype="email", mode="build",
        members=[{"name": "Email", "role": "Email & Lifecycle", "avatar": "generic"}],
        auto_approve=False,
    )
    pid = proj["id"]
    log(f"  ✓ created — name: {proj['name']}  ·  id: {pid}")

    members = proj.get("members", [])

    # GROUND TRUTH from real Klaviyo — fails if not truly connected or the numbers are inconsistent.
    truth = harness.klaviyo_truth()
    fl = (truth.get("flows") or {})
    kl_connected = bool(fl.get("ok"))
    total = fl.get("total")
    by = fl.get("by_status") or {}
    live, draft = by.get("live"), by.get("draft")
    metrics_ok = bool((truth.get("metrics") or {}).get("ok"))
    lists_ok = bool((truth.get("lists") or {}).get("ok"))

    timeout = harness.smart_timeout("single", agents=1)
    log(f"\n[run] read-only query — timeout {timeout}s…")
    harness.run_flow(pid, "Read Klaviyo: number of live/draft/total workflows, metrics, lists. Read-only.", timeout)
    answer = harness.pool_text(pid, exclude_owner_cto=True)
    truthful, snakes = harness.truthfulness(pid)

    log("\n" + "=" * 60 + "\n  STRONG SCORECARD\n" + "=" * 60)
    s1 = harness.scoreline("KLAVIYO TRULY CONNECTED", kl_connected, f"flows.ok={fl.get('ok')}")
    s2 = harness.scoreline("REAL WORKFLOW COUNTS", isinstance(total, int) and isinstance(live, int) and isinstance(draft, int),
                           f"total={total} live={live} draft={draft}")
    s3 = harness.scoreline("COUNT INTEGRITY (total = live + draft)",
                           isinstance(total, int) and total == (live or 0) + (draft or 0))
    s4 = harness.scoreline("AGENT REPORTED THE REAL NUMBERS",
                           all(isinstance(x, int) and str(x) in answer for x in (total, live, draft)),
                           "live/draft/total all present in the agent's answer"
                           if all(isinstance(x, int) and str(x) in answer for x in (total, live, draft))
                           else "the real numbers are NOT all in the answer (data didn't flow / invented)")
    s5 = harness.scoreline("METRICS + LISTS READABLE", metrics_ok and lists_ok, f"metrics={metrics_ok} lists={lists_ok}")
    s6 = harness.scoreline("EMAIL-ONLY, NO DEVOPS", any(m.lower() == "email" for m in members) and not any(
        m.lower() in ("devops", "frontend", "backend", "shipping", "qa", "security", "database") for m in members),
        f"members={members}")
    s7 = harness.scoreline("CTO PRESENT (manager)", harness.assert_cto_present(pid))
    s8 = harness.scoreline("TRUTHFUL (no fake success)", truthful, f"snakes={snakes or 'none'}")

    ok = all([s1, s2, s3, s4, s5, s6, s7, s8])
    log("\n" + ("  ✅ TEST 3 PASSED — real Klaviyo data flowed read-only"
                if ok else "  ❌ TEST 3 REVEALED A GAP — fix the rows above (do NOT weaken the test)"))
    harness.SeedingPrompt.run(project_ids=[pid], passed=ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
