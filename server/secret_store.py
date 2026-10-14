"""G9b — the OWNER's key path. An agent may only ASK for a key (a key request); the owner types the value in the
app's secure field (desktop now; phone via the encrypted relay, F-41); THIS module (the app/brain process, never an
agent) stores it, and the project's delta records only the key's NAME. The value is never returned or logged."""
from __future__ import annotations
import os, re, pathlib, tempfile, json

ROOT = pathlib.Path(__file__).resolve().parent.parent
CRED = ROOT / "workspace" / "shared" / "oth" / ".cred"
NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")


def _write_cred(name: str, value: str) -> None:
    """Replace or append NAME=value atomically; file mode 600. Other lines are kept byte-for-byte."""
    CRED.parent.mkdir(parents=True, exist_ok=True)
    lines = CRED.read_text(encoding="utf-8").splitlines() if CRED.exists() else []
    out, done = [], False
    for ln in lines:
        k = re.split(r"[=:]", ln.strip(), 1)[0].strip() if ln.strip() and not ln.strip().startswith("#") else None
        if k == name:
            out.append(f"{name}={value}"); done = True
        else:
            out.append(ln)
    if not done:
        out.append(f"{name}={value}")
    fd, tmp = tempfile.mkstemp(dir=str(CRED.parent), prefix=".cred.")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    os.chmod(tmp, 0o600)
    os.replace(tmp, CRED)


def request_key(pid: str, member: str, service: str = "", name: str = "", why: str = "") -> dict:
    """An agent ASKS for a key. Creates a 'key_request' approval (no value, ever) and notifies the owner."""
    import approvals
    name = (name or "").strip().upper()
    if name and not NAME_RE.match(name):
        name = ""
    for a in approvals.list_pending(pid):   # one open request per key name
        if a.get("kind") == "key_request" and a.get("key_name") == name and name:
            return a
    a = approvals.create(pid, member, title=f"Key needed: {name or service or 'a credential'}",
                         summary=(why or f"{member} needs a key for {service or 'this project'}. Enter it in the "
                                  "secure field; the app stores it - the agent never sees or writes it."),
                         kind="key_request")
    approvals.set_fields(a["id"], key_service=(service or "").lower(), key_name=name)
    try:
        import notifications_store as _ns
        _ns.add(kind="finding", title=f"{member} asks for a key", body=f"{name or service} for project {pid}",
                pid=pid, severity="attention", icon="\U0001f511")
    except Exception:
        pass
    return approvals.get(a["id"])


def provide_key(aid: str, value: str, name: str = "", service: str = "", channel: str = "secure-field") -> dict:
    """The OWNER fulfils a key request from the app's secure field. Stores the value (app process, not an agent),
    records only the NAME in the project's delta, and closes the request. Returns no value."""
    import approvals, workspace_mw as mw
    a = approvals.get(aid)
    if not a or a.get("kind") != "key_request" or a.get("status") != "pending":
        return {"ok": False, "error": "no open key request with this id"}
    name = (name or a.get("key_name") or "").strip().upper()
    service = (service or a.get("key_service") or "").strip().lower()
    if not NAME_RE.match(name):
        return {"ok": False, "error": "the key name must be UPPER_SNAKE_CASE, e.g. KLAVIYO_KEY_BRAND2"}
    if not value or not value.strip():
        return {"ok": False, "error": "empty value"}
    _write_cred(name, value.strip())
    if not service:   # derive it from the name (KLAVIYO_KEY_BRAND2 -> klaviyo) when the request did not say
        _ch = mw.credential_choice_from_text(name)
        service = _ch[0][0] if _ch else ""
    rec = mw.record_credential_choice(a["pid"], service, name, source="owner") if service else {}
    _how = "on the phone through the encrypted relay" if channel == "phone" else "in the app"
    approvals.decide(aid, True, f"key {name} provided by the owner {_how} (value stored by the app, not shown)",
                     by="owner", channel=channel)
    approvals.mark_applied(aid, f"stored {name}; delta records the name only")
    return {"ok": True, "id": aid, "name": name, "service": service, "stored_in": "workspace/shared/oth/.cred",
            "recorded_for": rec.get("agents", [])}


def provide_key_e2e(aid: str, envelope: dict, name: str = "") -> dict:
    """F-41: the phone's sealed envelope (relayed by the Anchor as ciphertext) is opened HERE, on the Mac, and
    the value goes down the same path as the desktop field. Errors never contain the value."""
    import approvals, key_relay
    a = approvals.get(aid)
    if not a or a.get("kind") != "key_request" or a.get("status") != "pending":
        return {"ok": False, "error": "no open key request with this id"}
    name = (name or a.get("key_name") or "").strip().upper()
    if not NAME_RE.match(name):
        return {"ok": False, "error": "the key name must be UPPER_SNAKE_CASE, e.g. KLAVIYO_KEY_BRAND2"}
    try:
        value = key_relay.open_envelope(envelope, aid, name)
    except key_relay.RelayError as e:
        return {"ok": False, "error": f"encrypted key refused: {e}"}
    return provide_key(aid, value, name=name, channel="phone")


KEY_REQ_RE = re.compile(r"KEY_REQUEST:\s*(\{[^{}]*\})")


def requests_from_reply(pid: str, member: str, reply: str) -> list:
    """Agents ask with a line `KEY_REQUEST: {"service": "...", "name": "...", "why": "..."}`."""
    out = []
    for m in KEY_REQ_RE.finditer(reply or ""):
        try:
            d = json.loads(m.group(1))
        except Exception:
            continue
        out.append(request_key(pid, member, d.get("service", ""), d.get("name", ""), d.get("why", "")))
    return out
