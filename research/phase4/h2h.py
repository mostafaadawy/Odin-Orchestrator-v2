"""P4f-1 head-to-head on the held-out REAL TEST split (never used in training or tuning).
Normal mode = the real LLM decision (baseline_rep{1,2,3}.jsonl, Odin's own code paths).
Jev mode    = the local decider; when its calibrated confidence is below tau it falls back to the LLM, so the
              Jev answer and time for that case = decider time + that rep's LLM answer and time.
3 repetitions each, same inputs. Reports accuracy (all labels / confident labels only), mean and median time,
reported usage (USD, NOT charged), calibration (ECE of the decider), fallback rate, and the one-time context
preparation cost. usage: h2h.py"""
import sys, os, json, time, statistics, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "server"))
import jev_decider as jd
P4 = ROOT / "research/phase4"; RES = P4 / "results"
split = json.loads((P4 / "data/split.json").read_text()); TEST = set(split["test"])
items = {x["id"]: x for x in (json.loads(l) for l in open(P4 / "data/labels_draft.jsonl")) if x["id"] in TEST}
GT, GSRC = {}, {}
for f in ("gt_outcome.jsonl", "gt_owner.jsonl"):     # INDEPENDENT truth only (log outcomes + owner review); never Claude drafts
    if (P4 / "data" / f).exists():
        for l in open(P4 / "data" / f):
            g = json.loads(l); GT[(g["id"], g["decision"])] = g["label"]; GSRC[(g["id"], g["decision"])] = g.get("rule", "owner")
if os.environ.get("H2H_EXT") == "1" and (P4 / "data" / "gt_outcome_ext.jsonl").exists():   # + EXTENDED read/change truth (tier=extended)
    for l in open(P4 / "data" / "gt_outcome_ext.jsonl"):
        g = json.loads(l)
        if (g["id"], g["decision"]) not in GT: GT[(g["id"], g["decision"])] = g["label"]; GSRC[(g["id"], g["decision"])] = g["rule"] + "/" + g["tier"]
import math
def wilson(k, n, z=1.96):
    if not n: return [None, None]
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(max(0, c - h), 3), round(min(1, c + h), 3)]
def mcnemar_exact(b, c):
    n = b + c
    if n == 0: return 1.0
    k = min(b, c); return round(min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n), 4)
def paired(rs, key_a, key_b):
    """per CASE: correct in the majority of its repetitions (3 reps), then exact McNemar on the discordant cases."""
    by = {}
    for r in rs: by.setdefault(r["id"], []).append(r)
    A = B = b = c = 0; n = 0
    for i, g in by.items():
        if any(r[key_b] is None for r in g) and key_b == "claude_pred" and all(r[key_b] is None for r in g): continue
        a_ok = sum(r[key_a] == r["label"] for r in g) * 2 > len(g); b_ok = sum(r[key_b] == r["label"] for r in g) * 2 > len(g)
        n += 1; A += a_ok; B += b_ok; b += a_ok and not b_ok; c += b_ok and not a_ok
    return {"n_cases": n, "jev_correct": A, "other_correct": B, "jev_acc": round(A / max(1, n), 3), "other_acc": round(B / max(1, n), 3),
            "jev_ci95": wilson(A, n), "other_ci95": wilson(B, n), "jev_only_right": b, "other_only_right": c, "mcnemar_p": mcnemar_exact(b, c)}
def verdict2(st, jms, oms, off):
    """owner 2026-10-13: 'BEST' only if the difference is significant (McNemar p < 0.05)."""
    if off: return "OFF - not measured (the LLM decides every case)"
    j, o, p = st["jev_acc"], st["other_acc"], st["mcnemar_p"]; fast = jms < oms
    if j > o and p < 0.05: return "BEST - significantly more accurate" + (" and faster" if fast else " (not faster)")
    if j < o and p < 0.05: return "FAILURE - significantly less accurate"
    if j > o: return f"NON-INFERIOR - higher but not significant (p={p})" + (", faster" if fast else "")
    if j == o: return "NON-INFERIOR - same accuracy" + (", faster; the LLM still handles every low-confidence case" if fast else ", not faster")
    return f"INCONCLUSIVE - lower but not significant (p={p})" + (", faster" if fast else "")
KIND = {"D1_mode": "message", "D2_agent": "message", "D2_action": "message", "D4_qa": "goal", "D9_nature": "agent"}
t0 = time.time(); m = jd._load(); load_s = time.time() - t0
TAG = os.environ.get("H2H_TAG", m["meta"].get("model", "chosen"))
RAW = {}                                                     # decider probabilities BEFORE temperature scaling (T=1), per item
def raw_conf(dec, text):
    k = (dec, text)
    if k not in RAW:
        h = m["heads"].get(dec)
        if h is None: RAW[k] = None
        else:
            p = jd.head_probs({**h, "T": 1.0}, m["enc"].features(dec, text)); i = int(p.argmax().item())
            RAW[k] = (h["options"][i], float(p[i].item()))
    return RAW[k]
CL = {}                                                      # Claude baseline (D2_action only), per rep
for rep_ in (1, 2, 3):
    f = RES / f"baseline_claude_D2_action_rep{rep_}.jsonl"
    if f.exists():
        for l in open(f):
            r = json.loads(l); CL[(rep_, r["id"], r["decision"])] = r
