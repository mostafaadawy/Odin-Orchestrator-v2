#!/usr/bin/env python3
"""
Threat Prediction & Prevention — the Threat Prediction & Prevention Agent's capability.

FORWARD-LOOKING security. Given (a) the living asset inventory, (b) this run's findings, and (c) the
targeted threat intelligence, it predicts WHERE A WEAKNESS IS LIKELY TO APPEAR NEXT and recommends
proactive HARDENING to prevent it BEFORE exploitation. Predict & prevent — not detect (Investigator),
not curate external advisories (Architect), not inventory (Asset agent). Read-only; recommendations only.

Each prediction: {area, prediction, likelihood(low/medium/high), why (evidence-linked), prevention (proactive,
approval-gated), attack_vector (MITRE ATT&CK where applicable)}.
"""
from __future__ import annotations

# Stack-driven predictive rules — "if we run X and it's exposed, Y tends to become the next weakness".
_STACK_RULES = {
    "Next.js (SSR/React)": [
        ("SSR request handling", "SSRF / header-injection via SSR data fetching is a recurring Next.js class",
         "medium", "Add strict allow-lists for server-side fetch targets; security headers (CSP, HSTS, "
         "X-Content-Type-Options); disable source maps in prod.", "T1190 exploit public-facing app"),
        ("client bundle", "API keys/secrets accidentally shipped in the client bundle",
         "medium", "Scan build output for secrets; keep secrets server-side only; rotate any NEXT_PUBLIC_* misuse.",
         "T1552 unsecured credentials"),
    ],
    "NestJS (Node API)": [
        ("dependency surface", "A transitive npm dependency gains a critical advisory and becomes exploitable",
         "high", "Pin + monitor (already via OSV); enable Dependabot/renovate; test-gated upgrades; runtime WAF.",
         "T1190 → T1496 (as in the mining incident)"),
        ("authz", "Broken object-level authorization as endpoints grow", "medium",
         "Central guard + per-resource ownership checks; add authz tests.", "T1078 valid accounts abuse"),
    ],
    "Laravel/PHP": [
        ("mass assignment / upload", "Mass-assignment + unrestricted file upload are the top Laravel weaknesses",
         "medium", "$fillable allow-lists; validate+scan uploads; store outside web-root.", "T1190"),
    ],
    "Prisma/PostgreSQL": [
        ("backup/DR", "No verified, dated, encrypted backups → unrecoverable data loss on abuse/ransomware",
         "high", "Enable the Recovery agent's encrypted dated backups + periodic restore test.", "T1485/T1486 data destruction"),
        ("exposure", "DB drifts to a non-localhost bind or weak creds as infra changes", "low",
         "Keep localhost-only bind + firewall; strong rotated creds; monitor (already).", "T1210"),
    ],
    "Static/landing": [
        ("form abuse", "Guest/newsletter forms become bot-abuse + third-party quota drains (the RedBerry class)",
         "high", "CAPTCHA + single-use tokens + rate-limit on ALL guest-triggerable endpoints; edge bot control.",
         "business-logic abuse T1583/T1586"),
    ],
}

def predict(inventory: dict, findings: list, intel_summary: dict | None = None) -> list:
    preds = []
    frameworks = set(inventory.get("reverse_search", {}).get("frameworks", []))
    providers = set(inventory.get("reverse_search", {}).get("providers", []))

    # 1) stack-driven predictions for everything we actually run
    for fw in frameworks:
        for area, prediction, likelihood, prevention, vector in _STACK_RULES.get(fw, []):
            preds.append({"area": f"{fw} · {area}", "prediction": prediction, "likelihood": likelihood,
                          "why": f"we run {fw} (from the living inventory)", "prevention": prevention,
                          "attack_vector": vector})

    # 2) evidence-linked predictions from THIS run's findings (escalate likelihood when corroborated)
    byid = {f["id"]: f for f in findings}
    dep = byid.get("SOC-DEP-002")
    if dep and dep.get("classification") in ("Suspicious", "Probable"):
        preds.append({"area": "dependency drift", "prediction": "A currently runtime-reachable vulnerable package "
                      "will be the next exploited entry point if left unpatched (this is exactly how the mining/502 "
                      "incident started).", "likelihood": "high", "why": f"evidence: {dep['id']} {dep['classification']}",
                      "prevention": "Prioritized, test-gated upgrade of runtime-reachable packages; keep OSV monitoring daily; "
                      "add a WAF/edge in front; least-privilege runtime user so an exploit can't mine freely.",
                      "attack_vector": "T1190 → T1496 resource hijacking"})
    if byid.get("SOC-APP-004", {}).get("classification") in ("Suspicious", "Probable") or \
       byid.get("SOC-APP-001", {}).get("classification") in ("Suspicious", "Probable"):
        preds.append({"area": "abuse escalation", "prediction": "Bot abuse will migrate to any UNPROTECTED guest "
                      "endpoint next (password reset, contact, promo) and keep draining Klaviyo/HubSpot quota.",
                      "likelihood": "high", "why": "evidence: active app-abuse findings this run",
                      "prevention": "Apply CAPTCHA + single-use tokens + rate-limit UNIFORMLY across ALL guest-triggerable "
                      "endpoints, not just newsletter; verify OTP/verification code is never exposed client-side.",
                      "attack_vector": "business-logic abuse"})

    # 3) architecture-level predictions from provider posture
    if "azure-vm" in providers and "cloudflare" not in providers and "static-cdn" not in providers:
        preds.append({"area": "single-origin exposure", "prediction": "A single origin VM with no edge WAF is the "
                      "likely next DoS/abuse pressure point.", "likelihood": "medium",
                      "why": "inventory shows origin-only exposure (no edge/WAF provider)",
                      "prevention": "Put Cloudflare/edge WAF in front; keep only 80/443 public via reverse proxy; "
                      "SSH restricted to your single (dynamic) IP with a refresh protocol; ufw on.",
                      "attack_vector": "T1498/T1499 DoS"})
    if not any("backup" in (f.get("title", "").lower()) for f in findings):
        preds.append({"area": "resilience", "prediction": "Without verified encrypted backups, any successful abuse/"
                      "ransomware/DB corruption becomes unrecoverable.", "likelihood": "medium",
                      "why": "no verified backup evidence in this run",
                      "prevention": "Enable the Recovery & Resilience agent: dated, checksummed, ENCRYPTED config+DB "
                      "backups + periodic restore tests + smart date-aware recovery.",
                      "attack_vector": "T1485/T1486 data destruction"})

    # de-dup + stable order (high likelihood first)
    order = {"high": 0, "medium": 1, "low": 2}
    seen, out = set(), []
    for p in sorted(preds, key=lambda x: order.get(x["likelihood"], 3)):
        k = (p["area"], p["prediction"][:40])
        if k not in seen:
            seen.add(k); out.append(p)
    return out
