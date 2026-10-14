"""Paper v2 (DRAFT): every number, table and figure is generated from the result files in data/ — nothing is typed by hand.
All outputs are PROVISIONAL, pending the owner's human labels (re-generated after after_labels.sh).
usage: python3 make_figs.py   -> figs/*.pdf, tables/*.tex, numbers.tex"""
import json, pathlib, glob
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

H = pathlib.Path(__file__).parent; D = H / "data"; F = H / "figs"; T = H / "tables"
F.mkdir(exist_ok=True); T.mkdir(exist_ok=True)
OI = {"blue": "#0072B2", "orange": "#E69F00", "verm": "#D55E00", "green": "#009E73", "sky": "#56B4E9", "grey": "#555555"}
plt.rcParams.update({"font.size": 7.5, "font.family": "serif", "axes.spines.top": False, "axes.spines.right": False,
                     "axes.linewidth": 0.6, "xtick.major.width": 0.6, "ytick.major.width": 0.6})
M5, M15 = "Qwen2.5-0.5B-Instruct", "Qwen2.5-1.5B-Instruct"
tr = json.loads((D / "train_summary.json").read_text())
H2 = {k: json.loads((D / f"h2h_summary_{k}.json").read_text()) for k in
      (f"strict_{M5}", f"strict_{M15}", f"ext_{M5}", f"ext_{M15}")}
PROV = "PROVISIONAL -- pending human labels"
def pct(x): return "--" if x is None else f"{100 * x:.1f}"
def ci(c): return "--" if not c or c[0] is None else f"[{100 * c[0]:.1f}, {100 * c[1]:.1f}]"
def pv(p): return "--" if p is None else ("$<$0.001" if p < 0.001 else f"{p:.3f}")
DECN = {"D1_mode": "Mode (direct / orchestrate)", "D2_agent": "Specialist", "D2_action": "Read / change", "D4_qa": "QA gate", "D9_nature": "Agent nature"}
DECS = ["D1_mode", "D2_agent", "D2_action", "D4_qa", "D9_nature"]

# ---------------- numbers.tex : macros used in the text ----------------
s5, s15 = H2[f"strict_{M5}"]["per_decision"], H2[f"strict_{M15}"]["per_decision"]
e5, e15 = H2[f"ext_{M5}"]["per_decision"], H2[f"ext_{M15}"]["per_decision"]
mods = tr["models"]
nums = {
    "nTrainSyn": mods[M5]["heads"]["D2_action"]["n_syn_train"],
    "nStrictDtwo": s5["D2_action"]["stats_vs_production_llm"]["n_cases"],
    "nExtDtwo": e5["D2_action"]["stats_vs_production_llm"]["n_cases"],
    "nDone": s5["D1_mode"]["stats_vs_production_llm"]["n_cases"],
    "layerFive": mods[M5]["layer"], "layerFifteen": mods[M15]["layer"],
    "prefixTokens": H2[f"strict_{M5}"]["prep"]["prefix_tokens"], "prefixMsFive": H2[f"strict_{M5}"]["prep"]["prefix_prep_ms"],
    "loadSFive": H2[f"strict_{M5}"]["prep"]["model_load_s"],
    "dOneLlmMed": round(s5["D1_mode"]["llm_ms_median"] / 1000, 1), "dOneJevMed": s5["D1_mode"]["jev_ms_median"],
    "dTwoRouterMed": s5["D2_action"]["llm_ms_median"], "dTwoJevMed": s5["D2_action"]["jev_ms_median"],
    "dTwoClaudeMed": round(s5["D2_action"]["claude_ms_median"] / 1000, 1),
    "dOneUsd": s5["D1_mode"]["llm_usd"], "dTwoClaudeUsd": s5["D2_action"]["claude_usd_per_run"],
}
def mac(k): return "".join(c for c in k if c.isalpha())
(T / "numbers.tex").write_text("\n".join(f"\\newcommand{{\\{mac(k)}}}{{{str(v).replace('_', ' ')}}}" for k, v in nums.items()) + "\n")

# ---------------- Table: layer comparison ----------------
SPECS = ["L12", "L16", "L20", "L24", "L28", "mean16-24", "final"]
lab = {"L12": "12", "L16": "16", "L20": "20", "L24": "24", "L28": "28", "mean16-24": "mean 16--24", "final": "final (normed)"}
rows = []
for sp in SPECS:
    r = [lab[sp]]
    for m in (M5, M15):
        c = tr["layer_comparison"][m].get(sp)
        if not c: r += ["n/a", "n/a", "n/a"]; continue
        best = " $\\star$" if mods[m]["layer"] == sp else ""
        r += [f"{100 * c['_mean_syn_val_acc']:.1f}{best}", f"{100 * c['D2_action']['syn_val_acc']:.1f}", f"{c['D2_action']['syn_val_ece_T1']:.3f}"]
    rows.append(" & ".join(r) + r" \\")
