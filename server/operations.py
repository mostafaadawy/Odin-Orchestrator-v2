"""
Operations — the ONE source of truth for a running task (deploy, sync, …).

The whole point: every long task becomes a single record the UI can WATCH and STOP.
It owns four things in one place, so nothing is scattered across screens, chats, LLM turns
and approval files anymore:
  • a LIVE log (every command + file change + output, as it happens),
  • a STATE (running / done / failed / stopped),
  • a STOP flag (the executor checks it between steps and aborts cleanly),
  • the final RESULT (so a finish/stop card can fire reliably from real completion).

In-memory for instant live updates + persisted to data/operations.json so it survives a
backend restart and the UI can re-attach after navigation. No AI anywhere in here.
"""
from __future__ import annotations

import threading
import time
import uuid

import store

_LOCK = threading.RLock()
_OPS: dict[str, dict] = {}      # oid -> op
_FILE = "operations.json"
_LOG_CAP = 800                  # keep the last N log lines per op (plenty for a deploy)
_KEEP = 50                      # how many finished ops to retain on disk


def _load() -> None:
    if _OPS:
        return
    for op in store.read_json(_FILE, []):
        _OPS[op["id"]] = op
        # a process restart means nothing is truly still running — mark stale runs interrupted
        if op.get("state") == "running":
            op["state"] = "stopped"
            op["summary"] = "interrupted by a backend restart"


def _persist() -> None:
    ops = sorted(_OPS.values(), key=lambda o: o.get("started", 0), reverse=True)[:_KEEP]
    store.write_json(_FILE, ops)


def create(pid: str, kind: str, title: str, meta: dict | None = None) -> str:
    """Open a new operation in the 'running' state and return its id."""
    _load()
    oid = uuid.uuid4().hex[:12]
    op = {
        "id": oid, "pid": pid, "kind": kind, "title": title,
        "state": "running", "summary": "",
        "started": time.time(), "ended": 0.0,
        "stop": False, "log": [], "steps": [], "meta": meta or {},
        # block→ask→resume: when blocked, `question` explains what's wrong and `needs` lists the
        # exact fields to collect; the owner's answers land in `answers` and drive the resume.
        "question": "", "needs": [], "answers": {},
    }
    with _LOCK:
        _OPS[oid] = op
        _persist()
    return oid


def ask(oid: str, question: str, needs: list | None = None) -> dict:
    """Block the operation and ASK the owner for the exact info needed to continue. `needs` is a list
    of {key,label,placeholder} fields the UI renders as inputs."""
    op = _OPS.get(oid)
    if not op:
        return {"ok": False, "error": "no such operation"}
    with _LOCK:
        op["state"] = "blocked"
        op["question"] = question
        op["needs"] = needs or []
        op["summary"] = question
        op["ended"] = time.time()
        op["log"].append({"t": time.time(), "line": "⛔ Blocked — need your input: " + question})
        _persist()
    return {"ok": True, "id": oid, "needs": op["needs"]}


def set_meta(oid: str, key: str, value) -> None:
    op = _OPS.get(oid)
    if not op:
        return
    with _LOCK:
        op.setdefault("meta", {})[key] = value
        _persist()


def provide(oid: str, answers: dict) -> dict:
    """Record the owner's answers so a resume can use them to CORRECT the operation."""
    op = _OPS.get(oid)
    if not op:
        return {"ok": False, "error": "no such operation"}
    with _LOCK:
        op["answers"] = {**(op.get("answers") or {}), **(answers or {})}
        op["log"].append({"t": time.time(), "line": "✍️ You provided: " + ", ".join(f"{k}={v}" for k, v in (answers or {}).items())})
        _persist()
    return {"ok": True, "id": oid, "answers": op["answers"]}


def log(oid: str, line: str) -> None:
    op = _OPS.get(oid)
    if not op or not line:
        return
    with _LOCK:
        for ln in str(line).splitlines() or [str(line)]:
            op["log"].append({"t": time.time(), "line": ln[:2000]})
        if len(op["log"]) > _LOG_CAP:
            op["log"] = op["log"][-_LOG_CAP:]
        _persist()


def step(oid: str, name: str, ok: bool, detail: str = "") -> None:
    op = _OPS.get(oid)
    if not op:
        return
    with _LOCK:
        op["steps"].append({"name": name, "ok": bool(ok), "detail": detail[:400], "t": time.time()})
        _persist()


def set_state(oid: str, state: str, summary: str = "") -> None:
    """state ∈ {running, done, failed, stopped}. Finishing stamps 'ended'."""
    op = _OPS.get(oid)
    if not op:
        return
    with _LOCK:
        op["state"] = state
        if summary:
            op["summary"] = summary
        if state in ("done", "failed", "stopped"):
            op["ended"] = time.time()
        _persist()


def request_stop(oid: str) -> dict:
    op = _OPS.get(oid)
    if not op:
        return {"ok": False, "error": "no such operation"}
    with _LOCK:
        if op["state"] == "running":
            op["stop"] = True
            op["log"].append({"t": time.time(), "line": "⏹ Stop requested — finishing the current step then halting…"})
            _persist()
    return {"ok": True, "id": oid, "state": op["state"]}


def stop_requested(oid: str) -> bool:
    op = _OPS.get(oid)
    return bool(op and op.get("stop"))


def purge(pid: str) -> int:
    """Remove ALL operations for a project (memory + disk) — used when a project is deleted so a
    re-created project with the same id never inherits old deploy status/logs."""
    _load()
    with _LOCK:
        gone = [oid for oid, op in list(_OPS.items()) if op.get("pid") == pid]
        for oid in gone:
            _OPS.pop(oid, None)
        if gone:
            _persist()
    return len(gone)


def get(oid: str) -> dict | None:
    _load()
    return _OPS.get(oid)


def list_for(pid: str | None = None, limit: int = 20) -> list:
    _load()
    ops = sorted(_OPS.values(), key=lambda o: o.get("started", 0), reverse=True)
    if pid:
        ops = [o for o in ops if o.get("pid") == pid]
    # don't ship the full log in the list view — keep it light
    return [{k: v for k, v in o.items() if k != "log"} for o in ops[:limit]]


def latest(pid: str) -> dict | None:
    _load()
    ops = [o for o in _OPS.values() if o.get("pid") == pid]
    return max(ops, key=lambda o: o.get("started", 0)) if ops else None
