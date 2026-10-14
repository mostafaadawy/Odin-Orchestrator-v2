# paper-v1-submission: change list

**Source:** paper-v1 = `Odin-Isolated/_research/deliverables/final3` (frozen, untouched).
**This copy:** the owner-approved description corrections from `PAPER_V1_ACCURACY_CHECK.md` (2026-10-11), the layout fixes PP-8 and PP-9, and the author e-mail (named version only).

**Checks after the last rebuild:**

- **Pages:** 9 in both builds; references start on p.8; limit 10+2.
- **Undefined references:** none.
- **Numbers and results:** unchanged.
  - `05-results.tex`, all tables and all data files are byte-identical.
  - The only number changes in the PDF text are citation indices (SBERT/MiniLM moved to §6).

| # | File | Before | After |
|---|---|---|---|
| 10 | `sections/03-architecture.tex` | members work back and forth with the CTO, which re-plans and re-assigns when a result is insufficient. | members work back and forth with the CTO, which re-assigns work when QA or the audit rejects a result. |
| 5 | `sections/03-architecture.tex` | a total match points to the shared base, a near match stores only a small delta that references the base, and a different job composes a different agent. This is the same idea as delta-oriented product lines~\cite{schaefer2010delta}, applied to the operational scripts that agents run. | a total match points to the shared base, a near match is meant to store only a small delta that references the base, and a different job composes a different agent. This is the same idea as delta-oriented product lines~\cite{schaefer2010delta}, applied to the operational scripts that agents run. In the studied version, agents generated such deltas, but saving and registering them was incomplete (Section~\ref{sec:threats}). |
| 1 | `sections/03-architecture.tex` | A middleware routes each request to an existing base (reuse), a base plus delta, or new work. A deterministic keyword floor sits under a local semantic classifier so that safety-relevant routing never depends on the model alone. | Reuse is decided by meaning: the agents read the middleware's guards and a registry view of the existing capabilities, and choose an existing base (reuse), a base plus delta, or new work. Placement and safety-relevant routing stay deterministic: a keyword floor sits under an optional local classifier, so they never depend on the model alone. |
| 2 | `sections/03-architecture.tex` | When a new project is created, the middleware checks the library and the database against the project type and builds the requirement list; only missing capabilities are built. | Before a project is created, an intake interview builds its features, its team and a readiness list that marks which resources already exist and which are missing; for security projects a blueprint provisions a complete security team. |
| 3 | `sections/03-architecture.tex` | The CTO asks the owner ``we already have this under \emph{key} --- use it?''. | Agents propose reusing an existing capability, and name it, before building anything new. |
| 4 | `sections/03-architecture.tex` | and writes the file and its database row together. | and writes the file and its database row together. In the studied version, changes applied after an owner's approval were registered only by the next audit. |
| 9 | `sections/03-architecture.tex` | clients pull deltas by sequence (a missing message is a visible gap), | web and mobile clients pull deltas by sequence (a missing message is a visible gap), the desktop polls the pool, |
| 11 | `sections/03-architecture.tex` | When the owner's machine is connected it pulls by status, prioritises, processes, publishes and writes the status back. | When the owner's machine is connected it pulls the queued requests in order of arrival, processes them, publishes and writes the status back. |
| 6 | `sections/03-architecture.tex` | After a task, an audit checks that created files obey the shared/delta structure and sit in the folder declared for them, | On a timer and on demand, an audit checks that files sit in the folder declared for them, |
| 7 | `sections/03-architecture.tex` | A separate \emph{truth gate} rejects any ``done'' claim that is not backed by evidence. | A separate \emph{truth gate} rejects success claims that contradict the tools' own output; in the studied version it did not yet cover the reviewer's verdict at the end of a run (Section~\ref{sec:threats}). |
| 8 | `sections/08-related.tex` | \sys{} routes between reuse, delta and new work, with a deterministic floor under a semantic classifier~\cite{reimers2019sbert,wang2020minilm}. | \sys{}'s agents choose between reuse, delta and new work by reading a registry view, while placement stays rule-based; sentence embeddings are only proposed (Section~\ref{sec:proposals}). |
| 8b | `sections/06-discussion.tex` | add a sentence-embedding similarity as a second ranking signal next to keywords, | add a sentence-embedding similarity~\cite{reimers2019sbert,wang2020minilm} as a second ranking signal next to keywords, |
| 7b | `sections/08-related.tex` | The truth gate addresses the verification failures reported by MAST. | The truth gate addresses part of the verification failures reported by MAST. |
| 5+7 (threats) | `sections/07-threats.tex` | The registry database is a private copy restored from a read-only dump. | The registry database is a private copy restored from a read-only dump. Two weaknesses of the studied version lie outside our consistency metrics: per-project deltas were generated but not always saved and registered, and the truth gate did not yet cover the reviewer's verdict, so a run could report success while its review asked for a fix. Neither affects the reported placement, violation or task-success figures, which are taken from disk, from the system's own checks and from tests that we run ourselves. |
| PP-8 (layout only) | `sections/03-architecture.tex` | \item[P2a: start in the own folder.] … / \item[P2b: a pre-tool hook.] … (description labels wider than the label box overprinted their text) | \begin{description}[\IEEEsetlabelwidth{}] \item[] \textbf{P2a: start in the own folder.} … / \item[] \textbf{P2b: a pre-tool hook.} … (same words; run-in bold label, no overprint, no wide indent) |
| PP-8b (rendering only) | `sections/03-architecture.tex` | (\vendors and several … — the macro swallowed the space: printed "fulfilmentand" (named) / "e-mail-marketingand" (anon) | (\vendors{} and several … — prints "fulfilment and" / "e-mail-marketing and"; same words |
| PP-9 (author, named only) | `main.tex` | [e-mail to be confirmed] | mostafa\_adawy@ymail.com (affiliation still a placeholder: awaiting the owner's wording). The anonymous version is unchanged. |
| PP-9 (figures, layout only) | `make_figs.py → figs/fig_consistency.pdf, figs/fig_anchor.pdf` | Fig. 2: right y-label clipped; "dashed: after heal" touched the curve. Fig. 5: legend "publish+callback" clipped. | Fig. 2: y-label on two lines (same words), note moved to the clear lower-right area, wider panel gap. Fig. 5: legend in 2 columns, centred. Same data: input data files are byte-identical to paper-v1, and every plotted value (lines, error bars, bars) hashes identically for all 4 figures under the old and new scripts. |

## Proof that the regenerated figures plot the same data

**Input data files** (SHA-256; paper-v1 = submission copy):

- `results/anchor_exp.json`: `eda664d0fe8749de62a5adca8e62b6f66f6c6f1182b4434905244ca9a9a507a1` → identical
- `results/consistency_env_start.json`: `2ba35b41802489eb9d9f576c5c8b47dbd94419eb90848c47a9da7a3b1aeb2503` → identical
- `results/consistency_trials.jsonl`: `01ad0d813cffd4f5db313b519091227948f3f52a3261880bd527d1e963329db9` → identical
- `results/llm_summary.json`: `7949a0be1f6be1a2b8aa9b859dda22dfb3d2e463ffc3185ba3d86a5dcaee230f` → identical
- `results/summary.json`: `05a75db00af3c266627cf730db91bdcd007a56fa9e47593004331b7b3425354c` → identical

**Plotted values** (SHA-256 of every line, error bar and bar segment drawn, captured while the figure was saved, original script vs layout-only script):

- `fig_consistency.pdf`: `adbbf5c33180e5ba58c9e4b06d175a1fb8afa3c2c24bde6e4d54b20d7b4ffae9` → identical
- `fig_latency.pdf`: `d5a1f06a1b427eb5b3bff6faffa944b325df1c01a3034f742d1a7c211a45f2a7` → identical
- `fig_anchor.pdf`: `44be51235cc6632db788deedcabc349fc1a6c300e8431aecde82b5a4170c649e` → identical
- `fig_rq2_p2.pdf`: `bf8e89a7b2dc45583ff0982f13a222315a2b6260e424f9c5a9f02f414cc2afb0` → identical

**Only `fig_consistency.pdf` (Fig. 2) and `fig_anchor.pdf` (Fig. 5) were replaced.** `fig_latency.pdf` and `fig_rq2_p2.pdf` are the paper-v1 files, unchanged.
The script change (`make_figs.py`) is layout only:
- Fig. 2: the y-label is split over two lines (same words), the note "dashed: after heal" is moved to the clear lower-right area, and the gap between the two panels is wider;
- Fig. 5: the legend has 2 columns and is centred.

## Visual check (every page of both PDFs, rendered as images)

**Fixed:**
- the P2a/P2b label overprint (p.3);
- the missing space after the vendor list (p.2);
- the clipped Fig. 2 label and the overlapping note (p.5);
- the clipped Fig. 5 legend (p.7).

**Still open:** the named PDF affiliation reads "[Affiliation to be confirmed by the author]" until you give the wording. The anonymous PDF stays anonymous.
**No other overlapping or clipped text** on any page.
