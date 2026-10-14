# Proposals: written only, NOT applied (2026-10-06)

Each proposal is filtered against the owner's rule: reject anything that harms structure, consistency, database design or database connections. If one is approved, it is revised first, run against the regression suite (`_research/regression/regress.py`), and applied only after the owner's review.

P1. **Move the terminal bridge outside the real folder.**
- Today `shells/agent_terminal_bridge.sh` writes CMD, OUT.log, STATUS and .run_out inside the git-tracked real folder, which is the main source of runtime git noise.
- Proposal: an env var `ODIN_BRIDGE_DIR`, defaulting to `~/Library/Application Support/Odin/agent_term`, with a fallback to the current path.
- Risk: none to structure. Needs: the owner's review of a ~5-line change.

P2. **Agent writes go through the door** (found by the LLM experiment).
- Agents' own Write tool writes relative to their working directory. In the LLM runs, some files landed at the root or outside the project's slot. Odin's audit FLAGS these as root-stray, but they are never routed at write time.
- Proposal: run each project's agents with their working directory set to `workspace/projects/<pid>/code`, plus a PreToolUse hook (the same mechanism as `readonly_hook.py`) that rewrites or denies Write paths outside the actor's own folder. This reuses `workspace_mw.route` and adds no new rules.
- Risk: low. It follows the existing owner-scope guard.

P3. **Door latency under concurrency.**
- The p50 latency per door write grows about 6x from 1 to 10 projects (30 concurrent writers), because every write opens its own database connection.
- Proposal: a small connection pool inside `workspace_mw._db()`. Same schema, same single door.
- Risk: database connection handling. It must be benchmarked and approved.

P4. **Job B: vector signal as a SECOND ranking signal for finding reusable scripts.** Proposal and benchmark design only.
- Job A (structural enforcement) stays exact, keyword and rule based, and is untouched.
- For Job B, add a MiniLM embedding of each shared-script description. Rank = keyword score + λ·cosine, with keyword hits still first when they are exact.
- Benchmark protocol: a labelled set of real capability requests → the correct shared script, with labels written by the owner. Metrics: top-1 and top-3 accuracy and MRR, keyword-only vs hybrid, with a paired test.
- NOT run now. The old labels were dropped on the owner's instruction, and inventing labels would bias the result.

P5. **RAG for the story-writing project only** (design).
- Ingest the style and reference PDFs. Split them with LangChain RecursiveCharacterTextSplitter (about 800 tokens, 100 overlap) or LlamaIndex SemanticSplitterNodeParser.
- Embed with bge-small-en-v1.5, or all-MiniLM-L6-v2 for speed, into a local Chroma (or FAISS) index.
- Retrieve the top-k (k = 20), re-rank with a cross-encoder (bge-reranker-base or ms-marco-MiniLM-L-6-v2) down to 5, and cite the chunk ids in the story notes.
- Re-index only when a PDF changes (hash check). Nothing else in Odin uses RAG.

P6. **Webhook duplicate tolerance.**
- One retried callback was delivered in a later run, which is at-least-once behaviour.
- Proposal: document that receivers must deduplicate by `request_id`, and send an `Idempotency-Key` header equal to `request_id` (Stripe style).

P7. **Router agreement.**
- The deterministic keyword dispatcher agrees with the logged lead agent on 43% of the 162 real requests. The semantic router (local qwen) was not measured, because Ollama was not part of the isolated run.
- Proposal: measure the semantic router on the same set before making any change.
