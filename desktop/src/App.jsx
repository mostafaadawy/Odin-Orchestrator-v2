import React, { useEffect, useState, useCallback, useRef } from "react";
import { createPortal } from "react-dom";
import { api, setBase, setToken, getBase, isMuted, setMuted } from "./api.js";
import { Dashboard, ProjectView, MemberView, ArchivedView, ConversationalNewProject, ApprovalCenter, OutcomeToasts, OperationFinishWatcher, BellNotification, NotificationsBell, PeriodicApprovalWatcher, AnchorView, AuditView, ProjectsGrid, AgentsGrid } from "./views.jsx";
import { ConversationsView } from "./Conversations.jsx";
import { Modal, StatusDot } from "./ui.jsx";
import { V2Badge, WhatsNewModal, PaperView, DeciderSwitch } from "./v2.jsx";

export default function App() {
  const [view, setView] = useState({ name: "dashboard" }); // dashboard | project | member
  const [projects, setProjects] = useState([]);
  const [health, setHealth] = useState(null);
  const [activeSet, setActiveSet] = useState(new Set());
  const [activeTasks, setActiveTasks] = useState({});
  const [showNew, setShowNew] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [showNews, setShowNews] = useState(false);   // v2: "What's new in v2" panel
  const [showPorts, setShowPorts] = useState(false);
  const [refreshSignal, setRefreshSignal] = useState(0);
  const [muted, setMutedState] = useState(isMuted());
  const [navOpen, setNavOpen] = useState(localStorage.getItem("odin.nav") !== "0");
  const [convMode, setConvMode] = useState(false);   // extra mode: Dashboard ⇄ Conversations (same pool)
  const [err, setErr] = useState("");
  // STANDALONE CHATS (chat:<id>) — the SAME shared list as web + mobile. Lives in the left sidebar's CHATS
  // section (after PROJECTS). chatScope = which chat the dashboard's chat area shows (sidebar-driven).
  const [chats, setChats] = useState([]);
  const [chatScope, setChatScope] = useState("company");
  const [chatTitle, setChatTitle] = useState("Chief Engineer · company");
  const toggleNav = () => { const v = !navOpen; setNavOpen(v); localStorage.setItem("odin.nav", v ? "1" : "0"); };
  // top-bar horizontal scroll — explicit ‹ › arrows so no action button is ever unreachable when narrow
  const actionsRef = useRef(null);
  const scrollActions = (dir) => {
    const el = actionsRef.current;
    if (!el) return;
    const step = Math.max(180, Math.round(el.clientWidth * 0.7));
    // set scrollLeft directly (works everywhere, incl. Electron) — scrollBy/smooth can be a no-op in some builds
    try { el.scrollTo({ left: el.scrollLeft + dir * step, behavior: "smooth" }); }
    catch (e) { el.scrollLeft = el.scrollLeft + dir * step; }
  };

  const loadProjects = useCallback(async () => {
    try { setProjects(await api.projects()); setErr(""); }
    catch (e) { setErr("Connecting to the backend… (first start loads voice models, ~20s)"); }
  }, []);
  const loadChats = useCallback(async () => { try { setChats(await api.chats()); } catch {} }, []);
  const openChat = (scope, title) => { setChatScope(scope); setChatTitle(title); setConvMode(false); setView({ name: "dashboard" }); };
  const newChat = async () => { const name = (window.prompt("Name this chat:", "") || "").trim(); if (!name) return; try { const c = await api.createChat(name); await loadChats(); if (c && c.scope) openChat(c.scope, c.title || name); } catch {} };
  const renChat = async (scope, cur) => { const name = (window.prompt("Rename chat:", cur || "") || "").trim(); if (!name) return; try { await api.renameChat(scope, name); await loadChats(); if (chatScope === scope) setChatTitle(name); } catch {} };
  const delChat = async (scope) => { if (!window.confirm("Delete this chat everywhere?")) return; try { await api.deleteChat(scope); await loadChats(); if (chatScope === scope) openChat("company", "Chief Engineer · company"); } catch {} };

  useEffect(() => { loadProjects(); loadChats(); }, [loadProjects, loadChats]);

  // poll health: once the backend is up, clear the error and (re)load projects — self-heals so the
  // "cannot reach backend" message never sticks after the server finishes booting.
  useEffect(() => {
    const tick = async () => {
      try { const h = await api.health(); setHealth(h); setErr(""); loadProjects(); loadChats(); }
      catch { /* backend still booting */ }
    };
    tick();
    const t = setInterval(tick, 4000);
    return () => clearInterval(t);
  }, [loadProjects, loadChats]);

  // live activity → heartbeat set
  useEffect(() => {
    const tick = async () => {
      try {
        const d = await api.activity();
        setActiveSet(new Set((d.active || []).map((a) => `${a.pid}:${a.agent}`)));
        const tasks = {}; (d.active || []).forEach((a) => { tasks[`${a.pid}:${a.agent}`] = { task: a.task || "", phase: a.phase || "working" }; });
        setActiveTasks(tasks);
      } catch {}
    };
    tick();
    const t = setInterval(tick, 2500);
    return () => clearInterval(t);
  }, []);

  const [kickoffPid, setKickoffPid] = useState(null);
  const openProject = (pid) => setView({ name: "project", pid });
  const openMember = (pid, member) => setView({ name: "member", pid, member });

  return (
    <div className="app" style={{ gridTemplateColumns: navOpen ? "264px 1fr" : "62px 1fr" }}>
      <aside className="sidebar" style={{ padding: navOpen ? undefined : "16px 8px" }}>
        <div className="brand" style={{ justifyContent: navOpen ? "space-between" : "center", padding: navOpen ? undefined : "4px 0 12px" }}>
          {navOpen && (
            <div className="row" style={{ gap: 10 }}>
              <div className="mark">Ω</div>
              <div><h1>Odin <V2Badge onClick={() => setShowNews(true)} /></h1><small>{health?.engine?.includes("Claude") ? "Claude engine" : "engine"}</small></div>
            </div>
          )}
          <button className="iconbtn" style={{ width: 30, height: 30, fontSize: 15, flexShrink: 0 }} onClick={toggleNav}
            title={navOpen ? "Collapse sidebar (more space)" : "Expand sidebar"}>{navOpen ? "‹" : "›"}</button>
        </div>
        {navOpen && <DeciderSwitch />}
        <div className="nav scroll">
          <button className={view.name === "dashboard" && !convMode && chatScope === "company" ? "active" : ""} title="Talk to the Chief Engineer — company-wide view of all projects" onClick={() => openChat("company", "Chief Engineer · company")}>🏛️ {navOpen && "Company"}</button>
          {navOpen && <div className="faint" style={{ fontSize: 10.5, padding: "8px 11px 2px", letterSpacing: 1 }}>PROJECTS</div>}
          {projects.map((p) => (
            <button key={p.id} title={`Open ${p.name} — talk to its Project CTO`} className={view.name !== "dashboard" && view.pid === p.id ? "active" : ""} onClick={() => openProject(p.id)}>
              📁 {navOpen && p.name}
            </button>
          ))}
          <button title="Start a new project (guided conversation with the CTO)" onClick={() => setShowNew(true)}>＋ {navOpen && "New project"}</button>
          {/* CHATS — its OWN section after PROJECTS (same shared list as web + mobile). No extra bar inside
              the chat container; selecting a chat here opens it in the Chief-Engineer chat area. */}
          {navOpen && (
            <div className="row between" style={{ padding: "8px 11px 2px" }}>
              <span className="faint" style={{ fontSize: 10.5, letterSpacing: 1 }}>CHATS</span>
              <span className="faint" style={{ fontSize: 11, color: "var(--brand)", cursor: "pointer" }} onClick={newChat} title="Start a new shared chat">＋ New</span>
            </div>
          )}
          {chats.map((c) => (
            <button key={c.scope} title={c.title} className={view.name === "dashboard" && !convMode && chatScope === c.scope ? "active" : ""} onClick={() => openChat(c.scope, c.title || "Chat")}>
              💬 {navOpen && <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{c.title || "Chat"}</span>}
              {navOpen && <span style={{ marginLeft: "auto", opacity: .6, cursor: "pointer" }} onClick={(e) => { e.stopPropagation(); renChat(c.scope, c.title); }} title="Rename this chat">✎</span>}
              {navOpen && <span className="x" style={{ marginLeft: 6, opacity: .6 }} onClick={(e) => { e.stopPropagation(); delChat(c.scope); }} title="Delete this chat">✕</span>}
            </button>
          ))}
          {navOpen && chats.length === 0 && <div className="faint" style={{ fontSize: 11, padding: "2px 11px 6px" }}>No chats yet — tap ＋ New</div>}
          <button className={view.name === "archived" ? "active" : ""} title="View and restore archived projects" onClick={() => setView({ name: "archived" })}>🗄 {navOpen && "Archived"}</button>
          <button className={view.name === "anchor" ? "active" : ""} title="Anchor Connect — external access layer: queue, webhooks, statuses" onClick={() => setView({ name: "anchor" })}>🔌 {navOpen && "Anchor Connect"}</button>
          <button className={view.name === "audit" ? "active" : ""} title="Audit / Observer — structure integrity + debounced self-healing" onClick={() => setView({ name: "audit" })}>🛰️ {navOpen && "Audit"}</button>
          <button className={view.name === "projectsgrid" ? "active" : ""} title="All projects — generic, DB-driven cards (type defines controls, content defines count)" onClick={() => setView({ name: "projectsgrid" })}>🗂 {navOpen && "Projects"}</button>
          <button className={view.name === "paper" ? "active" : ""} title="Paper v2 (provisional), paper v1 submission, figures, results tables, CHANGES — view and download" onClick={() => setView({ name: "paper" })}>📄 {navOpen && "Paper"}</button>
          <button title="What's new in Odin v2" onClick={() => setShowNews(true)}>✨ {navOpen && "What's new in v2"}</button>
          <button className={view.name === "agentsgrid" ? "active" : ""} title="All agents — generic, DB-driven roster grouped by type" onClick={() => setView({ name: "agentsgrid" })}>👥 {navOpen && "Agents"}</button>
        </div>
        <div className="nav" style={{ flexShrink: 0 }}>
          <button title="Backend URL, access token, preferences" onClick={() => setShowSettings(true)}>⚙️ {navOpen && "Settings"}</button>
        </div>
        <div className="col" style={{ gap: 6, padding: "6px 10px", display: navOpen ? "flex" : "none" }}>
          <StatusDot state={health?.ok ? "ok" : "bad"} label={health?.ok ? "Connected" : "Offline"} />
          <StatusDot state={health?.voice_enabled ? "ok" : "warn"} label={health?.voice_enabled ? "Voice ready" : "Voice off"} />
        </div>
      </aside>

      <main className="main">
        <div className="topbar">
          <div className="crumbs">
            <span onClick={() => setView({ name: "dashboard" })} style={{ cursor: "pointer" }}>Company</span>
            {view.name !== "dashboard" && <><span>/</span><b style={{ cursor: "pointer" }} onClick={() => openProject(view.pid)}>{projName(projects, view.pid)}</b></>}
            {view.name === "member" && <><span>/</span><b>{view.member}</b></>}
          </div>
          <button className="topbar-arrow" onClick={() => scrollActions(-1)} title="Scroll toolbar left">‹</button>
          <div className="topbar-actions" ref={actionsRef}>
          {err && <span className="pill" style={{ color: "var(--danger)", borderColor: "rgba(255,107,129,.4)" }}>{err}</span>}
          <button className="btn sm" title="Toggle the assistant voice"
            onClick={() => { const v = !muted; setMuted(v); setMutedState(v); }}>
            {muted ? "🔇 Voice off" : "🔊 Voice on"}
          </button>
          <button className={"btn sm" + (convMode ? " primary" : "")} title="Switch between the Dashboard and Conversations — same chat pool, different view"
            onClick={() => setConvMode((v) => !v)}>{convMode ? "🗂 Dashboard" : "💬 Conversations"}</button>
          <EnvBadge onClick={() => setShowPorts(true)} />
          <ConnectorBadges />
          <HubSpotBadge />
          <AnchorCodeIndicator />
          <DeciderToggle />
          <button className="btn sm" title="Show the ports & links map and flip Development / Production (only the anchor + web are online in production)" onClick={() => setShowPorts(true)}>🗺 Ports & Env</button>
          <button className="btn sm" title="Reload projects, health and connection status" onClick={() => { setRefreshSignal((s) => s + 1); loadProjects(); api.health().then(setHealth); }}>↻ Refresh</button>
          <ApprovalCenter />
          <NotificationsBell onOpenProject={(pid) => setView({ name: "project", pid })} />
          <BellNotification />
          </div>
          <button className="topbar-arrow" onClick={() => scrollActions(1)} title="Scroll toolbar right">›</button>
        </div>

        <div className="content">
          {convMode && <ConversationsView projects={projects} />}
          {!convMode && view.name === "dashboard" && (
            <Dashboard health={health} projects={projects} activeSet={activeSet} activeTasks={activeTasks} chatScope={chatScope} chatTitle={chatTitle}
              onOpenProject={openProject} onOpenMember={openMember} onNewProject={() => setShowNew(true)} onReload={loadProjects} />
          )}
          {!convMode && view.name === "project" && (
            <ProjectView pid={view.pid} activeSet={activeSet} onOpenMember={openMember} refreshSignal={refreshSignal} kickoff={kickoffPid === view.pid} />
          )}
          {!convMode && view.name === "member" && (
            <MemberView pid={view.pid} name={view.member} activeSet={activeSet} activeTasks={activeTasks} />
          )}
          {!convMode && view.name === "archived" && (
            <ArchivedView onOpenProject={openProject} onReload={loadProjects} />
          )}
          {!convMode && view.name === "anchor" && (
            <AnchorView />
          )}
          {!convMode && view.name === "audit" && (
            <AuditView />
          )}
          {!convMode && view.name === "projectsgrid" && (
            <ProjectsGrid onOpenProject={openProject} />
          )}
          {!convMode && view.name === "paper" && <PaperView />}
          {!convMode && view.name === "agentsgrid" && (
            <AgentsGrid />
          )}
        </div>
      </main>

      <ConversationalNewProject open={showNew} onClose={() => setShowNew(false)}
        onCreated={(p) => { loadProjects(); if (p && p.id) { setKickoffPid(p.id); openProject(p.id); setTimeout(() => setKickoffPid(null), 6000); } }} />
      <SettingsModal open={showSettings} onClose={() => setShowSettings(false)} />
      <WhatsNewModal open={showNews} onClose={() => setShowNews(false)} onOpenPaper={() => { setConvMode(false); setView({ name: "paper" }); }} />
      <PortsModal open={showPorts} onClose={() => setShowPorts(false)} />
      {/* approvals now live as a blinking top-bar button that opens ONE tabbed dialog (see the top bar) */}
      {/* clear success/problem dialogs when a run ends */}
      <OutcomeToasts />
      {/* global: fire the finish dialog on ANY screen the moment a task ends (success or fail) */}
      <OperationFinishWatcher />
      {/* global: periodic projects ask to start when due + device online */}
      <PeriodicApprovalWatcher />
    </div>
  );
}

