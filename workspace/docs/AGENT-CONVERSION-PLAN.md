# Conversion plan — from raw‑dump hand‑offs to a Main‑Task shared‑state core

*Goal: convert Odin's orchestration so every prompt becomes a persistent **Main Task** (the single
source of truth), the CTO decomposes it with **no omission**, and every agent works from **the big
picture + its own bounded mandate** — the architecture the best practitioners (Cognition, Anthropic,
LangGraph) converge on. No Roo, no core damage. Each phase is measurable by the frozen capability E2E.*

---

## 0. The spine: the Main Task

Your insight, made the centre of the design: **a new prompt is not a chat message — it is a Main
Task object** that persists for the whole run and that *everything* references. It carries:

```
MainTask {
  id, project_id, created
  objective            # one-line goal
  brief_verbatim       # the owner's EXACT prompt (never summarized — Cognition's rule)
  requirements[]       # the brief split into checkable items: {id, text, status: open|done, owner}
  decisions{}          # the CTO's choices (stack, method, target paths, migration mode, …)
  plan[]               # mandates: {member, objective, inputs, deliverable, acceptance, depends_on}
  status{}             # running state: each member's deliverable + what's still open
}
```

Two non‑negotiables from the research, baked in:
- **`brief_verbatim` is the curated full context** every agent sees (the "big picture"). It is the
  *structured* Main Task, **not** the raw chat transcript — that distinction is what avoids the
  context‑dump noise while keeping full alignment.
- **`requirements[]` is the omission guard.** Nothing is "done" until every requirement is `done`.

---

## 1. Detailed review of the current code (what exists, where it breaks)

| Stage | Current code | What it does | Gap vs. best practice |
|---|---|---|---|
| Prompt intake | `projects.intake_step()` | Adaptive Q&A → a project `spec` | Good — but the result isn't persisted as a checkable **requirements list**; it becomes free‑text `description`. |
| Run start | `_orchestrate_gen(pid, goal)` | `goal` = the raw prompt | `goal` is treated as a string, not a **Main Task** object with state. |
| Decomposition | `projects.plan_pipeline()` → `[{member, task, depends_on}]` | CTO splits into ordered steps | **`task` is a one‑line label** — no inputs/deliverable/acceptance. (Specification failure.) |
| Hand‑off | `owner_brief` = the raw `goal` verbatim, sent to **every** member + the thin `task` | Member gets the whole wall of text + a label | **Raw‑dump hand‑off** — the #1 documented failure (context loss / misalignment). No curated state, no per‑member spec. |
| Downstream context | `results = [{member, task, review}]` (a list, not fed forward) | Tracks finished parts | Downstream members **don't receive upstream deliverables** as structured inputs. |
| Completeness | none | — | **No check that the plan covers every requirement** (omission goes uncaught). |
| Verification | QA gate + the new audit eye | Catches fakes/snakes | Good (ahead of most) — but it validates *a step*, never the **Main Task as a whole**. |

Net: the **front half** (spec + decomposition + hand‑off) is where we lose; the **back half**
(verification) is already strong. The conversion is mostly front‑half work.

---

## 2. Target flow (what it becomes)

1. **Confirm the spec (discussion first).** `intake_step` runs until the owner confirms — then emit a
   **MainTask** with `brief_verbatim` + a parsed `requirements[]` checklist. (No omission at the source.)
2. **CTO builds the master plan.** A new `plan_main_task()` replaces the thin `plan_pipeline`: the CTO
   produces, for each step, a **mandate** `{member, objective, inputs, deliverable, acceptance,
   depends_on}` — and **maps every requirement to a step**.
3. **Completeness gate.** Before running: verify every `requirement` is covered by ≥1 mandate; if a
   requirement maps to nothing, the CTO re‑plans. (Catches omission deterministically.)
4. **Structured hand‑off.** Each member receives: the **MainTask big picture** (objective +
   `brief_verbatim` + the requirements + current `status`) **+ its own mandate** + the **deliverables
   of the steps it depends on** (structured, from `status`). Never the raw dump alone.
5. **Write‑back to shared state.** When a member finishes, its **deliverable** is written into
   `MainTask.status`, and the matching `requirements` flip to `done`. The next member reads that state.
6. **Align to the big picture every step.** After each step the CTO compares `status` vs `requirements`
   ("where are we, what's left") and re‑dispatches anything unmet — the loop you described.
7. **Final verification.** The run is "done" only when **all requirements are `done`** AND each
   deliverable passed QA + the audit eye. (Termination check — the back‑half we already have, now tied
   to the Main Task.)

---

## 3. The conversion, phased (each phase is small, shippable, and measurable)

**Phase A — Main Task object + persistence.**
New `server/main_task.py`: the `MainTask` dataclass + `create/get/update/set_requirement_status/
write_deliverable`, persisted via `store` (like operations.py). No behaviour change yet — just the
state container. *Measure:* unit‑level (create, update, reload).

**Phase B — Requirements extraction + completeness gate.**
On run start, parse `brief_verbatim` → `requirements[]` (engine, with a deterministic fallback that
splits on lines/sentences). Add `plan covers all requirements?` check before execution; if not,
re‑plan once. *Measure:* the frozen E2E's **MINING** should rise toward 100% reliably (it's literally
"did it discover all the requirements").

**Phase C — Mandates replace thin tasks.**
Replace `plan_pipeline` with `plan_main_task()` emitting full mandates. Update `_orchestrate_gen` to
brief each member with **MainTask big picture + its mandate + upstream deliverables**, instead of the
raw `owner_brief` dump. *Measure:* **PROPAGATION** stops drifting (the member has a bounded, correct
spec; it isn't guessing from a wall of text).

**Phase D — Write‑back + alignment loop.**
Members write deliverables to `status`; CTO re‑checks `status` vs `requirements` each step and
re‑dispatches gaps. *Measure:* **CRYSTALLIZATION** + a new sense of "all requirements done."

**Phase E — Tie final verification to the Main Task.**
"Done" requires every requirement `done` + QA/audit clean. *Measure:* **TRUTHFULNESS** holds, and the
overall verdict reflects real completion, not a step passing.

> Routing note (from the analysis): sequential ops (deploy) still run the **single‑agent hybrid** —
> the Main‑Task layer governs *build* projects (parallel members) where the hand‑off problem lives.
> Right pattern per task, as Anthropic prescribes.

---

## 4. What I need from you

- A **yes** to make the *Main Task* the spine (it is — confirming).
- Whether the **"discussion before confirming the prompt"** should be required for every new project,
  or skippable when you paste a complete brief (default: run it, but let you skip with one click).

After Phase A–C you'll *see* the difference on the frozen stick (MINING + PROPAGATION), and we keep
going phase by phase, finding and filling the next gap each time — never touching the stick.

---

## 5. Files touched
- **new** `server/main_task.py` (the shared‑state object)
- `server/projects.py` — `intake_step` emits requirements; `plan_pipeline` → `plan_main_task`
- `server/api_v2.py` — `_orchestrate_gen` uses MainTask hand‑off + completeness/alignment gates
- *(frozen, untouched)* `server/e2e_ai_capability.py` — measures every phase
