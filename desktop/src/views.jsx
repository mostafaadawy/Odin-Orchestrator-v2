import React, { useEffect, useState, useRef } from "react";
import { createPortal } from "react-dom";
import { motion } from "framer-motion";
import { api, getBase, streamOrchestrate } from "./api.js";
import { Avatar, avatarKey, Modal, UsageBar, StatusDot, Markdown } from "./ui.jsx";
const api_base = () => getBase();
import ChatPanel from "./ChatPanel.jsx";

const COLOR = { frontend: "var(--frontend)", backend: "var(--backend)", devops: "var(--devops)", security: "var(--security)", qa: "var(--qa)", database: "var(--database)", generic: "var(--generic)" };

// OS (macOS) notification — works inside Electron via the Web Notifications API.
function osNotify(title, body) {
  try {
    if (!("Notification" in window)) return;
    if (Notification.permission === "granted") { new Notification(title, { body }); return; }
    if (Notification.permission !== "denied") Notification.requestPermission().then((p) => { if (p === "granted") new Notification(title, { body }); });
  } catch {}
}

// Announce a finished/failed outcome BOTH ways: a styled in-app dialog (OutcomeToasts) + an OS
// notification — so you always know it ended and whether it worked, without asking.
export function emitOutcome(kind, title, message) {
  try { window.dispatchEvent(new CustomEvent("odin-outcome", { detail: { kind, title, message, id: Date.now() + Math.random() } })); } catch {}
  osNotify(title, (message || "").replace(/\s+/g, " ").slice(0, 180));
}

/* Clear, nicely-styled outcome dialogs at top-center: green for success, red for a problem.
   Success auto-dismisses; problems stay until you close them. */
export function OutcomeToasts() {
  const [items, setItems] = useState([]);
  useEffect(() => {
    const onEvt = (e) => {
      const o = e.detail; if (!o) return;
      setItems((x) => [...x.filter((i) => i.id !== o.id), o]);
      if (o.kind === "success") setTimeout(() => setItems((x) => x.filter((i) => i.id !== o.id)), 9000);
    };
    window.addEventListener("odin-outcome", onEvt);
    return () => window.removeEventListener("odin-outcome", onEvt);
  }, []);
  if (!items.length) return null;
  return (
    <div style={{ position: "fixed", top: 18, left: "50%", transform: "translateX(-50%)", zIndex: 100, display: "flex", flexDirection: "column", gap: 10, width: "min(560px, 92vw)" }}>
      {items.map((o) => {
        const ok = o.kind === "success";
        return (
          <motion.div key={o.id} className="card pad" initial={{ y: -22, opacity: 0 }} animate={{ y: 0, opacity: 1 }} exit={{ opacity: 0 }}
            style={{ border: `1.5px solid ${ok ? "rgba(0,200,120,.65)" : "rgba(255,90,90,.75)"}`,
              boxShadow: `0 0 0 1px ${ok ? "rgba(0,200,120,.25)" : "rgba(255,90,90,.3)"}, 0 18px 44px rgba(0,0,0,.55)` }}>
            <div className="row between">
              <b style={{ fontSize: 14.5, color: ok ? "var(--ok)" : "var(--danger)" }}>{ok ? "✅" : "⚠️"} {o.title}</b>
              <button className="iconbtn" style={{ width: 26, height: 26 }} title="Dismiss"
                onClick={() => setItems((x) => x.filter((i) => i.id !== o.id))}>✕</button>
            </div>
            {o.message && <div style={{ fontSize: 12.5, marginTop: 6, lineHeight: 1.5, whiteSpace: "pre-wrap" }}>{o.message}</div>}
          </motion.div>
        );
      })}
    </div>
  );
}

/* Global finish watcher — polls EVERY project's operations and fires the success/fail dialog the
   instant any task reaches a terminal state (done / failed / stopped), no matter which screen you're
   on. Mounted once at the app root. Remembers what it already announced (localStorage) so a finished
   task is reported exactly once, and never re-announced after a reload. */
export function OperationFinishWatcher() {
  const seen = useRef(null);
  const firstRun = useRef(true);
  useEffect(() => {
    if (seen.current === null) {
      try { seen.current = new Set(JSON.parse(localStorage.getItem("odin.ops.announced") || "[]")); }
      catch { seen.current = new Set(); }
    }
    let alive = true;
    const tick = async () => {
      try {
        const ops = await api.operations();          // all projects, light (no log payload)
        if (!alive) return;
        for (const op of ops) {
          if (!op || !op.id || op.state === "running") continue;
          if (seen.current.has(op.id)) continue;
          seen.current.add(op.id);
          if (firstRun.current) continue;            // silently seed pre-existing finished tasks on first pass
          const ok = op.state === "done";
          emitOutcome(ok ? "success" : "problem",
            ok ? "Task finished" : op.state === "stopped" ? "Task stopped" : "Task failed",
            (op.summary || op.title || "") + (op.pid ? `  ·  ${op.pid}` : ""));
        }
        firstRun.current = false;
        try { localStorage.setItem("odin.ops.announced", JSON.stringify([...seen.current].slice(-200))); } catch {}
      } catch {}
    };
    tick();
    const t = setInterval(tick, 2500);
    return () => { alive = false; clearInterval(t); };
  }, []);
  return null;
}

/* Approval center — a popup bubble for every pending change an agent wants to make. Nothing is
   applied to your files or the VM until you Approve here. Also fires a macOS notification. */
// APPROVALS — a single top-bar button (blinks with a count while anything is pending) that opens ONE
// dialog holding EVERY pending approval as tabs. You decide them one-by-one; closing the dialog does NOT
// decide anything (they stay pending and the button keeps blinking). SECURITY approvals are shown red and
// are NEVER part of "approve all safe" — they must be decided individually.
export function ApprovalCenter() {
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState("");
  const [tab, setTab] = useState(0);
  const [confirmAll, setConfirmAll] = useState(null);   // F-33: the list shown before "Approve all"
  const seen = useRef(new Set());
  useEffect(() => {
    try { if ("Notification" in window && Notification.permission === "default") Notification.requestPermission(); } catch {}
    let alive = true;
    const load = async () => {
      try {
        const a = await api.approvals();
        if (!alive) return;
        setItems(a);
        a.forEach((x) => {
          if (!seen.current.has(x.id)) {
            seen.current.add(x.id);
            const n = (x.files?.length || 0) + (x.commands?.length || 0);
            osNotify(`Approval needed — ${x.member || "agent"}`, `${x.title || "A change needs your OK"} (${n} item${n === 1 ? "" : "s"})`);
          }
        });
      } catch {}
    };
    load();
    const t = setInterval(load, 2500);
    return () => { alive = false; clearInterval(t); };
  }, []);

  const SEV = {
    security: { rank: -1, border: "rgba(255,60,60,.95)", glow: "0 0 0 2px rgba(255,60,60,.5)", icon: "🔴", label: "SECURITY — decide individually", chip: "var(--danger)" },
    critical: { rank: 0, border: "rgba(255,90,90,.8)", glow: "0 0 0 1px rgba(255,90,90,.35)", icon: "🛑", label: "Critical — read carefully", chip: "var(--danger)" },
    caution: { rank: 1, border: "rgba(255,190,70,.7)", glow: "none", icon: "⚠️", label: "Caution", chip: "#e6a700" },
    routine: { rank: 2, border: "var(--stroke-strong)", glow: "none", icon: "🔔", label: "Review", chip: "var(--brand-2)" },
  };
  const sevOf = (a) => a.security ? "security" : (a.kind === "qa-recommendation" ? "routine" : (SEV[a.severity] ? a.severity : "caution"));
  const sorted = [...items].sort((x, y) => SEV[sevOf(x)].rank - SEV[sevOf(y)].rank);
  const count = sorted.length;
  const reds = sorted.filter((a) => sevOf(a) === "critical" || sevOf(a) === "security").length;
  const nonSec = sorted.filter((a) => !a.security).length;
  const cur = sorted[Math.min(tab, Math.max(0, count - 1))] || null;

  const act = async (aid, approve) => {
    setBusy(aid);
    try {
      if (approve) await api.approveChange(aid); else await api.rejectChange(aid);
      setItems((i) => i.filter((x) => x.id !== aid));
      seen.current.delete(aid);
      setTab((t) => Math.max(0, Math.min(t, count - 2)));
    } catch {} finally { setBusy(""); }
  };
  // F-33 (owner, 2026-10-11): "Approve all" first lists EVERY pending proposal (id, project, what it changes);
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
  };

  const fileList = (a) => a.files?.length > 0 && (
    <div style={{ marginBottom: 8 }}>
      <b style={{ fontSize: 11 }}>Files to change ({a.files.length}):</b>
      <div className="col" style={{ gap: 3, marginTop: 4 }}>
        {a.files.map((f, i) => (
          <div key={i} style={{ fontSize: 11 }}>
            <span className="pill" style={{ fontSize: 9, padding: "1px 6px" }}>{f.action}</span> {f.path}
            {f.why ? <span className="faint"> — {f.why}</span> : null}
          </div>
        ))}
      </div>
    </div>
  );
  const cmdList = (a) => a.commands?.length > 0 && (
    <div style={{ marginBottom: 8 }}>
      <b style={{ fontSize: 11 }}>Commands to run ({a.commands.length}):</b>
      <div className="col" style={{ gap: 3, marginTop: 4 }}>
        {a.commands.map((c, i) => (
          <div key={i} style={{ fontSize: 11, fontFamily: "ui-monospace, monospace" }}>
            <span className="pill" style={{ fontSize: 9, padding: "1px 6px", color: c.where === "vm" ? "var(--devops)" : "var(--txt)" }}>{c.where}</span> {c.cmd}
          </div>
        ))}
      </div>
    </div>
  );

  return (
    <>
      <style>{"@keyframes odn-appblink{0%,100%{box-shadow:0 0 0 0 rgba(255,80,80,0)}50%{box-shadow:0 0 0 3px rgba(255,80,80,.65)}}"}</style>
      <button className="btn sm" onClick={() => setOpen(true)}
        title={count ? `${count} approval(s) awaiting your decision` : "Approvals — nothing pending"}
        style={count ? { animation: "odn-appblink 1.1s infinite", borderColor: "var(--danger)", color: "var(--danger)", fontWeight: 700 } : {}}>
        🛡️ Approvals{count ? ` • ${count}` : ""}
      </button>
      {open && createPortal(
        <>
          <div onClick={() => setOpen(false)} style={{ position: "fixed", inset: 0, background: "rgba(4,6,12,.6)", backdropFilter: "blur(4px)", zIndex: 2147483004 }} />
          <div style={{ position: "fixed", top: "6vh", left: "50%", transform: "translateX(-50%)", width: "min(680px, 94vw)", maxHeight: "86vh",
            display: "flex", flexDirection: "column", background: "var(--panel-solid)", border: "1px solid var(--stroke-strong)",
            borderRadius: 16, boxShadow: "0 30px 80px rgba(0,0,0,.6)", zIndex: 2147483005, overflow: "hidden" }}>
            <div className="row between" style={{ padding: "13px 16px", borderBottom: "1px solid var(--stroke)" }}>
              <b style={{ fontSize: 14 }}>🛡️ Approvals {count ? `(${count})` : ""}{reds ? <span style={{ color: "var(--danger)" }}> · {reds} 🔴</span> : null}</b>
              <div className="row" style={{ gap: 8 }}>
                {nonSec > 1 && <button className="btn sm" disabled={busy === "__all__"} onClick={askApproveAll}
                  title="Approve all NON-security requests at once. Security alarms are left for individual decision.">✓ Approve all safe ({nonSec})</button>}
                <button className="btn sm ghost" onClick={() => setOpen(false)} title="Close — this does NOT decide anything; requests stay pending">✕ Close</button>
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
            )}
            {count === 0 ? (
              <div className="empty" style={{ padding: 40 }}>All clear — nothing needs your approval.</div>
            ) : (
              <>
                <div style={{ display: "flex", gap: 6, padding: "10px 12px", overflowX: "auto", borderBottom: "1px solid var(--stroke)", flexShrink: 0 }}>
                  {sorted.map((a, i) => {
                    const s = SEV[sevOf(a)];
                    const active = i === Math.min(tab, count - 1);
                    return (
                      <button key={a.id} onClick={() => setTab(i)} className="btn sm"
                        style={{ flexShrink: 0, maxWidth: 200, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                          borderColor: active ? s.chip : "var(--stroke-strong)",
                          background: active ? "rgba(108,140,255,.14)" : (a.security ? "rgba(255,60,60,.08)" : "transparent"),
                          color: active ? "#fff" : "var(--txt-dim)" }}
                        title={a.title}>{s.icon} {a.title || a.member || "Request"}</button>
                    );
                  })}
                </div>
                {cur && (
                  <div style={{ padding: 16, overflowY: "auto" }}>
                    <div className="row between" style={{ marginBottom: 8 }}>
                      <b style={{ fontSize: 13.5, color: (sevOf(cur) === "critical" || sevOf(cur) === "security") ? "var(--danger)" : undefined }}>
                        {SEV[sevOf(cur)].icon} {SEV[sevOf(cur)].label}</b>
                      <span className="pill" style={{ color: SEV[sevOf(cur)].chip }}>{cur.member}</span>
                    </div>
                    <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 6 }}>{cur.title}</div>
                    {cur.summary && <div className="faint" style={{ fontSize: 12.5, marginBottom: 8 }}>{cur.summary}</div>}
                    {cur.recommended && <div style={{ fontSize: 12.5, marginBottom: 6 }}><b>Recommended:</b> {cur.recommended}</div>}
                    {cur.fix_plan && <div className="faint" style={{ fontSize: 12, marginBottom: 8 }}><b>How:</b> {cur.fix_plan}</div>}
                    {fileList(cur)}
                    {cmdList(cur)}
                    {cur.security && <div style={{ fontSize: 11.5, color: "var(--danger)", margin: "6px 0" }}>🔴 This is a SECURITY approval — never part of “approve all”. Decide it on its own.</div>}
                    {cur.kind === "key_request" ? <KeyRequestForm req={cur} onDone={() => setItems((xs) => xs.filter((x) => x.id !== cur.id))} /> :
                    <div className="row" style={{ gap: 8, marginTop: 12 }}>
                      <button className="btn sm primary" disabled={busy === cur.id || busy === "__all__"} onClick={() => act(cur.id, true)}>✓ Approve</button>
                      <button className="btn sm danger" disabled={busy === cur.id || busy === "__all__"} onClick={() => act(cur.id, false)}>✕ Reject</button>
                    </div>}
                  </div>
                )}
              </>
            )}
          </div>
        </>,
        document.body
      )}
    </>
  );
}

/* G9b — the owner's SECURE key field. The value goes straight to the app's store (never to an agent); it is
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

/* live Azure VM connection status (lazy — checks on mount + on click) */
function VmStatus() {
  const [state, setState] = useState("checking"); // checking | ok | bad
  const [detail, setDetail] = useState("");
  const [busy, setBusy] = useState(false);        // a probe is in flight (recheck spinner)
  const fails = useRef(0);                          // consecutive failed probes
  const FAIL_THRESHOLD = 2;                         // only show "disconnected" after N misses in a row
  async function check() {
    // never drop to "checking" if we were already up — show a faint recheck instead, no flapping
    setBusy(true);
    setState((s) => (s === "ok" ? "ok" : "checking"));
    try {
      const r = await api.connectTest();
      if (r && r.ok) {
        fails.current = 0;
        setState("ok"); setDetail(`${r.vm || "django-vm"} · ${r.rg || ""}`);
      } else {
        fails.current += 1;
        const reason = r && r.reason;
        const why = reason === "az-not-found" ? "Azure CLI not found"
          : reason === "not-logged-in" ? "run `az login`"
          : (r && (r.hint || r.error)) ? String(r.hint || r.error).slice(0, 70) : "not reachable";
        // tolerate a single transient miss — only flip to "bad" after consecutive failures
        if (fails.current >= FAIL_THRESHOLD) { setState("bad"); setDetail(why); }
      }
    } catch {
      fails.current += 1;
      if (fails.current >= FAIL_THRESHOLD) { setState("bad"); setDetail("backend starting…"); }
    } finally { setBusy(false); }
  }
  useEffect(() => { check(); const t = setInterval(check, 60000); return () => clearInterval(t); }, []);
  const map = { checking: "warn", ok: "ok", bad: "bad" };
  const label = state === "checking" ? "Azure VM: checking…" : state === "ok" ? "Azure VM: connected" : "Azure VM: " + (detail || "not reachable");
  return (
    <span className="row" style={{ gap: 7, cursor: "pointer" }} title={detail} onClick={check}>
      <StatusDot state={map[state]} label={label} />
      {detail && state === "ok" && <span className="faint" style={{ fontSize: 11 }}>({detail})</span>}
      <span className="faint" style={{ fontSize: 11 }}>{busy ? "rechecking…" : "↻"}</span>
    </span>
  );
}

/* full system-status panel — preserves every indicator (connection, engine, voice, VM, model) */
function StatusPanel({ health, projects, activeCount }) {
  return (
    <div className="card pad">
      <div className="row between" style={{ marginBottom: 12 }}>
        <div>
          <div className="h-title">System status</div>
          <div className="faint" style={{ fontSize: 12 }}>Company CTO · live across all projects</div>
        </div>
        <div className="statbar">
          <div className="kpi"><b>{projects.length}</b><span>PROJECTS</span></div>
          <div className="kpi"><b style={{ color: activeCount ? "var(--ok)" : "var(--txt)" }}>{activeCount}</b><span>AGENTS LIVE</span></div>
        </div>
      </div>
      <div className="row wrap" style={{ gap: 18 }}>
        <StatusDot state={health?.ok ? "ok" : "bad"} label={"API " + (health?.ok ? "ready" : "offline")} />
        <StatusDot state={health?.engine?.includes("Claude") ? "ok" : "warn"} label={health?.engine || "engine"} />
        <StatusDot state={health?.voice_enabled ? "ok" : "warn"} label={health?.voice_enabled ? "Voice: EN Kokoro · AR Coqui" : "Voice off"} />
        <VmStatus />
        <span className="pill">main model: {health?.engine?.includes("Claude") ? "Claude Code" : (health?.ollama_model || "—")}</span>
      </div>
    </div>
  );
}

