# Phase 3, fix #1 (priority 1): deltas written but not saved or registered (G4 + G3)

**Status:** designed, not applied. **Waiting for your approval.**
**Working folder:** Odin-Consolidated only, tagged `phase3-start`.

## The root cause, proven by replaying your own recorded runs

I replayed `api_v2._parse_proposal()` (`server/api_v2.py` l.949) on the 6 transcripts recorded in Phase 2.

The parser takes the **first** fenced code block marked `proposal` **or `json`**. When an agent first shows file contents in a ```` ```json ```` block (for example the delta's `deploy-config.json`) and then writes its ```` ```proposal ```` block, the parser reads the wrong block. That block has no `files` or `commands`, so it returns nothing. The proposal is silently lost: no approval is created and the delta is never written.

| Run | Fenced blocks in the agent reply | What the parser picked | Result |
|---|---|---|---|
| S2 r1 | json, sh, **proposal** | `deploy-config.json` contents | lost |
| S2 r2 | **proposal** | the proposal | approval created; delta written |
| S2 r3 | sh, json, **proposal** | `deploy-config.json` contents | lost |
| S1 r1 | bash, json, json, ts… **proposal** | `package.json` contents | lost |
| S4 r1 | tsx, ts, css, **proposal** | the proposal | approval created |
| S4 r2 | tsx, ts, prisma… **proposal** | `package.json` contents | lost |

This matches exactly what Phase 2 observed.

**Second cause (registration).** After an approval is applied (`_apply_approval_bg`, l.1310), the written files are never indexed in odin_core. A file that says it is a delta over a shared base is never added to the project's `dependencies/manifest.json` or to the `dependencies` table.

Also, `workspace_mw.resolve_capability` (l.533) looks for overlays under `code/<overlay>`. Your existing manifests, Revealer's included, store overlays relative to the project folder (`deploy/<pid>.config.sh`), so a registered delta can never resolve.

## The fix: 3 small changes, all extending existing mechanisms

1. **`_parse_proposal` (api_v2.py l.949).**
   - Prefer a block fenced as `proposal`.
   - Otherwise use the **last** fenced JSON block that contains `files` or `commands`.
   - Otherwise fall back to the current brace scan.
   - Replies with a single proposal block behave exactly as today.
2. **New helper `_register_applied_files(pid, files)`**, called at the end of `_apply_approval_bg` and of the inline auto-approve apply path. For each approved path under `workspace/`:
   - `workspace_mw.sync_row(path)` indexes it (existing function).
   - If the file's header reads `delta over shared capability: shared/...`, it calls the existing `workspace_mw.add_dependency("project", pid, ...)` with `mode="extend"` and `overlay=<path relative to the project>`. That writes the manifest entry plus the `dependencies` and `shared_capabilities` rows.
   - Nothing else changes, and no new table is added.
3. **`workspace_mw.resolve_capability` (l.533):** check the overlay relative to the project folder first, then `code/<overlay>` as today. Existing manifests resolve, and nothing that resolves today stops resolving.

## What stays the same

- **Approval gate:** unchanged. Nothing is written without your approval, and VM commands are still never auto-run.
- **Approval files:** same format as today.
- **Database:** no schema change.
- **Folders:** no new folders.

**Risk:** low for 1 and 3; medium for 2, because it writes database rows. That uses the same functions the audit already uses.

## How it will be tested (cost estimate about $6, within the $40 cap; $18.29 used so far)

1. **Parser replay:** all 6 recorded transcripts must produce the correct proposal, 6/6 (no model cost).
2. **Unit check:** apply a test approval in the copy's own throwaway project. The file must be indexed, the manifest entry and `dependencies` row created, and `resolve_capability` true. Revealer's existing delta must still resolve.
3. **Regression suite:** must stay 31/32 with no new failures.
4. **Your end-to-end tests:** `phase7_lifecycle.py` and `phase7_strong.py`.
5. **Scenario S2 ×3**, rerun with owner approval through the UI path. **Pass condition:** the delta is written, registered in the manifest and database, and resolves, in 3/3 runs. The old project (Revealer) still resolves, and the audit shows 0 issues for both.
6. **MFI check:** the approval gate, proposal → approval, audit and lockstep rows behave exactly as in v1.

Then I report the before/after results and wait for your approval for fix #2 (G1, false success, covering all 42 chat mismatches).