(T / "layers.tex").write_text(r"""\begin{table}[t]\centering\scriptsize
\caption{Layer comparison on the synthetic held-out validation split (15\% of the generated data). Mean = mean accuracy over the five decisions; $\star$ = kept. \textbf{""" + PROV + r"""}.}
\label{tab:layers}\setlength{\tabcolsep}{3.5pt}
\begin{tabular}{lrrr rrr}\toprule
 & \multicolumn{3}{c}{Qwen2.5-0.5B (24 layers)} & \multicolumn{3}{c}{Qwen2.5-1.5B (28 layers)}\\
\cmidrule(lr){2-4}\cmidrule(lr){5-7}
Layer & Mean & R/C acc & R/C ECE & Mean & R/C acc & R/C ECE\\\midrule
""" + "\n".join(rows) + r"""
\bottomrule\end{tabular}\end{table}
""")

# ---------------- Table: per-class recall at the kept layer ----------------
rr = []
for d in DECS:
    for m, tag in ((M5, "0.5B"), (M15, "1.5B")):
        rec = tr["layer_comparison"][m][mods[m]["layer"]][d]["recall"]
        rr.append(f"{DECN[d]} & {tag} & " + ", ".join(f"{k.replace('&', chr(92) + '&')} {100 * v:.0f}" for k, v in rec.items() if v is not None) + r" \\")
(T / "recall.tex").write_text(r"""\begin{table}[t]\centering\scriptsize
\caption{Per-class recall (\%) at the kept layer, synthetic held-out validation split. \textbf{""" + PROV + r"""}.}
\label{tab:recall}\setlength{\tabcolsep}{3pt}
\begin{tabular}{l l p{4.6cm}}\toprule Decision & Model & Recall per class\\\midrule
""" + "\n".join(rr) + r"""
\bottomrule\end{tabular}\end{table}
""")

# ---------------- Table: head-to-head with CIs and McNemar ----------------
def h2h_rows(P, tag):
    out = []
    for d in ("D1_mode", "D2_action", "D4_qa"):
        v = P[d]; a = v["stats_vs_production_llm"]
        out.append(f"{DECN[d]} & {tag} & {a['n_cases']} & {pct(a['other_acc'])} {ci(a['other_ci95'])} & {pct(a['jev_acc'])} {ci(a['jev_ci95'])} & "
                   f"{a['jev_only_right']}/{a['other_only_right']} & {pv(a['mcnemar_p'])} & {100 * v['fallback_rate']:.0f} \\\\")
    return out
lines = h2h_rows(s5, "0.5B") + h2h_rows(s15, "1.5B")
(T / "h2h.tex").write_text(r"""\begin{table*}[t]\centering\scriptsize
\caption{Head-to-head on the held-out test split (strict independent truth), 3 repetitions. A case counts as correct when it is correct in the majority of its repetitions; 95\% Wilson intervals; exact McNemar test on the discordant cases ($b$ = only Jev right, $c$ = only the production LLM path right). Mode and QA gate: the production path is Claude; read/change: the production path is the local semantic router. \textbf{""" + PROV + r"""}.}
\label{tab:h2h}
\begin{tabular}{l l r l l r r r}\toprule
Decision & Jev model & $n$ & Production path acc.\ \% [95\% CI] & Jev acc.\ \% [95\% CI] & $b/c$ & McNemar $p$ & Fallback \%\\\midrule
""" + "\n".join(lines) + r"""
\bottomrule\end{tabular}\end{table*}
""")

# ---------------- Table: read/change vs Claude, strict and extended ----------------
cl = []
for P, set_ in ((s5, "strict"), (e5, "strict+extended")):
    pass
for (P5, P15, set_) in ((s5, s15, "strict"), (e5, e15, "strict + extended")):
    for P, tag in ((P5, "0.5B"), (P15, "1.5B")):
        v = P["D2_action"]; c = v["stats_vs_claude"]; a = v["stats_vs_production_llm"]
        cl.append(f"{set_} & {tag} & {c['n_cases']} & {pct(a['other_acc'])} & {pct(c['other_acc'])} {ci(c['other_ci95'])} & {pct(c['jev_acc'])} {ci(c['jev_ci95'])} & "
                  f"{c['jev_only_right']}/{c['other_only_right']} & {pv(c['mcnemar_p'])} \\\\")
