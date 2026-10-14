"""P4b-2 / P4c / P4d-3: train the Jev decision heads on the M4 with MLX.
 1. split the REAL labelled inputs into validation (30%) and held-out TEST (70%) per kind, fixed seed; TEST is never
    used for training or tuning (P4d-3);
 2. leakage check: drop generated training examples too close to ANY real input (ratio > 0.80 or token Jaccard > 0.70);
 3. for each candidate model (Qwen2.5 0.5B / 1.5B, full precision): frozen features with the prepared prefix;
 4. per decision: MLP head (hidden 256) trained with class weights; temperature T fitted on validation (P4c-3);
    fallback threshold tau = lowest confidence where the decider's validation accuracy on the kept cases is at
    least the real LLM's validation accuracy (P4c-5); never below the LLM;
 5. pick the model size by validation accuracy (tie -> smaller); save heads to data/jev/ + metadata.
usage: train_decider.py"""
import sys, os, json, re, time, random, pathlib, difflib
ROOT = pathlib.Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "server"))
import mlx.core as mx, mlx.nn as nn, mlx.optimizers as optim
import jev_decider as jd
P4 = ROOT / "research/phase4"; DATA = P4 / "data"; RES = P4 / "results"; CACHE = P4 / "cache"
real = [json.loads(l) for l in open(DATA / "labels_draft.jsonl")]
gen = [json.loads(l) for f in ("train_gen.jsonl", "train_gen_extra.jsonl") if (DATA / f).exists() for l in open(DATA / f)]
# owner correction 2 (2026-10-12): validation/test truth is INDEPENDENT of the compared LLM — log outcomes
# (outcome_labels.py) plus the owner's reviewed labels (gt_owner.jsonl); Claude's drafts are never truth.
GT = {}
for f in ("gt_outcome.jsonl", "gt_owner.jsonl"):
    if (DATA / f).exists():
        for l in open(DATA / f):
            g = json.loads(l); GT[(g["id"], g["decision"])] = g["label"]      # owner review overrides a log outcome
MIN_VAL = 5
# 1. split
rnd = random.Random(7); val, test = [], []
for kind in ("message", "agent", "goal"):
    xs = [x for x in real if x["kind"] == kind]; rnd.shuffle(xs); k = max(1, round(len(xs) * 0.3))
    val += xs[:k]; test += xs[k:]
(DATA / "split.json").write_text(json.dumps({"val": [x["id"] for x in val], "test": [x["id"] for x in test]}))
# 2. leakage check
def norm(t): return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9؀-ۿ ]", " ", t.lower())).strip()
RN = [(norm(x["text"]), set(norm(x["text"]).split())) for x in real]
def leaks(t):
    n = norm(t); w = set(n.split())
    for rn, rw in RN:
        if w and rw and len(w & rw) / len(w | rw) > 0.70: return True
        if abs(len(n) - len(rn)) < 0.5 * max(len(n), len(rn)) and difflib.SequenceMatcher(None, n, rn).ratio() > 0.80: return True
    return False
seen, train, dropped = set(), [], 0
for x in gen:
    n = norm(x["text"])
    if n in seen: continue
    seen.add(n)
    if leaks(x["text"]): dropped += 1; continue
    train.append(x)
print(f"train {len(train)} (dropped {dropped} for leakage, dupes removed), val {len(val)}, test {len(test)}", flush=True)
# LLM validation accuracy per decision (from the 4a-2 baseline run)
base = {}
_bf = RES / "baseline_rep1.jsonl"
if not _bf.exists(): _bf = RES / "baseline_rep1.partial.jsonl"     # LLM accuracy only from rows the real LLM answered
for l in open(_bf):
    r = json.loads(l); base[(r["id"], r["decision"])] = r
def llm_val_acc(dec):
    rs = [(base[(x["id"], dec)], GT[(x["id"], dec)]) for x in val if (x["id"], dec) in base and (x["id"], dec) in GT]
    return sum(r["pred"] == g for r, g in rs) / max(1, len(rs))
DEC_KIND = {"D1_mode": "message", "D2_agent": "message", "D2_action": "message", "D4_qa": "goal", "D9_nature": "agent"}
def rows(items, dec): return [(x["text"], x["labels"][dec]) for x in items if x["kind"] == DEC_KIND[dec] and dec in x["labels"]]
def gt_rows(items, dec): return [(x["text"], GT[(x["id"], dec)]) for x in items if x["kind"] == DEC_KIND[dec] and (x["id"], dec) in GT]
class Head(nn.Module):
    def __init__(s, d, k): super().__init__(); s.l1 = nn.Linear(d, 256); s.l2 = nn.Linear(256, k); s.drop = nn.Dropout(0.1)
    def __call__(s, x): return s.l2(s.drop(nn.relu(s.l1(x))))
def feats(enc, dec, texts, tag, model_name):
    import hashlib; h = hashlib.sha256("\x00".join(texts).encode()).hexdigest()[:12]   # cache keyed by the exact texts
    f = CACHE / model_name / f"{dec}_{tag}_{h}.npy"; f.parent.mkdir(parents=True, exist_ok=True)
    if f.exists(): return mx.load(str(f))
    a = mx.stack([enc.features(dec, t) for t in texts]); mx.save(str(f), a); return a
