"""
Odin-Orchestrator — local server.

Serves the dashboard (static) and the voice loop:
    GET  /                      -> dashboard (dashboard/index.html)
    GET  /state/*, /history/*   -> live JSON the dashboard reads
    POST /voice/stt             -> local Whisper transcription (EN + AR)
    GET  /voice/tts             -> Kokoro (EN) / Piper or macOS (AR)
    POST /chat                  -> brain handler (local Ollama today; dispatcher later)
    GET  /health                -> readiness probe

Run:
    pip install -r server/requirements.txt -r voice/backend/requirements-voice.txt
    USE_VOICE=1 uvicorn server.app:app --reload --port 18000
    # then open http://localhost:18000/
"""
from __future__ import annotations

import os
import sys
import pathlib

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT = pathlib.Path(__file__).resolve().parent.parent  # Odin-Orchestrator/

# Make the voice backend + this server dir + orchestrator importable regardless of invocation.
sys.path.insert(0, str(ROOT / "voice" / "backend"))
sys.path.insert(0, str(ROOT / "orchestrator"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

app = FastAPI(title="Odin-Orchestrator", version="0.4.0")

# Allow the desktop app (Vite dev server / Electron file origin) to call the API locally.
try:
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], allow_credentials=False,
        allow_methods=["*"], allow_headers=["*"],
    )
except Exception:
    pass


# --- Optional shared-secret gate for the API (for mobile / any non-localhost use) ---
# If ODIN_ACCESS_TOKEN is set, API calls must send header  X-Odin-Token: <token>.
# Static dashboard + /health stay open so the page can load and prompt for the token.
@app.middleware("http")
async def access_token_gate(request, call_next):
    token = os.environ.get("ODIN_ACCESS_TOKEN")
    if token:
        path = request.url.path
        protected = path.startswith("/chat") or path.startswith("/dispatch") or path.startswith("/voice")
        ok = (request.headers.get("X-Odin-Token") == token
              or request.query_params.get("token") == token)  # query token for SSE/EventSource
        if protected and not ok:
            from starlette.responses import JSONResponse as _JR
            return _JR({"detail": "missing or invalid X-Odin-Token"}, status_code=401)
    return await call_next(request)

# --- Voice router (STT + TTS) ------------------------------------------------
try:
    from voice_service import build_router  # type: ignore
    app.include_router(build_router())
except Exception as e:  # keep the server up even if heavy voice deps aren't installed
    @app.get("/voice/_status")
    def _voice_status():
        return {"voice": "unavailable", "reason": str(e)}

# --- v2 API: projects, scoped org, agents/rules, models, scheduling, activity ---
try:
    from api_v2 import build_router as build_v2  # type: ignore
    app.include_router(build_v2())
except Exception as e:
    @app.get("/v2/_status")
    def _v2_status():
        return {"v2": "unavailable", "reason": str(e)}

# --- SOC: /soc/* (RedBerry Continuous SOC status + runtime settings + run-now) ---
try:
    from soc_api import build_router as build_soc  # type: ignore
    app.include_router(build_soc())
except Exception as e:
    @app.get("/soc/_status")
    def _soc_status():
        return {"soc": "unavailable", "reason": str(e)}

# --- Notifications: live sync feed for recurring/periodical work (list/read/clear) ---
try:
    from notifications_api import build_router as build_notifs  # type: ignore
    app.include_router(build_notifs())
except Exception as e:
    @app.get("/notifications/_status")
    def _notifs_status():
        return {"notifications": "unavailable", "reason": str(e)}

# --- Meeting monitor: /meeting/* (live chunk capture -> transcribe -> report -> export md/docx) ---
try:
    from meeting_api import build_router as build_meeting  # type: ignore
    app.include_router(build_meeting())
except Exception as e:
    @app.get("/meeting/_status")
    def _meeting_status():
        return {"meeting": "unavailable", "reason": str(e)}

# --- Auth: login / 2FA / change-password / config (web + Flutter; desktop stays open) ---
try:
    from auth import build_router as build_auth  # type: ignore
    app.include_router(build_auth())
except Exception as e:
    @app.get("/auth/_status")
    def _auth_status():
        return {"auth": "unavailable", "reason": str(e)}

