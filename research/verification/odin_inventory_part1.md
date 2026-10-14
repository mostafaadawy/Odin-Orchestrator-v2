# Odin: inventory, and the six mismatches re-examined

**Part 3 step 1. Read-only. No runs have been made yet.**

**Sources read:**
- the real folder `Odin-Orchestrator`, at HEAD `af2cbd8`;
- the paper copy `Odin-Isolated`, at `86cf630`, plus its uncommitted P2 changes;
- `workspace/shared/directions/`: core-rules, STRUCTURING-PLAN, WORKSPACE-SCHEMA, PHASE7-RESULTS, PHASE7-HANDOFF;
- `workspace/history/*.jsonl`;
- the agent folders, the dependency manifests and the delta files on disk.

**Status rule (yours):** a point can be WORKS, PARTIAL or NOT WORKING only after a run on the copy. Until those runs happen, every point below is **UNDETERMINED (pending run)**. Where your history records an earlier real run, it is listed as *recorded-run evidence*. That supports the point, but it is not a run made in this verification.

**Safety baseline (recorded before anything else):**

| Folder | HEAD | Code files hashed | Status at baseline |
|---|---|---|---|
| Odin-Orchestrator | `af2cbd8` | 3,213 | 8 runtime data files modified, no code |
| Odin-Isolated | `86cf630` | 377 | 26 entries (the P2 work) |

Odin-Isolated is the newest research folder. Odin-Keel-Research no longer exists.

---

## A. Inventory by point

### 1. Main chat: create a project, or ask about the system

- `POST /chat` and the scoped chat run through `api_v2._scoped_gen` (~l.3340).
- `Dispatcher.route()` in `orchestrator/dispatcher.py` does two things:
  - routes semantically through `semantic_router.classify` (local Ollama);
  - falls back to keywords (`classify`) and an approval gate (`approval_check`).
- Project creation has two entry points:
  - `POST /intake` → `projects.intake_step()` (`projects.py:1245`), an LLM CTO interview that returns `ask` or `propose`;
  - `POST /projects` → `projects.create_project()` (`projects.py:687`).

### 2. Database + middleware + audit as the creation backbone

**Middleware (the single door), in `server/workspace_mw.py`:**
- `validate` (l.55), `route` (l.103), `put_file` with the owner-scope guard (l.143);
- `sync_row` (l.192), `create_owner` (l.661), `delete_owner` (l.724).

**The database is the only registry.** odin_core tables:
- `projects`, `agents`, `project_agents`, `connectors`, `chats`, `folders`, `files`;
- `dependencies`, `shared_capabilities`;
- `agent_scope` and `external_report` (created on demand, `workspace_mw.py:831`, `923`).

**Doctrine read first:** `core-rules.md`, `ORCHESTRATOR.md`, `WORKSPACE-SCHEMA.md` (placement plus the agent registration contract) and `STRUCTURING-PLAN.md` (phases 0–7).

**Knowledge view:** `server/directions.py` exposes `overview`, `find`, `capability` (the reuse advisory) and `similar` at `/directions/*`.

**Agent orientation prompts:**
- `api_v2._orientation_block` (~l.3093) and `_brain_orientation` (~l.3200).
- They inject the team, live connectors, the shared tools, the tutorial and agent-scope guards, the audit's broken-method list, and the instruction "BE SMART & AVOID DUPLICATION".

### 3. Role recommendation, with owner approval

- `intake_step()` prompt (`projects.py:1245–1320`). The LLM:
  - decides PLATFORM, TEAM and FEATURES from the project's nature;
  - may recommend new members, each with a reason, in `recommendations`, and never auto-staffs them;
  - fills `readiness` (have or need) against real resources.
- `infer_team()` (`projects.py:463`) is the negation-aware default for the direct path. "No QA" removes QA; "deploy later" drops DevOps.
- `_apply_agent_controls()` in `api_v2` (~l.3375) honours "remove X" and "only use X" typed in chat.
- `agents_registry.is_excluded()` makes an owner-removed agent never come back silently.

### 4. Agent matching and reuse

