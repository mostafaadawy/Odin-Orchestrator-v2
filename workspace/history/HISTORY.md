# HISTORY.md — Running Audit Log

> Human-readable source of truth for decisions and changes. Machine-readable mirror in
> `log.jsonl`. Newest entries at the top. Every entry is timestamped (UTC).

---

## 2026-06-21 — Dispatcher + mobile access (pending backbone items finished)

- **2026-06-21T14:00Z · BUILD · ADR-008** — Built the Brain↔agent **dispatcher**
  (`orchestrator/dispatcher.py`): deterministic classify → load-rules → approval-check →
  lifecycle hooks → route. Wired into the server as `/dispatch` and as the Brain behind
  `/chat` + the voice loop. Routing telemetry → `history/routing.jsonl`.
- **2026-06-21T14:00Z · BUILD** — Mobile access: `dashboard/mobile.html` (phone voice+chat),
  optional `ODIN_ACCESS_TOKEN` gate on `/chat`,`/dispatch`,`/voice/*`, and
  `runbooks/mobile-access.md` (LAN now; internet exposure approval-gated via Azure procedure).
- **2026-06-21T14:00Z · VERIFY** — Routing unit tests pass (6/6); live: `/chat` 401 without
  token / 200 with token; gated request returns an approval message (not executed);
  `/dispatch` returns routing JSON with hooks fired; `/mobile.html` served; non-gated request
  degrades gracefully without Ollama.
- **2026-06-21T14:00Z · NOTE** — All three backbone pending items (connection, mobile, voice)
  now built and wired. See `PENDING.md` for suggested next items.
- **2026-06-21T14:00Z · SNAPSHOT** — `snap-0004-dispatcher-mobile`.

---

## 2026-06-21 — Voice wired into dashboard (local server)

- **2026-06-21T12:00Z · BUILD** — Added `server/` (FastAPI): serves dashboard + `/voice/stt`
  (Whisper) + `/voice/tts` (Kokoro EN / Piper AR) + `/chat` (local Ollama via pluggable
  `brain_handler`). Added a Voice Console panel to `dashboard/index.html`
  (mic → STT → Brain → TTS, EN/AR toggle).
- **2026-06-21T12:00Z · DECISION · ADR-007** — Voice host = dashboard via local server; brain
  handler = Ollama now, pluggable for the future dispatcher; Arabic TTS = Piper (macOS say
  fallback).
- **2026-06-21T12:00Z · VERIFY** — Server boots; `/health` 200; `/chat` 200 with graceful
  fallback when Ollama absent (EN+AR); `/voice/stt` and `/voice/tts` routes confirmed;
  dashboard + `/state` served. STT/TTS/LLM exercised on the Mac (deps not in sandbox).
- **2026-06-21T12:00Z · SNAPSHOT** — `snap-0003-voice-wired`.

---

## 2026-06-21 — Voice analysis, Ruflo comparison, Azure procedure

- **2026-06-21T00:00Z · BUILD** — Extracted a dependency-free voice module into `voice/`:
  reused Kokoro English TTS (`tts.py`), added local faster-whisper STT (EN+AR), Arabic TTS
  (macOS `say`/Piper), language-aware service + frontend hook. Verified zero references to
  `mostafa-app`; Python compiles clean. See `voice/VOICE-ANALYSIS.md`.
- **2026-06-21T00:00Z · DECISION · ADR-004** — Voice stack is hybrid (reuse TTS, rebuild STT
  locally for EN+AR, on-device only).
- **2026-06-21T00:00Z · NOTE** — Finding: the prototype's "Arabic version" was not backed by
  code; STT was cloud Web Speech (EN-only). Corrected in our rebuild.
- **2026-06-21T00:00Z · DECISION · ADR-005** — Ruflo review: adopt hooks + lean dispatcher +
  (later) local semantic memory; reject swarm scale, self-evolving rules, stub tools. See
  `RUFLO-COMPARISON.md` (incl. sourced community feedback: ~97% stub tools, broken verify).
- **2026-06-21T00:00Z · DECISION · ADR-006** — Encoded the strict Azure dynamic-IP procedure
  (`runbooks/azure-secure-connection.md`): two-place IP update, systemd (not PM2), scp,
  folder mapping organics↔organics & organics-backend↔Bendcore, approval-gated.
- **2026-06-21T00:00Z · NOTE** — Pending items tracked in `PENDING.md`: Brain↔agent
  connection, mobile dispatcher, end-to-end voice. To be revisited after every task.
- **2026-06-21T00:00Z · SNAPSHOT** — `snap-0002-voice-ruflo-azure`.

---

## 2026-06-20 — Phase 1: Foundation established

- **2026-06-20T00:00Z · DECISION · ADR-001** — Adopted `Odin-Orchestrator/` structure
  (rules + history + agents + approvals + dashboard + runbooks + infra). _By: CTO Brain._
- **2026-06-20T00:00Z · BUILD** — Created folder tree and foundational files:
  `README.md`, `config/system.config.json`, `config/project.config.json`,
  `rules/core-rules.md`, `orchestrator/ORCHESTRATOR.md`, history system.
- **2026-06-20T00:00Z · DECISION · ADR-003** — Azure VM access will run via sandboxed
  shell over key-based SSH (no dedicated MCP connector exists), gated by approvals.
  _Pending owner-provided access details._
- **2026-06-20T00:00Z · NOTE** — Custom subscription/billing model recorded as a
  PLACEHOLDER in `core-rules.md §6.1`; orchestrator will not assume standard recurring
  billing until the owner specifies the real model.
- **2026-06-20T00:00Z · SNAPSHOT** — `snap-0001-phase1-foundation` created as the first
  restore point.

---

### Entry format

```
YYYY-MM-DDTHH:MMZ · TYPE · [ref] — summary. _By: actor._
TYPE ∈ DECISION | BUILD | CHANGE | PROBLEM | SOLUTION | APPROVAL | SNAPSHOT | REVERT | NOTE
```
