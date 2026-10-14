#!/usr/bin/env python3
"""
e2e_anchor_http.py — Anchor Connect Phase-1 E2E over the REAL HTTP API (the interface contract).

Unlike e2e_anchor.py (which drives the queue functions in-process), this boots the ACTUAL FastAPI
app and calls the live /anchor/v1 endpoints through the real router — so it exercises the true
request/response shapes, JSON (de)serialization and X-API-Key auth that Phase 2 (Flutter) and real
third parties will use. The webhook leg is a real local HTTP receiver. Nothing is mocked away; this
IS the contract.

Run on a machine where fastapi is installed (your Mac):  python3 server/e2e_anchor_http.py
"""
from __future__ import annotations

import os
os.environ["ODIN_ANCHOR_NO_POLLER"] = "1"   # we drive poll/result manually for a deterministic test

import json
import time
import threading
import http.server
import socketserver
import uuid


class _Rec:
    received: list = []

    @classmethod
    def reset(cls):
        cls.received = []


class _H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("content-length", 0))
        _Rec.received.append(json.loads(self.rfile.read(n) or b"{}"))
        self.send_response(200); self.end_headers(); self.wfile.write(b'{"ack":true}')


def _receiver():
    httpd = socketserver.TCPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}/webhook"


def main() -> int:
    print("=" * 70); print("ANCHOR CONNECT — PHASE 1 E2E over REAL HTTP (/anchor/v1 contract)"); print("=" * 70)
    try:
        try:
            from fastapi.testclient import TestClient
        except Exception:
            from starlette.testclient import TestClient
        import app as appmod
        import projects, anchor_queue as q
        from integrations import cred
    except Exception as e:
        print(f"❌ Cannot import the app/TestClient here ({e}).")
        print("   Run this on the machine where fastapi is installed (your Mac).")
        return 2

    client = TestClient(appmod.app)
    httpd, hook = _receiver(); _Rec.reset()
    ok_all = True

    def check(name, cond):
        nonlocal ok_all
        ok_all = ok_all and bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")

    # throwaway target project so the /requests project check passes
    proj = projects.create_project(name=f"Anchor HTTP E2E {uuid.uuid4().hex[:4]}",
                                   description="anchor http contract test", ptype="web",
                                   members=[{"name": "Backend", "role": "Backend"}],
                                   local_path="/tmp/anchor_http_e2e", auto_approve=True)
    pid = proj["id"]
    created_reqs = []
    key = cred.get("ANCHOR_API_KEY", "")
    hdr = {"X-API-Key": key} if key else {}

    try:
        # auth: when a key is configured, an unauthenticated poll must be rejected
        if key:
            check("401 without X-API-Key", client.get("/anchor/v1/poll").status_code == 401)

        # 1) third party POSTs a request (real HTTP)
        rr = client.post("/anchor/v1/requests",
                         json={"project": pid, "prompt": "order status?", "webhook_url": hook}, headers=hdr)
        check("POST /requests -> 200", rr.status_code == 200)
        rid = rr.json().get("request_id", "")
        created_reqs.append(rid)
        check("returns request_id + queued", rid.startswith("req_") and rr.json().get("status") == "queued")

        # 2) local machine polls over HTTP
        pj = client.get("/anchor/v1/poll", headers=hdr).json()
        check("GET /poll returns the task", any(t["id"] == rid for t in pj.get("tasks", [])))

        # 3) local machine returns the result over HTTP -> webhook delivered + acked
        sr = client.post(f"/anchor/v1/requests/{rid}/result", json={"result": {"answer": "shipped"}}, headers=hdr)
        check("POST /result -> ok", sr.status_code == 200 and sr.json().get("ok"))
        time.sleep(0.2)

        # 4) status reflects finished + acked, with the result
        st = client.get(f"/anchor/v1/requests/{rid}").json()
        check("status FINISHED + acked", st.get("status") == "finished" and st.get("acked") is True)
        check("third party received result over real webhook",
              _Rec.received and _Rec.received[0]["request_id"] == rid
              and _Rec.received[0]["result"]["answer"] == "shipped")

        # 5) finished task is never re-polled
        pj2 = client.get("/anchor/v1/poll", headers=hdr).json()
        check("finished task not re-polled", all(t["id"] != rid for t in pj2.get("tasks", [])))

        # 6) admin endpoints
        check("admin/counts works", "counts" in client.get("/anchor/v1/admin/counts").json())
        check("admin/config works", "retry_count" in client.get("/anchor/v1/admin/config").json())
    finally:
        try:
            rows = [x for x in q._all() if x["id"] not in created_reqs]
            q._save(rows)
        except Exception:
            pass
        try:
            projects.delete_project(pid)
        except Exception:
            pass
        httpd.shutdown()

    print("\n" + "-" * 70)
    print("  ✅ ANCHOR HTTP CONTRACT E2E PASSED — real /anchor/v1 endpoints + auth + webhook"
          if ok_all else "  ❌ FAILED — see [FAIL] lines")
    print("-" * 70)
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
