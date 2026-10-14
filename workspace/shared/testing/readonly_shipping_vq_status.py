"""
test_2_shipping_vq_readonly.py — Test 2: Shipping / Fulfillment provider (VQ / Veeqo). READ-ONLY.

Real user flow: create a Fulfillment project that asks ONLY for the Shipping agent (VQ); CTO is the
manager (always present). NO folder is required — the test proves the app does not block when no folder
is selected. The project only READS from the external provider: connection status, total order count,
channels/vendors, and confirms it's ready to answer future per-order status requests. Nothing is written.
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import harness  # noqa: E402
from harness import log  # noqa: E402

PROMPT = ("Shipping/fulfillment via the Veeqo (VQ) provider — READ ONLY. Do NOT create or change "
          "anything. Tasks: (1) check the VQ connection status, (2) return the total number of orders, "
          "(3) list the channels/vendors, (4) confirm you are ready to answer future status requests for "
          "any order. Use ONLY the Fulfillment agent. No folders are needed for this project.")


def main() -> int:
    import projects
    log("=" * 74)
    log("READ-ONLY — Shipping / VQ (read-only, folders optional)")
    log("=" * 74)

    # No local_path / sources at all → proves folders are optional and do not block creation.
    proj = projects.create_project(
        name="Fulfillment — VQ status (read-only)",
        description=PROMPT, ptype="fulfillment", mode="build",
        members=[{"name": "Fulfillment", "role": "Fulfillment Operations", "avatar": "generic"}],
        auto_approve=False,                      # read-only; nothing to approve
    )
    pid = proj["id"]
    log(f"  ✓ created with NO folder selected — name: {proj['name']}  ·  id: {pid}")

    members = proj.get("members", [])

    # GROUND TRUTH from the real provider — the test fails if VQ is not truly connected/returning data.
    truth = harness.veeqo_truth()
    o = (truth.get("orders") or {})
    vq_connected = bool(o.get("ok"))
    real_count = o.get("count")
    carriers_ok = bool((truth.get("carriers") or {}).get("ok"))

    timeout = harness.smart_timeout("single", agents=1)
    log(f"\n[run] read-only query — timeout {timeout}s…")
    harness.run_flow(pid, "Read VQ: connection status, total order count, channels/vendors. Read-only.", timeout)
    answer = harness.pool_text(pid, exclude_owner_cto=True)
    truthful, snakes = harness.truthfulness(pid)

    log("\n" + "=" * 60 + "\n  STRONG SCORECARD\n" + "=" * 60)
    s1 = harness.scoreline("VQ TRULY CONNECTED", vq_connected, f"orders.ok={o.get('ok')}")
    s2 = harness.scoreline("REAL ORDER COUNT", isinstance(real_count, int), f"count={real_count}")
    # the agent must have REPORTED the real number it read (not invented one) — proof of real data flow
    s3 = harness.scoreline("AGENT REPORTED THE REAL COUNT",
                           isinstance(real_count, int) and str(real_count) in answer,
                           "live count present in the agent's answer" if (isinstance(real_count, int) and str(real_count) in answer)
                           else "real count NOT in the agent's answer (data didn't flow or was invented)")
    s4 = harness.scoreline("CHANNELS/VENDORS READABLE", carriers_ok)
    s5 = harness.scoreline("FULFILLMENT-ONLY TEAM", any(m.lower() == "fulfillment" for m in members) and not any(
        m.lower() in ("devops", "fullstack", "mobile", "email", "qa") for m in members), f"members={members}")
    s6 = harness.scoreline("CTO PRESENT (manager)", harness.assert_cto_present(pid))
    # REAL check (not hardcoded): the project must have been created with NO folder set, proving the
    # app did not block on a missing folder.
    s7 = harness.scoreline("FOLDER OPTIONAL — created with NO folder",
                           bool(pid) and not proj.get("localPath") and not (proj.get("sources") or []),
                           f"localPath={proj.get('localPath')!r} sources={proj.get('sources')!r}")
    s8 = harness.scoreline("TRUTHFUL (no fake success)", truthful, f"snakes={snakes or 'none'}")

    ok = all([s1, s2, s3, s4, s5, s6, s7, s8])
    log("\n" + ("  ✅ TEST 2 PASSED — real VQ data flowed read-only"
                if ok else "  ❌ TEST 2 REVEALED A GAP — fix the rows above (do NOT weaken the test)"))
    harness.SeedingPrompt.run(project_ids=[pid], passed=ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