(T / "claude.tex").write_text(r"""\begin{table*}[t]\centering\scriptsize
\caption{Read/change: Jev against a Claude classifier (plan login, same standing context and definition) and the production router. Strict = log-outcome truth with owner acceptance; extended = additional log rules for this decision only, lower confidence (Section~\ref{sec:truth}). McNemar against Claude. \textbf{""" + PROV + r"""}.}
\label{tab:claude}
\begin{tabular}{l l r r l l r r}\toprule
Truth set & Jev & $n$ & Router \% & Claude \% [95\% CI] & Jev \% [95\% CI] & $b/c$ & McNemar $p$\\\midrule
""" + "\n".join(cl) + r"""
\bottomrule\end{tabular}\end{table*}
""")

# ---------------- Table: calibration ----------------
def f3(x): return '--' if x is None else f'{x:.3f}'
cal = []
for m, tag in ((M5, "0.5B"), (M15, "1.5B")):
    for d in DECS:
        h = mods[m]["heads"][d]; c = h["calibration"]; P = H2[f"strict_{m}"]["per_decision"].get(d, {})
        state = "on" if h["tau"] <= 1.0 else "off"
        cal.append(f"{tag} & {DECN[d]} & {h['T']:.2f} & {c.get('syn_val_ece_before', 0):.3f} & {c.get('syn_val_ece_after', 0):.3f} & "
                   f"{f3(P.get('ece_decider_before_T')) if P else '--'} & {f3(P.get('ece_decider_after_T')) if P else '--'} & {state} \\\\")
(T / "calib.tex").write_text(r"""\begin{table}[t]\centering\scriptsize
\caption{Temperature scaling: ECE before ($T{=}1$) and after, on the synthetic validation split and on the real held-out test split. Target $<0.05$. \emph{off} = head disabled (fewer than 5 independent validation labels): the LLM decides. \textbf{""" + PROV + r"""}.}
\label{tab:calib}\setlength{\tabcolsep}{2.5pt}
\begin{tabular}{l l r rr rr l}\toprule
 & & & \multicolumn{2}{c}{Synthetic val} & \multicolumn{2}{c}{Real test} & \\
\cmidrule(lr){4-5}\cmidrule(lr){6-7}
Model & Decision & $T$ & before & after & before & after & Head\\\midrule
""" + "\n".join(cal) + r"""
\bottomrule\end{tabular}\end{table}
""")

# ---------------- Figure: layers ----------------
fig, ax = plt.subplots(figsize=(3.4, 1.7))
xs = range(len(SPECS)); w = 0.38
for i, (m, col, tag) in enumerate(((M5, OI["blue"], "0.5B"), (M15, OI["orange"], "1.5B"))):
    ys = [tr["layer_comparison"][m][sp]["_mean_syn_val_acc"] * 100 if sp in tr["layer_comparison"][m] else 0 for sp in SPECS]
    ax.bar([x + (i - 0.5) * w for x in xs], ys, w, color=col, label=tag)
ax.set_xticks(list(xs)); ax.set_xticklabels([lab[s].replace(" (normed)", "") for s in SPECS], rotation=0, fontsize=6)
ax.set_ylim(88, 95); ax.set_ylabel("mean val. acc. (%)"); ax.legend(frameon=False, fontsize=6, ncol=2, loc="upper left")
ax.set_title("PROVISIONAL", fontsize=6, color=OI["verm"], loc="right")
fig.tight_layout(); fig.savefig(F / "layers.pdf"); plt.close(fig)

# ---------------- Figure: read/change accuracy with CIs ----------------
fig, ax = plt.subplots(figsize=(3.4, 2.2))
items = []
for P5, P15, set_ in ((s5, s15, "strict"), (e5, e15, "strict+ext")):
    a5 = P5["D2_action"]; c5 = a5["stats_vs_claude"]; r5 = a5["stats_vs_production_llm"]; a15 = P15["D2_action"]["stats_vs_production_llm"]
    items += [(f"router\n{set_}", r5["other_acc"], r5["other_ci95"], OI["grey"]), (f"Claude\n{set_}", c5["other_acc"], c5["other_ci95"], OI["green"]),
              (f"Jev 0.5B\n{set_}", r5["jev_acc"], r5["jev_ci95"], OI["blue"]), (f"Jev 1.5B\n{set_}", a15["jev_acc"], a15["jev_ci95"], OI["orange"])]
for i, (n, y, c, col) in enumerate(items):
    ax.errorbar(i, y * 100, yerr=[[y * 100 - c[0] * 100], [c[1] * 100 - y * 100]], fmt="o", color=col, ms=3.5, capsize=2, lw=0.8)
ax.set_xticks(range(len(items))); ax.set_xticklabels([n.replace("\n", " ") for n, *_ in items], fontsize=5, rotation=35, ha="right")
ax.set_ylabel("accuracy (%), 95% CI"); ax.set_ylim(50, 100)
ax.set_title("Read/change - PROVISIONAL (no difference significant)", fontsize=6, color=OI["verm"])
fig.tight_layout(); fig.savefig(F / "rc_acc.pdf"); plt.close(fig)

