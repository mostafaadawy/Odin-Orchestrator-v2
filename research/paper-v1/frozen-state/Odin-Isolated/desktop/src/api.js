// Backend client for the Odin desktop app. Talks to the local FastAPI server.
const BASE = localStorage.getItem("odin.base") || "http://localhost:18000";
const TOKEN = () => localStorage.getItem("odin.token") || "";

export function setBase(b) { localStorage.setItem("odin.base", b); }
export function setToken(t) { localStorage.setItem("odin.token", t); }
export function getBase() { return BASE; }

function headers() {
  const h = { "Content-Type": "application/json" };
  if (TOKEN()) h["X-Odin-Token"] = TOKEN();
  return h;
}
function qtoken(url) {
  if (!TOKEN()) return url;
  return url + (url.includes("?") ? "&" : "?") + "token=" + encodeURIComponent(TOKEN());
}

async function jget(path) {
  const r = await fetch(BASE + path, { headers: headers() });
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return r.json();
}
async function jpost(path, body, method = "POST") {
  const r = await fetch(BASE + path, { method, headers: headers(), body: body ? JSON.stringify(body) : undefined });
  if (!r.ok) throw new Error(`${path} → ${r.status}`);
  return r.json();
}

export const api = {
  // 🎙 live-meeting asset: is this project meeting-capable, and the monitor URL for the popup dialog
  meetingCapable: (pid) => jget(`/meeting/capable?pid=${encodeURIComponent(pid)}`).then((d) => !!(d && d.capable)).catch(() => false),
  monitorUrl: (pid) => `${BASE}/meeting_monitor.html?pid=${encodeURIComponent(pid)}`,
  health: () => jget("/health"),
  // 📄 report export URL (Reporting agent) — generic per-project endpoint: works for ANY project
  // (generates on-the-fly from the team pool); SOC still serves its pre-styled health report.
  reportUrl: (pid, fmt) => `${BASE}/project/report?pid=${encodeURIComponent(pid)}&fmt=${fmt}`,
  // 🔔 notifications (live feed for recurring/periodical work)
  notifications: (unread = false) => jget(`/notifications?unread=${unread}&limit=100`).catch(() => ({ items: [], unread: 0 })),
  notifCount: () => jget("/notifications/count").then((d) => d.unread).catch(() => 0),
  markNotif: (id) => jpost("/notifications/read", { id }),
  markAllNotifs: () => jpost("/notifications/read", { all: true }),
  // Audit / Observer (Phase 5)
  auditStatus: () => jget("/audit/status"),
  auditScan: () => jget("/audit/scan"),
  auditRun: () => jpost("/audit/run?force=true"),
  auditLog: (limit = 60) => jget(`/audit/violations?limit=${limit}`),
  auditConfig: (enabled, silence) => jpost(`/audit/config?enabled=${enabled}&silence_minutes=${silence}`),
  // Generic UI contract (Phase 6) — cards + type-driven controls/icons straight from the DB
  uiProjects: () => jget("/ui/projects").then((d) => d.cards || []).catch(() => []),
  uiProject: (pid) => jget(`/ui/project/${encodeURIComponent(pid)}`).catch(() => null),
  uiAgents: () => jget("/ui/agents").then((d) => d.agents || []).catch(() => []),
  uiConnectors: () => jget("/ui/connectors").then((d) => d.connectors || []).catch(() => []),
  uiTypes: () => jget("/ui/types").catch(() => ({})),
  // ⏰ schedules (list + edit time/cadence/timezone)
  schedules: (pid) => jget(`/schedules?pid=${encodeURIComponent(pid)}`).then((d) => d.tasks || []).catch(() => []),
  updateSchedule: (tid, schedule) => jpost(`/schedules/${tid}/update`, { schedule }),
  // projects
  projects: () => jget("/projects").then((d) => d.projects),
  project: (pid) => jget("/projects/" + pid),
  createProject: (b) => jpost("/projects", b),
  intake: (history) => jpost("/projects/intake", { history }),
  intakeReadiness: () => jget("/projects/intake/readiness"),
  validateAgents: (names) => jpost("/agents/validate", { names }),
  capability: (pid, task) => jpost(`/projects/${pid}/capability`, { task }),
  addAgentForce: (pid, b) => jpost(`/projects/${pid}/agents`, b),
  runNow: (pid, prompt = "", cid = "") => jpost(`/projects/${pid}/run-now`, { prompt, cid }),
  capabilities: () => jget("/capabilities"),
  allAgents: () => jget("/agents/all").then((d) => d.agents || []),
  companyAgents: () => jget("/company/agents").then((d) => d.agents),
  addCompanyAgent: (b) => jpost("/company/agents", b),
  removeCompanyAgent: (name) => jpost(`/company/agents/${encodeURIComponent(name)}`, null, "DELETE"),
  connectors: () => jget("/connectors").then((d) => d.connectors),
  addConnector: (b) => jpost("/connectors", b),
  removeConnector: (cid) => jpost(`/connectors/${cid}`, null, "DELETE"),
  // HubSpot operator agent (portal 47173986) — connection badge + run + specific asks
  hubspotStatus: () => jget("/hubspot/status"),
  hubspotRun: () => jpost("/hubspot/run", {}),
  hubspotAsk: (query) => jpost("/hubspot/ask", { query }),
  updateProject: (pid, b) => jpost(`/projects/${pid}/update`, b),
  deleteProject: (pid) => jpost("/projects/" + pid, null, "DELETE"),
  archivedProjects: () => jget("/projects/archived").then((d) => d.projects),
  archiveProject: (pid) => jpost(`/projects/${pid}/archive`, {}),
  unarchiveProject: (pid) => jpost(`/projects/${pid}/unarchive`, {}),
  addMapping: (pid, b) => jpost(`/projects/${pid}/mappings`, b),
  plan: (pid) => jget(`/projects/${pid}/plan`),
  rules: (pid) => jget(`/projects/${pid}/rules`).then((d) => d.rules),
  addRule: (pid, rule) => jpost(`/projects/${pid}/rules`, { rule }),
  updateRule: (pid, rid, rule) => jpost(`/projects/${pid}/rules/${rid}`, { rule }),
  removeRule: (pid, rid) => jpost(`/projects/${pid}/rules/${rid}`, null, "DELETE"),
  syncRun: (pid) => jpost(`/projects/${pid}/sync/run`, {}),
  deployRun: (pid) => jpost(`/projects/${pid}/deploy/run`, {}),
  // agents
  agents: (pid) => jget(`/projects/${pid}/agents`).then((d) => d.agents),
  agent: (pid, name) => jget(`/projects/${pid}/agents/${encodeURIComponent(name)}`),
  suggestAgent: (pid, description) => jpost(`/projects/${pid}/agents/suggest`, { description }),
  addAgent: (pid, b) => jpost(`/projects/${pid}/agents`, b),
  updateAgent: (pid, name, b) => jpost(`/projects/${pid}/agents/${encodeURIComponent(name)}/update`, b),
  removeAgent: (pid, name) => jpost(`/projects/${pid}/agents/${encodeURIComponent(name)}`, null, "DELETE"),
  saveRule: (pid, name, rule) => jpost(`/projects/${pid}/agents/${encodeURIComponent(name)}/rule`, { rule }),
  stats: (pid) => jget(`/projects/${pid}/stats`),
  // models
  models: () => jget("/models"),
  setModel: (scope, model) => jpost("/models/set", { scope, model }),
  // scoped chat
  // STANDALONE CHATS registry (chat:<id> scopes) — the SAME list web + mobile use, so chats are shared
  // across every device (WhatsApp-style). These live in the left sidebar's CHATS section.
  chats: () => jget(`/chats`).then((d) => d.chats || []),
  createChat: (title = "New chat") => jpost(`/chats`, { title }),
  renameChat: (scope, title) => jpost(`/chats/rename?scope=${encodeURIComponent(scope)}`, { title }),
  deleteChat: (scope) => jpost(`/chats/${encodeURIComponent(scope)}`, null, "DELETE"),
  scopeChats: (scope) => jget(`/scope/chats?scope=${encodeURIComponent(scope)}`).then((d) => d.chats),
  createScopeChat: (scope, title = "New chat") => jpost(`/scope/chats?scope=${encodeURIComponent(scope)}`, { title }),
  scopeChat: (scope, cid) => jget(`/scope/chat?scope=${encodeURIComponent(scope)}&cid=${cid}`),
  renameScopeChat: (scope, cid, title) => jpost(`/scope/chat/rename?scope=${encodeURIComponent(scope)}&cid=${cid}`, { title }),
  deleteScopeChat: (scope, cid) => jpost(`/scope/chat?scope=${encodeURIComponent(scope)}&cid=${cid}`, null, "DELETE"),
  scopeSummary: (scope) => jget(`/scope/summary?scope=${encodeURIComponent(scope)}`),
  // group chat (same pool): post a message (no AI turn) + upload attachments + resolve file URLs
  postScopeMessage: (scope, cid, body) => jpost(`/scope/message?scope=${encodeURIComponent(scope)}&cid=${cid}`, body),
  uploadScopeFile: async (scope, blob, name) => {
    const fd = new FormData();
    fd.append("file", blob, name);
    fd.append("scope", scope);
    const h = {};
    if (TOKEN()) h["X-Odin-Token"] = TOKEN();
    const r = await fetch(BASE + `/scope/upload?scope=${encodeURIComponent(scope)}`, { method: "POST", headers: h, body: fd });
    if (!r.ok) throw new Error("upload " + r.status);
    return r.json();
  },
  fileUrl: (p) => (p && String(p).startsWith("http")) ? p : BASE + p,
  // the WHOLE pool for a scope (all chats merged, in time order) + per-message delete
  scopeAllMessages: (scope) => jget(`/scope/messages?scope=${encodeURIComponent(scope)}`).then((d) => d.messages || []),
  deleteScopeMessage: (scope, cid, mid) => jpost(`/scope/message?scope=${encodeURIComponent(scope)}&cid=${cid}&mid=${mid}`, null, "DELETE"),
  scopeChildren: (scope) => jget(`/scope/children?scope=${encodeURIComponent(scope)}`).then((d) => d.children),
  // activity
  activity: (pid) => jget("/activity" + (pid ? `?pid=${pid}` : "")),
  // schedules
  schedules: (pid) => jget("/schedules" + (pid ? `?pid=${pid}` : "")).then((d) => d.tasks),
  createSchedule: (b) => jpost("/schedules", b),
  deleteSchedule: (tid) => jpost("/schedules/" + tid, null, "DELETE"),
  updateSchedule: (tid, b) => jpost(`/schedules/${tid}/update`, b),
  // Anchor Connect — external access layer (queue + lifecycle visibility)
  anchorRequests: (status = "") => jget("/anchor/v1/admin/requests" + (status ? `?status=${status}` : "")).then((d) => d.requests || []),
  anchorCounts: () => jget("/anchor/v1/admin/counts").then((d) => d.counts || {}),
  anchorConfig: () => jget("/anchor/v1/admin/config"),
  anchorSetConfig: (b) => jpost("/anchor/v1/admin/config", b),
  // project types + role roster + periodic run gate (Phase 3)
  projectTypes: () => jget("/project-types"),
  roles: () => jget("/roles").then((d) => d.roles || []),
  pendingSchedules: (pid) => jget("/schedules/pending" + (pid ? `?pid=${pid}` : "")).then((d) => d.pending || []),
  approveSchedule: (tid) => jpost(`/schedules/${tid}/approve`, {}),
  skipSchedule: (tid) => jpost(`/schedules/${tid}/skip`, {}),
  // infra
  connectTest: () => jget("/infra/connect-test"),
  // approval gate — pending change requests the owner must approve
  approvals: (pid) => jget("/approvals" + (pid ? `?pid=${pid}` : "")).then((d) => d.approvals || []),
  approvalsCount: (pid) => jget("/approvals/count" + (pid ? `?pid=${pid}` : "")).then((d) => d.pending || 0),
  approveChange: (aid, note = "") => jpost(`/approvals/${aid}/approve`, { note }),
  rejectChange: (aid, note = "") => jpost(`/approvals/${aid}/reject`, { note }),
  // background team run — survives UI navigation (runs on the server, UI polls)
  startRun: (pid, goal) => jpost(`/projects/${pid}/orchestrate/start`, { goal }),
  runStatus: (pid) => jget(`/projects/${pid}/orchestrate/status`),
  stopRun: (pid) => jpost(`/projects/${pid}/orchestrate/stop`, {}),
  // operations — the ONE record per long task: live log, state, stop, finish card
  operations: (pid) => jget("/operations" + (pid ? `?pid=${pid}` : "")).then((d) => d.operations || []),
  latestOperation: (pid) => jget(`/operations/latest?pid=${pid}`),
  operation: (oid) => jget(`/operations/${oid}`),
  stopOperation: (oid) => jpost(`/operations/${oid}/stop`, {}),
  provideOperation: (oid, answers) => jpost(`/operations/${oid}/provide`, { answers }),
  runDeployOperation: (pid) => jpost(`/projects/${pid}/deploy/operation`, {}),
  requestDeploy: (pid) => jpost(`/projects/${pid}/deploy/request`, {}),
};

