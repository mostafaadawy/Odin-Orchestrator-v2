"""
Persistent chat store for the cockpit — one JSON file per conversation under chats/.

Makes the cockpit non-volatile: conversations survive refresh/restart, can be listed,
renamed, and deleted. Each chat also remembers its Claude Code session_id so the engine keeps
context across turns (real conversation memory).
"""
import json
import time
import uuid
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
CHATS_DIR = ROOT / "workspace" / "chats"
CHATS_DIR.mkdir(parents=True, exist_ok=True)


def _path(cid: str) -> pathlib.Path:
    return CHATS_DIR / f"{cid}.json"


def _save(d: dict) -> dict:
    d["updated"] = time.time()
    _path(d["id"]).write_text(json.dumps(d, ensure_ascii=False, indent=2))
    return d


def list_chats() -> list:
    out = []
    for p in sorted(CHATS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            d = json.loads(p.read_text())
            if d.get("deleted"):
                continue  # logically deleted (where hard unlink wasn't possible)
            out.append({"id": d["id"], "title": d.get("title", "New chat"),
                        "updated": d.get("updated"), "count": len(d.get("messages", []))})
        except Exception:
            pass
    return out


def create_chat(title: str = "New chat") -> dict:
    # Reuse an existing EMPTY "New chat" instead of piling up duplicates.
    if title == "New chat":
        for c in list_chats():
            if c.get("count", 0) == 0 and c.get("title") == "New chat":
                return get_chat(c["id"]) or {}
    cid = uuid.uuid4().hex[:12]
    return _save({"id": cid, "title": title, "created": time.time(),
                  "session_id": None, "messages": []})


def get_chat(cid: str):
    p = _path(cid)
    return json.loads(p.read_text()) if p.exists() else None


def add_message(cid: str, role: str, content: str):
    d = get_chat(cid)
    if not d:
        return None
    d["messages"].append({"role": role, "content": content, "ts": time.time()})
    if d.get("title", "New chat") == "New chat" and role == "user":
        d["title"] = (content[:40] + "…") if len(content) > 40 else content
    return _save(d)


def set_session(cid: str, session_id: str):
    d = get_chat(cid)
    if d and session_id:
        d["session_id"] = session_id
        _save(d)


def rename_chat(cid: str, title: str):
    d = get_chat(cid)
    if not d:
        return None
    d["title"] = title.strip() or d.get("title", "New chat")
    return _save(d)


def delete_chat(cid: str) -> bool:
    p = _path(cid)
    if not p.exists():
        return False
    try:
        p.unlink()  # normal case (works on the owner's Mac)
        return True
    except Exception:
        # Hard delete blocked (e.g. restricted mount) -> mark logically deleted; list skips it.
        try:
            p.write_text(json.dumps({"id": cid, "deleted": True, "messages": []}))
        except Exception:
            pass
        return True
