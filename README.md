# Odin Orchestrator — v2

Odin is a local multi-agent orchestration system: a "brain" on your Mac (FastAPI, Postgres, Claude CLI as the engine)
plans work, routes it to specialist agents, asks you before anything changes your files or the VM, and keeps an audit
trail. The desktop app talks to the brain directly; the web app, the mobile app and outside callers reach it only
through the **Anchor** (a relay on your VM) — never the brain itself.

v2 is v1 with every Phase 3 fix, the local decider **Jev**, secure phone approvals and all research in one folder.
What changed and why: **`CHANGES.md`**. Change log: `CHANGELOG.md`.

## The two commands

```bash
# 1) ENVIRONMENT — local, no deploy, no cost: brain + local Anchor + poller + webhook + external-user page + web app
#    + desktop app + iOS simulator, with seeded test data. Create an internal project and watch it work everywhere.
bash ~/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2/shells/development_full_checker.sh

# 2) PRODUCTION — deploys the Anchor + web to your VM (asks first), switches every link to the production URLs,
#    builds the mobile app, then asks you to connect your iPhone to install it.
bash ~/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2/shells/production_full_checker.sh
```

Both stop cleanly with **Ctrl-C** (every port is freed). Useful options:

| Option | Script | Effect |
|---|---|---|
| `USE_ANCHOR=0` | environment | offline drill: web/mobile must show "You are offline" |
| `ODIN_DECIDER=jev` or `normal` | environment | set the decider mode at start (otherwise the saved mode is kept) |
| `ODIN_HEADLESS=1` | environment | same stack, nothing pops up (used for automated proofs) |
| `--rotate-keys` | production | new Anchor API key, Manage password and VM password before the deploy — all generated and saved locally (backup kept), no prompt |
| `ODIN_PHASE3_YES=1` | production | skip the deploy confirmation (only when you mean it) |
| `ODIN_SKIP_MOBILE=1` | production | do not build/install the phone app this time |

## What each part is

| Part | Where | Port (local) |
|---|---|---|
| Brain (backend) | `server/` (+ `orchestrator/`) | 8000 |
| Anchor (relay) | `server/anchor_remote.py`; online at `https://anchor.odinmarkets.com/odin-anchor` | 9100 local |
| Poller | `server/local_poller_http.py` (supervised by `shells/poller_supervisor.sh`) | — |
| Webhook receiver | `server/webhook_receiver.py` | 9300 |
| External-user page | `workspace/anchor-layer/anchor_sim.html`, served by `server/sim_server.py` (webhook pre-wired) | 9104 |
| Web app | `odin_app/` (Flutter, release build served statically) | 8080 |
| Mobile app | `odin_app/` (Flutter iOS) | — |
| Desktop app | `desktop/` (Electron + React) | 5173 in dev |
| Data | Postgres `odin_core` (brain), `odin_anchor` (Anchor), files under `workspace/` and `data/` | 5432 |

## Desktop app (DMG)

```bash
bash ~/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2/shells/build_desktop_dmg.sh
```

Builds `desktop/release/Odin-<version>.dmg`, checks the bundle carries no owner secret and no v1 path, then installs it
into a temporary folder with a temporary profile and starts it against the isolated test clone to prove it starts its
backend from a clean path and quits cleanly. To install: quit the old Odin, drag the old `Odin.app` out of
Applications, open the DMG and drag Odin in. First launch: right-click ▸ Open (the app is ad-hoc signed).

Where things live for the installed app:

* backend folder: `~/Desktop/AiAgentWorkSpace/Odin-Orchestrator-v2` (a saved choice is honoured only if it is a v2
  folder; `ODIN_ROOT` overrides);
* owner secrets: macOS Keychain, service `odin-anchor`, accounts `anchor-key`, `manage-email`, `manage-password`
  (written by `python3 server/odin_secrets.py keychain`, which the production script runs; `status` shows
  present/missing, never a value);
* app profile: `~/Library/Application Support/odin-desktop`;
* brain token: `data/brain_token` (created by the brain, mode 600).

## Jev — the local decider

Settings ▸ Decider: **Normal** = exactly the v1 path (the LLM decides). **Jev** = a frozen Qwen2.5 model on the Mac
(MLX) with one small head per decision (mode, specialist, read/change, QA gate, agent nature); low confidence, disabled
classes and any owner exclusion fall back to the LLM. Until your labels are applied Jev runs in **shadow** (logged, the
LLM still decides). Models: `research/phase4/models` (0.5B active, 1.5B kept); heads: `data/jev`.
After your labels: `bash research/phase4/after_labels.sh` (layer choice → temperature → thresholds → head-to-head).
Details and measurements: `CHANGES.md` section 4.

## Phone approvals (PC-4)

On the phone: Approvals ▸ **Pair** (sends only the phone's public key). On the Mac: Settings ▸ **Paired phones** — check
that the fingerprint is the one on the phone, press **Trust**. From then on the phone's Approve/Reject is signed on the
phone, encrypted for the Mac, tied to that one request and usable once; the Anchor only relays ciphertext. Keys are
still entered only through the encrypted key field (F-41); "approve all" stays desktop-only. Revoke any time on the Mac.

## Paper v1 reproduction

Paper v1 is frozen in `research/paper-v1/frozen-state` (fingerprinted) and `research/paper-v1-submission`. Any run
that must reproduce paper v1 sets `ODIN_AGENT_RULES_MODE=legacy900` and Decider = Normal.

## Tests

```bash
bash _v2/iso/run_suite.sh <label>      # full re-proof on the isolated clone → _v2/results/<label>/summary.txt
cd odin_app && flutter test            # app tests (incl. F-41 relay, PC-4 digest/signature vectors)
```

The isolated clone (`_v2/iso_root`, rebuilt each run) has its own paths, databases, ports and blank secrets, so the
suite never touches your real data, VM or credentials.

## Folder map

```
Odin-Orchestrator-v2/
├── README.md  CHANGES.md  CHANGELOG.md  CLAUDE.md
├── server/  orchestrator/          brain, Anchor, poller, decider (jev_decider.py), phone approvals
├── desktop/                        Electron app (build: shells/build_desktop_dmg.sh)
├── odin_app/                       Flutter web + mobile app
├── dashboard/  voice/
├── shells/                         the two run scripts, DMG build, Anchor helpers
├── workspace/                      agents, shared rules/runbooks, projects (each project's own folder), chats, logs
├── data/                           runtime data (decider mode, Jev heads, relay key, tokens) — mostly gitignored
├── research/                       paper-v1 (frozen), paper-v1-submission, paper-v2, phase4 (Jev), consolidation
├── docs/program/                   requirements tracker, phase reports, decisions, feature inventory
├── tests/harness/                  the item tests and suites (Consolidated dialect, rewritten for the clone)
└── _v2/                            v2 tooling: repath, replay, isolated clone builder + suite, results
```

## Rules that stay in force

Nothing changes your files, the VM or a database without your approval; RBO Staging and Production are never deployed,
synced, migrated or restarted by Odin; sandbox deploys change the firewall only through your single dynamic-IP rule;
secrets are never printed or committed.
