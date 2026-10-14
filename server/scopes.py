"""
Scoped memory — the backbone of the multi-agent org (Phase 2).

Three nested scopes, each owning its own pool of chats + a rolled-up summary feed:
    company                      -> the company CTO (spans all projects, coarse)
    project:<pid>                -> one project's CTO (full project detail)
    member:<pid>:<agent>         -> one team member inside a project (deepest detail)

Rules implemented here:
- Each scope has its OWN chats (separate threads) but a member's many chats share the member
  scope's pool. Conversation memory per chat via the engine session id (unchanged mechanism).
- UPWARD SYNC: when something happens in a scope (a turn, a change, a correction), a compact
  event is appended to every ANCESTOR's feed (member -> project -> company) so higher levels stay
  synchronized. Detail stays low; summaries roll up.
- DRILL-DOWN: a parent can read a child's chats/feed (children_of, read_child_chats).
- Scope-relative context: "last thing" in a scope = that scope's own last activity.
"""
from __future__ import annotations

import uuid
import store  # server dir is on sys.path (see server/app.py)


def _safe(scope_id: str) -> str:
    return scope_id.replace(":", "__").replace("/", "_")


def parent_of(scope_id: str) -> str | None:
    if scope_id == "company":
        return None
    if scope_id.startswith("member:"):
        _, pid, _agent = scope_id.split(":", 2)
        return f"project:{pid}"
    if scope_id.startswith("project:"):
        return "company"
    return "company"


def ancestors(scope_id: str) -> list[str]:
    out, cur = [], parent_of(scope_id)
    while cur:
        out.append(cur)
        cur = parent_of(cur)
    return out


def _dir(scope_id: str):
    return store.ensure_dir("scopes", _safe(scope_id))


def _meta_path(scope_id: str) -> str:
    return f"scopes/{_safe(scope_id)}/meta.json"


def _meta(scope_id: str) -> dict:
    m = store.read_json(_meta_path(scope_id), None)
    if m is None:
        m = {"scope": scope_id, "summary": "", "feed": [], "created": store.now()}
        store.write_json(_meta_path(scope_id), m)
    return m


def _chat_path(scope_id: str, cid: str) -> str:
    return f"scopes/{_safe(scope_id)}/chats/{cid}.json"


