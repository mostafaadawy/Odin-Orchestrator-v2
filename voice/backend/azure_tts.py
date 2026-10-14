"""
Azure Neural TTS — genuine EGYPTIAN Arabic voice (ar-EG-SalmaNeural / ar-EG-ShakirNeural).

This is the correct, high-quality path for Egyptian Arabic. No voice sample needed.
Uses the Azure Speech REST endpoint over HTTPS (stdlib only — no SDK install).

Configure (in the shell that runs the server):
    export AZURE_SPEECH_KEY="<your speech resource key>"
    export AZURE_SPEECH_REGION="<region, e.g. eastus>"
    # optional:
    export AZURE_AR_VOICE="ar-EG-SalmaNeural"   # female (default) | ar-EG-ShakirNeural (male)
    export AZURE_TTS_RATE="+8%"                  # speak a bit faster than default
"""
import os
import html
import urllib.request

DEFAULT_VOICE = "ar-EG-SalmaNeural"


def available() -> bool:
    return bool(os.environ.get("AZURE_SPEECH_KEY") and os.environ.get("AZURE_SPEECH_REGION"))


def synthesize(text: str, lang: str = "ar-EG", voice: str | None = None, rate: str | None = None) -> bytes:
    if not available():
        raise RuntimeError(
            "Azure TTS not configured. Set AZURE_SPEECH_KEY and AZURE_SPEECH_REGION "
            "(create a free 'Speech service' resource in the Azure Portal)."
        )
    key = os.environ["AZURE_SPEECH_KEY"]
    region = os.environ["AZURE_SPEECH_REGION"]
    voice = voice or os.environ.get("AZURE_AR_VOICE", DEFAULT_VOICE)
    rate = rate or os.environ.get("AZURE_TTS_RATE", "+0%")

    ssml = (
        f"<speak version='1.0' xml:lang='{lang}'>"
        f"<voice xml:lang='{lang}' name='{voice}'>"
        f"<prosody rate='{rate}'>{html.escape(text)}</prosody>"
        f"</voice></speak>"
    )
    url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
    req = urllib.request.Request(
        url,
        data=ssml.encode("utf-8"),
        headers={
            "Ocp-Apim-Subscription-Key": key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "riff-24khz-16bit-mono-pcm",  # standard WAV
            "User-Agent": "odin-orchestrator",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()
