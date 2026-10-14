"""
Project registry (Phase 2 + Phase 6).

A project is the unit the company CTO manages. It owns: a name/description, its team members
(agents), local↔cloud folder mappings, and its scope id. Supports create-from-description
(the engine generates the component plan), select-existing-local-folder, folder mapping, and
sync/deploy actions (which remain approval-gated and run via the Azure connector).
"""
from __future__ import annotations

import re
import uuid
import store  # type: ignore

# TECHNICAL roles — build/ship software. `deps` = external connectors a role needs to do its job
# (DevOps needs the cloud/Azure). Missing deps are WARNED about, not blocked.
# TECHNICAL members. PRINCIPLE: combine as much as ONE person can own so there is NO back-and-forth and
# NO two people editing the same folders. Web UI + server/API + database are ONE owner (Fullstack).
# Roles are only separated when the work is a genuinely different discipline (mobile, deploy, QA,
# security, firmware, data/ML, game, XR). Each rule states clearly: what they OWN and whether they code.
ALL_MEMBERS = {
    "Fullstack": {"name": "Fullstack", "role": "Full-Stack Engineer", "avatar": "backend", "nature": "technical", "group": "tech", "deps": [], "icon": "🧱",
                  "description": "Builds the ENTIRE web application — frontend + backend + database — in ONE hand, in ANY web stack (Node.js/TS, Laravel/PHP, Python/Django, .NET/C#, Rails, …), installing whatever it needs (Node, Laravel, .NET, etc.). May use Flutter for WEB targets only (never mobile). RESEARCHES & WRITES every third-party integration itself (HubSpot, Klaviyo, Mailchimp, Veeqo, 3PL, GA, …) — for those it only ASKS the relevant operator for that service's API KEY, then writes the calling code. One owner of the whole web codebase: NO frontend/backend hand-off, no shared-folder conflict. Does NOT build mobile apps (Mobile) and does NOT deploy (DevOps)."},
    "Mobile":    {"name": "Mobile", "role": "Mobile Engineer", "avatar": "frontend", "nature": "technical", "group": "tech", "deps": [], "icon": "📱",
                  "description": "Builds ALL mobile apps end-to-end — Flutter, Dart, Xamarin, native iOS & Android (Java/Kotlin/Swift), plus Firebase & Google mobile services — and PUBLISHES to the App Store & Google Play. Writes & edits mobile code. (There is no 'Flutter' role — Flutter is just a tool; web belongs to Fullstack.)"},
    "DevOps":    {"name": "DevOps", "role": "DevOps & Cloud", "avatar": "devops", "nature": "technical", "group": "tech", "deps": ["azure"], "icon": "🚀",
                  "description": "Owns ALL cloud & delivery — ANY provider (Azure/AWS/GCP/…), CI/CD (CircleCI, GitHub Actions, …), Git/GitHub sync, Kubernetes, load balancers, releases & rollbacks. Deploys/operates what others built; writes NO application feature code. Runs LAST, after QA approves."},
    "QA":        {"name": "QA", "role": "QA & Testing", "avatar": "qa", "nature": "technical", "group": "tech", "deps": [], "icon": "✅",
                  "description": "Owns quality — tests, reviews and VERIFIES each part against the brief, runs lint/type-check/test suites, and audits every success claim against real evidence. READ-ONLY: it verifies, it does NOT implement features. Runs AFTER the thing it checks exists."},
    "Security":  {"name": "Security", "role": "Security & Threat Hunting", "avatar": "security", "nature": "technical", "group": "tech", "deps": [], "icon": "🛡️",
                  "description": "Owns security & THREAT HUNTING — scans the codebase for vulnerabilities, hunts breaches, researches new CVEs/threats online, hardens auth/secrets, and runs PERIODIC security checks across BOTH local and cloud, surfacing suspicious activity. Reviews/advises and applies security config; not feature development."},
    "Embedded":  {"name": "Embedded", "role": "Embedded / Firmware", "avatar": "generic", "nature": "technical", "group": "tech", "deps": [], "icon": "🔧",
                  "description": "Owns firmware & on-device software for hardware/IoT (C/C++/Rust/MCU). A distinct platform — separate from web (Fullstack) and Mobile."},
    "Data":      {"name": "Data", "role": "Data / ML", "avatar": "database", "nature": "technical", "group": "tech", "deps": [], "icon": "🧠",
                  "description": "Owns data science & ML — data pipelines, model training/serving, analytics engineering. A distinct specialty from ordinary web app code (Fullstack)."},
    "GameDev":   {"name": "GameDev", "role": "Game Developer", "avatar": "generic", "nature": "technical", "group": "tech", "deps": [], "icon": "🎮",
                  "description": "Owns game development — game logic, engines (Unity/Unreal/Godot) & assets. A distinct platform from web/mobile."},
    "XR":        {"name": "XR", "role": "XR (AR/VR · Unity/Unreal)", "avatar": "generic", "nature": "technical", "group": "tech", "deps": [], "icon": "🕶️",
                  "description": "Owns AR/VR experiences in Unity/Unreal. A distinct platform from web/mobile."},
    "Designer":  {"name": "Designer", "role": "Product Design / UX", "avatar": "generic", "nature": "technical", "group": "tech", "deps": [], "icon": "🎨",
                  "description": "Owns product DESIGN & UX — user flows, wireframes, mockups, the visual design system, accessibility & usability. Produces design specs/assets that Fullstack (web) or Mobile (apps) IMPLEMENT. Does NOT write production code (that is Fullstack/Mobile)."},
}