function projName(projects, pid) { const p = projects.find((x) => x.id === pid); return p ? p.name : pid; }

// PORTS & ENVIRONMENT MAP — a single place to SEE every port/link and to FLIP Development <-> Production.
// In production only the ANCHOR and the WEB are online (on the Azure VM); the desktop brain stays local and
// is reached only through the anchor. Flipping here is the one change to go live — it writes odin.env +
// odin.anchor and reloads, exactly like Settings.
const PORT_MAP = {
  development: {
    label: "Development — everything LOCAL (localhost)",
    rows: [
      ["brain (desktop AI + API)", "http://localhost:8000", "local"],
      ["anchor (3rd-party entry / queue)", "http://localhost:9100", "local"],
      ["3rd-party test page (sim)", "http://localhost:9104/anchor_sim.html", "local"],
      ["webhook receiver (results)", "http://localhost:9300", "local"],
      ["WEB app (Flutter)", "http://localhost:8080", "local"],
    ],
    anchor: "http://localhost:9100",
  },
  production: {
    label: "Production — ANCHOR + WEB via nginx reverse proxy on 443 (no open ports; anchor.odinmarkets.com)",
    rows: [
      ["brain (desktop AI + API)", "http://localhost:8000", "stays LOCAL — reached only via anchor"],
      ["anchor (ONLINE, reverse proxy)", "https://anchor.odinmarkets.com/odin-anchor", "ONLINE · 443"],
      ["WEB app (ONLINE, reverse proxy)", "https://anchor.odinmarkets.com/odin-web", "ONLINE · 443"],
      ["webhook (via anchor)", "https://anchor.odinmarkets.com/odin-anchor", "ONLINE · 443"],
    ],
    anchor: "https://anchor.odinmarkets.com/odin-anchor",
  },
};
// ALWAYS-VISIBLE environment badge in the top bar — so you can never mistake Development for Production.
// Green = Production (online anchor), Blue = Development (local). Click it to open the Ports & Env map.
// HubSpot connection badge — sits in the top bar BESIDE the Azure/Env badge. Green dot = connected.
// Click runs the account overview (real counts) and shows it in a small popup (high z-index).
// GENERIC connection badges — one per connector from /connectors (NOT static). Each shows a live status
// dot. Add a connector to the registry and its badge appears automatically; the color reflects its real
// connection state. (Azure/env is the separate EnvBadge; HubSpot keeps its own overview popup too.)
function ConnectorBadges() {
  const [cons, setCons] = React.useState([]);
  React.useEffect(() => {
    let alive = true;
    const load = () => api.uiConnectors().then((c) => alive && Array.isArray(c) && c.length && setCons(c)).catch(() => {});
    load();
    const t = setInterval(load, 15000);
    return () => { alive = false; clearInterval(t); };
  }, []);
  const ICON = { hubspot: "🧡", klaviyo: "✉️", veeqo: "📦", azure: "☁️", az: "☁️", "claude-cli": "🤖", claude: "🤖" };
  if (!cons.length) return null;
  return (
    <>
      {cons.map((c) => {
        const key = (c.id || c.name || "").toLowerCase();
        const on = c.connected ?? (c.status === "connected");
        return (
          <span key={key} className="btn sm" title={`${c.name || c.id} — ${on ? "connected" : "not connected"}`}
            style={{ display: "inline-flex", alignItems: "center", gap: 5, cursor: "default" }}>
            {ICON[key] || "🔌"} {c.name || c.id}
            <span style={{ width: 7, height: 7, borderRadius: "50%", background: on ? "#3ecf8e" : "#8b93a7", display: "inline-block" }} />
          </span>
        );
      })}
    </>
  );
}
function hsFmt(v) { return (v === null || v === undefined) ? "—" : (typeof v === "object" ? "scope needed" : v); }
function HubSpotBadge() {
  const [st, setSt] = useState(null);
  const [open, setOpen] = useState(false);
  const [ov, setOv] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let alive = true;
    const load = () => api.hubspotStatus().then((d) => alive && setSt(d)).catch(() => alive && setSt({ connected: false }));
    load(); const t = setInterval(load, 60000);
    return () => { alive = false; clearInterval(t); };
  }, []);
  const run = async () => {
    setBusy(true);
    try { setOv(await api.hubspotRun()); setOpen(true); }
    catch (e) { setOv({ connected: false, error: String(e) }); setOpen(true); }
    finally { setBusy(false); }
  };
  const connected = st && st.connected;
  const dot = connected ? "#39d98a" : (st ? "#ff6b81" : "#c9a227");
  return (
    <>
      <button className="btn sm" disabled={busy}
        title="HubSpot CRM connection — click to run the account overview (real counts)"
        onClick={run} style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span style={{ width: 8, height: 8, borderRadius: 8, background: dot, display: "inline-block" }} />
        🧡 HubSpot{st ? (connected ? "" : " ⚠") : "…"}
      </button>
      {open && ov && (
        <div onClick={() => setOpen(false)}
          style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,.4)", zIndex: 99999, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div onClick={(e) => e.stopPropagation()}
            style={{ background: "var(--panel,#1a1d24)", color: "var(--txt,#eee)", padding: 20, borderRadius: 12, minWidth: 320, maxWidth: 460, boxShadow: "0 10px 40px rgba(0,0,0,.5)", border: "1px solid var(--line,#333)" }}>
            <div style={{ fontWeight: 700, fontSize: 15, marginBottom: 10 }}>🧡 HubSpot CRM — Account Overview</div>
            {ov.connected ? (
              <div style={{ fontSize: 13.5, lineHeight: 2 }}>
                <div>Status: <b style={{ color: "#39d98a" }}>Connected</b> · portal {ov.connection?.portal_id}</div>
                <div>Contacts: <b>{hsFmt(ov.counts?.contacts)}</b></div>
                <div>Companies: <b>{hsFmt(ov.counts?.companies)}</b></div>
                <div>Deals: <b>{hsFmt(ov.counts?.deals)}</b></div>
                <div>Contacts this month: <b>{hsFmt(ov.counts?.contacts_this_month)}</b></div>
                <div style={{ marginTop: 6, color: "var(--dim,#9aa)" }}>Scopes granted: {ov.granted_scope_count}</div>
              </div>
            ) : (
              <div style={{ fontSize: 13.5, color: "#ff6b81" }}>Not connected: {ov.error || "check HUBSPOT_SECRET_KEY in oth/.cred"}</div>
            )}
            <div style={{ marginTop: 14, textAlign: "right" }}>
              <button className="btn sm" onClick={() => setOpen(false)}>Close</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

// P4e (owner spec): a big, clear toggle — "Normal (LLM)" / "Jev mode (local decider)". Default Normal. The brain
// keeps the setting (data/decider_mode.json); in Normal mode Odin behaves exactly as before.
export function DeciderToggle() {
  const [mode, setMode] = useState("normal");
  const [authority, setAuthority] = useState("shadow");   // owner 2026-10-13: shadow until the owner's labels arrive
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.deciderMode().then((d) => { setMode((d && d.mode) || "normal"); setAuthority((d && d.authority) || "shadow"); }).catch(() => setMode("normal")); }, []);
  async function flip() {
    const next = mode === "jev" ? "normal" : "jev";
    setBusy(true);
    try { const d = await api.setDeciderMode(next); setMode((d && d.mode) || next); if (d && d.authority) setAuthority(d.authority); } catch (e) { /* stays as it was */ }
    setBusy(false);
  }
  const jev = mode === "jev";
  const c = jev ? "var(--warn, #ffb547)" : "var(--brand, #6c8cff)";
  return (
    <button data-testid="decider-toggle" disabled={busy} onClick={flip}
      title="Decisions: Normal = the LLM decides (default). Jev mode = the local decider on this Mac decides closed choices; low confidence falls back to the LLM."
      style={{ display: "inline-flex", alignItems: "center", gap: 8, cursor: "pointer", background: "transparent",
               border: `2px solid ${c}`, color: c, borderRadius: 999, padding: "5px 14px", fontSize: 13, fontWeight: 800 }}>
      <span style={{ width: 10, height: 10, borderRadius: "50%", background: c, display: "inline-block" }} />
      {jev ? (authority === "shadow" ? "Jev mode (shadow: LLM decides)" : "Jev mode (local decider)") : "Normal (LLM)"}
    </button>
  );
}

