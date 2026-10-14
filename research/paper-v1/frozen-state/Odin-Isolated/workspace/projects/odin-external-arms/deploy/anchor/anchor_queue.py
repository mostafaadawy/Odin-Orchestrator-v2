"""
Anchor Connect — smart queue + request lifecycle.

Storage is PLUGGABLE:
  • PostgreSQL (robust) when ANCHOR_PG_DSN is set and reachable  ← the anchor's production store
  • JSON file (data/anchor_queue.json) as a safe fallback so the anchor NEVER breaks if Postgres is down.

Either way, a LARGE AI response is NOT kept inline — it is written to a file under
    data/active_requests/<request_id>/<random>.json
and only a small pointer {"__file__": path} is stored in the row. Small results stay inline (size threshold).
Reads rehydrate the pointer back into the full result. This keeps the DB small and handles big/image responses.

Public API is unchanged (enqueue, next_pending, submit_result, deliver_webhook, get, list_requests, counts,
cancel, remove, clear_all, ack, retry_due, mark_processing, cfg, set_cfg), so anchor_remote.py / the poller
need no changes. Desktop is untouched.
"""
from __future__ import annotations

import json
import os
import time
import uuid
import secrets
import threading
import urllib.request
import urllib.error

import store

_CFG_FILE = "anchor_config.json"
_JSON_FILE = "anchor_queue.json"
_LOCK = threading.RLock()
_INLINE_MAX = 32000
_RESP_ROOT = os.path.join(str(store.WS), "anchor-layer", "active_requests")

# ---- status lifecycle ----
RECEIVED = "received"
QUEUED = "queued"
SENT_TO_LOCAL = "sent_to_local"
RECEIVED_BY_LOCAL = "received_by_local"
PROCESSING = "processing"
PROCESSED = "processed"
RESPONSE_RECEIVED = "response_received"
WEBHOOK_SENT = "webhook_sent"
ACK_PENDING = "ack_pending"
ACKNOWLEDGED = "acknowledged"
FINISHED = "finished"
FAILED = "failed"
CANCELLED = "cancelled"

_PICKABLE = {QUEUED}
_TERMINAL = {ACKNOWLEDGED, FINISHED, FAILED, CANCELLED}

DEFAULT_CFG = {"retry_count": 4, "retry_interval_sec": 600, "poll_limit": 5}


# ---- config (small; JSON) ----
def cfg() -> dict:
    c = store.read_json(_CFG_FILE, {}) or {}
    return {**DEFAULT_CFG, **c}


def set_cfg(**kw) -> dict:
    c = cfg()
    for k, v in kw.items():
        if v is not None and k in DEFAULT_CFG:
            c[k] = int(v)
    store.write_json(_CFG_FILE, c)
    return c


# =====================================================================================================
# STORAGE BACKEND — Postgres if available, else JSON. Both expose the same row primitives.
# =====================================================================================================
_PG_DSN = None  # set to the DSN string when Postgres is active


def backend() -> str:
    return "postgres" if _PG_DSN else "json"


def _pg_init() -> bool:
    """Try to bring up the Postgres backend. Returns True if active. Safe to call once at import."""
    global _PG_DSN
    dsn = os.environ.get("ANCHOR_PG_DSN")
    if not dsn:
        return False
    try:
        import psycopg2
        conn = psycopg2.connect(dsn)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS anchor_requests("
                    "id text PRIMARY KEY, status text, created double precision, data jsonb)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ar_status ON anchor_requests(status)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_ar_created ON anchor_requests(created)")
        conn.commit()
        cur.close()
        conn.close()
        _PG_DSN = dsn
        return True
    except Exception as e:  # noqa
        _PG_DSN = None
        print("[anchor_queue] Postgres unavailable (%s) — using JSON fallback" % str(e)[:120])
        return False


def _pg():
    import psycopg2
    import psycopg2.extras  # noqa
    return psycopg2.connect(_PG_DSN)


# ---- JSON primitives ----
def _json_all() -> list:
    return store.read_json(_JSON_FILE, {"requests": []})["requests"]


def _json_save(rows: list) -> None:
    store.write_json(_JSON_FILE, {"requests": rows[-2000:]})


# ---- unified row primitives (dispatch) ----
def _row_all() -> list:
    if _PG_DSN:
        c = _pg()
        try:
            cur = c.cursor()
            cur.execute("SELECT data FROM anchor_requests ORDER BY created")
            return [r[0] for r in cur.fetchall()]
        finally:
            c.close()
    return list(_json_all())


def _row_get(rid: str) -> dict | None:
    if _PG_DSN:
        c = _pg()
        try:
            cur = c.cursor()
            cur.execute("SELECT data FROM anchor_requests WHERE id=%s", (rid,))
            row = cur.fetchone()
            return row[0] if row else None
        finally:
            c.close()
    for r in _json_all():
        if r["id"] == rid:
            return dict(r)
    return None


