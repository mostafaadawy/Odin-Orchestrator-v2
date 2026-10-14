# Odin-Orchestrator: verifying your six points against the code

**Scope.** This is a read-only investigation. No file was edited and nothing is recommended.

**What was read:**
- **Code:** the real folder `AiAgentWorkSpace/Odin-Orchestrator` (HEAD `af2cbd8`).
- **Isolated copy:** `AiAgentWorkSpace/Odin-Isolated`.
- **Paper:** `Odin-Isolated/_research/deliverables/final3/latex-source.zip`, the latest version, dated 2026-10-06.

Line numbers refer to the real folder.

**How claims are tagged:**
- **PROVEN** means I read it in the code.
- **NOT FOUND** means I searched and the code does not do it.
- **CANNOT DETERMINE** means the answer depends on runtime or LLM behaviour.

---

## 0. The two folders compared

I compared the code with runtime data, logs, `.git`, `.venv` and `node_modules` excluded. Before comparing, I mapped the isolation remaps back: paths, the `_iso` database names and the 18000/19xxx ports.

**Same after remapping (no logic difference):**
- `store.py`, `workspace_audit.py`, `agents_registry.py`, `directions.py`, `capabilities.py`, `app.py`, `deploy_runner.py`, `third_party.py`, `ui_api.py`.
- All the shells except one whitespace change in `anchor_loop.sh`.
- `orchestrator/semantic_router.py` and `orchestrator/dispatcher.py`.

**Real logic changes that exist only in the isolated copy.** These are the paper's "P2" work. They are uncommitted in the copy's own git, on top of commit `86cf630`.

| File | Change (isolated only) |
|---|---|
| `server/scope_hook.py` | **New file.** A PreToolUse hook. Agents may write only inside their own project. Writes to `shared/` must go through the door. |
| `server/door_cli.py` | **New file.** A command-line door used by the hook to promote files. |
| `server/claude_cli.py` | `_scope_settings_file()` and `_actor_for()` register that hook for agent runs. |
| `server/projects.py` | New `agent_workdir(pid)`. Adds the missing `"EasyPost"` role to the role catalogue. |
| `server/api_v2.py` (~l.3447) | `fp = localPath or agent_workdir(pid)`: agents start in their own project folder. |
| `server/workspace_mw.py` `delete_owner()` | Also deletes a project's chat-scope folders and their database rows. |

The other differing files contain only absolute-path remaps: `views.jsx`, `e2e_ai_capability.py`, `e2e_phase1_hard_deploy.py` and `flutter_export_environment.sh`.

**Real folder git status:** only runtime data files are modified (`workspace/history/*.jsonl`, `logs/agent_term/*`, two `agents.json`). No code files are modified.

**Note on papers:** `Resulted Papers and Documents/odin_paper.tex`, dated June 25, is a different and older paper. It is not the one compared here.

---

## 1. "A new project first checks the middleware together with the audit and delta files"

**Partly true. Corrected sequence: PROVEN.**

The entry point is `POST /projects` in `api_v2.py:121`, which calls `projects.create_project()` (`projects.py:687`). The steps run in this order:

1. `unique_identifier()` makes the project id unique.
2. `recommend_type(description)` (`projects.py:300`) is a keyword `if`-chain over the description.
3. The project is saved to the registry with `_save_all()`.
4. **`workspace_mw.create_owner("project", pid, …)`** (`workspace_mw.py:661`) is the middleware door. It:
   - stamps the full canonical folder skeleton;
   - writes `index.json` and `agents.json`;
   - inserts the `projects` row into odin_core;
   - calls `sync_folders()`, then `sync_row()` for each root file.
5. `infer_team(description)` (`projects.py:463`) is negation-aware keyword team inference.
6. `agents_registry.register_agent()` runs for each team member and each company agent.
7. If the brief is security-related, `soc_blueprint.provision()` runs (`projects.py:~800`).
8. If the project is periodic, `scheduler.create_task()` runs.

