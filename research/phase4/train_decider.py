"""P4b-2 / P4c / P4d-3 (v2, owner 2026-10-13): train the Jev decision heads on the M4 with MLX.
 1. real labelled inputs -> validation (30%) / held-out TEST (70%) per kind, seed 7 (unchanged); TEST never trains or tunes;
    truth = independent labels only (log outcomes + owner review), never Claude's drafts;
 2. generated training data: leakage filter (as v1), then a fixed 15% SYNTHETIC held-out split (seed 13) used to compare
    layers, report per-class recall and help fit the temperature (it never touches TEST);
 3. LAYER COMPARISON: last-token state after layers 12, 16, 20, 24, 28, the mean of 16-24, and the final normed state;
    per layer: validation accuracy, ECE and per-class recall; the best layer (mean synthetic-validation accuracy over
    the decisions) is kept per model;
 4. CALIBRATION: temperature T fitted on the validation set (independent + synthetic), log grid 0.05-100;
    ECE before (T=1) and after; thresholds tau re-fitted AFTER calibration on the independent validation labels
    (tau = lowest confidence where the decider's accuracy on kept cases >= the LLM's; never below the LLM);
 5. classes with < 5 independent cases (val+test) are OFF (that answer always goes to the LLM); heads with < 5
    independent validation labels stay OFF entirely; rare (< 20 training examples) grouped -> LLM;
 6. BOTH model sizes are saved (data/jev_models/<model>/); the chosen one is also written to data/jev.
usage: train_decider.py"""
import sys, os, json, re, time, random, pathlib, difflib, hashlib, math, shutil
ROOT = pathlib.Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT / "server"))
import mlx.core as mx, mlx.nn as nn, mlx.optimizers as optim
import jev_decider as jd
P4 = ROOT / "research/phase4"; DATA = P4 / "data"; RES = P4 / "results"; CACHE = P4 / "cache"
SPECS = ["L12", "L16", "L20", "L24", "L28", "mean16-24", "final"]
MIN_VAL, MIN_CLASS_CASES = 5, 5
# owner 2026-10-13 item 7: after the owner's labels the re-run order is fixed: (1) layer choice on the REAL validation set,
# (2) temperature on the REAL validation set only, (3) thresholds, (4) head-to-head (h2h.py, run by after_labels.sh).
# Only this mode may write authority "live"; every other run writes "shadow" (no live decisions).
AFTER_LABELS = "--after-labels" in sys.argv
if AFTER_LABELS and not ((DATA / "gt_owner.jsonl").exists() and (DATA / "gt_owner.jsonl").read_text().strip()):
    print("REFUSED: --after-labels needs the owner's labels in data/gt_owner.jsonl"); sys.exit(2)
real = [json.loads(l) for l in open(DATA / "labels_draft.jsonl")]
gen = [json.loads(l) for f in ("train_gen.jsonl", "train_gen_extra.jsonl") if (DATA / f).exists() for l in open(DATA / f)]
GT = {}
for f in ("gt_outcome.jsonl", "gt_owner.jsonl"):
    if (DATA / f).exists():
        for l in open(DATA / f):
            g = json.loads(l); GT[(g["id"], g["decision"])] = g["label"]
rnd = random.Random(7); val, test = [], []
for kind in ("message", "agent", "goal"):
    xs = [x for x in real if x["kind"] == kind]; rnd.shuffle(xs); k = max(1, round(len(xs) * 0.3))
    val += xs[:k]; test += xs[k:]
(DATA / "split.json").write_text(json.dumps({"val": [x["id"] for x in val], "test": [x["id"] for x in test]}))
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
r2 = random.Random(13); syn_tr, syn_va = [], []
for x in train: (syn_va if r2.random() < 0.15 else syn_tr).append(x)
print(f"generated {len(train)} after leakage ({dropped} dropped): synthetic train {len(syn_tr)}, synthetic val {len(syn_va)}; real val {len(val)}, test {len(test)}", flush=True)
_bf = RES / "baseline_rep1.jsonl"
base = {}
for l in open(_bf):
    r = json.loads(l); base[(r["id"], r["decision"])] = r