# OPERATIONAL, NON-technical operators. RULE: they NEVER write or edit app code and they do NOT define API
# contracts/protocols (Fullstack researches & builds those). Each operator HOLDS THE POWER (via an API key)
# to operate ONE external third-party platform. The CTO may ask an operator EARLY only for its API key (to
# be saved). After the app is built, deployed and running, the operator connects to its platform and does
# its real work — feeding live data into the app and reporting status. No two operators share a domain.
OPERATIONAL_MEMBERS = {
    "HubSpot":     {"name": "HubSpot", "role": "HubSpot CRM Operator", "avatar": "generic", "nature": "operational", "mode": "normal", "group": "operational"},
    "CloudDebug":  {"name": "CloudDebug", "role": "Cloud Diagnosis & SRE (read-only VM, logs, systemd)", "avatar": "generic", "nature": "operational", "mode": "normal", "group": "operational"},
    "Marketing":   {"name": "Marketing", "role": "Marketing & Growth", "avatar": "generic", "nature": "operational", "mode": "normal", "group": "operational", "deps": ["analytics"], "icon": "📈", "description": "NON-technical. Plans campaigns, positioning & growth, reads analytics; writes NO code, defines no API protocol."},
    "Email":       {"name": "Email", "role": "Email Specialist", "avatar": "generic", "nature": "operational", "mode": "normal", "group": "operational", "deps": ["klaviyo"], "icon": "✉️", "description": "NON-technical operator of the email platforms (Klaviyo AND Mailchimp) via their API. Configures the account, CREATES email templates, manages LISTS & SEGMENTS, sends/triggers campaigns & lifecycle emails, and ANALYZES sending (opens, clicks, deliverability). Holds the email-platform API key. Early, supplies only that key; writes NO app code (Fullstack builds any in-app email integration)."},
    "Content":     {"name": "Content", "role": "Content Creator", "avatar": "generic", "nature": "operational", "mode": "normal", "group": "operational", "deps": [], "icon": "✍️", "description": "NON-technical. Produces posts, copy & a content calendar; writes NO code."},
    "Support":     {"name": "Support", "role": "Customer Support", "avatar": "generic", "nature": "operational", "mode": "normal", "group": "operational", "deps": ["helpdesk"], "icon": "💬", "description": "NON-technical operator of the helpdesk platform via its API. Triages, drafts replies, reports ticket status; writes NO code."},
    "Sales":       {"name": "Sales", "role": "Sales & Outreach", "avatar": "generic", "nature": "operational", "mode": "normal", "group": "operational", "deps": ["crm"], "icon": "🤝", "description": "NON-technical operator of the CRM via its API. Leads, outreach, follow-ups and pipeline status; writes NO code."},
    "Fulfillment": {"name": "Fulfillment", "role": "Fulfillment Operations", "avatar": "generic", "nature": "operational", "mode": "normal", "group": "operational", "deps": ["veeqo", "easypost"], "icon": "📦", "description": "NON-technical operator connected to ALL fulfillment / 3PL providers (Veeqo, ShipBob, …) and multi-carrier tracking (EasyPost) via their API. Answers anything about orders, shipments, sales channels, revenue/profit, last-month totals, and live shipping/order status. Holds the fulfillment API key(s). Early, supplies only the key; writes NO app code (Fullstack builds any in-app fulfillment integration)."},
    # FIX (owner's Revealer pre-flight): EasyPost was registered as an agent (workspace/agents/easypost, 07-30) but
    # never added to this role catalogue, so resources_block("EasyPost") was EMPTY and the pre-flight refused to run.
    "EasyPost":    {"name": "EasyPost", "role": "EasyPost Shipping & Tracking Operator", "avatar": "generic", "nature": "operational", "mode": "normal", "group": "operational", "deps": ["easypost"], "icon": "🚚", "description": "NON-technical operator connected to EasyPost for multi-carrier shipment TRACKING and rates via its API. Answers live carrier progress (in_transit / out_for_delivery / delivered), tracking numbers, ETAs and exceptions across carriers. Complements Fulfillment/Veeqo: Veeqo owns pre-shipping ORDER state, EasyPost owns POST-shipping CARRIER tracking. Holds the EasyPost API key; supplies only the key early and writes NO app code (Fullstack builds any in-app EasyPost integration). READ-ONLY integration — no label/postage writes."},
    "Analytics":   {"name": "Analytics", "role": "Analytics (Google Analytics)", "avatar": "generic", "nature": "operational", "mode": "normal", "group": "operational", "deps": ["analytics"], "icon": "📊", "description": "NON-technical operator of Google Analytics via its API. Early, supplies only the GA property/measurement ID + key (Fullstack adds the tags in code). After deploy, reads & reports traffic/conversions from the live property; writes NO code."},
    "Writer":      {"name": "Writer", "role": "Technical Writer / Docs", "avatar": "generic", "nature": "operational", "mode": "normal", "group": "operational", "deps": [], "icon": "📝", "description": "Owns product DOCUMENTATION — user guides, API docs, READMEs, release notes, help-center articles. Writes NO code. Distinct from Content (which is marketing copy/posts) and from Designer (visual/UX)."},
    "Finance":     {"name": "Finance", "role": "Finance & Accounting Ops", "avatar": "generic", "nature": "operational", "mode": "normal", "group": "operational", "deps": [], "icon": "💰", "description": "NON-technical operator of the accounting/billing platform (QuickBooks/Xero/Stripe billing) via its API: invoices, reconciliation, revenue/expense reporting. Writes NO code. Distinct from Sales (CRM/pipeline)."},
    "SEO":         {"name": "SEO", "role": "SEO Specialist", "avatar": "generic", "nature": "operational", "mode": "normal", "group": "operational", "deps": [], "icon": "🔍", "description": "Owns search-engine optimization — keyword research, on-page/technical SEO audits, metadata/sitemap recommendations, backlink strategy. Asks Fullstack to IMPLEMENT any code/markup change. Writes NO code. Distinct from Marketing (campaigns/brand)."},
    "Reporter": {"name": "Reporter", "role": "Reporting & Documentation Agent", "avatar": "generic",
        "nature": "operational", "mode": "normal", "group": "operational", "deps": [], "icon": "📝",
        "asset": "report_engine",
        "description": "Owns the reusable REPORTING asset. Given structured info from any project, it "
                       "prepares a fully-styled, comprehensive, branded report and exports it as Markdown, "
                       "Word (.docx), PDF, or PowerPoint (.pptx) — with the company logo + info. Add this "
                       "agent to ANY project that needs professional reports/exports (SOC health reports, "
                       "meeting reports, deploy reports). Uses server/report_engine.py; writes NO app code."},
    "SecCTO": {"name": "SecCTO", "role": "CTO Orchestrator", "avatar": "generic",
        "nature": "operational", "mode": "normal", "group": "security", "deps": [], "icon": "🧭",
        "asset": "soc_run",
        "description": "The SOC's governance & decision agent — the ONLY one that presents decisions to the owner. "
                       "Initiates each run, prevents overlapping investigations, correlates every agent's findings into "
                       "an evidence-based root cause, and raises approval requests. Never approves its own action. "
                       "Owns the run engine (server/soc_run.py). Add this + the security team to ANY security project."},
    "SecArchitect": {"name": "SecArchitect", "role": "Security Intelligence & Threat-Hunting Architect", "avatar": "generic",
        "nature": "operational", "mode": "normal", "group": "security", "deps": [], "icon": "🧠",
        "asset": "soc_intel",
        "description": "Owns external threat INTELLIGENCE + the knowledge base + detection rules + hunt methodology. "
                       "Pulls current advisories (OSV) for our actual versions and fuses professional feeds (CISA KEV, "
                       "abuse.ch) filtered to our stack. Vuln presence != compromise; triages by reachability. Never "
                       "touches production. Uses server/soc_intel.py + soc_intel_fusion.py."},
    "SecInvestigator": {"name": "SecInvestigator", "role": "Security Operations Investigator", "avatar": "generic",
        "nature": "operational", "mode": "normal", "group": "security", "deps": [], "icon": "🔎",
        "asset": "soc_run",
        "description": "The single read-only investigator of the PRESENT state: services, ports/NSG/ufw, website, SSH, "
                       "persistence, miner hunt, application abuse, DB anomaly, subscriber forensics, dependency intel. "
                       "A guard refuses any mutating command. Executes the Architect's hunt hypotheses. Uses server/soc_run.py."},
    "AssetSurface": {"name": "AssetSurface", "role": "Asset, Exposure & Attack-Surface Agent", "avatar": "generic",
        "nature": "operational", "mode": "normal", "group": "operational", "deps": [], "icon": "🗺️",
        "asset": "soc_inventory",
        "description": "Owns the LIVING ASSET INVENTORY & ATTACK-SURFACE map across ALL clouds, VMs, services and "
                       "stacks (Azure VM today; extensible to GoDaddy, Hostinger, AWS, other providers). It enumerates "
                       "every project/service the org runs, fingerprints each stack (Node/Next.js, Laravel/PHP, Python, "
                       "static/landing, DB), and maintains a reverse-search filter list so intelligence is targeted to "
                       "WHAT WE ACTUALLY RUN (not the whole internet). Distinct lane: it answers 'what do we have and "
                       "where is it exposed' — NOT intel curation, NOT detection, NOT prediction. Uses server/soc_inventory.py."},
    "Predictor":   {"name": "Predictor", "role": "Threat Prediction & Prevention Agent", "avatar": "generic",
        "nature": "operational", "mode": "normal", "group": "operational", "deps": [], "icon": "🔮",
        "asset": "soc_predict",
        "description": "Owns FORWARD-LOOKING security: predicts where a weakness is LIKELY to appear next (given our "
                       "stacks, exposure and current findings) and recommends proactive HARDENING to prevent it BEFORE "
                       "exploitation (predict & prevent, not just detect). Distinct lane: future/likelihood, not present "
                       "evidence (Investigator) and not external advisory curation (Architect). Uses server/soc_predict.py."},
    "Recovery":    {"name": "Recovery", "role": "Recovery & Resilience Agent", "avatar": "generic",
        "nature": "operational", "mode": "normal", "group": "operational", "deps": [], "icon": "🛟",
        "asset": "soc_recovery",
        "description": "Owns RESILIENCE: dated, checksummed, ENCRYPTED backups of configuration and database (read-only "
                       "capture, encrypted with a strong key held on the local desktop — never in plaintext on the VM), a "
                       "backups registry, and a SMART recovery protocol that finds the date of a problem and restores from "
                       "the newest CLEAN backup BEFORE it (avoiding over-recovery and re-introducing the damage). Restore is "
                       "always approval-gated. Distinct lane: recover/protect — not detect, hunt, predict or report. Uses server/soc_recovery.py."},
    "BehaviorIDS": {"name": "BehaviorIDS", "role": "Intrusion Detection & Behavioral Analytics Agent", "avatar": "generic",
        "nature": "operational", "mode": "normal", "group": "operational", "deps": [], "icon": "🕵️",
        "asset": "soc_behavior",
        "description": "Owns BEHAVIOR-BASED intrusion detection (UEBA) — catches stealthy, signature-EVADING, AI-era "
                       "attacks by how entities BEHAVE, not by known signatures. It builds a visitor/entity behavior "
                       "profile (IP → cadence, endpoints, accounts-created, user-agent rotation, entropy), flags "
                       "same-IP-many-accounts and machine-regular low-and-slow patterns (the RedBerry 10-minute pattern), "
                       "and SMARTLY separates the owner's legitimate dynamic IP from real bad actors to minimize false "
                       "positives. It recommends UFW/edge blocks for confirmed-bad IPs — ALWAYS approval-gated, never "
                       "auto-applied. Distinct lane: behavioral anomaly over time — NOT static config checks (Investigator), "
                       "NOT future prediction (Predictor), NOT external advisories (Architect). Uses server/soc_behavior.py."},
    "MeetingVoice": {"name": "MeetingVoice", "role": "Live Meeting & Voice Streaming Agent", "avatar": "generic", "nature": "operational", "mode": "normal", "group": "operational", "deps": [], "icon": "🎙️", "asset": "meeting_monitor", "description": "Owns the reusable LIVE-MEETING / VOICE-STREAMING asset. Whenever a project needs to listen to a meeting or voice in real time, THIS agent provides the 🎙 listener beside the ▶ button in the chat and runs the shared asset: capture audio in serial chunks (mic / meeting audio), transcribe each chunk live, DETECT each chunk's language, and on Stop build a smart 13-section report in the meeting's majority language — exportable as Markdown or Word, in Arabic OR English. Uses the shared asset (dashboard/meeting_monitor.html + the /meeting/* endpoints); writes NO app code. Add this agent to ANY project that must stream/record voice and it brings this whole capability with it."},
}

# The single reusable ASSET this system owns for live voice/meeting streaming. An agent that carries
# asset == MEETING_ASSET (or whose role/name matches the signature below) exposes the 🎙 listener and
# uses dashboard/meeting_monitor.html + /meeting/* to capture → transcribe → report → export.
MEETING_ASSET = "meeting_monitor"
_MEETING_SIGNATURE = ("meeting", "voice stream", "voice-stream", "audio capture", "transcription",
                      "live meeting", "streaming")


def project_has_meeting_asset(pid: str) -> bool:
    """True if this project has an agent that owns/uses the live-meeting asset — so the app shows 🎙."""
    try:
        import agents_registry
        for a in agents_registry.list_agents(pid):
            if (a.get("asset") == MEETING_ASSET):
                return True
            blob = f"{a.get('name','')} {a.get('role','')} {a.get('description','')}".lower()
            if any(s in blob for s in _MEETING_SIGNATURE):
                return True
    except Exception:
        pass
    return False

# Friendly labels for connector dependencies (used in readiness warnings).
DEP_LABELS = {"azure": "Azure", "klaviyo": "Klaviyo", "veeqo": "Veeqo", "easypost": "EasyPost",
              "analytics": "Analytics (e.g. GA)", "helpdesk": "Helpdesk", "crm": "CRM"}

# Where saved platform credentials live (default keys), and the order an agent reads integration config.
CRED_PATH = "workspace/shared/oth/.cred"
ENV_SOURCES = "(1) the ENV/keys block in your mandate/brief, (2) the shared pool, (3) the project `.env`, (4) " + CRED_PATH