# --- External access API: /api/v1 (per-project identifier → prompt → smart response) ---
try:
    from external_api import build_router as build_ext  # type: ignore
    app.include_router(build_ext())
except Exception as e:
    @app.get("/api/v1/_status")
    def _ext_status():
        return {"external_api": "unavailable", "reason": str(e)}

# --- Anchor Connect: /anchor/v1 (smart queue + local poller + webhook/ack/retry) ---
try:
    import anchor as _anchor  # type: ignore
    app.include_router(_anchor.build_router())
    _anchor.start_local_poller()          # local machine pulls + processes pending tasks
except Exception as e:
    @app.get("/anchor/v1/_status")
    def _anchor_status():
        return {"anchor": "unavailable", "reason": str(e)}

# --- Auto-register external connectors (Klaviyo, Veeqo, HubSpot, EasyPost) if their keys are in workspace/shared/oth/.cred ---
try:
    import capabilities as _caps
    from integrations import klaviyo as _kl, veeqo as _vq, hubspot as _hs, easypost as _ep
    _have = {c.get("name", "").lower() for c in _caps.list_connectors()}
    if _kl.configured() and "klaviyo" not in _have:
        _caps.add_connector("Klaviyo", "email", _kl._cfg()[0])
    if _vq.configured() and "veeqo" not in _have:
        _caps.add_connector("Veeqo", "fulfillment", _vq._key())
    if _hs.configured() and "hubspot" not in _have:
        _caps.add_connector("HubSpot", "crm", _hs._token())
    if _ep.configured() and "easypost" not in _have:
        _caps.add_connector("EasyPost", "shipping", _ep._key())
except Exception:
    pass

# --- HubSpot operator agent API: /hubspot/status, /hubspot/run, /hubspot/scopes, /hubspot/ask ---
try:
    import hubspot_api as _hsapi  # type: ignore
    app.include_router(_hsapi.build_router())
except Exception as e:
    @app.get("/hubspot/_status")
    def _hubspot_unavailable():
        return {"hubspot": "unavailable", "reason": str(e)}

# --- Directions: /directions/* — schema-backed knowledge layer (read FIRST; capability-reuse advisory) ---
try:
    import directions as _directions  # type: ignore
    app.include_router(_directions.build_router())
except Exception as e:
    @app.get("/directions/_status")
    def _directions_unavailable():
        return {"directions": "unavailable", "reason": str(e)}

# --- Audit / Observer: /audit/* — debounced self-healing safety net (has its own page) ---
try:
    import workspace_audit as _wsaudit  # type: ignore
    app.include_router(_wsaudit.build_router())
except Exception as e:
    @app.get("/audit/_status")
    def _audit_unavailable():
        return {"audit": "unavailable", "reason": str(e)}

# --- UI contract: /ui/* — generic DB-driven cards (type→controls, features→icons) for all clients ---
try:
    import ui_api as _ui_api  # type: ignore
    app.include_router(_ui_api.build_router())
except Exception as e:
    @app.get("/ui/_status")
    def _ui_unavailable():
        return {"ui": "unavailable", "reason": str(e)}


# --- Chat (brain handler) ----------------------------------------------------
class ChatIn(BaseModel):
    text: str
    lang: str = "en"


def _brain():
    """The Brain behind /chat and the voice loop. Dispatcher by default (routes to a
    specialist + enforces the approval gate); set ODIN_USE_DISPATCHER=0 for raw Ollama."""
    if os.environ.get("ODIN_USE_DISPATCHER", "1") == "1":
        from dispatcher import default_dispatcher
        return default_dispatcher
    from brain_handler import default_handler
    return default_handler


@app.post("/chat")
def chat(body: ChatIn):
    reply = _brain().respond(body.text, lang=body.lang)
    return {"reply": reply, "lang": body.lang}


@app.post("/dispatch")
def dispatch(body: ChatIn):
    """Full routing decision: which agent(s), whether approval is required, hooks fired."""
    from dispatcher import default_dispatcher
    return default_dispatcher.route(body.text, lang=body.lang)


