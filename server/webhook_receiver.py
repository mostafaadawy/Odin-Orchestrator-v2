#!/usr/bin/env python3
"""
webhook_receiver.py — a temporary place to SEE the anchor's webhook reply and acknowledge it.

This stands in for the third party's own endpoint. The anchor POSTs the result here; this server
records it and (by default) replies 2xx = acknowledged. A small viewer at `/` lists every webhook
received and lets you re-acknowledge explicitly via the anchor's ack endpoint.

Run:
    python3 server/webhook_receiver.py --port 9300
Use  http://localhost:9300/cb  as the webhook_url in the simulator / third party.
Open http://localhost:9300/    to watch replies + acknowledge.
"""
from __future__ import annotations

import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RECEIVED: list = []


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj, ctype="application/json"):
        body = obj.encode() if isinstance(obj, str) else json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass

    def do_GET(self):
        # /list                -> everything (newest first)
        # /list/<project_id>   -> only that project's callbacks
        # /list?project=<id>   -> same, via query
        if self.path.startswith("/list"):
            from urllib.parse import urlparse, parse_qs, unquote
            u = urlparse(self.path)
            pid = ""
            parts = [p for p in u.path.split("/") if p]     # ['list', '<pid>']
            if len(parts) >= 2:
                pid = unquote(parts[1])
            if not pid:
                pid = (parse_qs(u.query).get("project") or [""])[0]
            if pid:
                out = [r for r in RECEIVED
                       if (r.get("project") == pid) or ((r.get("payload") or {}).get("project") == pid)]
                return self._send(200, {"received": out, "project": pid})
            return self._send(200, {"received": RECEIVED})
        return self._send(200, _VIEWER, ctype="text/html")

    def do_POST(self):
        from urllib.parse import unquote
        n = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(n).decode() or "{}") if n else {}
        except Exception:
            body = {}
        # PER-PROJECT webhook: /cb/<project_id>. The project id in the path wins; else fall back
        # to the id inside the payload. This lets every seeded project have its OWN return url so
        # you can fire many requests at once and keep each one's response separate.
        parts = [p for p in self.path.split("/") if p]       # ['cb', '<pid>']
        path_pid = unquote(parts[1]) if len(parts) >= 2 else ""
        project = path_pid or body.get("project") or ""
        rec = {"at": time.strftime("%H:%M:%S"), "project": project, "payload": body}
        RECEIVED.insert(0, rec)
        print(f"[webhook] received for {body.get('request_id')} (project {project}, "
              f"status {body.get('status')}) — replying 200 (ack)")
        # 2xx == acknowledgement per the contract
        self._send(200, {"ok": True, "acknowledged": True})


_VIEWER = """<!doctype html><html><head><meta charset="utf-8"><title>Webhook receiver</title>
<style>
body{margin:0;background:#0a0c12;color:#e8ecf6;font-family:-apple-system,Segoe UI,sans-serif;padding:20px}
h1{font-size:18px}.sub{color:#9aa4bf;font-size:13px;margin-bottom:14px}
.card{background:#161b2a;border:1px solid rgba(255,255,255,.12);border-radius:12px;padding:12px;margin-bottom:10px}
.row{display:flex;gap:10px;align-items:center;font-size:12px;color:#9aa4bf}
.pill{font-size:11px;padding:2px 9px;border-radius:999px;border:1px solid rgba(255,255,255,.18);color:#4be3a0}
pre{background:#0a0c14;border:1px solid rgba(255,255,255,.1);border-radius:8px;padding:10px;font-size:11px;overflow:auto;white-space:pre-wrap}
button{margin-top:8px;background:#6c8cff;color:#fff;border:0;border-radius:8px;padding:8px 12px;font-size:12px;cursor:pointer}
input{background:#0a0c14;border:1px solid rgba(255,255,255,.18);color:#e8ecf6;border-radius:8px;padding:7px 10px;font-size:12px}
.empty{color:#5f6885;padding:30px;text-align:center}
</style></head><body>
<h1>🛰️ Webhook receiver</h1>
<div class="sub">The anchor POSTs results to <code>/cb</code> (or <code>/cb/&lt;project&gt;</code> — a separate return url per project); this page shows them all and replies 2xx (ack). Auto-refreshes every 3s.</div>
<div class="row" style="margin-bottom:12px">Anchor URL <input id="anchor" value="http://localhost:9100" style="width:220px"> · X-API-Key <input id="key" placeholder="ANCHOR_API_KEY" style="width:280px"></div>
<div id="list" class="empty">No webhooks yet…</div>
<script>
async function ack(id){const a=document.getElementById('anchor').value.replace(/\\/+$/,'');const k=document.getElementById('key').value.trim();
  const h={'Content-Type':'application/json'};if(k)h['X-API-Key']=k;
  try{const r=await fetch(a+'/anchor/v1/requests/'+id+'/ack',{method:'POST',headers:h});alert('ack '+id+': '+r.status);}catch(e){alert('ack error: '+e);}}
async function tick(){try{const d=await (await fetch('/list')).json();const el=document.getElementById('list');
  if(!d.received.length){el.className='empty';el.textContent='No webhooks yet…';return;}el.className='';
  el.innerHTML=d.received.map(function(r){var p=r.payload||{};return '<div class="card"><div class="row"><span class="pill">'+(p.status||'completed')+'</span><b style="color:#e8ecf6">'+(p.request_id||'')+'</b> → '+(p.project||'')+' <span style="margin-left:auto">'+r.at+'</span></div><pre>'+JSON.stringify(p.result!==undefined?p.result:p,null,2)+'</pre><button onclick="ack(\\''+(p.request_id||'')+'\\')">Acknowledge again</button></div>';}).join('');
}catch(e){}}
setInterval(tick,3000);tick();
</script></body></html>"""


def serve(port: int):
    httpd = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"[webhook] receiver on http://localhost:{port}  (callback: /cb, viewer: /)")
    httpd.serve_forever()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9300)
    serve(ap.parse_args().port)
