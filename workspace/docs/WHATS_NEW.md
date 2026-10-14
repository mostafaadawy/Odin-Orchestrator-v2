# What's New in Odin — Feature Guide & Tutorials

This is the documentation the in‑app notification bell points to. The bell badge shows the number of
tabs (one per feature). Each tab is a short tutorial; the full detail for each feature is below.

---

## ⑨ Live Meeting — Voice → Smart Report (Global Voice Streaming Asset)

A reusable, app‑wide asset owned by the **Live Meeting & Voice Streaming Agent** (the existing Audio
Capture Agent, enriched). Any project that needs voice streaming / mic capture / speech‑to‑text /
chunking / meeting reports automatically gets it. Works on **web, desktop, and mobile**.

**How to use**
1. Open a meeting/voice project (e.g. the Zoom Smart Meeting Notification Agent). In the chat header —
   in **both** normal mode and chat‑toggle mode — tap the **speaking‑head** icon (🗣️ /
   `record_voice_over`), next to ▶. It is deliberately different from the plain dictation mic.
2. A **popup dialog** opens (web/desktop) or a **native sheet** (mobile) — never a browser tab.
3. Grant microphone permission → **Start listening**. You see: a big mic, a live **sensitivity** meter,
   **voice‑activity** and **noise** indicators, the detected **language**, and **chunks saving 1, 2, 3…**
4. **Pause/Resume** anytime. Each chunk is transcribed live, its language detected, and low‑confidence
   chunks are marked *"confidence low — may need review."*
5. **Stop** → chunks are **refined** (fillers, duplicate phrases, and stray noise removed; names,
   commands, APIs, files, dates preserved) and merged into one **13‑section smart report** in the
   meeting's majority language.
6. The report appears **inside the dialog** and is **embedded into the project chat** as Markdown. Tap
   **Close** when done.
7. **Export**: Markdown or Word (.docx), Arabic or English — or **“All 4”** as a single zip. The DOCX is
   clean, professional, colorful and structured (RTL for Arabic).

**Per‑chunk data:** id, start/end, language, speaker (if any), raw + cleaned transcript, noise score,
confidence, topic, operational points, status.

**Source & dependencies:** `dashboard/meeting_monitor.html` (shared dialog UI), `server/meeting_api.py`
(`/meeting/*`), `scopes.transcribe` (Whisper), `projects._engine` (report), `python-docx` (export),
`odin_app/lib/screens/meeting_sheet.dart` (native mobile). Full asset spec:
`assets/global_voice_streaming_asset.md`.

---

## ⑩ Deploy — DevOps Production Deployment (Azure VM)

A corrected, repeatable production deployment. **Source is always the local machine; destination is
always the Azure VM.** Executed only by the **DevOps Agent**.

**How it works**
1. The deployment project (e.g. *“Organics Production Deploy (2VM)”*) is created through the **real
   intake flow** — DevOps‑only, no other agents.
2. The **source‑of‑truth** folders (`organics-backend`, `organics-frontend`) are **read‑only**. A working
   copy plus a **`.git` baseline** live under `~/Desktop/Odin/`.
3. A **persistent first‑time flag** (`.deploy_state`): the first corrected deploy ships all allowed
   files; later deploys **diff the `.git` baseline** and ship **only changed files**.
4. Deploy from the project → you preview the exact **rsync + build commands + reboot**, honoring the
   **exclusion lists** (`.env*`, `node_modules`, `dist`, `.next`, `prisma/migrations`, `package*.json`,
   `public`, `uploads`, `*.mp4/mp5/copy`).
5. **Database:** the reset runs **only the first time**; every later deploy **asks before any DB reset**.
   Nothing destructive runs without your approval.
6. After reboot, **health checks** (domain, backend, frontend, nginx proxy, systemd services) confirm the
   change is really live on the VM.

**Config:** `infra/deploy.config.sh` (targets, migrate mode, excludes, reboot). Never sets migrate mode
back to `reset` silently.

---

## Other recent reliability fixes
- **Agent‑terminal bridge** made hang‑proof (output captured to a file, stdin detached, timeout watchdog)
  so backgrounded processes can never freeze it.
- **Stripe checkout**: `finalize` made **idempotent** — after 3DS, if the webhook captured the order
  first, finalize returns success instead of a false “failed payment.” Stripe‑only; Elavon untouched.
- **Notification bell**: the badge now equals the number of tabs, and every new feature gets its own
  documented tab (this file).
