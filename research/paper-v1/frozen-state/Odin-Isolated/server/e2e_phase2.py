#!/usr/bin/env python3
"""
e2e_phase2.py — Phase 2/3 TOPOLOGY E2E (app ⇄ REMOTE anchor ⇄ local machine), over real HTTP.

This proves the exact shape Phase 3 will run in, with the ONLY simulated piece being the
anchor's *location* (a local stand-in process instead of the Azure VM). Everything else is
real and crosses a real HTTP boundary:

  [the app / third party]  --HTTP-->  [REMOTE anchor (anchor_remote)]  <--HTTP--  [local machine]
        sends a request                 owns the queue + webhooks            polls, runs the REAL
        receives the webhook                                                 CTO→team orchestration

Modes:
  (default)  REAL: the local side runs anchor.process() — real CTO→team orchestration grounded in
             real READ-ONLY Klaviyo/Veeqo data. Slow (minutes) and prints the exact numbers.
  --smoke    TRANSPORT ONLY: replaces the processor with a labeled echo to validate the
             HTTP/queue/webhook plumbing fast. Clearly NOT an AI test.

Run:
    python3 server/e2e_phase2.py            # real (run on your Mac)
    python3 server/e2e_phase2.py --smoke    # fast plumbing check (runs anywhere)
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
import threading
import time
import urllib.request
import urllib.error
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import anchor
import anchor_remote
import anchor_queue as q
import projects

ok_all = True


def check(name, cond, extra=""):
    global ok_all
    ok_all = ok_all and bool(cond)
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  → {extra}" if extra else ""))


def free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


# ---- the third party / app webhook receiver ----
class _Hook(BaseHTTPRequestHandler):
    received: list = []

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = json.loads(self.rfile.read(n).decode() or "{}") if n else {}
        _Hook.received.append(body)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"ok":true}')

    def log_message(self, *a):
        pass


def _call(base, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(base + path, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    try:
        from integrations import cred
        k = cred.get("ANCHOR_API_KEY", "")
        if k:
            r.add_header("X-API-Key", k)
    except Exception:
        pass
    with urllib.request.urlopen(r, timeout=120) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="transport-only (no real AI)")
    args = ap.parse_args()

    print("=" * 72)
    print(f"ANCHOR CONNECT — PHASE 2/3 TOPOLOGY E2E over REAL HTTP  ({'SMOKE/transport' if args.smoke else 'REAL orchestration'})")
    print("=" * 72)

    aport, hport = free_port(), free_port()
    base = f"http://127.0.0.1:{aport}"
    hook = f"http://127.0.0.1:{hport}/cb"

    # remote anchor (the deployed-anchor stand-in) + the app's webhook receiver
    anchor_remote._retry_sweep(interval=2.0)
    remote = ThreadingHTTPServer(("127.0.0.1", aport), anchor_remote.Handler)
    threading.Thread(target=remote.serve_forever, daemon=True).start()
    hooksrv = ThreadingHTTPServer(("127.0.0.1", hport), _Hook)
    threading.Thread(target=hooksrv.serve_forever, daemon=True).start()
    time.sleep(0.3)
    check("remote anchor reachable over HTTP (_status)", _call(base, "GET", "/anchor/v1/_status").get("ok") is True)

    created_pids, created_reqs = [], []
    pe = projects.create_project(name=f"Email Klaviyo {uuid.uuid4().hex[:4]}", description="email project on klaviyo",
                                 ptype="email", members=[{"name": "Email", "role": "Email", "nature": "operational"}],
                                 local_path="", auto_approve=True)
    pf = projects.create_project(name=f"Shipping Veeqo {uuid.uuid4().hex[:4]}", description="fulfillment project on veeqo",
                                 ptype="fulfillment", members=[{"name": "Shipping", "role": "Shipping", "nature": "operational"}],
                                 local_path="", auto_approve=True)
    created_pids += [pe["id"], pf["id"]]
    check("two real projects created (Email/Klaviyo + Shipping/Veeqo)", pe["type"] == "email" and pf["type"] == "fulfillment")

    # the processor the LOCAL side runs on each polled task
    def processor(task):
        if args.smoke:
            return {"answer": f"TRANSPORT SMOKE echo (NOT AI): {task.get('payload', {}).get('prompt', '')}",
                    "via": "smoke", "secs": 0.0, "facts": {}}
        return anchor.process(task)  # REAL CTO→team orchestration + real read-only data

    def run_one(label, pid, prompt):
        # 1) the APP submits a request to the REMOTE anchor over HTTP, with its webhook
        created = _call(base, "POST", "/anchor/v1/requests",
                        {"project": pid, "prompt": prompt, "webhook_url": hook, "sender": "odin_app"})
        rid = created.get("request_id")
        created_reqs.append(rid)
        check(f"{label}: app POST /requests over HTTP → request_id + queued",
              bool(rid) and created.get("status") == "queued", f"id={rid}")

        # 2) the LOCAL machine polls the REMOTE anchor over HTTP, processes, posts result over HTTP
        before = len(_Hook.received)
        tasks = _call(base, "GET", "/anchor/v1/poll").get("tasks", [])
        mine = [t for t in tasks if t["id"] == rid]
        check(f"{label}: local machine polled the task over HTTP", len(mine) == 1)
        out = processor(mine[0]) if mine else {"answer": "(not polled)", "facts": {}, "via": "none"}
        _call(base, "POST", f"/anchor/v1/requests/{rid}/result", {"result": out.get("answer")})

        # 3) wait for the remote to deliver the webhook + reach finished
        deadline = time.time() + 30
        fr = {}
        while time.time() < deadline:
            fr = _call(base, "GET", f"/anchor/v1/requests/{rid}")
            if fr.get("status") in ("finished", "failed", "cancelled"):
                break
            time.sleep(0.5)
        delivered = any(r.get("request_id") == rid for r in _Hook.received[before:])
        facts = out.get("facts") or {}
        print(f"\n  [{label}] prompt: {prompt}")
        print(f"          routed via: {out.get('via')}  ·  secs: {out.get('secs')}")
        if not args.smoke:
            print(f"          EXACT DATA (verify against what you know): {json.dumps(facts)[:300]}")
            print(f"          AI answer: {str(out.get('answer'))[:200]}")
        check(f"{label}: finished + acked through the REMOTE anchor", fr.get("status") == "finished" and fr.get("acked"))
        check(f"{label}: app webhook received the result over HTTP", delivered)
        if not args.smoke:
            check(f"{label}: handled by the REAL CTO→team orchestration", out.get("via") == "orchestration")
        return out, facts

    out_e, fe_all = run_one("Klaviyo", pe["id"], "How many flows are live vs draft?")
    out_f, ff_all = run_one("Veeqo", pf["id"], "How many orders did we get this week?")

    if not args.smoke:
        fe = (fe_all.get("flows") or {})
        ff = (ff_all.get("orders") or {})
        check("Klaviyo TRULY connected — real flow counts returned", fe.get("ok") is True,
              f"total={fe.get('total')} by_status={fe.get('by_status')}")
        check("Veeqo TRULY connected — real order count returned", ff.get("ok") is True,
              f"orders_this_week={ff.get('count')}")
        print("\n  >>> NUMBERS TO VERIFY AGAINST WHAT YOU KNOW:")
        print(f"      Klaviyo flows: total={fe.get('total')}  by_status={fe.get('by_status')}")
        print(f"      Veeqo orders this week: {ff.get('count')}")

    # the app's status page reads this over HTTP
    feed = _call(base, "GET", "/anchor/v1/admin/requests").get("requests", [])
    counts = _call(base, "GET", "/anchor/v1/admin/counts").get("counts", {})
    check("app status page: both requests visible via remote admin/requests",
          len([r for r in feed if r["id"] in created_reqs]) == 2, f"counts={counts}")

    # cleanup
    try:
        rows = [x for x in q._all() if x["id"] not in created_reqs]
        q._save(rows)
        for pid in created_pids:
            projects.delete_project(pid)
    except Exception:
        pass
    remote.shutdown()
    hooksrv.shutdown()

    print("\n" + "-" * 72)
    print(("  ✅ PHASE 2/3 TOPOLOGY E2E PASSED" if ok_all else "  ❌ PHASE 2/3 TOPOLOGY E2E had failures")
          + (" (transport/plumbing only)" if args.smoke else " — real remote round-trip with real data"))
    print("-" * 72)
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
