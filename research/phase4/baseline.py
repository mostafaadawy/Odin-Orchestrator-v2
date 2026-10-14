"""P4a-2 / P4f: today's REAL LLM decision for each labelled input, through Odin's own code paths:
  D1 mode    -> intent.classify_request(text, engine=projects._engine)        (Claude, plan login)
  D2 agent+action -> Dispatcher.route(text) (semantic_router = local Ollama + keyword rules; no routing log)
  D4 QA      -> the exact QA-recommendation prompt from api_v2 (Claude)
  D9 nature  -> agents_registry.suggest_agent(description)                   (Claude, keyword fallback)
Records per item: prediction, ms, reported usage (USD, NOT charged — plan login). R-ZC: refuses to run if any
paid auth is configured. usage: baseline.py <rep> [ids_file]"""
import sys, os, re, json, time, threading, pathlib, concurrent.futures as cf
LIMIT = threading.Event()
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "server")); sys.path.insert(0, str(ROOT / "orchestrator"))
import claude_cli, projects, intent, agents_registry
from dispatcher import Dispatcher
prob = claude_cli.paid_auth_problem()
if prob:
    print("R-ZC STOP:", prob); sys.exit(3)
rep = int(sys.argv[1]); ids = set(json.loads(open(sys.argv[2]).read())) if len(sys.argv) > 2 else None
items = [json.loads(l) for l in open(ROOT / "research/phase4/data/labels_draft.jsonl")]
if ids is not None: items = [x for x in items if x["id"] in ids]
tls = threading.local(); _orig = claude_cli.subprocess.run
def _run(cmd, *a, **k):
    r = _orig(cmd, *a, **k)
    try:
        if cmd and cmd[0] == "claude":
            d = json.loads(r.stdout or "{}"); tls.cost = getattr(tls, "cost", 0.0) + float(d.get("total_cost_usd") or 0)
            if re.search(r"hit your .{0,20}limit|usage limit|resets \d", str(d.get("result") or "")[:300], re.I):
                LIMIT.set()                      # plan limit: stop; an answer made without the LLM must never be recorded as the LLM's
    except Exception: pass
    return r
claude_cli.subprocess.run = _run
disp = Dispatcher(); disp.audit = False
QA_TMPL = ("You are the Project CTO for '{name}' (project id: {pid} — folders and paths use this ID, never the name). This project has NO QA agent.\nGoal: {goal}\n"
           "Is adding QA (a quality/code-review/test gate after each task) genuinely IMPORTANT "
           "here? Say yes ONLY if it materially reduces real risk (real code changes, production, "
           "data integrity). For a pure ops/deploy/sync or trivial task, say no.\n"
           'Reply ONLY JSON: {{"recommend": true|false, "why": "<one short sentence>"}}')
def one(x):
    tls.cost = 0.0; out = []
    if x["kind"] == "message":
        t0 = time.time(); c = intent.classify_request(x["text"], engine=projects._engine); ms = (time.time() - t0) * 1000
        out.append(("D1_mode", c.get("mode"), ms, tls.cost)); tls.cost = 0.0
        t0 = time.time(); d = disp.route(x["text"]); ms = (time.time() - t0) * 1000
        ap = d.get("approval") or {}
        act = ap.get("intent") or ("read" if ap.get("readOnly") or not ap.get("required") else "change")
        out.append(("D2_agent", d.get("leadAgent"), ms, 0.0)); out.append(("D2_action", act, ms, 0.0))
    elif x["kind"] == "goal":
        name, _, goal = x["text"].partition(": ")
        t0 = time.time(); raw = projects._engine(QA_TMPL.format(name=name, pid=x["source"].split(":", 1)[1], goal=goal))
        d = projects._extract_json_object(raw) or {}; ms = (time.time() - t0) * 1000
        out.append(("D4_qa", "yes" if d.get("recommend") else "no", ms, tls.cost))
    elif x["kind"] == "agent":
        t0 = time.time(); s = agents_registry.suggest_agent(x["text"]); ms = (time.time() - t0) * 1000
        out.append(("D9_nature", s.get("nature"), ms, tls.cost))
    return [{"id": x["id"], "decision": k, "pred": p, "label": x["labels"].get(k), "ms": round(ms, 1), "usage_usd": round(c, 5),
             "uncertain": x["uncertain"], "mode": "normal"} for k, p, ms, c in out]
o = ROOT / f"research/phase4/results/baseline_rep{rep}.jsonl"
part = o.with_suffix(".partial.jsonl"); o.parent.mkdir(parents=True, exist_ok=True)
res = [json.loads(l) for l in open(part)] if part.exists() else []     # resume: items already measured are kept
done = {r["id"] for r in res}; todo = [x for x in items if x["id"] not in done]
print(f"rep {rep}: {len(done)} items saved earlier, {len(todo)} to run", flush=True)
_lock = threading.Lock()
with cf.ThreadPoolExecutor(int(os.environ.get("P4_PAR", "4"))) as ex:
    for n, r in enumerate(ex.map(one, todo), 1):
        if LIMIT.is_set():
            print("STOP: plan usage limit reached - rerun later; this and later items are NOT saved", flush=True); ex.shutdown(wait=False, cancel_futures=True); os._exit(5)
        res += r
        with _lock, open(part, "a") as fh: fh.write("".join(json.dumps(z, ensure_ascii=False) + "\n" for z in r))
        if n % 20 == 0: print(f"  {n}/{len(todo)}", flush=True)
o.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in res))
from collections import defaultdict
agg = defaultdict(lambda: [0, 0, 0.0, 0.0])
for r in res:
    a = agg[r["decision"]]; a[0] += 1; a[1] += (r["pred"] == r["label"]); a[2] += r["ms"]; a[3] += r["usage_usd"]
for k, (n, ok, ms, c) in sorted(agg.items()):
    print(f"{k}: n={n} acc={ok/n:.3f} mean_ms={ms/n:.0f} usage_usd={c:.3f} (reported, not charged)")