function EnvBadge({ onClick }) {
  const env = localStorage.getItem("odin.env") || (import.meta.env.VITE_ODIN_ENV || "development");
  const prod = env === "production";
  const c = prod ? "var(--ok, #4be3a0)" : "var(--brand, #6c8cff)";
  return (
    <button
      onClick={onClick}
      title="Current environment — click to view the ports map or switch"
      style={{
        display: "inline-flex", alignItems: "center", gap: 6, cursor: "pointer",
        background: "transparent", border: `1px solid ${c}`, color: c,
        borderRadius: 999, padding: "3px 10px", fontSize: 12, fontWeight: 700,
      }}>
      <span style={{ width: 8, height: 8, borderRadius: "50%", background: c, display: "inline-block" }} />
      {prod ? "PRODUCTION" : "DEVELOPMENT"}
    </button>
  );
}

// ---- CONNECTING WITH ANCHOR — the secure channel that shows the owner the anchor's Manage login code.
// When "Manage" is pressed on the anchor landing page, the anchor generates a random code; this button
// polls the anchor, BLINKS when a code is waiting, and (on click) shows the sign-in email, password and the
// code to copy into the Manage login. F-14: the key, email and password are NOT in the source — the
// desktop reads them at run time from the macOS Keychain (service "odin-anchor") through the Electron main process.
async function ownerSecret(name) {
  try { return (window.odin && window.odin.secret) ? ((await window.odin.secret(name)) || "") : ""; } catch (e) { return ""; }
}

