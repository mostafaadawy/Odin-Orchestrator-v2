import React, { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { api, streamScope, speak, stopSpeech, transcribe } from "./api.js";
import { Markdown, toSpeech } from "./ui.jsx";

// A full multi-level chat bound to ANY scope (company / project / member).
export default function ChatPanel({ scope, lang = "en", autospeak = false, onActivity, activeNow = false, activePhase = "" }) {
  const [lng, setLng] = useState(lang); // EN/AR, switchable from the chat header
  const [sideOpen, setSideOpen] = useState(true); // collapse the chat list for more space
  const [chats, setChats] = useState([]);
  const [cid, setCid] = useState(null);
  const [messages, setMessages] = useState([]);
  const [syncing, setSyncing] = useState(false);
  const [running, setRunning] = useState(false); // ▶ run-now (recurring task) in flight
  const [showMonitor, setShowMonitor] = useState(false); // 🎙 live-meeting popup dialog (in-app, not a browser)
  const [meetingCapable, setMeetingCapable] = useState(false); // project owns the live-meeting asset (has the agent)
  const [showExport, setShowExport] = useState(false); // 📄 report-export menu (PDF/DOCX/MD/PPTX)
  const [steps, setSteps] = useState([]);
  const [streaming, setStreaming] = useState(false);
  const [runActive, setRunActive] = useState(false); // a run is active on the server
  const [runStuck, setRunStuck] = useState(false);   // active but silent too long → likely wedged
  const stuckRef = useRef({ n: 0, t: Date.now() });
  const [draft, setDraft] = useState("");
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [micErr, setMicErr] = useState("");
  const [attached, setAttached] = useState([]);   // file/folder paths to include in the next message
  const [plusOpen, setPlusOpen] = useState(false);
  const [copied, setCopied] = useState(null);   // which message/"all" was just copied (shows ✓)
  const [queue, setQueue] = useState([]);        // messages typed while busy, sent when it's free
  const [capGap, setCapGap] = useState(null);    // {task, recommended[], suggestion{}} → CTO capability dialog
  const [capMode, setCapMode] = useState("self"); // self | existing | create
  const [capPick, setCapPick] = useState("");    // chosen existing agent
  const [capName, setCapName] = useState("");    // new custom agent name (editable suggestion)
  const [capRole, setCapRole] = useState("");    // new custom agent role
  const [capRules, setCapRules] = useState("");  // new custom agent rules (editable suggestion)
  const [capEditPick, setCapEditPick] = useState(""); // existing member chosen to EXPAND (choice 3)
  const [capEditRules, setCapEditRules] = useState(""); // its current role rules, editable to widen
  const esRef = useRef(null);                    // the live stream, so Stop can really close it
  const scrollRef = useRef(null);
  const recRef = useRef(null);   // MediaRecorder (Whisper fallback)
  const srRef = useRef(null);    // live SpeechRecognition (primary)
  const draftLockRef = useRef(false); // when true, late dictation results must NOT refill the input (we just sent)

  async function copyText(text, key) {
    try {
      if (navigator.clipboard?.writeText) await navigator.clipboard.writeText(text || "");
      else { const t = document.createElement("textarea"); t.value = text || ""; document.body.appendChild(t); t.select(); document.execCommand("copy"); t.remove(); }
      setCopied(key); setTimeout(() => setCopied((k) => (k === key ? null : k)), 1200);
    } catch {}
  }

  useEffect(() => { loadChats(); }, [scope]);
  useEffect(() => { if (scope) loadChat(); }, [scope, cid]);
  // LIVE: while a run is writing to this chat (e.g. the team run working through DevOps), keep the
  // open chat in sync so you SEE it progress — and so it's all still here when you navigate back.
  // Skips while you're locally streaming/recording so it never clobbers your own in-flight message.
  useEffect(() => {
    if (!cid) return;
    const t = setInterval(async () => {
      if (streaming || recording) return;
      const msgs = await api.scopeAllMessages(scope).catch(() => null);
      if (Array.isArray(msgs)) {
        setMessages((prev) => msgs.length !== prev.length ? msgs : prev);
      }
      // RUN STATE: know if a run is active; if active but silent >90s, flag STUCK and auto-try to clear it.
      if (typeof scope === "string" && scope.startsWith("project:")) {
        const pid = scope.slice("project:".length);
        const st = await api.runStatus(pid).catch(() => null);
        const active = !!(st && st.running);
        setRunActive(active);
        const n = Array.isArray(msgs) ? msgs.length : stuckRef.current.n;
        if (n !== stuckRef.current.n) { stuckRef.current = { n, t: Date.now() }; setRunStuck(false); }
        else if (active && Date.now() - stuckRef.current.t > 300000) { setRunStuck(true); }  // >5min silent: INFO only, NEVER auto-stop (that killed real runs)
        else if (!active) { setRunStuck(false); }
      }
      refreshChatList();
    }, 3000);
    return () => clearInterval(t);
  }, [cid, scope, streaming, recording]);
  useEffect(() => { scrollRef.current && (scrollRef.current.scrollTop = scrollRef.current.scrollHeight); }, [messages, steps]);
  // close the live-meeting dialog when its iframe asks to close; refresh chat (report was posted in)
  useEffect(() => {
    function onMsg(e) { if (e && e.data && e.data.type === "meeting-close") { setShowMonitor(false); setTimeout(doRefresh, 400); } }
    window.addEventListener("message", onMsg);
    return () => window.removeEventListener("message", onMsg);
  }, []);
  // is THIS project meeting-capable? (has the Live Meeting & Voice Streaming Agent) → show the 🎙 button
  useEffect(() => {
    let ok = true;
    if (typeof scope === "string" && scope.startsWith("project:")) {
      api.meetingCapable(scope.slice("project:".length)).then((c) => { if (ok) setMeetingCapable(c); });
    } else setMeetingCapable(false);
    return () => { ok = false; };
  }, [scope]);

  async function loadChats() {
    const cs = await api.scopeChats(scope).catch(() => []);
    // newest-activity first, so returning to a member lands on the chat that's ACTUALLY working
    const sorted = [...cs].sort((a, b) => (b.updated || b.created || 0) - (a.updated || a.created || 0));
    setChats(sorted);
    if (sorted.length) setCid((prev) => prev && sorted.some((c) => c.id === prev) ? prev : sorted[0].id);
    else { const c = await api.createScopeChat(scope); setChats([c]); setCid(c.id); }
  }
  // refresh ONLY the chat-list titles/counts — never touch the current cid or messages
  // (calling loadChats() after a send caused the message to re-appear/duplicate).
  async function refreshChatList() {
    const cs = await api.scopeChats(scope).catch(() => null);
    if (cs) setChats(cs);
  }
  async function loadChat() {
    // Show the WHOLE scope pool — every chat merged in time order — so the full CTO↔agent group
    // conversation is visible and scrollable (WhatsApp-style), not just one sub-chat's messages.
    const msgs = await api.scopeAllMessages(scope).catch(() => null);
    setMessages(Array.isArray(msgs) ? msgs : []);
    setSteps([]);
  }
  // manual REFRESH — re-pull the whole seq-sorted pool for this scope (WhatsApp-style "syncing…"); recovers
  // any message that was missed. Reads the WHOLE scope pool (all chats merged, seq order), then this chat.
  async function doRefresh() {
    setSyncing(true);
    try {
      await loadChats();
      if (cid) await loadChat();
    } catch (e) { /* keep what we have */ }
    setSyncing(false);
  }
  // ▶ RUN NOW — trigger the project's AUTONOMOUS scheduled run (the exact thing the cron does — it EXECUTES,
  // it does NOT stop to ask approval like the interactive chat). Its output is posted into THIS chat.
  async function runProjectNow() {
    if (!(typeof scope === "string" && scope.startsWith("project:"))) return;
    if (running) return;
    const pid = scope.slice("project:".length);
    setRunning(true);
    setMessages((m) => [...m, { role: "assistant", content: "▶ Running the recurring task now — autonomous (it executes, no approval prompt). This can take a bit; the result will appear here." }]);
    try {
      await api.runNow(pid, "", cid || "");
      setTimeout(doRefresh, 3000);
      setTimeout(doRefresh, 8000);
      setTimeout(doRefresh, 15000);
    } catch (e) { setMicErr(String((e && e.message) || e)); }
    finally { setRunning(false); }
  }
  async function newChat() {
    const c = await api.createScopeChat(scope, "New chat");
    setChats((p) => [c, ...p.filter((x) => x.id !== c.id)]); setCid(c.id); setMessages([]);
  }
  async function delChat(id) {
    await api.deleteScopeChat(scope, id);
    const rest = chats.filter((c) => c.id !== id); setChats(rest);
    if (id === cid) { rest.length ? setCid(rest[0].id) : newChat(); }
  }

  function send() {
    if (recording) { toggleMic(); return; }   // finish dictation first — don't send a partial sentence
    let text = draft.trim();
    if (!text && attached.length === 0) return;
    if (attached.length) text = `[Attached for you to use/consider: ${attached.join(" | ")}]\n${text}`.trim();
    draftLockRef.current = true;   // block any late dictation transcript from refilling the box
    setDraft(""); setAttached([]);
    if (streaming) { setQueue((q) => [...q, text]); return; }   // busy → QUEUE it, don't block
    stopSpeech();
    fire(text);
  }

  function fire(text) {
    setMessages((m) => [...m, { role: "user", content: text }, { role: "assistant", content: "" }]);
    setSteps([]); setStreaming(true);
    let acc = "";
    esRef.current = streamScope(scope, text, lng, cid, {
      status: (d) => setSteps((s) => [...s, d]),
      delegate: (d) => onActivity && onActivity(d),
      capability_gap: (d) => {
        const sg = d.suggestion || {};
        setCapMode((d.recommended || []).length ? "existing" : "create");
        setCapPick((d.recommended && d.recommended[0] && d.recommended[0].name) || "");
        setCapName(sg.name || ""); setCapRole(sg.role || ""); setCapRules(sg.rules || "");
        setCapGap(d);
      },
      token: (d) => { acc += d.t; setMessages((m) => { const c = [...m]; c[c.length - 1] = { role: "assistant", content: acc }; return c; }); },
      done: () => { esRef.current = null; setStreaming(false); if (autospeak && acc) speak(toSpeech(acc), lng); refreshChatList(); dequeue(); },
      error: (d) => { esRef.current = null; setStreaming(false); setMessages((m) => { const c = [...m]; c[c.length - 1] = { role: "assistant", content: "⚠️ " + (d.text || "error") }; return c; }); dequeue(); },
    });
  }

  // Resolve the CTO capability dialog → one of: CTO does it / pick existing agent / create custom.
  // Every path keeps the SAME shared pool (the message goes to the project scope all agents see).
  async function resolveCapability() {
    if (!capGap) return;
    const task = capGap.task || "";
    let msg;
    if (capMode === "existing") {
      if (!capPick) return;
      msg = `⟦resolve⟧ Delegate this to ${capPick} (they have the full shared pool): ${task}`;
    } else if (capMode === "create") {
      if (!capName.trim() || !capRole.trim()) return;
      try {
        const pid = scope.split(":")[1];
        await api.addAgentForce(pid, { name: capName.trim(), role: capRole.trim(),
          description: capRules.trim(), restrictions: capRules.trim() ? [capRules.trim()] : [] });
      } catch {}
      msg = `⟦resolve⟧ Delegate this to ${capName.trim()} (full shared context): ${task}`;
    } else if (capMode === "expand") {
      // CHOICE 3 — widen an EXISTING member's role so it can take this task (no new/duplicate agent)
      if (!capEditPick || !capEditRules.trim()) return;
      try {
        const pid = scope.split(":")[1];
        await api.updateAgent(pid, capEditPick, { description: capEditRules.trim(),
          restrictions: capEditRules.trim() ? [capEditRules.trim()] : [] });
      } catch {}
      msg = `⟦resolve⟧ Delegate this to ${capEditPick} (role expanded; full shared pool): ${task}`;
    } else {
      msg = `⟦resolve⟧ Handle this yourself, CTO (you have the full shared context): ${task}`;
    }
    setCapGap(null);
    if (streaming) { setQueue((q) => [...q, msg]); } else { stopSpeech(); fire(msg); }
  }

  // Send the next queued message (if any) once the current run ends.
  function dequeue() {
    setQueue((q) => {
      if (q.length) { const [next, ...rest] = q; setTimeout(() => fire(next), 150); return rest; }
      return q;
    });
  }

  // REAL stop: close the live stream (the server disconnects and terminates the engine), and mark it.
  function stop() {
    try { esRef.current && esRef.current.close(); } catch {}
    esRef.current = null;
    setStreaming(false);
    setMessages((m) => {
      const c = [...m];
      if (c.length && c[c.length - 1].role === "assistant")
        c[c.length - 1] = { role: "assistant", content: (c[c.length - 1].content || "") + "\n\n⏹ Stopped by you." };
      return c;
    });
  }

  // MIC: record and re-transcribe the GROWING clip every ~900ms with a FAST whisper model, so the
  // text appears in near-real-time as you speak; a final pass with the full model on stop. Errors
  // are surfaced so we're never blind. (Web Speech is NOT used — it silently fails in Electron.)
  async function startWhisper() {
    setMicErr("");
    draftLockRef.current = false; // a fresh dictation may write to the box again
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      setMicErr("Microphone blocked — allow it in System Settings → Privacy & Security → Microphone, then reopen.");
      setRecording(false);
      return;
    }
    let mr;
    try { mr = new MediaRecorder(stream); }
    catch (e) { setMicErr("Recorder error: " + (e.message || e)); stream.getTracks().forEach((t) => t.stop()); return; }
    startBeep();                              // audible START cue so you know it's listening
    recRef.current = mr;
    const chunks = [];
    const base = draft ? draft + " " : "";
    let busy = false;
    const interim = async () => {             // live text WHILE you talk (fast model, with a delay)
      if (busy || chunks.length === 0) return;
      busy = true;
      try { const t = await transcribe(new Blob(chunks, { type: "audio/webm" }), lng, true); if (t && !draftLockRef.current) setDraft(base + t); }
      catch { /* partial decode can fail mid-stream — the final pass fixes it */ }
      busy = false;
    };
    const iv = setInterval(interim, 1800);
    mr.ondataavailable = (e) => { if (e.data && e.data.size) chunks.push(e.data); };
    mr.onstop = async () => {
      clearInterval(iv);
      stream.getTracks().forEach((t) => t.stop());
      setRecording(false); setTranscribing(true);   // "refining…" — correct the full sentence
      try {
        const t = await transcribe(new Blob(chunks, { type: "audio/webm" }), lng, false); // accurate model
        if (t && !draftLockRef.current) setDraft(base + t);
        else if (!t) setMicErr("No speech detected — try again, a bit closer to the mic.");
      } catch (e) {
        setMicErr(String(e.message || e));
      }
      setTranscribing(false);
    };
    mr.start(500);                            // emit audio chunks every 0.5s for the live passes
    setRecording(true);
  }

  function startBeep() {
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext;
      const ctx = new Ctx();
      const o = ctx.createOscillator(), g = ctx.createGain();
      o.frequency.value = 880; o.connect(g); g.connect(ctx.destination);
      g.gain.setValueAtTime(0.05, ctx.currentTime);
      o.start(); o.stop(ctx.currentTime + 0.12);
      setTimeout(() => { try { ctx.close(); } catch {} }, 300);
    } catch {}
  }

  function toggleMic() {
    if (recording) {
      if (recRef.current) { try { recRef.current.stop(); } catch {} }
      setRecording(false);
      return;
    }
    startWhisper();
  }

  const groups = groupChatsByDate(chats);
  return (
    <div className="chat" style={{ flexDirection: "row" }}>
      {capGap && (
        <div style={{ position: "fixed", inset: 0, zIndex: 2147483647, background: "rgba(0,0,0,.55)",
          display: "flex", alignItems: "center", justifyContent: "center", padding: 18 }}
          onClick={(e) => { if (e.target === e.currentTarget) setCapGap(null); }}>
          <div className="card pad" style={{ width: "min(560px,94vw)", maxHeight: "88vh", overflow: "auto", background: "var(--bg)" }}>
            <b style={{ fontSize: 14 }}>🧭 The current agent can't do this per its rules</b>
            <div className="faint" style={{ fontSize: 12, margin: "6px 0 12px" }}>
              Please specify what you need — “{(capGap.task || "").slice(0, 120)}”. What would you like me to do?
            </div>
            <div className="col" style={{ gap: 8 }}>
              {[["self", "🧭 I'll do it myself (CTO handles it)"],
                ["existing", "🔁 Embed an existing agent"],
                ["expand", "✏️ Expand an existing member's role"],
                ["create", "➕ Create a new custom role"]].map(([m, lbl]) => (
                <button key={m} className={"btn" + (capMode === m ? " primary" : "")} style={{ textAlign: "left" }}
                  onClick={() => setCapMode(m)}>{lbl}</button>
              ))}
            </div>
            {capMode === "existing" && (
              <div style={{ marginTop: 10 }}>
                <label>Recommended agents for this task</label>
                <select value={capPick} onChange={(e) => setCapPick(e.target.value)} style={{ width: "100%" }}>
                  {(capGap.recommended || []).map((r) => <option key={r.name} value={r.name}>{r.name} — {r.role}</option>)}
                </select>
              </div>
            )}
            {capMode === "expand" && (
              <div className="col" style={{ gap: 6, marginTop: 10 }}>
                <label>Expand which member's role?</label>
                <select value={capEditPick} onChange={(e) => {
                  const m = (capGap.editable || []).find((x) => x.name === e.target.value);
                  setCapEditPick(e.target.value); setCapEditRules((m && (m.rules || "")) || "");
                }} style={{ width: "100%" }}>
                  <option value="">— pick a member —</option>
                  {(capGap.editable || []).map((r) => <option key={r.name} value={r.name}>{r.name} — {r.role}</option>)}
                </select>
                <div className="faint" style={{ fontSize: 11 }}>Edit its role/rules to also cover this task:</div>
                <textarea value={capEditRules} placeholder="Current role rules — add what it should also do"
                  onChange={(e) => setCapEditRules(e.target.value)} style={{ minHeight: 80 }} />
              </div>
            )}
            {capMode === "create" && (
              <div className="col" style={{ gap: 6, marginTop: 10 }}>
                <div className="faint" style={{ fontSize: 11 }}>Suggested name, role & rule — accept, edit, or replace:</div>
                {capGap.suggestion && capGap.suggestion.overlaps && (
                  <div className="faint" style={{ fontSize: 11, color: "var(--warn,#d80)" }}>
                    ⚠ {capGap.suggestion.overlaps.note}
                  </div>
                )}
                <input value={capName} placeholder="Agent name" onChange={(e) => setCapName(e.target.value)} />
                <input value={capRole} placeholder="Role" onChange={(e) => setCapRole(e.target.value)} />
                <textarea value={capRules} placeholder="Rules / scope (prevents hallucination)" onChange={(e) => setCapRules(e.target.value)} style={{ minHeight: 70 }} />
              </div>
            )}
            <div className="row" style={{ gap: 8, marginTop: 14, justifyContent: "flex-end" }}>
              <button className="btn ghost" onClick={() => setCapGap(null)}>Cancel</button>
              <button className="btn primary"
                disabled={(capMode === "existing" && !capPick) || (capMode === "create" && (!capName.trim() || !capRole.trim())) || (capMode === "expand" && (!capEditPick || !capEditRules.trim()))}
                onClick={resolveCapability}>Proceed</button>
            </div>
          </div>
        </div>
      )}
      {/* The middle chat-list column ("extra bar") is intentionally GONE — chats now live in the ONE main
          left sidebar (CHATS section), consistent with web + mobile. The container is just the conversation. */}
      <div className="chat-main">
      <div className="row between" style={{ padding: "8px 12px", borderBottom: "1px solid var(--stroke)" }}>
        <div className="row" style={{ gap: 8 }}>
          <span className="faint" style={{ fontSize: 11 }}>{scopeLabel(scope)}</span>
          <button className="iconbtn" style={{ width: 28, height: 28, fontSize: 12 }} disabled={!messages.length}
            title="Copy the whole conversation"
            onClick={() => copyText(messages.map((m) => `${m.role === "assistant" ? "Assistant" : "You"}: ${m.content || ""}`).join("\n\n"), "all")}>
            {copied === "all" ? "✓" : "⧉"}</button>
          {/* REFRESH — pull the latest pool from the single source of truth (seq-sorted); shows "syncing…" */}
          <button className="iconbtn" style={{ width: 28, height: 28, fontSize: 13 }} disabled={syncing}
            title="Refresh — pull the latest messages (seq-sorted)" onClick={doRefresh}>
            {syncing ? "…" : "↻"}</button>
          {syncing && <span className="faint" style={{ fontSize: 10.5 }}>syncing…</span>}
          {/* ▶ RUN NOW — fire this project's recurring/scheduled task on demand */}
          {typeof scope === "string" && scope.startsWith("project:") && (
            <button className="iconbtn" style={{ width: 28, height: 28, fontSize: 13, color: "var(--ok)" }} disabled={running}
              title="Run now — the recurring/periodic task (autonomous, runs in this chat)"
              onClick={runProjectNow}>
              {running ? "…" : "▶"}</button>
          )}
          {/* 📄 REPORT EXPORT — Reporting agent capability, surfaced at the top of the chat for project scopes.
              One click each: PDF / DOCX / MD / PPTX (opens the styled report from the brain). */}
          {typeof scope === "string" && scope.startsWith("project:") && (
            <span style={{ position: "relative" }}>
              <button className="iconbtn" style={{ width: 28, height: 28, fontSize: 13 }}
                title="Export report — PDF · DOCX · MD · PPTX (Reporting agent)"
                onClick={() => setShowExport((v) => !v)}>📄</button>
              {showExport && (
                <div style={{ position: "absolute", top: 32, right: 0, zIndex: 30, background: "var(--panel-solid)",
                  border: "1px solid var(--stroke-strong)", borderRadius: 10, padding: 6, minWidth: 180,
                  boxShadow: "0 18px 50px rgba(0,0,0,.5)" }}>
                  {[["pdf", "📄  Export PDF"], ["docx", "📝  Export Word (.docx)"], ["md", "🔖  Export Markdown"], ["pptx", "📊  Export PowerPoint"]].map(([f, label]) => (
                    <button key={f} className="btn sm ghost" style={{ display: "block", width: "100%", textAlign: "left", border: 0 }}
                      onClick={() => { window.open(api.reportUrl(scope.slice("project:".length), f), "_blank"); setShowExport(false); }}>
                      {label}</button>
                  ))}
                </div>
              )}
            </span>
          )}
          {/* 🎙 LIVE MEETING — shown only when the project owns the asset (has the Live Meeting & Voice
              Streaming Agent). Opens the in-app popup dialog (not a browser). */}
          {meetingCapable && (
            <button className="iconbtn" style={{ width: 28, height: 28, fontSize: 14 }}
              title="Live meeting — voice streaming → smart report (MD/Word · AR/EN)"
              onClick={() => setShowMonitor(true)}>
              🗣️</button>
          )}
        </div>
        <div className="row" style={{ gap: 0, border: "1px solid var(--stroke-strong)", borderRadius: 9, overflow: "hidden" }}>
          <button className={"btn sm ghost" + (lng === "en" ? " primary" : "")} style={{ borderRadius: 0, border: 0 }} onClick={() => setLng("en")} title="Reply and speak in English">EN</button>
          <button className={"btn sm ghost" + (lng === "ar" ? " primary" : "")} style={{ borderRadius: 0, border: 0 }} onClick={() => setLng("ar")} title="الرد والتحدث بالعربية">ع</button>
        </div>
      </div>

      {typeof scope === "string" && scope.startsWith("project:") && (() => {
        const working = running || streaming || runActive;
        if (working && runStuck) return (
          <div style={{ padding: "12px 14px", textAlign: "center", fontWeight: 800, fontSize: 14,
            background: "rgba(216,0,0,.16)", color: "#ff6b6b", borderBottom: "1px solid rgba(216,0,0,.35)" }}>
            ⚠️ Taking longer than usual — still working (reads can take minutes). Nothing stopped; let it finish.
          </div>);
        if (working) return (
          <div style={{ padding: "12px 14px", textAlign: "center", fontWeight: 800, fontSize: 14,
            background: "rgba(245,166,35,.16)", color: "#f5a623", borderBottom: "1px solid rgba(245,166,35,.35)" }}>
            ⏳ WORKING — the CTO is on it. New messages appear below.
          </div>);
        if (messages.length) return (
          <div style={{ padding: "12px 14px", textAlign: "center", fontWeight: 800, fontSize: 14,
            background: "rgba(0,200,83,.14)", color: "#33d17a", borderBottom: "1px solid rgba(0,200,83,.35)" }}>
            ✅ FINISHED — the CTO's final answer is below. Nothing more until you ask again.
          </div>);
        return null;
      })()}
      <div className="chat-scroll" ref={scrollRef}>
        {messages.length === 0 && <div className="empty">Start the conversation in this scope.</div>}
        {messages.map((m, i) => {
          const ar = /[؀-ۿ]/.test(m.content || "");   // Arabic → RTL, English → LTR
          return (
            <motion.div key={i} className={`msg ${m.role} msg-copyable`} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              dir={ar ? "rtl" : "ltr"} style={{ textAlign: ar ? "right" : "left", position: "relative" }}>
              {m.role === "assistant" ? <Markdown text={m.content || (streaming && i === messages.length - 1 ? "…" : "")} /> : m.content}
              <button className="msg-copy" title="Copy this message" onClick={() => copyText(m.content || "", i)}
                style={{ position: "absolute", top: 4, [ar ? "left" : "right"]: 4, width: 22, height: 22, fontSize: 11, lineHeight: "20px",
                  borderRadius: 6, border: "1px solid var(--stroke-strong)", background: "var(--bg)", color: "var(--txt-dim)", cursor: "pointer" }}>
                {copied === i ? "✓" : "⧉"}</button>
            </motion.div>
          );
        })}
      </div>

      <AnimatePresence>
        {streaming && steps.length > 0 && (
          <motion.div className="status-rail" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            {steps.slice(-5).map((s, i) => (
              <div className="status-step" key={i}>
                <span className="ic">{s.icon || "•"}</span><span>{s.text}</span>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {attached.length > 0 && (
        <div className="row wrap" style={{ gap: 6, padding: "0 18px 6px" }}>
          {attached.map((p, i) => (
            <span key={i} className="pill" style={{ display: "flex", gap: 6, alignItems: "center" }} title={p}>
              📎 {p.split("/").pop() || p}
              <span style={{ cursor: "pointer", opacity: 0.7 }} onClick={() => setAttached((a) => a.filter((_, j) => j !== i))}>✕</span>
            </span>
          ))}
        </div>
      )}
      <div className="composer">
        <div style={{ position: "relative" }}>
          <button className="iconbtn" onClick={() => setPlusOpen((o) => !o)} title="Attach a file or folder for the chat to use">＋</button>
          {plusOpen && (
            <div className="card" style={{ position: "absolute", bottom: 50, left: 0, zIndex: 30, padding: 6, minWidth: 170 }}>
              <button className="navitem" onClick={async () => { setPlusOpen(false); const f = window.odin && (await window.odin.pickFiles()); if (f && f.length) setAttached((a) => [...a, ...f]); }}>🖼 Attach file(s)</button>
              <button className="navitem" onClick={async () => { setPlusOpen(false); const f = window.odin && (await window.odin.pickFolders()); if (f && f.length) setAttached((a) => [...a, ...f]); }}>🗂 Attach folder(s)</button>
            </div>
          )}
        </div>
        <button className={"iconbtn " + (recording ? "live" : "")} onClick={toggleMic}
          title={recording ? "Listening — tap to stop" : "Speak"}>
          {recording ? "■" : "🎤"}
        </button>
        {recording && <span className="pill blink" style={{ color: "var(--danger)", alignSelf: "center" }}>● listening — speak</span>}
        {transcribing && <span className="pill" style={{ color: "var(--warn)", alignSelf: "center" }}>refining…</span>}
        {(streaming || activeNow) && <span className="pill blink" style={{ color: "var(--ok)", alignSelf: "center" }}>● working{activeNow && activePhase ? ` — ${activePhase}` : "…"}</span>}
        {queue.length > 0 && <span className="pill" style={{ color: "var(--brand-2)", alignSelf: "center" }} title="Queued — will send when the current task is done">⏳ {queue.length} queued</span>}
        {micErr && <span className="pill" style={{ color: "var(--danger)", alignSelf: "center", maxWidth: 320, overflow: "hidden", textOverflow: "ellipsis" }} title={micErr}>{micErr}</span>}
        <textarea value={draft} dir={lng === "ar" ? "rtl" : "ltr"}
          placeholder={streaming ? (lng === "ar" ? "يعمل… اكتب لإضافته للطابور" : "Working… type to queue the next message") : (lng === "ar" ? "اكتب رسالتك…" : `Message ${scope.split(":").pop() || "Odin"}…`)}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} />
        <button className="iconbtn" onClick={stopSpeech} title="Stop the current voice playback">⏹</button>
        {streaming
          ? <button className="btn" style={{ background: "var(--danger)", color: "#fff", borderColor: "var(--danger)" }} onClick={stop} title="Stop the running task now">⏹ Stop</button>
          : <button className="btn primary" onClick={send} title="Send your message (Enter)">{queue.length ? "Queue" : "Send"}</button>}
      </div>
      </div>
      {/* 🎙 LIVE MEETING — in-app popup dialog (NOT a browser tab). Same page served by the brain,
          embedded in an iframe so it looks/behaves identically on web + desktop. Mic allowed. */}
      {showMonitor && typeof scope === "string" && scope.startsWith("project:") && (
        <div style={{ position: "fixed", inset: 0, background: "rgba(4,6,12,.72)", zIndex: 1000, display: "flex", alignItems: "center", justifyContent: "center" }}
             onClick={(e) => { if (e.target === e.currentTarget) setShowMonitor(false); }}>
          <div style={{ width: "min(820px, 94vw)", height: "min(760px, 92vh)", background: "var(--panel, #121522)", border: "1px solid var(--stroke, #232838)", borderRadius: 14, overflow: "hidden", boxShadow: "0 20px 60px rgba(0,0,0,.5)" }}>
            <iframe title="Live Meeting" allow="microphone; autoplay"
              src={api.monitorUrl(scope.slice("project:".length))}
              style={{ width: "100%", height: "100%", border: 0 }} />
          </div>
        </div>
      )}
    </div>
  );
}

function scopeLabel(scope) {
  if (scope === "company") return "Chief Engineer · company";
  if (scope.startsWith("project:")) return "Project CTO";
  if (scope.startsWith("member:")) return scope.split(":").pop() + " · team member";
  return scope;
}

function groupChatsByDate(chats) {
  const out = {};
  const today = new Date(); today.setHours(0, 0, 0, 0);
  (chats || []).forEach((c) => {
    const d = c.updated ? new Date(c.updated * 1000) : new Date();
    const day = new Date(d); day.setHours(0, 0, 0, 0);
    const diff = Math.round((today - day) / 86400000);
    const label = diff <= 0 ? "Today" : diff === 1 ? "Yesterday" : d.toLocaleDateString();
    (out[label] = out[label] || []).push(c);
  });
  return out;
}