def _row_put(req: dict) -> None:
    if _PG_DSN:
        c = _pg()
        try:
            cur = c.cursor()
            cur.execute("INSERT INTO anchor_requests(id,status,created,data) VALUES(%s,%s,%s,%s) "
                        "ON CONFLICT (id) DO UPDATE SET status=EXCLUDED.status, data=EXCLUDED.data",
                        (req["id"], req.get("status"), float(req.get("created", 0) or 0), json.dumps(req)))
            c.commit()
        finally:
            c.close()
        return
    rows = _json_all()
    for i, r in enumerate(rows):
        if r["id"] == req["id"]:
            rows[i] = req
            _json_save(rows)
            return
    rows.append(req)
    _json_save(rows)


def _row_by_status(status: str) -> list:
    if _PG_DSN:
        c = _pg()
        try:
            cur = c.cursor()
            cur.execute("SELECT data FROM anchor_requests WHERE status=%s ORDER BY created", (status,))
            return [r[0] for r in cur.fetchall()]
        finally:
            c.close()
    return [r for r in _json_all() if r.get("status") == status]


def _row_counts() -> dict:
    if _PG_DSN:
        c = _pg()
        try:
            cur = c.cursor()
            cur.execute("SELECT status, COUNT(*) FROM anchor_requests GROUP BY status")
            return {r[0]: r[1] for r in cur.fetchall()}
        finally:
            c.close()
    out = {}
    for r in _json_all():
        out[r.get("status", "?")] = out.get(r.get("status", "?"), 0) + 1
    return out


def _row_delete(rid: str) -> bool:
    if _PG_DSN:
        c = _pg()
        try:
            cur = c.cursor()
            cur.execute("DELETE FROM anchor_requests WHERE id=%s", (rid,))
            n = cur.rowcount
            c.commit()
            return n > 0
        finally:
            c.close()
    rows = _json_all()
    keep = [r for r in rows if r.get("id") != rid]
    if len(keep) == len(rows):
        return False
    _json_save(keep)
    return True


def _row_delete_all() -> int:
    if _PG_DSN:
        c = _pg()
        try:
            cur = c.cursor()
            cur.execute("SELECT COUNT(*) FROM anchor_requests")
            n = cur.fetchone()[0]
            cur.execute("DELETE FROM anchor_requests")
            c.commit()
            return n
        finally:
            c.close()
    n = len(_json_all())
    _json_save([])
    return n


# ---- big-result file offload (backend-agnostic) ----
def _offload(rid: str, result):
    """Big result → a file under active_requests/<rid>/<random>.json; returns a pointer. Small → as-is."""
    if result is None:
        return None
    try:
        blob = json.dumps(result)
    except Exception:
        result = str(result)
        blob = json.dumps(result)
    if len(blob) <= _INLINE_MAX:
        return result
    d = os.path.join(_RESP_ROOT, rid)
    try:
        os.makedirs(d, exist_ok=True)
        # one active result per request — clear old files first (avoid orphans)
        for fn in os.listdir(d):
            try:
                os.remove(os.path.join(d, fn))
            except Exception:
                pass
        path = os.path.join(d, secrets.token_hex(8) + ".json")
        with open(path, "w", encoding="utf-8") as f:
            f.write(blob)
        return {"__file__": path}
    except Exception:
        return result  # if the file write fails, keep it inline so nothing is lost


