# Phase 4a — decision points (P4a-1) and CLOSED vs OPEN (P4a-3)
Source: Odin-Consolidated at `phase3-done` candidate (2026-10-12). Read-only inventory. "Fixed-option" = the answer is one choice from a known list.

| # | Decision | Where (file:line) | Options | Decided by today | P4a-3 |
|---|---|---|---|---|---|
| D1 | Request mode: answer directly or run the team | server/intent.py:70 (`classify_request`), used at server/api_v2.py:2482 | direct / orchestrate (+ forbidden actions) | LLM (Claude, plan) + rules | **CLOSED** |
| D2 | Which specialist owns a chat request, and read vs change | orchestrator/semantic_router.py:48, called by orchestrator/dispatcher.py:188 (`route`) → api_v2.py:4237, app.py:222/237/322, scheduler.py:332 | 7 specialists × read/change | local Ollama LLM + keyword rules | **CLOSED** |
| D3 | Which existing member fixes a QA failure | server/api_v2.py:2808–2815 (`qa_gate`) | one of the project's members | LLM | **CLOSED** (member choice; the fix text stays LLM) |
| D4 | Recommend adding QA to a project | server/api_v2.py:2442–2447 | yes / no | LLM | **CLOSED** |
| D5 | CTO review verdict of a step | server/api_v2.py:3358 (`qa_gate` review) | PASSED / NOT_DONE / WAITING_FOR_APPROVAL | LLM + fixed VERDICT field (G1) | **CLOSED**, safety gate: G1 checks always apply on top; low confidence → LLM |
| D6 | Audit verdict on a claim | server/audit.py:193 (`engine_audit`) | VERIFIED / UNVERIFIED / FAKE | LLM | **CLOSED**, safety gate (same rule as D5) |
| D7 | Pipeline: which member does each step, and the order | server/projects.py:1192 (`_meta`) | members of the team; order | LLM (whole plan incl. free-text mandates) | member/order **CLOSED**; mandates **OPEN** (generated text) |
| D8 | Intake: ask vs propose, and which roles staff the team | server/projects.py:1350 (`_intake`, via `_engine_research` = web search allowed) | ask / propose / digest; roles from the fixed technical + operational lists | LLM with web search | **OPEN** (uses search/research) — the role pick is a closed sub-decision only when the brief needs no research |
| D9 | New agent: technical or operational | server/agents_registry.py:485 (`suggest_agent`) + keyword rule above it | technical / operational | LLM, keyword fallback | **CLOSED** (name/description text stays LLM) |
| D10 | Reuse / strengthen / create an agent for a needed platform | server/strengthen.py (`propose_from_readiness`, `pick_agent`) from intake readiness | reuse existing / strengthen (add skill, owner approves) / create new | rules on the LLM's readiness list | **CLOSED** |
| D11 | Which shared script serves a need | server/workspace_mw.py `request_capability` (name substring), server/directions.py `lookup` (F-06 token weighting) | the existing shared/owner files | rules (no LLM) | **CLOSED** — baseline = today's rules |
| D12 | Shared base + delta vs separate scripts | server/workspace_mw.py `share_decision` (F-11) | shared+delta / separate / review | owner's 50% rule (deterministic) | **CLOSED** — stays the owner's rule; the decider must NOT replace it |
| D13 | Where a file belongs in a project (slot) | server/workspace_mw.py `route` (scope_hook.py:128, workspace_audit.py:526) | code / deploy / tests / files … | rules | **CLOSED** — deterministic rule, kept |
| D14 | Deploy plan: migration type and targets | server/deploy_runner.py:179 (`ai_decide_deploy`) | migration none / new / reset; target subset | LLM | **CLOSED** for migration (reset only if the brief authorizes it — rule stays on top); paths are extracted text |
| D15 | Request priority | not found — Anchor queue is first-in-first-out (server/anchor_queue.py:161, :211 `ORDER BY created`); scheduler runs by time | — | none | no decision point exists today; noted, not invented |

OPEN (always the LLM, not decider candidates): deploy failure diagnosis (deploy_agent.py:128), plan coverage gaps (projects.py:1257), sync/deploy proposals (projects.py:1061/1076), meeting / Zoom reports (meeting_api.py, zoom_pipeline_run.py), requirements extraction (main_task.py:58), all chat answers.

Existing evidence for D2: the regression already measures the router against the logged lead specialist: `R6.router_agrees_with_logged_lead` = 0.43 and deterministic = 1.0 (logged lead is NOT ground truth — a reviewed label set is needed, P4a-2 / P4d-2).

## P4b-1 — machine
Apple M4 Pro, 12 cores, 24 GB unified memory, macOS 26.5.2, 63 GB free disk. MLX and PyTorch are not installed yet (free, pip). Ollama has quantized Qwen 2.5 7B/14B (serving only — never trained, P4b-3).

P4b-1 confirmed 2026-10-12: MLX 0.29.3 installed in the copy venv; a training step runs on the GPU (Device gpu,0), loss 1.21 → 0.88 on a toy head. PyTorch/MPS not needed.
