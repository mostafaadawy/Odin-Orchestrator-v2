#!/usr/bin/env python3
"""P4e test (no LLM, no model): the Normal / Jev mode toggle. Normal = exactly the old path (the decider is never
called). Jev = local decision with fallback on low confidence or any owner exclusion; safety rules stay on top;
every Jev decision is logged. python p4e_test.py <root>"""
import sys, os, pathlib, json
root = pathlib.Path(sys.argv[1]).resolve(); os.chdir(root)
sys.path.insert(0, str(root / "server")); sys.path.insert(0, str(root / "orchestrator"))
fails = []
def check(n, c, info=""):
    print(("PASS " if c else "FAIL ") + n + (f"  [{str(info)[:300]}]" if info and not c else ""))
    if not c: fails.append(n)
try:
    import jev_decider as jd
except Exception as e:
    check("0: the decider module exists", False, repr(e)); print("\nRESULT:", f"{len(fails)} FAIL: {fails}"); sys.exit(1)
import intent, semantic_router, dispatcher, api_v2
R = {(r.path, list(r.methods)[0]): r.endpoint for r in api_v2.build_router().routes if hasattr(r, "endpoint")}
calls = {"engine": 0, "router": 0, "decide": 0}
def engine(p): calls["engine"] += 1; return '{"mode": "orchestrate", "forbid": [], "why": "llm"}'
semantic_router.classify = lambda t, timeout=None: (calls.__setitem__("router", calls["router"] + 1), {"agents": ["Backend"], "action": "change", "why": "llm"})[1]
SCRIPT = {}
def fake_decide(dec, text):
    calls["decide"] += 1
    c, conf = SCRIPT.get(dec, (None, 0.0))
    return {"choice": c, "confidence": conf, "ms": 3.0, "fallback": conf < 0.8}
_real_decide = jd.decide
jd.decide = fake_decide
if jd.MODE_FILE.exists(): jd.MODE_FILE.unlink()
g = R.get(("/settings/decider-mode", "GET"))
check("1: the default mode is Normal", jd.get_mode() == "normal" and g is not None and g()["mode"] == "normal")
r = intent.classify_request("build the full app and deploy it", engine=engine); d = dispatcher.Dispatcher(audit=False).route("show the VM status")
check("2: Normal mode = the old path: engine + router called, decider never called",
      calls["engine"] == 1 and calls["router"] == 1 and calls["decide"] == 0 and r["source"] == "engine", calls)
p = R[("/settings/decider-mode", "POST")]
import tempfile; jd.ART = pathlib.Path(tempfile.mkdtemp()) / "jev"   # an UNTRAINED decider (the root may hold a copy of the real heads)
check("3: Jev mode cannot be switched on before the decider is trained", "error" in p({"mode": "jev"}) and jd.get_mode() == "normal")
jd.ART.mkdir(parents=True, exist_ok=True); (jd.ART / "meta.json").write_text('{"authority": "live"}')   # = after the owner's labels
check("4: the toggle switches to Jev mode once trained (and back)", p({"mode": "jev"})["mode"] == "jev" and jd.get_mode() == "jev")
calls.update(engine=0, router=0, decide=0); SCRIPT.update(D1_mode=("direct", 0.97), D2_agent=("DevOps & Cloud", 0.95), D2_action=("read", 0.93))
r = intent.classify_request("check the vm health", engine=engine)
check("5: Jev mode, confident: the local decider answers D1, the LLM engine is NOT called", r["mode"] == "direct" and r["source"] == "jev" and calls["engine"] == 0, (r, calls))
r = intent.classify_request("check the logs but do not deploy anything", engine=engine)
check("6: a message with an owner exclusion always goes to the LLM engine (exclusions never handled with less care)",
      r["source"] == "engine" and calls["engine"] == 1 and "deploy" in r["forbid"], (r, calls))
SCRIPT["D1_mode"] = ("orchestrate", 0.55)
r = intent.classify_request("make the landing page", engine=engine)
check("7: low confidence falls back to the LLM engine", r["source"] == "engine" and calls["engine"] == 2, (r, calls))
calls.update(router=0)
d = dispatcher.Dispatcher(audit=False).route("show the VM status and the payment card settings")
check("8: Jev routing: the decider picks lead + action; the semantic router is not called; security co-owner rule still applies",
      d["leadAgent"] == "DevOps & Cloud" and calls["router"] == 0 and "Security & Compliance" in d["agents"] and "Jev" in d["approval"].get("why", ""), d)
SCRIPT["D2_action"] = ("read", 0.95)
d = dispatcher.Dispatcher(audit=False).route("drop the production database table users")
check("9: hard approval categories stay on top even if the decider says read", d["approval"]["required"] is True, d["approval"])
SCRIPT["D2_agent"] = ("Backend", 0.4); calls.update(router=0)
d = dispatcher.Dispatcher(audit=False).route("list the orders")
check("10: low confidence on routing falls back to the semantic router", calls["router"] == 1, calls)
log = [json.loads(l) for l in open(jd.LOG)] if jd.LOG.exists() else []
check("11: every Jev decision is logged with mode, confidence, timing and fallback",
      log and all(set(("mode", "decision", "confidence", "ms", "fallback")) <= set(x) for x in log) and any(x["fallback"] for x in log) and any(not x["fallback"] for x in log), log[-2:])
