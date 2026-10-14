"""
Odin-Orchestrator — Voice Service (self-contained).

Extracted and rebuilt from the mostafa-app voice prototype. There is NO runtime
dependency on mostafa-app — this module stands alone and can be mounted on the Odin
backend FastAPI app, or run standalone.

Provides language-aware voice I/O for English + Arabic, fully local on Apple Silicon:

  STT  POST /voice/stt   (audio file)        -> {"text": ..., "lang": ...}
       local faster-whisper (offline, EN + AR). Replaces the old browser Web Speech
       API, which sent microphone audio to Google/Apple cloud servers — unacceptable
       for a fintech product handling sensitive context.

  TTS  GET  /voice/tts?text=...&lang=en|ar   -> audio/wav
       English -> Kokoro neural TTS (reused from prototype, see tts.py).
       Arabic  -> macOS `say -v Maged` (zero-install) or Piper (optional upgrade).

Enable heavy deps with USE_VOICE=1 and install voice/backend/requirements-voice.txt.
"""
# NOTE: intentionally NOT using `from __future__ import annotations` — FastAPI's File/UploadFile
# params must be real annotation objects, not strings, for pydantic v2 to resolve them.

import io
import os
import shutil
import subprocess
import tempfile
import logging

log = logging.getLogger("odin.voice")

# ---------------------------------------------------------------------------
# STT — local Whisper (faster-whisper), lazy-loaded
# ---------------------------------------------------------------------------
_whisper = None


def _load_whisper():
    """Lazy-load faster-whisper. 'medium' int8 is the EN+AR sweet spot on M4/24GB."""
    global _whisper
    if _whisper is not None:
        return _whisper
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "faster-whisper not installed. Run:\n"
            "  pip install -r voice/backend/requirements-voice.txt"
        ) from e
    model_size = os.environ.get("ODIN_WHISPER_MODEL", "medium")
    # int8 on CPU is the safest cross-version choice on Apple Silicon.
    _whisper = WhisperModel(model_size, device="cpu", compute_type="int8")
    log.info("Loaded faster-whisper '%s' (int8/cpu).", model_size)
    return _whisper


_whisper_fast = None


def _load_whisper_fast():
    """A SMALL/base model for near-real-time partials — much faster than 'medium'."""
    global _whisper_fast
    if _whisper_fast is not None:
        return _whisper_fast
    from faster_whisper import WhisperModel  # type: ignore
    size = os.environ.get("ODIN_WHISPER_FAST_MODEL", "base")
    _whisper_fast = WhisperModel(size, device="cpu", compute_type="int8")
    log.info("Loaded fast faster-whisper '%s' (int8/cpu) for live partials.", size)
    return _whisper_fast


def transcribe(audio_path: str, language: str | None = None, fast: bool = False) -> dict:
    """Transcribe an audio file. language None/""/"auto" -> auto-detect (handles EN + AR).
    fast=True uses the small model + lighter settings for live, near-real-time partials."""
    if language in (None, "", "auto"):
        language = None  # let Whisper detect EN vs AR — avoids garbage from a forced language
    model = _load_whisper_fast() if fast else _load_whisper()
    segments, info = model.transcribe(
        audio_path,
        language=language,
        beam_size=1 if fast else 5,     # fast = greedy (quicker); final = more accurate
        vad_filter=True,                # drop silence
        temperature=0.0,                # deterministic
    )
    text = "".join(seg.text for seg in segments).strip()
    return {"text": text, "lang": info.language, "lang_prob": round(info.language_probability, 3)}


# ---------------------------------------------------------------------------
# TTS — English (Kokoro) + Arabic (macOS say / Piper)
# ---------------------------------------------------------------------------
def synthesize(text: str, lang: str = "en", voice: str | None = None, speed: float = 1.0) -> bytes:
    """English -> Kokoro (American voice). Arabic -> Azure Neural EGYPTIAN voice
    (ar-EG-SalmaNeural). NO macOS voice, NO browser fallback (owner requirement)."""
    if str(lang).lower().startswith("ar"):
        from coqui_tts import synthesize as ar_synth    # Coqui XTTS-v2: free, offline, no key
        # XTTS Arabic is slow by default; speed it up. Honor the request's speed, else a sensible
        # faster default (override with ODIN_XTTS_SPEED). >1.0 = faster.
        import os as _os
        ar_speed = speed if (speed and speed != 1.0) else float(_os.environ.get("ODIN_XTTS_SPEED", "1.15"))
        return ar_synth(text, lang="ar", speed=ar_speed)
    from tts import synthesize as en_synth              # Kokoro, American English voice
    return en_synth(text, voice=voice or "af_heart", speed=speed)