# ---------------- Figure: latency ----------------
fig, ax = plt.subplots(figsize=(3.4, 1.6))
bars = [("Mode: Claude", s5["D1_mode"]["llm_ms_median"], OI["green"]), ("Mode: Jev 0.5B", s5["D1_mode"]["jev_ms_median"], OI["blue"]),
        ("R/C: router", s5["D2_action"]["llm_ms_median"], OI["grey"]), ("R/C: Claude", s5["D2_action"]["claude_ms_median"], OI["green"]),
        ("R/C: Jev 0.5B", s5["D2_action"]["jev_ms_median"], OI["blue"]), ("R/C: Jev 1.5B", s15["D2_action"]["jev_ms_median"], OI["orange"])]
ax.barh(range(len(bars)), [b[1] for b in bars], color=[b[2] for b in bars]); ax.set_xscale("log")
ax.set_yticks(range(len(bars))); ax.set_yticklabels([b[0] for b in bars], fontsize=6); ax.invert_yaxis()
for i, b in enumerate(bars): ax.text(b[1] * 1.1, i, f"{b[1]:,} ms", va="center", fontsize=5.5)
ax.set_xlabel("median decision time per case (ms, log)"); ax.set_title("PROVISIONAL", fontsize=6, color=OI["verm"], loc="right")
fig.tight_layout(); fig.savefig(F / "latency.pdf"); plt.close(fig)

# ---------------- Real-scenario table (filled when the runs exist) ----------------
sc = sorted(glob.glob(str(D / "scenarios" / "*_r*.json")))
REPS = []
if sc:
    import statistics
    R = [r for f in sc for r in json.loads(pathlib.Path(f).read_text()) if not r.get("limit_seen")]
    # paired design: keep only repetitions that are COMPLETE in both modes (a plan-limit stop leaves a partial rep out)
    def complete(mode, rep):
        z = [r for r in R if r["mode"] == mode and r["rep"] == rep]
        return len([r for r in z if r["kind"] == "chat"]) == 6 and len([r for r in z if r["kind"] == "project_run"]) == 3
    REPS = sorted(r for r in {x["rep"] for x in R} if complete("normal", r) and complete("jev", r))
    R = [r for r in R if r["rep"] in REPS]
    def agg(kind, mode):
        z = [r for r in R if r["kind"] == kind and r["mode"] == mode and not r.get("limit_seen")]
        if not z: return None
        reps = sorted({r["rep"] for r in z})
        acc = None
        if kind == "project_run":
            acc = sum(r["inferred_mode"] == r["truth_D1_mode"] for r in z) / len(z)
        used = [d for r in z for d in r["jev_decisions"]]
        return {"n": len(z), "reps": len(reps), "sec_med": statistics.median(r["seconds"] for r in z), "sec_mean": statistics.mean(r["seconds"] for r in z),
                "usd": sum(r["usage_usd"] for r in z) / max(1, len(reps)), "err": sum(r["error"] for r in z), "acc": acc,
                "jev_used": sum(1 for d in used if d.get("used")), "jev_fb": sum(1 for d in used if d.get("fallback"))}
    lines = []
    for kind, name in (("chat", "Chat turn (routing)"), ("project_run", "Project run (mode)")):
        for mode in ("normal", "jev"):
            a = agg(kind, mode)
            if a: lines.append(f"{name} & {mode} & {a['n']} & {a['reps']} & {a['sec_med']:.1f} & {a['sec_mean']:.1f} & "
                               f"{'--' if a['acc'] is None else pct(a['acc'])} & {a['jev_used']}/{a['jev_fb']} & {a['usd']:.2f} & {a['err']} \\\\")
    body = "\n".join(lines)
else:
    body = r"\multicolumn{10}{c}{\emph{runs in progress -- table regenerated when they finish}}\\"
(T / "scenarios.tex").write_text(r"""\begin{table*}[t]\centering\scriptsize
\caption{Real Odin scenarios on the isolated copy (same HTTP entry points as the desktop app), Normal vs.\ Jev mode, """ + str(len(REPS) if sc else 0) + r""" complete paired repetitions (paused by the owner; one more run follows the re-measure on human labels). Jev used/fallback = decisions answered locally / handed to the LLM. Usage = reported plan usage per repetition, not charged. \textbf{""" + PROV + r"""}.}
\label{tab:scen}
\begin{tabular}{l l r r r r r r r r}\toprule
Scenario & Mode & runs & reps & median s & mean s & mode acc.\ \% & Jev used/fallback & usage \$ & errors\\\midrule
""" + body + r"""
\bottomrule\end{tabular}\end{table*}
""")
print("ok:", sorted(p.name for p in F.iterdir()), sorted(p.name for p in T.iterdir()))
