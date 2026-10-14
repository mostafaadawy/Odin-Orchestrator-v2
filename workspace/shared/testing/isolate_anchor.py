"""
isolate_anchor.py — ONE NODE, PROVEN 100%. We do NOT redeploy and we do NOT move on until every single
transmission TO and FROM the anchor is verified, timing included. This runs on the Mac (external, over public
HTTPS) so it mimics EXACTLY what the web/mobile app does — same URLs, same headers, same order.

It answers, with evidence, the three doubts:
  (1) Is the anchor reachable and does its DATA come back correctly (forward read)?         → T1..T3
  (2) What EXACTLY causes the app's "HTTP 404 error page"? (a 404 has ONE meaning: wrong link) → T4
  (3) Is the async queue real: FAST ACK now ("received/queued"), then the local machine pulls,
      processes, and the RESULT returns later (webhook + acknowledgement) — never a synchronous 502? → T5

Every transmission prints: the exact request, the exact response (status + head of body + key headers),
the elapsed time, and a hard PASS/PROBLEM verdict. A final VERDICT block says whether the ANCHOR NODE is
100% or names the first transmission that failed.
"""
from __future__ import annotations
import json, ssl, time, pathlib, urllib.request, urllib.error

DOMAIN = "anchor.odinmarkets.com"
BASE = f"https://{DOMAIN}/odin-anchor"          # the CORRECT public path (nginx → 127.0.0.1:48619)
ORIGIN = f"https://{DOMAIN}"
PROJECT = "fulfillment-vq-status-read-only-dc1e"  # a real seeded project (read-only Veeqo)
PROMPT = "status check: how many orders this week"

_CTX = ssl.create_default_context()
_results = []  # (label, ok, detail)


def _key() -> str:
    for p in (pathlib.Path(__file__).resolve().parent.parent / "oth" / ".cred",):
        try:
            for ln in p.read_text().splitlines():
                if "ANCHOR_API_KEY" in ln and "=" in ln:
                    return ln.split("=", 1)[1].strip().strip('"')
        except Exception:
            pass
    return ""


def _req(method, url, headers=None, body=None, timeout=30):
    """Return (status:int|str, body:str, headers:dict, elapsed:float). Never raises."""
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method, headers=headers or {})
    t0 = time.time()
    try:
        with urllib.request.urlopen(r, timeout=timeout, context=_CTX) as resp:
            return resp.status, resp.read().decode(errors="ignore"), dict(resp.headers), time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="ignore"), dict(e.headers or {}), time.time() - t0
    except Exception as e:
        return "ERR", str(e), {}, time.time() - t0


def _verdict(label, ok, detail=""):
    _results.append((label, ok, detail))
    print(f"   {'✅ PASS' if ok else '❌ PROBLEM'} — {label}" + (f"  ·  {detail}" if detail else ""))


def _kind(body: str) -> str:
    b = body.lstrip()[:1]
    if b == "{" or b == "[":
        return "JSON"
    if body.lstrip()[:1] == "<" or "<!doctype" in body[:120].lower() or "<html" in body[:200].lower():
        return "HTML"
    return "text"