@app.get("/chat/stream")
def chat_stream(text: str, lang: str = "en"):
    """Server-Sent Events for the animated cockpit: emits live status steps (icons),
    then streams the answer in for a typing effect, then 'done'. Phase A of the cockpit."""
    import json as _json
    from dispatcher import default_dispatcher as d

    def sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {_json.dumps(data, ensure_ascii=False)}\n\n"

    def gen():
        try:
            decision = d.route(text, lang)
            lead = decision["leadAgent"]
            gated = decision["approval"]["required"]
            engine = "Claude CLI" if __import__("os").environ.get("ODIN_ENGINE", "claude") == "claude" else "local LLM"
            yield sse("status", {"icon": "🧠", "text": "Understanding your request…"})
            yield sse("status", {"icon": "🔎", "text": f"Routing to {lead}"})
            if gated:
                cats = ", ".join(decision["approval"]["categories"])
                yield sse("status", {"icon": "⛔", "text": f"Needs your approval ({cats})"})
            else:
                yield sse("status", {"icon": "⚙️", "text": f"{lead} is working via {engine}…"})

            reply = d.respond(text, lang)  # gated → approval message; else engine answer
            yield sse("status", {"icon": "✅", "text": "Done"})

            buf = ""
            for chunk in reply:
                buf += chunk
                if len(buf) >= 4 or chunk in " \n،.!؟":
                    yield sse("token", {"t": buf})
                    buf = ""
            if buf:
                yield sse("token", {"t": buf})
            yield sse("done", {"agent": lead, "approval": decision["approval"], "lang": lang})
        except Exception as e:
            yield sse("error", {"text": str(e)})

    return StreamingResponse(gen(), media_type="text/event-stream")


# --- Persistent chats (non-volatile; conversation memory via Claude sessions) ----------
class TitleIn(BaseModel):
    title: str = "New chat"


@app.get("/chats")
def chats_list():
    import chats
    return {"chats": chats.list_chats()}


@app.post("/chats")
def chats_create(body: TitleIn | None = None):
    import chats
    return chats.create_chat(body.title if body else "New chat")


@app.get("/chats/{cid}")
def chats_get(cid: str):
    import chats
    d = chats.get_chat(cid)
    if not d:
        raise HTTPException(404, "no such chat")
    return d


@app.delete("/chats/{cid}")
def chats_delete(cid: str):
    import chats
    return {"deleted": chats.delete_chat(cid)}


@app.post("/chats/{cid}/rename")
def chats_rename(cid: str, body: TitleIn):
    import chats
    d = chats.rename_chat(cid, body.title)
    if not d:
        raise HTTPException(404, "no such chat")
    return d


@app.get("/chats/{cid}/stream")
def chats_stream(cid: str, text: str, lang: str = "en"):
    """Persistent, memory-keeping chat stream: saves messages, resumes the chat's Claude
    session for context, enforces the approval gate, streams status + answer."""
    import json as _json
    import chats
    from dispatcher import default_dispatcher as d

    def sse(ev, data):
        return f"event: {ev}\ndata: {_json.dumps(data, ensure_ascii=False)}\n\n"

    def gen():
        try:
            chats.add_message(cid, "user", text)
            decision = d.route(text, lang)
            lead = decision["leadAgent"]
            gated = decision["approval"]["required"]
            yield sse("status", {"icon": "🧠", "text": "Understanding…"})
            yield sse("status", {"icon": "🔎", "text": f"Routing to {lead}"})
            if gated:
                cats = ", ".join(decision["approval"]["categories"])
                yield sse("status", {"icon": "⛔", "text": f"Change ({cats}) — will propose & wait for your OK"})
            else:
                yield sse("status", {"icon": "⚙️", "text": f"{lead} working…"})

            reply = None
            streamed = False
            try:
                from claude_cli import available as _av, ClaudeCLIBrain
                if os.environ.get("ODIN_ENGINE", "claude") == "claude" and _av():
                    streamed = True
                    parts, new_sid = [], None
                    sid0 = (chats.get_chat(cid) or {}).get("session_id")
                    # LIVE stream of the engine's work — shows real commands, no timeout-stop.
                    for evd in ClaudeCLIBrain().stream_session(text, lang, sid0):
                        k = evd.get("kind")
                        if k == "status":
                            yield sse("status", {"icon": evd.get("icon", "🔧"), "text": evd.get("text", "")})
                        elif k == "text":
                            parts.append(evd["t"]); yield sse("token", {"t": evd["t"]})
                        elif k == "session":
                            new_sid = evd.get("id")
                        elif k == "final":
                            reply = evd.get("text") or "".join(parts)
                            if evd.get("session_id"):
                                new_sid = evd["session_id"]
                    if new_sid:
                        chats.set_session(cid, new_sid)
                    if reply is None:
                        reply = "".join(parts)
            except Exception as e:
                reply = f"(engine error: {e})"; streamed = False
            if reply is None:
                reply = d.respond(text, lang)

            if not streamed:
                buf = ""
                for ch in reply:
                    buf += ch
                    if len(buf) >= 4 or ch in " \n،.!؟":
                        yield sse("token", {"t": buf}); buf = ""
                if buf:
                    yield sse("token", {"t": buf})

            chats.add_message(cid, "assistant", reply or "")
            yield sse("status", {"icon": "✅", "text": "Done"})
            yield sse("done", {"agent": lead, "approval": decision["approval"], "lang": lang})
        except Exception as e:
            yield sse("error", {"text": str(e)})

    return StreamingResponse(gen(), media_type="text/event-stream")


