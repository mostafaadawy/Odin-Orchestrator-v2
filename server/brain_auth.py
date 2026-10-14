"""F-20 (owner 2026-10-12): the brain is LOCAL ONLY and every route that CHANGES something needs the brain token.

  * local only   — the client must be this machine (127.0.0.1 / ::1) and the Host header must name localhost
                   (blocks other machines and DNS-rebinding pages);
  * brain token  — POST / PUT / PATCH / DELETE, and the GET routes that run work (/scope/stream, /chat/stream,
                   /chats/{id}/stream, /dispatch, /voice), need X-Odin-Token (or ?token= for EventSource).
The token is ODIN_ACCESS_TOKEN when set, otherwise a random token created once in data/brain_token (mode 600,
gitignored). Local clients read it: the poller and test tools from the file, the desktop through the Electron
main process. Never logged."""
from __future__ import annotations
import os, re, secrets, pathlib, hmac

ROOT = pathlib.Path(__file__).resolve().parent.parent
TOKEN_FILE = ROOT / "data" / "brain_token"
LOCAL_IPS = {"127.0.0.1", "::1", "localhost"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "[::1]"}
CHANGING = {"POST", "PUT", "PATCH", "DELETE"}
# PC-5 (owner 2026-10-12): only the desktop app's own origin and localhost pages may call the brain from a
# browser engine; every other web origin (incl. "null" from sandboxed frames / file pages) is refused for READS
# and WRITES. Requests without an Origin header are local programs (poller, CLI) — covered by local-only + token.
DESKTOP_ORIGIN = "app://odin-desktop"
ORIGIN_RE = re.compile(r"^(https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?|app://odin-desktop)$")
_RUNS_WORK = re.compile(r"^/(scope/stream|chat(/|$)|chats/[^/]+/stream|dispatch|voice)")


def token() -> str:
    t = os.environ.get("ODIN_ACCESS_TOKEN", "").strip()
    if t:
        return t
    try:
        if TOKEN_FILE.is_file():
            t = TOKEN_FILE.read_text().strip()
            if t:
                return t
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        t = secrets.token_urlsafe(32)
        fd = os.open(str(TOKEN_FILE), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as fh:
            fh.write(t + "\n")
        return t
    except FileExistsError:
        return TOKEN_FILE.read_text().strip()


def headers() -> dict:
    return {"X-Odin-Token": token()}


def _host_name(host_header: str) -> str:
    h = (host_header or "").strip().lower()
    if h.startswith("["):
        return h[: h.find("]") + 1] if "]" in h else h
    return h.rsplit(":", 1)[0] if h.count(":") == 1 else h


def origin_allowed(origin) -> bool:
    return origin is None or bool(ORIGIN_RE.match(origin))


def decide(method: str, path: str, client_ip: str, host_header: str, sent_token: str, origin=None) -> tuple[int, str]:
    """(0, '') = allow; otherwise (status, reason). origin=None means the request carried no Origin header."""
    if (client_ip or "") not in LOCAL_IPS or _host_name(host_header) not in LOCAL_HOSTS:
        return 403, "the brain accepts local requests only"
    if not origin_allowed(origin):
        return 403, "this web origin may not use the brain (PC-5)"
    needs = method.upper() in CHANGING or bool(_RUNS_WORK.match(path or ""))
    if needs and not (sent_token and hmac.compare_digest(sent_token, token())):
        return 401, "missing or invalid X-Odin-Token"
    return 0, ""
