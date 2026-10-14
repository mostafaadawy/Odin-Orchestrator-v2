# Odin‑Orchestrator vs. real multi‑agent systems — an honest gap analysis

*Comparison of your code against (a) how Anthropic and the field actually build strong multi‑agent
systems, and (b) how a single strong agent (Claude here in Cowork) works. No trivial reassurance —
the real gaps, with evidence from your own code.*

---

## 1. The short, honest verdict

Two things are true at once, and you sensed both:

1. **Your architecture is the right, industry‑standard pattern.** A Project CTO that plans and
   delegates to specialist members, with a QA/evaluator gate, is exactly the *orchestrator‑workers +
   evaluator‑optimizer* pattern Anthropic recommends. You did not invent something naive.

2. **But your implementation hits the three failure modes that the published research says cause
   ~79% of multi‑agent failures** — and they are precisely the ones you suspected: shallow task
   hand‑off (information leakage), weak specification of each member's job, and incomplete
   verification of whether the plan even covered the requirement.

And one meta‑point you also sensed: **you are running multi‑agent on tasks that don't need it.** A
deploy is sequential, not parallel — and Anthropic is explicit that for non‑parallel tasks a single
agent beats a multi‑agent crew. That mismatch is *why it keeps degrading into "a script feeling":*
the multi‑agent overhead adds failure surface without buying the parallel benefit.

So the "labels and rebels" claiming real AI agents are mostly **not lying** — but they (a) use
structured hand‑offs you don't yet have, and (b) only use multi‑agent where it actually pays.

---

## 2. How strong multi‑agent systems actually work (the standard)

From Anthropic's *Building Effective Agents* and *How we built our multi‑agent research system*, plus
the 2025 failure studies:

- **Five composable patterns**, not a monolith: prompt‑chaining, routing, parallelization,
  **orchestrator‑workers**, and **evaluator‑optimizer**. "The most successful implementations use
  simple, composable patterns rather than complex frameworks."
- **Lead agent decomposes, then spawns subagents with *specific mandates*.** In Anthropic's research
  system the lead agent "analyzes the request, develops a strategic approach, and creates multiple
  subagents with **specific research mandates**." Each subagent gets a *crisp, bounded objective* —
  not a vague label.
- **Each subagent has its own context window** and explores independently; the lead keeps the plan in
  **memory** and re‑reads it rather than losing it.
- **Hand‑offs carry structured state, not raw transcripts.** The field's hard‑won lesson: *"the thing
  that gets thrown over the wall is almost always wrong."* Dumping the whole context adds noise and
  loses the decision logic; summarizing loses edge cases. The fix is **explicit state objects /
  structured summaries that capture the key decisions and the exact spec for the next agent.**
- **A verifier closes the loop.** Anthropic adds a *Citation Agent*; the evaluator‑optimizer pattern
  adds a checker that sends work back until it passes.
- **Multi‑agent only pays when the task decomposes into parallel directions.** "If the task does not
  decompose into parallel directions, you pay the cost without earning it." Their system beat
  single‑agent by **90.2%** — *on research tasks*, which are massively parallel. A deploy is not.

The 2025 **MAST** study (Cemri et al., 1,600 traces across AutoGen/MetaGPT/ChatDev/etc.) names 14
failure modes in 3 buckets: **(i) specification & system‑design, (ii) inter‑agent misalignment
(≈36.9% — context loss in hand‑offs, conflicting assumptions), (iii) task verification & termination.**
That taxonomy is the lens for your code below.

---

## 3. How "I" (a single strong agent) work — the contrast

In this very conversation I operate as one agent that: keeps the *entire* context in one head (no
hand‑off loss), **does and verifies** with tools before claiming anything, **persists** across many
turns (try → diagnose the real reason → retry → widen scope), and **never throws work over a wall**
to a fresh context that lost the decisions. That is exactly why a single agent avoids the inter‑agent
misalignment that dominates multi‑agent failures — there is no "between" to leak in.

Your members, by contrast, each start a **fresh CLI session** (`claude -p …`), receive a *raw dump +
a one‑line label*, and hand back a report. The decision logic lives in the orchestrator's head and is
**not packaged** for them — so they re‑derive it (and, as we saw, re‑read stale scripts and drift).

---

## 4. The real gaps in your code (with evidence)

### Gap 1 — Shallow decomposition (specification failure)
`projects.plan_pipeline()` returns `[{"member", "task": "<one concrete part>", "depends_on": […]}]`.
The CTO's output for each member is **a single string label** — no explicit *requirements list, inputs,
expected outputs, acceptance criteria, or "what to pass downstream."* That is MAST category (i):
unclear role boundaries and insufficient context. A real lead agent emits a *mandate* per worker, not
a title.