# --- Azure VM connector (read-only helpers; command execution is approval-gated) ---
@app.get("/infra/ip")
def infra_ip():
    """Detect this Mac's public IP (the source IP Azure NSG must allow for SSH). Safe."""
    from infra_ssh import current_public_ip, configured
    return {"public_ip": current_public_ip(), "configured": configured()}


@app.get("/infra/reachable")
def infra_reachable():
    """Read-only SSH reachability test (runs `uname -a` on the VM). Safe."""
    from infra_ssh import reachable
    return reachable()


@app.get("/infra/connect-test")
def infra_connect_test():
    """Odin connects to the VM via Azure (az vm run-command, no SSH/key/IP) and lists the
    home folder — read-only proof of connection. Runs on the Mac where `az` is logged in."""
    from infra_az import connect_test
    return connect_test()


@app.on_event("startup")
def _prewarm_voice():
    """Load the TTS models in the background at startup so the first user request is fast
    (XTTS is ~1.8 GB and slow to load on CPU). Non-blocking — server starts immediately."""
    if os.environ.get("USE_VOICE", "0") != "1":
        return
    import threading

    def _warm():
        try:
            from coqui_tts import _load as _load_ar
            _load_ar()  # Arabic (XTTS-v2)
        except Exception as e:
            print(f"[prewarm] Arabic XTTS not ready: {e}")
        try:
            from tts import _load as _load_en
            _load_en()  # English (Kokoro)
        except Exception as e:
            print(f"[prewarm] English Kokoro not ready: {e}")
        try:
            from voice_service import _load_whisper_fast
            _load_whisper_fast()  # STT fast model — so live mic partials aren't slow on first use
            print("[prewarm] STT fast model ready.")
        except Exception as e:
            print(f"[prewarm] STT fast model not ready: {e}")
        print("[prewarm] voice models loaded.")

    threading.Thread(target=_warm, daemon=True).start()


@app.on_event("startup")
def _start_scheduler():
    """Start the per-project task scheduler (Phase 7) in the background."""
    try:
        import scheduler
        scheduler.start_background()
    except Exception as e:
        print(f"[scheduler] not started: {e}")


@app.get("/health")
def health():
    # Report which engine is actually active (Claude CLI is the core; Ollama is fallback).
    engine = "local LLM (Ollama)"
    if os.environ.get("ODIN_ENGINE", "claude") == "claude":
        try:
            from claude_cli import available as _cli
            engine = "Claude CLI (Claude Code)" if _cli() else "local LLM (Ollama) — Claude CLI not installed"
        except Exception:
            pass
    return {
        "ok": True,
        "engine": engine,
        "voice_enabled": os.environ.get("USE_VOICE", "0") == "1",
        "ollama_model": os.environ.get("ODIN_OLLAMA_MODEL", "qwen2.5:7b-instruct-q4_K_M"),
    }


# --- Static: serve the dashboard, state, and history -------------------------
# Mounted AFTER the API routes so /chat, /voice, /health win.
app.mount("/state", StaticFiles(directory=str(ROOT / "workspace" / "state")), name="state")
app.mount("/history", StaticFiles(directory=str(ROOT / "workspace" / "history")), name="history")
app.mount("/", StaticFiles(directory=str(ROOT / "dashboard"), html=True), name="dashboard")