def resources_block(name: str) -> str:
    """The per-agent 'Allowed Resources & Dependencies' section. Every agent reviews this BEFORE it starts:
    what it HAS (permissions, tools, where its creds/env are), what it must CONFIRM (default-vs-provided key
    for operators), and what to ASK the CTO for if-and-only-if it is genuinely missing. The golden rule is
    REASON-BEFORE-ASK: never ask for anything already listed here or already present in the brief/shared
    pool/.env/.cred. This is what stops both the '5-minutes-to-find-a-key' waste and the silent
    missing-permission failures."""
    cat = {**ALL_MEMBERS, **OPERATIONAL_MEMBERS}.get(name) or {}
    nature = cat.get("nature", "technical")
    deps = cat.get("deps") or []
    plat = ", ".join(DEP_LABELS.get(d, d) for d in deps) if deps else ""
    head = ("=== ALLOWED RESOURCES & DEPENDENCIES (read FIRST; REASON before you ask — never ask for "
            "anything already here or already in the brief/shared pool) ===\n")
    n = name.lower()

    if n in ("fullstack", "mobile"):
        return head + (
            "• PERMISSIONS: full read/write + shell. You CREATE and EDIT files (Write/Edit/Bash) inside the "
            "project folder you are given. If a Write/Edit actually fails, say so explicitly — do NOT silently "
            "narrate instead of building.\n"
            f"• INTEGRATION KEYS / ENV: credentials come from the ENVIRONMENT, not from other agents. Read them, "
            f"in this order, from: {ENV_SOURCES}. Do NOT ask an operator (Fulfillment/Email/…) for the app's key "
            "— the app uses the env key provided for it. START by reading the env/config; do NOT begin by testing "
            "a key unless the task requires it.\n"
            "• ASK-IF-MISSING: only if a key/var the task needs is in NONE of those sources, ask the CTO ONCE for "
            "that specific item, then continue. If read/write is genuinely unavailable, state exactly that.\n")
    if n == "devops":
        return head + (
            f"• ACCESS: deploy/cloud access. Reach the VM over SSH as user `mostafa` (password in {CRED_PATH}); the "
            "`az` control plane runs on the Mac, NOT on the VM. Tools: rsync, ssh, docker, nginx, systemctl, CI/CD.\n"
            "• FIREWALL / PORTS (CONFIRMED RULES — obey exactly, do NOT widen): SSH port 22 must stay open to "
            "EXACTLY ONE IP — your current public IP — and no other; never open 22 to 0.0.0.0/0. Ports 80 and 443 "
            "(the reverse proxy) are already configured and serve traffic — do NOT change, close, or reorder their "
            "rules. When you touch UFW/NSG, ADD only the single-IP rule for 22 if it's missing; leave 80/443 and "
            "every other rule untouched. If SSH/22 is blocked, re-pin 22 to your current IP, then RETRY the "
            "transport before aborting — do not give up on the first hiccup.\n"
            "• VERIFY EVERY COMMAND (do NOT assume success): after EACH remote command, READ its real result — the "
            "exit code AND the output — and decide from that, not from the fact that it ran. A non-zero exit, a "
            "stderr error, or empty/unexpected output means it did NOT succeed; report the exact output and fix or "
            "retry. Never report a step done on an assumed/blind success.\n"
            "• FILE UPDATES MUST OVERWRITE AT CONTENT LEVEL (line-level), not just add missing files: sync with "
            "rsync `--checksum` so a changed file ALWAYS overwrites the VM copy by CONTENT (not mtime/size). After "
            "syncing, CONFIRM it actually updated: re-run rsync with `--checksum --dry-run --itemize-changes` and "
            "expect ZERO pending files (or `md5sum` the changed files on BOTH local and VM and confirm they match). "
            "If anything is still pending, the update did NOT take — investigate (permissions, wrong path, excluded "
            "by filter) and redo until the VM content matches local exactly.\n"
            "• NEEDS: a deploy TARGET (host + path) and the QA-approved build from Fullstack. If the target, "
            "credentials, or deploy URL is missing, ask the CTO ONCE.\n"
            "• BOUNDARY: you deploy/operate; you write NO application feature code. You run LAST, after QA passes.\n")
    if n == "qa":
        return head + (
            "• PERMISSIONS: READ-ONLY (Read/Glob/Grep + read-only Bash). You verify; you NEVER implement.\n"
            "• RESOURCES: the built code on disk + the acceptance criteria. FIRST run `ls -R` on the project folder "
            "to confirm the app actually EXISTS; if it is empty, reply FAIL (it was not built). Verify against real "
            "files/evidence and quick checks (lint/type/unit) — no full prod build, no long-lived server.\n"
            "• NEEDS: the thing under test must already exist. If it does not, report that, don't invent a pass.\n")
    if nature == "operational" and deps:
        return head + (
            f"• ROLE: NON-technical operator of {plat} via its API. You write NO app code and define no API "
            "contract (Fullstack owns integration code).\n"
            f"• DEFAULT KEY: you hold a DEFAULT {plat} API key saved in {CRED_PATH}. It is ALREADY AVAILABLE there "
            "— do NOT search the codebase for it; read it from that file when you need it.\n"
            "• KEY = USE WHAT THE CTO TOLD YOU; ASK ONLY IF IT WAS SILENT (smart reasoning, no loops):\n"
            f"   – If the CTO's mandate says 'use your default {plat} key' → read it from {CRED_PATH} and proceed. "
            "Do NOT ask.\n"
            "   – If the CTO's mandate gives you a specific key (a value, or a file PATH to read) → use THAT key "
            "and proceed. Do NOT ask. (This is the normal smart case: the CTO already passed the project key from "
            "the create-project env, so the answer is given before you'd ask.)\n"
            f"   – ONLY if the CTO's mandate is SILENT about the key do you ask the CTO ONCE: \"You didn't specify a "
            f"key — should I use my default {plat} key from {CRED_PATH}?\" Then proceed on the reply. Ask AT MOST "
            "ONCE; never loop and never ask when you were already told.\n"
            "• WHEN YOU WORK: your REAL work runs AFTER the app is deployed and running — the CTO hands you the "
            f"deployed link/endpoint; you confirm the key (above), connect to {plat}, retrieve the required data, "
            "and post it back into the app via its API; then it is verified. EARLY (pre-deploy) the ONLY thing you "
            "may provide is the key, and only if it isn't already saved.\n"
            "• ASK-IF-MISSING: if you have NO real key and none is provided, say you need it (ask the CTO ONCE). "
            "Never fabricate data.\n")
    if nature == "operational":
        return head + (
            "• ROLE: NON-technical. You produce your specialist artifact (docs/content/SEO recommendations); you "
            "write NO code and hold no API key.\n"
            "• NEEDS: the inputs named in your mandate. If an input is missing, ask the CTO ONCE; otherwise proceed.\n")
    # other technical specialists (Security, Data, Embedded, GameDev, XR, Designer)
    return head + (
        "• PERMISSIONS: read/write within your discipline (Write/Edit/Bash as needed).\n"
        f"• ENV/KEYS: if your task needs credentials, read them from {ENV_SOURCES}; ask the CTO ONCE only if a "
        "needed item is absent everywhere.\n"
        "• NEEDS: the upstream deliverables named in your mandate. Reason before asking; never ask for what you "
        "already have.\n")


def resources_hint(name: str) -> str:
    """One-line resource summary for the CTO planner, so it knows what each agent ALREADY has (and therefore
    must NOT re-request) when it gathers requirements and orders the pipeline."""
    cat = {**ALL_MEMBERS, **OPERATIONAL_MEMBERS}.get(name) or {}
    nature = cat.get("nature", "technical")
    deps = cat.get("deps") or []
    plat = ", ".join(DEP_LABELS.get(d, d) for d in deps) if deps else ""
    n = name.lower()
    if n in ("fullstack", "mobile"):
        return "has read/write; reads integration keys from the ENV/brief/pool/.env/.cred (NOT from operators)."
    if n == "devops":
        return f"has SSH-as-mostafa + az control plane + firewall/port-22 fallback; needs a deploy target."
    if n == "qa":
        return "read-only; verifies the built app on disk against acceptance criteria."
    if nature == "operational" and deps:
        return (f"operator of {plat}; has a DEFAULT key in {CRED_PATH}; uses the key YOU name in its mandate "
                "(default or a provided one) — tell it up front; works AFTER deploy.")
    if nature == "operational":
        return "non-technical; produces a specialist artifact; no keys."
    return "technical specialist; reads any creds from env; asks CTO only if missing."

# Canonical project TYPES — a category/recommendation shown at creation, grouped into TECH and
# OPERATIONAL, and used to group the dashboard. The type does NOT replace the brief.
PROJECT_TYPES = [
    # --- Tech ---
    {"key": "web",         "group": "tech", "label": "Web application",     "icon": "🌐", "suggests": ["Fullstack", "QA"]},
    {"key": "mobile",      "group": "tech", "label": "Mobile application",  "icon": "📱", "suggests": ["Mobile", "QA"]},
    {"key": "desktop",     "group": "tech", "label": "Desktop application", "icon": "🖥️", "suggests": ["Fullstack", "QA"]},
    {"key": "deployment",  "group": "tech", "label": "Deployment",          "icon": "🚀", "suggests": ["DevOps"]},
    {"key": "security",    "group": "tech", "label": "Security",            "icon": "🛡️", "suggests": ["Security", "DevOps"]},
    {"key": "scripting",   "group": "tech", "label": "Scripting / Automation", "icon": "🧩", "suggests": ["Fullstack"]},
    {"key": "integration", "group": "tech", "label": "Integration / API",   "icon": "🔌", "suggests": ["Fullstack"]},
    {"key": "embedded",    "group": "tech", "label": "Embedded / Firmware",  "icon": "🔧", "suggests": ["Embedded", "QA"]},
    {"key": "gaming",      "group": "tech", "label": "Game",                 "icon": "🎮", "suggests": ["GameDev", "QA"]},
    {"key": "xr",          "group": "tech", "label": "XR (AR / VR)",         "icon": "🕶️", "suggests": ["XR", "QA"]},
    {"key": "ai_ml",       "group": "tech", "label": "AI / ML",             "icon": "🧠", "suggests": ["Data", "Fullstack"]},
    {"key": "data",        "group": "tech", "label": "Data / Analytics",     "icon": "📊", "suggests": ["Data", "Fullstack"]},
    # --- Operational ---
    {"key": "marketing",   "group": "operational", "label": "Marketing",        "icon": "📈", "suggests": ["Marketing"]},
    {"key": "email",       "group": "operational", "label": "Email specialist", "icon": "✉️", "suggests": ["Email"]},
    {"key": "content",     "group": "operational", "label": "Content creator",  "icon": "✍️", "suggests": ["Content"]},
    {"key": "support",     "group": "operational", "label": "Customer support", "icon": "💬", "suggests": ["Support"]},
    {"key": "sales",       "group": "operational", "label": "Sales / Outreach", "icon": "🤝", "suggests": ["Sales"]},
    {"key": "social",      "group": "operational", "label": "Social media",     "icon": "📣", "suggests": ["Content", "Marketing"]},
    {"key": "fulfillment", "group": "operational", "label": "Fulfillment Provider", "icon": "📦", "suggests": ["Fulfillment"]},
]
_TYPE_KEYS = {t["key"] for t in PROJECT_TYPES}
_TYPE_GROUP = {t["key"]: t["group"] for t in PROJECT_TYPES}


def recommend_type(description: str) -> str:
    """Smart recommendation of a project type from the description (a suggestion, not a lock)."""
    d = " " + (description or "").lower() + " "
    def has(*ws): return any(w in d for w in ws)
    if has("fulfillment", "shipping", "shipment", "veeqo", "veqo", "order tracking", "courier"): return "fulfillment"
    if has("email blast", "newsletter", "lifecycle email", "klaviyo", "drip "): return "email"
    if has("market", "campaign", "growth", "seo ", "brand ", "ads "):          return "marketing"
    if has("content calendar", "blog post", "copywrit", "article"):            return "content"
    if has("customer support", "help desk", "helpdesk", "ticket"):             return "support"
    if has("social media", "instagram", "linkedin post", "tweet"):             return "social"
    if has("sales", "outreach", "lead ", "crm"):                               return "sales"
    if has("ar ", "vr ", "augmented reality", "virtual reality", "unity", "unreal"): return "xr"
    if has("game", "gameplay", "godot"):                                       return "gaming"
    if has("embedded", "firmware", "microcontroller", "arduino", "esp32", "rtos"): return "embedded"
    if has("machine learning", " ml ", " ai ", "model train", "llm", "neural"): return "ai_ml"
    if has("data pipeline", "analytics", "etl", "dashboard report", "warehouse"): return "data"
    if has("mobile", "ios", "android", "react native", "flutter", "swift", "kotlin"): return "mobile"
    if has("desktop app", "electron", "tauri", "wpf", ".net app"):             return "desktop"
    if has("deploy", "ship to", " vm", "nginx", "azure", "ci/cd", "hosting"):  return "deployment"
    if has("security", "audit", "harden", "penetration", "vulnerab", "cve"):   return "security"
    if has("integration", "integrate", "webhook", "api "):                     return "integration"
    if has("script", "automation", "cron", "scrape", "glue "):                 return "scripting"
    return "web"


def member_def(name: str) -> dict | None:
    """Look up a member's canonical definition in either the technical or operational registry."""
    return ALL_MEMBERS.get(name) or OPERATIONAL_MEMBERS.get(name)


def _dep_met(dep: str) -> bool:
    """Is a role's required connector available? (azure via capabilities; others via user connectors)."""
    dep = (dep or "").lower()
    try:
        import capabilities  # type: ignore
        if dep == "azure":
            return any("azure" in (h.get("name", "").lower()) for h in capabilities.snapshot().get("have", []))
        for c in capabilities.list_connectors():
            blob = (c.get("name", "") + " " + c.get("type", "")).lower()
            if dep in blob and c.get("status") == "connected":
                return True
    except Exception:
        return False
    return False


def role_catalog() -> list:
    """All known roles (technical + operational) with their dependencies — the dashboard roster."""
    return [dict(m) for m in list(ALL_MEMBERS.values()) + list(OPERATIONAL_MEMBERS.values())]


def known_role(name: str) -> bool:
    """TRUE if `name` is a real, catalogued agent role. Used to STOP the system from silently
    inventing an agent from a provider/word the owner typed (e.g. 'Vapi') — those must be confirmed."""
    if not name:
        return False
    if member_def(name):
        return True
    n = name.strip().lower()
    for m in role_catalog():
        if n == m["name"].lower() or n == m["role"].lower():
            return True
    return False


def classify_team(names: list) -> dict:
    """Split proposed member names into known (catalogued) vs unknown (need owner confirmation)."""
    known, unknown = [], []
    for n in (names or []):
        (known if known_role(n) else unknown).append(n)
    return {"known": known, "unknown": unknown, "catalog": [m["name"] for m in role_catalog()]}