p({"mode": "normal"}); calls.update(engine=0, router=0, decide=0)
intent.classify_request("check the vm health", engine=engine); dispatcher.Dispatcher(audit=False).route("show the VM status")
check("12: back in Normal mode the decider is never called again", calls["decide"] == 0 and calls["engine"] == 1 and calls["router"] == 1, calls)
# 13 (owner correction 1, 2026-10-12): a rarely seen class is grouped and ALWAYS handed to the LLM, even when confident
try:
    import mlx.core as mx
    class _E:
        def features(self, dec, text): return mx.array([1.0, 0.0])
    _h = {"W1": mx.eye(2), "b1": mx.zeros(2), "W2": mx.array([[0.0, 9.0, 0.0], [0.0, 0.0, 0.0]]), "b2": mx.zeros(3), "T": 1.0, "tau": 0.5,
          "options": ["Backend", getattr(jd, "RARE", "_rare"), "CTO Brain"]}
    _old = jd._load; jd._load = lambda: {"enc": _E(), "heads": {"D2_agent": _h}, "meta": {}}
    rr = _real_decide("D2_agent", "x"); jd._load = _old
    check("13: a grouped rare class always falls back to the LLM (never answered locally)", rr.get("fallback") is True and rr.get("confidence", 0) > 0.9, rr)
except Exception as e:
    check("13: a grouped rare class always falls back to the LLM (never answered locally)", False, repr(e))
# 14 (owner 2026-10-13): a class with < 5 independent test cases is OFF -> always the LLM, even when confident
try:
    import mlx.core as mx
    class _E2:
        def features(self, dec, text): return mx.array([1.0, 0.0])
    _h2 = {"W1": mx.eye(2), "b1": mx.zeros(2), "W2": mx.array([[0.0, 9.0], [0.0, 0.0]]), "b2": mx.zeros(2), "T": 1.0, "tau": 0.5,
           "options": ["direct", "orchestrate"], "off": ["orchestrate"]}
    _old2 = jd._load; jd._load = lambda: {"enc": _E2(), "heads": {"D1_mode": _h2}, "meta": {}}
    r14 = _real_decide("D1_mode", "x"); _h2["off"] = []; r14b = _real_decide("D1_mode", "x"); jd._load = _old2
    check("14: an OFF class always falls back to the LLM; the same answer is local once the class is on",
          r14.get("fallback") is True and r14b.get("fallback") is False, (r14, r14b))
except Exception as e:
    check("14: an OFF class always falls back to the LLM; the same answer is local once the class is on", False, repr(e))
# 15 (owner 2026-10-13): SHADOW authority (the default until the owner's labels) -> in Jev mode the decider runs and is
# logged, but the LLM path decides every case, even a confident one
try:
    (jd.ART / "meta.json").write_text('{"authority": "shadow"}'); p({"mode": "jev"})
    calls.update(engine=0, router=0, decide=0); SCRIPT.update(D1_mode=("direct", 0.99), D2_agent=("DevOps & Cloud", 0.99), D2_action=("read", 0.99))
    n0 = len(jd.LOG.read_text().splitlines()) if jd.LOG.exists() else 0
    r15 = intent.classify_request("check the vm health", engine=engine); d15 = dispatcher.Dispatcher(audit=False).route("show the VM status")
    if hasattr(jd, "flush"): jd.flush()   # v2: shadow decisions run off the request path; wait for their log lines
    new15 = [json.loads(l) for l in jd.LOG.read_text().splitlines()[n0:]] if jd.LOG.exists() else []
    check("15: shadow authority: decider runs + logged (authority=shadow, used=false) but the LLM engine and router decide",
          calls["decide"] >= 1 and calls["engine"] == 1 and calls["router"] == 1 and r15["source"] == "engine" and
          any(x.get("authority") == "shadow" and x.get("used") is False for x in new15) and jd.authority() == "shadow", (calls, r15.get("source"), new15[-2:]))
    # 16 (v2, cutover check A): in SHADOW the decider is OFF the request path — a slow decider adds no latency
    import time as _t
    _slow = lambda dec, text: (_t.sleep(0.5), {"choice": "direct", "confidence": 0.99, "ms": 500.0, "fallback": False})[1]
    jd.decide = _slow; t0 = _t.time(); rr = jd.jev_choice("D1_mode", "check the vm health"); dt = _t.time() - t0
    jd.flush(); jd.decide = fake_decide
    check("16: shadow adds no latency (answer None at once; decision still logged)", rr is None and dt < 0.1, round(dt, 3))
    check("17: the decider can be pre-warmed in the background", callable(getattr(jd, "prewarm", None)))
    os.environ["ODIN_JEV_EXPERIMENT"] = "1"
    check("15b: the measurement-only experiment switch is recognised (isolated copy harness only)", jd.authority() == "experiment")
    del os.environ["ODIN_JEV_EXPERIMENT"]
except Exception as e:
    check("15: shadow authority", False, repr(e))
print("\nRESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}"); sys.exit(1 if fails else 0)
