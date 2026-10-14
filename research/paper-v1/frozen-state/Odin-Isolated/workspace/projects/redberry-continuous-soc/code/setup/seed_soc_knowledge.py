#!/usr/bin/env python3
"""Seed the RedBerry Continuous SOC shared knowledge base — the full real-world SOC job set, with
consistent structure (every item: id, indicators, required/disconfirming evidence, false-positives,
early-stop, data sources, safe commands, operational impact, remediation, cadence, status)."""
import sys, pathlib, json, datetime
R = pathlib.Path("/Users/mostafaadawy/Desktop/AiAgentWorkSpace/Odin-Isolated")
sys.path.insert(0, str(R / "server"))
import store  # type: ignore

PID = "redberry-continuous-soc"
BASE = store.DATA / "projects" / PID / "soc"
TODAY = datetime.date.today().isoformat()

def w(rel, text):
    p = BASE / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text if text.endswith("\n") else text + "\n", encoding="utf-8")

# ---- playbook template (every real SOC job uses the same consistent shape) ------------------------
def playbook(pid, title, category, assets, threat, indicators, req_ev, disc_ev, fps, earlystop,
             sources, cmds, impact, remediation, risks, cadence, related):
    def bl(items): return "\n".join(f"- {x}" for x in items)
    return f"""# {title}

- **ID:** {pid}
- **Category:** {category}
- **Affected assets:** {assets}
- **Status:** active   **Last reviewed:** {TODAY}   **Review cadence:** {cadence}

## Threat description
{threat}

## Indicators (weak → strong)
{bl(indicators)}

## Required evidence before escalating
{bl(req_ev)}

## Disconfirming / false-positive evidence
{bl(disc_ev)}

## Known false-positive cases
{bl(fps)}

## Early-stop conditions
{bl(earlystop)}

## Data sources
{bl(sources)}

## Safe (read-only) commands / queries
```bash
{chr(10).join(cmds)}
```

## Possible operational impact of remediation
{impact}

## Remediation options (recommend only — never auto-apply)
{bl(remediation)}

## Remediation risks
{bl(risks)}

## Related
{related}
"""

# ================= KNOWLEDGE CATALOGS =================
w("knowledge/asset-inventory.md", f"""# Asset Inventory  (last reviewed {TODAY})

## Cloud / VM
- Azure VM `django-vm` (52.180.154.225), resource group `Django-Project`, NSG `django-vm-nsg`.
- SSH: user `mostafa`, port 22 restricted to the owner's current dynamic IP (single-IP allow).
- Firewall: ufw 80/443 open; 22 single-IP; PostgreSQL localhost-only.

## Services (systemd, on the VM)
- `bendcore` (NestJS API, :4013) · `organics` (Next.js, :3000) · `nginx` (reverse proxy 80/443)
- `odin-anchor-online` · `odin-web-online` · `odinmarkets` · `odinmedicalsupplies-*` · `omh` · `odin-travel-desk`

## Applications / public endpoints
- RedBerry Organics: `POST /email-subscribe`, `POST /api/register`, `/api/payments/*` (Stripe + Elavon)
- Payment gateways: Stripe (3DS) + Elavon/Converge. 2FA runtime-gated (SKIP_2FA=false = required).

## Data stores
- PostgreSQL `organics` (localhost:5432) · `odin_anchor_iso` DB.

## Integrations
- Klaviyo, HubSpot (marketing), Stripe, Elavon, email/SMTP.

> Baseline: the authoritative known-good is in `history/baselines/`. Update via the Architect agent only.
""")

w("knowledge/evidence-standards.md", """# Evidence Standards

Every finding carries evidence with: source, collection time, collection method, integrity metadata
(where practical), retention status, redaction status, chain-of-custody (for serious incidents).

## Confidence ladder (a finding is only 'Confirmed' when its evidence threshold is met)
Informational · Benign/Expected · False Positive · Needs Review · Suspicious · Probable · Confirmed

## Redaction (never place in reports)
passwords, API keys, JWTs, cookies, session tokens, verification codes, 2FA codes, private keys,
payment data, complete customer records. Mask/hash emails; obey raw-IP retention policy.

## Data-source states (never turn missing evidence into a healthy conclusion)
Checked and healthy · Checked and finding detected · Partially checked · Not checked · Data unavailable · Not applicable
""")