def _suggest_rule(task: str) -> str:
    """A well-written default RULE for a new agent created to handle `task` — so it never starts
    rule-less (which causes hallucination). The owner can accept / edit / refuse it."""
    t = (task or "this task").strip().rstrip(".")
    return (f"Scope: handle \"{t}\" and closely related requests only. Use just the tools/data/"
            "connectors relevant to it; stay within the shared project context. Never touch production "
            "or run destructive/VM commands without explicit owner approval. Report only verified "
            "results (no guesses); if information is missing, ask in the shared pool rather than inventing.")


def capability_options(pid: str, task: str) -> dict:
    """For the CTO 'this agent's rules don't cover the request' dialog: a filtered, ranked list of
    EXISTING agents (project members first, then catalogue roles) most able to handle `task`, plus a
    smart SUGGESTION (name + role + rules) for creating a new custom agent. Excluded (owner-removed)
    agents are never offered."""
    import agents_registry
    t = (task or "").lower()
    words = {w for w in re.findall(r"[a-z]+", t) if len(w) > 3}
    excluded = {e.lower() for e in agents_registry.excluded_agents(pid)}

    def score(blob: str) -> int:
        b = (blob or "").lower()
        return sum(1 for w in words if w in b)

    cands, seen = [], set()
    for a in agents_registry.list_agents(pid):           # project members first
        if a["name"].lower() in excluded:
            continue
        seen.add(a["name"].lower())
        cands.append({"name": a["name"], "role": a.get("role", a["name"]),
                      "why": "already on this project",
                      "score": score(f"{a.get('name','')} {a.get('role','')} {a.get('description','')}") + 1})
    for m in role_catalog():                              # then catalogue roles
        if m["name"].lower() in seen or m["name"].lower() in excluded:
            continue
        cands.append({"name": m["name"], "role": m["role"], "why": m.get("description", ""),
                      "score": score(f"{m.get('name','')} {m.get('role','')} {m.get('description','')} {' '.join(m.get('deps',[]))}")})
    cands.sort(key=lambda c: -c["score"])
    # CHOICE 1 — embed an existing agent (project members + catalogue roles able to do this task)
    recommended = [{k: c[k] for k in ("name", "role", "why")} for c in cands[:6]]

    # CHOICE 2 — create a NEW role, with a suggested editable definition. NON-INTERSECTION GUARD: never
    # suggest a role that overlaps one we already have (e.g. a 'Node'/'Mailchimp' specialist when
    # Fullstack/Email already cover it) — collapse it into the existing role instead.
    sug = agents_registry.suggest_agent(task or "specialist")
    sug_role = sug.get("role", "Specialist")
    _overlap = None
    for m in (list(ALL_MEMBERS.values()) + list(OPERATIONAL_MEMBERS.values())):
        blob = f"{m['name']} {m['role']} {m.get('description','')}".lower()
        if score(blob) >= 2 or m["role"].lower() == sug_role.lower():
            _overlap = m
            break
    # the suggestion carries the AI-DRAFTED description + editable Resources & Dependencies section + env,
    # so the owner can ACCEPT or EDIT them before the agent is created.
    suggestion = {"name": sug.get("suggestedName") or "Specialist", "role": sug_role,
                  "nature": sug.get("nature", "technical"),
                  "description": sug.get("description", ""),
                  "resources": sug.get("resources", ""),
                  "env": sug.get("env", []),
                  "rules": _suggest_rule(task),
                  "overlaps": (None if not _overlap else
                               {"name": _overlap["name"], "role": _overlap["role"],
                                "note": f"This overlaps the existing {_overlap['name']} role — prefer expanding "
                                        f"{_overlap['name']} (Choice 3) instead of creating a duplicate."})}

    # CHOICE 3 — expand an EXISTING project member's role (shown with its current role + rules + the editable
    # Resources & Dependencies section + env, so the owner can edit any of them from the dialog/dashboard).
    editable = []
    for a in agents_registry.list_agents(pid):
        if a["name"].lower() in excluded:
            continue
        editable.append({"name": a["name"], "role": a.get("role", a["name"]),
                         "rules": a.get("rules") or a.get("description", ""),
                         "resources": a.get("resources") or resources_block(a["name"]),
                         "env": a.get("env", [])})

    return {"recommended": recommended, "suggestion": suggestion, "editable": editable}


def roles_readiness() -> list:
    """Role roster annotated with which dependencies are missing (warn-but-continue, never blocks)."""
    out = []
    for r in role_catalog():
        missing = [d for d in r.get("deps", []) if not _dep_met(d)]
        r["missing"] = [DEP_LABELS.get(m, m) for m in missing]
        r["ready"] = not missing
        out.append(r)
    return out


def infer_team(description: str) -> list:
    """Decide the RIGHT team from the description — and RESPECT NEGATION/INTENT, not just
    keywords. 'no backend' must NOT add Backend; 'deploy later' must NOT add DevOps; 'static'
    means Frontend-only. (In the real app, the conversational intake lets the engine decide the
    team; this is the smart default for the direct create path.)"""
    d = " " + (description or "").lower() + " "

    # Honor an explicit "only DevOps" restriction up front (deploy/sync runs the owner wants
    # handled by DevOps alone — no QA/FE/BE/etc.).
    if any(p in d for p in ("only devops", "devops only", "only the devops", "no other agent",
                            "no other agents", "agents other than devops")):
        return [ALL_MEMBERS["DevOps"]]
    no_qa = any(p in d for p in ("no qa", "without qa", "remove qa", "no quality", "do not involve",
                                 "don't involve"))

    def mentioned(words, negators=("no ", "without ", "not ", "don't ", "dont ", "skip ")):
        for w in words:
            i = d.find(w)
            while i != -1:
                pre = d[max(0, i - 14):i]
                if not any(neg in pre for neg in negators):
                    return True
                i = d.find(w, i + 1)
        return False

    static_only = mentioned(("static", "frontend only", "frontend-only", "just a landing", "simple landing")) \
        or ("landing" in d and ("no backend" in d or "without backend" in d))

    # OPERATIONAL-ONLY projects (content / research / monitoring / reporting / marketing — NO code to
    # build) must NOT be force-staffed with Fullstack/QA/DevOps. Detect a real BUILD intent first; if
    # there is none, staff only the relevant OPERATORS derived from the brief.
    build_intent = mentioned((
        "build", "develop", "app", "application", "website", "web app", "webapp", "web site", "api",
        "backend", "front end", "frontend", "dashboard", "portal", "platform", "software", "system",
        "web page", "landing", "mobile app", "integrate", "codebase", "microservice", "database", "deploy"))
    if not build_intent:
        ops = []
        if mentioned(("content", "post", "posts", "instagram", "facebook", "tiktok", "social", "blog",
                      "copywrit", "caption", "reel", "article", "video script")):
            ops.append("Content")
        if mentioned(("marketing", "campaign", "growth", "brand", "positioning")):
            ops.append("Marketing")
        if mentioned(("seo", "keyword", "search ranking", "on-page", "backlink")):
            ops.append("SEO")
        if mentioned(("email campaign", "klaviyo", "mailchimp", "newsletter", "lifecycle email")):
            ops.append("Email")
        if mentioned(("google analytics", "ga4", "analytics report", "traffic report", "conversion report")):
            ops.append("Analytics")
        # real shipping OPERATIONS only — never merely researching a marketplace (e.g. Amazon) for content
        if mentioned(("manage orders", "manage shipments", "fulfilment operation", "fulfillment operation",
                      "3pl", "shipping operation", "dispatch order")):
            ops.append("Fulfillment")
        if not ops:
            ops = ["Content"]   # sensible operational default — never Fullstack/QA for a no-code project
        _CAT0 = {**ALL_MEMBERS, **OPERATIONAL_MEMBERS}
        seen0, out0 = set(), []
        for n in ops:
            if n not in seen0 and n in _CAT0:
                seen0.add(n); out0.append(_CAT0[n])
        return out0

    # ONE owner of the whole web app (UI + API + database) — no frontend/backend/database split, so no
    # hand-off and no two members in the same folders.
    team = ["Fullstack"]
    # deploy ONLY if wanted in THIS phase (not "later"/negated)
    deploy = mentioned(("deploy", "vm", "azure", "cloud", "ci/cd", "ci cd", "docker", "kubernetes",
                        "nginx", "production", "hosting", "release"))
    if deploy and any(p in d for p in ("later", "next phase", "phase 2", "future", "for now no",
                                       "not now", "not yet")):
        deploy = False
    if deploy:
        team.append("DevOps")
    if mentioned(("auth", "login", "payment", "card", "secure", "compliance", "pii", "phi")):
        team.append("Security")
    # mobile is its OWN platform (never folded into Fullstack)
    if mentioned(("mobile app", "ios app", "android app", "flutter app", "play store", "app store", "native app")):
        team.append("Mobile")
    # OPERATIONAL members are DERIVED FROM THE BRIEF when it references their business domain/connector —
    # the team comes from the NEEDS, it is not hard-coded. The CTO then assigns each its operational part
    # (supply key + read contract + monitor), never code.
    if mentioned(("veeqo", "shipping", "fulfillment", "tracking number", "order status", "shipment", "3pl", "courier")):
        team.append("Fulfillment")
    if mentioned(("klaviyo", "mailchimp", "email metric", "lifecycle email", "newsletter", "email campaign")):
        team.append("Email")
    if mentioned(("google analytics", "ga4", "gtag", "analytics tag", "conversion tracking")):
        team.append("Analytics")
    # QA verifies the build for ANY buildable project — UNLESS the owner explicitly said no QA.
    if not no_qa:
        team.append("QA")

    _CAT = {**ALL_MEMBERS, **OPERATIONAL_MEMBERS}   # operational roles live in a separate dict
    seen, out = set(), []
    for n in team:
        if n not in seen and n in _CAT:
            seen.add(n); out.append(_CAT[n])
    return out


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or uuid.uuid4().hex[:6]


def _id_taken(pid: str, parent: str = "") -> bool:
    if any(p["id"] == pid for p in list_projects()):
        return True
    try:
        if (store.WS / "projects" / pid).is_dir():
            return True
    except Exception:
        pass
    try:
        if parent:
            import os
            lp = os.path.expanduser(parent)
            tgt = lp if os.path.basename(os.path.normpath(lp)).lower() == pid else os.path.join(lp, pid)
            if os.path.isdir(tgt) and os.listdir(tgt):
                return True
    except Exception:
        pass
    return False


def unique_identifier(base: str, parent: str = "") -> str:
    """A unique, slugified identifier; appends a short suffix on any clash (active project, leftover
    record dir, or an existing non-empty target folder) — so a re-used prompt never reuses an old folder."""
    pid = _slug(base or "project")
    if not _id_taken(pid, parent):
        return pid
    for _ in range(50):
        cand = f"{pid}-{uuid.uuid4().hex[:4]}"
        if not _id_taken(cand, parent):
            return cand
    return f"{pid}-{uuid.uuid4().hex[:8]}"


def suggest_identifier(name: str, local_path: str = "") -> str:
    """The recommended (editable) identifier shown in the create dialog — unique by construction."""
    return unique_identifier(name or "project", local_path)


def _db_project_ids():
    """The DATABASE (odin_core) is the single source of truth for WHICH projects exist. Returns the id
    list, or None if the DB is unreachable (callers then degrade to on-disk project folders — never to a
    global JSON registry, which no longer exists)."""
    try:
        import psycopg2  # type: ignore
        c = psycopg2.connect(dbname="odin_core"); cu = c.cursor()
        cu.execute("SELECT id FROM projects"); ids = [r[0] for r in cu.fetchall()]; c.close()
        return ids
    except Exception:
        return None


def _proj_reg_path(pid: str) -> str:
    """A project's config lives in its OWN canonical manifest (index.json) — the file the database points
    to for this project. Never a global registry file."""
    return f"projects/{pid}/index.json"