# ---- chats within a scope -------------------------------------------------------
def list_chats(scope_id: str) -> list:
    d = _dir(scope_id) / "chats"
    out = []
    if d.exists():
        for p in sorted(d.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
            try:
                c = store.read_json(f"scopes/{_safe(scope_id)}/chats/{p.stem}.json", {})
                if c.get("deleted"):
                    continue
                out.append({"id": c["id"], "title": c.get("title", "New chat"),
                            "updated": c.get("updated"), "count": len(c.get("messages", []))})
            except Exception:
                pass
    return out


def create_chat(scope_id: str, title: str = "New chat") -> dict:
    if title == "New chat":
        for c in list_chats(scope_id):
            if c.get("count", 0) == 0 and c.get("title") == "New chat":
                return get_chat(scope_id, c["id"]) or {}
    cid = uuid.uuid4().hex[:12]
    d = {"id": cid, "scope": scope_id, "title": title, "created": store.now(),
         "updated": store.now(), "session_id": None, "messages": []}
    store.write_json(_chat_path(scope_id, cid), d)
    return d


def get_chat(scope_id: str, cid: str):
    return store.read_json(_chat_path(scope_id, cid), None)


def all_messages(scope_id: str) -> list:
    """The WHOLE pool for a scope: every message across all its chats, merged in time order.
    This is the single-source-of-truth view (the CTO plan, run logs, deploy feedback, agent
    replies and your messages — all together) used by the Conversations representation."""
    out = []
    for c in list_chats(scope_id):
        d = get_chat(scope_id, c["id"]) or {}
        for m in d.get("messages", []):
            mm = dict(m)
            mm["chat"] = c.get("title", "")
            mm["cid"] = c["id"]
            out.append(mm)
    # Order by the authoritative per-scope SEQ (contiguous), ts as a tiebreak for old messages without seq.
    out.sort(key=lambda x: (x.get("seq", 0), x.get("ts", 0)))
    return out


def _next_seq(scope_id: str) -> int:
    """Monotonic per-SCOPE sequence number — the authoritative ordering key + gap detector. Assigned by the
    backend (the single source of truth), so messages sort contiguously and a MISSING message shows up as a
    gap in seq that any client can detect on refresh and pull. Stored in one small counter file."""
    key = "s_" + scope_id.replace(":", "_").replace("/", "_")
    d = store.read_json("_seq_counters.json", {})
    n = int(d.get(key, 0)) + 1
    d[key] = n
    store.write_json("_seq_counters.json", d)
    return n


def add_message(scope_id: str, cid: str, role: str, content: str,
                sender: str | None = None, kind: str = "text",
                attachment: dict | None = None, reply_to: str | None = None,
                client_msg_id: str | None = None):
    """Append a message to a scope chat. Rich/group fields are optional & backward compatible:
      sender     = display name (e.g. 'Mostafa (iPhone)', 'Project CTO', 'Email agent')
      kind       = text | image | audio | file | zip
      attachment = {id, name, url, kind, size}
      reply_to   = the id of the message being replied to
    Returns the appended message (with its own id)."""
    d = get_chat(scope_id, cid)
    if not d:
        return None
    # IDEMPOTENT: if this exact client message was already saved, return it — no duplicate. This is what makes
    # "confirmed send" safe (a retry after a dropped ack can't create a second copy).
    if client_msg_id:
        for _m in d.get("messages", []):
            if _m.get("client_msg_id") == client_msg_id:
                return _m
    msg = {"id": uuid.uuid4().hex[:12], "role": role, "content": content,
           "ts": store.now(), "seq": _next_seq(scope_id), "kind": kind}
    if client_msg_id:
        msg["client_msg_id"] = client_msg_id
    if sender:
        msg["sender"] = sender
    if attachment:
        msg["attachment"] = attachment
    if reply_to:
        msg["reply_to"] = reply_to
    d["messages"].append(msg)
    d["updated"] = store.now()
    if d.get("title", "New chat") == "New chat" and role == "user" and content:
        d["title"] = (content[:40] + "…") if len(content) > 40 else content
    store.write_json(_chat_path(scope_id, cid), d)
    # Upward sync: record a compact event for every ancestor.
    if role == "user":
        sync_up(scope_id, f"{_label(scope_id)}: “{(content or kind)[:80]}”")
    return msg


def save_attachment(filename: str, data: bytes) -> dict:
    """Store an uploaded file under data/scope_files and return its descriptor."""
    fid = uuid.uuid4().hex[:16]
    safe_name = (filename or "file").replace("/", "_").replace("\\", "_")
    d = store.ensure_dir("scope_files")
    path = d / f"{fid}__{safe_name}"
    with open(path, "wb") as f:
        f.write(data)
    ext = safe_name.rsplit(".", 1)[-1].lower() if "." in safe_name else ""
    if ext in ("png", "jpg", "jpeg", "gif", "webp", "heic"):
        kind = "image"
    elif ext in ("m4a", "mp3", "wav", "aac", "ogg", "webm", "caf"):
        kind = "audio"
    elif ext == "zip":
        kind = "zip"
    else:
        kind = "file"
    desc = {"id": fid, "name": safe_name, "url": f"/scope/file/{fid}", "kind": kind, "size": len(data)}
    # A voice note is also transcribed to text (beside the audio) so the CTO/agents can read it.
    if kind == "audio":
        desc["transcript"] = transcribe(path)
    return desc


_WHISPER = {"model": None, "tried": False}


def transcribe(path) -> str:
    """Best-effort speech-to-text for voice notes. Uses faster-whisper or whisper if installed;
    returns '' (audio still kept) if no transcriber is available — never raises."""
    try:
        if not _WHISPER["tried"]:
            _WHISPER["tried"] = True
            try:
                from faster_whisper import WhisperModel  # type: ignore
                _WHISPER["model"] = ("fw", WhisperModel("base", device="cpu", compute_type="int8"))
            except Exception:
                try:
                    import whisper  # type: ignore
                    _WHISPER["model"] = ("w", whisper.load_model("base"))
                except Exception:
                    _WHISPER["model"] = None
        m = _WHISPER["model"]
        if not m:
            return ""
        if m[0] == "fw":
            segs, _info = m[1].transcribe(str(path))
            return " ".join(s.text for s in segs).strip()
        return (m[1].transcribe(str(path)).get("text") or "").strip()
    except Exception:
        return ""


def attachment_path(fid: str):
    """Resolve a stored attachment by id → filesystem path (or None)."""
    d = store.ensure_dir("scope_files")
    for p in d.glob(f"{fid}__*"):
        return p
    return None


def delete_message(scope_id: str, cid: str, mid: str) -> bool:
    """Delete a single message (WhatsApp-style). Persistent pool — only removed when asked."""
    d = get_chat(scope_id, cid)
    if not d:
        return False
    before = len(d.get("messages", []))
    d["messages"] = [m for m in d.get("messages", []) if m.get("id") != mid]
    if len(d["messages"]) != before:
        d["updated"] = store.now()
        store.write_json(_chat_path(scope_id, cid), d)
        return True
    return False


def set_session(scope_id: str, cid: str, session_id: str):
    d = get_chat(scope_id, cid)
    if d and session_id:
        d["session_id"] = session_id
        store.write_json(_chat_path(scope_id, cid), d)


def rename_chat(scope_id: str, cid: str, title: str):
    d = get_chat(scope_id, cid)
    if not d:
        return None
    d["title"] = (title or "").strip() or d.get("title", "New chat")
    store.write_json(_chat_path(scope_id, cid), d)
    return d


def delete_chat(scope_id: str, cid: str) -> bool:
    d = get_chat(scope_id, cid)
    if not d:
        return False
    store.write_json(_chat_path(scope_id, cid), {"id": cid, "deleted": True, "messages": []})
    return True


# ---- summaries + upward sync ----------------------------------------------------
def _label(scope_id: str) -> str:
    if scope_id == "company":
        return "Company"
    if scope_id.startswith("project:"):
        return f"Project {scope_id.split(':',1)[1]}"
    if scope_id.startswith("member:"):
        _, pid, agent = scope_id.split(":", 2)
        return f"{agent}@{pid}"
    return scope_id


def sync_up(scope_id: str, event: str, max_feed: int = 200) -> None:
    """Append a compact event to every ancestor's feed so higher scopes stay synchronized."""
    for anc in ancestors(scope_id):
        m = _meta(anc)
        m.setdefault("feed", []).append({"ts": store.now(), "from": scope_id, "event": event})
        m["feed"] = m["feed"][-max_feed:]
        store.write_json(_meta_path(anc), m)


def get_summary(scope_id: str) -> dict:
    return _meta(scope_id)


def set_summary(scope_id: str, text: str) -> dict:
    m = _meta(scope_id)
    m["summary"] = text
    store.write_json(_meta_path(scope_id), m)
    return m


# ---- drill-down (parent reads children) -----------------------------------------
def children_of(scope_id: str) -> list[str]:
    """Members of a project (project scope) — derived from the agent registry if available."""
    if scope_id.startswith("project:"):
        pid = scope_id.split(":", 1)[1]
        try:
            import agents_registry  # type: ignore
            return [f"member:{pid}:{a['name']}" for a in agents_registry.list_agents(pid)]
        except Exception:
            return []
    return []


def read_child_chats(scope_id: str) -> list:
    """A project CTO can view its members' chats (separate but interconnected)."""
    out = []
    for child in children_of(scope_id):
        out.append({"scope": child, "label": _label(child), "chats": list_chats(child)})
    return out
