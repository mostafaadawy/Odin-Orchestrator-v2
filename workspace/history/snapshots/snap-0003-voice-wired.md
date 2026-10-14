# Snapshot: snap-0003-voice-wired

**Created (UTC):** 2026-06-21T12:00:00Z
**By:** CTO Brain
**Reason:** Restore point after wiring voice end-to-end into the dashboard via a local server.

## What changed since snap-0002
- Added `server/` — `app.py` (FastAPI: dashboard + `/voice/stt` + `/voice/tts` + `/chat` +
  `/health`), `brain_handler.py` (pluggable Ollama handler), `requirements.txt`, `run.sh`,
  `README.md`.
- `dashboard/index.html` — added the **Voice Console** panel (mic → STT → Brain → TTS,
  EN/AR toggle) that talks to the backend; static view degrades gracefully.
- `voice/backend/voice_service.py` — Arabic TTS now prefers **Piper** (macOS `say` fallback).
- `rules/core-rules.md` ADR-007; `PENDING.md` voice marked wired; history + state updated.

## Verified
Server boots; `/health` 200; `/chat` 200 with graceful EN+AR fallback when Ollama absent;
`/voice/stt` (422 on missing file) and `/voice/tts` routes present; dashboard + `/state` served.

## To revert here
Follow `runbooks/revert.md` (a pre-revert snapshot is taken first, so this is reversible).
