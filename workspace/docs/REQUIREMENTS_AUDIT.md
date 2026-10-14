# Odin — Requirements Audit (this session)

Review of every real requirement you raised, with honest status. Verified = confirmed in code/tested here.
"Pending your run" = code is done but not yet confirmed live in your last drill (the next `phase2_up.sh` run
validates several fixes at once).

## ✅ DONE — verified in code / tested here
1. **Phase 2 mimics Phase 3 — web & mobile go ONLY through the anchor.** Pure anchor profile (apiBase empty);
   no hardcoded backend URL. Kill the anchor → the app gets nothing.
2. **All app READS come from the anchor** (not just projects): projects, health, roles, company agents,
   connectors, activity/statuses, and message pools — via the anchor mirror + `/anchor/v1/pool/{id}` +
   `/anchor/v1/mirror/{key}`. The poller pushes all of these.
3. **Durable mirror** — the anchor persists its synced snapshot to disk; survives anchor restarts AND
   desktop-offline periods. Returns `updated/age_seconds/stale`.
4. **Offline sensing** — app shows "You are offline / Try again" when the anchor is unreachable; no stale
   data, no infinite spinner. Retry genuinely attempts (spinner held ~0.8s so you see the attempt).
5. **Phase 2 asks "use anchor? [Y/n]"**; `anchor_up.sh` runs the anchor standalone (second-terminal drill).
6. **Web renders** — Phase 2 builds a RELEASE web and serves it statically (the debug dev-server was the
   splash-hang cause). Auto-opens; served no-cache.
7. **Ctrl-C closes everything** (brain, anchor, web, sim, webhook, desktop:5173).
8. **Quitting the mobile no longer closes the session** — mobile run backgrounded; only Ctrl-C stops all.
9. **No port spam in the terminal** — clean status output.
10. **Anchor landing page** opens in the browser ONLY when anchor = yes (browser gets HTML, API gets JSON).
    **Request page** always opens (so you can test offline sends).
11. **Request page = SQLite + response files** — its own durable log (`server/sim_server.py`): requests
    persist across refresh AND browser close; responses saved to files (pointer in DB); ↻ Refresh statuses
    button (re-queries the anchor by ID); ✕ delete per request. Tested end-to-end.
12. **Fast-ack feedback on the request page** — Send shows "✓ ACKNOWLEDGED (queued, result via webhook)";
    when the anchor is off it shows "✗ Anchor offline — not received".
13. **Async queue = standard pattern** — every request has a unique ID + its own return URL; the anchor
    acks immediately (no wait, no 502); the local machine pulls, works out-of-band, posts result by ID; the
    anchor delivers to the return URL (2xx=ack, else retry). Retrievable by ID any time.
14. **Deploy fingerprint gate** (Phase 3) — code changes always redeploy (no silent skips).
15. **`agent_terminal_bridge.sh`** — controlled terminal access for you to grant (Ctrl-C revokes).

## ⏳ PENDING your run (code done — confirm in the next drill)
- The full offline→online drill on web + mobile (items 4,6,8) with the latest fixes.
- The request page persisting across refresh/close in the live run (item 11).

## 🟡 PENDING — needs the terminal bridge (Postgres)
16. **Anchor storage → PostgreSQL** (robust DB; on your Mac now, Azure later), with big AI responses saved
    to files under `active_requests/<request_id>/<random>.json` (path in Postgres; small results inline via
    a size threshold). Requires you to run `agent_terminal_bridge.sh` so I can create the dev database.
    Desktop stays untouched.

## 🆕 NEW — just requested, to build next
17. **Request page: "Clear all" button** — bulk delete/clean the request-page database from a button.
18. **Anchor landing page: protected "Manage" area** — a Manage button that requires login:
    - email `tech@odinmarkets.com`, password (provided, for now), + a **random confirmation code**.
    - "Remember this device & browser" to skip the code next time.
    - Inside: full CRUD on current requests, plus toggles to **allow/stop the mobile** and **allow/stop the
      web** (default allowed), and other useful management fields.
19. **Desktop: "Connecting with Anchor" topbar indicator** (intentional new desktop feature) — when the
    anchor generates a login code (because Manage was pressed on the landing page), this **blinks** on the
    desktop; opening it shows a dialog with the sign-in **email, password, and the received code** to copy.
    (This is the secure channel that gates the protected Manage CRUD.)

## Notes
- "Desktop must not be affected" = its existing behavior is unchanged. Item 19 is a deliberate NEW addition
  you asked for (the code indicator), not a change to existing desktop function.
- Phase 3 (VM deploy) is intentionally paused until Phase 2 is fully confirmed.
