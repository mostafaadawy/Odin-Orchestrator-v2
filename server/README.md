# Odin-Orchestrator — Local Server (Voice wired into the dashboard)

Runs the dashboard **and** the end-to-end voice loop on your Mac:

```
mic → /voice/stt (local Whisper, EN+AR) → /chat (local Ollama) → /voice/tts (Kokoro EN / Piper AR) → speaker
```

The brain handler is **pluggable** (`server/brain_handler.py`): today it calls Ollama; when
the Brain↔agent dispatcher is built, swap in an object exposing `respond(text, lang)` — the
voice loop and dashboard don't change.

## One-time setup
```bash
cd Odin-Orchestrator
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r server/requirements.txt
pip install -r voice/backend/requirements-voice.txt     # Whisper + Kokoro (~2 GB)
```

Ollama (local LLM):
```bash
brew install ollama && brew services start ollama
ollama pull qwen2.5:7b-instruct-q4_K_M      # default; or set ODIN_OLLAMA_MODEL
```

### Arabic TTS via Piper (chosen engine)
```bash
pip install piper-tts
mkdir -p ~/piper-voices && cd ~/piper-voices
# Download an Arabic voice (example) — model + its .json config must sit together:
#   ar_JO-kareem-medium.onnx  +  ar_JO-kareem-medium.onnx.json
# from the Piper voices catalog (rhasspy/piper-voices on HuggingFace).
export ODIN_PIPER_AR_MODEL="$HOME/piper-voices/ar_JO-kareem-medium.onnx"
```
If `ODIN_PIPER_AR_MODEL` is unset, Arabic falls back to the macOS `Maged` voice.

## Run
```bash
USE_VOICE=1 ./server/run.sh
# open http://localhost:8000/   → use the "Voice Console" card at the top
```

## Endpoints
| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/` | Dashboard + Voice Console |
| POST | `/voice/stt?language=en\|ar` | audio file → `{text, lang}` (local Whisper) |
| GET  | `/voice/tts?text=...&lang=en\|ar` | → `audio/wav` (Kokoro EN / Piper AR) |
| POST | `/chat` | `{text, lang}` → `{reply}` (Ollama; dispatcher later) |
| GET  | `/health` | readiness + config |

## Env knobs
`USE_VOICE=1` · `ODIN_OLLAMA_MODEL` · `ODIN_WHISPER_MODEL` (tiny…large-v3) ·
`ODIN_PIPER_AR_MODEL` · `ODIN_MAC_AR_VOICE` (fallback).

## Notes / limits
- Browser mic capture needs `localhost` (a secure origin) — which `run.sh` uses.
- This is local-only and unauthenticated by design; add auth before any network exposure
  (and never bypass the Azure approval gate to expose it).
- The voice loop is **record → stop → process** (not live streaming) in v1.
