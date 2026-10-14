#!/usr/bin/env python3
"""
e2e_anchor_live.py — Anchor Connect with REAL projects + REAL read-only data (no fakes for what we
already have).

Principle (owner's rule): we do NOT fake the parts we own. Real projects are created, the local
machine really processes the request, and it really queries the LIVE Klaviyo / Veeqo APIs — READ
ONLY (GET; it cannot create or modify anything in your accounts). Only the not-yet-built pieces are
simulated: the external third party and its webhook receiver (Phase 2 web + Phase 3 deployed anchor).

Scenario:
  • Project A = Email (Klaviyo). External request: "How many workflows do we have — live vs draft?"
  • Project B = Fulfillment (Veeqo). External request: "How many orders did we get this week?"
Each goes through the full anchor lifecycle with real processing + real timing, then the result is
delivered to the simulated third party and acknowledged.

Run where the keys + network work (your Mac):  python3 server/e2e_anchor_live.py
"""
from __future__ import annotations

import os
os.environ["ODIN_ANCHOR_NO_POLLER"] = "1"   # drive poll/process/result manually for determinism

import json
import time
import threading
import http.server
import socketserver
import uuid

import anchor_queue as q
import anchor


class _Rec:
    received: list = []


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
    print("=" * 72); print("ANCHOR CONNECT — LIVE E2E (real projects, real READ-ONLY Klaviyo/Veeqo data)"); print("=" * 72)
    import projects
    from integrations import klaviyo as kl, veeqo as vq

    httpd, hook = _receiver()
    _Rec.received = []
    ok_all = True
    created_pids, created_reqs = [], []

    def check(name, cond, extra=""):
        nonlocal ok_all
        ok_all = ok_all and bool(cond)
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}" + (f"  → {extra}" if extra else ""))

    print(f"\n  Klaviyo configured: {kl.configured()} | Veeqo configured: {vq.configured()}")

    # --- CONSOLIDATION: confirm the already-implemented features are wired (no network needed) ---
    tkeys = [t["key"] for t in projects.project_types()]
    roles = {r["name"] for r in projects.roles_readiness()}
    check("feature: Email project type exists", "email" in tkeys)
    check("feature: Fulfillment Provider project type exists", "fulfillment" in tkeys)
    check("feature: Email role exists (Klaviyo dependency)", "Email" in roles)
    check("feature: Shipping role exists (Veeqo dependency)", "Shipping" in roles)
    check("feature: Klaviyo client configured (key in .cred)", kl.configured())
    check("feature: Veeqo client configured (key in .cred)", vq.configured())

    # --- REAL projects (we own this power; not faked) ---
    pe = projects.create_project(name=f"Email Klaviyo {uuid.uuid4().hex[:4]}", description="email project on klaviyo",
                                 ptype="email", members=[{"name": "Email", "role": "Email", "nature": "operational"}],
                                 local_path="", auto_approve=True)
    pf = projects.create_project(name=f"Shipping Veeqo {uuid.uuid4().hex[:4]}", description="fulfillment project on veeqo",
                                 ptype="fulfillment", members=[{"name": "Shipping", "role": "Shipping", "nature": "operational"}],
                                 local_path="", auto_approve=True)
    created_pids += [pe["id"], pf["id"]]
    check("two real projects created (Email/Klaviyo + Shipping/Veeqo)", pe["type"] == "email" and pf["type"] == "fulfillment")

    # ---- STEP 1 — CREATION confirms CONNECTION ONLY (no request work here) ----
    # Per the model: creating a project just sets it up and confirms the connector is reachable
    # (read-only). The actual question is asked later, as a separate incoming request.
    from integrations import klaviyo as _kl, veeqo as _vq
    import datetime as _dt
    kc = _kl.flows_summary() if _kl.configured() else {"ok": False, "error": "klaviyo not configured"}
    _since = (_dt.datetime.utcnow() - _dt.timedelta(days=7)).strftime("%Y-%m-%dT00:00:00Z")
    vc = _vq.orders_summary(_since) if _vq.configured() else {"ok": False, "error": "veeqo not configured"}
    print(f"\n  [CREATION] Email project → Klaviyo connection: {json.dumps(kc)[:200]}")
    print(f"  [CREATION] Shipping project → Veeqo connection: {json.dumps(vc)[:200]}")
    check("CREATION: Email project confirms Klaviyo connection (read-only ping)", kc.get("ok") is True)
    check("CREATION: Shipping project confirms Veeqo connection (read-only ping)", vc.get("ok") is True)

    def run_one(label, pid, prompt):
        # ---- STEP 2 — an INCOMING REQUEST: CTO is asked → assigns the agent → agent works → returns ----
        req = q.enqueue(pid, {"prompt": prompt}, sender="external-app", webhook_url=hook)
        created_reqs.append(req["id"])
        pulled = q.next_pending()
        got = any(t["id"] == req["id"] for t in pulled)
        q.mark_processing(req["id"])
        t0 = time.time()
        out = anchor.process(q.get(req["id"]))       # REAL CTO→team orchestration, grounded in REAL read-only data
        took = round(time.time() - t0, 2)
        q.submit_result(req["id"], out.get("answer"))
        time.sleep(0.2)
        fr = q.get(req["id"])
        delivered = bool(_Rec.received and _Rec.received[-1]["request_id"] == req["id"])
        facts = out.get("facts") or {}
        # evidence the REAL orchestration ran: the run's shared pool shows the CTO planned and an agent worked
        import main_task as _mt
        pool = (_mt.get(pid) or {}).get("pool") or []
        whos = " | ".join(e.get("who", "") for e in pool)
        cto_planned = any(("plan" in e.get("who", "").lower()) or ("cto" in e.get("who", "").lower()) for e in pool)
        agent_worked = len([e for e in pool if e.get("text")]) >= 2
        print(f"\n  [{label}] incoming request: {prompt}")
        print(f"          EXACT DATA fetched (verify against what you know): {json.dumps(facts)[:300]}")
        print(f"          routed via: {out.get('via')}  ·  run participants: {whos[:160]}")
        print(f"          orchestration ran for {out.get('secs')}s (wall {took}s)")
        print(f"          AI answer: {str(out.get('answer'))[:200]}")
        check(f"{label}: polled + processed + finished + webhook acked",
              got and fr["status"] == q.FINISHED and fr["acked"] and delivered)
        check(f"{label}: handled by the REAL CTO→team orchestration (not a shortcut)",
              out.get("via") == "orchestration")
        check(f"{label}: CTO planned AND an agent produced work in the run",
              cto_planned and agent_worked)
        check(f"{label}: real AI processing took real time (not instant/fake)", took > 1.0)
        return out

    out_e = run_one("Klaviyo", pe["id"], "How many workflows (flows) do we have, and how many are live vs draft?")
    out_f = run_one("Veeqo", pf["id"], "How many orders did we get this week?")

    # --- TRULY CONNECTED proof: the connector read must have succeeded with REAL numbers. If the
    #     numbers don't match what you know, it's not truly connected. A non-answer FAILS here. ---
    fe = (out_e.get("facts") or {}).get("flows") or {}
    ff = (out_f.get("facts") or {}).get("orders") or {}
    check("Klaviyo TRULY connected — real flow counts returned", fe.get("ok") is True,
          f"total={fe.get('total')} by_status={fe.get('by_status')}")
    check("Veeqo TRULY connected — real order count returned", ff.get("ok") is True,
          f"orders_this_week={ff.get('count')}")
    print("\n  >>> NUMBERS TO VERIFY AGAINST WHAT YOU KNOW:")
    print(f"      Klaviyo flows: total={fe.get('total')}  by_status={fe.get('by_status')}")
    print(f"      Veeqo orders this week: {ff.get('count')}")

    # --- the web/desktop would read exactly this on click (on-demand) ---
    rows = q.list_requests()
    mine = [r for r in rows if r["id"] in created_reqs]
    check("both requests visible to the status page (admin/requests feed)", len(mine) == 2)

    # cleanup (read-only run; remove our test projects + requests)
    try:
        rows = [x for x in q._all() if x["id"] not in created_reqs]; q._save(rows)
        for pid in created_pids:
            projects.delete_project(pid)
    except Exception:
        pass
    httpd.shutdown()

    print("\n" + "-" * 72)
    if ok_all:
        print("  ✅ LIVE E2E PASSED — real projects answered real external requests using real")
        print("     READ-ONLY Klaviyo/Veeqo data, through the full queue→process→webhook→ack lifecycle.")
    else:
        print("  ❌ LIVE E2E had failures — see [FAIL] lines (a real API/auth/network error shows here honestly).")
    print("-" * 72)
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