def _persist_one(proj: dict) -> None:
    """MERGE the project config into its canonical index.json (preserving canonical keys the middleware
    stamps), then let store.write_json re-index it in odin_core. Per-project, single door, no global file."""
    pid = proj.get("id")
    if not pid:
        return
    cur = store.read_json(_proj_reg_path(pid), {}) or {}
    cur.update(proj)
    store.write_json(_proj_reg_path(pid), cur)


def _synth_project(pid: str) -> dict:
    """Fallback config from the project's on-disk index.json when no registry file exists yet, so a
    project the DB knows about is never missing from the list."""
    ix = store.read_json(f"projects/{pid}/index.json", {}) or {}
    ix.setdefault("id", pid); ix.setdefault("status", "active"); ix.setdefault("members", [])
    return ix


def list_projects() -> list:
    """Single source of truth = odin_core. We list EXACTLY the projects the database has, loading each
    one's config from its own on-disk file (the DB points to the files). There is no global projects.json
    registry anymore, so a stale/ghost entry can never appear — if the DB doesn't have it, it doesn't exist."""
    ids = _db_project_ids()
    if ids is None:
        base = store._p("projects")
        try:
            ids = [d.name for d in base.iterdir() if d.is_dir() and d.name != "_shared"]
        except Exception:
            ids = []
    out = []
    for pid in ids:
        p = store.read_json(_proj_reg_path(pid), None) or _synth_project(pid)
        if p:
            p.setdefault("id", pid)
            out.append(p)
    return out


def agent_workdir(pid: str) -> str:
    """P2 — where a project's agents START: the project's own working folder (localPath) if it has one,
    otherwise its own canonical code slot workspace/projects/<pid>/code (created if missing). Agents never
    start at the Odin repo root, so relative writes land inside their own project."""
    p = get_project(pid) or {}
    lp = (p.get("localPath") or "").strip()
    if lp:
        return lp
    d = store.WS / "projects" / pid / "code"
    try:
        d.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return str(d)


def get_project(pid: str):
    for p in list_projects():
        if p["id"] == pid:
            return p
    return None


def _save_all(projects: list) -> None:
    """Persist each project's config to its OWN canonical index.json (per-project, middleware-indexed). No
    global registry file is ever written — the database owns 'what exists'."""
    for p in projects:
        _persist_one(p)


def set_flags(pid: str, **flags) -> dict | None:
    """Persist small per-project flags (e.g. qa_asked, qa_declined)."""
    projs = list_projects()
    for p in projs:
        if p["id"] == pid:
            p.update(flags)
            _save_all(projs)
            return p
    return None


def create_project(name: str, description: str = "", local_path: str = "",
                   members: list | None = None, ptype: str = "", stack: str = "", url: str = "",
                   mode: str = "build", sources: list | None = None, auto_approve: bool = False,
                   periodic: dict | None = None, cadence: str = "", identifier: str = "",
                   readiness: list | None = None) -> dict:
    import os
    projects = list_projects()
    # identifier: owner-chosen in the create dialog (recommended value suggested from the name),
    # slugified + made unique so a re-used prompt never lands on an old project's folder/records.
    pid = unique_identifier(identifier or name, local_path)
    # normalize the project type: keep a known key; allow a CUSTOM type (any non-empty slug); else
    # recommend one from the description. (Custom types are supported — the picker is extensible.)
    ptype = (ptype or "").strip().lower()
    if not ptype:
        ptype = recommend_type(description)
    elif ptype not in _TYPE_KEYS:
        ptype = re.sub(r"[^a-z0-9_]+", "_", ptype).strip("_") or recommend_type(description)
    # cadence: how often the project runs — once | recurring (on-demand, many times) | periodical
    cadence = (cadence or "").strip().lower()
    if cadence not in ("once", "recurring", "periodical"):
        cadence = "periodical" if (isinstance(periodic, dict) and periodic.get("enabled")) else "once"
    # periodic = {"enabled":bool,"schedule":{kind,...},"requireApproval":bool} — the project re-runs
    # its brief on a cadence, gated by owner approval when due (see scheduler).
    periodic = periodic if isinstance(periodic, dict) else {}
    if cadence == "periodical":
        periodic["enabled"] = True
    elif cadence != "periodical":
        periodic["enabled"] = bool(periodic.get("enabled")) and cadence == "periodical"
    # (pid is already unique via unique_identifier above)
    # Actually create the project folder on disk at the chosen location (anywhere the user picked).
    # If they gave a parent folder, create <parent>/<slug>; if it already points at a folder, use it.
    created_path = ""
    if local_path:
        lp = os.path.expanduser(local_path)
        try:
            if os.path.isdir(lp) and os.path.basename(os.path.normpath(lp)).lower() != pid:
                lp = os.path.join(lp, pid)   # treat given path as the PARENT; make a project subfolder
            os.makedirs(lp, exist_ok=True)
            created_path = lp
        except Exception:
            created_path = local_path
    if not (created_path or local_path):
        # F-38: no declared folder → the standard one, workspace/projects/<id>/code (never left empty)
        _std = store.WS / "projects" / pid / "code"
        try:
            _std.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
        created_path = str(_std)
    proj = {
        "id": pid,
        "name": name,
        "type": ptype,
        "stack": stack,
        "url": url,
        "mode": mode,
        "sources": sources or [],
        "auto_approve": bool(auto_approve),
        "cadence": cadence,
        "periodic": {"enabled": bool(periodic.get("enabled")),
                     "schedule": periodic.get("schedule") or {},
                     "requireApproval": bool(periodic.get("requireApproval", True))},
        "rules": [],
        "description": description,
        "localPath": created_path or local_path,
        "created": store.now(),
        "mappings": [],            # [{local, cloud, role}]
        "members": [],             # filled below via agents_registry
        "scope": f"project:{pid}",
        "status": "active",
    }
    projects.append(proj)
    _save_all(projects)

    # SINGLE DOOR (Phase-3/7): stamp the canonical workspace skeleton + seed odin_core for the new project
    # so it exists in the DB / directions / UI immediately — not only in the app's projects.json registry.
    try:
        import workspace_mw
        workspace_mw.create_owner("project", pid, {
            "id": pid, "name": name, "type": ptype, "category": stack or "",
            "description": description, "cadence": cadence,
            "config": {"cadence": cadence, "schedule": (periodic.get("schedule") or {})},
        })
    except Exception:
        pass

    # seed the RIGHT team for this project (inferred from the description) — not every role.
    import agents_registry  # type: ignore
    seed = members if members is not None else infer_team(description)
    for m in seed:
        canon = member_def(m["name"]) or {}
        nature = m.get("nature") or canon.get("nature", "technical")
        mmode = m.get("mode") or canon.get("mode", "")
        desc = m.get("description") or canon.get("description") or f"{m.get('role','')} specialist for {name}"
        agents_registry.register_agent(pid, m["name"], role=m.get("role", m["name"]),
                                       avatar=m.get("avatar", canon.get("avatar", "generic")),
                                       description=desc, nature=nature, mode=mmode,
                                       asset=m.get("asset") or canon.get("asset", ""))
        # a CONFIRMED custom agent comes with the owner's rules — save them so it has clear guidance
        # (an agent created without rules is what caused hallucination). Rules may be a list or string.
        for _rl in (m.get("rules") or []) if isinstance(m.get("rules"), list) else ([m["rules"]] if m.get("rules") else []):
            try:
                agents_registry.save_rule(pid, m["name"], _rl if isinstance(_rl, str) else _rl.get("rule", ""))
            except Exception:
                pass
    # company-level agents are "native" to every project — auto-add them too.
    # G12 (owner decision): an agent that is also a catalogue ROLE (e.g. EasyPost) is NOT native — it is
    # recommended per project like any role and added only when the owner approves it (it is in `members`).
    _chosen = {str(m.get("name", "") if isinstance(m, dict) else m).lower() for m in (members or [])}
    for ca in agents_registry.list_company_agents():
        if member_def(ca["name"]) and ca["name"].lower() not in _chosen:
            continue
        agents_registry.register_agent(pid, ca["name"], role=ca.get("role", ca["name"]),
                                       avatar=ca.get("avatar", "generic"),
                                       description=ca.get("description", ""),
                                       restrictions=None)
        for rl in ca.get("rules", []):
            agents_registry.save_rule(pid, ca["name"], rl if isinstance(rl, str) else rl.get("rule", ""))
    proj["members"] = [a["name"] for a in agents_registry.list_agents(pid)]
    _update(proj)
    # G9: a different credential named in the owner's brief is RECORDED (agent_scope + connectors/ reference)
    try:
        import workspace_mw as _mw_g9
        for _svc, _ref in _mw_g9.credential_choice_from_text(f"{name}. {description}"):
            _mw_g9.record_credential_choice(pid, _svc, _ref, source="intake")
    except Exception:
        pass

    # ── SOC BLUEPRINT AUTO-PROVISION ──────────────────────────────────────────────────────────────────
    # If the request describes a SECURITY COMPANY / SOC / security-monitoring, provision the ENTIRE advanced
    # SOC from the reusable capability: the 8 non-overlapping agents (from the core catalog), a seeded
    # knowledge base, and the recurring monitor-and-report schedule. This is what guarantees that deleting
    # this project and simply asking the app to "create a very advanced security company" rebuilds everything
    # we have now — nothing lives only in a one-off manual step.
    try:
        import soc_blueprint  # type: ignore
        if soc_blueprint.is_security_intent(f"{name} {description}") or ptype == "security":
            prov = soc_blueprint.provision(pid, name=name)
            proj["soc_provisioned"] = True
            proj["members"] = [a["name"] for a in agents_registry.list_agents(pid)]
            _update(proj)
            try:
                import scopes as _sc  # type: ignore
                _sc.sync_up(f"project:{pid}", "🛡️ Advanced SOC provisioned: 8-agent security team + knowledge "
                            "base + monitor-and-report schedule (reusable capability).")
            except Exception:
                pass
    except Exception:
        pass

    # if this is a PERIODICAL project, register its recurring run (approval-gated when due)
    if proj["periodic"]["enabled"] and proj["periodic"]["schedule"]:
        try:
            import scheduler  # type: ignore
            scheduler.create_task(
                pid, prompt=(description or name),
                schedule=proj["periodic"]["schedule"],
                title=f"⏰ {name} (periodic)",
                require_approval=proj["periodic"]["requireApproval"],
                kind_tag="project-periodic")
        except Exception:
            pass
    # G13: a platform the intake marked as NEEDED -> propose (never apply) strengthening the builder agent
    if readiness:
        try:
            import strengthen
            strengthen.propose_from_readiness(pid, readiness)
        except Exception:
            pass
    # company-level feed entry
    import scopes  # type: ignore
    scopes.sync_up(f"project:{pid}", f"Project created: {name}")
    return proj


def project_types() -> list:
    """The catalog the creation UI shows (types + the operational agents they can use)."""
    return PROJECT_TYPES


def operational_members() -> list:
    return list(OPERATIONAL_MEMBERS.values())


def _update(proj: dict) -> dict:
    """Persist ONE project's config to its canonical index.json (middleware-indexed). No global registry."""
    _persist_one(proj)
    return proj


def update_project(pid: str, **fields) -> dict | None:
    p = get_project(pid)
    if not p:
        return None
    p.update({k: v for k, v in fields.items() if v is not None})
    return _update(p)


def add_sources(pid: str, paths: list) -> dict | None:
    """Add local folder(s) the owner supplied (e.g. answering a deploy block) to the project's
    selected sources, so the deploy resolver finds them on resume."""
    p = get_project(pid)
    if not p:
        return None
    srcs = list(p.get("sources") or [])
    for path in (paths or []):
        path = (path or "").strip()
        if path and path not in srcs:
            srcs.append(path)
    p["sources"] = srcs
    return _update(p)


