# Jev timing diagnosis (cutover condition A) — from existing logs only, $0

Source: the real-scenario runs (2026-10-13, isolated copy) + the Claude-call ledger (`claude_calls.jsonl`: start/end of
every LLM call). Each project run was split into its LLM calls (alignment check: LLM time = run time − 0.5 s for every
run). Script: `research/phase4/timing_diag.py <Odin-Consolidated>`.

## Per-stage breakdown, project runs (all available runs: Normal 9 = 3 reps × 3 projects, Jev 6 = 2 reps × 3)

| Stage | Normal mean / median s | Jev mean / median s |
|---|---|---|
| Before the agent (mode decision + routing/plan) | 17.5 / 16.3 | 10.1 / 10.2 |
| — of which mode decision | one LLM call, ~5–20 s | local decider 42–61 ms (used) |
| Agent step (the specialist's own work) | 113.6 / 118.4 (9.7 / 11 tool turns) | 119.8 / 123.7 (11 / 13.5 turns) |
| Review / answer | 26.4 / 20.7 | 31.5 / 30.3 |
| Non-LLM time (Odin's own code, waits) | 0.5–0.9 | 0.5–0.7 |
| **Total** | **154.5 / 154.7** | **158.3 / 171.1** |

## Where the "+47 s" came from

* It was the median of only the 2 paired repetitions (Normal rep 3 was not in that table). With every run, the gap is
  **+3.8 s mean** — inside the noise.
* Same path chosen: identical mode (direct), plan (1 step) and agent in every pair.
* Jev **saves** ~7 s before the agent (no mode-classifier LLM call).
* The difference is **agent variance**: the same agent on the same question took 49–217 s and 3–19 tool turns within
  the SAME mode (e.g. Email, Normal: 81 / 118 / 217 s). Time follows the number of tool turns, not the mode.
* Not shadow overhead and not model load in project runs (decider 42–61 ms there).

## Overhead that Jev DID add — fixed before cutover

1. **Shadow mode ran the decider on the request path** (~40 ms per chat turn, answer never used). Now it runs on a
   background worker with the same log record: request path 0.3 ms (measured on the Mac with the real model).
2. **Cold start**: the first decision after start paid ~1.5 s to load the model and context cache. Now pre-warmed in
   the background at brain start and when Jev is switched on: first real decision 72 ms.

Tests: p4e 16 "shadow adds no latency" and 17 "pre-warm" added; the suite re-run is in `_v2/results/after_jevfix`.

## Honest conclusion

Per decision Jev is ~200× faster (≈45 ms vs 5–20 s). End-to-end runs are dominated by agent work and its variance, so
with n = 6–9 runs there is no measurable end-to-end gain yet; Jev is not slower once the noise is accounted for.
In shadow (until your labels) Jev cannot speed anything up, by design.
