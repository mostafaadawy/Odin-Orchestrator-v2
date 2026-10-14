#!/usr/bin/env python3
"""
e2e_anchor.py — Anchor Connect Phase-1 E2E. BOTH a test AND the integration contract.

It stands up a REAL local HTTP server acting as the third party's webhook receiver, then drives the
full lifecycle through the SAME queue functions the anchor HTTP API wraps:

  third party enqueues → local machine polls → processes → returns result →
  anchor delivers webhook → third party ACKs (HTTP 2xx) → FINISHED.

Also tests: retry when the webhook is flaky, FAILED after exhausted retries, and that a finished
task is never handed to the local machine again. No external services, no engine needed — runnable
anywhere:  python3 server/e2e_anchor.py
"""
from __future__ import annotations

import json
import time
import threading
import http.server
import socketserver

import anchor_queue as q


# ---- fake THIRD PARTY: a real webhook receiver (records payloads; can be made flaky) ----
class _Receiver:
    received: list = []
    fail_first = 0          # return 500 this many times before 200 (to exercise retry)
    _hits = 0

    @classmethod
    def reset(cls, fail_first=0):
        cls.received = []; cls.fail_first = fail_first; cls._hits = 0


class _Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a):  # silence
        pass

    def do_POST(self):
        n = int(self.headers.get("content-length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        _Receiver._hits += 1
        if _Receiver._hits <= _Receiver.fail_first:
            self.send_response(500); self.end_headers(); self.wfile.write(b"flaky")
            return
        _Receiver.received.append(body)            # ACK = a 2xx response
        self.send_response(200); self.end_headers(); self.wfile.write(b'{"ack":true}')


def _start_receiver():
    httpd = socketserver.TCPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}/webhook"


CK = lambda name, ok: print(f"  [{'PASS' if ok else 'FAIL'}] {name}")


def main() -> int:
    print("=" * 70); print("ANCHOR CONNECT — PHASE 1 E2E (test + interface contract)"); print("=" * 70)
    httpd, hook = _start_receiver()
    created = []
    ok_all = True

    def check(name, cond):
        nonlocal ok_all
        ok_all = ok_all and bool(cond); CK(name, cond)

    # ---------- 1) HAPPY PATH ----------
    print("\n[1] Happy path: enqueue → poll → process → result → webhook → ack → finished")
    _Receiver.reset()
    req = q.enqueue("organics", {"prompt": "what is the order status?"}, sender="shipping-app", webhook_url=hook)
    created.append(req["id"])
    check("enqueue returns a unique id + queued", req["id"].startswith("req_") and req["status"] == q.QUEUED)

    pend = q.next_pending()
    check("local poll receives the task", any(t["id"] == req["id"] for t in pend))
    check("task flipped to sent_to_local", q.get(req["id"])["status"] == q.SENT_TO_LOCAL)

    q.mark_processing(req["id"])
    res = q.submit_result(req["id"], {"answer": "order #123 is shipped"})
    check("submit_result ok", res.get("ok"))
    time.sleep(0.2)
    final = q.get(req["id"])
    check("status FINISHED", final["status"] == q.FINISHED)
    check("acknowledged flag set", final["acked"] is True)
    check("third party received the webhook with the result",
          _Receiver.received and _Receiver.received[0]["request_id"] == req["id"]
          and _Receiver.received[0]["result"]["answer"] == "order #123 is shipped")

    # ---------- 2) NO DOUBLE-PROCESSING ----------
    print("\n[2] A finished task is never handed to the local machine again")
    again = q.next_pending()
    check("finished task NOT re-polled", all(t["id"] != req["id"] for t in again))
    res2 = q.submit_result(req["id"], {"answer": "dup"})
    check("re-submit is idempotent (already)", res2.get("already") is True)

    # ---------- 3) RETRY then succeed ----------
    print("\n[3] Webhook flaky (fails twice) → retry → ack → finished")
    _Receiver.reset(fail_first=2)
    q.set_cfg(retry_count=5, retry_interval_sec=0)   # interval 0 so retry is due immediately
    r2 = q.enqueue("organics", {"prompt": "x"}, webhook_url=hook); created.append(r2["id"])
    q.next_pending(); q.mark_processing(r2["id"])
    q.submit_result(r2["id"], {"answer": "ok"})       # attempt 1 → 500
    check("after 1st failure → ack_pending", q.get(r2["id"])["status"] == q.ACK_PENDING)
    q.retry_due()                                     # attempt 2 → 500 → still pending
    q.retry_due()                                     # attempt 3 → 200 → finished
    fr = q.get(r2["id"])
    check("eventually FINISHED after retries", fr["status"] == q.FINISHED and fr["acked"])
    check("took 3 webhook attempts", fr["webhook_attempts"] == 3)

    # ---------- 4) FAIL after exhausted retries ----------
    print("\n[4] Webhook always fails → FAILED after retry_count (record kept, not deleted)")
    _Receiver.reset(fail_first=999)
    q.set_cfg(retry_count=3, retry_interval_sec=0)
    r3 = q.enqueue("organics", {"prompt": "y"}, webhook_url=hook); created.append(r3["id"])
    q.next_pending(); q.mark_processing(r3["id"])
    q.submit_result(r3["id"], {"answer": "ok"})       # attempt 1
    q.retry_due()                                     # attempt 2
    q.retry_due()                                     # attempt 3 → FAILED
    f3 = q.get(r3["id"])
    check("status FAILED after exhausting retries", f3["status"] == q.FAILED)
    check("record kept with the result (not deleted)", f3.get("result") is not None)

    # ---------- 5) admin config + counts ----------
    print("\n[5] Admin config + status counts")
    q.set_cfg(retry_count=4, retry_interval_sec=600)
    check("config persists", q.cfg()["retry_count"] == 4 and q.cfg()["retry_interval_sec"] == 600)
    check("counts include finished + failed", q.counts().get(q.FINISHED, 0) >= 1 and q.counts().get(q.FAILED, 0) >= 1)

    # ---------- cleanup test rows ----------
    try:
        rows = [x for x in q._all() if x["id"] not in created]
        q._save(rows)
    except Exception:
        pass
    httpd.shutdown()

    print("\n" + "-" * 70)
    print("  ✅ ANCHOR PHASE-1 E2E PASSED — full lifecycle + retry + fail + no-double-processing"
          if ok_all else "  ❌ ANCHOR PHASE-1 E2E FAILED — see [FAIL] lines above")
    print("-" * 70)
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