DEC_KIND = {"D1_mode": "message", "D2_agent": "message", "D2_action": "message", "D4_qa": "goal", "D9_nature": "agent"}
def rows(items, dec): return [(x["text"], x["labels"][dec]) for x in items if x["kind"] == DEC_KIND[dec] and dec in x["labels"]]
def gt_rows(items, dec): return [(x["id"], x["text"], GT[(x["id"], dec)]) for x in items if x["kind"] == DEC_KIND[dec] and (x["id"], dec) in GT]
def llm_acc(rs, dec):
    z = [(base[(i, dec)]["pred"], y) for i, _, y in rs if (i, dec) in base]
    return sum(p == y for p, y in z) / max(1, len(z))
def indep_counts(dec):
    c = {}
    for x in val + test:
        if (x["id"], dec) in GT: c[GT[(x["id"], dec)]] = c.get(GT[(x["id"], dec)], 0) + 1
    return c
class Head(nn.Module):
    def __init__(s, d, k): super().__init__(); s.l1 = nn.Linear(d, 256); s.l2 = nn.Linear(256, k); s.drop = nn.Dropout(0.1)
    def __call__(s, x): return s.l2(s.drop(nn.relu(s.l1(x))))
def feats(enc, dec, texts, tag, model_name):
    """all layer specs from ONE forward per text; cached per (texts, spec)."""
    h = hashlib.sha256("\x00".join(texts).encode()).hexdigest()[:12]
    d = CACHE / model_name; d.mkdir(parents=True, exist_ok=True)
    specs = [sp for sp in SPECS if enc.available(sp)]
    files = {sp: d / f"{dec}_{tag}_{sp}_{h}.npy" for sp in specs}
    if not texts: return {sp: mx.zeros((0, 1)) for sp in specs}
    if all(f.exists() for f in files.values()): return {sp: mx.load(str(f)) for sp, f in files.items()}
    acc = {sp: [] for sp in specs}
    for t in texts:
        r = enc.features_specs(dec, t, specs)
        for sp in specs: acc[sp].append(r[sp])
    out = {}
    for sp in specs:
        a = mx.stack(acc[sp]); mx.save(str(files[sp]), a); out[sp] = a
    return out
def ece(p, y, bins=10):
    if p.shape[0] == 0: return None
    conf = p.max(-1); pred = p.argmax(-1); ok = (pred == y).astype(mx.float32); tot = 0.0; n = p.shape[0]
    for b in range(bins):
        lo, hi = b / bins, (b + 1) / bins
        m = (conf > lo) & (conf <= hi) if b else (conf <= hi)
        k = int(m.sum().item())
        if k: tot += k / n * abs(float((ok * m).sum().item()) / k - float((conf * m).sum().item()) / k)
    return round(tot, 4)
def nll(z, y, T): return float(nn.losses.cross_entropy(z / T, y).mean().item())
TGRID = [round(math.exp(math.log(0.05) + i * (math.log(100) - math.log(0.05)) / 79), 4) for i in range(80)]   # 0.05-100 (10 was hit as an edge)
def fit_head(Xtr, ytr, k, cw):
    mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-5
    mx.random.seed(0); head = Head(Xtr.shape[1], k); opt = optim.AdamW(1e-3, weight_decay=1e-2)
    def lf(m, x, y): return (nn.losses.cross_entropy(m(x), y) * cw[y]).mean()
    g = nn.value_and_grad(head, lf); xn = (Xtr - mu) / sd
    for _ in range(300):
        l, gr = g(head, xn, ytr); opt.update(head, gr); mx.eval(head.parameters(), opt.state)
    head.eval(); return head, mu, sd
