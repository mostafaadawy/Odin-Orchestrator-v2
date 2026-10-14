"""
run_all.py — ONE command to run EVERY test in this folder and bring back all results.

Auto-discovers tests: any *.py in testing/ that defines a `main()` (except this runner, harness, and
__init__). Future tests are picked up automatically — just drop a new file here with a `main()`.

- Runs each test in sequence, in a sensible order (known tests first, then any new ones).
- Each test prints its own STRONG scorecard; this runner adds a final aggregate SUMMARY (pass/fail +
  duration per test) and exits non-zero if anything failed.
- Keeps all created data by default (seeding) so results can be fetched — override with ODIN_TEST_CLEAN=1.
- Test 1 stays safe (propose-only) unless you set ODIN_TEST_PROD_DEPLOY=1 for the real production deploy.

Run from the repo root:   python3 testing/run_all.py
"""
from __future__ import annotations

import importlib
import os
import pathlib
import sys
import time
import traceback

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
for p in (str(HERE), str(ROOT / "server")):
    if p not in sys.path:
        sys.path.insert(0, p)

# NOTE: we do NOT force ODIN_TEST_KEEP here, so an INTERACTIVE run shows the per-test
# keep/clean prompt. The loop daemon (loop.sh) sets ODIN_TEST_KEEP=1 itself so it never blocks.
# A non-interactive run with no choice set defaults to KEEP inside SeedingPrompt (safe).


def _ensure_venv():
    """If deps aren't importable under the current interpreter, re-run THIS runner under .venv via a
    subprocess (reliable + streams output) instead of os.execv (which could exit silently). Returns
    True if it handled everything in a child (caller should exit)."""
    try:
        import fastapi  # noqa: F401
        return False
    except ModuleNotFoundError:
        venv = ROOT / ".venv" / "bin" / "python3"
        if venv.exists() and os.environ.get("ODIN_RUNALL_REEXEC") != "1":
            import subprocess
            print(f"(switching to project venv: {venv})", flush=True)
            env = dict(os.environ, ODIN_RUNALL_REEXEC="1")
            rc = subprocess.run([str(venv), str(pathlib.Path(__file__).resolve()), *sys.argv[1:]], env=env).returncode
            sys.exit(rc)
        print("⚠ project deps not importable and no usable .venv found — run: "
              "source .venv/bin/activate && python3 testing/", flush=True)
        sys.exit(2)
    return False


# Known tests in the order requested; any OTHER test files are appended automatically (future-proof).
KNOWN_ORDER = [
    "readonly_shipping_vq_status",
    "readonly_email_klaviyo_workflows",
    "sandbox_revealer_multiagent",
    "sandbox_deploy_overwrite_check",
]
SKIP = {"run_all", "harness", "__init__", "__main__"}


def discover(flt: str = "") -> list[str]:
    mods = []
    for f in sorted(HERE.glob("*.py")):
        name = f.stem
        if name in SKIP:
            continue
        mods.append(name)
    ordered = [m for m in KNOWN_ORDER if m in mods] + [m for m in mods if m not in KNOWN_ORDER]
    if flt and flt.lower() not in ("all", "*"):
        ordered = [m for m in ordered if flt.lower() in m.lower()]
    return ordered


PROGRESS = HERE / "results" / "PROGRESS.txt"


def _write_progress(tests, status, t0_all):
    """A simple human-readable board you can just WATCH (cat / tail -f testing/results/PROGRESS.txt):
        Odin tests — 1/4 done
          [1] organics-prod-deploy (canonical infra/deploy_run.sh)   ▶ RUNNING
          [2] readonly_shipping_vq_status          ✅ PASS (12.3s)
          ..."""
    try:
        PROGRESS.parent.mkdir(parents=True, exist_ok=True)
        done = sum(1 for s in status.values() if s[0] in ("PASS", "FAIL"))
        lines = [f"Odin tests — {done}/{len(tests)} done   (elapsed {int(time.time() - t0_all)}s)   "
                 + time.strftime("%H:%M:%S")]
        icon = {"PENDING": "·  pending", "RUNNING": "▶  RUNNING", "PASS": "✅ PASS", "FAIL": "❌ FAIL"}
        for i, name in enumerate(tests, 1):
            st, secs = status.get(name, ("PENDING", 0))
            secs_s = f" ({secs}s)" if st in ("PASS", "FAIL") else ""
            lines.append(f"  [{i}] {name:<44} {icon[st]}{secs_s}")
        PROGRESS.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except Exception:
        pass


def main() -> int:
    _ensure_venv()
    # SEED-ON-PASS by default (testing only): keep a PASSING run's data for the owner to inspect, clean
    # only a genuine FAIL. This is purely a post-verdict cleanup policy — it never changes a test's
    # checks or the AI. Set here so it applies even with an already-running loop daemon. (Explicit
    # ODIN_TEST_KEEP/ODIN_TEST_CLEAN still override if the owner sets them.)
    os.environ.setdefault("ODIN_TEST_SEED_ON_PASS", "1")
    # SPEED (testing only): run the evaluative QA / CTO-review gates on a fast model so we don't wait
    # ~10 min/step. This NEVER skips a rule and NEVER touches production (which sets no model). Override
    # with ODIN_GATE_MODEL="" to force the full model on the gates too.
    os.environ.setdefault("ODIN_GATE_MODEL", "haiku")
    flt = ""
    for a in sys.argv[1:]:
        if not a.startswith("-"):
            flt = a
            break
    tests = discover(flt)
    t0_all = time.time()
    status = {n: ("PENDING", 0) for n in tests}
    _write_progress(tests, status, t0_all)
    print("=" * 78)
    print(f"ODIN — RUN {'TESTS matching ' + repr(flt) if flt else 'ALL TESTS'} ({len(tests)} found)   "
          f"keep_data={os.environ.get('ODIN_TEST_KEEP') == '1'}")
    print("  " + "  ·  ".join(tests))
    print("=" * 78)

    results = []
    for i, name in enumerate(tests, 1):
        print("\n\n" + "#" * 78)
        print(f"# RUNNING [{i}/{len(tests)}]: {name}")
        print("#" * 78)
        status[name] = ("RUNNING", 0)
        _write_progress(tests, status, t0_all)
        t0 = time.time()
        try:
            mod = importlib.import_module(name)
            importlib.reload(mod)
            rc = mod.main() if hasattr(mod, "main") else 0
            ok = (rc == 0)
        except Exception:
            ok = False
            print(f"\n!! {name} crashed:\n{traceback.format_exc()}")
        secs = round(time.time() - t0, 1)
        status[name] = ("PASS" if ok else "FAIL", secs)
        _write_progress(tests, status, t0_all)
        print(f"# [{i}/{len(tests)}] {name} → {'✅ PASS' if ok else '❌ FAIL'} ({secs}s)")
        results.append((name, ok, secs))

    print("\n\n" + "=" * 78)
    print("FINAL SUMMARY — all tests")
    print("=" * 78)
    passed = sum(1 for _, ok, _ in results if ok)
    for name, ok, secs in results:
        print(f"  {'✅ PASS' if ok else '❌ FAIL'}  {name:<46} {secs:>7.1f}s")
    print("-" * 78)
    print(f"  {passed}/{len(results)} passed")
    print("=" * 78)
    _write_progress(tests, status, t0_all)
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
