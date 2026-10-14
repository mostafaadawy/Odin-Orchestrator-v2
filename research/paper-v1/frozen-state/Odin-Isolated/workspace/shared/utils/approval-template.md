# Approval Request — APR-0000 (EXAMPLE, not a live request)

**Request ID:** APR-0000 (illustrative)
**Date (UTC):** 2026-06-20T00:00:00Z
**Requested by:** DevOps & Cloud (coordinated by CTO Brain)
**Category:** ssl-certificate

## 1. What I want to do
Renew the expiring TLS certificate on the Azure VM for `app.odinmarkets.com` via the SSL runbook.

```
sudo certbot renew --cert-name app.odinmarkets.com --deploy-hook "systemctl reload nginx"
```

## 2. Why
The current certificate expires in 9 days; renewing now avoids an outage and browser warnings.

## 3. Impact & blast radius
- **Touches:** nginx TLS config on the production VM; one graceful reload.
- **Depends on / depended on by:** all HTTPS traffic to app.odinmarkets.com.
- **Reversible?** yes — previous cert + nginx config retained; reload is non-destructive.

## 4. Risk assessment
- **Risk level:** low
- **Reasoning:** standard renewal, graceful reload, no schema/data change.
- **Worst case:** reload fails → fall back to prior config (kept).
- **Mitigations:** dry-run first (`certbot renew --dry-run`); snapshot nginx config before.

## 5. Rollback plan
Restore `/etc/nginx` from the pre-change copy and `systemctl reload nginx`; cert files are versioned by certbot.

## 6. Owner decision
- [ ] APPROVED — proceed
- [ ] APPROVED WITH CHANGES
- [ ] REJECTED

**Owner notes:** _(example only — no action will be taken on this file)_
