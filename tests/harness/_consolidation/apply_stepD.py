"""Step D (F-22 / CAT_COMMS N5, N6, N7)."""
import pathlib
def patch(path, a, b, n=1):
    p = pathlib.Path(path); s = p.read_text(); assert s.count(a) == n, (path, s.count(a), a[:80]); p.write_text(s.replace(a, b))
patch("server/anchor_queue.py", "_LOCK = threading.RLock()\n", '''class _QueueLock:
    """F-22 / N5: the in-process RLock PLUS — when the queue is the JSON file (no Postgres) — an exclusive
    cross-process file lock, so two processes (the brain's thread and the HTTP poller) can never interleave a
    read-modify-write or hand out the same row twice. Re-entrant; the file lock is taken on the outermost entry."""
    def __init__(self):
        self._r = threading.RLock(); self._depth = 0; self._fh = None
    def __enter__(self):
        self._r.acquire(); self._depth += 1
        if self._depth == 1 and not globals().get("_PG_DSN"):
            try:
                import fcntl
                os.makedirs(str(store.DATA), exist_ok=True)
                self._fh = open(os.path.join(str(store.DATA), "anchor_queue.lock"), "a+")
                fcntl.flock(self._fh, fcntl.LOCK_EX)
            except Exception:
                self._fh = None
        return self
    def __exit__(self, *exc):
        if self._depth == 1 and self._fh is not None:
            try:
                import fcntl
                fcntl.flock(self._fh, fcntl.LOCK_UN); self._fh.close()
            except Exception:
                pass
            self._fh = None
        self._depth -= 1; self._r.release()
        return False
    def acquire(self, *a, **k):
        self.__enter__(); return True
    def release(self):
        self.__exit__(None, None, None)


_LOCK = _QueueLock()
''')
patch("desktop/src/App.jsx", '''        const base = (env === "production"
          ? "https://anchor.odinmarkets.com/odin-anchor"
          : (localStorage.getItem("odin.anchor") || "http://localhost:29100")).replace(/\\/+$/, "");''',
'''        // F-22 / N7: honour the editable production anchor (Settings), like the rest of the desktop does
        const base = (env === "production"
          ? (localStorage.getItem("odin.prod.anchor") || "https://anchor.odinmarkets.com/odin-anchor")
          : (localStorage.getItem("odin.anchor") || "http://localhost:29100")).replace(/\\/+$/, "");''')
patch("shells/phase_ctl.sh", '''  local body; body=$(printf '{"project":"%s","prompt":"%s","webhook_url":"http://localhost:%s/cb"}' "$proj" "$prompt" "$WH_PORT")''',
'''  # F-22 / N6: a localhost webhook only works with the LOCAL anchor; the online anchor (VM) cannot reach this Mac,
  # so against it we register NO webhook and simply poll for the result below (no ack_pending retry noise).
  local body
  if [ -n "$VM_IP" ]; then
    body=$(printf '{"project":"%s","prompt":"%s"}' "$proj" "$prompt")
  else
    body=$(printf '{"project":"%s","prompt":"%s","webhook_url":"http://localhost:%s/cb"}' "$proj" "$prompt" "$WH_PORT")
  fi''')
print("ok")