There is also an optional step before creation: `POST /intake` (`api_v2.py:160`) calls `projects.intake_step()` (`projects.py:1245`), an LLM interview.
- Its prompt receives `capabilities.summary_text()` (the connected services) and the fixed role list.
- It does **not** receive the shared library, the `directions` view or the existing projects.

**NOT FOUND:**
- No audit call during project creation. The audit runs separately: `scheduler._audit_sentinel_maybe()` (`scheduler.py:441`) runs `workspace_audit.sentinel()` about every 15 minutes.
- No delta step during creation. `create_project` never calls `request_capability`, `provision_capability` or `customize_shared`.

---

## 2. "The middleware lets a new request see all capabilities and all previous projects"

**What the middleware holds: PROVEN.** `workspace_mw.py` contains:
- the schema constants `PROJECT_SUBFOLDERS`, `AGENT_SUBFOLDERS` and the root-file sets (l.19–29);
- `validate()`, `route()` and `put_file()`, which place files;
- `sync_row()`, which upserts the odin_core tables `projects`, `agents`, `connectors`, `chats`, `folders` and `files`;
- `add_dependency()`, which writes `dependencies/manifest.json` plus the `dependencies` and `shared_capabilities` rows.

**How existing capabilities are exposed: PROVEN.** This is a separate module, `server/directions.py`, mounted at `/directions/*` in `app.py:163-166`. It has five functions, all SQL `ILIKE` keyword queries on odin_core:

| Function | What it returns |
|---|---|
| `overview()` | Counts for every table |
| `find(q)` | Projects, agents, connectors, chats, shared capabilities and files that match the keyword |
| `capability(need)` | Shared capabilities, `dependencies.used_by` and `also_built_in` (custom copies inside projects), plus a reuse recipe |
| `resources()` | One owner's files, dependencies, connectors and agents |
| `similar(text)` | Files whose description contains up to 6 words from the text |

**What agents are told: PROVEN.** `api_v2._orientation_block()` (~l.3093) and `_brain_orientation()` (~l.3200) inject text into agent prompts. It tells them to read `core-rules.md` and `ORCHESTRATOR.md`, and to "first READ what already exists in **this project's** folder and records — then reuse/extend it".

That instruction is scoped to the agent's own project. The prompt does not tell agents to query all projects.

**CANNOT DETERMINE:** whether agents actually call `/directions` at runtime. Nothing in the server code calls `directions.capability()` automatically. Use depends on the LLM.

---

## 3. "Two kinds of matching: exact/static and semantic"

**Exact or static matching: PROVEN, and used in many places.**

| Where | What it matches |
|---|---|
| `workspace_mw.validate()` / `route()` | Fixed folder sets. Redirects a file by extension and name. |
| `directions.find`, `capability` and `similar` | SQL `ILIKE` substring search |
| `workspace_mw.request_capability()` | `need.lower() in filename.lower()` (a filename substring) |
| `workspace_audit.scan()` | SHA-256 identical content, or the same filename |
| `dispatcher.Dispatcher.classify()` | `AGENT_TRIGGERS` keyword counts |
| `projects.recommend_type()` / `infer_team()` | Keyword rules |
| `projects.capability_options()` | Counts of overlapping words |

**Semantic matching: PROVEN, but narrower than described.**
- The only semantic module is `orchestrator/semantic_router.py`, function `classify()`. It sends the request to a local Ollama chat model (`qwen2.5:7b-instruct`).
- It returns one of 7 fixed specialists (Frontend, Backend, DevOps & Cloud, Security, QA, Database, CTO Brain) and `read` or `change`.
- It is called only from `Dispatcher.route()` (`dispatcher.py:~187`). It decides the owner label and the approval gate, and falls back to keyword `classify()` when the model is unavailable.