def add_mapping(pid: str, local: str, cloud: str, role: str = "") -> dict | None:
    p = get_project(pid)
    if not p:
        return None
    p.setdefault("mappings", []).append({"local": local, "cloud": cloud, "role": role})
    return _update(p)


def _write_project_rules(pid: str, rules: list) -> None:
    """Write the project's custom rules into its skills folder so the engine/agents respect them."""
    import store as _s
    d = _s.ensure_dir("projects", pid, "plan")
    lines = [f"# Project {pid} — custom rules (owner-edited)", ""]
    lines += [f"- {r['rule']}" for r in rules] or ["- (none)"]
    (d / "_custom-rules.md").write_text("\n".join(lines), encoding="utf-8")


def list_rules(pid: str) -> list:
    p = get_project(pid)
    return (p or {}).get("rules", [])


def add_rule(pid: str, rule: str) -> dict | None:
    import uuid as _u
    p = get_project(pid)
    if not p:
        return None
    p.setdefault("rules", []).append({"id": _u.uuid4().hex[:8], "rule": rule.strip()})
    _update(p)
    _write_project_rules(pid, p["rules"])
    return p


def update_rule(pid: str, rid: str, rule: str) -> dict | None:
    p = get_project(pid)
    if not p:
        return None
    for r in p.get("rules", []):
        if r["id"] == rid:
            r["rule"] = rule.strip()
    _update(p)
    _write_project_rules(pid, p.get("rules", []))
    return p


def remove_rule(pid: str, rid: str) -> dict | None:
    p = get_project(pid)
    if not p:
        return None
    p["rules"] = [r for r in p.get("rules", []) if r["id"] != rid]
    _update(p)
    _write_project_rules(pid, p["rules"])
    return p


def archive_project(pid: str):
    return update_project(pid, status="archived")


def unarchive_project(pid: str):
    return update_project(pid, status="active")


def delete_project(pid: str) -> bool:
    import shutil, glob
    _prot = get_project(pid)
    if _prot and (_prot.get("protected") or _prot.get("type") == "arm"):
        return False   # PROTECTED arm (anchor/backend/desktop/mobile) — a company arm, never deletable
    _save_all([p for p in list_projects() if p["id"] != pid])
    # SINGLE DOOR (Phase-3/7): clean the odin_core rows (files/folders/deps/links + the project row) so a
    # deletion never leaves orphan DB rows. delete_owner also removes the canonical folder (idempotent).
    try:
        import workspace_mw
        workspace_mw.delete_owner("project", pid)
    except Exception:
        pass
    # remove the project's data + ALL its scope chats (project + every member) — now under workspace/
    for d in [store._p("projects", pid), store._p("scopes", f"project__{pid}")]:
        shutil.rmtree(d, ignore_errors=True)
    for d in glob.glob(str(store._p("scopes")) + f"/member__{pid}__*"):
        shutil.rmtree(d, ignore_errors=True)
    # PURGE every per-project store so a re-created project with the SAME id starts truly FRESH —
    # no carried-over status. (This was the bug: only the folder/chats were removed before.)
    try:                                   # shared-context pool (Main Task)
        mt = store.read_json("main_tasks.json", {})
        if pid in mt:
            mt.pop(pid, None); store.write_json("main_tasks.json", mt)
    except Exception:
        pass
    try:                                   # operations (deploy/sync status + logs) — memory + disk
        import operations
        operations.purge(pid)
    except Exception:
        pass
    try:                                   # scheduled / periodic tasks
        s = store.read_json("schedules.json", {"tasks": []})
        s["tasks"] = [t for t in s.get("tasks", []) if t.get("pid") != pid]
        store.write_json("schedules.json", s)
    except Exception:
        pass
    try:                                   # pending approvals
        a = store.read_json("approvals.json", {"items": []})
        a["items"] = [x for x in a.get("items", []) if x.get("pid") != pid]
        store.write_json("approvals.json", a)
    except Exception:
        pass
    try:                                   # deploy config
        (store.WS / "projects" / pid / "deploy-config.json").unlink()
    except Exception:
        pass
    try:                                   # live activity marker
        import activity
        activity.clear(pid)
    except Exception:
        pass
    return True


def _engine(prompt: str, model: str | None = None) -> str:
    try:
        import claude_cli  # type: ignore
        if claude_cli.available():
            return claude_cli.ClaudeCLIBrain().respond(prompt, lang="en", model=model)
    except Exception:
        pass
    try:
        import brain_handler  # type: ignore
        return brain_handler.OllamaBrain().respond(prompt, lang="en")
    except Exception:
        return "(engine offline — cannot compute right now.)"


def sync_proposal(pid: str) -> str:
    """SMART read-only pre-flight: the engine reads workspace/shared/infra/DEPLOY-PLAYBOOK.md, inspects the actual
    local vs VM folders, detects production, and returns its analysis + the CONTEXT-AWARE questions
    it needs answered — never executes anything."""
    p = get_project(pid)
    if not p:
        return "No such project."
    if not p.get("mappings"):
        return "No folder mappings yet. Add a mapping (local ↔ cloud) first."
    maps = "\n".join(f"- {m['local']}  →  {m['cloud']}  ({m.get('role','')})" for m in p["mappings"])
    return _engine(
        f"You are preparing a local→VM sync for project '{p['name']}'. Mappings:\n{maps}\n"
        "FIRST read workspace/shared/infra/DEPLOY-PLAYBOOK.md for the owner's rules. Then do a READ-ONLY pre-flight: "
        "compare local vs VM (diff -rq / rsync --dry-run), check sizes of public/upload/logs, "
        "package-lock diff, git status, and whether it's PRODUCTION (running systemd services). "
        "Report what you found, then ASK the context-aware questions (touch .env? DB reseed/migrate "
        "or leave data? include public/upload/logs? npm install? rebuild+report errors? restart "
        "service vs reboot?). Do NOT execute anything — this is the proposal the owner approves.")


def deploy_proposal(pid: str) -> str:
    """Gated deploy proposal: exact steps + impact + rollback, then STOP for approval."""
    p = get_project(pid)
    if not p:
        return "No such project."
    return _engine(
        f"For project '{p['name']}', draft a deployment PROPOSAL to its VM: the exact commands, the "
        "impact on the running site, and the rollback. Treat the site as PRODUCTION. End by asking "
        "for approval. Do NOT execute anything.")


