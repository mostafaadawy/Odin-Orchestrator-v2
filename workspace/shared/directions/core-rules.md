# core-rules.md — SOURCE OF TRUTH

> **This file is loaded and obeyed before ANY implementation or modification task.**
> If a rule here conflicts with a "standard" or "best-practice" default, **this file wins.**
> Last updated: 2026-06-20 · Maintained by: CTO Brain (with owner approval for changes).

---

## 0. How to use this document

- The orchestrator MUST read this file in full before planning or executing any task.
- Rules are versioned. Any change to this file is itself a logged event in `history/`.
- New custom requirements are added here intelligently: appended under the right section,
  dated, and never silently overwriting prior intent. Superseded rules are struck through,
  not deleted, with a pointer to the replacement.

---

## 1. Inviolable operating rules

1. **Read these rules first.** No coding, config, or infra task starts before this file is read.
2. **Never assume standard behavior when custom logic exists.** Check this document for a
   custom rule before applying any conventional default (billing, auth, deploy, data, etc.).
3. **Never touch production or the Azure VM without explicit approval.** Explain → assess
   risk → request approval → only then act. (See `orchestrator/ORCHESTRATOR.md` §Approval Gate.)
4. **Never break existing working logic.** Before changing anything, identify what currently
   works and what depends on it. If a change risks regression, say so and propose mitigation.
5. **Keep complete history.** Every significant decision/change is timestamped in `history/`.
6. **Ask when unclear.** Ambiguity → ask the owner. Do not guess on anything consequential.
7. **Clean, documented, professional output.** Structure and code must be maintainable.
8. **Respect existing security posture.** Closed ports, IP allowlists, existing sync method —
   honor them; never widen network exposure without approval.

---

## 2. Architecture decisions (ADR log)

> Append new decisions here as `ADR-NNN`. Keep them short and dated.

- **ADR-001 (2026-06-20):** The orchestration platform lives in `Odin-Orchestrator/` with a
  rules + history + agents + approvals + dashboard structure. Rationale: separation of
  memory, audit, execution, and oversight. Status: Accepted.
- **ADR-002 (2026-06-20):** No production/VM action proceeds without an approval artifact in
  `approvals/`. Status: Accepted.
- **ADR-003 (2026-06-20):** Azure VM access (no dedicated MCP connector available) will run
  through the sandboxed shell over key-based SSH, gated by the approval system. Status:
  Accepted, pending owner-provided access details.
- **ADR-004 (2026-06-21):** Voice stack is **hybrid** — reuse Kokoro English TTS, rebuild STT
  on local faster-whisper (EN+AR, offline), add Arabic TTS (macOS `say`/Piper). Components
  extracted into `voice/` with zero dependency on `mostafa-app` (which will be deleted).
  Status: Accepted (integration into a running app still pending).
- **ADR-005 (2026-06-21):** From the Ruflo review — **adapt** lifecycle hooks, a lean
  deterministic dispatcher, and (later) a read-only local semantic memory; **reject** swarm
  scale, self-evolving rules, and stub tools. Keep "fewer but real" tools + human approval.
  Status: Accepted as direction.
- **ADR-006 (2026-06-21):** Azure connection uses the strict dynamic-IP procedure
  (`runbooks/azure-secure-connection.md`); systemd (not PM2); fixed folder mapping. Status:
  Accepted.
- **ADR-008 (2026-06-21):** Brain↔agent **dispatcher** built as a lean deterministic router
  (`orchestrator/dispatcher.py`): classify→load-rules→approval-check→hooks→route. It is the
  Brain behind `/chat` + voice and enforces the approval gate (gated requests are NOT executed;
  the user is told an approval request will be prepared). Routing telemetry → `history/routing.jsonl`
  (kept out of the main audit log). **Mobile access** = `dashboard/mobile.html` + optional
  `ODIN_ACCESS_TOKEN` gate on `/chat`,`/dispatch`,`/voice/*`; LAN use is free, **internet
  exposure is approval-gated** via the Azure procedure (`runbooks/mobile-access.md`). Status: Accepted.
- **ADR-007 (2026-06-21):** Voice wired into the dashboard via a local FastAPI server
  (`server/app.py`): mic → `/voice/stt` (Whisper) → `/chat` (local Ollama, **pluggable**
  `brain_handler`) → `/voice/tts` (Kokoro EN / Piper AR). The brain handler is the documented
  swap point for the future dispatcher (same `respond(text, lang)` interface). Arabic TTS
  engine = **Piper** (macOS `say` fallback). Status: Accepted; runs locally, unauthenticated
  by design (add auth before any exposure; never bypass the Azure gate).

---

