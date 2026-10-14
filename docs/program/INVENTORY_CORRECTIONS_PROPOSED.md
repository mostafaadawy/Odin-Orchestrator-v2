# Proposed inventory corrections (group C: 11 items). NOT applied; waiting for your review

**Rule:** nothing is applied until you approve it. **No feature is removed.** Every correction changes only a status or a note. Old wording is kept as "previously: …" so nothing is lost.

| # | Mismatch | Inventory row | BEFORE (now) | AFTER (proposed) | Evidence |
|---|---|---|---|---|---|
| 1 | CH0-1 | MFI l.904, "Test persistent chat memory" | PENDING | **VERIFIED-RUN (2026-06-22, chat)**. Previously: PENDING. | Chat 2e6a41cd6e97 @1782161107: a 2-turn recall test passed |
| 2 | CH0-2 | A-063, "Six specialist agents" | Six agents (Frontend, Backend, …) from `agents/*.agent.md` | Row kept. Note added: **"Superseded by the owner on 2026-07-08: the front/back split is the old version; Fullstack is one merged role (K1-101). The `.agent.md` files are stale but kept."** | company/d7a7b2bad54e @1783547762 |
| 3 | CH1-3 | MFI l.910, "Veeqo carrier-tracking fallback not built" | Open / not built | **BUILT and observed: Veeqo → EasyPost fallback** (`tracking-status.service.ts` → `getEasyPostConfig`). The tracking-source decision stays open. Previously: not built. | c8038d310db7 1785414074; 55f61b99d233 1785415484 |
| 4 | CH1-6 | MFI l.899, `CFG_BACKEND_MIG="reset"` | "reset" still set | **"new" (the one-time reset was reverted through an approved proposal; the deploy then passed)**, matching K5B-042. Previously: "reset". | d0127007bda4 / f7928b560cf6 1784962407 |
| 5 | CH2-8 | P-01, daily-egypt-amazon-product-poster | Code "NOT FOUND (only .gitkeep)"; schedule 09:00 | Note added: **"A working pipeline exists in the owner's Odin Testing/testing folder (CH2-016). A local launchd fires at 08:50; the project schedule says 09:00."** The launchd defect is F-24. | CH2-016 |
| 6 | CH2-10 | K5A-038, "Posts the 8 SOC lanes" | 8 lanes | **8 lanes in the explainer post; the CTO plan in the chats runs 13 lanes** (both recorded). | CH2-019 |
| 7 | CH3-1 | K2A-185, "background-run message is dead code" | Dead code | **UNDETERMINED:** the message appears in chats dated 2026-07-25. Either the code changed later or the path is live. To be settled by a run in Phase 6. | RDD chats 2026-07-25 |
| 8 | CH3-2 | P-08 / K-notes, SOC team size | "11-agent" (K) / 13 names (P-08) | **8 agents in every SOC chat (CTO plus 7 lanes); P-08's 13 names include aliases; the "11" in K-notes is unconfirmed.** | CH3 chats |
| 9 | CH5-2 | P-10, vm-sentinel | Schedule `{}` (empty) | **Config has an empty schedule, but daily runs at about 08:00 are seen on 2026-07-19, 07-24 and 07-25** (a trigger exists outside the project config). | CH5 chats |
| 10 | CH5-3 | T-17, Revealer | NestJS + Next.js app | **Delivered as a backend-only Python FastAPI service, no frontend (owner decision CH5-002).** The original test spec is kept as "previously". | CH5-002 |
| 11 | CH4-6 | A-229, SOC checks catalogue | Abuse = app DB / nginx | Note added: **"The owner moved the fake-user problem to the Klaviyo side (CH4-002). The catalogue has no vendor-side fake-contact check; SOC-EXT-006 tracks only quota."** This may also need a new check; that is your decision. | CH4-002 |
