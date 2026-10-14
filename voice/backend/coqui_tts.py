"""
Arabic TTS via Coqui XTTS-v2 — free, offline, NO API key, NO voice sample needed
(uses a built-in studio speaker). This is the engine the owner heard good Arabic from.

Install once (into the Odin venv):
    pip install coqui-tts

First run downloads the XTTS-v2 model (~1.8 GB) once, then it's fully offline.

Env knobs:
    ODIN_XTTS_SPEAKER  built-in voice name (default "Claribel Dervla")
    ODIN_XTTS_SPEED    speaking speed, e.g. 1.1 for a bit faster
    ODIN_XTTS_MODEL    model id (default tts_models/multilingual/multi-dataset/xtts_v2)
"""
import io
import os
import logging

log = logging.getLogger("odin.voice.tts.coqui")

_tts = None
_SR = 24000  # XTTS output sample rate


def _load():
    global _tts
    if _tts is not None:
        return _tts
    os.environ.setdefault("COQUI_TOS_AGREED", "1")  # accept model license non-interactively
    try:
        from TTS.api import TTS  # provided by the 'coqui-tts' package
    except ModuleNotFoundError as e:
        if (e.name or "").split(".")[0] == "TTS":
            raise RuntimeError("Coqui not installed. Run:  pip install coqui-tts") from e
        raise RuntimeError(f"Coqui import failed — missing dependency '{e.name}': {e}") from e
    except Exception as e:
        # Surface the REAL error (often a transformers/torch version mismatch inside XTTS).
        raise RuntimeError(f"Coqui import failed ({type(e).__name__}: {e})") from e
    model = os.environ.get("ODIN_XTTS_MODEL", "tts_models/multilingual/multi-dataset/xtts_v2")
    log.info("Loading Coqui XTTS-v2 (%s). First run downloads ~1.8 GB once.", model)
    _tts = TTS(model)
    return _tts


def synthesize(text: str, lang: str = "ar", speaker: str | None = None, speed=None) -> bytes:
    import numpy as np
    import soundfile as sf

    tts = _load()
    speaker = speaker or os.environ.get("ODIN_XTTS_SPEAKER", "Claribel Dervla")
    lang_code = "ar" if str(lang).lower().startswith("ar") else "en"

    kwargs = dict(text=text, language=lang_code, speaker=speaker)
    sp = speed or os.environ.get("ODIN_XTTS_SPEED")
    if sp:
        try:
            kwargs["speed"] = float(sp)
        except (TypeError, ValueError):
            pass

    wav = tts.tts(**kwargs)
    arr = np.asarray(wav, dtype="float32")
    buf = io.BytesIO()
    sf.write(buf, arr, _SR, format="WAV")
    return buf.getvalue()
