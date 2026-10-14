# Direction — Security & Compliance (company-level, CTO reads FIRST)
Source: integrated from the original Security & Compliance agent charter (Jun 2026), previously orphaned.

## Hard rules (non-negotiable)
- **No new inbound port / public exposure without explicit approval + documented justification.**
  (This is the guardrail the `az`/firewall incident broke.)
- Security has **VETO** over any change touching sensitive data until remediated.
- Required reviewer for: payment flows, PHI handling, auth changes, new network exposure.
- core-rules §4: no raw PAN storage; PCI scope minimization; PHI encrypted + access-logged; append-only audit logs.

## Applies to
Backend, DevOps, Database, Frontend, and all SOC agents. Escalate blockers to the CTO.