- `agents_registry.register_agent()` (l.175):
  - returns the existing member if one is found;
  - in the database, reuses the agent row by name and links it through `project_agents`, so one agent can serve many projects.
- `projects.capability_options()` (l.383), served at `POST /projects/{pid}/capability`, offers three choices:
  1. embed an existing agent, ranked;
  2. create a new one, drafted by the LLM in `suggest_agent`, with a **non-intersection guard**: "prefer expanding Fullstack instead of a duplicate";
  3. expand an existing member's role, rules and resources.
- `api_v2._ensure_member()` (~l.2088) auto-hires **only known catalogue roles**. It never invents a made-up agent and never resurrects a removed one.
- Coverage rule: Fullstack owns the whole web app, with no separate Frontend or Backend member. This is in the `intake_step` prompt and in `infer_team`.

### 5. Shared files, deltas and promotion

**Functions in `workspace_mw.py`:**
- `request_capability` (l.434), `promote_to_shared` (l.371), `add_dependency` (l.300);
- `customize_shared` (l.469) for an overlay with mode extend, subset or override;
- `provision_capability` (l.487), which **generates** a per-project delta;
- `resolve_capability` (l.533), `repoint_reference` (l.409).

**Recorded-run evidence, real files on disk:**
- `projects/revealer-6978/dependencies/manifest.json` contains two deltas:
  - `deploy_changes.py`, mode `extend`, overlay `deploy/revealer-6978.config.sh`;
  - `run_all.py`, mode `extend`, overlay `tests/`.
- The overlay file's header reads "GENERATED BY THE SYSTEM … delta over shared capability".
- `PHASE7-HANDOFF.md §2` records that a hand-written delta was deleted and **the system regenerated it**, after which the deploy was green.
- Other projects and agents point to shared files: `full-services-19jul`, `redberry-continuous-soc`, `odin-external-arms`, and four security agents that share `ensure-connection.sh`.
- `history/audit-log.jsonl` records real promotions:
  - 15 identical duplicates promoted to `shared/utils` and `shared/infra`;
  - 15 foreign references promoted and repointed, 2026-07-17 to 07-20.

**Not yet located: the 50% threshold rule.** It is not in code, directions or the schema files read so far. It needs a run, or a pointer from you to where it was written.

### 6. Per-project credentials through deltas

- The `agent_scope` table stores (project, agent, service, credential_ref, read_only) (`workspace_mw.py:831–888`).
- `agent_scope_guard()` (l.890) is injected at `api_v2.py:1007` and `:3239`. Its prompt says:
  - "use the SCOPED credential … do NOT use your default key, state credential_source=delta";
  - otherwise, use the default from `.cred`.
- `vm_diagnosis_guard()` (l.966) reads the scoped key from runtime settings.
- **Not yet located:**
  - who writes `agent_scope` rows. `set_agent_scope` has no Python caller in `server/`, so it may be called by an agent, a script or a chat flow;
  - the "same key or a different account?" question to you.

### 7. At runtime an agent follows its rules, then its delta

- The agent prompt is built from its `capability.md`, rules, resources, orientation, agent-scope guard, tutorial guard and audit guard (`api_v2` ~l.1000–1012, 3200–3255).
- Deploy follows the per-project delta: `shared/infra/deploy_changes.py --project <pid>`, with per-project baselines, and `deploy.sh` reads the port from the delta.
- **Needs a run:** a non-deploy agent applying a delta's extra or skipped steps.

### 8. Main-chat questions about existing projects

- `scope_answer_guard()` (`workspace_mw.py:770`), owner path: "reason about meaning … if outside this project … GO FIND it from the global / other-projects / system data".
- `read_execute_guard()` (l.804): a read is executed, never proposed.
- `directions.find/capability/similar` hold the knowledge.
- `anchor.py:249` applies the external-request version.

### 9. Audit and guard rules to preserve

