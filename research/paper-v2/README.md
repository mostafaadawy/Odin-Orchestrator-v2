# Paper v2 — DRAFT (provisional)

Every number, table and figure is PROVISIONAL, pending the owner's human labels. Paper v1 is a separate, frozen document and is not changed.

- `make_figs.py` regenerates `figs/` and `tables/` from the result files in `data/` (copied from `Odin-Consolidated/_research/phase4/results/`); nothing is typed by hand.
- Build: `python3 make_figs.py && latexmk -pdf main.tex` (IEEEtran).
- After the owner's labels: run `_research/phase4/after_labels.sh`, copy the new result files into `data/`, regenerate, rebuild.
