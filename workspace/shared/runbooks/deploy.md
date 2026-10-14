# Runbook: Safe Deployment to Azure VM

**Owner agent:** DevOps & Cloud · **Gate:** APPROVAL REQUIRED before any VM step.

## Preconditions
- `core-rules.md` read. Existing sync method confirmed and respected.
- QA go/no-go obtained. Security sign-off if sensitive data paths changed.
- Backup/snapshot of current deployed state taken.

## Steps
1. **Prepare** — build artifact locally; record version tied to a `history/` entry title.
2. **Approval** — raise `APR-NNNN` (category `deployment`) with exact commands, impact, rollback.
3. **Stage** — deploy to staging or a non-serving path; smoke test.
4. **Cutover** — switch traffic per existing sync method (no exposure changes without separate approval).
5. **Verify** — health checks, key flows, error logs clean.
6. **Log** — write BUILD/CHANGE entry to history; update `state/` for the dashboard.

## Rollback
Re-point to previous artifact/version; restore config from pre-change copy; verify health.
