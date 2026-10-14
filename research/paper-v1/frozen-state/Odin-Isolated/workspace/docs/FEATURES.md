# Odin-Orchestrator — Features Built So Far

_What the application is and does today. Updated 2026-06-22. (Required deliverable — kept current
as we build.)_

## What Odin is
A local **CTO-Brain orchestration platform**: it wraps the Claude CLI (Claude Code) as its real
engine, adds an approval/safety gate, persistent memory, a specialist-agent router, bilingual
voice, and a live cockpit — and connects to the owner's Azure production VM read-only.

## Feature table

| # | Area | What it does today | Status | Key files |
|---|------|--------------------|--------|-----------|
| 1 | **Engine (core)** | Claude CLI (Claude Code) is the brain, running in the project with terminal tools (Read/Glob/Grep/Bash). Streams its live work. Ollama (qwen) is the offline fallback. | ✅ Live | `server/claude_cli.py`, `server/brain_handler.py` |
| 2 | **Local server / API** | FastAPI app: dashboard, chat, SSE streaming, persistent chats, voice, infra, health. | ✅ Live | `server/app.py`, `server/run.sh` |
| 3 | **Specialist router** | Routes a request to the right agent (Frontend/Backend/DevOps/Security/QA/Database) and decides read-vs-change. Now **semantic** (local model understands intent) with a deterministic keyword **fallback + safety floor**. | ✅ Live | `orchestrator/dispatcher.py`, `orchestrator/semantic_router.py` |
| 4 | **Approval / safety gate** | Read/compare/list run immediately; any state change must be proposed (command + impact + rollback) and approved in-conversation. Secrets/prod-data always gated. | ✅ Live | `CLAUDE.md`, `orchestrator/dispatcher.py`, `rules/core-rules.md` |
| 5 | **Persistent chats + memory** | JSON-per-chat store; new/rename/delete; conversation memory via resumed Claude session ids (survives refresh). | ✅ Live | `server/chats.py`, `dashboard/console.html` |
| 6 | **Live cockpit (UI)** | Streaming console: animated status steps with icons, token-by-token answers, markdown/table/code rendering, chat sidebar. | ✅ Live (HTML) | `dashboard/console.html`, `dashboard/odin-md.js` |
| 7 | **Voice I/O (EN + AR)** | Mic = browser Web Speech (en-US / ar-EG). TTS English = Kokoro (US), Arabic = Coqui XTTS-v2 — **offline, free, no API key, no macOS voice**. Clean speech (markdown stripped). | ✅ Live | `voice/backend/*`, `server/app.py` |
| 8 | **Azure VM connection** | Reaches the production VM through the Azure control plane (`az vm run-command`, no SSH/key/IP). Read-only inspection live; changes gated. | ✅ Live | `server/infra_az.py`, `infra/azure/connection.profile.json` |
| 9 | **Infra helpers** | Public-IP detect, SSH reachability, NSG IP-rotation scaffolding (built, used only if needed). | ⚙️ Built | `server/infra_ssh.py`, `server/infra_rotate.py` |
| 10 | **Mobile access (basic)** | Mobile cockpit + shared-secret token gate (header or query). | ⚙️ Basic | `dashboard/mobile.html`, `runbooks/phone-access.md` |
| 11 | **Agent definitions** | The 6 specialists defined with triggers/responsibilities. | ✅ Live | `agents/*.agent.md` |
| 12 | **Rules + history/audit** | Core rules (memory), append-only decision log (ADRs), pending backlog. | ✅ Live | `rules/core-rules.md`, `history/log.jsonl`, `PENDING.md` |

## v0.4 — Premium desktop app + scoped org (NEW, built 2026-06-22)

| # | Area | What it does | Status | Key files |
|---|------|--------------|--------|-----------|
| 13 | **Desktop app** | Electron + React + Vite + Framer Motion. Premium dark UI; boots the backend; one command. | ✅ Built | `desktop/` (`App.jsx`, `electron/main.cjs`) |
| 14 | **Company dashboard** | Big chat (company scope), live statuses, all projects, agents-live count, new project. | ✅ Built | `desktop/src/views.jsx` (Dashboard) |
| 15 | **Scoped multi-agent org** | company → project:<id> → member:<pid>:<agent> scopes, each its own pool; upward sync; drill-down. | ✅ Built | `server/scopes.py` |
| 16 | **Delegation + live activity** | Project CTO delegates a turn to the responsible member; heartbeat avatars; flow rail. | ✅ Built | `server/api_v2.py` (`_scoped_gen`), `server/activity.py` |
| 17 | **Projects** | Create from description (engine plans components), select local folder, registry. | ✅ Built | `server/projects.py` |
| 18 | **Agents + rules engine** | Add member by description (suggest name), per-project skills folder, restrictions, save-as-rule, interrupt chat. | ✅ Built | `server/agents_registry.py`, MemberView |
| 19 | **Usage stats** | Per-agent invocation counts + % of work, animated bars. | ✅ Built | `agents_registry.stats`, views.jsx |
| 20 | **Per-scope model control** | Pick model for main / project / member (cheap local vs paid). | ✅ Built | `server/models_config.py` |
| 21 | **Folder mapping + sync/deploy** | Map local↔cloud; sync dry-run + deploy proposal (gated, .env-excluded). | ✅ Built (gated) | `projects.sync_proposal/deploy_proposal` |
| 22 | **Per-project scheduling** | Schedule prompts daily / interval / once; background runner. | ✅ Built | `server/scheduler.py` |
| 23 | **Multi-level chat + voice** | Chat at every scope; Whisper mic + Kokoro/Coqui speech; markdown render. | ✅ Built | `desktop/src/ChatPanel.jsx` |

## Still parked (by owner's choice)
- **Mobile / phone-terminal connection** — owner kept this pending.
- **Turnkey one-click VM deploy** — intentionally left as a *gated proposal* (owner: "not rigid
  enough to touch running sites"); execution still requires explicit in-chat approval.
