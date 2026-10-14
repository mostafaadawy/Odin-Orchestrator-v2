# RedBerry Continuous SOC — Security Roles, Tools & Methodology (Learn-the-SOC)

This is the **educational guide** to the security company running inside Odin. It explains, for a non‑expert,
**who each agent is, what it does, the tools and methodology it uses, and how the agents hand work to each
other** — with **no overlapping responsibilities**. You can also open any agent in the app and ask it
"what is your role / your dependencies / how do you work" — each answer maps to a section below.

## How a real SOC thinks (the methodology we follow)

We use recognised industry standards, not ad‑hoc guessing:

- **NIST SP 800‑61** incident lifecycle: *Detection & Analysis → Containment → Eradication → Recovery → Post‑incident.*
- **SANS PICERL**: Preparation, Identification, Containment, Eradication, Recovery, Lessons‑learned.
- **The threat‑hunting funnel**: start **wide** (hypothesis‑free "white‑scope" sweep of the whole surface),
  then **narrow** to what the evidence actually supports — never jump to a cause.
- **MITRE ATT&CK**: every finding is mapped to the attacker technique it represents (e.g. T1190 exploit
  public‑facing app, T1496 resource hijacking, T1499 DoS, T1485/T1486 data destruction).
- **Evidence over symptoms**: a symptom (a 502, a CVE's *presence*) is never treated as the root cause. We
  confirm the actual mechanism before we call anything "confirmed", and we never turn missing data into a
  healthy conclusion.

Operating principle for the whole company: **Observe → Correlate → Verify → Report → Request approval → Act
only if approved.** The SOC is **read‑only and monitor‑only** by default; it changes nothing on its own.

## The team (each agent = one clear lane, no intersection)

### 🧭 CTO Orchestrator — governance & decisions
- **Job:** runs each cycle, decides scope, correlates everyone's findings into a root‑cause story, talks to
  you, and raises **approval requests**. It is the *only* agent that presents decisions to you.
- **Tools/Methodology:** correlation across all findings; NIST/PICERL framing; approval workflow.
- **Depends on:** every other agent's output. **Never** approves its own action.
- **Hands off:** a clear owner summary + approval requests.

### 🗺️ Asset, Exposure & Attack‑Surface Agent — "what do we have, where is it exposed"
- **Job:** maintains the **living inventory** of every cloud, VM, service and stack we run (Azure VM today;
  extensible to AWS, GoDaddy, Hostinger, Cloudflare, static/CDN). Fingerprints each stack (Next.js, NestJS,
  Laravel/PHP, Python, Prisma/PostgreSQL, static). Produces the **reverse‑search filter** so intelligence is
  targeted to *what we actually run* — not the whole internet.
- **Tools:** `server/soc_inventory.py`; project enumeration; stack fingerprints; provider models.
- **Depends on:** the platform project list + local paths. **Feeds:** Architect (targets intel), Predictor.
- **Not its lane:** it does not curate advisories, detect, or predict.

### 🧠 Security Intelligence & Threat‑Hunting Architect — external knowledge
- **Job:** pulls **current** vulnerability advisories for our *actual* dependency versions from **OSV.dev**
  (aggregates GHSA/NVD/npm), triages by **reachability** (runtime vs dev), and keeps the knowledge base +
  playbooks + detection rules current. Vulnerability *presence ≠ compromise.*
- **Tools:** `server/soc_intel.py`; OSV.dev API; the knowledge base + playbooks.
- **Depends on:** the Asset agent's inventory (what to look up). **Feeds:** Investigator, Predictor.

### 🔎 Security Operations Investigator — present‑state evidence
- **Job:** runs the **read‑only checks** on the current state: service health, network listeners, port/NSG/ufw
  hardening, website/endpoint health, SSH keys/users, persistence (cron/timers), crypto‑miner hunt,
  application abuse, DB anomaly, subscriber forensics, dependency intel.
- **Tools:** `server/soc_run.py` checks; read‑only SSH (a guard **refuses** any mutating command); `az` reads.
- **Depends on:** Architect intel + Asset inventory. **Feeds:** CTO correlation.
- **Not its lane:** behaviour‑over‑time (that's the Behavioral agent) and the future (that's the Predictor).

### 🕵️ Intrusion Detection & Behavioral Analytics Agent (UEBA) — stealthy abuse by behaviour
- **Job:** catches **signature‑evading, AI‑era** attacks by **how entities behave over time**, not by known
  signatures. Builds a **visitor behaviour profile** per IP (cadence, endpoints, accounts created, user‑agent
  rotation, timing regularity/entropy). Flags **same‑IP‑many‑accounts** and machine‑regular **low‑and‑slow**
  patterns (the RedBerry "an account every ~10 minutes from one IP"). **Smartly excludes the owner's dynamic
  IP** (allow‑list + interactive‑vs‑automated signature) to avoid false positives. Recommends **UFW/edge
  blocks** for confirmed‑bad IPs — **approval‑gated, never automatic.**
- **Tools:** `server/soc_behavior.py`; nginx access‑log mining (read‑only); coefficient‑of‑variation cadence
  scoring; rolling profiles persisted for cross‑run learning.
- **Depends on:** access logs. **Feeds:** CTO correlation (abuse chain).

### 🔮 Threat Prediction & Prevention Agent — predict & prevent (forward‑looking)
- **Job:** predicts **where a weakness is likely to appear next** given our stacks, exposure and the current
  findings, and recommends **proactive hardening to prevent it before exploitation.** (e.g. "a runtime‑reachable
  vulnerable package will be the next entry point — patch + add a WAF + least‑privilege runtime, exactly like
  the mining/502 incident".)
- **Tools:** `server/soc_predict.py`; stack‑driven predictive rules; evidence‑linked escalation; ATT&CK vectors.
- **Depends on:** Asset inventory + this run's findings + intel. **Not its lane:** present detection or advisories.

### 🛟 Recovery & Resilience Agent — protect & recover
- **Job:** business continuity. Keeps **dated, checksummed, ENCRYPTED backups** of configuration and database
  (captured **read‑only**, encrypted with a **strong key held only on your local desktop** — never in plaintext
  on the VM). Maintains a **backups registry**. Provides a **smart, date‑aware recovery plan**: given the date a
  problem started, it selects the **newest CLEAN backup *before* that date** (so recovery doesn't re‑introduce
  the damage), verifies the checksum, and decides whether recovery is even needed (avoids over‑recovery).
- **Tools:** `server/soc_recovery.py`; Fernet/AES encryption; pg_dump/config capture (read‑only); registry.
- **Approval rule:** **backup capture is non‑harmful → automatic, no approval.** **Restore overwrites
  production → always approval‑gated (you execute).**

### 📝 Reporting & Documentation Agent — explain it (reusable asset)
- **Job:** turns the whole cycle into a **branded, styled report** with a **plain‑language "In Plain Words"
  section first**, then the technical detail — exported as **PDF / DOCX / MD / PPTX** with the company logo.
  Reusable by any project (SOC, meetings, deploys).
- **Tools:** `server/report_engine.py`.

## Hand‑off flow (how they integrate)

```
Asset maps the surface  →  Architect arms with targeted intel  →  Investigator + Behavioral agent detect
        →  CTO correlates & narrows to a root cause (evidence, not a guess)
        →  Predictor says what to prevent next  →  Recovery ensures we can roll back cleanly
        →  Reporting explains it (humanized + technical)  →  CTO asks you to approve any change.
Nothing that modifies or recovers a working service happens without your explicit approval.
```

## What needs approval vs. what doesn't (the smart line)

- **No approval (read‑only / additive, harms nothing):** all checks, the asset inventory, threat‑intel
  refresh, behaviour profiling/list, prediction, and **encrypted backup capture** (writes only to the SOC's own
  encrypted folder).
- **Approval required (modifies or recovers a working service, or affects other users):** database/service
  **restore**, **UFW/edge IP blocks**, dependency **upgrades/patches**, service **restarts**, firewall/NSG or
  config **changes**. The SOC prepares the exact action, evidence, impact, downtime and rollback — **you decide.**

## Where it lives (separate, inspectable project)

The SOC is its own project folder so you can open its content directly:
`~/Desktop/AiAgentWorkSpace/RedBerry-Continuous-SOC/soc/` → `knowledge/`, `playbooks/`, `detections/`,
`history/`, `reports/`, `backups/`, `schedules/`. Reports land in `reports/` (PDF/DOCX/MD/PPTX).

## APIs (web/mobile/desktop use these)

`/soc/status`, `/soc/settings`, `/soc/run`, `/soc/report?fmt=`, `/soc/finding`, `/soc/inventory`,
`/soc/behavior`, `/soc/recovery`, `/soc/backup`. Daily automated run at **23:00 America/New_York** (DST‑aware,
with catch‑up if the desktop was off).

## Added lanes (expansion — autonomous agents, read-only + approval-gated changes)

### 🩹 Vulnerability & Patch-Management Agent — "what's vulnerable, patch what matters"
Maps the live stack (OS pkgs, npm, nginx, Prisma) to CVEs, ranks by exploitability + exposure, produces a patch plan.
- **Depends on:** Asset inventory.  **Feeds:** Threat Prediction, Investigator.  **Never** applies patches (approval-gated).

### 🔑 Identity & Access Governance Agent — "who can access what"
Enumerates accounts, SSH keys, sudo/privileges, dormant/over-privileged users, MFA coverage; flags least-privilege violations.
- **Depends on:** Asset inventory.  **Feeds:** Investigator, Compliance.  **Never** changes accounts/keys (approval-gated).

### 📋 Compliance & Config-Baseline Agent — "are we compliant + on-baseline"
Checks PCI/PHI scope, config-baseline drift (nginx/systemd/ufw/TLS), audit-log integrity, secrets hygiene.
- **Depends on:** Asset + IAM.  **Feeds:** Reporting, CTO verdict.  **Never** changes config (approval-gated).

### 🧪 Detection Engineering & Purple-Team Validation Agent — "do our detections actually fire"
Authors/maintains detection rules and safely validates they fire (benign simulation); maps coverage to MITRE ATT&CK.
- **Depends on:** Architect intel + Investigator/UEBA findings.  **Feeds:** UEBA, Investigator.  Validations are benign; active tests approval-gated.
