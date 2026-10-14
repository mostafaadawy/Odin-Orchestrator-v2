"""
Brain handler — the pluggable component that turns transcribed user text into a reply.

Today this routes to a local Ollama model. It is intentionally behind a small interface so
that, when the real Brain<->agent dispatcher exists, it can be swapped in WITHOUT touching the
voice loop: just provide an object with `respond(text, lang) -> str`.
"""
from __future__ import annotations

import os
import json
import logging
import urllib.request

log = logging.getLogger("odin.brain")

OLLAMA_URL = os.environ.get("ODIN_OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("ODIN_OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_K_M")

SYSTEM_EN = (
    "You are the Odin CTO Brain assistant speaking over voice. Reply briefly and clearly "
    "in plain spoken English (1-3 sentences, no markdown)."
)
SYSTEM_AR = (
    "أنت مساعد Odin CTO Brain تتحدث عبر الصوت. أجب بإيجاز ووضوح باللغة العربية "
    "(جملة إلى ثلاث جمل، بدون تنسيق)."
)


class OllamaBrain:
    """Default handler: calls a local Ollama chat model. Stdlib-only (no extra deps)."""

    def __init__(self, model: str | None = None, url: str | None = None):
        self.model = model or OLLAMA_MODEL
        self.url = (url or OLLAMA_URL).rstrip("/")

    def respond(self, text: str, lang: str = "en") -> str:
        system = SYSTEM_AR if str(lang).startswith("ar") else SYSTEM_EN
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
        }
        req = urllib.request.Request(
            f"{self.url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                data = json.loads(r.read().decode("utf-8"))
            return (data.get("message", {}) or {}).get("content", "").strip() or "(no reply)"
        except Exception as e:  # surface a spoken-friendly error, don't crash the loop
            log.warning("Ollama call failed: %s", e)
            return (
                "تعذّر الوصول إلى النموذج المحلي." if str(lang).startswith("ar")
                else f"Local model unavailable ({e.__class__.__name__}). Is Ollama running?"
            )


# Swap point for the future dispatcher: assign a different object exposing respond(text, lang).
default_handler: object = OllamaBrain()
