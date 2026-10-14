#!/usr/bin/env bash
# Launch the Odin-Orchestrator local server (dashboard + voice + chat).
set -euo pipefail
cd "$(dirname "$0")/.."          # -> Odin-Orchestrator/

# macOS GUI apps (e.g. the Electron app spawning this) get a stripped PATH WITHOUT Homebrew —
# so `az`, `ollama`, `claude` wouldn't be found. Put the common tool dirs back on PATH.
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:/usr/local/sbin:$HOME/.local/bin:$PATH"

# Activate the project's virtualenv so deps (uvicorn, fastapi, voice…) are found EVEN when this
# script is launched without an activated shell (e.g. spawned by the desktop app). Checks the
# common locations; override with ODIN_VENV=/path/to/venv.
for V in "${ODIN_VENV:-}" ".venv" "venv" "../.venv" "$HOME/.venvs/odin"; do
  if [ -n "$V" ] && [ -f "$V/bin/activate" ]; then
    # shellcheck disable=SC1090
    source "$V/bin/activate"
    break
  fi
done
PYBIN="$(command -v python || command -v python3)"

PORT="${PORT:-18000}"
export USE_VOICE="${USE_VOICE:-1}"
export ODIN_OLLAMA_MODEL="${ODIN_OLLAMA_MODEL:-qwen2.5:7b-instruct-q4_K_M}"
export ODIN_WHISPER_MODEL="${ODIN_WHISPER_MODEL:-medium}"
# Arabic TTS via Piper (set the model path you downloaded):
# export ODIN_PIPER_AR_MODEL="$HOME/piper-voices/ar_JO-kareem-medium.onnx"

HOST="${ODIN_HOST:-127.0.0.1}"
# IMPORTANT: do NOT auto-reload in normal use — the server writes its own data files
# (chats/, history/, state/) on every message, which would trip the reloader and KILL the
# in-flight request mid-stream. Enable dev reload only with ODIN_RELOAD=1 (data dirs excluded).
RELOAD=()
if [ "${ODIN_RELOAD:-0}" = "1" ]; then
  RELOAD=(--reload --reload-dir server --reload-dir orchestrator)
fi

# Free the port first — kill any stale/zombie server from a previous run so we always bind a
# CURRENT backend (prevents the "old server without CORS holds :8000" problem).
if command -v lsof >/dev/null 2>&1; then
  STALE="$(lsof -ti tcp:"$PORT" 2>/dev/null || true)"
  if [ -n "$STALE" ]; then
    echo "Freeing port $PORT (killing stale pids: $STALE)"
    kill -9 $STALE 2>/dev/null || true
    sleep 1
  fi
fi

echo "Odin server → http://localhost:${PORT}/   (USE_VOICE=$USE_VOICE, model=$ODIN_OLLAMA_MODEL, reload=${ODIN_RELOAD:-0}, py=$PYBIN)"
# Use `python -m uvicorn` so it resolves via the active venv even if the `uvicorn` console
# script isn't on PATH.
exec "$PYBIN" -m uvicorn server.app:app --host "$HOST" --port "$PORT" ${RELOAD[@]+"${RELOAD[@]}"}
