# Runbook: SSL/TLS Certificate Issue & Renewal

**Owner agent:** DevOps & Cloud · **Gate:** APPROVAL REQUIRED before any VM step.

## Track expiry
Maintain cert inventory in `infra/azure/inventory.md`. Renew **before** 14 days to expiry.

## Steps
1. **Dry run** — validate renewal without changes (e.g. `certbot renew --dry-run`).
2. **Approval** — raise `APR-NNNN` (category `ssl-certificate`) incl. exact command + reload hook.
3. **Backup** — copy current cert + web server config.
4. **Renew** — execute approved command; graceful reload only.
5. **Verify** — confirm new expiry, valid chain, HTTPS works, no mixed-content.
6. **Log** — history entry; update inventory + dashboard state.

## Rollback
Restore prior cert + config from backup; graceful reload.

## Notes
Never widen ports/exposure to obtain a cert without a separate approval (respect IP allowlist).
