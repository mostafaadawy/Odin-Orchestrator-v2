"""
Optional text-to-speech backend using Kokoro (https://github.com/hexgrad/kokoro).

Kokoro ships a small (~82M param) neural TTS model with natural-sounding English voices.
It's an *optional* add-on — the default install does not pull its ~2 GB of torch deps.

Enable it by:
    cd backend
    source .venv/bin/activate
    pip install -r requirements-voice.txt
    echo "USE_KOKORO=1" >> .env

The pipeline and model weights (~300 MB) download from HuggingFace on first call.
"""
from __future__ import annotations

import io
import logging

log = logging.getLogger("odin.voice.tts")

_pipeline = None
_soundfile = None
_numpy = None
_lang_code = "a"  # 'a' = American English; 'b' = British English


class TTSUnavailable(RuntimeError):
    """Raised when Kokoro or its deps are not installed."""


def _load():
    """Lazy-load the Kokoro pipeline so default users never pay the import cost."""
    global _pipeline, _soundfile, _numpy
    if _pipeline is not None:
        return _pipeline

    try:
        from kokoro import KPipeline  # type: ignore
        import numpy as np  # type: ignore
        import soundfile as sf  # type: ignore
    except ImportError as e:
        raise TTSUnavailable(
            "Kokoro not installed. Run:\n"
            "  cd backend && source .venv/bin/activate && pip install -r requirements-voice.txt"
        ) from e

    log.info("Loading Kokoro pipeline (lang=%s). First run downloads ~300 MB from HuggingFace.", _lang_code)
    _pipeline = KPipeline(lang_code=_lang_code)
    _soundfile = sf
    _numpy = np
    return _pipeline


def synthesize(text: str, voice: str = "af_heart", speed: float = 1.0) -> bytes:
    """Return WAV-encoded audio bytes for `text`.

    Voices (a selection — full list in Kokoro docs):
        af_heart, af_bella, af_sarah, af_sky  — American female
        am_adam, am_michael                   — American male
        bf_emma, bf_isabella                  — British female
        bm_george, bm_lewis                   — British male
    """
    pipe = _load()
    assert _soundfile is not None and _numpy is not None  # satisfied by _load()

    segments = []
    for item in pipe(text, voice=voice, speed=speed):
        # Be robust across Kokoro versions: newer returns a Result object (.audio),
        # older yields (graphemes, phonemes, audio) tuples.
        audio = getattr(item, "audio", None)
        if audio is None:
            audio = item[-1] if isinstance(item, (tuple, list)) else item
        if audio is None:
            continue
        # Kokoro returns a torch.Tensor (or ndarray) at 24 kHz mono.
        arr = audio.detach().cpu().numpy() if hasattr(audio, "detach") else _numpy.asarray(audio)
        segments.append(arr)

    if not segments:
        raise RuntimeError("Kokoro produced no audio (empty or unsupported text).")

    combined = segments[0] if len(segments) == 1 else _numpy.concatenate(segments)
    buf = io.BytesIO()
    _soundfile.write(buf, combined, 24000, format="WAV")
    return buf.getvalue()
