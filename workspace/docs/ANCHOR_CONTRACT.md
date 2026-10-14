# Anchor Connect — Phase 1 Definition of Done + Interface Contract

This is the **single source of truth** for Anchor Connect. Phase 2 (Flutter mobile/web), real
third parties, and Phase 3 (deployed anchor) all integrate against **exactly** these shapes. The two
E2E suites enforce this contract, so real integration is a *replacement of the fake side, not a
redesign*.

## Components (all additive; existing AI features untouched)
- `server/anchor_queue.py` — smart queue + lifecycle + webhook delivery + ack + retry (durable, in `data/anchor_queue.json`).
- `server/anchor.py` — HTTP API (`/anchor/v1`) + local‑machine poller.
- `server/e2e_anchor.py` — logic E2E (real webhook round‑trip; runs anywhere).
- `server/e2e_anchor_http.py` — **HTTP contract** E2E (real FastAPI endpoints + auth; run where fastapi is installed).

## Auth
`X-API-Key: <ANCHOR_API_KEY>` (from `oth/.cred`). Required when the key is set; open on localhost until then.

## Endpoints

### Third party / remote client → anchor
```
POST /anchor/v1/requests
  body : {"project":"<identifier>","prompt":"...", "payload":{...}?, "webhook_url":"https://...", "sender":"..."}
  200  : {"request_id":"req_xx",  "status":"queued",  "message":"received — ..."}

GET  /anchor/v1/requests/{request_id}
  200  : {id, project, status, result, webhook_attempts, acked, error, created, updated, history}

POST /anchor/v1/requests/{request_id}/ack      # explicit async ack (alt to 2xx webhook ack)
  200  : {"ok":true}
```

### Local machine (client that pulls work)
```
GET  /anchor/v1/poll
  200  : {"tasks":[ {id, project, payload, webhook_url, status, ...}, ... ]}   # only un-handed-out, never finished

POST /anchor/v1/requests/{request_id}/result
  body : {"result": <any JSON>}
  200  : {"ok":true}   (or {"ok":true,"already":true} if already finished — idempotent)
```

### Admin / dashboard
```
GET  /anchor/v1/admin/requests?status=<optional>   -> {"requests":[...]}
GET  /anchor/v1/admin/counts                        -> {"counts":{status:n,...}}
GET  /anchor/v1/admin/config                        -> {retry_count, retry_interval_sec, poll_limit}
POST /anchor/v1/admin/config  {retry_count?, retry_interval_sec?, poll_limit?}
```

### Webhook delivered TO the third party (their endpoint)
```
POST <webhook_url>
  body : {"request_id","project","status":"completed","result":<...>,"attempt":N}
  the third party MUST reply 2xx  == acknowledgement.  Non-2xx → anchor retries.
```

## Status lifecycle
`received → queued → sent_to_local → processing → response_received → webhook_sent → (acknowledged → finished)`
Branches: `ack_pending` (awaiting retry) ; `failed` (retries exhausted) ; `cancelled` (admin).
**A request is FINISHED only after the local machine returned a result AND the webhook was acked.**
"Delete" is never a real delete — it is a final status flag. A finished/failed task is **never**
re‑polled or re‑processed.

## Retry
Default `retry_count=4`, `retry_interval_sec=600`; both configurable via `/admin/config`. The local
poller runs the retry sweep; `ack_pending` tasks re‑deliver when their interval elapses; exhausted →
`failed` (record kept with its result).

## Phase‑1 Definition of Done (all must be GREEN before Phase 2)
Run both:
```
python3 server/e2e_anchor.py        # logic + real webhook  (runs anywhere)
python3 server/e2e_anchor_http.py   # real /anchor/v1 HTTP + auth  (run where fastapi is installed)
```
Done means every check passes:
- [ ] auth rejects missing/invalid key (when key set)
- [ ] POST /requests returns a unique `request_id` and `queued`
- [ ] local `/poll` receives the task; it flips to `sent_to_local`
- [ ] POST /result stores it and delivers the webhook
- [ ] third party receives the **exact** result; replies 2xx → `acknowledged` → `finished`
- [ ] a finished task is never re‑polled; re‑submit is idempotent
- [ ] flaky webhook → retries → eventually `finished`, with the real attempt count
- [ ] always‑failing webhook → `failed` after `retry_count` (record kept, not deleted)
- [ ] admin config + counts reflect real state