def main():
    key = _key()
    H = {"X-API-Key": key, "Origin": ORIGIN}
    print("=" * 78)
    print("ISOLATION — NODE: ANCHOR (outside caller ⇄ anchor ⇄ desktop). We do not leave this node")
    print(f"until 100% proven. base = {BASE}   project = {PROJECT}")
    print("=" * 78)

    # ---- T1: connectivity (the app's health() in production) ----
    print("\n[T1] REACH THE ANCHOR — GET /odin-anchor/health   (mimics app health())")
    s, b, _, dt = _req("GET", f"{BASE}/health")
    print(f"     → HTTP {s}  {_kind(b)}  {dt*1000:.0f}ms  body: {b[:110]}")
    ok1 = (s == 200 and _kind(b) == "JSON" and '"odin-anchor"' in b)
    _verdict("anchor is reachable and answers JSON health", ok1, f"{dt*1000:.0f}ms")

    # ---- T2: CORS preflight — can a BROWSER call the read endpoint? ----
    print("\n[T2] BROWSER PREFLIGHT — OPTIONS /odin-anchor/anchor/v1/projects  (Origin + x-api-key)")
    s, b, hd, dt = _req("OPTIONS", f"{BASE}/anchor/v1/projects",
                        headers={"Origin": ORIGIN, "Access-Control-Request-Method": "GET",
                                 "Access-Control-Request-Headers": "x-api-key"})
    acao = hd.get("Access-Control-Allow-Origin", "")
    ach = hd.get("Access-Control-Allow-Headers", "")
    print(f"     → HTTP {s}  Allow-Origin='{acao}'  Allow-Headers='{ach}'  {dt*1000:.0f}ms")
    ok2 = (s == 200 and acao == "*")
    _verdict("browser CORS preflight passes (web is allowed to read)", ok2, f"ACAO={acao or 'MISSING'}")

    # ---- T3: DATA FORWARD — GET projects exactly like the app (key + Origin) ----
    print("\n[T3] READ DATA (forward) — GET /odin-anchor/anchor/v1/projects  (mimics app projects())")
    s, b, hd, dt = _req("GET", f"{BASE}/anchor/v1/projects", headers=H)
    n, stale, upd = None, None, None
    try:
        j = json.loads(b); n = len(j.get("projects", [])); stale = j.get("stale"); upd = j.get("updated")
    except Exception:
        pass
    print(f"     → HTTP {s}  {_kind(b)}  {dt*1000:.0f}ms  projects={n}  stale={stale}  updated={upd}")
    print(f"       Access-Control-Allow-Origin on the GET = '{hd.get('Access-Control-Allow-Origin','')}'")
    ok3 = (s == 200 and _kind(b) == "JSON" and (n or 0) > 0 and hd.get("Access-Control-Allow-Origin") == "*")
    _verdict("projects data returns (200 JSON, non-empty, CORS ok)", ok3, f"{n} projects, {dt*1000:.0f}ms")

    # ---- T4: THE 404's ONE MEANING — a wrong link. Prove it, and prove the right one differs. ----
    print("\n[T4] 404 ROOT-CAUSE — a 404 HTML means the LINK IS WRONG. Compare wrong vs right vs unknown-path:")
    wrong = f"https://{DOMAIN}/anchor/v1/projects"          # MISSING the /odin-anchor prefix (old/bad base)
    s_w, b_w, _, _ = _req("GET", wrong, headers=H)
    print(f"     wrong link (no /odin-anchor)  {wrong}\n        → HTTP {s_w}  {_kind(b_w)}   ← this is the app's '404 error page' when its base URL is wrong")
    s_r, b_r, _, _ = _req("GET", f"{BASE}/anchor/v1/projects", headers=H)
    print(f"     right link                    {BASE}/anchor/v1/projects\n        → HTTP {s_r}  {_kind(b_r)}")
    s_u, b_u, _, _ = _req("GET", f"{BASE}/anchor/v1/does-not-exist", headers=H)
    print(f"     unknown path ON the anchor    {BASE}/anchor/v1/does-not-exist\n        → HTTP {s_u}  {_kind(b_u)}  (anchor's OWN clean JSON 404, not an HTML page)")
    ok4 = (s_w == 404 and _kind(b_w) == "HTML" and s_r == 200 and _kind(b_r) == "JSON")
    _verdict("404 cause isolated: wrong base → HTML 404; correct base → 200 JSON", ok4,
             f"wrong={s_w}/{_kind(b_w)} right={s_r}/{_kind(b_r)}")

    # ---- T5: ASYNC QUEUE — fast ack now, result later. Prove no synchronous 502. ----
    print("\n[T5] ASYNC QUEUE — POST a request; the anchor must ACK IMMEDIATELY (received/queued), then the")
    print("     local machine pulls → processes → the RESULT returns later. We time every transition.")
    s, b, _, dt = _req("POST", f"{BASE}/anchor/v1/requests",
                       headers={"X-API-Key": key, "Content-Type": "application/json", "Origin": ORIGIN},
                       body={"project": PROJECT, "prompt": PROMPT, "sender": "isolation_probe"})
    rid, status0, msg0 = "", "", ""
    try:
        j = json.loads(b); rid = j.get("request_id", ""); status0 = j.get("status", ""); msg0 = j.get("message", "")
    except Exception:
        pass
    print(f"     → POST answered in {dt*1000:.0f}ms  HTTP {s}  status='{status0}'  id={rid}")
    print(f"       message: {msg0[:120]}")
    ok5a = (s == 200 and status0 == "queued" and dt < 3.0 and ("queue" in msg0.lower() or "receiv" in msg0.lower()))
    _verdict("FAST ACK: request accepted immediately (no synchronous wait → no 502)", ok5a, f"{dt*1000:.0f}ms, status={status0}")

    # follow the lifecycle
    ok5b = False
    if rid:
        print("     following the lifecycle (poll /requests/{id}):")
        seen, t_start, last = [], time.time(), ""
        result = None
        while time.time() - t_start < 120:
            time.sleep(2)
            sc, bc, _, _ = _req("GET", f"{BASE}/anchor/v1/requests/{rid}", headers=H)
            try:
                jj = json.loads(bc); st = jj.get("status", "?"); result = jj.get("result")
            except Exception:
                st = "?"
            if st != last:
                el = time.time() - t_start
                print(f"        t+{el:5.1f}s   status → {st}")
                seen.append(st); last = st
            if st in ("finished", "acknowledged", "failed", "response_received", "webhook_sent", "ack_pending"):
                # terminal-enough for the read path: result is available
                if result is not None or st in ("finished", "acknowledged", "failed"):
                    break
        pulled = any(s in seen for s in ("sent_to_local", "received_by_local", "processing"))
        returned = (result is not None) or any(s in seen for s in ("response_received", "webhook_sent", "ack_pending", "acknowledged", "finished"))
        print(f"        transitions: {' → '.join(seen) or '(none)'}")
        if result is not None:
            rp = result if isinstance(result, str) else json.dumps(result)
            print(f"        RESULT returned: {rp[:160]}")
        ok5b = pulled and returned
        _verdict("ASYNC ROUND-TRIP: local pulled (sent_to_local) and the RESULT came back", ok5b,
                 f"saw: {', '.join(seen)}")
    else:
        _verdict("ASYNC ROUND-TRIP", False, "no request_id returned — cannot follow lifecycle")

    # ---- FINAL VERDICT ----
    print("\n" + "=" * 78)
    allok = all(ok for _, ok, _ in _results)
    for label, ok, detail in _results:
        print(f"   {'✅' if ok else '❌'} {label}")
    print("-" * 78)
    if allok:
        print("   🟢 ANCHOR NODE: 100% PROVEN — reachable, CORS-open, data forward OK, 404-cause isolated,")
        print("      async queue = fast-ack + local pull + result-return. This node is DONE. Safe to move on.")
    else:
        first = next((l for l, ok, _ in _results if not ok), "?")
        print(f"   🔴 ANCHOR NODE: NOT DONE. First failing transmission → {first}")
        print("      Stay on THIS node; fix this exact transmission before touching anything else.")
    print("=" * 78)


if __name__ == "__main__":
    main()