w("knowledge/false-positive-catalog.md", """# False-Positive Catalog  (expected benign patterns)

A warning/suspicious string is NOT automatically a confirmed threat. Known benign:
- Gunicorn temp files marked deleted; MySQL temp files; PostgreSQL shared-memory files.
- Ordinary systemd timers; approved cron jobs; Azure VM agent / authorized Azure Run Command.
- Expected app ports protected by NSG + UFW; failed auth from an admin mistyping a password.
- Expected dynamic owner IP changes; rejected `.env` / WordPress scans (internet background noise).
- Node.js/Next.js/TypeScript build metadata containing 'suspicious' words; dependency code refs not executed.
- Healthy DB localhost bindings; known monitoring agents; established deploy behavior.
- Legitimate shared-household IP / office NAT (multiple accounts one IP can be benign).
""")

w("knowledge/dependency-security.md", """# Dependency & Supply-Chain Security

Coverage: NPM, OS packages, backend/frontend frameworks, DB clients, auth libs, cloud SDKs, integrations.
Do NOT report all CVEs. For each vuln determine: installed?, exact version, runtime vs dev, vulnerable
code path used?, config present?, externally reachable?, auth required?, exploitation indicators?, fixed
version?, upgrade breakage?, transitive?, lockfile trustworthy?, malicious-package indicators?, install
scripts executed?, integrity changed?, evidence of actual exploitation?

Prioritize: Exploited&confirmed > Exploitable-in-env > Likely > Potentially affected > Installed-not-reachable > Not applicable.

Supply-chain hunts: package hijacking, malicious deps, typosquatting, lockfile manipulation, install-script
abuse, dependency confusion, compromised NPM packages. Record advisory source + publication date.
""")

# compact catalogs
for name, body in [
 ("threat-catalog.md", "Master index of threats; each links to a playbook + detection rule. Cross-reference, never duplicate."),
 ("detection-catalog.md", "Index of detection rules (see detections/detection-rules.yaml) mapped to data sources + evidence."),
 ("data-source-map.md", "Maps each check to its data source: nginx logs, systemd journal, auth log, PostgreSQL, Azure Activity Log, Klaviyo/HubSpot APIs, git, npm, ss/netstat."),
 ("cloud-security.md", "Azure control-plane review: Activity Log, Run Command / VM extensions, NSG changes, identity/role changes, key/secret events. Read-only when connectors available."),
 ("application-abuse.md", "Business-logic abuse: registration/subscription abuse, account farming, coupon/quiz/referral abuse, idempotency failures, direct API automation bypassing frontend."),
 ("authentication-abuse.md", "Auth abuse: credential stuffing, 2FA/verification farming, replayed/expired challenges, CAPTCHA bypass, SSH auth anomalies, new keys/users."),
 ("incident-history.md", f"## {TODAY} — RedBerry newsletter/registration abuse (INC-2026-001)\nApp-level business-logic abuse (low-and-slow, ~10-min cadence). NOT VM compromise. See playbooks/newsletter-subscription-abuse.md."),
]:
    w(f"knowledge/{name}", f"# {name.replace('-',' ').replace('.md','').title()}\n\n{body}\n")

