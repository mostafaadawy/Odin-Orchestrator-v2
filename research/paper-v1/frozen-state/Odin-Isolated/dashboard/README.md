# Dashboard

Two ways to view the CTO Brain dashboard:

## 1. Static local file (`index.html`)
- Double-click to open in any browser — it shows a built-in snapshot even with no server.
- For **live** data, serve the project folder so it can fetch `state/*.json` and `history/log.jsonl`:

```bash
cd Odin-Orchestrator
python3 -m http.server 8080
# then open http://localhost:8080/dashboard/index.html
```

It reads:
- `state/project.json` — progress, phases, features, delivery status
- `state/tasks.json` — active tasks & owners
- `state/approvals.json` — pending approvals
- `history/log.jsonl` — recent decisions & history

## 2. Live Cowork artifact
A persistent dashboard that re-opens across sessions is also created in this workspace.
Ask me to "open the Odin dashboard" any time and I'll surface it.

## Mobile / desktop
The static page is responsive and works on phones (single-column) and desktops (multi-column).
The Cowork artifact is accessible from the Claude desktop and mobile apps.
