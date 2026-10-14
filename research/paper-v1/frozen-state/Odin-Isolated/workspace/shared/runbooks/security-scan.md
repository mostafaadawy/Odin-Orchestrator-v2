# Runbook: Basic Security Scanning

**Owner agent:** Security & Compliance · **Gate:** passive = allowed; active = APPROVAL REQUIRED.

## Passive (no approval needed)
- Dependency/CVE review of declared manifests.
- Static config review (TLS settings, headers, open-port inventory from owner-provided data).
- Secret-scanning of the codebase in the workspace (never logs secrets found — references only).

## Active (approval required)
- Any scan that sends traffic to the VM/production (port scan, vuln scan, fuzzing).
- Raise `APR-NNNN` (category `security-scan-active`) with scope, target IPs, timing, intensity.
- Respect closed ports and IP allowlist; coordinate timing with owner to avoid alarms.

## Output
Findings → severity-ranked report in `history/` (no raw secrets). Critical issues escalate immediately.