// SSE stream for a scoped chat turn. Returns an EventSource-like controller.
export function streamScope(scope, text, lang, cid, handlers) {
  const url = qtoken(
    `${BASE}/scope/stream?scope=${encodeURIComponent(scope)}&text=${encodeURIComponent(text)}&lang=${lang}&cid=${cid || ""}`
  );
  const es = new EventSource(url);
  for (const ev of ["status", "token", "delegate", "approval", "capability_gap", "done", "error"]) {
    es.addEventListener(ev, (e) => {
      let data = {};
      try { data = JSON.parse(e.data); } catch {}
      handlers[ev] && handlers[ev](data);
      if (ev === "done" || ev === "error") es.close();
    });
  }
  return es;
}

// Autonomous team run: plan → run each member → auto hand-off. SSE.
export function streamOrchestrate(pid, goal, handlers) {
  const url = qtoken(`${BASE}/projects/${pid}/orchestrate?goal=${encodeURIComponent(goal)}`);
  const es = new EventSource(url);
  for (const ev of ["status", "plan", "delegate", "token", "step_done", "approval", "done", "error"]) {
    es.addEventListener(ev, (e) => {
      let d = {}; try { d = JSON.parse(e.data); } catch {}
      handlers[ev] && handlers[ev](d);
      if (ev === "done" || ev === "error") es.close();
    });
  }
  return es;
}

