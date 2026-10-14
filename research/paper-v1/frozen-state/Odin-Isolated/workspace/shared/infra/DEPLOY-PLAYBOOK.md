# Local → VM Sync / Deploy Playbook (owner's rules + the smart pre-flight to build)

> Captured 2026-06-23 from the owner. ANY local→cloud sync/deploy MUST follow these standing
> rules AND run the context-aware pre-flight below. This is sensitive (production VM): the system
> reasons about the ACTUAL folder content, never blindly, and respects the owner's decisions.

## Owner's standing rules (defaults — always apply)
- **Never touch `node_modules`.**
- **`public` (frontend), `upload` (backend), `logs`** — these hold large/important data. ASK each
  time whether to include or exclude (sometimes new images should sync, sometimes leave untouched).
- **`package-lock.json`** — do NOT touch unless there are real dependency changes.
- **`.env`** — DO NOT update the production `.env` (true ~99% of the time). The local `.env` is
  dev-only. Exclude by default; only touch on explicit, per-run approval.
- **`npm install`** — sometimes needed; ASK (and run only if dependencies changed).
- **Always remove the destination folder before rebuilding.**
- **Always rebuild BOTH frontend and backend.**
- **Restart via `systemd`** (auto-start), NOT `npm start` directly.
- **Reboot after updates** is the owner's habit — BUT a smart system should suggest the safer
  alternative of **restarting only the affected `systemd` service(s)** when that suffices.

## Smart pre-flight (NOT a fixed list — driven by reading the folders)
Before proposing anything, the system must:
1. **Read & analyze** the local and VM folders (structure, sizes, presence of `.env`,
   `public`/`upload`/`logs`, `package-lock` diffs, git status, dependency changes).
2. **Detect production** (running services, real data, env markers) and raise criticality.
3. **Ask context-aware questions** based on what it actually found, e.g.:
   - Touch `.env`? (default: no)
   - Production — avoid DB reseed/re-migrate? Or do you want a full reset+remigrate this time?
   - Include `public` / `upload` / `logs`? (per folder, based on what changed/their size)
   - After updating, rebuild and report any `pm2`/build errors?
   - Restart only the affected service(s) or full reboot?
   - Dependencies changed → run `npm install`?
4. **Respect the owner's answers**, support doing **frontend + backend together** in one run with
   the relevant questions asked for each, and **propose safer/more efficient alternatives** when
   appropriate.
5. Present the EXACT commands + impact + rollback, get final approval, execute, then report
   results (build output, errors, service status).

## Post-deploy verification (the QA/checker step — always runs after a deploy)
After the deploy/restart, a QA/checker MUST verify the service actually comes back ONLINE — it
won't be up instantly:
- Poll the health endpoint / public URL with a delay+retry loop (e.g. curl every ~10s, up to a
  sensible timeout like 2-3 minutes), waiting for HTTP 200.
- When it responds, report ✅ online (with response time). If it's still down at the timeout,
  report ❌ with the last error + the service logs (`journalctl -u <svc> --no-pager -n 50`) and
  suggest a rollback — do NOT pretend it's healthy.
- Never report success until the checker has actually seen the service respond.

## Status
The smart pre-flight is NOT built yet (current sync/deploy is a blunt gated execute). Build this
flow next, with these rules baked in as defaults. Until then, do NOT run sync/deploy on production.