function AnchorCodeIndicator() {
  const [pending, setPending] = useState(null);
  const [open, setOpen] = useState(false);
  const [creds, setCreds] = useState({ email: "", password: "" });
  useEffect(() => {
    let stop = false;
    let key = "";
    async function poll() {
      try {
        if (!key) key = await ownerSecret("anchor-key");
        if (!key) { if (!stop) setPending(null); return; }   // no key in the Keychain -> nothing to poll
        // In PRODUCTION the anchor is ONLINE — poll the deployed anchor for the login code (not localhost,
        // which isn't running online). Dev keeps the local anchor.
        const env = localStorage.getItem("odin.env") || (import.meta.env.VITE_ODIN_ENV || "development");
        // F-22 / N7: honour the editable production anchor (Settings), like the rest of the desktop does
        const base = (env === "production"
          ? (localStorage.getItem("odin.prod.anchor") || "https://anchor.odinmarkets.com/odin-anchor")
          : (localStorage.getItem("odin.anchor") || "http://localhost:9100")).replace(/\/+$/, "");
        const r = await fetch(base + "/anchor/v1/manage/pending-code", { headers: { "X-API-Key": key } });
        const d = await r.json();
        if (!stop) setPending(d && d.pending ? d : null);
      } catch (e) { if (!stop) setPending(null); }
    }
    poll();
    const iv = setInterval(poll, 4000);
    return () => { stop = true; clearInterval(iv); };
  }, []);
  const active = !!pending;
  useEffect(() => {            // fetch email/password only when the dialog is opened with a code waiting
    if (!(open && active)) return;
    Promise.all([ownerSecret("manage-email"), ownerSecret("manage-password")])
      .then(([email, password]) => setCreds({ email, password }));
  }, [open, active]);
  return (
    <>
      <style>{"@keyframes odinBlink{0%,100%{box-shadow:0 0 0 0 rgba(122,240,208,0)}50%{box-shadow:0 0 0 3px rgba(122,240,208,.6)}}"}</style>
      <button className={"btn sm" + (active ? " primary" : "")}
        style={active ? { animation: "odinBlink 1s infinite", borderColor: "var(--brand2, #7af0d0)" } : {}}
        title={active ? "The anchor generated a login code — click to view" : "Connecting with Anchor — the anchor's Manage login code appears here"}
        onClick={() => setOpen(true)}>
        🔗 Anchor{active ? " • CODE" : ""}
      </button>
      {createPortal(
        <Modal open={open} onClose={() => setOpen(false)} title="🔗 Connecting with Anchor">
          {active ? (
            <div>
              <div style={{ color: "var(--dim)", fontSize: 12, marginBottom: 10 }}>
                A login code is waiting. Copy these into the anchor's <b>Manage</b> page:
              </div>
              <CopyRow label="Email" value={pending.email || creds.email} />
              <CopyRow label="Password" value={creds.password || "(not in Keychain — see Settings)"} />
              <CopyRow label="Confirmation code" value={pending.code} big />
              <div style={{ color: "var(--dim)", fontSize: 11, marginTop: 10 }}>The code expires in ~10 minutes.</div>
            </div>
          ) : (
            <div style={{ color: "var(--dim)" }}>
              No login code right now. Press <b>Manage</b> on the anchor landing page to generate one — it will
              appear here and this button will blink.
            </div>
          )}
        </Modal>,
        document.body
      )}
    </>
  );
}

