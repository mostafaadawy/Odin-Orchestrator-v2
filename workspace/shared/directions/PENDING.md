# PENDING — Open Items (revisit after every task)

_Last reviewed: 2026-06-22._

## Done ✅
- Foundation, rules, history/audit, 6 agents, approval gate
- Dashboard + **streaming cockpit** + **persistent chats with memory** (sidebar: new/rename/delete)
- Voice: English (Kokoro) + Arabic (Coqui XTTS), offline
- **Claude CLI = the engine**, with terminal access (az/ssh/bash) — self-solves, gated for changes
- Mobile access (basic) + token gate
- **Azure VM connected** (django-vm / DJANGO-PROJECT) — read-only inspection LIVE via az run-command

## Next — in the owner's stated order
1. **Test persistent chat memory** (immediate): restart Odin, hard-refresh cockpit, confirm a
   multi-turn thread holds context ("list mostafa folders" → "yes" → it continues).
2. **Phone terminal** (owner's #2 after VM): drive Odin + the VM from the phone as a real
   connected terminal (secure access on top of mobile.html). ← the planned next BUILD.

## Deferred / optional (owner's call)
- **Per-chat project scoping** — tie a chat to a project (organics, bendcore, …) so it works in
  that project's context. (Discussed; nice next.)
- **Deploy/sync to VM (.env-safe)** — owner said NOT yet ("not rigid enough to touch running
  sites"). Build when trust is there.
- **IP rotation (NSG + ufw)** — only needed for the scp path; az run-command doesn't need it.
- **Cockpit Phase C/D** — stream Claude's live tool activity + richer artifact rendering.
  (Owner deprioritized: "needs more trials, not now.")

## Done ✅ (2026-06-22 — full desktop build, all phases)
- **Scoped multi-agent org** BUILT — `server/scopes.py` (company→project→member pools, upward
  sync, drill-down) + delegation/activity in `server/api_v2.py`. The core vision is implemented.
- **Premium desktop app** BUILT — `desktop/` (Electron+React+Vite+Framer Motion).
- Projects, agents+rules, model control, scheduling, mapping, sync/deploy proposals — all built
  and verified (see FEATURES.md rows 13–23). Backend smoke + route + regression tests PASS;
  React bundle compiles.

## Parked — owner will recall later
- **Mobile / phone-terminal connection** — kept pending by owner.
- **Turnkey one-click VM sync/deploy execution** — currently a gated PROPOSAL (dry-run/plan),
  by owner's "not rigid enough to touch running sites" rule. Promote to one-click when trusted.
  Notes captured during the read-only comparison:
  - Mapped VM apps exist: `~/organics` (Next.js) and `~/bendcore` (NestJS+Prisma) — both have `.env`.
  - Neither VM folder is a git repo → a future diff must be content-based (rsync --dry-run / checksums), excluding `.env`/`node_modules`.
  - Profile casing fixed: `~/Bendcore` → `~/bendcore` (real dir is lowercase).
  - No local clones exist at the mapped paths yet.

## Blocked on owner
- **Custom subscription/billing model** — only the owner can specify it (placeholder in
  `core-rules.md §6.1`).
