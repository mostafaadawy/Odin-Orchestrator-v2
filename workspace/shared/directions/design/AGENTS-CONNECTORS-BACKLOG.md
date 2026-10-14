# Requested capabilities — agents, connectors, scheduling, attachments, presets

Status as of 2026-06-23. Verified = compiles + smoke/route-tested in sandbox (engine behavior runs
on the owner's machine).

## ✅ DONE
- **Scheduler is VISIBLE** — per-project "⏰ Scheduled tasks" panel (cadence, runs, assignee) with
  add/remove. (verified)
- **Periodic agent** — a scheduled task can be **assigned to a specific agent** (e.g. SecMan hourly);
  it runs AS that agent, logged in its chat + rolled up to the CTO. (verified)
- **Company-level agents** — create an agent once on the dashboard (name/role/rule); it is
  **auto-added (native) to every new project**. (verified: new project team included the company agent)
- **External connectors with API key + status badge** — add Google Analytics / Klaviyo / MCP etc.
  with a key → "connected" badge; keys stored privately (gitignored). (verified)
- **Project presets** — one-click "Deployable web app (FE+BE+DevOps+QA)", "Static landing", "Mobile".
- **Chat + button (attachments)** — every chat input has a ＋ to attach file(s) or folder(s) by path
  (native picker); the paths are included in the message so the engine reads/uses them — e.g. point
  to the local folder(s) to sync and the Azure destination during a deploy.
- **Build inside the chosen folder** — agents now run with cwd = the project's folder (not the app repo).
- **E2E updated** — now checks company agents (auto-seed), connectors, and agent-assigned periodic schedules.

## ⚠️ Partial / honest
- **Periodic agent AUTO-triggering other agents** (SecMan finds a vuln → FE bumps the package → DevOps
  redeploys): the agent runs periodically and reports/rolls up to the CTO, and it can recommend the
  hand-off — but a hard-wired automatic cross-agent delegation chain from a finding is engine-guided,
  not yet a fixed loop. Next.
- **Attachments** pass file/folder PATHS to the engine (which can Read them); they are not uploaded
  into a vector store. For local files/folders/images on the owner's machine this is what's needed.