def nll(logits, y, T): return float(nn.losses.cross_entropy(logits / T, y).mean().item())
summary = {}
for model_name in [m for m in ("Qwen2.5-0.5B-Instruct", "Qwen2.5-1.5B-Instruct") if (P4 / "models" / m / "config.json").exists()]:
    t0 = time.time(); enc = jd.Encoder(str(P4 / "models" / model_name)); load_s = time.time() - t0
    out = {"load_s": round(load_s, 1), "prefix_tokens": enc.prefix_tokens, "prefix_ms": round(enc.prefix_ms), "heads": {}}
    for dec, spec in jd.DECISIONS.items():
        tr, va, te = rows(train, dec), gt_rows(val, dec), gt_rows(test, dec)
        counts = {o: sum(1 for _, y in tr if y == o) for o in spec["options"]}
        rare = [o for o, c in counts.items() if c < jd.MIN_PER_CLASS]          # owner correction 1: grouped -> LLM decides them
        opts = [o for o in spec["options"] if o not in rare] + ([jd.RARE] if rare else [])
        tr = [(t, jd.RARE if y in rare else y) for t, y in tr]
        if not tr: continue
        Xtr = feats(enc, dec, [t for t, _ in tr], "train", model_name); ytr = mx.array([opts.index(y) for _, y in tr])
        va = [(t, jd.RARE if y in rare else y) for t, y in va]
        mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-5
        cnt = [max(1, sum(1 for _, y in tr if y == o)) for o in opts]; cw = mx.array([len(tr) / (len(opts) * c) for c in cnt])
        mx.random.seed(0); head = Head(Xtr.shape[1], len(opts)); opt = optim.AdamW(1e-3, weight_decay=1e-2)
        def lf(m, x, y): return (nn.losses.cross_entropy(m(x), y) * cw[y]).mean()
        g = nn.value_and_grad(head, lf); xn = (Xtr - mu) / sd
        for ep in range(300):
            l, gr = g(head, xn, ytr); opt.update(head, gr); mx.eval(head.parameters(), opt.state)
        head.eval(); T, tau, acc_va, llm, why = 1.0, 1.01, None, None, ""
        if len(va) >= MIN_VAL:
            Xva = feats(enc, dec, [t for t, _ in va], "val", model_name); yva = mx.array([opts.index(y) for _, y in va])
            zva = head((Xva - mu) / sd)
            T = min([0.5 + 0.1 * i for i in range(46)], key=lambda t: nll(zva, yva, t))
            p = mx.softmax(zva / T, axis=-1); conf = p.max(-1); pred = p.argmax(-1)
            ok = (pred == yva)
            if jd.RARE in opts: ok = ok * (pred != opts.index(jd.RARE))     # a rare-group answer is a fallback, never a local success
            acc_va = float(ok.mean().item()); llm = llm_val_acc(dec)
            for c in sorted(set(round(float(v), 4) for v in conf.tolist())):
                keep = conf >= c
                if int(keep.sum().item()) >= 3 and float((ok * keep).sum().item() / keep.sum().item()) >= llm:
                    tau = c; break
        else:
            why = f"only {len(va)} independent validation labels (< {MIN_VAL}): head stays OFF (always the LLM) until the owner reviews labels"
        if te: feats(enc, dec, [t for t, _ in te], "test", model_name)
        # fold the standardisation into the first layer so serving needs no extra state
        W1 = head.l1.weight.T / sd[:, None]; b1 = head.l1.bias - (mu / sd) @ head.l1.weight.T
        out["heads"][dec] = {"options": opts, "T": round(T, 2), "tau": tau, "val_acc": None if acc_va is None else round(acc_va, 3),
                             "llm_val_acc": None if llm is None else round(llm, 3), "train_counts": counts, "rare_grouped": rare, "off_why": why,
                             "val_class_counts": {o: sum(1 for _, y in va if y == o) for o in opts},
                             "n_train": len(tr), "n_val": len(va), "n_test": len(te),
                             "_w": {"W1": W1, "b1": b1, "W2": head.l2.weight.T, "b2": head.l2.bias}}
        print(f"[{model_name}] {dec}: counts={counts} rare={rare} n_val={len(va)} val_acc={acc_va} llm_val={llm} T={T:.2f} tau={tau} {why}", flush=True)
    summary[model_name] = out; del enc
def score(o):
    hs = [h for h in o["heads"].values() if h["val_acc"] is not None]
    return sum(h["val_acc"] * h["n_val"] for h in hs) / max(1, sum(h["n_val"] for h in hs))
names = sorted(summary, key=lambda m: (-round(score(summary[m]), 3), "1.5B" in m))
best = names[0]; print("chosen:", best, {m: round(score(summary[m]), 3) for m in summary}, flush=True)
ART = jd.ART; ART.mkdir(parents=True, exist_ok=True)
(ART / "context.txt").write_text(jd.standing_context())
meta = {"model": best, "model_dir": str(P4 / "models" / best), "trained": time.strftime("%Y-%m-%d %H:%M"), "heads": {}}
for dec, h in summary[best]["heads"].items():
    mx.savez(str(ART / f"{dec}.npz"), **h["_w"])
    meta["heads"][dec] = {k: v for k, v in h.items() if k != "_w"}
(ART / "meta.json").write_text(json.dumps(meta, indent=1))
(RES / "train_summary.json").write_text(json.dumps({m: {**{k: v for k, v in o.items() if k != "heads"},
    "heads": {d: {k: v for k, v in h.items() if k != "_w"} for d, h in o["heads"].items()}, "val_score": round(score(o), 3)} for m, o in summary.items()} | {"chosen": best}, indent=1))
print("SAVED", ART)
