"""Re-ask Claude ONCE for rows of baseline_claude_D2_action_rep<r>.jsonl whose answer had no 'read'/'change' word
(fairness to the Claude baseline; Odin's own json_retry pattern). Records the raw replies. usage: baseline_claude_fix.py <rep>"""
import sys, os, re, json, time, pathlib
sys.argv = [sys.argv[0], sys.argv[1]]
exec(open(pathlib.Path(__file__).parent / "baseline_claude.py").read().split("res = []")[0])   # same setup (R-ZC, context, limit guard)
f = P4 / f"results/baseline_claude_{DEC}_rep{rep}.jsonl"; rows = [json.loads(l) for l in open(f)]; txt = {x["id"]: x["text"] for x in items}
for r in rows:
    if r["pred"] is not None: continue
    tls.cost = 0.0; t0 = time.time()
    raw = claude_cli.ClaudeCLIBrain().respond(CTX + jd.suffix(DEC, txt[r["id"]]) + "\nReply with ONLY one word: read or change.", lang="en")
    if LIMIT.is_set(): print("STOP: plan usage limit"); sys.exit(5)
    m = re.search(r"\b(read|change)\b", (raw or "").lower())
    r.update({"first_raw_unparsed": True, "retry_raw": (raw or "")[:200], "pred": m.group(1) if m else None,
              "ms": round(r["ms"] + (time.time() - t0) * 1000, 1), "usage_usd": round(r["usage_usd"] + tls.cost, 5)})
f.write_text("".join(json.dumps(r) + "\n" for r in rows))
print(f"rep {rep}: acc={sum(r['pred'] == r['label'] for r in rows) / len(rows):.3f} still_unparsed={sum(r['pred'] is None for r in rows)}",
      [r.get("retry_raw", "")[:80] for r in rows if r.get("first_raw_unparsed")][:6])
