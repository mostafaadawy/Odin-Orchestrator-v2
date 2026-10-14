# ISOLATION STATE — where we are (paused by owner, resume here)

## THE ERROR IS ISOLATED TO ONE POINT: the WEB/FLUTTER app rendering.
Everything BEHIND it is PROVEN working — do NOT re-debug the backend.

## PROVEN WORKING (verified with real data — do not touch):
- **Desktop brain** `localhost:8000/projects` → 200, real projects.
- **Anchor local** `127.0.0.1:48619/anchor/v1/projects` → real projects JSON.
- **Anchor public** `https://anchor.odinmarkets.com/odin-anchor/anchor/v1/projects` → real projects JSON (trace, from VM).
- **Full round-trip** (acting AS the anchor → desktop → response): sent `how many orders this week`
  → `RESULT: Veeqo (live, read-only): 46 orders since 2026-06-27` (req_8585d9e0…). REAL data returned.
- **Poller** (on the Mac, external) syncs `4 projects, N pools, statuses → anchor` continuously, no 502.
- **nginx** `odin-proxy` site enabled, `nginx -t` successful, trusted Let's Encrypt cert, anchor service active.
- Rule: server = anchor asks the local machine; poller pulls + processes + posts result. WORKS.

## THE ISOLATED PROBLEM (work ONLY on this, mimic/isolate — don't reconnect the whole system):
The **web** is stuck at "Web · connecting to your machine…" and the **mobile** shows
`projects: ApiException(404): the anchor returned an error page`. The anchor's response is GOOD;
the APP fails to fetch/render it.

## ⟵ NEW ROOT CAUSE FOUND (Jul 4, isolated from the live VM without the Mac):
Hitting the live anchor directly showed `GET /odin-anchor/anchor/v1/projects → {"projects":[],"updated":0}`.
TWO real causes behind the empty/stuck web, now fixed in code:
1. **Volatile mirror.** `anchor_remote.py`'s `SYNC` was an in-memory global. Every anchor restart (systemd)
   AND every desktop-offline period wiped it → web had nothing to render (updated:0). → Made the mirror
   **durable**: persist to `data/anchor_sync.json` on each `/sync` push, reload on startup. `/projects` now
   also returns `age_seconds` + `stale` for the offline badge. Last-synced projects survive restarts/offline.
2. **Deploy gate skipped code changes.** phase3's smart gate skipped the VM deploy whenever endpoints merely
   returned 200 — so the bootAuth WEB render fix (edited earlier) NEVER actually compiled/deployed (that's why
   the web still hung). → Added a **source-fingerprint gate**: if server/testing/dart source changed since the
   last deploy, force a full redeploy INCL. `export ODIN_FORCE_DEPLOY=1` so `test_web_online.py` rebuilds the web.
   Fingerprint saved only after a successful deploy → fixes can never again silently fail to ship.

## STILL BLOCKED ON (not a code problem): the Mac Phase-3 loop is CLOSED (poller + bridge down since 14:58).
The agent sandbox cannot start the Mac loop or SSH the VM. To make the above LIVE: resume the loop
(`./anchor_loop.sh`) and type `phase3` ONCE. `logs/FORCE_DEPLOY` is already set → it will full-redeploy
(anchor durable mirror + fresh web build), then the poller pushes → mirror fills → web renders the projects.

## FIXES ALREADY APPLIED (on disk, in code):
1. `odin_app/lib/state/app_state.dart` bootAuth: in anchor/production mode (apiBase empty) SKIP the local
   `/auth/config` call (that was the "connecting to your machine" hang) → open immediately.
2. `refreshDashboard`: auto-switch to the Deployed anchor profile if the local brain is unreachable.
3. `anchor_api.dart`: `projects()`/`health()` read from the anchor mirror in anchor mode; clean error (no raw HTML).
4. `config.dart` Deployed profile: `anchorBaseUrl = https://anchor.odinmarkets.com/odin-anchor` + anchorApiKey set.
5. `phase3_up.sh`: on forced deploy runs `flutter clean` so mobile+web rebuild FRESH (stale build was the 404).
6. `test_web_online.py`: web deploy NO LONGER touches nginx (anchor owns the single odin-proxy site) — stops the 404 flip-flop.

## RESUME PLAN — isolate the web only:
1. Rebuild JUST the web/mobile fresh (`touch logs/FORCE_DEPLOY` then `phase3` in the loop) so the bootAuth
   fix + domain URL are compiled in. Confirm the deployed web (`https://anchor.odinmarkets.com/odin-web`)
   opens PAST the spinner and shows the 4 projects.
2. If it still fails, mimic the WEB's exact browser fetch in isolation: GET
   `https://anchor.odinmarkets.com/odin-anchor/anchor/v1/projects` with `Origin:` + `X-API-Key:` headers and
   inspect the RESPONSE HEADERS (CORS: `Access-Control-Allow-Origin`) and the OPTIONS preflight — a CORS/preflight
   gap is the most likely remaining web-only cause. Use Chrome DevTools Network on the running web app.
3. Fix that one point; deploy alone, modify alone. Do NOT rerun the whole system to test — isolate this point.

## Tools available in the loop bridge (logs/phase_ctl/CMD):
health | send <project> <prompt> | tail <comp> | vm | redeploy | audit | auditfix | trace
- `trace` runs testing/trace_chain.py (desktop → anchor local → anchor public → 3b Mac-external → web → nginx).
- Smart gate: phase3 SKIPS the VM deploy when anchor+web healthy (fast). Force full/web rebuild: `touch logs/FORCE_DEPLOY`.