def plan_pipeline(pid: str, goal: str) -> list:
    """The Project CTO decides the ORDERED sequence of team members + each one's subtask to
    achieve `goal`. The CTO is RESOURCE-AWARE: it's told the connected resources (MCP/connectors)
    and the full team roster (each member + role), and it expresses DEPENDENCIES so the runner can
    wait for one part before starting a dependent one.
    Returns [{"member": name, "task": subtask, "depends_on": [member names]}, …].
    Uses the engine to plan; falls back to a sensible order if the model is unavailable."""
    p = get_project(pid)
    if not p:
        return []
    try:
        import agents_registry
        members = agents_registry.list_agents(pid)
    except Exception:
        members = []
    names = [m["name"] for m in members] or ["Fullstack", "DevOps"]
    # Tell the CTO each member's NATURE + what they actually do, so it never hands a coding job to a
    # non-technical operator (the Shipping/Email "integrate into the backend" hallucination).
    _CAT = {**ALL_MEMBERS, **OPERATIONAL_MEMBERS}

    def _meta(m):
        c = _CAT.get(m.get("name")) or {}
        return (c.get("nature") or m.get("nature") or "technical"), (c.get("description") or m.get("description") or "")

    _lines = []
    for m in (members or []):
        nat, desc = _meta(m)
        tag = "OPERATIONAL — NON-technical, does NOT write code" if nat == "operational" else "TECHNICAL — writes/edits code"
        _lines.append(f"- {m['name']} ({m.get('role','')}) — {tag}. {desc}\n"
                      f"    RESOURCES: {resources_hint(m['name'])}")
    roles = "\n".join(_lines) or "- Fullstack (TECHNICAL — owns the whole web app)\n- DevOps (TECHNICAL — deploy)"
    # what resources/connectors the CTO actually has to work with
    try:
        import capabilities
        caps = capabilities.summary_text()
    except Exception:
        caps = "Claude engine (Read/Glob/Grep/Bash + web)."
    prompt = (
        f"You are the Project CTO for '{p['name']}'. Goal: {goal}\n"
        f"YOUR TEAM (assign work ONLY to these existing members, by their specialty):\n{roles}\n"
        f"RESOURCES / CONNECTORS you can use: {caps}\n\n"
        "REQUIREMENTS FIRST — gather before you delegate:\n"
        "Before building the pipeline, REASON about everything the goal needs to actually run: env variables, "
        "API keys/credentials, a database URL, service configuration, third-party integrations, a deploy "
        "target. For EACH such input, decide where it comes from: it is either (a) ALREADY PROVIDED in the "
        "goal/brief or the shared pool (an ENV/keys block, a .env, or saved in " + CRED_PATH + "), or (b) "
        "MISSING. If anything required is MISSING, your FIRST step must be a single requirements step assigned "
        "to the OWNER (member 'Owner') that lists EXACTLY what you need (e.g. 'VEEQO_API_KEY for the app "
        "integration, the deploy host'). Do NOT ask operators for the application's key — the app uses the env "
        "key provided for it; you simply PASS the provided env/keys to Fullstack in its build mandate. If every "
        "input is already provided, do not add a requirements step.\n"
        "SMART KEY ASSIGNMENT — answer the key question BEFORE the agent has to ask (this is reasoning, be smart):\n"
        "Every agent already has a DEFAULT key in " + CRED_PATH + " and knows it (Fulfillment→Veeqo, Email→"
        "Klaviyo, DevOps→Azure/SSH). So whenever you assign a task that needs a credential, STATE THE KEY IN THAT "
        "STEP'S MANDATE so the agent never has to come back and ask: either 'use your default <provider> key' "
        "(when the brief/env did NOT give a project-specific one) OR 'use this project key: <value-or-path>' (when "
        "the create-project brief/env DID provide a different key for that service). Mine the brief/env to decide. "
        "Pass the actual key/value or its path in the mandate. Only if you genuinely forget will the agent ask once "
        "— but the smart, fast path is that you already told it, so it proceeds with no round-trip.\n"
        "NO NO-OP STEPS: never add busywork like 'establish/stand up the shared pool', 'set up coordination', "
        "or 'initialise the workspace' — the shared pool already exists and every step uses it automatically. "
        "Every step must be a REAL deliverable (build / deploy / fetch-and-post live data). Keep the pipeline "
        "as SHORT as the goal allows.\n"
        "QA IS AUTOMATIC: a QA review runs AUTOMATICALLY after every build step — do NOT add a separate "
        "standalone 'QA' step to the pipeline (it is redundant and doubles the time). Plan the build, the "
        "deploy, and the operators' live-data work; QA happens on its own between them.\n\n"
        "THINK FIRST — REASON, do not keyword-match:\n"
        "Before assigning anything, MINE the real meaning of each role's scope and each task. A role covers "
        "its whole DISCIPLINE, not a literal word: Fullstack builds web apps on ANY platform/stack (Node.js, "
        "Laravel/PHP, C#/.NET, Python/Django, Rails, …) and owns UI+API+DB together — so 'build the Node.js "
        "API' is Fullstack, not some 'Node' specialist. Match a task to a role by what the WORK actually is "
        "and what the role can truly do, never by surface keywords. If you are unsure what a role covers, "
        "reason it out from its description above.\n\n"
        "ROLE BOUNDARIES — obey strictly, do NOT cross them:\n"
        "• The whole WEB APP (UI + server/API + database + connector-calling code) is built by ONE "
        "technical owner: FULLSTACK. Do NOT split it across people and do NOT invent Frontend/Backend/"
        "Database — that role no longer exists. Mobile apps go to MOBILE. Any 'write/wire/integrate/build "
        "code' task goes to a TECHNICAL member (Fullstack for web, Mobile for apps).\n"
        "• OPERATIONAL members (Fulfillment, Email, Marketing, Support, Sales, Content, Analytics) are "
        "NON-technical operators — NEVER assign them to write/modify code and NEVER to define an API "
        "contract/protocol (Fullstack researches & builds those). Each HOLDS the power (via an API key) to "
        "operate ONE external platform. Early you may ask them ONLY for that API key (to save). Their REAL "
        "work — connect to the platform and feed/verify LIVE data — happens AFTER deploy (e.g. Fulfillment "
        "reports live order/shipping status via the fulfillment provider; Email runs/reports campaigns via "
        "Klaviyo/Mailchimp). The in-app code that calls those platforms is written by FULLSTACK.\n"
        "• Before EVER proposing a NEW role, CHECK whether an EXISTING member's FIELD already covers the "
        "task: Fullstack covers ALL web/server/database/integration code in any stack; Mobile ALL mobile; "
        "DevOps ALL cloud/CI-CD/deploy; Security ALL security; QA ALL testing; each operator its WHOLE "
        "platform domain. Only if NO existing field covers it may you name a new role — never create a "
        "duplicate of a field a current member already owns.\n"
        "ORDERING — the standard workflow; reason it out, an operational role acts on a RUNNING system. Graded:\n"
        "  0) (Only if inputs are missing) Owner requirements step — collect the missing env/keys/target.\n"
        "  1) FULLSTACK builds the whole app, including the code that calls the integrations. PASS the provided "
        "env/keys to Fullstack in its mandate (it reads them from env — it does NOT get them from operators). "
        "The keys are config for the app's own integration.\n"
        "  2) QA verifies the build AFTER it exists (confirms the app is real on disk, runs quick checks).\n"
        "  3) DEVOPS deploys to the target AFTER QA approves, and reports the DEPLOYED LINK/endpoint.\n"
        "  4) THEN each operational member does its REAL work, AFTER deploy: the CTO hands it the DEPLOYED LINK, "
        "it confirms which key to use (its default vs the app/env key), connects to its platform (Fulfillment→"
        "fulfillment provider for live order/shipping data; Email→Klaviyo/Mailchimp for campaign metrics), and "
        "posts that live data back into the app via its API. NEVER place this before the build or before deploy.\n"
        "  5) A FINAL verification step (QA or DevOps) confirms via a real API/cURL check that the deployed site "
        "actually reflects the fulfillment + email data.\n"
        "  (Before deploy, the ONLY early thing an operator may give is its API key, and only if it isn't already "
        "saved in " + CRED_PATH + " — usually it is, so you don't need the operator early at all.)\n\n"
        "Break the goal into an ORDERED pipeline. Each step = ONE member doing ONE concrete part. For "
        "EACH step give a real MANDATE, not a label: the member, a crisp OBJECTIVE (the one part they "
        "own), the DELIVERABLE they must produce, the ACCEPTANCE_CRITERIA (how we verify it's actually "
        "done), and depends_on (member names whose part must finish first, or []). Cover EVERY "
        "requirement in the goal — do not drop any. Respect the ROLE BOUNDARIES and ORDERING above.\n"
        "Reply with ONLY a JSON array, no prose:\n"
        '[{"member":"<name>","objective":"<one concrete part>","deliverable":"<what they produce>",'
        '"acceptance_criteria":"<how to verify done>","depends_on":["<name>", …]}]'
    )
    raw = _engine(prompt)
    steps = _extract_json_array(raw) or json_retry(raw, "array", '[{"member","objective","deliverable","acceptance_criteria","depends_on"}]')   # PC-2
    clean = []
    for s in steps:
        if not isinstance(s, dict):
            continue
        m = s.get("member")
        t = s.get("objective") or s.get("task")   # objective is the mandate's core; keep `task` alias
        if not (m and t):
            continue
        # snap to a real member name (fuzzy)
        match = next((n for n in names if n.lower() == str(m).lower()), None) \
            or next((n for n in names if n.lower() in str(m).lower() or str(m).lower() in n.lower()), None)
        # normalise depends_on to real member names
        deps_raw = s.get("depends_on") or s.get("dependsOn") or []
        if isinstance(deps_raw, str):
            deps_raw = [deps_raw]
        deps = []
        for d in deps_raw:
            dn = next((n for n in names if n.lower() == str(d).lower()), None) \
                or next((n for n in names if n.lower() in str(d).lower() or str(d).lower() in n.lower()), None)
            if dn:
                deps.append(dn)
        # keep a brand-NEW role the CTO proposes (it'll be hired on the fly) instead of forcing an existing one
        clean.append({"member": match or str(m), "task": str(t), "objective": str(t),
                      "deliverable": str(s.get("deliverable", "")),
                      "acceptance_criteria": str(s.get("acceptance_criteria", "")),
                      "depends_on": deps})
    if not clean:  # offline / unparseable -> heuristic chain over the real team
        order = [n for n in ["Fullstack", "Mobile", "Security", "QA", "DevOps"] if n in names] or names
        clean = [{"member": n, "task": f"Do your part for: {goal}", "objective": f"Do your part for: {goal}",
                  "deliverable": "your completed part", "acceptance_criteria": "it works and matches the brief",
                  "depends_on": ([order[i - 1]] if i else [])} for i, n in enumerate(order)]
    # DETERMINISTIC: drop a REDUNDANT pre-deploy QA step. QA runs AUTOMATICALLY after every build step
    # (the qa_gate), so a standalone QA step placed BEFORE the deploy just duplicates that gate and — worse —
    # itself goes through the gate (QA-ing QA), which looped 3× and blew the time budget. We KEEP a QA step
    # that comes AFTER the deploy (the real post-deploy cURL/data verification), and never drop the last step.
    _dep_i = next((i for i, s in enumerate(clean) if str(s.get("member", "")).strip().lower() == "devops"), None)
    if _dep_i is not None and len(clean) > 1:
        _kept = []
        for i, s in enumerate(clean):
            _is_qa = str(s.get("member", "")).strip().lower() == "qa"
            if _is_qa and i < _dep_i and i != len(clean) - 1:
                continue   # redundant pre-deploy QA gate → drop (the automatic gate already covers it)
            _kept.append(s)
        clean = _kept
    return clean


def check_plan_coverage(goal: str, steps: list) -> list:
    """The CTO QAs its OWN plan: does it cover EVERY requirement in the goal? Returns the list of
    requirements that NO step covers (omissions) — empty list = full coverage."""
    if not steps:
        return []
    plan_txt = "\n".join(
        f"- {s.get('member')}: {s.get('objective', s.get('task', ''))} → deliverable: {s.get('deliverable', '')}"
        for s in steps)
    prompt = ("You are the Project CTO reviewing your OWN plan for omissions. Below is the owner's "
              "goal/brief and the plan you produced. List ONLY the concrete requirements in the goal "
              "that NO step covers (true omissions — be strict but do not invent). \n\n"
              f"GOAL/BRIEF:\n{(goal or '')[:2600]}\n\nPLAN:\n{plan_txt}\n\n"
              'Reply ONLY JSON: {"missing":["<requirement>", …]}  (empty list if fully covered).')
    _raw = _engine(prompt)
    d = _extract_json_object(_raw) or json_retry(_raw, "object", '{"missing":[...]}') or {}   # PC-2
    miss = d.get("missing")
    return [str(x) for x in miss] if isinstance(miss, list) else []


def _extract_json_array(text: str) -> list:
    import json as _json
    if not text:
        return []
    try:
        i, j = text.index("["), text.rindex("]")
        return _json.loads(text[i:j + 1])
    except Exception:
        return []


def json_retry(raw: str, kind: str = "object", shape: str = ""):
    """PC-2 (F-16) wrong-format handling: the reply was not valid JSON — ask the engine ONCE to turn its own
    reply into exactly the required JSON shape. Returns the parsed value or None/[] (callers keep their safe default)."""
    try:
        fixed = _engine("FORMAT CORRECTION. The reply below was supposed to be ONLY a JSON " + kind
                        + (f" of this shape: {shape}" if shape else "") + ". Rewrite it as ONLY that JSON, no prose, "
                        "keeping its decision exactly; if it contains no decision, reply with null.\n\nREPLY:\n" + (raw or "")[:3000])
    except Exception:
        return None if kind == "object" else []
    return _extract_json_object(fixed) if kind == "object" else _extract_json_array(fixed)


def _extract_json_object(text: str):
    import json as _json
    if not text:
        return None
    try:
        i = text.index("{"); depth = 0
        for j in range(i, len(text)):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    return _json.loads(text[i:j + 1])
    except Exception:
        return None
    return None


