# Odin-Orchestrator

**Multi-Agent AI Orchestration Platform for Odin Markets / Odin AI Systems**

The CTO Brain — a strategic technical leadership system that plans before it builds,
keeps persistent memory and rules, maintains a full audit trail, coordinates a team of
specialized sub-agents, and never touches production without your explicit approval.

---

## What this is

This is not a code generator. It is a disciplined engineering operating system:

- **Think first, then plan, then build.** Every request is read against the project rules
  before any work begins.
- **Persistent memory.** All custom business logic and architecture decisions live in
  `rules/core-rules.md` and are loaded before every task.
- **Full auditability.** Every significant decision, task, and change is timestamped in
  `history/` and can be reverted to any prior snapshot.
- **Specialized agents.** Frontend, Backend, DevOps/Cloud, Security/Compliance, QA, and
  Database agents are activated and coordinated by the orchestrator.
- **Approval gate.** No code, config, or Azure VM change happens without an explained,
  risk-assessed approval request.

## Folder map

```
Odin-Orchestrator/
├── README.md                  ← you are here
├── config/                    ← system + project configuration
│   ├── system.config.json     ← orchestrator settings, paths, gates
│   └── project.config.json     ← Odin Markets project profile
├── rules/
│   └── core-rules.md          ← SOURCE OF TRUTH for all custom logic & standards
├── history/
│   ├── HISTORY.md             ← human-readable running log
│   ├── log.jsonl              ← machine-readable append-only audit log
│   ├── daily/                 ← per-day decision journals
│   └── snapshots/             ← restore points (revert targets)
├── agents/                    ← role definitions for each specialized agent
│   └── *.agent.md
├── orchestrator/
│   └── ORCHESTRATOR.md        ← the CTO Brain operating manual (how I think/act)
├── approvals/
│   ├── pending/               ← approval requests awaiting your decision
│   ├── approved/              ← granted (with your sign-off recorded)
│   └── rejected/              ← declined (with reason)
├── runbooks/                  ← step-by-step procedures (deploy, SSL, scan…)
├── infra/azure/               ← Azure VM access framework & inventory
├── state/                     ← live JSON the dashboard reads
│   ├── project.json
│   ├── tasks.json
│   └── approvals.json
└── dashboard/
    ├── index.html             ← self-contained local dashboard
    └── README.md
```

## How to use it

Talk to me normally. For any non-trivial request I will:

1. Load `rules/core-rules.md` and the relevant config.
2. Restate what I understand, surface unknowns, and propose a plan.
3. Break it into tasks and assign specialized agents.
4. For anything touching code/config/VM, raise an **approval request** first.
5. Execute only after approval, then log everything to `history/`.

## Current status

Phase 1 (Foundation) — built. See `history/HISTORY.md` for the running log.