function CopyRow({ label, value, big }) {
  const [copied, setCopied] = useState(false);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, margin: "8px 0" }}>
      <div style={{ width: 140, color: "var(--dim)", fontSize: 12 }}>{label}</div>
      <code style={{ flex: 1, fontSize: big ? 20 : 13, letterSpacing: big ? 4 : 0, userSelect: "all" }}>{value}</code>
      <button className="btn sm" onClick={() => {
        try { navigator.clipboard.writeText(String(value)); setCopied(true); setTimeout(() => setCopied(false), 1200); } catch (e) {}
      }}>{copied ? "✓" : "Copy"}</button>
    </div>
  );
}

function PortsModal({ open, onClose }) {
  const [envKey, setEnvKey] = useState(localStorage.getItem("odin.env") || (import.meta.env.VITE_ODIN_ENV || "development"));
  const M = PORT_MAP[envKey] || PORT_MAP.development;
  function apply() {
    localStorage.setItem("odin.env", envKey);
    localStorage.setItem("odin.anchor", M.anchor);
    if (envKey === "production") localStorage.setItem("odin.prod.anchor", M.anchor);
    setBase(envKey === "production" ? "http://localhost:8000" : "http://localhost:8000");
    location.reload();
  }
  return (
    <Modal open={open} onClose={onClose} title="🗺 Ports & Environment"
      footer={<button className="btn primary" onClick={apply}>Apply “{envKey}” & reload</button>}>
      <div><label>Environment</label>
        <select value={envKey} onChange={(e) => setEnvKey(e.target.value)}>
          <option value="development">Development (local — default)</option>
          <option value="production">Production (Azure VM — anchor + web online)</option>
        </select></div>
      <div style={{ fontSize: 12, color: "var(--dim)", margin: "6px 0 10px" }}>{M.label}</div>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12.5 }}>
        <thead><tr style={{ textAlign: "left", color: "var(--dim)" }}>
          <th style={{ padding: "6px 8px" }}>Service</th><th style={{ padding: "6px 8px" }}>URL</th><th style={{ padding: "6px 8px" }}>Where</th></tr></thead>
        <tbody>
          {M.rows.map(([name, url, where], i) => (
            <tr key={i} style={{ borderTop: "1px solid var(--stroke)" }}>
              <td style={{ padding: "6px 8px" }}>{name}</td>
              <td style={{ padding: "6px 8px", fontFamily: "ui-monospace,Menlo,monospace", color: "var(--brand2)" }}>{url}</td>
              <td style={{ padding: "6px 8px", color: where.includes("ONLINE") ? "var(--ok)" : "var(--dim)" }}>{where}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="faint" style={{ fontSize: 12, marginTop: 10 }}>
        Applying “production” points the desktop at the online anchor (https://anchor.odinmarkets.com/odin-anchor). The desktop brain always stays local — remote web/mobile reach it only through the anchor.
      </div>
    </Modal>
  );
}

export function relayFingerprint(kid) {   // PC-3: identical grouping to the phone's KeyRelay.pretty()
  const k = String(kid || "");
  return k ? (k.match(/.{1,4}/g) || []).join("-") : "";
}

export function SettingsModal({ open, onClose }) {
  // ENVIRONMENT SELECTOR (Development / Production) — the ONLY change to go live is switching this dropdown.
  // Development = local; Production = the Azure VM anchor (fill its ip:port). Persisted so it survives reload.
  const ENVS = {
    development: { label: "Development (local — default)", base: "http://localhost:8000", anchor: "http://localhost:9100" },
    production: { label: "Production (Azure VM)",
                  base: localStorage.getItem("odin.prod.base") || "http://localhost:8000",
                  anchor: localStorage.getItem("odin.prod.anchor") || "https://anchor.odinmarkets.com/odin-anchor" },
  };
  const [envKey, setEnvKey] = useState(localStorage.getItem("odin.env") || (import.meta.env.VITE_ODIN_ENV || "development"));
  const [base, setB] = useState(localStorage.getItem("odin.base") || "http://localhost:8000");
  const [anchor, setA] = useState(localStorage.getItem("odin.anchor") || "http://localhost:9100");
  const [token, setT] = useState(localStorage.getItem("odin.token") || "");
  // PC-3: show the Mac's phone-relay key fingerprint (same grouping as the phone: xxxx-xxxx-xxxx-xxxx)
  const [relayFp, setRelayFp] = useState("");
  // PC-4: paired phones — the owner trusts a phone HERE after comparing its fingerprint with the phone's screen
  const [phones, setPhones] = useState([]);
  const loadPhones = () => api.phoneDevices().then((d) => setPhones((d && d.devices) || [])).catch(() => setPhones([]));
  useEffect(() => {
    if (!open) return;
    api.relayKey().then((d) => setRelayFp(relayFingerprint(d && d.kid))).catch(() => setRelayFp(""));
    loadPhones();
  }, [open]);
  function applyEnv(k) { setEnvKey(k); const e = ENVS[k]; setB(e.base); setA(e.anchor); }
  function save() {
    localStorage.setItem("odin.env", envKey);
    localStorage.setItem("odin.anchor", anchor);
    if (envKey === "production") { localStorage.setItem("odin.prod.base", base); localStorage.setItem("odin.prod.anchor", anchor); }
    setBase(base); setToken(token); location.reload();
  }
  return (
    <Modal open={open} onClose={onClose} title="Settings"
      footer={<button className="btn primary" onClick={save}>Save & reload</button>}>
      <div><label>Environment</label>
        <select value={envKey} onChange={(e) => applyEnv(e.target.value)}>
          <option value="development">{ENVS.development.label}</option>
          <option value="production">{ENVS.production.label}</option>
        </select></div>
      <div><label>Backend URL</label><input value={base} onChange={(e) => setB(e.target.value)} /></div>
      <div><label>Anchor URL (queue / webhooks)</label><input value={anchor} onChange={(e) => setA(e.target.value)} /></div>
      <div><label>Access token (if the server requires one)</label><input value={token} onChange={(e) => setT(e.target.value)} placeholder="optional" /></div>
      <div data-testid="relay-fp"><label>Phone key relay — this Mac's fingerprint</label>
        <div style={{ fontFamily: "monospace", fontSize: 14 }}>{relayFp || "(not available — is the brain running?)"}</div>
        <div className="faint" style={{ fontSize: 11 }}>Compare it with the fingerprint your phone shows before you send it a key. If they differ, do not send keys.</div></div>
      <div data-testid="paired-phones"><label>Paired phones — approvals from the phone (signed, end-to-end encrypted)</label>
        {phones.length === 0 && <div className="faint" style={{ fontSize: 12 }}>No phone has asked to pair. On the phone: Approvals ▸ Pair.</div>}
        {phones.map((p) => (
          <div key={p.device_id} style={{ display: "flex", alignItems: "center", gap: 8, margin: "4px 0" }}>
            <span style={{ fontFamily: "monospace", fontSize: 13 }}>{p.fingerprint}</span>
            <span className="faint" style={{ fontSize: 12 }}>{p.name} · {p.status}</span>
            {p.status !== "trusted" && <button className="btn sm primary" data-testid={"trust-" + p.device_id}
              onClick={() => api.trustPhone(p.device_id).then(loadPhones)}>Trust</button>}
            {p.status !== "revoked" && <button className="btn sm" data-testid={"revoke-" + p.device_id}
              onClick={() => api.revokePhone(p.device_id).then(loadPhones)}>Revoke</button>}
          </div>))}
        <div className="faint" style={{ fontSize: 11 }}>Trust a phone only if this fingerprint is the one your phone shows. A trusted phone can approve or reject one request at a time; never "approve all", never keys.</div></div>
      <div className="faint" style={{ fontSize: 12 }}>Development = local. Production = the Azure VM anchor (fill its ip:port). Switching this points the whole desktop app at the online anchor — the only change needed to go live.</div>
    </Modal>
  );
}
