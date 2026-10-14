#!/usr/bin/env python3
"""
Real notifications system — the sync feed for recurring/periodical work (distinct from the "Guide / What's
New" docs bell). Events: a scheduled project STARTED its run, FINISHED (with a result), or raised a
CRITICAL/attention finding. Each notification carries a deep-link target (pid + optional chat id) so the UI
can redirect. Supports unread tracking + mark-one / mark-all read.

Persisted to data/notifications.json (newest first, capped). Read/write only — no side effects on projects.
"""
from __future__ import annotations
import time, uuid, threading
import store  # type: ignore

_FILE = "notifications.json"
_CAP = 300
_LOCK = threading.RLock()   # serialize read-modify-write so concurrent writers can't clobber notifications

def _load():
    d = store.read_json(_FILE, {"items": []})
    if "items" not in d:
        d = {"items": []}
    return d

def _save(d):
    d["items"] = d["items"][:_CAP]
    store.write_json(_FILE, d)

def add(kind: str, title: str, body: str = "", pid: str = "", cid: str = "",
        project_name: str = "", severity: str = "info", icon: str = "🔔") -> dict:
    """kind: started | finished | finding | info. severity: info | attention | critical."""
    with _LOCK:
        d = _load()
        n = {"id": uuid.uuid4().hex[:12], "ts": time.time(), "kind": kind, "title": title, "body": body,
             "pid": pid, "cid": cid, "project": project_name, "severity": severity, "icon": icon, "read": False}
        d["items"].insert(0, n)
        _save(d)
        return n

def list(unread_only: bool = False, limit: int = 100) -> list:
    items = _load()["items"]
    if unread_only:
        items = [n for n in items if not n.get("read")]
    return items[:limit]

def unread_count() -> int:
    return sum(1 for n in _load()["items"] if not n.get("read"))

def mark_read(nid: str = "", all: bool = False) -> dict:
    with _LOCK:
        d = _load(); changed = 0
        for n in d["items"]:
            if all or n.get("id") == nid:
                if not n.get("read"):
                    n["read"] = True; changed += 1
        _save(d)
        return {"ok": True, "marked": changed, "unread": unread_count()}

def clear(all: bool = False) -> dict:
    with _LOCK:
        d = _load()
        d["items"] = [] if all else [n for n in d["items"] if not n.get("read")]
        _save(d)
        return {"ok": True, "remaining": len(d["items"])}
