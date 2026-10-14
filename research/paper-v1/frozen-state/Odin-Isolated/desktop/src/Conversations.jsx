import React, { useEffect, useRef, useState } from "react";
import { api, streamScope } from "./api.js";

// Conversations MODE (additive): the dashboard re-represented as a chat app. Left = Company +
// every project as a conversation; open one → its SAME scope pool, chat-style with image/file/
// voice + reply. Messages sent here are tagged "via Conversations". Nothing else is changed.
export function ConversationsView({ projects }) {
  const [scope, setScope] = useState("company");
  // SAME scope keys the dashboard + orchestration use: company / project:<pid>
  const convs = [{ scope: "company", title: "Company — Chief Engineer", icon: "🏛️" },
    ...(projects || []).map((p) => ({ scope: `project:${p.id}`, title: p.name, icon: "📁" }))];
  const cur = convs.find((c) => c.scope === scope) || convs[0];
  return (
    <div className="chat" style={{ flexDirection: "row", height: "100%" }}>
      <div className="chat-side">
        <div className="faint" style={{ padding: "6px 4px", letterSpacing: 1, fontSize: 10 }}>CONVERSATIONS</div>
        {convs.map((c) => (
          <button key={c.scope} className={"chat-item" + (c.scope === scope ? " active" : "")} onClick={() => setScope(c.scope)} title={c.title}>
            <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.icon} {c.title}</span>
          </button>
        ))}
      </div>
      <ConversationPanel key={scope} scope={scope} title={cur.title} />
    </div>
  );
}