def intake_step(history: list) -> dict:
    """ADAPTIVE project-intake interview, driven by the engine (the CTO). Given the conversation
    so far, returns the NEXT best question (branching on prior answers) OR a final proposal.
    The number/direction of questions depends on the answers — static site = few; full app +
    deploy = many (stack, data, auth, integrations, domain, TLS, auto-start, host, build)."""
    convo = "\n".join(f"{h.get('role', 'user')}: {h.get('content', '')}" for h in (history or []))
    try:
        import capabilities
        caps = capabilities.summary_text()
    except Exception:
        caps = "Already connected: Claude engine. (capabilities unavailable)"
    prompt = (
        "You are a SENIOR engineer/architect and the CTO. The owner will PASTE a full description of "
        "what they want (often a long copy-pasted prompt). Your job is NOT to run a long interview — "
        "it is to UNDERSTAND that description, analyze it like a domain expert, and get to a project "
        "as fast as is responsible.\n"
        "- READ everything the owner gave you, INCLUDING any attached files/docs. When the "
        "conversation lists 'ATTACHED FILES' with paths, OPEN them with the Read tool and use their "
        "contents as part of the description.\n"
        "- RESEARCH quietly only if you must: if a key tool/stack choice is genuinely unclear for "
        "this domain, you may web-search, but do NOT stall.\n"
        "- ASK A CLARIFYING QUESTION **ONLY IF** something CRITICAL is truly unclear or missing and "
        "you cannot reasonably decide it yourself. You may ask several times (one at a time) until "
        "the picture is complete — but never ask about things the owner already stated, and never ask "
        "filler questions. If the description is already clear enough, DO NOT ask anything — propose.\n"
        "- If it's an EXISTING project, you will READ/work on the selected folders and must NOT plan "
        "to rewrite them — only modify what the owner explicitly asks.\n"
        "- Before you propose, you MUST decide and CONFIRM these explicitly. If the owner did not "
        "specify them, DERIVE them from your analysis and include them so the owner can confirm:\n"
        "    1) PLATFORM  — the stack / target (e.g. Next.js + NestJS on an Azure VM, native iOS, …). "
        "For a purely operational/content project with no software to build, PLATFORM is 'operational — no build'.\n"
        "    2) TEAM — staff ONLY the members this project ACTUALLY needs, chosen from the REAL roles below. "
        "FIRST decide the project's NATURE: does it require building or changing CODE (an app, website, API, "
        "dashboard, mobile app), or is it OPERATIONAL (content, research, monitoring, reporting, marketing, a "
        "notification/agent pipeline) with NO code to build?\n"
        "         • Technical roles — ONLY if real code must be written/deployed: Fullstack (owns the WHOLE web "
        "app; there is NO separate 'Frontend'/'Backend'/'Database' member — that IS Fullstack), Mobile, DevOps "
        "(only if it must deploy), QA (only if there is a build to verify), Security, Designer, Data, Embedded, "
        "GameDev, XR.\n"
        "         • Operational roles — non-technical operators, pick by the brief's business domain: Content, "
        "Marketing, SEO, Email, Analytics, Sales, Support, Fulfillment, Finance, Writer.\n"
        "         Do NOT staff Fullstack/DevOps/QA on a purely operational/content/research/monitoring project. "
        "Do NOT invent roles outside these lists. Do NOT add Fulfillment/shipping just because a marketplace like "
        "Amazon is mentioned for research or content — add it ONLY when the project actually operates orders/"
        "shipments.\n"
        "    3) FEATURES  — the concrete feature list the project will deliver\n"
        "- ANTI-DEVIATION (critical): staff and propose ONLY what the brief needs. If the brief EXPLICITLY defines "
        "its OWN agents and rules and says to use only those and invent nothing, propose EXACTLY those agents "
        "verbatim (as the team) and add NOTHING else — no extra technical agents, no QA, no DevOps, no operators.\n"
        "- You MAY RECOMMEND new features or a new team member the owner didn't ask for — but you MUST "
        "say WHY for each (put them in 'recommendations'), and NEVER auto-staff them. The owner approves or drops them.\n"
        "- READINESS — map the work to OUR ACTUAL RESOURCES (Azure, the Claude engine, the connected "
        "services listed below, and the team). For each capability, say whether we can already do it "
        "with what we have, or whether it NEEDS something first — either a NEW TEAM MEMBER to create, "
        "or an API/service the owner must CONNECT — so it can be set up and tested BEFORE we generate "
        "the project. Put this in 'readiness'.\n\n"
        f"What we currently have / can connect:\n{caps}\n\n"
        f"Conversation so far:\n{convo or '(empty — the owner has not pasted a description yet)'}\n\n"
        "Reply with ONLY JSON, no prose. One of:\n"
        '{"action":"ask","question":"...","options":["..."]}   (use ONLY when something critical is unclear)\n'
        '{"action":"propose","spec":{"name":"...","type":"<kind of software>","stack":"<PLATFORM/tools>",'
        '"description":"<COMPLETE brief: objective + every decision + folders + platform + integrations + deploy>",'
        '"features":["<feature>", "..."],'
        '"team":["<ONLY the real roles this project needs — technical roles only if code is built; otherwise operational roles>"],'
        '"recommendations":{"features":[{"name":"...","why":"..."}],"members":[{"name":"...","why":"..."}]},'
        '"readiness":[{"item":"<capability>","status":"ready|needs","by":"azure|claude|connector|team",'
        '"need":"<new member to create OR API to connect, empty if ready>"}],'
        '"dependencies":[{"name":"...","status":"have|need","why":"..."}]}}\n'
        "The description must be COMPLETE enough that the project CTO could start without asking "
        "basics. Always populate features, team, stack (platform), and readiness from your analysis.\n"
        "FAITHFULNESS (critical): preserve the owner's requirements EXACTLY in the description — do NOT "
        "omit, summarize away, or invent anything. If the owner gave exact paths, commands, excludes or "
        "'this run / next run' rules, keep them VERBATIM. The description is the contract the whole team "
        "works from; a dropped or fabricated detail here corrupts every step downstream."
    )
    data = _extract_json_object(_engine_research(prompt))
    if data and data.get("action") in ("ask", "propose", "digest"):
        if data.get("action") == "propose" and isinstance(data.get("spec"), dict) and not data["spec"].get("identifier"):
            data["spec"]["identifier"] = suggest_identifier(data["spec"].get("name") or "project")
        return data
    return _intake_fallback(history or [])


def _engine_research(prompt: str) -> str:
    """Engine call for the intake that's ALLOWED to web-search before recommending."""
    import os as _os
    prev = _os.environ.get("ODIN_CLAUDE_TOOLS")
    _os.environ["ODIN_CLAUDE_TOOLS"] = "Read,Glob,Grep,Bash,WebSearch,WebFetch"
    try:
        return _engine(prompt)
    finally:
        if prev is None:
            _os.environ.pop("ODIN_CLAUDE_TOOLS", None)
        else:
            _os.environ["ODIN_CLAUDE_TOOLS"] = prev


def _intake_fallback(history: list) -> dict:
    """Deterministic fallback when the model is unavailable. Chat-only spirit: ask once for the
    full description, then derive platform/team/features from it and propose — no long interview."""
    # the owner's real input = everything they typed except the auto seed/context line
    users = [h["content"] for h in history
             if h.get("role") == "user" and not h.get("content", "").startswith("This is ")]
    desc = "\n\n".join(u.strip() for u in users if u.strip())
    if len(desc) < 12:
        return {"action": "ask",
                "question": "Paste a full description of what you want to build (and attach any files/docs). "
                            "I'll only ask again if something critical is unclear."}
    joined = desc.lower()
    # ONE web owner — Fullstack covers UI + API + database (no front/back/db split)
    team = ["Fullstack"]
    if any(k in joined for k in ("mobile", "ios", "android", "flutter app", "play store", "app store")):
        team.append("Mobile")
    deploy = any(k in joined for k in ("deploy", "vm", "azure", "host", "production", "server", "domain"))
    if deploy:
        team.append("DevOps")
    if any(k in joined for k in ("auth", "login", "payment", "secure", "security", "token")):
        team.append("Security")
    # naive feature extraction from lines/sentences so the confirm screen isn't empty
    feats = [s.strip(" .-•\t") for s in re.split(r"[\n.;]", desc) if 6 < len(s.strip()) < 120][:8]
    deploy_ready = any(k in joined for k in ("azure", "vm", "deploy"))
    readiness = [
        {"item": "App build & code generation", "status": "ready", "by": "claude", "need": ""},
        {"item": "Cloud deploy / hosting", "status": "ready" if deploy_ready else "needs",
         "by": "azure", "need": "" if deploy_ready else "confirm the Azure VM / hosting target"},
    ]
    _nm = " ".join(desc.split()[:4]) or "New project"
    return {"action": "propose", "spec": {
        "name": _nm,
        "identifier": suggest_identifier(_nm),
        "type": "Software", "stack": "",
        "description": desc,
        "features": feats,
        "team": team,
        "recommendations": {"features": [], "members": []},
        "readiness": readiness,
        "dependencies": [],
    }}


def _engine_cwd(prompt: str, cwd: str | None = None) -> str:
    """Run the engine (Claude) in a specific working directory (the project folder)."""
    try:
        import claude_cli
        if claude_cli.available():
            parts = []
            for ev in claude_cli.ClaudeCLIBrain().stream_session(prompt, "en", None, cwd=cwd):
                if ev.get("kind") == "text":
                    parts.append(ev["t"])
                elif ev.get("kind") == "final":
                    return ev.get("text") or "".join(parts)
            return "".join(parts) or "(no output)"
    except Exception as e:
        return f"(engine error: {e})"
    return _engine(prompt)


def auto_remediate(pid: str, finding: str) -> dict:
    """AUTO cross-agent chain: a checker found an issue → CTO hands the FIX to Frontend/Backend
    (in the project folder, non-production), then DevOps redeploy comes back as a GATED proposal
    (never auto-deploys to prod). Everything is written to the chats + rolled up."""
    import scopes, agents_registry
    p = get_project(pid)
    if not p:
        return {"ok": False}
    members = [a["name"] for a in agents_registry.list_agents(pid)]
    folder = p.get("localPath") or None
    pscope = f"project:{pid}"
    run = scopes.create_chat(pscope, title="🛡️ Auto-remediation")
    scopes.add_message(pscope, run["id"], "user",
                       f"[Auto] A check found: {finding[:200]}. CTO, coordinate a safe fix.")
    fixers = [m for m in members if m in ("Fullstack", "Mobile")] or members[:1]
    for m in fixers:
        ms = f"member:{pid}:{m}"
        mc = scopes.create_chat(ms, title="🛡️ fix")
        task = (f"A security/dependency issue was found: {finding[:300]}.\n"
                "In THIS project's folder, update the affected package(s) safely (e.g. npm audit fix "
                "or bump the specific dep), build, and report. Do NOT touch production or .env.")
        scopes.add_message(ms, mc["id"], "user", f"[Project CTO → {m}] {task}")
        agents_registry.record_usage(pid, m)
        reply = _engine_cwd(task, folder)
        scopes.add_message(ms, mc["id"], "assistant", reply)
        scopes.sync_up(ms, f"{m} attempted fix for: {finding[:50]}")
    if "DevOps" in members:
        proposal = deploy_proposal(pid)
        scopes.add_message(pscope, run["id"], "assistant",
                           f"[Project CTO → DevOps] Fixes attempted. Redeploy PROPOSAL (approve to run):\n{proposal[:700]}")
    scopes.sync_up(pscope, "auto-remediation done (redeploy pending approval)")
    return {"ok": True, "fixers": fixers}


def sync_run(pid: str, decisions: str = "") -> str:
    """EXECUTE the local→cloud sync, following the playbook + the owner's decisions for this run.
    Always excludes .env/secrets/node_modules. Returns what changed + build/service status."""
    p = get_project(pid)
    if not p:
        return "No such project."
    if not p.get("mappings"):
        return "No folder mappings first. Add a mapping first."
    maps = "\n".join(f"- {m['local']}  →  {m['cloud']}  ({m.get('role','')})" for m in p["mappings"])
    dec = f"\nOwner's decisions for THIS run: {decisions}\n" if decisions else "\n"
    return _engine(
        f"The owner approved this run. Read workspace/shared/infra/DEPLOY-PLAYBOOK.md and follow it. EXECUTE the "
        f"local→VM sync for project '{p['name']}', mappings:\n{maps}{dec}"
        "Defaults: never node_modules; NEVER the production .env; remove destination before rebuild; "
        "rebuild both; restart via systemd (not npm start). Do a --dry-run to confirm, then apply, "
        "then rebuild and report any pm2/build errors and final service status. If anything looks "
        "risky or contradicts the owner's decisions, STOP and explain instead of forcing it.")


def deploy_run(pid: str) -> str:
    """EXECUTE the deploy now (owner's click = approval). Conservative: build + restart the
    service, never touch .env, report result + how to roll back."""
    p = get_project(pid)
    if not p:
        return "No such project."
    return _engine(
        f"The owner approved this by clicking Run. Deploy project '{p['name']}' to its VM now: "
        "pull/sync the code (excluding .env/secrets), install, build, and restart its service via "
        "systemd. Do NOT modify other running sites. Report the result and the exact rollback "
        "command. If anything looks risky, stop and say why instead of forcing it.")


def generate_plan(pid: str) -> str:
    """Ask the engine to propose the components for a project from its description.
    Read-only planning (no writes); returns a markdown plan to show in the UI."""
    p = get_project(pid)
    if not p:
        return "No such project."
    prompt = (f"You are the Project CTO for '{p['name']}'. Description: {p.get('description','')}.\n"
              f"Propose the components/modules, the team members needed (frontend/backend/devops/…), "
              f"and a short build order. Be concise; this is a plan only, do not write code.")
    try:
        import claude_cli  # type: ignore
        if claude_cli.available():
            return claude_cli.ClaudeCLIBrain().respond(prompt, lang="en")
    except Exception:
        pass
    try:
        import brain_handler  # type: ignore
        return brain_handler.OllamaBrain().respond(prompt, lang="en")
    except Exception:
        return ("Plan (offline): scaffold frontend, backend API, data model, and a deploy "
                "pipeline; assign Frontend, Backend, and DevOps members; build core flow first.")
