# Approval Request — TEMPLATE

> Copy this into `approvals/pending/APR-NNNN-<slug>.md` for any action that touches code,
> config, or the Azure VM. The orchestrator fills it out, then STOPS and waits for the owner.

---

**Request ID:** APR-NNNN
**Date (UTC):** YYYY-MM-DDTHH:MMZ
**Requested by:** <agent> (coordinated by CTO Brain)
**Category:** code-change | config-change | azure-vm-action | deployment | ssl-certificate | security-scan-active | database-migration | production-data-access | dependency-install | secret-change

## 1. What I want to do
<Exact description. Include the precise commands / diffs / file changes in full.>

```
<exact commands or code diff here — nothing hidden>
```

## 2. Why
<The goal this serves and why now.>

## 3. Impact & blast radius
- **Touches:** <files / services / VM / data>
- **Depends on / depended on by:** <what could be affected downstream>
- **Reversible?** yes/no — <how>

## 4. Risk assessment
- **Risk level:** low | medium | high | critical
- **Reasoning:** <why that level>
- **Worst case:** <what could go wrong>
- **Mitigations:** <safeguards, backups taken, staged rollout>

## 5. Rollback plan
<Exact steps to undo, including snapshot/backup reference.>

## 6. Owner decision
- [ ] APPROVED — proceed
- [ ] APPROVED WITH CHANGES — see notes
- [ ] REJECTED — see notes

**Owner notes:**
**Signed (owner):** ____________  **Decision date (UTC):** ____________

---
_On a decision, move this file to `approvals/approved/` or `approvals/rejected/` and log it
in `history/HISTORY.md` + `history/log.jsonl`._