prep = {"model": m["meta"].get("model"), "layer": m["meta"].get("layer", "final"), "model_load_s": round(load_s, 1), "prefix_tokens": m["enc"].prefix_tokens, "prefix_prep_ms": round(m["enc"].prefix_ms)}
rows = []
for rep in (1, 2, 3):
    llm = {}
    for l in open(RES / f"baseline_rep{rep}.jsonl"):
        r = json.loads(l)
        if r["id"] in TEST: llm[(r["id"], r["decision"])] = r
    for dec in jd.DECISIONS:
        for x in items.values():
            if x["kind"] != KIND[dec] or (x["id"], dec) not in llm or (x["id"], dec) not in GT: continue
            L = llm[(x["id"], dec)]; d = jd.decide(dec, x["text"])
            fb = d["fallback"]; rc = raw_conf(dec, x["text"]); C = CL.get((rep, x["id"], dec))
            rows.append({"rep": rep, "decision": dec, "id": x["id"], "label": GT[(x["id"], dec)], "truth_src": GSRC[(x["id"], dec)], "uncertain": False,
                         "llm_pred": L["pred"], "llm_ms": L["ms"], "llm_usd": L["usage_usd"],
                         "jev_raw": d["choice"], "jev_conf": d["confidence"], "jev_ms_local": d["ms"], "fallback": fb,
                         "jev_pred": L["pred"] if fb else d["choice"], "jev_ms": d["ms"] + (L["ms"] if fb else 0.0),
                         "jev_usd": L["usage_usd"] if fb else 0.0,
                         "raw_choice": rc[0] if rc else None, "raw_conf": rc[1] if rc else 0.0,
                         "claude_pred": C["pred"] if C else None, "claude_ms": C["ms"] if C else None, "claude_usd": C["usage_usd"] if C else None})
(RES / f"h2h_rows_{TAG}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
def ece(rs, bins=10, conf_key="jev_conf", choice_key="jev_raw"):
    if not rs: return None
    tot = 0.0
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        s = [r for r in rs if lo < r[conf_key] <= hi or (b == 0 and r[conf_key] == 0)]
        if s: tot += len(s) / len(rs) * abs(sum(r[choice_key] == r["label"] for r in s) / len(s) - sum(r[conf_key] for r in s) / len(s))
    return round(tot, 3)
out = {"prep": prep, "per_decision": {}}
for dec in list(jd.DECISIONS) + ["ALL"]:
    rs = [r for r in rows if dec == "ALL" or r["decision"] == dec]
    if not rs: continue
    conf = [r for r in rs if not r["uncertain"]]
    def acc(k, s): return round(sum(r[k] == r["label"] for r in s) / max(1, len(s)), 3)
    reps = {}
    for rep in (1, 2, 3):
        s = [r for r in rs if r["rep"] == rep]
        reps[rep] = {"llm_acc": acc("llm_pred", s), "jev_acc": acc("jev_pred", s)}
    out["per_decision"][dec] = {
        "n_cases": len(rs) // 3, "n_confident_label": len(conf) // 3,
        "llm_acc": acc("llm_pred", rs), "jev_acc": acc("jev_pred", rs),
        "llm_acc_confident": acc("llm_pred", conf), "jev_acc_confident": acc("jev_pred", conf),
        "decider_alone_acc": acc("jev_raw", rs), "jev_agrees_with_llm": round(sum(r["jev_pred"] == r["llm_pred"] for r in rs) / len(rs), 3),
        "truth_sources": dict(__import__("collections").Counter(r["truth_src"] for r in rs if r["rep"] == 1)),
        "label_classes": dict(__import__("collections").Counter(r["label"] for r in rs if r["rep"] == 1)),
        "llm_ms_mean": round(statistics.mean(r["llm_ms"] for r in rs)), "llm_ms_median": round(statistics.median(r["llm_ms"] for r in rs)),
        "jev_ms_mean": round(statistics.mean(r["jev_ms"] for r in rs)), "jev_ms_median": round(statistics.median(r["jev_ms"] for r in rs)),
        "decider_ms_mean": round(statistics.mean(r["jev_ms_local"] for r in rs)),
        "llm_usd": round(sum(r["llm_usd"] for r in rs) / 3, 3), "jev_usd": round(sum(r["jev_usd"] for r in rs) / 3, 3),
        "fallback_rate": round(sum(r["fallback"] for r in rs) / len(rs), 3), "ece_decider_after_T": ece(rs),
        "ece_decider_before_T": ece(rs, conf_key="raw_conf", choice_key="raw_choice"), "by_rep": reps}
    cr = [r for r in rs if r["claude_pred"] is not None or r["claude_ms"] is not None]
    if cr:
        out["per_decision"][dec].update({"claude_n": len(cr) // 3 if len(cr) >= 3 else len(cr), "claude_acc": acc("claude_pred", cr),
            "claude_ms_mean": round(statistics.mean(r["claude_ms"] for r in cr)), "claude_ms_median": round(statistics.median(r["claude_ms"] for r in cr)),
            "claude_usd_per_run": round(sum(r["claude_usd"] or 0 for r in cr) / 3, 3), "jev_acc_same_cases": acc("jev_pred", cr), "llm_acc_same_cases": acc("llm_pred", cr)})
    v = out["per_decision"][dec]
    off_ = v["fallback_rate"] >= 0.999
    v["stats_vs_production_llm"] = st1 = paired(rs, "jev_pred", "llm_pred")
    v["verdict_vs_production_llm_stat"] = verdict2(st1, v["jev_ms_mean"], v["llm_ms_mean"], off_)
    if cr:
        v["stats_vs_claude"] = st2 = paired(cr, "jev_pred", "claude_pred")
        v["verdict_vs_claude_stat"] = verdict2(st2, v["jev_ms_mean"], v["claude_ms_mean"], off_)
    # (the gate2 verdict without a significance test was removed: owner 2026-10-13)
(RES / f"h2h_summary_{TAG}.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
