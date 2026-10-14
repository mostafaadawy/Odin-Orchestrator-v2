# Odin-Orchestrator — Voice Module

Self-contained, local-first voice I/O for **English + Arabic**. Extracted from the
`mostafa-app` prototype with **no dependency** on it (safe to delete that folder).

See `VOICE-ANALYSIS.md` for the full analysis and the reuse/rebuild decision.

## Capabilities
- **STT:** local `faster-whisper` (offline, EN + AR, auto language detect).
- **TTS:** Kokoro neural (English) + macOS `Maged` / optional Piper (Arabic).
- **Privacy:** audio never leaves the machine (replaces the prototype's cloud Web Speech API).

## Enable (backend)
```bash
# in the Odin backend venv
pip install -r voice/backend/requirements-voice.txt
export USE_VOICE=1            # gate the heavy deps
# optional tuning:
export ODIN_WHISPER_MODEL=medium     # tiny|base|small|medium|large-v3
export ODIN_MAC_AR_VOICE=Maged       # macOS Arabic voice
# export ODIN_PIPER_AR_MODEL=/path/ar.onnx   # to use Piper instead of macOS say
```

Mount the router on a FastAPI app:
```python
from voice.backend.voice_service import build_router
app.include_router(build_router())   # adds POST /voice/stt and GET /voice/tts
```

## Endpoints
- `POST /voice/stt` — multipart `file` (audio), optional `?language=en|ar` → `{text, lang}`.
- `GET  /voice/tts?text=...&lang=en|ar` → `audio/wav`.

## Frontend
Import the hook and wire it to your chat input:
```ts
import { useVoice } from "@/voice/frontend/useVoice";
const { listening, toggleMic, speak } = useVoice({ lang: "ar" }); // or "en"
```
`toggleMic(setInput)` records → local Whisper → fills the input. `speak(reply)` plays TTS.

## macOS Arabic voice (one-time, for Arabic TTS default)
System Settings → Accessibility → Spoken Content → System Voice → Manage Voices → Arabic → **Maged**.

## Notes
- First Kokoro call downloads ~300 MB weights; first Whisper call downloads the model once.
- `__pycache__` is build output — exclude from packaging/commits.
