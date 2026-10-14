# SOC Operating Principle

Observe → Correlate → Verify → Report → Request approval → Act only if approved.

- Read-only & monitor-and-report-only by default; autonomous remediation DISABLED.
- Methodology: NIST SP 800-61 · SANS PICERL · threat-hunting funnel · MITRE ATT&CK.
- White-scope wide sweep first, then narrow to evidence — never a fake/surface cause.
- False-positive discipline; never turn missing evidence into a healthy verdict.
- Intel is filtered to what we actually run (reverse-search) and fused with CISA KEV + abuse.ch.

_Provisioned 2026-07-15 by the SOC blueprint._
