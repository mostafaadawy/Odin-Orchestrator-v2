# DEPLOY / SYNC — Organics (local → Azure VM)  ·  DevOps agent ONLY

OBJECTIVE: Update the Azure VM with the latest LOCAL code, then run the listed
commands, reboot, and verify it's back online. SOURCE is always local; DEST is the VM.
This is an EXISTING PRODUCTION app — touch only what's listed here.

## Agents
- Use the **DevOps agent ONLY**. Do NOT involve or activate QA, Frontend, Backend,
  Security, or any other agent at any stage.

## ONE command the agent runs
- The agent runs **`bash infra/deploy_run.sh`** (add `--bootstrap` for a full clean redeploy that marks
  every file changed). It chains: change-detection → deploy (rsync→migrate→build→restart bendcore-staging+organics-staging)
  → STRONG verify (fresh builds + :4014/:3001 == 200 + DB users/roles/superadmin/appSettings seeded) →
  update change-lists ONLY on a pass. Each stage gates the next; a failed verify STOPS and never updates
  the lists and never reports success. The steps below are the reference the orchestrator implements.
- **The reboot solution:** after the build, restart ONLY `bendcore-staging`+`organics-staging` (re-runs bendcore's boot
  self-seed to repopulate users/roles/captcha config after a reset, and loads the new frontend build).
  NEVER full-reboot the shared VM, NEVER touch nginx/ports/the other 5 sites.

## Step 0 — CHANGE DETECTION (run FIRST, before anything else)   ← REQUIRED
- The FIRST action of every deploy is: `python infra/deploy_changes.py scan`.
  It keeps TWO saved lists (front-end + back-end) of every deployable file + its **modification date**,
  built from the LOCAL `RBO-Staging/f` / `RBO-Staging/b` folders, EXCLUDING exactly the items in
  the "NEVER sync" list below (node_modules, .env*, .backup-env, build folders `.next`/`dist`, package.json
  + lockfile, public, uploads, logs). It compares current mtimes to the saved lists and reports
  added / modified / removed.
- **If NOTHING changed (and a baseline exists) → deployment is NOT required. STOP and report "no changes".**
- **If there are changes → show me the changed files and ASK for my approval** before deploying, and deploy
  **only the changed files** (`python infra/deploy_changes.py changed <backend|frontend>` feeds rsync `--files-from`).
- One-time bootstrap: if there is no reliable saved list, run `python infra/deploy_changes.py seed-old` once
  (baseline dated 2 years ago) so this run detects EVERYTHING as changed → a clean full overwrite via the
  NORMAL flow (no hardcoded exception).
- **SMART DB-CHANGE GATE (new):** the change-detector also classifies each changed file. If any changed file
  is a **schema** file (`prisma/schema.prisma`, `prisma/migrations/**`) or a **seed** file (`src/seed/**`,
  `prisma/seed*`, `seed-data/**`, `*seed-reference*`), `scan` prints `DB_SENSITIVE: YES` with a
  **RECOMMENDATION (serious, but required): a DATABASE rebase/reseed is recommended**, and lists which
  schema/seed files changed. `deploy_run.sh` then **STOPS and ASKS you to approve or deny** the destructive
  rebase (`ODIN_DB_REBASE=approve` → `migrate reset --force`+reseed; `deny` → code-only, data kept). No
  schema/seed change → non-destructive deploy by default (data kept). The DB decision is never made silently.

## Restrictions for THIS project (bound to the AI agent, not just to the owner)
- The **AI agent runs and reasons through every step**; the owner only monitors/approves. Do not do the work
  "as yourself" outside the project flow.
- **Never** touch nginx, ports, or the other 5 sites on the shared VM. **Never** full-reboot the VM (restart
  only `bendcore-staging`+`organics-staging`). **Never** run app commands as root; **never** `npm run start`.
- `az` is used ONLY to refresh the SSH firewall (NSG port-22 + ufw single-IP; keep 80/443 open; never widen).
- The deploy is not "done" until `deploy_verify.py` prints ✅ PASS (fresh builds + :4014/:3001 200 + DB
  seeded incl. a superadmin). Only then are the change-lists updated. Never report a fake success.
- **After a VERIFIED-successful deploy (services healthy), run `python infra/deploy_changes.py update`** to save
  each file's **real** current modification date as the new baseline — so future runs detect only real changes.

## Connectivity (how to reach the VM)   ← CORRECTED
- Reach the VM over **SSH as the user `mostafa`**, authenticating with the PASSWORD in
  `oth/.cred` (key `azvmcred`). Force password auth so SSH doesn't fail on key offers:
  `sshpass -p "$PW" ssh -o PreferredAuthentications=password -o PubkeyAuthentication=no -o StrictHostKeyChecking=no mostafa@<vm-ip> '<cmd>'`
  and for files: `rsync -az -e 'ssh <same opts>' <excludes> <local>/ mostafa@<vm-ip>:<dest>/`.
