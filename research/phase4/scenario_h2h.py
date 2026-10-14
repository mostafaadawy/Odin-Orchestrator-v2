"""P4f-2 / JEV-DoD-4 (owner 2026-10-13): REAL-scenario head-to-head, Normal vs Jev mode, 3 repetitions, through the SAME
HTTP entry points the desktop uses, on the ISOLATED copy server (port 28000, remote tools blocked by the shims, private
Postgres). Plan login only (R-ZC); stops on a plan-limit message. Jev runs with the measurement-only 'experiment'
authority (env ODIN_JEV_EXPERIMENT=1 on the COPY server only; production/live stays SHADOW until the owner's labels).
  chat runs   -> /scope/stream (routing D2 = specialist + read/change; the D2 specialist head is OFF, so the router
                 decides in both modes and the run measures the Jev overhead when it falls back)
  project runs-> /projects/{pid}/orchestrate (D1 direct/orchestrate via intent.classify_request)
Inputs: real owner messages from the held-out TEST set with INDEPENDENT truth (log outcomes). Records end-to-end time,
the decision taken (D1 inferred from the run: one delegate = direct, a multi-step plan = orchestrate; Jev decisions from
workspace/history/decisions.jsonl), reported usage (not charged), errors. usage: scenario_h2h.py <normal|jev> <rep>"""
import sys, os, json, time, re, pathlib, urllib.request, urllib.parse
R = pathlib.Path(__file__).resolve().parents[2]; BASE = "http://127.0.0.1:28000"
OUT = R / "research/phase4/results/scenarios"; OUT.mkdir(parents=True, exist_ok=True)
LEDGER = R / "_consolidation/results/claude_calls.jsonl"; DLOG = R / "workspace/history/decisions.jsonl"
LIMIT_RE = re.compile(r"(usage limit reached|reached your usage limit|claude ai usage limit|limit will reset|out of extra usage|5-hour limit|weekly limit|hit your .{0,20}limit)", 2)
def tok(): return (R / "data/brain_token").read_text().strip()
def spent():
    s = 0.0
    if LEDGER.exists():
        for l in LEDGER.read_text().splitlines():
            try: s += json.loads(l).get("cost_usd") or 0
            except Exception: pass
    return s
def jpost(p, b):
    r = urllib.request.Request(BASE + p, data=json.dumps(b).encode(), headers={"Content-Type": "application/json", "X-Odin-Token": tok()})
    return json.load(urllib.request.urlopen(r, timeout=60))
def jget(p): return json.load(urllib.request.urlopen(urllib.request.Request(BASE + p, headers={"X-Odin-Token": tok()}), timeout=60))
def sse(path, maxs=900):
    ev, cur = [], None; t0 = time.time()
    try:
        req = urllib.request.Request(BASE + path, headers={"X-Odin-Token": tok()})
        with urllib.request.urlopen(req, timeout=maxs) as resp:
            for raw in resp:
                line = raw.decode("utf-8", "replace").rstrip("\n")
                if line.startswith("event:"): cur = line[6:].strip()
                elif line.startswith("data:"):
                    d = line[5:].strip()
                    try: d = json.loads(d)
                    except Exception: pass
                    ev.append((cur, d))
                if time.time() - t0 > maxs: ev.append(("_timeout", maxs)); break
    except Exception as e:
        ev.append(("_error", str(e)))
    return ev, time.time() - t0
CHAT = [("how many contacts", "read"), ("hey what is the time now", "read"), ("can you recall the last question", "read"),
        ("remember apple", "change"), ("remember my favorite number is 4747", "change"),
        ("use the protocol od dynamic ip az cimmands then access by ssk , no vulnarbility is accepted", "change")]
RUNS = [("hubspot-crm-operator", "How many contacts and companies do we have", "direct"),
        ("fulfillment-vq-status-read-only-dc1e", "how many orders this month?", "direct"),
        ("email-klaviyo-workflows-read-only-18ca", "how many profiles do we have", "direct")]