def _synthesize_arabic(text: str) -> bytes:
    """
    Arabic TTS. PRIMARY path is Piper (neural) when ODIN_PIPER_AR_MODEL points at a .onnx
    voice and the `piper` binary is available — higher quality and fully offline. Falls back
    to the macOS built-in 'Maged' voice via `say` if Piper isn't configured.
    See server/README.md for the one-time Piper Arabic model download.
    """
    piper_model = os.environ.get("ODIN_PIPER_AR_MODEL")
    if piper_model:
        if not shutil.which("piper"):
            raise RuntimeError(
                "ODIN_PIPER_AR_MODEL is set but the `piper` binary is not on PATH. "
                "Install Piper (`pip install piper-tts`) or unset ODIN_PIPER_AR_MODEL to use "
                "the macOS fallback voice."
            )
        if not os.path.exists(piper_model):
            raise RuntimeError(f"Piper model not found: {piper_model} (see server/README.md).")
        return _piper_synthesize(text, piper_model)

    if not shutil.which("say"):
        raise RuntimeError(
            "Arabic TTS: configure Piper (set ODIN_PIPER_AR_MODEL to a .onnx voice) or run on "
            "macOS with the 'Maged' voice installed (System Settings > Accessibility > Spoken "
            "Content > System Voice > Manage Voices > Arabic)."
        )
    with tempfile.TemporaryDirectory() as d:
        aiff = os.path.join(d, "out.aiff")
        wav = os.path.join(d, "out.wav")
        voice = os.environ.get("ODIN_MAC_AR_VOICE", "Maged")
        subprocess.run(["say", "-v", voice, "-o", aiff, text], check=True)
        # Convert AIFF -> WAV using afconvert (ships with macOS).
        subprocess.run(["afconvert", "-f", "WAVE", "-d", "LEI16", aiff, wav], check=True)
        with open(wav, "rb") as f:
            return f.read()


def _piper_synthesize(text: str, model_path: str) -> bytes:
    """Optional high-quality Arabic via Piper CLI -> WAV bytes."""
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, "out.wav")
        proc = subprocess.run(
            ["piper", "--model", model_path, "--output_file", wav],
            input=text.encode("utf-8"), check=True,
        )
        with open(wav, "rb") as f:
            return f.read()


# ---------------------------------------------------------------------------
# Optional: FastAPI router (mount on the Odin backend when one exists)
# ---------------------------------------------------------------------------
def build_router():
    """Return an APIRouter exposing /voice/stt and /voice/tts. Import-safe: only
    pulled in when the backend explicitly mounts voice."""
    from fastapi import APIRouter, UploadFile, File, Query, HTTPException, Response

    router = APIRouter(prefix="/voice", tags=["voice"])

    @router.post("/stt")
    async def stt(file: UploadFile = File(...), language: str | None = Query(None),
                  fast: int = Query(0)):
        if os.environ.get("USE_VOICE", "0") != "1":
            raise HTTPException(503, "Voice disabled. Set USE_VOICE=1 and install requirements-voice.txt.")
        with tempfile.NamedTemporaryFile(delete=True, suffix=".webm") as tmp:
            tmp.write(await file.read())
            tmp.flush()
            try:
                return transcribe(tmp.name, language=language, fast=bool(fast))
            except Exception as e:
                raise HTTPException(500, f"stt failed: {e}")

    @router.get("/tts")
    def tts(text: str = Query(..., min_length=1, max_length=4000),
            lang: str = Query("en"),
            voice: str | None = Query(None),
            speed: float = Query(1.0, ge=0.5, le=2.0)):
        if os.environ.get("USE_VOICE", "0") != "1":
            raise HTTPException(503, "Voice disabled. Set USE_VOICE=1 and install requirements-voice.txt.")
        try:
            wav = synthesize(text, lang=lang, voice=voice, speed=speed)
        except Exception as e:
            raise HTTPException(500, f"tts failed: {e}")
        return Response(content=wav, media_type="audio/wav")

    return router