- Before any SSH/rsync, **refresh the firewall to my CURRENT public IP** (Azure NSG port-22 rule
  + ufw): single-IP allow, deny all others — never widen it. (Firewall is the only thing done
  via Azure; app commands do NOT run that way — `az` is on my Mac, not the VM.)
- **Run every app command AS the user `mostafa`, NEVER as root.** Only `sudo reboot` is elevated
  (run as mostafa via `sudo -S` with the password). Root-owned files lock me out.

## Folder mapping (source → destination)
- Local frontend  `/Users/mostafaadawy/Desktop/VolatileWorkSpace/RBO-Staging/f`  →  VM `/home/mostafa/RBO-Staging/f`
- Local backend   `/Users/mostafaadawy/Desktop/VolatileWorkSpace/RBO-Staging/b` (a.k.a. bendcore)  →  VM `/home/mostafa/RBO-Staging/b`

## NEVER sync / never touch these (excludes — apply to BOTH unless noted)
.env*  ·  .backup-env  ·  *.pem  ·  *.key  ·  config/google-oauth-client.json  ·  *.mp4  ·  *.mp5
·  *.copy  ·  *.bak  ·  *.tmp  ·  *.DS_Store  ·  node_modules/**  ·  dist/**  ·  logs/**
·  prisma/migrations/**  ·  .next/**  ·  package.json  ·  package-lock.json  ·  public/**
·  uploads/**  ·  organics-local-vm-deploy-sync/**
(These hold secrets, dependencies, build output, or production data — keep them untouched on the VM.)

## Backend commands — run in `/home/mostafa/RBO-Staging/b`, in this exact order, as `mostafa`
DATABASE — pick ONE and tell me which you authorize THIS run:
  (A) NON-destructive (keep data, default):  `npx prisma generate && npx prisma migrate deploy`
      ← CORRECTED: `migrate deploy` applies committed migrations only — it NEVER resets and
        never prompts. (The old interactive dev-migration command was wrong here: it resets on
        drift and hangs over SSH.)
  (B) DESTRUCTIVE wipe+reseed (ONLY if I explicitly say "reset this run"):
      `npx prisma migrate reset --force` (drops, re-applies all migrations, reseeds — DATA LOSS).
BUILD:
  `rm -rf dist && npm run build`

## Frontend commands — run in `/home/mostafa/RBO-Staging/f`, in order, as `mostafa`
  `rm -rf .next && npm run build`

## Final step (after BOTH frontend and backend complete)
  `sudo reboot`

## Strict restrictions
- Run ONLY the commands listed above. No extra commands.
- NEVER run `npm run start` or any start-like command.
- NEVER run system installs (`apt`, `npm install -g`, nodesource) — if a tool/version is
  missing, STOP and ask me; do not install it yourself.
- Never read, copy, or sync any secret/.env/.backup-env/key.

## After reboot — VERIFY (mandatory gate), then report   ← REQUIRED, no fake "healthy"
- HTTP 200 is NOT proof of a good deploy. A `migrate reset` can drop every table UNDER a still-running
  process, so the OLD process keeps answering 200 while the DB is EMPTY and every login fails with
  "You do not have permission to perform this action". (Real incident 2026-07-16.)
- The FINAL action of every deploy is: **`python infra/deploy_verify.py`**. It:
    1. **Smart endpoints** — polls backend (`http://127.0.0.1:4014`) and frontend to a REAL HTTP 200
       (retries through startup, not a single shot).
    2. **DB health check (every time)** — over SSH as mostafa, confirms `users > 0`, `rbacRoles > 0`,
       at least one `isSuperadmin=true`, and key tables seeded (`products`, `appSettings`).
    3. **Auto-remediate by restart** — if the DB check FAILS (empty/partial) but the service is up, it
       runs `sudo systemctl restart bendcore-staging` (as mostafa) so `main.ts` boot `seedIfNeeded()` refills the
       DB, waits, and re-checks. (Restarting the service after a reset is what re-runs the seed — the step
       that was skipped in the incident.)
    4. **Verdict** — PASS only when endpoints 200 AND DB seeded (+ superadmin present). Otherwise ❌ and I
       do NOT report success.
- Also check `systemctl status` for both services.
- Then send me a clear status report: sync summary, build output/errors, service status, **DB health
  numbers (users/roles/superadmin/products)**, timing, and the PASS/FAIL verdict.
  If still ❌ at timeout, report the last error + journalctl logs + a rollback suggestion — never a fake OK.

## This run vs future runs
- Honor the DB choice (A or B) I authorize for THIS run only.
- From the NEXT run on, re-confirm the full exclude list AND the exact commands with me before
  doing anything — no standing authorization carries over.

Handle this safely and exactly: do not add, skip, or reorder anything. Every change to the VM
waits for my approval before it runs.
