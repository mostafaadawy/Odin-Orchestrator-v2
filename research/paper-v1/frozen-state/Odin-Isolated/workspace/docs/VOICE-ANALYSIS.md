# Voice System Analysis & Recommendation (Step 1)

**Date:** 2026-06-21 · **Author:** CTO Brain · **Source analyzed:** `mostafa-app/` (to be deleted)
**Target:** integrate a dependency-free voice stack into `Odin-Orchestrator/voice/`.

---

## 1. What the `mostafa-app` voice system actually is

I read the real implementation, not the README claims. Findings:

### Speech-to-Text (STT)
- Implemented entirely in the browser via the **Web Speech API**
  (`webkitSpeechRecognition`) in `frontend/app/page.tsx`, hardcoded `rec.lang = "en-US"`.
- **It is not a local model.** In Chrome the Web Speech API streams microphone audio to
  **Google's servers**; in Safari, to Apple's. Nothing runs offline.
- **English-only** as written. There is **no Arabic STT** anywhere in the code.

### Text-to-Speech (TTS)
- Primary path: **Kokoro** neural TTS (~82M params, ~300 MB weights, 24 kHz mono) in
  `backend/tts.py`, served at `GET /api/tts`, gated by `USE_KOKORO=1`. Configured
  `lang_code="a"` → **American English only**; default voice `af_heart`.
- Fallback path: browser `SpeechSynthesis` using macOS native voices (Samantha, etc.),
  and the fallback code **filters for English voices only**.
- **Arabic TTS is effectively absent.** Kokoro as configured (and as a model) does not
  produce Arabic, and the browser fallback selects English voices.

### Verdict on the "English + Arabic, two versions" claim
The working, real capability is **English-only**: Kokoro English TTS (good) + cloud
browser STT (English). The "Arabic version" is not backed by the code. This matters a lot
for a fintech product that needs genuine Arabic support and must keep audio private.

---

## 2. Performance on MacBook Pro M4 / 24 GB

| Component | Footprint | M4 verdict |
|-----------|-----------|------------|
| Kokoro TTS (82M) | ~300 MB weights, <1 GB RAM | Excellent — real-time, trivial load |
| Browser Web Speech STT | ~0 local (cloud) | Fast but **off-device / privacy risk** |
| (context) Qwen2.5-14B Q4 LLM | ~8.5 GB | Heavy but separate from voice |

The M4/24 GB has ample headroom to run a **local** STT model alongside the LLM, which the
prototype never did. There is no performance reason to keep audio in the cloud.

---

## 3. Recommendation: **Hybrid — reuse the good part, rebuild the weak part**

- **Reuse (as-is):** Kokoro English TTS — `tts.py` is self-contained, M4-friendly, and high
  quality. Extracted into `voice/backend/tts.py` with zero links back to `mostafa-app`.
- **Rebuild:** STT. Replace the cloud, English-only Web Speech API with **local
  faster-whisper** (`medium`, int8) which transcribes **English and Arabic offline** on the
  M4 (~1.5 GB RAM, near real-time). This is the single most important upgrade — it gives us
  real Arabic, and it keeps potentially sensitive audio on-device (fintech requirement).
- **Add:** real **Arabic TTS**. Default to the macOS built-in `Maged` voice via `say`
  (zero install, offline). Optional upgrade path documented for **Piper** Arabic (neural,
  small, M4-friendly) when higher quality is wanted.

Why not "reuse everything"? The STT is cloud-bound and English-only — wrong for our needs.
Why not "rebuild everything"? Kokoro English TTS is already excellent; rebuilding it would
waste effort and lose quality.

---

## 4. What was extracted into Odin (dependency-free)

```
voice/
├── backend/
│   ├── tts.py                 # Kokoro English TTS — reused, self-contained
│   ├── voice_service.py       # NEW: Whisper STT (EN+AR) + lang-aware TTS + FastAPI router
│   └── requirements-voice.txt # faster-whisper + kokoro + torch + soundfile
├── frontend/
│   └── useVoice.ts            # NEW: cleaned React hook; local STT first, EN/AR aware
├── VOICE-ANALYSIS.md          # this document
└── README.md                  # how to enable + run
```

**Dependency check performed:** `tts.py` imports nothing from `mostafa-app`
(`agent/models/crypto/scheduler/main`); the whole `voice/` tree has zero references to the
old project. Python modules compile clean. After integration, `mostafa-app/` can be deleted
and the Odin voice stack will keep working.

---

## 5. Status & what's still pending
- ✅ Reusable voice components extracted and re-architected for EN + AR, local-first.
- ⏳ **Wiring into a running Odin backend/frontend is still pending** — it depends on the
  Brain↔agent connection layer, the mobile dispatcher, and the end-to-end voice I/O loop,
  which are open items (see the Step 4 summary).
