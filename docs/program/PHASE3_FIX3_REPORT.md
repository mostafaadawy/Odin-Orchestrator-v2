# Phase 3, fix #3 (F-23 approval bypass): before and after report

**Applied in:** Odin-Consolidated only. Tags `fix3-start` (a8ff6fb) → **`fix3-done` (805e25a)**. Changed file: `server/api_v2.py`. CHANGELOG entry added.

## Root cause (confirmed)

The chat rule "a message containing *approve(d)* approves ALL pending" also ran on Odin's **own** text.
- After applying an approved change, Odin posts "[system] The gate you proposed was **APPROVED** and applied…" into the project chat.
- That message matched the rule.
- Every other pending proposal was then approved and applied. In S2 r5 this hit `dc13fbd7`, 34 s after you approved `8206a5ef`.

## Your four rules, as implemented

1. **A chat "approve" applies only to the proposal named by its id, or the one being replied to.** If there is no id, nothing is approved and the pending ids are listed.
2. **Only your own chat message can approve.** This is the owner endpoint, also used by the Anchor poller for your phone. Odin's follow-ups, scheduled goals, agents, and any message in "[…]" system format can never approve.
3. **Older pending proposals stay pending.** "approve all" in chat no longer bulk-approves.
4. **Test** (below).

## Results

| Test | Before (`fix3-start`) | After (`fix3-done`) |
|---|---|---|
| **The 34-second case, scripted:** you approve B, then Odin's own follow-up is posted | **REPRODUCED:** the older proposal A was approved 0.04 s after the follow-up, without you | **A stays pending** |
| No id → nothing approved, ids listed | — | PASS |
| "approve <id>" → only that one | — | PASS |
| `reply_to` → only the replied-to one | — | PASS |
| System/agent-format text, even with an id → nothing | — | PASS |
| Internal caller, even with an id → nothing | — | PASS |
| "approve all" in chat → nothing bulk-approved | — | PASS |
| **Live S11** (operational project, 2 proposals; you approve only the newer one; Odin auto-continued) | — | **Older proposal still pending after 91 s.** The auto-continue was seen; the newer one was applied. |
| Regression suite | 32/32 | **32/32** |
| Your end-to-end tests | ALL GREEN 1/1 | **ALL GREEN 3/3 each** |

## Behaviour changes, flagged

- Typing just "approve" in a project chat now replies with the pending ids instead of approving everything. The popups and the phone's Approve buttons are unchanged: they already approve one id each.
- **F-33 (new, your decision):** a separate **"Approve all" button endpoint** (`/approvals/approve-all`, non-security items) still exists. It is your own explicit button, but it conflicts with rule 3 ("individually"). Keep, remove, or require a confirmation?
- **Note:** anyone holding the Anchor key could send a chat "approve <id>" through the phone path. That key ships in the DMG today (F-14, F-04). The F-14 Keychain fix closes it.

STATUS
- Phase and step: Phase 3, step 3.3 (fix #3) done, waiting for your approval
- Done this step: F-32 + G2 (approved; fail-safe F-32b/F-32c verified), F-23 (verified by runs)
- Still open in this phase: 34. P8-2, G5, G6, G7, G8, F-07, G11, G12, G9, G10, G13, F-06, F-08, F-14, F-18, F-23, F-24…F-31, F-03, F-04, F-05, F-10, F-11, F-16, F-20, F-21, F-26, F-33. Plus the 11 inventory corrections (group C of F-18).
- Still open overall: 94; waiting for your decision: F-23, F-33, F-03, F-04, F-05, F-10, F-11, F-16, F-20, F-21, F-26
- New items added this step: F-33
- Budget: $45.99 of $100
- Paper v1 fingerprint: unchanged
- v1 (Odin-Orchestrator): unchanged
- Next step: your approval of fix #3, then the audit fixes one at a time (G6 first)
