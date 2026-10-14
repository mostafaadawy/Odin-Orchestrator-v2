import http.server, json, sys
LOG = []
class H(http.server.BaseHTTPRequestHandler):
    def _h(self, allow):
        LOG.append({"path": self.path, "method": self.command, "origin": self.headers.get("Origin")})
        open("origins.json", "w").write(json.dumps(LOG))
        self.send_response(200)
        if allow: self.send_header("Access-Control-Allow-Origin", "app://odin-desktop"); self.send_header("Access-Control-Allow-Headers", "*"); self.send_header("Access-Control-Allow-Methods", "*")
        self.end_headers()
    def do_OPTIONS(self): self._h(self.path.startswith("/allow"))
    def do_GET(self): self._h(self.path.startswith("/allow")); self.wfile.write(b"ok")
    def do_POST(self): self._h(self.path.startswith("/allow")); self.wfile.write(b"posted")
    def log_message(self, *a): pass
http.server.HTTPServer(("127.0.0.1", 28999), H).serve_forever()
