// v2 identity + Paper tab (frontend only — no backend calls; Paper files come from the Electron main process,
// catalog ids only).
import React, { useEffect, useMemo, useState } from "react";
import { Modal } from "./ui.jsx";
import { RenderedFile } from "./renderers.jsx";
import { api } from "./api.js";

export function V2Badge({ onClick }) {
  return (
    <button className="v2-badge" onClick={onClick} title="What's new in Odin v2">v2</button>
  );
}

const NEWS = [
  { icon: "🧠", title: "Jev mode — a local decider on this Mac",
    body: "Settings ▸ Decider. Normal = the LLM decides, exactly as v1. Jev = a small local model decides the closed choices in about 45 ms; low confidence falls back to the LLM. Until your labels are applied Jev runs in shadow (logged only, the LLM still decides)." },
  { icon: "📱", title: "Secure phone approvals",
    body: "Pair your phone once (Settings ▸ Paired phones, compare the fingerprint, Trust). Approve/Reject on the phone is signed on the phone, encrypted for this Mac and usable once — the Anchor only relays ciphertext." },
  { icon: "🔐", title: "Security fixes",
    body: "The online Anchor now really enforces its key (it did not read its credentials before). Web and phone sign in with your Manage login + the one-time code from this Mac, exactly as in v1; the key is never inside the web app. Secrets live in the Keychain, not in the app. Keys and passwords were rotated at cutover." },
  { icon: "📄", title: "Paper tab",
    body: "Every paper file — paper v2 (provisional numbers, pending your labels), the paper v1 submission, figures, results tables and the v2 change record — viewable here and downloadable." },
  { icon: "🧰", title: "One folder, two commands",
    body: "Everything lives in Odin-Orchestrator-v2. Environment: shells/development_full_checker.sh · Production: shells/production_full_checker.sh. Any failed check stops a deploy." },
];

export function WhatsNewModal({ open, onClose, onOpenPaper }) {
  return (
    <Modal open={open} onClose={onClose} title="What's new in Odin v2">
      <div className="col" style={{ gap: 12 }}>
        {NEWS.map((n) => (
          <div key={n.title} className="v2-news">
            <div className="v2-news-icon">{n.icon}</div>
            <div><b>{n.title}</b><div className="dim" style={{ fontSize: 12.5, marginTop: 3, lineHeight: 1.5 }}>{n.body}</div></div>
          </div>
        ))}
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button className="btn sm" onClick={() => { onClose(); onOpenPaper && onOpenPaper(); }}>📄 Open the Paper tab</button>
        </div>
      </div>
    </Modal>
  );
}

function fmtSize(n) { return n > 1e6 ? (n / 1e6).toFixed(1) + " MB" : n > 1e3 ? Math.round(n / 1e3) + " KB" : n + " B"; }
function statusClass(s) { return /provisional/i.test(s) ? "warn" : /frozen|submitted/i.test(s) ? "ok" : "info"; }

export function PaperView() {
  const bridge = typeof window !== "undefined" ? window.odin : null;
  const [files, setFiles] = useState(null);
  const [sel, setSel] = useState(null);
  const [doc, setDoc] = useState(null);
  const [msg, setMsg] = useState("");
  useEffect(() => {
    if (!bridge || !bridge.paperList) { setFiles([]); return; }
    bridge.paperList().then((l) => { setFiles(l || []); const first = (l || []).find((f) => f.exists); if (first) setSel(first.id); });
  }, []);
  useEffect(() => {
    if (!sel || !bridge) return;
    setDoc(null);
    bridge.paperRead(sel).then((r) => {
      if (!r || !r.ok) { setDoc({ error: (r && r.error) || "could not read" }); return; }
      if (!r.text && r.mime === "application/octet-stream") { setDoc({ error: "No preview for this file type — use Download.", name: r.name }); return; }
      if (r.mime.startsWith("image/")) { setDoc({ img: "data:" + r.mime + ";base64," + r.base64, name: r.name }); return; }
      if (r.mime === "application/pdf") {
        const bin = atob(r.base64); const u8 = new Uint8Array(bin.length);
        for (let i = 0; i < bin.length; i++) u8[i] = bin.charCodeAt(i);
        setDoc({ pdf: URL.createObjectURL(new Blob([u8], { type: "application/pdf" })), name: r.name });
      } else {
        let text = decodeURIComponent(escape(atob(r.base64)));
        if (r.ext === ".json") { try { text = JSON.stringify(JSON.parse(text), null, 2); } catch {} }
        setDoc({ text, name: r.name, ext: r.ext });
      }
    });
  }, [sel]);
  const groups = useMemo(() => {
    const g = {}; (files || []).forEach((f) => { (g[f.group] = g[f.group] || []).push(f); }); return g;
  }, [files]);
  const cur = (files || []).find((f) => f.id === sel);
  if (!bridge || !bridge.paperList) return <div className="card pad">The Paper tab is available in the desktop app.</div>;
  return (
    <div className="paper-wrap">
      <div className="paper-list card">
        <div className="row" style={{ justifyContent: "space-between", padding: "12px 14px 6px" }}>
          <b>📄 Papers & research files</b><span className="faint" style={{ fontSize: 11 }}>{(files || []).length} files</span>
        </div>
        <div className="paper-scroll">
          {files === null && <div className="faint" style={{ padding: 14 }}>loading…</div>}
          {Object.entries(groups).map(([g, fs]) => (
            <div key={g}>
              <div className="paper-group row" style={{ justifyContent: "space-between" }}>
                <span>{g} · {fs.length}</span>
                {g !== "Records" && bridge.paperSaveGroup && (
                  <span className="paper-saveall" title="Save every file of this group (keeps the folders)"
                    onClick={async () => { const r = await bridge.paperSaveGroup(g); setMsg(r && r.ok ? "All files saved to " + r.path : r && r.canceled ? "" : "Could not save"); }}>⬇ all</span>
                )}
              </div>
              {fs.map((f, i) => (<React.Fragment key={f.id}>
                {f.sub && (i === 0 || fs[i - 1].sub !== f.sub) && <div className="paper-sub">{f.sub}/</div>}
                <button className={"paper-item" + (f.id === sel ? " active" : "")} disabled={!f.exists} onClick={() => setSel(f.id)}>
                  <div className="row" style={{ gap: 8 }}>
                    <span className="paper-kind">{f.kind.toUpperCase()}</span>
                    <span style={{ flex: 1, textAlign: "left" }}>{f.title}</span>
                  </div>
                  <div className={"paper-status " + statusClass(f.status)}>{f.exists ? f.status : "missing on disk"}{f.exists && " · " + fmtSize(f.size)}</div>
                </button></React.Fragment>
              ))}
            </div>
          ))}
        </div>
      </div>
      <div className="paper-view card">
        {cur && (
          <div className="row paper-head">
            <div style={{ flex: 1, minWidth: 0 }}>
              <b>{cur.title}</b>
              <div className="faint" style={{ fontSize: 11.5 }}>{cur.file} · updated {new Date(cur.mtime).toLocaleString()}</div>
            </div>
            <span className={"paper-status " + statusClass(cur.status)} style={{ marginRight: 8 }}>{cur.status}</span>
            <button className="btn sm" onClick={async () => { const r = await bridge.paperSave(cur.id); setMsg(r && r.ok ? "Saved to " + r.path : r && r.canceled ? "" : "Could not save"); }}>⬇ Download</button>
          </div>
        )}
        {msg && <div className="faint" style={{ fontSize: 12, padding: "0 16px 8px" }}>{msg}</div>}
        <div className="paper-body">
          {!doc && <div className="faint" style={{ padding: 20 }}>{sel ? "opening…" : "pick a file"}</div>}
          {doc && doc.error && <div style={{ padding: 20, color: "var(--danger)" }}>{doc.error}</div>}
          {doc && doc.pdf && <iframe title={doc.name} src={doc.pdf} className="paper-pdf" />}
          {doc && doc.text !== undefined && <RenderedFile ext={doc.ext} text={doc.text} />}
          {doc && doc.img && <div style={{ padding: 16 }}><img src={doc.img} alt={doc.name} style={{ maxWidth: "100%" }} /></div>}
        </div>
      </div>
    </div>
  );
}


