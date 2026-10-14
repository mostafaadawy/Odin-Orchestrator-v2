# Conversational Cockpit — Full Requirements & Architecture Spec

> Master record of the owner's requirements. NOTHING here is to be discarded.
> Last updated: 2026-06-21.

## Guiding principle
The Odin window is an **enhancement layer** around **Claude CLI** (Claude Code). Claude CLI is
the **main player / core engine** — it was the design from the first prompt, and the Ruflo
reference is exactly this: wrap Claude Code, keep the good parts, replace the bad. We **never
limit** Claude CLI; we **surface and elevate** it with a fast, humanized, transparent front.

---

## A. Engine & integration — "humanized, fast, harmonized" (owner's words)

A1. **Claude CLI is the core engine.** Real answers/work come from Claude Code running on the
    project folder (reading real files, real data). NOT a generic local LLM.
A2. **Two brains, harmonized:**
    - **Fast front (local, instant)** — handles greetings, simple/general questions, and
      narrates progress. Feels like talking to a real partner.
    - **Claude CLI (engine)** — does the heavy, professional work when needed.
A3. **Triage every message:**
    - If the question is **general / answerable directly** → reply **immediately**, fast.
    - If it **needs a lot of info or real project work** → it does NOT vanish; it **asks**
      "do you want me to go deeper / pull more info?" and waits for the owner's **yes**.
A4. **On "yes" → call Claude CLI** to do the real work on the project.
A5. **Intermediary that keeps me company:** while the engine works it says things like
    "one moment… we're processing… reading the project… almost done." The owner is **never
    isolated** and never left guessing.
A6. **Fast & nimble** — not a slow heavy "train"; a small, quick intermediary that gives
    indications and shows capabilities.
A7. **Approval gate** still applies to anything that writes/changes code/config/VM.

---

## B. UI modifications — exactly as described (do NOT discard)

B1. **Bigger window.** The current chat card is too small. The console must be large enough to
    see the interaction and what's going on.
B2. **See the real processor working** — live visibility into what Claude CLI is doing behind
    the scenes (not hidden).
B3. **Nice styling + animated responses** — polished, animated, alive (not a static frozen box).
B4. **Live logs + icons + status steps** so the owner can SEE progress:
    🧠 thinking · 🔎 reading files · ⚙️ running · 🛰️ contacting VM (gated) · ✅ done.
B5. **Continuous progress indicators** — every step shows something; never a boring/"deceiving"
    silent wait. (This is explicitly called out as the current window's worst flaw.)
B6. **Streamed answers** — text types in as it's produced, then is spoken (voice).
B7. **Artifact rendering — proper styles:**
    - If Claude CLI returns **code** → show it as a **styled, syntax‑highlighted code block**
      (with filename + copy button) back in the window.
    - If it returns a **document** → render it as a **formatted document**, not raw text.
    - Whatever file/artifact the engine produces appears in the window in its right style.
B8. **The window must represent these capabilities well** — it is the face of the whole system.

---

## C. Voice (DONE — accepted by owner)
- English = Kokoro (US accent). Arabic = Coqui XTTS‑v2 (offline, no API key).
- Mic = browser speech (instant, great Arabic). No macOS voice anywhere. Latency accepted.

## D. Backbone (DONE)
- Dispatcher (triage + approval gate + hooks), mobile access, dashboard, audit/history, rules.

---

## Architecture to deliver A & B
- **Transport:** Server‑Sent Events (SSE) so the console updates live (status, logs, tokens).
- **Bridge:** the dispatcher spawns `claude` with streaming output (`--output-format
  stream-json`), parses each event (assistant text, tool_use, tool results), and forwards them
  as nicely‑styled SSE events (icons, logs, progress) to the console.
- **Fast front:** local model answers simple messages and narrates while Claude CLI works.
- **Renderer:** console parses streamed events → animated status steps + activity log +
  streamed answer + artifact panels (code highlight / document view).

## Build phases (each ends with something visible to test)
- **A. Streaming animated console** — big window + SSE; animated status steps & icons; live
  activity log; token‑streamed answers; voice on final.
- **B. Triage + "go deeper?" confirmation** — fast direct answers vs. confirmed deep work.
- **C. Claude CLI bridge (live)** — stream Claude Code's real steps/tools/logs into the panel.
- **D. Artifact rendering** — code (highlight + copy) and documents, styled.

## Non‑negotiables (owner)
- Claude CLI is the engine; never limited, always surfaced.
- Never leave me in a silent/frozen window — always show live progress.
- Fast, humanized, harmonized conversation.
- Keep the approval gate for code/config/VM.
