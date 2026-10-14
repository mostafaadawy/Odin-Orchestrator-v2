# Odin-Orchestrator — Setup & Test Guide (MacBook Pro M4 / 24 GB)

Follow top to bottom. Everything is **local** — nothing touches your Azure VM (that stays
behind the approval gate). Copy-paste the commands in Terminal.

---

## 0. Prerequisites (one-time)

```bash
# Homebrew (skip if you have it)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Python 3.12 (you already have it from the old app; this is harmless if so)
brew install python@3.12

# Ollama (the local LLM that powers the Brain's free-form replies)
brew install ollama
brew services start ollama
ollama pull qwen2.5:7b-instruct-q4_K_M      # fast; ~4.7 GB. (14b also fine if you prefer)
```

You do **not** need Node/npm — the dashboard is plain HTML.

---

## 1. Install the Odin project

```bash
cd <odin-repo-root>

python3.12 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r server/requirements.txt              # FastAPI server (small)
pip install -r voice/backend/requirements-voice.txt # Whisper + Kokoro (~2 GB, first time)
```

> First run of voice will download model weights once (Whisper model + Kokoro ~300 MB).

---

## 2. Start the server

```bash
# from the project root, with the venv active:
USE_VOICE=1 ./server/run.sh
#   (if "permission denied":  USE_VOICE=1 bash server/run.sh )
```

You should see: `Odin server → http://localhost:8000/`. Leave this running.

Open a **second** Terminal tab for the tests below (re-activate the venv there if needed:
`cd <odin-repo-root> && source .venv/bin/activate`).

---

## 3. One-command smoke test

```bash
bash scripts/smoke_test.sh
```

Green ✅ across health, dashboard, mobile, chat, and the approval gate means the backbone
works. Voice lines show 200 when STT/TTS deps are installed.

---

## 4. Test each feature yourself (checklist)

### A. Dashboard
- [ ] Open **http://localhost:8000/** — see progress, phases, tasks, history, and the
      **Voice Console** card at top.

### B. Voice loop (desktop)
- [ ] In the Voice Console click **Record**, allow the mic, say *"What is the approval gate?"*,
      click **Stop**. You should see your words (STT) → a Brain reply → it speaks (TTS).
- [ ] Toggle **AR**, speak Arabic, confirm Arabic transcription + reply. (Arabic voice uses
      macOS *Maged* unless you set up Piper — see §6.)

### C. Brain routing + approval gate (the important safety test)
```bash
# A safe question — should answer normally:
curl -s -X POST http://localhost:8000/chat -H 'Content-Type: application/json' \
  -d '{"text":"write a react login component","lang":"en"}'

# A risky action — must REFUSE to execute and ask for approval:
curl -s -X POST http://localhost:8000/dispatch -H 'Content-Type: application/json' \
  -d '{"text":"deploy the backend to the azure vm and restart the service","lang":"en"}'
```
- [ ] The second returns `"approval":{"required":true,...}` and the chat reply says it will
      prepare an approval request. ✅ This proves nothing risky runs without you.

### D. Mobile (same Wi-Fi)
- [ ] Stop the server. Set a token and bind to your LAN:
```bash
export ODIN_ACCESS_TOKEN="$(openssl rand -hex 16)"; echo "TOKEN: $ODIN_ACCESS_TOKEN"
USE_VOICE=1 PORT=8000 uvicorn server.app:app --host 0.0.0.0 --port 8000
```
- [ ] Find your Mac IP: `ipconfig getifaddr en0`
- [ ] On your phone (same Wi-Fi) open `http://<that-ip>:8000/mobile.html`, paste the token,
      and try typing a message. (Phone **mic** needs HTTPS — see `runbooks/mobile-access.md`
      §Option B; typing works fine over plain LAN.)

### E. Audit & revert
- [ ] `cat history/HISTORY.md` — every action is timestamped.
- [ ] `tail history/routing.jsonl` — your test routings were logged here (separate from the
      main audit log).
- [ ] Snapshots in `history/snapshots/` are restore points (`runbooks/revert.md`).

---

## 5. Stop / restart
- Stop the server: `Ctrl+C` in its Terminal.
- Restart later: `cd ...Odin-Orchestrator && source .venv/bin/activate && USE_VOICE=1 ./server/run.sh`

---

## 6. Optional: high-quality Arabic TTS via Piper
```bash
pip install piper-tts
mkdir -p ~/piper-voices && cd ~/piper-voices
# Download an Arabic voice (model .onnx + its .onnx.json) from rhasspy/piper-voices on HuggingFace,
# e.g. ar_JO-kareem-medium.onnx  +  ar_JO-kareem-medium.onnx.json
export ODIN_PIPER_AR_MODEL="$HOME/piper-voices/ar_JO-kareem-medium.onnx"
# restart the server; Arabic now uses Piper instead of macOS Maged.
```

---

## 7. Troubleshooting
- **`/chat` says "Local model unavailable"** → Ollama isn't running or the model isn't pulled:
  `brew services start ollama && ollama list`.
- **Voice `/voice/tts` returns 503** → you didn't start with `USE_VOICE=1`.
- **Voice `/voice/tts` returns 500** → voice deps not installed: re-run the
  `pip install -r voice/backend/requirements-voice.txt` step.
- **Mic does nothing on the phone** → browsers block mic on plain `http://<ip>`. Use the
  approval-gated HTTPS exposure (`runbooks/mobile-access.md`) or just type on mobile for now.
- **Port 8000 busy** → `PORT=8010 USE_VOICE=1 ./server/run.sh`.
- **Slow first reply** → the LLM and voice models load into memory on first use; subsequent
  calls are fast.

## What is NOT being tested here (by design)
The live **Azure VM** is untouched — connecting it is a separate, approval-gated step that
needs your access details. The **custom billing model** is still a placeholder in
`rules/core-rules.md §6.1`.
