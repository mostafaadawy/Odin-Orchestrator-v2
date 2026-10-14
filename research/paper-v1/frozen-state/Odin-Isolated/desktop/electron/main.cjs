// Electron main process — the real desktop app.
// Installed from the .dmg, pinned to the dock, double-clicked. On launch it:
//   1) checks if the Odin backend is already running on the port (if so, just connects);
//   2) otherwise locates the project folder and boots the backend itself.
// The heavy Python/venv/voice models stay in the project folder (not inside the .app), so the
// app is small and updates cleanly when you rebuild.
const { app, BrowserWindow, shell, session, ipcMain, dialog } = require("electron");
const path = require("path");
const fs = require("fs");
const os = require("os");
const { spawn } = require("child_process");
const http = require("http");

const DEV = !!process.env.ODIN_DEV; // ODIN_DEV=1 -> load Vite dev server
const BACKEND_PORT = process.env.ODIN_PORT || 8000;
// The ONLINE anchor the poller bridges to in production (overridable via env).
const ONLINE_ANCHOR = process.env.ODIN_ANCHOR || "https://anchor.odinmarkets.com/odin-anchor";
let backend = null;
let poller = null;

// Where the Python backend (server/run.sh) lives. Resolution order:
//   ODIN_ROOT env  ->  saved config (userData/root.txt)  ->  dev location (../..)  ->  default ~/Desktop path
function backendRoot() {
  if (process.env.ODIN_ROOT && fs.existsSync(process.env.ODIN_ROOT)) return process.env.ODIN_ROOT;
  try {
    const saved = path.join(app.getPath("userData"), "root.txt");
    if (fs.existsSync(saved)) {
      const r = fs.readFileSync(saved, "utf8").trim();
      if (r && fs.existsSync(path.join(r, "server", "run.sh"))) return r;
    }
  } catch {}
  const devRoot = path.resolve(__dirname, "..", ".."); // when run from the repo (not packaged)
  if (fs.existsSync(path.join(devRoot, "server", "run.sh"))) return devRoot;
  const guess = path.join(os.homedir(), "Desktop", "AiAgentWorkSpace", "Odin-Isolated");
  return guess;
}

function isUp(cb) {
  const req = http.get({ host: "127.0.0.1", port: BACKEND_PORT, path: "/health", timeout: 1200 }, (res) => {
    cb(res.statusCode === 200); res.resume();
  });
  req.on("error", () => cb(false));
  req.on("timeout", () => { req.destroy(); cb(false); });
}

function startBackend() {
  const root = backendRoot();
  const run = path.join(root, "server", "run.sh");
  if (!fs.existsSync(run)) {
    console.error("[backend] run.sh not found at", run, "- set ODIN_ROOT or start it manually.");
    return;
  }
  try {
    // macOS GUI PATH is stripped — put Homebrew/tool dirs back so az/ollama/claude are found.
    const extraPath = ["/opt/homebrew/bin", "/opt/homebrew/sbin", "/usr/local/bin", "/usr/local/sbin",
                       `${process.env.HOME}/.local/bin`].join(":");
    backend = spawn("bash", [run], {
      cwd: root,
      env: { ...process.env, USE_VOICE: process.env.USE_VOICE || "1", PORT: String(BACKEND_PORT),
             PATH: `${extraPath}:${process.env.PATH || ""}` },
      stdio: "inherit",
      detached: true,            // own process group → we can kill the WHOLE backend tree
    });
    backend.on("error", (e) => console.error("[backend] failed:", e.message));
  } catch (e) {
    console.error("[backend] spawn error:", e.message);
  }
}

// Kill the backend + its whole process group so NO uvicorn/port is ever left behind.
let _killed = false;
function killBackend() {
  if (_killed || !backend) return;
  _killed = true;
  const pid = backend.pid;
  try { process.kill(-pid, "SIGKILL"); } catch {}   // kill the process group
  try { backend.kill("SIGKILL"); } catch {}         // and the direct child, belt-and-suspenders
  backend = null;
}

// PRODUCTION only: start the POLLER — the bridge that carries messages between the
// ONLINE anchor and the local brain. Without it, web/mobile chat queues on the anchor
// but is never processed (nothing saved, no reply, app shows "offline"). This is what
// makes the packaged .dmg self-sufficient. In DEV, phase2/phase3 own the poller, so we
// skip it here to avoid running two.
function startPoller() {
  if (DEV) return;
  const root = backendRoot();
  const script = path.join(root, "server", "local_poller_http.py");
  if (!fs.existsSync(script)) { console.error("[poller] local_poller_http.py not found at", script); return; }
  const venvPy = path.join(root, ".venv", "bin", "python");
  const py = fs.existsSync(venvPy) ? venvPy : "python3";
  try {
    const extraPath = ["/opt/homebrew/bin", "/opt/homebrew/sbin", "/usr/local/bin", "/usr/local/sbin",
                       `${process.env.HOME}/.local/bin`].join(":");
    poller = spawn(py, ["-u", "local_poller_http.py", "--anchor", ONLINE_ANCHOR, "--interval", "4"], {
      cwd: path.join(root, "server"),
      env: { ...process.env, PATH: `${extraPath}:${process.env.PATH || ""}` },
      stdio: "inherit",
      detached: true,
    });
    poller.on("error", (e) => console.error("[poller] failed:", e.message));
    // SELF-HEALING: if the poller ever dies and we are NOT intentionally quitting, bring it back after a short
    // delay — the same crash-proof guarantee poller_supervisor.sh gives phase2/phase3, now built into the
    // packaged .dmg so a poller crash never silently stops web/mobile request+sync flow (the bug we hit before).
    poller.on("exit", (code, sig) => {
      poller = null;
      if (_pollerKilled) return;                 // intentional shutdown (app quitting) — do not restart
      console.error(`[poller] exited (code=${code} sig=${sig}) — restarting in 3s`);
      setTimeout(() => { if (!_pollerKilled) startPoller(); }, 3000);
    });
  } catch (e) {
    console.error("[poller] spawn error:", e.message);
  }
}

