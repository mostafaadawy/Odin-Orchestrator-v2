# WORKSPACE-SCHEMA.md — the canonical structure (SOURCE OF TRUTH for placement)

> Read this BEFORE creating any file, project, or agent. It answers one question:
> **"Given a new artifact, where does it go?"** — deterministically, every time.
> Every project shares the SAME skeleton; every agent shares the SAME skeleton.
> A folder that doesn't apply to a project is still created, just EMPTY — so the
> structure itself tells you what exists and what doesn't. No file lives "loose".

---

## 1. Placement decision (run this for EVERY new artifact)

**Q1 — SCOPE: who does it serve?**
- ONE project only ............... → `workspace/projects/<id>/…`
- GENERAL / reusable across projects or apps → `workspace/shared/…`
- a chat / conversation .......... → `workspace/chats/…`
- one specialist agent ........... → `workspace/agents/<slug>/…`
- the running app's live runtime .. → `workspace/anchor-layer/…` (or the arm code itself)

**Q2 — TYPE/PURPOSE: which subfolder?**
| The artifact is… | goes in subfolder |
|---|---|
| human documentation (.md/.pdf/.html) | `docs/` |
| knowledge / an artifact a specialist produced | `files/` |
| an executable script (.sh/.py) specific to the owner | `scripts/` (project) or `shared/utils/` (general) |
| structured machine state (a json store) | `jsons/` |
| a single approval record | `approvals/` |
| deployment config or staging | `deploy/` (project) or `shared/infra/` (the shared engine) |
| identity / configuration | `index.json` / `shared/config/` |
| a rule / mandate | `rules.md` |

If both answers are clear, the destination is unique. If not, it's shared by default only when it truly serves more than one owner.

---

## 2. Canonical PROJECT skeleton — IDENTICAL for every project (empty where N/A)

```
workspace/projects/<id>/
  index.json        # identity: id, name, type, members, flags, cadence, stack
  rules.md          # this project's mandate + custom rules
  agents.json       # which agents are assigned here
  docs/             # documentation for this project
  files/            # knowledge + artifacts the agents produce here
  jsons/            # structured state shards (store-managed: tasks, schedules, notifications, approvals.json…)
  approvals/        # individual approval records
  scripts/          # project-specific executables (may sub-group: scripts/setup/, scripts/sensor/)
  deploy/           # deploy config + staging for this project (deploy-config.json, anchor/web copies)
```

Project-type only changes WHICH folders are full:
- a read-only monitor project → `files/`+`jsons/` full, `deploy/`+`scripts/` empty
- a deploy project (organics) → `deploy/`+`scripts/` full
- the SOC project → `scripts/sensor/`, `files/` (knowledge), `jsons/` full
- the arm (odin-external-arms) → `deploy/` full, `references.md` in `docs/`

## 3. Canonical AGENT skeleton — IDENTICAL for every agent

```
workspace/agents/<slug>/
  index.json        # identity: name, role, type, group, nature, avatar, description (+ optional company:true)
  capability.md     # the agent's capability / skills doc
  handoff.json      # {runs_after, runs_before, collaborates_with}
  instructions/  restrictions/  dependencies/  code/  outputs/   (hold the agent's files)
```

Every agent MUST have `index.json` + `capability.md` + `handoff.json` (the three canonical root files)
plus the five canonical subfolders. There is NO `rules.md`/`files/` for an agent (that was an earlier,
now-defunct shape). One canonical slug per role.

### AGENT REGISTRATION CONTRACT — create -> DB -> visible (ENFORCED)
odin_core (Postgres) is the SINGLE SOURCE OF TRUTH for which agents exist. Whenever an agent is created —
create-agent button, a chat request, `suggest_agent`, `create_owner`, or `register_agent` — the middleware
MUST write a COMPLETE `agents` row (id, name, role, type, "group", nature, description) and, if the agent
belongs to a project, link it in `project_agents`. The roster the app reads (`/agents/all`) is sourced from
that DB table, so any registered agent appears everywhere. The audit (`workspace_audit.scan`) ENFORCES it:
`agent-incomplete` for a NULL nature/group, `agent-invisible` for a DB agent missing from the roster. A
partial row or an invisible agent is a BUG, not an accepted state.

## 4. SHARED layer — the general / reusable tier (serves many projects or the whole app)

```
workspace/shared/
  core-registry/    # the index of everything (projects, agents, connectors, keys) → becomes odin_core DB
  config/           # system config (models, system-identity, company-profile)
  directions/       # doctrine read first (core-rules, ORCHESTRATOR, THIS schema, plans, design/)
  runbooks/         # operational how-to procedures
  skills/           # packaged skills (SKILL.md bundles)
  infra/            # the ONE deploy/infra engine (shared across every project)
  testing/          # the ONE test suite (shared)
  utils/            # reusable utility scripts/tools (general, cross-app)
  assets/           # reusable assets (e.g. the live voice-streaming asset)
  oth/              # secrets (.cred, .auth) — gitignored
  cached_modules/   # cached shared modules
```

## 5. Non-project workspace roots (not everything is a project)

```
workspace/chats/        # conversations: registry, per-chat json, files/, scopes/
workspace/anchor-layer/ # the anchor runtime data + sim (served by the app)
workspace/docs/         # general/main-app docs (not tied to one project)
workspace/state/        # dashboard-served state (approvals/project/tasks snapshots)
workspace/history/      # audit log + snapshots (served at /history)
workspace/logs/         # runtime logs + the IPC bridges
```

## 6. Invariants (what "structured" guarantees)

1. Every project folder has the SAME 9 entries (§2) — open any project, know exactly where to look.
2. Every agent folder has the SAME entries (§3).
3. Nothing is created "loose" — every artifact resolves to exactly one folder via §1.
4. General/reusable → `shared/`; one-owner → its project/agent. Decided by §1-Q1, never by guesswork.
5. Empty folders are KEPT (with `.gitkeep`) — absence of content is information, not a reason to delete the folder.
6. One canonical file per function — duplicates are integrated, not multiplied.