mode, rep = sys.argv[1], int(sys.argv[2])
assert mode in ("normal", "jev")
st = jpost("/settings/decider-mode", {"mode": mode}); assert st.get("mode") == mode, st
assert mode == "normal" or st.get("authority") == "experiment", ("copy server must run with ODIN_JEV_EXPERIMENT=1 for the Jev arm", st)
rows = []
def dlog_n(): return len(DLOG.read_text().splitlines()) if DLOG.exists() else 0
def dlog_since(n): return [json.loads(l) for l in DLOG.read_text().splitlines()[n:]] if DLOG.exists() else []
for text, truth in CHAT:
    n0, c0 = dlog_n(), spent()
    ev, sec = sse(f"/scope/stream?scope=company&text={urllib.parse.quote(text)}&lang=en&cid=", 600)
    js = json.dumps(ev, default=str)[-60000:]
    jd = dlog_since(n0)
    rows.append({"kind": "chat", "mode": mode, "rep": rep, "text": text, "truth_D2_action": truth, "seconds": round(sec, 2),
                 "usage_usd": round(spent() - c0, 4), "n_events": len(ev), "error": any(e in ("_error", "_timeout") for e, _ in ev),
                 "jev_decisions": [{k: d.get(k) for k in ("decision", "choice", "confidence", "fallback", "used", "ms", "authority")} for d in jd],
                 "limit_seen": bool(LIMIT_RE.search(js))})
    print(json.dumps({k: rows[-1][k] for k in ("kind", "mode", "rep", "text", "seconds", "usage_usd", "error")}), flush=True)
    if rows[-1]["limit_seen"]: break
if not any(r["limit_seen"] for r in rows):
    for pid, goal, truth in RUNS:
        n0, c0 = dlog_n(), spent()
        ev, sec = sse(f"/projects/{pid}/orchestrate?goal={urllib.parse.quote(goal)}", 900)
        js = json.dumps(ev, default=str)[-60000:]
        plans = [d for e, d in ev if e == "plan"]; dels = [d for e, d in ev if e == "delegate"]
        steps = None
        if plans:
            s = plans[-1].get("steps") if isinstance(plans[-1], dict) else None
            try: steps = len(s) if isinstance(s, list) else len(eval(s)) if isinstance(s, str) else None
            except Exception: steps = None
        members = {d.get("to") for d in dels if isinstance(d, dict)}
        inferred = "orchestrate" if (steps or 0) > 1 or len(members) > 1 else ("direct" if (dels or plans) else None)
        jd = dlog_since(n0); done = [d for e, d in ev if e == "done"]
        rows.append({"kind": "project_run", "mode": mode, "rep": rep, "pid": pid, "text": goal, "truth_D1_mode": truth, "inferred_mode": inferred,
                     "plan_steps": steps, "members": sorted(m for m in members if m), "seconds": round(sec, 2), "usage_usd": round(spent() - c0, 4),
                     "ok": (done[-1].get("ok") if done and isinstance(done[-1], dict) else None), "n_events": len(ev),
                     "error": any(e in ("_error", "_timeout") for e, _ in ev),
                     "jev_decisions": [{k: d.get(k) for k in ("decision", "choice", "confidence", "fallback", "used", "ms", "authority")} for d in jd],
                     "limit_seen": bool(LIMIT_RE.search(js))})
        print(json.dumps({k: rows[-1][k] for k in ("kind", "mode", "rep", "pid", "inferred_mode", "seconds", "usage_usd", "error")}), flush=True)
        if rows[-1]["limit_seen"]: break
jpost("/settings/decider-mode", {"mode": "normal"})
(OUT / f"{mode}_r{rep}.json").write_text(json.dumps(rows, indent=1))
if any(r["limit_seen"] for r in rows): print("STOP: plan limit"); sys.exit(4)
print("DONE", mode, rep)