// v2: the DECIDER choice, front and centre in the sidebar — a two-way switch plus a clear explanation dialog.
// Same backend setting as the top-bar pill (/settings/decider-mode); nothing else changes.
export function DeciderSwitch() {
  const [mode, setMode] = useState("normal");
  const [authority, setAuthority] = useState("shadow");
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);
  const load = () => api.deciderMode().then((d) => { setMode((d && d.mode) || "normal"); setAuthority((d && d.authority) || "shadow"); }).catch(() => {});
  useEffect(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t); }, []);
  async function pick(m) {
    if (m === mode || busy) return;
    setBusy(true);
    try { const d = await api.setDeciderMode(m); setMode((d && d.mode) || m); if (d && d.authority) setAuthority(d.authority); } catch (e) {}
    setBusy(false);
  }
  const jev = mode === "jev";
  return (
    <>
      <div className="decider-card">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <span className="decider-title">Who decides?</span>
          <span className="decider-info" onClick={() => setOpen(true)} title="What is this?">ⓘ</span>
        </div>
        <div className="decider-seg">
          <button className={!jev ? "on llm" : ""} disabled={busy} onClick={() => pick("normal")} title="The LLM decides (v1 behaviour)">🧠 LLM</button>
          <button className={jev ? "on jev" : ""} disabled={busy} onClick={() => pick("jev")} title="Jev — the local decider on this Mac">⚡ Jev</button>
        </div>
        <div className="decider-note">
          {!jev ? "Normal — the LLM decides, exactly as v1."
            : authority === "shadow" ? "Jev in shadow — it decides in the background and is logged; the LLM still decides until your labels arrive."
            : "Jev decides closed choices locally (~45 ms); low confidence falls back to the LLM."}
        </div>
      </div>
      <Modal open={open} onClose={() => setOpen(false)} title="Who decides — LLM or Jev?">
        <div className="decider-pick">
          <div className={"decider-opt" + (!jev ? " on" : "")} onClick={() => { pick("normal"); }}>
            <div className="decider-opt-h">🧠 LLM <span className="faint">(Normal)</span></div>
            <ul><li>Every decision goes to the LLM, exactly as in v1.</li><li>Slower (seconds per decision), uses the plan.</li><li>The default and the reference for the paper.</li></ul>
          </div>
          <div className={"decider-opt jev" + (jev ? " on" : "")} onClick={() => { pick("jev"); }}>
            <div className="decider-opt-h">⚡ Jev <span className="faint">(local decider)</span></div>
            <ul><li>A small model on this Mac decides closed choices (mode, specialist, read/change, QA gate) in ~45 ms.</li>
              <li>Low confidence, disabled classes and your exclusions go to the LLM.</li>
              <li><b>Shadow until your labels arrive:</b> Jev's choice is logged; the LLM still decides.</li></ul>
          </div>
        </div>
        <div className="faint" style={{ fontSize: 12, marginTop: 10 }}>Current: <b>{jev ? (authority === "shadow" ? "Jev (shadow)" : "Jev") : "LLM"}</b>. Changing it takes effect on the next decision; nothing else changes.</div>
      </Modal>
    </>
  );
}
