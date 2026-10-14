# Paper v1 accuracy check: text vs verified code

**Paper checked:** `Odin-Isolated/_research/deliverables/final3/latex-source.zip` (2026-10-06), all 10 sections, read in full from a scratch copy. **The paper folder was not changed.**

**Checked against:**
- the v1 code (read only);
- the code verification report;
- the Phase 2 scenario runs, with the retractions applied;
- the Phase 3 runs.

**Rules:**
- Measurements, numbers, tables, figures and results are not touched.
- Only descriptions are listed.
- Nothing is applied without your approval.

## A. Text that disagrees with verified behaviour (proposed corrections)

**1. §3 F2: "A middleware routes each request to an existing base (reuse), a base plus delta, or new work. A deterministic keyword floor sits under a local semantic classifier so that safety-relevant routing never depends on the model alone."**
- **Code / runs:**
  - The semantic classifier (`orchestrator/semantic_router.py`, a local Ollama chat model) sits in the dispatcher, not the middleware. It picks a specialist and read/change, not reuse/delta/new, and it was not running in the measured copy (DECISIONS D12).
  - Reuse/delta/new is decided by the LLM agents reading the middleware's guards and the `/directions` registry view. Scenario S2 showed this 3/3.
  - Keyword rules (placement, routing floor) are deterministic.
- **Proposed:** "Reuse is decided by meaning: agents read the middleware's guards and a registry view of existing capabilities, and choose reuse, base plus delta, or new work (observed 3/3 in a reuse scenario). Placement and safety-relevant routing stay deterministic: a keyword floor sits under an optional local classifier, so they never depend on the model alone."

**2. §3 F3: "When a new project is created, the middleware checks the library and the database against the project type and builds the requirement list; only missing capabilities are built."**
- **Code / runs:**
  - `create_project()` does not do this.
  - An LLM intake interview (`intake_step`) builds the features, team and a readiness list (have / need) against the connected resources. This was observed 12/12.
  - Type-driven provisioning exists only for security projects (the SOC blueprint).
  - "Only missing capabilities are built": UNDETERMINED (no run proved it).
- **Proposed:** "Before a project is created, an intake interview builds its features, team and a readiness list that marks which resources already exist and which are missing; for security projects a blueprint provisions a complete security team."

**3. §3 F3: "The CTO asks the owner 'we already have this under *key* --- use it?'."**
- **Code / runs:** this wording is not in the code. In runs, agents offered and explained reuse in their own text (S2: "the same engine Revealer uses"). An explicit question to the owner was not observed: UNDETERMINED.
- **Proposed:** "Agents propose reusing an existing capability and say which one, before building anything new."

**4. §3 F3: "Every create, update and delete passes one creation door … and writes the file and its database row together."**
- **Code / runs:** true for writes made through the middleware.
  - Two paths bypassed it in the studied version:
    - the agents' own tools, which the paper already states in §3.1;
    - **changes applied after an owner approval**, which were written without a database row until the next audit (found in Phase 2: 0/3 registered).
- **Proposed:** add one clause: "… writes the file and its database row together. Changes applied after an owner's approval were registered only by the next audit in the studied version."

**5. §3 F1: "a near match stores only a small delta that references the base".**
- **Runs:** agents generated the delta content 3/3, but in the studied version it was saved to disk 1/3 and registered 0/3, and existing delta overlays did not resolve.
- **Proposed:** "a near match is meant to store only a small delta that references the base; in the studied version, generating such deltas worked, but saving and registering them was incomplete."

**6. §3 F11: "After a task, an audit checks that created files obey the shared/delta structure and sit in the folder declared for them, …"**
- **Code:**
  - The audit runs on a timer (about every 15 minutes) and on demand, not after each task.
  - It checks placement, duplicates, cross-project references and registry lockstep in both directions.
  - It does not check delta-to-base links.
- **Proposed:** "On a timer and on demand, an audit checks that files sit in the folder declared for them, …" ("shared/delta structure" is removed; the rest of the sentence is kept).

**7. §3 F11: "A separate *truth gate* rejects any 'done' claim that is not backed by evidence."**
- **Code / runs:**
  - The truth gate flags success claims that contradict tool output (hidden errors).
  - It did **not** cover the reviewer's verdict: runs ended "All requirements addressed ✅" while the review said "Needs fix". This happened in 14 of 15 Phase 2 runs and 7 of 11 success claims in the v1 history.
- **Proposed:** "A separate *truth gate* rejects success claims that contradict the tools' own output; in the studied version it did not yet cover the reviewer's verdict at the end of a run."

**8. §8 Related work (Routing): "\sys{} routes between reuse, delta and new work, with a deterministic floor under a semantic classifier [SBERT, MiniLM]."**
- **Code:** there are no sentence embeddings anywhere. The classifier is a chat model, and reuse/delta/new is chosen by agents (see 1).
- **Proposed:** "\sys{}'s agents choose between reuse, delta and new work by reading a registry view; placement stays rule-based." Move the SBERT/MiniLM citations to proposal P4 (§6), where embeddings are proposed and not claimed.

**9. §3 F4: "clients pull deltas by sequence (a missing message is a visible gap)".**
- **Code:** web and mobile pull by sequence (delta cursor). The desktop client polls the pool and detects changes by count; it never sends a sequence. This is from reading the code; a Phase 6 run will confirm it.
- **Proposed:** "web and mobile clients pull deltas by sequence (a missing message is a visible gap); the desktop polls the pool."

**10. §3 opening: "members work back and forth with the CTO, which re-plans and re-assigns when a result is insufficient".**
- **Code / runs:** re-assignment happens when QA or the audit rejects a step. The CTO's own "Needs fix" review did not trigger it (see 7).
- **Proposed:** "… which re-assigns work when QA or the audit rejects a result."

## B. Undetermined: decide whether to soften (no run proves either way)

**11. §3 F5: "it pulls by status, prioritises, processes, publishes".** The queue code pulls by status in arrival order (`ORDER BY created`). No prioritisation was found in the queue code. By our rule, a code search alone cannot mark it missing. **Option:** "it pulls by status in arrival order" (or keep, and settle it in Phase 6).

## C. Checked and consistent (no change)

- **Abstract:** the "every write" wording is qualified later in the same paragraph by the agents' own-tool gap.
- **F5 and F6:** callback retries until acknowledged (`_retry_sweep`).
- **F7:** shared agent roster.
- **F8:** single /32 rule, replaced.
- **F9:** the DB migration is a separate gate.
- **"Twelve security agents":** the live SOC roster has 12 including its CTO. The blueprint provisions 8.
- **On-device Whisper EN/AR.**
- **Zoom live audio:** `meeting_api.py` captures serial audio chunks and transcribes them live.
- **§3.1 P2, §4 method, §6, §7, §9:** match the record.

**Correction to my own earlier work:** the Zoom finding means chat mismatch **CH5-1 was not a false claim**. I had put it in fix #2's group A. I will move it to "no defect" in the tracker.

## How to apply (needs your decision)

Your rule PP-1 freezes paper v1. To keep that record intact, I suggest:
- leave `final3` untouched as **paper-v1 (frozen)**;
- put the corrected text into a separate **"paper-v1 submission copy"**, with a list of every changed sentence;
- re-compile the PDFs from that copy.

Numbers stay identical. Nothing is applied until you approve each item, or a group of them.