**Workspace audit, `server/workspace_audit.py`:**
- `scan` (l.104), `heal` (l.350), `sentinel` (l.314), run about every 15 minutes from `scheduler._audit_sentinel_maybe` (l.441).
- Issue types:
  - unindexed, db-orphan, misplaced, parallel-registry;
  - agent-incomplete, agent-invisible, agent-unregistered;
  - root-stray;
  - identical duplicate (promoted), same-name duplicate (flagged);
  - foreign-ref (promoted and repointed);
  - external-write (`_external_writes`, l.263).
- `PROTECTED_PROJECTS` keeps production untouched.

**Middleware write rules:**
- `put_file` redirects a misplaced or cross-owner write to the right place and logs it to `history/mw-corrections.jsonl` (33 entries).
- `write_external_report` enforces the single-file rule for external folders (l.948).

**Truth and hallucination gate, `server/audit.py`:**
- `claims_success`, `assess`, `gate_success`, `correction_prompt`, `scan_hidden_faults`, `audit_deploy_proposal`, `audit_prompt`, `engine_audit`.
- Used in the run loop at `api_v2.py:2682` and `:2776`; this catches fake "done" claims.

**Stuck detection:** `claude_cli.py:210–300` stops an engine call after `ODIN_CLAUDE_IDLE` (420 s) with no output.

**Semantic scope tests**, the rules you added after semantic testing:
- `server/scope_guide_test.py` and `server/scope_reasoning_test.py`.
- Each logs `scope-answer` misses into the audit log: 55 recorded, flagged as "refine the middleware guard".

**Agent rules:**
- `_suggest_rule` gives no agent a rule-less start (rule-less agents caused hallucination).
- `_ensure_member` never invents an agent.

**Isolated copy only (P2):**
- `server/scope_hook.py`, a PreToolUse write rule;
- `server/door_cli.py`;
- `claude_cli._scope_settings_file`.

**Not yet located:** the step where the audit traces the creating agent and updates the middleware rule automatically. The scope tests do flag "refine the middleware guard", but by a person or agent, not automatically. **Needs a run.**

---

## B. The six earlier mismatches, re-judged under your rules

| # | Earlier claim | Verdict now | Evidence |
|---|---|---|---|
| 1 | The semantic router decides specialist and read/change, not reuse/delta/new | **Partly retracted.** Semantic decisions also come from LLM agents reading the middleware guards and directions (`intake_step`, `suggest_agent`, `scope_answer_guard`, CTO orientation). Whether reuse/delta/new is decided by meaning at creation: UNDETERMINED until a run. | `projects.py:1245`; `workspace_mw.py:770`; `api_v2 ~3200` |
| 2 | The paper cites SBERT/MiniLM, but the code uses an Ollama chat model | **Kept, as a citation-accuracy note.** It does not claim a missing feature. | `semantic_router.py:20`; related-work §8 |
| 3 | No type-based requirement list at creation | **Retracted as stated.** `intake_step` builds features, team and readiness (have or need) against real resources. The SOC blueprint is type-driven reuse. "Only missing capabilities are built": UNDETERMINED until a run. | `projects.py:1290–1311`, `:795` |
| 4 | "We already have this under *key*, use it?" not found | **Retracted to UNDETERMINED.** The behaviour may come from the LLM through `directions.capability`'s verdict and the capability dialog; the exact wording is not in code. | `directions.py:67`; `projects.py:383` |
| 5 | "Deltas are only written by test scripts" | **Retracted.** A system-generated delta exists for revealer-6978, and the recorded run shows the system regenerated it. Which entry path calls it at runtime: UNDETERMINED until a run. | manifest and overlay header; HANDOFF §2 |
| 6 | The audit is timer-based and does not verify delta→base links | **Softened.** The workspace audit is timer-based, but the truth gate runs inside each task (`api_v2:2682`, `2776`). Whether broken delta links are caught: UNDETERMINED until a run. | `scheduler.py:441`; `audit.py` |

---

## C. Still open: needs the bridge and runs on your Mac

1. Make `Odin-Consolidated` from Odin-Isolated, with a private PostgreSQL cluster on port 15432 filled from a read-only `pg_dump`, shims active and dummy credentials.
2. A cost estimate before any LLM batch.
3. The six scenario runs from Part 3, each repeated 3 times, then the final report `odin_scenario_verification.md`.