**NOT FOUND:**
- Any comparison of the task's meaning against existing scripts or capabilities.
- Any embedding, vector or cosine-similarity code anywhere in `server/` or `orchestrator/`.

LLM judgement does appear in `intake_step()` and `suggest_agent()`, but that is prompt reasoning, not a matching module.

**Side observation:** the router's 7 specialist names (Frontend, Backend, Database) do not match the project role catalogue, which uses Fullstack, QA, DevOps and others.

---

## 4. "The CTO decides agents: full match → reuse; match plus extra → shared + delta; none → new agent"

**PROVEN, for agents:**
- **Reuse at creation:**
  - `agents_registry.register_agent()` (l.175) returns the existing agent if the name is already on the project.
  - Its database step looks up `agents` by `lower(name)` and links it through `project_agents`. The same agent row is therefore shared across projects.
- **Capability-gap dialog:** `projects.capability_options(pid, task)` (l.383) is served at `POST /projects/{pid}/capability` (`api_v2.py:144`). It:
  - scores existing agents and catalogue roles by word overlap with the task;
  - returns three choices:
    1. embed an existing agent (top 6);
    2. create a new agent, drafted by the LLM in `agents_registry.suggest_agent()`, with an overlap guard;
    3. expand an existing member's role.
  - **The owner chooses.** The code does not decide on its own.

**NOT FOUND:**
- The branch "agent matches but needs extra work, so reuse shared files and write a delta" does not exist for agents. Choice 3 edits the agent's role, rules and resources; it writes no delta file.
- The search is word overlap over names, roles and descriptions. It does not search skills, and it is not semantic.

---

## 5. "Overlapping script → promote to shared base, delta per project, original points to shared"

**The promotion mechanism: PROVEN.** `workspace_mw.promote_to_shared(src_path, category, extra_consumers)` (l.371):

1. Chooses a category from the filename: `deploy` → `infra`, `test`/`e2e`/`spec` → `testing`, otherwise `utils`.
2. **Moves** the file with `shutil.move` to `workspace/shared/<cat>/<name>`, so the project copy is removed. If the shared file already exists, it deletes the duplicate instead.
3. Removes the old database row with `remove_file()` and indexes the new one with `sync_row()`.
4. For the original owner and each extra consumer:
   - `add_dependency()` writes a manifest entry `{source: shared/…, mode: "as-is", overlay: null}` plus the `dependencies` and `shared_capabilities` rows;
   - `_rewrite_owner_refs()` replaces the old path with the new one, by plain string replacement, in the owner's `.py/.sh/.js/.ts/.dart/.json/.md` files.

**What actually triggers promotion at runtime: PROVEN.** Only the audit, in `workspace_audit.heal()`:
- `duplicate` with identical content: it promotes the first copy and deletes the other copies.
- `foreign-ref`: it promotes the referenced file, then `repoint_reference()` rewrites the file that referenced it.
- `duplicate` with the same name but different content: **FLAGGED only**. No delta is created.

**Corrections to your description:**
- After promotion the original project points to shared through an **"as-is" manifest pointer, not a delta file**.
- Delta, or overlay, files are created only by:
  - `customize_shared()` (l.469): an overlay in the owner's `code/`, with mode `extend`, `subset` or `override`;
  - `provision_capability()` (l.487): generates `deploy/<pid>.config.sh`, for deploy needs only.
- `request_capability()`, `customize_shared()`, `provision_capability()` and `resolve_capability()` **have no caller in the running server**. They are called only from the test scripts `workspace/shared/testing/phase7_lifecycle.py` and `phase7_strong.py`.

**Observations from reading the code (not run):**
- `provision_capability()` stores the overlay as `"deploy/<pid>.config.sh"`. `resolve_capability()` builds the overlay path as `<owner>/code/<overlay>`, which gives `code/deploy/…`. By reading alone, that path would not resolve.
- `customize_shared()` picks the first shared file whose name *contains* the given name. That is a substring match, not an exact one.

