import json, statistics as st, collections, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
R = "/home/claude/paper2/results/"; F = "/home/claude/paper2/figs/"
BLUE, ORANGE, VERM, GREEN, GREY = "#0072B2", "#E69F00", "#D55E00", "#009E73", "#555555"
plt.rcParams.update({"font.size": 8, "font.family": "sans-serif", "axes.spines.top": False, "axes.spines.right": False})
rows = [json.loads(l) for l in open(R + "consistency_trials.jsonl") if l.strip()]
g = collections.defaultdict(list)
for r in rows: g[(r["N"], r["cond"])].append(r)
Ns = [1, 2, 5, 10]
def ms(c, f): return [st.mean(f(x) for x in g[(n, c)]) for n in Ns], [st.pstdev(f(x) for x in g[(n, c)]) for n in Ns]
fig, ax = plt.subplots(1, 2, figsize=(3.5, 1.7))
for c, col, lab in (("bypass", VERM, "no door"), ("door", BLUE, "door")):
    m, s = ms(c, lambda x: x["violation_rate"]); ax[0].errorbar(Ns, m, yerr=s, color=col, marker="o", ms=3, lw=1.2, capsize=2, label=lab)
    m2, s2 = ms(c, lambda x: x["residual_rate_after_heal"]); ax[0].plot(Ns, m2, color=col, ls="--", lw=1, marker="x", ms=3)
    m3, s3 = ms(c, lambda x: x["cross_project_landed"] / x["writes"]); ax[1].errorbar(Ns, m3, yerr=s3, color=col, marker="o", ms=3, lw=1.2, capsize=2, label=lab)
ax[0].set_xlabel("concurrent projects"); ax[0].set_ylabel("violations / write"); ax[0].set_xticks(Ns); ax[0].set_ylim(-0.02, 0.4)
ax[0].text(10, 0.045, "dashed: after heal", fontsize=6, color=GREY, ha="right")
ax[1].set_xlabel("concurrent projects"); ax[1].set_ylabel("cross-project\nwrites / write"); ax[1].set_xticks(Ns); ax[1].legend(frameon=False, fontsize=6)
fig.tight_layout(w_pad=1.2); fig.savefig(F + "fig_consistency.pdf"); plt.close(fig)
# latency ratio (door per-write p50 relative to N=1) and audit/heal
fig, ax = plt.subplots(figsize=(1.9, 1.6))
base = st.mean(x["lat_p50_ms"] for x in g[(1, "door")])
ax.plot(Ns, [st.mean(x["lat_p50_ms"] for x in g[(n, "door")]) / base for n in Ns], color=BLUE, marker="o", ms=3, lw=1.2)
ax.set_xlabel("concurrent projects"); ax.set_ylabel("door write latency\n(p50, ratio to N=1)"); ax.set_xticks(Ns)
fig.tight_layout(); fig.savefig(F + "fig_latency.pdf"); plt.close(fig)
# anchor stage shares
a = json.load(open(R + "anchor_exp.json"))
cats = [("in->queued", "submit"), ("queued->pulled", "wait for pull"), ("pulled->processed", "process"), ("processed->callback", "publish+callback")]
def shares(r):
    s = dict(r["stage_share_of_end_to_end"]); s["processed->callback"] = s.pop("processed->published", 0) + s.pop("published->callback", 0); return s
conds = [("50 req, 1 client, 0% fail", lambda r: r["M"] == 50), ("200 req, 4 clients, 0% fail", lambda r: r["M"] == 200 and r["webhook_fail_rate_injected"] == 0),
         ("200 req, 4 clients, 20% fail", lambda r: r["M"] == 200 and r["webhook_fail_rate_injected"] > 0)]
fig, ax = plt.subplots(figsize=(3.5, 1.35))
cols = [GREY, ORANGE, GREEN, BLUE]
for i, (lab, f) in enumerate(conds):
    rs = [shares(r) for r in a["queue"] if f(r)]; left = 0
    for j, (k, nm) in enumerate(cats):
        v = st.mean(max(0, r[k]) for r in rs); ax.barh(i, v, left=left, color=cols[j], label=nm if i == 0 else None); left += v
ax.set_yticks(range(3)); ax.set_yticklabels([c[0] for c in conds], fontsize=6); ax.set_xlabel("share of end-to-end time"); ax.set_xlim(0, 1)
ax.legend(ncol=2, fontsize=5.5, frameon=False, loc="lower center", bbox_to_anchor=(0.5, 1.0))
fig.tight_layout(); fig.savefig(F + "fig_anchor.pdf"); plt.close(fig)
print("figs ok")

# RQ2 before/after P2
S = json.load(open(R + "summary.json"))["rq2"]
fig, ax = plt.subplots(1, 2, figsize=(3.5, 1.6))
for ph, col, lab in (("before", VERM, "before P2"), ("after", BLUE, "after P2")):
    ax[0].plot(Ns, [S[ph][str(n)]["in_code_slot_ratio"] for n in Ns], color=col, marker="o", ms=3, lw=1.2, label=lab)
    ax[1].plot(Ns, [S[ph][str(n)]["outside_files_per_task"] for n in Ns], color=col, marker="o", ms=3, lw=1.2, label=lab)
ax[0].set_xlabel("concurrent projects"); ax[0].set_ylabel("tasks in own code slot"); ax[0].set_xticks(Ns); ax[0].set_ylim(-0.05, 1.05)
ax[1].set_xlabel("concurrent projects"); ax[1].set_ylabel("outside files / task"); ax[1].set_xticks(Ns); ax[1].legend(frameon=False, fontsize=6)
fig.tight_layout(); fig.savefig(F + "fig_rq2_p2.pdf"); plt.close(fig)
print("rq2 fig ok")
