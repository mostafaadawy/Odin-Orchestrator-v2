# Scoped Multi-Agent Org — owner requirement (PARKED, not yet built)

> Captured 2026-06-22 from the owner's spec. This is the **original intent** of the project
> ("multiple AI agents — one may be the boss of another, a boss over all bosses; each with its
> own scope and data"). It must **imitate a real company org 100%**. Build on request — next to
> the parked **mobile/phone-terminal** task.

## The defect today
- One shared memory pool. No scopes, no ownership hierarchy. Agents are **labels, not owners**.
- The badge is decided per-message and advisory; a task is never *owned* by an agent for its
  lifetime, so the responsible agent flickers (e.g. clear DevOps work was badged "CTO Brain").
- Context queries ("last thing", "redo last", "yes") resolve against the global pool, so they're
  inconsistent and ownership is undefined. Rule definitions don't enforce any of this.

## The org to imitate (real company)
```
You (human owner)  ── can enter ANY chat at ANY level and request changes
   │
Company CTO  (main dashboard) ── coarse view across ALL projects; decides the project CTOs
   │
Project CTO  (one per project) ── full detail of ONE project; THINKS, then DECIDES which team
   │                              member owns each task, and delegates to them (visible pipeline)
Team member / agent ── a specialist (Frontend, DevOps, …); owns its task + its own pool;
   │                    a member may serve MULTIPLE projects (same person, different project scope)
Chat threads ── a member can have many chats; they share ONE pool per (member × project)
```

## How it must behave
**1. Delegation (top-down, with thinking).** A task entering a project goes to the **Project
CTO**, who *reasons about who is responsible* and hands it to that team member — it is not a
keyword guess. The owner can watch this in the chat as a **visible pipeline**: task → routed to
the responsible member(s) → member works → replies back → result rolls up. This is the
agent-to-agent interaction asked for from day one.

**2. Drill-down on demand (escalation of detail).** Each scope answers at its own level and can
**offer more**:
- Ask the **Company CTO** → coarse, cross-project answer; it offers more.
- Need project depth → it consults the **Project CTO** (detailed for that project).
- Still not enough → the detail is fetched from the **team member** directly.
So a single question can walk *down* the org until the needed depth is reached, then summarized
back up.

**3. Upward synchronization of changes.** The owner can enter **any** chat — even the smallest
member chat — and request a change there. That change must **propagate up**: recorded in the
member's brain → reflected in the **Project CTO's** brain → reflected in the **Company (main)**
brain. Detail stays where it belongs (the member level); summaries roll upward so every level
stays **synchronized** and consistent. No level is ever stale relative to a change below it.

**4. Scope-relative context.** "last / it / yes / redo last" resolves at the CURRENT scope first.
Inside member #N working task X, "the last thing" = X's last thing — never the company pool,
never a sibling's pool.

## Governing rules
- Each scope owns its own pool; detail increases as you descend.
- **Ownership persists:** a task is bound to an owner for its lifetime; the label reflects that
  binding, not a per-message re-guess.
- Containment + drill-down: a higher scope may reach DOWN for detail; never sideways into an
  unrelated sibling. Escalation up is explicit (member → project CTO → company CTO).
- A member's identity may be shared across projects, but its memory/pool is per (member × project).
- Every existing capability (persistent chats, rename/delete, voice, streaming, approval gate,
  semantic routing) must work WITHIN each scope unchanged.
- Enforced in the rule/role definitions — not as per-case patches.

## To design when building
- Storage keyed by scope id: `company`, `project:<id>`, `member:<project>:<agent>` — each with
  its own session(s) + rolled-up summary.
- A delegation/record protocol so changes at a member level emit summaries upward (member →
  project CTO → company) and stay synchronized.
- UI: main dashboard (company) → project dashboard (project CTO) → member view (agent chats),
  with the delegation pipeline visible.
- Context answers should state which scope/level they came from (transparency).

## Status
PARKED — owner will request implementation. Do NOT build until then.
Sibling parked task: **mobile / phone-terminal** connection.
