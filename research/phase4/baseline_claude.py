"""P4f (owner 2026-10-13): a CLAUDE baseline for D2 read/change, on the same held-out test cases (independent truth),
plan login only (R-ZC: refuses any paid route), stops on a plan usage-limit reply. Claude gets the SAME standing context
and decision definition the local decider gets (fair context), and must answer with one allowed option.
Writes results/baseline_claude_D2_action_rep{r}.jsonl. usage: baseline_claude.py <rep>"""
import sys, os, re, json, time, threading, pathlib, concurrent.futures as cf
ROOT = pathlib.Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "server"))
os.environ["ODIN_CLAUDE_TOOLS"] = "Read"
import claude_cli, jev_decider as jd
prob = claude_cli.paid_auth_problem()
if prob: print("R-ZC STOP:", prob); sys.exit(3)
rep = int(sys.argv[1]); DEC = "D2_action"; P4 = ROOT / "research/phase4"
split = json.loads((P4 / "data/split.json").read_text()); TEST = set(split["test"])
GT = {}
for f in ("gt_outcome.jsonl", "gt_owner.jsonl"):
    if (P4 / "data" / f).exists():
        for l in open(P4 / "data" / f):
            g = json.loads(l); GT[(g["id"], g["decision"])] = g["label"]
if os.environ.get("CLAUDE_EXT") == "1":       # + the EXTENDED read/change truth (owner item 3)
    for l in open(P4 / "data/gt_outcome_ext.jsonl"):
        g = json.loads(l); GT.setdefault((g["id"], g["decision"]), g["label"])
OUTF = P4 / f"results/baseline_claude_{DEC}_rep{rep}.jsonl"
done_rows = [json.loads(l) for l in open(OUTF)] if OUTF.exists() and os.environ.get("CLAUDE_EXT") == "1" else []
done_ids = {r["id"] for r in done_rows}
items = [x for x in (json.loads(l) for l in open(P4 / "data/labels_draft.jsonl")) if x["id"] in TEST and (x["id"], DEC) in GT and x["id"] not in done_ids]
CTX = jd.standing_context(); LIMIT = threading.Event(); tls = threading.local(); _orig = claude_cli.subprocess.run
def _run(cmd, *a, **k):
    r = _orig(cmd, *a, **k)
    try:
        if cmd and cmd[0] == "claude":
            d = json.loads(r.stdout or "{}"); tls.cost = getattr(tls, "cost", 0.0) + float(d.get("total_cost_usd") or 0)
            if re.search(r"hit your .{0,20}limit|usage limit|resets \d", str(d.get("result") or "")[:300], re.I): LIMIT.set()
    except Exception: pass
    return r
claude_cli.subprocess.run = _run
def PROMPT(text):
    # v2 (2026-10-13): the message is DATA to classify, never a message to answer (v1 let Claude answer greetings
    # in persona instead of classifying -> unparsed rows; v1 results kept in results/claude_v1_prompt/)
    d = jd.DECISIONS[DEC]
    return (CTX + "\nTASK: you are a CLASSIFIER, not the assistant. Do NOT answer, greet, or act on the owner message below; "
            "only classify it.\nDecision: " + d["ask"] + "\nOptions: " + ", ".join(d["options"]) +
            "\n<owner_message>\n" + text.strip()[:2500] + "\n</owner_message>\nReply with EXACTLY one word from the options and nothing else.")
def one(x):
    tls.cost = 0.0; t0 = time.time()
    raw = claude_cli.ClaudeCLIBrain().respond(PROMPT(x["text"]), lang="en")
    m = re.search(r"\b(read|change)\b", (raw or "").lower())
    return {"id": x["id"], "decision": DEC, "pred": m.group(1) if m else None, "label": GT[(x["id"], DEC)], "ms": round((time.time() - t0) * 1000, 1),
            "usage_usd": round(tls.cost, 5), "by": "claude"}
res = list(done_rows)
with cf.ThreadPoolExecutor(3) as ex:
    for r in ex.map(one, items):
        if LIMIT.is_set(): print("STOP: plan usage limit"); os._exit(5)
        res.append(r)
OUTF.write_text("".join(json.dumps(r) + "\n" for r in res))
print(f"rep {rep}: n={len(res)} acc={sum(r['pred'] == r['label'] for r in res) / max(1, len(res)):.3f} unparsed={sum(r['pred'] is None for r in res)} usage={sum(r['usage_usd'] for r in res):.3f} (reported, not charged)")