let _pollerKilled = false;
function killPoller() {
  if (_pollerKilled || !poller) return;
  _pollerKilled = true;
  const pid = poller.pid;
  try { process.kill(-pid, "SIGKILL"); } catch {}
  try { poller.kill("SIGKILL"); } catch {}
  poller = null;
}

function cleanupAll() { killBackend(); killPoller(); killReqpage(); }

function createWindow() {
  const win = new BrowserWindow({
    width: 1440, height: 920, minWidth: 1080, minHeight: 720,
    backgroundColor: "#0a0c12",
    titleBarStyle: "hiddenInset",
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
      preload: path.join(__dirname, "preload.cjs"),
    },
  });
  win.webContents.setWindowOpenHandler(({ url }) => { shell.openExternal(url); return { action: "deny" }; });
  if (DEV) {
    win.loadURL("http://localhost:5173");
    win.webContents.openDevTools({ mode: "bottom" }); // docked in the SAME window (no 2nd window)
  } else {
    win.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }
}

// Native folder picker — lets the user create a project ANYWHERE on disk (real Desktop, etc.).
ipcMain.handle("pick-folder", async () => {
  const res = await dialog.showOpenDialog({
    title: "Choose where to create the project",
    properties: ["openDirectory", "createDirectory"],
  });
  return res.canceled ? "" : (res.filePaths[0] || "");
});
ipcMain.handle("pick-folders", async () => {
  const res = await dialog.showOpenDialog({ title: "Choose folder(s)", properties: ["openDirectory", "multiSelections"] });
  return res.canceled ? [] : (res.filePaths || []);
});
ipcMain.handle("pick-files", async () => {
  const res = await dialog.showOpenDialog({ title: "Choose file(s)", properties: ["openFile", "multiSelections"] });
  return res.canceled ? [] : (res.filePaths || []);
});

// Start the local REQUEST page: a simple static server on REQ_PORT serving anchor_sim.html
// (which reads anchor_seed.js → the ONLINE anchor). Then open it in the browser. Idempotent:
// if it's already running we just re-open the URL.
const REQ_PORT = Number(process.env.ODIN_REQ_PORT || 9104);
const REQ_URL = `http://localhost:${REQ_PORT}/anchor_sim.html?env=prod`;
let reqpage = null;
ipcMain.handle("start-request-page", async () => {
  try {
    const root = backendRoot();
    if (!fs.existsSync(path.join(root, "anchor_sim.html"))) {
      return { ok: false, url: REQ_URL, error: "anchor_sim.html not found in " + root };
    }
    const alreadyUp = await new Promise((resolve) => {
      const r = http.get({ host: "127.0.0.1", port: REQ_PORT, path: "/anchor_sim.html", timeout: 1000 },
        (res) => { resolve(res.statusCode > 0); res.resume(); });
      r.on("error", () => resolve(false));
      r.on("timeout", () => { r.destroy(); resolve(false); });
    });
    if (!alreadyUp && !reqpage) {
      const venvPy = path.join(root, ".venv", "bin", "python");
      const py = fs.existsSync(venvPy) ? venvPy : "python3";
      const extraPath = ["/opt/homebrew/bin", "/opt/homebrew/sbin", "/usr/local/bin", "/usr/local/sbin"].join(":");
      reqpage = spawn(py, ["-m", "http.server", String(REQ_PORT), "--bind", "127.0.0.1"], {
        cwd: root, env: { ...process.env, PATH: `${extraPath}:${process.env.PATH || ""}` },
        stdio: "ignore", detached: true,
      });
      reqpage.on("error", (e) => console.error("[reqpage] failed:", e.message));
    }
    await new Promise((r) => setTimeout(r, alreadyUp ? 0 : 800));
    await shell.openExternal(REQ_URL);
    return { ok: true, url: REQ_URL };
  } catch (e) {
    return { ok: false, url: REQ_URL, error: String(e && e.message || e) };
  }
});
function killReqpage() { if (reqpage) { try { process.kill(-reqpage.pid, "SIGKILL"); } catch {} try { reqpage.kill("SIGKILL"); } catch {} reqpage = null; } }

// Only ONE app instance — prevents a second launch from spawning a second backend / fighting the port.
if (!app.requestSingleInstanceLock()) {
  app.quit();
} else {
  app.whenReady().then(() => {
    try {
      session.defaultSession.setPermissionRequestHandler((wc, perm, cb) => {
        cb(perm === "media" || perm === "microphone" || perm === "audioCapture" ? true : true);
      });
    } catch {}
    // Always start a FRESH backend (run.sh frees the port first), so a stale/zombie server can
    // never hold the port. createWindow immediately.
    startBackend();
    startPoller(); // production: bring up the online-anchor ↔ local-brain bridge so chat works from the .dmg alone
    createWindow();
    app.on("activate", () => { if (BrowserWindow.getAllWindows().length === 0) createWindow(); });
  });
}

// --- bulletproof cleanup: kill the backend on EVERY exit path (no leftover ports) ---
app.on("window-all-closed", () => { cleanupAll(); app.quit(); });
app.on("before-quit", cleanupAll);
app.on("will-quit", cleanupAll);
process.on("exit", cleanupAll);
process.on("SIGINT", () => { cleanupAll(); process.exit(0); });
process.on("SIGTERM", () => { cleanupAll(); process.exit(0); });
process.on("uncaughtException", (e) => { console.error(e); cleanupAll(); process.exit(1); });
