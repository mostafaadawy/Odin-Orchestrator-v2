#!/usr/bin/env python3
"""
sim_server.py — serves the 3rd-party REQUEST PAGE (anchor_sim.html) AND gives it a DURABLE, SQLite-backed
record of the requests it fires. This is the request page's OWN store (the third party's log) — SEPARATE from
the anchor. For local testing only.

Why SQLite + files: each request is one small row (id, project, prompt, webhook, status, timestamps). The
RESPONSE (which can be large — long text or images) is written to a FILE under data/sim_responses/<id>.json,
and the row only keeps a POINTER (response_path). So the database never grows huge, and a response can be
re-fetched at any time by id. The page reads this on load, so a refresh or a full browser close never loses
the requests or their statuses.

Endpoints (same-origin from the page):
  GET    /sim/requests            → list the recorded requests (newest first)
  POST   /sim/requests            → record a new request {rid,project,prompt,webhook,status}
  PUT    /sim/requests/<rid>      → update {status?, response?}  (response is saved to a file)
  DELETE /sim/requests/<rid>      → delete the row + its response file
  GET    /sim/response/<rid>      → the saved response for a request
Everything else is served as a static file from the repo root (anchor_sim.html, anchor_seed.js, …).
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repo root
# The sim's own store lives with the anchor layer (it's the third-party side of the anchor CD-flow).
DATA = os.environ.get("ODIN_SIM_DATA", os.path.join(ROOT, "workspace", "anchor-layer"))
os.makedirs(DATA, exist_ok=True)
DB = os.path.join(DATA, "sim_requests.db")
RESP_DIR = os.path.join(DATA, "sim_responses")
LOCK = threading.RLock()


def _conn() -> sqlite3.Connection:
    os.makedirs(DATA, exist_ok=True)
    c = sqlite3.connect(DB, timeout=15)
    c.row_factory = sqlite3.Row
    return c


def _init() -> None:
    with LOCK:
        c = _conn()
        try:
            # NOTE: no WAL — the default rollback journal works on ALL filesystems (WAL's shared-memory
            # files fail on some network/fuse/synced mounts with "disk I/O error").
            # rid = the CARD id (one per Send press, generated locally so OFFLINE sends still show a card).
            # anchor_id = the anchor's request_id once accepted (used to poll status/result). May be empty.
            c.execute("""CREATE TABLE IF NOT EXISTS reqs(
                rid TEXT PRIMARY KEY, project TEXT, prompt TEXT, webhook TEXT,
                status TEXT, anchor_id TEXT, response_path TEXT, created REAL, updated REAL)""")
            try:
                c.execute("ALTER TABLE reqs ADD COLUMN anchor_id TEXT")  # migrate older DBs
            except Exception:
                pass
            c.commit()
        finally:
            c.close()


_init()


def _resp_path(rid: str) -> str:
    os.makedirs(RESP_DIR, exist_ok=True)
    return os.path.join(RESP_DIR, rid + ".json")


def _row(r) -> dict:
    return {"rid": r["rid"], "project": r["project"], "prompt": r["prompt"], "webhook": r["webhook"],
            "status": r["status"], "anchor_id": (r["anchor_id"] if "anchor_id" in r.keys() else "") or "",
            "created": r["created"], "updated": r["updated"], "has_response": bool(r["response_path"])}


def list_reqs() -> list:
    c = _conn()
    try:
        rows = c.execute("SELECT * FROM reqs ORDER BY created DESC LIMIT 200").fetchall()
    finally:
        c.close()
    return [_row(r) for r in rows]


def get_response(rid: str):
    c = _conn()
    try:
        row = c.execute("SELECT response_path FROM reqs WHERE rid=?", (rid,)).fetchone()
    finally:
        c.close()
    if row and row["response_path"] and os.path.exists(row["response_path"]):
        try:
            with open(row["response_path"], "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None


def upsert(rid: str, project=None, prompt=None, webhook=None, status=None, response=None, anchor_id=None) -> None:
    with LOCK:
        c = _conn()
        try:
            row = c.execute("SELECT * FROM reqs WHERE rid=?", (rid,)).fetchone()
            now = time.time()
            rp = row["response_path"] if row else None
            if response is not None:                 # big/any response → its own FILE (pointer in the row)
                rp = _resp_path(rid)
                with open(rp, "w", encoding="utf-8") as f:
                    json.dump(response, f)
            if row:
                cur_aid = row["anchor_id"] if "anchor_id" in row.keys() else ""
                c.execute("UPDATE reqs SET project=?,prompt=?,webhook=?,status=?,anchor_id=?,response_path=?,updated=? WHERE rid=?",
                          (project if project is not None else row["project"],
                           prompt if prompt is not None else row["prompt"],
                           webhook if webhook is not None else row["webhook"],
                           status if status is not None else row["status"],
                           anchor_id if anchor_id is not None else cur_aid,
                           rp, now, rid))
            else:
                c.execute("INSERT INTO reqs(rid,project,prompt,webhook,status,anchor_id,response_path,created,updated) "
                          "VALUES(?,?,?,?,?,?,?,?,?)",
                          (rid, project or "", prompt or "", webhook or "", status or "queued",
                           anchor_id or "", rp, now, now))
            c.commit()
        finally:
            c.close()


def delete(rid: str) -> None:
    with LOCK:
        c = _conn()
        try:
            row = c.execute("SELECT response_path FROM reqs WHERE rid=?", (rid,)).fetchone()
            if row and row["response_path"]:
                try:
                    os.remove(row["response_path"])
                except Exception:
                    pass
            c.execute("DELETE FROM reqs WHERE rid=?", (rid,))
            c.commit()
        finally:
            c.close()


def clear_all() -> int:
    """Wipe the whole request-page log — every row AND every saved response file."""
    with LOCK:
        c = _conn()
        try:
            rows = c.execute("SELECT response_path FROM reqs").fetchall()
            for r in rows:
                if r["response_path"]:
                    try:
                        os.remove(r["response_path"])
                    except Exception:
                        pass
            n = c.execute("SELECT COUNT(*) n FROM reqs").fetchone()["n"]
            c.execute("DELETE FROM reqs")
            c.commit()
        finally:
            c.close()
    return n


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,DELETE,OPTIONS")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(b)

    def _reqbody(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode() or "{}")
        except Exception:
            return {}

    def do_OPTIONS(self):
        self._json(200, {"ok": True})

    def do_GET(self):
        p = urlparse(self.path).path
        if p == "/sim/requests":
            return self._json(200, {"requests": list_reqs()})
        if p.startswith("/sim/response/"):
            return self._json(200, {"response": get_response(p.rsplit("/", 1)[-1])})
        return self._static(p)

    def do_POST(self):
        if urlparse(self.path).path == "/sim/requests":
            b = self._reqbody()
            rid = b.get("rid")
            if not rid:
                return self._json(400, {"error": "rid required"})
            upsert(rid, b.get("project"), b.get("prompt"), b.get("webhook"), b.get("status") or "queued",
                   anchor_id=b.get("anchor_id"))
            return self._json(200, {"ok": True})
        return self._json(404, {"error": "not found"})

    def do_PUT(self):
        p = urlparse(self.path).path
        if p.startswith("/sim/requests/"):
            rid = p.rsplit("/", 1)[-1]
            b = self._reqbody()
            upsert(rid, status=b.get("status"), response=b.get("response"), anchor_id=b.get("anchor_id"))
            return self._json(200, {"ok": True})
        return self._json(404, {"error": "not found"})

    def do_DELETE(self):
        p = urlparse(self.path).path
        if p == "/sim/requests":                       # DELETE the whole log (Clear all)
            return self._json(200, {"ok": True, "cleared": clear_all()})
        if p.startswith("/sim/requests/"):
            delete(p.rsplit("/", 1)[-1])
            return self._json(200, {"ok": True})
        return self._json(404, {"error": "not found"})

    def _static(self, p):
        if p == "/":
            p = "/anchor_sim.html"
        rel = p.lstrip("/")
        fp = os.path.normpath(os.path.join(DATA, rel))
        # SELF-HEALING seed resolution: the page (served from DATA=anchor-layer) loads anchor_seed.js /
        # anchor_prod.js, but the launch scripts historically write them to the REPO ROOT — a path
        # mismatch that 404'd the seed, left the X-API-Key empty, and made the anchor return no projects.
        # If a requested file isn't in DATA, fall back to the repo root so the seed loads no matter where
        # it's written. Both roots are trusted local dirs; still guard against path traversal.
        if not (fp.startswith(DATA) and os.path.isfile(fp)):
            alt = os.path.normpath(os.path.join(ROOT, rel))
            if alt.startswith(ROOT) and os.path.isfile(alt):
                fp = alt
            else:
                return self._json(404, {"error": "not found"})
        ext = fp.rsplit(".", 1)[-1].lower()
        ctype = {"html": "text/html", "js": "application/javascript", "json": "application/json",
                 "css": "text/css", "svg": "image/svg+xml"}.get(ext, "text/plain")
        with open(fp, "rb") as f:
            b = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(b)


def serve(host: str, port: int):
    print(f"[sim-server] request simulator + SQLite log → http://{host}:{port}  (db={DB})")
    ThreadingHTTPServer((host, port), H).serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=9104)
    a = ap.parse_args()
    serve(a.host, a.port)