def _rehydrate(result):
    if isinstance(result, dict) and "__file__" in result:
        try:
            with open(result["__file__"], "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return result


def _remove_files(rid: str) -> None:
    d = os.path.join(_RESP_ROOT, rid)
    try:
        if os.path.isdir(d):
            for fn in os.listdir(d):
                try:
                    os.remove(os.path.join(d, fn))
                except Exception:
                    pass
            os.rmdir(d)
    except Exception:
        pass


# =====================================================================================================
# LIFECYCLE (one copy, backend-agnostic)
# =====================================================================================================
def get(rid: str) -> dict | None:
    r = _row_get(rid)
    if r is not None:
        r["result"] = _rehydrate(r.get("result"))
    return r


def _update(rid: str, **fields) -> dict | None:
    with _LOCK:
        r = _row_get(rid)   # raw (result may be a pointer)
        if not r:
            return None
        if "status" in fields and fields["status"] != r.get("status"):
            r.setdefault("history", []).append({"status": fields["status"], "ts": time.time()})
        if "result" in fields:
            r["result"] = _offload(rid, fields.pop("result"))  # big → file pointer; small → inline
        r.update(fields)
        r["updated"] = time.time()
        _row_put(r)
        return get(rid)


def enqueue(project: str, payload, sender: str = "", webhook_url: str = "", api_key_id: str = "") -> dict:
    rid = "req_" + uuid.uuid4().hex[:16]
    now = time.time()
    req = {"id": rid, "project": project, "payload": payload, "sender": sender,
           "webhook_url": webhook_url, "api_key_id": api_key_id,
           "status": QUEUED, "result": None, "created": now, "updated": now,
           "history": [{"status": RECEIVED, "ts": now}, {"status": QUEUED, "ts": now}],
           "webhook_attempts": 0, "next_retry_at": 0.0, "acked": False, "error": ""}
    with _LOCK:
        _row_put(req)
    return dict(req)


def next_pending(limit: int | None = None) -> list:
    lim = limit or cfg()["poll_limit"]
    out = []
    with _LOCK:
        for r in _row_by_status(QUEUED):
            d = _update(r["id"], status=SENT_TO_LOCAL)
            if d:
                out.append(d)
            if len(out) >= lim:
                break
    return out


def mark_processing(rid: str) -> dict | None:
    return _update(rid, status=PROCESSING)


def submit_result(rid: str, result) -> dict:
    r = get(rid)
    if not r:
        return {"ok": False, "error": "no such request"}
    if r.get("status") in _TERMINAL:
        return {"ok": True, "already": True, "status": r["status"]}
    _update(rid, result=result, status=RESPONSE_RECEIVED, next_retry_at=0.0)
    return deliver_webhook(rid)


def _post(url: str, body: dict):
    try:
        data = json.dumps(body).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("content-type", "application/json")
        with urllib.request.urlopen(req, timeout=20) as resp:
            return (200 <= resp.status < 300), resp.status
    except urllib.error.HTTPError as e:
        return False, e.code
    except Exception:
        return False, 0


def deliver_webhook(rid: str) -> dict:
    r = get(rid)   # rehydrated result
    if not r or r.get("status") in _TERMINAL:
        return {"ok": True, "skip": True}
    if not r.get("webhook_url"):
        _update(rid, status=FINISHED)
        return {"ok": True, "no_webhook": True}
    attempts = int(r.get("webhook_attempts", 0)) + 1
    _update(rid, status=WEBHOOK_SENT, webhook_attempts=attempts)
    ok, code = _post(r["webhook_url"], {"request_id": rid, "project": r.get("project"),
                                        "status": "completed", "result": r.get("result"),
                                        "attempt": attempts})
    c = cfg()
    if ok:
        _update(rid, acked=True, status=ACKNOWLEDGED)
        _update(rid, status=FINISHED)
        return {"ok": True, "acked": True, "attempts": attempts}
    if attempts >= c["retry_count"]:
        _update(rid, status=FAILED, error=f"webhook not acknowledged after {attempts} attempts (last HTTP {code})")
        return {"ok": False, "failed": True, "attempts": attempts}
    _update(rid, status=ACK_PENDING, next_retry_at=time.time() + c["retry_interval_sec"],
            error=f"webhook attempt {attempts} not acked (HTTP {code})")
    return {"ok": False, "retry_scheduled": True, "attempts": attempts}


def ack(rid: str) -> dict:
    r = get(rid)
    if not r:
        return {"ok": False, "error": "no such request"}
    _update(rid, acked=True, status=ACKNOWLEDGED)
    _update(rid, status=FINISHED)
    return {"ok": True}


def retry_due() -> int:
    now = time.time()
    n = 0
    for r in _row_by_status(ACK_PENDING):
        if r.get("next_retry_at", 0) and now >= r["next_retry_at"]:
            deliver_webhook(r["id"])
            n += 1
    return n


# ---- queries / admin ----
def list_requests(status: str | None = None, limit: int = 200) -> list:
    rows = _row_by_status(status) if status else _row_all()
    rows = sorted(rows, key=lambda r: r.get("created", 0), reverse=True)[:limit]
    for r in rows:
        r["result"] = _rehydrate(r.get("result"))
    return rows


def counts() -> dict:
    return _row_counts()


def cancel(rid: str) -> dict | None:
    return _update(rid, status=CANCELLED)


def remove(rid: str) -> dict:
    with _LOCK:
        ok = _row_delete(rid)
        if ok:
            _remove_files(rid)
    return {"ok": ok, "deleted": rid} if ok else {"ok": False, "error": "no such request"}


def clear_all() -> dict:
    with _LOCK:
        n = _row_delete_all()
        try:
            import shutil
            if os.path.isdir(_RESP_ROOT):
                shutil.rmtree(_RESP_ROOT, ignore_errors=True)
        except Exception:
            pass
    return {"ok": True, "cleared": n}


# bring up Postgres if configured (safe — falls back to JSON)
_pg_init()