summary = {"layer_comparison": {}, "models": {}, "mode": "after-labels (real validation)" if AFTER_LABELS else "pre-labels (synthetic validation; SHADOW only)"}
for model_name in [m for m in ("Qwen2.5-0.5B-Instruct", "Qwen2.5-1.5B-Instruct") if (P4 / "models" / m / "config.json").exists()]:
    t0 = time.time(); enc = jd.Encoder(str(P4 / "models" / model_name)); load_s = time.time() - t0
    print(f"[{model_name}] loaded {load_s:.1f}s, {enc.n_layers} layers", flush=True)
    data = {}
    for dec, spec in jd.DECISIONS.items():
        str_, sva = rows(syn_tr, dec), rows(syn_va, dec); iva, ite = gt_rows(val, dec), gt_rows(test, dec)
        counts = {o: sum(1 for _, y in str_ if y == o) for o in spec["options"]}
        rare = [o for o, c in counts.items() if c < jd.MIN_PER_CLASS]
        opts = [o for o in spec["options"] if o not in rare] + ([jd.RARE] if rare else [])
        mp = lambda y: jd.RARE if y in rare else y
        str_ = [(t, mp(y)) for t, y in str_]; sva = [(t, mp(y)) for t, y in sva]; iva = [(i, t, mp(y)) for i, t, y in iva]
        F = {"tr": feats(enc, dec, [t for t, _ in str_], "syntr", model_name), "sva": feats(enc, dec, [t for t, _ in sva], "synva", model_name),
             "iva": feats(enc, dec, [t for _, t, _ in iva], "val", model_name), "ite": feats(enc, dec, [t for _, t, _ in ite], "test", model_name)}
        data[dec] = dict(opts=opts, rare=rare, counts=counts, str_=str_, sva=sva, iva=iva, ite=ite, F=F)
        print(f"[{model_name}] {dec}: features done ({len(str_)}/{len(sva)}/{len(iva)}/{len(ite)})", flush=True)
    comp = {}
    for sp in [s for s in SPECS if enc.available(s)]:
        comp[sp] = {}
        for dec, D in data.items():
            opts = D["opts"]; ytr = mx.array([opts.index(y) for _, y in D["str_"]]); ysv = mx.array([opts.index(y) for _, y in D["sva"]])
            cnt = [max(1, sum(1 for _, y in D["str_"] if y == o)) for o in opts]; cw = mx.array([len(D["str_"]) / (len(opts) * c) for c in cnt])
            head, mu, sd = fit_head(D["F"]["tr"][sp], ytr, len(opts), cw)
            zs = head((D["F"]["sva"][sp] - mu) / sd); ps = mx.softmax(zs, -1); pred = ps.argmax(-1)
            rec = {o: (round(float(((pred == i) * (ysv == i)).sum().item()) / max(1, int((ysv == i).sum().item())), 3) if int((ysv == i).sum().item()) else None) for i, o in enumerate(opts)}
            iacc = None
            if D["iva"]:
                yiv = mx.array([opts.index(y) for _, _, y in D["iva"]]); pi = head((D["F"]["iva"][sp] - mu) / sd).argmax(-1)
                iacc = round(float((pi == yiv).mean().item()), 3)
            comp[sp][dec] = {"syn_val_acc": round(float((pred == ysv).mean().item()), 3), "syn_val_ece_T1": ece(ps, ysv), "recall": rec,
                             "indep_val_acc": iacc, "n_syn_val": int(ysv.shape[0]), "n_indep_val": len(D["iva"])}
        comp[sp]["_mean_syn_val_acc"] = round(sum(v["syn_val_acc"] for k, v in comp[sp].items() if not k.startswith("_")) / len(data), 4)
        print(f"[{model_name}] layer {sp}: mean synthetic-val acc {comp[sp]['_mean_syn_val_acc']}", flush=True)
    if AFTER_LABELS:   # (1) layer choice on the REAL validation set (decisions with >= MIN_VAL real validation labels)
        def real_score(sp):
            v = [comp[sp][d]["indep_val_acc"] for d in data if comp[sp][d]["indep_val_acc"] is not None and comp[sp][d]["n_indep_val"] >= MIN_VAL]
            return sum(v) / len(v) if v else -1
        for sp in comp: comp[sp]["_mean_real_val_acc"] = round(real_score(sp), 4)
        best = max(comp, key=lambda sp: (comp[sp]["_mean_real_val_acc"], comp[sp]["_mean_syn_val_acc"], -SPECS.index(sp)))
    else:
        best = max(comp, key=lambda sp: (comp[sp]["_mean_syn_val_acc"], -SPECS.index(sp)))
    summary["layer_comparison"][model_name] = comp
    print(f"[{model_name}] BEST LAYER = {best}", flush=True)
    heads = {}
    for dec, D in data.items():
        opts = D["opts"]; F = D["F"]
        ytr = mx.array([opts.index(y) for _, y in D["str_"]]); ysv = mx.array([opts.index(y) for _, y in D["sva"]])
        cnt = [max(1, sum(1 for _, y in D["str_"] if y == o)) for o in opts]; cw = mx.array([len(D["str_"]) / (len(opts) * c) for c in cnt])
        head, mu, sd = fit_head(F["tr"][best], ytr, len(opts), cw)
        zs = head((F["sva"][best] - mu) / sd)
        Zv, Yv = [zs], [ysv]
        if D["iva"]:
            yiv = mx.array([opts.index(y) for _, _, y in D["iva"]]); ziv = head((F["iva"][best] - mu) / sd); Zv.append(ziv); Yv.append(yiv)
        if AFTER_LABELS and D["iva"] and len(D["iva"]) >= MIN_VAL:   # (2) temperature on the REAL validation set only
            Zv, Yv = [ziv], [yiv]
        Zc, Yc = mx.concatenate(Zv), mx.concatenate(Yv)
        T = min(TGRID, key=lambda t: nll(Zc, Yc, t))
        cal = {"syn_val_ece_before": ece(mx.softmax(zs, -1), ysv), "syn_val_ece_after": ece(mx.softmax(zs / T, -1), ysv)}
        tau, why, iacc, llm = 1.01, "", None, None
        ic = indep_counts(dec); off = [o for o in opts if o != jd.RARE and ic.get(o, 0) < MIN_CLASS_CASES]
        if len(D["iva"]) >= MIN_VAL:
            cal["indep_val_ece_before"] = ece(mx.softmax(ziv, -1), yiv); cal["indep_val_ece_after"] = ece(mx.softmax(ziv / T, -1), yiv)
            p = mx.softmax(ziv / T, -1); conf = p.max(-1); pred = p.argmax(-1); ok = (pred == yiv)
            for o in off + ([jd.RARE] if jd.RARE in opts else []): ok = ok * (pred != opts.index(o))   # off / rare answers are fallbacks
            iacc = round(float(ok.mean().item()), 3); llm = round(llm_acc(D["iva"], dec), 3)
            for c in sorted(set(round(float(v), 4) for v in conf.tolist())):
                keep = conf >= c
                if int(keep.sum().item()) >= 3 and float((ok * keep).sum().item() / keep.sum().item()) >= llm:
                    tau = c; break
        else:
            why = f"only {len(D['iva'])} independent validation labels (< {MIN_VAL}): head OFF (always the LLM) until the owner's labels"
        W1 = head.l1.weight.T / sd[:, None]; b1 = head.l1.bias - (mu / sd) @ head.l1.weight.T
        heads[dec] = {"options": opts, "T": T, "tau": tau, "off_classes": off, "rare_grouped": D["rare"], "train_counts": D["counts"],
                      "independent_case_counts": ic, "indep_val_acc": iacc, "llm_indep_val_acc": llm, "calibration": cal, "off_why": why,
                      "n_syn_train": len(D["str_"]), "n_syn_val": len(D["sva"]), "n_indep_val": len(D["iva"]), "n_test": len(D["ite"]),
                      "_w": {"W1": W1, "b1": b1, "W2": head.l2.weight.T, "b2": head.l2.bias}}
        print(f"[{model_name}] {dec}: T={T} tau={tau} off={off} cal={cal} indep_val_acc={iacc} llm={llm} {why}", flush=True)
    out = ROOT / "data" / "jev_models" / model_name; out.mkdir(parents=True, exist_ok=True)
    (out / "context.txt").write_text(jd.standing_context())
    meta = {"model": model_name, "model_dir": str(P4 / "models" / model_name), "layer": best, "authority": "live" if AFTER_LABELS else "shadow", "trained": time.strftime("%Y-%m-%d %H:%M"),
            "load_s": round(load_s, 1), "prefix_tokens": enc.prefix_tokens, "prefix_ms": round(enc.prefix_ms), "heads": {}}
    for dec, h in heads.items():
        mx.savez(str(out / f"{dec}.npz"), **h["_w"]); meta["heads"][dec] = {k: v for k, v in h.items() if k != "_w"}
    (out / "meta.json").write_text(json.dumps(meta, indent=1))
    summary["models"][model_name] = {k: v for k, v in meta.items()}
    del enc
def score(m):
    hs = [h for h in summary["models"][m]["heads"].values() if h["indep_val_acc"] is not None]
    return sum(h["indep_val_acc"] * h["n_indep_val"] for h in hs) / max(1, sum(h["n_indep_val"] for h in hs))
names = sorted(summary["models"], key=lambda m: (-round(score(m), 3), "1.5B" in m)); chosen = names[0]
summary["chosen"] = chosen; summary["scores"] = {m: round(score(m), 3) for m in names}
ART = jd.ART
if ART.exists(): shutil.rmtree(ART)
shutil.copytree(ROOT / "data" / "jev_models" / chosen, ART)
(RES / "train_summary.json").write_text(json.dumps(summary, indent=1))
print("chosen:", chosen, summary["scores"], "| both kept in data/jev_models/", flush=True)