## 3. Coding standards

- Prefer clarity over cleverness. Document non-obvious decisions inline.
- All money/amounts handled with integer minor units or decimal types — **never floats.**
- All external input validated and sanitized at the boundary.
- Secrets never hard-coded, never logged, never committed. Use env/secret store.
- Errors are handled explicitly; no silent catches on financial or auth paths.
- Every new module ships with at least basic tests (QA agent enforces).

## 4. Security & compliance rules (fintech / HIPAA)

- Anything touching PII, PHI, or payment data triggers a **Security & Compliance review**.
- Payment/card data: never store raw PAN; follow PCI-DSS scope minimization.
- PHI (where HIPAA applies): encryption in transit and at rest; access logged; minimum necessary.
- Audit logs for sensitive access are append-only and retained.
- No new inbound port or public exposure without approval + documented justification.

## 5. DevOps / Azure rules

- Deployments follow a runbook in `runbooks/`. No ad-hoc production changes.
- SSL certificates managed via runbook; track expiry; renew before lapse.
- Respect the owner's existing synchronization method — augment, do not replace it.
- Every VM-touching command is shown in full and approved before execution.

### 5.1 Azure secure-connection procedure (CUSTOM — strict, dynamic IP / Egypt)
Full procedure: `runbooks/azure-secure-connection.md`. The system MUST remember:
- Operator's home IP is **dynamic**; the VM allows **one IP at a time** for SSH. Never widen
  exposure (no `0.0.0.0/0`) to simplify access.
- The allowed IP must be updated in **two** places that must agree: the VM **OS firewall**
  (via Azure **Serial Console**, because SSH is blocked until the IP is allowed) **and** the
  Azure **NSG** (VM → Networking → SSH inbound source IP).
- Services run under **`systemd`** (NOT PM2); restart/rebuild via `systemctl`.
- Sync uses **`scp`** local → Azure. **Folder mapping:**
  `frontend/organics` ↔ `organics` ; `backend/organics-backend` ↔ `bendcore`.
- Reverse **proxies** front the sites and must be handled on rebuild.
- **Automation policy:** Brain may auto-run read-only steps (detect IP, SSH reachability,
  health checks, log reads, drafting commands). All firewall/NSG/scp/systemctl/proxy changes
  are **approval-gated**. Serial Console + NSG Portal edits are **manual** (Brain guides only).

## 6. Custom business logic (NON-STANDARD — read carefully)

> These are the behaviors that differ from industry defaults. **Always check here first.**

### 6.1 Subscription / billing model — CUSTOM
- **Status: PLACEHOLDER — awaiting owner specification.**
- Known: Odin Markets uses a subscription model that is **NOT standard recurring billing.**
- Until the owner documents the exact rules here, the orchestrator MUST NOT implement,
  modify, or reason about billing using standard recurring-subscription assumptions.
  It must ask the owner for the precise model first.
- _Fields to capture when specified: billing trigger, proration logic, trial/grace behavior,
  upgrade/downgrade handling, refunds, failed-payment handling, dunning, entitlements._

### 6.2 Voice — CUSTOM
- Audio must stay **on-device** (local Whisper STT, local TTS). Do not reintroduce cloud
  speech APIs for a fintech product. EN + AR both required. See `workspace/docs/VOICE-ANALYSIS.md`.

### 6.3 No dependency on `mostafa-app` — CUSTOM
- The final system must run independently. Nothing in `Odin-Orchestrator/` may import from or
  reference `mostafa-app`. Useful pieces are **extracted and integrated**, then the folder is
  deleted by the owner. (Verified for the voice module on 2026-06-21.)

### 6.4 Engine & Cockpit UX — CUSTOM (binding)
- **Claude CLI is the core engine** (Claude Code on the project), NOT the local LLM. Ollama is
  only a fast front for triage/simple answers/progress narration and a fallback. Wired in
  `server/claude_cli.py`; dispatcher prefers it (ODIN_ENGINE=claude). _Corrected 2026-06-21
  after finding the brain was running on Ollama only._
- **Full requirements live in `design/CONVERSATIONAL-UX-SPEC.md` and must not be discarded:**
  humanized/fast triage (answer simple directly; ask before deep work; narrate while working),
  and the UI cockpit (bigger window, animated status + icons + live logs, continuous progress,
  streamed answers, artifact rendering for code/documents). Build phases A–D.

### 6.5 Other custom rules
- _(append as they emerge)_

---

## 7. Change log for this file

| Date (UTC) | Change | By | Approval |
|------------|--------|----|----------|
| 2026-06-20 | Initial creation of core-rules with §1–6 and billing placeholder | CTO Brain | Phase 1 build |