# ================= THE REDBERRY REFERENCE PLAYBOOK (detailed) =================
w("playbooks/newsletter-subscription-abuse.md", playbook(
 "PB-APP-001", "Newsletter / Registration Abuse (RedBerry INC-2026-001)", "application-abuse",
 "POST /email-subscribe, POST /api/register, Klaviyo/HubSpot, email/2FA, customer+marketing DBs",
 "Automated business-logic abuse: fraudulent newsletter subscriptions + automated account registrations "
 "using controlled mailboxes that successfully receive email verification and 2FA codes, verify, and log "
 "in. Submissions are spaced several minutes apart (~10 min) to evade burst throttling. This was determined "
 "to be APP-LEVEL abuse — NOT malware, root compromise, persistence, DB exposure, exfiltration, web/reverse "
 "shells, crypto-mining, or public internal-port access. Preserve that distinction.",
 ["Submissions separated by ~10 minutes (low-and-slow — a 10-min gap does NOT make it legitimate)",
  "Randomized/implausible user-agents; suspicious or fabricated names (weak signals)",
  "Disposable/temporary email domains (weak signal)",
  "Distinct accounts sharing one IP/device; OR one account across many IPs",
  "Repeated email-verification + 2FA activity; verification success followed by suspicious behavior",
  "Newsletter submits triggering disproportionate Klaviyo/HubSpot/journey/support/email actions",
  "Requests that bypass normal frontend navigation; direct API automation",
  "Idempotency failures causing duplicate downstream jobs; replayed/expired challenges; CAPTCHA fail/bypass"],
 ["Correlated request log showing the ~10-min cadence across >N submissions",
  "IP↔account↔device association table (distinct accounts/IP or distinct IPs/account)",
  "Downstream amplification count (Klaviyo/HubSpot events, support tasks, emails) per submission",
  "Evidence the requests skip frontend flow (missing expected headers/steps) — direct automation"],
 ["Traffic matches a real launch/campaign with legitimate users",
  "Shared-household / office-NAT explains one-IP-many-accounts",
  "Downstream actions are within normal per-submission ratios"],
 ["Legitimate shared IP (household/office NAT)", "A real marketing campaign spike",
  "One genuine user retrying after a failed submission"],
 ["If the endpoints are not receiving elevated volume vs baseline, stop and mark informational",
  "If no downstream amplification exists, downgrade to weak-signal watch",
  "If a prior investigation remains valid and no new pattern, reuse it"],
 ["nginx access logs (/email-subscribe, /api/register)", "app auth/verification logs",
  "Klaviyo/HubSpot event APIs (read-only)", "DB registration/subscription tables (read-only counts)"],
 ["# READ-ONLY counts only — never mutate:",
  "grep -E 'POST /(email-subscribe|api/register)' /var/log/nginx/access.log | awk '{print $1,$4}' | tail -200",
  "# in the app DB (read-only): count registrations & subscriptions per hour / per IP (no deletes)"],
 "None from detection (read-only). Remediation (CAPTCHA, step-up, tokens) may add user friction and, if "
 "misconfigured, block legitimate signups — must be approval-gated with false-positive protection for shared IPs.",
 ["Managed CAPTCHA on register/login; risk-based step-up challenges",
  "Action-bound, expiring, single-use tokens + replay prevention; server-side challenge validation",
  "Separate low-friction marketing verification; double opt-in for elevated risk",
  "Idempotency keys; suppress downstream actions until security checks pass; monitor/skip/enforce modes"],
 ["CAPTCHA/step-up can hurt conversion + block shared-IP legit users if thresholds are wrong",
  "Token/replay changes can break existing links; test in monitor mode first"],
 "daily (event-driven on abuse spikes)",
 "account-farming.md · low-and-slow-automation.md · authentication-abuse.md · INC-2026-001"))