### Gap 2 — Hand‑off by raw dump + thin label (inter‑agent misalignment — the #1 failure)
In `_orchestrate_gen`, each member is briefed with: a generic "follow the owner's instructions
EXACTLY," **the full `owner_brief` verbatim**, and the one‑line `task`. So every member gets *the
same raw wall of text* and must guess which part is theirs. This is the **context‑dump fallacy** the
research warns about: large unstructured transfers "increase noise, degrade reasoning, and cause
downstream agents to lose the decision logic." There is **no structured state object** carrying *the
CTO's decisions and the specific, bounded spec for this member.* Result: members interpret the shared
brief differently — exactly the "locally consistent but globally contradictory" failure.

### Gap 3 — No plan‑completeness check (omission — your exact suspicion)
Nothing validates that the CTO's plan **covers every requirement in the owner's brief.** The plan is
generated and immediately executed (`steps = plan_pipeline(...)` → run). If the CTO drops a
requirement (your "if he missed the send"), nothing catches it. Real systems verify the *spec → plan*
coverage before running. This is MAST (i)+(iii).

### Gap 4 — Verification exists but the loop/termination is thin
You *do* have an evaluator (the QA gate + the new audit eye), which is good and ahead of many naive
systems. But: QA is off unless the team includes QA; the CTO does not re‑validate the *plan* after QA;
and there's no explicit "are ALL parts done and consistent?" termination check. MAST (iii).

### Gap 5 — (Meta) multi‑agent on a non‑parallel task
For a **deploy/sync**, the steps are inherently sequential (firewall → sync → build → reboot → verify).
There is no parallel decomposition to exploit, so the CTO→DevOps→QA crew adds coordination/hand‑off
failure surface **for no benefit** — which is why it "becomes a script" and underperforms the
deterministic path. Anthropic's guidance: **use a single agent (or a plain workflow) when the task
isn't parallel.** Multi‑agent should be reserved for your *build* projects (Frontend ∥ Backend ∥ DB),
where it genuinely shines.

---

## 5. Why it "degrades into a script," precisely

It's not that turning execution deterministic made it "not AI." It's that **you applied a
parallel‑specialist pattern to a sequential task.** Stripped of the parallel benefit, all that's left
of the multi‑agent layer is overhead + hand‑off leakage — so the only way to make it reliable was to
collapse it toward a script. The honest resolution isn't "more agents" or "one script" — it's
**right tool per task:**
- **Sequential ops (deploy/sync):** single agent *decides* (the hybrid you approved) + deterministic
  execution + verifier. No crew.
- **Parallel build (a new app):** the orchestrator‑workers crew — but with the fixes below.

---

## 6. What to fix (in priority order) — to become a *real* agent, not a label

1. **Replace the one‑line task with a structured MANDATE per member.** Have the CTO emit, for each
   step: `{member, objective, inputs, deliverable, acceptance_criteria, depends_on, hand_off}`. That
   single change attacks Gaps 1 & 2 at once.
2. **Hand off a state object, not the raw brief.** Pass each member *its mandate* + only the
   upstream **deliverables it depends on** (structured), not the whole wall of text. Keep the owner's
   verbatim rules available as reference, but the *working spec* is the structured mandate.
3. **Add a CTO plan‑completeness gate.** Before running, check the plan's mandates **cover every
   requirement** in the brief; if a requirement maps to no step, the CTO re‑plans. (Catches omission.)
4. **Close the verification loop explicitly.** After all steps: a termination check that every mandate
   met its acceptance criteria and the deliverables are mutually consistent — re‑dispatch what failed.
5. **Route by task type.** Sequential/ops → single‑agent hybrid (no crew). Parallel/build → the crew
   with 1–4. This is "right pattern per task," straight from Anthropic.

The good news: your audit/truth layer (no fake success, snake‑hunt, the capability E2E) is *already*
ahead of the field's biggest blind spot (task verification). The missing piece is the **front half** —
specification + structured hand‑off — which is where 79% of failures actually live.

---

## Sources
- [Building Effective AI Agents — Anthropic](https://www.anthropic.com/research/building-effective-agents)
- [How we built our multi‑agent research system — Anthropic](https://www.anthropic.com/engineering/multi-agent-research-system)
- [When to use multi‑agent systems (and when not to) — Claude](https://claude.com/blog/building-multi-agent-systems-when-and-how-to-use-them)
- [Why Do Multi‑Agent LLM Systems Fail? (MAST, Cemri et al., 2025)](https://arxiv.org/abs/2503.13657v1)
- [Are Your Multi‑Agent Systems Failing for These 7 Reasons? — Galileo](https://galileo.ai/blog/why-multi-agent-systems-fail)
- [AI Agent Handoff: Why Context Breaks & How to Fix It — XTrace](https://xtrace.ai/blog/ai-agent-context-handoff)
- [The Compounding Errors Problem — Zartis](https://www.zartis.com/the-compounding-errors-problem-why-multi-agent-systems-fail-and-the-architecture-that-fixes-it/)
