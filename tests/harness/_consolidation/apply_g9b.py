#!/usr/bin/env python3
"""G9b: keep the owner's per-project key feature: agents ASK (key_request), the owner enters the value in the app's
secure field, the APP stores it (server/secret_store.py), the delta records only the NAME. Agents never write .cred/.env."""
import pathlib, sys
R = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
def sub(path, old, new, count=1):
    p = R / path; s = p.read_text()
    assert s.count(old) == count, (path, old[:70], s.count(old)); p.write_text(s.replace(old, new))
AP, API, V, JS = "server/approvals.py", "server/api_v2.py", "desktop/src/views.jsx", "desktop/src/api.js"
sub(AP, '''def mark_applied(aid: str, result: str = "") -> None:''', '''def set_fields(aid: str, **kw) -> None:
    """G9b: extra non-secret fields on an approval (e.g. key_service, key_name of a key request)."""
    items = _all()
    for a in items:
        if a["id"] == aid:
            a.update({k: v for k, v in kw.items() if k not in ("id", "status", "value")})
            _save(items)
            return


def mark_applied(aid: str, result: str = "") -> None:''')
sub(AP, '''    if bulk:
        out = [a for a in out if not a.get("security")]''', '''    if bulk:   # G9b: a key request needs the owner to TYPE a value — never part of "approve all"
        out = [a for a in out if not a.get("security") and a.get("kind") != "key_request"]''')
# endpoints
sub(API, '''    @r.post("/approvals/{aid}/approve")
    def approvals_approve(aid: str, body: dict | None = None):
        import approvals, threading''', '''    @r.post("/secrets/project-key")
    def secrets_project_key(body: dict | None = None):
        """G9b: the app's secure field. The OWNER's value is stored by the app (never by an agent) and is never
        echoed back or logged; the project's delta records only the key's NAME."""
        import secret_store
        b = body or {}
        return secret_store.provide_key(str(b.get("aid", "")), str(b.get("value", "")),
                                        name=str(b.get("name", "")), service=str(b.get("service", "")))

    @r.post("/approvals/{aid}/approve")
    def approvals_approve(aid: str, body: dict | None = None):
        import approvals, threading
        _ka = approvals.get(aid)
        if _ka and _ka.get("kind") == "key_request":   # G9b: a key request is fulfilled only through the secure field
            return {**_ka, "error": "enter the key in the secure field (POST /secrets/project-key)"}''')
# agents are told how to ask
sub(API, '''    "Only include changes that are truly needed. If NO change is needed, do not emit a proposal block.")''',
         '''    "Only include changes that are truly needed. If NO change is needed, do not emit a proposal block.\\n"
    "KEYS: never write or edit .cred or .env files, and never put a key value in a file or command. If you need a "
    "new or different key, add ONE line `KEY_REQUEST: {\\"service\\": \\"<service>\\", \\"name\\": \\"<UPPER_SNAKE_NAME>\\", "
    "\\"why\\": \\"<reason>\\"}` - the owner enters it in the app's secure field and the app stores it.")''')
# member runs: a KEY_REQUEST line creates the request; a refused secret write becomes a key request too
sub(API, '''    prop = _parse_proposal(reply)
    if not prop:
        yield ("__return__", {"reply": reply, "approved": None, "applied": False}); return''', '''    try:   # G9b: the agent ASKS for a key; the owner enters it in the app
        import secret_store as _ss
        for _kr in _ss.requests_from_reply(pid, member, reply):
            yield sse("status", {"icon": "\\U0001f511", "text": f"{member} asks for a key: {_kr.get('key_name') or _kr.get('key_service')}. Enter it in the app's secure field."})
    except Exception:
        pass
    prop = _parse_proposal(reply)
    if not prop:
        yield ("__return__", {"reply": reply, "approved": None, "applied": False}); return''')
sub(API, '''        _r = _refuse_outside(pid, member, prop, _bad, folder, task_label)''', '''        _r = _refuse_outside(pid, member, prop, _bad, folder, task_label)
        if any("cred" in x or ".env" in x or "/oth" in x for x in _bad):   # G9b: turn it into a key request
            try:
                import secret_store as _ss, workspace_mw as _mwk
                _ch = _mwk.credential_choice_from_text(json.dumps(prop))
                _ss.request_key(pid, member, (_ch[0][0] if _ch else ""), (_ch[0][1] if _ch else ""),
                                "The agent tried to store a key itself (refused). Enter the key here instead.")
            except Exception:
                pass''')
