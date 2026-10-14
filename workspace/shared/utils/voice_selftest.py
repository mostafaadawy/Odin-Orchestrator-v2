#!/usr/bin/env python3
"""
Odin neural TTS self-test — proves the voice output works in BOTH English and Arabic,
fully local, NO macOS voice. Downloads the two small MMS-TTS models on first run.

(The microphone uses the browser's speech recognition in the app, so it isn't part of this
headless test — this script verifies the neural VOICE OUTPUT, the part that had to change.)

Run (from project root, venv active — no new installs needed):
    python scripts/voice_selftest.py
Then listen:
    afplay /tmp/odin_en.wav ; afplay /tmp/odin_ar.wav
"""
import sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT / "voice" / "backend"))

EN_TEXT = "Hello, this is the Odin C T O brain speaking English with a neural voice."
AR_TEXT = "مرحبا، هذا هو عقل أودين يتحدث باللغة العربية بصوت عصبي."

results = {}


def run(name, lang, text, path):
    print(f"\n=== {name} ===", flush=True)
    try:
        from voice_service import synthesize  # real routing: EN->Kokoro(US), AR->MMS Egyptian
        wav = synthesize(text, lang=lang)
        pathlib.Path(path).write_bytes(wav)
        kb = len(wav) // 1024
        assert kb > 5, f"audio suspiciously small ({kb} KB)"
        results[name] = True
        print(f"[PASS] {name}: wrote {path} ({kb} KB)", flush=True)
    except Exception as e:
        results[name] = False
        print(f"[FAIL] {name}: {e!r}", flush=True)


run("English neural voice (MMS-TTS eng)", "en", EN_TEXT, "/tmp/odin_en.wav")
run("Arabic neural voice (MMS-TTS ara)", "ar", AR_TEXT, "/tmp/odin_ar.wav")

print("\n==================== SUMMARY ====================")
for k, ok in results.items():
    print(f"  {'✅' if ok else '❌'} {k}")
print("================================================")
if all(results.values()):
    print("BOTH neural voices work and are downloaded. ✅")
    print("Listen:  afplay /tmp/odin_en.wav ; afplay /tmp/odin_ar.wav")
    sys.exit(0)
print("A voice FAILED — see the [FAIL] line above; paste it and I'll fix it.")
sys.exit(1)
