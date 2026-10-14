# Rescued from Odin-Keel-Research (2026-10-06)

Only these 3 items were kept. All results, runs, logs, the old harness, the regression suite, the delta guard and its policy and manifests, the patches, the defects list, the old PDFs, the Word file and the cover note were left out.

1. `paper/latex-source.zip`: the old paper's sources. Reused for related work and references only.
2. `router/base_descriptions.json`: the base-script descriptions.
3. `testset/`: the raw anonymised extraction of real past requests, with no labels and no splits.
   - `raw_requests_anon.jsonl` has 162 owner-written requests, after exact dedupe and near-dedupe (difflib ratio of at least 0.90).
   - Each row has these fields: cid, ts, scope, source, dups, route_lead, route_approval, text.
   - `route_*` is Odin's own logged routing (lead agent and approval flag), joined by timestamp within ±180 s. It is not a label.
   - `extract.py` is the original extraction script. It reads `workspace/history/routing.jsonl` and `workspace/chats/**/*.json`, and its paths must be pointed at the new copy before it is rerun.
   - `anonymise.py` holds the anonymisation rules copied verbatim from the old `build.py`. These cover project, client and company names, user and home paths, vendors, IPs, emails and long ids.
   - `extract_stats.json` gives the stage counts:
     - S0: 390 routing events (no request text).
     - S1: 499 user messages, of which 222 were written by the owner.
     - S3: 165 left after exact dedupe.
     - S4: 162 left after near-dedupe.
   - The routing log stores no request text, so the texts come from the chat archive.
