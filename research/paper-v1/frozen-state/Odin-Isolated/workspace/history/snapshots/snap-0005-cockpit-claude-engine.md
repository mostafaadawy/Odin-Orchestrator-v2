# Snapshot: snap-0005-cockpit-claude-engine
**Created:** 2026-06-21 · **By:** CTO Brain
**Reason:** Claude CLI engine + animated streaming Cockpit (Phase A) live and accepted.

## State
- Engine = Claude CLI (Claude Code 2.1.185), dispatcher auto-detects; Ollama = fallback.
- Cockpit: dashboard/console.html (SSE /chat/stream, animated status icons, token streaming,
  code-block rendering, voice). /health reports active engine.
- Voice: EN Kokoro, AR Coqui XTTS-v2 (offline). Accepted.
- Backbone: dispatcher + approval gate, mobile, dashboard, audit/history, rules.

## Revert
runbooks/revert.md (a pre-revert snapshot is taken first).