# ================= THE FULL REAL-WORLD SOC JOB SET (playbooks) =================
PB = [
 ("account-farming.md","PB-APP-002","Account Farming","application-abuse","registration, accounts DB",
  "Mass creation of accounts (often via controlled mailboxes) for coupon/quiz/referral abuse or resale."),
 ("low-and-slow-automation.md","PB-APP-003","Low-and-Slow Automation","application-abuse","public endpoints",
  "Automation deliberately spaced to evade burst/rate limits. Detect via cadence regularity, not volume."),
 ("credential-abuse.md","PB-AUTH-001","Credential Abuse / Stuffing","authentication-abuse","auth, accounts",
  "Credential stuffing / brute force / password spraying against login + 2FA."),
 ("suspicious-ssh-access.md","PB-AUTH-002","Suspicious SSH Access","authentication-abuse","VM ssh",
  "Unexpected SSH auth, new authorized keys, new users, logins from unexpected IPs."),
 ("azure-control-plane-review.md","PB-CLOUD-001","Azure Control-Plane Review","cloud-security","Azure",
  "Review Activity Log, Run Command / VM extensions, NSG/identity/role changes for unauthorized control-plane actions."),
 ("exposed-secrets.md","PB-CLOUD-002","Exposed Secrets","cloud-security","repos, env, VM",
  "Secrets committed to git, world-readable .env, tokens in logs. Redact; never print the secret."),
 ("web-shell-hunt.md","PB-HOST-001","Web-Shell Hunt","host-security","web roots, php/node",
  "Hunt for web shells / unexpected executable handlers in web-served paths."),
 ("malware-and-miner-hunt.md","PB-HOST-002","Malware & Crypto-Miner Hunt","host-security","VM processes",
  "Hunt for miners/malware: high steady CPU, unknown binaries, suspicious outbound to mining pools."),
 ("persistence-hunt.md","PB-HOST-003","Persistence Hunt","host-security","cron, systemd, keys, rc",
  "Hunt persistence: cron, systemd units/timers, authorized_keys, profile/rc, LD_PRELOAD, startup hooks."),
 ("database-exposure.md","PB-DB-001","Database Exposure","database-security","PostgreSQL",
  "Confirm DB is localhost-only; detect any external bind / firewall gap. Localhost bind is benign."),
 ("database-access-anomaly.md","PB-DB-002","Database Access Anomaly","database-security","PostgreSQL",
  "Auth failures, new roles, unusual query volume, privilege changes (read-only audit)."),
 ("dependency-compromise.md","PB-DEP-001","Dependency Compromise","dependency-security","npm, os pkgs",
  "Malicious/compromised dependencies; verify reachability + exploitation before escalating."),
 ("npm-supply-chain.md","PB-DEP-002","NPM Supply-Chain","dependency-security","node_modules, lockfile",
  "Typosquat, dependency confusion, lockfile manipulation, install-script abuse, integrity change."),
 ("data-exfiltration.md","PB-NET-001","Data Exfiltration","network-security","VM egress",
  "Unusual outbound volume/destinations; large DB reads followed by egress. Baseline egress first."),
 ("unusual-outbound-networking.md","PB-NET-002","Unusual Outbound Networking","network-security","VM egress",
  "New outbound connections, beaconing patterns, connections to known-bad infra."),
 ("service-health-and-resource-abuse.md","PB-OPS-001","Service Health & Resource Abuse","operations","systemd, VM",
  "Unexpected restarts, failed services, resource exhaustion, quota abuse of third-party APIs."),
 ("integrity-monitoring-failure.md","PB-OPS-002","Integrity-Monitoring Failure","operations","monitoring",
  "Detect when integrity/security monitoring itself is broken (e.g. misconfigured email reporting)."),
 ("false-positive-validation.md","PB-META-001","False-Positive Validation","meta","all",
  "Validate suspected findings against the false-positive catalog before escalation."),
]
for fname, pid, title, cat, assets, threat in PB:
    w(f"playbooks/{fname}", playbook(
        pid, title, cat, assets, threat,
        ["(topic-specific weak→strong indicators — see detections/detection-rules.yaml)"],
        ["(defined required evidence before escalation — evidence-standards.md)"],
        ["(disconfirming evidence / benign explanation)"],
        ["(see knowledge/false-positive-catalog.md)"],
        ["If the relevant service/port/package is absent → stop that branch (not applicable)",
         "If a prior valid investigation exists and nothing changed → reuse it"],
        ["(see knowledge/data-source-map.md)"],
        ["# READ-ONLY inspection only — never mutate production"],
        "Detection is read-only (no impact). Any remediation is approval-gated with stated downtime/rollback.",
        ["(recommend-only options with operational impact + rollback)"],
        ["(remediation risks + false-positive protection)"],
        "daily / weekly per risk-based cadence", cat))

