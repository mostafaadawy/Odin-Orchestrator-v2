"""
run_timer.py — E2E timing for a task run (start at task begin, stop at completion).

Used to compare same-difficulty runs WITHOUT caching vs WITH caching and show the speedup.
Timings persist to data/run_timings.json so the UI / a report can read them.
"""
from __future__ import annotations

import json
import os
import pathlib
import time

DATA = pathlib.Path(__file__).resolve().parent.parent / "data"
DATA.mkdir(exist_ok=True)
STORE = DATA / "run_timings.json"


def _load() -> list:
    try:
        return json.loads(STORE.read_text(encoding="utf-8"))
    except Exception:
        return []


def _save(rows: list) -> None:
    STORE.write_text(json.dumps(rows[-200:], indent=2), encoding="utf-8")


class Timer:
    """timer = Timer(pid, task); ... ; timer.stop(ok=True)"""

    def __init__(self, pid: str, task: str, cached: bool | None = None):
        self.pid = pid
        self.task = (task or "")[:120]
        # if not told, infer from the live cache switch
        self.cached = (os.environ.get("ODIN_DISABLE_CACHE") != "1") if cached is None else cached
        self.t0 = time.time()
        self.seconds = None

    def stop(self, ok: bool = True) -> float:
        self.seconds = round(time.time() - self.t0, 2)
        rows = _load()
        rows.append({
            "pid": self.pid, "task": self.task, "cached": self.cached,
            "ok": ok, "seconds": self.seconds, "ts": int(self.t0),
        })
        _save(rows)
        return self.seconds


def compare(task_contains: str = "") -> dict:
    """Latest cached vs non-cached run (optionally for a task substring) + speedup."""
    rows = [r for r in _load() if r.get("ok") and task_contains.lower() in r.get("task", "").lower()]
    cached = next((r for r in reversed(rows) if r.get("cached")), None)
    plain = next((r for r in reversed(rows) if not r.get("cached")), None)
    out = {"cached": cached, "non_cached": plain, "speedup": None, "saved_seconds": None}
    if cached and plain and cached["seconds"] > 0:
        out["speedup"] = round(plain["seconds"] / cached["seconds"], 2)
        out["saved_seconds"] = round(plain["seconds"] - cached["seconds"], 2)
    return out


if __name__ == "__main__":
    import sys
    print(json.dumps(compare(sys.argv[1] if len(sys.argv) > 1 else ""), indent=2))