function ConversationPanel({ scope, title }) {
  const [cid, setCid] = useState(null);
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState("");
  const [replyTo, setReplyTo] = useState(null);
  const [recording, setRecording] = useState(false);
  const [busy, setBusy] = useState(false);
  const [sel, setSel] = useState(() => new Set()); // selected message ids
  const [selMode, setSelMode] = useState(false);
  const fileRef = useRef(null);
  const recRef = useRef(null);
  const scrollRef = useRef(null);
  const sender = "Owner · via Conversations";

  const lineOf = (m) => `${m.sender || m.role || ""}: ${m.content || (m.attachment ? "[" + (m.attachment.name || m.kind) + "]" : "")}`;
  async function copyTexts(msgs) {
    try { await navigator.clipboard.writeText(msgs.map(lineOf).join("\n")); } catch {}
    setSel(new Set()); setSelMode(false);
  }
  function toggleSel(id) {
    setSel((s) => { const n = new Set(s); n.has(id) ? n.delete(id) : n.add(id); setSelMode(n.size > 0); return n; });
  }
  const selMsgs = () => messages.filter((m) => sel.has(m.id));
  async function delSelected() {
    for (const m of selMsgs()) { try { await api.deleteScopeMessage(scope, m.cid, m.id); } catch {} }
    setSel(new Set()); setSelMode(false); reload();
  }
  async function fwdSelected() {
    const projects = await api.projects().catch(() => []);
    const opts = ["company", ...(projects || []).map((p) => "project:" + p.id)];
    const pick = window.prompt("Forward to which scope?\n" + opts.map((o, i) => `${i}: ${o}`).join("\n"), "0");
    const t = opts[parseInt(pick, 10)]; if (!t) return;
    const cs = await api.scopeChats(t).catch(() => []); let id = cs[0]?.id; if (!id) { const c = await api.createScopeChat(t); id = c.id; }
    for (const m of selMsgs()) {
      await api.postScopeMessage(t, id, { role: "user", content: m.content || "", sender: sender + " (forwarded)", kind: m.kind || "text", ...(m.attachment ? { attachment: m.attachment } : {}) });
    }
    setSel(new Set()); setSelMode(false);
  }

  useEffect(() => { (async () => {
    const cs = await api.scopeChats(scope).catch(() => []);
    let id = cs[0]?.id; if (!id) { const c = await api.createScopeChat(scope); id = c.id; }
    setCid(id);
  })(); }, [scope]);
  useEffect(() => {
    if (!cid) return; reload();
    const t = setInterval(() => { if (!recording && !busy) reload(); }, 3000);
    return () => clearInterval(t);
  }, [cid]);
  useEffect(() => { scrollRef.current && (scrollRef.current.scrollTop = scrollRef.current.scrollHeight); }, [messages]);

  async function reload() {
    const all = await api.scopeAllMessages(scope).catch(() => null); // WHOLE pool, all chats merged
    if (all) setMessages(all);
  }
  async function sendText() {
    const t = draft.trim(); if (!t || !cid) return; setDraft("");
    const reply = replyTo?.id; setReplyTo(null);
    if (reply) {
      // a reply = group post (tagged, no AI)
      await api.postScopeMessage(scope, cid, { role: "user", content: t, sender, kind: "text", reply_to: reply });
      reload();
      return;
    }
    // a plain message talks to the CTO/team (streamed) — same as the normal chat, shown here
    setMessages((m) => [...m, { role: "user", content: t, sender }, { role: "assistant", content: "", sender: "CTO" }]);
    let acc = "";
    streamScope(scope, t, "en", cid, {
      token: (d) => { acc += d.t; setMessages((m) => { const c = [...m]; c[c.length - 1] = { role: "assistant", content: acc, sender: "CTO" }; return c; }); },
      done: () => reload(),
      error: (d) => { setMessages((m) => { const c = [...m]; c[c.length - 1] = { role: "assistant", content: "⚠️ " + (d.text || "error") }; return c; }); },
    });
  }
  async function sendFile(file) {
    if (!cid) return; setBusy(true);
    try {
      const desc = await api.uploadScopeFile(scope, file, file.name || "file");
      const reply = replyTo?.id; setReplyTo(null);
      await api.postScopeMessage(scope, cid, { role: "user", content: desc.transcript || "", sender, kind: desc.kind || "file", attachment: desc, ...(reply ? { reply_to: reply } : {}) });
      reload();
    } catch (e) { alert("Attach failed: " + (e.message || e)); } finally { setBusy(false); }
  }
  async function toggleMic() {
    if (recording) { try { recRef.current && recRef.current.stop(); } catch {} setRecording(false); return; }
    let stream; try { stream = await navigator.mediaDevices.getUserMedia({ audio: true }); } catch { alert("Microphone blocked"); return; }
    const mr = new MediaRecorder(stream); recRef.current = mr; const chunks = [];
    mr.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
    mr.onstop = async () => { stream.getTracks().forEach((t) => t.stop()); setRecording(false);
      await sendFile(new File([new Blob(chunks, { type: "audio/webm" })], `voice_${Date.now()}.webm`, { type: "audio/webm" })); };
    mr.start(); setRecording(true);
  }

  return (
    <div className="chat-main">
      <div className="row between" style={{ padding: "8px 12px", borderBottom: "1px solid var(--stroke)" }}>
        <b style={{ fontSize: 13 }}>{title}</b>
        {selMode ? (
          <div className="row" style={{ gap: 6 }}>
            <span className="faint" style={{ fontSize: 11 }}>{sel.size} selected</span>
            <button className="btn sm" onClick={() => copyTexts(selMsgs())} title="Copy selected">⧉ Copy</button>
            <button className="btn sm" onClick={fwdSelected} title="Forward selected">↪ Forward</button>
            <button className="btn sm danger" onClick={delSelected} title="Delete selected">🗑 Delete</button>
            <button className="btn sm ghost" onClick={() => { setSel(new Set()); setSelMode(false); }}>✕</button>
          </div>
        ) : (
          <div className="row" style={{ gap: 6 }}>
            <span className="faint" style={{ fontSize: 11 }}>same pool · chat view</span>
            <button className="btn sm" disabled={!messages.length} onClick={() => copyTexts(messages)} title="Copy the whole conversation">⧉ Copy all</button>
          </div>
        )}
      </div>
      <div className="chat-scroll" ref={scrollRef}>
        {messages.length === 0 && <div className="empty">No messages yet — say hi, attach a photo, file or voice note.</div>}
        {messages.map((m, i) => {
          const you = (m.role || "") === "user";
          const att = m.attachment;
          const replied = m.reply_to ? messages.find((x) => x.id === m.reply_to) : null;
          const picked = sel.has(m.id);
          return (
            <div key={i} className={"msg " + (you ? "user" : "assistant")} style={{ position: "relative", outline: picked ? "2px solid var(--brand-2)" : "none", cursor: selMode ? "pointer" : "default" }}
              onClick={selMode ? () => toggleSel(m.id) : undefined}>
              {m.sender && <div className="faint" style={{ fontSize: 10.5, marginBottom: 3, fontWeight: 700, color: "var(--brand-2)" }}>{m.sender}</div>}
              {replied && <div style={{ borderLeft: "2px solid var(--brand-2)", padding: "2px 6px", margin: "0 0 4px", fontSize: 11, color: "var(--txt-faint)", background: "rgba(255,255,255,.04)", borderRadius: 4 }}>↩ {(replied.sender || replied.role)}: {String(replied.content || replied.kind || "").slice(0, 60)}</div>}
              {att && att.kind === "image" && <img src={api.fileUrl(att.url)} alt={att.name || "image"} style={{ maxWidth: "100%", borderRadius: 8, margin: "4px 0", display: "block" }} />}
              {att && att.kind === "audio" && <div><audio controls src={api.fileUrl(att.url)} style={{ width: "100%", margin: "4px 0" }} />{m.content && <em style={{ color: "var(--txt-dim)" }}>“{m.content}”</em>}</div>}
              {att && (att.kind === "file" || att.kind === "zip") && <a href={api.fileUrl(att.url)} target="_blank" rel="noreferrer" className="pill" style={{ display: "inline-flex", gap: 6, margin: "4px 0", textDecoration: "none" }}>{att.kind === "zip" ? "🗜" : "📄"} {att.name || "file"}</a>}
              {(!att || m.kind === "text") && (m.content || "")}
              <button className="msg-copy" onClick={(e) => { e.stopPropagation(); setReplyTo(m); }} title="Reply"
                style={{ position: "absolute", top: 4, right: 4, width: 22, height: 22, fontSize: 11, lineHeight: "20px", borderRadius: 6, border: "1px solid var(--stroke-strong)", background: "var(--bg)", color: "var(--txt-dim)", cursor: "pointer" }}>↩</button>
              <button className="msg-copy" onClick={(e) => { e.stopPropagation(); toggleSel(m.id); }} title="Select"
                style={{ position: "absolute", top: 4, right: 30, width: 22, height: 22, fontSize: 11, lineHeight: "20px", borderRadius: 6, border: "1px solid var(--stroke-strong)", background: "var(--bg)", color: picked ? "var(--brand-2)" : "var(--txt-dim)", cursor: "pointer" }}>{picked ? "☑" : "▢"}</button>
            </div>
          );
        })}
      </div>
      {replyTo && (
        <div className="row" style={{ gap: 8, padding: "4px 18px" }}>
          <span className="faint" style={{ fontSize: 11 }}>↩ Replying to {(replyTo.sender || replyTo.role)}: {String(replyTo.content || replyTo.kind || "").slice(0, 50)}</span>
          <span style={{ cursor: "pointer", opacity: 0.7 }} onClick={() => setReplyTo(null)}>✕</span>
        </div>
      )}
      <input type="file" ref={fileRef} style={{ display: "none" }} onChange={(e) => { const f = e.target.files && e.target.files[0]; if (f) sendFile(f); e.target.value = ""; }} />
      <div className="composer">
        <button className="iconbtn" onClick={() => fileRef.current && fileRef.current.click()} title="Send image / file / doc / zip">📎</button>
        <button className={"iconbtn " + (recording ? "live" : "")} onClick={toggleMic} title={recording ? "Stop recording" : "Voice note"}>{recording ? "■" : "🎤"}</button>
        <textarea value={draft} placeholder="Message…" onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendText(); } }} />
        <button className="btn primary" onClick={sendText} disabled={busy}>Send</button>
      </div>
    </div>
  );
}