# ================= DETECTIONS =================
w("detections/severity-model.yaml", """# Severity model (severity x confidence -> action)
levels: [informational, low, medium, high, critical]
classification: [Informational, Benign/Expected, False Positive, Needs Review, Suspicious, Probable, Confirmed]
rule: "A finding is 'Confirmed' ONLY when its playbook evidence threshold is satisfied."
action_gate: "Any production-affecting action requires an approval request (never auto-applied)."
""")
w("detections/early-stop-rules.yaml", """# Early-stop rules (reduce load/noise/cost without hiding uncertainty)
- if: service_not_installed        then: stop_branch(not_applicable)
- if: port_not_listening_no_forward then: stop_public_exposure_test
- if: package_version_not_affected then: stop_vuln_branch
- if: exploit_prereq_absent        then: mark_not_applicable
- if: logs_show_rejection_only     then: stop_disclosure_escalation
- if: matches_healthy_baseline     then: stop_treating_suspicious
- if: hash_matches_release_baseline then: stop_malware_analysis(file)
- if: prior_investigation_valid_no_change then: reuse_previous
""")
w("detections/risk-signals.yaml", """# Weak risk signals (never confirm on their own)
weak_signals: [disposable_email, implausible_user_agent_rotation, suspicious_name, shared_ip, ten_minute_cadence]
note: "Weak signals raise suspicion + drive correlation; they do NOT confirm a finding."
""")
w("detections/correlation-rules.yaml", """# Correlation rules
- name: newsletter_amplification
  when: [post_email_subscribe, downstream_klaviyo_or_support_actions]
  correlate_by: [ip, account, device, timing]
  raises: PB-APP-001
- name: distinct_accounts_one_ip
  when: [many_registrations_single_ip]
  raises: PB-APP-002
- name: verification_2fa_farming
  when: [repeated_verification, repeated_2fa, controlled_mailboxes]
  raises: PB-AUTH-001
""")
w("detections/detection-rules.yaml", """# Detection rules (data-source -> signal -> playbook). Read-only.
rules:
  - id: DR-APP-001
    source: nginx_access_log
    signal: "regular ~10-min POST /email-subscribe or /api/register cadence"
    playbook: PB-APP-001
    evidence: [request_cadence, ip_account_map, downstream_amplification]
  - id: DR-AUTH-002
    source: auth_log
    signal: "new authorized_key OR new user OR ssh login from unexpected IP"
    playbook: PB-AUTH-002
    evidence: [authorized_keys_diff, passwd_diff, ssh_login_ip]
  - id: DR-DB-001
    source: ss_netstat
    signal: "postgres listening on non-localhost"
    playbook: PB-DB-001
    evidence: [listen_addresses]
  - id: DR-OPS-001
    source: systemd
    signal: "unexpected service restart OR failed unit"
    playbook: PB-OPS-001
    evidence: [restart_count, unit_state]
  - id: DR-DEP-002
    source: npm_lockfile
    signal: "lockfile integrity change OR install-script anomaly"
    playbook: PB-DEP-002
    evidence: [lockfile_diff, install_scripts]
""")

# ================= SCHEDULES =================
w("schedules/security-check-cadence.yaml", """# Risk-based cadence (editable). Daily primary run: 11:00 PM America/New_York.
frequent_2h_or_event:
  [service_restarts, failed_services, suspicious_ssh, new_public_listeners, outbound_change,
   registration_subscription_spike, 2fa_verification_spike, high_risk_process, high_risk_cloud_event,
   integrity_monitoring_failure, third_party_api_spike]
daily:
  [application_abuse_correlation, registration_anomalies, newsletter_email_anomalies,
   distinct_accounts_per_ip, klaviyo_hubspot_correlation, db_auth_warnings, source_integrity,
   recent_privileged_actions, dependency_changes, new_scheduled_tasks, changed_security_config]
weekly:
  [package_vuln_review, lockfile_integrity, public_exposure_review, dormant_key_review,
   firewall_nsg_consistency, tls_review, baseline_drift, cloud_identity_review, backup_security]
monthly_quarterly:
  [threat_model_refresh, playbook_validation, pentest_planning, retention_privacy_review,
   dr_security_exercise, admin_access_review, third_party_review, incident_trend_analysis]
event_driven:
  [critical_vuln_detected, service_restart, firewall_nsg_change, new_authorized_key, new_user,
   new_external_port, auth_anomaly, security_setting_change, third_party_quota_spike,
   deploy_changed_protected_endpoints, threat_intel_affects_installed_tech]
""")

# ================= HISTORY (seed the incident + baseline placeholders) =================
w("history/incident-history.md", f"# Incident history\n\n## INC-2026-001 ({TODAY}) RedBerry newsletter/registration abuse\nApp-level business-logic abuse, low-and-slow (~10 min). NOT VM compromise. Playbook PB-APP-001. Status: monitoring.\n")
w("history/baselines/known-good.md", f"""# Known-good baseline (authoritative — update via Architect only)  {TODAY}
- Expected services (active): bendcore, organics, nginx, odin-anchor-online, odin-web-online, postgres.
- Expected ports: 80,443 public; 22 owner-IP only; 4013/3000 localhost/NSG; 5432 localhost-only.
- Expected SSH keys: the owner's key(s). Expected admin user: mostafa.
- Expected cron/timers: OS defaults + approved app timers.
- Accepted risks / exceptions: dynamic owner IP; rejected .env/WordPress internet scans are benign.
""")
for d in ("history/investigations", "history/findings", "history/decisions", "history/approvals", "history/remediations"):
    (BASE / d).mkdir(parents=True, exist_ok=True)
    (BASE / d / ".keep").write_text("")

print("seeded SOC knowledge base at", BASE)
import subprocess
print("files:", subprocess.run(["find", str(BASE), "-type", "f"], capture_output=True, text=True).stdout.count("\n"))