## How Phase 2 (Flutter mobile/web) consumes this
Phase 2 is a **client of these same endpoints** (plus the existing project/chat APIs), with
**on‑demand refresh** (load on click, not constant polling):
- Anchor status page → `GET /anchor/v1/admin/requests` + `/admin/counts`.
- Projects/chat → existing `/projects`, `/scope/*` endpoints.
- Auth → `X-API-Key` (same key).
Because Phase 2 talks to this exact contract, swapping the local anchor for the **deployed** anchor
(Phase 3, on the Azure VM) needs no client change — only the base URL.

## How Phase 3 (deploy) preserves this
The anchor deploys to the Azure VM unchanged; the local machine then polls the **same** `/anchor/v1`
endpoints over HTTP instead of in‑process. Same contract → seamless cutover. The Phase‑3 prompt for
Odin must validate the live anchor against this exact checklist.

---

# Phase 2 — the app + the remote-topology test harness

Phase 2 = the Flutter app (`odin_app/`, **one shared codebase** for web + Android + iOS) **plus**
the scripts that let us run the *Phase‑3 topology now*, with only the anchor's **location** simulated.

## Final-state architecture (agreed)
- **Mobile** (Android/iOS): standalone client of the VM anchor over the internet.
- **Web + anchor backend**: deployed **together to the Azure VM** (same origin). The backend owns
  queuing, auth, webhooks; the web build is served beside it.
- The Flutter UI is **shared** between web and mobile (no duplication); the **anchor backend is a
  separate deployable project** — built in Phase 3 (Docker + systemd). For Phase 2 testing,
  `server/anchor_remote.py` already *is* that standalone backend, just not yet containerized.

## Pieces (Phase 2)
- `odin_app/` — Flutter client of this contract. Screens: Projects, Chat, Anchor status, Settings.
- `server/anchor_remote.py` — **stand-in for the deployed anchor**: serves the exact `/anchor/v1`
  contract over real HTTP on a chosen host:port, backed by the same `anchor_queue`; owns webhook
  delivery + retry sweep (as the VM will). `python3 server/anchor_remote.py --port 9100`.
- `server/local_poller_http.py` — the **local machine** talking to the anchor **only over HTTP**:
  pulls tasks, runs the real CTO→team orchestration, posts results.
  `python3 server/local_poller_http.py --anchor http://localhost:9100`.
- `server/e2e_phase2.py` — topology E2E (app ⇄ remote anchor ⇄ local). `--smoke` = fast plumbing
  check (runs anywhere); default = real orchestration + real read-only Klaviyo/Veeqo numbers.

## The IP/port concern (Phase 2 → Phase 3)
The app keeps **two** base URLs per environment profile, because they move independently:
- `apiBaseUrl` → `/api/v1` (project list + synchronous chat) — the local **brain**.
- `anchorBaseUrl` → `/anchor/v1` (queue + status) — **local now, the VM ip:port later**.

And a **mode** per profile:
- `direct` (same network / Phase 2): chat is synchronous via `/api/v1/p/{id}/ask`.
- `anchor` (remote / Phase 3): chat is an **async anchor request** — `POST /anchor/v1/requests`
  then poll `GET /anchor/v1/requests/{id}` until terminal. **Identical screens; only transport differs.**

Shipped profiles (edit IP/port/keys in **Settings**): `Local (Phase 2)`,
`Anchor sim (Phase 3 test)` (anchor → `http://localhost:9100`), `Deployed (Phase 3)` (anchor →
`http://YOUR_VM_IP:PORT`). **Going to Phase 3 = pick the Deployed profile + set the anchor URL.**

## Run the topology test
```bash
# fast plumbing (HTTP + queue + webhook + ack), runs anywhere:
python3 server/e2e_phase2.py --smoke
# REAL remote round-trip (real CTO→team orchestration + real read-only numbers), run on your Mac:
python3 server/e2e_phase2.py
```

## Build + run the app (on your Mac, needs the Flutter SDK)
```bash
cd odin_app
flutter create . --platforms web,android,ios --project-name odin_app --org com.odin
git checkout -- lib/      # restore our entry point if flutter regenerated lib/main.dart
flutter pub get
flutter run -d chrome     # web   (or a device id for Android/iOS)
```

## Phase-2 Definition of Done
- [ ] `e2e_phase2.py --smoke` passes (remote HTTP topology + webhook + ack).
- [ ] `e2e_phase2.py` passes on the Mac (real orchestration; exact Klaviyo/Veeqo numbers).
- [ ] App builds and runs on **web** and at least **iOS**; Projects/Chat/Anchor/Settings work.
- [ ] In `direct` mode chat answers synchronously; in `anchor` mode it goes async via the anchor and
      shows the lifecycle, returning the same real result.
- [ ] Switching to a remote anchor is **only** a profile/base-URL change.