# chat path too
sub(API, '''            _bad = _outside_paths(pid, prop, proj_cwd or "") if prop else []''', '''            try:   # G9b
                import secret_store as _ss
                _ss.requests_from_reply(pid, member or "Project CTO", reply or "")
            except Exception:
                pass
            _bad = _outside_paths(pid, prop, proj_cwd or "") if prop else []''')
# desktop app: the secure field
sub(JS, '''  approveChange: (aid, note = "") => jpost(`/approvals/${aid}/approve`, { note }),''', '''  approveChange: (aid, note = "") => jpost(`/approvals/${aid}/approve`, { note }),
  provideProjectKey: (aid, name, service, value) => jpost("/secrets/project-key", { aid, name, service, value }),''')
sub(V, '''                    {cur.security && <div style={{ fontSize: 11.5, color: "var(--danger)", margin: "6px 0" }}>🔴 This is a SECURITY approval — never part of “approve all”. Decide it on its own.</div>}
                    <div className="row" style={{ gap: 8, marginTop: 12 }}>''', '''                    {cur.security && <div style={{ fontSize: 11.5, color: "var(--danger)", margin: "6px 0" }}>🔴 This is a SECURITY approval — never part of “approve all”. Decide it on its own.</div>}
                    {cur.kind === "key_request" ? <KeyRequestForm req={cur} onDone={() => setItems((xs) => xs.filter((x) => x.id !== cur.id))} /> :
                    <div className="row" style={{ gap: 8, marginTop: 12 }}>''')
sub(V, '''                      <button className="btn sm danger" disabled={busy === cur.id || busy === "__all__"} onClick={() => act(cur.id, false)}>✕ Reject</button>
                    </div>''', '''                      <button className="btn sm danger" disabled={busy === cur.id || busy === "__all__"} onClick={() => act(cur.id, false)}>✕ Reject</button>
                    </div>}''')
sub(V, '''/* live Azure VM connection status (lazy — checks on mount + on click) */''', '''/* G9b — the owner's SECURE key field. The value goes straight to the app's store (never to an agent); it is
   cleared from memory after sending and never shown again. The project's delta records only the key NAME. */
function KeyRequestForm({ req, onDone }) {
  const [name, setName] = useState(req.key_name || "");
  const [value, setValue] = useState("");
  const [msg, setMsg] = useState("");
  async function save() {
    setMsg("");
    try {
      const r = await api.provideProjectKey(req.id, name.trim().toUpperCase(), req.key_service || "", value);
      setValue("");
      if (r && r.ok) { setMsg(`Stored ${r.name}. The project now records only the name.`); onDone && onDone(); }
      else setMsg((r && r.error) || "Could not store the key.");
    } catch (e) { setValue(""); setMsg("Could not store the key."); }
  }
  return (
    <div data-testid="key-request-form" className="col" style={{ gap: 8, marginTop: 12 }}>
      <div className="faint" style={{ fontSize: 12 }}>🔑 {req.member} needs a key{req.key_service ? ` for ${req.key_service}` : ""}. The app stores it; the agent never sees it.</div>
      <input data-testid="key-name" value={name} placeholder="KEY_NAME (e.g. KLAVIYO_KEY_BRAND2)" onChange={(e) => setName(e.target.value)} />
      <input data-testid="key-value" type="password" autoComplete="off" value={value} placeholder="paste the key (hidden)" onChange={(e) => setValue(e.target.value)} />
      <div className="row" style={{ gap: 8 }}>
        <button data-testid="key-save" className="btn sm primary" disabled={!value || !name} onClick={save}>Save key securely</button>
      </div>
      {msg && <div data-testid="key-msg" className="faint" style={{ fontSize: 12 }}>{msg}</div>}
    </div>
  );
}

/* live Azure VM connection status (lazy — checks on mount + on click) */''')
print("G9b applied")
