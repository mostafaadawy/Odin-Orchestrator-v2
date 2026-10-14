# Runbooks

Step-by-step procedures the agents follow. Every production/VM step in these runbooks is
**approval-gated** — the orchestrator raises an approval request before executing it.

| Runbook | Purpose |
|---------|---------|
| `approval-template.md` | The form for any code/config/VM approval request |
| `deploy.md` | Safe deployment to the Azure VM |
| `ssl-certificate.md` | Issue/renew TLS certificates |
| `security-scan.md` | Basic security scanning (passive first, active gated) |
| `revert.md` | Restore project state from a history snapshot |
