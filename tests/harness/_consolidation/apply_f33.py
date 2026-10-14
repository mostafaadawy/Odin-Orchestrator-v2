#!/usr/bin/env python3
"""F-33 (owner decision 2026-10-11): keep "Approve all", but FIRST show a confirmation that lists EVERY pending
proposal (id, project, what it changes); only after the owner confirms are EXACTLY the listed ids approved.
- desktop/src/views.jsx: the "Approve all safe" button opens an in-dialog list; "Confirm" approves that snapshot.
- server/approvals.py + soc_api.py: POST /approvals/approve-all without `confirm` approves NOTHING and returns the
  list + a confirmation token; with the token it approves exactly that list, and refuses if the list changed.
Security alarms stay outside "approve all" (unchanged)."""
import pathlib, sys
R = pathlib.Path(__file__).resolve().parent.parent
def patch(path, edits, tag):
    p = R / path; s = p.read_text()
    if tag in s: sys.exit(f"{path}: already applied")
    for name, old, new in edits:
        assert s.count(old) == 1, f"{path} anchor {name}: {s.count(old)}"
        s = s.replace(old, new)
    p.write_text(s)
patch("server/approvals.py", [
 ("import", "import re\nimport uuid\n", "import re\nimport uuid\nimport hashlib\n"),
 ("approve_all", '''def approve_all_safe(pid: str | None = None) -> dict:
    """'Approve all' — approves every pending NON-security approval. Security-alarm approvals are LEFT
    pending on purpose (they require an individual, deliberate decision). Returns what was approved and
    what was deliberately skipped so the UI can say 'N approved · M security items need your attention'."""
    approved = []
    for a in list_pending(pid, bulk=True):
        decide(a["id"], True, note="approved via approve-all (non-security)")
        approved.append(a["id"])''',
 '''def approve_all_preview(pid: str | None = None) -> dict:
    """F-33: the list the owner must see before 'Approve all': every pending NON-security proposal with its id,
    project and what it changes, plus a token that binds the confirmation to exactly this list."""
    items = [{"id": a["id"], "pid": a.get("pid"), "member": a.get("member", ""), "title": a.get("title", ""),
              "files": [f.get("path") for f in (a.get("files") or [])],
              "commands": [{"where": c.get("where"), "cmd": c.get("cmd")} for c in (a.get("commands") or [])]}
             for a in list_pending(pid, bulk=True)]
    token = hashlib.sha256(",".join(sorted(x["id"] for x in items)).encode()).hexdigest()[:16]
    return {"needs_confirmation": True, "count": len(items), "items": items, "confirm": token}


def approve_all_safe(pid: str | None = None, confirm: str | None = None) -> dict:
    """'Approve all' — approves every pending NON-security approval. Security-alarm approvals are LEFT
    pending on purpose (they require an individual, deliberate decision). Returns what was approved and
    what was deliberately skipped so the UI can say 'N approved · M security items need your attention'.
    F-33 (owner, 2026-10-11): WITHOUT the confirmation token nothing is approved — the full list is returned
    for the owner to check. With the token, exactly that list is approved; if it changed, nothing is."""
    pv = approve_all_preview(pid)
    if not confirm:
        return pv
    if confirm != pv["confirm"]:
        return {**pv, "error": "The list of pending proposals changed — check the new list and confirm again."}
    approved = []
    for x in pv["items"]:
        decide(x["id"], True, note="approved via approve-all after the owner confirmed the full list")
        approved.append(x["id"])'''),
], "approve_all_preview")
patch("server/soc_api.py", [
 ("endpoint", '''    def approvals_approve_all(pid: str = ""):
        import approvals
        return approvals.approve_all_safe(pid or None)''',
 '''    def approvals_approve_all(pid: str = "", confirm: str = ""):
        # F-33: first call (no confirm) approves NOTHING and returns the full list + token; the second call
        # with that token approves exactly the listed proposals.
        import approvals
        return approvals.approve_all_safe(pid or None, confirm or None)'''),
], "F-33")
patch("desktop/src/views.jsx", [
 ("state", '''  const [tab, setTab] = useState(0);
  const seen = useRef(new Set());''', '''  const [tab, setTab] = useState(0);
  const [confirmAll, setConfirmAll] = useState(null);   // F-33: the list shown before "Approve all"
  const seen = useRef(new Set());'''),
 ("fn", '''  const approveAllSafe = async () => {
    setBusy("__all__");
    try {
      for (const a of sorted) {
        if (a.security) continue;   // SECURITY is NEVER swept in by 'approve all' — decided individually
        try { await api.approveChange(a.id); seen.current.delete(a.id); } catch {}
      }
      setItems((i) => i.filter((x) => x.security));
      setTab(0);
    } finally { setBusy(""); }
  };''', '''  // F-33 (owner, 2026-10-11): "Approve all" first lists EVERY pending proposal (id, project, what it changes);
  // only after Confirm are EXACTLY the listed ids approved. SECURITY is never swept in — decided individually.
  const askApproveAll = () => setConfirmAll(sorted.filter((a) => !a.security).map((a) => ({ ...a })));
  const approveAllSafe = async () => {
    const list = confirmAll || [];
    setBusy("__all__");
    try {
      for (const a of list) {
        try { await api.approveChange(a.id, "approved via 'Approve all' after the owner confirmed the full list"); seen.current.delete(a.id); } catch {}
      }
      const done = new Set(list.map((a) => a.id));
      setItems((i) => i.filter((x) => !done.has(x.id)));
      setTab(0); setConfirmAll(null);
    } finally { setBusy(""); }
  };'''),
 ("button", "onClick={approveAllSafe}", "onClick={askApproveAll}"),
 ("panel", '''                <button className="btn sm ghost" onClick={() => setOpen(false)} title="Close — this does NOT decide anything; requests stay pending">✕ Close</button>
              </div>
            </div>''', '''                <button className="btn sm ghost" onClick={() => setOpen(false)} title="Close — this does NOT decide anything; requests stay pending">✕ Close</button>
              </div>
            </div>
            {confirmAll && (
              <div data-testid="approve-all-confirm" style={{ padding: "12px 16px", borderBottom: "1px solid var(--stroke)", maxHeight: "50vh", overflowY: "auto", background: "rgba(255,190,70,.06)" }}>
                <b style={{ fontSize: 13 }}>Approve all {confirmAll.length} non-security proposals? Check every item first:</b>
                <div className="col" style={{ gap: 8, marginTop: 8 }}>
                  {confirmAll.map((a) => (
                    <div key={a.id} style={{ fontSize: 11, border: "1px solid var(--stroke)", borderRadius: 8, padding: 8 }}>
                      <div><b>{a.id}</b> · project <b>{a.pid || "—"}</b> · {a.member || "agent"} — {a.title}</div>
                      {(a.files || []).map((f, i) => <div key={"f" + i}>• {f.action || "edit"} {f.path}</div>)}
                      {(a.commands || []).map((c, i) => <div key={"c" + i} style={{ fontFamily: "ui-monospace, monospace" }}>• [{c.where}] {c.cmd}</div>)}
                      {!(a.files || []).length && !(a.commands || []).length && <div className="faint">(no file or command changes listed)</div>}
                    </div>
                  ))}
                </div>
                <div className="row" style={{ gap: 8, marginTop: 10 }}>
                  <button className="btn sm primary" disabled={busy === "__all__"} onClick={approveAllSafe}>✓ Confirm — approve these {confirmAll.length}</button>
                  <button className="btn sm ghost" onClick={() => setConfirmAll(null)}>Cancel</button>
                </div>
              </div>
            )}'''),
], "F-33")
print("F-33 applied")