---

## 6. "The audit verifies every file is in the database, prevents hallucination such as recreating scripts, and corrects"

**What `workspace_audit.scan()` (l.104) checks: PROVEN.**

| Check | Correction applied in `heal()` (l.350) |
|---|---|
| Misplaced file (`mw.scan_violations`) | Moved to the slot `route()` picks |
| File on disk but not in the database (`unindexed`) | Indexed |
| Database row but file gone (`db-orphan`) | Row removed |
| Parallel JSON registry | `projects.json` deleted; others flagged |
| Agent with NULL nature, not on the roster, or not registered | Flagged only (no fix branch) |
| Identical duplicate in `projects/*/code\|deploy` | Promoted to shared |
| Same filename, different content | Flagged |
| Foreign reference to another project's file | Promoted and repointed |
| External writes, root strays | Flagged |

`sentinel()` (l.314) runs `heal(force=True)`, then raises a notification if any hard violation remains.

**When it runs: PROVEN.** On the scheduler timer, about every 15 minutes (`scheduler.py:441`), and from a "Run now" button. **NOT FOUND:** any trigger tied to the end of a task.

**On "prevents hallucination / recreating scripts": NOT FOUND as prevention.**
- The audit acts after the fact.
- It detects a re-created script only if the content is byte-identical or the filename is the same, and only inside project `code/` and `deploy/`.
- A re-implementation with a different name and different content is not detected.

**What is real:**
- Write-time prevention of wrong-folder and cross-project writes is in the middleware, `put_file()` (l.143). In the isolated copy only, the P2 `scope_hook.py` adds the same for agents' own tools.
- A separate "truth gate" against false "done" claims exists in `server/audit.py`: `claims_success()`, `gate_success()` and `scan_hidden_faults()`, used in `api_v2.py:2682` and `2776`.

---

## Could not determine

- Whether LLM agents actually query `/directions` or follow the reuse instructions at runtime. This is behavioural and not visible in the code.
- The live contents of odin_core: how many shared capabilities, dependencies or deltas actually exist. I did not query the database.
- Whether Ollama, and therefore the semantic router, runs in your real system. In the isolated study it was **not** started (`_research/DECISIONS.md` D12), so only the keyword router was measured.
- The internals of `soc_blueprint.provision()`, which I did not read.
- Where the "we already have this under *key* — use it?" question would come from. That text does not appear anywhere in the code.

## Where the paper and the code disagree

1. **F2:** the paper says "middleware routes each request to reuse / base+delta / new work, with a keyword floor under a semantic classifier".
   - The semantic classifier is in the dispatcher, not the middleware. It picks a specialist and read/change, not reuse/delta/new.
   - The reuse/delta/new functions use filename substring matching and are not called at runtime.
2. **Related work (§8):** it cites sentence embeddings (SBERT, MiniLM) for routing. The code uses an Ollama chat model; there are no embeddings.
3. **F3:** the paper says "on project creation the middleware checks the library and database against the project type and builds the requirement list". `create_project()` does not do this. The only type-driven provisioning is the SOC blueprint for security projects.
4. **F3:** the paper says "the CTO asks the owner 'we already have this under key — use it?'". Not found. The nearest thing is the agent capability dialog.
5. **F1:** the paper says "a near match stores only a small delta". The delta functions exist but are exercised only by test scripts, not by the running server.
6. **F11:** the paper says "after a task, an audit checks files obey the shared/delta structure".
   - The audit runs on a 15-minute timer, not after each task.
   - It checks placement, duplicates and references. It does not verify delta→base links, because it never calls `resolve_capability`.
7. **Consistent with the code:**
   - F7: agents are shared through the `agents` and `project_agents` tables.
   - The one-door claim: `put_file` and `create_owner` behave as described.
   - P2: the paper states it was implemented only in the isolated copy.
