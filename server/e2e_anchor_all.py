#!/usr/bin/env python3
"""
e2e_anchor_all.py — ONE command to run every Anchor Connect Phase-1 test.

Runs the three suites, each in its own process (clean isolation), and prints one summary:
  1. logic lifecycle      (e2e_anchor.py)        — queue + webhook + retry + fail + no-double-process
  2. HTTP contract        (e2e_anchor_http.py)   — the real /anchor/v1 endpoints + auth
  3. live read-only data  (e2e_anchor_live.py)   — real projects query LIVE Klaviyo/Veeqo (GET only)

Run:  python3 server/e2e_anchor_all.py
(#3 needs network access to Klaviyo/Veeqo + the keys in workspace/shared/oth/.cred — run it on your Mac.)
"""
from __future__ import annotations

import subprocess
import sys
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
SUITES = [
    ("logic lifecycle", "e2e_anchor.py"),
    ("HTTP contract", "e2e_anchor_http.py"),
    ("live read-only data (Klaviyo/Veeqo)", "e2e_anchor_live.py"),
]


def main() -> int:
    results = {}
    for label, fname in SUITES:
        print("\n" + "#" * 74)
        print(f"#  {label}   ({fname})")
        print("#" * 74)
        rc = subprocess.run([sys.executable, str(HERE / fname)]).returncode
        results[label] = rc

    print("\n" + "=" * 74)
    print("ANCHOR CONNECT — PHASE 1 E2E SUMMARY")
    print("=" * 74)
    for label, rc in results.items():
        print(f"  {'✅ PASS' if rc == 0 else '❌ FAIL'}   {label}")
    all_ok = all(rc == 0 for rc in results.values())
    print("-" * 74)
    print("  ✅ ALL ANCHOR E2E PASSED" if all_ok else
          "  ❌ Some suites failed — a failure in 'live read-only data' off your Mac is usually just\n"
          "     no network access to Klaviyo/Veeqo; run it on your Mac to see real counts.")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