// ---- voice ----
let _audio = null;            // only ONE voice plays at a time
export function stopSpeech() {
  if (_audio) { try { _audio.pause(); _audio.currentTime = 0; } catch {} _audio = null; }
}
export function isMuted() { return localStorage.getItem("odin.mute") === "1"; }
export function setMuted(v) { localStorage.setItem("odin.mute", v ? "1" : "0"); if (v) stopSpeech(); }
export async function speak(text, lang) {
  // Backend TTS only (Kokoro EN / Coqui AR) — never the OS voice.
  if (isMuted()) return null;  // user turned the voice off
  stopSpeech();                // interrupt any current message before speaking the next
  const ar = String(lang).toLowerCase().startsWith("ar");
  const speed = Number(localStorage.getItem(ar ? "odin.speed.ar" : "odin.speed.en") || (ar ? 1.15 : 1.0));
  const url = qtoken(`${BASE}/voice/tts?text=${encodeURIComponent(text)}&lang=${lang}&speed=${speed}`);
  const a = new Audio(url);
  _audio = a;
  a.onended = () => { if (_audio === a) _audio = null; };
  try { await a.play(); } catch {}
  return a;
}

export async function transcribe(blob, lang, fast = false) {
  // Backend expects form field `file` + query `language` (faster-whisper). fast=1 -> small model
  // for near-real-time partials; the final pass uses the accurate model.
  const fd = new FormData();
  fd.append("file", blob, "clip.webm");
  const h = {};
  if (TOKEN()) h["X-Odin-Token"] = TOKEN();
  const url = qtoken(`${BASE}/voice/stt?language=${encodeURIComponent(lang || "")}${fast ? "&fast=1" : ""}`);
  const r = await fetch(url, { method: "POST", headers: h, body: fd });
  if (!r.ok) {
    let detail = "";
    try { const j = await r.json(); detail = j.detail || ""; } catch {}
    throw new Error("STT " + r.status + (detail ? ": " + detail : ""));
  }
  const d = await r.json();
  return d.text || d.transcript || "";
}
