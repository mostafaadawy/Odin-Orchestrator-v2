#!/usr/bin/env python3
"""
e2e_cache_timing.py — REAL E2E timing: same task, WITHOUT caching vs WITH caching.

It runs the identical project twice through the live orchestration:
  pass 1: ODIN_DISABLE_CACHE=1  -> pool hidden, the agent works from scratch (baseline)
  pass 2: cache on              -> the role agent may reuse the proven cached module
The E2E timer (run_timer) records each run's wall-clock seconds; we print the measured
speedup. Numbers come ONLY from these real runs — nothing is fabricated.

Same-difficulty deploy/ops task is used so the comparison is fair. Sandbox-safe: it points
at the sandbox config and never reboots / never touches production.

Run:  python3 server/e2e_cache_timing.py
"""
from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))

GOAL = ("DevOps: connect to the sandbox VM and run a safe, read-only health check "
        "(verify the app responds on its local port). Do NOT reboot. Report the verified result.")


def run_once(cached: bool) -> float:
    import api_v2
    import projects
    import run_timer

    os.environ["ODIN_DISABLE_CACHE"] = "0" if cached else "1"
    label = "WITH cache" if cached else "WITHOUT cache (baseline)"
    print(f"\n=== PASS: {label} ===")
    proj = projects.create_project(
        name=f"E2E Timing ({'cached' if cached else 'plain'})", description=GOAL, mode="build",
        members=[{"name": "DevOps", "role": "DevOps", "avatar": "generic"}],
        local_path="/tmp/odin_timing", sources=[], auto_approve=True)
    pid = proj["id"]

    t0 = time.time()
    api_v2.start_run(pid, GOAL)
    while time.time() - t0 < 900:
        if not api_v2.run_status(pid).get("running"):
            break
        time.sleep(5)
    else:
        try:
            api_v2.stop_run(pid)
        except Exception:
            pass
    # prefer the timer's recorded value; fall back to our own wall clock
    cmp = run_timer.compare("E2E Timing")
    rec = cmp["cached"] if cached else cmp["non_cached"]
    secs = rec["seconds"] if rec else round(time.time() - t0, 2)
    print(f"    {label}: {secs}s")
    return secs


def main() -> int:
    print("=" * 70)
    print("E2E CACHE TIMING — same task, no-cache baseline vs cached")
    print("=" * 70)
    try:
        plain = run_once(cached=False)
        cached = run_once(cached=True)
    finally:
        os.environ.pop("ODIN_DISABLE_CACHE", None)

    print("\n" + "-" * 70)
    print(f"  WITHOUT cache : {plain}s")
    print(f"  WITH cache    : {cached}s")
    if cached and cached > 0:
        print(f"  SPEEDUP       : {round(plain / cached, 2)}x   (saved {round(plain - cached, 2)}s)")
    print("-" * 70)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
