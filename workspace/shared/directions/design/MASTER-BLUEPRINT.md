# Odin-Orchestrator — Master Blueprint (premium desktop app)

_Consolidates the full product vision (2026-06-22). Anchored on the **scoped multi-agent org**
(`SCOPED-MEMORY-SPEC.md`) as the backbone that completes it. Hard rule: **preserve everything
already built — nothing breaks.**_

## Decisions (made, can be vetoed cheaply)
- **Desktop app:** Electron + React + Vite + Tailwind + Framer Motion. Premium dark UI, real
  "alive" agent animations. (Tauri = lighter-native alternative.)
- **Backend:** reuse the existing FastAPI server (engine, voice, chats, Azure, gate) — extended,
  not rewritten. The desktop app is a new front-end + new backend modules on top.
- **Order:** backbone (scoped org + projects + multi-level chat) first; visuals, agent
  management, models, ops, scheduling attach to it.

## Requirement → feature map
| Your requirement | Where it lands |
|---|---|
| Large chat (~40%), statuses, project list, modern pro UI | Phase 1 — desktop shell + main dashboard |
| Open project → agent switches context; chat stays in project scope | Phase 2 — scoped org |
| Create project from description → auto-generate components | Phase 2/4 — project create + agent gen |
| Real-time animated indicators of which agents are active per project; flow FE→BE→Dev | Phase 3 — live cockpit |
| Per-project page; click member → exactly what that agent does, full detail | Phase 3 — member detail pages |
| Each member = character w/ distinct avatar; heartbeat animation when working | Phase 3 — agent characters |
| Member detail: tools/tech in use, tasks, progress; navigate back/forth | Phase 3 |
| Add member to a project; usage stats (% FE vs BE vs deploy, counts) | Phase 4/5 — agent mgmt + stats |
| Add member by description → system suggests a name | Phase 4 |
| New role registered into the brain (purpose/skills/restrictions); per-project skills folder; suggest agents on repeat patterns; "save as permanent rule" prompts | Phase 4 — skills/rules engine |
| Interrupt a working member, correct mid-task, agree fix, save as rule | Phase 4 — interrupt + correction loop |
| Per-member / per-project / main-brain model selection (cheap vs paid) | Phase 5 — model control |
| Direct terminal + CLIs (Azure, Cloudinary); self-heal or ask; monitor own status | Phase 6 — ops + self-healing |
| Create new project OR map existing local folders → cloud; sync local→cloud; deploy to VM | Phase 6 — project ops (completes parked VM-sync) |
| Strong modern tools, premium clean dark UI/UX | Cross-cutting — design system |
| Preserve all prior work; nothing breaks | Cross-cutting — regression guard each phase |
| Keep voice/speech humanization; richer "alive" animation when speaking/working | Cross-cutting — Phase 3 animation + existing voice |
| Document all built features in a table | Done now — `FEATURES.md` (kept current) |
| Multi-level consistent chat (main brain / project / member), interconnected; project chat sees member chats | Phase 2 — multi-level chat |
| Schedule tasks per project (in project chat + from dashboard); time/recurring | Phase 7 — scheduling |

## Architecture (target)
```
Electron desktop app  (React + Tailwind + Framer Motion, dark premium)
  ├─ Company dashboard  : all projects, global statuses, big chat (40%), live agent indicators
  ├─ Project page       : that project's CTO chat, assigned members, flow, usage stats, schedule
  └─ Member detail page : avatar + heartbeat, tools/tasks/progress, interrupt chat, model picker
        │  (all talk over HTTP/SSE to →)
FastAPI backend (existing, extended)
  ├─ engine: Claude CLI (primary) + Ollama (fallback)            [exists]
  ├─ router: semantic + keyword floor                            [exists]
  ├─ approval gate + rules (CLAUDE.md, core-rules)               [exists]
  ├─ voice (Kokoro EN / Coqui AR, offline)                       [exists]
  ├─ Azure VM via az run-command                                 [exists]
  ├─ NEW: scope/memory store  (company / project:<id> / member:<project>:<agent>)
  ├─ NEW: project registry + folder↔cloud mapping + sync/deploy
  ├─ NEW: agent registry + per-project skills/rules folders
  ├─ NEW: per-scope model config
  └─ NEW: scheduler (per project, time/recurring)
```

## Phased roadmap (each phase verified; nothing prior broken)
- **Phase 0 — Plan & inventory (this):** blueprint + `FEATURES.md` table + preserve guarantee.
- **Phase 1 — Desktop shell:** Electron+React premium dark app; main dashboard (big chat reuse,
  statuses, project list); wraps existing backend; current cockpit/voice still work.
- **Phase 2 — Scoped org backbone:** project scoping/switching, Company→Project→Member memory
  scopes, multi-level interconnected chat, upward sync. (Solves the parked core task.)
- **Phase 3 — Live agent characters:** avatars per role, heartbeat/alive animations, real-time
  active-agent + flow indicators, member detail pages, usage stats.
- **Phase 4 — Agent management & rules:** add member by description (suggest name), register role
  into brain + per-project skills folder, per-agent rules/restrictions, save-as-rule prompts,
  interrupt + correct-and-save loop.
- **Phase 5 — Model control:** per-member / per-project / main-brain model selection, cost-aware.
- **Phase 6 — Project ops & self-healing:** local folder mapping, create-new/select-existing,
  local↔cloud sync, deploy to VM, CLIs (Azure/Cloudinary), connection monitoring + self-heal.
- **Phase 7 — Scheduling:** per-project scheduled/recurring tasks, from chat and dashboard.

## Preserve guarantee
Each phase ends with a regression check that the existing engine, router, approval gate, voice,
persistent chats, and Azure connection still pass. Parked items kept: mobile/phone terminal.
