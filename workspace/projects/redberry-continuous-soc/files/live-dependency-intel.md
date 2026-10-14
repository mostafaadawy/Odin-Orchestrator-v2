# Live Dependency Threat Intelligence  (source: OSV.dev · 2026-07-15)

- Packages scanned: 1149
- Vulnerable packages: 36 (runtime-reachable: 18)
- Data-source state: Checked and healthy

## Prioritized (runtime-reachable first)

| Package | Version | Reachability | Vulns | Worst | Example CVE | Fixed in |
|---|---|---|---|---|---|---|
| axios | 1.13.2 | runtime | 23 | MODERATE | CVE-2026-44494 | 1.16.0 |
| next | 16.1.6 | runtime | 19 | HIGH | CVE-2026-44575 | 16.2.5 |
| nodemailer | 7.0.10 | runtime | 7 | MODERATE | GHSA-268h-hp4c-crq3 | 8.0.9 |
| multer | 2.0.2 | runtime | 5 | MODERATE | CVE-2026-5038 | 3.0.0-alpha.2 |
| lodash | 4.17.21 | runtime | 3 | MODERATE | CVE-2025-13465 | 4.18.0 |
| qs | 6.14.0 | runtime | 3 | MODERATE | CVE-2025-15284 | 6.14.1 |
| file-type | 21.0.0 | runtime | 2 | MODERATE | CVE-2026-31808 | 21.3.1 |
| path-to-regexp | 8.3.0 | runtime | 2 | MODERATE | CVE-2026-4923 | 8.4.0 |
| ws | 8.20.0 | runtime | 2 | MODERATE | CVE-2026-45736 | 8.20.1 |
| brace-expansion | 2.0.2 | runtime | 1 | MODERATE | CVE-2026-33750 | 1.1.13 |
| @nestjs/core | 11.1.8 | runtime | 1 | MODERATE | CVE-2026-35515 | 11.1.18 |
| body-parser | 2.2.0 | runtime | 1 | MODERATE | CVE-2025-13466 | 2.2.1 |

## Triage rule (do NOT report presence as compromise)
For each: is it runtime? externally reachable? vulnerable path used? fixed version available? upgrade breakage? Prioritize Exploitable-in-env > Likely > Installed-not-reachable. Presence of a CVE is NOT compromise — reachability + evidence required to escalate.

_Last updated by the Security Intelligence & Threat-Hunting Architect: 2026-07-15_