/* ONLY agents that are actually working now (the full roster lives on each project page) */
function LiveAgents({ projects, activeSet, activeTasks = {}, onOpenMember }) {
  const working = [];
  // the Project CTO is a first-class agent: when IT is the one working (planning/handling your
  // message), show + animate the CTO — not a member. (Mirrors activity key `pid:Project CTO`.)
  projects.forEach((p) => ["Project CTO", ...(p.members || [])].forEach((m) => {
    if (activeSet.has(`${p.id}:${m}`)) { const info = activeTasks[`${p.id}:${m}`] || {}; working.push({ pid: p.id, name: m, avatar: m === "Project CTO" ? "cto" : memberAvatar(p, m), project: p.name, task: info.task, phase: info.phase }); }
  }));
  return (
    <div className="card pad">
      <div className="row between" style={{ marginBottom: working.length ? 10 : 0 }}>
        <b style={{ fontSize: 13 }}>Live agents</b>
        <span className="pill" style={{ color: working.length ? "var(--ok)" : "var(--txt-dim)" }}>{working.length ? `${working.length} working now` : "all idle"}</span>
      </div>
      <div className="col" style={{ gap: 8 }}>
        {working.map((a, i) => (
          <div key={i} className="row" style={{ gap: 10, cursor: "pointer" }} onClick={() => onOpenMember(a.pid, a.name)}>
            <Avatar kind={a.avatar} name={a.name} size="sm" active />
            <div className="col" style={{ gap: 1 }}>
              <span style={{ fontSize: 12.5 }}>🗣️ {a.phase || a.name} <span className="faint">· {a.project}</span></span>
              {a.task && <span className="faint" style={{ fontSize: 10.5 }}>{a.task}</span>}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* Agent roster — EVERY actual agent the company has (across all projects + company-level), grouped by
   nature (Operational / Technical). This shows the real agents that EXIST (HubSpot, the security team, …),
   not just the template role catalog — and it is NOT limited to the currently-active ones. Scrolls
   internally so a large roster never pushes other cards off the page. */
function AgentRoster() {
  const [agents, setAgents] = useState([]);
  // RETRY so a transient failure (e.g. a brain restart) never leaves the roster stuck on "Loading agents…";
  // only replace state once we actually have agents.
  useEffect(() => {
    let alive = true;
    const load = () => api.allAgents().then((a) => { if (alive && Array.isArray(a) && a.length) setAgents(a); }).catch(() => {});
    load();
    const t = setInterval(load, 5000);
    return () => { alive = false; clearInterval(t); };
  }, []);
  // dedupe by name (an agent can appear in several projects) — keep the first, collect its projects
  const byName = {};
  for (const a of agents) {
    const k = (a.name || "").toLowerCase(); if (!k) continue;
    if (!byName[k]) byName[k] = { ...a, projects: [] };
    if (a.project && !byName[k].projects.includes(a.project)) byName[k].projects.push(a.project);
  }
  const uniq = Object.values(byName);
  const groups = [["operational", "📋 Operational"], ["technical", "🛠 Technical"]];
  return (
    <div className="card pad col" style={{ gap: 8 }}>
      <b style={{ fontSize: 13 }}>Agent roster — all agents the company has ({uniq.length})</b>
      <div className="faint" style={{ fontSize: 11 }}>Every created agent across all projects + company (from the central store, not only the active ones), grouped by nature. HubSpot is operational; security agents appear under their category.</div>
      {uniq.length === 0 && <span className="faint" style={{ fontSize: 12 }}>Loading agents…</span>}
      <div style={{ maxHeight: 300, overflowY: "auto", paddingRight: 4 }}>
        {groups.map(([g, label]) => {
          const rs = uniq.filter((a) => (a.nature || "technical") === g);
          if (!rs.length) return null;
          return (
            <div key={g} className="col" style={{ gap: 5, marginBottom: 8 }}>
              <div className="faint" style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: .4 }}>{label} · {rs.length}</div>
              <div className="row wrap" style={{ gap: 8 }}>
                {rs.map((a, i) => (
                  <span key={a.name + i} className="pill" style={{ display: "flex", gap: 6, alignItems: "center" }}
                    title={`${a.role || a.name}${a.projects.length ? " · " + a.projects.join(", ") : ""}`}>
                    <Avatar kind={a.avatar} name={a.name} size="sm" /> {a.name}
                    {a.projects[0] && <span className="faint" style={{ fontSize: 10 }}>{a.projects[0]}{a.projects.length > 1 ? ` +${a.projects.length - 1}` : ""}</span>}
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/* Company-level agents — define once, auto-added to every new project; + connectors with badges */
function CompanyAgents() {
  const [agents, setAgents] = useState([]);
  const [name, setName] = useState(""); const [role, setRole] = useState(""); const [rule, setRule] = useState("");
  const load = () => api.companyAgents().then(setAgents).catch(() => setAgents([]));
  useEffect(() => { load(); }, []);
  async function add() {
    if (!name.trim()) return;
    await api.addCompanyAgent({ name: name.trim(), role: role.trim() || name.trim(), avatar: "generic", description: role.trim(), skills: rule.trim() ? [rule.trim()] : [] });
    setName(""); setRole(""); setRule(""); load();
  }
  return (
    <div className="card pad col">
      <b style={{ fontSize: 13 }}>Company agents (native to every project)</b>
      <div className="faint" style={{ fontSize: 11 }}>Define an agent once — its role + rule — and it's added to every new project automatically.</div>
      <div className="row wrap" style={{ gap: 8 }}>
        {agents.map((a) => (
          <span key={a.name} className="pill" style={{ display: "flex", gap: 6, alignItems: "center" }} title={a.description}>
            <Avatar kind={a.avatar} name={a.name} size="sm" /> {a.name}
            <span style={{ cursor: "pointer", opacity: 0.7 }} onClick={async () => { await api.removeCompanyAgent(a.name); load(); }}>✕</span>
          </span>
        ))}
        {agents.length === 0 && <span className="faint" style={{ fontSize: 12 }}>None yet.</span>}
      </div>
      <div className="row"><input value={name} placeholder="name (e.g. SecMan)" onChange={(e) => setName(e.target.value)} />
        <input value={role} placeholder="role (e.g. Security checker)" onChange={(e) => setRole(e.target.value)} /></div>
      <div className="row"><input value={rule} placeholder="a rule for this agent (optional)" onChange={(e) => setRule(e.target.value)} />
        <button className="btn sm primary" onClick={add} title="Create a company-level agent">Create</button></div>
    </div>
  );
}

function Connectors() {
  const [cons, setCons] = useState([]);
  const [name, setName] = useState(""); const [type, setType] = useState(""); const [key, setKey] = useState("");
  const load = () => api.connectors().then(setCons).catch(() => setCons([]));
  useEffect(() => { load(); }, []);
  async function add() { if (!name.trim()) return; await api.addConnector({ name: name.trim(), type: type.trim(), apiKey: key.trim() }); setName(""); setType(""); setKey(""); load(); }
  return (
    <div className="card pad col">
      <b style={{ fontSize: 13 }}>Connectors / integrations</b>
      <div className="faint" style={{ fontSize: 11 }}>External services (Google Analytics, Klaviyo, an MCP…). Add an API key → a live status badge.</div>
      <div className="row wrap" style={{ gap: 8 }}>
        {cons.map((c) => (
          <span key={c.id} className="pill" style={{ display: "flex", gap: 6, alignItems: "center" }}>
            <span className={"dot " + (c.status === "connected" ? "ok" : "warn")} /> {c.name}
            <span className="faint" style={{ fontSize: 10 }}>{c.status}</span>
            <span style={{ cursor: "pointer", opacity: 0.7 }} onClick={async () => { await api.removeConnector(c.id); load(); }}>✕</span>
          </span>
        ))}
        {cons.length === 0 && <span className="faint" style={{ fontSize: 12 }}>None yet.</span>}
      </div>
      <div className="row"><input value={name} placeholder="name (e.g. Google Analytics)" onChange={(e) => setName(e.target.value)} />
        <input value={type} placeholder="type (e.g. analytics)" onChange={(e) => setType(e.target.value)} /></div>
      <div className="row"><input value={key} type="password" placeholder="API key (stored privately)" onChange={(e) => setKey(e.target.value)} />
        <button className="btn sm primary" onClick={add} title="Connect this integration">Connect</button></div>
    </div>
  );
}

/* =================== DASHBOARD (Company CTO) =================== */
// 🔁 RECURRING & SCHEDULED — a card you notice on open; pulses when there's new notification activity.
function RecurringCard({ projects, onOpenProject }) {
  const [unread, setUnread] = useState(0);
  const [editPid, setEditPid] = useState(null);
  const [editTask, setEditTask] = useState(null);
  useEffect(() => {
    const f = () => api.notifCount().then(setUnread).catch(() => {});
    f(); const t = setInterval(f, 12000); return () => clearInterval(t);
  }, []);
  const rec = (projects || []).filter((p) => p.periodic && p.periodic.enabled);
  if (rec.length === 0) return null;
  async function toggleEdit(pid) {
    if (editPid === pid) { setEditPid(null); setEditTask(null); return; }
    const tasks = await api.schedules(pid);
    setEditTask(tasks && tasks.length ? tasks[0] : null);
    setEditPid(pid);
  }
  return (
    <div className="card pad">
      <style>{"@keyframes odn-pulse{0%,100%{opacity:.35}50%{opacity:1}}"}</style>
      <div className="row" style={{ gap: 8, alignItems: "center", marginBottom: 8 }}>
        <b style={{ fontSize: 13 }}>🔁 Recurring & scheduled</b>
        {unread > 0 && <span style={{ width: 8, height: 8, borderRadius: 999, background: "var(--danger)", animation: "odn-pulse 1s infinite" }} />}
        <span className="faint" style={{ marginLeft: "auto", fontSize: 12 }}>{rec.length}</span>
      </div>
      <div className="sec-scroll">
      {rec.map((p) => (
        <div key={p.id} className="col" style={{ borderBottom: "1px solid var(--stroke)", paddingBottom: 3 }}>
          <div className="row" style={{ gap: 8, alignItems: "center", padding: "5px 2px" }}>
            <span style={{ fontSize: 13 }}>⏰</span>
            <span style={{ fontSize: 12.5, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", cursor: "pointer" }}
              onClick={() => onOpenProject(p.id)}>{p.name}</span>
            <span className="faint" style={{ fontSize: 11 }}>{editPid === p.id && editTask ? schedText(editTask.schedule) : scheduleLabel(p.periodic)}</span>
            <button className="btn sm ghost" style={{ padding: "1px 6px" }} title="Edit schedule (time · days · timezone)"
              onClick={() => toggleEdit(p.id)}>✎</button>
            <span className="faint" style={{ fontSize: 13, cursor: "pointer" }} onClick={() => onOpenProject(p.id)}>›</span>
          </div>
          {editPid === p.id && (editTask
            ? <ScheduleEditor task={editTask} onSaved={() => toggleEdit(p.id)} />
            : <div className="faint" style={{ fontSize: 11, padding: "2px 6px 6px" }}>No editable schedule task on this project.</div>)}
        </div>
      ))}
      </div>
    </div>
  );
}

export function Dashboard({ health, projects, activeSet, activeTasks = {}, chatScope = "company", chatTitle = "", onOpenProject, onOpenMember, onNewProject, onDeployExisting, onReload }) {
  const activeCount = activeSet.size;
  const [rightOpen, setRightOpen] = useState(true);
  return (
    <div className="col" style={{ height: "100%", gap: 16 }}>
      <StatusPanel health={health} projects={projects} activeCount={activeCount} />
      <RecurringCard projects={projects} onOpenProject={onOpenProject} />
      <div className="grid" style={{ gridTemplateColumns: rightOpen ? "minmax(0,1.1fr) 8px minmax(0,1fr)" : "1fr 8px 0", gap: 10, flex: 1, minHeight: 0 }}>
        <div className="card" style={{ minHeight: 0, overflow: "hidden" }}>
          {/* scope driven by the left sidebar's Company / CHATS section — key forces a clean remount per chat */}
          <ChatPanel key={chatScope} scope={chatScope} autospeak />
        </div>
        {/* slim divider handle between the columns — collapses/expands the right panel */}
        <div onClick={() => setRightOpen((o) => !o)} title={rightOpen ? "Hide projects panel (more space for chat)" : "Show projects panel"}
          style={{ cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", borderRadius: 6, background: "rgba(255,255,255,0.04)", fontSize: 12, color: "var(--txt-dim)" }}>
          {rightOpen ? "⟩" : "⟨"}
        </div>
        <div className="col" style={{ minHeight: 0, overflow: "auto", display: rightOpen ? "flex" : "none" }}>
          <AgentRoster />
          <LiveAgents projects={projects} activeSet={activeSet} activeTasks={activeTasks} onOpenMember={onOpenMember} />
          <CompanyAgents />
          <Connectors />
          <MonitorFeed scope="company" title="Company monitor — across all projects" />
          <div className="row between">
            <div className="h-title">Projects</div>
            <button className="btn primary" onClick={onNewProject}>＋ New project</button>
          </div>
          {projects.length === 0 && <div className="empty card pad">No projects yet. Create one or map a local folder.</div>}
          {(() => {
            // group projects under their type heading (showy, organized dashboard)
            const groups = {};
            projects.forEach((p) => { const k = p.type || "web"; (groups[k] = groups[k] || []).push(p); });
            const known = TYPE_META.filter((t) => groups[t.key]);
            const customKeys = Object.keys(groups).filter((k) => !TYPE_BY_KEY[k]);
            const order = [...known, ...customKeys.map((k) => ({ key: k, icon: "📦", label: k }))];
            const card = (p) => {
              const liveMembers = ["Project CTO", ...(p.members || [])].filter((m) => activeSet.has(`${p.id}:${m}`));
              const isPeriodic = p.periodic && p.periodic.enabled;
              return (
                <motion.div key={p.id} className="card pad" whileHover={{ y: -4 }}
                  style={{ cursor: "pointer" }} onClick={() => onOpenProject(p.id)}>
                  <div className="row between">
                    <div>
                      <div className="h-title row" style={{ fontSize: 16, gap: 7, alignItems: "center" }}>
                        <span>{(TYPE_BY_KEY[p.type] || {}).icon || "📦"}</span>{p.name}
                      </div>
                      <div className="faint" style={{ fontSize: 10.5, fontFamily: "var(--mono, monospace)", color: "var(--brand-2)" }}>id: {p.id}</div>
                    </div>
                    <div className="row" style={{ gap: 6 }}>
                      {isPeriodic && <span className="pill" style={{ color: "var(--brand-2)", borderColor: "rgba(122,240,208,.4)" }} title="Periodical — runs on a schedule, with your approval">⏰ {scheduleLabel(p.periodic)}</span>}
                      {liveMembers.length > 0 && <span className="pill blink" style={{ color: "var(--ok)", borderColor: "rgba(75,227,160,.4)" }}>● {liveMembers.length} live</span>}
                      <ProjectMenu p={p} onReload={onReload} />
                    </div>
                  </div>
                  <div className="muted" style={{ fontSize: 12, margin: "4px 0 12px", minHeight: 18 }}>
                    {(TYPE_BY_KEY[p.type] || {}).label || p.type || "Web application"}{p.stack ? " · " + p.stack : ""}
                  </div>
                  <div className="row wrap" style={{ gap: 10 }}>
                    {/* Project CTO is a FIRST-CLASS agent on EVERY project — always shown, animates when it
                        plans/assigns/reviews (activity key `${pid}:Project CTO`). */}
                    {["Project CTO", ...(p.members || [])].map((m) => {
                      const isCto = m === "Project CTO";
                      return (
                        <div key={m} className="col" style={{ alignItems: "center", gap: 2 }}>
                          <Avatar kind={isCto ? "cto" : memberAvatar(p, m)} name={m} size="sm" active={activeSet.has(`${p.id}:${m}`)} />
                          <span className="faint" style={{ fontSize: 9, color: isCto ? "var(--brand-2)" : undefined, fontWeight: isCto ? 700 : undefined }}>{isCto ? "CTO" : m}</span>
                        </div>
                      );
                    })}
                  </div>
                  {liveMembers.map((m) => {
                    const info = activeTasks[`${p.id}:${m}`] || {};
                    return (
                      <div key={"live" + m} className="row" style={{ gap: 6, marginTop: 8, fontSize: 11, color: "var(--ok)" }}>
                        <span className="blink">🗣️</span><span>{info.phase || `${m} working`}</span>
                      </div>
                    );
                  })}
                </motion.div>
              );
            };
            return order.map((t) => (
              <div key={t.key} className="col" style={{ gap: 8, marginBottom: 6 }}>
                <div className="row" style={{ gap: 7, alignItems: "center", fontSize: 12.5, color: "var(--txt-dim)", fontWeight: 700, letterSpacing: .3 }}>
                  <span style={{ fontSize: 14 }}>{t.icon}</span>{t.label}
                  <span className="faint" style={{ fontWeight: 400 }}>· {groups[t.key].length}</span>
                  <div style={{ flex: 1, height: 1, background: "var(--stroke)" }} />
                </div>
                <div className="grid cards">{groups[t.key].map(card)}</div>
              </div>
            ));
          })()}
        </div>
      </div>
    </div>
  );
}
function memberAvatar(p, name) {
  const a = (p.agentsMeta || []).find((x) => x.name === name);
  return a ? a.avatar : avatarKey(name);
}

/* three-dots project menu: Archive / Delete (delete also removes its chats) */
function ProjectMenu({ p, onReload }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ position: "relative" }} onClick={(e) => e.stopPropagation()}>
      <button className="btn sm ghost" style={{ padding: "2px 8px" }} onClick={() => setOpen((o) => !o)}>⋯</button>
      {open && (
        <div className="card" style={{ position: "absolute", right: 0, top: 28, zIndex: 30, padding: 6, minWidth: 150 }}>
          <button className="navitem" onClick={async () => { setOpen(false); await api.archiveProject(p.id); onReload && onReload(); }}>🗄 Archive</button>
          <button className="navitem" style={{ color: "var(--danger)" }}
            onClick={async () => { setOpen(false); if (window.confirm(`Delete "${p.name}" and its chats? (files on disk are kept)`)) { await api.deleteProject(p.id); onReload && onReload(); } }}>🗑 Delete</button>
        </div>
      )}
    </div>
  );
}

/* Archived projects page */
export function ArchivedView({ onOpenProject, onReload }) {
  const [list, setList] = useState([]);
  const load = () => api.archivedProjects().then(setList).catch(() => setList([]));
  useEffect(() => { load(); }, []);
  return (
    <div className="col">
      <div className="h-title">Archived projects</div>
      {list.length === 0 && <div className="empty card pad">Nothing archived.</div>}
      <div className="grid cards">
        {list.map((p) => (
          <div key={p.id} className="card pad">
            <div className="h-title" style={{ fontSize: 16 }}>{p.name}</div>
            <div className="faint" style={{ fontSize: 10.5, fontFamily: "var(--mono, monospace)", color: "var(--brand-2)" }}>id: {p.id}</div>
            <div className="muted" style={{ fontSize: 12.5, margin: "6px 0 12px", minHeight: 28 }}>{p.description || "—"}</div>
            <div className="row">
              <button className="btn sm" onClick={async () => { await api.unarchiveProject(p.id); load(); onReload && onReload(); }}>↩ Restore</button>
              <button className="btn sm danger" onClick={async () => { if (window.confirm(`Delete "${p.name}" and its chats permanently?`)) { await api.deleteProject(p.id); load(); onReload && onReload(); } }}>🗑 Delete</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* =================== PROJECT VIEW (Project CTO) =================== */
export function ProjectView({ pid, activeSet, onOpenMember, refreshSignal, kickoff }) {
  const [p, setP] = useState(null);
  const [models, setModels] = useState([]);
  const [showAdd, setShowAdd] = useState(false);
  const [editMember, setEditMember] = useState(null);
  const [showSched, setShowSched] = useState(false);
  const [showMap, setShowMap] = useState(false);
  const [plan, setPlan] = useState("");

  async function load() {
    setP(await api.project(pid));
  }
  useEffect(() => { load(); api.models().then((d) => setModels(d.models)).catch(() => {}); }, [pid, refreshSignal]);
  if (!p) return <div className="empty">Loading project…</div>;
  const stats = p.stats || { perAgent: [] };
  const hasDevOps = (p.agents || []).some((a) => a.avatar === "devops" || /devops/i.test(a.role || ""));

  return (
    <div className="grid" style={{ gridTemplateColumns: "1.05fr 1fr", gap: 18, height: "100%" }}>
      <div className="col" style={{ minHeight: 0, overflowY: "auto", paddingRight: 6 }}>
        <div className="card pad">
          <div className="row between">
            <div>
              <div className="h-title">{p.name}</div>
              <div className="faint" style={{ fontSize: 11, fontFamily: "var(--mono, monospace)", color: "var(--brand-2)" }}>id: {p.id}</div>
              <div className="faint" style={{ fontSize: 12 }}>{p.type ? `${p.type}${p.stack ? " · " + p.stack : ""}` : "Project CTO scope"}</div>
            </div>
            <div className="row wrap">
              <button className="btn sm" title="Ask the Project CTO to plan the components & build order" onClick={() => { setPlan("Thinking…"); api.plan(pid).then((d) => setPlan(d.plan)); }}>✦ Plan</button>
              <button className="btn sm" title="Schedule a task for this project (daily / interval / once)" onClick={() => setShowSched(true)}>⏰ Schedule</button>
              {hasDevOps && <button className="btn sm" title="Map a local folder to its cloud/VM destination" onClick={() => setShowMap(true)}>🗂 Map folders</button>}
              {hasDevOps && <button className="btn sm" title="Run a local→cloud sync now (.env/secrets excluded)" onClick={async () => { if (!window.confirm("Run local→cloud sync NOW? (.env/secrets excluded)")) return; setPlan("Running sync…"); try { const d = await api.syncRun(pid); setPlan(d.result); } catch { setPlan("Backend offline"); } }}>⇅ Sync</button>}
              {hasDevOps && <button className="btn sm danger" title="Request a deploy — preview the exact rsync + commands, then approve to run it (watchable + stoppable)" onClick={async () => { if (!window.confirm("Request a deploy to the VM? You'll preview the exact steps and must APPROVE before anything runs.")) return; setPlan("Requesting deploy…"); try { const d = await api.requestDeploy(pid); setPlan(d && d.error ? `⚠️ ${d.error}` : "✅ Deploy requested — approve it in the Approval Center (top of screen) to start. You'll then see it run live below."); } catch { setPlan("Backend offline"); } }}>🚀 Deploy</button>}
            </div>
          </div>
          {plan && <div className="card pad msg" style={{ marginTop: 12, fontSize: 13 }}><Markdown text={plan} /></div>}
        </div>

        <LiveOperation pid={pid} />

        <div className="card pad">
          <div className="row between" style={{ marginBottom: 10 }}>
            <b>Team members</b>
            <button className="btn sm primary" title="Hire a new team member — describe the role, the CTO suggests a name" onClick={() => setShowAdd(true)}>＋ Add member</button>
          </div>
          <div className="grid" style={{ gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)", gap: 10 }}>
            {/* Project CTO — the orchestrator: a FIRST-CLASS agent on every project, always shown with its
                own icon, and its avatar ANIMATES (active) whenever it is planning/assigning/reviewing
                (activity key `${pid}:Project CTO`). Not removable/editable — it is the manager. */}
            {(() => {
              const ctoLive = activeSet.has(`${pid}:Project CTO`);
              return (
                <motion.div key="__cto" className="card pad" whileHover={{ y: -3 }}
                  style={{ padding: 12, borderColor: "rgba(122,240,208,.35)" }}>
                  <div className="row" style={{ gap: 10 }}>
                    <Avatar kind="cto" active={ctoLive} />
                    <div className="col" style={{ gap: 3, flex: 1, minWidth: 0 }}>
                      <div className="row between"><b style={{ fontSize: 13.5 }}>Project CTO</b>
                        {ctoLive
                          ? <span className="pill blink" style={{ color: "var(--ok)" }}>working</span>
                          : <span className="pill" style={{ color: "var(--brand-2)", borderColor: "rgba(122,240,208,.4)" }}>orchestrator</span>}
                      </div>
                      <div className="faint" style={{ fontSize: 11 }}>Plans the build, assigns every member, reviews their work</div>
                    </div>
                  </div>
                </motion.div>
              );
            })()}
            {(p.agents || []).map((a) => {
              const live = activeSet.has(`${pid}:${a.name}`);
              const st = stats.perAgent.find((s) => s.name === a.name) || { percent: 0, invocations: 0 };
              return (
                <motion.div key={a.name} className="card pad" whileHover={{ y: -3 }} style={{ cursor: "pointer", padding: 12 }}
                  onClick={() => onOpenMember(pid, a.name)}>
                  <div className="row" style={{ gap: 10 }}>
                    <Avatar kind={a.avatar} name={a.name} active={live} />
                    <div className="col" style={{ gap: 3, flex: 1, minWidth: 0 }}>
                      <div className="row between"><b style={{ fontSize: 13.5 }}>{a.name}</b>
                        <span className="row" style={{ gap: 6, alignItems: "center" }}>
                          {live
                            ? <span className="pill blink" style={{ color: "var(--ok)" }}>working</span>
                            : st.invocations > 0
                              ? <span className="pill" style={{ color: "var(--ok)", borderColor: "rgba(0,200,120,.35)" }}>✓ done</span>
                              : <span className="pill faint">idle</span>}
                          <span title={`Edit ${a.name}'s resources, dependencies & env`} style={{ cursor: "pointer", opacity: 0.55, fontSize: 12 }}
                            onClick={(e) => { e.stopPropagation(); setEditMember(a.name); }}>✎</span>
                          <span title={`Remove ${a.name} from this project's team`} style={{ cursor: "pointer", opacity: 0.55, fontSize: 12 }}
                            onClick={async (e) => { e.stopPropagation(); if (window.confirm(`Remove ${a.name} from the team? (You can add a member back anytime.)`)) { try { await api.removeAgent(pid, a.name); } catch {} load(); } }}>✕</span>
                        </span></div>
                      <div className="faint" style={{ fontSize: 11 }}>{a.role}</div>
                      <UsageBar percent={st.percent} color={COLOR[a.avatar] || "var(--brand)"} />
                      <div className="faint" style={{ fontSize: 10.5 }}>{st.invocations} runs · {st.percent}%</div>
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>

        <TeamRun pid={pid} onActivity={load} initialGoal={p.description} autostart={kickoff} />
        <SchedulesPanel pid={pid} onAdd={() => setShowSched(true)} />
        <ProjectRules pid={pid} />
        <FlowRail pid={pid} />
        <MonitorFeed scope={`project:${pid}`} title="Team monitor — what members are doing" />
      </div>

      <div className="card" style={{ minHeight: 0, overflow: "hidden" }}>
        <ChatPanel scope={`project:${pid}`} autospeak onActivity={() => setTimeout(load, 400)}
          activeNow={(p.agents || []).some((a) => activeSet.has(`${pid}:${a.name}`))} />
      </div>

      <AddMemberModal pid={pid} open={showAdd} onClose={() => setShowAdd(false)} onAdded={load} />
      <EditMemberModal pid={pid} member={editMember} open={!!editMember} onClose={() => setEditMember(null)} onSaved={load} />
      <ScheduleModal pid={pid} open={showSched} onClose={() => setShowSched(false)} onSaved={load} agents={p.agents || []} />
      <MapModal pid={pid} open={showMap} onClose={() => setShowMap(false)} onSaved={load} />
    </div>
  );
}

function fmtElapsed(ms) {
  const s = Math.floor(ms / 1000), m = Math.floor(s / 60);
  return `${m}:${String(s % 60).padStart(2, "0")}`;
}

/* LiveOperation — the ONE place you SEE a long task (deploy/sync) as it happens and can STOP it.
   Polls the server's single operation record: shows every command + output as a live log, a
   working indicator, a Stop button, and — when it ends — a clear finish/stop banner + card.
   Because the operation lives on the SERVER, this keeps showing the same run after you navigate
   away and come back; nothing is tied to this component's lifetime. */
export function LiveOperation({ pid }) {
  const [op, setOp] = useState(null);
  const [busy, setBusy] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [ans, setAns] = useState({});       // answers the owner types to a blocked operation
  const logRef = useRef(null);
  const lastTerminal = useRef("");      // op id we've already announced, so the card fires once

  useEffect(() => {
    let alive = true;
    async function tick() {
      try {
        const latest = await api.latestOperation(pid);
        if (!alive) return;
        if (!latest || !latest.id) { setOp(null); return; }
        // pull the full record (with log) for the active/most-recent operation
        const full = await api.operation(latest.id);
        if (!alive || !full || !full.id) return;
        setOp(full);
        // fire the finish/stop card exactly once when it reaches a terminal state
        if (full.state !== "running" && lastTerminal.current !== full.id) {
          lastTerminal.current = full.id;
          const ok = full.state === "done";
          emitOutcome(ok ? "success" : "problem",
            ok ? "Deploy finished" : full.state === "stopped" ? "Deploy stopped"
              : full.state === "blocked" ? "Deploy needs your input" : "Deploy had issues",
            full.summary || "");
        }
      } catch {}
    }
    tick();
    const iv = setInterval(tick, 1500);
    return () => { alive = false; clearInterval(iv); };
  }, [pid]);

  useEffect(() => { logRef.current && (logRef.current.scrollTop = logRef.current.scrollHeight); }, [op && op.log && op.log.length]);

  if (!op || !op.id) return null;
  const running = op.state === "running";
  const blocked = op.state === "blocked";
  const ended = op.ended ? op.ended * 1000 : Date.now();
  const elapsed = fmtElapsed(ended - op.started * 1000);
  const stateColor = running ? "var(--ok)" : op.state === "done" ? "var(--ok)"
    : op.state === "stopped" ? "var(--warn, #e0a500)" : blocked ? "var(--warn, #e0a500)" : "var(--danger)";
  const stateLabel = running ? `running… ${elapsed}` : op.state === "done" ? `✅ done · ${elapsed}`
    : op.state === "stopped" ? `⏹ stopped · ${elapsed}` : blocked ? `⛔ needs your input` : `⚠️ issues · ${elapsed}`;
  const okc = (op.steps || []).filter((s) => s.ok).length;

  async function stop() {
    setBusy(true);
    try { await api.stopOperation(op.id); } catch {}
    setBusy(false);
  }
  async function cont() {
    setBusy(true);
    try {
      lastTerminal.current = "";
      if (blocked && (op.needs || []).length) {
        // SMART CONTINUE: send the owner's answers; the backend corrects the operation and resumes
        await api.provideOperation(op.id, ans);
        setAns({});
      } else {
        await api.runDeployOperation(pid);
      }
    } catch {}
    setBusy(false);
  }

  return (
    <div className="card pad col" style={{ border: `1.5px solid ${running ? "rgba(0,200,120,.5)" : op.state === "done" ? "rgba(0,200,120,.4)" : op.state === "stopped" ? "rgba(224,165,0,.5)" : "rgba(255,90,90,.55)"}` }}>
      <div className="row between">
        <b style={{ fontSize: 13 }}>⚙️ {op.title || "Operation"}</b>
        <span className="row" style={{ gap: 8, alignItems: "center" }}>
          <span className={"pill" + (running ? " blink" : "")} style={{ color: stateColor, borderColor: stateColor }}>{stateLabel}</span>
          {running
            ? <button className="btn sm danger" disabled={busy} title="Stop this operation cleanly after the current step" onClick={stop}>{busy ? "stopping…" : "⏹ Stop"}</button>
            : <>
                <button className="btn sm primary" disabled={busy} title="Run it again (e.g. after fixing folders or starting the VM)" onClick={cont}>{busy ? "…" : (blocked ? "▶ Continue" : "▶ Run again")}</button>
                <button className="iconbtn" style={{ width: 26, height: 26 }} title={collapsed ? "Show log" : "Hide log"} onClick={() => setCollapsed((c) => !c)}>{collapsed ? "▸" : "▾"}</button>
              </>}
        </span>
      </div>
      {blocked && (
        <div className="card pad col" style={{ marginTop: 8, gap: 8, borderColor: "rgba(224,165,0,.5)", background: "rgba(224,165,0,.07)" }}>
          <div style={{ fontSize: 12.5, color: "var(--txt)" }}>⛔ {op.question || op.summary || "Needs your input to continue."}</div>
          {(op.needs || []).map((n) => (
            <div key={n.key} className="col" style={{ gap: 3 }}>
              <label style={{ fontSize: 11 }}>{n.label || n.key}</label>
              <div className="row" style={{ gap: 6 }}>
                <input value={ans[n.key] || ""} placeholder={n.placeholder || ""} style={{ flex: 1, fontSize: 12 }}
                  onChange={(e) => setAns((a) => ({ ...a, [n.key]: e.target.value }))} />
                {window.odin && window.odin.pickFolder && (n.key || "").startsWith("local_") && (
                  <button className="btn sm" title="Browse for the folder" onClick={async () => { const p = await window.odin.pickFolder(); if (p) setAns((a) => ({ ...a, [n.key]: p })); }}>🗂</button>
                )}
              </div>
            </div>
          ))}
          <div className="faint" style={{ fontSize: 10.5 }}>Your answer is used to correct the operation, then it continues from here.</div>
        </div>
      )}

      {/* step chips — a quick at-a-glance of what's done vs failed */}
      {(op.steps || []).length > 0 && (
        <div className="row wrap" style={{ gap: 6, marginTop: 8 }}>
          {op.steps.map((s, i) => (
            <span key={i} className="pill" style={{ fontSize: 10.5, color: s.ok ? "var(--ok)" : "var(--danger)", borderColor: s.ok ? "rgba(0,200,120,.35)" : "rgba(255,90,90,.4)" }}
              title={s.detail || ""}>{s.ok ? "✓" : "✕"} {s.name}</span>
          ))}
        </div>
      )}

      {!collapsed && (
        <div ref={logRef} className="mono" style={{ marginTop: 10, maxHeight: 220, overflowY: "auto", fontSize: 11.5, lineHeight: 1.5,
          background: "rgba(0,0,0,.28)", borderRadius: 8, padding: "8px 10px", whiteSpace: "pre-wrap" }}>
          {(op.log || []).length === 0
            ? <span className="faint">waiting for the first step…</span>
            : op.log.map((l, i) => <div key={i}>{l.line}</div>)}
        </div>
      )}

      {!running && op.summary && (
        <div style={{ marginTop: 8, fontSize: 12.5, color: stateColor }}>{op.summary} ({okc}/{(op.steps || []).length} steps ok)</div>
      )}
    </div>
  );
}

function TeamRun({ pid, onActivity, initialGoal = "", autostart = false }) {
  const [goal, setGoal] = useState(initialGoal);
  const [running, setRunning] = useState(false);
  const [steps, setSteps] = useState([]);
  const [log, setLog] = useState([]);
  const [current, setCurrent] = useState(null);
  const [doneSet, setDoneSet] = useState([]);     // members that have finished
  const [stepTotal, setStepTotal] = useState(0);  // total steps in the plan
  const [finished, setFinished] = useState(false);// whole run is done
  const [failed, setFailed] = useState("");       // error text if it failed
  const [elapsed, setElapsed] = useState(0);      // ms since start (visibly alive)
  const startRef = useRef(0);
  const logRef = useRef(null);
  const started = useRef(false);
  useEffect(() => { logRef.current && (logRef.current.scrollTop = logRef.current.scrollHeight); }, [log]);
  useEffect(() => { if (initialGoal) setGoal(initialGoal); }, [initialGoal]);
  // tick a live timer while running so the user always sees it's alive (not frozen)
  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setElapsed(Date.now() - startRef.current), 1000);
    return () => clearInterval(t);
  }, [running]);
  // when a project is just created, the team starts working automatically (you SEE it live)
  useEffect(() => {
    if (autostart && initialGoal && !started.current) { started.current = true; run(initialGoal); }
  }, [autostart, initialGoal]);

  function run(g) {
    const gg = (g != null ? g : goal).trim();
    if (!gg || running) return;
    startRef.current = Date.now();
    setRunning(true); setSteps([]); setLog([]); setCurrent(null);
    setDoneSet([]); setStepTotal(0); setFinished(false); setFailed(""); setElapsed(0);
    streamOrchestrate(pid, gg, {
      plan: (d) => { setSteps(d.steps || []); setStepTotal((d.steps || []).length); },
      delegate: (d) => { setCurrent(d.to); setStepTotal((t) => d.of || t); setLog((l) => [...l, { t: `→ ${d.to}  (step ${d.step}/${d.of}): ${d.task}`, head: true }]); onActivity && onActivity(); },
      status: (d) => setLog((l) => [...l.slice(-60), { t: d.text }]),
      step_done: (d) => { setDoneSet((s) => s.includes(d.member) ? s : [...s, d.member]); setLog((l) => [...l, { t: `✓ ${d.member} finished`, done: true }]); onActivity && onActivity(); },
      done: (d) => {
        setRunning(false); setCurrent(null); setFinished(true); setElapsed(Date.now() - startRef.current); onActivity && onActivity();
        const okAll = !(d && d.ok === false);
        const mins = fmtElapsed(Date.now() - startRef.current);
        emitOutcome(okAll ? "success" : "problem",
          okAll ? "Task finished successfully" : "Task finished with issues",
          okAll ? `The team completed all ${stepTotal || doneSet.length} step(s) in ${mins}. Open the project chat for the full report.`
                : `The run completed in ${mins}, but some parts still have issues. Open the project to review what's flagged.`);
      },
      error: (d) => {
        setRunning(false); setCurrent(null); setFailed(d.text || "error"); setLog((l) => [...l, { t: "⚠️ " + (d.text || "error") }]);
        emitOutcome("problem", "Task stopped before finishing", (d.text || "It hit an error and stopped.") + " — press Go to retry.");
      },
    });
  }

  const pct = stepTotal > 0 ? Math.round((doneSet.length / stepTotal) * 100) : 0;
  const totalSteps = stepTotal || doneSet.length;

  return (
    <div className="card pad col">
      <div className="row between">
        <b style={{ fontSize: 13 }}>Build with the team</b>
        {running && <span className="pill blink" style={{ color: "var(--ok)" }}>team working… {fmtElapsed(elapsed)}</span>}
        {finished && <span className="pill" style={{ color: "var(--ok)", borderColor: "rgba(0,200,120,.4)" }}>✅ finished · {fmtElapsed(elapsed)}</span>}
        {failed && <span className="pill" style={{ color: "var(--danger)", borderColor: "rgba(255,107,129,.4)" }}>⚠️ stopped</span>}
      </div>
      <div className="faint" style={{ fontSize: 11 }}>Describe a goal; the project CTO plans it, assigns each member, and they work in turn — you watch it below.</div>
      <div className="row">
        <input value={goal} placeholder="what should the team build/do next?" title="Type a goal; the CTO plans it and assigns each member in turn"
          onChange={(e) => setGoal(e.target.value)} onKeyDown={(e) => e.key === "Enter" && run()} />
        <button className="btn primary" title="Start the team on this goal — CTO plans, briefs each member, reviews their work" onClick={() => run()} disabled={running}>{running ? "Working…" : "Go"}</button>
      </div>

      {/* progress bar + step counter — always tells you where you are */}
      {(running || finished || stepTotal > 0) && (
        <div className="col" style={{ gap: 4, marginTop: 6 }}>
          <div className="row between" style={{ fontSize: 11.5 }}>
            <span className="faint">{finished ? "All steps done" : current ? `Working: ${current}` : "Planning…"}</span>
            <span className="faint">{stepTotal > 0 ? `${doneSet.length}/${stepTotal} done` : ""}{running ? ` · ${fmtElapsed(elapsed)}` : ""}</span>
          </div>
          <div style={{ height: 7, borderRadius: 4, background: "var(--stroke)", overflow: "hidden" }}>
            <div style={{ height: "100%", width: `${finished ? 100 : pct}%`, background: failed ? "var(--danger)" : "var(--ok)", transition: "width .4s ease" }} />
          </div>
        </div>
      )}

      {/* the plan as a row of members; each goes green when its step is done */}
      {steps.length > 0 && (
        <div className="flow" style={{ marginTop: 6 }}>
          {steps.map((s, i) => {
            const isDone = doneSet.includes(s.member);
            const isNow = current === s.member && !isDone;
            const col = isDone ? "var(--ok)" : isNow ? "var(--brand-2)" : "var(--stroke-strong)";
            return (
              <span key={i} className="row" style={{ gap: 6 }}>
                <span className="node" style={{ borderColor: col, color: isDone ? "var(--ok)" : isNow ? "var(--brand-2)" : "var(--txt)" }}>
                  {isDone ? "✓ " : isNow ? "● " : ""}{s.member}
                </span>
                {i < steps.length - 1 && <span className="arrow">→</span>}
              </span>
            );
          })}
        </div>
      )}

      {finished && (
        <div className="row" style={{ gap: 8, marginTop: 8, padding: "8px 10px", borderRadius: 8, background: "rgba(0,200,120,.08)", border: "1px solid rgba(0,200,120,.3)" }}>
          <span style={{ fontSize: 16 }}>✅</span>
          <div className="col" style={{ gap: 1 }}>
            <b style={{ fontSize: 12.5, color: "var(--ok)" }}>Done — the team completed all {totalSteps} step{totalSteps === 1 ? "" : "s"}.</b>
            <span className="faint" style={{ fontSize: 11 }}>Finished in {fmtElapsed(elapsed)}. See the chat on the right for what each member delivered.</span>
          </div>
        </div>
      )}
      {failed && (
        <div className="row" style={{ gap: 8, marginTop: 8, padding: "8px 10px", borderRadius: 8, background: "rgba(255,107,129,.08)", border: "1px solid rgba(255,107,129,.3)" }}>
          <span style={{ fontSize: 16 }}>⚠️</span>
          <div className="col" style={{ gap: 1 }}>
            <b style={{ fontSize: 12.5, color: "var(--danger)" }}>Stopped before finishing.</b>
            <span className="faint" style={{ fontSize: 11 }}>{failed} — press Go to retry.</span>
          </div>
        </div>
      )}

      {log.length > 0 && (
        <div ref={logRef} style={{ maxHeight: 160, overflow: "auto", fontSize: 12, marginTop: 6, display: "flex", flexDirection: "column", gap: 3 }}>
          {log.map((l, i) => (
            <div key={i} style={{ color: l.done ? "var(--ok)" : l.head ? "var(--brand-2)" : "var(--txt-dim)", fontWeight: l.head ? 600 : 400 }}>{l.t}</div>
          ))}
        </div>
      )}
    </div>
  );
}

// Monitoring feed (#14): higher scope sees what lower scopes are doing (company→projects→members).
function MonitorFeed({ scope, title }) {
  const [feed, setFeed] = useState([]);
  useEffect(() => {
    const load = () => api.scopeSummary(scope).then((d) => setFeed((d.feed || []).slice(-60).reverse())).catch(() => {});
    load(); const t = setInterval(load, 3000); return () => clearInterval(t);
  }, [scope]);
  return (
    <div className="card pad">
      <b style={{ fontSize: 13 }}>{title}</b>
      {feed.length === 0 && <div className="faint" style={{ fontSize: 12, marginTop: 6 }}>No activity yet.</div>}
      <div className="col" style={{ gap: 4, marginTop: 8, maxHeight: 220, overflowY: "auto" }}>
        {feed.map((f, i) => (
          <div key={i} className="faint" style={{ fontSize: 11.5 }}>• {f.event}</div>
        ))}
      </div>
    </div>
  );
}

// Per-agent activity log (#13): every task this member received + did, as a timeline.
function MemberActivityLog({ pid, name }) {
  const [chats, setChats] = useState([]);
  useEffect(() => {
    const s = `member:${pid}:${name}`;
    const load = () => api.scopeChats(s).then(setChats).catch(() => {});
    load(); const t = setInterval(load, 3000); return () => clearInterval(t);
  }, [pid, name]);
  return (
    <div className="card pad col">
      <b style={{ fontSize: 13 }}>Activity log ({chats.length})</b>
      {chats.length === 0 && <div className="faint" style={{ fontSize: 12 }}>No tasks received yet.</div>}
      {chats.map((c) => (
        <div key={c.id} className="row between" style={{ fontSize: 12 }}>
          <span>{c.title}</span><span className="faint">{c.count} msgs</span>
        </div>
      ))}
    </div>
  );
}

// Per-project custom rules — owner can ADD / EDIT / DISCARD live; the CTO & team follow them.
// These are ADDITIVE constraints; they do not replace the CTO's task-dividing or agent-creation.
function ProjectRules({ pid }) {
  const [rules, setRules] = useState([]);
  const [draft, setDraft] = useState("");
  const load = () => api.rules(pid).then(setRules).catch(() => setRules([]));
  useEffect(() => { load(); }, [pid]);
  async function add() { if (draft.trim()) { await api.addRule(pid, draft.trim()); setDraft(""); load(); } }
  return (
    <div className="card pad col">
      <b style={{ fontSize: 13 }}>Project rules</b>
      <div className="faint" style={{ fontSize: 11 }}>Custom rules the CTO & team follow for THIS project — add or discard anytime.</div>
      {rules.map((r) => (
        <div key={r.id} className="row between" style={{ fontSize: 12 }}>
          <input defaultValue={r.rule} style={{ fontSize: 12, padding: "4px 8px" }}
            onBlur={(e) => { if (e.target.value.trim() && e.target.value !== r.rule) api.updateRule(pid, r.id, e.target.value.trim()).then(load); }} />
          <button className="btn sm ghost" style={{ color: "var(--danger)", padding: "2px 7px" }} title="Discard this rule"
            onClick={async () => { await api.removeRule(pid, r.id); load(); }}>✕</button>
        </div>
      ))}
      <div className="row">
        <input value={draft} placeholder="e.g. never expose .env; always use Tailwind tokens"
          onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => e.key === "Enter" && add()} />
        <button className="btn sm" onClick={add} title="Add a custom rule for this project">Add</button>
      </div>
    </div>
  );
}

// Common timezones — Egypt (Africa/Cairo) is the DEFAULT.
const TZS = ["Africa/Cairo", "Europe/London", "America/New_York", "America/Los_Angeles", "Europe/Berlin",
  "Asia/Dubai", "Asia/Riyadh", "Asia/Kolkata", "Asia/Singapore", "Australia/Sydney", "UTC"];
const WD = [["Mon", 0], ["Tue", 1], ["Wed", 2], ["Thu", 3], ["Fri", 4], ["Sat", 5], ["Sun", 6]];

function schedText(s) {
  if (!s) return "—";
  if (s.kind === "calendar") {
    const times = (s.times && s.times.length ? s.times : [s.hhmm || "09:00"]).join(", ");
    let when = "every day";
    if (s.weekdays && s.weekdays.length) when = "weekly " + s.weekdays.map((d) => WD[d][0]).join("/");
    else if (s.monthdays && s.monthdays.length) when = "monthly on " + s.monthdays.join(",");
    return `${when} at ${times} (${s.tz || "Africa/Cairo"})`;
  }
  return s.kind === "daily" ? `daily ${s.hhmm} (${s.tz || "Africa/Cairo"})` : s.kind === "interval" ? `every ${s.seconds}s` : "once";
}

// Inline editor: change time(s), add multiple times, pick daily/weekly/monthly + timezone. Saves to the brain.
function ScheduleEditor({ task, onSaved }) {
  const s0 = task.schedule || {};
  const [cadence, setCadence] = useState(s0.weekdays?.length ? "weekly" : s0.monthdays?.length ? "monthly" : "daily");
  const [times, setTimes] = useState(s0.times && s0.times.length ? s0.times : [s0.hhmm || "09:00"]);
  const [tz, setTz] = useState(s0.tz || "Africa/Cairo");
  const [weekdays, setWeekdays] = useState(s0.weekdays || []);
  const [monthdays, setMonthdays] = useState((s0.monthdays || []).join(",") || "1");
  const [busy, setBusy] = useState(false);
  const setTime = (i, v) => setTimes(times.map((t, k) => (k === i ? v : t)));
  async function save() {
    setBusy(true);
    const sched = { kind: "calendar", times: times.filter(Boolean), tz };
    if (cadence === "weekly") sched.weekdays = weekdays.length ? weekdays : [0, 1, 2, 3, 4, 5, 6];
    if (cadence === "monthly") sched.monthdays = monthdays.split(",").map((x) => parseInt(x.trim())).filter((x) => x >= 1 && x <= 31);
    await api.updateSchedule(task.id, sched);
    setBusy(false); onSaved && onSaved();
  }
  return (
    <div className="col" style={{ gap: 7, padding: "8px 4px", borderTop: "1px solid var(--stroke)" }}>
      <div className="row" style={{ gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        <span className="faint" style={{ fontSize: 11 }}>Repeat</span>
        {["daily", "weekly", "monthly"].map((c) => (
          <button key={c} className={"btn sm" + (cadence === c ? " primary" : " ghost")} style={{ fontSize: 11 }} onClick={() => setCadence(c)}>{c}</button>
        ))}
        <span className="faint" style={{ fontSize: 11, marginLeft: 6 }}>Timezone</span>
        <select value={tz} onChange={(e) => setTz(e.target.value)} style={{ fontSize: 11 }}>
          {TZS.map((z) => <option key={z} value={z}>{z}{z === "Africa/Cairo" ? " (Egypt · default)" : ""}</option>)}
        </select>
      </div>
      {cadence === "weekly" && (
        <div className="row" style={{ gap: 4, flexWrap: "wrap" }}>
          {WD.map(([lbl, d]) => (
            <button key={d} className={"btn sm" + (weekdays.includes(d) ? " primary" : " ghost")} style={{ fontSize: 10.5, padding: "2px 7px" }}
              onClick={() => setWeekdays(weekdays.includes(d) ? weekdays.filter((x) => x !== d) : [...weekdays, d])}>{lbl}</button>
          ))}
        </div>
      )}
      {cadence === "monthly" && (
        <div className="row" style={{ gap: 6, alignItems: "center" }}>
          <span className="faint" style={{ fontSize: 11 }}>Day(s) of month</span>
          <input value={monthdays} onChange={(e) => setMonthdays(e.target.value)} placeholder="1,15" style={{ width: 90, fontSize: 11 }} />
        </div>
      )}
      <div className="row" style={{ gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        <span className="faint" style={{ fontSize: 11 }}>Time(s)</span>
        {times.map((t, i) => (
          <span key={i} className="row" style={{ gap: 2 }}>
            <input type="time" value={t} onChange={(e) => setTime(i, e.target.value)} style={{ fontSize: 11 }} />
            {times.length > 1 && <button className="btn sm ghost" style={{ padding: "0 5px", color: "var(--danger)" }} onClick={() => setTimes(times.filter((_, k) => k !== i))}>✕</button>}
          </span>
        ))}
        <button className="btn sm ghost" style={{ fontSize: 11 }} onClick={() => setTimes([...times, "12:00"])}>＋ time</button>
      </div>
      <div className="row" style={{ gap: 6 }}>
        <button className="btn sm primary" disabled={busy} onClick={save}>{busy ? "Saving…" : "Save schedule"}</button>
        <button className="btn sm ghost" style={{ color: "var(--ok)" }} title="Test — run this task now" onClick={() => api.runNow(task.pid, "", "")}>▶ Test now</button>
      </div>
    </div>
  );
}

// VISIBLE list of scheduled/periodic tasks for this project (see · edit time/cadence/tz · test · remove).
function SchedulesPanel({ pid, onAdd }) {
  const [tasks, setTasks] = useState([]);
  const [editing, setEditing] = useState(null);
  const load = () => api.schedules(pid).then(setTasks).catch(() => setTasks([]));
  useEffect(() => { load(); const t = setInterval(load, 10000); return () => clearInterval(t); }, [pid]);
  return (
    <div className="card pad col">
      <div className="row between"><b style={{ fontSize: 13 }}>⏰ Scheduled tasks ({tasks.length})</b>
        <button className="btn sm" onClick={onAdd} title="Schedule a recurring/periodic task">＋ Schedule</button></div>
      {tasks.length === 0 && <div className="faint" style={{ fontSize: 12 }}>None yet — schedule one (e.g. a security agent that runs nightly).</div>}
      <div className="sec-scroll col" style={{ gap: 6 }}>
      {tasks.map((t) => (
        <div key={t.id} className="col" style={{ gap: 2, borderBottom: "1px solid var(--stroke)", paddingBottom: 4 }}>
          <div className="row between" style={{ fontSize: 12 }}>
            <div className="col" style={{ gap: 1 }}>
              <span>{t.title}</span>
              <span className="faint" style={{ fontSize: 10.5 }}>{schedText(t.schedule)} · {t.runs || 0} runs{t.assignee ? ` · ${t.assignee}` : ""}</span>
            </div>
            <div className="row" style={{ gap: 4 }}>
              <button className="btn sm ghost" style={{ padding: "2px 7px" }} title="Edit schedule (time · days · timezone)" onClick={() => setEditing(editing === t.id ? null : t.id)}>✎</button>
              <button className="btn sm ghost" style={{ color: "var(--danger)", padding: "2px 7px" }} title="Remove" onClick={async () => { await api.deleteSchedule(t.id); load(); }}>✕</button>
            </div>
          </div>
          {editing === t.id && <ScheduleEditor task={t} onSaved={() => { setEditing(null); load(); }} />}
        </div>
      ))}
      </div>
    </div>
  );
}

function FlowRail({ pid }) {
  const [flow, setFlow] = useState([]);
  useEffect(() => {
    const t = setInterval(() => api.activity(pid).then((d) => setFlow(d.flow || [])).catch(() => {}), 2500);
    return () => clearInterval(t);
  }, [pid]);
  const handoffs = flow.filter((f) => f.type === "handoff").slice(-4);
  return (
    <div className="card pad">
      <b style={{ fontSize: 13 }}>Live flow</b>
      <div className="flow" style={{ marginTop: 10 }}>
        {handoffs.length === 0 && <span className="faint" style={{ fontSize: 12 }}>No active hand-offs.</span>}
        {handoffs.map((f, i) => (
          <span key={i} className="row" style={{ gap: 8 }}>
            <span className="node">{f.from}</span><span className="arrow">→</span><span className="node">{f.to}</span>
          </span>
        ))}
      </div>
    </div>
  );
}

/* =================== MEMBER VIEW (team member) =================== */
export function MemberView({ pid, name, activeSet, activeTasks = {} }) {
  const [a, setA] = useState(null);
  const [models, setModels] = useState([]);
  const [rule, setRule] = useState("");
  const live = activeSet.has(`${pid}:${name}`);
  const info = activeTasks[`${pid}:${name}`];
  const currentTask = info && (info.task || "");
  const currentPhase = info && info.phase;

  async function load() { setA(await api.agent(pid, name)); }
  useEffect(() => { load(); api.models().then((d) => setModels(d.models)).catch(() => {}); }, [pid, name]);
  if (!a) return <div className="empty">Loading member…</div>;

  return (
    <div className="grid" style={{ gridTemplateColumns: "360px 1fr", gap: 18, height: "100%" }}>
      <div className="col" style={{ minHeight: 0, overflow: "auto" }}>
        <div className="card pad col" style={{ alignItems: "center", textAlign: "center" }}>
          <Avatar kind={a.avatar} name={a.name} size="lg" active={live} />
          <div className="h-title" style={{ marginTop: 10 }}>{a.name}</div>
          <div className="faint">{a.role}</div>
          {live ? <span className="pill blink" style={{ color: "var(--ok)", marginTop: 6 }}>● working now</span>
                : <span className="pill" style={{ marginTop: 6 }}>idle</span>}
          {live && currentTask && (
            <div className="card pad" style={{ marginTop: 10, width: "100%", borderColor: "rgba(75,227,160,.35)" }}>
              <div className="faint" style={{ fontSize: 10.5, letterSpacing: 1 }}>{(currentPhase || "WORKING ON NOW").toUpperCase()}</div>
              <div style={{ fontSize: 13, marginTop: 4 }}>{currentTask}</div>
            </div>
          )}
          <div className="muted" style={{ fontSize: 12.5, marginTop: 10 }}>{a.description}</div>
        </div>

        <div className="card pad col">
          <label>Model for this member (Phase 5)</label>
          <select defaultValue={a.model || ""} onChange={(e) => api.setModel(`member:${pid}:${name}`, e.target.value)}>
            <option value="">Inherit project / main</option>
            {models.map((m) => <option key={m.id} value={m.id}>{m.label} · {m.cost}</option>)}
          </select>
          <div className="faint" style={{ fontSize: 11 }}>Lighter local models save credits; use paid only where needed.</div>
        </div>

        <div className="card pad col">
          <b style={{ fontSize: 13 }}>Skills & restrictions</b>
          <div className="faint" style={{ fontSize: 12 }}>Skills: {(a.skills || []).join(", ") || "—"}</div>
          <div className="faint" style={{ fontSize: 12 }}>Restrictions: {(a.restrictions || []).join(", ") || "—"}</div>
          <b style={{ fontSize: 13, marginTop: 8 }}>Custom rules ({(a.rules || []).length})</b>
          {(a.rules || []).map((r, i) => <div key={i} className="muted" style={{ fontSize: 12 }}>• {r.rule}</div>)}
          <div className="row" style={{ marginTop: 6 }}>
            <input placeholder="Save a new permanent rule…" value={rule} title="A rule this member always follows from now on" onChange={(e) => setRule(e.target.value)} />
            <button className="btn sm" title="Save this as a permanent rule for this member" onClick={async () => { if (rule.trim()) { await api.saveRule(pid, name, rule.trim()); setRule(""); load(); } }}>Save</button>
          </div>
        </div>

        <MemberActivityLog pid={pid} name={name} />
      </div>

      <div className="card" style={{ minHeight: 0, overflow: "hidden" }}>
        <div className="row" style={{ padding: "10px 14px", borderBottom: "1px solid var(--stroke)", gap: 8 }}>
          <span className="pill" style={{ color: "var(--warn)" }}>Interrupt chat</span>
          <span className="faint" style={{ fontSize: 12 }}>Pause & correct {name} directly — agree a fix, then save it as a rule.</span>
        </div>
        <div style={{ height: "calc(100% - 44px)" }}>
          <ChatPanel scope={`member:${pid}:${name}`} autospeak activeNow={live} activePhase={info && info.phase} />
        </div>
      </div>
    </div>
  );
}

/* =================== MODALS =================== */
const ROLE_AVATAR = { frontend: "frontend", backend: "backend", "devops & cloud": "devops", devops: "devops", database: "database", "security & compliance": "security", security: "security", "qa & testing": "qa", qa: "qa" };
function teamFromSpec(spec) {
  return (spec.team || ["Frontend"]).map((n) => ({ name: n, role: n, avatar: ROLE_AVATAR[String(n).toLowerCase()] || "generic" }));
}

// Canonical project types (kept in sync with the backend PROJECT_TYPES) — used by the creation
// picker and the dashboard grouping.
// Canonical project types — grouped (Tech / Operational), extensible. Kept in sync with backend.
const TYPE_META = [
  // tech
  { key: "web", label: "Web application", icon: "🌐", group: "tech", suggests: ["Frontend", "Backend", "QA"] },
  { key: "mobile", label: "Mobile application", icon: "📱", group: "tech", suggests: ["Mobile", "Backend", "QA"] },
  { key: "desktop", label: "Desktop application", icon: "🖥️", group: "tech", suggests: ["Frontend", "Backend", "QA"] },
  { key: "deployment", label: "Deployment", icon: "🚀", group: "tech", suggests: ["DevOps"] },
  { key: "security", label: "Security", icon: "🛡️", group: "tech", suggests: ["Security", "DevOps"] },
  { key: "scripting", label: "Scripting / Automation", icon: "🧩", group: "tech", suggests: ["Backend"] },
  { key: "integration", label: "Integration / API", icon: "🔌", group: "tech", suggests: ["Backend"] },
  { key: "embedded", label: "Embedded / Firmware", icon: "🔧", group: "tech", suggests: ["Embedded", "QA"] },
  { key: "gaming", label: "Game", icon: "🎮", group: "tech", suggests: ["GameDev", "QA"] },
  { key: "xr", label: "XR (AR / VR)", icon: "🕶️", group: "tech", suggests: ["XR", "QA"] },
  { key: "ai_ml", label: "AI / ML", icon: "🧠", group: "tech", suggests: ["Data", "Backend"] },
  { key: "data", label: "Data / Analytics", icon: "📊", group: "tech", suggests: ["Data", "Backend"] },
  // operational
  { key: "marketing", label: "Marketing", icon: "📈", group: "operational", suggests: ["Marketing"] },
  { key: "email", label: "Email specialist", icon: "✉️", group: "operational", suggests: ["Email"] },
  { key: "content", label: "Content creator", icon: "✍️", group: "operational", suggests: ["Content"] },
  { key: "support", label: "Customer support", icon: "💬", group: "operational", suggests: ["Support"] },
  { key: "sales", label: "Sales / Outreach", icon: "🤝", group: "operational", suggests: ["Sales"] },
  { key: "social", label: "Social media", icon: "📣", group: "operational", suggests: ["Content", "Marketing"] },
  { key: "fulfillment", label: "Fulfillment Provider", icon: "📦", group: "operational", suggests: ["Shipping"] },
];
const TYPE_BY_KEY = Object.fromEntries(TYPE_META.map((t) => [t.key, t]));
// role → nature/avatar so the chosen type can seed the right kind of agent
const ROLE_META = {
  Frontend: { nature: "technical", avatar: "frontend" }, Backend: { nature: "technical", avatar: "backend" },
  DevOps: { nature: "technical", avatar: "devops" }, Database: { nature: "technical", avatar: "database" },
  Security: { nature: "technical", avatar: "security" }, QA: { nature: "technical", avatar: "qa" },
  Mobile: { nature: "technical", avatar: "frontend" }, Embedded: { nature: "technical", avatar: "generic" },
  GameDev: { nature: "technical", avatar: "generic" }, XR: { nature: "technical", avatar: "generic" },
  Data: { nature: "technical", avatar: "database" },
  Marketing: { nature: "operational", avatar: "generic" }, Email: { nature: "operational", avatar: "generic" },
  Content: { nature: "operational", avatar: "generic" }, Support: { nature: "operational", avatar: "generic" },
  Sales: { nature: "operational", avatar: "generic" }, Shipping: { nature: "operational", avatar: "generic" },
};
// client-side mirror of the server's recommend_type — for a smart default in the picker
function clientRecommendType(text) {
  const d = " " + (text || "").toLowerCase() + " ";
  const has = (...ws) => ws.some((w) => d.includes(w));
  if (has("fulfillment", "shipping", "shipment", "veeqo", "order tracking", "courier")) return "fulfillment";
  if (has("email blast", "newsletter", "lifecycle email", "klaviyo", "drip ")) return "email";
  if (has("market", "campaign", "growth", "seo ", "brand ", "ads ")) return "marketing";
  if (has("content calendar", "blog post", "copywrit", "article")) return "content";
  if (has("customer support", "help desk", "helpdesk", "ticket")) return "support";
  if (has("social media", "instagram", "linkedin post", "tweet")) return "social";
  if (has("sales", "outreach", "lead ", "crm")) return "sales";
  if (has("ar ", "vr ", "augmented reality", "virtual reality", "unity", "unreal")) return "xr";
  if (has("game", "gameplay", "godot")) return "gaming";
  if (has("embedded", "firmware", "microcontroller", "arduino", "esp32", "rtos")) return "embedded";
  if (has("machine learning", " ml ", " ai ", "model train", "llm", "neural")) return "ai_ml";
  if (has("data pipeline", "analytics", "etl", "warehouse")) return "data";
  if (has("mobile", "ios", "android", "react native", "flutter", "swift", "kotlin")) return "mobile";
  if (has("desktop app", "electron", "tauri", "wpf")) return "desktop";
  if (has("deploy", "ship to", " vm", "nginx", "azure", "ci/cd", "hosting")) return "deployment";
  if (has("security", "audit", "harden", "penetration", "vulnerab", "cve")) return "security";
  if (has("integration", "integrate", "webhook", "api ")) return "integration";
  if (has("script", "automation", "cron", "scrape", "glue ")) return "scripting";
  return "web";
}
// build a scheduler schedule object from the periodic UI state
function periodicSchedule(p) {
  if (!p || !p.enabled) return { enabled: false };
  const schedule = p.kind === "interval"
    ? { kind: "interval", seconds: Math.max(60, Number(p.seconds) || 3600) }
    : { kind: "daily", hhmm: p.hhmm || "09:00" };
  return { enabled: true, schedule, requireApproval: p.requireApproval !== false };
}
export function scheduleLabel(t) {
  const s = (t && t.schedule) || {};
  if (s.kind === "daily") return `every day at ${s.hhmm || "—"}`;
  if (s.kind === "interval") { const n = s.seconds || 0; return n % 86400 === 0 ? `every ${n / 86400}d` : n % 3600 === 0 ? `every ${n / 3600}h` : `every ${Math.round(n / 60)}m`; }
  if (s.kind === "once") return `once`;
  return "scheduled";
}

// The owner's EXACT words from the intake (everything they actually typed), joined verbatim —
// excluding only the auto seed line and the one-click "Confirm" string. This is what must reach
// the team without omission.
function ownerVerbatim(history) {
  return (history || [])
    .filter((m) => m.role === "user"
      && !m.content.startsWith("This is ")
      && m.content.trim() !== "Confirmed — correct, proceed.")
    .map((m) => m.content.trim())
    .filter(Boolean)
    .join("\n\n");
}

// Plain-language note on what each suggested member will actually DO — and, for an existing
// project, that they only EDIT your code when you ask (read-only by default).
function TEAM_ROLE_NOTE(m, kind) {
  const existing = kind === "existing";
  const tail = existing ? " — works on your selected folder; reads it, edits only when you ask." : ".";
  switch (String(m.name || "").toLowerCase()) {
    case "frontend": return "Builds & edits the UI / frontend" + tail;
    case "backend": return "Builds & edits the API, server logic & data access" + tail;
    case "database": return "Designs the schema & handles data/migrations" + tail;
    case "devops": return "Deploys & runs it on the cloud (Azure)" + (existing ? " — deploy stays approval-gated." : ".");
    case "security": return "Reviews auth, secrets & security" + tail;
    case "qa": return "Builds, lints, type-checks, tests & reviews each part, then reports bugs to the CTO to assign.";
    default: return (m.role || "Specialist") + tail;
  }
}

// 4-step creation: (1) existing vs new, (2) browse folder(s), (3) the existing adaptive question
// set, (4) a DIGEST that confirms the full understanding — only then propose → review → create.
export function ConversationalNewProject({ open, onClose, onCreated }) {
  const [phase, setPhase] = useState("kind");        // kind | folders | chat
  const [kind, setKind] = useState("");              // existing | new
  const [folders, setFolders] = useState([]);
  const [history, setHistory] = useState([]);
  const [current, setCurrent] = useState(null);      // {action:"ask"|"digest", question, options, summary}
  const [spec, setSpec] = useState(null);
  const [brief, setBrief] = useState("");            // the validated brief — EDITABLE before create
  const [autoApprove, setAutoApprove] = useState(false);  // pre-authorize changes (skip the popup)
  const [excluded, setExcluded] = useState([]);      // team members the owner dropped from the CTO's rec
  const [answer, setAnswer] = useState("");
  const [path, setPath] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [attached, setAttached] = useState([]);     // file/doc paths the owner attached to describe the project
  const [identifier, setIdentifier] = useState(""); // owner-editable unique id (recommended from name)
  const [unknownResolve, setUnknownResolve] = useState(null); // [{name,mode,role,rules,pick}] when confirming new agents
  const [pendingCreate, setPendingCreate] = useState(null);   // stashed create payload while the dialog is open
  const [catalog, setCatalog] = useState([]);        // known agent roles (for the "pick existing" dropdown)
  const [dropRec, setDropRec] = useState([]);        // recommendation keys the owner declined ("feat:.."/"mem:..")
  const [ready, setReady] = useState(null);          // live readiness re-check result
  const [ptype, setPtype] = useState("");            // chosen project type (category/recommendation)
  const [customType, setCustomType] = useState("");  // optional custom type the owner types in
  const [cadence, setCadence] = useState("once");    // once | recurring | periodical
  const [periodic, setPeriodic] = useState({ enabled: false, kind: "daily", hhmm: "09:00", seconds: 3600, requireApproval: true });
  const scrollRef = useRef(null);
  useEffect(() => { scrollRef.current && (scrollRef.current.scrollTop = scrollRef.current.scrollHeight); }, [history, current]);

  function reset() { setPhase("kind"); setKind(""); setFolders([]); setHistory([]); setCurrent(null); setSpec(null); setBrief(""); setAutoApprove(false); setExcluded([]); setAnswer(""); setPath(""); setName(""); setIdentifier(""); setAttached([]); setUnknownResolve(null); setPendingCreate(null); setDropRec([]); setReady(null); setPtype(""); setCustomType(""); setCadence("once"); setPeriodic({ enabled: false, kind: "daily", hhmm: "09:00", seconds: 3600, requireApproval: true }); }
  function close() { reset(); onClose(); }

  async function step(h) {
    setBusy(true);
    try {
      const d = await api.intake(h);
      if (d.action === "propose" && d.spec) {
        setSpec(d.spec); setName(d.spec.name || ""); setIdentifier((cur) => cur || d.spec.identifier || "");
        // The brief MUST contain the owner's exact words verbatim — never just the CTO's summary.
        // Put the owner's instructions first (authoritative), the CTO's understanding second.
        const owner = ownerVerbatim(h);
        const desc = d.spec.description || "";
        setBrief(owner
          ? `OWNER'S INSTRUCTIONS — verbatim, follow EXACTLY (no omission):\n${owner}\n\n———\nCTO's understanding (supporting):\n${desc}`
          : desc);
        // smart default for the type picker (a recommendation the owner can change) — but NEVER
        // overwrite a type the owner already chose early in the flow.
        const recKey = TYPE_BY_KEY[String(d.spec.type || "").toLowerCase()] ? String(d.spec.type).toLowerCase()
          : clientRecommendType(`${owner}\n${desc}`);
        setPtype((cur) => cur || recKey);
        setCurrent(null);
      } else { setCurrent(d); }
    } catch { setCurrent({ action: "ask", question: "(backend offline — start it, then reopen)" }); }
    setBusy(false);
  }

  function startChat() {
    const ctx = kind === "existing"
      ? `This is an EXISTING project. Folders to work on (READ-ONLY unless I explicitly ask to modify): ${folders.join(" | ") || "(none)"}.`
      : `This is a NEW project to create at: ${path || folders[0] || "(location chosen later)"}.`;
    // Seed the context, then show a fixed intro WITHOUT calling the model — the owner will paste
    // their full description first. We only call the engine once they've sent something.
    setHistory([{ role: "user", content: ctx }]);
    setCurrent({ action: "ask", intro: true,
      question: "Paste a full description of what you want to build. Attach any files or docs that help (📎 below). I'll only ask again if something critical is unclear — then I'll confirm the platform, team and features before generating." });
    setPhase("chat");
  }

  async function attachFiles() {
    const r = window.odin && (await window.odin.pickFiles());
    if (!r) return;
    const arr = Array.isArray(r) ? r : [r];
    if (arr.length) setAttached((a) => [...new Set([...a, ...arr])]);
  }

  function answerWith(text) {
    if ((!text && attached.length === 0) || busy) return;
    const q = current && !current.intro ? (current.question || current.summary || "") : "";
    // attach the file/doc paths so the CTO can READ them as part of the description
    const filesBlock = attached.length ? `\n\nATTACHED FILES (read these):\n${attached.map((f) => "- " + f).join("\n")}` : "";
    const h = [...history, ...(q ? [{ role: "assistant", content: q }] : []), { role: "user", content: (text || "(see attached files)") + filesBlock }];
    setHistory(h); setAnswer(""); setCurrent(null); step(h);
  }

  async function browseFolders() {
    const r = window.odin && (kind === "existing" ? await window.odin.pickFolders() : await window.odin.pickFolder());
    if (!r) return;
    const arr = Array.isArray(r) ? r : [r];
    if (arr.length) { setFolders((f) => [...new Set([...f, ...arr])]); if (kind === "new") setPath(arr[0]); }
  }

  async function create() {
    // LONG-STREAMING (e.g. Zoom/meeting) projects can't be processed as one block — they must be CHUNKED.
    // Put a big, explicit confirmation in front of the owner before creating such a project.
    const _txt = `${name} ${(spec && spec.description) || ""} ${brief || ""}`.toLowerCase();
    const _isStreaming = ["zoom", "meeting", "transcrib", "listen to", "live audio", "stream", "microphone",
      "call recording", "two hour", "2 hour", "chunk", "long audio", "real-time audio", "speech to text"]
      .some((k) => _txt.includes(k));
    if (_isStreaming && !window.confirm(
      "🎙️  LONG-STREAMING PROJECT — CHUNKED PROCESSING\n\n" +
      "This project listens to long live audio (e.g. a 1–2 hour Zoom meeting). Waiting for the whole meeting " +
      "is not practical, so Odin processes it in SMALL CHUNKS while it runs:\n\n" +
      "•  Audio is captured in short serial segments and transcribed as it arrives.\n" +
      "•  Each chunk is analyzed on its own during the meeting — never one giant transcript.\n" +
      "•  At the end, all chunks merge into ONE final smart report.\n" +
      "•  Your microphone / meeting audio is never blocked — capture runs in parallel.\n\n" +
      "Long sessions use more CPU/RAM — keep the desktop running for the whole meeting.\n\n" +
      "Create this streaming project?"
    )) { return; }
    setBusy(true);
    const isExisting = kind === "existing";
    // fold ACCEPTED recommended members into the team (owner can have dropped some)
    const recMembers = ((spec.recommendations && spec.recommendations.members) || [])
      .filter((m) => !dropRec.includes("mem:" + m.name))
      .map((m) => ({ name: m.name, role: m.name, avatar: ROLE_AVATAR[String(m.name).toLowerCase()] || "generic" }));
    const baseTeam = teamFromSpec(spec).filter((m) => !excluded.includes(m.name));
    const seen = new Set(baseTeam.map((m) => m.name.toLowerCase()));
    const finalType = (customType.trim() || ptype || spec.type || "web").toLowerCase();
    // the chosen TYPE seeds its specialist roles (e.g. Email type → Email agent), with the right nature
    const typeMembers = ((TYPE_BY_KEY[finalType] || {}).suggests || [])
      .filter((rn) => !seen.has(rn.toLowerCase()) && !excluded.includes(rn))
      .map((rn) => { const meta = ROLE_META[rn] || {}; return { name: rn, role: rn, avatar: meta.avatar || "generic",
        nature: meta.nature || "technical", mode: meta.nature === "operational" ? "normal" : "" }; });
    typeMembers.forEach((m) => seen.add(m.name.toLowerCase()));
    const team = [...baseTeam, ...recMembers.filter((m) => !seen.has(m.name.toLowerCase())), ...typeMembers];
    // append ACCEPTED recommended features to the brief so they reach the team
    const recFeats = ((spec.recommendations && spec.recommendations.features) || [])
      .filter((f) => !dropRec.includes("feat:" + f.name)).map((f) => `- ${f.name}${f.why ? " — " + f.why : ""}`);
    const finalBrief = (brief || spec.description || "").trim() +
      (recFeats.length ? `\n\nAPPROVED RECOMMENDED FEATURES:\n${recFeats.join("\n")}` : "");
    // GATE: never silently create an agent the system invented from a word in the prompt (e.g. "Vapi").
    // Any team member that isn't a known catalog role must be CONFIRMED in a separate dialog first.
    let unknown = [];
    try { const v = await api.validateAgents(team.map((m) => m.name)); unknown = v.unknown || []; setCatalog(v.catalog || []); } catch {}
    if (unknown.length) {
      setBusy(false);
      setPendingCreate({ team, finalBrief, finalType, isExisting });
      setUnknownResolve(unknown.map((n) => ({ name: n, mode: "create", role: "", rules: "", pick: "" })));
      return;   // show the confirmation dialog; creation continues only after it's resolved
    }
    await _finalizeCreate(team, finalBrief, finalType, isExisting);
  }

  async function _finalizeCreate(team, finalBrief, finalType, isExisting) {
    setBusy(true);
    const p = await api.createProject({
      name: (name || spec.name || "New project").trim(),
      identifier: (identifier || spec.identifier || "").trim(),
      description: finalBrief, members: team,
      type: finalType, stack: spec.stack || "", mode: isExisting ? "existing" : "build",
      readiness: spec.readiness || [],   // G13: a needed new platform -> "strengthen agent" proposal
      localPath: isExisting ? (folders[0] || "") : (path || folders[0] || ""),
      sources: isExisting ? folders : [],
      autoApprove: autoApprove,
      cadence: cadence,
      periodic: cadence === "periodical" ? periodicSchedule({ ...periodic, enabled: true }) : { enabled: false },
    });
    setBusy(false); reset(); onCreated && onCreated(p); onClose();
  }

  // resolve the unknown-agent dialog: create-with-rules / pick-existing / remove, then continue
  async function confirmUnknownAgents() {
    const { team, finalBrief, finalType, isExisting } = pendingCreate || {};
    const resolved = [];
    for (const m of (team || [])) {
      const u = (unknownResolve || []).find((x) => x.name === m.name);
      if (!u) { resolved.push(m); continue; }
      if (u.mode === "remove") continue;
      if (u.mode === "pick" && u.pick) {
        resolved.push({ name: u.pick, role: u.pick, avatar: (ROLE_META[u.pick] || {}).avatar || "generic",
          nature: (ROLE_META[u.pick] || {}).nature || "technical" });
        continue;
      }
      resolved.push({ ...m, role: (u.role || m.name).trim(),
        description: (u.rules || "").trim() || `Custom agent: ${m.name}`,
        rules: u.rules ? [u.rules.trim()] : [] });
    }
    setUnknownResolve(null); setPendingCreate(null);
    await _finalizeCreate(resolved, finalBrief, finalType, isExisting);
  }

  // Reusable: project TYPE + OPERATIONAL agents + PERIODICAL schedule (with a little animation).
  // Shown EARLY (in the folder step) so the owner picks the kind up front, and again on the
  // confirm screen for review — both share the same state.
  const schedSummary = periodic.kind === "interval"
    ? `Every ${Math.max(1, Math.round((periodic.seconds || 3600) / 3600))} hour(s)`
    : `Every day at ${periodic.hhmm || "09:00"}`;
  function typeBtn(t) {
    const on = (customType.trim() ? "" : ptype) === t.key;
    return (
      <button key={t.key} type="button" onClick={() => { setCustomType(""); setPtype(t.key); }}
        style={{ display: "flex", alignItems: "center", gap: 7, padding: "8px 12px", borderRadius: 11, cursor: "pointer",
          fontSize: 12.5, fontWeight: 600, transition: ".15s",
          background: on ? "linear-gradient(180deg,rgba(108,140,255,.22),rgba(122,240,208,.10))" : "rgba(255,255,255,.04)",
          color: on ? "var(--txt)" : "var(--txt-dim)",
          border: "1px solid " + (on ? "var(--brand)" : "var(--stroke-strong)") }}>
        <span style={{ fontSize: 15 }}>{t.icon}</span>{t.label}{on && <span style={{ color: "var(--brand-2)" }}>✓</span>}
      </button>
    );
  }
  const cadenceOpt = (key, icon, title, sub) => {
    const on = cadence === key;
    return (
      <button key={key} type="button" onClick={() => setCadence(key)}
        style={{ flex: 1, textAlign: "left", padding: "9px 11px", borderRadius: 11, cursor: "pointer", transition: ".15s",
          background: on ? "linear-gradient(180deg,rgba(108,140,255,.22),rgba(122,240,208,.10))" : "rgba(255,255,255,.04)",
          border: "1px solid " + (on ? "var(--brand)" : "var(--stroke-strong)") }}>
        <div style={{ fontSize: 12.5, fontWeight: 700, color: on ? "var(--txt)" : "var(--txt-dim)" }}>{icon} {title}</div>
        <div className="faint" style={{ fontSize: 10.5, marginTop: 2 }}>{sub}</div>
      </button>
    );
  };
  function typeSchedulePicker() {
    const tech = TYPE_META.filter((t) => t.group === "tech");
    const oper = TYPE_META.filter((t) => t.group === "operational");
    return (
      <>
        <style>{`
          @keyframes odn-spin{to{transform:rotate(360deg)}}
          @keyframes odn-ringpulse{0%,100%{opacity:.45}50%{opacity:1}}
          @keyframes odn-slidein{from{opacity:0;transform:translateX(-6px)}to{opacity:1;transform:translateX(0)}}
        `}</style>
        <div>
          <label className="row between"><span>Project type</span><span className="faint" style={{ fontSize: 10.5 }}>tap to choose</span></label>
          <div className="faint" style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: .4, margin: "2px 0 5px" }}>🛠 TECH PROJECTS</div>
          <div className="row wrap" style={{ gap: 8 }}>{tech.map(typeBtn)}</div>
          <div className="faint" style={{ fontSize: 10.5, fontWeight: 700, letterSpacing: .4, margin: "10px 0 5px" }}>📋 OPERATIONAL PROJECTS</div>
          <div className="row wrap" style={{ gap: 8 }}>{oper.map(typeBtn)}</div>
          <div className="row" style={{ gap: 6, marginTop: 8, alignItems: "center" }}>
            <span className="faint" style={{ fontSize: 11 }}>or custom:</span>
            <input value={customType} placeholder="e.g. blockchain, IoT…" onChange={(e) => setCustomType(e.target.value)}
              style={{ fontSize: 12, padding: "4px 8px", flex: 1, borderColor: customType.trim() ? "var(--brand)" : undefined }} />
          </div>
          <div className="faint" style={{ fontSize: 11, marginTop: 4 }}>A category — it organizes your dashboard and seeds the right roles. It doesn't change your brief.</div>
        </div>
        <div>
          <label>How often does it run?</label>
          <div className="row" style={{ gap: 8 }}>
            {cadenceOpt("once", "▶️", "One-off", "Run a single time.")}
            {cadenceOpt("recurring", "🔁", "Recurring", "Run it again whenever you want.")}
            {cadenceOpt("periodical", "⏰", "Periodical", "On a schedule, with approval.")}
          </div>
        </div>
        {cadence === "periodical" && (
          <div className="card pad" style={{ background: "rgba(122,240,208,.07)", transition: ".2s" }}>
            <div className="faint" style={{ fontSize: 11, marginBottom: 4 }}>When it's due and your device is on, Odin asks you to start it — nothing runs unattended. Miss the time (device off)? No problem — it rolls to the next slot.</div>
            <div className="row" style={{ gap: 14, marginTop: 6, alignItems: "center" }}>
              <svg width="46" height="46" viewBox="0 0 46 46" style={{ flexShrink: 0 }}>
                <circle cx="23" cy="23" r="19" fill="none" stroke="var(--brand-2)" strokeWidth="2" style={{ animation: "odn-ringpulse 2s ease-in-out infinite" }} />
                <line x1="23" y1="23" x2="23" y2="11" stroke="var(--brand-2)" strokeWidth="2.2" strokeLinecap="round" style={{ animation: "odn-spin 3s linear infinite", transformOrigin: "23px 23px" }} />
                <line x1="23" y1="23" x2="32" y2="23" stroke="var(--brand)" strokeWidth="2.2" strokeLinecap="round" style={{ animation: "odn-spin 12s linear infinite", transformOrigin: "23px 23px" }} />
                <circle cx="23" cy="23" r="2.4" fill="var(--brand-2)" />
              </svg>
              <div className="col" style={{ gap: 8, flex: 1 }}>
                <div key={schedSummary} style={{ fontSize: 13, fontWeight: 700, color: "var(--brand-2)", animation: "odn-slidein .3s ease both" }}>{schedSummary}</div>
                <div className="row" style={{ gap: 8, alignItems: "center" }}>
                  <select value={periodic.kind} onChange={(e) => setPeriodic((p) => ({ ...p, kind: e.target.value }))} style={{ fontSize: 12, padding: "4px 8px" }}>
                    <option value="daily">Every day at…</option>
                    <option value="interval">Every N hours</option>
                  </select>
                  {periodic.kind === "daily"
                    ? <input type="time" value={periodic.hhmm} onChange={(e) => setPeriodic((p) => ({ ...p, hhmm: e.target.value }))} style={{ fontSize: 12, padding: "4px 8px", width: 110 }} />
                    : <div className="row" style={{ gap: 6, alignItems: "center" }}>
                        <input type="number" min={1} value={Math.max(1, Math.round((periodic.seconds || 3600) / 3600))}
                          onChange={(e) => setPeriodic((p) => ({ ...p, seconds: Math.max(1, Number(e.target.value) || 1) * 3600 }))}
                          style={{ fontSize: 12, padding: "4px 8px", width: 70 }} /><span className="faint" style={{ fontSize: 12 }}>hours</span>
                      </div>}
                </div>
                <label className="row" style={{ gap: 8, cursor: "pointer", fontSize: 11.5 }}>
                  <input type="checkbox" checked={periodic.requireApproval} style={{ width: 14, height: 14 }}
                    onChange={(e) => setPeriodic((p) => ({ ...p, requireApproval: e.target.checked }))} />
                  <span>Ask me to approve before each run <span className="faint">(recommended)</span></span>
                </label>
              </div>
            </div>
          </div>
        )}
      </>
    );
  }

  const deps = (spec && spec.dependencies) || [];
  const title = spec ? "New project · confirm platform, team & features"
    : phase === "kind" ? "New project · existing or new?"
    : phase === "folders" ? (kind === "existing" ? "New project · select folder(s)" : "New project · where should it live?") : "New project · describe what you want";
  return (
    <Modal open={open} onClose={close} title={title}
      footer={
        spec ? <><button className="btn ghost" onClick={() => setSpec(null)}>← Back</button>
                 <button className="btn primary" onClick={create} disabled={busy}>{busy ? "Creating…" : "Create & start"}</button></>
        : phase === "folders" ? <><button className="btn ghost" onClick={() => setPhase("kind")}>← Back</button>
                 <button className="btn primary" onClick={startChat}>Next: describe →</button></>
        : <button className="btn ghost" onClick={close}>Cancel</button>}>

      {!spec && phase === "kind" && (
        <div className="col" style={{ gap: 12 }}>
          <div className="muted" style={{ fontSize: 13 }}>First — is this an existing project, or a new one?</div>
          <button className="btn" onClick={() => { setKind("existing"); setPhase("folders"); }}>📂 I have an existing project (work on it)</button>
          <button className="btn" onClick={() => { setKind("new"); setPhase("folders"); }}>✨ Create a new project</button>
        </div>
      )}

      {!spec && phase === "folders" && (
        <div className="col" style={{ gap: 10 }}>
          <div className="muted" style={{ fontSize: 13 }}>{kind === "existing" ? "Select the folder(s) to work on — you can add many." : "Choose where the project will live. Pick a parent folder (I'll create the project folder inside it) or an empty folder to use directly."}</div>
          <button className="btn" onClick={browseFolders}>🗂 Browse…</button>
          {kind === "new" && (
            <div className="row" style={{ gap: 6 }}>
              <input value={path} placeholder="…or type a path, e.g. /Users/you/Desktop/projects" onChange={(e) => setPath(e.target.value)} />
            </div>
          )}
          <div className="col" style={{ gap: 4 }}>
            {folders.map((f, i) => (
              <div key={i} className="row between" style={{ fontSize: 12 }}><span title={f}>📁 {f}</span>
                <span style={{ cursor: "pointer", color: "var(--danger)" }} onClick={() => setFolders((a) => a.filter((_, j) => j !== i))}>✕</span></div>
            ))}
            {folders.length === 0 && kind === "existing" && <div className="faint" style={{ fontSize: 12 }}>No folder selected yet.</div>}
          </div>
          {kind === "existing" && <div className="faint" style={{ fontSize: 11 }}>Read-only — the team reads/considers this code and only modifies when you ask.</div>}
          <div style={{ height: 1, background: "var(--stroke)", margin: "4px 0" }} />
          {typeSchedulePicker()}
        </div>
      )}

      {!spec && phase === "chat" && (
        <div className="col" style={{ gap: 10 }}>
          {(() => {
            const convo = history.filter((m) => !(m.role === "user" && m.content.startsWith("This is")));
            if (!convo.length) return null;
            return (
              <div ref={scrollRef} style={{ maxHeight: 300, overflow: "auto", display: "flex", flexDirection: "column", gap: 8 }}>
                {convo.map((m, i) => (
                  <div key={i} className={"msg " + (m.role === "user" ? "user" : "assistant")}
                    style={{ alignSelf: m.role === "user" ? "flex-end" : "flex-start", fontSize: 13 }}>{m.content}</div>
                ))}
              </div>
            );
          })()}
          {current?.action === "digest" ? (
            <div className="card pad col" style={{ borderColor: "rgba(108,140,255,.4)" }}>
              <b style={{ fontSize: 12.5 }}>Here's my understanding — confirm or correct:</b>
              <div style={{ fontSize: 12.5, whiteSpace: "pre-wrap" }}>{current.summary}</div>
              <div className="row"><button className="btn sm primary" title="Looks right — build the final brief (you can still edit it on the next screen)"
                onClick={() => answerWith(answer.trim() || "Confirmed — correct, proceed.")}>✓ Confirm</button>
                <input value={answer} placeholder="or type a correction / add detail…" onChange={(e) => setAnswer(e.target.value)} onKeyDown={(e) => e.key === "Enter" && answerWith(answer.trim())} /></div>
              <div className="faint" style={{ fontSize: 11 }}>Tip: type any correction and press Enter (or Confirm) — it won't be lost. You'll get a final, editable brief before anything is created.</div>
            </div>
          ) : (
            <>
              <div className="row" style={{ gap: 10, marginTop: 6 }}>
                <Avatar kind="generic" size="sm" active={busy} />
                <div className="muted" style={{ fontSize: 13 }}>{busy ? "Analyzing your description…" : (current?.question || "…")}</div>
              </div>
              {current?.options && <div className="row wrap" style={{ gap: 8 }}>{current.options.map((o) => <button key={o} className="btn sm" onClick={() => answerWith(o)}>{o}</button>)}</div>}
              {attached.length > 0 && (
                <div className="row wrap" style={{ gap: 6 }}>
                  {attached.map((f, i) => (
                    <span key={i} className="pill" style={{ fontSize: 10.5 }} title={f}>📎 {f.split("/").pop()}
                      <span style={{ cursor: "pointer", marginLeft: 6, color: "var(--danger)" }} onClick={() => setAttached((a) => a.filter((_, j) => j !== i))}>✕</span></span>
                  ))}
                </div>
              )}
              <textarea value={answer} autoFocus rows={current?.intro ? 6 : 3}
                placeholder={current?.intro ? "Paste your full description here… (Shift+Enter for a new line, Enter to send)" : "type your answer…"}
                onChange={(e) => setAnswer(e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); answerWith(answer.trim()); } }}
                style={{ width: "100%", fontSize: 12.5, lineHeight: 1.5, resize: "vertical" }} />
              <div className="row between">
                <button className="btn sm" onClick={attachFiles} title="Attach files or docs that describe the project — I'll read them">📎 Attach files/docs</button>
                <button className="btn primary" onClick={() => answerWith(answer.trim())} disabled={busy || (!answer.trim() && attached.length === 0)}>{busy ? "…" : "Send"}</button>
              </div>
            </>
          )}
        </div>
      )}

      {spec && (
        <div className="col">
          <div className="card pad" style={{ borderColor: "rgba(108,140,255,.4)", fontSize: 12.5 }}>
            Here's my analysis. Confirm the <b>platform</b>, <b>team</b> and <b>features</b> below — drop anything you don't want — then create. Nothing is built until you click Create.
          </div>
          <div><label>Project name</label><input value={name} onChange={(e) => setName(e.target.value)} /></div>
          <div><label>Identifier <span className="faint">(recommended — editable; must be unique so a re-used prompt won't reuse an old project's folder)</span></label>
            <input value={identifier} placeholder={(spec && spec.identifier) || "auto"} onChange={(e) => setIdentifier(e.target.value)} style={{ fontFamily: "var(--mono, monospace)" }} /></div>
          <div className="card pad" style={{ fontSize: 12, color: "var(--txt-dim)" }}>
            Type: <b style={{ color: "var(--txt)" }}>{customType.trim() || (TYPE_BY_KEY[ptype] || {}).label || "Web application"}</b>
            <span> · Cadence: <b style={{ color: "var(--txt)" }}>{cadence}</b></span>
            {cadence === "periodical" && <span> · <b style={{ color: "var(--brand-2)" }}>⏰ {schedSummary}</b></span>}
            <span className="faint"> (chosen at the start — go back to change)</span>
          </div>
          <div><label>Platform</label><div className="card pad" style={{ fontSize: 12.5 }}>{spec.stack || spec.type || "—"}</div></div>
          {(spec.features || []).length > 0 && (
            <div><label>Features — what this project will deliver</label>
              <div className="col" style={{ gap: 3 }}>
                {spec.features.map((f, i) => (
                  <div key={i} className="row" style={{ gap: 8, fontSize: 12 }}><span className="dot ok" /><span>{typeof f === "string" ? f : f.name}</span></div>
                ))}
              </div>
            </div>
          )}
          <div>
            <label>Brief — this is what the project is built from. Edit it; it becomes the team's instructions.</label>
            <textarea value={brief} onChange={(e) => setBrief(e.target.value)} rows={8}
              style={{ width: "100%", fontSize: 12.5, lineHeight: 1.5, resize: "vertical", minHeight: 120 }} />
            {brief.trim() !== (spec.description || "").trim() && <div className="faint" style={{ fontSize: 11 }}>✎ Edited — your version will be used.</div>}
          </div>
          {(() => {
            const rf = (spec.recommendations && spec.recommendations.features) || [];
            const rm = (spec.recommendations && spec.recommendations.members) || [];
            if (!rf.length && !rm.length) return null;
            const Row = (key, label, why) => {
              const on = !dropRec.includes(key);
              return (
                <label key={key} className="row" style={{ gap: 8, fontSize: 12, cursor: "pointer", alignItems: "flex-start", opacity: on ? 1 : 0.45 }}>
                  <input type="checkbox" checked={on} style={{ width: 15, height: 15, marginTop: 2 }}
                    onChange={() => setDropRec((x) => on ? [...x, key] : x.filter((k) => k !== key))} />
                  <span><b>{label}</b>{why ? <span className="faint"> — {why}</span> : null}</span>
                </label>
              );
            };
            return (
              <div><label>I also recommend (you approve each — with my reason)</label>
                <div className="col" style={{ gap: 6 }}>
                  {rm.map((m) => Row("mem:" + m.name, "Team: " + m.name, m.why))}
                  {rf.map((f) => Row("feat:" + f.name, "Feature: " + f.name, f.why))}
                </div>
              </div>
            );
          })()}
          <div><label>Team — the CTO's recommendation. You decide: tick to include, untick to drop.</label>
            <div className="col" style={{ gap: 6 }}>{teamFromSpec(spec).map((m) => {
              const on = !excluded.includes(m.name);
              return (
                <label key={m.name} className="row" style={{ gap: 8, fontSize: 12, cursor: "pointer", opacity: on ? 1 : 0.45 }}>
                  <input type="checkbox" checked={on} style={{ width: 15, height: 15 }}
                    onChange={() => setExcluded((x) => on ? [...x, m.name] : x.filter((n) => n !== m.name))} />
                  <Avatar kind={m.avatar} name={m.name} size="sm" /><b>{m.name}</b>
                  <span className="faint">{TEAM_ROLE_NOTE(m, kind)}</span>
                </label>
              );
            })}</div>
            <div className="faint" style={{ fontSize: 11, marginTop: 4 }}>Dropping QA keeps its full quality rules intact for other projects — it just won't run on this one. You can also add or remove members later.</div>
          </div>
          {/* Type / operational / periodical are chosen EARLY (folder step). Shown there, reviewed above. */}
          {(spec.readiness || []).length > 0 && (
            <div><label className="row between"><span>Readiness — can our resources (Azure · Claude · connectors · team) do this?</span>
              <button className="btn sm" title="Test live: check Azure + the engine + connected services right now"
                onClick={async () => { setReady({ loading: true }); try { setReady(await api.intakeReadiness()); } catch { setReady({ error: true }); } }}>↻ Re-check live</button></label>
              <div className="col" style={{ gap: 5 }}>
                {spec.readiness.map((rdy, i) => {
                  const needs = String(rdy.status) === "needs";
                  return (
                    <div key={i} className="row" style={{ gap: 8, fontSize: 12, alignItems: "flex-start" }}>
                      <span className={"dot " + (needs ? "warn" : "ok")} style={{ marginTop: 4 }} />
                      <span><b>{rdy.item}</b> <span className="faint">· {rdy.by || "—"}</span>
                        {needs && <span style={{ color: "var(--warn)" }}> — needs: {rdy.need || "setup"} {/connect|api/i.test(rdy.need || "") && <span className="faint">(add it in Connectors first)</span>}</span>}
                      </span>
                    </div>
                  );
                })}
              </div>
              {ready && !ready.loading && !ready.error && (
                <div className="faint" style={{ fontSize: 11, marginTop: 6 }}>
                  Live: engine {ready.claude ? "✅" : "❌"} · Azure {ready.azure ? "✅" : "❌"} · connectors: {(ready.connectors || []).join(", ") || "none"}
                </div>
              )}
              {ready && ready.loading && <div className="faint" style={{ fontSize: 11, marginTop: 6 }}>Checking live resources…</div>}
              {ready && ready.error && <div style={{ fontSize: 11, marginTop: 6, color: "var(--danger)" }}>Couldn't reach the backend to re-check.</div>}
              <div className="faint" style={{ fontSize: 11, marginTop: 4 }}>Anything marked “needs” should be connected/created and tested before you generate — or create now and resolve it when that part runs (it stays approval-gated).</div>
            </div>
          )}
          {deps.length > 0 && (<div><label>Dependencies</label><div className="col" style={{ gap: 5 }}>{deps.map((d, i) => (<div key={i} className="row" style={{ gap: 8, fontSize: 12 }}><span className={"dot " + (String(d.status).startsWith("have") ? "ok" : "warn")} /><b>{d.name}</b><span className="faint">{d.why || d.how || ""}</span></div>))}</div></div>)}
          {kind === "existing"
            ? <div><label>Working on (read-only)</label>{folders.map((f, i) => <div key={i} className="faint" style={{ fontSize: 11 }}>📁 {f}</div>)}</div>
            : <div><label>Create at</label><div className="row"><input value={path || folders[0] || ""} onChange={(e) => setPath(e.target.value)} placeholder="/Users/you/Desktop/projects" /><button className="btn" onClick={async () => { const pp = window.odin && (await window.odin.pickFolder()); if (pp) setPath(pp); }}>Browse…</button></div></div>}
          <div className="card pad" style={{ background: autoApprove ? "rgba(255,180,80,.08)" : undefined }}>
            <label className="row" style={{ gap: 8, cursor: "pointer", alignItems: "flex-start" }}>
              <input type="checkbox" checked={autoApprove} style={{ width: 16, height: 16, marginTop: 2 }}
                onChange={(e) => setAutoApprove(e.target.checked)} />
              <span style={{ fontSize: 12.5 }}>
                <b>Pre‑approve changes for this project</b> — let the team edit files & run commands without asking.
                <div className="faint" style={{ fontSize: 11, marginTop: 2 }}>
                  {autoApprove ? "⚠️ No approval popup — changes apply automatically. Use only for sandboxes/new projects."
                              : "Default: every modification waits for your approval (you'll get a popup + macOS alert)."}
                </div>
              </span>
            </label>
          </div>
        </div>
      )}

      {unknownResolve && (
        <div style={{ position: "fixed", inset: 0, zIndex: 2147483647, background: "rgba(0,0,0,.55)",
          display: "flex", alignItems: "center", justifyContent: "center", padding: 18 }}
          onClick={(e) => { if (e.target === e.currentTarget) setUnknownResolve(null); }}>
          <div className="card pad" style={{ width: "min(560px,94vw)", maxHeight: "86vh", overflow: "auto", background: "var(--bg)" }}>
            <b style={{ fontSize: 14 }}>⚠️ New agent(s) not recognized</b>
            <div className="faint" style={{ fontSize: 12, margin: "6px 0 12px" }}>
              These names aren't existing agents. Nothing is created until you decide. For each: create it
              (give a role + rules so it doesn't hallucinate), pick an existing agent if you mis-named it, or remove it.
            </div>
            <div className="col" style={{ gap: 14 }}>
              {unknownResolve.map((u, i) => {
                const set = (patch) => setUnknownResolve((arr) => arr.map((x, j) => j === i ? { ...x, ...patch } : x));
                return (
                  <div key={u.name} className="card pad" style={{ background: "rgba(255,255,255,.03)" }}>
                    <b style={{ fontSize: 13 }}>“{u.name}”</b>
                    <div className="row" style={{ gap: 6, margin: "8px 0" }}>
                      {[["create", "➕ Create new"], ["pick", "🔁 Use existing"], ["remove", "🗑 Remove"]].map(([m, lbl]) => (
                        <button key={m} className={"btn sm" + (u.mode === m ? " primary" : "")} onClick={() => set({ mode: m })}>{lbl}</button>
                      ))}
                    </div>
                    {u.mode === "create" && (
                      <div className="col" style={{ gap: 6 }}>
                        <input placeholder="Role (e.g. Fulfillment via Vapi)" value={u.role} onChange={(e) => set({ role: e.target.value })} />
                        <textarea placeholder="Rules / scope — what it MUST and must NOT do (prevents hallucination)" value={u.rules} onChange={(e) => set({ rules: e.target.value })} style={{ minHeight: 60 }} />
                      </div>
                    )}
                    {u.mode === "pick" && (
                      <select value={u.pick} onChange={(e) => set({ pick: e.target.value })}>
                        <option value="">— pick an existing agent —</option>
                        {catalog.map((c) => <option key={c} value={c}>{c}</option>)}
                      </select>
                    )}
                    {u.mode === "remove" && <div className="faint" style={{ fontSize: 11 }}>This agent won't be added.</div>}
                  </div>
                );
              })}
            </div>
            <div className="row" style={{ gap: 8, marginTop: 14, justifyContent: "flex-end" }}>
              <button className="btn ghost" onClick={() => setUnknownResolve(null)}>Cancel</button>
              <button className="btn primary"
                disabled={unknownResolve.some((u) => (u.mode === "create" && !u.role.trim()) || (u.mode === "pick" && !u.pick))}
                onClick={confirmUnknownAgents}>Confirm & create project</button>
            </div>
          </div>
        </div>
      )}
    </Modal>
  );
}

// DEPLOY an EXISTING app — connect local folders to Azure destinations (update, not scaffold).
export function DeployProjectModal({ open, onClose, onCreated }) {
  const [name, setName] = useState("");
  const [rows, setRows] = useState([{ role: "frontend", local: "", cloud: "" }, { role: "backend", local: "", cloud: "" }]);
  const [updateMode, setUpdateMode] = useState("update");   // update (default) | replace
  const [busy, setBusy] = useState(false);
  function reset() { setName(""); setRows([{ role: "frontend", local: "", cloud: "" }, { role: "backend", local: "", cloud: "" }]); setUpdateMode("update"); }
  function close() { reset(); onClose(); }
  function setRow(i, k, v) { setRows((r) => r.map((x, j) => (j === i ? { ...x, [k]: v } : x))); }
  async function browse(i) { const f = window.odin && (await window.odin.pickFolder()); if (f) setRow(i, "local", f); }
  async function create() {
    if (!name.trim()) return; setBusy(true);
    const desc = `Deploy an EXISTING app to the Azure VM (${updateMode === "update" ? "UPDATE in place, do not replace" : "replace"}). Follow the deploy playbook: never node_modules, never production .env, ask about public/upload/logs, rebuild both, restart via systemd.`;
    const p = await api.createProject({
      name: name.trim(), description: desc, mode: "deploy",
      members: [{ name: "DevOps", role: "DevOps & Cloud", avatar: "devops" }, { name: "QA", role: "QA & Testing", avatar: "qa" }],
    });
    for (const r of rows) if (r.local && r.cloud) await api.addMapping(p.id, { local: r.local, cloud: r.cloud, role: r.role });
    setBusy(false); reset(); onCreated && onCreated(p); onClose();
  }
  return (
    <Modal open={open} onClose={close} title="Deploy an existing project"
      footer={<><span className="faint" style={{ fontSize: 12 }}>DevOps + QA — no scaffolding.</span>
        <button className="btn primary" onClick={create} disabled={busy}>{busy ? "Creating…" : "Create deploy project"}</button></>}>
      <div><label>Name</label><input value={name} onChange={(e) => setName(e.target.value)} placeholder="Organics deploy" /></div>
      {rows.map((r, i) => (
        <div key={i} className="card pad col" style={{ gap: 6 }}>
          <div className="row between"><b style={{ fontSize: 12.5, textTransform: "capitalize" }}>{r.role} folder</b>
            <select value={r.role} onChange={(e) => setRow(i, "role", e.target.value)} style={{ width: 130 }}>
              <option value="frontend">frontend</option><option value="backend">backend</option><option value="other">other</option></select></div>
          <div className="row"><input value={r.local} placeholder="local folder…" onChange={(e) => setRow(i, "local", e.target.value)} />
            <button className="btn" onClick={() => browse(i)}>Browse…</button></div>
          <input value={r.cloud} placeholder="Azure VM destination (e.g. ~/organics)" onChange={(e) => setRow(i, "cloud", e.target.value)} />
        </div>
      ))}
      <button className="btn sm" onClick={() => setRows((r) => [...r, { role: "other", local: "", cloud: "" }])}>＋ Add another folder</button>
      <div><label>Mode</label>
        <select value={updateMode} onChange={(e) => setUpdateMode(e.target.value)}>
          <option value="update">Update in place (don't replace data)</option>
          <option value="replace">Replace destination before rebuild</option>
        </select></div>
      <div className="faint" style={{ fontSize: 11 }}>DevOps will run the smart pre-flight (asks about .env, public/upload/logs, rebuild, restart) and only deploy on your approval; QA verifies it's online.</div>
    </Modal>
  );
}

export function NewProjectModal({ open, onClose, onCreated }) {
  const [name, setName] = useState(""); const [desc, setDesc] = useState(""); const [path, setPath] = useState(""); const [busy, setBusy] = useState(false);
  async function create() {
    if (!name.trim()) return; setBusy(true);
    const p = await api.createProject({ name: name.trim(), description: desc.trim(), localPath: path.trim() });
    setBusy(false); setName(""); setDesc(""); setPath(""); onCreated && onCreated(p); onClose();
  }
  return (
    <Modal open={open} onClose={onClose} title="New project"
      footer={<><span className="faint" style={{ fontSize: 12 }}>Seeds Frontend, Backend & DevOps members.</span>
        <button className="btn primary" onClick={create} disabled={busy}>{busy ? "Creating…" : "Create"}</button></>}>
      <div><label>Name</label><input value={name} onChange={(e) => setName(e.target.value)} placeholder="Organics" /></div>
      <div><label>Description (the AI proposes components from this)</label>
        <textarea rows={3} value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="Next.js storefront + NestJS API on Azure" /></div>
      <div>
        <label>Where to create it (any folder on your disk)</label>
        <div className="row">
          <input value={path} onChange={(e) => setPath(e.target.value)} placeholder="/Users/you/Desktop/my-projects" />
          <button className="btn" onClick={async () => { const p = window.odin && (await window.odin.pickFolder()); if (p) setPath(p); }}>Browse…</button>
        </div>
        <div className="faint" style={{ fontSize: 11 }}>Pick a parent folder — a subfolder named after the project is created there. Leave blank for none.</div>
      </div>
    </Modal>
  );
}

export function AddMemberModal({ pid, open, onClose, onAdded }) {
  const [desc, setDesc] = useState(""); const [busy, setBusy] = useState(false);
  // editable fields the AI recommendation fills in — the owner ACCEPTS or EDITS before creating.
  const [name, setName] = useState(""); const [role, setRole] = useState(""); const [avatar, setAvatar] = useState("generic");
  const [nature, setNature] = useState("technical"); const [edesc, setEdesc] = useState("");
  const [resources, setResources] = useState(""); const [env, setEnv] = useState([]); const [got, setGot] = useState(false);
  async function suggest() {
    if (!desc.trim()) return; setBusy(true);
    const s = await api.suggestAgent(pid, desc.trim()); setBusy(false);
    setName(s.suggestedName || "Member"); setRole(s.role || "Specialist"); setAvatar(s.avatar || "generic");
    setNature(s.nature || "technical"); setEdesc(s.description || desc.trim());
    setResources(s.resources || ""); setEnv(s.env || []); setGot(true);
  }
  function setEnvRow(i, k, v) { setEnv(env.map((e, j) => j === i ? { key: k, value: v } : e)); }
  function reset() { setDesc(""); setGot(false); setName(""); setRole(""); setResources(""); setEnv([]); }
  async function add() {
    if (!name.trim()) return;
    await api.addAgent(pid, { name: name.trim(), role: role.trim(), avatar, nature, description: edesc.trim(),
                              resources, env: env.filter(e => e.key) });
    reset(); onAdded && onAdded(); onClose();
  }
  return (
    <Modal open={open} onClose={() => { reset(); onClose(); }} title="Add team member"
      footer={<><button className="btn" onClick={suggest} disabled={busy}>{busy ? "Thinking…" : (got ? "Re-suggest" : "Suggest with AI")}</button>
        <button className="btn primary" onClick={add} disabled={!got || !name.trim()}>Create member</button></>}>
      <div><label>Describe the role & responsibilities</label>
        <textarea rows={2} value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="e.g. operates our Mailchimp account — builds campaigns and reports email metrics" /></div>
      {got && (
        <div className="col" style={{ gap: 10, marginTop: 8 }}>
          <div className="faint" style={{ fontSize: 12 }}>AI recommendation — review and edit anything before creating:</div>
          <div className="row" style={{ gap: 8 }}>
            <div style={{ flex: 1 }}><label>Name</label><input value={name} onChange={(e) => setName(e.target.value)} /></div>
            <div style={{ flex: 1 }}><label>Role</label><input value={role} onChange={(e) => setRole(e.target.value)} /></div>
            <div><label>Nature</label>
              <select value={nature} onChange={(e) => setNature(e.target.value)}>
                <option value="technical">technical</option><option value="operational">operational</option>
              </select></div>
          </div>
          <div><label>Description</label><textarea rows={2} value={edesc} onChange={(e) => setEdesc(e.target.value)} /></div>
          <div><label>Allowed Resources & Dependencies (what it has, where its keys live, what to ask if missing)</label>
            <textarea rows={7} style={{ fontFamily: "monospace", fontSize: 12 }} value={resources} onChange={(e) => setResources(e.target.value)} /></div>
          <div><label>Environment variables (keys this agent may use)</label>
            {env.map((e, i) => (
              <div className="row" key={i} style={{ gap: 6, marginBottom: 4 }}>
                <input style={{ flex: 1 }} placeholder="KEY" value={e.key} onChange={(ev) => setEnvRow(i, ev.target.value, e.value)} />
                <input style={{ flex: 2 }} placeholder="value (optional)" value={e.value || ""} onChange={(ev) => setEnvRow(i, e.key, ev.target.value)} />
                <button className="btn sm" onClick={() => setEnv(env.filter((_, j) => j !== i))}>✕</button>
              </div>
            ))}
            <button className="btn sm" onClick={() => setEnv([...env, { key: "", value: "" }])}>＋ Add variable</button>
          </div>
        </div>
      )}
    </Modal>
  );
}

// Edit an EXISTING member's Resources & Dependencies + env from the dashboard.
export function EditMemberModal({ pid, member, open, onClose, onSaved }) {
  const [resources, setResources] = useState(""); const [env, setEnv] = useState([]); const [desc, setDesc] = useState(""); const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!open || !member) return;
    (async () => { const a = await api.agent(pid, member); setResources(a.resources || ""); setEnv(a.env || []); setDesc(a.description || ""); })();
  }, [open, member, pid]);
  function setEnvRow(i, k, v) { setEnv(env.map((e, j) => j === i ? { key: k, value: v } : e)); }
  async function save() {
    setBusy(true);
    await api.updateAgent(pid, member, { description: desc, resources, env: env.filter(e => e.key) });
    setBusy(false); onSaved && onSaved(); onClose();
  }
  return (
    <Modal open={open} onClose={onClose} title={`Edit ${member} — resources & env`}
      footer={<button className="btn primary" onClick={save} disabled={busy}>{busy ? "Saving…" : "Save"}</button>}>
      <div><label>Description</label><textarea rows={2} value={desc} onChange={(e) => setDesc(e.target.value)} /></div>
      <div><label>Allowed Resources & Dependencies</label>
        <textarea rows={9} style={{ fontFamily: "monospace", fontSize: 12 }} value={resources} onChange={(e) => setResources(e.target.value)} /></div>
      <div><label>Environment variables (e.g. set a new Mailchimp key for this project)</label>
        {env.map((e, i) => (
          <div className="row" key={i} style={{ gap: 6, marginBottom: 4 }}>
            <input style={{ flex: 1 }} placeholder="KEY" value={e.key} onChange={(ev) => setEnvRow(i, ev.target.value, e.value)} />
            <input style={{ flex: 2 }} placeholder="value" value={e.value || ""} onChange={(ev) => setEnvRow(i, e.key, ev.target.value)} />
            <button className="btn sm" onClick={() => setEnv(env.filter((_, j) => j !== i))}>✕</button>
          </div>
        ))}
        <button className="btn sm" onClick={() => setEnv([...env, { key: "", value: "" }])}>＋ Add variable</button>
      </div>
    </Modal>
  );
}

export function ScheduleModal({ pid, open, onClose, onSaved, agents = [] }) {
  const [prompt, setPrompt] = useState(""); const [kind, setKind] = useState("daily"); const [hhmm, setHhmm] = useState("06:00"); const [seconds, setSeconds] = useState(3600);
  const [assignee, setAssignee] = useState("");
  async function save() {
    if (!prompt.trim()) return;
    const schedule = kind === "daily" ? { kind, hhmm } : kind === "interval" ? { kind, seconds: Number(seconds) } : { kind: "once", at: Date.now() / 1000 + 60 };
    await api.createSchedule({ pid, prompt: prompt.trim(), schedule, assignee }); setPrompt(""); onSaved && onSaved(); onClose();
  }
  return (
    <Modal open={open} onClose={onClose} title="Schedule a recurring task"
      footer={<button className="btn primary" onClick={save}>Schedule</button>}>
      <div><label>Prompt to run</label><textarea rows={2} value={prompt} onChange={(e) => setPrompt(e.target.value)} placeholder="e.g. scan dependencies for vulnerabilities and report" /></div>
      <div><label>Run as agent (optional — makes it a periodic agent like a security checker)</label>
        <select value={assignee} onChange={(e) => setAssignee(e.target.value)}>
          <option value="">Project CTO (default)</option>
          {agents.map((a) => <option key={a.name} value={a.name}>{a.name} — {a.role}</option>)}
        </select></div>
      <div className="row">
        <div style={{ flex: 1 }}><label>When</label>
          <select value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="daily">Daily at…</option><option value="interval">Every N seconds</option><option value="once">Once (in 1 min)</option>
          </select></div>
        {kind === "daily" && <div style={{ flex: 1 }}><label>Time</label><input value={hhmm} onChange={(e) => setHhmm(e.target.value)} /></div>}
        {kind === "interval" && <div style={{ flex: 1 }}><label>Seconds</label><input type="number" value={seconds} onChange={(e) => setSeconds(e.target.value)} /></div>}
      </div>
    </Modal>
  );
}

export function MapModal({ pid, open, onClose, onSaved }) {
  const [local, setLocal] = useState(""); const [cloud, setCloud] = useState(""); const [role, setRole] = useState("frontend");
  async function save() { if (!local || !cloud) return; await api.addMapping(pid, { local, cloud, role }); setLocal(""); setCloud(""); onSaved && onSaved(); onClose(); }
  return (
    <Modal open={open} onClose={onClose} title="Map local ↔ cloud folder"
      footer={<button className="btn primary" onClick={save}>Add mapping</button>}>
      <div><label>Local folder</label><input value={local} onChange={(e) => setLocal(e.target.value)} placeholder="~/Desktop/organics-frontend" /></div>
      <div><label>Cloud / VM destination</label><input value={cloud} onChange={(e) => setCloud(e.target.value)} placeholder="~/organics (django-vm)" /></div>
      <div><label>Role</label><select value={role} onChange={(e) => setRole(e.target.value)}>
        <option value="frontend">frontend</option><option value="backend">backend</option><option value="other">other</option></select></div>
      <div className="faint" style={{ fontSize: 11.5 }}>Sync/deploy stays approval-gated and excludes .env — nothing runs without your OK.</div>
    </Modal>
  );
}

/* ============================================================================
   BellNotification — top-bar bell (always a "1" badge) → invite → two animated
   tabs: "The Story" (why we needed shared context) and "Caching" (what we built).
   Self-contained: its own keyframes + SVG, no external CSS needed.
============================================================================ */
const BELL_CSS = `
@keyframes odn-ring { 0%,92%,100%{transform:rotate(0)} 94%{transform:rotate(12deg)} 96%{transform:rotate(-10deg)} 98%{transform:rotate(6deg)} }
@keyframes odn-badge { 0%,100%{transform:scale(1);box-shadow:0 0 0 0 rgba(122,240,208,.55)} 50%{transform:scale(1.12);box-shadow:0 0 0 6px rgba(122,240,208,0)} }
@keyframes odn-pop { from{opacity:0;transform:translateY(-8px) scale(.97)} to{opacity:1;transform:translateY(0) scale(1)} }
@keyframes odn-fade { from{opacity:0;transform:translateY(8px)} to{opacity:1;transform:translateY(0)} }
@keyframes odn-drift { 0%{transform:translateX(0);fill:#7af0d0} 45%{transform:translateX(46px);fill:#ff6b81} 55%{transform:translateX(46px);fill:#ff6b81} 100%{transform:translateX(0);fill:#7af0d0} }
@keyframes odn-pulse { 0%,100%{opacity:.35;r:26} 50%{opacity:.9;r:31} }
@keyframes odn-flow { 0%{offset-distance:0%;opacity:0} 12%{opacity:1} 88%{opacity:1} 100%{offset-distance:100%;opacity:0} }
@keyframes odn-dash { to{stroke-dashoffset:-24} }
@keyframes odn-tick { 0%{opacity:0;transform:scale(.6)} 60%{opacity:1;transform:scale(1.15)} 100%{opacity:1;transform:scale(1)} }
.odn-tabbtn{flex:1;padding:9px 0;border:0;border-radius:10px;cursor:pointer;font-weight:600;font-size:13px;transition:.18s;background:transparent;color:var(--txt-dim)}
.odn-tabbtn.on{background:linear-gradient(180deg,rgba(108,140,255,.22),rgba(122,240,208,.12));color:var(--txt);box-shadow:inset 0 0 0 1px var(--stroke-strong)}
`;

// 🔔 REAL NOTIFICATIONS — live feed for recurring/periodical work (read · mark · redirect · shakes on new).
export function NotificationsBell({ onOpenProject }) {
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const [shake, setShake] = useState(false);
  const prev = useRef(0);
  async function refresh() {
    const d = await api.notifications();
    setItems(d.items || []);
    const u = d.unread || 0;
    if (u > prev.current) { setShake(true); setTimeout(() => setShake(false), 2500); }
    prev.current = u; setUnread(u);
  }
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 12000); // keep the bell live so it shakes when a scheduled project runs
    return () => clearInterval(t);
  }, []);
  async function openOne(n) {
    if (!n.read) { await api.markNotif(n.id); refresh(); }
    if (n.pid && onOpenProject) { onOpenProject(n.pid); setOpen(false); }
  }
  return (
    <div style={{ position: "relative" }}>
      <style>{"@keyframes odn-shake{0%,100%{transform:rotate(0)}20%{transform:rotate(16deg)}40%{transform:rotate(-14deg)}60%{transform:rotate(10deg)}80%{transform:rotate(-8deg)}}"}</style>
      <button className="btn sm" title="Notifications — recurring & scheduled work"
        onClick={() => { setOpen((v) => !v); refresh(); }}
        style={{ position: "relative", width: 36, padding: 0, display: "grid", placeItems: "center" }}>
        <span style={{ display: "inline-block", fontSize: 16, animation: shake ? "odn-shake .6s ease-in-out 3" : "none",
          color: unread > 0 ? "var(--danger)" : undefined }}>🔔</span>
        {unread > 0 && (
          <span style={{ position: "absolute", top: -6, right: -6, minWidth: 17, height: 17, padding: "0 4px",
            borderRadius: 999, background: "var(--danger)", color: "#fff", fontSize: 11, fontWeight: 800,
            display: "grid", placeItems: "center" }}>{unread}</span>
        )}
      </button>
      {open && createPortal(
        <>
          {/* click-away backdrop; the panel is a FIXED portal on document.body so no ancestor (the scrolling
              top-bar, backdrop-filter, etc.) can clip it or bury it behind page content. */}
          <div onClick={() => setOpen(false)} style={{ position: "fixed", inset: 0, zIndex: 2147483000 }} />
          <div style={{ position: "fixed", top: 58, right: 16, zIndex: 2147483001, width: 360, maxHeight: "70vh", overflow: "auto",
            background: "var(--panel-solid)", border: "1px solid var(--stroke-strong)", borderRadius: 14,
            boxShadow: "0 24px 60px rgba(0,0,0,.55)" }}>
            <div className="row" style={{ justifyContent: "space-between", padding: "11px 13px", borderBottom: "1px solid var(--stroke)", position: "sticky", top: 0, background: "var(--panel-solid)" }}>
              <b style={{ fontSize: 13.5 }}>🔔 Notifications</b>
              <div className="row" style={{ gap: 8 }}>
                {unread > 0 && <button className="btn sm ghost" style={{ fontSize: 11 }} onClick={async () => { await api.markAllNotifs(); refresh(); }}>Mark all read</button>}
                <button className="btn sm ghost" onClick={() => setOpen(false)}>✕</button>
              </div>
            </div>
            {items.length === 0 ? (
              <div className="faint" style={{ padding: 22, fontSize: 12, textAlign: "center", lineHeight: 1.5 }}>
                No notifications yet. Scheduled & recurring projects report here when they run.</div>
            ) : items.map((n) => (
              <div key={n.id} onClick={() => openOne(n)} style={{ cursor: "pointer", padding: "10px 13px",
                borderBottom: "1px solid var(--stroke)", background: n.read ? "transparent" : "rgba(108,140,255,.06)" }}>
                <div className="row" style={{ gap: 8, alignItems: "flex-start" }}>
                  <span style={{ width: 8, height: 8, borderRadius: 999, marginTop: 5,
                    background: n.read ? "var(--stroke-strong)" : (n.severity === "critical" ? "var(--danger)" : n.severity === "attention" ? "var(--warn)" : "var(--brand-2)") }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 12.5, fontWeight: n.read ? 500 : 700 }}>{n.icon || "🔔"}  {n.title}</div>
                    {n.body && <div className="faint" style={{ fontSize: 11, marginTop: 2, lineHeight: 1.4 }}>{n.body}</div>}
                    {n.project && <div className="faint" style={{ fontSize: 10.5, marginTop: 3 }}>{n.project}  ·  click to open</div>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </>,
        document.body
      )}
    </div>
  );
}

// single source of truth for the desktop notification tabs → the badge auto-updates when tabs change
const BELL_TABS = ["story", "caching", "tests", "anchor", "links", "request", "livemeeting", "deploy", "soc"];
export function BellNotification() {
  const [open, setOpen] = useState(false);
  const [stage, setStage] = useState("invite");   // invite | details
  const [tab, setTab] = useState("story");          // story | caching | tests

  function close() { setOpen(false); setTimeout(() => { setStage("invite"); setTab("story"); }, 200); }

  return (
    <div style={{ position: "relative" }}>
      <style>{BELL_CSS}</style>
      <button className="btn sm" title="Guide — what's new & how-to" onClick={() => setOpen((v) => !v)}
        style={{ position: "relative", width: 36, padding: 0, display: "grid", placeItems: "center" }}>
        <span style={{ display: "inline-block", transformOrigin: "50% 4px", animation: "odn-ring 4s ease-in-out infinite", fontSize: 16 }}>📖</span>
        <span style={{ position: "absolute", top: -6, right: -6, minWidth: 17, height: 17, padding: "0 4px",
          borderRadius: 999, background: "var(--brand-2)", color: "#06231c", fontSize: 11, fontWeight: 800,
          display: "grid", placeItems: "center", animation: "odn-badge 2.2s ease-in-out infinite" }}>{BELL_TABS.length}</span>
      </button>

      {open && createPortal((
        <>
          {/* Rendered via a PORTAL to <body>: the top bar has backdrop-filter, which traps any
              position:fixed descendant inside its stacking context (that's why z-index alone failed).
              Portaling out of the top bar lets the panel truly float above everything. */}
          <div onClick={close} style={{ position: "fixed", inset: 0, zIndex: 2147483646 }} />
          <div style={{ position: "fixed", top: 58, right: 16,
            width: stage === "details" ? 440 : 320, maxWidth: "calc(100vw - 32px)",
            maxHeight: "calc(100vh - 80px)", overflowY: "auto", zIndex: 2147483647,
            background: "var(--panel-solid)", border: "1px solid var(--stroke-strong)", borderRadius: 16,
            boxShadow: "0 24px 60px rgba(0,0,0,.5)", animation: "odn-pop .22s ease both" }}>

            <div className="row" style={{ justifyContent: "space-between", padding: "13px 15px", borderBottom: "1px solid var(--stroke)", position: "sticky", top: 0, background: "var(--panel-solid)" }}>
              <b style={{ fontSize: 14 }}>✨ New in Odin</b>
              <span onClick={close} style={{ cursor: "pointer", color: "var(--txt-dim)", fontSize: 18, lineHeight: 1 }}>×</span>
            </div>

            {stage === "invite" && (
              <div style={{ padding: 16, animation: "odn-fade .3s both" }}>
                <div style={{ fontSize: 13.5, color: "var(--txt)", lineHeight: 1.55 }}>
                  Your agents just got a memory. We taught them to <b style={{ color: "var(--brand-2)" }}>reuse proven work</b> instead
                  of rebuilding it every time — so tasks finish faster and more reliably.
                </div>
                <button className="btn primary" style={{ width: "100%", marginTop: 14 }}
                  onClick={() => setStage("details")}>See how it works →</button>
              </div>
            )}

            {stage === "details" && (
              <div style={{ animation: "odn-fade .3s both" }}>
                <div className="row" style={{ gap: 6, padding: 10 }}>
                  <button className={"odn-tabbtn" + (tab === "story" ? " on" : "")} onClick={() => setTab("story")}>① Story</button>
                  <button className={"odn-tabbtn" + (tab === "caching" ? " on" : "")} onClick={() => setTab("caching")}>② Caching</button>
                  <button className={"odn-tabbtn" + (tab === "tests" ? " on" : "")} onClick={() => setTab("tests")}>③ Tests</button>
                  <button className={"odn-tabbtn" + (tab === "anchor" ? " on" : "")} onClick={() => setTab("anchor")}>④ Anchor</button>
                  <button className={"odn-tabbtn" + (tab === "links" ? " on" : "")} onClick={() => setTab("links")}>⑤ Links</button>
                  <button className={"odn-tabbtn" + (tab === "request" ? " on" : "")} onClick={() => setTab("request")}>⑥ Request</button>
                  <button className={"odn-tabbtn" + (tab === "livemeeting" ? " on" : "")} onClick={() => setTab("livemeeting")}>⑦ Live Meeting</button>
                  <button className={"odn-tabbtn" + (tab === "deploy" ? " on" : "")} onClick={() => setTab("deploy")}>⑧ Deploy</button>
                  <button className={"odn-tabbtn" + (tab === "soc" ? " on" : "")} onClick={() => setTab("soc")}>⑨ Security SOC</button>
                </div>
                <div style={{ padding: "4px 16px 18px" }}>
                  {tab === "story" ? <StoryTab /> : tab === "caching" ? <CachingTab /> : tab === "anchor" ? <AnchorDocTab /> : tab === "links" ? <LinksDocTab /> : tab === "request" ? <RequestPageTab /> : tab === "livemeeting" ? <LiveMeetingTab /> : tab === "deploy" ? <DeployTab /> : tab === "soc" ? <SocTab /> : <TestsTab />}
                </div>
              </div>
            )}
          </div>
        </>
      ), document.body)}
    </div>
  );
}

function LinksDocTab() {
  const grp = (title, items) => (
    <div style={{ marginBottom: 10 }}>
      <div style={{ fontSize: 12.5, fontWeight: 700, color: "var(--brand-2)", marginBottom: 4 }}>{title}</div>
      {items.map((s, i) => (
        <div key={i} style={{ fontSize: 11.5, color: "var(--txt-dim)", fontFamily: "ui-monospace,Menlo,monospace", lineHeight: 1.5 }}>• {s}</div>
      ))}
    </div>
  );
  return (
    <div key="links" style={{ animation: "odn-fade .35s both" }}>
      <div style={{ fontSize: 13.5, color: "var(--txt)", fontWeight: 700, marginBottom: 2 }}>🔗 Important files & links</div>
      <div style={{ fontSize: 11, color: "var(--txt-faint)", marginBottom: 10 }}>Paths under ~/Desktop/AiAgentWorkSpace.</div>
      {grp("Paper & article (previous)", [
        "Resulted Papers and Documents/odin_paper.pdf (.docx, .tex)",
        "Resulted Papers and Documents/engineering_journey.pdf (.docx, .md)",
        "Resulted Papers and Documents/venue_submission_guide.pdf (.docx)",
        "Resulted Papers and Documents/Social Media/linkedin_post.docx · instagram_post.docx",
      ])}
      {grp("Current docs", [
        "Odin-Orchestrator/docs/ODIN_PHASES_TECH_DOC.pdf (.md)",
        "Odin-Orchestrator/docs/odin_pipeline.html",
        "Odin-Orchestrator/ANCHOR_CONTRACT.md",
        "Odin-Orchestrator/README_ANCHOR_AND_INTEGRATIONS.md",
      ])}
      {grp("Key code", [
        "server/anchor_queue.py · anchor.py · anchor_remote.py",
        "server/local_poller_http.py · webhook_receiver.py · auth.py",
        "server/integrations/klaviyo.py · veeqo.py",
        "server/e2e_anchor_all.py · e2e_phase2.py · third_party.py",
        "odin_app/lib (Flutter) · desktop/src/views.jsx",
        "third_party_sim.html · phase2_up.sh",
      ])}
    </div>
  );
}

function RequestPageTab() {
  const [status, setStatus] = useState("");   // "" | starting | ok | err
  const [msg, setMsg] = useState("");
  const cmd = "cd ~/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2 && python3 -m http.server 9104 --bind 127.0.0.1";
  const url = "http://localhost:9104/anchor_sim.html?env=prod";
  async function run() {
    setStatus("starting"); setMsg("");
    try {
      if (window.odin && window.odin.startRequestPage) {
        const r = await window.odin.startRequestPage();
        if (r && r.ok) { setStatus("ok"); setMsg("Started — opening it in your browser…"); }
        else { setStatus("err"); setMsg((r && r.error) || "Couldn't start it here — run the command below in a terminal."); }
      } else { setStatus("err"); setMsg("Open this from the desktop app, or run the command below."); }
    } catch (e) { setStatus("err"); setMsg(String((e && e.message) || e)); }
  }
  async function copy() { try { await navigator.clipboard.writeText(cmd); setMsg("Command copied."); setStatus(""); } catch {} }
  return (
    <div key="request" style={{ animation: "odn-fade .35s both" }}>
      <div style={{ fontSize: 13.5, color: "var(--txt)", fontWeight: 700, marginBottom: 4 }}>🛰️ The Request page</div>
      <div style={{ fontSize: 12, color: "var(--txt-dim)", lineHeight: 1.6, marginBottom: 10 }}>
        A local page third parties use to send tasks to your projects <b style={{ color: "var(--brand-2)" }}>through the anchor</b>.
        It's a lightweight static page — it just needs a small local server to be reachable. If it shows a 404 or
        won't open, that server isn't running. Start it with one click.
      </div>
      <div style={{
        background: "linear-gradient(180deg, rgba(108,140,255,.14), rgba(122,240,208,.06))",
        border: "1px solid var(--stroke-strong)", borderRadius: 12, padding: "10px 12px", marginBottom: 10,
      }}>
        <div style={{ fontSize: 10.5, color: "var(--brand-2)", fontWeight: 800, letterSpacing: .5, marginBottom: 5 }}>▹ SHELL</div>
        <code style={{ display: "block", fontFamily: "ui-monospace,Menlo,monospace", fontSize: 11, color: "var(--txt)", whiteSpace: "pre-wrap", wordBreak: "break-all", lineHeight: 1.55 }}>{cmd}</code>
        <div className="row" style={{ gap: 6, marginTop: 9 }}>
          <button className="btn primary" style={{ flex: 1 }} onClick={run} disabled={status === "starting"}>
            {status === "starting" ? "Starting…" : "▶ Run it & open"}
          </button>
          <button className="btn sm" onClick={copy} title="Copy the command">Copy</button>
        </div>
      </div>
      <div style={{ fontSize: 11.5, color: "var(--txt-dim)" }}>
        Opens: <span style={{ fontFamily: "ui-monospace,Menlo,monospace", color: "var(--txt)" }}>{url}</span>
      </div>
      {msg && (
        <div style={{ marginTop: 8, fontSize: 11.5, fontWeight: 600, color: status === "err" ? "#ff6b81" : "var(--ok)" }}>
          {status === "ok" ? "✓ " : status === "err" ? "⚠ " : ""}{msg}
        </div>
      )}
    </div>
  );
}

function AnchorDocTab() {
  const row = { fontSize: 12, color: "var(--txt-dim)", lineHeight: 1.6, margin: "2px 0" };
  const code = { fontFamily: "ui-monospace,Menlo,monospace", fontSize: 11.5, color: "var(--txt)", background: "rgba(255,255,255,.05)", padding: "1px 5px", borderRadius: 5 };
  return (
    <div key="anchor" style={{ animation: "odn-fade .35s both" }}>
      <div style={{ fontSize: 13.5, color: "var(--txt)", fontWeight: 700, marginBottom: 6 }}>🔌 Klaviyo · Veeqo · Anchor Connect</div>
      <svg viewBox="0 0 300 150" style={{ width: "100%", height: 150, marginBottom: 4 }}>
        {[["TP", 8], ["Anchor", 66], ["Local", 124], ["Agents", 182], ["Klav/Veeqo", 240]].map(([t, x], i) => (
          <g key={i}>
            <rect x={x} y="34" width="52" height="30" rx="7" fill="rgba(108,140,255,.13)" stroke={i === 1 ? "var(--brand-2)" : "var(--brand)"} strokeWidth="1.3"
              style={i === 1 ? { animation: "odn-ringpulse 2.6s ease-in-out infinite" } : undefined} />
            <text x={x + 26} y="52" textAnchor="middle" fontSize="8.5" fill="var(--txt-dim)" fontWeight="700">{t}</text>
          </g>
        ))}
        {[60, 118, 176, 234].map((x, i) => (
          <g key={"c" + i}>
            <path d={`M${x} 49 H${x + 6}`} stroke="var(--stroke-strong)" strokeWidth="2" strokeDasharray="4 4" style={{ animation: "odn-dash 1s linear infinite" }} />
            <circle r="3.5" fill="var(--brand-2)" style={{ offsetPath: `path('M${x} 49 H${x + 6}')`, animation: `odn-flow 2.6s ease-in-out ${i * 0.3}s infinite` }} />
          </g>
        ))}
        {/* result + webhook return path */}
        <path id="odn-ret" d="M266 64 V96 H30 V64" fill="none" stroke="rgba(122,240,208,.5)" strokeWidth="2" strokeDasharray="4 4" style={{ animation: "odn-dash 1s linear infinite" }} />
        <circle r="3.5" fill="var(--ok)" style={{ offsetPath: "path('M266 64 V96 H30 V64')", animation: "odn-flow 3s ease-in-out infinite" }} />
        <text x="150" y="112" textAnchor="middle" fontSize="8.5" fill="var(--brand-2)">result → POST /result → webhook → 2xx ack → finished</text>
        <text x="150" y="128" textAnchor="middle" fontSize="8" fill="var(--txt-faint)">POST /requests · X-API-Key · project id · prompt · webhook_url</text>
        <text x="150" y="142" textAnchor="middle" fontSize="8" fill="var(--txt-faint)">GET /poll → CTO→team → read-only GET</text>
      </svg>
      <div style={row}>Klaviyo (Email) + Veeqo (Shipping) read‑only integrations, and the Anchor — a queue + auth + webhooks layer so third parties and your remote app reach local projects.</div>
      <div style={row}>Flow: third party → anchor (:9100) → local poller → CTO→team on the brain → real Klaviyo/Veeqo data → webhook back → ack → finished.</div>
      <div style={{ fontWeight: 700, fontSize: 12.5, color: "var(--txt)", margin: "10px 0 4px" }}>How to test</div>
      <div style={row}>• Everything up: <span style={code}>./phase2_up.sh</span></div>
      <div style={row}>• Integrations + anchor: <span style={code}>python3 server/e2e_anchor_all.py</span> (prints 50 flows 28/22, 26 orders)</div>
      <div style={row}>• Topology: <span style={code}>python3 server/e2e_phase2.py</span></div>
      <div style={row}>• Be a third party: <span style={code}>third_party_sim.html</span> or <span style={code}>server/third_party.py</span></div>
      <div style={row}>• See webhook + ack: <span style={code}>server/webhook_receiver.py --port 9300</span></div>
      <div style={row}>Full doc: <span style={code}>docs/ODIN_PHASES_TECH_DOC.pdf</span> · contract: <span style={code}>ANCHOR_CONTRACT.md</span></div>
    </div>
  );
}

function StoryTab() {
  return (
    <div key="story" style={{ animation: "odn-fade .35s both" }}>
      <svg viewBox="0 0 300 130" style={{ width: "100%", height: 130 }}>
        {/* central shared-context pool */}
        <circle cx="150" cy="65" r="26" fill="rgba(122,240,208,.12)" stroke="var(--brand-2)" strokeWidth="1.5" style={{ animation: "odn-pulse 3s ease-in-out infinite" }} />
        <text x="150" y="62" textAnchor="middle" fontSize="9" fill="var(--brand-2)" fontWeight="700">SHARED</text>
        <text x="150" y="73" textAnchor="middle" fontSize="9" fill="var(--brand-2)" fontWeight="700">CONTEXT</text>
        {/* two agents */}
        <g fontSize="10" fill="var(--txt-dim)" fontWeight="600">
          <circle cx="40" cy="65" r="16" fill="rgba(108,140,255,.15)" stroke="var(--brand)" strokeWidth="1.3" />
          <text x="40" y="68" textAnchor="middle">A1</text>
          <circle cx="260" cy="65" r="16" fill="rgba(108,140,255,.15)" stroke="var(--brand)" strokeWidth="1.3" />
          <text x="260" y="68" textAnchor="middle">A2</text>
        </g>
        {/* connecting lines (animated flow) */}
        <path d="M56 65 H124" stroke="var(--stroke-strong)" strokeWidth="2" strokeDasharray="4 4" style={{ animation: "odn-dash 1s linear infinite" }} />
        <path d="M176 65 H244" stroke="var(--stroke-strong)" strokeWidth="2" strokeDasharray="4 4" style={{ animation: "odn-dash 1s linear infinite" }} />
        {/* a token that used to drift apart, now kept identical */}
        <rect x="80" y="20" width="14" height="14" rx="3" style={{ animation: "odn-drift 4s ease-in-out infinite" }} />
        <text x="150" y="118" textAnchor="middle" fontSize="9" fill="var(--txt-faint)">one source of truth — no drift between agents</text>
      </svg>
      <div style={{ fontSize: 12.5, color: "var(--txt-dim)", lineHeight: 1.6, marginTop: 6 }}>
        When a job is split across agents, each used to see only its slice — details drifted and results
        clashed. Now every agent reads from <b style={{ color: "var(--brand-2)" }}>one growing shared context</b> (the
        CTO's plan + everyone's work), and appends back to it. Same picture for all → consistent results.
      </div>
    </div>
  );
}

function CachingTab() {
  const steps = [
    { i: "📥", t: "A task arrives for a role (e.g. DevOps)." },
    { i: "🔎", t: "The agent fetches its pool folder + reads each module's metadata." },
    { i: "🧠", t: "It DECIDES: does a proven module match? If yes — configure & reuse." },
    { i: "⚡", t: "Reused, not rebuilt → faster, and already battle-tested." },
  ];
  return (
    <div key="caching" style={{ animation: "odn-fade .35s both" }}>
      <svg viewBox="0 0 300 96" style={{ width: "100%", height: 96 }}>
        <rect x="10" y="30" width="84" height="40" rx="8" fill="rgba(108,140,255,.12)" stroke="var(--brand)" strokeWidth="1.3" />
        <text x="52" y="47" textAnchor="middle" fontSize="9" fill="var(--txt-dim)" fontWeight="700">NEW TASK</text>
        <text x="52" y="59" textAnchor="middle" fontSize="9" fill="var(--txt-dim)">role: DevOps</text>
        <rect x="206" y="22" width="84" height="56" rx="8" fill="rgba(122,240,208,.12)" stroke="var(--brand-2)" strokeWidth="1.3" />
        <text x="248" y="40" textAnchor="middle" fontSize="9" fill="var(--brand-2)" fontWeight="700">POOL</text>
        <text x="248" y="53" textAnchor="middle" fontSize="8" fill="var(--brand-2)">cloud_deploy.sh</text>
        <text x="248" y="64" textAnchor="middle" fontSize="8" fill="var(--ok)">✓ working</text>
        <path id="odn-track" d="M94 50 H206" stroke="var(--stroke-strong)" strokeWidth="2" strokeDasharray="4 4" />
        <circle r="5" fill="var(--brand-2)" style={{ offsetPath: "path('M94 50 H206')", animation: "odn-flow 2.4s ease-in-out infinite" }} />
      </svg>
      <div style={{ fontSize: 11, color: "var(--txt-faint)", fontFamily: "ui-monospace,monospace", background: "rgba(255,255,255,.03)",
        border: "1px solid var(--stroke)", borderRadius: 8, padding: "7px 9px", margin: "2px 0 10px" }}>
        cached_modules/<span style={{ color: "var(--brand-2)" }}>DevOps</span>/cloud_deploy.sh + .meta.json
      </div>
      <div className="col" style={{ gap: 8 }}>
        {steps.map((s, k) => (
          <div key={k} className="row" style={{ gap: 9, alignItems: "flex-start", animation: `odn-tick .4s ${0.15 * k}s both` }}>
            <span style={{ fontSize: 15, width: 20, textAlign: "center" }}>{s.i}</span>
            <span style={{ fontSize: 12.5, color: "var(--txt-dim)", lineHeight: 1.45 }}>{s.t}</span>
          </div>
        ))}
      </div>
      <div style={{ fontSize: 11.5, color: "var(--txt-faint)", lineHeight: 1.5, marginTop: 11, paddingTop: 9, borderTop: "1px solid var(--stroke)" }}>
        The library only grows from work that <b style={{ color: "var(--brand-2)" }}>actually succeeded</b> — never filler.
        Each script carries safe defaults (keeps ports 80/443 open, never syncs secrets, never reboots unless asked).
      </div>
    </div>
  );
}

function LiveMeetingTab() {
  const steps = [
    { i: "🗣️", t: "Open a meeting/voice project. In the chat header (normal AND chat mode) tap the speaking-head icon (next to ▶) — not the plain dictation mic." },
    { i: "🎙️", t: "A popup dialog opens (web/desktop) or a native sheet (mobile). Allow mic, then Start: big mic, live sensitivity, voice-activity, noise & language, chunks saving 1,2,3…" },
    { i: "⏸️", t: "Pause/Resume anytime. Each chunk is transcribed live; low-confidence chunks are marked for review." },
    { i: "🧠", t: "Stop → chunks are refined (fillers/duplicates/noise removed; names, commands, APIs, dates kept) → one 13-section smart report in the meeting's language." },
    { i: "📄", t: "The report shows in the dialog AND is embedded into the project chat as Markdown. Click Close when done." },
    { i: "⬇️", t: "Export: Markdown or Word (.docx), Arabic or English — or “All 4” as one zip. DOCX is clean, colorful, structured." },
  ];
  return (
    <div key="livemeeting" style={{ animation: "odn-fade .35s both" }}>
      <div style={{ fontSize: 13.5, fontWeight: 700, marginBottom: 2 }}>🗣️ Live Meeting — voice → smart report</div>
      <div style={{ fontSize: 11, color: "var(--txt-faint)", marginBottom: 10 }}>A reusable app asset owned by the Live Meeting &amp; Voice Streaming Agent. Web · desktop · mobile.</div>
      <div className="col" style={{ gap: 8 }}>
        {steps.map((s, k) => (
          <div key={k} className="row" style={{ gap: 9, alignItems: "flex-start", animation: `odn-tick .4s ${0.12 * k}s both` }}>
            <span style={{ fontSize: 15, width: 20, textAlign: "center" }}>{s.i}</span>
            <span style={{ fontSize: 12.5, color: "var(--txt-dim)", lineHeight: 1.45 }}>{s.t}</span>
          </div>
        ))}
      </div>
      <div style={{ fontSize: 11.5, color: "var(--txt-faint)", lineHeight: 1.5, marginTop: 11, paddingTop: 9, borderTop: "1px solid var(--stroke)" }}>
        📚 Docs: <span style={{ color: "var(--brand-2)", fontFamily: "ui-monospace,monospace" }}>assets/global_voice_streaming_asset.md · docs/WHATS_NEW.md</span>
      </div>
    </div>
  );
}

function DeployTab() {
  const steps = [
    { i: "📦", t: "The deployment project (e.g. “Organics Production Deploy (2VM)”) is created through the real intake flow — DevOps-only, no other agents." },
    { i: "🔒", t: "Source-of-truth folders (organics-backend/frontend) are read-only. Working copy + a .git baseline live under ~/Desktop/misc/Odin/." },
    { i: "🚩", t: "Persistent first-time flag: first deploy ships everything; later deploys diff the .git baseline and ship ONLY changed files." },
    { i: "⚙️", t: "Preview the exact rsync + build commands + reboot, respecting the exclusion lists (.env, node_modules, dist, .next, migrations, package*.json, public, uploads…)." },
    { i: "🗄️", t: "Database reset runs only the first time; every later deploy ASKS before any DB reset. Nothing destructive runs without your approval." },
    { i: "✅", t: "After reboot: health checks (domain, backend, frontend, nginx, systemd) confirm the update is really live on the Azure VM." },
  ];
  return (
    <div key="deploy" style={{ animation: "odn-fade .35s both" }}>
      <div style={{ fontSize: 13.5, fontWeight: 700, marginBottom: 2 }}>🚀 Deploy — DevOps to the Azure VM</div>
      <div style={{ fontSize: 11, color: "var(--txt-faint)", marginBottom: 10 }}>Corrected, repeatable production deploy. Source = local machine → destination = Azure VM.</div>
      <div className="col" style={{ gap: 8 }}>
        {steps.map((s, k) => (
          <div key={k} className="row" style={{ gap: 9, alignItems: "flex-start", animation: `odn-tick .4s ${0.12 * k}s both` }}>
            <span style={{ fontSize: 15, width: 20, textAlign: "center" }}>{s.i}</span>
            <span style={{ fontSize: 12.5, color: "var(--txt-dim)", lineHeight: 1.45 }}>{s.t}</span>
          </div>
        ))}
      </div>
      <div style={{ fontSize: 11.5, color: "var(--txt-faint)", lineHeight: 1.5, marginTop: 11, paddingTop: 9, borderTop: "1px solid var(--stroke)" }}>
        📚 Docs: <span style={{ color: "var(--brand-2)", fontFamily: "ui-monospace,monospace" }}>docs/WHATS_NEW.md · infra/deploy.config.sh</span>
      </div>
    </div>
  );
}

function SocTab() {
  const agents = [
    { i: "🧭", t: "CTO Orchestrator — governs each run, correlates everyone into a root cause, raises approvals (approves nothing itself)." },
    { i: "🗺️", t: "Asset & Attack-Surface — living inventory of every cloud/VM/stack (Azure now; extensible to AWS/GoDaddy/Hostinger/Cloudflare) + reverse-search targeting." },
    { i: "🧠", t: "Threat-Hunting Architect — current advisories (OSV.dev) for OUR versions, triaged by reachability; keeps playbooks current." },
    { i: "🔎", t: "Operations Investigator — read-only checks: services, ports/NSG/ufw, website, SSH, persistence, miner hunt, abuse, DB, deps." },
    { i: "🕵️", t: "Behavioral Analytics (UEBA) — stealthy/AI-era abuse by behaviour (same-IP-many-accounts, low-and-slow); excludes YOUR dynamic IP." },
    { i: "🔮", t: "Prediction & Prevention — predicts the NEXT weakness and hardens before exploitation." },
    { i: "🛟", t: "Recovery & Resilience — encrypted dated backups (key on your desktop only) + smart date-aware recovery." },
    { i: "📝", t: "Reporting — branded report: plain-language first, then technical. PDF/DOCX/MD/PPTX." },
  ];
  return (
    <div key="soc" style={{ animation: "odn-fade .35s both" }}>
      <div style={{ fontSize: 13.5, fontWeight: 700, marginBottom: 2 }}>🛡️ RedBerry Continuous SOC</div>
      <div style={{ fontSize: 11, color: "var(--txt-faint)", marginBottom: 10, lineHeight: 1.5 }}>
        An always-on, monitor-and-report-only security company of 8 non-overlapping agents. Runs daily 11 PM (New York,
        DST-aware, with catch-up) and on demand. It changes nothing on its own — only decisions that recover or modify a
        working service need your approval.
      </div>
      <div className="col" style={{ gap: 7 }}>
        {agents.map((s, k) => (
          <div key={k} className="row" style={{ gap: 9, alignItems: "flex-start", animation: `odn-tick .4s ${0.08 * k}s both` }}>
            <span style={{ fontSize: 15, width: 20, textAlign: "center" }}>{s.i}</span>
            <span style={{ fontSize: 12.5, color: "var(--txt-dim)", lineHeight: 1.45 }}>{s.t}</span>
          </div>
        ))}
      </div>
      <div style={{ fontSize: 11.5, color: "var(--txt-dim)", lineHeight: 1.5, marginTop: 10 }}>
        Methodology: white-scope wide sweep → narrow to evidence (NIST 800-61 · SANS PICERL · threat-hunting funnel · MITRE ATT&CK).
        Reports &amp; backups live in the RedBerry-Continuous-SOC project folder.
      </div>
      <div style={{ fontSize: 11.5, color: "var(--txt-faint)", lineHeight: 1.6, marginTop: 11, paddingTop: 9, borderTop: "1px solid var(--stroke)" }}>
        📚 Learn: <span style={{ color: "var(--brand-2)", fontFamily: "ui-monospace,monospace" }}>docs/SOC_SECURITY_ROLES.md · docs/SOC_REDBERRY.md</span><br/>
        🔗 API: <span style={{ color: "var(--brand-2)", fontFamily: "ui-monospace,monospace" }}>/soc/status · /soc/run · /soc/report?fmt=pdf · /soc/inventory · /soc/behavior · /soc/recovery</span>
      </div>
    </div>
  );
}

function TestsTab() {
  const cmd = (c) => (
    <code style={{ display: "block", fontFamily: "ui-monospace,monospace", fontSize: 11,
      background: "rgba(255,255,255,.04)", border: "1px solid var(--stroke)", borderRadius: 7,
      padding: "6px 8px", margin: "3px 0 9px", color: "var(--brand-2)", whiteSpace: "pre-wrap" }}>{c}</code>
  );
  const row = (n, title, what) => (
    <div className="row" style={{ gap: 9, alignItems: "flex-start", marginBottom: 9, animation: `odn-tick .4s ${0.12 * n}s both` }}>
      <span style={{ fontSize: 14, width: 18, textAlign: "center", color: "var(--brand-2)" }}>{n}</span>
      <div className="col" style={{ gap: 1 }}>
        <b style={{ fontSize: 12.5 }}>{title}</b>
        <span style={{ fontSize: 11.5, color: "var(--txt-dim)", lineHeight: 1.45 }}>{what}</span>
      </div>
    </div>
  );
  return (
    <div key="tests" style={{ animation: "odn-fade .35s both" }}>
      <div style={{ fontSize: 12.5, color: "var(--txt-dim)", lineHeight: 1.55, marginBottom: 10 }}>
        Nothing here is trusted without proof. These end‑to‑end tests are how we verify the work —
        and they're built to be <b style={{ color: "var(--brand-2)" }}>un‑gameable</b> (a green that was
        massaged is treated as a failure). Run them from the <code>server/</code> folder:
      </div>
      {row(1, "Full acceptance gate", "Phase 1 shared context (runtime tokens across hops) · Phase 2 DB migrate deploy+reset on a throwaway DB with production fingerprinted · Phase 3 the new features. Later phases never relax earlier ones.")}
      {cmd("python3 e2e_phase2_gate.py")}
      {row(2, "Cache speedup timing", "Runs the same task with the cache OFF (baseline) then ON, and reports the measured time — real numbers only, never faked.")}
      {cmd("python3 e2e_cache_timing.py")}
      {row(3, "No‑cache baseline toggle", "Any run can hide the module pool to measure 'from scratch' — empty the pool folder, or set the flag:")}
      {cmd("ODIN_DISABLE_CACHE=1 python3 e2e_cache_timing.py")}
      <div style={{ fontSize: 11.5, color: "var(--txt-faint)", lineHeight: 1.5, marginTop: 4, paddingTop: 9, borderTop: "1px solid var(--stroke)" }}>
        The gate's Phase 1/2 need the live engine + VM; Phase 3 runs standalone and self‑cleans. A
        red test that finds a real bug beats a green one that was tuned to pass.
      </div>
    </div>
  );
}

/* ============================================================================
   PeriodicApprovalWatcher — global. Polls for periodic tasks that came due while
   the device is on, and asks the owner to start them (approve) or skip. Nothing
   periodic runs unattended.
============================================================================ */
export function PeriodicApprovalWatcher() {
  const [pending, setPending] = useState([]);
  const [busy, setBusy] = useState("");
  const seen = useRef(new Set());

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const list = await api.pendingSchedules();
        if (!alive) return;
        setPending(list);
        list.forEach((t) => { if (!seen.current.has(t.id)) { seen.current.add(t.id); osNotify("⏰ Periodic task due", `${t.title} — open Odin to start or skip.`); } });
      } catch {}
    };
    tick();
    const h = setInterval(tick, 10000);
    return () => { alive = false; clearInterval(h); };
  }, []);

  async function act(tid, kind) {
    setBusy(tid + kind);
    try { kind === "approve" ? await api.approveSchedule(tid) : await api.skipSchedule(tid); }
    catch {}
    setPending((x) => x.filter((t) => t.id !== tid));
    setBusy("");
  }

  if (!pending.length) return null;
  return (
    <div style={{ position: "fixed", right: 18, bottom: 18, zIndex: 70, display: "flex", flexDirection: "column", gap: 10, width: 340 }}>
      {pending.map((t) => (
        <motion.div key={t.id} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }}
          className="card pad" style={{ borderColor: "rgba(122,240,208,.45)", boxShadow: "0 18px 44px rgba(0,0,0,.45)" }}>
          <div className="row" style={{ gap: 8, alignItems: "center" }}>
            <span style={{ fontSize: 18 }}>⏰</span>
            <div className="col" style={{ gap: 1 }}>
              <b style={{ fontSize: 13.5 }}>Periodic task is due</b>
              <span className="faint" style={{ fontSize: 11 }}>{scheduleLabel(t)} · awaiting your go-ahead</span>
            </div>
          </div>
          <div style={{ fontSize: 12.5, color: "var(--txt)", margin: "8px 0 10px" }}>{t.title}</div>
          <div className="row" style={{ gap: 8 }}>
            <button className="btn primary sm" disabled={!!busy} onClick={() => act(t.id, "approve")}>{busy === t.id + "approve" ? "Starting…" : "✓ Approve & run"}</button>
            <button className="btn ghost sm" disabled={!!busy} onClick={() => act(t.id, "skip")}>Skip this time</button>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

/* ============================================================================
   AnchorView — Anchor Connect status page: the external access layer's queue +
   lifecycle (pending / processing / webhook / acknowledged / finished / failed),
   with retry config. On-demand refresh (no constant polling).
============================================================================ */
const ANCHOR_STATUS_COLOR = {
  queued: "var(--brand-2)", sent_to_local: "var(--brand)", processing: "var(--brand)",
  response_received: "var(--brand)", webhook_sent: "var(--brand)", ack_pending: "var(--warn,#e0a500)",
  acknowledged: "var(--ok)", finished: "var(--ok)", failed: "var(--danger)", cancelled: "var(--txt-faint)",
};

export function AnchorView() {
  const [counts, setCounts] = useState({});
  const [rows, setRows] = useState([]);
  const [cfg, setCfg] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = async () => {
    setBusy(true);
    try {
      setCounts(await api.anchorCounts());
      setRows(await api.anchorRequests());
      setCfg(await api.anchorConfig());
    } catch {}
    setBusy(false);
  };
  useEffect(() => { load(); }, []);
  return (
    <div className="col" style={{ gap: 14, height: "100%", overflow: "auto" }}>
      <div className="row between">
        <div className="h-title">🔌 Anchor Connect — external access layer</div>
        <button className="btn sm" onClick={load} disabled={busy}>{busy ? "…" : "↻ Refresh"}</button>
      </div>
      <div className="muted" style={{ fontSize: 12 }}>
        Third parties &amp; your remote apps reach local projects through the Anchor. A request is FINISHED only
        after the local machine processed it AND the webhook was delivered + acknowledged. Refresh is on‑demand.
      </div>
      <div className="row wrap" style={{ gap: 8 }}>
        {Object.keys(counts).length === 0 && <span className="faint" style={{ fontSize: 12 }}>No requests yet.</span>}
        {Object.entries(counts).map(([s, n]) => (
          <span key={s} className="pill" style={{ color: ANCHOR_STATUS_COLOR[s] || "var(--txt-dim)", borderColor: "var(--stroke-strong)" }}>{s}: {n}</span>
        ))}
      </div>
      {cfg && (
        <div className="card pad row wrap" style={{ gap: 14, fontSize: 12 }}>
          <span>retry count: <b>{cfg.retry_count}</b></span>
          <span>retry interval: <b>{cfg.retry_interval_sec}s</b></span>
          <span>poll limit: <b>{cfg.poll_limit}</b></span>
          <span className="faint">(configurable via the admin API)</span>
        </div>
      )}
      <div className="card pad col" style={{ gap: 6, minHeight: 0 }}>
        <b style={{ fontSize: 13 }}>Requests</b>
        {rows.length === 0 && <span className="faint" style={{ fontSize: 12 }}>None.</span>}
        {rows.map((r) => (
          <div key={r.id} className="row" style={{ gap: 10, fontSize: 11.5, padding: "5px 0", borderBottom: "1px solid var(--stroke)", alignItems: "center" }}>
            <span className="pill" style={{ color: ANCHOR_STATUS_COLOR[r.status] || "var(--txt-dim)", borderColor: "var(--stroke-strong)", minWidth: 110, justifyContent: "center" }}>{r.status}</span>
            <span style={{ fontFamily: "ui-monospace,monospace", color: "var(--txt-dim)" }}>{r.id.slice(0, 14)}</span>
            <span style={{ minWidth: 90 }}>→ {r.project}</span>
            <span className="faint">webhook ×{r.webhook_attempts || 0}{r.acked ? " · ✓ack" : ""}</span>
            {r.error && <span style={{ color: "var(--danger)" }} title={r.error}>{r.error.slice(0, 40)}</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Audit / Observer (Phase 5): structure integrity + debounced self-healing ──
export function AuditView() {
  const [st, setSt] = useState(null);
  const [issues, setIssues] = useState(null);
  const [log, setLog] = useState([]);
  const [msg, setMsg] = useState("");
  const load = async () => {
    try { setSt(await api.auditStatus()); } catch { setSt(null); }
    try { setLog(((await api.auditLog(60)).log || []).slice().reverse()); } catch { setLog([]); }
  };
  useEffect(() => { load(); }, []);
  const scan = async () => { try { setIssues((await api.auditScan()).issues || []); } catch { setIssues([]); } load(); };
  const run = async () => { setMsg("running…"); try { const r = await api.auditRun(); setMsg(r.ran ? `healed ${r.healed} · flagged ${r.flagged}` : "debounced (silence gap not reached)"); } catch { setMsg("error"); } scan(); };
  const c = (st && st.config) || {}, deb = (st && st.debounce) || {};
  const col = (t) => ({ misplaced: "#ffb454", unindexed: "#6c8cff", duplicate: "#ff6b6b", "root-stray": "#c58bff" }[t] || "#8b93a7");
  const Tag = ({ t }) => <span style={{ fontSize: 11, padding: "2px 7px", borderRadius: 6, background: "#1c2130", color: col(t) }}>{t}</span>;
  const cell = { padding: "6px 8px", verticalAlign: "top" }, mono = { ...cell, fontFamily: "monospace", fontSize: 12 };
  return (
    <div style={{ display: "grid", gap: 14 }}>
      <div className="card" style={{ padding: 16 }}>
        <h2 style={{ margin: "0 0 10px" }}>🛰️ Audit / Observer</h2>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
          <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
            <div><div style={{ fontSize: 22, fontWeight: 700 }}>{st ? st.open_issues : "–"}</div><div className="faint" style={{ fontSize: 12 }}>open issues</div></div>
            <div><div style={{ fontSize: 22, fontWeight: 700 }}>{deb.quiet_minutes ?? "–"}</div><div className="faint" style={{ fontSize: 12 }}>quiet minutes</div></div>
            <div><div style={{ fontSize: 22, fontWeight: 700 }}>{c.silence_minutes ?? "–"}</div><div className="faint" style={{ fontSize: 12 }}>silence gap (min)</div></div>
            <div><div style={{ fontSize: 22, fontWeight: 700 }}>{deb.should_run ? "yes" : "no"}</div><div className="faint" style={{ fontSize: 12 }}>would run now?</div></div>
          </div>
          <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
            <label style={{ display: "flex", gap: 6, alignItems: "center" }}>
              <input type="checkbox" checked={!!c.enabled} onChange={e => api.auditConfig(e.target.checked, c.silence_minutes || 30).then(load)} />
              {c.enabled ? "enabled" : "disabled"}
            </label>
            <label className="faint" style={{ fontSize: 12 }}>gap <input type="number" min="0" defaultValue={c.silence_minutes || 30} style={{ width: 60 }} onBlur={e => api.auditConfig(!!c.enabled, +e.target.value).then(load)} /> min</label>
          </div>
        </div>
        <div style={{ display: "flex", gap: 10, marginTop: 14, alignItems: "center" }}>
          <button onClick={scan}>Scan (read-only)</button>
          <button style={{ background: "#6c8cff", color: "#fff" }} onClick={run}>▶ Run now (heal)</button>
          <span className="faint">{msg}</span>
        </div>
      </div>
      <div className="card" style={{ padding: 16 }}>
        <h3 style={{ margin: "0 0 8px" }}>Open issues</h3>
        {issues == null ? <div className="faint">click Scan…</div> :
          issues.length === 0 ? <div style={{ color: "#3ecf8e" }}>✓ no issues — everything in its correct place and indexed.</div> :
          <table style={{ width: "100%", borderCollapse: "collapse" }}><tbody>
            {issues.map((i, k) => <tr key={k} style={{ borderTop: "1px solid #232838" }}>
              <td style={cell}><Tag t={i.type} /></td>
              <td style={mono}>{i.path || (i.paths || []).join(", ") || i.name}</td>
              <td style={{ ...cell, color: "#8b93a7" }}>{i.reason}</td>
            </tr>)}
          </tbody></table>}
      </div>
      <div className="card" style={{ padding: 16 }}>
        <h3 style={{ margin: "0 0 8px" }}>History — what was found &amp; how it was solved</h3>
        {log.length === 0 ? <div className="faint">no runs yet.</div> :
          <table style={{ width: "100%", borderCollapse: "collapse" }}><tbody>
            {log.map((e, k) => <tr key={k} style={{ borderTop: "1px solid #232838" }}>
              <td style={{ ...mono, color: "#8b93a7", fontSize: 11 }}>{(e.ts || "").slice(0, 19).replace("T", " ")}</td>
              <td style={cell}><Tag t={e.type} /></td>
              <td style={mono}>{e.path || (e.paths || []).join(", ") || e.name}</td>
              <td style={{ ...cell, color: (e.fix || "").startsWith("FLAGGED") ? "#ffb454" : "#3ecf8e" }}>{e.fix}</td>
            </tr>)}
          </tbody></table>}
      </div>
    </div>
  );
}

// ── Phase 6: fully GENERIC, DB-driven project grid. Content defines the count (array.map),
//    TYPE defines the UI (controls + icons come from the /ui/projects contract, nothing hardcoded). ──
export function ProjectsGrid({ onOpenProject }) {
  const [cards, setCards] = useState(null);
  useEffect(() => { api.uiProjects().then(setCards); }, []);
  const ICON = { "streaming-voice": "🎙️", "notification": "🔔", "play": "▶" };
  if (cards == null) return <div className="faint">loading…</div>;
  if (!cards.length) return <div className="faint">No projects yet.</div>;
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(290px,1fr))", gap: 12 }}>
      {cards.map((c) => (
        <div key={c.id} className="card" style={{ padding: 14, cursor: "pointer" }} onClick={() => onOpenProject && onOpenProject(c.id)}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
            <b style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.name}</b>
            <span style={{ fontSize: 11, padding: "2px 9px", borderRadius: 20, background: "#1c2130", color: "#8b93a7", flexShrink: 0 }}>{c.ui.chip}</span>
          </div>
          <div className="faint" style={{ fontSize: 12, margin: "4px 0" }}>
            {c.category}{(c.ui.icons || []).length ? " · " + (c.ui.icons || []).map((i) => ICON[i] || "•").join(" ") : ""}
          </div>
          <div className="faint" style={{ fontSize: 12 }}>agents {c.counts.agents} · connectors {c.counts.connectors} · files {c.counts.files}</div>
          <div style={{ display: "flex", gap: 8, marginTop: 10, alignItems: "center", flexWrap: "wrap" }} onClick={(e) => e.stopPropagation()}>
            {(c.ui.controls || []).map((ctrl) => {
              if (ctrl === "play" || ctrl === "run-once") return <button key={ctrl} style={{ background: "#3ecf8e", color: "#06210f", fontWeight: 700 }} title="Run this project" onClick={() => onOpenProject && onOpenProject(c.id)}>▶ {ctrl === "run-once" ? "Run once" : "Run"}</button>;
              if (ctrl === "export") return <button key={ctrl} title="Export report (Reporting agent)" onClick={() => onOpenProject && onOpenProject(c.id)}>⬇ Export</button>;
              if (ctrl === "cadence") return <span key={ctrl} className="faint" style={{ fontSize: 12 }}>cadence: {c.config.cadence || c.cadence || "—"}</span>;
              if (ctrl === "period") return <span key={ctrl} className="faint" style={{ fontSize: 12 }}>period: {c.config.period || "—"}</span>;
              if (ctrl === "timeout") return <label key={ctrl} className="faint" style={{ fontSize: 12 }}>timeout <input type="number" defaultValue={c.config.timeout || 300} style={{ width: 60 }} /> s</label>;
              return null;
            })}
            {!(c.ui.controls || []).length && <span className="faint" style={{ fontSize: 12 }}>on-demand</span>}
          </div>
        </div>
      ))}
    </div>
  );
}

// Generic, DB-driven agent roster (Phase 6). Grouped by TYPE (content defines the count, type defines the
// chip). Reads /ui/agents — same contract the web/mobile consume from the anchor mirror.
export function AgentsGrid({ onOpenAgent }) {
  const [agents, setAgents] = useState(null);
  useEffect(() => { api.uiAgents().then(setAgents); }, []);
  if (agents == null) return <div className="faint">loading…</div>;
  if (!agents.length) return <div className="faint">No agents yet.</div>;
  const groups = {};
  for (const a of agents) (groups[a.type || "technical"] ||= []).push(a);
  return (
    <div style={{ display: "grid", gap: 16 }}>
      {Object.keys(groups).sort().map((typ) => (
        <div key={typ}>
          <div style={{ fontSize: 12, textTransform: "uppercase", letterSpacing: 1, color: "#8b93a7", margin: "2px 0 8px" }}>
            {(groups[typ][0].ui && groups[typ][0].ui.chip) || typ} · {groups[typ].length}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(240px,1fr))", gap: 10 }}>
            {groups[typ].map((a) => (
              <div key={a.id} className="card" style={{ padding: 12, cursor: onOpenAgent ? "pointer" : "default" }} onClick={() => onOpenAgent && onOpenAgent(a.id, a.name)}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                  <Avatar kind={a.avatar || "generic"} name={a.name + " " + (a.role || "")} size="sm" />
                  <b style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>{a.name}</b>
                  {a.group && <span style={{ fontSize: 11, padding: "2px 9px", borderRadius: 20, background: "#1c2130", color: "#8b93a7", flexShrink: 0 }}>{a.group}</span>}
                </div>
                {a.role && <div className="faint" style={{ fontSize: 12, margin: "3px 0" }}>{a.role}</div>}
                <div className="faint" style={{ fontSize: 12 }}>used by {a.projects} project{a.projects === 1 ? "" : "s"}</div>
                {((a.ui && a.ui.controls) || []).length > 0 && (
                  <div style={{ display: "flex", gap: 6, marginTop: 6 }}>
                    {(a.ui.controls || []).map((ctrl) => (
                      <span key={ctrl} className="pill" style={{ fontSize: 11 }} title={`agent capability: ${ctrl}`}>
                        {ctrl === "voice" ? "🎙️ Voice" : ctrl === "export" ? "⬇ Export" : ctrl}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
