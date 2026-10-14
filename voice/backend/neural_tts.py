"""
Neural TTS for English + Arabic — Meta MMS-TTS (VITS) via transformers.

Chosen because Kokoro has NO Arabic. MMS-TTS gives genuine neural English AND Arabic,
runs fully offline (after a one-time ~145 MB model download per language), and uses only
libraries already installed (transformers, torch, soundfile, numpy). NO macOS voices, NO
browser fallback — owner requirement.

Arabic (non-Latin script) needs romanization (uroman) before the VITS tokenizer:
    pip install uroman
"""
import io
import logging

log = logging.getLogger("odin.voice.tts")

# Arabic: facebook/mms-tts-ara (Modern Standard Arabic). NOTE: there is NO official MMS
# Egyptian-dialect TTS model — true Egyptian voice needs XTTS-v2 voice cloning (separate task).
_MODELS = {"en": "facebook/mms-tts-eng", "ar": "facebook/mms-tts-ara"}
_cache: dict = {}
_uroman = None


def _load(key: str):
    from transformers import AutoTokenizer
    try:
        from transformers import VitsModel
    except ImportError:  # newer transformers may only expose the module path
        from transformers.models.vits.modeling_vits import VitsModel
    if key not in _cache:
        mid = _MODELS[key]
        log.info("Loading MMS-TTS '%s' (%s). First time downloads ~145 MB.", key, mid)
        model = VitsModel.from_pretrained(mid)
        tok = AutoTokenizer.from_pretrained(mid)
        model.eval()
        _cache[key] = (model, tok)
    return _cache[key]


def _romanize(text: str, lcode: str) -> str:
    global _uroman
    try:
        import uroman as _ur
    except ImportError as e:
        raise RuntimeError(
            "Arabic TTS needs the 'uroman' package. Install it once:\n"
            "  pip install uroman"
        ) from e
    if _uroman is None:
        _uroman = _ur.Uroman()
    return _uroman.romanize_string(text, lcode=lcode)


def synthesize(text: str, lang: str = "en", **_) -> bytes:
    """Return WAV bytes of `text` spoken in English or Arabic — neural, no fallback."""
    import torch
    import soundfile as sf

    key = "ar" if str(lang).lower().startswith("ar") else "en"
    model, tok = _load(key)

    feed = text
    if getattr(tok, "is_uroman", False):
        feed = _romanize(text, "ara" if key == "ar" else "eng")

    inputs = tok(feed, return_tensors="pt")
    with torch.no_grad():
        waveform = model(**inputs).waveform  # [1, samples]

    arr = waveform.squeeze().detach().cpu().numpy().astype("float32")
    sr = int(model.config.sampling_rate)
    buf = io.BytesIO()
    sf.write(buf, arr, sr, format="WAV")
    return buf.getvalue()
