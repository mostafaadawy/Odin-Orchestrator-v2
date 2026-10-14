#!/usr/bin/env python3
"""
local_poller_http.py — the LOCAL machine (your Mac) working against a REMOTE anchor.

This is the Phase-3 client: it reaches the anchor ONLY over HTTP (no shared files, no
in-process calls), pulls pending tasks, runs each through the REAL CTO→team orchestration
(grounded in real read-only connector data), and posts the result back. The anchor then
delivers the webhook + handles retries.

Run (pointing at the stand-in or the real VM anchor):
    python3 server/local_poller_http.py --anchor http://localhost:19100
    python3 server/local_poller_http.py --anchor http://YOUR_VM_IP:PORT
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.request
import urllib.error

import anchor  # real orchestration processor (anchor.process)


def _key() -> str:
    try:
        from integrations import cred
        return cred.get("ANCHOR_API_KEY", "")
    except Exception:
        return ""


def _req(method: str, url: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Content-Type", "application/json")
    k = _key()
    if k:
        r.add_header("X-API-Key", k)
    # the anchor is reached via the VM's nginx reverse proxy (https, self-signed cert for the IP) — the
    # poller runs on your Mac, so accept that self-signed cert for HTTPS. Plain http is unaffected.
    ctx = None
    if url.startswith("https"):
        import ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(r, timeout=60, context=ctx) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else {}


def poll_once(base: str) -> int:
    base = base.rstrip("/")
    tasks = _req("GET", f"{base}/anchor/v1/poll").get("tasks", [])
    any_chat = False
    for t in tasks:
        rid = t["id"]
        out = None
        is_chat = (t.get("sender") == "chat")
        is_command = (t.get("sender") == "command")
        print(f"[local-poller] processing {rid} (project {t.get('project')}"
              f"{' · CHAT' if is_chat else ''}{' · COMMAND' if is_command else ''})…")
        if is_command:
            # WRITE action (create_project, clear_scope, …) — executed on the backend on the app's behalf.
            answer = _run_command(t)
            any_chat = True   # trigger an immediate mirror push so web/mobile see the change
        elif is_chat:
            # CHAT goes through the SAME brain path as the desktop (/scope/stream): it uses the conversation
            # HISTORY and PERSISTS the turn to the shared pool — so replies are in-context and every surface
            # (web/mobile/desktop) shows the identical, consistent conversation.
            payload = t.get("payload") or {}
            scope = (payload.get("scope") if isinstance(payload, dict) else None) or t.get("project") or "company"
            text = (payload.get("text") or payload.get("prompt") or "") if isinstance(payload, dict) else ""
            try:
                answer = _brain_chat_stream(scope, text)
                any_chat = True
            except Exception as e:
                print(f"[local-poller] {rid} chat error: {e}")
                answer = "(the assistant is temporarily unavailable — try again)"
        else:
            out = anchor.process(t)  # CTO → agent → result, grounded in real read-only data
            answer = out.get("answer")
        try:
            _req("POST", f"{base}/anchor/v1/requests/{rid}/result", {"result": answer})
            secs = out.get("secs") if out else 0
            via = out.get("via") if out else ("chat" if is_chat else "command" if is_command else "?")
            print(f"[local-poller] {rid} done in {secs}s via {via} → result posted")
        except urllib.error.HTTPError as e:
            print(f"[local-poller] {rid} result POST failed: {e.code} {e.read().decode()[:200]}")
    if any_chat:
        try:
            sync_push(base)   # push the updated pools to the anchor NOW so other surfaces sync immediately
        except Exception:
            pass
    return len(tasks)


def _brain_post(path: str, body: dict):
    brain = os.environ.get("ODIN_BRAIN", "http://localhost:18000").rstrip("/")
    data = json.dumps(body).encode()
    req = urllib.request.Request(brain + path, data=data, method="POST")
    req.add_header("content-type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw else {}


def _brain_delete(path: str):
    brain = os.environ.get("ODIN_BRAIN", "http://localhost:18000").rstrip("/")
    req = urllib.request.Request(brain + path, method="DELETE")
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw else {}


def _run_command(t: dict) -> str:
    """Execute a client WRITE command on the backend (create a project, clear a conversation, …)."""
    from urllib.parse import quote
    payload = t.get("payload") or {}
    kind = payload.get("kind") if isinstance(payload, dict) else None
    if kind == "create_project":
        name = (payload.get("name") or "New project").strip() or "New project"
        try:
            r = _brain_post("/projects", {"name": name, "description": "", "type": "", "mode": "build",
                                          "cadence": "once", "autoApprove": True})
            return f"created project: {r.get('name') or name}"
        except Exception as e:
            return f"create_project error: {e}"
    if kind == "create_chat":
        title = (payload.get("title") or "New chat").strip() or "New chat"
        try:
            r = _brain_post("/chats", {"title": title})
            return r.get("scope", "")   # return the new scope so the client can open it
        except Exception as e:
            return f"create_chat error: {e}"
    if kind == "rename_chat":
        scope = payload.get("scope") or ""
        title = (payload.get("title") or "").strip()
        try:
            _brain_post(f"/chats/rename?scope={quote(scope)}", {"title": title})
            return "renamed"
        except Exception as e:
            return f"rename_chat error: {e}"
    if kind == "delete_chat":
        scope = payload.get("scope") or ""
        try:
            _brain_delete(f"/chats/{scope}")
            return "deleted"
        except Exception as e:
            return f"delete_chat error: {e}"
    if kind == "clear_scope":
        scope = payload.get("scope") or ""
        try:
            d = _brain_get(f"/scope/chats?scope={quote(scope)}")
            for c in d.get("chats", []):
                try:
                    _brain_delete(f"/scope/chat?scope={quote(scope)}&cid={quote(str(c.get('id','')))}")
                except Exception:
                    pass
            return "cleared"
        except Exception as e:
            return f"clear_scope error: {e}"
    if kind == "run_now":
        pid = payload.get("pid") or ""
        prompt = (payload.get("prompt") or "").strip()
        cid = payload.get("cid") or ""
        try:
            r = _brain_post(f"/projects/{quote(pid)}/run-now", {"prompt": prompt, "cid": cid})
            return r.get("message", "Running now…")
        except Exception as e:
            return f"run_now error: {e}"
    if kind == "mark_notif":
        # web/mobile in anchor mode marked a notification read → apply it on the brain (syncs back via mirror)
        try:
            _brain_post("/notifications/read", {"id": payload.get("id", ""), "all": bool(payload.get("all"))})
            return "notification marked read"
        except Exception as e:
            return f"mark_notif error: {e}"
    if kind == "post_message":
        # web/mobile in anchor mode: a REPLY / attachment / voice / forward it created must reach the
        # brain pool (then mirror back to every device). Plain text uses chat_stream; these rich posts
        # come here so they no longer silently fail in production. Idempotent via client_msg_id.
        scope = payload.get("scope") or ""
        cid = payload.get("cid") or _ensure_scope_chat(scope)
        body = {"role": payload.get("role", "user"), "content": payload.get("content", "")}
        for src, dst in (("sender", "sender"), ("msg_kind", "kind"), ("attachment", "attachment"),
                         ("reply_to", "reply_to"), ("client_msg_id", "client_msg_id")):
            if payload.get(src) is not None:
                body[dst] = payload.get(src)
        try:
            _brain_post(f"/scope/message?scope={quote(scope)}&cid={quote(str(cid))}", body)
            return "message posted"
        except Exception as e:
            return f"post_message error: {e}"
    if kind == "delete_message":
        # web/mobile delete must propagate everywhere (WhatsApp-style) — apply on the brain; the mirror
        # then removes it from every device on the next sync.
        scope = payload.get("scope") or ""
        cid = payload.get("cid") or ""
        mid = payload.get("mid") or ""
        try:
            _brain_delete(f"/scope/message?scope={quote(scope)}&cid={quote(str(cid))}&mid={quote(str(mid))}")
            return "message deleted"
        except Exception as e:
            return f"delete_message error: {e}"
    if kind == "meeting_report":
        # MOBILE live-meeting: phone transcribed on-device and sent the chunk texts; build the report on
        # the brain (raw engine, bilingual) and post it into the project chat (syncs back to the phone).
        pid = payload.get("pid") or ""
        texts = payload.get("texts") or []
        lang = payload.get("lang") or ""
        try:
            r = _brain_post(f"/meeting/finish_text?pid={quote(pid)}", {"texts": texts, "lang": lang})
            return f"meeting report ready ({r.get('chunks',0)} chunks, {r.get('lang','')})"
        except Exception as e:
            return f"meeting_report error: {e}"
    return "unknown command"


def _ensure_scope_chat(scope: str) -> str:
    from urllib.parse import quote
    try:
        d = _brain_get(f"/scope/chats?scope={quote(scope)}")
        chats = d.get("chats", [])
        if chats:
            return str(chats[0].get("id", ""))
        c = _brain_post(f"/scope/chats?scope={quote(scope)}", {"title": "App chat"})
        return str(c.get("id", ""))
    except Exception:
        return ""


def _brain_chat_stream(scope: str, text: str) -> str:
    """Run a chat turn through the brain's /scope/stream — the SAME path the desktop uses. It processes WITH
    the conversation history and PERSISTS both the user message and the reply into the shared pool. We drain
    the stream (ignore tokens) and then read the last assistant message back from the pool as the reply."""
    from urllib.parse import quote
    brain = os.environ.get("ODIN_BRAIN", "http://localhost:18000").rstrip("/")
    cid = _ensure_scope_chat(scope)
    url = f"{brain}/scope/stream?scope={quote(scope)}&text={quote(text)}&lang=en&cid={quote(str(cid))}"
    import time as _t
    _start = _t.time()
    try:
        req = urllib.request.Request(url, headers={"Accept": "text/event-stream"})
        with urllib.request.urlopen(req, timeout=90) as r:
            for _line in r:   # drain — the brain persists user+assistant to the pool. Bounded so it can
                if _t.time() - _start > 90:   # never hang the poller: give up draining after 90s and read back.
                    break
                pass
    except Exception as e:
        print(f"[local-poller] scope/stream note: {e}")
    # read back the reply the brain just persisted (last assistant message in this scope)
    try:
        m = _brain_get(f"/scope/messages?scope={quote(scope)}")
        for x in reversed(m.get("messages") or []):
            if x.get("role") == "assistant":
                return x.get("content", "")
    except Exception:
        pass
    return ""


def _brain_get(path: str):
    """Read from the LOCAL brain (this Mac) — used to mirror projects/pools up to the anchor."""
    brain = os.environ.get("ODIN_BRAIN", "http://localhost:18000").rstrip("/")
    with urllib.request.urlopen(brain + path, timeout=15) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw else {}


_sync_every = 0


def sync_push(base: str):
    """WhatsApp-style mirror: push the brain's project list (with agents) + each project's message pool
    UP to the anchor so web/mobile can read them directly (fast, paginated). Incremental + best-effort."""
    global _sync_every
    try:
        from urllib.parse import quote
        d = _brain_get("/projects")
        projects = d.get("projects", d if isinstance(d, list) else [])
        pools = {}
        # Push EVERY scope pool each cycle — the company chat ('company') AND every project — so web/mobile
        # stay in sync with the desktop for ALL chats (main Chief-Engineer chat + project chats).
        # canonical scopes: 'company' for the main chat, 'project:<id>' for each project (same keys the app,
        # brain and desktop use) — so every surface reads/writes the SAME pool.
        # standalone chats registry (server-side, shared by all surfaces)
        chats = []
        try:
            chats = _brain_get("/chats").get("chats", [])
        except Exception:
            pass
        scopes = ["company"] + [f"project:{p.get('id')}" for p in projects if p.get("id")] \
            + [c.get("scope") for c in chats if c.get("scope")]
        for sc in scopes:
            try:
                m = _brain_get(f"/scope/messages?scope={quote(str(sc))}")
                # CAP each pool to the last 60 messages — pushing EVERY message of EVERY scope made the sync
                # body exceed the anchor's size limit (HTTP 413) which silently killed the WHOLE project sync
                # (request page + web/mobile showed no projects). Web/mobile paginate older history separately.
                pools[sc] = (m.get("messages") or m.get("pool") or [])[-60:]
            except Exception:
                pass
        _sync_every += 1
        body = {"projects": projects}
        if pools:
            body["pools"] = pools
        # widen the mirror to ALL statuses (activity/agents-live/health) so web+mobile match the desktop
        agents = {}
        try:
            act = _brain_get("/activity")
            agents = {"active": act.get("active", []), "tasks": act.get("tasks", {})}
        except Exception:
            pass
        try:
            agents["health"] = _brain_get("/health")
        except Exception:
            pass
        if agents:
            body["agents"] = agents
        # GENERIC MIRROR — push the brain's raw JSON for every read the app needs, so flutter/web read
        # EVERYTHING from the anchor (zero direct-backend calls). Best-effort per key.
        mirror = {}
        for key, path in (("roles", "/roles"), ("company_agents", "/company/agents"),
                          ("all_agents", "/agents/all"),
                          ("connectors", "/connectors"), ("activity", "/activity"),
                          ("hubspot", "/hubspot/overview"),   # HubSpot badge + counts for web/mobile (anchor)
                          ("notifications", "/notifications"),   # live bell for web/mobile in anchor mode
                          # Phase-6 GENERIC UI contract — type-driven cards/controls/icons + agent roster,
                          # mirrored so web/mobile render identically to desktop from ONE payload (no direct calls).
                          ("ui_projects", "/ui/projects"),
                          ("ui_agents", "/ui/agents"),
                          ("ui_types", "/ui/types"),
                          ("ui_connectors", "/ui/connectors")):
            try:
                mirror[key] = _brain_get(path)
            except Exception:
                pass
        mirror["chats"] = {"chats": chats}   # standalone chats list → web/mobile read it from the anchor
        if mirror:
            body["mirror"] = mirror
        _req("POST", f"{base.rstrip('/')}/anchor/v1/sync", body)
        print(f"[local-poller] synced {len(projects)} projects, {len(pools)} pools, {len(mirror)} mirror keys → anchor")
    except Exception as e:
        print(f"[local-poller] sync push error: {e}")


def run(base: str, interval: float):
    print(f"[local-poller] polling {base} every {interval}s  (auth={'on' if _key() else 'off'})")
    while True:
        try:
            poll_once(base)
        except Exception as e:
            print(f"[local-poller] poll error: {e}")
        try:
            sync_push(base)   # keep web/mobile's WhatsApp-style view fresh
        except Exception as e:
            print(f"[local-poller] sync error: {e}")
        time.sleep(interval)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchor", default="http://localhost:19100", help="base URL of the (remote) anchor")
    ap.add_argument("--interval", type=float, default=5.0)
    args = ap.parse_args()
    run(args.anchor, args.interval)
