# Odin Desktop — premium cockpit (Electron + React + Vite + Framer Motion)

The native desktop app for Odin-Orchestrator. It reuses the existing FastAPI backend (engine,
voice, chats, Azure, approval gate) and adds the full org cockpit: company dashboard, project
pages, member detail pages, live animated agents, models, scheduling.

## Two commands, two jobs

| You're… | Run | What happens |
|---------|-----|--------------|
| **Testing / fixing bugs** | `npm run dev` | Live app with hot-reload, **all logs in the terminal**, DevTools auto-open. Edit `src/`, the UI updates instantly. Boots the backend for you. |
| **Done — want the installer** | `npm run dist` | Builds the `.dmg` you drag to Applications. |

```bash
cd ~/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2/desktop
npm install        # one time
npm run dev        # ← daily: test with live logs
# …when finished:
npm run dist       # ← cut the .dmg
```

In `npm run dev`: Electron main-process logs, the Python backend logs, AND the React console
all print to the terminal; DevTools opens automatically for interactive UI debugging.
(Set `USE_VOICE=0 npm run dev` to skip loading the heavy voice models for a faster start.)

## Build the real app (.dmg you double-click)
```bash
cd ~/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2/desktop
npm install                 # one time, downloads the build tools
npm run dist                # builds the UI + packages a macOS .dmg
```
The installer appears in `desktop/release/Odin-1.0.0.dmg`. Open it, **drag Odin to Applications**,
then **pin it to the dock** and double-click — like any native app. No terminal, no `npm` after this.

- First open: macOS may say "unverified developer" (the app is unsigned). Right-click the app →
  **Open** → **Open** once; after that double-click works normally.
- The app starts the Python backend itself on launch (it finds the project folder automatically,
  or set `ODIN_ROOT`). If you already ran `./server/run.sh`, it just connects to it.

## Update the app later
Re-run `npm run dist`, open the new `.dmg`, and drag Odin to Applications (replace). The pinned
dock icon keeps working — same app, updated in place.

## Faster: just rebuild the app bundle (no installer)
```bash
npm run pack                # outputs desktop/release/mac/Odin.app — drag to Applications
```

## Dev mode (hot reload while you work on the UI)
```bash
cd desktop && npm run start      # Vite + Electron with live reload (backend auto-starts)
```

Open Settings (⚙️) in the app to point at a different backend URL or set an access token.

## What's where
- `src/App.jsx` — shell: sidebar, breadcrumbs, live-activity polling, routing.
- `src/views.jsx` — Dashboard (company), ProjectView (project CTO), MemberView (team member), modals.
- `src/ChatPanel.jsx` — multi-level streaming chat + voice (Whisper mic, Kokoro/Coqui speech).
- `src/ui.jsx` — animated avatars (heartbeat), markdown, modal, usage bars.
- `src/api.js` — backend client (REST + SSE + voice).
- `electron/main.cjs` — desktop window; optionally spawns the backend.

Voice never uses the OS voice — English = Kokoro, Arabic = Coqui XTTS, via the backend.
