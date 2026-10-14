"""
Live activity bus (Phase 3) — drives the animated, heartbeat agent indicators.

Tracks, in memory, which agents are currently ACTIVE on which project, and a rolling flow log
(e.g. Frontend → Backend → DevOps). The cockpit polls /activity (or subscribes to the SSE feed)
to animate avatars: an agent marked active gets the heartbeat; the flow log draws the hand-offs.
"""
from __future__ import annotations

import time
import threading

_LOCK = threading.RLock()
# active[(pid, agent)] = {"since": ts, "task": str}
_active: dict[tuple[str, str], dict] = {}
_flow: list[dict] = []          # recent hand-offs / events
_ACTIVE_TTL = 180.0            # seconds an "active" mark lingers without a refresh (long enough
                               # that a silent engine 'thinking' gap never drops the indicator)


def mark_active(pid: str, agent: str, task: str = "", phase: str = "working") -> None:
    with _LOCK:
        prev = _active.get((pid, agent), {})
        _active[(pid, agent)] = {"since": prev.get("since", time.time()), "task": task,
                                 "beat": time.time(), "phase": phase}
        _flow.append({"ts": time.time(), "pid": pid, "agent": agent, "task": task,
                      "phase": phase, "type": "active"})
        del _flow[:-300]


def beat(pid: str, agent: str) -> None:
    with _LOCK:
        if (pid, agent) in _active:
            _active[(pid, agent)]["beat"] = time.time()


def mark_idle(pid: str, agent: str) -> None:
    with _LOCK:
        _active.pop((pid, agent), None)


def log_flow(pid: str, frm: str, to: str, note: str = "") -> None:
    with _LOCK:
        _flow.append({"ts": time.time(), "pid": pid, "from": frm, "to": to,
                      "note": note, "type": "handoff"})
        del _flow[:-300]


def _prune() -> None:
    now = time.time()
    for k in [k for k, v in _active.items() if now - v.get("beat", v["since"]) > _ACTIVE_TTL]:
        _active.pop(k, None)


def snapshot(pid: str | None = None) -> dict:
    with _LOCK:
        _prune()
        active = [{"pid": p, "agent": a, "task": v.get("task", ""), "phase": v.get("phase", "working"),
                   "since": v["since"]} for (p, a), v in _active.items()
                  if pid is None or p == pid]
        flow = [f for f in _flow[-60:] if pid is None or f.get("pid") == pid]
        return {"active": active, "flow": flow, "ts": now_iso()}


def now_iso() -> str:
    return time.strftime("%H:%M:%S")
