# Incident History — Cross-Reference Index

Authoritative ID reconciliation so every SOC lane resolves to the same incident.

## INC-2026-001 — Fake-User / App-Abuse (run-1784584358)

**One incident, multiple IDs.** The following are the same thing and must not be treated as
separate investigations:

| Role | ID |
| --- | --- |
| SOC finding | **SOC-APP-001** |
| Incident | **INC-2026-001** |
| Base response playbook | **PB-APP-001** |
| Hunting playbook | **PB-HUNT-APP-001** |
| Run | **run-1784584358** |

- **Reconciled identity:** `SOC-APP-001` = `INC-2026-001` = `PB-APP-001`.
- **Hunting directive:** [PB-HUNT-APP-001 — fake-user-app-abuse-hunt.md](../playbooks/fake-user-app-abuse-hunt.md)
- **Run charter:** [run-1784584358-charter.md](../history/investigations/run-1784584358-charter.md)
- **No-overlap lock:** [ACTIVE-RUN.lock](../history/investigations/ACTIVE-RUN.lock) — held for the run; released at Lane 13 close.

### Scope & mode (from charter)

- **Mode:** Monitor-and-report-only.
- **Scope:** Fake-user / app-abuse only. Infra/network/host/VM and real-user data actions are
  out of scope.

### Lane guidance

Every lane MUST hunt this one reference. If a lane encounters another ID that appears to name a
different incident on the same fake-user / app-abuse surface, treat it as an **alias** of
`INC-2026-001` and record the mapping in the alias table below — do not open a parallel
investigation while `ACTIVE-RUN.lock` is held.

### ID alias table

| Alias encountered | Resolves to | Noted by | Date |
| --- | --- | --- | --- |
| _(none yet)_ | INC-2026-001 | — | — |
