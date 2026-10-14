#!/usr/bin/env python3
"""
anchor_remote.py — the STAND-IN for the *deployed* anchor (Phase 3), runnable now.

It serves the EXACT `/anchor/v1` contract over real HTTP on a configurable host:port,
backed by the same `anchor_queue` module the in-process anchor uses. This is the only
piece we "fake" — its *location* (localhost:PORT here vs the Azure VM ip:port later).
Everything that talks to it — the Flutter app and the local poller — does so purely over
HTTP, so cutover to the real VM is a base-URL change and nothing else.

It deliberately runs WITHOUT a local processor: on the VM the anchor only relays. The
LOCAL machine (your Mac) pulls work via `local_poller_http.py` and posts results back.

Run:
    python3 server/anchor_remote.py --host 0.0.0.0 --port 19100
Auth: if ANCHOR_API_KEY is set in workspace/shared/oth/.cred, callers must send  X-API-Key: <key>
      on /poll, /result and admin endpoints (third-party intake stays open like the contract).
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

import anchor_queue as q
import anchor_manage as mng
import store


def _want_key() -> str:
    try:
        from integrations import cred
        return cred.get("ANCHOR_API_KEY", "")
    except Exception:
        return ""


def _public(r: dict) -> dict:
    return {k: r.get(k) for k in ("id", "project", "status", "result", "webhook_attempts",
                                  "acked", "error", "created", "updated", "history")}


# ---- WhatsApp-style SYNC STORE (single source of truth mirrored from the Mac's brain) ----
# The local poller PUSHES the project list + each project's message pool here (incremental). Web/mobile
# then READ it directly from the anchor (fast, paginated, lazy-loaded) — no engine call on open. This is
# what makes projects/agents/messages appear on every surface, like WhatsApp.
#
# DURABLE (survives anchor restarts AND desktop-offline periods): the snapshot is PERSISTED to disk on
# every push and RELOADED on startup. Without this the mirror was a volatile in-memory global — an anchor
# restart (systemd) or a stopped poller wiped it to empty, so the web/mobile rendered NOTHING (updated:0).
# Now the last-synced projects always remain visible, with `updated` powering an "offline / last synced X
# ago" badge when the desktop is closed. Exactly WhatsApp: your messages are there even when the phone is off.
_SYNC_FILE = "anchor_sync.json"
# "mirror" is a GENERIC bucket of the brain's raw JSON keyed by name (roles, company_agents, connectors,
# activity, …) so web/mobile read EVERYTHING from the anchor — zero direct-backend calls.
_SYNC_DEFAULT = {"projects": [], "agents": {}, "pools": {}, "mirror": {}, "updated": 0}


def _load_sync() -> dict:
    try:
        s = store.read_json(_SYNC_FILE, dict(_SYNC_DEFAULT)) or dict(_SYNC_DEFAULT)
        # be defensive about shape so a malformed file can never crash reads
        return {"projects": s.get("projects", []) if isinstance(s.get("projects"), list) else [],
                "agents": s.get("agents", {}) if isinstance(s.get("agents"), dict) else {},
                "pools": s.get("pools", {}) if isinstance(s.get("pools"), dict) else {},
                "mirror": s.get("mirror", {}) if isinstance(s.get("mirror"), dict) else {},
                "updated": int(s.get("updated", 0) or 0)}
    except Exception:
        return dict(_SYNC_DEFAULT)


SYNC = _load_sync()


def _persist_sync() -> None:
    try:
        store.write_json(_SYNC_FILE, SYNC)
    except Exception:
        pass


def _landing_html() -> str:
    """The anchor's public LANDING PAGE (browser view of the secure hub). Shows it is ONLINE plus live
    counts, so simply reaching this page is proof the anchor is up."""
    import time as _t
    try:
        counts = q.counts()
    except Exception:
        counts = {}
    nproj = len(SYNC.get("projects", []) or [])
    upd = int(SYNC.get("updated", 0) or 0)
    ago = ("%ds ago" % (int(_t.time()) - upd)) if upd else "not yet"
    rows = "".join("<span class='pill'>" + str(k) + ": <b>" + str(v) + "</b></span>"
                   for k, v in sorted(counts.items())) or "<span class='pill dim'>no requests yet</span>"
    # token replacement (NOT %/format) — the CSS below contains % and {} which would break those.
    return _LANDING_TMPL.replace("__NPROJ__", str(nproj)).replace("__AGO__", ago).replace("__ROWS__", rows)


_LANDING_TMPL = """<!doctype html><html><head><meta charset='utf-8'><title>Odin Anchor — Online</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
 body{margin:0;font-family:-apple-system,Segoe UI,system-ui,sans-serif;background:
  radial-gradient(1000px 500px at 10% -10%,rgba(108,140,255,.18),transparent 60%),#0a0c12;color:#e8ecf6;
  min-height:100vh;display:flex;align-items:center;justify-content:center}
 .card{background:#141a29;border:1px solid rgba(255,255,255,.12);border-radius:18px;padding:34px 40px;max-width:560px}
 .mark{width:56px;height:56px;border-radius:16px;display:grid;place-items:center;font-weight:800;font-size:28px;color:#0a0c12;
  background:conic-gradient(from 220deg,#6c8cff,#b07cff,#7af0d0,#6c8cff)}
 h1{font-size:20px;margin:16px 0 2px} .dot{color:#4be3a0}
 .sub{color:#9aa4bf;font-size:13px;margin-bottom:16px}
 .pill{display:inline-block;font-size:11.5px;padding:4px 10px;border-radius:999px;border:1px solid rgba(255,255,255,.12);
  color:#c9d2ee;margin:4px 6px 0 0} .pill.dim{color:#9aa4bf}
 code{color:#7af0d0}
</style></head><body><div class='card'>
 <div class='mark'>&#937;</div>
 <h1><span class='dot'>&#9679;</span> Odin Anchor — ONLINE</h1>
 <div class='sub'>The secure hub (queue + webhooks). Web &amp; mobile reach your machine only through here.</div>
 <div><span class='pill'>projects synced: <b>__NPROJ__</b></span><span class='pill'>last sync: <b>__AGO__</b></span></div>
 <div style='margin-top:6px'>__ROWS__</div>
 <div style='margin-top:18px'><a href='manage' onclick="event.preventDefault();var b=location.pathname.replace(/[/]+$/,'');location.href=b+'/manage';"
   style='display:inline-block;background:linear-gradient(135deg,#6c8cff,#7af0d0);color:#0a0c12;font-weight:800;
   text-decoration:none;padding:10px 18px;border-radius:11px'>&#128273; Manage (owner)</a></div>
 <div class='sub' style='margin-top:16px'>API: <code>/anchor/v1/_status</code> · <code>/anchor/v1/projects</code> ·
  <code>POST /anchor/v1/requests</code> · <code>/anchor/v1/requests/{id}</code></div>
</div></body></html>"""


def _manage_html() -> str:
    return _MANAGE_TMPL


_MANAGE_TMPL = """<!doctype html><html><head><meta charset='utf-8'><title>Odin Anchor — Manage</title>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<style>
 body{margin:0;font-family:-apple-system,Segoe UI,system-ui,sans-serif;background:
  radial-gradient(1000px 500px at 10% -10%,rgba(108,140,255,.16),transparent 60%),#0a0c12;color:#e8ecf6;min-height:100vh}
 .wrap{max-width:820px;margin:0 auto;padding:28px 20px}
 h1{font-size:20px;margin:0 0 4px} .sub{color:#9aa4bf;font-size:13px}
 .card{background:#141a29;border:1px solid rgba(255,255,255,.12);border-radius:14px;padding:20px;margin-top:16px}
 label{display:block;font-size:12px;color:#9aa4bf;margin:10px 0 4px}
 input[type=text],input[type=password]{width:100%;box-sizing:border-box;background:#0e1320;border:1px solid rgba(255,255,255,.12);
  color:#e8ecf6;border-radius:9px;padding:10px 12px;font-size:14px;outline:none}
 button{background:#6c8cff;color:#0a0c12;font-weight:700;border:0;border-radius:9px;padding:9px 15px;font-size:13px;cursor:pointer}
 button.ghost{background:#222a3f;color:#e8ecf6} button.danger{background:#2a1420;color:#ff6b81;border:1px solid rgba(255,255,255,.12)}
 .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
 .muted{color:#9aa4bf;font-size:12px} .ok{color:#4be3a0} .bad{color:#ff6b81}
 table{width:100%;border-collapse:collapse;font-size:12.5px;margin-top:8px}
 th,td{text-align:left;padding:7px 8px;border-bottom:1px solid rgba(255,255,255,.08)} th{color:#9aa4bf;font-weight:600}
 .pill{display:inline-block;font-size:11px;padding:2px 9px;border-radius:999px;border:1px solid rgba(255,255,255,.12);color:#c9d2ee}
 .sw{display:flex;align-items:center;justify-content:space-between;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.08)}
 a{color:#7af0d0}
</style></head><body><div class='wrap'>
 <h1>&#128273; Odin Anchor — Manage</h1>
 <div class='sub'>Protected owner area. <a href='#' onclick="event.preventDefault();location.href=location.pathname.replace(/manage[/]?$/,'');">&larr; back to landing</a></div>

 <div class='card' id='loginCard'>
   <div style='font-weight:700;margin-bottom:4px'>Sign in</div>
   <div class='muted'>A confirmation code was just generated — open <b>&ldquo;Connecting with Anchor&rdquo;</b> on your desktop to see the email, password and code, then enter them here.</div>
   <label>Email</label><input id='email' type='text' autocomplete='off' placeholder='you@company.com'>
   <label>Password</label><input id='password' type='password' autocomplete='off'>
   <div id='codeRow'><label>Confirmation code (from your desktop)</label><input id='code' type='text' autocomplete='off' placeholder='6 digits'></div>
   <label class='row' style='margin-top:12px'><input type='checkbox' id='remember' style='width:auto'> &nbsp;Remember this device &amp; browser (skip the code next time)</label>
   <div class='row' style='margin-top:14px'><button onclick='doLogin()'>Sign in</button><button class='ghost' onclick='newCode()'>Resend code</button><span id='msg' class='bad'></span></div>
 </div>

 <div id='panel' style='display:none'>
   <div class='card'>
     <div class='row' style='justify-content:space-between'>
       <div style='font-weight:700'>Requests <span id='counts' class='muted'></span></div>
       <div class='row'><button class='ghost' onclick='loadReqs()'>&#8635; Refresh</button><button class='danger' onclick='clearReqs()'>&#128465; Clear all</button><button class='ghost' onclick='logout()'>Sign out</button></div>
     </div>
     <div id='reqs'><div class='muted'>loading…</div></div>
   </div>
   <div class='card'>
     <div style='font-weight:700;margin-bottom:6px'>Access control</div>
     <div class='sw'><div><b>Mobile app</b><div class='muted'>allow the phone app to read from the anchor</div></div><label class='row'><input type='checkbox' id='am' onchange='saveSettings()' style='width:auto'> allowed</label></div>
     <div class='sw'><div><b>Web app</b><div class='muted'>allow the web app to read from the anchor</div></div><label class='row'><input type='checkbox' id='aw' onchange='saveSettings()' style='width:auto'> allowed</label></div>
   </div>
 </div>
</div>
<script>
// PROXY-AWARE: build the API base from the CURRENT url so it works both at the root (localhost:19100/manage)
// AND behind the /odin-anchor reverse proxy (/odin-anchor/manage → /odin-anchor/anchor/v1/manage).
const A=(location.pathname.replace(/[/]manage[/]?$/,'').replace(/[/]+$/,''))+'/anchor/v1/manage';
function $(i){return document.getElementById(i);} function v(i){return $(i).value.trim();}
function msg(t){$('msg').textContent=t||'';}
let TOKEN=localStorage.getItem('odin.manage.token')||'';
let DEV=localStorage.getItem('odin.manage.device');
if(!DEV){ DEV='dev_'+Math.random().toString(36).slice(2)+Date.now().toString(36); localStorage.setItem('odin.manage.device',DEV); }
async function newCode(){ try{ await fetch(A+'/request-code',{method:'POST'}); msg('code sent to your desktop'); setTimeout(()=>msg(''),2500);}catch(e){} }
async function init(){
  try{ await fetch(A+'/request-code',{method:'POST'}); }catch(e){}
  try{ const r=await fetch(A+'/check-device',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({device_id:DEV})});
    if((await r.json()).remembered){ $('codeRow').style.display='none'; } }catch(e){}
  if(TOKEN){ showPanel(); }
}
async function doLogin(){
  msg('');
  const r=await fetch(A+'/login',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({email:v('email'),password:v('password'),code:v('code'),remember:$('remember').checked,device_id:DEV})});
  const d=await r.json();
  if(d.ok){ TOKEN=d.token; localStorage.setItem('odin.manage.token',TOKEN); showPanel(); }
  else{ msg(d.error||'sign in failed'); }
}
function showPanel(){ $('loginCard').style.display='none'; $('panel').style.display='block'; loadReqs(); loadSettings(); }
function showLogin(){ $('panel').style.display='none'; $('loginCard').style.display='block'; }
function H(){ return {'Content-Type':'application/json','X-Manage-Token':TOKEN}; }
async function loadReqs(){
  const r=await fetch(A+'/requests',{headers:H()}); if(r.status===401){ return logout(); }
  const d=await r.json(); const rs=d.requests||[];
  $('counts').textContent='('+rs.length+')';
  if(!rs.length){ $('reqs').innerHTML='<div class="muted">no requests</div>'; return; }
  let h='<table><tr><th>id</th><th>project</th><th>status</th><th></th></tr>';
  rs.forEach(x=>{ h+='<tr><td>'+String(x.id).slice(0,14)+'</td><td>'+(x.project||'')+'</td><td><span class="pill">'+(x.status||'')+'</span></td>'
    +'<td><button class="danger" onclick="delReq(\\''+x.id+'\\')">delete</button></td></tr>'; });
  $('reqs').innerHTML=h+'</table>';
}
async function delReq(id){ await fetch(A+'/requests/'+encodeURIComponent(id),{method:'DELETE',headers:H()}); loadReqs(); }
async function clearReqs(){ if(!confirm('Delete ALL requests on the anchor?'))return; await fetch(A+'/requests/clear',{method:'POST',headers:H()}); loadReqs(); }
async function loadSettings(){ const r=await fetch(A+'/settings',{headers:H()}); const s=await r.json(); $('am').checked=s.allow_mobile!==false; $('aw').checked=s.allow_web!==false; }
async function saveSettings(){ await fetch(A+'/settings',{method:'POST',headers:H(),body:JSON.stringify({allow_mobile:$('am').checked,allow_web:$('aw').checked})}); }
async function logout(){ try{ await fetch(A+'/logout',{method:'POST',headers:H()});}catch(e){} TOKEN=''; localStorage.removeItem('odin.manage.token'); showLogin(); }
init();
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "OdinAnchorRemote/1.0"

    # ---- helpers ----
    def _send(self, code: int, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-API-Key, X-Manage-Token, X-Odin-Client")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, code: int, html: str):
        body = html.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def _body(self) -> dict:
        n = int(self.headers.get("Content-Length") or 0)
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode() or "{}")
        except Exception:
            return {}

    def _auth_ok(self) -> bool:
        want = _want_key()
        if not want:
            return True
        return (self.headers.get("X-API-Key") or "") == want

    def log_message(self, *a):  # quiet
        pass

    def do_OPTIONS(self):
        self._send(200, {"ok": True})

    # PERMANENT SAFEGUARD: never let a bug in one route crash the whole anchor (that caused the 502 loop).
    # Every request is wrapped — any exception returns a clean 500 and the service keeps serving.
    def do_GET(self):
        try:
            self._do_GET()
        except Exception as e:
            try:
                self._send(500, {"error": "internal", "detail": str(e)[:200]})
            except Exception:
                pass

    def do_POST(self):
        try:
            self._do_POST()
        except Exception as e:
            try:
                self._send(500, {"error": "internal", "detail": str(e)[:200]})
            except Exception:
                pass

    def do_DELETE(self):
        try:
            self._do_DELETE()
        except Exception as e:
            try:
                self._send(500, {"error": "internal", "detail": str(e)[:200]})
            except Exception:
                pass

    # ---- manage helpers ----
    def _mng_token(self) -> str:
        return self.headers.get("X-Manage-Token") or ""

    def _client(self) -> str:
        return (self.headers.get("X-Odin-Client") or "").strip().lower()

    def _client_blocked(self) -> bool:
        """True (and sends 403/401) if this web/mobile client is STOPPED in Manage, OR not logged in.
        Web/mobile MUST authenticate (email+password+desktop code) — no anonymous access to anchor data."""
        cl = self._client()
        if cl in ("mobile", "web"):
            if not mng.client_allowed(cl):
                self._send(403, {"error": cl + " access is currently stopped by the anchor owner",
                                 "stopped": True, "client": cl})
                return True
            if not mng.valid_session(self._mng_token()):
                self._send(401, {"error": "login required", "login_required": True, "client": cl})
                return True
        return False

    # ---- routing ----
    def _do_GET(self):
        u = urlparse(self.path)
        parts = [unquote(p) for p in u.path.split("/") if p]  # decode %3A→: so chat:<id>/project:<id> scopes match
        if u.path == "/" and "text/html" in (self.headers.get("Accept") or ""):
            # A browser hitting the anchor root gets the LANDING PAGE (proof the secure hub is online).
            return self._send_html(200, _landing_html())
        if u.path in ("/manage", "/manage/"):
            return self._send_html(200, _manage_html())
        if u.path in ("/", "/health", "/healthz"):
            return self._send(200, {
                "ok": True, "service": "odin-anchor", "auth_required": bool(_want_key()),
                "endpoints": ["/anchor/v1/_status", "POST /anchor/v1/requests",
                              "/anchor/v1/requests/{id}", "/anchor/v1/poll",
                              "/anchor/v1/admin/requests", "/anchor/v1/admin/counts",
                              "/anchor/v1/admin/config"],
            })
        # /anchor/v1/...
        if parts[:2] != ["anchor", "v1"]:
            return self._send(404, {"error": "not found", "hint": "try /anchor/v1/_status"})
        rest = parts[2:]

        if rest == ["_status"]:
            return self._send(200, {"ok": True, "service": "anchor-remote", "auth_required": bool(_want_key())})

        # ---- MANAGE (protected owner area) ----
        if rest[:1] == ["manage"]:
            sub = rest[1:]
            if sub == ["pending-code"]:               # the DESKTOP polls this (anchor key) to show the code
                if not self._auth_ok():
                    return self._send(401, {"error": "invalid or missing X-API-Key"})
                return self._send(200, mng.pending_code(parse_qs(u.query).get("target", [""])[0]))
            if sub == ["me"]:                         # web/mobile/manage: is my saved session still valid?
                return self._send(200, {"ok": mng.valid_session(self._mng_token())})
            if not mng.valid_session(self._mng_token()):
                return self._send(401, {"error": "manage login required"})
            if sub == ["requests"]:                   # full CRUD read of the anchor's requests
                return self._send(200, {"requests": [_public(x) for x in q.list_requests()], "counts": q.counts()})
            if sub == ["settings"]:
                return self._send(200, mng.settings())
            return self._send(404, {"error": "not found"})

        # ---- WhatsApp-style synced reads (fast, no engine) ----
        if rest == ["projects"]:                      # GET /anchor/v1/projects  → mirrored project list
            if not self._auth_ok():
                return self._send(401, {"error": "invalid or missing X-API-Key"})
            if self._client_blocked():
                return
            import time as _t
            upd = int(SYNC.get("updated", 0) or 0)
            age = int(_t.time()) - upd if upd else -1
            # STALE = the Mac poller hasn't pushed recently (desktop offline/closed). The poller pushes every
            # few seconds, so > 90s without a push means "offline". The web shows the last-synced snapshot
            # plus an "offline · last synced X ago" badge instead of a blank/stuck screen.
            stale = (upd == 0) or (age > 90)
            return self._send(200, {"projects": SYNC.get("projects", []),
                                    "agents": SYNC.get("agents", {}), "updated": upd,
                                    "age_seconds": age, "stale": stale})
        if len(rest) == 2 and rest[0] == "mirror":    # GET /anchor/v1/mirror/{key} → brain's raw JSON (roles, …)
            if not self._auth_ok():
                return self._send(401, {"error": "invalid or missing X-API-Key"})
            if self._client_blocked():
                return
            return self._send(200, SYNC.get("mirror", {}).get(rest[1], {}))
        if len(rest) == 2 and rest[0] == "pool":      # GET /anchor/v1/pool/{pid}?offset=&limit=  (paginated)
            if not self._auth_ok():
                return self._send(401, {"error": "invalid or missing X-API-Key"})
            if self._client_blocked():
                return
            pid = rest[1]
            qs = parse_qs(u.query)   # NOT `q` — `q` is the module-level anchor_queue used by /poll below
            try:
                offset = int((qs.get("offset") or ["0"])[0]); limit = int((qs.get("limit") or ["30"])[0])
            except Exception:
                offset, limit = 0, 30
            pool = SYNC.get("pools", {}).get(pid, [])
            total = len(pool)
            mx = max((m.get("seq", 0) for m in pool), default=0)
            # DELTA SYNC: ?since=<seq> → return ONLY messages newer than that seq (empty when up to date).
            # This is the cursor-based fast/consistent sync — a client fetches only what it's missing, and
            # a missing message is just "seq I don't have yet", so it can never be permanently lost.
            try:
                since = int((qs.get("since") or ["0"])[0])
            except Exception:
                since = 0
            if since:
                delta = [m for m in pool if m.get("seq", 0) > since]
                return self._send(200, {"project": pid, "since": since, "max_seq": mx,
                                        "total": total, "messages": delta, "delta": True})
            # newest-last pool: return the last `limit` items before `total-offset` (lazy scroll-up)
            end = max(0, total - offset)
            start = max(0, end - limit)
            return self._send(200, {"project": pid, "total": total, "offset": offset, "limit": limit,
                                    "max_seq": mx, "messages": pool[start:end], "has_more": start > 0})

        if rest == ["poll"]:
            if not self._auth_ok():
                return self._send(401, {"error": "invalid or missing X-API-Key"})
            return self._send(200, {"tasks": q.next_pending()})

        if len(rest) == 2 and rest[0] == "requests":  # /requests/{id}
            if not self._auth_ok():
                return self._send(401, {"error": "invalid or missing X-API-Key"})
            r = q.get(rest[1])
            return self._send(200, _public(r)) if r else self._send(404, {"error": "no such request"})

        if rest == ["admin", "requests"]:
            if not self._auth_ok():
                return self._send(401, {"error": "invalid or missing X-API-Key"})
            status = (parse_qs(u.query).get("status") or [""])[0]
            return self._send(200, {"requests": [_public(x) for x in q.list_requests(status or None)]})

        if rest == ["admin", "counts"]:
            if not self._auth_ok():
                return self._send(401, {"error": "invalid or missing X-API-Key"})
            return self._send(200, {"counts": q.counts()})

        if rest == ["admin", "config"]:
            if not self._auth_ok():
                return self._send(401, {"error": "invalid or missing X-API-Key"})
            return self._send(200, q.cfg())

        return self._send(404, {"error": "not found"})

    def _do_POST(self):
        u = urlparse(self.path)
        parts = [unquote(p) for p in u.path.split("/") if p]  # decode %3A→: so chat:<id>/project:<id> scopes match
        if parts[:2] != ["anchor", "v1"]:
            return self._send(404, {"error": "not found"})
        rest = parts[2:]
        body = self._body()

        # ---- MANAGE (protected owner area) ----
        if rest[:1] == ["manage"]:
            sub = rest[1:]
            if sub == ["request-code"]:               # Manage pressed → generate a code (desktop will show it).
                # Public on purpose: generating a code is harmless — only the DESKTOP (which holds the API key)
                # can READ it via /manage/pending-code, and login still needs email+password+that code.
                return self._send(200, mng.request_code(body.get("target", "web")))
            if sub == ["check-device"]:               # skip the code on a remembered device
                return self._send(200, mng.check_device(body.get("device_id", "")))
            if sub == ["login"]:
                return self._send(200, mng.login(body.get("email", ""), body.get("password", ""),
                                                 body.get("code", ""), bool(body.get("remember")),
                                                 body.get("device_id", ""), body.get("target", "web")))
            # everything below needs a valid manage session
            if not mng.valid_session(self._mng_token()):
                return self._send(401, {"error": "manage login required"})
            if sub == ["logout"]:
                return self._send(200, mng.logout(self._mng_token()))
            if sub == ["settings"]:
                return self._send(200, mng.set_settings(allow_mobile=body.get("allow_mobile"),
                                                        allow_web=body.get("allow_web")))
            if sub == ["requests", "clear"]:
                return self._send(200, q.clear_all())
            return self._send(404, {"error": "not found"})

        # third-party intake — REQUIRES the API key (auth is not optional on the remote door)
        if rest == ["requests"]:
            if not self._auth_ok():
                return self._send(401, {"error": "invalid or missing X-API-Key"})
            # web/mobile must be LOGGED IN (valid session) to submit chat/commands — no anonymous injection.
            # 3rd-party intake (no X-Odin-Client) is unaffected; only web/mobile clients are gated.
            if self._client_blocked():
                return
            project = body.get("project")
            # CHAT (sender='chat', any scope) and COMMAND (sender='command', e.g. create_project) requests
            # don't target an existing project — skip the project-existence check for them.
            is_special = body.get("sender") in ("chat", "command")
            if not is_special:
                try:
                    import projects
                    if project and not projects.get_project(project):
                        return self._send(404, {"error": f"unknown target project '{project}'"})
                except Exception:
                    pass
            payload = body.get("payload") if body.get("payload") is not None else {"prompt": body.get("prompt", "")}
            req = q.enqueue(project, payload, body.get("sender", ""), body.get("webhook_url", ""))
            return self._send(200, {"request_id": req["id"], "status": req["status"],
                                    "message": "received — queued; result will be delivered to your webhook."})

        # ---- the Mac's poller PUSHES the mirrored state here (projects + agents + pools) ----
        if rest == ["sync"]:
            if not self._auth_ok():
                return self._send(401, {"error": "invalid or missing X-API-Key"})
            import time as _t
            if isinstance(body.get("projects"), list):
                SYNC["projects"] = body["projects"]
            if isinstance(body.get("agents"), dict):
                SYNC["agents"] = body["agents"]
            if isinstance(body.get("pools"), dict):
                # merge per-project pools so a partial push doesn't wipe others
                for k, v in body["pools"].items():
                    if isinstance(v, list):
                        SYNC["pools"][k] = v
            if isinstance(body.get("mirror"), dict):
                # generic mirror (roles/company_agents/connectors/activity/…) — merge so partial pushes are ok
                SYNC.setdefault("mirror", {})
                for k, v in body["mirror"].items():
                    SYNC["mirror"][k] = v
            SYNC["updated"] = int(_t.time())
            _persist_sync()   # DURABLE: survive anchor restarts + desktop-offline (WhatsApp-style)
            return self._send(200, {"ok": True, "projects": len(SYNC["projects"]),
                                    "pools": len(SYNC["pools"]), "updated": SYNC["updated"]})

        if len(rest) == 3 and rest[0] == "requests" and rest[2] == "ack":
            return self._send(200, q.ack(rest[1]))

        if len(rest) == 3 and rest[0] == "requests" and rest[2] == "result":
            if not self._auth_ok():
                return self._send(401, {"error": "invalid or missing X-API-Key"})
            return self._send(200, q.submit_result(rest[1], body.get("result")))

        if rest == ["admin", "config"]:
            if not self._auth_ok():
                return self._send(401, {"error": "invalid or missing X-API-Key"})
            return self._send(200, q.set_cfg(**body))

        return self._send(404, {"error": "not found"})

    def _do_DELETE(self):
        u = urlparse(self.path)
        parts = [unquote(p) for p in u.path.split("/") if p]  # decode %3A→: so chat:<id>/project:<id> scopes match
        rest = parts[2:] if parts[:2] == ["anchor", "v1"] else []
        # Manage: delete a single request (protected by the manage session)
        if len(rest) == 3 and rest[0] == "manage" and rest[1] == "requests":
            if not mng.valid_session(self._mng_token()):
                return self._send(401, {"error": "manage login required"})
            return self._send(200, q.remove(rest[2]))
        return self._send(404, {"error": "not found"})


def _retry_sweep(interval: float = 30.0):
    """The deployed anchor owns webhook delivery + retries (it has the public network to
    reach third parties). Re-deliver any ack_pending requests whose retry interval elapsed."""
    import threading
    import time

    def loop():
        while True:
            try:
                q.retry_due()
            except Exception:
                pass
            time.sleep(interval)

    threading.Thread(target=loop, daemon=True).start()


def serve(host: str, port: int):
    _retry_sweep()
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"[anchor-remote] serving /anchor/v1 on http://{host}:{port}  (auth={'on' if _want_key() else 'off'})")
    httpd.serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="0.0.0.0")
    ap.add_argument("--port", type=int, default=19100)
    args = ap.parse_args()
    serve(args.host, args.port)
